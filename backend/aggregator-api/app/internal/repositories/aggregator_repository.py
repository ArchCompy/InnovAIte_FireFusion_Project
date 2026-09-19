from psycopg import AsyncConnection

from ..models.fire_event import FireEvent
from ..models.fire_incident_v2 import FireIncidentV2
from ..models.fire_risk_source import FireRiskSourceRecord
from ...config.config import environment


# Existing query used by the current Backend event pipeline.
# This reads from the older fire_events_full PostgreSQL view and is kept
# available while the newer Data Engineering schema is introduced.
RECENT_DATA_SQL_QUERY = """
    SELECT * FROM fire_events_full
    WHERE event_date >= CURRENT_DATE - make_interval(days => %s)
    ORDER BY event_date DESC
"""


# Query used to retrieve fire incidents from the newer Data Engineering schema.
# Fire_Incident_Record is joined with Location_Registry and Time_Registry so
# Backend receives the fire data together with its location and time information.
RECENT_FIRE_INCIDENTS_V2_SQL = """
    SELECT
        fir.incident_id,
        fir.location_id,
        fir.time_id,
        fir.original_latitude,
        fir.original_longitude,
        fir.record_type,
        fir.source,
        fir.satellite,
        fir.instrument,
        fir.acq_date,
        fir.acq_time,
        fir.brightness_ti4,
        fir.brightness_ti5,
        fir.frp,
        fir.confidence,
        fir.daynight,

        lr.grid_latitude,
        lr.grid_longitude,
        lr.region_name,

        tr.datetime_record,
        tr.season

    FROM Fire_Incident_Record fir

    JOIN Location_Registry lr
        ON fir.location_id = lr.location_id

    JOIN Time_Registry tr
        ON fir.time_id = tr.time_id

    WHERE tr.datetime_record >= NOW() - make_interval(days => %s)

    ORDER BY tr.datetime_record DESC
"""


# Data Engineering has confirmed that the current seven AI Modelling
# input fields exist directly on public.weather_observation.
#
# weather_observation is joined with:
#
#   location_registry
#       -> grid_latitude / grid_longitude
#       -> grid_row / grid_col
#
#   time_registry
#       -> datetime_record
#
# The query represents the intended live DE -> Backend source shape.
# Current DE rows may still return no usable data because the ERA5
# fields, time_id, and grid indices are not yet fully populated.
FIRE_RISK_SOURCE_SQL = """
    SELECT
        wo.location_id,
        wo.time_id,

        -- Chronological timestamp required when constructing the
        -- 30-step AI Modelling observation sequence.
        tr.datetime_record,

        -- Canonical Data Engineering grid/location information.
        lr.grid_latitude,
        lr.grid_longitude,
        lr.grid_row,
        lr.grid_col,
        lr.region_name,

        -- Current seven ERA5 features required by AI Modelling.
        wo.era5land_temperature_2m_c,
        wo.era5_dewpoint_temperature_2m_c,
        wo.era5_total_precipitation,
        wo.era5_u_component_of_wind_10m,
        wo.era5_v_component_of_wind_10m,
        wo.era5land_surface_solar_radiation_downwards,
        wo.era5land_skin_temperature_c

    FROM weather_observation wo

    -- Data Engineering confirmed location_id as the relationship
    -- between weather observations and the canonical grid location.
    JOIN location_registry lr
        ON wo.location_id = lr.location_id

    -- Data Engineering confirmed time_id as the relationship used
    -- to obtain the timestamp for each observation.
    JOIN time_registry tr
        ON wo.time_id = tr.time_id

    -- Retrieve a recent time window while allowing enough history
    -- for Backend to construct the required 30-step AI input.
    WHERE tr.datetime_record >= NOW() - make_interval(hours => %s)

    -- Keep observations grouped by grid cell and ordered
    -- chronologically before they reach AIRequestBuilder.
    ORDER BY
        wo.location_id,
        tr.datetime_record ASC
"""


class AggregatorRepository:

    def __init__(self):
        # Database connection URL supplied through the Aggregator API
        # environment configuration.
        #
        # For the shared Data Engineering Supabase database this should
        # use the scoped aggregator_readonly PostgreSQL role rather than
        # a service-role credential.
        self.db_url = environment.relational_db_url

    async def get_recent_events(
        self,
        days: int = 14
    ) -> list[FireEvent]:

        # Get events from the last N days using the existing
        # fire_events_full database view.
        async with await AsyncConnection.connect(
            self.db_url
        ) as connection:

            async with connection.cursor() as cursor:

                # Execute the existing query and pass the requested
                # number of days as a SQL parameter.
                await cursor.execute(
                    RECENT_DATA_SQL_QUERY,
                    (days,)
                )

                # Return an empty list if the query does not return
                # any column information.
                if cursor.description is None:
                    return []

                # Extract the returned column names so they can be
                # matched with the values from each database row.
                columns = [
                    description[0]
                    for description in cursor.description
                ]

                # Retrieve each SELECT row as a tuple.
                rows: list[tuple] = await cursor.fetchall()

                # Convert each returned row into the existing
                # FireEvent model.
                events = []

                for row in rows:

                    # Match each column name with its corresponding
                    # row value.
                    row_dict = dict(zip(columns, row))

                    # Validate and convert the database row into
                    # FireEvent.
                    events.append(
                        FireEvent(**row_dict)
                    )

                return events

    async def get_recent_fire_incidents_v2(
        self,
        days: int = 14
    ) -> list[FireIncidentV2]:

        # Retrieve fire incidents using the newer Data Engineering
        # schema while keeping the existing get_recent_events()
        # pathway available.
        async with await AsyncConnection.connect(
            self.db_url
        ) as connection:

            async with connection.cursor() as cursor:

                # Query Fire_Incident_Record and join the related
                # location and time registry information.
                await cursor.execute(
                    RECENT_FIRE_INCIDENTS_V2_SQL,
                    (days,)
                )

                # Return an empty list if no column information
                # is available.
                if cursor.description is None:
                    return []

                # Extract the joined query column names for
                # model conversion.
                columns = [
                    description[0]
                    for description in cursor.description
                ]

                # Retrieve all matching database rows.
                rows: list[tuple] = await cursor.fetchall()

                # Convert each joined row into the
                # FireIncidentV2 model.
                return [
                    FireIncidentV2(
                        **dict(zip(columns, row))
                    )
                    for row in rows
                ]

    async def get_fire_risk_source_data(
        self,
        hours: int = 720
    ) -> list[FireRiskSourceRecord]:
        """
        Retrieve the Data Engineering records required to construct
        the AI Modelling bushfire forecast request.

        The intended source is:

            weather_observation
                -> location_registry
                -> time_registry

        The seven ERA5 feature columns are now confirmed by Data
        Engineering, so no substitution from the older general weather
        fields is performed here.

        The source data may currently be incomplete because DE has
        confirmed that the ERA5 values, time_id values, and grid indices
        are not yet fully populated.
        """

        async with await AsyncConnection.connect(
            self.db_url
        ) as connection:

            async with connection.cursor() as cursor:

                await cursor.execute(
                    FIRE_RISK_SOURCE_SQL,
                    (hours,)
                )

                if cursor.description is None:
                    return []

                # Use the returned SQL column names when converting each
                # row into the FireRiskSourceRecord model.
                columns = [
                    description[0]
                    for description in cursor.description
                ]

                rows: list[tuple] = await cursor.fetchall()

                return [
                    FireRiskSourceRecord(
                        **dict(zip(columns, row))
                    )
                    for row in rows
                ]