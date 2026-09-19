from typing import Iterable

from ..models.geojson import Feature
from .geometry import polygons_intersect
from .models import Region, RegionAssessment


def assess_region(features: Iterable[Feature], region: Region) -> RegionAssessment:
    """Summarise a forecast over one region.

    The region's risk is the most severe (lowest) risk_factor among the
    forecast polygons that touch it. Taking the worst rather than an average is
    deliberate: one extreme polygon inside the region is what a responder needs
    to hear about, however mild the rest of it is.
    """
    region_polygon = region.geometry.coordinates

    risk_factor: int | None = None
    feature_count = 0
    max_fire_probability: float | None = None

    for feature in features:
        if not polygons_intersect(region_polygon, feature.geometry.coordinates):
            continue

        feature_count += 1
        value = feature.properties.risk_factor
        if risk_factor is None or value < risk_factor:
            risk_factor = value

        probability = feature.properties.fire_probability
        if probability is not None and (
            max_fire_probability is None or probability > max_fire_probability
        ):
            max_fire_probability = float(probability)

    return RegionAssessment(
        risk_factor=risk_factor,
        feature_count=feature_count,
        max_fire_probability=max_fire_probability,
    )
