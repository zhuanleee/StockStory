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

    # =========================================================================
    # FINANCIALS & EARNINGS DATA
    # =========================================================================

    async def get_financials(
        self,
        ticker: str,
        timeframe: str = 'quarterly',
        limit: int = 10,
    ) -> List[Dict]:
        """
        Get company financial statements.

        Args:
            ticker: Stock symbol
            timeframe: 'annual' or 'quarterly'
            limit: Number of periods to return

        Returns:
            List of financial statement data
        """
        endpoint = f"/vX/reference/financials"
        params = {
            'ticker': ticker.upper(),
            'timeframe': timeframe,
            'limit': limit,
            'sort': 'filing_date',
            'order': 'desc',
        }

        data = await self._request(endpoint, params)

        if not data or 'results' not in data:
            return []

        financials = []
        for item in data['results']:
            fin = item.get('financials', {})
            income = fin.get('income_statement', {})
            balance = fin.get('balance_sheet', {})
            cash_flow = fin.get('cash_flow_statement', {})

            financials.append({
                'ticker': ticker.upper(),
                'period': item.get('fiscal_period'),
                'fiscal_year': item.get('fiscal_year'),
                'filing_date': item.get('filing_date'),
                'timeframe': timeframe,
                # Income Statement
                'revenue': income.get('revenues', {}).get('value'),
                'gross_profit': income.get('gross_profit', {}).get('value'),
                'operating_income': income.get('operating_income_loss', {}).get('value'),
                'net_income': income.get('net_income_loss', {}).get('value'),
                'eps_basic': income.get('basic_earnings_per_share', {}).get('value'),
                'eps_diluted': income.get('diluted_earnings_per_share', {}).get('value'),
                # Balance Sheet
                'total_assets': balance.get('assets', {}).get('value'),
                'total_liabilities': balance.get('liabilities', {}).get('value'),
                'total_equity': balance.get('equity', {}).get('value'),
                'cash': balance.get('cash', {}).get('value'),
                # Cash Flow
                'operating_cash_flow': cash_flow.get('net_cash_flow_from_operating_activities', {}).get('value'),
                'investing_cash_flow': cash_flow.get('net_cash_flow_from_investing_activities', {}).get('value'),
                'financing_cash_flow': cash_flow.get('net_cash_flow_from_financing_activities', {}).get('value'),
            })

        return financials

    async def get_earnings_history(self, ticker: str, limit: int = 8) -> List[Dict]:
        """
        Get earnings history with EPS surprises.

        Args:
            ticker: Stock symbol
            limit: Number of quarters

        Returns:
            List of earnings with actual vs estimate
        """
        financials = await self.get_financials(ticker, 'quarterly', limit)

        earnings = []
        for fin in financials:
            if fin.get('eps_diluted') is not None:
                earnings.append({
                    'ticker': ticker.upper(),
                    'period': fin.get('period'),
                    'fiscal_year': fin.get('fiscal_year'),
                    'filing_date': fin.get('filing_date'),
                    'eps_actual': fin.get('eps_diluted'),
                    'revenue': fin.get('revenue'),
                    'net_income': fin.get('net_income'),
                })

        return earnings

    # =========================================================================
    # DIVIDENDS DATA
    # =========================================================================

    async def get_dividends(
        self,
        ticker: str = None,
        ex_dividend_date_gte: str = None,
        ex_dividend_date_lte: str = None,
        limit: int = 50,
    ) -> List[Dict]:
        """
        Get dividend data.

        Args:
            ticker: Stock symbol (optional, gets all if not specified)
            ex_dividend_date_gte: Min ex-dividend date (YYYY-MM-DD)
            ex_dividend_date_lte: Max ex-dividend date (YYYY-MM-DD)
            limit: Max results

        Returns:
            List of dividend records
        """
        endpoint = "/v3/reference/dividends"
        params = {'limit': limit, 'order': 'desc', 'sort': 'ex_dividend_date'}

        if ticker:
            params['ticker'] = ticker.upper()
        if ex_dividend_date_gte:
            params['ex_dividend_date.gte'] = ex_dividend_date_gte
        if ex_dividend_date_lte:
            params['ex_dividend_date.lte'] = ex_dividend_date_lte

        data = await self._request(endpoint, params)

        if not data or 'results' not in data:
            return []

        dividends = []
        for d in data['results']:
            dividends.append({
                'ticker': d.get('ticker'),
                'cash_amount': d.get('cash_amount'),
                'currency': d.get('currency', 'USD'),
                'declaration_date': d.get('declaration_date'),
                'ex_dividend_date': d.get('ex_dividend_date'),
                'pay_date': d.get('pay_date'),
                'record_date': d.get('record_date'),
                'frequency': d.get('frequency'),  # 1=annual, 2=semi, 4=quarterly, 12=monthly
                'dividend_type': d.get('dividend_type'),  # CD=cash, SC=special cash
            })

        return dividends

    async def get_upcoming_dividends(self, days_ahead: int = 14) -> List[Dict]:
        """
        Get stocks with upcoming ex-dividend dates.

        Args:
            days_ahead: Number of days to look ahead

        Returns:
            List of upcoming dividends
        """
        today = datetime.now().strftime('%Y-%m-%d')
        future = (datetime.now() + timedelta(days=days_ahead)).strftime('%Y-%m-%d')

        return await self.get_dividends(
            ex_dividend_date_gte=today,
            ex_dividend_date_lte=future,
            limit=100,
        )

    async def get_dividend_yield(self, ticker: str, current_price: float = None) -> Dict:
        """
        Calculate dividend yield for a ticker.

        Args:
            ticker: Stock symbol
            current_price: Current stock price (fetched if not provided)

        Returns:
            Dividend yield data
        """
        # Get recent dividends
        dividends = await self.get_dividends(ticker, limit=12)

        if not dividends:
            return {
                'ticker': ticker.upper(),
                'annual_dividend': 0,
                'yield_percent': 0,
                'frequency': 'none',
                'next_ex_date': None,
            }

        # Get current price if not provided
        if current_price is None:
            snapshot = await self.get_snapshot(ticker)
            current_price = snapshot.get('price', 0) if snapshot else 0

        # Calculate annual dividend (sum of last 4 quarters or annualize)
        annual_dividend = 0
        frequency = dividends[0].get('frequency', 4)

        if frequency == 4:  # Quarterly
            annual_dividend = sum(d.get('cash_amount', 0) for d in dividends[:4])
        elif frequency == 12:  # Monthly
            annual_dividend = sum(d.get('cash_amount', 0) for d in dividends[:12])
        elif frequency == 2:  # Semi-annual
            annual_dividend = sum(d.get('cash_amount', 0) for d in dividends[:2])
        elif frequency == 1:  # Annual
            annual_dividend = dividends[0].get('cash_amount', 0) if dividends else 0

        yield_percent = (annual_dividend / current_price * 100) if current_price > 0 else 0

        return {
            'ticker': ticker.upper(),
            'annual_dividend': round(annual_dividend, 4),
            'yield_percent': round(yield_percent, 2),
            'frequency': {1: 'annual', 2: 'semi-annual', 4: 'quarterly', 12: 'monthly'}.get(frequency, 'unknown'),
            'last_amount': dividends[0].get('cash_amount') if dividends else None,
            'last_ex_date': dividends[0].get('ex_dividend_date') if dividends else None,
        }

    # =========================================================================
    # STOCK SPLITS DATA
    # =========================================================================

    async def get_stock_splits(
        self,
        ticker: str = None,
        execution_date_gte: str = None,
        execution_date_lte: str = None,
        limit: int = 50,
    ) -> List[Dict]:
        """
        Get stock split data.

        Args:
            ticker: Stock symbol (optional)
            execution_date_gte: Min execution date (YYYY-MM-DD)
            execution_date_lte: Max execution date (YYYY-MM-DD)
            limit: Max results

        Returns:
            List of stock split records
        """
        endpoint = "/v3/reference/splits"
        params = {'limit': limit, 'order': 'desc', 'sort': 'execution_date'}

        if ticker:
            params['ticker'] = ticker.upper()
        if execution_date_gte:
            params['execution_date.gte'] = execution_date_gte
        if execution_date_lte:
            params['execution_date.lte'] = execution_date_lte

        data = await self._request(endpoint, params)

        if not data or 'results' not in data:
            return []

        splits = []
        for s in data['results']:
            split_from = s.get('split_from', 1)
            split_to = s.get('split_to', 1)
            ratio = split_to / split_from if split_from > 0 else 1

            splits.append({
                'ticker': s.get('ticker'),
                'execution_date': s.get('execution_date'),
                'split_from': split_from,
                'split_to': split_to,
                'ratio': ratio,
                'ratio_str': f"{split_to}:{split_from}",
                'is_forward_split': ratio > 1,  # Forward split increases shares
                'is_reverse_split': ratio < 1,  # Reverse split decreases shares
            })

        return splits

    async def get_upcoming_splits(self, days_ahead: int = 30) -> List[Dict]:
        """
        Get stocks with upcoming splits.

        Args:
            days_ahead: Number of days to look ahead

        Returns:
            List of upcoming splits
        """
        today = datetime.now().strftime('%Y-%m-%d')
        future = (datetime.now() + timedelta(days=days_ahead)).strftime('%Y-%m-%d')

        return await self.get_stock_splits(
            execution_date_gte=today,
            execution_date_lte=future,
            limit=100,
        )

    async def get_recent_splits(self, days_back: int = 30) -> List[Dict]:
        """
        Get recent stock splits.

        Args:
            days_back: Number of days to look back

        Returns:
            List of recent splits
        """
        today = datetime.now().strftime('%Y-%m-%d')
        past = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')

        return await self.get_stock_splits(
            execution_date_gte=past,
            execution_date_lte=today,
            limit=100,
        )

    # =========================================================================
    # TECHNICAL INDICATORS
    # =========================================================================

    async def get_sma(
        self,
        ticker: str,
        window: int = 50,
        timespan: str = 'day',
        limit: int = 100,
    ) -> Optional[pd.DataFrame]:
        """
        Get Simple Moving Average.

        Args:
            ticker: Stock symbol
            window: SMA window period
            timespan: 'day', 'week', 'month'
            limit: Number of data points

        Returns:
            DataFrame with SMA values
        """
        endpoint = f"/v1/indicators/sma/{ticker.upper()}"
        params = {
            'timespan': timespan,
            'window': window,
            'limit': limit,
            'order': 'desc',
        }

        data = await self._request(endpoint, params)

        if not data or 'results' not in data or 'values' not in data['results']:
            return None

        values = data['results']['values']
        if not values:
            return None

        df = pd.DataFrame(values)
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df.set_index('timestamp')
        df = df.rename(columns={'value': f'SMA_{window}'})

        return df.sort_index()

    async def get_ema(
        self,
        ticker: str,
        window: int = 20,
        timespan: str = 'day',
        limit: int = 100,
    ) -> Optional[pd.DataFrame]:
        """
        Get Exponential Moving Average.

        Args:
            ticker: Stock symbol
            window: EMA window period
            timespan: 'day', 'week', 'month'
            limit: Number of data points

        Returns:
            DataFrame with EMA values
        """
        endpoint = f"/v1/indicators/ema/{ticker.upper()}"
        params = {
            'timespan': timespan,
            'window': window,
            'limit': limit,
            'order': 'desc',
        }

        data = await self._request(endpoint, params)

        if not data or 'results' not in data or 'values' not in data['results']:
            return None

        values = data['results']['values']
        if not values:
            return None

        df = pd.DataFrame(values)
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df.set_index('timestamp')
        df = df.rename(columns={'value': f'EMA_{window}'})

        return df.sort_index()

    async def get_rsi(
        self,
        ticker: str,
        window: int = 14,
        timespan: str = 'day',
        limit: int = 100,
    ) -> Optional[pd.DataFrame]:
        """
        Get Relative Strength Index.

        Args:
            ticker: Stock symbol
            window: RSI window period (default 14)
            timespan: 'day', 'week', 'month'
            limit: Number of data points

        Returns:
            DataFrame with RSI values
        """
        endpoint = f"/v1/indicators/rsi/{ticker.upper()}"
        params = {
            'timespan': timespan,
            'window': window,
            'limit': limit,
            'order': 'desc',
        }

        data = await self._request(endpoint, params)

        if not data or 'results' not in data or 'values' not in data['results']:
            return None

        values = data['results']['values']
        if not values:
            return None

        df = pd.DataFrame(values)
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df.set_index('timestamp')
        df = df.rename(columns={'value': 'RSI'})

        return df.sort_index()

    async def get_macd(
        self,
        ticker: str,
        short_window: int = 12,
        long_window: int = 26,
        signal_window: int = 9,
        timespan: str = 'day',
        limit: int = 100,
    ) -> Optional[pd.DataFrame]:
        """
        Get MACD (Moving Average Convergence Divergence).

        Args:
            ticker: Stock symbol
            short_window: Short EMA period (default 12)
            long_window: Long EMA period (default 26)
            signal_window: Signal line period (default 9)
            timespan: 'day', 'week', 'month'
            limit: Number of data points

        Returns:
            DataFrame with MACD, signal, and histogram
        """
        endpoint = f"/v1/indicators/macd/{ticker.upper()}"
        params = {
            'timespan': timespan,
            'short_window': short_window,
            'long_window': long_window,
            'signal_window': signal_window,
            'limit': limit,
            'order': 'desc',
        }

        data = await self._request(endpoint, params)

        if not data or 'results' not in data or 'values' not in data['results']:
            return None

        values = data['results']['values']
        if not values:
            return None

        df = pd.DataFrame(values)
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df.set_index('timestamp')
        df = df.rename(columns={
            'value': 'MACD',
            'signal': 'MACD_Signal',
            'histogram': 'MACD_Histogram',
        })

        return df.sort_index()

    async def get_technical_summary(self, ticker: str) -> Dict:
        """
        Get a technical analysis summary for a ticker.

        Returns:
            Dict with key technical indicators and signals
        """
        # Fetch indicators concurrently
        sma_20, sma_50, sma_200, rsi, macd = await asyncio.gather(
            self.get_sma(ticker, window=20, limit=1),
            self.get_sma(ticker, window=50, limit=1),
            self.get_sma(ticker, window=200, limit=1),
            self.get_rsi(ticker, limit=1),
            self.get_macd(ticker, limit=1),
            return_exceptions=True,
        )

        # Get current price
        snapshot = await self.get_snapshot(ticker)
        current_price = snapshot.get('price', 0) if snapshot else 0

        # Extract latest values
        sma_20_val = sma_20.iloc[-1]['SMA_20'] if sma_20 is not None and not isinstance(sma_20, Exception) and len(sma_20) > 0 else None
        sma_50_val = sma_50.iloc[-1]['SMA_50'] if sma_50 is not None and not isinstance(sma_50, Exception) and len(sma_50) > 0 else None
        sma_200_val = sma_200.iloc[-1]['SMA_200'] if sma_200 is not None and not isinstance(sma_200, Exception) and len(sma_200) > 0 else None
        rsi_val = rsi.iloc[-1]['RSI'] if rsi is not None and not isinstance(rsi, Exception) and len(rsi) > 0 else None
        macd_val = macd.iloc[-1]['MACD'] if macd is not None and not isinstance(macd, Exception) and len(macd) > 0 else None
        macd_signal = macd.iloc[-1]['MACD_Signal'] if macd is not None and not isinstance(macd, Exception) and len(macd) > 0 else None

        # Generate signals
        signals = []

        if current_price and sma_20_val:
            if current_price > sma_20_val:
                signals.append('ABOVE_SMA20')
            else:
                signals.append('BELOW_SMA20')

        if current_price and sma_50_val:
            if current_price > sma_50_val:
                signals.append('ABOVE_SMA50')
            else:
                signals.append('BELOW_SMA50')

        if current_price and sma_200_val:
            if current_price > sma_200_val:
                signals.append('ABOVE_SMA200')
            else:
                signals.append('BELOW_SMA200')

        if rsi_val:
            if rsi_val > 70:
                signals.append('RSI_OVERBOUGHT')
            elif rsi_val < 30:
                signals.append('RSI_OVERSOLD')

        if macd_val is not None and macd_signal is not None:
            if macd_val > macd_signal:
                signals.append('MACD_BULLISH')
            else:
                signals.append('MACD_BEARISH')

        # Determine trend
        trend = 'neutral'
        if sma_20_val and sma_50_val and sma_200_val:
            if sma_20_val > sma_50_val > sma_200_val:
                trend = 'strong_uptrend'
            elif sma_20_val > sma_50_val:
                trend = 'uptrend'
            elif sma_20_val < sma_50_val < sma_200_val:
                trend = 'strong_downtrend'
            elif sma_20_val < sma_50_val:
                trend = 'downtrend'

        return {
            'ticker': ticker.upper(),
            'price': current_price,
            'sma_20': round(sma_20_val, 2) if sma_20_val else None,
            'sma_50': round(sma_50_val, 2) if sma_50_val else None,
            'sma_200': round(sma_200_val, 2) if sma_200_val else None,
            'rsi': round(rsi_val, 1) if rsi_val else None,
            'macd': round(macd_val, 4) if macd_val else None,
            'macd_signal': round(macd_signal, 4) if macd_signal else None,
            'trend': trend,
            'signals': signals,
        }

    # =========================================================================
    # TICKER UNIVERSE & REFERENCE DATA
    # =========================================================================

    async def get_tickers(
        self,
        ticker_type: str = 'CS',  # CS=Common Stock
        market: str = 'stocks',
        exchange: str = None,
        active: bool = True,
        limit: int = 1000,
        search: str = None,
    ) -> List[Dict]:
        """
        Get list of tickers with filtering.

        Args:
            ticker_type: 'CS' (common stock), 'ETF', 'ADRC', etc.
            market: 'stocks', 'crypto', 'fx', 'otc'
            exchange: Filter by exchange (e.g., 'XNAS' for NASDAQ, 'XNYS' for NYSE)
            active: Only active tickers
            limit: Max results (up to 1000)
            search: Search term for ticker or name

        Returns:
            List of ticker information
        """
        endpoint = "/v3/reference/tickers"
        params = {
            'type': ticker_type,
            'market': market,
            'active': str(active).lower(),
            'limit': limit,
            'order': 'asc',
            'sort': 'ticker',
        }

        if exchange:
            params['exchange'] = exchange
        if search:
            params['search'] = search

        data = await self._request(endpoint, params)

        if not data or 'results' not in data:
            return []

        tickers = []
        for t in data['results']:
            tickers.append({
                'ticker': t.get('ticker'),
                'name': t.get('name'),
                'market': t.get('market'),
                'locale': t.get('locale'),
                'type': t.get('type'),
                'active': t.get('active'),
                'currency': t.get('currency_name'),
                'exchange': t.get('primary_exchange'),
                'cik': t.get('cik'),
                'composite_figi': t.get('composite_figi'),
            })

        return tickers

    async def get_us_stocks(
        self,
        min_market_cap: float = None,
        exchange: str = None,
        limit: int = 1000,
    ) -> List[str]:
        """
        Get list of US stock tickers.

        Args:
            min_market_cap: Minimum market cap filter (requires additional API call)
            exchange: 'XNAS' (NASDAQ), 'XNYS' (NYSE), 'XASE' (AMEX)
            limit: Max tickers to return

        Returns:
            List of ticker symbols
        """
        tickers = await self.get_tickers(
            ticker_type='CS',
            market='stocks',
            exchange=exchange,
            active=True,
            limit=limit,
        )

        return [t['ticker'] for t in tickers if t.get('ticker')]

    async def get_nasdaq_stocks(self, limit: int = 1000) -> List[str]:
        """Get NASDAQ-listed stocks."""
        return await self.get_us_stocks(exchange='XNAS', limit=limit)

    async def get_nyse_stocks(self, limit: int = 1000) -> List[str]:
        """Get NYSE-listed stocks."""
        return await self.get_us_stocks(exchange='XNYS', limit=limit)

    async def get_etfs(self, limit: int = 500) -> List[Dict]:
        """Get list of ETFs."""
        return await self.get_tickers(
            ticker_type='ETF',
            market='stocks',
            active=True,
            limit=limit,
        )

    async def search_tickers(self, query: str, limit: int = 20) -> List[Dict]:
        """
        Search for tickers by name or symbol.

        Args:
            query: Search term
            limit: Max results

        Returns:
            List of matching tickers
        """
        return await self.get_tickers(
            search=query,
            limit=limit,
        )

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


