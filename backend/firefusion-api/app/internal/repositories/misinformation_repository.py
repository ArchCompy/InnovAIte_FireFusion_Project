from typing import Optional

from psycopg.rows import class_row

from .database import get_pool
from ..models.misinformation_models import NarrativeClusterObject, ActiveIncidentObject, Post


async def _fetch_all(model, query: str, params: tuple = ()) -> list:
    """Run a SELECT expected to return zero or more rows, via the shared pool."""
    async with get_pool().connection() as conn:
        async with conn.cursor(row_factory=class_row(model)) as cur:
            await cur.execute(query, params)
            return await cur.fetchall()


async def _fetch_one(model, query: str, params: tuple = ()):
    """Run a SELECT expected to return at most one row, via the shared pool."""
    async with get_pool().connection() as conn:
        async with conn.cursor(row_factory=class_row(model)) as cur:
            await cur.execute(query, params)
            return await cur.fetchone()


class MisinformationRepository:

    async def get_all_narrative_cluster_objects(self) -> list[NarrativeClusterObject]:
        return await _fetch_all(
            NarrativeClusterObject,
            "SELECT * FROM narrative_cluster_objects"
        )

    async def get_narrative_cluster_object_by_id(self, narrative_id: str) -> Optional[NarrativeClusterObject]:
        return await _fetch_one(
            NarrativeClusterObject,
            "SELECT * FROM narrative_cluster_objects WHERE narrative_id = %s",
            (narrative_id,)
        )

    async def get_incident_narrative_cluster_objects(self, incident_id: str) -> list[NarrativeClusterObject]:
        return await _fetch_all(
            NarrativeClusterObject,
            "SELECT * FROM narrative_cluster_objects WHERE incident_id = %s",
            (incident_id,)
        )

    async def get_all_posts(self) -> list[Post]:
        return await _fetch_all(Post, "SELECT * FROM posts")

    async def get_post_by_id(self, post_id: str) -> Optional[Post]:
        return await _fetch_one(
            Post,
            "SELECT * FROM posts WHERE id = %s",
            (post_id,)
        )

    async def get_all_active_incidents(self) -> list[ActiveIncidentObject]:
        return await _fetch_all(ActiveIncidentObject, "SELECT * FROM active_incident_objects")

    async def get_active_incident_by_id(self, incident_id: str) -> Optional[ActiveIncidentObject]:
        return await _fetch_one(
            ActiveIncidentObject,
            "SELECT * FROM active_incident_objects WHERE incident_id = %s",
            (incident_id,)
        )
