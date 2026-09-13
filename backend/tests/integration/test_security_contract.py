"""
Integration tests for the API-key security contract introduced by Arsh's
backend-security-hardening work.

The important merge-level behaviour is:
- internal Aggregator routes reject missing/invalid credentials;
- a valid key crosses the authentication boundary;
- known downstream data/schema issues must not be mistaken for auth failures;
- Model API liveness remains public.
"""

import pytest


@pytest.mark.parametrize(
    "path",
    [
        "/internal/data/fire-incidents",
        "/internal/data/fire-risk-inputs",
    ],
)
def test_aggregator_internal_routes_reject_missing_api_key(
    aggregator_url,
    http,
    path,
):
    """Internal Aggregator data routes must not be anonymously accessible."""
    response = http.get(f"{aggregator_url}{path}")

    assert response.status_code in {401, 403}


@pytest.mark.parametrize(
    "path",
    [
        "/internal/data/fire-incidents",
        "/internal/data/fire-risk-inputs",
    ],
)
def test_aggregator_internal_routes_reject_invalid_api_key(
    aggregator_url,
    http,
    path,
):
    """An explicitly incorrect service key must still be rejected."""
    response = http.get(
        f"{aggregator_url}{path}",
        headers={"X-API-Key": "definitely-not-the-real-key"},
    )

    assert response.status_code in {401, 403}


@pytest.mark.parametrize(
    "path",
    [
        "/internal/data/fire-incidents",
        "/internal/data/fire-risk-inputs",
    ],
)
def test_valid_api_key_passes_authentication_boundary(
    aggregator_url,
    http,
    api_key,
    path,
):
    """
    Confirm that a valid key passes authentication.

    A route can still return a downstream 5xx after authentication, for example
    while the known Fire_Incident_Record schema alignment issue is unresolved.
    The purpose of this assertion is therefore to prove the request was not
    rejected as unauthorised.
    """
    response = http.get(
        f"{aggregator_url}{path}",
        headers={"X-API-Key": api_key},
    )

    assert response.status_code not in {401, 403}


def test_model_geojson_route_rejects_missing_api_key(model_url, http):
    """The protected Model API route should require the service API key."""
    response = http.get(f"{model_url}/model/geojson")

    assert response.status_code in {401, 403}


def test_model_liveness_route_stays_public(model_url, http):
    """The Model API liveness route should remain usable by probes without credentials."""
    response = http.get(f"{model_url}/model/hello")

    assert response.status_code == 200
