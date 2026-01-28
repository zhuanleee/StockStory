#!/usr/bin/env python3
"""
Sync Hub - WebSocket-based bi-directional sync between Dashboard and Telegram.

Architecture:
- WebSocket server for real-time dashboard connections
- Event-driven sync with persistent event store
- Telegram bot integration for command/notification sync
"""

import os
import json
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Any, Callable
from dataclasses import dataclass
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class SyncSource(str, Enum):
    """Source of sync event."""
    DASHBOARD = "dashboard"
    TELEGRAM = "telegram"
    SYSTEM = "system"


class EventType(str, Enum):
    """Types of sync events."""
    # Trade Events
    TRADE_CREATED = "trade_created"
    TRADE_DELETED = "trade_deleted"
    BUY_EXECUTED = "buy_executed"
    SELL_EXECUTED = "sell_executed"
    POSITION_CLOSED = "position_closed"

    # Scan Events
    SCAN_STARTED = "scan_started"
    SCAN_COMPLETED = "scan_completed"
    EXIT_SIGNAL = "exit_signal"
    SCALE_OPPORTUNITY = "scale_opportunity"

    # Journal Events
    JOURNAL_ADDED = "journal_added"
    JOURNAL_DELETED = "journal_deleted"

    # Alert Events
    ALERT_TRIGGERED = "alert_triggered"
    RISK_WARNING = "risk_warning"

    # Report Events
    REPORT_GENERATED = "report_generated"
    BRIEFING_REQUESTED = "briefing_requested"

    # Command Events
    COMMAND_RECEIVED = "command_received"
    COMMAND_RESPONSE = "command_response"

    # System Events
    CONNECTION_ESTABLISHED = "connection_established"
    CONNECTION_LOST = "connection_lost"
    SYNC_REQUESTED = "sync_requested"
    HEARTBEAT = "heartbeat"


@dataclass
class SyncEvent:
    """A sync event that can be sent between Dashboard and Telegram."""
    id: str
    event_type: EventType
    source: SyncSource
    payload: Dict[str, Any]
    timestamp: str
    synced_to_telegram: bool = False
    synced_to_dashboard: bool = False
    ack_required: bool = True
    priority: int = 1  # 1=normal, 2=high, 3=critical

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'event_type': self.event_type.value if isinstance(self.event_type, EventType) else self.event_type,
            'source': self.source.value if isinstance(self.source, SyncSource) else self.source,
            'payload': self.payload,
            'timestamp': self.timestamp,
            'synced_to_telegram': self.synced_to_telegram,
            'synced_to_dashboard': self.synced_to_dashboard,
            'ack_required': self.ack_required,
            'priority': self.priority,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'SyncEvent':
        return cls(
            id=data['id'],
            event_type=EventType(data['event_type']) if data['event_type'] in [e.value for e in EventType] else data['event_type'],
            source=SyncSource(data['source']) if data['source'] in [s.value for s in SyncSource] else data['source'],
            payload=data['payload'],
            timestamp=data['timestamp'],
            synced_to_telegram=data.get('synced_to_telegram', False),
            synced_to_dashboard=data.get('synced_to_dashboard', False),
            ack_required=data.get('ack_required', True),
            priority=data.get('priority', 1),
        )


