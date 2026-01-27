"""
Polygon.io Data Provider

High-performance data provider using Polygon.io API.
Replaces yfinance for faster, more reliable price data.
"""

import os
import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import pandas as pd

logger = logging.getLogger(__name__)

# API Configuration
POLYGON_API_KEY = os.environ.get('POLYGON_API_KEY', '')
POLYGON_BASE_URL = 'https://api.polygon.io'


class PolygonProvider:
    """
    Async Polygon.io data provider.

    Provides:
    - Historical price data (OHLCV)
    - Real-time quotes
    - Stock details/fundamentals
    - News articles
    - Ticker search
    """

    def __init__(self, api_key: str = None, session: aiohttp.ClientSession = None):
        self.api_key = api_key or POLYGON_API_KEY
        self._session = session
        self._owns_session = session is None

        if not self.api_key:
            logger.warning("POLYGON_API_KEY not set - Polygon provider disabled")

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
            self._owns_session = True
        return self._session

    async def close(self):
        """Close the session if we own it."""
        if self._owns_session and self._session and not self._session.closed:
            await self._session.close()

    async def _request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Make API request to Polygon."""
        if not self.api_key:
            return None

        session = await self._get_session()
        url = f"{POLYGON_BASE_URL}{endpoint}"

        params = params or {}
        params['apiKey'] = self.api_key

        try:
            async with session.get(url, params=params, timeout=10) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 429:
                    logger.warning("Polygon rate limit hit")
                    return None
                else:
                    logger.debug(f"Polygon API error: {response.status}")
                    return None
        except asyncio.TimeoutError:
            logger.debug(f"Polygon request timeout: {endpoint}")
            return None
        except Exception as e:
            logger.debug(f"Polygon request error: {e}")
            return None

    async def get_aggregates(
        self,
        ticker: str,
        multiplier: int = 1,
        timespan: str = 'day',
        from_date: str = None,
        to_date: str = None,
        limit: int = 250,
    ) -> Optional[pd.DataFrame]:
        """
        Get aggregate bars (OHLCV) for a ticker.

        Args:
            ticker: Stock symbol
            multiplier: Size of timespan multiplier
            timespan: 'minute', 'hour', 'day', 'week', 'month', 'quarter', 'year'
            from_date: Start date (YYYY-MM-DD)
            to_date: End date (YYYY-MM-DD)
            limit: Max results

        Returns:
            DataFrame with OHLCV data
        """
        if to_date is None:
            to_date = datetime.now().strftime('%Y-%m-%d')
        if from_date is None:
            from_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')

        endpoint = f"/v2/aggs/ticker/{ticker.upper()}/range/{multiplier}/{timespan}/{from_date}/{to_date}"

        data = await self._request(endpoint, {'limit': limit, 'sort': 'asc'})

        if not data or 'results' not in data:
            return None

        results = data['results']
        if not results:
            return None

        df = pd.DataFrame(results)

        # Rename columns to match yfinance format
        df = df.rename(columns={
            'o': 'Open',
            'h': 'High',
            'l': 'Low',
            'c': 'Close',
            'v': 'Volume',
            'vw': 'VWAP',
            't': 'Timestamp',
            'n': 'Transactions',
        })

        # Convert timestamp to datetime index
        df['Date'] = pd.to_datetime(df['Timestamp'], unit='ms')
        df = df.set_index('Date')

        # Ensure required columns exist
        for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
            if col not in df.columns:
                df[col] = 0

        return df[['Open', 'High', 'Low', 'Close', 'Volume']]

    async def get_daily_bars(
        self,
        ticker: str,
        days: int = 250,
    ) -> Optional[pd.DataFrame]:
        """
        Get daily OHLCV bars for a ticker.

        Args:
            ticker: Stock symbol
            days: Number of days of history

        Returns:
            DataFrame with daily OHLCV
        """
        to_date = datetime.now().strftime('%Y-%m-%d')
        from_date = (datetime.now() - timedelta(days=days + 30)).strftime('%Y-%m-%d')  # Extra buffer for weekends

        return await self.get_aggregates(
            ticker=ticker,
            multiplier=1,
            timespan='day',
            from_date=from_date,
            to_date=to_date,
            limit=days + 50,
        )

    async def get_previous_close(self, ticker: str) -> Optional[Dict]:
        """Get previous day's close data."""
        endpoint = f"/v2/aggs/ticker/{ticker.upper()}/prev"

        data = await self._request(endpoint)

        if data and 'results' in data and data['results']:
            result = data['results'][0]
            return {
                'ticker': ticker.upper(),
                'close': result.get('c'),
                'open': result.get('o'),
                'high': result.get('h'),
                'low': result.get('l'),
                'volume': result.get('v'),
                'vwap': result.get('vw'),
            }
        return None

    async def get_snapshot(self, ticker: str) -> Optional[Dict]:
        """Get current snapshot (quote + day stats)."""
        endpoint = f"/v2/snapshot/locale/us/markets/stocks/tickers/{ticker.upper()}"

        data = await self._request(endpoint)

        if data and 'ticker' in data:
            t = data['ticker']
            return {
                'ticker': t.get('ticker'),
                'price': t.get('day', {}).get('c') or t.get('prevDay', {}).get('c'),
                'change': t.get('todaysChange'),
                'change_percent': t.get('todaysChangePerc'),
                'volume': t.get('day', {}).get('v'),
                'vwap': t.get('day', {}).get('vw'),
                'open': t.get('day', {}).get('o'),
                'high': t.get('day', {}).get('h'),
                'low': t.get('day', {}).get('l'),
                'prev_close': t.get('prevDay', {}).get('c'),
            }
        return None

    async def get_ticker_details(self, ticker: str) -> Optional[Dict]:
        """Get ticker details (sector, industry, market cap, etc.)."""
        endpoint = f"/v3/reference/tickers/{ticker.upper()}"

        data = await self._request(endpoint)

        if data and 'results' in data:
            r = data['results']
            return {
                'ticker': r.get('ticker'),
                'name': r.get('name'),
                'market_cap': r.get('market_cap'),
                'sector': r.get('sic_description', 'Unknown'),
                'industry': r.get('sic_description'),
                'description': r.get('description'),
                'homepage': r.get('homepage_url'),
                'employees': r.get('total_employees'),
                'list_date': r.get('list_date'),
                'type': r.get('type'),
            }
        return None

    async def get_news(
        self,
        ticker: str = None,
        limit: int = 10,
        order: str = 'desc',
    ) -> List[Dict]:
        """
        Get news articles.

        Args:
            ticker: Optional ticker to filter news
            limit: Max articles to return
            order: 'asc' or 'desc' by published date

        Returns:
            List of news articles
        """
        endpoint = "/v2/reference/news"
        params = {'limit': limit, 'order': order}

        if ticker:
            params['ticker'] = ticker.upper()

        data = await self._request(endpoint, params)

        if data and 'results' in data:
            articles = []
            for article in data['results']:
                articles.append({
                    'title': article.get('title'),
                    'summary': article.get('description', ''),
                    'url': article.get('article_url'),
                    'source': article.get('publisher', {}).get('name'),
                    'published': article.get('published_utc'),
                    'tickers': article.get('tickers', []),
                    'keywords': article.get('keywords', []),
                })
            return articles
        return []

    async def get_related_companies(self, ticker: str) -> List[str]:
        """Get related companies/tickers."""
        endpoint = f"/v1/related-companies/{ticker.upper()}"

        data = await self._request(endpoint)

        if data and 'results' in data:
            return [r.get('ticker') for r in data['results'] if r.get('ticker')]
        return []

    async def batch_get_daily_bars(
        self,
        tickers: List[str],
        days: int = 250,
        max_concurrent: int = 10,
    ) -> Dict[str, pd.DataFrame]:
        """
        Batch fetch daily bars for multiple tickers.

        Args:
            tickers: List of symbols
            days: Days of history
            max_concurrent: Max concurrent requests

        Returns:
            Dict mapping ticker -> DataFrame
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        results = {}

        async def fetch_one(ticker: str):
            async with semaphore:
                df = await self.get_daily_bars(ticker, days)
                if df is not None and not df.empty:
                    results[ticker] = df

        await asyncio.gather(*[fetch_one(t) for t in tickers], return_exceptions=True)

        return results


# Singleton instance
_provider = None


def get_polygon_provider() -> PolygonProvider:
    """Get global Polygon provider instance."""
    global _provider
    if _provider is None:
        _provider = PolygonProvider()
    return _provider


async def get_price_data(ticker: str, days: int = 250) -> Optional[pd.DataFrame]:
    """Convenience function to get price data."""
    provider = get_polygon_provider()
    return await provider.get_daily_bars(ticker, days)


async def get_news(ticker: str = None, limit: int = 10) -> List[Dict]:
    """Convenience function to get news."""
    provider = get_polygon_provider()
    return await provider.get_news(ticker, limit)


async def batch_get_prices(tickers: List[str], days: int = 250) -> Dict[str, pd.DataFrame]:
    """Convenience function to batch fetch prices."""
    provider = get_polygon_provider()
    return await provider.batch_get_daily_bars(tickers, days)
