from fastapi import APIRouter, Depends, HTTPException

from ..internal.models.misinformation_models import (
    ActiveIncidentObject,
    NarrativeClusterObject,
    Post,
)
from ..internal.services.misinformation_service import MisinformationService, MisinformationUnavailableError

# tags used for categorising endpoints in Swagger documentation
router = APIRouter(prefix="/api/misinformation", tags=["misinformation"])

UNAVAILABLE_DETAIL = "Misinformation data temporarily unavailable"


@router.get("/narratives", response_model=list[NarrativeClusterObject])
async def get_all_narrative_cluster_objects(
    service: MisinformationService = Depends(MisinformationService),
):
    try:
        return await service.get_all_narrative_cluster_objects()
    except MisinformationUnavailableError:
        raise HTTPException(status_code=503, detail=UNAVAILABLE_DETAIL)


@router.get(
    "/narratives/{narrative_id}",
    response_model=NarrativeClusterObject,
)
async def get_narrative_cluster_object_by_id(
    narrative_id: str,
    service: MisinformationService = Depends(MisinformationService),
):
    try:
        result = await service.get_narrative_cluster_object_by_id(narrative_id)
    except MisinformationUnavailableError:
        raise HTTPException(status_code=503, detail=UNAVAILABLE_DETAIL)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Narrative cluster {narrative_id} not found")
    return result


@router.get(
    "/incidents/{incident_id}/narrative-cluster-objects",
    response_model=list[NarrativeClusterObject],
)
async def get_incident_narrative_cluster_objects(
    incident_id: str,
    service: MisinformationService = Depends(MisinformationService),
):
    try:
        return await service.get_incident_narrative_cluster_objects(incident_id)
    except MisinformationUnavailableError:
        raise HTTPException(status_code=503, detail=UNAVAILABLE_DETAIL)


@router.get("/posts", response_model=list[Post])
async def get_all_posts(
    service: MisinformationService = Depends(MisinformationService),
):
    try:
        return await service.get_all_posts()
    except MisinformationUnavailableError:
        raise HTTPException(status_code=503, detail=UNAVAILABLE_DETAIL)


@router.get("/posts/{post_id}", response_model=Post)
async def get_post_by_id(
    post_id: str,
    service: MisinformationService = Depends(MisinformationService),
):
    try:
        result = await service.get_post_by_id(post_id)
    except MisinformationUnavailableError:
        raise HTTPException(status_code=503, detail=UNAVAILABLE_DETAIL)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Post {post_id} not found")
    return result


@router.get("/incidents", response_model=list[ActiveIncidentObject])
async def get_all_active_incidents(
    service: MisinformationService = Depends(MisinformationService),
):
    try:
        return await service.get_all_active_incidents()
    except MisinformationUnavailableError:
        raise HTTPException(status_code=503, detail=UNAVAILABLE_DETAIL)


@router.get("/incidents/{incident_id}", response_model=ActiveIncidentObject)
async def get_active_incident_by_id(
    incident_id: str,
    service: MisinformationService = Depends(MisinformationService),
):
    try:
        result = await service.get_active_incident_by_id(incident_id)
    except MisinformationUnavailableError:
        raise HTTPException(status_code=503, detail=UNAVAILABLE_DETAIL)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")
    return result