class EventStore:
    """Persistent event store for sync events."""

    def __init__(self, store_path: str = "data/sync_events.json"):
        self.store_path = Path(store_path)
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self.events: List[SyncEvent] = []
        self.max_events = 1000  # Keep last 1000 events
        self._load()

    def _load(self):
        """Load events from file."""
        if self.store_path.exists():
            try:
                with open(self.store_path, 'r') as f:
                    data = json.load(f)
                    self.events = [SyncEvent.from_dict(e) for e in data]
            except Exception as e:
                logger.error(f"Failed to load event store: {e}")
                self.events = []

    def _save(self):
        """Save events to file."""
        try:
            # Keep only recent events
            self.events = self.events[-self.max_events:]
            with open(self.store_path, 'w') as f:
                json.dump([e.to_dict() for e in self.events], f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save event store: {e}")

    def add(self, event: SyncEvent):
        """Add an event to the store."""
        self.events.append(event)
        self._save()

    def get_unsynced(self, target: str) -> List[SyncEvent]:
        """Get events not yet synced to target (telegram/dashboard)."""
        if target == 'telegram':
            return [e for e in self.events if not e.synced_to_telegram]
        elif target == 'dashboard':
            return [e for e in self.events if not e.synced_to_dashboard]
        return []

    def mark_synced(self, event_id: str, target: str):
        """Mark an event as synced to target."""
        for event in self.events:
            if event.id == event_id:
                if target == 'telegram':
                    event.synced_to_telegram = True
                elif target == 'dashboard':
                    event.synced_to_dashboard = True
                self._save()
                break

    def get_recent(self, count: int = 50) -> List[SyncEvent]:
        """Get most recent events."""
        return self.events[-count:]

    def get_by_type(self, event_type: EventType, count: int = 20) -> List[SyncEvent]:
        """Get events by type."""
        return [e for e in self.events if e.event_type == event_type][-count:]


class SyncHub:
    """
    Central sync hub managing bi-directional sync between Dashboard and Telegram.

    Features:
    - WebSocket connections for dashboard clients
    - Event-driven architecture
    - Persistent event store
    - Telegram bot integration
    - Automatic reconnection handling
    """

    def __init__(self):
        self.event_store = EventStore()
        self.connected_clients: Set[Any] = set()  # WebSocket connections
        self.event_handlers: Dict[EventType, List[Callable]] = {}
        self.telegram_bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '')
        self.telegram_chat_id = os.environ.get('TELEGRAM_CHAT_ID', '')
        self._running = False

        # Register default handlers
        self._register_default_handlers()

    def _register_default_handlers(self):
        """Register default event handlers."""
        # Trade events -> Telegram notifications
        self.register_handler(EventType.TRADE_CREATED, self._handle_trade_created)
        self.register_handler(EventType.BUY_EXECUTED, self._handle_buy_executed)
        self.register_handler(EventType.SELL_EXECUTED, self._handle_sell_executed)
        self.register_handler(EventType.EXIT_SIGNAL, self._handle_exit_signal)
        self.register_handler(EventType.JOURNAL_ADDED, self._handle_journal_added)
        self.register_handler(EventType.SCAN_COMPLETED, self._handle_scan_completed)
        self.register_handler(EventType.COMMAND_RECEIVED, self._handle_command_received)

    def register_handler(self, event_type: EventType, handler: Callable):
        """Register a handler for an event type."""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)

    def create_event(
        self,
        event_type: EventType,
        source: SyncSource,
        payload: Dict[str, Any],
        priority: int = 1,
        ack_required: bool = True,
    ) -> SyncEvent:
        """Create a new sync event."""
        event = SyncEvent(
            id=str(uuid.uuid4())[:8],
            event_type=event_type,
            source=source,
            payload=payload,
            timestamp=datetime.now().isoformat(),
            priority=priority,
            ack_required=ack_required,
        )
        return event

    async def publish(self, event: SyncEvent):
        """Publish an event to all targets."""
        # Store event
        self.event_store.add(event)

        # Run handlers
        if event.event_type in self.event_handlers:
            for handler in self.event_handlers[event.event_type]:
                try:
                    result = handler(event)
                    if asyncio.iscoroutine(result):
                        await result
                except Exception as e:
                    logger.error(f"Handler error for {event.event_type}: {e}")

        # Broadcast to connected dashboard clients
        await self._broadcast_to_dashboards(event)

        # Send to Telegram if from dashboard
        if event.source == SyncSource.DASHBOARD:
            await self._send_to_telegram(event)
            self.event_store.mark_synced(event.id, 'telegram')

    async def _broadcast_to_dashboards(self, event: SyncEvent):
        """Broadcast event to all connected dashboard clients."""
        if not self.connected_clients:
            return

        message = json.dumps({
            'type': 'sync_event',
            'event': event.to_dict()
        })

        disconnected = set()
        for client in self.connected_clients:
            try:
                await client.send(message)
                self.event_store.mark_synced(event.id, 'dashboard')
            except Exception as e:
                logger.warning(f"Failed to send to client: {e}")
                disconnected.add(client)

        # Remove disconnected clients
        self.connected_clients -= disconnected

    async def _send_to_telegram(self, event: SyncEvent):
        """Send event notification to Telegram."""
        if not self.telegram_bot_token or not self.telegram_chat_id:
            return

        message = self._format_telegram_message(event)
        if not message:
            return

        try:
            import aiohttp
            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            async with aiohttp.ClientSession() as session:
                await session.post(url, json={
                    'chat_id': self.telegram_chat_id,
                    'text': message,
                    'parse_mode': 'Markdown'
                })
        except Exception as e:
            logger.error(f"Failed to send to Telegram: {e}")

    def _format_telegram_message(self, event: SyncEvent) -> Optional[str]:
        """Format event as Telegram message."""
        payload = event.payload

        formatters = {
            EventType.TRADE_CREATED: lambda p: f"📝 *Trade Created*\n`{p.get('ticker')}` added to watchlist\nThesis: {p.get('thesis', 'N/A')[:100]}",
            EventType.BUY_EXECUTED: lambda p: f"📈 *Buy Executed*\n`{p.get('ticker')}`: {p.get('shares')} shares @ ${p.get('price', 0):.2f}\nReason: {p.get('reason', 'N/A')}",
            EventType.SELL_EXECUTED: lambda p: f"📉 *Sell Executed*\n`{p.get('ticker')}`: {p.get('shares')} shares @ ${p.get('price', 0):.2f}\nReason: {p.get('reason', 'N/A')}",
            EventType.EXIT_SIGNAL: lambda p: f"⚠️ *Exit Signal*\n`{p.get('ticker')}`: {p.get('signal_type')}\nConfidence: {p.get('confidence', 0):.0f}%\n{p.get('reason', '')}",
            EventType.SCALE_OPPORTUNITY: lambda p: f"💡 *Scale {'In' if p.get('direction') == 'in' else 'Out'}*\n`{p.get('ticker')}`: {p.get('size_pct', 0):.0f}%\n{p.get('reason', '')}",
            EventType.JOURNAL_ADDED: lambda p: f"📓 *Journal Entry*\n[{p.get('entry_type', 'note').upper()}] {p.get('ticker', '')}\n{p.get('content', '')[:200]}",
            EventType.SCAN_COMPLETED: lambda p: f"🔍 *Scan Complete*\n{p.get('positions_scanned', 0)} positions scanned\nSignals: {p.get('signals_count', 0)}",
            EventType.REPORT_GENERATED: lambda p: f"📊 *Report Ready*\n{p.get('report_type', 'Daily')} report generated",
            EventType.RISK_WARNING: lambda p: f"🚨 *Risk Warning*\n`{p.get('ticker')}`: {p.get('risk_level', 'unknown').upper()}\n{p.get('message', '')}",
            EventType.ALERT_TRIGGERED: lambda p: f"🔔 *Alert*\n{p.get('alert_type', 'Info')}: {p.get('message', '')}",
        }

        formatter = formatters.get(event.event_type)
        if formatter:
            try:
                return formatter(payload)
            except Exception as e:
                logger.error(f"Format error: {e}")
        return None

    # Event Handlers
    def _handle_trade_created(self, event: SyncEvent):
        """Handle trade created event."""
        logger.info(f"Trade created: {event.payload.get('ticker')}")

    def _handle_buy_executed(self, event: SyncEvent):
        """Handle buy executed event."""
        logger.info(f"Buy executed: {event.payload.get('ticker')} x {event.payload.get('shares')}")

    def _handle_sell_executed(self, event: SyncEvent):
        """Handle sell executed event."""
        logger.info(f"Sell executed: {event.payload.get('ticker')} x {event.payload.get('shares')}")

    def _handle_exit_signal(self, event: SyncEvent):
        """Handle exit signal event."""
        logger.info(f"Exit signal: {event.payload.get('ticker')} - {event.payload.get('signal_type')}")

    def _handle_journal_added(self, event: SyncEvent):
        """Handle journal added event."""
        logger.info(f"Journal added: {event.payload.get('entry_type')}")

    def _handle_scan_completed(self, event: SyncEvent):
        """Handle scan completed event."""
        logger.info(f"Scan completed: {event.payload.get('positions_scanned')} positions")

    def _handle_command_received(self, event: SyncEvent):
        """Handle command received from Telegram."""
        command = event.payload.get('command', '')
        logger.info(f"Command received: {command}")
        # This will be processed and response sent back

    # Client Management
    async def register_client(self, websocket):
        """Register a new dashboard client."""
        self.connected_clients.add(websocket)

        # Send connection event
        event = self.create_event(
            EventType.CONNECTION_ESTABLISHED,
            SyncSource.SYSTEM,
            {'client_count': len(self.connected_clients)},
            ack_required=False,
        )
        await websocket.send(json.dumps({
            'type': 'connected',
            'client_id': str(uuid.uuid4())[:8],
            'event': event.to_dict()
        }))

        # Send recent events for sync
        recent = self.event_store.get_recent(20)
        await websocket.send(json.dumps({
            'type': 'sync_history',
            'events': [e.to_dict() for e in recent]
        }))

    async def unregister_client(self, websocket):
        """Unregister a dashboard client."""
        self.connected_clients.discard(websocket)

    def get_sync_status(self) -> dict:
        """Get current sync status."""
        unsynced_telegram = len(self.event_store.get_unsynced('telegram'))
        unsynced_dashboard = len(self.event_store.get_unsynced('dashboard'))

        return {
            'connected_clients': len(self.connected_clients),
            'total_events': len(self.event_store.events),
            'unsynced_to_telegram': unsynced_telegram,
            'unsynced_to_dashboard': unsynced_dashboard,
            'last_event': self.event_store.events[-1].to_dict() if self.event_store.events else None,
            'telegram_configured': bool(self.telegram_bot_token and self.telegram_chat_id),
        }


