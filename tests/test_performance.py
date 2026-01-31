"""
Tests for Performance Utilities
"""
import pytest
import asyncio
import time
from src.core.performance import (
    PerformanceMonitor,
    monitor_performance,
    timed_lru_cache,
    parallel_fetch,
    batch_process
)


class TestPerformanceMonitor:
    """Test performance monitoring"""

    def test_record_metric(self):
        """Test recording a performance metric"""
        monitor = PerformanceMonitor()

        monitor.record("test_function", 1.5)

        assert "test_function" in monitor.metrics
        assert monitor.metrics["test_function"] == [1.5]
        assert monitor.call_counts["test_function"] == 1

    def test_get_stats(self):
        """Test retrieving performance statistics"""
        monitor = PerformanceMonitor()

        # Record multiple measurements
        monitor.record("test_function", 1.0)
        monitor.record("test_function", 2.0)
        monitor.record("test_function", 3.0)

        stats = monitor.get_stats("test_function")

        assert stats['count'] == 3
        assert stats['avg'] == 2.0
        assert stats['min'] == 1.0
        assert stats['max'] == 3.0

    def test_get_stats_empty(self):
        """Test stats for non-existent metric"""
        monitor = PerformanceMonitor()

        stats = monitor.get_stats("nonexistent")

        assert stats == {}

    def test_max_measurements(self):
        """Test that only last 1000 measurements are kept"""
        monitor = PerformanceMonitor()

        # Record 1500 measurements
        for i in range(1500):
            monitor.record("test_function", float(i))

        # Should only keep last 1000
        assert len(monitor.metrics["test_function"]) == 1000
        # Should keep total count
        assert monitor.call_counts["test_function"] == 1500


class TestMonitorPerformanceDecorator:
    """Test performance monitoring decorator"""

    @pytest.mark.asyncio
    async def test_async_function_monitoring(self):
        """Test monitoring async function"""
        monitor = PerformanceMonitor()

        @monitor_performance(name="test_async")
        async def test_function():
            await asyncio.sleep(0.1)
            return "done"

        # Note: In real implementation, this would use perf_monitor global
        result = await test_function()

        assert result == "done"

    def test_sync_function_monitoring(self):
        """Test monitoring sync function"""

        @monitor_performance(name="test_sync")
        def test_function():
            time.sleep(0.01)
            return "done"

        # Note: In real implementation, this would use perf_monitor global
        result = test_function()

        assert result == "done"


class TestTimedLRUCache:
    """Test TTL-based LRU cache"""

    def test_cache_hit(self):
        """Test that cache returns cached value"""
        call_count = 0

        @timed_lru_cache(seconds=60, maxsize=10)
        def expensive_function(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        # First call
        result1 = expensive_function(5)
        # Second call (should hit cache)
        result2 = expensive_function(5)

        assert result1 == 10
        assert result2 == 10
        assert call_count == 1  # Only called once

    def test_cache_expiration(self):
        """Test that cache expires after TTL"""
        call_count = 0

        @timed_lru_cache(seconds=1, maxsize=10)
        def expensive_function(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        # First call
        result1 = expensive_function(5)

        # Wait for expiration
        time.sleep(1.1)

        # Second call (should miss cache)
        result2 = expensive_function(5)

        assert result1 == 10
        assert result2 == 10
        assert call_count == 2  # Called twice


class TestParallelFetch:
    """Test parallel fetching utilities"""

    @pytest.mark.asyncio
    async def test_parallel_fetch_success(self):
        """Test parallel fetching of multiple functions"""

        async def fetch1():
            await asyncio.sleep(0.01)
            return "result1"

        async def fetch2():
            await asyncio.sleep(0.01)
            return "result2"

        async def fetch3():
            await asyncio.sleep(0.01)
            return "result3"

        results = await parallel_fetch([fetch1, fetch2, fetch3])

        assert results == ["result1", "result2", "result3"]

    @pytest.mark.asyncio
    async def test_parallel_fetch_with_exception(self):
        """Test parallel fetching handles exceptions"""

        async def fetch_success():
            return "success"

        async def fetch_error():
            raise ValueError("Test error")

        results = await parallel_fetch([fetch_success, fetch_error])

        assert results[0] == "success"
        assert isinstance(results[1], ValueError)


class TestBatchProcess:
    """Test batch processing with concurrency"""

    @pytest.mark.asyncio
    async def test_batch_process_success(self):
        """Test batch processing items"""

        async def processor(item):
            await asyncio.sleep(0.01)
            return item * 2

        items = [1, 2, 3, 4, 5]
        results = await batch_process(items, processor, batch_size=2, max_concurrent=2)

        assert results == [2, 4, 6, 8, 10]

    @pytest.mark.asyncio
    async def test_batch_process_with_errors(self):
        """Test batch processing handles errors"""

        async def processor(item):
            if item == 3:
                raise ValueError(f"Error processing {item}")
            return item * 2

        items = [1, 2, 3, 4, 5]
        results = await batch_process(items, processor, batch_size=2, max_concurrent=2)

        # Results should include exception for item 3
        assert results[0] == 2
        assert results[1] == 4
        assert isinstance(results[2], ValueError)
        assert results[3] == 8
        assert results[4] == 10


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
