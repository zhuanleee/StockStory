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

    async def get_market_movers(self, direction: str = 'gainers') -> List[Dict]:
        """
        Get market movers (gainers or losers).

        Args:
            direction: 'gainers' or 'losers'

        Returns:
            List of top movers with price data
        """
        endpoint = f"/v2/snapshot/locale/us/markets/stocks/{direction}"

        data = await self._request(endpoint)

        if data and 'tickers' in data:
            movers = []
            for t in data['tickers'][:20]:  # Top 20
                movers.append({
                    'ticker': t.get('ticker'),
                    'price': t.get('day', {}).get('c'),
                    'change': t.get('todaysChange'),
                    'change_percent': t.get('todaysChangePerc'),
                    'volume': t.get('day', {}).get('v'),
                    'prev_close': t.get('prevDay', {}).get('c'),
                })
            return movers
        return []

    async def get_all_snapshots(self, tickers: List[str] = None) -> Dict[str, Dict]:
        """
        Get snapshots for all tickers or specific list.

        Args:
            tickers: Optional list of tickers (if None, gets all)

        Returns:
            Dict mapping ticker -> snapshot data
        """
        if tickers:
            # Fetch individual snapshots for specific tickers
            endpoint = "/v2/snapshot/locale/us/markets/stocks/tickers"
            params = {'tickers': ','.join(t.upper() for t in tickers[:50])}  # Max 50
        else:
            endpoint = "/v2/snapshot/locale/us/markets/stocks/tickers"
            params = {}

        data = await self._request(endpoint, params)

        snapshots = {}
        if data and 'tickers' in data:
            for t in data['tickers']:
                ticker = t.get('ticker')
                if ticker:
                    snapshots[ticker] = {
                        'ticker': ticker,
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
        return snapshots

    async def batch_get_ticker_details(
        self,
        tickers: List[str],
        max_concurrent: int = 10,
    ) -> Dict[str, Dict]:
        """
        Batch fetch ticker details for multiple tickers.

        Args:
            tickers: List of symbols
            max_concurrent: Max concurrent requests

        Returns:
            Dict mapping ticker -> details
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        results = {}

        async def fetch_one(ticker: str):
            async with semaphore:
                details = await self.get_ticker_details(ticker)
                if details:
                    results[ticker] = details

        await asyncio.gather(*[fetch_one(t) for t in tickers], return_exceptions=True)

        return results

    async def batch_get_news(
        self,
        tickers: List[str],
        limit_per_ticker: int = 5,
        max_concurrent: int = 10,
    ) -> Dict[str, List[Dict]]:
        """
        Batch fetch news for multiple tickers.

        Args:
            tickers: List of symbols
            limit_per_ticker: Max articles per ticker
            max_concurrent: Max concurrent requests

        Returns:
            Dict mapping ticker -> list of articles
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        results = {}

        async def fetch_one(ticker: str):
            async with semaphore:
                news = await self.get_news(ticker, limit=limit_per_ticker)
                if news:
                    results[ticker] = news

        await asyncio.gather(*[fetch_one(t) for t in tickers], return_exceptions=True)

        return results

    async def get_market_status(self) -> Dict:
        """Get current market status (open/closed)."""
        endpoint = "/v1/marketstatus/now"

        data = await self._request(endpoint)

        if data:
            return {
                'market': data.get('market', 'unknown'),
                'exchanges': data.get('exchanges', {}),
                'server_time': data.get('serverTime'),
                'after_hours': data.get('afterHours', False),
                'early_hours': data.get('earlyHours', False),
            }
        return {'market': 'unknown'}

    # =========================================================================
    # OPTIONS DATA
    # =========================================================================

    async def get_options_chain(
        self,
        underlying: str,
        expiration_date: str = None,
        strike_price: float = None,
        contract_type: str = None,
    ) -> Dict:
        """
        Get options chain snapshot for an underlying asset.

        Args:
            underlying: Stock symbol (e.g., 'AAPL')
            expiration_date: Filter by expiration (YYYY-MM-DD)
            strike_price: Filter by strike price
            contract_type: 'call' or 'put'

        Returns:
            Dict with options chain data including calls, puts, and summary stats
        """
        endpoint = f"/v3/snapshot/options/{underlying.upper()}"
        params = {}

        if expiration_date:
            params['expiration_date'] = expiration_date
        if strike_price:
            params['strike_price'] = strike_price
        if contract_type:
            params['contract_type'] = contract_type

        data = await self._request(endpoint, params)

        if not data or 'results' not in data:
            return {'calls': [], 'puts': [], 'summary': {}}

        calls = []
        puts = []
        total_call_volume = 0
        total_put_volume = 0
        total_call_oi = 0
        total_put_oi = 0

        for option in data['results']:
            details = option.get('details', {})
            day = option.get('day', {})
            greeks = option.get('greeks', {})
            underlying_asset = option.get('underlying_asset', {})

            contract = {
                'ticker': details.get('ticker'),
                'contract_type': details.get('contract_type'),
                'strike': details.get('strike_price'),
                'expiration': details.get('expiration_date'),
                'last_price': day.get('close'),
                'bid': option.get('last_quote', {}).get('bid'),
                'ask': option.get('last_quote', {}).get('ask'),
                'volume': day.get('volume', 0),
                'open_interest': option.get('open_interest', 0),
                'implied_volatility': option.get('implied_volatility'),
                'delta': greeks.get('delta'),
                'gamma': greeks.get('gamma'),
                'theta': greeks.get('theta'),
                'vega': greeks.get('vega'),
                'underlying_price': underlying_asset.get('price'),
            }

            if details.get('contract_type') == 'call':
                calls.append(contract)
                total_call_volume += day.get('volume', 0)
                total_call_oi += option.get('open_interest', 0)
            else:
                puts.append(contract)
                total_put_volume += day.get('volume', 0)
                total_put_oi += option.get('open_interest', 0)

        # Calculate put/call ratios
        pc_volume_ratio = total_put_volume / total_call_volume if total_call_volume > 0 else 0
        pc_oi_ratio = total_put_oi / total_call_oi if total_call_oi > 0 else 0

        return {
            'underlying': underlying.upper(),
            'calls': sorted(calls, key=lambda x: (x.get('expiration', ''), x.get('strike', 0))),
            'puts': sorted(puts, key=lambda x: (x.get('expiration', ''), x.get('strike', 0))),
            'summary': {
                'total_call_volume': total_call_volume,
                'total_put_volume': total_put_volume,
                'total_call_oi': total_call_oi,
                'total_put_oi': total_put_oi,
                'put_call_volume_ratio': round(pc_volume_ratio, 2),
                'put_call_oi_ratio': round(pc_oi_ratio, 2),
                'sentiment': 'bearish' if pc_volume_ratio > 1.2 else ('bullish' if pc_volume_ratio < 0.7 else 'neutral'),
            }
        }

    async def get_options_contracts(
        self,
        underlying: str = None,
        contract_type: str = None,
        expiration_date_gte: str = None,
        expiration_date_lte: str = None,
        strike_price_gte: float = None,
        strike_price_lte: float = None,
        limit: int = 100,
    ) -> List[Dict]:
        """
        Search for options contracts.

        Args:
            underlying: Filter by underlying ticker
            contract_type: 'call' or 'put'
            expiration_date_gte: Min expiration date (YYYY-MM-DD)
            expiration_date_lte: Max expiration date (YYYY-MM-DD)
            strike_price_gte: Min strike price
            strike_price_lte: Max strike price
            limit: Max results

        Returns:
            List of matching options contracts
        """
        endpoint = "/v3/reference/options/contracts"
        params = {'limit': limit}

        if underlying:
            params['underlying_ticker'] = underlying.upper()
        if contract_type:
            params['contract_type'] = contract_type
        if expiration_date_gte:
            params['expiration_date.gte'] = expiration_date_gte
        if expiration_date_lte:
            params['expiration_date.lte'] = expiration_date_lte
        if strike_price_gte:
            params['strike_price.gte'] = strike_price_gte
        if strike_price_lte:
            params['strike_price.lte'] = strike_price_lte

        data = await self._request(endpoint, params)

        if not data or 'results' not in data:
            return []

        contracts = []
        for c in data['results']:
            contracts.append({
                'ticker': c.get('ticker'),
                'underlying': c.get('underlying_ticker'),
                'contract_type': c.get('contract_type'),
                'strike': c.get('strike_price'),
                'expiration': c.get('expiration_date'),
                'exercise_style': c.get('exercise_style'),
                'shares_per_contract': c.get('shares_per_contract', 100),
            })

        return contracts

    async def get_option_quote(self, options_ticker: str) -> Optional[Dict]:
        """
        Get quote for a specific options contract.

        Args:
            options_ticker: Options ticker (e.g., 'O:AAPL250117C00150000')

        Returns:
            Quote data for the option
        """
        endpoint = f"/v3/quotes/{options_ticker}"

        data = await self._request(endpoint)

        if data and 'results' in data and data['results']:
            q = data['results'][0] if isinstance(data['results'], list) else data['results']
            return {
                'ticker': options_ticker,
                'bid': q.get('bid_price'),
                'ask': q.get('ask_price'),
                'bid_size': q.get('bid_size'),
                'ask_size': q.get('ask_size'),
                'mid': (q.get('bid_price', 0) + q.get('ask_price', 0)) / 2,
                'timestamp': q.get('sip_timestamp'),
            }
        return None

    async def get_options_aggregates(
        self,
        options_ticker: str,
        multiplier: int = 1,
        timespan: str = 'day',
        from_date: str = None,
        to_date: str = None,
        limit: int = 50,
    ) -> Optional[pd.DataFrame]:
        """
        Get historical OHLCV data for an options contract.

        Args:
            options_ticker: Options ticker (e.g., 'O:AAPL250117C00150000')
            multiplier: Timespan multiplier
            timespan: 'minute', 'hour', 'day', 'week'
            from_date: Start date (YYYY-MM-DD)
            to_date: End date (YYYY-MM-DD)
            limit: Max results

        Returns:
            DataFrame with options OHLCV data
        """
        if to_date is None:
            to_date = datetime.now().strftime('%Y-%m-%d')
        if from_date is None:
            from_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')

        endpoint = f"/v2/aggs/ticker/{options_ticker}/range/{multiplier}/{timespan}/{from_date}/{to_date}"

        data = await self._request(endpoint, {'limit': limit, 'sort': 'asc'})

        if not data or 'results' not in data:
            return None

        results = data['results']
        if not results:
            return None

        df = pd.DataFrame(results)
        df = df.rename(columns={
            'o': 'Open', 'h': 'High', 'l': 'Low', 'c': 'Close',
            'v': 'Volume', 't': 'Timestamp'
        })
        df['Date'] = pd.to_datetime(df['Timestamp'], unit='ms')
        df = df.set_index('Date')

        return df[['Open', 'High', 'Low', 'Close', 'Volume']]

    async def analyze_unusual_options(
        self,
        ticker: str,
        volume_threshold: float = 2.0,
    ) -> Dict:
        """
        Analyze options for unusual activity.

        Looks for:
        - High volume vs open interest (potential new positions)
        - Large put/call imbalances
        - Near-expiry high volume

        Args:
            ticker: Stock symbol
            volume_threshold: Volume/OI ratio threshold for "unusual"

        Returns:
            Analysis of unusual options activity
        """
        chain = await self.get_options_chain(ticker)

        if not chain.get('calls') and not chain.get('puts'):
            return {'unusual_activity': False, 'signals': []}

        signals = []
        unusual_contracts = []

        # Analyze each contract for unusual activity
        for contract in chain.get('calls', []) + chain.get('puts', []):
            volume = contract.get('volume', 0)
            oi = contract.get('open_interest', 1)  # Avoid division by zero

            # High volume relative to open interest
            if volume > 0 and oi > 0:
                vol_oi_ratio = volume / oi
                if vol_oi_ratio >= volume_threshold:
                    unusual_contracts.append({
                        'ticker': contract.get('ticker'),
                        'type': contract.get('contract_type'),
                        'strike': contract.get('strike'),
                        'expiration': contract.get('expiration'),
                        'volume': volume,
                        'open_interest': oi,
                        'vol_oi_ratio': round(vol_oi_ratio, 2),
                        'implied_volatility': contract.get('implied_volatility'),
                        'signal': 'HIGH_VOL_VS_OI',
                    })

        # Overall flow analysis
        summary = chain.get('summary', {})
        pc_ratio = summary.get('put_call_volume_ratio', 1.0)

        if pc_ratio > 1.5:
            signals.append({
                'type': 'BEARISH_FLOW',
                'description': f'High put/call ratio: {pc_ratio:.2f}',
                'strength': 'strong' if pc_ratio > 2.0 else 'moderate',
            })
        elif pc_ratio < 0.5:
            signals.append({
                'type': 'BULLISH_FLOW',
                'description': f'Low put/call ratio: {pc_ratio:.2f}',
                'strength': 'strong' if pc_ratio < 0.3 else 'moderate',
            })

        # Sort unusual contracts by vol/oi ratio
        unusual_contracts.sort(key=lambda x: x.get('vol_oi_ratio', 0), reverse=True)

        return {
            'ticker': ticker,
            'unusual_activity': len(unusual_contracts) > 0 or len(signals) > 0,
            'unusual_contracts': unusual_contracts[:10],  # Top 10
            'signals': signals,
            'summary': summary,
            'total_unusual_contracts': len(unusual_contracts),
        }

    async def get_options_flow_summary(self, ticker: str) -> Dict:
        """
        Get a summary of options flow for quick analysis.

        Returns:
            Simplified options flow data for the ticker
        """
        chain = await self.get_options_chain(ticker)
        summary = chain.get('summary', {})

        # Determine overall sentiment from options flow
        pc_ratio = summary.get('put_call_volume_ratio', 1.0)

        if pc_ratio > 1.3:
            sentiment = 'bearish'
            sentiment_score = min(100, int((pc_ratio - 1.0) * 100))
        elif pc_ratio < 0.7:
            sentiment = 'bullish'
            sentiment_score = min(100, int((1.0 - pc_ratio) * 100))
        else:
            sentiment = 'neutral'
            sentiment_score = 50

        return {
            'ticker': ticker,
            'put_call_ratio': round(pc_ratio, 2),
            'sentiment': sentiment,
            'sentiment_score': sentiment_score,
            'total_call_volume': summary.get('total_call_volume', 0),
            'total_put_volume': summary.get('total_put_volume', 0),
            'total_call_oi': summary.get('total_call_oi', 0),
            'total_put_oi': summary.get('total_put_oi', 0),
            'has_unusual_activity': pc_ratio > 1.5 or pc_ratio < 0.5,
        }

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


# =============================================================================
# SYNCHRONOUS WRAPPERS (for use in non-async code)
# =============================================================================

def _run_async(coro):
    """Helper to run async code from sync context."""
    import concurrent.futures
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, coro)
                return future.result(timeout=30)
        else:
            return asyncio.run(coro)
    except RuntimeError:
        return asyncio.run(coro)


