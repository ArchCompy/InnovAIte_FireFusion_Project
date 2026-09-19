"""Tests for forecast history: persistence, point-in-time replay, and retention.

Exercise the real ForecastService with cache_client, ws_manager and the
history repository mocked, so these fail if forecast_service.py's behaviour
regresses. See docs/forecast-history.md for the capability this covers.

Skip if the service's runtime dependencies are not installed locally, same
as test_forecast_service_unit.py and test_graceful_degradation.py.
"""
import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

APP_DIR = Path(__file__).resolve().parents[1] / "firefusion-api"

# RabbitMQ the running stack consumes predictions from. Overridable, like
# TEST_CACHE_URL in conftest.py, so the test can target a stack that isn't on
# the default port instead of publishing into whichever broker owns 5672.
TEST_BROKER_URL = os.getenv("TEST_BROKER_URL", "amqp://guest:guest@localhost:5672")
REPO_SOURCE_PATH = (
    APP_DIR / "app" / "internal" / "repositories" / "forecast_history_repository.py"
)

VALID_PAYLOAD = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [142.1560, -37.5600],
                    [142.3200, -37.7400],
                    [142.5100, -37.6500],
                    [142.3800, -37.5100],
                    [142.1560, -37.5600],
                ]],
            },
            "properties": {"risk_factor": 1},
        }
    ],
}


@pytest.fixture
def forecast_module(monkeypatch):
    """Import the real forecast_service module, with its cache client mocked."""
    if str(APP_DIR) not in sys.path:
        sys.path.insert(0, str(APP_DIR))
    # forecast_service imports shared.tracing; backend/ (APP_DIR's parent)
    # is where that top-level shared/ package lives.
    if str(APP_DIR.parent) not in sys.path:
        sys.path.insert(0, str(APP_DIR.parent))
    monkeypatch.setenv("CACHE_URL", "redis://localhost:6379")
    # config.config.Environment requires these even though history logic
    # never touches the broker, matching the other unit test fixtures.
    monkeypatch.setenv("DB_URL", "postgresql://localhost/unused")
    monkeypatch.setenv("BROKER_URL", "amqp://localhost/unused")
    try:
        from app.internal.services import forecast_service as fs
    except Exception as exc:
        pytest.skip(f"forecast_service dependencies unavailable locally: {exc}")
    return fs


@pytest.fixture
def service(forecast_module, monkeypatch):
    """Real ForecastService with cache, ws_manager and history repository mocked."""
    cache = AsyncMock()
    ws = AsyncMock()
    history_repo = AsyncMock()
    monkeypatch.setattr(forecast_module, "cache_client", cache, raising=True)
    monkeypatch.setattr(forecast_module, "ws_manager", ws, raising=True)
    svc = forecast_module.ForecastService()
    svc.history_repository = history_repo
    return svc, cache, ws, history_repo


# --- a stored prediction is recorded in history ---

@pytest.mark.asyncio
async def test_store_prediction_records_history(service):
    svc, cache, ws, history_repo = service

    result = await svc.store_prediction(VALID_PAYLOAD)

    history_repo.insert.assert_awaited_once()
    generated_at_arg, payload_arg = history_repo.insert.await_args.args
    assert isinstance(generated_at_arg, datetime)
    assert payload_arg == result


# --- a history write failure does not break store_prediction ---

@pytest.mark.asyncio
async def test_history_write_failure_does_not_break_store_prediction(service, caplog):
    svc, cache, ws, history_repo = service
    history_repo.insert.side_effect = ConnectionError("db unreachable")

    with caplog.at_level(logging.ERROR):
        result = await svc.store_prediction(VALID_PAYLOAD)

    # Live delivery must be entirely unaffected by the history failure.
    assert result["type"] == "FeatureCollection"
    assert result["features"] == VALID_PAYLOAD["features"]
    assert cache.set.await_count == 2, "cache writes (predictions, generated_at) must still happen"
    ws.broadcast.assert_awaited_once()
    assert any(r.levelno >= logging.ERROR for r in caplog.records), (
        "history failure must be logged at ERROR level"
    )


# --- at?timestamp= returns the forecast current at that time ---

@pytest.mark.asyncio
async def test_get_forecast_at_returns_none_when_nothing_recorded(service):
    svc, cache, ws, history_repo = service
    history_repo.get_at.return_value = None

    result = await svc.get_forecast_at(datetime.now(timezone.utc))

    assert result is None, "the router turns this into a 404"


