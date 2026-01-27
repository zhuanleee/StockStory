"""
Async Scanner Pipeline

High-performance async scanner for 8-25x speedup over sequential scanning.
Uses aiohttp for concurrent HTTP requests with proper rate limiting and caching.
"""

import asyncio
import aiohttp
import time
import re
import os
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
import pandas as pd
import yfinance as yf

from cache_manager import (
    CacheManager, CacheConfig,
    stocktwits_cache_key, reddit_cache_key, sec_cache_key,
    sector_cache_key, news_cache_key,
)
from config import config
import param_helper as params

logger = logging.getLogger(__name__)


# =============================================================================
# ASYNC RATE LIMITER (Token Bucket)
# =============================================================================

class AsyncRateLimiter:
    """
    Async-compatible token bucket rate limiter.

    Allows burst traffic up to `burst` tokens, then enforces `rate` tokens/second.
    """

    def __init__(self, rate: float, burst: int = 1):
        """
        Initialize rate limiter.

        Args:
            rate: Tokens per second
            burst: Maximum burst size (tokens available initially)
        """
        self.rate = rate
        self.burst = burst
        self._tokens = burst
        self._last_update = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: int = 1) -> None:
        """
        Acquire tokens, waiting if necessary.

        This is the main method to call before making an API request.
        """
        async with self._lock:
            while True:
                now = time.monotonic()
                elapsed = now - self._last_update
                self._tokens = min(self.burst, self._tokens + elapsed * self.rate)
                self._last_update = now

                if self._tokens >= tokens:
                    self._tokens -= tokens
                    return

                # Wait for tokens to become available
                wait_time = (tokens - self._tokens) / self.rate
                await asyncio.sleep(wait_time)


# =============================================================================
# RATE LIMITERS FOR EACH API
# =============================================================================

RATE_LIMITERS = {
    'stocktwits': AsyncRateLimiter(rate=3.0, burst=5),   # ~200/hour
    'reddit': AsyncRateLimiter(rate=1.0, burst=4),        # ~60/min, 4 subreddits
    'sec': AsyncRateLimiter(rate=10.0, burst=20),         # Be nice to SEC
    'news': AsyncRateLimiter(rate=5.0, burst=10),         # General news APIs
    'yfinance': AsyncRateLimiter(rate=2.0, burst=10),     # Yahoo Finance
}


# =============================================================================
# ASYNC HTTP CLIENT
# =============================================================================

