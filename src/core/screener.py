#!/usr/bin/env python3
"""
Stock Screener with Custom Filters - Enhanced Version

Features:
- Full S&P 500 universe (500+ stocks)
- Efficient SPY caching (single download)
- Result caching (5 minute TTL)
- More presets and filters
- Sector/market cap filtering
"""

import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import json
from pathlib import Path

from config import config
from utils import (
    get_logger, normalize_dataframe_columns, get_spy_data_cached,
    calculate_rs, safe_float, download_stock_data,
)

logger = get_logger(__name__)

# Import full S&P 500 universe from market_health
try:
    from market_health import BREADTH_UNIVERSE
    DEFAULT_TICKERS = BREADTH_UNIVERSE
except Exception as e:
    # Fallback if import fails
    logger.error(f"Error importing BREADTH_UNIVERSE: {e}")
    DEFAULT_TICKERS = [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA', 'BRK-B',
        'JPM', 'V', 'UNH', 'MA', 'HD', 'PG', 'JNJ', 'XOM', 'BAC', 'ABBV',
    ]

# Sector mapping for filtering
SECTOR_TICKERS = {
    'tech': ['AAPL', 'MSFT', 'GOOGL', 'GOOG', 'META', 'NVDA', 'AVGO', 'ADBE', 'CRM', 'CSCO',
             'ORCL', 'ACN', 'IBM', 'INTC', 'AMD', 'QCOM', 'TXN', 'NOW', 'INTU', 'AMAT'],
    'semis': ['NVDA', 'AMD', 'AVGO', 'QCOM', 'TXN', 'AMAT', 'ADI', 'LRCX', 'MU', 'KLAC',
              'MCHP', 'NXPI', 'ON', 'MRVL', 'INTC', 'TSM'],
    'financials': ['JPM', 'BAC', 'WFC', 'GS', 'MS', 'C', 'BLK', 'SCHW', 'AXP', 'SPGI',
                   'V', 'MA', 'PGR', 'MMC', 'CB'],
    'healthcare': ['UNH', 'JNJ', 'PFE', 'MRK', 'ABBV', 'LLY', 'TMO', 'ABT', 'DHR', 'BMY'],
    'energy': ['XOM', 'CVX', 'COP', 'SLB', 'EOG', 'MPC', 'PSX', 'VLO', 'OXY', 'WMB'],
    'consumer': ['AMZN', 'TSLA', 'HD', 'MCD', 'NKE', 'LOW', 'SBUX', 'TJX', 'COST', 'WMT'],
    'industrials': ['CAT', 'DE', 'BA', 'HON', 'UPS', 'RTX', 'LMT', 'GE', 'UNP', 'MMM'],
    'crypto': ['MSTR', 'COIN', 'MARA', 'RIOT', 'CLSK'],
    'nuclear': ['CEG', 'VST', 'CCJ', 'UEC', 'SMR', 'OKLO'],
    'ai': ['NVDA', 'AMD', 'AVGO', 'MRVL', 'SMCI', 'PLTR', 'AI', 'MSFT', 'GOOGL', 'META'],
}

# Cache configuration
CACHE_DIR = Path('cache')
CACHE_DIR.mkdir(exist_ok=True)


