"""
Google Trends Intelligence - Retail Interest Signal
===================================================
Track search interest trends as retail FOMO indicator.

Google Trends shows when retail investors are searching for a stock,
indicating potential viral interest and FOMO buying.

Uses: pytrends library (no API key needed)

Usage:
    from src.intelligence.google_trends import get_trend_score

    # Get trend score for a ticker
    score = get_trend_score('NVDA')  # Returns 0-100

    # Check if stock is breaking out in search interest
    breakout = is_search_breakout('TSLA')
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from pathlib import Path
import json
import time

logger = logging.getLogger(__name__)

# Cache
DATA_DIR = Path("data/google_trends")
CACHE_FILE = DATA_DIR / "trends_cache.json"
CACHE_TTL = 3600  # 1 hour


def ensure_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class TrendData:
    """Google Trends data for a ticker."""
    ticker: str
    search_interest: int  # 0-100 (Google's normalized score)
    trend_direction: str  # rising, falling, stable
    is_breakout: bool  # True if recent spike >2x average
    relative_to_peak: float  # % of all-time peak search interest
    timestamp: str


class GoogleTrendsIntelligence:
    """
    Google Trends intelligence for retail interest tracking.
    """

    def __init__(self):
        ensure_data_dir()
        self._cache = self._load_cache()
        self._pytrends = None

    def _load_cache(self) -> Dict:
        """Load trends cache."""
        if CACHE_FILE.exists():
            try:
                with open(CACHE_FILE) as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load Google Trends cache: {e}")
        return {}

    def _save_cache(self):
        """Save trends cache."""
        try:
            with open(CACHE_FILE, 'w') as f:
                json.dump(self._cache, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save Google Trends cache: {e}")

    def _get_cached(self, key: str) -> Optional[Dict]:
        """Get cached data if still valid."""
        if key in self._cache:
            cached_time = self._cache[key].get('cached_at', 0)
            if time.time() - cached_time < CACHE_TTL:
                return self._cache[key].get('data')
        return None

    def _set_cached(self, key: str, data: Dict):
        """Cache data with timestamp."""
        self._cache[key] = {
            'cached_at': time.time(),
            'data': data
        }
        self._save_cache()

    def _get_pytrends(self):
        """Get or create pytrends instance."""
        if self._pytrends is None:
            try:
                from pytrends.request import TrendReq
                self._pytrends = TrendReq(hl='en-US', tz=360, timeout=(10, 25))
            except ImportError:
                logger.error("pytrends not installed. Run: pip install pytrends")
                return None
        return self._pytrends

    def get_ticker_trend(self, ticker: str) -> TrendData:
        """
        Get Google Trends data for a ticker.

        Args:
            ticker: Stock ticker symbol

        Returns:
            TrendData object with search interest metrics
        """
        # Check cache first
        cache_key = f"trend:{ticker}"
        cached = self._get_cached(cache_key)
        if cached:
            return TrendData(**cached)

        pytrends = self._get_pytrends()
        if not pytrends:
            # Return default if pytrends not available
            default = TrendData(
                ticker=ticker,
                search_interest=50,
                trend_direction='stable',
                is_breakout=False,
                relative_to_peak=0.5,
                timestamp=datetime.now().isoformat()
            )
            return default

        try:
            # Build search term (ticker + stock)
            search_term = f"{ticker} stock"

            # Get interest over past 90 days
            pytrends.build_payload(
                [search_term],
                cat=0,
                timeframe='today 3-m',
                geo='US',
                gprop=''
            )

            interest_over_time = pytrends.interest_over_time()

            if interest_over_time.empty:
                logger.debug(f"No Google Trends data for {ticker}")
                default = TrendData(
                    ticker=ticker,
                    search_interest=0,
                    trend_direction='stable',
                    is_breakout=False,
                    relative_to_peak=0.0,
                    timestamp=datetime.now().isoformat()
                )
                self._set_cached(cache_key, asdict(default))
                return default

            # Extract metrics
            values = interest_over_time[search_term].values
            current_interest = int(values[-1])  # Most recent week
            avg_interest = int(values.mean())
            peak_interest = int(values.max())

            # Determine trend direction
            recent_7_days = values[-2:]  # Last 2 weeks
            prev_7_days = values[-4:-2]  # Previous 2 weeks

            if len(recent_7_days) > 0 and len(prev_7_days) > 0:
                recent_avg = recent_7_days.mean()
                prev_avg = prev_7_days.mean()

                if recent_avg > prev_avg * 1.2:
                    trend_direction = 'rising'
                elif recent_avg < prev_avg * 0.8:
                    trend_direction = 'falling'
                else:
                    trend_direction = 'stable'
            else:
                trend_direction = 'stable'

            # Detect breakout (current > 2x average)
            is_breakout = current_interest > avg_interest * 2

            # Relative to peak
            relative_to_peak = current_interest / peak_interest if peak_interest > 0 else 0

            trend_data = TrendData(
                ticker=ticker,
                search_interest=current_interest,
                trend_direction=trend_direction,
                is_breakout=is_breakout,
                relative_to_peak=relative_to_peak,
                timestamp=datetime.now().isoformat()
            )

            # Cache result
            self._set_cached(cache_key, asdict(trend_data))

            return trend_data

        except Exception as e:
            logger.error(f"Google Trends error for {ticker}: {e}")

            # Return default on error
            default = TrendData(
                ticker=ticker,
                search_interest=50,
                trend_direction='stable',
                is_breakout=False,
                relative_to_peak=0.5,
                timestamp=datetime.now().isoformat()
            )
            return default

    def get_breakout_stocks(self, tickers: List[str]) -> List[Dict]:
        """
        Find stocks with search interest breakouts.

        Args:
            tickers: List of tickers to check

        Returns:
            List of tickers with breakout signals
        """
        breakouts = []

        for ticker in tickers:
            try:
                trend = self.get_ticker_trend(ticker)
                if trend.is_breakout:
                    breakouts.append({
                        'ticker': ticker,
                        'search_interest': trend.search_interest,
                        'trend_direction': trend.trend_direction
                    })
            except Exception as e:
                logger.debug(f"Failed to check trends for {ticker}: {e}")
                continue

        # Sort by search interest
        breakouts.sort(key=lambda x: x['search_interest'], reverse=True)

        return breakouts


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

_trends_intelligence = None


def get_trends_intelligence() -> GoogleTrendsIntelligence:
    """Get or create singleton Google Trends Intelligence."""
    global _trends_intelligence
    if _trends_intelligence is None:
        _trends_intelligence = GoogleTrendsIntelligence()
    return _trends_intelligence


def get_trend_score(ticker: str) -> int:
    """Get Google Trends search interest score (0-100)."""
    trend = get_trends_intelligence().get_ticker_trend(ticker)
    return trend.search_interest


def is_search_breakout(ticker: str) -> bool:
    """Check if ticker has search interest breakout."""
    trend = get_trends_intelligence().get_ticker_trend(ticker)
    return trend.is_breakout


def get_trend_data(ticker: str) -> Dict:
    """Get full trend data for ticker."""
    trend = get_trends_intelligence().get_ticker_trend(ticker)
    return asdict(trend)


# =============================================================================
# INTEGRATION WITH STORY SCORING
# =============================================================================

def calculate_retail_momentum_score(ticker: str) -> float:
    """
    Calculate retail momentum score from Google Trends.

    Returns 0-20 score for story scoring integration.
    """
    try:
        trend = get_trends_intelligence().get_ticker_trend(ticker)

        score = 0

        # Base score from search interest (0-10 points)
        if trend.search_interest >= 80:
            score += 10
        elif trend.search_interest >= 60:
            score += 7
        elif trend.search_interest >= 40:
            score += 5
        elif trend.search_interest >= 20:
            score += 3

        # Breakout bonus (0-5 points)
        if trend.is_breakout:
            score += 5

        # Rising trend bonus (0-5 points)
        if trend.trend_direction == 'rising':
            score += 5
        elif trend.trend_direction == 'stable':
            score += 2

        return min(20, score)  # Cap at 20

    except Exception as e:
        logger.debug(f"Failed to calculate retail momentum for {ticker}: {e}")
        return 10  # Neutral default


# =============================================================================
# TELEGRAM FORMATTING
# =============================================================================

def format_trends_message(data: Dict) -> str:
    """Format Google Trends data for Telegram."""
    ticker = data.get('ticker', 'Unknown')
    interest = data.get('search_interest', 0)
    direction = data.get('trend_direction', 'stable')
    breakout = data.get('is_breakout', False)
    peak_pct = data.get('relative_to_peak', 0) * 100

    # Direction emoji
    if direction == 'rising':
        emoji = '📈'
    elif direction == 'falling':
        emoji = '📉'
    else:
        emoji = '➡️'

    msg = f"🔍 *GOOGLE TRENDS: ${ticker}*\n"
    msg += f"_Retail search interest indicator_\n\n"

    msg += f"{emoji} *Search Interest:* {interest}/100\n"
    msg += f"📊 *Trend:* {direction.upper()}\n"
    msg += f"🎯 *vs All-Time Peak:* {peak_pct:.0f}%\n"

    if breakout:
        msg += f"\n🔥 *SEARCH BREAKOUT DETECTED*\n"
        msg += f"_Search volume >2x average_\n"

    # Interpretation
    msg += f"\n💡 *Interpretation:*\n"
    if interest >= 80:
        msg += f"• Very high retail interest\n"
        msg += f"• Potential FOMO buying\n"
    elif interest >= 60:
        msg += f"• Strong retail interest\n"
    elif interest >= 40:
        msg += f"• Moderate retail interest\n"
    elif interest >= 20:
        msg += f"• Low retail interest\n"
    else:
        msg += f"• Very low retail interest\n"

    if direction == 'rising':
        msg += f"• Increasing retail awareness\n"
    elif direction == 'falling':
        msg += f"• Declining retail interest\n"

    msg += f"\n_Updated: {datetime.now().strftime('%H:%M:%S')}_"

    return msg