# =============================================================================
# FINANCIALS & EARNINGS SYNC WRAPPERS
# =============================================================================

def get_financials_sync(ticker: str, timeframe: str = 'quarterly', limit: int = 10) -> List[Dict]:
    """Synchronous wrapper to get company financials."""
    async def fetch():
        provider = PolygonProvider()
        try:
            return await provider.get_financials(ticker, timeframe, limit)
        finally:
            await provider.close()

    return _run_async(fetch())


def get_earnings_history_sync(ticker: str, limit: int = 8) -> List[Dict]:
    """Synchronous wrapper to get earnings history."""
    async def fetch():
        provider = PolygonProvider()
        try:
            return await provider.get_earnings_history(ticker, limit)
        finally:
            await provider.close()

    return _run_async(fetch())


# =============================================================================
# DIVIDENDS SYNC WRAPPERS
# =============================================================================

def get_dividends_sync(ticker: str = None, limit: int = 50) -> List[Dict]:
    """Synchronous wrapper to get dividend data."""
    async def fetch():
        provider = PolygonProvider()
        try:
            return await provider.get_dividends(ticker, limit=limit)
        finally:
            await provider.close()

    return _run_async(fetch())


def get_upcoming_dividends_sync(days_ahead: int = 14) -> List[Dict]:
    """Synchronous wrapper to get upcoming dividends."""
    async def fetch():
        provider = PolygonProvider()
        try:
            return await provider.get_upcoming_dividends(days_ahead)
        finally:
            await provider.close()

    return _run_async(fetch())


