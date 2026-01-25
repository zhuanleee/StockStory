#!/usr/bin/env python3
"""
Market Health Module

Calculates:
- Market Breadth indicators
- Fear & Greed Index
- Overall market health score
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

# Stock universe for breadth calculation
BREADTH_UNIVERSE = [
    # Mega caps
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA', 'BRK-B',
    # Tech
    'AMD', 'AVGO', 'CRM', 'ADBE', 'INTC', 'CSCO', 'ORCL', 'IBM',
    # Finance
    'JPM', 'BAC', 'WFC', 'GS', 'MS', 'V', 'MA', 'AXP',
    # Healthcare
    'UNH', 'JNJ', 'PFE', 'MRK', 'ABBV', 'LLY', 'TMO', 'ABT',
    # Consumer
    'WMT', 'PG', 'KO', 'PEP', 'COST', 'HD', 'MCD', 'NKE',
    # Industrial
    'CAT', 'DE', 'BA', 'HON', 'UPS', 'RTX', 'LMT', 'GE',
    # Energy
    'XOM', 'CVX', 'COP', 'SLB', 'EOG',
    # Utilities/REIT
    'NEE', 'DUK', 'SO', 'AMT', 'PLD'
]


def get_stock_data(ticker, period='3mo'):
    """Fetch stock data with error handling."""
    try:
        df = yf.download(ticker, period=period, progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return ticker, df
    except:
        return ticker, None


def calculate_market_breadth():
    """
    Calculate comprehensive market breadth indicators.

    Returns dict with:
    - above_20sma: % of stocks above 20-day SMA
    - above_50sma: % of stocks above 50-day SMA
    - above_200sma: % of stocks above 200-day SMA
    - advance_decline: Ratio of advancing vs declining stocks
    - new_highs: Count of stocks at 52-week highs
    - new_lows: Count of stocks at 52-week lows
    - sector_breadth: % of sectors positive
    - breadth_score: Overall breadth score (0-100)
    """
    results = {
        'above_20sma': 0,
        'above_50sma': 0,
        'above_200sma': 0,
        'advancing': 0,
        'declining': 0,
        'unchanged': 0,
        'advance_decline_ratio': 1.0,
        'new_highs': 0,
        'new_lows': 0,
        'breadth_score': 50,
        'stocks_analyzed': 0
    }

    stocks_data = []

    # Parallel fetch
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(get_stock_data, t, '1y'): t for t in BREADTH_UNIVERSE}

        for future in as_completed(futures):
            ticker, df = future.result()
            if df is not None and len(df) >= 50:
                stocks_data.append((ticker, df))

    if not stocks_data:
        return results

    above_20 = 0
    above_50 = 0
    above_200 = 0
    advancing = 0
    declining = 0
    new_highs = 0
    new_lows = 0

    for ticker, df in stocks_data:
        try:
            close = df['Close']
            current = float(close.iloc[-1])
            prev_close = float(close.iloc[-2])

            # SMA calculations
            sma_20 = float(close.rolling(20).mean().iloc[-1])
            sma_50 = float(close.rolling(50).mean().iloc[-1])
            sma_200 = float(close.rolling(200).mean().iloc[-1]) if len(close) >= 200 else sma_50

            if current > sma_20:
                above_20 += 1
            if current > sma_50:
                above_50 += 1
            if current > sma_200:
                above_200 += 1

            # Advance/Decline
            if current > prev_close * 1.001:
                advancing += 1
            elif current < prev_close * 0.999:
                declining += 1

            # 52-week high/low
            high_52w = float(close.tail(252).max()) if len(close) >= 252 else float(close.max())
            low_52w = float(close.tail(252).min()) if len(close) >= 252 else float(close.min())

            if current >= high_52w * 0.98:  # Within 2% of high
                new_highs += 1
            if current <= low_52w * 1.02:  # Within 2% of low
                new_lows += 1

        except Exception as e:
            continue

    total = len(stocks_data)

    results['stocks_analyzed'] = total
    results['above_20sma'] = round(above_20 / total * 100, 1) if total > 0 else 0
    results['above_50sma'] = round(above_50 / total * 100, 1) if total > 0 else 0
    results['above_200sma'] = round(above_200 / total * 100, 1) if total > 0 else 0
    results['advancing'] = advancing
    results['declining'] = declining
    results['unchanged'] = total - advancing - declining
    results['advance_decline_ratio'] = round(advancing / declining, 2) if declining > 0 else 10.0
    results['new_highs'] = new_highs
    results['new_lows'] = new_lows

    # Calculate breadth score (0-100)
    breadth_score = 0
    breadth_score += results['above_50sma'] * 0.3  # 30% weight
    breadth_score += results['above_200sma'] * 0.2  # 20% weight
    breadth_score += min(results['advance_decline_ratio'] * 10, 25)  # 25% weight, capped
    breadth_score += (new_highs / (new_highs + new_lows + 1)) * 25  # 25% weight

    results['breadth_score'] = round(min(max(breadth_score, 0), 100), 1)

    return results


def calculate_fear_greed_index():
    """
    Calculate Fear & Greed Index (0-100).

    Components:
    1. VIX Level (25%) - Lower VIX = More Greed
    2. Market Momentum (20%) - SPY vs 125-day MA
    3. Put/Call Ratio (20%) - Lower = More Greed (estimated)
    4. Safe Haven Demand (15%) - Stocks vs Bonds performance
    5. Junk Bond Demand (10%) - HYG vs LQD spread
    6. Market Volatility (10%) - Recent ATR of SPY

    Returns:
    - score: 0-100 (0=Extreme Fear, 100=Extreme Greed)
    - label: Text label
    - components: Individual component scores
    """
    components = {}

    try:
        # 1. VIX Level (25%)
        try:
            vix = yf.download('^VIX', period='5d', progress=False)
            if isinstance(vix.columns, pd.MultiIndex):
                vix.columns = vix.columns.get_level_values(0)
            vix_current = float(vix['Close'].iloc[-1])

            # VIX scoring: <12 = 100 (extreme greed), >40 = 0 (extreme fear)
            if vix_current <= 12:
                vix_score = 100
            elif vix_current >= 40:
                vix_score = 0
            else:
                vix_score = 100 - ((vix_current - 12) / 28 * 100)

            components['vix'] = {
                'value': round(vix_current, 1),
                'score': round(vix_score, 1),
                'weight': 0.25,
                'label': 'VIX Level'
            }
        except:
            components['vix'] = {'value': 20, 'score': 50, 'weight': 0.25, 'label': 'VIX Level'}

        # 2. Market Momentum (20%) - SPY vs 125-day MA
        try:
            spy = yf.download('SPY', period='6mo', progress=False)
            if isinstance(spy.columns, pd.MultiIndex):
                spy.columns = spy.columns.get_level_values(0)

            spy_close = spy['Close']
            current_spy = float(spy_close.iloc[-1])
            ma_125 = float(spy_close.rolling(125).mean().iloc[-1])

            momentum_pct = (current_spy - ma_125) / ma_125 * 100

            # Momentum scoring: >8% above = 100, >8% below = 0
            if momentum_pct >= 8:
                momentum_score = 100
            elif momentum_pct <= -8:
                momentum_score = 0
            else:
                momentum_score = 50 + (momentum_pct / 8 * 50)

            components['momentum'] = {
                'value': round(momentum_pct, 1),
                'score': round(momentum_score, 1),
                'weight': 0.20,
                'label': 'Market Momentum'
            }
        except:
            components['momentum'] = {'value': 0, 'score': 50, 'weight': 0.20, 'label': 'Market Momentum'}

        # 3. Put/Call Ratio Estimate (20%)
        # Using VIX term structure as proxy
        try:
            # Higher VIX relative to recent average = more puts = fear
            vix_ma = float(vix['Close'].rolling(5).mean().iloc[-1])
            pc_proxy = vix_current / vix_ma

            # PC ratio scoring: <0.8 = greed, >1.2 = fear
            if pc_proxy <= 0.8:
                pc_score = 100
            elif pc_proxy >= 1.2:
                pc_score = 0
            else:
                pc_score = 100 - ((pc_proxy - 0.8) / 0.4 * 100)

            components['put_call'] = {
                'value': round(pc_proxy, 2),
                'score': round(pc_score, 1),
                'weight': 0.20,
                'label': 'Put/Call Ratio'
            }
        except:
            components['put_call'] = {'value': 1.0, 'score': 50, 'weight': 0.20, 'label': 'Put/Call Ratio'}

        # 4. Safe Haven Demand (15%) - SPY vs TLT (bonds)
        try:
            tlt = yf.download('TLT', period='1mo', progress=False)
            if isinstance(tlt.columns, pd.MultiIndex):
                tlt.columns = tlt.columns.get_level_values(0)

            spy_ret_20d = (float(spy_close.iloc[-1]) / float(spy_close.iloc[-20]) - 1) * 100
            tlt_ret_20d = (float(tlt['Close'].iloc[-1]) / float(tlt['Close'].iloc[-20]) - 1) * 100

            # If stocks outperform bonds = greed
            safe_haven_diff = spy_ret_20d - tlt_ret_20d

            if safe_haven_diff >= 5:
                sh_score = 100
            elif safe_haven_diff <= -5:
                sh_score = 0
            else:
                sh_score = 50 + (safe_haven_diff / 5 * 50)

            components['safe_haven'] = {
                'value': round(safe_haven_diff, 1),
                'score': round(sh_score, 1),
                'weight': 0.15,
                'label': 'Safe Haven Demand'
            }
        except:
            components['safe_haven'] = {'value': 0, 'score': 50, 'weight': 0.15, 'label': 'Safe Haven Demand'}

        # 5. Junk Bond Demand (10%) - HYG vs LQD
        try:
            hyg = yf.download('HYG', period='1mo', progress=False)
            lqd = yf.download('LQD', period='1mo', progress=False)

            if isinstance(hyg.columns, pd.MultiIndex):
                hyg.columns = hyg.columns.get_level_values(0)
            if isinstance(lqd.columns, pd.MultiIndex):
                lqd.columns = lqd.columns.get_level_values(0)

            hyg_ret = (float(hyg['Close'].iloc[-1]) / float(hyg['Close'].iloc[-20]) - 1) * 100
            lqd_ret = (float(lqd['Close'].iloc[-1]) / float(lqd['Close'].iloc[-20]) - 1) * 100

            # If junk outperforms investment grade = greed
            junk_diff = hyg_ret - lqd_ret

            if junk_diff >= 2:
                junk_score = 100
            elif junk_diff <= -2:
                junk_score = 0
            else:
                junk_score = 50 + (junk_diff / 2 * 50)

            components['junk_bond'] = {
                'value': round(junk_diff, 1),
                'score': round(junk_score, 1),
                'weight': 0.10,
                'label': 'Junk Bond Demand'
            }
        except:
            components['junk_bond'] = {'value': 0, 'score': 50, 'weight': 0.10, 'label': 'Junk Bond Demand'}

        # 6. Market Volatility (10%) - SPY ATR
        try:
            high = spy['High']
            low = spy['Low']
            close = spy['Close']

            tr = pd.concat([
                high - low,
                abs(high - close.shift(1)),
                abs(low - close.shift(1))
            ], axis=1).max(axis=1)

            atr_14 = float(tr.rolling(14).mean().iloc[-1])
            atr_pct = atr_14 / float(close.iloc[-1]) * 100

            # Lower volatility = greed
            if atr_pct <= 0.8:
                vol_score = 100
            elif atr_pct >= 2.5:
                vol_score = 0
            else:
                vol_score = 100 - ((atr_pct - 0.8) / 1.7 * 100)

            components['volatility'] = {
                'value': round(atr_pct, 2),
                'score': round(vol_score, 1),
                'weight': 0.10,
                'label': 'Market Volatility'
            }
        except:
            components['volatility'] = {'value': 1.5, 'score': 50, 'weight': 0.10, 'label': 'Market Volatility'}

        # Calculate weighted score
        total_score = 0
        for comp in components.values():
            total_score += comp['score'] * comp['weight']

        total_score = round(min(max(total_score, 0), 100), 1)

        # Label
        if total_score >= 80:
            label = 'Extreme Greed'
            color = '#22c55e'
        elif total_score >= 60:
            label = 'Greed'
            color = '#84cc16'
        elif total_score >= 40:
            label = 'Neutral'
            color = '#eab308'
        elif total_score >= 20:
            label = 'Fear'
            color = '#f97316'
        else:
            label = 'Extreme Fear'
            color = '#ef4444'

        return {
            'score': total_score,
            'label': label,
            'color': color,
            'components': components,
            'timestamp': datetime.now().isoformat()
        }

    except Exception as e:
        return {
            'score': 50,
            'label': 'Neutral',
            'color': '#eab308',
            'components': {},
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }


def get_market_health():
    """
    Get complete market health data.

    Returns combined breadth and fear/greed data.
    """
    breadth = calculate_market_breadth()
    fear_greed = calculate_fear_greed_index()

    # Overall health score (average of breadth and fear/greed)
    overall = (breadth['breadth_score'] + fear_greed['score']) / 2

    if overall >= 70:
        health_label = 'Bullish'
        health_color = '#22c55e'
    elif overall >= 50:
        health_label = 'Neutral-Bullish'
        health_color = '#84cc16'
    elif overall >= 30:
        health_label = 'Neutral-Bearish'
        health_color = '#f97316'
    else:
        health_label = 'Bearish'
        health_color = '#ef4444'

    return {
        'breadth': breadth,
        'fear_greed': fear_greed,
        'overall_score': round(overall, 1),
        'overall_label': health_label,
        'overall_color': health_color,
        'timestamp': datetime.now().isoformat()
    }


def format_health_report(health):
    """Format health data for Telegram."""
    fg = health['fear_greed']
    br = health['breadth']

    # Emoji for fear/greed
    if fg['score'] >= 80:
        fg_emoji = '🟢🟢'
    elif fg['score'] >= 60:
        fg_emoji = '🟢'
    elif fg['score'] >= 40:
        fg_emoji = '🟡'
    elif fg['score'] >= 20:
        fg_emoji = '🟠'
    else:
        fg_emoji = '🔴'

    msg = "📊 *MARKET HEALTH*\n\n"

    msg += f"*Fear & Greed:* {fg_emoji} {fg['score']:.0f} ({fg['label']})\n\n"

    msg += "*Components:*\n"
    for key, comp in fg.get('components', {}).items():
        score = comp['score']
        emoji = '🟢' if score >= 60 else ('🟡' if score >= 40 else '🔴')
        msg += f"  {emoji} {comp['label']}: {score:.0f}\n"

    msg += f"\n*Market Breadth:* {br['breadth_score']:.0f}/100\n"
    msg += f"  • Above 50 SMA: {br['above_50sma']:.0f}%\n"
    msg += f"  • Above 200 SMA: {br['above_200sma']:.0f}%\n"
    msg += f"  • A/D Ratio: {br['advance_decline_ratio']:.2f}\n"
    msg += f"  • New Highs: {br['new_highs']} | Lows: {br['new_lows']}\n"

    msg += f"\n*Overall:* {health['overall_label']} ({health['overall_score']:.0f}/100)"

    return msg


if __name__ == '__main__':
    print("Calculating market health...")
    health = get_market_health()
    print(format_health_report(health))
