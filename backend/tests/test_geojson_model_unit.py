"""Contract tests for the production Fire Risk Map GeoJSON models.

These tests import and validate the real Pydantic models used by
ForecastService. They enforce the confirmed Fire Risk Map contract, including
optional fire_probability validation when that field is supplied.
"""

from copy import deepcopy
from pathlib import Path
import sys

import pytest
from pydantic import ValidationError


APP_DIR = Path(__file__).resolve().parents[1] / "firefusion-api"

if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from app.internal.models.geojson import FeatureCollection


VALID_FEATURE_COLLECTION = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [142.1560, -37.5600],
                        [142.3200, -37.7400],
                        [142.5100, -37.6500],
                        [142.3800, -37.5100],
                        [142.1560, -37.5600],
                    ]
                ],
            },
            "properties": {
                "risk_factor": 1,
            },
        }
    ],
}


@pytest.fixture
def valid_payload():
    return deepcopy(VALID_FEATURE_COLLECTION)


def assert_invalid(payload):
    with pytest.raises(ValidationError):
        FeatureCollection.model_validate(payload)


def test_accepts_valid_feature_collection(valid_payload):
    result = FeatureCollection.model_validate(valid_payload)

    assert result.model_dump(exclude_none=True) == valid_payload


def test_preserves_optional_fire_probability(valid_payload):
    valid_payload["features"][0]["properties"]["fire_probability"] = 0.78

    result = FeatureCollection.model_validate(valid_payload)

    assert (
        result.features[0].properties.fire_probability
        == 0.78
    )


@pytest.mark.parametrize("fire_probability", [0, 1])
def test_accepts_fire_probability_boundaries(
    valid_payload,
    fire_probability,
):
    valid_payload["features"][0]["properties"][
        "fire_probability"
    ] = fire_probability

    result = FeatureCollection.model_validate(valid_payload)

    assert (
        result.features[0].properties.fire_probability
        == fire_probability
    )


@pytest.mark.parametrize("fire_probability", [-0.01, 1.01])
def test_rejects_fire_probability_outside_zero_to_one(
    valid_payload,
    fire_probability,
):
    valid_payload["features"][0]["properties"][
        "fire_probability"
    ] = fire_probability

    assert_invalid(valid_payload)


@pytest.mark.parametrize(
    "fire_probability",
    [True, "0.78"],
    ids=["boolean", "numeric-string"],
)
def test_rejects_non_numeric_fire_probability(
    valid_payload,
    fire_probability,
):
    valid_payload["features"][0]["properties"][
        "fire_probability"
    ] = fire_probability

    assert_invalid(valid_payload)


def test_accepts_empty_feature_collection():
    payload = {
        "type": "FeatureCollection",
        "features": [],
    }

    result = FeatureCollection.model_validate(payload)

    assert result.model_dump() == payload


def test_rejects_wrong_feature_collection_type(valid_payload):
    valid_payload["type"] = "Feature"

    assert_invalid(valid_payload)


def test_rejects_wrong_feature_type(valid_payload):
    valid_payload["features"][0]["type"] = "Polygon"

    assert_invalid(valid_payload)


def test_rejects_non_polygon_geometry(valid_payload):
    valid_payload["features"][0]["geometry"]["type"] = "Point"

    assert_invalid(valid_payload)


@pytest.mark.parametrize("risk_factor", [0, 6])
def test_rejects_risk_factor_outside_one_to_five(
    valid_payload,
    risk_factor,
):
    valid_payload["features"][0]["properties"]["risk_factor"] = risk_factor

    assert_invalid(valid_payload)


@pytest.mark.parametrize("risk_factor", [True, "3"])
def test_rejects_non_integer_risk_factor(
    valid_payload,
    risk_factor,
):
    valid_payload["features"][0]["properties"]["risk_factor"] = risk_factor

    assert_invalid(valid_payload)


@pytest.mark.parametrize("longitude", [-180.1, 180.1])
def test_rejects_longitude_outside_valid_range(
    valid_payload,
    longitude,
):
    ring = valid_payload["features"][0]["geometry"]["coordinates"][0]
    ring[1][0] = longitude

    assert_invalid(valid_payload)


@pytest.mark.parametrize("latitude", [-90.1, 90.1])
def test_rejects_latitude_outside_valid_range(
    valid_payload,
    latitude,
):
    ring = valid_payload["features"][0]["geometry"]["coordinates"][0]
    ring[1][1] = latitude

    assert_invalid(valid_payload)


def test_rejects_open_polygon_ring(valid_payload):
    ring = valid_payload["features"][0]["geometry"]["coordinates"][0]
    ring[-1] = [142.0000, -37.0000]

    assert_invalid(valid_payload)


def test_rejects_polygon_ring_with_fewer_than_four_positions(valid_payload):
    valid_payload["features"][0]["geometry"]["coordinates"] = [
        [
            [142.1560, -37.5600],
            [142.3200, -37.7400],
            [142.1560, -37.5600],
        ]
    ]

    assert_invalid(valid_payload)


def test_rejects_polygon_without_rings(valid_payload):
    valid_payload["features"][0]["geometry"]["coordinates"] = []

    assert_invalid(valid_payload)


@pytest.mark.parametrize(
    "position",
    [
        [142.3200],
        [142.3200, -37.7400, 100.0],
    ],
)
def test_rejects_position_that_is_not_longitude_latitude_pair(
    valid_payload,
    position,
):
    ring = valid_payload["features"][0]["geometry"]["coordinates"][0]
    ring[1] = position

    assert_invalid(valid_payload)


def test_rejects_missing_feature_collection_type(valid_payload):
    del valid_payload["type"]

    assert_invalid(valid_payload)


def test_rejects_missing_feature_type(valid_payload):
    del valid_payload["features"][0]["type"]

    assert_invalid(valid_payload)


@pytest.mark.parametrize(
    "longitude",
    [
        "142.3200",
        True,
    ],
    ids=["numeric-string", "boolean"],
)
def test_rejects_coordinate_that_is_not_a_json_number(
    valid_payload,
    longitude,
):
    ring = valid_payload["features"][0]["geometry"]["coordinates"][0]
    ring[1][0] = longitude

    assert_invalid(valid_payload)