def get_dividend_yield_sync(ticker: str) -> Dict:
    """Synchronous wrapper to get dividend yield."""
    async def fetch():
        provider = PolygonProvider()
        try:
            return await provider.get_dividend_yield(ticker)
        finally:
            await provider.close()

    return _run_async(fetch())


# =============================================================================
# STOCK SPLITS SYNC WRAPPERS
# =============================================================================

def get_stock_splits_sync(ticker: str = None, limit: int = 50) -> List[Dict]:
    """Synchronous wrapper to get stock splits."""
    async def fetch():
        provider = PolygonProvider()
        try:
            return await provider.get_stock_splits(ticker, limit=limit)
        finally:
            await provider.close()

    return _run_async(fetch())


def get_upcoming_splits_sync(days_ahead: int = 30) -> List[Dict]:
    """Synchronous wrapper to get upcoming stock splits."""
    async def fetch():
        provider = PolygonProvider()
        try:
            return await provider.get_upcoming_splits(days_ahead)
        finally:
            await provider.close()

    return _run_async(fetch())


def get_recent_splits_sync(days_back: int = 30) -> List[Dict]:
    """Synchronous wrapper to get recent stock splits."""
    async def fetch():
        provider = PolygonProvider()
        try:
            return await provider.get_recent_splits(days_back)
        finally:
            await provider.close()

    return _run_async(fetch())


