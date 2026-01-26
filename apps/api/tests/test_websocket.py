from __future__ import annotations

from fastapi.testclient import TestClient

from app.db.models import AssetType
from app.main import app


def test_websocket_subscribe_and_receive_message() -> None:
    client = TestClient(app)

    with client.websocket_connect("/ws/stream") as websocket:
        websocket.send_json(
            {
                "type": "subscribe",
                "symbols": ["AAPL"],
                "assetType": AssetType.STOCK.value,
            }
        )

        message = websocket.receive_json()
        # The server should acknowledge the subscription; future background
        # streamer will send tick messages separately.
        assert message["type"] in {"subscribed", "tick"}
        assert message["assetType"] == AssetType.STOCK.value