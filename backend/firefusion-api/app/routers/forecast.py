import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from ..internal.services.forecast_service import (
    DEFAULT_HISTORY_LIMIT,
    MAX_HISTORY_LIMIT,
    ForecastService,
)
from ..internal.services.websocket_connection_manager import ws_manager
from ..internal.services.caching_service import cache_client

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
async def get_bushfire_forecast(service: ForecastService = Depends(ForecastService)):
    """Serve Fire Risk Map data as a GeoJSON FeatureCollection.

    Always returns a valid FeatureCollection so the map can render without
    special-casing missing data. See docs/fire-risk-map-api-contract.md.
    """
    try:
        return await service.fetch_predictions()
    except Exception:
        logger.exception("Failed to fetch bushfire forecast")
        raise HTTPException(status_code=503, detail="Forecast data temporarily unavailable")


@router.get(
    "/bushfire-forecast/at",
    tags=["bushfire"],
    summary="Fire Risk Map data at a past moment",
    response_description="The GeoJSON FeatureCollection that was current at the given timestamp",
    responses={
        404: {"description": "No forecast was recorded at or before the given timestamp"},
        503: {"description": "Forecast history temporarily unavailable"},
    },
)
async def get_bushfire_forecast_at(
    timestamp: datetime,
    service: ForecastService = Depends(ForecastService),
):
    """Serve the forecast that was current at a past moment.

    The most recent recorded forecast at or before timestamp, never a later
    one. Same FeatureCollection shape as GET /bushfire-forecast, so
    Front-end can reuse its existing rendering. See
    docs/forecast-history.md.
    """
    try:
        result = await service.get_forecast_at(timestamp)
    except Exception:
        logger.exception("Failed to fetch forecast history")
        raise HTTPException(status_code=503, detail="Forecast history temporarily unavailable")

    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"No forecast was recorded at or before {timestamp.isoformat()}",
        )
    return result


@router.get(
    "/bushfire-forecast/history",
    tags=["bushfire"],
    summary="Fire Risk Map data over a time window",
    response_description="GeoJSON FeatureCollections in the window, newest first",
    responses={
        503: {"description": "Forecast history temporarily unavailable"},
    },
)
async def get_bushfire_forecast_history(
    from_timestamp: datetime = Query(..., alias="from"),
    to_timestamp: datetime = Query(..., alias="to"),
    limit: int = Query(DEFAULT_HISTORY_LIMIT, ge=1, le=MAX_HISTORY_LIMIT),
    service: ForecastService = Depends(ForecastService),
):
    """Serve recorded forecasts across a time window, newest first.

    Drives a time slider over recent risk trend. limit defaults to
    100 and is capped at 1000, so a wide window cannot return everything
    at once. See docs/forecast-history.md.
    """
    try:
        return await service.get_forecast_history(from_timestamp, to_timestamp, limit)
    except Exception:
        logger.exception("Failed to fetch forecast history")
        raise HTTPException(status_code=503, detail="Forecast history temporarily unavailable")