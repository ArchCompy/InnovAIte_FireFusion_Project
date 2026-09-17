"""Shared fixtures for the Backend test suite.

Integration tests exercise the running Backend stack over HTTP and, where
required, control service dependencies such as Redis. Unreachable services
produce explicit skips so CI can distinguish unavailable infrastructure from
application assertion failures.
"""

import os

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

    The previous value is restored after every test so integration tests
    remain independent of execution order and do not destroy developer data.
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

    original_prediction = client.get(PREDICTION_CACHE_KEY)

    try:
        yield client
    finally:
        if original_prediction is None:
            client.delete(PREDICTION_CACHE_KEY)
        else:
            client.set(
                PREDICTION_CACHE_KEY,
                original_prediction,
            )
        client.close()
