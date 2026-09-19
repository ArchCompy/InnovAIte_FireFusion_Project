"""
Shared pytest configuration for the FireFusion Backend integration suite.

These tests are intentionally black-box tests. They communicate with the
running Backend services over HTTP and Redis instead of importing the feature
implementation directly. This allows the suite to validate the final merged
behaviour after the current PRs are integrated.

The defaults below match the local ports used during recent Backend testing.
Every value can be overridden with an environment variable if the final
merged Docker/Kubernetes configuration differs.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest

try:
    import redis
except ImportError:
    # Redis-dependent tests will be skipped cleanly if redis-py is not installed.
    redis = None


FIXTURE_DIR = Path(__file__).parent / "fixtures"


def _env(name: str, default: str) -> str:
    """Read a URL-like environment variable and remove a trailing slash."""
    return os.getenv(name, default).rstrip("/")


@pytest.fixture(scope="session")
def firefusion_url() -> str:
    """Base URL for the public FireFusion API."""
    return _env("FIREFUSION_URL", "http://localhost:8080")


@pytest.fixture(scope="session")
def model_url() -> str:
    """Base URL for the Model API."""
    return _env("MODEL_URL", "http://localhost:8081")


@pytest.fixture(scope="session")
def aggregator_url() -> str:
    """Base URL for the Aggregator API."""
    return _env("AGGREGATOR_URL", "http://localhost:8082")


@pytest.fixture(scope="session")
def api_key() -> str:
    """
    API key used for service-to-service security tests.

    The default is only intended for local development. A real shared/deployed
    environment should supply its configured API_KEY explicitly.
    """
    return os.getenv("API_KEY", "secret_key")


@pytest.fixture(scope="session")
def http() -> httpx.Client:
    """Reuse one HTTP client for the complete integration-test session."""
    with httpx.Client(timeout=8.0) as client:
        yield client


@pytest.fixture(scope="session")
def redis_client():
    """
    Connect directly to Redis so tests can create controlled forecast states.

    Direct cache access is deliberate here: it lets the integration suite
    reproduce fresh, stale, missing and corrupted cache states without
    depending on the real AI/Data Engineering pipeline.
    """
    if redis is None:
        pytest.skip(
            "redis package is not installed; install redis-py to run cache-state tests"
        )

    url = os.getenv("CACHE_URL", "redis://localhost:6379/0")
    client = redis.Redis.from_url(url)

    try:
        client.ping()
    except Exception as exc:
        pytest.skip(f"Redis is not reachable at {url}: {exc}")

    return client


@pytest.fixture(scope="session")
def valid_forecast() -> dict:
    """Load a known-valid forecast used by the cache-state tests."""
    with (FIXTURE_DIR / "valid_forecast.json").open("r", encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture
def preserve_forecast_cache(redis_client):
    """
    Preserve and restore the forecast cache around each test.

    This prevents an integration test from permanently replacing a developer's
    current local prediction or timestamp.
    """
    keys = ("predictions", "predictions:generated_at")
    before = {key: redis_client.get(key) for key in keys}

    try:
        yield redis_client
    finally:
        # Restore exactly what existed before the test.
        for key, value in before.items():
            if value is None:
                redis_client.delete(key)
            else:
                redis_client.set(key, value)


def seed_prediction(redis_client, payload: dict, generated_at: str | None = None) -> None:
    """
    Put a controlled prediction into Redis.

    The final merged Fire Risk contract is expected to use:
      - predictions
      - predictions:generated_at

    Omitting generated_at intentionally creates the "age unknown" case.
    """
    redis_client.set("predictions", json.dumps(payload))

    if generated_at is None:
        redis_client.delete("predictions:generated_at")
    else:
        redis_client.set("predictions:generated_at", generated_at)


def utc_now_iso() -> str:
    """Return an ISO-8601 UTC timestamp for tests that need a current value."""
    return datetime.now(timezone.utc).isoformat()
