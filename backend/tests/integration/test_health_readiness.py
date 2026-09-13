"""
Integration tests for the Backend health/readiness contract.

Primary recent work covered:
- Ashan's /health and /ready lifecycle commit.
- Compatibility with the security work, where operational endpoints should
  remain public while protected business/internal routes still require auth.

These tests assume the final merged stack is already running.
"""

import pytest


@pytest.mark.parametrize(
    ("service_fixture", "path"),
    [
        ("firefusion_url", "/health"),
        ("model_url", "/health"),
        ("aggregator_url", "/health"),
    ],
)
def test_all_services_are_live(request, http, service_fixture, path):
    """Every Backend service should expose a successful lightweight liveness endpoint."""
    base_url = request.getfixturevalue(service_fixture)

    response = http.get(f"{base_url}{path}")

    assert response.status_code == 200


@pytest.mark.parametrize(
    "service_fixture",
    ["firefusion_url", "model_url", "aggregator_url"],
)
def test_all_services_report_ready_when_stack_is_healthy(
    request,
    http,
    service_fixture,
):
    """
    A fully started local stack should report all three APIs as ready.

    This is a post-startup integration check. Separate unit/lifecycle tests can
    cover the brief 503 state while an individual service is still starting.
    """
    base_url = request.getfixturevalue(service_fixture)

    response = http.get(f"{base_url}/ready")

    assert response.status_code == 200


def test_firefusion_health_and_ready_are_public(firefusion_url, http):
    """
    Operational probes must remain reachable without an API key.

    This protects against a merge accidentally applying API-key authentication
    to /health or /ready while security changes are reconciled.
    """
    assert http.get(f"{firefusion_url}/health").status_code == 200
    assert http.get(f"{firefusion_url}/ready").status_code == 200