# Global sync hub instance
_sync_hub: Optional[SyncHub] = None


def get_sync_hub() -> SyncHub:
    """Get the global sync hub instance."""
    global _sync_hub
    if _sync_hub is None:
        _sync_hub = SyncHub()
    return _sync_hub


# Convenience functions for publishing events
async def publish_trade_created(ticker: str, thesis: str, theme: str = "", source: SyncSource = SyncSource.DASHBOARD):
    """Publish trade created event."""
    hub = get_sync_hub()
    event = hub.create_event(
        EventType.TRADE_CREATED,
        source,
        {'ticker': ticker, 'thesis': thesis, 'theme': theme}
    )
    await hub.publish(event)


async def publish_buy_executed(ticker: str, shares: int, price: float, reason: str = "", source: SyncSource = SyncSource.DASHBOARD):
    """Publish buy executed event."""
    hub = get_sync_hub()
    event = hub.create_event(
        EventType.BUY_EXECUTED,
        source,
        {'ticker': ticker, 'shares': shares, 'price': price, 'reason': reason},
        priority=2
    )
    await hub.publish(event)


async def publish_sell_executed(ticker: str, shares: int, price: float, reason: str = "", source: SyncSource = SyncSource.DASHBOARD):
    """Publish sell executed event."""
    hub = get_sync_hub()
    event = hub.create_event(
        EventType.SELL_EXECUTED,
        source,
        {'ticker': ticker, 'shares': shares, 'price': price, 'reason': reason},
        priority=2
    )
    await hub.publish(event)


