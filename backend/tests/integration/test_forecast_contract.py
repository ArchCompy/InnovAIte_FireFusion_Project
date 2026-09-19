"""
Merged Fire Risk Map contract tests.

This file deliberately tests behaviour that spans multiple recent PRs:

Zehong PR #238
- malformed/schema-invalid cached forecasts remain explicit failures (503);
- risk_factor remains required;
- fire_probability remains optional and valid when present.

Arsh PR #250
- fresh forecasts are live;
- old forecasts remain visible as stale;
- unknown age fails cautiously toward stale;
- no forecast is unavailable rather than a server error.

The goal is to prevent one PR's forecast_service.py / geojson.py changes from
silently overwriting the other's behaviour during merge reconciliation.
"""

import json
from datetime import datetime, timedelta, timezone

from conftest import seed_prediction


def _forecast(http, firefusion_url):
    """Request the public Fire Risk Map endpoint."""
    return http.get(f"{firefusion_url}/api/bushfire-forecast")


def test_no_prediction_is_unavailable_not_an_error(
    preserve_forecast_cache,
    firefusion_url,
    http,
):
    """
    No prediction is a valid no-data state.

    Expected final behaviour:
    200 + empty FeatureCollection + meta.status=unavailable.
    """
    redis_client = preserve_forecast_cache
    redis_client.delete("predictions", "predictions:generated_at")

    response = _forecast(http, firefusion_url)

    assert response.status_code == 200

    body = response.json()
    assert body["type"] == "FeatureCollection"
    assert body["features"] == []
    assert body["meta"]["status"] == "unavailable"


def test_fresh_prediction_is_live_and_preserves_final_contract(
    preserve_forecast_cache,
    valid_forecast,
    firefusion_url,
    http,
):
    """
    A current valid prediction should be live and preserve both newer fields:
    fire_probability from PR #238 and meta from PR #250.
    """
    generated_at = datetime.now(timezone.utc).isoformat()
    seed_prediction(preserve_forecast_cache, valid_forecast, generated_at)

    response = _forecast(http, firefusion_url)

    assert response.status_code == 200

    body = response.json()
    assert body["meta"]["status"] == "live"
    assert body["features"]

    properties = body["features"][0]["properties"]
    assert properties["risk_factor"] == 3
    assert properties["fire_probability"] == 0.72


def test_stale_prediction_is_still_served(
    preserve_forecast_cache,
    valid_forecast,
    firefusion_url,
    http,
):
    """
    A valid old prediction must remain visible.

    This is the core graceful-degradation behaviour: stale data is served with
    an explicit warning status instead of making the map disappear.
    """
    old_time = datetime.now(timezone.utc) - timedelta(hours=2)
    seed_prediction(preserve_forecast_cache, valid_forecast, old_time.isoformat())

    response = _forecast(http, firefusion_url)

    assert response.status_code == 200

    body = response.json()
    assert body["meta"]["status"] == "stale"
    assert body["features"]


def test_prediction_with_missing_timestamp_fails_toward_caution(
    preserve_forecast_cache,
    valid_forecast,
    firefusion_url,
    http,
):
    """
    Valid data with unknown age should be treated as stale, not live.

    This intentionally fails toward caution for an emergency-use application.
    """
    seed_prediction(preserve_forecast_cache, valid_forecast, generated_at=None)

    response = _forecast(http, firefusion_url)

    assert response.status_code == 200

    body = response.json()
    assert body["meta"]["status"] == "stale"
    assert body["features"]


def test_prediction_with_invalid_timestamp_fails_toward_caution(
    preserve_forecast_cache,
    valid_forecast,
    firefusion_url,
    http,
):
    """An unreadable timestamp should not cause the Backend to overstate freshness."""
    seed_prediction(
        preserve_forecast_cache,
        valid_forecast,
        generated_at="not-a-timestamp",
    )

    response = _forecast(http, firefusion_url)

    assert response.status_code == 200

    body = response.json()
    assert body["meta"]["status"] == "stale"
    assert body["features"]


def test_corrupted_cached_json_remains_503_after_freshness_merge(
    preserve_forecast_cache,
    firefusion_url,
    http,
):
    """
    Corrupted cache state must stay distinguishable from "no forecast".

    This protects PR #238's explicit cache-corruption semantics when the
    graceful-degradation work from PR #250 is merged.
    """
    redis_client = preserve_forecast_cache
    redis_client.set("predictions", b"{ definitely not valid json")
    redis_client.set(
        "predictions:generated_at",
        datetime.now(timezone.utc).isoformat(),
    )

    response = _forecast(http, firefusion_url)

    assert response.status_code == 503


def test_schema_invalid_cached_prediction_remains_503_after_freshness_merge(
    preserve_forecast_cache,
    firefusion_url,
    http,
):
    """
    Syntactically valid JSON with the wrong GeoJSON schema is still corruption.

    It must not be converted into meta.status=unavailable.
    """
    redis_client = preserve_forecast_cache
    redis_client.set(
        "predictions",
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": "wrong",
            }
        ),
    )
    redis_client.set(
        "predictions:generated_at",
        datetime.now(timezone.utc).isoformat(),
    )

    response = _forecast(http, firefusion_url)

    assert response.status_code == 503
