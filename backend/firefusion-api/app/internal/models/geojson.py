from pydantic import BaseModel
from typing import Any

from .forecast_status import ForecastMeta

class Geometry(BaseModel):
    type: str  # "Point", "Polygon", etc.
    coordinates: list[Any]

class Properties(BaseModel):
    risk_factor: int

class Feature(BaseModel):
    type: str = "Feature"
    geometry: Geometry
    properties: Properties

class FeatureCollection(BaseModel):
    type: str = "FeatureCollection"
    features: list[Feature]

    # Freshness of the served forecast. Optional and additive so existing
    # Front-end clients reading only type/features are unaffected; omitted
    # entirely from the response when unset (see model_dump(exclude_none=True)
    # call sites in forecast_service.py).
    meta: ForecastMeta | None = None