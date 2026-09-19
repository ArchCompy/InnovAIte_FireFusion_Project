"""Shared fixtures for the Backend test suite.

Integration tests exercise the running Backend stack over HTTP and, where
required, control service dependencies such as Redis. Unreachable services
produce explicit skips so CI can distinguish unavailable infrastructure from
application assertion failures.
"""

import os
import sys
from pathlib import Path

import httpx
import pytest
from redis import Redis
from redis.exceptions import RedisError


FF_URL = os.getenv("FF_URL", "http://localhost:8080")
MODEL_URL = os.getenv("MODEL_URL", "http://localhost:8081")
AGG_URL = os.getenv("AGG_URL", "http://localhost:8082")
TEST_CACHE_URL = os.getenv(
    "TEST_CACHE_URL",
    "redis://localhost:6379/0",
)

PREDICTION_CACHE_KEY = "predictions"
GENERATED_AT_CACHE_KEY = "predictions:generated_at"

# forecast_service reads freshness settings from config.config, whose
# Environment requires these even for tests that never touch the database or
# broker. Unit tests import the service without a running stack, so provide
# inert defaults (real values, if already set, win).
os.environ.setdefault("DB_URL", "postgresql://localhost/unused")
os.environ.setdefault("BROKER_URL", "amqp://localhost/unused")

# forecast_service imports the top-level shared/ package (shared/tracing.py),
# which lives in backend/ next to each service. In the images it sits beside
# app/; for tests, put backend/ on the path once here so every test module can
# import the service without depending on which file ran first.
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        (
            "integration: hits the running Backend stack "
            "and its service dependencies"
        ),
    )


def _reachable(url):
    try:
        httpx.get(url, timeout=2.0)
        return True
    except Exception:
        return False


@pytest.fixture(scope="session")
def http():
    with httpx.Client(timeout=10.0) as client:
        yield client


@pytest.fixture
def ff():
    if not _reachable(f"{FF_URL}/openapi.json"):
        pytest.skip(
            f"firefusion-api not reachable at {FF_URL}. "
            "Start the stack: docker compose --profile default up -d"
        )
    return FF_URL


@pytest.fixture
def model():
    if not _reachable(f"{MODEL_URL}/model/hello"):
        pytest.skip(f"model-api not reachable at {MODEL_URL}.")
    return MODEL_URL


@pytest.fixture
def agg():
    if not _reachable(f"{AGG_URL}/openapi.json"):
        pytest.skip(f"aggregator-api not reachable at {AGG_URL}.")
    return AGG_URL


@pytest.fixture
def prediction_cache():
    """Provide isolated access to the running prediction cache.

    Both the forecast and its predictions:generated_at timestamp are
    restored after every test so integration tests remain independent of
    execution order and do not destroy developer data. The timestamp is also
    cleared on entry: a leftover one from an earlier test or a real prediction
    would otherwise make a forecast written directly to Redis look live
    instead of having an unknown age.
    """

    client = Redis.from_url(
        TEST_CACHE_URL,
        decode_responses=True,
        socket_connect_timeout=2.0,
        socket_timeout=2.0,
    )

    try:
        client.ping()
    except RedisError:
        client.close()
        pytest.skip(
            "Redis test dependency is not reachable"
        )

    original = {
        key: client.get(key)
        for key in (PREDICTION_CACHE_KEY, GENERATED_AT_CACHE_KEY)
    }
    client.delete(GENERATED_AT_CACHE_KEY)

    try:
        yield client
    finally:
        for key, value in original.items():
            if value is None:
                client.delete(key)
            else:
                client.set(key, value)
        client.close()
