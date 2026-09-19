"""Unit tests for FireFusion Redis client configuration."""

from pathlib import Path
import sys
from unittest.mock import Mock

import pytest


APP_DIR = Path(__file__).resolve().parents[1] / "firefusion-api"

if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))


@pytest.fixture
def caching_module(monkeypatch):
    monkeypatch.setenv(
        "CACHE_URL",
        "redis://initial-cache:6379/0",
    )

    from app.internal.services import caching_service

    return caching_service


def test_create_cache_client_uses_cache_url_and_timeouts(
    caching_module,
    monkeypatch,
):
    configured_url = "redis://redis.example:6380/2"
    expected_client = object()
    redis_factory = Mock(return_value=expected_client)

    monkeypatch.setenv("CACHE_URL", configured_url)
    monkeypatch.setattr(
        caching_module.asyncio,
        "from_url",
        redis_factory,
    )

    result = caching_module.create_cache_client()

    assert result is expected_client
    redis_factory.assert_called_once_with(
        configured_url,
        socket_connect_timeout=5.0,
        socket_timeout=5.0,
    )


def test_create_cache_client_requires_cache_url(
    caching_module,
    monkeypatch,
):
    monkeypatch.delenv("CACHE_URL")

    with pytest.raises(KeyError):
        caching_module.create_cache_client()