# =============================================================================
# TECHNICAL INDICATORS SYNC WRAPPERS
# =============================================================================

def get_sma_sync(ticker: str, window: int = 50) -> Optional[pd.DataFrame]:
    """Synchronous wrapper to get SMA."""
    async def fetch():
        provider = PolygonProvider()
        try:
            return await provider.get_sma(ticker, window)
        finally:
            await provider.close()

    return _run_async(fetch())


def get_ema_sync(ticker: str, window: int = 20) -> Optional[pd.DataFrame]:
    """Synchronous wrapper to get EMA."""
    async def fetch():
        provider = PolygonProvider()
        try:
            return await provider.get_ema(ticker, window)
        finally:
            await provider.close()

    return _run_async(fetch())


def get_rsi_sync(ticker: str, window: int = 14) -> Optional[pd.DataFrame]:
    """Synchronous wrapper to get RSI."""
    async def fetch():
        provider = PolygonProvider()
        try:
            return await provider.get_rsi(ticker, window)
        finally:
            await provider.close()

    return _run_async(fetch())


def get_macd_sync(ticker: str) -> Optional[pd.DataFrame]:
    """Synchronous wrapper to get MACD."""
    async def fetch():
        provider = PolygonProvider()
        try:
            return await provider.get_macd(ticker)
        finally:
            await provider.close()

    return _run_async(fetch())


