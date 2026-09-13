"""Unit tests for ForecastService.fetch_predictions.

These exercise the real production implementation with the cache client mocked,
so the tests fail if forecast_service.py changes behaviour.

They skip if the service's runtime dependencies (FastAPI, Redis, aio_pika) are not
installed locally. CI installs them, so the tests run there. The same guarantees are
also covered end to end in test_fire_risk_map_contract.py.
"""
import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

APP_DIR = Path(__file__).resolve().parents[1] / "firefusion-api"

EMPTY_FEATURE_COLLECTION = {"type": "FeatureCollection", "features": []}

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
    monkeypatch.setenv("CACHE_URL", "redis://localhost:6379")
    # forecast_service now reads forecast_stale_after_seconds from config.config,
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
    """Return the real ForecastService with cache_client replaced by a mock."""
    cache = AsyncMock()
    monkeypatch.setattr(forecast_module, "cache_client", cache, raising=True)
    return forecast_module.ForecastService(), cache


@pytest.mark.asyncio
async def test_returns_empty_feature_collection_when_no_data(service):
    """Contract: no cached prediction returns an empty FeatureCollection, not null."""
    svc, cache = service
    cache.get.return_value = None

    result = await svc.fetch_predictions()

    # Graceful degradation attaches meta (see test_graceful_degradation.py);
    # the type/features contract this test checks is otherwise unchanged.
    assert result["type"] == EMPTY_FEATURE_COLLECTION["type"]
    assert result["features"] == EMPTY_FEATURE_COLLECTION["features"]
    cache.get.assert_awaited_once_with("predictions")


@pytest.mark.asyncio
async def test_returns_cached_prediction_when_available(service):
    """Contract: a cached prediction is returned as a FeatureCollection."""
    svc, cache = service
    cache.get.return_value = json.dumps(VALID_PAYLOAD)

    result = await svc.fetch_predictions()

    assert result["type"] == "FeatureCollection"
    assert len(result["features"]) == 1
    assert result["features"][0]["properties"]["risk_factor"] == 1


@pytest.mark.asyncio
async def test_invalid_cached_json_falls_back_to_empty(service):
    """Contract: unusable cached data must not produce a malformed response."""
    svc, cache = service
    cache.get.return_value = "not-json-at-all"

    result = await svc.fetch_predictions()

    assert result["type"] == EMPTY_FEATURE_COLLECTION["type"]
    assert result["features"] == EMPTY_FEATURE_COLLECTION["features"]


@pytest.mark.asyncio
async def test_json_null_does_not_escape_as_none(service):
    """Regression: Redis holding the literal string "null".

    json.loads("null") succeeds and yields None, so a naive parse-then-fallback
    lets None through and the map client receives an invalid body.
    """
    svc, cache = service
    cache.get.return_value = "null"

    result = await svc.fetch_predictions()

    assert result is not None, 'cached "null" escaped as None'
    assert result["type"] == EMPTY_FEATURE_COLLECTION["type"]
    assert result["features"] == EMPTY_FEATURE_COLLECTION["features"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "cached",
    [
        None,             # nothing cached
        "",               # empty string
        "garbage",        # not JSON
        "null",           # valid JSON, decodes to None
        "123",            # valid JSON, decodes to an int
        '"a string"',     # valid JSON, decodes to a str
        "[]",             # valid JSON, decodes to a list
        "{}",             # object, but not a FeatureCollection
        '{"type": "Feature"}',  # wrong GeoJSON type
    ],
)
async def test_never_returns_a_non_feature_collection(service, cached):
    """Contract: whatever the cache holds, the result is a FeatureCollection."""
    svc, cache = service
    cache.get.return_value = cached

    result = await svc.fetch_predictions()

    assert result is not None, f"cache value {cached!r} produced None"
    assert isinstance(result, dict), f"cache value {cached!r} produced {type(result).__name__}"
    assert result.get("type") == "FeatureCollection", f"cache value {cached!r} produced {result!r}"
    assert isinstance(result.get("features"), list)


@pytest.mark.asyncio
async def test_valid_payload_is_returned_intact(service):
    """A well-formed cached prediction passes through unchanged."""
    svc, cache = service
    cache.get.return_value = json.dumps(VALID_PAYLOAD)

    result = await svc.fetch_predictions()

    assert result["type"] == "FeatureCollection"
    assert len(result["features"]) == 1


@pytest.mark.asyncio
async def test_cache_failure_propagates_for_503(service):
    """A cache/dependency failure must raise so the router can return 503."""
    svc, cache = service
    cache.get.side_effect = ConnectionError("redis unavailable")

    with pytest.raises(Exception):
        await svc.fetch_predictions()