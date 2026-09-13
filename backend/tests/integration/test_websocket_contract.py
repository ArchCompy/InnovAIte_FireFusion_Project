"""
WebSocket/REST contract consistency test.

Zehong's reliability work and Arsh's freshness metadata both affect the
forecast payload. This test verifies that clients do not receive one contract
over REST and a different contract over WebSocket after the final merge.

The exact WebSocket route was intentionally left configurable because it may
change before the branch is ready to run.
"""

import json
import os

import pytest


# Skip this module cleanly if the optional websocket client is not installed.
websockets = pytest.importorskip("websockets")


@pytest.mark.asyncio
async def test_websocket_payload_uses_same_final_contract_as_rest(
    http,
    firefusion_url,
):
    """
    Compare one pushed WebSocket prediction with the current REST forecast.

    Set FORECAST_WEBSOCKET_URL once the final merged WebSocket endpoint is
    confirmed. If it is not configured yet, this future-facing test skips.
    """
    ws_url = os.getenv("FORECAST_WEBSOCKET_URL")

    if not ws_url:
        pytest.skip(
            "Set FORECAST_WEBSOCKET_URL once the merged WebSocket route is confirmed"
        )

    # Wait for one pushed forecast event.
    async with websockets.connect(ws_url, open_timeout=5) as websocket:
        raw = await websocket.recv()
        ws_payload = json.loads(raw)

    # Fetch the same public contract over REST for comparison.
    rest = http.get(f"{firefusion_url}/api/bushfire-forecast")

    assert rest.status_code == 200
    rest_payload = rest.json()

    assert ws_payload["type"] == rest_payload["type"]
    assert ws_payload.get("meta", {}).get("status") == rest_payload.get(
        "meta", {}
    ).get("status")

    # If a feature exists, confirm key merged property fields are consistent.
    if rest_payload.get("features"):
        rest_props = rest_payload["features"][0]["properties"]
        ws_props = ws_payload["features"][0]["properties"]

        assert ws_props.get("risk_factor") == rest_props.get("risk_factor")
        assert ws_props.get("fire_probability") == rest_props.get(
            "fire_probability"
        )
