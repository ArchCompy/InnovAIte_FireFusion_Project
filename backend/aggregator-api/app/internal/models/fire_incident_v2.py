from datetime import date, datetime
from pydantic import BaseModel


# Represents the newer Data Engineering fire incident schema.
#
# This model is intentionally separate from the existing FireEvent model so
# the legacy fire_events_full path can remain available while Backend moves
# toward the newer Location_Registry / Time_Registry / Fire_Incident_Record
# structure.
class FireIncidentV2(BaseModel):

    # Primary identifiers from Data Engineering.
    incident_id: int
    location_id: int
    time_id: int

    # Original source coordinates are retained for data lineage.
    original_latitude: float
    original_longitude: float

    # Indicates whether the record is active/historical and its source.
    record_type: str
    source: str

    # Optional NASA FIRMS metadata.
    satellite: str | None = None
    instrument: str | None = None
    acq_date: date | None = None
    acq_time: str | None = None

    # Optional raw fire measurements that may be required by AI Modelling.
    # Whether AI needs these directly is still a cross-stream decision.
    brightness_ti4: float | None = None
    brightness_ti5: float | None = None
    frp: float | None = None

    confidence: str | None = None
    daynight: str | None = None

    # Location information joined from Location_Registry.
    grid_latitude: float
    grid_longitude: float
    region_name: str | None = None

    # Time information joined from Time_Registry.
    datetime_record: datetime
    season: str | None = None