def get_technical_summary_sync(ticker: str) -> Dict:
    """Synchronous wrapper to get technical analysis summary."""
    async def fetch():
        provider = PolygonProvider()
        try:
            return await provider.get_technical_summary(ticker)
        finally:
            await provider.close()

    return _run_async(fetch())


# =============================================================================
# TICKER UNIVERSE SYNC WRAPPERS
# =============================================================================

def get_tickers_sync(
    ticker_type: str = 'CS',
    market: str = 'stocks',
    exchange: str = None,
    limit: int = 1000,
) -> List[Dict]:
    """Synchronous wrapper to get tickers."""
    async def fetch():
        provider = PolygonProvider()
        try:
            return await provider.get_tickers(ticker_type, market, exchange, limit=limit)
        finally:
            await provider.close()

    return _run_async(fetch())


def get_us_stocks_sync(exchange: str = None, limit: int = 1000) -> List[str]:
    """Synchronous wrapper to get US stock tickers."""
    async def fetch():
        provider = PolygonProvider()
        try:
            return await provider.get_us_stocks(exchange=exchange, limit=limit)
        finally:
            await provider.close()

    return _run_async(fetch())


def get_nasdaq_stocks_sync(limit: int = 1000) -> List[str]:
    """Synchronous wrapper to get NASDAQ stocks."""
    async def fetch():
        provider = PolygonProvider()
        try:
            return await provider.get_nasdaq_stocks(limit)
        finally:
            await provider.close()

    return _run_async(fetch())


def get_nyse_stocks_sync(limit: int = 1000) -> List[str]:
    """Synchronous wrapper to get NYSE stocks."""
    async def fetch():
        provider = PolygonProvider()
        try:
            return await provider.get_nyse_stocks(limit)
        finally:
            await provider.close()

    return _run_async(fetch())


def get_etfs_sync(limit: int = 500) -> List[Dict]:
    """Synchronous wrapper to get ETFs."""
    async def fetch():
        provider = PolygonProvider()
        try:
            return await provider.get_etfs(limit)
        finally:
            await provider.close()

    return _run_async(fetch())


def search_tickers_sync(query: str, limit: int = 20) -> List[Dict]:
    """Synchronous wrapper to search tickers."""
    async def fetch():
        provider = PolygonProvider()
        try:
            return await provider.search_tickers(query, limit)
        finally:
            await provider.close()

    return _run_async(fetch())


def is_polygon_configured() -> bool:
    """Check if Polygon API is configured."""
    return bool(os.environ.get('POLYGON_API_KEY', ''))
