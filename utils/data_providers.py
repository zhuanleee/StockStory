"""
High-accuracy data providers module.

Free tier data sources with better reliability than web scraping:
- Finnhub: Real-time quotes, news, sentiment (60 req/min)
- Tiingo: EOD data, news (1000 req/day)
- Alpha Vantage: Fundamentals, technicals (25 req/day)
- SEC EDGAR: Official filings, insider trades (unlimited)
- FRED: Economic indicators (unlimited)
"""

import os
import requests
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from functools import lru_cache
import time

logger = logging.getLogger(__name__)

# =============================================================================
# API CONFIGURATION
# =============================================================================

class DataProviderConfig:
    """Configuration for data providers."""

    # API Keys (from environment)
    FINNHUB_API_KEY = os.environ.get('FINNHUB_API_KEY', '')
    TIINGO_API_KEY = os.environ.get('TIINGO_API_KEY', '')
    ALPHA_VANTAGE_API_KEY = os.environ.get('ALPHA_VANTAGE_API_KEY', '')
    FRED_API_KEY = os.environ.get('FRED_API_KEY', '')

    # Base URLs
    FINNHUB_BASE = 'https://finnhub.io/api/v1'
    TIINGO_BASE = 'https://api.tiingo.com'
    ALPHA_VANTAGE_BASE = 'https://www.alphavantage.co/query'
    SEC_EDGAR_BASE = 'https://data.sec.gov'
    FRED_BASE = 'https://api.stlouisfed.org/fred'

    # Rate limits (requests per minute)
    FINNHUB_RATE_LIMIT = 60
    TIINGO_RATE_LIMIT = 50
    ALPHA_VANTAGE_RATE_LIMIT = 5

    # Timeouts
    REQUEST_TIMEOUT = 10


# =============================================================================
# RATE LIMITER
# =============================================================================

class RateLimiter:
    """Simple rate limiter for API calls."""

    def __init__(self, calls_per_minute: int):
        self.calls_per_minute = calls_per_minute
        self.calls = []

    def wait_if_needed(self):
        """Wait if rate limit would be exceeded."""
        now = time.time()
        # Remove calls older than 1 minute
        self.calls = [t for t in self.calls if now - t < 60]

        if len(self.calls) >= self.calls_per_minute:
            sleep_time = 60 - (now - self.calls[0])
            if sleep_time > 0:
                logger.debug(f"Rate limit reached, sleeping {sleep_time:.1f}s")
                time.sleep(sleep_time)

        self.calls.append(time.time())


# Rate limiters for each provider
_finnhub_limiter = RateLimiter(DataProviderConfig.FINNHUB_RATE_LIMIT)
_tiingo_limiter = RateLimiter(DataProviderConfig.TIINGO_RATE_LIMIT)
_alpha_vantage_limiter = RateLimiter(DataProviderConfig.ALPHA_VANTAGE_RATE_LIMIT)


# =============================================================================
# FINNHUB PROVIDER (Real-time quotes, news, sentiment)
# =============================================================================

