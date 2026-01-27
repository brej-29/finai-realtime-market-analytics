from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from app.core.deps import get_realtime_manager
from app.core.logging import get_logger
from app.db.models import AssetType
from app.services.realtime.manager import RealtimeManager

router = APIRouter()

logger = get_logger("app.api.websocket")


@router.websocket("/ws/stream")
async def websocket_stream(
    websocket: WebSocket,
    manager: RealtimeManager = Depends(get_realtime_manager),
) -> None:
    await manager.connect(websocket)
    logger.info("WebSocket connected", extra={"client": str(websocket.client)})
    try:
        while True:
            message: Dict[str, Any] = await websocket.receive_json()
            msg_type = message.get("type")
            if msg_type == "subscribe":
                symbols: List[str] = message.get("symbols") or []
                asset_type_str: str = message.get("assetType", "stock")
                try:
                    asset_type = AssetType(asset_type_str)
                except ValueError:
                    asset_type = AssetType.STOCK
                await manager.subscribe(websocket, symbols=symbols, asset_type=asset_type)
                await websocket.send_json(
                    {
                        "type": "subscribed",
                        "symbols": [s.upper() for s in symbols],
                        "assetType": asset_type.value,
                    }
                )
            elif msg_type == "unsubscribe":
                await manager.unsubscribe_all(websocket)
            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})
            # Ignore unknown message types to keep protocol forward compatible.
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected", extra={"client": str(websocket.client)})
        await manager.disconnect(websocket)
    except Exception as exc:
        logger.warning(
            "WebSocket error",
            extra={"error": str(exc), "client": str(websocket.client)},
        )
        await manager.disconnect(websocket)