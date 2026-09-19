"""Tests for graceful degradation of the Fire Risk Map forecast endpoint.

Exercise the real ForecastService with cache_client and ws_manager mocked, so
these fail if forecast_service.py's behaviour changes. See
docs/fire-risk-map-graceful-degradation.md for the behaviour these cover.

Skip if the service's runtime dependencies (FastAPI, Redis, aio_pika) are not
installed locally, same as test_forecast_service_unit.py.
"""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

APP_DIR = Path(__file__).resolve().parents[1] / "firefusion-api"

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
            # risk_factor 1 = extreme on the confirmed Front-end convention
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
    # forecast_service reads forecast_stale_after_seconds from config.config,
    # whose Environment requires these even though this module doesn't use them.
    monkeypatch.setenv("DB_URL", "postgresql://localhost/unused")
    monkeypatch.setenv("BROKER_URL", "amqp://localhost/unused")
    try:
        from app.internal.services import forecast_service as fs
    except Exception as exc:
        pytest.skip(f"forecast_service dependencies unavailable locally: {exc}")
    return fs


@pytest.fixture
def service(forecast_module, monkeypatch):
    """Return the real ForecastService with cache_client and ws_manager mocked."""
    cache = AsyncMock()
    ws = AsyncMock()
    monkeypatch.setattr(forecast_module, "cache_client", cache, raising=True)
    monkeypatch.setattr(forecast_module, "ws_manager", ws, raising=True)
    return forecast_module.ForecastService(), cache, ws


def _cache_returning(predictions, generated_at):
    """cache.get side_effect keyed by cache key, like real Redis GET would be."""
    values = {"predictions": predictions, "predictions:generated_at": generated_at}

    async def _get(key):
        return values.get(key)

    return _get


# --- table row: forecast within the freshness window -> live, served ---

@pytest.mark.asyncio
async def test_fresh_forecast_is_live(service):
    svc, cache, _ = service
    now = datetime.now(timezone.utc)
    cache.get.side_effect = _cache_returning(json.dumps(VALID_PAYLOAD), now.isoformat())

    result = await svc.fetch_predictions()

    assert result["meta"]["status"] == "live"
    assert result["meta"]["age_seconds"] == 0
    assert result["features"] == VALID_PAYLOAD["features"]


# --- table row: forecast older than the window -> stale, still served ---

@pytest.mark.asyncio
async def test_stale_forecast_is_still_served(service, forecast_module):
    svc, cache, _ = service
    stale_after = forecast_module.environment.forecast_stale_after_seconds
    old = datetime.now(timezone.utc) - timedelta(seconds=stale_after + 60)
    cache.get.side_effect = _cache_returning(json.dumps(VALID_PAYLOAD), old.isoformat())

    result = await svc.fetch_predictions()

    assert result["meta"]["status"] == "stale"
    assert result["meta"]["age_seconds"] >= stale_after
    assert result["features"] == VALID_PAYLOAD["features"], (
        "stale data must still be served, not dropped"
    )


# --- table row: no forecast ever received -> unavailable, empty ---

@pytest.mark.asyncio
async def test_no_forecast_ever_received_is_unavailable(service):
    svc, cache, _ = service
    cache.get.side_effect = _cache_returning(None, None)

    result = await svc.fetch_predictions()

    assert result["meta"]["status"] == "unavailable"
    assert result["features"] == []


# --- table row: forecast age unknown -> stale, served, never reported live ---

@pytest.mark.asyncio
async def test_unknown_age_is_stale_not_live(service):
    """A forecast is present but its timestamp key is missing.

    Overstating freshness is the dangerous error for an emergency tool, so
    this must never be reported as live.
    """
    svc, cache, _ = service
    cache.get.side_effect = _cache_returning(json.dumps(VALID_PAYLOAD), None)

    result = await svc.fetch_predictions()

    assert result["meta"]["status"] == "stale"
    assert "age_seconds" not in result["meta"], "unknown age must not be reported as 0"
    assert result["features"] == VALID_PAYLOAD["features"], (
        "data of unknown age must still be served, not dropped"
    )


