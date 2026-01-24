#!/usr/bin/env python3
"""
Stock Screener with Custom Filters

Allows filtering stocks by various criteria.
"""

import yfinance as yf
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

# Default universe
DEFAULT_TICKERS = [
    'NVDA', 'AMD', 'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA',
    'AVGO', 'TSM', 'MU', 'INTC', 'QCOM', 'AMAT', 'LRCX', 'KLAC',
    'CRM', 'NOW', 'SNOW', 'PLTR', 'CRWD', 'PANW', 'ZS', 'NET',
    'LLY', 'NVO', 'AMGN', 'MRNA', 'PFE', 'JNJ', 'UNH', 'ABBV',
    'CEG', 'VST', 'CCJ', 'SMR', 'OKLO', 'UEC',
    'MSTR', 'COIN', 'MARA', 'RIOT', 'CLSK',
    'JPM', 'GS', 'MS', 'BAC', 'V', 'MA',
    'XOM', 'CVX', 'SLB', 'OXY',
    'CAT', 'DE', 'GE', 'HON', 'RTX', 'LMT',
    'COST', 'WMT', 'HD', 'LOW', 'TGT',
    'DIS', 'NFLX', 'CMCSA', 'T', 'VZ'
]


def get_stock_metrics(ticker):
    """Fetch metrics for a single stock."""
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period='3mo')

        if len(df) < 20:
            return None

        close = df['Close']
        volume = df['Volume']
        current = float(close.iloc[-1])

        # Calculate metrics
        sma_20 = float(close.rolling(20).mean().iloc[-1])
        sma_50 = float(close.rolling(50).mean().iloc[-1]) if len(close) >= 50 else sma_20

        # Returns
        ret_5d = (current / float(close.iloc[-5]) - 1) * 100 if len(close) >= 5 else 0
        ret_20d = (current / float(close.iloc[-20]) - 1) * 100 if len(close) >= 20 else 0

        # Volume
        vol_avg = float(volume.iloc[-20:].mean())
        vol_ratio = float(volume.iloc[-1] / vol_avg) if vol_avg > 0 else 1

        # Relative strength vs SPY
        spy = yf.download('SPY', period='1mo', progress=False)
        if isinstance(spy.columns, pd.MultiIndex):
            spy.columns = spy.columns.get_level_values(0)
        spy_ret = (float(spy['Close'].iloc[-1]) / float(spy['Close'].iloc[-20]) - 1) * 100
        rs = ret_20d - spy_ret

        # ATR
        high = df['High']
        low = df['Low']
        tr = pd.concat([high - low, abs(high - close.shift(1)), abs(low - close.shift(1))], axis=1).max(axis=1)
        atr = float(tr.rolling(14).mean().iloc[-1])
        atr_pct = atr / current * 100

        # Distance from highs/lows
        high_52w = float(close.max())
        low_52w = float(close.min())
        from_high = (current - high_52w) / high_52w * 100
        from_low = (current - low_52w) / low_52w * 100

        return {
            'ticker': ticker,
            'price': current,
            'sma_20': sma_20,
            'sma_50': sma_50,
            'above_20sma': current > sma_20,
            'above_50sma': current > sma_50,
            'ret_5d': ret_5d,
            'ret_20d': ret_20d,
            'rs': rs,
            'volume': float(volume.iloc[-1]),
            'vol_ratio': vol_ratio,
            'atr_pct': atr_pct,
            'from_high': from_high,
            'from_low': from_low,
        }
    except Exception as e:
        return None


def screen_stocks(filters, tickers=None, max_workers=10):
    """
    Screen stocks with custom filters.

    Filters format: {'rs': '>5', 'vol_ratio': '>2', 'above_20sma': True}

    Supported filters:
    - rs: Relative strength vs SPY (>, <, =)
    - vol_ratio: Volume ratio vs 20-day avg
    - ret_5d, ret_20d: Returns
    - above_20sma, above_50sma: Boolean
    - atr_pct: ATR as % of price
    - from_high, from_low: % from high/low
    """
    if tickers is None:
        tickers = DEFAULT_TICKERS

    # Fetch all metrics in parallel
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(get_stock_metrics, t): t for t in tickers}

        for future in as_completed(futures):
            try:
                metrics = future.result()
                if metrics:
                    results.append(metrics)
            except:
                pass

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
                if condition.startswith('>'):
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

    Example: "rs>5 vol_ratio>2 above_20sma"
    Returns: {'rs': '>5', 'vol_ratio': '>2', 'above_20sma': True}
    """
    filters = {}

    if not args_str:
        return filters

    parts = args_str.lower().split()

    for part in parts:
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


def format_screen_results(results, limit=10):
    """Format screen results for Telegram."""
    if not results:
        return "No stocks match your criteria."

    msg = f"🔍 *SCREENER RESULTS* ({len(results)} matches)\n\n"

    for i, stock in enumerate(results[:limit], 1):
        emoji = "🟢" if stock['rs'] > 0 else "🔴"
        msg += f"{emoji} *{stock['ticker']}* ${stock['price']:.2f}\n"
        msg += f"   RS: {stock['rs']:+.1f}% | Vol: {stock['vol_ratio']:.1f}x\n"

    if len(results) > limit:
        msg += f"\n_...and {len(results) - limit} more_"

    return msg


# Preset screens
PRESET_SCREENS = {
    'momentum': {'rs': '>5', 'above_20sma': True, 'above_50sma': True, 'vol_ratio': '>1'},
    'breakout': {'rs': '>3', 'vol_ratio': '>2', 'from_high': '>-5'},
    'oversold': {'rs': '<-5', 'from_low': '<20'},
    'volume': {'vol_ratio': '>3'},
    'leaders': {'rs': '>10', 'above_20sma': True},
}
