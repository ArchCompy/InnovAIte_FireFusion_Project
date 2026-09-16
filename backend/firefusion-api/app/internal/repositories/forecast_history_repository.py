from datetime import datetime
from typing import Optional

from psycopg.rows import class_row
from psycopg.types.json import Jsonb

from .database import get_pool
from ..models.forecast_history import ForecastHistoryRecord


class ForecastHistoryRepository:

    async def insert(self, generated_at: datetime, payload: dict) -> None:
        async with get_pool().connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "INSERT INTO forecast_history (generated_at, payload) VALUES (%s, %s)",
                    (generated_at, Jsonb(payload))
                )

    async def get_at(self, timestamp: datetime) -> Optional[ForecastHistoryRecord]:
        """Return the forecast that was current at the given moment.

        The most recent row at or before the timestamp, never a later one.
        """
        async with get_pool().connection() as conn:
            async with conn.cursor(row_factory=class_row(ForecastHistoryRecord)) as cur:
                await cur.execute(
                    """
                    SELECT id, generated_at, payload, created_at
                    FROM forecast_history
                    WHERE generated_at <= %s
                    ORDER BY generated_at DESC
                    LIMIT 1
                    """,
                    (timestamp,)
                )
                return await cur.fetchone()

    async def get_window(
        self,
        from_timestamp: datetime,
        to_timestamp: datetime,
        limit: int
    ) -> list[ForecastHistoryRecord]:
        """Return forecasts in [from_timestamp, to_timestamp], newest first."""
        async with get_pool().connection() as conn:
            async with conn.cursor(row_factory=class_row(ForecastHistoryRecord)) as cur:
                await cur.execute(
                    """
                    SELECT id, generated_at, payload, created_at
                    FROM forecast_history
                    WHERE generated_at >= %s AND generated_at <= %s
                    ORDER BY generated_at DESC
                    LIMIT %s
                    """,
                    (from_timestamp, to_timestamp, limit)
                )
                return await cur.fetchall()

    async def prune_older_than(self, cutoff: datetime) -> int:
        """Delete rows older than cutoff. Returns the number of rows removed."""
        async with get_pool().connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "DELETE FROM forecast_history WHERE generated_at < %s",
                    (cutoff,)
                )
                return cur.rowcount
