"""Unit tests for WebSocket connection and broadcast reliability."""

import logging
from pathlib import Path
import sys
from unittest.mock import AsyncMock

import pytest


APP_DIR = Path(__file__).resolve().parents[1] / "firefusion-api"

PAYLOAD = {
    "type": "FeatureCollection",
    "features": [],
}


@pytest.fixture
def manager_class():
    """Import the real production WebSocket connection manager."""
    if str(APP_DIR) not in sys.path:
        sys.path.insert(0, str(APP_DIR))

    from app.internal.services.websocket_connection_manager import (
        WebsocketConnectionManager,
    )

    return WebsocketConnectionManager


@pytest.fixture
def manager(manager_class):
    """Return a fresh manager so tests do not share active clients."""
    return manager_class()


@pytest.mark.asyncio
async def test_connect_accepts_and_tracks_client(manager):
    client = AsyncMock()

    await manager.connect(client)

    client.accept.assert_awaited_once_with()
    assert manager.active == [client]


def test_disconnect_removes_connected_client(manager):
    client = AsyncMock()
    manager.active.append(client)

    manager.disconnect(client)

    assert client not in manager.active


@pytest.mark.asyncio
async def test_broadcast_sends_payload_to_every_active_client(
    manager,
):
    first_client = AsyncMock()
    second_client = AsyncMock()
    manager.active.extend([first_client, second_client])

    await manager.broadcast(PAYLOAD)

    first_client.send_json.assert_awaited_once_with(PAYLOAD)
    second_client.send_json.assert_awaited_once_with(PAYLOAD)
    assert manager.active == [first_client, second_client]


@pytest.mark.asyncio
async def test_broadcast_isolates_failed_client_and_logs_warning(
    manager,
    caplog,
):
    first_healthy_client = AsyncMock()
    failed_client = AsyncMock()
    second_healthy_client = AsyncMock()

    failed_client.send_json.side_effect = RuntimeError(
        "client disconnected"
    )
    manager.active.extend(
        [
            first_healthy_client,
            failed_client,
            second_healthy_client,
        ]
    )

    with caplog.at_level(
        logging.WARNING,
        logger=(
            "app.internal.services."
            "websocket_connection_manager"
        ),
    ):
        await manager.broadcast(PAYLOAD)

    first_healthy_client.send_json.assert_awaited_once_with(
        PAYLOAD
    )
    failed_client.send_json.assert_awaited_once_with(PAYLOAD)
    second_healthy_client.send_json.assert_awaited_once_with(
        PAYLOAD
    )

    assert failed_client not in manager.active
    assert manager.active == [
        first_healthy_client,
        second_healthy_client,
    ]
    assert "WebSocket broadcast failed" in caplog.text


@pytest.mark.asyncio
async def test_disconnect_is_safe_after_broadcast_removes_stale_client(
    manager,
):
    failed_client = AsyncMock()
    failed_client.send_json.side_effect = RuntimeError(
        "client disconnected"
    )
    manager.active.append(failed_client)

    await manager.broadcast(PAYLOAD)

    # The endpoint may later receive WebSocketDisconnect for the same
    # connection, so disconnect must tolerate an already-removed client.
    manager.disconnect(failed_client)

    assert manager.active == []


@pytest.mark.asyncio
async def test_removed_failed_client_is_not_retried(
    manager,
):
    failed_client = AsyncMock()
    healthy_client = AsyncMock()

    failed_client.send_json.side_effect = RuntimeError(
        "client disconnected"
    )
    manager.active.extend([failed_client, healthy_client])

    await manager.broadcast(PAYLOAD)

    failed_client.send_json.reset_mock()
    healthy_client.send_json.reset_mock()

    await manager.broadcast(PAYLOAD)

    failed_client.send_json.assert_not_awaited()
    healthy_client.send_json.assert_awaited_once_with(PAYLOAD)