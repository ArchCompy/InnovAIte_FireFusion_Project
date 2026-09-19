# Current AI Modelling request uses 30 chronological
# observations for each grid cell.
AI_INPUT_STEPS = 30


# Current seven input features confirmed by AI Modelling.
#
# The order must remain consistent because every observation
# array in the AI request follows this sequence.
AI_FEATURE_NAMES = [
    "era5land_temperature_2m_c",
    "era5_dewpoint_temperature_2m_c",
    "era5_total_precipitation",
    "era5_u_component_of_wind_10m",
    "era5_v_component_of_wind_10m",
    "era5land_surface_solar_radiation_downwards",
    "era5land_skin_temperature_c",
]


# Data Engineering has now confirmed that all seven AI input fields
# exist directly on public.weather_observation.
#
# The values are currently still unpopulated, but once DE fills them
# Backend can pass them into the AI request without translating from
# unrelated weather fields such as temperature_c or wind_speed_kmh.
DE_TO_AI_FEATURE_MAPPING = {
    "era5land_temperature_2m_c":
        "era5land_temperature_2m_c",

    "era5_dewpoint_temperature_2m_c":
        "era5_dewpoint_temperature_2m_c",

    "era5_total_precipitation":
        "era5_total_precipitation",

    "era5_u_component_of_wind_10m":
        "era5_u_component_of_wind_10m",

    "era5_v_component_of_wind_10m":
        "era5_v_component_of_wind_10m",

    "era5land_surface_solar_radiation_downwards":
        "era5land_surface_solar_radiation_downwards",

    "era5land_skin_temperature_c":
        "era5land_skin_temperature_c",
}