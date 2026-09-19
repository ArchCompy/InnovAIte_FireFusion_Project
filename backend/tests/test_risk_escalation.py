"""Unit tests for risk escalation detection.

These import the real alerting modules: polygon intersection, region
assessment, and the escalation decision. They need no database, broker or
running stack, so they run as plain unit tests. See
docs/risk-escalation-alerts.md.
"""

from pathlib import Path
import random
import sys

import pytest
from pydantic import ValidationError


APP_DIR = Path(__file__).resolve().parents[1] / "firefusion-api"

if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from app.internal.alerting import geometry
from app.internal.alerting.assessment import assess_region
from app.internal.alerting.detector import evaluate
from app.internal.alerting.models import (
    AlertKind,
    AlertRule,
    Region,
    RegionAssessment,
)
from app.internal.models.geojson import FeatureCollection


def rect(x1, y1, x2, y2):
    return [[[x1, y1], [x2, y1], [x2, y2], [x1, y2], [x1, y1]]]


def feature(x1, y1, x2, y2, risk, probability=None):
    properties = {"risk_factor": risk}
    if probability is not None:
        properties["fire_probability"] = probability
    return {
        "type": "Feature",
        "geometry": {"type": "Polygon", "coordinates": rect(x1, y1, x2, y2)},
        "properties": properties,
    }


def features_of(*items):
    return FeatureCollection(
        type="FeatureCollection", features=list(items)
    ).features


# --- segments ---

@pytest.mark.parametrize(
    "a,b,c,d,expected",
    [
        pytest.param((0, 0), (2, 2), (0, 2), (2, 0), True, id="crossing"),
        pytest.param((0, 0), (1, 1), (1, 1), (2, 0), True, id="touching-endpoints"),
        pytest.param((0, 0), (2, 0), (1, 0), (3, 0), True, id="collinear-overlap"),
        pytest.param((0, 0), (1, 0), (2, 0), (3, 0), False, id="collinear-disjoint"),
        pytest.param((0, 0), (2, 0), (0, 1), (2, 1), False, id="parallel"),
        pytest.param((0, 0), (1, 1), (2, 0), (3, 1), False, id="apart"),
        pytest.param((0, 0), (2, 0), (1, 0), (1, 5), True, id="t-junction"),
    ],
)
def test_segments_intersect(a, b, c, d, expected):
    assert geometry.segments_intersect(a, b, c, d) is expected
    assert geometry.segments_intersect(c, d, a, b) is expected


# --- point in polygon ---

L_SHAPE = [[[0, 0], [4, 0], [4, 2], [2, 2], [2, 4], [0, 4], [0, 0]]]
WITH_HOLE = [
    [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]],
    [[4, 4], [6, 4], [6, 6], [4, 6], [4, 4]],
]


@pytest.mark.parametrize(
    "point,polygon,expected",
    [
        pytest.param((1, 1), L_SHAPE, True, id="inside"),
        pytest.param((3, 3), L_SHAPE, False, id="in-the-notch-of-a-concave-shape"),
        pytest.param((5, 5), L_SHAPE, False, id="outside"),
        pytest.param((2, 0), L_SHAPE, True, id="on-an-edge"),
        pytest.param((0, 0), L_SHAPE, True, id="on-a-vertex"),
        pytest.param((5, 5), WITH_HOLE, False, id="strictly-inside-a-hole"),
        pytest.param((4, 5), WITH_HOLE, True, id="on-a-hole-edge"),
        pytest.param((1, 1), WITH_HOLE, True, id="in-material-around-a-hole"),
    ],
)
def test_point_in_polygon(point, polygon, expected):
    assert geometry.point_in_polygon(point, polygon) is expected


# --- polygon intersection ---

@pytest.mark.parametrize(
    "a,b,expected",
    [
        pytest.param(rect(0, 0, 4, 4), rect(2, 2, 6, 6), True, id="partial-overlap"),
        pytest.param(rect(0, 0, 4, 4), rect(5, 5, 6, 6), False, id="disjoint"),
        pytest.param(rect(0, 0, 10, 10), rect(4, 4, 5, 5), True, id="second-inside-first"),
        pytest.param(rect(4, 4, 5, 5), rect(0, 0, 10, 10), True, id="first-inside-second"),
        pytest.param(rect(0, 0, 4, 4), rect(4, 0, 8, 4), True, id="sharing-an-edge"),
        pytest.param(rect(0, 0, 4, 4), rect(4, 4, 8, 8), True, id="touching-at-a-corner"),
        pytest.param(rect(0, 0, 4, 4), rect(4.001, 0, 8, 4), False, id="just-apart"),
        pytest.param(rect(0, 0, 10, 10), rect(-5, 4, 15, 5), True, id="crossing-with-no-vertex-inside"),
        pytest.param(L_SHAPE, rect(3, 3, 3.5, 3.5), False, id="bbox-overlaps-but-shapes-do-not"),
        pytest.param(L_SHAPE, rect(1, 1, 3, 3), True, id="into-the-notch-edge"),
        pytest.param(WITH_HOLE, rect(4.5, 4.5, 5.5, 5.5), False, id="entirely-inside-a-hole"),
        pytest.param(WITH_HOLE, rect(3, 3, 5, 5), True, id="straddling-a-hole-edge"),
        pytest.param(WITH_HOLE, rect(-5, -5, 15, 15), True, id="enclosing-a-polygon-with-a-hole"),
    ],
)
def test_polygons_intersect(a, b, expected):
    assert geometry.polygons_intersect(a, b) is expected
    assert geometry.polygons_intersect(b, a) is expected


