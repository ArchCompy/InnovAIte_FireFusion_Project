import os

from redis import asyncio


CACHE_CONNECT_TIMEOUT_SECONDS = 5.0
CACHE_SOCKET_TIMEOUT_SECONDS = 5.0


def create_cache_client():
    """Create the Redis client from the configured cache URL.

    Connection and socket timeouts prevent Backend requests from waiting
    indefinitely when Redis is unavailable or unresponsive.
    """
    return asyncio.from_url(
        os.environ["CACHE_URL"],
        socket_connect_timeout=CACHE_CONNECT_TIMEOUT_SECONDS,
        socket_timeout=CACHE_SOCKET_TIMEOUT_SECONDS,
    )


cache_client = create_cache_client()
