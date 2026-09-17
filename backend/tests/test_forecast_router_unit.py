"""Unit and contract tests for the Fire Risk Map forecast router."""

from pathlib import Path
import sys
from unittest.mock import AsyncMock

from fastapi import FastAPI, HTTPException
import pytest
from redis.exceptions import (
    ConnectionError as RedisConnectionError,
    TimeoutError as RedisTimeoutError,
)


APP_DIR = Path(__file__).resolve().parents[1] / "firefusion-api"

if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))


@pytest.fixture
def forecast_router(monkeypatch):
    monkeypatch.setenv(
        "CACHE_URL",
        "redis://localhost:6379/0",
    )

    from app.routers import forecast

    return forecast


@pytest.mark.asyncio
async def test_router_returns_forecast_payload(forecast_router):
    service = AsyncMock(spec=forecast_router.ForecastService)
    payload = {
        "type": "FeatureCollection",
        "features": [],
    }
    service.fetch_predictions.return_value = payload

    result = await forecast_router.get_bushfire_forecast(
        service=service,
    )

    assert result == payload
    service.fetch_predictions.assert_awaited_once_with()


@pytest.mark.parametrize(
    "dependency_error",
    [
        RedisConnectionError("redis unavailable"),
        RedisTimeoutError("redis timeout"),
    ],
    ids=["redis-unavailable", "redis-timeout"],
)


@pytest.mark.asyncio
async def test_router_returns_503_for_redis_failure(
    forecast_router,
    dependency_error,
):
    service = AsyncMock(spec=forecast_router.ForecastService)
    service.fetch_predictions.side_effect = dependency_error

    with pytest.raises(HTTPException) as exc_info:
        await forecast_router.get_bushfire_forecast(
            service=service,
        )

    assert exc_info.value.status_code == 503
    assert (
        exc_info.value.detail
        == "Forecast data temporarily unavailable"
    )
    service.fetch_predictions.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_router_returns_503_for_corrupt_cached_prediction(
    forecast_router,
):
    """Corrupt cached forecast data must be reported as unavailable."""
    from app.internal.services.forecast_service import (
        ForecastCacheCorruptionError,
    )

    service = AsyncMock(spec=forecast_router.ForecastService)
    service.fetch_predictions.side_effect = (
        ForecastCacheCorruptionError(
            "cached prediction was invalid"
        )
    )

    with pytest.raises(HTTPException) as exc_info:
        await forecast_router.get_bushfire_forecast(
            service=service,
        )

    assert exc_info.value.status_code == 503
    assert (
        exc_info.value.detail
        == "Forecast data temporarily unavailable"
    )
    service.fetch_predictions.assert_awaited_once_with()


def test_openapi_documents_forecast_503_response(forecast_router):
    app = FastAPI()
    app.include_router(forecast_router.router)

    responses = app.openapi()["paths"][
        "/api/bushfire-forecast"
    ]["get"]["responses"]

    assert "503" in responses
    assert (
        responses["503"]["description"]
        == "Forecast data temporarily unavailable"
    )


def test_openapi_documents_forecast_response_model(
    forecast_router,
):
    """The success response publishes the formal GeoJSON schema."""

    app = FastAPI()
    app.include_router(forecast_router.router)

    spec = app.openapi()
    success_response = spec["paths"][
        "/api/bushfire-forecast"
    ]["get"]["responses"]["200"]

    assert success_response["content"][
        "application/json"
    ]["schema"] == {
        "$ref": "#/components/schemas/FeatureCollection"
    }

    properties_schema = spec["components"]["schemas"][
        "Properties"
    ]

    assert "risk_factor" in properties_schema["required"]
    assert (
        "fire_probability"
        not in properties_schema["required"]
    )
    assert (
        "fire_probability"
        in properties_schema["properties"]
    )


@pytest.mark.asyncio
async def test_router_does_not_misreport_unexpected_error_as_503(
    forecast_router,
):
    """Unexpected programming errors must remain internal server errors."""
    service = AsyncMock(spec=forecast_router.ForecastService)
    service.fetch_predictions.side_effect = RuntimeError(
        "unexpected forecast failure"
    )

    with pytest.raises(
        RuntimeError,
        match="unexpected forecast failure",
    ):
        await forecast_router.get_bushfire_forecast(
            service=service,
        )

    service.fetch_predictions.assert_awaited_once_with()