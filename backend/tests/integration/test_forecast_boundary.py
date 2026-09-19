"""
Freshness-threshold integration tests for Arsh PR #250.

The final stale window is configurable through FORECAST_STALE_AFTER_SECONDS.
The exact production value still depends on the agreed AI prediction cadence,
so these tests read the configured value instead of hard-coding 900 seconds.
"""

import os
from datetime import datetime, timedelta, timezone

from conftest import seed_prediction


def _stale_after_seconds() -> int:
    """Return the stale threshold expected by the running Backend."""
    return int(os.getenv("FORECAST_STALE_AFTER_SECONDS", "900"))


def test_just_inside_freshness_window_is_live(
    preserve_forecast_cache,
    valid_forecast,
    firefusion_url,
    http,
):
    """
    A prediction comfortably inside the freshness window should be live.

    Five seconds of margin is used to avoid a flaky exact-boundary comparison
    while the request is travelling through the running stack.
    """
    threshold = _stale_after_seconds()
    generated_at = datetime.now(timezone.utc) - timedelta(
        seconds=max(threshold - 5, 0)
    )
    seed_prediction(
        preserve_forecast_cache,
        valid_forecast,
        generated_at.isoformat(),
    )

    response = http.get(f"{firefusion_url}/api/bushfire-forecast")

    assert response.status_code == 200
    assert response.json()["meta"]["status"] == "live"


def test_clearly_outside_freshness_window_is_stale(
    preserve_forecast_cache,
    valid_forecast,
    firefusion_url,
    http,
):
    """A prediction clearly older than the configured threshold should be stale."""
    threshold = _stale_after_seconds()
    generated_at = datetime.now(timezone.utc) - timedelta(
        seconds=threshold + 30
    )
    seed_prediction(
        preserve_forecast_cache,
        valid_forecast,
        generated_at.isoformat(),
    )

    response = http.get(f"{firefusion_url}/api/bushfire-forecast")

    assert response.status_code == 200
    assert response.json()["meta"]["status"] == "stale"


def test_meta_exposes_age_and_threshold_when_available(
    preserve_forecast_cache,
    valid_forecast,
    firefusion_url,
    http,
):
    """
    The metadata should explain why Frontend can trust or warn about a forecast.

    These fields allow UI and operational tooling to distinguish the status
    without independently calculating age from an undocumented timestamp.
    """
    seed_prediction(
        preserve_forecast_cache,
        valid_forecast,
        datetime.now(timezone.utc).isoformat(),
    )

    response = http.get(f"{firefusion_url}/api/bushfire-forecast")

    assert response.status_code == 200
    meta = response.json()["meta"]

    assert "status" in meta
    assert "generated_at" in meta
    assert "age_seconds" in meta
    assert "stale_after_seconds" in meta
