from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ForecastHistoryRecord(BaseModel):
    id: int
    generated_at: datetime
    payload: dict[str, Any]
    created_at: datetime
