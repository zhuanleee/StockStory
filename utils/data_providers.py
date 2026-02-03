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

        Note: news-sentiment endpoint requires premium. Use company-news instead
        and derive sentiment from headlines.

        Returns: {
            'buzz': {'articlesInLastWeek': int, 'buzz': float},
            'sentiment': {'bearishPercent': float, 'bullishPercent': float}
        }
        """
        # news-sentiment requires premium, use company-news instead
        try:
            news = FinnhubProvider.get_company_news(ticker, days_back=7)
            if not news:
                return None

            # Simple sentiment analysis from headlines
            bullish_words = ['beat', 'surge', 'gain', 'rise', 'jump', 'high', 'record', 'growth', 'strong', 'upgrade', 'buy']
            bearish_words = ['miss', 'drop', 'fall', 'low', 'down', 'weak', 'concern', 'risk', 'decline', 'downgrade', 'sell']

            bullish_count = 0
            bearish_count = 0

            for article in news[:20]:
                headline = (article.get('headline', '') + ' ' + article.get('summary', '')).lower()
                if any(w in headline for w in bullish_words):
                    bullish_count += 1
                if any(w in headline for w in bearish_words):
                    bearish_count += 1

            total = bullish_count + bearish_count
            if total > 0:
                bullish_pct = bullish_count / total
                bearish_pct = bearish_count / total
            else:
                bullish_pct = 0.5
                bearish_pct = 0.5

            return {
                'buzz': {'articlesInLastWeek': len(news), 'buzz': len(news) / 10.0},
                'sentiment': {'bullishPercent': bullish_pct, 'bearishPercent': bearish_pct}
            }
        except Exception:
            return None

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
        # Interest Rates
        'fed_funds_rate': 'FEDFUNDS',
        'treasury_10y': 'DGS10',
        'treasury_2y': 'DGS2',
        'treasury_3m': 'DGS3MO',
        'treasury_30y': 'DGS30',
        # Employment
        'unemployment': 'UNRATE',
        'initial_claims': 'ICSA',
        'continuing_claims': 'CCSA',
        'nonfarm_payrolls': 'PAYEMS',
        # Inflation
        'cpi': 'CPIAUCSL',
        'cpi_yoy': 'CPIAUCSL',
        'core_cpi': 'CPILFESL',
        'pce': 'PCE',
        'core_pce': 'PCEPILFE',
        # Growth
        'gdp': 'GDP',
        'real_gdp': 'A191RL1Q225SBEA',
        'industrial_production': 'INDPRO',
        # Consumer
        'consumer_sentiment': 'UMCSENT',
        'retail_sales': 'RSAFS',
        'housing_starts': 'HOUST',
        # Credit & Liquidity
        'high_yield_spread': 'BAMLH0A0HYM2',
        'm2_money': 'M2SL',
        'fed_balance_sheet': 'WALCL',
        # Market
        'sp500': 'SP500',
        'vix': 'VIXCLS',
    }

    # Series metadata for tooltips and interpretation
    SERIES_META = {
        'fed_funds_rate': {
            'name': 'Fed Funds Rate',
            'tooltip': 'The interest rate banks charge each other for overnight loans. Set by the Federal Reserve to control monetary policy.',
            'unit': '%',
            'good_direction': None,  # Context dependent
        },
        'treasury_10y': {
            'name': '10-Year Treasury',
            'tooltip': 'Yield on 10-year US government bonds. Key benchmark for mortgages and long-term rates.',
            'unit': '%',
            'good_direction': None,
        },
        'treasury_2y': {
            'name': '2-Year Treasury',
            'tooltip': 'Yield on 2-year US government bonds. Reflects near-term Fed rate expectations.',
            'unit': '%',
            'good_direction': None,
        },
        'unemployment': {
            'name': 'Unemployment Rate',
            'tooltip': 'Percentage of labor force without jobs. Below 4% is considered full employment.',
            'unit': '%',
            'good_direction': 'down',
            'thresholds': {'good': 4.0, 'warning': 5.5, 'danger': 7.0},
        },
        'initial_claims': {
            'name': 'Initial Jobless Claims',
            'tooltip': 'Weekly new unemployment filings. Leading indicator - rising claims signal economic weakness.',
            'unit': 'K',
            'good_direction': 'down',
            'thresholds': {'good': 220, 'warning': 280, 'danger': 350},
        },
        'cpi_yoy': {
            'name': 'CPI Inflation',
            'tooltip': 'Consumer Price Index year-over-year change. Fed targets 2% inflation.',
            'unit': '%',
            'good_direction': 'target',
            'target': 2.0,
            'thresholds': {'good': 2.5, 'warning': 4.0, 'danger': 6.0},
        },
        'high_yield_spread': {
            'name': 'High Yield Spread',
            'tooltip': 'Difference between junk bond and treasury yields. Widening spread = credit stress/risk-off.',
            'unit': 'bp',
            'good_direction': 'down',
            'thresholds': {'good': 350, 'warning': 500, 'danger': 700},
        },
        'm2_money': {
            'name': 'M2 Money Supply',
            'tooltip': 'Total money in circulation including savings. Growth rate indicates liquidity conditions.',
            'unit': 'T$',
            'good_direction': None,
        },
        'consumer_sentiment': {
            'name': 'Consumer Sentiment',
            'tooltip': 'University of Michigan survey of consumer confidence. Above 80 is healthy.',
            'unit': '',
            'good_direction': 'up',
            'thresholds': {'good': 80, 'warning': 65, 'danger': 55},
        },
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
    def get_yoy_change(series_id: str) -> Optional[Tuple[str, float]]:
        """
        Calculate year-over-year percentage change for a series.
        Used for index values like CPI that need YoY transformation.
        """
        from datetime import datetime
        from dateutil.relativedelta import relativedelta

        # Get 15 months of data to ensure we have a year-ago comparison
        observations = FREDProvider.get_series(series_id, limit=20)
        if len(observations) < 12:
            return None

        try:
            # Filter out entries with invalid values (FRED uses "." for missing data)
            valid_obs = []
            for obs in observations:
                val = obs.get('value', '.')
                if val != '.' and val:
                    try:
                        valid_obs.append({
                            'date': obs.get('date'),
                            'value': float(val)
                        })
                    except (ValueError, TypeError):
                        continue

            if len(valid_obs) < 12:
                return None

            # Get current value (newest)
            current = valid_obs[0]['value']
            current_date = valid_obs[0]['date']

            # Parse current date and find year-ago date
            current_dt = datetime.strptime(current_date, '%Y-%m-%d')
            target_dt = current_dt - relativedelta(years=1)
            target_date_str = target_dt.strftime('%Y-%m-%d')

            # Find closest match to year-ago date
            year_ago = None
            for obs in valid_obs:
                obs_dt = datetime.strptime(obs['date'], '%Y-%m-%d')
                # Look for a date within 45 days of target (to handle monthly data)
                diff = abs((obs_dt - target_dt).days)
                if diff <= 45:
                    year_ago = obs['value']
                    break

            if year_ago and year_ago > 0:
                yoy_change = ((current - year_ago) / year_ago) * 100
                return (current_date, round(yoy_change, 2))

        except Exception as e:
            logger.error(f"Error calculating YoY change: {e}")
            return None
        return None

    @staticmethod
    def get_economic_dashboard() -> Dict[str, Any]:
        """
        Get comprehensive economic indicators for market analysis.

        Returns dict with latest values, interpretations, and alerts.
        """
        dashboard = {
            'indicators': {},
            'yield_curve': {},
            'alerts': [],
            'overall_score': 50,
            'overall_label': 'Neutral',
            'timestamp': datetime.now().isoformat()
        }

        # Key series to fetch
        key_series = [
            'fed_funds_rate', 'treasury_10y', 'treasury_2y',
            'unemployment', 'initial_claims', 'cpi_yoy',
            'high_yield_spread', 'consumer_sentiment', 'm2_money'
        ]

        scores = []

        for name in key_series:
            series_id = FREDProvider.SERIES.get(name)
            if series_id:
                # Use YoY change for CPI (it's an index, not a rate)
                if name == 'cpi_yoy':
                    result = FREDProvider.get_yoy_change(series_id)
                else:
                    result = FREDProvider.get_latest_value(series_id)
                if result:
                    value = result[1]
                    meta = FREDProvider.SERIES_META.get(name, {})

                    # Format value based on unit
                    unit = meta.get('unit', '')
                    if unit == 'K':
                        display_value = f"{value/1000:.0f}K" if value > 1000 else f"{value:.0f}"
                    elif unit == 'T$':
                        display_value = f"${value/1000:.1f}T" if value > 1000 else f"${value:.1f}B"
                    elif unit == 'bp':
                        display_value = f"{value*100:.0f}bp"
                    elif unit == '%':
                        display_value = f"{value:.2f}%"
                    else:
                        display_value = f"{value:.1f}"

                    # Calculate status
                    status = 'neutral'
                    status_emoji = '🟡'
                    thresholds = meta.get('thresholds', {})

                    if thresholds:
                        good_dir = meta.get('good_direction')
                        if good_dir == 'down':
                            if value <= thresholds.get('good', float('inf')):
                                status, status_emoji = 'good', '🟢'
                            elif value >= thresholds.get('danger', float('inf')):
                                status, status_emoji = 'danger', '🔴'
                            elif value >= thresholds.get('warning', float('inf')):
                                status, status_emoji = 'warning', '🟠'
                        elif good_dir == 'up':
                            if value >= thresholds.get('good', 0):
                                status, status_emoji = 'good', '🟢'
                            elif value <= thresholds.get('danger', 0):
                                status, status_emoji = 'danger', '🔴'
                            elif value <= thresholds.get('warning', 0):
                                status, status_emoji = 'warning', '🟠'
                        elif good_dir == 'target':
                            target = meta.get('target', 2.0)
                            diff = abs(value - target)
                            if diff <= 0.5:
                                status, status_emoji = 'good', '🟢'
                            elif value >= thresholds.get('danger', float('inf')):
                                status, status_emoji = 'danger', '🔴'
                            elif value >= thresholds.get('warning', float('inf')):
                                status, status_emoji = 'warning', '🟠'

                    # Score contribution (0-100)
                    if status == 'good':
                        scores.append(80)
                    elif status == 'danger':
                        scores.append(20)
                    elif status == 'warning':
                        scores.append(40)
                    else:
                        scores.append(50)

                    dashboard['indicators'][name] = {
                        'value': value,
                        'display': display_value,
                        'date': result[0],
                        'name': meta.get('name', name),
                        'tooltip': meta.get('tooltip', ''),
                        'status': status,
                        'emoji': status_emoji,
                        'unit': unit
                    }

                    # Add alerts for danger conditions
                    if status == 'danger':
                        dashboard['alerts'].append({
                            'indicator': meta.get('name', name),
                            'message': f"{meta.get('name', name)} at {display_value} - elevated risk",
                            'severity': 'high'
                        })

        # Calculate yield curve
        t10 = dashboard['indicators'].get('treasury_10y', {}).get('value')
        t2 = dashboard['indicators'].get('treasury_2y', {}).get('value')

        if t10 is not None and t2 is not None:
            spread = t10 - t2
            inverted = spread < 0

            if inverted:
                yc_status, yc_emoji = 'danger', '🔴'
                scores.append(10)
                dashboard['alerts'].append({
                    'indicator': 'Yield Curve',
                    'message': f'Yield curve INVERTED ({spread:.2f}%) - recession warning',
                    'severity': 'high'
                })
            elif spread < 0.25:
                yc_status, yc_emoji = 'warning', '🟠'
                scores.append(35)
            elif spread > 1.0:
                yc_status, yc_emoji = 'good', '🟢'
                scores.append(80)
            else:
                yc_status, yc_emoji = 'neutral', '🟡'
                scores.append(55)

            dashboard['yield_curve'] = {
                'spread': round(spread, 2),
                'display': f"{spread:+.2f}%",
                'inverted': inverted,
                'status': yc_status,
                'emoji': yc_emoji,
                'name': 'Yield Curve (10Y-2Y)',
                'tooltip': 'Spread between 10-year and 2-year Treasury yields. Inverted curve (negative) historically precedes recessions by 12-18 months.'
            }

        # Calculate overall score
        if scores:
            overall = sum(scores) / len(scores)
            dashboard['overall_score'] = round(overall, 0)

            if overall >= 70:
                dashboard['overall_label'] = 'Healthy'
                dashboard['overall_color'] = '#22c55e'
            elif overall >= 55:
                dashboard['overall_label'] = 'Stable'
                dashboard['overall_color'] = '#84cc16'
            elif overall >= 40:
                dashboard['overall_label'] = 'Cautious'
                dashboard['overall_color'] = '#eab308'
            elif overall >= 25:
                dashboard['overall_label'] = 'Stressed'
                dashboard['overall_color'] = '#f97316'
            else:
                dashboard['overall_label'] = 'Risk-Off'
                dashboard['overall_color'] = '#ef4444'

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