def get_price_data_sync(ticker: str, days: int = 250) -> Optional[pd.DataFrame]:
    """
    Synchronous wrapper to get price data from Polygon.

    Args:
        ticker: Stock symbol (e.g., 'AAPL', 'SPY', 'VIX' for ^VIX)
        days: Number of days of history

    Returns:
        DataFrame with OHLCV data or None
    """
    # Convert common index symbols
    ticker_map = {
        '^VIX': 'VIX',
        '^GSPC': 'SPY',  # S&P 500 -> use SPY as proxy
        '^DJI': 'DIA',   # Dow -> use DIA as proxy
        '^IXIC': 'QQQ',  # NASDAQ -> use QQQ as proxy
    }
    polygon_ticker = ticker_map.get(ticker, ticker.replace('^', ''))

    async def fetch():
        provider = PolygonProvider()
        try:
            return await provider.get_daily_bars(polygon_ticker, days)
        finally:
            await provider.close()

    return _run_async(fetch())


def get_ticker_details_sync(ticker: str) -> Optional[Dict]:
    """Synchronous wrapper to get ticker details."""
    async def fetch():
        provider = PolygonProvider()
        try:
            return await provider.get_ticker_details(ticker)
        finally:
            await provider.close()

    return _run_async(fetch())


def get_news_sync(ticker: str = None, limit: int = 10) -> List[Dict]:
    """Synchronous wrapper to get news."""
    async def fetch():
        provider = PolygonProvider()
        try:
            return await provider.get_news(ticker, limit)
        finally:
            await provider.close()

    return _run_async(fetch())


