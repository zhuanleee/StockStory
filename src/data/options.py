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
    get_technical_summary_sync,
    get_options_contracts_sync,
    get_snapshot_sync
)
from typing import Dict, List
from datetime import datetime, timedelta
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


def get_options_expirations(ticker: str) -> Dict:
    """
    Get available options expiration dates for a ticker.

    Returns:
        {
            'ticker': str,
            'expirations': List[str],  # YYYY-MM-DD format
            'nearest': str,  # Nearest expiration
            'count': int
        }
    """
    try:
        logger.info(f"Fetching options expirations for {ticker}")

        # Use contracts endpoint to get all available expirations
        # Search for contracts expiring in the next 90 days
        today = datetime.now().strftime('%Y-%m-%d')
        end_date = (datetime.now() + timedelta(days=90)).strftime('%Y-%m-%d')

        contracts = get_options_contracts_sync(
            underlying=ticker,
            expiration_date_gte=today,
            expiration_date_lte=end_date,
            limit=1000  # Get lots of contracts to find all expirations
        )

        if not contracts:
            # Fallback: try to get from chain data
            chain = get_options_chain_sync(ticker)
            if chain and 'calls' in chain:
                expirations = set()
                for c in chain.get('calls', []):
                    exp = c.get('expiration')
                    if exp:
                        expirations.add(exp)
                for p in chain.get('puts', []):
                    exp = p.get('expiration')
                    if exp:
                        expirations.add(exp)
                if expirations:
                    sorted_exps = sorted(list(expirations))
                    return {
                        'ticker': ticker.upper(),
                        'expirations': sorted_exps,
                        'nearest': sorted_exps[0],
                        'count': len(sorted_exps)
                    }
            return {"error": "Could not fetch options data", "ticker": ticker}

        # Extract unique expirations from contracts
        expirations = set()
        for c in contracts:
            exp = c.get('expiration')
            if exp:
                expirations.add(exp)

        # Sort chronologically and filter to future dates only
        sorted_exps = sorted([e for e in expirations if e >= today])

        if not sorted_exps:
            return {"error": "No expirations found", "ticker": ticker}

        logger.info(f"Found {len(sorted_exps)} expirations for {ticker}")

        return {
            'ticker': ticker.upper(),
            'expirations': sorted_exps,
            'nearest': sorted_exps[0] if sorted_exps else None,
            'count': len(sorted_exps)
        }

    except Exception as e:
        logger.error(f"Failed to get expirations for {ticker}: {e}")
        return {"error": str(e), "ticker": ticker}