@pytest.mark.asyncio
async def test_generated_at_as_bytes_is_still_classified_live(service):
    """Regression: redis-py returns bytes, not str, unless decode_responses is set.

    json.loads tolerates bytes transparently for the "predictions" key;
    datetime.fromisoformat does not, so a real Redis response for
    predictions:generated_at must not 500 the endpoint.
    """
    svc, cache, _ = service
    now = datetime.now(timezone.utc)
    cache.get.side_effect = _cache_returning(
        json.dumps(VALID_PAYLOAD).encode(), now.isoformat().encode()
    )

    result = await svc.fetch_predictions()

    assert result["meta"]["status"] == "live"
    assert result["features"] == VALID_PAYLOAD["features"]


@pytest.mark.asyncio
async def test_unparsable_timestamp_is_stale_not_live(service):
    """A corrupt timestamp must fail toward caution the same as a missing one."""
    svc, cache, _ = service
    cache.get.side_effect = _cache_returning(json.dumps(VALID_PAYLOAD), "not-a-timestamp")

    result = await svc.fetch_predictions()

    assert result["meta"]["status"] == "stale"
    assert result["features"] == VALID_PAYLOAD["features"]


# --- table row: cache itself unavailable -> raises, cannot degrade ---

@pytest.mark.asyncio
async def test_cache_failure_still_propagates(service):
    """A dependency failure must raise so the router returns 503, not degrade."""
    svc, cache, _ = service
    cache.get.side_effect = ConnectionError("redis unavailable")

    with pytest.raises(Exception):
        await svc.fetch_predictions()


# --- existing defensive handling degrades to unavailable, not an error ---

@pytest.mark.asyncio
async def test_malformed_cached_prediction_is_reported_not_disguised(service, forecast_module):
    """Damaged cache data is not "no forecast yet".

    A missing key degrades to unavailable, but a present-and-unusable value
    raises so the router returns 503 rather than showing a blank map as if
    there were simply nothing to report. Overstating "nothing to see" is the
    dangerous direction for an emergency tool.
    """
    svc, cache, _ = service
    cache.get.side_effect = _cache_returning("not-json-at-all", None)

    with pytest.raises(forecast_module.ForecastCacheCorruptionError):
        await svc.fetch_predictions()


# --- meta must be additive: old clients reading only type/features are unaffected ---

def test_feature_collection_omits_meta_key_when_unset(forecast_module):
    fc = forecast_module.FeatureCollection(type="FeatureCollection", features=[])

    dumped = fc.model_dump(exclude_none=True)

    assert "meta" not in dumped, "unset meta must be omitted, not sent as null"


# --- store_prediction: timestamp key and identical broadcast payload shape ---

@pytest.mark.asyncio
async def test_store_prediction_writes_generated_at(service):
    svc, cache, _ = service

    await svc.store_prediction(VALID_PAYLOAD)

    keys_set = {call.args[0] for call in cache.set.await_args_list}
    assert "predictions" in keys_set
    assert "predictions:generated_at" in keys_set

    generated_at_call = next(
        call for call in cache.set.await_args_list
        if call.args[0] == "predictions:generated_at"
    )
    # Must round-trip through datetime.fromisoformat like fetch_predictions does.
    datetime.fromisoformat(generated_at_call.args[1])


@pytest.mark.asyncio
async def test_broadcast_payload_carries_live_meta(service):
    """The WebSocket push and the REST response must share one payload shape."""
    svc, cache, ws = service

    await svc.store_prediction(VALID_PAYLOAD)

    ws.broadcast.assert_awaited_once()
    broadcast_payload = ws.broadcast.await_args.args[0]

    assert broadcast_payload["type"] == "FeatureCollection"
    assert broadcast_payload["features"] == VALID_PAYLOAD["features"]
    assert broadcast_payload["meta"]["status"] == "live"
    assert broadcast_payload["meta"]["age_seconds"] == 0
    assert "generated_at" in broadcast_payload["meta"]
