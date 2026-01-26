"""
File-based caching system for async scanner.

Provides TTL-based caching with automatic expiration and background pre-fetching.
"""

import json
import os
import time
import hashlib
import logging
import asyncio
from dataclasses import dataclass, asdict
from typing import Any, Optional, List
from pathlib import Path
import fnmatch

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

class CacheConfig:
    """Cache configuration constants."""
    CACHE_DIR = "cache_data"

    # TTL values in seconds
    TTL_PRICE = 300         # 5 minutes - price data changes frequently
    TTL_NEWS = 900          # 15 minutes - news updates periodically
    TTL_SOCIAL = 1800       # 30 minutes - social sentiment is semi-stable
    TTL_SEC = 1800          # 30 minutes - SEC filings don't change often
    TTL_SECTOR = 86400      # 24 hours - sector info is very stable
    TTL_DEFAULT = 600       # 10 minutes - default TTL

    # Cleanup settings
    CLEANUP_INTERVAL = 3600  # 1 hour between cleanup runs
    MAX_CACHE_SIZE_MB = 500  # Maximum cache directory size


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class CacheEntry:
    """A single cache entry with metadata."""
    data: Any
    timestamp: float
    ttl: int
    key: str

    def is_expired(self) -> bool:
        """Check if this entry has expired."""
        return time.time() > (self.timestamp + self.ttl)

    def remaining_ttl(self) -> float:
        """Get remaining TTL in seconds."""
        remaining = (self.timestamp + self.ttl) - time.time()
        return max(0, remaining)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'data': self.data,
            'timestamp': self.timestamp,
            'ttl': self.ttl,
            'key': self.key,
        }

    @classmethod
    def from_dict(cls, d: dict) -> 'CacheEntry':
        """Create from dictionary."""
        return cls(
            data=d['data'],
            timestamp=d['timestamp'],
            ttl=d['ttl'],
            key=d['key'],
        )


# =============================================================================
# CACHE MANAGER
# =============================================================================

