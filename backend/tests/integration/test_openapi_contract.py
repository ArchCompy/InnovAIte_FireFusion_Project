"""
OpenAPI regression tests for the final merged Backend contract.

These tests are intentionally broad. They catch merge mistakes where a shared
Pydantic model or router is replaced wholesale and newer fields silently
disappear.
"""


def test_forecast_openapi_includes_final_merged_fields(firefusion_url, http):
    """
    Final forecast schema should expose fields contributed by both reliability
    and graceful-degradation work.
    """
    response = http.get(f"{firefusion_url}/openapi.json")

    assert response.status_code == 200
    schema = response.json()

    # Serialising is a lightweight way to check nested component schemas without
    # coupling this integration test to FastAPI's exact generated component name.
    serialized = str(schema)

    assert "FeatureCollection" in serialized
    assert "risk_factor" in serialized
    assert "fire_probability" in serialized
    assert "meta" in serialized