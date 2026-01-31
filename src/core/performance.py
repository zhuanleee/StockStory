"""
Performance Optimization Utilities
===================================

Cache preloading, parallel execution helpers, and performance monitoring.

Author: Stock Scanner Bot
Date: February 1, 2026
"""

import asyncio
import time
from functools import wraps, lru_cache
from typing import Callable, Any, List, Dict
import logging

logger = logging.getLogger(__name__)

# =============================================================================
# CACHE PRELOADING
# =============================================================================

class CachePreloader:
    """Preload hot data on startup to eliminate cold start penalty"""

    def __init__(self):
        self.preload_tasks = []
        self.preloaded = False

    async def preload_hot_data(self):
        """Preload frequently accessed data"""
        if self.preloaded:
            return

        logger.info("Preloading hot data...")
        start_time = time.time()

        # List of hot tickers to preload
        hot_tickers = ['SPY', 'QQQ', 'AAPL', 'MSFT', 'NVDA', 'TSLA', 'GOOGL', 'AMZN', 'META', 'NFLX']

        tasks = []
        for ticker in hot_tickers:
            # Import here to avoid circular dependencies
            try:
                from src.data.polygon_provider import get_ticker_data_async
                tasks.append(get_ticker_data_async(ticker))
            except ImportError:
                logger.warning("Could not import polygon_provider for cache preload")
                break

        if tasks:
            # Run preload tasks in parallel
            results = await asyncio.gather(*tasks, return_exceptions=True)
            successful = sum(1 for r in results if not isinstance(r, Exception))
            logger.info(f"Preloaded {successful}/{len(hot_tickers)} tickers in {time.time() - start_time:.2f}s")

        self.preloaded = True

    def register_preload_task(self, coro):
        """Register a coroutine to run during preload"""
        self.preload_tasks.append(coro)

# Global preloader instance
cache_preloader = CachePreloader()

# =============================================================================
# PARALLEL EXECUTION HELPERS
# =============================================================================

async def gather_with_concurrency(n: int, *tasks):
    """
    Run tasks in parallel with concurrency limit

    Args:
        n: Maximum concurrent tasks
        *tasks: Async tasks to run

    Returns:
        List of results
    """
    semaphore = asyncio.Semaphore(n)

    async def sem_task(task):
        async with semaphore:
            return await task

    return await asyncio.gather(*(sem_task(task) for task in tasks))


async def parallel_fetch(fetchers: List[Callable], *args, **kwargs) -> List[Any]:
    """
    Execute multiple fetch functions in parallel

    Args:
        fetchers: List of async functions to call
        *args, **kwargs: Arguments to pass to each function

    Returns:
        List of results in same order as fetchers

    Example:
        results = await parallel_fetch([
            fetch_news,
            fetch_sentiment,
            fetch_social
        ], ticker='AAPL')
        news, sentiment, social = results
    """
    tasks = [fetcher(*args, **kwargs) for fetcher in fetchers]
    return await asyncio.gather(*tasks, return_exceptions=True)


# =============================================================================
# PERFORMANCE MONITORING
# =============================================================================

