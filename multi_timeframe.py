#!/usr/bin/env python3
"""
Multi-Timeframe Analysis Module

Analyzes stocks across daily, weekly, and monthly timeframes.
Confluence across timeframes = stronger signals.
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

from config import config
from utils import (
    get_logger, normalize_dataframe_columns, get_spy_data_cached,
    calculate_rs, safe_float, download_stock_data,
)

logger = get_logger(__name__)


def analyze_timeframe(df, timeframe_name):
    """Analyze a single timeframe."""
    if len(df) < 50:
        return None

    # Flatten columns if MultiIndex
    df = normalize_dataframe_columns(df)

    close = df['Close']
    current_price = float(close.iloc[-1])

    # MAs
    sma_20 = close.rolling(20).mean()
    sma_50 = close.rolling(50).mean()

    above_20 = current_price > float(sma_20.iloc[-1])
    above_50 = current_price > float(sma_50.iloc[-1])

    # Trend direction
    ma_20_slope = (float(sma_20.iloc[-1]) - float(sma_20.iloc[-5])) / float(sma_20.iloc[-5]) * 100
    ma_50_slope = (float(sma_50.iloc[-1]) - float(sma_50.iloc[-10])) / float(sma_50.iloc[-10]) * 100

    if ma_20_slope > 0.5:
        trend = 'UPTREND'
    elif ma_20_slope < -0.5:
        trend = 'DOWNTREND'
    else:
        trend = 'SIDEWAYS'

    # Momentum (rate of change)
    roc_10 = (current_price / float(close.iloc[-10]) - 1) * 100

    # Distance from 20 MA (extended or compressed)
    distance_from_ma = (current_price - float(sma_20.iloc[-1])) / float(sma_20.iloc[-1]) * 100

    return {
        'timeframe': timeframe_name,
        'trend': trend,
        'above_20ma': above_20,
        'above_50ma': above_50,
        'ma_20_slope': round(ma_20_slope, 2),
        'ma_50_slope': round(ma_50_slope, 2),
        'roc_10': round(roc_10, 2),
        'distance_from_ma': round(distance_from_ma, 2),
    }


def get_weekly_data(ticker, period='2y'):
    """Get weekly data for a ticker."""
    df = yf.download(ticker, period=period, interval='1wk', progress=False)
    return df


def get_monthly_data(ticker, period='5y'):
    """Get monthly data for a ticker."""
    df = yf.download(ticker, period=period, interval='1mo', progress=False)
    return df


def multi_timeframe_analysis(ticker):
    """
    Perform multi-timeframe analysis on a ticker.

    Returns analysis for daily, weekly, and monthly timeframes.
    """
    results = {}

    # Daily
    try:
        daily = yf.download(ticker, period='1y', progress=False)
        results['daily'] = analyze_timeframe(daily, 'DAILY')
    except Exception as e:
        logger.error(f"Error analyzing daily timeframe for {ticker}: {e}")
        results['daily'] = None

    # Weekly
    try:
        weekly = get_weekly_data(ticker)
        results['weekly'] = analyze_timeframe(weekly, 'WEEKLY')
    except Exception as e:
        logger.error(f"Error analyzing weekly timeframe for {ticker}: {e}")
        results['weekly'] = None

    # Monthly
    try:
        monthly = get_monthly_data(ticker)
        results['monthly'] = analyze_timeframe(monthly, 'MONTHLY')
    except Exception as e:
        logger.error(f"Error analyzing monthly timeframe for {ticker}: {e}")
        results['monthly'] = None

    # Calculate confluence score
    confluence = calculate_confluence(results)
    results['confluence'] = confluence

    return results


def calculate_confluence(mtf_results):
    """
    Calculate confluence score across timeframes.

    Higher score = more timeframes aligned bullish.
    """
    score = 0
    details = []

    for tf in ['daily', 'weekly', 'monthly']:
        data = mtf_results.get(tf)
        if data is None:
            continue

        # Trend alignment
        if data['trend'] == 'UPTREND':
            score += 2
            details.append(f"{tf}: Uptrend")
        elif data['trend'] == 'DOWNTREND':
            score -= 2
            details.append(f"{tf}: Downtrend")

        # Above MAs
        if data['above_20ma']:
            score += 1
        if data['above_50ma']:
            score += 1

    # Determine overall bias
    if score >= 6:
        bias = 'STRONG_BULLISH'
    elif score >= 3:
        bias = 'BULLISH'
    elif score >= 0:
        bias = 'NEUTRAL'
    elif score >= -3:
        bias = 'BEARISH'
    else:
        bias = 'STRONG_BEARISH'

    return {
        'score': score,
        'max_score': 12,  # 3 timeframes * (2 trend + 2 MAs)
        'bias': bias,
        'details': details,
    }


def format_mtf_analysis(ticker, results):
    """Format MTF analysis for Telegram."""
    msg = f"📊 *{ticker} MULTI-TIMEFRAME*\n\n"

    for tf in ['monthly', 'weekly', 'daily']:
        data = results.get(tf)
        if data is None:
            continue

        trend_emoji = '📈' if data['trend'] == 'UPTREND' else ('📉' if data['trend'] == 'DOWNTREND' else '➡️')

        msg += f"*{tf.upper()}:* {trend_emoji} {data['trend']}\n"
        msg += f"  • Above 20 MA: {'✅' if data['above_20ma'] else '❌'}\n"
        msg += f"  • Above 50 MA: {'✅' if data['above_50ma'] else '❌'}\n"
        msg += f"  • Momentum: {data['roc_10']:+.1f}%\n\n"

    # Confluence
    conf = results.get('confluence', {})
    bias = conf.get('bias', 'UNKNOWN')
    score = conf.get('score', 0)

    bias_emoji = {
        'STRONG_BULLISH': '🟢🟢',
        'BULLISH': '🟢',
        'NEUTRAL': '🟡',
        'BEARISH': '🔴',
        'STRONG_BEARISH': '🔴🔴',
    }.get(bias, '⚪')

    msg += f"*CONFLUENCE:* {bias_emoji} {bias}\n"
    msg += f"Score: {score}/12"

    return msg


def scan_mtf_confluence(tickers, min_score=6):
    """
    Scan multiple tickers for MTF confluence.

    Returns tickers with strong multi-timeframe alignment.
    """
    strong_confluence = []

    for ticker in tickers:
        try:
            results = multi_timeframe_analysis(ticker)
            conf = results.get('confluence', {})

            if conf.get('score', 0) >= min_score:
                strong_confluence.append({
                    'ticker': ticker,
                    'score': conf['score'],
                    'bias': conf['bias'],
                    'daily': results.get('daily', {}).get('trend', 'N/A'),
                    'weekly': results.get('weekly', {}).get('trend', 'N/A'),
                    'monthly': results.get('monthly', {}).get('trend', 'N/A'),
                })
        except Exception as e:
            logger.error(f"Error scanning MTF confluence for {ticker}: {e}")
            continue

    return sorted(strong_confluence, key=lambda x: x['score'], reverse=True)


def format_mtf_scan_results(results):
    """Format MTF scan results for Telegram."""
    if not results:
        return "No stocks found with strong MTF confluence."

    msg = "🎯 *MTF CONFLUENCE SCAN*\n"
    msg += "_Stocks aligned across all timeframes_\n\n"

    for r in results[:10]:
        msg += f"*{r['ticker']}* | Score: {r['score']}/12\n"
        msg += f"  D: {r['daily']} | W: {r['weekly']} | M: {r['monthly']}\n\n"

    return msg


if __name__ == '__main__':
    # Test single ticker
    ticker = 'NVDA'
    logger.info(f"Analyzing {ticker}...")
    results = multi_timeframe_analysis(ticker)
    logger.info(format_mtf_analysis(ticker, results))

    logger.info("=" * 60)

    # Test scan
    test_tickers = ['NVDA', 'AMD', 'AAPL', 'MSFT', 'GOOGL', 'META', 'TSLA', 'AMZN']
    logger.info("Scanning for MTF confluence...")
    scan_results = scan_mtf_confluence(test_tickers)
    logger.info(format_mtf_scan_results(scan_results))