def get_market_movers_sync(direction: str = 'gainers') -> List[Dict]:
    """Synchronous wrapper to get market movers."""
    async def fetch():
        provider = PolygonProvider()
        try:
            return await provider.get_market_movers(direction)
        finally:
            await provider.close()

    return _run_async(fetch())


def get_snapshot_sync(ticker: str) -> Optional[Dict]:
    """Synchronous wrapper to get real-time snapshot."""
    async def fetch():
        provider = PolygonProvider()
        try:
            return await provider.get_snapshot(ticker)
        finally:
            await provider.close()

    return _run_async(fetch())


# =============================================================================
# OPTIONS SYNCHRONOUS WRAPPERS
# =============================================================================

def get_options_chain_sync(
    underlying: str,
    expiration_date: str = None,
    contract_type: str = None,
) -> Dict:
    """
    Synchronous wrapper to get options chain.

    Args:
        underlying: Stock symbol (e.g., 'AAPL')
        expiration_date: Filter by expiration (YYYY-MM-DD)
        contract_type: 'call' or 'put'

    Returns:
        Options chain with calls, puts, and summary
    """
    async def fetch():
        provider = PolygonProvider()
        try:
            return await provider.get_options_chain(
                underlying, expiration_date, contract_type=contract_type
            )
        finally:
            await provider.close()

    return _run_async(fetch())


