"""Unit tests for ForecastService read and write paths.

These tests execute the real production ForecastService while replacing Redis
and WebSocket dependencies with mocks. Missing runtime dependencies are test
setup failures, not reasons to skip core tests.
"""

from copy import deepcopy
import json
from pathlib import Path
import sys
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError
from redis.exceptions import (
    ConnectionError as RedisConnectionError,
    TimeoutError as RedisTimeoutError,
)


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
    """Import the real production ForecastService module."""
    if str(APP_DIR) not in sys.path:
        sys.path.insert(0, str(APP_DIR))

    monkeypatch.setenv("CACHE_URL", "redis://localhost:6379")

    from app.internal.services import forecast_service as fs

    return fs


@pytest.fixture
def service(forecast_module, monkeypatch):
    """Return the real ForecastService with cache_client replaced by a mock."""
    cache = AsyncMock()
    monkeypatch.setattr(forecast_module, "cache_client", cache, raising=True)
    return forecast_module.ForecastService(), cache


@pytest.fixture
def prediction_pipeline(forecast_module, monkeypatch):
    """Provide mocked Redis and WebSocket dependencies."""
    cache = AsyncMock()
    websocket = AsyncMock()

    monkeypatch.setattr(
        forecast_module,
        "cache_client",
        cache,
        raising=True,
    )
    monkeypatch.setattr(
        forecast_module,
        "ws_manager",
        websocket,
        raising=True,
    )

    return forecast_module.ForecastService(), cache, websocket


@pytest.mark.asyncio
async def test_returns_empty_feature_collection_when_no_data(service):
    """No cached prediction returns an empty FeatureCollection."""
    svc, cache = service
    cache.get.return_value = None

    result = await svc.fetch_predictions()

    assert result == EMPTY_FEATURE_COLLECTION
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
@pytest.mark.parametrize(
    "cached",
    [
        pytest.param("", id="empty-string"),
        pytest.param("not-json-at-all", id="malformed-json"),
        pytest.param("null", id="json-null"),
        pytest.param("123", id="json-number"),
        pytest.param('"a string"', id="json-string"),
        pytest.param("[]", id="json-array"),
        pytest.param("{}", id="missing-feature-collection-fields"),
        pytest.param(
            '{"type": "Feature"}',
            id="wrong-geojson-type",
        ),
    ],
)
async def test_corrupt_cached_prediction_raises_explicit_error(
    service,
    forecast_module,
    cached,
):
    """Present but unusable cached data must be reported as corruption."""
    svc, cache = service
    cache.get.return_value = cached

    with pytest.raises(
        forecast_module.ForecastCacheCorruptionError,
    ):
        await svc.fetch_predictions()

    cache.get.assert_awaited_once_with("predictions")


@pytest.mark.asyncio
async def test_valid_payload_is_returned_intact(service):
    """A well-formed cached prediction passes through unchanged."""
    svc, cache = service
    cache.get.return_value = json.dumps(VALID_PAYLOAD)

    result = await svc.fetch_predictions()

    assert result["type"] == "FeatureCollection"
    assert len(result["features"]) == 1


@pytest.mark.asyncio
async def test_cache_connection_failure_propagates_to_router(service):
    """Redis connection failures must propagate to the router."""
    svc, cache = service
    cache.get.side_effect = RedisConnectionError(
        "redis unavailable"
    )

    with pytest.raises(
        RedisConnectionError,
        match="redis unavailable",
    ):
        await svc.fetch_predictions()

    cache.get.assert_awaited_once_with("predictions")


@pytest.mark.asyncio
async def test_store_prediction_caches_and_broadcasts_validated_payload(
    prediction_pipeline,
):
    """Valid predictions use the same payload for cache, broadcast and return."""
    svc, cache, websocket = prediction_pipeline

    result = await svc.store_prediction(deepcopy(VALID_PAYLOAD))

    cache.set.assert_awaited_once()
    cache_key, cached_json = cache.set.await_args.args

    assert cache_key == "predictions"
    assert json.loads(cached_json) == result
    websocket.broadcast.assert_awaited_once_with(result)
    assert result == VALID_PAYLOAD


@pytest.mark.asyncio
async def test_store_prediction_rejects_invalid_payload_without_side_effects(
    prediction_pipeline,
):
    """Validation must happen before Redis or WebSocket side effects."""
    svc, cache, websocket = prediction_pipeline
    invalid_payload = deepcopy(VALID_PAYLOAD)
    invalid_payload["features"][0]["properties"]["risk_factor"] = 0

    with pytest.raises(ValidationError):
        await svc.store_prediction(invalid_payload)

    cache.set.assert_not_awaited()
    websocket.broadcast.assert_not_awaited()


@pytest.mark.asyncio
async def test_store_prediction_does_not_broadcast_when_cache_write_fails(
    prediction_pipeline,
):
    """A failed Redis write must propagate and prevent a stale broadcast."""
    svc, cache, websocket = prediction_pipeline
    cache.set.side_effect = RedisConnectionError(
        "redis unavailable"
    )

    with pytest.raises(
        RedisConnectionError,
        match="redis unavailable",
    ):
        await svc.store_prediction(deepcopy(VALID_PAYLOAD))

    cache.set.assert_awaited_once()
    websocket.broadcast.assert_not_awaited()


@pytest.mark.asyncio
async def test_cache_timeout_propagates_to_router(service):
    """Redis timeouts must not be misreported as an empty forecast."""
    svc, cache = service
    cache.get.side_effect = RedisTimeoutError("redis timeout")

    with pytest.raises(
        RedisTimeoutError,
        match="redis timeout",
    ):
        await svc.fetch_predictions()

    cache.get.assert_awaited_once_with("predictions")


@pytest.mark.asyncio
async def test_unexpected_schema_error_propagates_to_router(
    service,
    forecast_module,
    monkeypatch,
):
    """Unexpected model failures must not be disguised as empty data."""
    svc, cache = service
    cache.get.return_value = json.dumps(VALID_PAYLOAD)

    def raise_unexpected_error(**_payload):
        raise RuntimeError("unexpected schema failure")

    monkeypatch.setattr(
        forecast_module,
        "FeatureCollection",
        raise_unexpected_error,
    )

    with pytest.raises(
        RuntimeError,
        match="unexpected schema failure",
    ):
        await svc.fetch_predictions()

    cache.get.assert_awaited_once_with("predictions")