class FinnhubProvider:
    """
    Finnhub.io data provider.

    Free tier: 60 API calls/minute
    Data: Real-time quotes, company news, market sentiment, earnings
    """

    @staticmethod
    def is_configured() -> bool:
        """Check if Finnhub API key is configured."""
        return bool(DataProviderConfig.FINNHUB_API_KEY)

    @staticmethod
    def _request(endpoint: str, params: dict = None) -> Optional[dict]:
        """Make authenticated request to Finnhub."""
        if not FinnhubProvider.is_configured():
            logger.warning("Finnhub API key not configured")
            return None

        _finnhub_limiter.wait_if_needed()

        params = params or {}
        params['token'] = DataProviderConfig.FINNHUB_API_KEY

        try:
            url = f"{DataProviderConfig.FINNHUB_BASE}/{endpoint}"
            response = requests.get(
                url,
                params=params,
                timeout=DataProviderConfig.REQUEST_TIMEOUT
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Finnhub request failed: {e}")
            return None

    @staticmethod
    def get_quote(ticker: str) -> Optional[Dict]:
        """
        Get real-time quote for a ticker.

        Returns: {
            'c': current_price,
            'h': high,
            'l': low,
            'o': open,
            'pc': previous_close,
            't': timestamp,
            'dp': percent_change
        }
        """
        data = FinnhubProvider._request('quote', {'symbol': ticker.upper()})
        if data and data.get('c'):
            data['dp'] = round((data['c'] - data['pc']) / data['pc'] * 100, 2) if data.get('pc') else 0
            return data
        return None

    @staticmethod
    def get_company_news(ticker: str, days_back: int = 7) -> List[Dict]:
        """
        Get company news for a ticker.

        Returns list of: {
            'headline': str,
            'summary': str,
            'source': str,
            'url': str,
            'datetime': timestamp,
            'category': str
        }
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)

        data = FinnhubProvider._request('company-news', {
            'symbol': ticker.upper(),
            'from': start_date.strftime('%Y-%m-%d'),
            'to': end_date.strftime('%Y-%m-%d')
        })

        return data if isinstance(data, list) else []

    @staticmethod
    def get_market_news(category: str = 'general') -> List[Dict]:
        """
        Get general market news.

        Categories: general, forex, crypto, merger
        """
        data = FinnhubProvider._request('news', {'category': category})
        return data if isinstance(data, list) else []

    @staticmethod
    def get_sentiment(ticker: str) -> Optional[Dict]:
        """
        Get social sentiment for a ticker.

        Returns: {
            'buzz': {'articlesInLastWeek': int, 'buzz': float},
            'sentiment': {'bearishPercent': float, 'bullishPercent': float}
        }
        """
        return FinnhubProvider._request('news-sentiment', {'symbol': ticker.upper()})

    @staticmethod
    def get_earnings_calendar(from_date: str = None, to_date: str = None) -> List[Dict]:
        """Get upcoming earnings calendar."""
        params = {}
        if from_date:
            params['from'] = from_date
        if to_date:
            params['to'] = to_date

        data = FinnhubProvider._request('calendar/earnings', params)
        return data.get('earningsCalendar', []) if data else []

    @staticmethod
    def get_recommendation_trends(ticker: str) -> List[Dict]:
        """
        Get analyst recommendation trends.

        Returns list of: {
            'buy': int, 'hold': int, 'sell': int,
            'strongBuy': int, 'strongSell': int,
            'period': str
        }
        """
        data = FinnhubProvider._request('stock/recommendation', {'symbol': ticker.upper()})
        return data if isinstance(data, list) else []

    @staticmethod
    def get_insider_transactions(ticker: str) -> List[Dict]:
        """Get insider transactions for a ticker."""
        data = FinnhubProvider._request('stock/insider-transactions', {'symbol': ticker.upper()})
        return data.get('data', []) if data else []

    @staticmethod
    def get_price_target(ticker: str) -> Optional[Dict]:
        """
        Get analyst price targets.

        Returns: {
            'targetHigh': float,
            'targetLow': float,
            'targetMean': float,
            'targetMedian': float
        }
        """
        return FinnhubProvider._request('stock/price-target', {'symbol': ticker.upper()})


# =============================================================================
# TIINGO PROVIDER (EOD data, fundamentals, news)
# =============================================================================

class TiingoProvider:
    """
    Tiingo data provider.

    Free tier: 1000 API calls/day
    Data: EOD prices, fundamentals, news
    """

    @staticmethod
    def is_configured() -> bool:
        """Check if Tiingo API key is configured."""
        return bool(DataProviderConfig.TIINGO_API_KEY)

    @staticmethod
    def _request(endpoint: str, params: dict = None) -> Optional[Any]:
        """Make authenticated request to Tiingo."""
        if not TiingoProvider.is_configured():
            logger.warning("Tiingo API key not configured")
            return None

        _tiingo_limiter.wait_if_needed()

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Token {DataProviderConfig.TIINGO_API_KEY}'
        }

        try:
            url = f"{DataProviderConfig.TIINGO_BASE}/{endpoint}"
            response = requests.get(
                url,
                headers=headers,
                params=params,
                timeout=DataProviderConfig.REQUEST_TIMEOUT
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Tiingo request failed: {e}")
            return None

    @staticmethod
    def get_ticker_metadata(ticker: str) -> Optional[Dict]:
        """
        Get ticker metadata.

        Returns: {
            'ticker': str,
            'name': str,
            'description': str,
            'startDate': str,
            'endDate': str,
            'exchangeCode': str
        }
        """
        return TiingoProvider._request(f'tiingo/daily/{ticker.upper()}')

    @staticmethod
    def get_eod_prices(ticker: str, start_date: str = None, end_date: str = None) -> List[Dict]:
        """
        Get end-of-day prices.

        Returns list of: {
            'date': str,
            'open': float,
            'high': float,
            'low': float,
            'close': float,
            'volume': int,
            'adjOpen': float,
            'adjHigh': float,
            'adjLow': float,
            'adjClose': float,
            'adjVolume': int
        }
        """
        params = {}
        if start_date:
            params['startDate'] = start_date
        if end_date:
            params['endDate'] = end_date

        data = TiingoProvider._request(f'tiingo/daily/{ticker.upper()}/prices', params)
        return data if isinstance(data, list) else []

    @staticmethod
    def get_realtime_price(ticker: str) -> Optional[Dict]:
        """Get real-time IEX price data."""
        data = TiingoProvider._request(f'iex/{ticker.upper()}')
        return data[0] if data and isinstance(data, list) else None

    @staticmethod
    def get_news(tickers: List[str] = None, limit: int = 20) -> List[Dict]:
        """
        Get news articles.

        Returns list of: {
            'title': str,
            'description': str,
            'url': str,
            'source': str,
            'publishedDate': str,
            'tickers': List[str]
        }
        """
        params = {'limit': limit}
        if tickers:
            params['tickers'] = ','.join(t.upper() for t in tickers)

        data = TiingoProvider._request('tiingo/news', params)
        return data if isinstance(data, list) else []


# =============================================================================
# ALPHA VANTAGE PROVIDER (Fundamentals, technicals)
# =============================================================================

class AlphaVantageProvider:
    """
    Alpha Vantage data provider.

    Free tier: 25 API calls/day
    Data: Fundamentals, technical indicators, earnings
    """

    @staticmethod
    def is_configured() -> bool:
        """Check if Alpha Vantage API key is configured."""
        return bool(DataProviderConfig.ALPHA_VANTAGE_API_KEY)

    @staticmethod
    def _request(function: str, params: dict = None) -> Optional[Dict]:
        """Make authenticated request to Alpha Vantage."""
        if not AlphaVantageProvider.is_configured():
            logger.warning("Alpha Vantage API key not configured")
            return None

        _alpha_vantage_limiter.wait_if_needed()

        params = params or {}
        params['function'] = function
        params['apikey'] = DataProviderConfig.ALPHA_VANTAGE_API_KEY

        try:
            response = requests.get(
                DataProviderConfig.ALPHA_VANTAGE_BASE,
                params=params,
                timeout=DataProviderConfig.REQUEST_TIMEOUT
            )
            response.raise_for_status()
            data = response.json()

            # Check for API error messages
            if 'Error Message' in data or 'Note' in data:
                logger.warning(f"Alpha Vantage: {data.get('Error Message') or data.get('Note')}")
                return None

            return data
        except requests.RequestException as e:
            logger.error(f"Alpha Vantage request failed: {e}")
            return None

    @staticmethod
    def get_company_overview(ticker: str) -> Optional[Dict]:
        """
        Get company fundamentals.

        Returns: {
            'Symbol': str,
            'Name': str,
            'Description': str,
            'Exchange': str,
            'Sector': str,
            'Industry': str,
            'MarketCapitalization': str,
            'PERatio': str,
            'EPS': str,
            '52WeekHigh': str,
            '52WeekLow': str,
            ...
        }
        """
        return AlphaVantageProvider._request('OVERVIEW', {'symbol': ticker.upper()})

    @staticmethod
    def get_income_statement(ticker: str) -> Optional[Dict]:
        """Get income statement data."""
        return AlphaVantageProvider._request('INCOME_STATEMENT', {'symbol': ticker.upper()})

    @staticmethod
    def get_balance_sheet(ticker: str) -> Optional[Dict]:
        """Get balance sheet data."""
        return AlphaVantageProvider._request('BALANCE_SHEET', {'symbol': ticker.upper()})

    @staticmethod
    def get_earnings(ticker: str) -> Optional[Dict]:
        """
        Get earnings data.

        Returns: {
            'annualEarnings': List[Dict],
            'quarterlyEarnings': List[Dict]
        }
        """
        return AlphaVantageProvider._request('EARNINGS', {'symbol': ticker.upper()})

    @staticmethod
    def get_sma(ticker: str, interval: str = 'daily', period: int = 20) -> Optional[Dict]:
        """Get Simple Moving Average."""
        return AlphaVantageProvider._request('SMA', {
            'symbol': ticker.upper(),
            'interval': interval,
            'time_period': period,
            'series_type': 'close'
        })

    @staticmethod
    def get_rsi(ticker: str, interval: str = 'daily', period: int = 14) -> Optional[Dict]:
        """Get Relative Strength Index."""
        return AlphaVantageProvider._request('RSI', {
            'symbol': ticker.upper(),
            'interval': interval,
            'time_period': period,
            'series_type': 'close'
        })

    @staticmethod
    def get_macd(ticker: str, interval: str = 'daily') -> Optional[Dict]:
        """Get MACD indicator."""
        return AlphaVantageProvider._request('MACD', {
            'symbol': ticker.upper(),
            'interval': interval,
            'series_type': 'close'
        })


# =============================================================================
# SEC EDGAR PROVIDER (Official filings, insider trades)
# =============================================================================

class SECEdgarProvider:
    """
    SEC EDGAR data provider.

    Free tier: Unlimited (public government data)
    Data: Official filings, insider transactions, institutional holdings
    """

    # SEC requires User-Agent header
    HEADERS = {
        'User-Agent': 'StockScannerBot/2.0 (contact@example.com)',
        'Accept-Encoding': 'gzip, deflate'
    }

    @staticmethod
    def _request(endpoint: str) -> Optional[Any]:
        """Make request to SEC EDGAR."""
        try:
            url = f"{DataProviderConfig.SEC_EDGAR_BASE}/{endpoint}"
            response = requests.get(
                url,
                headers=SECEdgarProvider.HEADERS,
                timeout=DataProviderConfig.REQUEST_TIMEOUT
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"SEC EDGAR request failed: {e}")
            return None

    @staticmethod
    def get_company_cik(ticker: str) -> Optional[str]:
        """Get CIK number for a ticker."""
        try:
            url = "https://www.sec.gov/files/company_tickers.json"
            response = requests.get(url, headers=SECEdgarProvider.HEADERS, timeout=10)
            response.raise_for_status()
            data = response.json()

            ticker_upper = ticker.upper()
            for item in data.values():
                if item.get('ticker') == ticker_upper:
                    # CIK needs to be zero-padded to 10 digits
                    return str(item.get('cik_str', '')).zfill(10)
            return None
        except Exception as e:
            logger.error(f"Failed to get CIK for {ticker}: {e}")
            return None

    @staticmethod
    def get_company_filings(ticker: str) -> Optional[Dict]:
        """
        Get recent company filings.

        Returns filings metadata including 10-K, 10-Q, 8-K, etc.
        """
        cik = SECEdgarProvider.get_company_cik(ticker)
        if not cik:
            return None

        return SECEdgarProvider._request(f'submissions/CIK{cik}.json')

    @staticmethod
    def get_insider_transactions(ticker: str, limit: int = 50) -> List[Dict]:
        """
        Get insider transactions from Form 4 filings.

        Returns list of insider buys/sells with details.
        """
        filings = SECEdgarProvider.get_company_filings(ticker)
        if not filings:
            return []

        # Filter for Form 4 filings
        recent = filings.get('filings', {}).get('recent', {})
        forms = recent.get('form', [])
        dates = recent.get('filingDate', [])
        accessions = recent.get('accessionNumber', [])

        form4_filings = []
        for i, form in enumerate(forms[:100]):  # Check last 100 filings
            if form == '4':
                form4_filings.append({
                    'form': form,
                    'filingDate': dates[i] if i < len(dates) else None,
                    'accessionNumber': accessions[i] if i < len(accessions) else None
                })
            if len(form4_filings) >= limit:
                break

        return form4_filings

    @staticmethod
    def get_institutional_holdings(ticker: str) -> List[Dict]:
        """
        Get institutional holdings from 13F filings.

        Returns list of major institutional holders.
        """
        filings = SECEdgarProvider.get_company_filings(ticker)
        if not filings:
            return []

        # Filter for 13F filings
        recent = filings.get('filings', {}).get('recent', {})
        forms = recent.get('form', [])
        dates = recent.get('filingDate', [])

        holdings = []
        for i, form in enumerate(forms[:50]):
            if '13F' in form:
                holdings.append({
                    'form': form,
                    'filingDate': dates[i] if i < len(dates) else None
                })

        return holdings[:20]


# =============================================================================
# FRED PROVIDER (Economic indicators)
# =============================================================================

class FREDProvider:
    """
    Federal Reserve Economic Data provider.

    Free tier: Unlimited with API key
    Data: Economic indicators, interest rates, employment, GDP
    """

    # Common series IDs
    SERIES = {
        'fed_funds_rate': 'FEDFUNDS',
        'unemployment': 'UNRATE',
        'cpi': 'CPIAUCSL',
        'gdp': 'GDP',
        'treasury_10y': 'DGS10',
        'treasury_2y': 'DGS2',
        'sp500': 'SP500',
        'vix': 'VIXCLS',
        'consumer_sentiment': 'UMCSENT',
        'industrial_production': 'INDPRO',
        'housing_starts': 'HOUST',
        'retail_sales': 'RSAFS',
        'pce': 'PCE',
        'core_pce': 'PCEPILFE',
        'm2_money': 'M2SL',
        'initial_claims': 'ICSA'
    }

    @staticmethod
    def is_configured() -> bool:
        """Check if FRED API key is configured."""
        return bool(DataProviderConfig.FRED_API_KEY)

    @staticmethod
    def _request(endpoint: str, params: dict = None) -> Optional[Dict]:
        """Make authenticated request to FRED."""
        if not FREDProvider.is_configured():
            logger.warning("FRED API key not configured")
            return None

        params = params or {}
        params['api_key'] = DataProviderConfig.FRED_API_KEY
        params['file_type'] = 'json'

        try:
            url = f"{DataProviderConfig.FRED_BASE}/{endpoint}"
            response = requests.get(
                url,
                params=params,
                timeout=DataProviderConfig.REQUEST_TIMEOUT
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"FRED request failed: {e}")
            return None

    @staticmethod
    def get_series(series_id: str, limit: int = 100) -> List[Dict]:
        """
        Get time series data.

        Returns list of: {
            'date': str,
            'value': str
        }
        """
        data = FREDProvider._request('series/observations', {
            'series_id': series_id,
            'sort_order': 'desc',
            'limit': limit
        })

        return data.get('observations', []) if data else []

    @staticmethod
    def get_latest_value(series_id: str) -> Optional[Tuple[str, float]]:
        """Get most recent value for a series."""
        observations = FREDProvider.get_series(series_id, limit=1)
        if observations:
            obs = observations[0]
            try:
                return (obs.get('date'), float(obs.get('value', 0)))
            except (ValueError, TypeError):
                return None
        return None

    @staticmethod
    def get_economic_dashboard() -> Dict[str, Any]:
        """
        Get key economic indicators for market analysis.

        Returns dict with latest values for major indicators.
        """
        dashboard = {}

        key_series = [
            'fed_funds_rate', 'unemployment', 'treasury_10y',
            'treasury_2y', 'vix', 'consumer_sentiment'
        ]

        for name in key_series:
            series_id = FREDProvider.SERIES.get(name)
            if series_id:
                result = FREDProvider.get_latest_value(series_id)
                if result:
                    dashboard[name] = {
                        'date': result[0],
                        'value': result[1]
                    }

        # Calculate yield curve (10y - 2y spread)
        if 'treasury_10y' in dashboard and 'treasury_2y' in dashboard:
            spread = dashboard['treasury_10y']['value'] - dashboard['treasury_2y']['value']
            dashboard['yield_curve_spread'] = {
                'value': round(spread, 2),
                'inverted': spread < 0
            }

        return dashboard


# =============================================================================
# UNIFIED DATA FETCHER (with fallbacks)
# =============================================================================

class UnifiedDataFetcher:
    """
    Unified interface for fetching data with automatic fallbacks.

    Priority order:
    1. Finnhub (real-time)
    2. Tiingo (reliable EOD)
    3. Alpha Vantage (fundamentals)
    4. yfinance (legacy fallback)
    """

    @staticmethod
    def get_quote(ticker: str) -> Optional[Dict]:
        """
        Get current quote with fallback chain.

        Returns standardized: {
            'price': float,
            'change': float,
            'change_percent': float,
            'high': float,
            'low': float,
            'open': float,
            'prev_close': float,
            'volume': int,
            'source': str
        }
        """
        # Try Finnhub first (real-time)
        if FinnhubProvider.is_configured():
            data = FinnhubProvider.get_quote(ticker)
            if data and data.get('c'):
                return {
                    'price': data['c'],
                    'change': round(data['c'] - data['pc'], 2),
                    'change_percent': data.get('dp', 0),
                    'high': data.get('h'),
                    'low': data.get('l'),
                    'open': data.get('o'),
                    'prev_close': data.get('pc'),
                    'volume': None,  # Not in Finnhub quote
                    'source': 'finnhub'
                }

        # Try Tiingo (IEX real-time)
        if TiingoProvider.is_configured():
            data = TiingoProvider.get_realtime_price(ticker)
            if data:
                return {
                    'price': data.get('last') or data.get('tngoLast'),
                    'change': None,
                    'change_percent': None,
                    'high': data.get('high'),
                    'low': data.get('low'),
                    'open': data.get('open'),
                    'prev_close': data.get('prevClose'),
                    'volume': data.get('volume'),
                    'source': 'tiingo'
                }

        # Fallback to yfinance
        try:
            import yfinance as yf
            stock = yf.Ticker(ticker)
            info = stock.fast_info
            return {
                'price': info.last_price,
                'change': None,
                'change_percent': None,
                'high': info.day_high,
                'low': info.day_low,
                'open': info.open,
                'prev_close': info.previous_close,
                'volume': info.last_volume,
                'source': 'yfinance'
            }
        except Exception as e:
            logger.error(f"All quote sources failed for {ticker}: {e}")
            return None

    @staticmethod
    def get_news(ticker: str = None, limit: int = 20) -> List[Dict]:
        """
        Get news with fallback chain.

        Returns standardized: [{
            'title': str,
            'summary': str,
            'source': str,
            'url': str,
            'published': str,
            'provider': str
        }]
        """
        news = []

        # Try Finnhub
        if FinnhubProvider.is_configured():
            if ticker:
                data = FinnhubProvider.get_company_news(ticker)
            else:
                data = FinnhubProvider.get_market_news()

            for item in data[:limit]:
                news.append({
                    'title': item.get('headline'),
                    'summary': item.get('summary'),
                    'source': item.get('source'),
                    'url': item.get('url'),
                    'published': datetime.fromtimestamp(item.get('datetime', 0)).isoformat() if item.get('datetime') else None,
                    'provider': 'finnhub'
                })

        # Supplement with Tiingo if needed
        if len(news) < limit and TiingoProvider.is_configured():
            tickers = [ticker] if ticker else None
            tiingo_news = TiingoProvider.get_news(tickers, limit - len(news))

            for item in tiingo_news:
                news.append({
                    'title': item.get('title'),
                    'summary': item.get('description'),
                    'source': item.get('source'),
                    'url': item.get('url'),
                    'published': item.get('publishedDate'),
                    'provider': 'tiingo'
                })

        return news[:limit]

    @staticmethod
    def get_sentiment(ticker: str) -> Optional[Dict]:
        """
        Get sentiment data.

        Returns: {
            'bullish': float (0-1),
            'bearish': float (0-1),
            'buzz': float,
            'source': str
        }
        """
        if FinnhubProvider.is_configured():
            data = FinnhubProvider.get_sentiment(ticker)
            if data and data.get('sentiment'):
                sentiment = data['sentiment']
                return {
                    'bullish': sentiment.get('bullishPercent', 0),
                    'bearish': sentiment.get('bearishPercent', 0),
                    'buzz': data.get('buzz', {}).get('buzz', 0),
                    'source': 'finnhub'
                }

        return None

    @staticmethod
    def get_insider_activity(ticker: str) -> List[Dict]:
        """
        Get insider transactions with fallback.

        Returns list of insider trades.
        """
        # Try Finnhub first
        if FinnhubProvider.is_configured():
            data = FinnhubProvider.get_insider_transactions(ticker)
            if data:
                return [{
                    'name': t.get('name'),
                    'shares': t.get('share'),
                    'value': t.get('transactionPrice'),
                    'type': t.get('transactionType'),
                    'date': t.get('transactionDate'),
                    'source': 'finnhub'
                } for t in data[:20]]

        # Fallback to SEC EDGAR
        sec_data = SECEdgarProvider.get_insider_transactions(ticker)
        if sec_data:
            return [{
                'form': t.get('form'),
                'date': t.get('filingDate'),
                'accession': t.get('accessionNumber'),
                'source': 'sec_edgar'
            } for t in sec_data]

        return []

    @staticmethod
    def get_fundamentals(ticker: str) -> Optional[Dict]:
        """
        Get company fundamentals.

        Returns: {
            'name': str,
            'sector': str,
            'industry': str,
            'market_cap': float,
            'pe_ratio': float,
            'eps': float,
            'dividend_yield': float,
            '52w_high': float,
            '52w_low': float,
            'source': str
        }
        """
        # Try Alpha Vantage (best fundamentals)
        if AlphaVantageProvider.is_configured():
            data = AlphaVantageProvider.get_company_overview(ticker)
            if data and data.get('Symbol'):
                return {
                    'name': data.get('Name'),
                    'sector': data.get('Sector'),
                    'industry': data.get('Industry'),
                    'market_cap': float(data.get('MarketCapitalization', 0)),
                    'pe_ratio': float(data.get('PERatio', 0)) if data.get('PERatio', 'None') != 'None' else None,
                    'eps': float(data.get('EPS', 0)) if data.get('EPS', 'None') != 'None' else None,
                    'dividend_yield': float(data.get('DividendYield', 0)) if data.get('DividendYield', 'None') != 'None' else None,
                    '52w_high': float(data.get('52WeekHigh', 0)),
                    '52w_low': float(data.get('52WeekLow', 0)),
                    'source': 'alpha_vantage'
                }

        # Fallback to Tiingo metadata
        if TiingoProvider.is_configured():
            data = TiingoProvider.get_ticker_metadata(ticker)
            if data:
                return {
                    'name': data.get('name'),
                    'description': data.get('description'),
                    'exchange': data.get('exchangeCode'),
                    'source': 'tiingo'
                }

        return None

    @staticmethod
    def get_economic_context() -> Dict:
        """Get economic indicators for market context."""
        if FREDProvider.is_configured():
            return FREDProvider.get_economic_dashboard()
        return {}


# =============================================================================
# PROVIDER STATUS CHECK
# =============================================================================

def check_provider_status() -> Dict[str, bool]:
    """Check which data providers are configured and available."""
    return {
        'finnhub': FinnhubProvider.is_configured(),
        'tiingo': TiingoProvider.is_configured(),
        'alpha_vantage': AlphaVantageProvider.is_configured(),
        'fred': FREDProvider.is_configured(),
        'sec_edgar': True  # Always available (no key needed)
    }


def get_available_providers() -> List[str]:
    """Get list of configured providers."""
    status = check_provider_status()
    return [name for name, available in status.items() if available]
