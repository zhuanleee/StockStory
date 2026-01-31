#!/usr/bin/env python3
"""
Options Data Aggregator

Centralized wrapper around Polygon options functions for easy API consumption.
All Polygon functions already exist in polygon_provider.py - this module provides:
- Clean abstraction layer between Polygon and API endpoints
- Centralized error handling
- Data aggregation (overview function)
- Universe scanning capabilities
"""

from src.data.polygon_provider import (
    get_options_flow_sync,
    get_unusual_options_sync,
    get_options_chain_sync,
    get_technical_summary_sync
)
from typing import Dict, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def get_options_flow(ticker: str) -> Dict:
    """
    Get options flow summary for a ticker.

    Returns:
        {
            'put_call_ratio': float,
            'sentiment': str (bullish/bearish/neutral),
            'sentiment_score': int (0-100),
            'total_call_volume': int,
            'total_put_volume': int,
            'total_call_oi': int,
            'total_put_oi': int,
            'has_unusual_activity': bool
        }
    """
    try:
        logger.debug(f"Fetching options flow for {ticker}")
        result = get_options_flow_sync(ticker)
        if result and 'error' not in result:
            logger.info(f"✅ Options flow for {ticker}: {result.get('sentiment')} ({result.get('put_call_ratio')})")
            return result
        return result or {"error": "No options flow data available"}
    except Exception as e:
        logger.error(f"Options flow error for {ticker}: {e}")
        return {"error": str(e)}


def get_unusual_activity(ticker: str, threshold: float = 2.0) -> Dict:
    """
    Detect unusual options activity for a ticker.

    Args:
        ticker: Stock symbol
        threshold: Volume/OI ratio threshold (default 2.0x)

    Returns:
        {
            'unusual_activity': bool,
            'unusual_contracts': List[Dict],  # Top 10 contracts
            'signals': List[Dict],  # Flow signals
            'summary': Dict,
            'total_unusual_contracts': int
        }
    """
    try:
        logger.debug(f"Scanning unusual options activity for {ticker} (threshold: {threshold})")
        result = get_unusual_options_sync(ticker, threshold)
        if result and 'error' not in result:
            count = len(result.get('unusual_contracts', []))
            logger.info(f"✅ Unusual options for {ticker}: {count} contracts, activity={result.get('unusual_activity')}")
            return result
        return result or {"error": "No unusual activity data available"}
    except Exception as e:
        logger.error(f"Unusual options error for {ticker}: {e}")
        return {"error": str(e)}


def get_options_chain(ticker: str, expiration: str = None) -> Dict:
    """
    Get full options chain with Greeks for a ticker.

    Args:
        ticker: Stock symbol
        expiration: Optional expiration date filter (YYYY-MM-DD)

    Returns:
        {
            'underlying': str,
            'calls': List[Dict],  # Call contracts with Greeks
            'puts': List[Dict],   # Put contracts with Greeks
            'summary': Dict       # PC ratios, sentiment
        }
    """
    try:
        logger.debug(f"Fetching options chain for {ticker} (expiration: {expiration or 'all'})")
        result = get_options_chain_sync(ticker, expiration)
        if result and 'error' not in result:
            calls_count = len(result.get('calls', []))
            puts_count = len(result.get('puts', []))
            logger.info(f"✅ Options chain for {ticker}: {calls_count} calls, {puts_count} puts")
            return result
        return result or {"error": "No options chain data available"}
    except Exception as e:
        logger.error(f"Options chain error for {ticker}: {e}")
        return {"error": str(e)}


def get_technical_indicators(ticker: str) -> Dict:
    """
    Get technical indicators summary (SMA, RSI, MACD, trend).

    Returns:
        {
            'ticker': str,
            'price': float,
            'sma_20': float,
            'sma_50': float,
            'sma_200': float,
            'rsi': float,
            'macd': float,
            'macd_signal': float,
            'trend': str,
            'signals': List[str]
        }
    """
    try:
        logger.debug(f"Fetching technical indicators for {ticker}")
        result = get_technical_summary_sync(ticker)
        if result and 'error' not in result:
            logger.info(f"✅ Technical indicators for {ticker}: trend={result.get('trend')}, RSI={result.get('rsi')}")
            return result
        return result or {"error": "No technical indicators available"}
    except Exception as e:
        logger.error(f"Technical indicators error for {ticker}: {e}")
        return {"error": str(e)}


