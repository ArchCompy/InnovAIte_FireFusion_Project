from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    Field,
    StrictFloat,
    StrictInt,
    field_validator,
)

Coordinate = StrictInt | StrictFloat

Position = Annotated[
    list[Coordinate],
    Field(min_length=2, max_length=2),
]

LinearRing = Annotated[
    list[Position],
    Field(min_length=4),
]

PolygonCoordinates = Annotated[
    list[LinearRing],
    Field(min_length=1),
]


class Geometry(BaseModel):
    type: Literal["Polygon"]
    coordinates: PolygonCoordinates

    @field_validator("coordinates")
    @classmethod
    def validate_polygon_coordinates(
        cls,
        rings: PolygonCoordinates,
    ) -> PolygonCoordinates:
        for ring_index, ring in enumerate(rings):
            if ring[0] != ring[-1]:
                raise ValueError(
                    f"Polygon ring {ring_index} must be closed"
                )

            for position_index, position in enumerate(ring):
                longitude, latitude = position

                if not -180 <= longitude <= 180:
                    raise ValueError(
                        "Longitude at "
                        f"ring {ring_index}, position {position_index} "
                        "must be between -180 and 180"
                    )

                if not -90 <= latitude <= 90:
                    raise ValueError(
                        "Latitude at "
                        f"ring {ring_index}, position {position_index} "
                        "must be between -90 and 90"
                    )

        return rings


class Properties(BaseModel):
    risk_factor: StrictInt = Field(ge=1, le=5)
    fire_probability: StrictInt | StrictFloat | None = None

    @field_validator("fire_probability")
    @classmethod
    def validate_fire_probability(
        cls,
        probability: StrictInt | StrictFloat | None,
    ) -> StrictInt | StrictFloat | None:
        if probability is not None and not 0 <= probability <= 1:
            raise ValueError(
                "fire_probability must be between 0 and 1"
            )

        return probability


class Feature(BaseModel):
    type: Literal["Feature"]
    geometry: Geometry
    properties: Properties


class FeatureCollection(BaseModel):
    type: Literal["FeatureCollection"]
    features: list[Feature]