def test_intersection_matches_the_analytic_answer_for_random_rectangles():
    """Rectangles overlap exactly when their intervals overlap on both axes.

    Touching counts, matching the module's rule that a boundary is inside.
    """
    rng = random.Random(20260919)
    grid = [i / 2 for i in range(0, 21)]  # coarse grid so edges often coincide

    def random_rect():
        x1, x2 = sorted(rng.sample(grid, 2))
        y1, y2 = sorted(rng.sample(grid, 2))
        return (x1, y1, x2, y2)

    for _ in range(2000):
        a, b = random_rect(), random_rect()
        expected = a[0] <= b[2] and b[0] <= a[2] and a[1] <= b[3] and b[1] <= a[3]
        assert geometry.polygons_intersect(rect(*a), rect(*b)) is expected, (a, b)


# --- region model ---

def test_bbox_builds_a_valid_region():
    region = Region.from_bbox(142.0, -38.0, 143.0, -37.0)

    assert region.geometry.coordinates[0][0] == region.geometry.coordinates[0][-1]


@pytest.mark.parametrize(
    "bbox",
    [
        pytest.param((143.0, -38.0, 142.0, -37.0), id="min-longitude-above-max"),
        pytest.param((142.0, -37.0, 143.0, -38.0), id="min-latitude-above-max"),
        pytest.param((142.0, -38.0, 142.0, -37.0), id="zero-width"),
    ],
)
def test_bbox_rejects_an_inverted_or_empty_box(bbox):
    with pytest.raises(ValueError):
        Region.from_bbox(*bbox)


def test_region_rejects_an_unclosed_ring_and_out_of_range_coordinates():
    unclosed = {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1]]]}
    out_of_range = {"type": "Polygon", "coordinates": rect(170, 0, 190, 10)}

    with pytest.raises(ValidationError):
        Region(geometry=unclosed)
    with pytest.raises(ValidationError):
        Region(geometry=out_of_range)


@pytest.mark.parametrize("threshold", [0, 6, -1])
def test_rule_rejects_a_threshold_outside_the_risk_scale(threshold):
    with pytest.raises(ValidationError):
        AlertRule(region=Region.from_bbox(0, 0, 1, 1), threshold_risk_factor=threshold)


def test_assessment_requires_risk_factor_exactly_when_features_exist():
    with pytest.raises(ValidationError):
        RegionAssessment(risk_factor=2, feature_count=0)
    with pytest.raises(ValidationError):
        RegionAssessment(risk_factor=None, feature_count=3)


# --- assessing a region against a forecast ---

REGION = Region.from_bbox(0, 0, 10, 10)


def test_region_risk_is_the_most_severe_touching_polygon():
    forecast = features_of(
        feature(1, 1, 2, 2, risk=4),
        feature(3, 3, 4, 4, risk=1),
        feature(5, 5, 6, 6, risk=3),
    )

    result = assess_region(forecast, REGION)

    assert result.risk_factor == 1
    assert result.feature_count == 3


def test_polygons_outside_the_region_are_ignored():
    forecast = features_of(
        feature(1, 1, 2, 2, risk=4),
        feature(20, 20, 30, 30, risk=1),
    )

    result = assess_region(forecast, REGION)

    assert result.risk_factor == 4
    assert result.feature_count == 1


def test_no_touching_polygon_means_no_known_risk():
    result = assess_region(features_of(feature(20, 20, 30, 30, risk=1)), REGION)

    assert result == RegionAssessment(risk_factor=None, feature_count=0)


def test_an_empty_forecast_means_no_known_risk():
    assert assess_region([], REGION).risk_factor is None


def test_polygon_only_touching_the_region_edge_counts():
    result = assess_region(features_of(feature(10, 0, 12, 5, risk=2)), REGION)

    assert result.risk_factor == 2