@pytest.mark.asyncio
async def test_get_forecast_at_matches_live_endpoint_response_shape(service, forecast_module):
    """Contract: /at must return the same FeatureCollection shape as the live endpoint."""
    from app.internal.models.forecast_history import ForecastHistoryRecord

    svc, cache, ws, history_repo = service
    history_repo.get_at.return_value = ForecastHistoryRecord(
        id=1,
        generated_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        payload=VALID_PAYLOAD,
        created_at=datetime.now(timezone.utc),
    )

    result = await svc.get_forecast_at(datetime.now(timezone.utc))

    # Must round-trip through the same model the live endpoint uses.
    parsed = forecast_module.FeatureCollection(**result)
    assert parsed.features[0].properties.risk_factor == 1
    assert result["meta"]["status"] in ("live", "stale")
    assert "stale_after_seconds" in result["meta"]


@pytest.mark.asyncio
async def test_get_forecast_at_passes_through_the_requested_timestamp(service):
    """Contract: querying at a given moment asks the repository for that moment.

    The at-or-before-not-after semantics live in the repository's SQL
    (ORDER BY generated_at DESC LIMIT 1, WHERE generated_at <= %s), locked in
    separately below since a mock can't prove SQL correctness.
    """
    svc, cache, ws, history_repo = service
    history_repo.get_at.return_value = None
    timestamp = datetime(2026, 1, 1, 14, 47, tzinfo=timezone.utc)

    await svc.get_forecast_at(timestamp)

    history_repo.get_at.assert_awaited_once_with(timestamp)


def test_get_at_query_is_at_or_before_ordered_newest_first():
    """Lock in the SQL semantics a mock can't verify: at-or-before, not the nearest later one."""
    source = REPO_SOURCE_PATH.read_text()
    assert "WHERE generated_at <= %s" in source, (
        "get_at must select rows at or before the timestamp, not after it"
    )
    assert "ORDER BY generated_at DESC" in source


# --- a timestamp before any recorded forecast returns 404 (verified via router in test_smoke-style below) ---
# get_forecast_at returning None (covered above) is exactly what the router
# turns into a 404; see misinformation_controller.py/forecast.py for the
# established None -> 404 convention this reuses.


# --- history window respects from, to and limit ---

@pytest.mark.asyncio
async def test_get_forecast_history_passes_through_window(service):
    svc, cache, ws, history_repo = service
    history_repo.get_window.return_value = []
    from_ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
    to_ts = datetime(2026, 1, 2, tzinfo=timezone.utc)

    await svc.get_forecast_history(from_ts, to_ts, limit=50)

    history_repo.get_window.assert_awaited_once_with(from_ts, to_ts, 50)


@pytest.mark.asyncio
async def test_get_forecast_history_clamps_limit_to_the_configured_maximum(service, forecast_module):
    svc, cache, ws, history_repo = service
    history_repo.get_window.return_value = []
    from_ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
    to_ts = datetime(2026, 1, 2, tzinfo=timezone.utc)

    await svc.get_forecast_history(from_ts, to_ts, limit=10_000_000)

    passed_limit = history_repo.get_window.await_args.args[2]
    assert passed_limit == forecast_module.MAX_HISTORY_LIMIT


@pytest.mark.asyncio
async def test_get_forecast_history_response_shape_matches_live_endpoint(service, forecast_module):
    from app.internal.models.forecast_history import ForecastHistoryRecord

    svc, cache, ws, history_repo = service
    history_repo.get_window.return_value = [
        ForecastHistoryRecord(
            id=2,
            generated_at=datetime.now(timezone.utc) - timedelta(minutes=1),
            payload=VALID_PAYLOAD,
            created_at=datetime.now(timezone.utc),
        ),
    ]

    results = await svc.get_forecast_history(
        datetime.now(timezone.utc) - timedelta(hours=1),
        datetime.now(timezone.utc),
    )

    assert len(results) == 1
    parsed = forecast_module.FeatureCollection(**results[0])
    assert parsed.features[0].properties.risk_factor == 1
    assert "status" in results[0]["meta"]


# --- retention pruning removes only rows older than the cutoff ---

@pytest.mark.asyncio
async def test_prune_expired_history_uses_the_configured_retention_window(service, forecast_module):
    svc, cache, ws, history_repo = service
    history_repo.prune_older_than.return_value = 3

    deleted = await svc.prune_expired_history()

    assert deleted == 3
    history_repo.prune_older_than.assert_awaited_once()
    cutoff = history_repo.prune_older_than.await_args.args[0]
    expected_cutoff = datetime.now(timezone.utc) - timedelta(
        days=forecast_module.environment.forecast_history_retention_days
    )
    assert abs((cutoff - expected_cutoff).total_seconds()) < 5


