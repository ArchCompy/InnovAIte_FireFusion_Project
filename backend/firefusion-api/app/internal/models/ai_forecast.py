from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator


# Current feature order expected by the AI model.
# This may expand later if live fire-event data is added,
# but the overall request structure is expected to stay the same.
EXPECTED_AI_FEATURE_NAMES = [
    "era5land_temperature_2m_c",
    "era5_dewpoint_temperature_2m_c",
    "era5_total_precipitation",
    "era5_u_component_of_wind_10m",
    "era5_v_component_of_wind_10m",
    "era5land_surface_solar_radiation_downwards",
    "era5land_skin_temperature_c",
]

AI_INPUT_TIMESTEPS = 30


class AIGridCellProperties(BaseModel):
    """
    Properties for one grid cell sent to the AI forecast endpoint.
    Each cell contains 30 historical timesteps of model input data.
    """

    id: str
    observations: list[list[float]]
    timestamps: list[datetime]
    grid_row: int
    grid_col: int

    @model_validator(mode="after")
    def validate_observation_shape(self):
        # The current model expects 30 historical timesteps per cell.
        if len(self.observations) != AI_INPUT_TIMESTEPS:
            raise ValueError(
                f"AI forecast request requires {AI_INPUT_TIMESTEPS} "
                f"observation timesteps, received {len(self.observations)}"
            )

        if len(self.timestamps) != AI_INPUT_TIMESTEPS:
            raise ValueError(
                f"AI forecast request requires {AI_INPUT_TIMESTEPS} "
                f"timestamps, received {len(self.timestamps)}"
            )

        return self


class AIGridCell(BaseModel):
    """
    GeoJSON Feature representing one model input grid cell.
    """

    type: str = "Feature"
    geometry: dict[str, Any]
    properties: AIGridCellProperties


class AIForecastRequest(BaseModel):
    """
    Request structure used for POST /predict/bushfire/forecast.

    feature_names defines the order of values in each observations row.
    The number of model input features can change without changing the
    overall GeoJSON request structure.
    """

    type: str = "FeatureCollection"
    features: list[AIGridCell]

    feature_names: list[str] = Field(
        default_factory=lambda: EXPECTED_AI_FEATURE_NAMES.copy()
    )

    @model_validator(mode="after")
    def validate_feature_shape(self):
        # Every observation row must match the supplied feature_names order.
        expected_count = len(self.feature_names)

        for feature in self.features:
            for index, observation in enumerate(
                feature.properties.observations
            ):
                if len(observation) != expected_count:
                    raise ValueError(
                        f"Observation {index} contains "
                        f"{len(observation)} values but "
                        f"{expected_count} feature_names were supplied"
                    )

        return self