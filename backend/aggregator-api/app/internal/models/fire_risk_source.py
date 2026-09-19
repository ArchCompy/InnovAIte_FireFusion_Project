from datetime import datetime

from pydantic import BaseModel


class FireRiskSourceRecord(BaseModel):
    """
    One Data Engineering observation prepared by the Aggregator
    for the Fire Risk Map AI integration.

    Fields remain nullable at this boundary because the current
    Data Engineering dataset is not yet fully populated.

    AIRequestBuilder performs the stricter validation before any
    request is sent to AI Modelling.
    """

    # Canonical Data Engineering location identifier.
    location_id: int

    # Source time identifier used to join weather_observation
    # to time_registry.
    time_id: int | None = None

    # Timestamp used to order observations chronologically.
    #
    # This is currently nullable because DE has confirmed that
    # existing weather_observation rows do not yet contain time_id.
    datetime_record: datetime | None = None

    # Spatial location information from location_registry.
    grid_latitude: float
    grid_longitude: float

    # AI Modelling requires these integer grid indices.
    # DE has confirmed the columns exist but are not yet populated.
    grid_row: int | None = None
    grid_col: int | None = None

    region_name: str | None = None

    # Current seven AI Modelling input features.
    #
    # These columns now exist directly on weather_observation,
    # but DE has confirmed that the existing values are currently null.
    era5land_temperature_2m_c: float | None = None
    era5_dewpoint_temperature_2m_c: float | None = None
    era5_total_precipitation: float | None = None
    era5_u_component_of_wind_10m: float | None = None
    era5_v_component_of_wind_10m: float | None = None
    era5land_surface_solar_radiation_downwards: float | None = None
    era5land_skin_temperature_c: float | None = None