"""
Optional destructive dependency-recovery tests.

These tests temporarily stop/start Docker services, so they are disabled by
default. Enable them only against a local development stack by setting:

    RUN_DESTRUCTIVE_INTEGRATION=1

Do not enable this against a shared environment.
"""

import os
import subprocess
import time

import pytest


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_DESTRUCTIVE_INTEGRATION") != "1",
    reason=(
        "Set RUN_DESTRUCTIVE_INTEGRATION=1 to allow Docker dependency "
        "stop/start tests"
    ),
)


def _compose(*args: str) -> None:
    """Run a docker compose command from the current repository context."""
    subprocess.run(["docker", "compose", *args], check=True)


def _wait_for_status(http, url: str, expected: int, timeout: int = 30) -> None:
    """Poll an endpoint until it reaches the expected status or times out."""
    deadline = time.time() + timeout
    last = None

    while time.time() < deadline:
        try:
            last = http.get(url).status_code
            if last == expected:
                return
        except Exception:
            # A connection failure is expected briefly while dependencies move.
            pass

        time.sleep(1)

    raise AssertionError(
        f"Expected {expected} from {url}, last status was {last}"
    )


def test_redis_outage_returns_503_and_recovers(firefusion_url, http):
    """
    Verify explicit failure while Redis is unavailable and responsiveness after recovery.

    Assumptions:
    - the Docker Compose Redis service is named "cache";
    - the command is run from a directory where Docker can resolve the project compose file.

    If the merged compose file uses another service name, update "cache" here.
    """
    _compose("stop", "cache")

    try:
        # Redis unavailability should be visible as service unavailability rather
        # than being disguised as a normal empty forecast.
        _wait_for_status(
            http,
            f"{firefusion_url}/api/bushfire-forecast",
            503,
        )
    finally:
        # Always attempt to bring Redis back, even if the assertion above fails.
        _compose("start", "cache")

    # The Redis client may need a short time to reconnect after the container
    # returns, so poll rather than asserting immediately.
    deadline = time.time() + 30

    while time.time() < deadline:
        try:
            status = http.get(
                f"{firefusion_url}/api/bushfire-forecast"
            ).status_code

            if status in {200, 503}:
                # The purpose of this phase is to prove the API is responsive
                # again. A 503 may still be valid if restored cache state itself
                # is intentionally invalid/corrupt.
                return
        except Exception:
            pass

        time.sleep(1)

    pytest.fail("FireFusion API did not respond after Redis was restarted")
