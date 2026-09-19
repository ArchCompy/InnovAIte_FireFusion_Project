from enum import Enum
from pydantic import BaseModel


class ForecastStatus(str, Enum):
    LIVE = "live"
    STALE = "stale"
    UNAVAILABLE = "unavailable"


class ForecastMeta(BaseModel):
    status: ForecastStatus

    # ISO 8601 UTC timestamp the served forecast was generated at.
    # Absent when no forecast has ever been received, or its age is unknown.
    generated_at: str | None = None

    # Absent rather than 0 when the age cannot be determined, so the
    # Front-end never mistakes "unknown" for "just generated".
    age_seconds: int | None = None

    # The freshness window this forecast was classified against.
    stale_after_seconds: int

    # Written to be displayed directly by the dashboard.
    message: str | None = None
