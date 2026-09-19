"""Security tests for the backend services.

Covers the findings from the backend audit:
  F1 - authentication was applied to one route out of sixteen
  F2 - CORS was open to all origins

These hit the running stack and skip cleanly when it is not up.
"""
import os

import pytest

pytestmark = pytest.mark.integration

API_KEY = os.getenv("API_KEY", "local-development-key")
BAD_KEY = "not-the-right-key"


# --- aggregator-api: internal data routes ---

@pytest.mark.parametrize("path", ["/internal/data/fire-incidents", "/internal/data/fire-risk-inputs"])
def test_internal_data_rejects_missing_key(agg, http, path):
    """Internal DE data must not be readable without the API key."""
    r = http.get(f"{agg}{path}")
    assert r.status_code == 401, f"{path} returned {r.status_code}; internal data is exposed"


@pytest.mark.parametrize("path", ["/internal/data/fire-incidents", "/internal/data/fire-risk-inputs"])
def test_internal_data_rejects_wrong_key(agg, http, path):
    r = http.get(f"{agg}{path}", headers={"X-API-Key": BAD_KEY})
    assert r.status_code == 401, f"{path} accepted an invalid key"

@pytest.mark.xfail(
    reason="Fire_Incident_Record expects NASA FIRMS fields (record_type, satellite, "
           "brightness_ti4, frp) that were never migrated. Open cross-stream decision "
           "with Data Engineering and AI Modelling.",
    strict=False,
)

def test_internal_data_accepts_valid_key(agg, http):
    """A valid key must still get through, so the guard has not broken the service."""
    r = http.get(f"{agg}/internal/data/fire-incidents", headers={"X-API-Key": API_KEY})
    assert r.status_code == 200, f"valid key rejected with {r.status_code}"

# --- model-api ---

def test_model_geojson_rejects_missing_key(model, http):
    """Model output is served to other services and must be protected."""
    r = http.get(f"{model}/model/geojson")
    assert r.status_code == 401, f"model output is exposed (got {r.status_code})"


def test_model_geojson_accepts_valid_key(model, http):
    r = http.get(f"{model}/model/geojson", headers={"X-API-Key": API_KEY})
    assert r.status_code == 200


def test_model_health_stays_public(model, http):
    """Liveness checks must remain unauthenticated for probes and CI."""
    assert http.get(f"{model}/model/hello").status_code == 200


# --- firefusion-api: CORS ---

def test_cors_rejects_unknown_origin(ff, http):
    """An arbitrary origin must not be echoed back as permitted."""
    r = http.get(f"{ff}/api/bushfire-forecast", headers={"Origin": "https://not-our-dashboard.example"})
    allowed = r.headers.get("access-control-allow-origin")
    assert allowed != "*", "CORS is still open to all origins"
    assert allowed != "https://not-our-dashboard.example", "an unknown origin was permitted"


def test_cors_allows_the_configured_dashboard_origin(ff, http):
    """The dashboard must still be able to call the API."""
    origin = "http://localhost:3000"
    r = http.get(f"{ff}/api/bushfire-forecast", headers={"Origin": origin})
    assert r.headers.get("access-control-allow-origin") == origin, "the dashboard origin is not permitted"


def test_frontend_endpoint_remains_reachable(ff, http):
    """The Fire Risk Map endpoint stays public; only internal routes are keyed."""
    assert http.get(f"{ff}/api/bushfire-forecast").status_code == 200
