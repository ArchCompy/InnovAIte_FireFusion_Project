"""Running-stack contract tests for the Fire Risk Map endpoint.

These tests exercise the real firefusion-api over HTTP and use the running
Redis service to establish explicit cache states. Each cache mutation is
restored by the shared prediction_cache fixture.
"""

import json

import pytest


pytestmark = pytest.mark.integration

RISK_MIN = 1
RISK_MAX = 5

ENDPOINT = "/api/bushfire-forecast"
CACHE_KEY = "predictions"

EMPTY_FEATURE_COLLECTION = {
    "type": "FeatureCollection",
    "features": [],
}

VALID_PAYLOAD = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [142.1560, -37.5600],
                    [142.3200, -37.7400],
                    [142.5100, -37.6500],
                    [142.3800, -37.5100],
                    [142.1560, -37.5600],
                ]],
            },
            "properties": {
                "risk_factor": 2,
                "fire_probability": 0.78,
            },
        }
    ],
}

SCHEMA_INVALID_PAYLOAD = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [142.1560, -37.5600],
                    [142.3200, -37.7400],
                    [142.5100, -37.6500],
                    [142.1560, -37.5600],
                ]],
            },
            "properties": {
                "risk_factor": 0,
            },
        }
    ],
}


def validate_feature(feature, index=0):
    """Assert one feature satisfies the external GeoJSON contract."""

    assert feature.get("type") == "Feature", (
        f"feature {index} has wrong type"
    )

    geometry = feature.get("geometry")
    assert isinstance(geometry, dict), (
        f"feature {index} geometry must be an object"
    )
    assert geometry.get("type") == "Polygon", (
        f"feature {index} geometry is not a Polygon"
    )

    rings = geometry.get("coordinates")
    assert isinstance(rings, list) and rings, (
        f"feature {index} has no polygon rings"
    )

    for ring_index, ring in enumerate(rings):
        assert isinstance(ring, list), (
            f"feature {index} ring {ring_index} is not a list"
        )
        assert len(ring) >= 4, (
            f"feature {index} ring {ring_index} "
            "needs at least four positions"
        )
        assert ring[0] == ring[-1], (
            f"feature {index} ring {ring_index} is not closed"
        )

        for position_index, position in enumerate(ring):
            assert isinstance(position, list), (
                f"feature {index} ring {ring_index} "
                f"position {position_index} is not a list"
            )
            assert len(position) == 2, (
                f"feature {index} ring {ring_index} "
                f"position {position_index} is not [longitude, latitude]"
            )

            longitude, latitude = position

            assert type(longitude) in (int, float), (
                f"feature {index} longitude is not numeric"
            )
            assert type(latitude) in (int, float), (
                f"feature {index} latitude is not numeric"
            )
            assert -180 <= longitude <= 180, (
                f"feature {index} longitude {longitude} out of range"
            )
            assert -90 <= latitude <= 90, (
                f"feature {index} latitude {latitude} out of range"
            )

    properties = feature.get("properties")
    assert isinstance(properties, dict), (
        f"feature {index} properties must be an object"
    )

    risk_factor = properties.get("risk_factor")
    assert type(risk_factor) is int, (
        f"feature {index} risk_factor is not a strict integer"
    )
    assert RISK_MIN <= risk_factor <= RISK_MAX, (
        f"feature {index} risk_factor {risk_factor} "
        f"outside {RISK_MIN}-{RISK_MAX}"
    )

    if "fire_probability" in properties:
        probability = properties["fire_probability"]
        assert type(probability) in (int, float), (
            f"feature {index} fire_probability is not numeric"
        )
        assert 0.0 <= probability <= 1.0, (
            f"feature {index} fire_probability "
            f"{probability} outside 0-1"
        )


def test_missing_cache_returns_empty_feature_collection(
    ff,
    http,
    prediction_cache,
):
    """A missing prediction is normal no-data, not a service failure."""

    prediction_cache.delete(CACHE_KEY)

    response = http.get(f"{ff}{ENDPOINT}")

    assert response.status_code == 200
    assert response.json() == EMPTY_FEATURE_COLLECTION


def test_valid_cached_prediction_is_served_over_http(
    ff,
    http,
    prediction_cache,
):
    """A real Redis value is validated and returned through HTTP."""

    prediction_cache.set(
        CACHE_KEY,
        json.dumps(VALID_PAYLOAD),
    )

    response = http.get(f"{ff}{ENDPOINT}")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith(
        "application/json"
    )

    body = response.json()
    assert body == VALID_PAYLOAD

    for index, feature in enumerate(body["features"]):
        validate_feature(feature, index)


@pytest.mark.parametrize(
    "cached_value",
    [
        pytest.param(
            "not-json-at-all",
            id="malformed-json",
        ),
        pytest.param(
            "[]",
            id="non-object-json",
        ),
        pytest.param(
            json.dumps(SCHEMA_INVALID_PAYLOAD),
            id="schema-invalid-geojson",
        ),
    ],
)
def test_corrupt_cached_prediction_returns_503(
    ff,
    http,
    prediction_cache,
    cached_value,
):
    """Present but unusable cached data is explicit unavailability."""

    prediction_cache.set(
        CACHE_KEY,
        cached_value,
    )

    response = http.get(f"{ff}{ENDPOINT}")

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Forecast data temporarily unavailable"
    }


def test_feature_structure_runs_against_model_sample(
    model,
    http,
):
    """The running model-api sample supplies non-empty GeoJSON."""

    response = http.get(f"{model}/model/geojson")

    assert response.status_code == 200

    body = response.json()
    collection = body[0] if isinstance(body, list) else body

    assert collection.get("type") == "FeatureCollection"

    features = collection.get("features")
    assert isinstance(features, list) and features

    for index, feature in enumerate(features):
        assert feature.get("type") == "Feature"
        geometry = feature.get("geometry", {})
        assert geometry.get("type") == "Polygon"

        for ring_index, ring in enumerate(
            geometry.get("coordinates", [])
        ):
            assert ring
            assert ring[0] == ring[-1], (
                f"sample feature {index} "
                f"ring {ring_index} is not closed"
            )


def test_endpoint_is_documented_in_openapi(ff, http):
    """The running API publishes the formal forecast response schema."""

    response = http.get(f"{ff}/openapi.json")

    assert response.status_code == 200

    spec = response.json()
    operation = spec["paths"][ENDPOINT]["get"]
    success_schema = operation["responses"]["200"][
        "content"
    ]["application/json"]["schema"]

    assert success_schema == {
        "$ref": "#/components/schemas/FeatureCollection"
    }

    properties_schema = spec["components"]["schemas"][
        "Properties"
    ]

    assert "risk_factor" in properties_schema["required"]
    assert (
        "fire_probability"
        not in properties_schema["required"]
    )
    assert (
        "fire_probability"
        in properties_schema["properties"]
    )


def test_openapi_documents_503_response(ff, http):
    """The running API advertises its temporary failure response."""

    spec = http.get(f"{ff}/openapi.json").json()
    responses = spec["paths"][ENDPOINT]["get"]["responses"]

    assert "503" in responses
    assert (
        responses["503"]["description"]
        == "Forecast data temporarily unavailable"
    )
