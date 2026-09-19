import logging

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from redis.exceptions import RedisError
from ..internal.models.geojson import FeatureCollection
from ..internal.services.forecast_service import (
    ForecastCacheCorruptionError,
    ForecastService,
)
from ..internal.services.websocket_connection_manager import ws_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["bushfire"])


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()  # leave connection open until user dc
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


@router.get(
    "/bushfire-forecast",
    tags=["bushfire"],
    summary="Fire Risk Map data",
    response_model=FeatureCollection,
    response_model_exclude_none=True,
    response_description="GeoJSON FeatureCollection of bushfire risk polygons (risk_factor 1=extreme to 5=very low)",
    responses={
        200: {
            "description": "Risk polygons as GeoJSON. risk_factor uses the Front-end scale where 1 is extreme and 5 is very low. Returns an empty FeatureCollection when no prediction is available.",
            "content": {
                "application/json": {
                    "example": {
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
                                "properties": {"risk_factor": 2, "fire_probability": 0.78},
                            }
                        ],
                    }
                }
            },
        },
        503: {"description": "Forecast data temporarily unavailable"},
    },
)


async def get_bushfire_forecast(
    service: ForecastService = Depends(ForecastService),
):
    """Serve Fire Risk Map data as a GeoJSON FeatureCollection.

    Missing prediction data returns an empty FeatureCollection. Redis
    dependency failures and corrupted cached predictions are reported as
    temporary service unavailability.

    See docs/fire-risk-map-api-contract.md.
    """

    try:
        return await service.fetch_predictions()
    except RedisError as exc:
        logger.exception(
            "Redis failure while fetching bushfire forecast"
        )
        raise HTTPException(
            status_code=503,
            detail="Forecast data temporarily unavailable",
        ) from exc
    except ForecastCacheCorruptionError as exc:
        logger.warning(
            "Cached bushfire forecast was invalid: %s",
            exc,
        )
        raise HTTPException(
            status_code=503,
            detail="Forecast data temporarily unavailable",
        ) from exc