def get_stock_metrics(ticker, spy_returns=None):
    """Fetch metrics for a single stock."""
    try:
        df = download_stock_data(ticker, period='3mo', normalize=True, validate=False)
        df = normalize_dataframe_columns(df)

        if df is None or len(df) < 20:
            return None

        close = df['Close']
        volume = df['Volume']
        current = safe_float(close.iloc[-1])
        if current is None:
            return None

        # Calculate metrics
        sma_20 = safe_float(close.rolling(20).mean().iloc[-1])
        sma_50 = safe_float(close.rolling(50).mean().iloc[-1]) if len(close) >= 50 else sma_20
        sma_200 = safe_float(close.rolling(200).mean().iloc[-1]) if len(close) >= 200 else sma_50

        # Returns
        ret_1d = (current / safe_float(close.iloc[-2]) - 1) * 100 if len(close) >= 2 else 0
        ret_5d = (current / safe_float(close.iloc[-5]) - 1) * 100 if len(close) >= 5 else 0
        ret_20d = (current / safe_float(close.iloc[-20]) - 1) * 100 if len(close) >= 20 else 0

        # Volume
        vol_avg = safe_float(volume.iloc[-20:].mean())
        vol_ratio = safe_float(volume.iloc[-1] / vol_avg) if vol_avg and vol_avg > 0 else 1

        # Relative strength vs SPY using calculate_rs utility
        rs_data = calculate_rs(df, spy_returns)
        rs_5d = rs_data.get('rs_5d', ret_5d)
        rs_20d = rs_data.get('rs_20d', ret_20d)
        rs = rs_data.get('rs_composite', rs_20d)  # Use composite as primary RS metric

        # ATR
        high = df['High']
        low = df['Low']
        tr = pd.concat([high - low, abs(high - close.shift(1)), abs(low - close.shift(1))], axis=1).max(axis=1)
        atr = safe_float(tr.rolling(14).mean().iloc[-1])
        atr_pct = atr / current * 100 if atr and current else 0

        # RSI
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs_val = gain / loss
        rsi = safe_float(100 - (100 / (1 + rs_val.iloc[-1])))

        # Distance from highs/lows
        high_52w = safe_float(close.max())
        low_52w = safe_float(close.min())
        from_high = (current - high_52w) / high_52w * 100 if high_52w else 0
        from_low = (current - low_52w) / low_52w * 100 if low_52w else 0

        # Trend strength
        trend_score = 0
        if current > sma_20: trend_score += 1
        if current > sma_50: trend_score += 1
        if current > sma_200: trend_score += 1
        if sma_20 > sma_50: trend_score += 1
        if sma_50 > sma_200: trend_score += 1

        return {
            'ticker': ticker,
            'price': round(current, 2),
            'sma_20': round(sma_20, 2) if sma_20 else 0,
            'sma_50': round(sma_50, 2) if sma_50 else 0,
            'sma_200': round(sma_200, 2) if sma_200 else 0,
            'above_20sma': current > sma_20 if sma_20 else False,
            'above_50sma': current > sma_50 if sma_50 else False,
            'above_200sma': current > sma_200 if sma_200 else False,
            'ret_1d': round(ret_1d, 2),
            'ret_5d': round(ret_5d, 2),
            'ret_20d': round(ret_20d, 2),
            'rs': round(rs, 2) if rs else 0,
            'rs_5d': round(rs_5d, 2) if rs_5d else 0,
            'rs_20d': round(rs_20d, 2) if rs_20d else 0,
            'volume': safe_float(volume.iloc[-1]) or 0,
            'vol_ratio': round(vol_ratio, 2) if vol_ratio else 1,
            'atr_pct': round(atr_pct, 2) if atr_pct else 0,
            'rsi': round(rsi, 1) if rsi else 50,
            'from_high': round(from_high, 1),
            'from_low': round(from_low, 1),
            'trend_score': trend_score,
        }
    except Exception as e:
        logger.error(f"Error fetching metrics for {ticker}: {e}")
        return None


def load_screener_cache():
    """Load cached screener results."""
    cache_path = CACHE_DIR / 'screener_cache.json'
    if cache_path.exists():
        try:
            with open(cache_path, 'r') as f:
                data = json.load(f)
                if time.time() - data.get('timestamp', 0) < config.cache.screener_ttl_seconds:
                    return data.get('results', [])
        except Exception as e:
            logger.error(f"Error loading screener cache: {e}")
    return None


def save_screener_cache(results):
    """Save screener results to cache."""
    cache_path = CACHE_DIR / 'screener_cache.json'
    data = {
        'timestamp': time.time(),
        'results': results,
    }
    with open(cache_path, 'w') as f:
        json.dump(data, f, default=str)


def screen_stocks(filters, tickers=None, max_workers=None, use_cache=True):
    """
    Screen stocks with custom filters.

    Filters format: {'rs': '>5', 'vol_ratio': '>2', 'above_20sma': True}

    Supported filters:
    - rs, rs_5d, rs_20d: Relative strength vs SPY
    - vol_ratio: Volume ratio vs 20-day avg
    - ret_1d, ret_5d, ret_20d: Returns
    - above_20sma, above_50sma, above_200sma: Boolean
    - atr_pct: ATR as % of price
    - rsi: RSI value (0-100)
    - from_high, from_low: % from 52-week high/low
    - trend_score: Trend strength (0-5)
    - sector: Filter by sector name
    """
    # Use config default if max_workers not specified
    if max_workers is None:
        max_workers = config.scanner.max_workers

    # Handle sector filter
    sector = filters.pop('sector', None)
    if sector and sector.lower() in SECTOR_TICKERS:
        tickers = SECTOR_TICKERS[sector.lower()]
    elif tickers is None:
        tickers = DEFAULT_TICKERS

    # Get cached SPY data once using utility function
    _, spy_returns = get_spy_data_cached()

    # Fetch all metrics in parallel
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(get_stock_metrics, t, spy_returns): t for t in tickers}

        for future in as_completed(futures):
            try:
                metrics = future.result()
                if metrics:
                    results.append(metrics)
            except Exception as e:
                logger.error(f"Error processing stock: {e}")

    # Apply filters
    filtered = []
    for stock in results:
        passes = True

        for key, condition in filters.items():
            if key not in stock:
                continue

            value = stock[key]

            # Boolean filter
            if isinstance(condition, bool):
                if value != condition:
                    passes = False
                    break

            # Numeric filter with operator
            elif isinstance(condition, str):
                if condition.startswith('>='):
                    threshold = float(condition[2:])
                    if value < threshold:
                        passes = False
                        break
                elif condition.startswith('<='):
                    threshold = float(condition[2:])
                    if value > threshold:
                        passes = False
                        break
                elif condition.startswith('>'):
                    threshold = float(condition[1:])
                    if value <= threshold:
                        passes = False
                        break
                elif condition.startswith('<'):
                    threshold = float(condition[1:])
                    if value >= threshold:
                        passes = False
                        break
                elif condition.startswith('='):
                    threshold = float(condition[1:])
                    if abs(value - threshold) > 0.01:
                        passes = False
                        break

        if passes:
            filtered.append(stock)

    # Sort by RS
    filtered.sort(key=lambda x: x.get('rs', 0), reverse=True)

    return filtered