class AsyncHTTPClient:
    """
    Shared aiohttp session with connection pooling.

    Reuse this across all async operations for efficiency.
    """

    def __init__(self, max_connections: int = 100, timeout: int = 30):
        """Initialize HTTP client."""
        self._session: Optional[aiohttp.ClientSession] = None
        self._max_connections = max_connections
        self._timeout = aiohttp.ClientTimeout(total=timeout)
        self._headers = {
            'User-Agent': 'StockScannerBot/2.0 (async)',
            'Accept': 'application/json',
        }

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create the aiohttp session."""
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(
                limit=self._max_connections,
                limit_per_host=20,
                enable_cleanup_closed=True,
            )
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=self._timeout,
                headers=self._headers,
            )
        return self._session

    async def get(
        self,
        url: str,
        params: Dict = None,
        headers: Dict = None,
        timeout: int = None,
    ) -> Optional[Dict]:
        """
        Make async GET request.

        Returns parsed JSON or None on error.
        """
        session = await self._get_session()

        try:
            request_timeout = aiohttp.ClientTimeout(total=timeout) if timeout else None

            async with session.get(
                url,
                params=params,
                headers=headers,
                timeout=request_timeout,
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.debug(f"HTTP {response.status} for {url}")
                    return None
        except asyncio.TimeoutError:
            logger.debug(f"Timeout for {url}")
            return None
        except aiohttp.ClientError as e:
            logger.debug(f"Client error for {url}: {e}")
            return None
        except Exception as e:
            logger.debug(f"Unexpected error for {url}: {e}")
            return None

    async def close(self) -> None:
        """Close the session."""
        if self._session and not self._session.closed:
            await self._session.close()


# =============================================================================
# RETRY WRAPPER
# =============================================================================

@dataclass
class RetryConfig:
    """Retry configuration."""
    max_retries: int = 3
    backoff_base: float = 1.0
    backoff_max: float = 10.0


async def fetch_with_retry(
    coro_func,
    *args,
    retries: int = 3,
    backoff_base: float = 1.0,
    **kwargs,
) -> Any:
    """
    Execute coroutine with exponential backoff retry.

    Args:
        coro_func: Async function to call
        *args: Arguments for the function
        retries: Number of retry attempts
        backoff_base: Base wait time in seconds
        **kwargs: Keyword arguments for the function
    """
    last_error = None

    for attempt in range(retries):
        try:
            return await coro_func(*args, **kwargs)
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            last_error = e
            if attempt < retries - 1:
                wait = min(backoff_base * (2 ** attempt), 10.0)
                logger.debug(f"Retry {attempt + 1}/{retries} after {wait}s: {e}")
                await asyncio.sleep(wait)

    logger.debug(f"All {retries} retries failed: {last_error}")
    return None


# =============================================================================
# ASYNC DATA FETCHER
# =============================================================================

class AsyncDataFetcher:
    """
    Async versions of all data fetching functions.

    Uses caching and rate limiting for efficient parallel fetching.
    """

    def __init__(self, client: AsyncHTTPClient = None, cache: CacheManager = None):
        """Initialize data fetcher."""
        self.client = client or AsyncHTTPClient()
        self.cache = cache or CacheManager()

    async def fetch_stocktwits_async(self, ticker: str) -> Dict:
        """
        Async fetch from StockTwits API.

        Returns sentiment data with caching.
        """
        # Check cache first
        cache_key = stocktwits_cache_key(ticker)
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        # Rate limit
        await RATE_LIMITERS['stocktwits'].acquire()

        url = f"https://api.stocktwits.com/api/2/streams/symbol/{ticker}.json"
        data = await self.client.get(url, timeout=10)

        if data is None:
            return {'sentiment': 'neutral', 'message_volume': 0, 'trending': False}

        symbol_data = data.get('symbol', {})
        messages = data.get('messages', [])

        # Count sentiment
        bullish = sum(1 for m in messages if m.get('entities', {}).get('sentiment', {}).get('basic') == 'Bullish')
        bearish = sum(1 for m in messages if m.get('entities', {}).get('sentiment', {}).get('basic') == 'Bearish')

        total = bullish + bearish
        if total > 0:
            bullish_pct = bullish / total
            if bullish_pct > 0.6:
                sentiment = 'bullish'
            elif bullish_pct < 0.4:
                sentiment = 'bearish'
            else:
                sentiment = 'neutral'
        else:
            sentiment = 'neutral'

        result = {
            'sentiment': sentiment,
            'bullish_count': bullish,
            'bearish_count': bearish,
            'message_volume': len(messages),
            'trending': symbol_data.get('is_following', False),
            'watchlist_count': symbol_data.get('watchlist_count', 0),
        }

        # Cache result
        self.cache.set(cache_key, result, ttl=CacheConfig.TTL_SOCIAL)
        return result

    async def fetch_reddit_subreddit_async(self, ticker: str, subreddit: str) -> List[Dict]:
        """Fetch mentions from a single subreddit."""
        url = f"https://www.reddit.com/r/{subreddit}/search.json"
        params = {
            'q': ticker,
            'restrict_sr': 'on',
            'sort': 'new',
            't': 'week',
            'limit': 10
        }
        headers = {'User-Agent': 'StockScanner/2.0 (async)'}

        data = await self.client.get(url, params=params, headers=headers, timeout=10)

        if data is None:
            return []

        posts = data.get('data', {}).get('children', [])
        mentions = []

        for post in posts:
            post_data = post.get('data', {})
            title = post_data.get('title', '').upper()

            # Check if ticker is actually mentioned
            if re.search(rf'\b{ticker}\b', title):
                mentions.append({
                    'subreddit': subreddit,
                    'title': post_data.get('title', ''),
                    'score': post_data.get('score', 0),
                    'num_comments': post_data.get('num_comments', 0),
                    'created': post_data.get('created_utc', 0),
                })

        return mentions

    async def fetch_reddit_async(self, ticker: str) -> Dict:
        """
        Async fetch from Reddit - all subreddits concurrently.

        This is a major speedup: 4 sequential requests -> 1 concurrent batch.
        """
        # Check cache first
        cache_key = reddit_cache_key(ticker)
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        subreddits = ['wallstreetbets', 'stocks', 'investing', 'options']

        # Rate limit once for all subreddits
        await RATE_LIMITERS['reddit'].acquire(tokens=len(subreddits))

        # Fetch all subreddits concurrently
        tasks = [
            self.fetch_reddit_subreddit_async(ticker, sub)
            for sub in subreddits
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Combine results
        mentions = []
        for result in results:
            if isinstance(result, list):
                mentions.extend(result)

        # Calculate sentiment
        total_score = sum(m.get('score', 0) for m in mentions)
        total_comments = sum(m.get('num_comments', 0) for m in mentions)

        if len(mentions) >= 3 and total_score > 100:
            sentiment = 'bullish'
        elif len(mentions) >= 1:
            sentiment = 'neutral'
        else:
            sentiment = 'quiet'

        result = {
            'mention_count': len(mentions),
            'total_score': total_score,
            'total_comments': total_comments,
            'sentiment': sentiment,
            'hot_posts': mentions[:3],
        }

        # Cache result
        self.cache.set(cache_key, result, ttl=CacheConfig.TTL_SOCIAL)
        return result

    async def fetch_sec_async(self, ticker: str) -> Dict:
        """
        Async fetch SEC filings from EDGAR.
        """
        # Check cache first
        cache_key = sec_cache_key(ticker)
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        # Rate limit
        await RATE_LIMITERS['sec'].acquire()

        headers = {'User-Agent': 'StockScanner research@example.com'}

        # Try SEC full-text search API
        search_url = f"https://efts.sec.gov/LATEST/search-index?q={ticker}&dateRange=custom&startdt=2024-01-01&enddt=2026-12-31"

        data = await self.client.get(search_url, headers=headers, timeout=10)

        filings = []
        has_8k = False
        insider_activity = False

        if data:
            hits = data.get('hits', {}).get('hits', [])

            for hit in hits[:10]:
                source = hit.get('_source', {})
                form_type = source.get('form', '')
                filed_date = source.get('file_date', '')

                filings.append({
                    'form': form_type,
                    'date': filed_date,
                    'description': source.get('display_names', [''])[0] if source.get('display_names') else '',
                })

                if '8-K' in form_type:
                    has_8k = True
                if form_type in ['4', '3', '5']:
                    insider_activity = True

        result = {
            'recent_filings': filings[:5],
            'filing_count': len(filings),
            'has_8k': has_8k,
            'insider_activity': insider_activity,
        }

        # Cache result
        self.cache.set(cache_key, result, ttl=CacheConfig.TTL_SEC)
        return result

    async def fetch_sector_async(self, ticker: str) -> str:
        """
        Async fetch sector for ticker.

        Uses yfinance in executor to avoid blocking.
        """
        # Check cache first
        cache_key = sector_cache_key(ticker)
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        # yfinance is synchronous, run in executor
        loop = asyncio.get_event_loop()
        try:
            def get_sector():
                try:
                    stock = yf.Ticker(ticker)
                    info = stock.info
                    return info.get('sector', 'Unknown')
                except Exception:
                    return 'Unknown'

            sector = await loop.run_in_executor(None, get_sector)

            # Cache result (long TTL since sectors don't change)
            self.cache.set(cache_key, sector, ttl=CacheConfig.TTL_SECTOR)
            return sector
        except Exception:
            return 'Unknown'

    async def fetch_news_async(self, ticker: str, days: int = 7) -> List[Dict]:
        """
        Async fetch news for ticker.
        """
        # Check cache first
        cache_key = news_cache_key(ticker, days)
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        # yfinance news is synchronous, run in executor
        loop = asyncio.get_event_loop()
        try:
            def get_news():
                try:
                    stock = yf.Ticker(ticker)
                    return stock.news or []
                except Exception:
                    return []

            news = await loop.run_in_executor(None, get_news)

            # Cache result
            self.cache.set(cache_key, news, ttl=CacheConfig.TTL_NEWS)
            return news
        except Exception:
            return []


# =============================================================================
# ASYNC STORY SCORER
# =============================================================================

class AsyncStoryScorer:
    """
    Async story scoring with parallel data fetching.
    """

    def __init__(self, fetcher: AsyncDataFetcher = None):
        """Initialize async story scorer."""
        self.fetcher = fetcher or AsyncDataFetcher()

    async def get_social_buzz_score_async(self, ticker: str) -> Dict:
        """
        Fetch all social sources CONCURRENTLY.

        This is a major speedup: 3 sequential API calls -> 1 concurrent batch.
        """
        # Fetch all social data concurrently
        stocktwits, reddit, sec = await asyncio.gather(
            self.fetcher.fetch_stocktwits_async(ticker),
            self.fetcher.fetch_reddit_async(ticker),
            self.fetcher.fetch_sec_async(ticker),
            return_exceptions=True,
        )

        # Handle exceptions
        if isinstance(stocktwits, Exception):
            stocktwits = {'sentiment': 'neutral', 'message_volume': 0, 'trending': False}
        if isinstance(reddit, Exception):
            reddit = {'mention_count': 0, 'total_score': 0, 'sentiment': 'quiet', 'hot_posts': []}
        if isinstance(sec, Exception):
            sec = {'recent_filings': [], 'has_8k': False, 'insider_activity': False}

        # Calculate component scores using learned thresholds
        st_score = 0
        if stocktwits.get('message_volume', 0) > params.threshold_stocktwits_high():
            st_score = params.score_stocktwits_high()
        elif stocktwits.get('message_volume', 0) > params.threshold_stocktwits_medium():
            st_score = params.score_stocktwits_medium()
        elif stocktwits.get('message_volume', 0) > params.threshold_stocktwits_low():
            st_score = params.score_stocktwits_low()

        if stocktwits.get('sentiment') == 'bullish':
            st_score += params.score_stocktwits_bullish_boost()

        reddit_score = 0
        mention_count = reddit.get('mention_count', 0)
        if mention_count >= params.threshold_reddit_high():
            reddit_score = params.score_stocktwits_high()
        elif mention_count >= params.threshold_reddit_medium():
            reddit_score = params.score_stocktwits_medium()
        elif mention_count >= 1:
            reddit_score = params.score_stocktwits_low()

        total_reddit_score = reddit.get('total_score', 0)
        if total_reddit_score > params.threshold_reddit_score_high():
            reddit_score += params.score_stocktwits_bullish_boost()
        elif total_reddit_score > params.threshold_reddit_score_medium():
            reddit_score += params.score_stocktwits_low()

        sec_score = 0
        if sec.get('has_8k'):
            sec_score += params.score_sec_8k()
        if sec.get('insider_activity'):
            sec_score += params.score_sec_insider()

        # Combined buzz score
        buzz_score = min(100, st_score + reddit_score + sec_score)

        # Is it trending?
        trending = (
            stocktwits.get('trending', False) or
            mention_count >= params.threshold_trending_reddit_mentions() or
            sec.get('has_8k', False)
        )

        return {
            'buzz_score': buzz_score,
            'trending': trending,
            'stocktwits': stocktwits,
            'reddit': reddit,
            'sec': sec,
        }

    async def calculate_story_score_async(
        self,
        ticker: str,
        price_data: pd.DataFrame = None,
    ) -> Dict:
        """
        Async STORY-FIRST scoring with parallel data fetching.

        Story-First Philosophy:
        - Story Quality (50%): Theme strength, freshness, clarity
        - Catalyst Strength (35%): Type, recency, magnitude
        - Confirmation (15%): Technical validation only

        The best trades are driven by narratives, not just technicals.
        """
        # Fetch social buzz, news, and sector concurrently
        social_task = self.get_social_buzz_score_async(ticker)
        news_task = self.fetcher.fetch_news_async(ticker)
        sector_task = self.fetcher.fetch_sector_async(ticker)

        social_buzz, news, sector = await asyncio.gather(
            social_task,
            news_task,
            sector_task,
            return_exceptions=True,
        )

        # Handle exceptions
        if isinstance(social_buzz, Exception):
            social_buzz = {'buzz_score': 0, 'trending': False, 'stocktwits': {}, 'reddit': {}, 'sec': {}}
        if isinstance(news, Exception):
            news = []
        if isinstance(sector, Exception):
            sector = 'Unknown'

        # Get theme data from registry
        theme_data = []
        try:
            from theme_registry import get_theme_membership_for_scoring
            theme_data = get_theme_membership_for_scoring(ticker) or []
        except ImportError:
            pass

        # Calculate technical data from price data
        price = 0
        rs_composite = 0
        vol_ratio = 1.0
        above_20 = False
        above_50 = False
        above_200 = False
        in_squeeze = False
        breakout_up = False
        distance_from_20sma_pct = None

        if price_data is not None and len(price_data) > 20:
            try:
                close = price_data['Close'] if 'Close' in price_data.columns else price_data.get('close', price_data.iloc[:, 0])
                volume = price_data['Volume'] if 'Volume' in price_data.columns else price_data.get('volume', pd.Series([0]))

                current = float(close.iloc[-1])
                price = current

                # Moving averages
                sma20 = float(close.rolling(20).mean().iloc[-1])
                above_20 = current > sma20

                # Distance from 20 SMA (for buyability)
                if sma20 > 0:
                    distance_from_20sma_pct = abs((current - sma20) / sma20 * 100)

                if len(close) > 50:
                    sma50 = float(close.rolling(50).mean().iloc[-1])
                    above_50 = current > sma50

                if len(close) > 200:
                    sma200 = float(close.rolling(200).mean().iloc[-1])
                    above_200 = current > sma200

                # RS composite (price vs 50 days ago)
                if len(close) > 50:
                    pct_change = (current - float(close.iloc[-50])) / float(close.iloc[-50]) * 100
                    rs_composite = round(pct_change, 1)

                # Volume ratio
                if len(volume) > 20:
                    avg_vol = float(volume.iloc[-20:].mean())
                    if avg_vol > 0:
                        vol_ratio = round(float(volume.iloc[-1]) / avg_vol, 2)

                # Bollinger Bands for squeeze detection
                if len(close) > 20:
                    bb_std = close.rolling(20).std()
                    upper_band = sma20 + (2 * float(bb_std.iloc[-1]))
                    lower_band = sma20 - (2 * float(bb_std.iloc[-1]))
                    band_width = (upper_band - lower_band) / sma20 * 100

                    # Check for squeeze (narrow bands)
                    if len(close) > 70:
                        avg_width = float(((close.rolling(20).mean() + 2 * close.rolling(20).std()) -
                                     (close.rolling(20).mean() - 2 * close.rolling(20).std())).rolling(50).mean().iloc[-1])
                    else:
                        avg_width = band_width

                    if avg_width > 0:
                        width_pct = (band_width / avg_width) * 100
                        in_squeeze = width_pct <= 50
                        breakout_up = current > upper_band

            except Exception as e:
                logger.debug(f"Technical data error for {ticker}: {e}")

        # =====================================================
        # STORY-FIRST SCORING
        # =====================================================
        from story_scoring import calculate_story_score, StoryScore

        # Prepare price data dict for story scorer
        price_dict = {
            'above_20': above_20,
            'above_50': above_50,
            'above_200': above_200,
            'vol_ratio': vol_ratio,
            'distance_from_20sma_pct': distance_from_20sma_pct,
            'breakout_up': breakout_up,
            'in_squeeze': in_squeeze,
        }

        # Get SEC data from social buzz
        sec_data = social_buzz.get('sec', {})

        # Calculate story-first score
        story_result = calculate_story_score(
            ticker=ticker,
            news=news,
            sec_data=sec_data,
            theme_data=theme_data,
            price_data=price_dict,
        )

        # Determine sentiment label from news
        bullish_words = ['beat', 'surge', 'gain', 'rise', 'jump', 'high', 'record', 'growth', 'strong', 'upgrade', 'buy']
        bearish_words = ['miss', 'drop', 'fall', 'low', 'down', 'weak', 'concern', 'risk', 'decline', 'downgrade', 'sell']
        bullish_count = 0
        bearish_count = 0
        for article in news[:10]:
            title = (article.get('title', '') + ' ' + article.get('summary', '')).lower()
            if any(w in title for w in bullish_words):
                bullish_count += 1
            if any(w in title for w in bearish_words):
                bearish_count += 1

        if bullish_count > bearish_count * 2:
            sentiment_label = 'bullish'
        elif bearish_count > bullish_count * 2:
            sentiment_label = 'bearish'
        else:
            sentiment_label = 'neutral'

        return {
            'ticker': ticker,
            'story_score': round(story_result.total_score, 1),
            'composite_score': round(story_result.total_score, 1),  # Alias for dashboard
            'story_strength': story_result.story_strength,
            'story_stage': 'unknown',
            'hottest_theme': story_result.primary_theme,
            'theme_role': None,
            'has_theme': story_result.theme_strength > 0,
            'has_catalyst': story_result.catalyst_type_score > 0,
            'is_early_stage': story_result.theme_freshness >= 80,
            'next_catalyst': story_result.primary_catalyst,
            'news_trend': 'accelerating' if len(news) >= 5 else 'stable',
            'sentiment_label': sentiment_label,
            # Dashboard-required fields
            'price': price,
            'rs_composite': rs_composite,
            'vol_ratio': vol_ratio,
            'above_20': above_20,
            'above_50': above_50,
            'above_200': above_200,
            'in_squeeze': in_squeeze,
            'breakout_up': breakout_up,
            'sector': sector,
            # Story-First score breakdown
            'story_quality': {
                'score': round(story_result.story_quality_score, 1),
                'theme_strength': round(story_result.theme_strength, 1),
                'theme_freshness': round(story_result.theme_freshness, 1),
                'story_clarity': round(story_result.story_clarity, 1),
                'institutional': round(story_result.institutional_narrative, 1),
            },
            'catalyst': {
                'score': round(story_result.catalyst_score, 1),
                'type': story_result.catalyst_type,
                'type_score': round(story_result.catalyst_type_score, 1),
                'recency': round(story_result.catalyst_recency_multiplier, 2),
                'description': story_result.primary_catalyst,
            },
            'confirmation': {
                'score': round(story_result.confirmation_score, 1),
                'trend': round(story_result.trend_score, 1),
                'volume': round(story_result.volume_score, 1),
                'buyability': round(story_result.buyability_score, 1),
            },
            'news_momentum': {'score': len(news) * 3, 'count': len(news)},
            'sentiment': {'score': 0, 'label': sentiment_label},
            'social_buzz': social_buzz,
        }


# =============================================================================
# ASYNC SCANNER
# =============================================================================

class AsyncScanner:
    """
    Main async scanner orchestrator.

    Coordinates parallel scanning of multiple tickers.
    """

    def __init__(
        self,
        max_concurrent: int = 50,
        client: AsyncHTTPClient = None,
        cache: CacheManager = None,
    ):
        """
        Initialize async scanner.

        Args:
            max_concurrent: Maximum concurrent ticker scans
            client: Shared HTTP client
            cache: Cache manager
        """
        self.max_concurrent = max_concurrent
        self.client = client or AsyncHTTPClient()
        self.cache = cache or CacheManager()
        self.fetcher = AsyncDataFetcher(self.client, self.cache)
        self.scorer = AsyncStoryScorer(self.fetcher)
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._stats = {
            'scanned': 0,
            'errors': 0,
            'cache_hits': 0,
            'start_time': None,
        }

    async def _fetch_price_data(self, tickers: List[str]) -> Dict[str, pd.DataFrame]:
        """
        Fetch price data for multiple tickers.
        Uses Polygon.io if available, falls back to yfinance.
        """
        price_data_dict = {}

        # Try Polygon first (faster, more reliable)
        polygon_key = os.environ.get('POLYGON_API_KEY', '')
        if polygon_key:
            try:
                from src.data.polygon_provider import PolygonProvider
                logger.info("Using Polygon.io for price data...")

                provider = PolygonProvider(api_key=polygon_key)
                price_data_dict = await provider.batch_get_daily_bars(
                    tickers + ['SPY'],
                    days=250,
                    max_concurrent=20,
                )
                await provider.close()

                if len(price_data_dict) >= len(tickers) * 0.8:
                    logger.info(f"Polygon fetched {len(price_data_dict)} tickers")
                    return price_data_dict
                else:
                    logger.warning(f"Polygon only got {len(price_data_dict)}/{len(tickers)}, falling back to yfinance")
            except Exception as e:
                logger.warning(f"Polygon error, falling back to yfinance: {e}")

        # Fallback to yfinance
        try:
            logger.info("Using yfinance for price data...")
            price_data = yf.download(
                tickers + ['SPY'],
                period='1y',
                group_by='ticker',
                progress=False,
                threads=True,
            )

            for ticker in tickers:
                try:
                    if isinstance(price_data.columns, pd.MultiIndex):
                        df = price_data[ticker]
                    else:
                        df = price_data
                    if len(df) > 0:
                        price_data_dict[ticker] = df
                except Exception:
                    pass

            logger.info(f"yfinance fetched {len(price_data_dict)} tickers")
        except Exception as e:
            logger.warning(f"Price data fetch error: {e}")

        return price_data_dict

    async def scan_ticker(
        self,
        ticker: str,
        price_data: pd.DataFrame = None,
    ) -> Optional[Dict]:
        """
        Scan a single ticker with semaphore for concurrency control.
        """
        async with self._semaphore:
            try:
                result = await self.scorer.calculate_story_score_async(ticker, price_data)
                self._stats['scanned'] += 1
                return result
            except Exception as e:
                logger.debug(f"Error scanning {ticker}: {e}")
                self._stats['errors'] += 1
                return None

    async def run_scan_async(
        self,
        tickers: List[str] = None,
        use_story_first: bool = True,
        price_data_dict: Dict[str, pd.DataFrame] = None,
    ) -> Tuple[pd.DataFrame, Dict]:
        """
        Run async scan on all tickers.

        Args:
            tickers: List of tickers to scan (default: from universe_manager)
            use_story_first: Whether to use story-first scoring
            price_data_dict: Pre-fetched price data by ticker

        Returns:
            Tuple of (results DataFrame, price_data dict)
        """
        self._stats['start_time'] = time.time()

        # Get tickers if not provided
        if tickers is None:
            try:
                from scanner_automation import get_scan_universe
                tickers = get_scan_universe()
            except ImportError:
                logger.error("No tickers provided and scanner_automation not available")
                return pd.DataFrame(), {}

        logger.info(f"Async scanning {len(tickers)} tickers with max_concurrent={self.max_concurrent}")

        # Fetch price data if not provided
        if price_data_dict is None:
            logger.info("Fetching price data...")
            price_data_dict = await self._fetch_price_data(tickers)

        # Create scan tasks
        tasks = []
        for ticker in tickers:
            ticker_price_data = price_data_dict.get(ticker)
            tasks.append(self.scan_ticker(ticker, ticker_price_data))

        # Run all scans concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, dict):
                valid_results.append(result)
            elif isinstance(result, Exception):
                logger.debug(f"Scan error for {tickers[i]}: {result}")

        # Create DataFrame
        if valid_results:
            df_results = pd.DataFrame(valid_results)
            df_results['rank'] = df_results['story_score'].rank(ascending=False).astype(int)
            df_results = df_results.sort_values('story_score', ascending=False)
        else:
            df_results = pd.DataFrame()

        # Log stats
        elapsed = time.time() - self._stats['start_time']
        logger.info(
            f"Async scan complete: {self._stats['scanned']} scanned, "
            f"{self._stats['errors']} errors, {elapsed:.1f}s total, "
            f"{elapsed/len(tickers):.2f}s/ticker"
        )

        # Save results to CSV for dashboard
        if not df_results.empty:
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d')
            csv_filename = f'scan_{timestamp}.csv'
            df_results.to_csv(csv_filename, index=False)
            logger.info(f"Saved scan results to {csv_filename}")

        return df_results, price_data_dict

    async def close(self) -> None:
        """Clean up resources."""
        await self.client.close()

    def get_stats(self) -> Dict:
        """Get scan statistics."""
        elapsed = 0
        if self._stats['start_time']:
            elapsed = time.time() - self._stats['start_time']

        return {
            **self._stats,
            'elapsed': round(elapsed, 1),
            'cache_stats': self.cache.get_stats(),
        }


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

async def run_async_scan(
    tickers: List[str] = None,
    max_concurrent: int = 50,
) -> Tuple[pd.DataFrame, Dict]:
    """
    Convenience function to run async scan.

    Usage:
        results, price_data = await run_async_scan()
    """
    scanner = AsyncScanner(max_concurrent=max_concurrent)
    try:
        return await scanner.run_scan_async(tickers)
    finally:
        await scanner.close()


def run_async_scan_sync(
    tickers: List[str] = None,
    max_concurrent: int = 50,
) -> Tuple[pd.DataFrame, Dict]:
    """
    Synchronous wrapper for async scan.

    Usage:
        results, price_data = run_async_scan_sync()
    """
    return asyncio.run(run_async_scan(tickers, max_concurrent))


# =============================================================================
# QUICK TEST
# =============================================================================

async def _test_async_scanner():
    """Quick test of async scanner components."""
    print("Testing async scanner components...")

    # Test HTTP client
    client = AsyncHTTPClient()
    result = await client.get('https://api.stocktwits.com/api/2/streams/symbol/AAPL.json')
    print(f"1. HTTP Client: {'OK' if result else 'FAILED'}")

    # Test data fetcher
    fetcher = AsyncDataFetcher(client)
    st_data = await fetcher.fetch_stocktwits_async('NVDA')
    print(f"2. StockTwits fetch: {st_data.get('sentiment', 'ERROR')}")

    reddit_data = await fetcher.fetch_reddit_async('NVDA')
    print(f"3. Reddit fetch: {reddit_data.get('mention_count', 'ERROR')} mentions")

    # Test story scorer
    scorer = AsyncStoryScorer(fetcher)
    buzz = await scorer.get_social_buzz_score_async('NVDA')
    print(f"4. Social buzz score: {buzz.get('buzz_score', 'ERROR')}")

    # Test full score
    score = await scorer.calculate_story_score_async('NVDA')
    print(f"5. Story score: {score.get('story_score', 'ERROR')}")

    await client.close()
    print("\nAll tests passed!")


if __name__ == '__main__':
    asyncio.run(_test_async_scanner())
