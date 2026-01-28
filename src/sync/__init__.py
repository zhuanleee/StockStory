"""
Sync Module - Bi-directional Dashboard ↔ Telegram synchronization.

Components:
- SyncHub: Central event processor and router
- SocketIO Server: Real-time communication with dashboard (Flask-SocketIO)
- EventStore: Persistent event storage
- TelegramSync: Telegram bot integration
"""

from .sync_hub import (
    SyncHub,
    SyncEvent,
    SyncSource,
    EventType,
    EventStore,
    get_sync_hub,
    publish_trade_created,
    publish_buy_executed,
    publish_sell_executed,
    publish_exit_signal,
    publish_journal_entry,
    publish_scan_completed,
    publish_telegram_command,
)

from .socketio_server import (
    init_socketio,
    get_socketio,
    broadcast_event,
    broadcast_telegram_command,
)

# Keep websocket_server for standalone use if needed
from .websocket_server import (
    SyncWebSocketServer,
    get_ws_server,
    start_sync_server,
    run_sync_server,
)

__all__ = [
    # Hub
    'SyncHub',
    'SyncEvent',
    'SyncSource',
    'EventType',
    'EventStore',
    'get_sync_hub',
    # Publishers
    'publish_trade_created',
    'publish_buy_executed',
    'publish_sell_executed',
    'publish_exit_signal',
    'publish_journal_entry',
    'publish_scan_completed',
    'publish_telegram_command',
    # SocketIO (primary)
    'init_socketio',
    'get_socketio',
    'broadcast_event',
    'broadcast_telegram_command',
    # WebSocket (standalone)
    'SyncWebSocketServer',
    'get_ws_server',
    'start_sync_server',
    'run_sync_server',
]
