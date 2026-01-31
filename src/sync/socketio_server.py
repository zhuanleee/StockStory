#!/usr/bin/env python3
"""
Flask-SocketIO integration for real-time sync.

This integrates directly with the Flask app for single-deployment sync.
"""

import logging
from datetime import datetime
from typing import Optional
from flask import request
from flask_socketio import SocketIO, emit

from .sync_hub import (
    get_sync_hub, SyncHub, SyncEvent, SyncSource, EventType
)

logger = logging.getLogger(__name__)

# Global SocketIO instance
socketio: Optional[SocketIO] = None


def init_socketio(app, **kwargs):
    """
    Initialize SocketIO with Flask app (async/non-blocking).

    Uses eventlet async_mode for better scalability and non-blocking I/O.
    """
    global socketio

    # CORS origins for GitHub Pages + local development
    allowed_origins = [
        'https://zhuanleee.github.io',
        'http://localhost:5000',
        'http://127.0.0.1:5000',
        'https://web-production-46562.up.railway.app',
    ]

    # Production config with eventlet for async/non-blocking
    default_config = {
        'cors_allowed_origins': allowed_origins,
        'async_mode': 'eventlet',  # Changed from 'threading' for non-blocking I/O
        'ping_timeout': 60,
        'ping_interval': 25,
        'logger': False,  # Disable SocketIO's verbose logging
        'engineio_logger': False,  # Disable engine.io logging
        'always_connect': True,  # Auto-reconnect on disconnection
    }
    default_config.update(kwargs)

    try:
        socketio = SocketIO(app, **default_config)

        # Register event handlers
        register_handlers(socketio)

        logger.info("✅ SocketIO initialized (async mode: eventlet)")
        return socketio
    except Exception as e:
        logger.error(f"❌ SocketIO initialization failed: {e}")
        return None


def get_socketio() -> Optional[SocketIO]:
    """Get the global SocketIO instance."""
    return socketio


def register_handlers(sio: SocketIO):
    """Register SocketIO event handlers."""

    @sio.on('connect')
    def handle_connect():
        """Handle client connection."""
        client_id = request.sid
        logger.info(f"Client connected: {client_id}")

        hub = get_sync_hub()

        # Send welcome message
        emit('connected', {
            'client_id': client_id,
            'timestamp': datetime.now().isoformat(),
            'message': 'Sync connection established'
        })

        # Send recent events for sync
        recent = hub.event_store.get_recent(30)
        emit('sync_history', {
            'events': [e.to_dict() for e in recent],
            'count': len(recent)
        })

        # Notify status
        emit('status', hub.get_sync_status())

    @sio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection."""
        client_id = request.sid
        logger.info(f"Client disconnected: {client_id}")

    @sio.on('heartbeat')
    def handle_heartbeat(data=None):
        """Handle heartbeat ping."""
        emit('heartbeat_ack', {
            'timestamp': datetime.now().isoformat()
        })

    @sio.on('publish')
    def handle_publish(data):
        """Handle event publish from dashboard."""
        try:
            event_type = data.get('event_type', '')
            payload = data.get('payload', {})

            if not event_type:
                emit('error', {'message': 'event_type required'})
                return

            hub = get_sync_hub()

            # Create event
            try:
                et = EventType[event_type.upper()]
            except KeyError:
                emit('error', {'message': f'Invalid event_type: {event_type}'})
                return

            event = hub.create_event(et, SyncSource.DASHBOARD, payload)

            # Store event
            hub.event_store.add(event)

            # Broadcast to all clients
            sio.emit('sync_event', {'event': event.to_dict()})

            # Send to Telegram
            _send_to_telegram_sync(hub, event)

            # Acknowledge
            emit('publish_ack', {
                'event_id': event.id,
                'timestamp': event.timestamp
            })

            logger.info(f"Published event: {event_type}")

        except Exception as e:
            logger.error(f"Publish error: {e}")
            emit('error', {'message': str(e)})

    @sio.on('request_sync')
    def handle_request_sync(data=None):
        """Handle full sync request."""
        hub = get_sync_hub()
        count = data.get('count', 50) if data else 50
        recent = hub.event_store.get_recent(count)
        emit('sync_history', {
            'events': [e.to_dict() for e in recent],
            'count': len(recent)
        })

    @sio.on('get_status')
    def handle_get_status(data=None):
        """Handle status request."""
        hub = get_sync_hub()
        emit('status', hub.get_sync_status())

    @sio.on('ack')
    def handle_ack(data):
        """Handle event acknowledgment."""
        event_id = data.get('event_id')
        if event_id:
            hub = get_sync_hub()
            hub.event_store.mark_synced(event_id, 'dashboard')


def _send_to_telegram_sync(hub: SyncHub, event: SyncEvent):
    """Send event to Telegram (synchronous)."""
    import requests

    if not hub.telegram_bot_token or not hub.telegram_chat_id:
        return

    message = hub._format_telegram_message(event)
    if not message:
        return

    try:
        url = f"https://api.telegram.org/bot{hub.telegram_bot_token}/sendMessage"
        response = requests.post(url, json={
            'chat_id': hub.telegram_chat_id,
            'text': message,
            'parse_mode': 'Markdown'
        }, timeout=10)

        if response.status_code == 200:
            hub.event_store.mark_synced(event.id, 'telegram')
            logger.info(f"Sent to Telegram: {event.event_type}")
        else:
            logger.warning(f"Telegram send failed: {response.status_code}")

    except Exception as e:
        logger.error(f"Telegram send error: {e}")


def broadcast_event(event: SyncEvent):
    """Broadcast an event to all connected clients."""
    global socketio
    if socketio:
        socketio.emit('sync_event', {'event': event.to_dict()})


def broadcast_telegram_command(command: str, args: str = "", user: str = ""):
    """Broadcast a Telegram command to dashboard."""
    global socketio

    hub = get_sync_hub()
    event = hub.create_event(
        EventType.COMMAND_RECEIVED,
        SyncSource.TELEGRAM,
        {
            'command': command,
            'args': args,
            'user': user,
            'raw_text': f"/{command} {args}".strip()
        }
    )
    hub.event_store.add(event)

    if socketio:
        socketio.emit('sync_event', {'event': event.to_dict()})

    return event