class PerformanceMonitor:
    """Monitor function execution times and track metrics"""

    def __init__(self):
        self.metrics = {}
        self.call_counts = {}

    def record(self, name: str, duration: float):
        """Record a performance metric"""
        if name not in self.metrics:
            self.metrics[name] = []
            self.call_counts[name] = 0

        self.metrics[name].append(duration)
        self.call_counts[name] += 1

        # Keep only last 1000 measurements
        if len(self.metrics[name]) > 1000:
            self.metrics[name] = self.metrics[name][-1000:]

    def get_stats(self, name: str) -> Dict[str, float]:
        """Get statistics for a metric"""
        if name not in self.metrics or not self.metrics[name]:
            return {}

        measurements = self.metrics[name]
        return {
            'count': len(measurements),
            'total_calls': self.call_counts.get(name, 0),
            'avg': sum(measurements) / len(measurements),
            'min': min(measurements),
            'max': max(measurements),
            'p50': sorted(measurements)[len(measurements) // 2],
            'p95': sorted(measurements)[int(len(measurements) * 0.95)],
            'p99': sorted(measurements)[int(len(measurements) * 0.99)]
        }

    def get_all_stats(self) -> Dict[str, Dict[str, float]]:
        """Get statistics for all metrics"""
        return {name: self.get_stats(name) for name in self.metrics.keys()}

# Global monitor instance
perf_monitor = PerformanceMonitor()


def monitor_performance(name: str = None):
    """
    Decorator to monitor function performance

    Args:
        name: Metric name (defaults to function name)

    Example:
        @monitor_performance()
        async def fetch_data(ticker):
            ...
    """
    def decorator(func):
        metric_name = name or func.__name__

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                perf_monitor.record(metric_name, duration)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                perf_monitor.record(metric_name, duration)

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator


# =============================================================================
# LAZY LOADING
# =============================================================================

class LazyImport:
    """Lazy import heavy modules only when needed"""

    def __init__(self, module_name: str):
        self.module_name = module_name
        self._module = None

    def __getattr__(self, name):
        if self._module is None:
            self._module = __import__(self.module_name, fromlist=[name])
        return getattr(self._module, name)


# Example usage:
# torch = LazyImport('torch')  # Only imports when actually used
# model = torch.nn.Linear(10, 5)  # Import happens here


# =============================================================================
# CACHING DECORATORS
# =============================================================================

def timed_lru_cache(seconds: int, maxsize: int = 128):
    """
    LRU cache with time-based expiration

    Args:
        seconds: Cache TTL in seconds
        maxsize: Maximum cache size

    Example:
        @timed_lru_cache(seconds=3600, maxsize=1000)
        def expensive_function(param):
            ...
    """
    def decorator(func):
        func = lru_cache(maxsize=maxsize)(func)
        func.lifetime = seconds
        func.expiration = time.time() + seconds

        @wraps(func)
        def wrapped(*args, **kwargs):
            if time.time() >= func.expiration:
                func.cache_clear()
                func.expiration = time.time() + func.lifetime
            return func(*args, **kwargs)

        return wrapped

    return decorator


# =============================================================================
# BATCH PROCESSING
# =============================================================================

async def batch_process(
    items: List[Any],
    processor: Callable,
    batch_size: int = 10,
    max_concurrent: int = 5
) -> List[Any]:
    """
    Process items in batches with concurrency control

    Args:
        items: Items to process
        processor: Async function to process each item
        batch_size: Items per batch
        max_concurrent: Maximum concurrent batches

    Returns:
        List of results

    Example:
        tickers = ['AAPL', 'MSFT', 'GOOGL', ...]
        results = await batch_process(
            tickers,
            fetch_ticker_data,
            batch_size=10,
            max_concurrent=5
        )
    """
    results = []
    semaphore = asyncio.Semaphore(max_concurrent)

    async def process_batch(batch):
        async with semaphore:
            tasks = [processor(item) for item in batch]
            return await asyncio.gather(*tasks, return_exceptions=True)

    # Split into batches
    batches = [items[i:i + batch_size] for i in range(0, len(items), batch_size)]

    # Process all batches
    for batch_results in await asyncio.gather(*[process_batch(b) for b in batches]):
        results.extend(batch_results)

    return results


# =============================================================================
# STARTUP OPTIMIZATION
# =============================================================================

async def optimize_startup():
    """Run all startup optimizations"""
    logger.info("Running startup optimizations...")

    # Preload hot data
    await cache_preloader.preload_hot_data()

    # Run any registered preload tasks
    if cache_preloader.preload_tasks:
        await asyncio.gather(*cache_preloader.preload_tasks, return_exceptions=True)

    logger.info("Startup optimizations complete")


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def log_slow_operations(threshold_seconds: float = 1.0):
    """
    Decorator to log operations that exceed threshold

    Args:
        threshold_seconds: Log if operation takes longer than this

    Example:
        @log_slow_operations(threshold_seconds=2.0)
        async def slow_function():
            ...
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            result = await func(*args, **kwargs)
            duration = time.time() - start_time
            if duration > threshold_seconds:
                logger.warning(f"{func.__name__} took {duration:.2f}s (threshold: {threshold_seconds}s)")
            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            if duration > threshold_seconds:
                logger.warning(f"{func.__name__} took {duration:.2f}s (threshold: {threshold_seconds}s)")
            return result

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator
