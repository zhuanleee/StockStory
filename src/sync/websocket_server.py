#!/usr/bin/env python3
"""
WebSocket Server for real-time Dashboard ↔ Telegram sync.

Features:
- Real-time bi-directional communication
- Automatic reconnection handling
- Heartbeat/ping-pong for connection health
- Event broadcasting
"""

import os
import json
import asyncio
import logging
from datetime import datetime
from typing import Set, Dict, Any
import websockets
from websockets.server import serve, WebSocketServerProtocol

from .sync_hub import (
    get_sync_hub, SyncHub, SyncEvent, SyncSource, EventType
)

logger = logging.getLogger(__name__)


class SyncWebSocketServer:
    """WebSocket server for sync hub."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8765):
        self.host = host
        self.port = port
        self.hub = get_sync_hub()
        self.clients: Dict[WebSocketServerProtocol, dict] = {}
        self._server = None
        self._running = False

    async def handler(self, websocket: WebSocketServerProtocol, path: str = "/"):
        """Handle WebSocket connections."""
        client_id = str(id(websocket))[-8:]
        client_info = {
            'id': client_id,
            'connected_at': datetime.now().isoformat(),
            'last_heartbeat': datetime.now().isoformat(),
        }
        self.clients[websocket] = client_info

        logger.info(f"Client connected: {client_id} (total: {len(self.clients)})")

        try:
            # Register with sync hub
            await self.hub.register_client(websocket)

            # Handle messages
            async for message in websocket:
                await self._handle_message(websocket, message)

        except websockets.exceptions.ConnectionClosed as e:
            logger.info(f"Client disconnected: {client_id} - {e}")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            # Cleanup
            await self.hub.unregister_client(websocket)
            del self.clients[websocket]
            logger.info(f"Client removed: {client_id} (remaining: {len(self.clients)})")

    async def _handle_message(self, websocket: WebSocketServerProtocol, message: str):
        """Handle incoming WebSocket message."""
        try:
            data = json.loads(message)
            msg_type = data.get('type', '')

            if msg_type == 'heartbeat':
                # Respond to heartbeat
                await websocket.send(json.dumps({
                    'type': 'heartbeat_ack',
                    'timestamp': datetime.now().isoformat()
                }))
                if websocket in self.clients:
                    self.clients[websocket]['last_heartbeat'] = datetime.now().isoformat()

            elif msg_type == 'sync_event':
                # Process incoming sync event from dashboard
                event_data = data.get('event', {})
                event = SyncEvent.from_dict(event_data)
                event.source = SyncSource.DASHBOARD
                await self.hub.publish(event)

            elif msg_type == 'ack':
                # Acknowledge event receipt
                event_id = data.get('event_id')
                if event_id:
                    self.hub.event_store.mark_synced(event_id, 'dashboard')

            elif msg_type == 'request_sync':
                # Client requesting full sync
                recent = self.hub.event_store.get_recent(50)
                await websocket.send(json.dumps({
                    'type': 'sync_history',
                    'events': [e.to_dict() for e in recent]
                }))

            elif msg_type == 'get_status':
                # Get sync status
                status = self.hub.get_sync_status()
                await websocket.send(json.dumps({
                    'type': 'status',
                    'status': status
                }))

            elif msg_type == 'publish':
                # Publish a new event
                event_type = data.get('event_type')
                payload = data.get('payload', {})

                if event_type and hasattr(EventType, event_type.upper()):
                    event = self.hub.create_event(
                        EventType[event_type.upper()],
                        SyncSource.DASHBOARD,
                        payload
                    )
                    await self.hub.publish(event)
                    await websocket.send(json.dumps({
                        'type': 'publish_ack',
                        'event_id': event.id
                    }))

        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON received: {message[:100]}")
        except Exception as e:
            logger.error(f"Message handling error: {e}")

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients."""
        if not self.clients:
            return

        msg_str = json.dumps(message)
        disconnected = []

        for websocket in self.clients:
            try:
                await websocket.send(msg_str)
            except Exception as e:
                logger.warning(f"Broadcast failed to client: {e}")
                disconnected.append(websocket)

        # Remove disconnected clients
        for ws in disconnected:
            if ws in self.clients:
                del self.clients[ws]

    async def start(self):
        """Start the WebSocket server."""
        self._running = True
        logger.info(f"Starting WebSocket server on ws://{self.host}:{self.port}")

        async with serve(self.handler, self.host, self.port):
            while self._running:
                await asyncio.sleep(1)

    async def stop(self):
        """Stop the WebSocket server."""
        self._running = False
        # Close all client connections
        for websocket in list(self.clients.keys()):
            await websocket.close()

    def get_client_count(self) -> int:
        """Get number of connected clients."""
        return len(self.clients)


# Global server instance
_ws_server: SyncWebSocketServer = None


def get_ws_server() -> SyncWebSocketServer:
    """Get the global WebSocket server instance."""
    global _ws_server
    if _ws_server is None:
        port = int(os.environ.get('WS_PORT', 8765))
        _ws_server = SyncWebSocketServer(port=port)
    return _ws_server


async def start_sync_server():
    """Start the sync WebSocket server."""
    server = get_ws_server()
    await server.start()


def run_sync_server():
    """Run sync server (blocking)."""
    asyncio.run(start_sync_server())


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    run_sync_server()