def test_prune_query_deletes_strictly_older_than_cutoff():
    """Lock in the SQL semantics: strictly older than, so a row exactly at the cutoff is kept."""
    source = REPO_SOURCE_PATH.read_text()
    assert "WHERE generated_at < %s" in source


# --- integration: the real pipeline, real replay, against the running stack ---

def _publish_prediction(channel, aio_pika, risk_factor: int):
    payload = {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [142.1560, -37.5600], [142.3200, -37.7400],
                    [142.5100, -37.6500], [142.3800, -37.5100],
                    [142.1560, -37.5600],
                ]],
            },
            "properties": {"risk_factor": risk_factor},
        }],
    }
    return channel.default_exchange.publish(
        aio_pika.Message(body=json.dumps(payload).encode()),
        routing_key="predictions",
    )


@pytest.mark.integration
def test_forecast_history_end_to_end_via_running_stack(ff, http):
    """Publish real predictions through the production RabbitMQ path (the
    same queue MessagingService consumes in app/main.py's lifespan), then
    verify /at replays the correct historical picture and /history returns
    the window newest first. This is the same mechanism a live prediction
    from AI Modelling uses, so it also proves the wiring end to end.
    """
    try:
        import aio_pika
    except Exception as exc:
        pytest.skip(f"aio_pika unavailable locally: {exc}")

    async def run():
        try:
            connection = await aio_pika.connect_robust(
                TEST_BROKER_URL, timeout=5
            )
        except Exception as exc:
            pytest.skip(f"RabbitMQ not reachable locally: {exc}")
            return

        try:
            channel = await connection.channel()
            await channel.declare_queue("predictions", durable=True)

            # Distinct risk_factor values stand in for a unique marker,
            # since Properties only carries risk_factor.
            old_marker, new_marker = 2, 3

            async def poll_current_risk_factor(expected, timeout=10.0):
                deadline = asyncio.get_event_loop().time() + timeout
                while asyncio.get_event_loop().time() < deadline:
                    r = http.get(f"{ff}/api/bushfire-forecast")
                    body = r.json()
                    features = body.get("features") or []
                    if features and features[0]["properties"]["risk_factor"] == expected:
                        return True
                    await asyncio.sleep(0.2)
                return False

            await _publish_prediction(channel, aio_pika, old_marker)
            assert await poll_current_risk_factor(old_marker), (
                "the old prediction was never consumed off the queue"
            )
            boundary = datetime.now(timezone.utc)
            await asyncio.sleep(0.3)

            await _publish_prediction(channel, aio_pika, new_marker)
            assert await poll_current_risk_factor(new_marker), (
                "the new prediction was never consumed off the queue"
            )

            return boundary
        finally:
            await connection.close()

    boundary = asyncio.run(run())
    if boundary is None:
        return  # skipped inside run()

    # /at boundary must replay the OLD forecast, not the new one.
    r = http.get(f"{ff}/api/bushfire-forecast/at", params={"timestamp": boundary.isoformat()})
    assert r.status_code == 200
    body = r.json()
    assert body["features"][0]["properties"]["risk_factor"] == 2
    assert body["meta"]["status"] in ("live", "stale")

    # A timestamp before anything was ever recorded returns 404.
    r = http.get(
        f"{ff}/api/bushfire-forecast/at",
        params={"timestamp": "2000-01-01T00:00:00Z"},
    )
    assert r.status_code == 404

    # /history over a window spanning both returns both, newest first.
    r = http.get(f"{ff}/api/bushfire-forecast/history", params={
        "from": (boundary - timedelta(seconds=5)).isoformat(),
        "to": datetime.now(timezone.utc).isoformat(),
    })
    assert r.status_code == 200
    entries = r.json()
    assert len(entries) >= 2
    assert entries[0]["features"][0]["properties"]["risk_factor"] == 3, "newest first"

    # limit is bounded: an excessive request is rejected, not truncated silently.
    r = http.get(f"{ff}/api/bushfire-forecast/history", params={
        "from": (boundary - timedelta(seconds=5)).isoformat(),
        "to": datetime.now(timezone.utc).isoformat(),
        "limit": 999999,
    })
    assert r.status_code == 422
