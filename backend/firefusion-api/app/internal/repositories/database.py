import logging

from psycopg_pool import AsyncConnectionPool

from ...config.config import environment

logger = logging.getLogger(__name__)

_pool: AsyncConnectionPool | None = None


async def open_pool() -> AsyncConnectionPool:
    """Open the shared connection pool. Call once during app startup.

    open() is non-blocking (wait=False, the default): it returns immediately
    and connections are established in the background, so a database outage
    at boot does not stop the rest of the service (forecast, WebSocket) from
    starting. Individual queries against an unreachable database still time
    out and raise, same as before.
    """
    global _pool

    _pool = AsyncConnectionPool(
        environment.db_url,
        min_size=environment.db_pool_min_size,
        max_size=environment.db_pool_max_size,
        timeout=environment.db_pool_timeout_seconds,
        open=False,
    )
    await _pool.open()

    logger.info(
        "Database pool opened (min_size=%s, max_size=%s)",
        environment.db_pool_min_size,
        environment.db_pool_max_size,
    )
    return _pool


async def close_pool() -> None:
    """Close the shared connection pool. Call once during app shutdown."""
    global _pool

    if _pool is not None:
        await _pool.close()
        _pool = None


def get_pool() -> AsyncConnectionPool:
    """Return the shared connection pool.

    Raises if called before open_pool() has run during startup, rather than
    silently opening a fresh pool per call.
    """
    if _pool is None:
        raise RuntimeError(
            "Database pool has not been opened. "
            "open_pool() must run during application startup before any query."
        )
    return _pool