def get_options_flow_sync(ticker: str) -> Dict:
    """
    Synchronous wrapper to get options flow summary.

    Returns simplified options flow data including:
    - Put/call ratio
    - Sentiment (bullish/bearish/neutral)
    - Volume and open interest totals
    """
    async def fetch():
        provider = PolygonProvider()
        try:
            return await provider.get_options_flow_summary(ticker)
        finally:
            await provider.close()

    return _run_async(fetch())


def get_unusual_options_sync(ticker: str, volume_threshold: float = 2.0) -> Dict:
    """
    Synchronous wrapper to detect unusual options activity.

    Args:
        ticker: Stock symbol
        volume_threshold: Volume/OI ratio for "unusual" (default 2.0x)

    Returns:
        Analysis of unusual options activity
    """
    async def fetch():
        provider = PolygonProvider()
        try:
            return await provider.analyze_unusual_options(ticker, volume_threshold)
        finally:
            await provider.close()

    return _run_async(fetch())


def get_options_contracts_sync(
    underlying: str,
    contract_type: str = None,
    expiration_date_gte: str = None,
    expiration_date_lte: str = None,
    limit: int = 100,
) -> List[Dict]:
    """Synchronous wrapper to search for options contracts."""
    async def fetch():
        provider = PolygonProvider()
        try:
            return await provider.get_options_contracts(
                underlying=underlying,
                contract_type=contract_type,
                expiration_date_gte=expiration_date_gte,
                expiration_date_lte=expiration_date_lte,
                limit=limit,
            )
        finally:
            await provider.close()

    return _run_async(fetch())


def is_polygon_configured() -> bool:
    """Check if Polygon API is configured."""
    return bool(os.environ.get('POLYGON_API_KEY', ''))