def test_highest_fire_probability_is_reported_when_supplied():
    forecast = features_of(
        feature(1, 1, 2, 2, risk=3, probability=0.4),
        feature(3, 3, 4, 4, risk=2, probability=0.9),
        feature(5, 5, 6, 6, risk=4),
    )

    assert assess_region(forecast, REGION).max_fire_probability == 0.9


def test_fire_probability_is_absent_when_no_polygon_supplies_it():
    result = assess_region(features_of(feature(1, 1, 2, 2, risk=3)), REGION)

    assert result.max_fire_probability is None


# --- the escalation decision ---

def assessment(risk):
    return RegionAssessment(
        risk_factor=risk, feature_count=0 if risk is None else 1
    )


def rule(threshold):
    return AlertRule(region=REGION, threshold_risk_factor=threshold)


@pytest.mark.parametrize(
    "previous,current,threshold,expected",
    [
        # Getting worse across the threshold.
        pytest.param(4, 2, 2, AlertKind.THRESHOLD_CROSSED, id="crosses-up-to-the-threshold"),
        pytest.param(5, 1, 3, AlertKind.THRESHOLD_CROSSED, id="jumps-past-the-threshold"),
        pytest.param(None, 2, 2, AlertKind.THRESHOLD_CROSSED, id="was-clear-now-at-threshold"),
        # Already at or beyond the threshold, and worse.
        pytest.param(2, 1, 2, AlertKind.ESCALATED, id="worsens-beyond-the-threshold"),
        pytest.param(3, 2, 3, AlertKind.ESCALATED, id="threshold-is-inclusive-then-worsens"),
        # Nothing to say.
        pytest.param(2, 2, 2, None, id="unchanged-at-the-threshold"),
        pytest.param(1, 1, 3, None, id="unchanged-well-beyond-the-threshold"),
        pytest.param(1, 2, 2, None, id="easing-is-not-alerted"),
        pytest.param(2, None, 2, None, id="risk-clears"),
        pytest.param(None, None, 2, None, id="still-clear"),
        pytest.param(4, 3, 2, None, id="worse-but-still-below-the-threshold"),
        pytest.param(5, 4, 2, None, id="mild-and-below-threshold"),
    ],
)
def test_decision_table(previous, current, threshold, expected):
    decision = evaluate(assessment(previous), assessment(current), rule(threshold))

    assert (decision.kind if decision else None) == expected


def test_a_first_forecast_at_the_threshold_alerts():
    decision = evaluate(None, assessment(2), rule(2))

    assert decision is not None
    assert decision.kind is AlertKind.THRESHOLD_CROSSED
    assert decision.previous_risk_factor is None


def test_a_first_forecast_below_the_threshold_does_not_alert():
    assert evaluate(None, assessment(4), rule(2)) is None


def test_decision_carries_the_before_and_after_and_context():
    current = RegionAssessment(
        risk_factor=1, feature_count=3, max_fire_probability=0.8
    )

    decision = evaluate(assessment(2), current, rule(2))

    assert decision.previous_risk_factor == 2
    assert decision.current_risk_factor == 1
    assert decision.feature_count == 3
    assert decision.max_fire_probability == 0.8


def test_flapping_around_the_threshold_alerts_each_time_it_is_crossed():
    """Documents current behaviour: the detector is stateless.

    Suppressing this noise (a cooldown per subscription) needs stored state, so
    it belongs to the delivery layer, not to this pure decision.
    """
    sequence = [4, 2, 4, 2, 2, 4, 2]
    previous = None
    alerts = []
    for risk in sequence:
        current = assessment(risk)
        decision = evaluate(previous, current, rule(2))
        alerts.append(decision.kind.value if decision else None)
        previous = current

    assert alerts == [
        None,
        "threshold_crossed",
        None,
        "threshold_crossed",
        None,
        None,
        "threshold_crossed",
    ]


# --- forecast in, decision out ---

def test_two_successive_forecasts_produce_an_alert_for_a_subscribed_region():
    subscription = AlertRule(
        region=Region.from_bbox(142.0, -38.0, 143.0, -37.0),
        threshold_risk_factor=2,
    )

    def forecast(risk):
        return FeatureCollection.model_validate({
            "type": "FeatureCollection",
            "features": [
                feature(142.4, -37.6, 142.6, -37.4, risk=risk, probability=0.7),
                # A severe polygon nowhere near the region must not matter.
                feature(146.0, -36.0, 146.5, -35.5, risk=1),
            ],
        }).features

    before = assess_region(forecast(4), subscription.region)
    after = assess_region(forecast(1), subscription.region)

    decision = evaluate(before, after, subscription)

    assert decision.kind is AlertKind.THRESHOLD_CROSSED
    assert decision.previous_risk_factor == 4
    assert decision.current_risk_factor == 1
    assert decision.feature_count == 1
