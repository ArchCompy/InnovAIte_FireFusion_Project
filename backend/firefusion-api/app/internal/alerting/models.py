from enum import Enum

from pydantic import BaseModel, Field, model_validator

from ..models.geojson import Geometry

# Fire Risk Map convention: risk_factor 1 is the most severe, 5 the least.
MOST_SEVERE = 1
LEAST_SEVERE = 5


class Region(BaseModel):
    """The area a subscriber wants to be told about.

    Validated by the same Geometry model the forecast uses, so a region
    follows the same rules as the polygons it is compared against: closed
    rings, longitude and latitude in range.
    """

    geometry: Geometry

    @classmethod
    def from_bbox(
        cls,
        min_longitude: float,
        min_latitude: float,
        max_longitude: float,
        max_latitude: float,
    ) -> "Region":
        if min_longitude >= max_longitude or min_latitude >= max_latitude:
            raise ValueError("bbox minimum must be less than its maximum")

        return cls(
            geometry=Geometry(
                type="Polygon",
                coordinates=[[
                    [min_longitude, min_latitude],
                    [max_longitude, min_latitude],
                    [max_longitude, max_latitude],
                    [min_longitude, max_latitude],
                    [min_longitude, min_latitude],
                ]],
            )
        )


class AlertRule(BaseModel):
    """Alert when the region's risk reaches this risk_factor or worse.

    threshold_risk_factor=2 means "tell me at 2 (high) or 1 (extreme)".
    """

    region: Region
    threshold_risk_factor: int = Field(ge=MOST_SEVERE, le=LEAST_SEVERE)


class RegionAssessment(BaseModel):
    """How one forecast looks over one region.

    risk_factor is the most severe (lowest) value among the forecast polygons
    that touch the region, or None when none do.
    """

    risk_factor: int | None = Field(default=None, ge=MOST_SEVERE, le=LEAST_SEVERE)
    feature_count: int = Field(default=0, ge=0)
    max_fire_probability: float | None = Field(default=None, ge=0, le=1)

    @model_validator(mode="after")
    def _risk_factor_matches_feature_count(self):
        if (self.risk_factor is None) != (self.feature_count == 0):
            raise ValueError(
                "risk_factor must be set exactly when feature_count is above zero"
            )
        return self


class AlertKind(str, Enum):
    # Region was below the threshold (or had no forecast risk) and is now at
    # or beyond it.
    THRESHOLD_CROSSED = "threshold_crossed"
    # Region was already at or beyond the threshold and has got worse.
    ESCALATED = "escalated"


class AlertDecision(BaseModel):
    kind: AlertKind
    previous_risk_factor: int | None
    current_risk_factor: int
    feature_count: int
    max_fire_probability: float | None = None