def calculate_max_pain(ticker: str, expiration: str = None) -> Dict:
    """
    Calculate Max Pain price for a ticker at a specific expiration.

    Max Pain Theory: The strike price where option writers (sellers)
    lose the least money if the stock closes at that price at expiration.

    Args:
        ticker: Stock symbol
        expiration: Expiration date (YYYY-MM-DD). If None, uses nearest expiration.

    Returns:
        {
            'ticker': str,
            'expiration': str,  # The expiration date used
            'max_pain_price': float,
            'current_price': float,
            'distance_pct': float,  # How far current price is from max pain
            'direction': str,  # 'above' or 'below' max pain
            'pain_by_strike': List[Dict],  # Pain value at each strike
            'total_call_oi': int,
            'total_put_oi': int,
            'days_to_expiry': int,
            'interpretation': str
        }
    """
    try:
        logger.info(f"Calculating max pain for {ticker} (expiration: {expiration or 'nearest'})")

        # Get options chain data (optionally filtered by expiration)
        chain = get_options_chain_sync(ticker, expiration)
        if not chain or 'error' in chain:
            return {"error": "Could not fetch options chain", "ticker": ticker}

        calls = chain.get('calls', [])
        puts = chain.get('puts', [])

        if not calls and not puts:
            return {"error": "No options data available", "ticker": ticker}

        # Get current price from real-time snapshot (more accurate than options chain data)
        current_price = 0
        try:
            snapshot = get_snapshot_sync(ticker)
            if snapshot:
                current_price = snapshot.get('price') or snapshot.get('last_price') or 0
                logger.debug(f"Got real-time price for {ticker}: ${current_price}")
        except Exception as e:
            logger.warning(f"Failed to get snapshot price for {ticker}: {e}")

        # Fallback to chain data if snapshot failed
        if not current_price:
            current_price = chain.get('summary', {}).get('underlying_price', 0)
        if not current_price and calls:
            # Last resort: estimate from ATM strike
            current_price = calls[len(calls)//2].get('strike', 0)

        # Collect all unique strikes
        strikes = set()
        for c in calls:
            strikes.add(c.get('strike', 0))
        for p in puts:
            strikes.add(p.get('strike', 0))

        strikes = sorted([s for s in strikes if s > 0])

        if not strikes:
            return {"error": "No valid strikes found", "ticker": ticker}

        # Build OI lookup by strike
        call_oi_by_strike = {c.get('strike'): c.get('open_interest', 0) for c in calls}
        put_oi_by_strike = {p.get('strike'): p.get('open_interest', 0) for p in puts}

        # Calculate pain at each strike
        # Pain = sum of (intrinsic value * OI) for all options that would be ITM
        pain_by_strike = []

        for strike in strikes:
            total_pain = 0

            # If stock closes at this strike:
            # - All calls with strike < this price are ITM (pain to call writers)
            # - All puts with strike > this price are ITM (pain to put writers)

            for call_strike, call_oi in call_oi_by_strike.items():
                if call_strike < strike:  # Call is ITM
                    intrinsic = (strike - call_strike) * 100  # Per contract value
                    total_pain += intrinsic * call_oi

            for put_strike, put_oi in put_oi_by_strike.items():
                if put_strike > strike:  # Put is ITM
                    intrinsic = (put_strike - strike) * 100  # Per contract value
                    total_pain += intrinsic * put_oi

            pain_by_strike.append({
                'strike': strike,
                'pain': total_pain,
                'call_oi': call_oi_by_strike.get(strike, 0),
                'put_oi': put_oi_by_strike.get(strike, 0)
            })

        # Max pain is the strike with minimum total pain
        if pain_by_strike:
            min_pain = min(pain_by_strike, key=lambda x: x['pain'])
            max_pain_price = min_pain['strike']
        else:
            max_pain_price = current_price

        # Calculate distance from current price
        if current_price > 0:
            distance_pct = ((current_price - max_pain_price) / current_price) * 100
            direction = 'above' if current_price > max_pain_price else 'below'
        else:
            distance_pct = 0
            direction = 'unknown'

        # Generate interpretation
        if abs(distance_pct) < 1:
            interpretation = f"Price is near max pain (${max_pain_price:.2f}). Expect sideways movement."
        elif distance_pct > 3:
            interpretation = f"Price is {abs(distance_pct):.1f}% above max pain. Gravitational pull may bring price down toward ${max_pain_price:.2f}."
        elif distance_pct < -3:
            interpretation = f"Price is {abs(distance_pct):.1f}% below max pain. Gravitational pull may push price up toward ${max_pain_price:.2f}."
        else:
            interpretation = f"Price is within normal range of max pain (${max_pain_price:.2f})."

        # Get totals
        total_call_oi = sum(c.get('open_interest', 0) for c in calls)
        total_put_oi = sum(p.get('open_interest', 0) for p in puts)

        # Determine actual expiration used (from first contract or parameter)
        used_expiration = expiration
        if not used_expiration and calls:
            used_expiration = calls[0].get('expiration')
        if not used_expiration and puts:
            used_expiration = puts[0].get('expiration')
        if not used_expiration:
            used_expiration = 'Unknown'

        # Calculate days to expiry
        days_to_expiry = 0
        if used_expiration and used_expiration != 'Unknown':
            try:
                exp_date = datetime.strptime(used_expiration, '%Y-%m-%d')
                days_to_expiry = (exp_date - datetime.now()).days
                if days_to_expiry < 0:
                    days_to_expiry = 0
            except:
                pass

        # Enhanced interpretation with expiry context
        if days_to_expiry <= 2:
            interpretation += f" ⚠️ Expiration in {days_to_expiry} days - max pain effect strongest!"
        elif days_to_expiry <= 5:
            interpretation += f" Options expire in {days_to_expiry} days."

        result = {
            'ticker': ticker.upper(),
            'expiration': used_expiration,
            'days_to_expiry': days_to_expiry,
            'max_pain_price': max_pain_price,
            'current_price': current_price,
            'distance_pct': round(distance_pct, 2),
            'direction': direction,
            'pain_by_strike': pain_by_strike[:20],  # Top 20 strikes
            'total_call_oi': total_call_oi,
            'total_put_oi': total_put_oi,
            'interpretation': interpretation
        }

        logger.info(f"✅ Max pain for {ticker} ({used_expiration}): ${max_pain_price:.2f} (current: ${current_price:.2f}, {direction} by {abs(distance_pct):.1f}%)")
        return result

    except Exception as e:
        logger.error(f"Max pain calculation error for {ticker}: {e}")
        return {"error": str(e), "ticker": ticker}


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
