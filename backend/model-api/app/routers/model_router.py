from fastapi import APIRouter, Depends

from ..internal.services.geojson_service import GeoJsonService
from ..internal.services.security import verify_api_key

router = APIRouter(
    prefix="/model",
    tags=["model"]
)
geojson_service = GeoJsonService()


@router.get("/hello")
async def hello():
    """Unauthenticated liveness check, used by health probes and CI."""
    return {"message": "Hello from model-api"}


# Serves model output to other backend services, so it requires the shared
# API key. The security dependency already existed in the codebase but was
# not applied to any route.
@router.get("/geojson", dependencies=[Depends(verify_api_key)])
async def get_geojson():
    return geojson_service.get_geojson()