async def publish_exit_signal(ticker: str, signal_type: str, confidence: float, reason: str = ""):
    """Publish exit signal event."""
    hub = get_sync_hub()
    event = hub.create_event(
        EventType.EXIT_SIGNAL,
        SyncSource.SYSTEM,
        {'ticker': ticker, 'signal_type': signal_type, 'confidence': confidence, 'reason': reason},
        priority=3
    )
    await hub.publish(event)


async def publish_journal_entry(entry_type: str, content: str, ticker: str = None, source: SyncSource = SyncSource.DASHBOARD):
    """Publish journal entry event."""
    hub = get_sync_hub()
    event = hub.create_event(
        EventType.JOURNAL_ADDED,
        source,
        {'entry_type': entry_type, 'content': content, 'ticker': ticker}
    )
    await hub.publish(event)


async def publish_scan_completed(positions_scanned: int, signals_count: int):
    """Publish scan completed event."""
    hub = get_sync_hub()
    event = hub.create_event(
        EventType.SCAN_COMPLETED,
        SyncSource.SYSTEM,
        {'positions_scanned': positions_scanned, 'signals_count': signals_count}
    )
    await hub.publish(event)


async def publish_telegram_command(command: str, args: str = "", user: str = ""):
    """Publish command received from Telegram."""
    hub = get_sync_hub()
    event = hub.create_event(
        EventType.COMMAND_RECEIVED,
        SyncSource.TELEGRAM,
        {'command': command, 'args': args, 'user': user}
    )
    await hub.publish(event)
