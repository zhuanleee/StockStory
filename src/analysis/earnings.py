#!/usr/bin/env python3
"""
Earnings Calendar Module - Enhanced Version

Features:
- Expanded watchlist (200+ stocks)
- Multiple data source fallbacks
- Earnings estimates (EPS, revenue)
- Historical beat/miss tracking
- Earnings surprise analysis
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path
import requests

from config import config
from utils import get_logger, normalize_dataframe_columns, safe_float

logger = get_logger(__name__)

# Import full S&P 500 universe
try:
    from market_health import BREADTH_UNIVERSE
    EARNINGS_WATCHLIST = BREADTH_UNIVERSE
except ImportError:
    logger.debug("market_health module not available, using fallback watchlist")
    # Fallback watchlist
    EARNINGS_WATCHLIST = [
        # Mega caps
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA',
        # Semis
        'AMD', 'AVGO', 'MU', 'INTC', 'QCOM', 'AMAT',
        # Software
        'CRM', 'NOW', 'PLTR', 'CRWD', 'PANW',
        # Healthcare
        'LLY', 'UNH', 'JNJ', 'PFE', 'MRK', 'ABBV',
        # Finance
        'JPM', 'GS', 'MS', 'BAC', 'V', 'MA',
        # Energy
        'XOM', 'CVX', 'SLB',
        # Consumer
        'COST', 'WMT', 'HD', 'NKE',
        # Other
        'DIS', 'NFLX', 'BA', 'CAT', 'GE'
    ]

# High-impact earnings (always track these)
HIGH_IMPACT_TICKERS = [
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA',
    'AMD', 'AVGO', 'MU', 'CRM', 'NOW',
    'JPM', 'GS', 'BAC',
    'UNH', 'LLY', 'JNJ',
    'XOM', 'CVX',
    'WMT', 'COST', 'HD',
    'NFLX', 'DIS', 'BA',
]

# Cache for earnings data
CACHE_DIR = Path('cache')
CACHE_DIR.mkdir(exist_ok=True)
EARNINGS_HISTORY_FILE = CACHE_DIR / 'earnings_history.json'


def load_earnings_history():
    """Load historical earnings data."""
    if EARNINGS_HISTORY_FILE.exists():
        try:
            with open(EARNINGS_HISTORY_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError, OSError) as e:
            logger.warning(f"Failed to load earnings history: {e}")
            pass
    return {'earnings': {}, 'surprises': []}


def save_earnings_history(data):
    """Save earnings history."""
    with open(EARNINGS_HISTORY_FILE, 'w') as f:
        json.dump(data, f, indent=2, default=str)


def get_earnings_info(ticker):
    """
    Get comprehensive earnings info for a ticker.

    Uses Polygon API as primary source, yfinance as fallback.

    Returns dict with:
    - next_date: Next earnings date
    - eps_estimate: Expected EPS
    - revenue_estimate: Expected revenue
    - historical_surprise: Average surprise %
    - beat_rate: % of times company beat estimates
    """
    import os

    result = {
        'ticker': ticker,
        'next_date': None,
        'days_until': None,
        'eps_estimate': None,
        'revenue_estimate': None,
        'historical_surprise': None,
        'beat_rate': None,
        'high_impact': ticker in HIGH_IMPACT_TICKERS,
    }

    # Try Polygon first for financial data
    polygon_key = os.environ.get('POLYGON_API_KEY', '')
    if polygon_key:
        try:
            from src.data.polygon_provider import get_financials_sync

            financials = get_financials_sync(ticker, timeframe='quarterly', limit=8)

            if financials:
                # Get latest quarter EPS and revenue
                latest = financials[0]
                result['eps_actual'] = latest.get('eps_diluted')
                result['revenue_actual'] = latest.get('revenue')
                result['net_income'] = latest.get('net_income')

                # Calculate beat rate from historical data
                if len(financials) >= 4:
                    # We have historical data but no estimates from Polygon
                    # Track EPS growth instead
                    eps_values = [f.get('eps_diluted') for f in financials if f.get('eps_diluted')]
                    if len(eps_values) >= 2:
                        current = eps_values[0]
                        previous = eps_values[1]
                        if previous and previous != 0:
                            yoy_growth = (current - previous) / abs(previous) * 100
                            result['eps_growth'] = round(yoy_growth, 1)

                logger.debug(f"Got Polygon financials for {ticker}")
        except Exception as e:
            logger.debug(f"Polygon financials failed for {ticker}: {e}")

    # Fallback to yfinance for earnings dates and estimates
    try:
        stock = yf.Ticker(ticker)

        # Get earnings date from calendar
        calendar = stock.calendar
        if calendar is not None and not calendar.empty:
            if 'Earnings Date' in calendar.index:
                dates = calendar.loc['Earnings Date']
                if isinstance(dates, (list, pd.Series)) and len(dates) > 0:
                    next_date = dates.iloc[0] if hasattr(dates, 'iloc') else dates[0]
                else:
                    next_date = dates

                if next_date:
                    if hasattr(next_date, 'date'):
                        result['next_date'] = next_date.date()
                    elif hasattr(next_date, 'to_pydatetime'):
                        result['next_date'] = next_date.to_pydatetime().date()
                    else:
                        result['next_date'] = next_date

                    if result['next_date']:
                        result['days_until'] = (result['next_date'] - datetime.now().date()).days

        # Get earnings estimates (yfinance still better for estimates)
        if result.get('eps_estimate') is None:
            try:
                earnings_est = stock.earnings_estimate
                if earnings_est is not None and not earnings_est.empty:
                    if 'avg' in earnings_est.index:
                        if '0q' in earnings_est.columns:
                            result['eps_estimate'] = float(earnings_est.loc['avg', '0q'])
                        elif len(earnings_est.columns) > 0:
                            result['eps_estimate'] = float(earnings_est.loc['avg'].iloc[0])
            except (KeyError, IndexError, TypeError, ValueError) as e:
                logger.debug(f"Could not get earnings estimate for {ticker}: {e}")

        # Get revenue estimates
        if result.get('revenue_estimate') is None:
            try:
                rev_est = stock.revenue_estimate
                if rev_est is not None and not rev_est.empty:
                    if 'avg' in rev_est.index:
                        if '0q' in rev_est.columns:
                            result['revenue_estimate'] = float(rev_est.loc['avg', '0q'])
                        elif len(rev_est.columns) > 0:
                            result['revenue_estimate'] = float(rev_est.loc['avg'].iloc[0])
            except (KeyError, IndexError, TypeError, ValueError) as e:
                logger.debug(f"Could not get revenue estimate for {ticker}: {e}")

        # Get historical earnings for beat/miss analysis
        if result.get('beat_rate') is None:
            try:
                earnings_hist = stock.earnings_history
                if earnings_hist is not None and len(earnings_hist) > 0:
                    surprises = []
                    beats = 0
                    total = 0

                    for _, row in earnings_hist.iterrows():
                        if 'epsActual' in row and 'epsEstimate' in row:
                            actual = row.get('epsActual')
                            estimate = row.get('epsEstimate')

                            if actual is not None and estimate is not None and estimate != 0:
                                surprise = (actual - estimate) / abs(estimate) * 100
                                surprises.append(surprise)
                                total += 1
                                if actual > estimate:
                                    beats += 1

                    if surprises:
                        result['historical_surprise'] = round(sum(surprises) / len(surprises), 1)
                    if total > 0:
                        result['beat_rate'] = round(beats / total * 100, 0)
            except (KeyError, IndexError, TypeError, ValueError, AttributeError) as e:
                logger.debug(f"Could not get earnings history for {ticker}: {e}")

    except Exception as e:
        logger.debug(f"Failed to get earnings info for {ticker}: {e}")

    return result


def get_earnings_date(ticker):
    """Get next earnings date for a ticker (simple version for compatibility)."""
    info = get_earnings_info(ticker)
    return info.get('next_date')


def get_upcoming_earnings(tickers=None, days_ahead=14, include_estimates=True):
    """
    Get upcoming earnings for watchlist with estimates.

    Returns list of earnings info sorted by date.
    """
    if tickers is None:
        tickers = EARNINGS_WATCHLIST

    today = datetime.now().date()
    cutoff = today + timedelta(days=days_ahead)

    earnings = []

    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(get_earnings_info, t): t for t in tickers}

        for future in as_completed(futures):
            try:
                info = future.result()
                if info and info.get('next_date'):
                    date = info['next_date']
                    if today <= date <= cutoff:
                        earnings.append(info)
            except Exception as e:
                logger.debug(f"Failed to get earnings for a ticker: {e}")
                pass

    # Sort by date, then by high impact
    earnings.sort(key=lambda x: (x['next_date'], not x.get('high_impact', False)))

    return earnings


def format_earnings_calendar(earnings):
    """Format earnings for Telegram message with estimates."""
    if not earnings:
        return "📅 *EARNINGS CALENDAR*\n\n_No upcoming earnings in the next 14 days._"

    msg = "📅 *EARNINGS CALENDAR*\n\n"

    current_date = None
    for e in earnings:
        date = e['next_date']
        days = e.get('days_until', 0)

        # Group by date
        if date != current_date:
            current_date = date
            day_name = date.strftime('%A')
            date_str = date.strftime('%b %d')

            if days == 0:
                msg += f"\n🔴 *TODAY* ({date_str})\n"
            elif days == 1:
                msg += f"\n🟡 *TOMORROW* ({date_str})\n"
            elif days <= 3:
                msg += f"\n🟠 *{day_name}* ({date_str})\n"
            else:
                msg += f"\n⚪ *{day_name}* ({date_str})\n"

        # Ticker with impact indicator
        impact = "⭐" if e.get('high_impact') else ""
        ticker_line = f"   {impact}`{e['ticker']}`"

        # Add estimates if available
        extras = []
        if e.get('eps_estimate'):
            extras.append(f"EPS est: ${e['eps_estimate']:.2f}")
        if e.get('beat_rate') is not None:
            extras.append(f"Beat: {e['beat_rate']:.0f}%")
        if e.get('historical_surprise') is not None:
            sign = "+" if e['historical_surprise'] > 0 else ""
            extras.append(f"Avg surprise: {sign}{e['historical_surprise']:.1f}%")

        if extras:
            ticker_line += f" ({', '.join(extras[:2])})"

        msg += ticker_line + "\n"

    msg += "\n⭐ = High impact earnings"
    msg += "\n_💡 Tip: Avoid new positions before earnings_"

    return msg


def check_earnings_soon(tickers, days=3):
    """
    Check if any tickers have earnings in next N days.

    Returns dict of {ticker: earnings_info}
    """
    earnings_soon = {}

    for ticker in tickers:
        try:
            info = get_earnings_info(ticker)
            if info.get('days_until') is not None:
                if 0 <= info['days_until'] <= days:
                    earnings_soon[ticker] = info
        except Exception as e:
            logger.debug(f"Failed to check earnings for {ticker}: {e}")
            pass

    return earnings_soon


def record_earnings_result(ticker, actual_eps, expected_eps, actual_rev=None, expected_rev=None, price_reaction=None):
    """
    Record actual earnings result for learning.

    This helps track historical accuracy and price reactions.
    """
    history = load_earnings_history()

    if ticker not in history['earnings']:
        history['earnings'][ticker] = []

    surprise = 0
    if expected_eps and expected_eps != 0:
        surprise = (actual_eps - expected_eps) / abs(expected_eps) * 100

    result = {
        'date': datetime.now().isoformat(),
        'actual_eps': actual_eps,
        'expected_eps': expected_eps,
        'eps_surprise': round(surprise, 2),
        'beat': actual_eps > expected_eps if expected_eps else None,
        'actual_revenue': actual_rev,
        'expected_revenue': expected_rev,
        'price_reaction': price_reaction,  # % move after earnings
    }

    history['earnings'][ticker].append(result)
    history['earnings'][ticker] = history['earnings'][ticker][-20:]  # Keep last 20

    # Track surprise patterns
    history['surprises'].append({
        'ticker': ticker,
        'surprise': surprise,
        'price_reaction': price_reaction,
        'date': datetime.now().isoformat(),
    })
    history['surprises'] = history['surprises'][-500:]

    save_earnings_history(history)

    return result


def get_earnings_patterns():
    """
    Analyze historical earnings patterns.

    Returns insights about typical reactions.
    """
    history = load_earnings_history()
    surprises = history.get('surprises', [])

    if len(surprises) < 10:
        return None

    # Analyze patterns
    beats = [s for s in surprises if s.get('surprise', 0) > 0]
    misses = [s for s in surprises if s.get('surprise', 0) < 0]

    beat_reactions = [s.get('price_reaction', 0) for s in beats if s.get('price_reaction') is not None]
    miss_reactions = [s.get('price_reaction', 0) for s in misses if s.get('price_reaction') is not None]

    return {
        'total_tracked': len(surprises),
        'beat_count': len(beats),
        'miss_count': len(misses),
        'avg_beat_reaction': sum(beat_reactions) / len(beat_reactions) if beat_reactions else 0,
        'avg_miss_reaction': sum(miss_reactions) / len(miss_reactions) if miss_reactions else 0,
    }


def get_high_impact_earnings(days_ahead=7):
    """Get only high-impact earnings in the next N days."""
    return get_upcoming_earnings(tickers=HIGH_IMPACT_TICKERS, days_ahead=days_ahead)


if __name__ == '__main__':
    logger.info("Testing enhanced earnings module...")

    # Test single ticker
    logger.info("\n=== NVDA Earnings Info ===")
    info = get_earnings_info('NVDA')
    logger.info(json.dumps(info, indent=2, default=str))

    # Test calendar
    logger.info("\n=== High Impact Earnings (7 days) ===")
    earnings = get_high_impact_earnings(days_ahead=7)
    logger.info(format_earnings_calendar(earnings))