class CacheManager:
    """
    File-based cache with TTL expiration.

    Uses JSON files stored in a directory structure:
    cache_data/
      ab/
        abcd1234.json  (hash-based filename)
    """

    def __init__(self, cache_dir: str = None):
        """Initialize cache manager."""
        self.cache_dir = Path(cache_dir or CacheConfig.CACHE_DIR)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'expired': 0,
        }
        self._last_cleanup = 0

    def _key_to_path(self, key: str) -> Path:
        """Convert cache key to file path."""
        # Hash the key for filesystem-safe filename
        key_hash = hashlib.md5(key.encode()).hexdigest()
        # Use first 2 chars as subdirectory for better distribution
        subdir = self.cache_dir / key_hash[:2]
        subdir.mkdir(exist_ok=True)
        return subdir / f"{key_hash}.json"

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Returns None if key doesn't exist or is expired.
        """
        path = self._key_to_path(key)

        if not path.exists():
            self._stats['misses'] += 1
            return None

        try:
            with open(path, 'r') as f:
                entry_dict = json.load(f)

            entry = CacheEntry.from_dict(entry_dict)

            if entry.is_expired():
                self._stats['expired'] += 1
                self._stats['misses'] += 1
                # Clean up expired entry
                path.unlink(missing_ok=True)
                return None

            self._stats['hits'] += 1
            return entry.data

        except (json.JSONDecodeError, KeyError, IOError) as e:
            logger.debug(f"Cache read error for {key}: {e}")
            self._stats['misses'] += 1
            return None

    def set(self, key: str, data: Any, ttl: int = None) -> None:
        """
        Set value in cache with TTL.

        Args:
            key: Cache key
            data: Data to cache (must be JSON-serializable)
            ttl: Time-to-live in seconds (default: CacheConfig.TTL_DEFAULT)
        """
        if ttl is None:
            ttl = CacheConfig.TTL_DEFAULT

        entry = CacheEntry(
            data=data,
            timestamp=time.time(),
            ttl=ttl,
            key=key,
        )

        path = self._key_to_path(key)

        try:
            with open(path, 'w') as f:
                json.dump(entry.to_dict(), f)
            self._stats['sets'] += 1
        except (IOError, TypeError) as e:
            logger.warning(f"Cache write error for {key}: {e}")

    def delete(self, key: str) -> bool:
        """Delete a specific cache entry."""
        path = self._key_to_path(key)
        if path.exists():
            path.unlink()
            return True
        return False

    def invalidate(self, pattern: str) -> int:
        """
        Invalidate all cache entries matching a pattern.

        Uses glob-style pattern matching on keys.
        Returns number of entries invalidated.
        """
        count = 0

        # We need to scan all files since keys are hashed
        for subdir in self.cache_dir.iterdir():
            if not subdir.is_dir():
                continue
            for cache_file in subdir.glob("*.json"):
                try:
                    with open(cache_file, 'r') as f:
                        entry_dict = json.load(f)
                    if fnmatch.fnmatch(entry_dict.get('key', ''), pattern):
                        cache_file.unlink()
                        count += 1
                except (json.JSONDecodeError, IOError):
                    pass

        logger.info(f"Invalidated {count} cache entries matching '{pattern}'")
        return count

    def clear_expired(self) -> int:
        """
        Remove all expired cache entries.

        Returns number of entries removed.
        """
        count = 0
        current_time = time.time()

        for subdir in self.cache_dir.iterdir():
            if not subdir.is_dir():
                continue
            for cache_file in subdir.glob("*.json"):
                try:
                    with open(cache_file, 'r') as f:
                        entry_dict = json.load(f)

                    entry = CacheEntry.from_dict(entry_dict)
                    if entry.is_expired():
                        cache_file.unlink()
                        count += 1
                except (json.JSONDecodeError, IOError, KeyError):
                    # Corrupted file, remove it
                    cache_file.unlink(missing_ok=True)
                    count += 1

        self._stats['expired'] += count
        logger.info(f"Cleared {count} expired cache entries")
        return count

    def clear_all(self) -> int:
        """Clear entire cache. Returns number of entries removed."""
        count = 0
        for subdir in self.cache_dir.iterdir():
            if not subdir.is_dir():
                continue
            for cache_file in subdir.glob("*.json"):
                cache_file.unlink()
                count += 1
        logger.info(f"Cleared all {count} cache entries")
        return count

    def get_stats(self) -> dict:
        """Get cache statistics."""
        total = self._stats['hits'] + self._stats['misses']
        hit_rate = (self._stats['hits'] / total * 100) if total > 0 else 0

        # Count current entries
        entry_count = 0
        total_size = 0
        for subdir in self.cache_dir.iterdir():
            if not subdir.is_dir():
                continue
            for cache_file in subdir.glob("*.json"):
                entry_count += 1
                total_size += cache_file.stat().st_size

        return {
            **self._stats,
            'hit_rate': round(hit_rate, 1),
            'entry_count': entry_count,
            'total_size_mb': round(total_size / 1024 / 1024, 2),
        }

    def maybe_cleanup(self) -> None:
        """Run cleanup if enough time has passed since last cleanup."""
        if time.time() - self._last_cleanup > CacheConfig.CLEANUP_INTERVAL:
            self.clear_expired()
            self._last_cleanup = time.time()


# =============================================================================
# BACKGROUND PREFETCHER
# =============================================================================

class BackgroundPrefetcher:
    """
    Pre-fetch data for upcoming scans to warm the cache.

    This runs in the background to prepare data before scheduled scans.
    """

    def __init__(self, cache: CacheManager = None):
        """Initialize prefetcher."""
        self.cache = cache or CacheManager()
        self._running = False
        self._prefetch_task = None

    async def prefetch_universe(self, tickers: List[str], fetch_func=None) -> dict:
        """
        Pre-fetch data for a list of tickers.

        Args:
            tickers: List of ticker symbols
            fetch_func: Async function to fetch data for a ticker

        Returns:
            Dict with prefetch statistics
        """
        if fetch_func is None:
            logger.warning("No fetch function provided for prefetch")
            return {'prefetched': 0, 'errors': 0}

        self._running = True
        prefetched = 0
        errors = 0

        for ticker in tickers:
            if not self._running:
                break

            try:
                # Check if already cached
                cache_key = f"prefetch:{ticker}"
                if self.cache.get(cache_key) is not None:
                    continue

                # Fetch and cache
                data = await fetch_func(ticker)
                if data:
                    self.cache.set(cache_key, data, ttl=CacheConfig.TTL_SOCIAL)
                    prefetched += 1

                # Small delay to avoid overwhelming APIs
                await asyncio.sleep(0.1)

            except Exception as e:
                logger.debug(f"Prefetch error for {ticker}: {e}")
                errors += 1

        self._running = False
        return {
            'prefetched': prefetched,
            'errors': errors,
            'total': len(tickers),
        }

    async def warm_cache(self, tickers: List[str] = None) -> dict:
        """
        Warm cache with commonly accessed data.

        This is called before scheduled scans to prepare data.
        """
        if tickers is None:
            # Get from universe manager if available
            try:
                from universe_manager import get_manager
                manager = get_manager()
                tickers = manager.get_scan_universe()[:100]  # Top 100
            except ImportError:
                tickers = []

        logger.info(f"Warming cache for {len(tickers)} tickers")

        # For now, just ensure cache directory exists and is clean
        self.cache.clear_expired()

        return {
            'tickers': len(tickers),
            'cache_stats': self.cache.get_stats(),
        }

    def stop(self) -> None:
        """Stop any running prefetch operation."""
        self._running = False


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

# Global cache instance
_cache_instance = None


def get_cache() -> CacheManager:
    """Get the global cache manager instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = CacheManager()
    return _cache_instance


def cache_get(key: str) -> Optional[Any]:
    """Shorthand for getting from global cache."""
    return get_cache().get(key)


def cache_set(key: str, data: Any, ttl: int = None) -> None:
    """Shorthand for setting in global cache."""
    get_cache().set(key, data, ttl)


# =============================================================================
# CACHE KEY BUILDERS
# =============================================================================

def make_cache_key(category: str, ticker: str, extra: str = None) -> str:
    """
    Build a consistent cache key.

    Format: {category}:{ticker}:{extra}
    Examples:
        social:stocktwits:NVDA
        price:daily:AAPL
        news:7d:MSFT
    """
    parts = [category, ticker.upper()]
    if extra:
        parts.append(extra)
    return ':'.join(parts)


# Pre-defined key builders for common use cases
def price_cache_key(ticker: str) -> str:
    return make_cache_key('price', ticker, 'daily')

def news_cache_key(ticker: str, days: int = 7) -> str:
    return make_cache_key('news', ticker, f'{days}d')

def stocktwits_cache_key(ticker: str) -> str:
    return make_cache_key('social', ticker, 'stocktwits')

def reddit_cache_key(ticker: str) -> str:
    return make_cache_key('social', ticker, 'reddit')

def sec_cache_key(ticker: str) -> str:
    return make_cache_key('sec', ticker, 'filings')

def sector_cache_key(ticker: str) -> str:
    return make_cache_key('meta', ticker, 'sector')
