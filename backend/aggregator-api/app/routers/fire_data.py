from fastapi import APIRouter, Depends, Query

from ..dependencies import verify_api_key

from ..internal.repositories.aggregator_repository import AggregatorRepository


# These routes expose Data Engineering source data to other backend services.
# They are internal and require the shared API key.
router = APIRouter(
    prefix="/internal/data",
    tags=["internal-data"],
    dependencies=[Depends(verify_api_key)]
)


@router.get("/fire-incidents")
async def get_fire_incidents(
    days: int = Query(default=14, ge=1, le=3650)
):
    repository = AggregatorRepository()

    return await repository.get_recent_fire_incidents_v2(days)


@router.get("/fire-risk-inputs")
async def get_fire_risk_inputs(
    hours: int = Query(
        default=720,
        ge=1,
        le=8760
    )
):
    """
    Return currently available Data Engineering weather/environmental
    data for Fire Risk Map AI integration.

    This endpoint exposes DE source data, NOT an AI ForecastRequest.
    """

    repository = AggregatorRepository()

    return await repository.get_fire_risk_source_data(hours)