def parse_screen_args(args_str):
    """
    Parse screen command arguments.

    Example: "rs>5 vol_ratio>2 above_20sma sector=tech"
    Returns: {'rs': '>5', 'vol_ratio': '>2', 'above_20sma': True, 'sector': 'tech'}
    """
    filters = {}

    if not args_str:
        return filters

    parts = args_str.lower().split()

    for part in parts:
        # Handle sector=xxx
        if part.startswith('sector='):
            filters['sector'] = part.split('=')[1]
            continue

        # Check for operators
        for op in ['>=', '<=', '>', '<', '=']:
            if op in part:
                key, value = part.split(op, 1)
                filters[key] = f'{op}{value}'
                break
        else:
            # Boolean flag
            if part.startswith('!') or part.startswith('no_'):
                key = part.lstrip('!').replace('no_', '')
                filters[key] = False
            else:
                filters[part] = True

    return filters


def format_screen_results(results, limit=15):
    """Format screen results for Telegram."""
    if not results:
        return "No stocks match your criteria."

    msg = f"🔍 *SCREENER RESULTS* ({len(results)} matches)\n\n"

    for i, stock in enumerate(results[:limit], 1):
        # Emoji based on trend score
        if stock['trend_score'] >= 4:
            emoji = "🟢"
        elif stock['trend_score'] >= 2:
            emoji = "🟡"
        else:
            emoji = "🔴"

        msg += f"{emoji} *{stock['ticker']}* ${stock['price']:.2f}\n"
        msg += f"   RS: {stock['rs']:+.1f}% | Vol: {stock['vol_ratio']:.1f}x | RSI: {stock['rsi']:.0f}\n"

    if len(results) > limit:
        msg += f"\n_...and {len(results) - limit} more_"

    return msg


# Enhanced preset screens
PRESET_SCREENS = {
    # Momentum plays
    'momentum': {'rs': '>5', 'above_20sma': True, 'above_50sma': True, 'vol_ratio': '>1'},
    'leaders': {'rs': '>10', 'above_20sma': True, 'above_200sma': True, 'trend_score': '>=4'},
    'rockets': {'rs': '>15', 'ret_5d': '>5', 'vol_ratio': '>2'},

    # Breakout plays
    'breakout': {'rs': '>3', 'vol_ratio': '>2', 'from_high': '>-5'},
    'newhi': {'from_high': '>-2', 'above_50sma': True, 'vol_ratio': '>1.5'},

    # Mean reversion
    'oversold': {'rsi': '<30', 'above_200sma': True},
    'pullback': {'rs': '>0', 'rsi': '<40', 'above_50sma': True, 'from_high': '<-10'},
    'bounce': {'ret_5d': '<-5', 'rsi': '<35'},

    # Volume
    'volume': {'vol_ratio': '>3'},
    'accumulation': {'vol_ratio': '>2', 'ret_1d': '>0', 'above_20sma': True},

    # Sector specific
    'tech_leaders': {'sector': 'tech', 'rs': '>5', 'above_20sma': True},
    'semi_momentum': {'sector': 'semis', 'rs': '>3'},
    'energy_strength': {'sector': 'energy', 'rs': '>0', 'above_50sma': True},

    # Special themes
    'ai_plays': {'sector': 'ai', 'rs': '>0'},
    'crypto_momentum': {'sector': 'crypto', 'ret_5d': '>0'},
    'nuclear': {'sector': 'nuclear'},
}


if __name__ == '__main__':
    logger.info("Testing enhanced screener...")

    # Test momentum screen
    logger.info("=== Momentum Leaders ===")
    results = screen_stocks(PRESET_SCREENS['momentum'].copy())
    logger.info(f"Found {len(results)} stocks")
    for r in results[:5]:
        logger.info(f"  {r['ticker']}: RS {r['rs']:+.1f}%, Vol {r['vol_ratio']:.1f}x")
