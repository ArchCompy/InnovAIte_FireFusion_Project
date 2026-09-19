import logging
from typing import Optional

from ..models.misinformation_models import NarrativeClusterObject, Post, ActiveIncidentObject
from ..repositories.misinformation_repository import MisinformationRepository

logger = logging.getLogger(__name__)


class MisinformationUnavailableError(Exception):
    """Raised when the misinformation database cannot be reached.

    Distinct from a genuine empty result: the router translates this to a
    503, so an outage is never shown to the dashboard as "no misinformation
    detected".
    """


class MisinformationService:

    def __init__(self):
        self.misinformation_repository: MisinformationRepository = MisinformationRepository()

    async def get_all_narrative_cluster_objects(self) -> list[NarrativeClusterObject]:
        try:
            return await self.misinformation_repository.get_all_narrative_cluster_objects()
        except Exception as e:
            logger.exception("Failed to fetch narrative cluster objects")
            raise MisinformationUnavailableError() from e

    async def get_narrative_cluster_object_by_id(self, narrative_id: str) -> Optional[NarrativeClusterObject]:
        try:
            return await self.misinformation_repository.get_narrative_cluster_object_by_id(narrative_id)
        except Exception as e:
            logger.exception("Failed to fetch narrative cluster object %s", narrative_id)
            raise MisinformationUnavailableError() from e

    async def get_incident_narrative_cluster_objects(self, incident_id: str) -> list[NarrativeClusterObject]:
        try:
            return await self.misinformation_repository.get_incident_narrative_cluster_objects(incident_id)
        except Exception as e:
            logger.exception("Failed to fetch narrative cluster objects for incident %s", incident_id)
            raise MisinformationUnavailableError() from e

    async def get_all_posts(self) -> list[Post]:
        try:
            return await self.misinformation_repository.get_all_posts()
        except Exception as e:
            logger.exception("Failed to fetch posts")
            raise MisinformationUnavailableError() from e

    async def get_post_by_id(self, post_id: str) -> Optional[Post]:
        try:
            return await self.misinformation_repository.get_post_by_id(post_id)
        except Exception as e:
            logger.exception("Failed to fetch post %s", post_id)
            raise MisinformationUnavailableError() from e

    async def get_all_active_incidents(self) -> list[ActiveIncidentObject]:
        try:
            return await self.misinformation_repository.get_all_active_incidents()
        except Exception as e:
            logger.exception("Failed to fetch active incidents")
            raise MisinformationUnavailableError() from e

    async def get_active_incident_by_id(self, incident_id: str) -> Optional[ActiveIncidentObject]:
        try:
            return await self.misinformation_repository.get_active_incident_by_id(incident_id)
        except Exception as e:
            logger.exception("Failed to fetch active incident %s", incident_id)
            raise MisinformationUnavailableError() from e