def get_options_overview(ticker: str) -> Dict:
    """
    Comprehensive options overview combining:
    - Flow sentiment
    - Unusual activity alerts
    - Technical indicators

    Perfect for dashboard "quick view" components.

    Returns:
        {
            'ticker': str,
            'flow': Dict,
            'unusual_activity': Dict,
            'technical': Dict,
            'timestamp': str
        }
    """
    try:
        logger.info(f"Generating options overview for {ticker}")

        # Fetch all data in parallel (sync wrappers are fast)
        flow = get_options_flow(ticker)
        unusual = get_unusual_activity(ticker)
        technical = get_technical_indicators(ticker)

        overview = {
            "ticker": ticker.upper(),
            "flow": flow,
            "unusual_activity": unusual,
            "technical": technical,
            "timestamp": datetime.now().isoformat()
        }

        logger.info(f"✅ Options overview complete for {ticker}")
        return overview

    except Exception as e:
        logger.error(f"Options overview error for {ticker}: {e}")
        return {
            "ticker": ticker.upper(),
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


def scan_unusual_options_universe(tickers: List[str], min_threshold: float = 2.0, limit: int = 20) -> List[Dict]:
    """
    Scan multiple tickers for unusual options activity.

    Args:
        tickers: List of stock symbols to scan
        min_threshold: Minimum vol/OI ratio (default 2.0)
        limit: Maximum results to return (default 20)

    Returns:
        List of tickers with unusual activity, sorted by contract count descending.
        [
            {
                'ticker': str,
                'unusual_contracts': int,
                'signals': List[Dict],
                'summary': Dict
            }
        ]
    """
    try:
        logger.info(f"Scanning {len(tickers)} tickers for unusual options activity (threshold: {min_threshold})")

        results = []

        for ticker in tickers:
            try:
                unusual = get_unusual_activity(ticker, min_threshold)

                # Only include if unusual activity detected
                if unusual.get('unusual_activity') and not unusual.get('error'):
                    results.append({
                        'ticker': ticker,
                        'unusual_contracts': len(unusual.get('unusual_contracts', [])),
                        'signals': unusual.get('signals', []),
                        'summary': unusual.get('summary', {})
                    })
            except Exception as e:
                logger.debug(f"Skipping {ticker} in unusual scan: {e}")
                continue

        # Sort by number of unusual contracts (most unusual first)
        results.sort(key=lambda x: x['unusual_contracts'], reverse=True)

        # Limit results
        results = results[:limit]

        logger.info(f"✅ Unusual options scan complete: {len(results)} tickers with unusual activity")
        return results

    except Exception as e:
        logger.error(f"Unusual options scan error: {e}")
        return []


# Example usage
if __name__ == '__main__':
    # Test the functions
    print("Testing Options Data Aggregator...\n")

    ticker = "AAPL"

    print(f"1. Options Flow for {ticker}:")
    flow = get_options_flow(ticker)
    print(f"   Sentiment: {flow.get('sentiment')}, PC Ratio: {flow.get('put_call_ratio')}\n")

    print(f"2. Unusual Activity for {ticker}:")
    unusual = get_unusual_activity(ticker)
    print(f"   Unusual: {unusual.get('unusual_activity')}, Contracts: {len(unusual.get('unusual_contracts', []))}\n")

    print(f"3. Technical Indicators for {ticker}:")
    tech = get_technical_indicators(ticker)
    print(f"   Trend: {tech.get('trend')}, RSI: {tech.get('rsi')}\n")

    print(f"4. Complete Overview for {ticker}:")
    overview = get_options_overview(ticker)
    print(f"   Timestamp: {overview.get('timestamp')}\n")

    print("5. Scanning universe for unusual options:")
    universe = ["AAPL", "TSLA", "NVDA", "SPY", "AMD"]
    unusual_scan = scan_unusual_options_universe(universe, limit=5)
    print(f"   Found {len(unusual_scan)} tickers with unusual activity")
    for item in unusual_scan:
        print(f"   - {item['ticker']}: {item['unusual_contracts']} contracts")
