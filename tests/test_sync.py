"""Tests for sync module."""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
import tempfile
import os


class TestSyncHub:
    """Tests for SyncHub class."""

    def test_sync_hub_singleton(self):
        """Test that get_sync_hub returns singleton."""
        from src.sync.sync_hub import get_sync_hub

        hub1 = get_sync_hub()
        hub2 = get_sync_hub()

        assert hub1 is hub2

    def test_create_event(self):
        """Test event creation."""
        from src.sync.sync_hub import get_sync_hub, EventType, SyncSource

        hub = get_sync_hub()
        event = hub.create_event(
            EventType.TRADE_CREATED,
            SyncSource.DASHBOARD,
            {'ticker': 'NVDA', 'price': 100}
        )

        assert event.event_type == EventType.TRADE_CREATED
        assert event.source == SyncSource.DASHBOARD
        assert event.payload['ticker'] == 'NVDA'
        assert event.id is not None

    def test_event_to_dict(self):
        """Test event serialization."""
        from src.sync.sync_hub import get_sync_hub, EventType, SyncSource

        hub = get_sync_hub()
        event = hub.create_event(
            EventType.BUY_EXECUTED,
            SyncSource.TELEGRAM,
            {'ticker': 'AAPL', 'shares': 10}
        )

        event_dict = event.to_dict()

        assert 'id' in event_dict
        assert 'event_type' in event_dict
        assert 'source' in event_dict
        assert 'payload' in event_dict
        assert 'timestamp' in event_dict


class TestEventStore:
    """Tests for EventStore class."""

    def test_add_and_get_recent(self):
        """Test adding and retrieving events."""
        from src.sync.sync_hub import EventStore, SyncEvent, EventType, SyncSource

        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = os.path.join(tmpdir, 'test_events.json')
            store = EventStore(store_path=store_path)
            event = SyncEvent(
                id='test-123',
                event_type=EventType.SCAN_COMPLETED,
                source=SyncSource.DASHBOARD,
                payload={'count': 50},
                timestamp=datetime.now().isoformat()
            )

            store.add(event)
            recent = store.get_recent(10)

            assert len(recent) >= 1
            assert any(e.id == 'test-123' for e in recent)

    def test_get_recent_events(self):
        """Test getting recent events."""
        from src.sync.sync_hub import EventStore, SyncEvent, EventType, SyncSource

        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = os.path.join(tmpdir, 'test_events.json')
            store = EventStore(store_path=store_path)

            for i in range(5):
                event = SyncEvent(
                    id=f'event-{i}',
                    event_type=EventType.JOURNAL_ADDED,
                    source=SyncSource.TELEGRAM,
                    payload={'index': i},
                    timestamp=datetime.now().isoformat()
                )
                store.add(event)

            recent = store.get_recent(3)

            assert len(recent) == 3

    def test_event_store_max_limit(self):
        """Test event store respects max limit."""
        from src.sync.sync_hub import EventStore, SyncEvent, EventType, SyncSource

        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = os.path.join(tmpdir, 'test_events.json')
            store = EventStore(store_path=store_path)
            store.max_events = 5  # Set max events limit

            for i in range(10):
                event = SyncEvent(
                    id=f'event-{i}',
                    event_type=EventType.EXIT_SIGNAL,
                    source=SyncSource.DASHBOARD,
                    payload={},
                    timestamp=datetime.now().isoformat()
                )
                store.add(event)

            # Should only keep last 5
            assert len(store.events) <= 5


class TestSyncPublishers:
    """Tests for sync publisher async functions."""

    def test_publish_trade_created(self):
        """Test publishing trade created event."""
        import asyncio
        from src.sync.sync_hub import publish_trade_created, get_sync_hub

        hub = get_sync_hub()
        initial_count = len(hub.event_store.events)

        # publish_trade_created is async
        asyncio.get_event_loop().run_until_complete(
            publish_trade_created('NVDA', 'Test thesis', 'tech')
        )

        assert len(hub.event_store.events) > initial_count

    def test_publish_buy_executed(self):
        """Test publishing buy executed event."""
        import asyncio
        from src.sync.sync_hub import publish_buy_executed, get_sync_hub

        hub = get_sync_hub()
        initial_count = len(hub.event_store.events)

        # publish_buy_executed(ticker, shares, price, reason, source)
        asyncio.get_event_loop().run_until_complete(
            publish_buy_executed('AAPL', 10, 150.0, 'Test buy')
        )

        assert len(hub.event_store.events) > initial_count

    def test_publish_sell_executed(self):
        """Test publishing sell executed event."""
        import asyncio
        from src.sync.sync_hub import publish_sell_executed, get_sync_hub

        hub = get_sync_hub()
        initial_count = len(hub.event_store.events)

        # publish_sell_executed(ticker, shares, price, reason, source)
        asyncio.get_event_loop().run_until_complete(
            publish_sell_executed('TSLA', 5, 200.0, 'Test sell')
        )

        assert len(hub.event_store.events) > initial_count


class TestEventTypes:
    """Tests for event type definitions."""

    def test_event_types_exist(self):
        """Test all required event types exist."""
        from src.sync.sync_hub import EventType

        required_types = [
            'TRADE_CREATED',
            'BUY_EXECUTED',
            'SELL_EXECUTED',
            'EXIT_SIGNAL',
            'JOURNAL_ADDED',
            'SCAN_COMPLETED',
            'COMMAND_RECEIVED',
        ]

        for event_type in required_types:
            assert hasattr(EventType, event_type)

    def test_sync_sources_exist(self):
        """Test all required sync sources exist."""
        from src.sync.sync_hub import SyncSource

        # Actual sources in implementation: DASHBOARD, TELEGRAM, SYSTEM
        required_sources = ['DASHBOARD', 'TELEGRAM', 'SYSTEM']

        for source in required_sources:
            assert hasattr(SyncSource, source)
