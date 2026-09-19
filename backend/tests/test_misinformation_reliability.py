"""Tests for reliability fixes in the misinformation API path.

Exercise the real MisinformationService with the repository mocked, so
these fail if the async conversion or error handling regress. See
docs/misinformation-api-reliability.md for the defects this covers.

Skip if the service's runtime dependencies are not installed locally, same
as test_forecast_service_unit.py.
"""
import asyncio
import inspect
import logging
import statistics
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock

import httpx
import pytest

APP_DIR = Path(__file__).resolve().parents[1] / "firefusion-api"
REPO_SOURCE_PATH = (
    APP_DIR / "app" / "internal" / "repositories" / "misinformation_repository.py"
)
SERVICE_SOURCE_PATH = (
    APP_DIR / "app" / "internal" / "services" / "misinformation_service.py"
)

SERVICE_METHODS = [
    "get_all_narrative_cluster_objects",
    "get_narrative_cluster_object_by_id",
    "get_incident_narrative_cluster_objects",
    "get_all_posts",
    "get_post_by_id",
    "get_all_active_incidents",
    "get_active_incident_by_id",
]


@pytest.fixture
def service_module(monkeypatch):
    """Import the real misinformation_service module."""
    if str(APP_DIR) not in sys.path:
        sys.path.insert(0, str(APP_DIR))
    # Importing the service pulls in config.config, which requires these
    # even though this module never uses broker/cache directly.
    monkeypatch.setenv("DB_URL", "postgresql://localhost/unused")
    monkeypatch.setenv("BROKER_URL", "amqp://localhost/unused")
    monkeypatch.setenv("CACHE_URL", "redis://localhost:6379")
    try:
        from app.internal.services import misinformation_service as ms
    except Exception as exc:
        pytest.skip(f"misinformation_service dependencies unavailable locally: {exc}")
    return ms


@pytest.fixture
def service(service_module, monkeypatch):
    """Return the real MisinformationService with its repository mocked."""
    repo = AsyncMock()
    svc = service_module.MisinformationService()
    monkeypatch.setattr(svc, "misinformation_repository", repo, raising=True)
    return svc, repo


# --- every public method must be async, so it can't block the event loop ---

@pytest.mark.parametrize("method_name", SERVICE_METHODS)
def test_service_methods_are_coroutines(service_module, method_name):
    method = getattr(service_module.MisinformationService, method_name)
    assert inspect.iscoroutinefunction(method), (
        f"{method_name} must be async so a slow query can't block the event loop"
    )


def test_repository_methods_are_coroutines(service_module):
    from app.internal.repositories.misinformation_repository import MisinformationRepository

    for method_name in SERVICE_METHODS:
        method = getattr(MisinformationRepository, method_name)
        assert inspect.iscoroutinefunction(method), f"{method_name} must be async"


# --- the repository no longer opens a raw connection per query ---

def test_repository_no_longer_calls_psycopg_connect():
    source = REPO_SOURCE_PATH.read_text()
    assert "psycopg.connect(" not in source, (
        "repository must not open a raw connection per query"
    )
    assert "get_pool()" in source, "repository must read from the shared pool"


def test_service_source_has_no_print():
    source = SERVICE_SOURCE_PATH.read_text()
    assert "print(" not in source, "print() bypasses logging; use logger.exception"


# --- a database failure raises, rather than being swallowed into an empty result ---

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method_name,args",
    [
        ("get_all_narrative_cluster_objects", ()),
        ("get_narrative_cluster_object_by_id", ("n1",)),
        ("get_incident_narrative_cluster_objects", ("i1",)),
        ("get_all_posts", ()),
        ("get_post_by_id", ("p1",)),
        ("get_all_active_incidents", ()),
        ("get_active_incident_by_id", ("i1",)),
    ],
)
async def test_database_failure_raises_unavailable(service, service_module, method_name, args):
    """Contract: an outage must not look like a genuine empty result."""
    svc, repo = service
    getattr(repo, method_name).side_effect = ConnectionError("db unreachable")

    with pytest.raises(service_module.MisinformationUnavailableError):
        await getattr(svc, method_name)(*args)


# --- those behaviours must not change: empty is still [], missing is still None ---

@pytest.mark.asyncio
async def test_empty_table_still_returns_empty_list(service):
    svc, repo = service
    repo.get_all_posts.return_value = []

    result = await svc.get_all_posts()

    assert result == []


@pytest.mark.asyncio
async def test_missing_record_still_returns_none(service):
    svc, repo = service
    repo.get_post_by_id.return_value = None

    result = await svc.get_post_by_id("does-not-exist")

    assert result is None


# --- failures are logged, not printed ---

@pytest.mark.asyncio
async def test_failure_is_logged_at_error_not_printed(service, capsys, caplog):
    svc, repo = service
    repo.get_all_posts.side_effect = ConnectionError("db unreachable")

    with caplog.at_level(logging.ERROR):
        with pytest.raises(Exception):
            await svc.get_all_posts()

    captured = capsys.readouterr()
    assert captured.out == "", f"failure must not be printed, got: {captured.out!r}"
    assert any(record.levelno >= logging.ERROR for record in caplog.records), (
        "failure must be logged at ERROR level"
    )


# --- integration: concurrent misinformation load must not stall the forecast path ---

@pytest.mark.integration
def test_concurrent_misinformation_load_does_not_degrade_forecast_latency(ff):
    """Regression for the event-loop-blocking defect.

    Fires 20 concurrent /api/misinformation/posts requests and times
    /api/bushfire-forecast in the same window. Before the async conversion,
    the synchronous psycopg.connect() calls ran on the event loop and
    serialized behind each other, stalling every other request on the
    process — including this one.
    """
    N_MISINFO = 20
    N_FORECAST = 10

    async def run():
        async with httpx.AsyncClient(base_url=ff, timeout=30.0) as client:
            idle_times = []
            for _ in range(5):
                start = time.perf_counter()
                r = await client.get("/api/bushfire-forecast")
                idle_times.append(time.perf_counter() - start)
                assert r.status_code == 200

            forecast_times = []

            async def timed_forecast():
                start = time.perf_counter()
                r = await client.get("/api/bushfire-forecast")
                forecast_times.append(time.perf_counter() - start)
                assert r.status_code == 200

            misinfo_tasks = [
                client.get("/api/misinformation/posts") for _ in range(N_MISINFO)
            ]
            forecast_tasks = [timed_forecast() for _ in range(N_FORECAST)]

            await asyncio.gather(*misinfo_tasks, *forecast_tasks)
            return idle_times, forecast_times

    idle_times, under_load_times = asyncio.run(run())

    idle_typical = statistics.median(idle_times)
    under_load_max = max(under_load_times)

    # Generous bound: normal async concurrency has scheduling jitter, but this
    # must not show the multi-hundred-millisecond serialized stall a blocking
    # psycopg.connect() call inside the event loop caused before the fix.
    threshold = max(idle_typical * 10, 1.0)
    assert under_load_max < threshold, (
        f"forecast latency degraded under misinformation load: "
        f"idle_median={idle_typical:.3f}s under_load_max={under_load_max:.3f}s "
        f"(threshold={threshold:.3f}s)"
    )
