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
    get_snapshot_sync,
    get_price_data_sync
)
from typing import Dict, List
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# Futures contract specifications
# Multiplier = dollar value per point of movement
FUTURES_SPECS = {
    'ES': {'name': 'E-mini S&P 500', 'multiplier': 50, 'tick_size': 0.25},
    'NQ': {'name': 'E-mini Nasdaq 100', 'multiplier': 20, 'tick_size': 0.25},
    'CL': {'name': 'Crude Oil', 'multiplier': 1000, 'tick_size': 0.01},
    'GC': {'name': 'Gold', 'multiplier': 100, 'tick_size': 0.10},
    'SI': {'name': 'Silver', 'multiplier': 5000, 'tick_size': 0.005},
    'ZB': {'name': '30-Year Treasury', 'multiplier': 1000, 'tick_size': 1/32},
    'ZN': {'name': '10-Year Treasury', 'multiplier': 1000, 'tick_size': 1/64},
    'RTY': {'name': 'E-mini Russell 2000', 'multiplier': 50, 'tick_size': 0.10},
    'YM': {'name': 'E-mini Dow', 'multiplier': 5, 'tick_size': 1.0},
    'MES': {'name': 'Micro E-mini S&P', 'multiplier': 5, 'tick_size': 0.25},
    'MNQ': {'name': 'Micro E-mini Nasdaq', 'multiplier': 2, 'tick_size': 0.25},
}


def is_futures_ticker(ticker: str) -> bool:
    """Check if ticker is a futures contract."""
    return ticker.upper() in FUTURES_SPECS


def get_futures_info(ticker: str) -> Dict:
    """Get futures contract info if it's a futures ticker."""
    ticker_upper = ticker.upper()
    if ticker_upper in FUTURES_SPECS:
        return {
            'is_futures': True,
            'ticker': ticker_upper,
            **FUTURES_SPECS[ticker_upper]
        }
    return {'is_futures': False, 'ticker': ticker_upper, 'multiplier': 100}  # Default for equities


def get_contract_multiplier(ticker: str) -> int:
    """Get contract multiplier for a ticker (futures or equity options)."""
    ticker_upper = ticker.upper()
    if ticker_upper in FUTURES_SPECS:
        return FUTURES_SPECS[ticker_upper]['multiplier']
    return 100  # Standard equity options = 100 shares


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

        # If no expiration provided, get the nearest one to avoid mixing multiple expirations
        if not expiration:
            try:
                expirations = get_options_expirations(ticker)
                if expirations and expirations.get('expirations'):
                    expiration = expirations['expirations'][0]  # Nearest expiration
                    logger.info(f"Using nearest expiration for {ticker}: {expiration}")
            except Exception as e:
                logger.warning(f"Could not fetch expirations for {ticker}: {e}")

        # Get options chain data filtered by expiration
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
        # Get contract multiplier (100 for equities, varies for futures)
        multiplier = get_contract_multiplier(ticker)
        futures_info = get_futures_info(ticker)

        pain_by_strike = []

        for strike in strikes:
            total_pain = 0

            # If stock closes at this strike:
            # - All calls with strike < this price are ITM (pain to call writers)
            # - All puts with strike > this price are ITM (pain to put writers)

            for call_strike, call_oi in call_oi_by_strike.items():
                if call_strike < strike:  # Call is ITM
                    intrinsic = (strike - call_strike) * multiplier  # Per contract value
                    total_pain += intrinsic * call_oi

            for put_strike, put_oi in put_oi_by_strike.items():
                if put_strike > strike:  # Put is ITM
                    intrinsic = (put_strike - strike) * multiplier  # Per contract value
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

        # Filter pain_by_strike to strikes around current price (+/- 15%)
        # This gives a meaningful chart view
        if current_price > 0:
            min_strike = current_price * 0.85
            max_strike = current_price * 1.15
            filtered_pain = [p for p in pain_by_strike if min_strike <= p['strike'] <= max_strike]
            # If not enough strikes in range, use strikes around max pain
            if len(filtered_pain) < 10:
                # Find max pain index and take 25 strikes centered on it
                max_pain_idx = next((i for i, p in enumerate(pain_by_strike) if p['strike'] == max_pain_price), len(pain_by_strike) // 2)
                start = max(0, max_pain_idx - 12)
                end = min(len(pain_by_strike), max_pain_idx + 13)
                filtered_pain = pain_by_strike[start:end]
        else:
            filtered_pain = pain_by_strike[:25]

        result = {
            'ticker': ticker.upper(),
            'expiration': used_expiration,
            'days_to_expiry': days_to_expiry,
            'max_pain_price': max_pain_price,
            'current_price': current_price,
            'distance_pct': round(distance_pct, 2),
            'direction': direction,
            'pain_by_strike': filtered_pain,
            'total_call_oi': total_call_oi,
            'total_put_oi': total_put_oi,
            'interpretation': interpretation,
            'is_futures': futures_info.get('is_futures', False),
            'futures_name': futures_info.get('name'),
            'contract_multiplier': multiplier
        }

        logger.info(f"✅ Max pain for {ticker} ({used_expiration}): ${max_pain_price:.2f} (current: ${current_price:.2f}, {direction} by {abs(distance_pct):.1f}%, multiplier={multiplier})")
        return result

    except Exception as e:
        logger.error(f"Max pain calculation error for {ticker}: {e}")
        return {"error": str(e), "ticker": ticker}


def calculate_gex_by_strike(ticker: str, expiration: str = None) -> Dict:
    """
    Calculate Gamma Exposure (GEX) by strike price.

    GEX measures how much dealers need to hedge as price moves.
    - Positive GEX: Dealers buy dips, sell rips (stabilizing)
    - Negative GEX: Dealers amplify moves (volatile)

    Formula per strike:
    GEX = (Call Gamma × Call OI × 100) - (Put Gamma × Put OI × 100)

    Returns:
        {
            'ticker': str,
            'expiration': str,
            'current_price': float,
            'total_gex': float,
            'gex_by_strike': List[Dict],  # [{strike, call_gex, put_gex, net_gex}, ...]
            'zero_gamma_level': float,  # Strike where GEX flips sign
        }
    """
    try:
        logger.info(f"Calculating GEX by strike for {ticker}")

        # If no expiration, get nearest
        if not expiration:
            try:
                expirations = get_options_expirations(ticker)
                if expirations and expirations.get('expirations'):
                    expiration = expirations['expirations'][0]
            except:
                pass

        # Get options chain with gamma data
        chain = get_options_chain_sync(ticker, expiration)
        if not chain or 'error' in chain:
            return {"error": "Could not fetch options chain", "ticker": ticker}

        calls = chain.get('calls', [])
        puts = chain.get('puts', [])

        if not calls and not puts:
            return {"error": "No options data", "ticker": ticker}

        # Get current price
        current_price = 0
        try:
            snapshot = get_snapshot_sync(ticker)
            if snapshot:
                current_price = snapshot.get('price') or snapshot.get('last_price') or 0
        except:
            pass
        if not current_price and calls:
            current_price = calls[len(calls)//2].get('underlying_price') or 0

        # Build GEX by strike
        # Group by strike
        strikes = set()
        call_data = {}  # strike -> {gamma, oi}
        put_data = {}   # strike -> {gamma, oi}

        for c in calls:
            strike = c.get('strike')
            if strike:
                strikes.add(strike)
                gamma = c.get('gamma') or 0
                oi = c.get('open_interest') or 0
                call_data[strike] = {'gamma': gamma, 'oi': oi}

        for p in puts:
            strike = p.get('strike')
            if strike:
                strikes.add(strike)
                gamma = p.get('gamma') or 0
                oi = p.get('open_interest') or 0
                put_data[strike] = {'gamma': gamma, 'oi': oi}

        # Calculate GEX per strike using INDUSTRY STANDARD formula:
        # GEX = Gamma × OI × Multiplier × Spot² / 100
        # This normalizes to "per 1% move" basis (SpotGamma convention)
        # Calls: positive contribution (dealers sold calls = long gamma exposure)
        # Puts: negative contribution (dealers sold puts = short gamma exposure)
        # Multiplier: 100 for equities, varies for futures (ES=50, NQ=20, etc.)
        multiplier = get_contract_multiplier(ticker)
        futures_info = get_futures_info(ticker)

        gex_by_strike = []
        total_gex = 0

        for strike in sorted(strikes):
            call_info = call_data.get(strike, {'gamma': 0, 'oi': 0})
            put_info = put_data.get(strike, {'gamma': 0, 'oi': 0})

            # Industry standard GEX formula: Gamma × OI × Multiplier × Spot² / 100
            # This gives dollar GEX per 1% move in underlying
            call_gex = call_info['gamma'] * call_info['oi'] * multiplier * (current_price ** 2) / 100
            # Puts: dealers are SHORT gamma on puts they sold, so negative
            put_gex = -put_info['gamma'] * put_info['oi'] * multiplier * (current_price ** 2) / 100
            net_gex = call_gex + put_gex

            total_gex += net_gex

            gex_by_strike.append({
                'strike': strike,
                'call_gex': round(call_gex, 0),
                'put_gex': round(put_gex, 0),
                'net_gex': round(net_gex, 0),
                'call_oi': call_info['oi'],
                'put_oi': put_info['oi']
            })

        # Find zero gamma level (where GEX flips from negative to positive)
        zero_gamma = None
        for i, g in enumerate(gex_by_strike):
            if i > 0 and gex_by_strike[i-1]['net_gex'] < 0 and g['net_gex'] >= 0:
                zero_gamma = g['strike']
                break

        # Filter to +/- 15% of current price
        if current_price > 0:
            min_s = current_price * 0.85
            max_s = current_price * 1.15
            gex_by_strike = [g for g in gex_by_strike if min_s <= g['strike'] <= max_s]

        # Get expiration used
        used_exp = expiration
        if not used_exp and calls:
            used_exp = calls[0].get('expiration')

        logger.info(f"✅ GEX calculated for {ticker}: total ${total_gex/1e6:.1f}M (multiplier={multiplier})")

        return {
            'ticker': ticker.upper(),
            'expiration': used_exp,
            'current_price': current_price,
            'total_gex': round(total_gex, 0),
            'gex_by_strike': gex_by_strike,
            'zero_gamma_level': zero_gamma,
            'is_futures': futures_info.get('is_futures', False),
            'futures_name': futures_info.get('name'),
            'contract_multiplier': multiplier
        }

    except Exception as e:
        logger.error(f"GEX calculation error for {ticker}: {e}")
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


def calculate_volume_profile(ticker: str, days: int = 30, num_bins: int = 50) -> Dict:
    """
    Calculate Volume Profile for a stock.

    Volume Profile shows where the most trading activity occurred at each price level.
    Key levels:
    - POC (Point of Control): Price level with highest volume - strongest support/resistance
    - VAH (Value Area High): Upper bound of 70% volume zone
    - VAL (Value Area Low): Lower bound of 70% volume zone
    - HVN (High Volume Nodes): Prices with heavy trading - support/resistance
    - LVN (Low Volume Nodes): Prices with light trading - breakout zones

    Args:
        ticker: Stock symbol (e.g., 'SPY')
        days: Number of days to analyze (default 30)
        num_bins: Number of price levels to group volume (default 50)

    Returns:
        {
            'ticker': str,
            'current_price': float,
            'poc': float (Point of Control - highest volume price),
            'vah': float (Value Area High),
            'val': float (Value Area Low),
            'daily_high': float,
            'daily_low': float,
            'hvn': List[float] (High Volume Nodes),
            'lvn': List[float] (Low Volume Nodes),
            'volume_by_price': List[{'price': float, 'volume': int, 'pct': float}],
            'analysis': str,
            'days_analyzed': int
        }
    """
    try:
        logger.info(f"Calculating volume profile for {ticker} ({days} days)")

        # Get price data
        df = get_price_data_sync(ticker, days=days)

        if df is None or df.empty:
            return {"error": f"No price data available for {ticker}", "ticker": ticker}

        # Get current price from snapshot
        current_price = 0
        try:
            snapshot = get_snapshot_sync(ticker)
            if snapshot:
                current_price = snapshot.get('price') or snapshot.get('last_price') or 0
        except:
            pass

        if not current_price:
            current_price = float(df['Close'].iloc[-1])

        # Get daily high/low from most recent day
        daily_high = float(df['High'].iloc[-1])
        daily_low = float(df['Low'].iloc[-1])

        # Calculate price range for binning
        price_high = float(df['High'].max())
        price_low = float(df['Low'].min())
        price_range = price_high - price_low

        if price_range == 0:
            return {"error": "Invalid price range", "ticker": ticker}

        bin_size = price_range / num_bins

        # Create volume profile - allocate volume to price bins
        volume_profile = {}

        for idx, row in df.iterrows():
            # Distribute volume across high-low range for each bar
            bar_high = float(row['High'])
            bar_low = float(row['Low'])
            bar_volume = float(row['Volume'])

            # Find bins this bar covers
            low_bin = int((bar_low - price_low) / bin_size)
            high_bin = int((bar_high - price_low) / bin_size)

            # Clamp to valid range
            low_bin = max(0, min(low_bin, num_bins - 1))
            high_bin = max(0, min(high_bin, num_bins - 1))

            # Distribute volume evenly across covered bins
            bins_covered = max(1, high_bin - low_bin + 1)
            volume_per_bin = bar_volume / bins_covered

            for b in range(low_bin, high_bin + 1):
                bin_price = price_low + (b + 0.5) * bin_size
                if bin_price not in volume_profile:
                    volume_profile[bin_price] = 0
                volume_profile[bin_price] += volume_per_bin

        # Sort by price
        sorted_prices = sorted(volume_profile.keys())
        total_volume = sum(volume_profile.values())

        # Find POC (Point of Control) - price with highest volume
        poc_price = max(volume_profile.keys(), key=lambda p: volume_profile[p])

        # Calculate Value Area (70% of volume around POC)
        # Start from POC and expand until we capture 70%
        poc_idx = sorted_prices.index(poc_price)
        value_area_volume = volume_profile[poc_price]
        target_volume = total_volume * 0.70

        low_idx = poc_idx
        high_idx = poc_idx

        while value_area_volume < target_volume and (low_idx > 0 or high_idx < len(sorted_prices) - 1):
            # Check which direction adds more volume
            low_add = volume_profile[sorted_prices[low_idx - 1]] if low_idx > 0 else 0
            high_add = volume_profile[sorted_prices[high_idx + 1]] if high_idx < len(sorted_prices) - 1 else 0

            if low_add >= high_add and low_idx > 0:
                low_idx -= 1
                value_area_volume += low_add
            elif high_idx < len(sorted_prices) - 1:
                high_idx += 1
                value_area_volume += high_add
            else:
                break

        val = sorted_prices[low_idx]  # Value Area Low
        vah = sorted_prices[high_idx]  # Value Area High

        # Find HVN and LVN
        avg_volume = total_volume / len(volume_profile)
        hvn = []
        lvn = []

        for price, vol in volume_profile.items():
            if vol > avg_volume * 1.5:
                hvn.append(round(price, 2))
            elif vol < avg_volume * 0.5:
                lvn.append(round(price, 2))

        # Sort and limit
        hvn = sorted(hvn)[:5]  # Top 5 HVNs
        lvn = sorted(lvn)[:5]  # Top 5 LVNs

        # Build volume by price list (for visualization)
        volume_by_price = []
        max_vol = max(volume_profile.values())
        for price in sorted_prices:
            vol = volume_profile[price]
            volume_by_price.append({
                'price': round(price, 2),
                'volume': int(vol),
                'pct': round(vol / max_vol * 100, 1)
            })

        # Analysis
        analysis = ""
        if current_price > vah:
            analysis = f"Price above Value Area High (${vah:.2f}) - Extended, may pull back to POC"
        elif current_price < val:
            analysis = f"Price below Value Area Low (${val:.2f}) - Weak, may rally to VAL/POC"
        elif abs(current_price - poc_price) < (vah - val) * 0.1:
            analysis = f"Price at POC (${poc_price:.2f}) - Fair value zone, consolidation expected"
        elif current_price > poc_price:
            analysis = f"Price above POC - Bullish bias, VAH (${vah:.2f}) is resistance"
        else:
            analysis = f"Price below POC - Bearish bias, VAL (${val:.2f}) is support"

        result = {
            'ticker': ticker.upper(),
            'current_price': round(current_price, 2),
            'poc': round(poc_price, 2),
            'vah': round(vah, 2),
            'val': round(val, 2),
            'daily_high': round(daily_high, 2),
            'daily_low': round(daily_low, 2),
            'hvn': hvn,
            'lvn': lvn,
            'volume_by_price': volume_by_price[-20:] if len(volume_by_price) > 20 else volume_by_price,  # Limit for API
            'analysis': analysis,
            'days_analyzed': len(df)
        }

        logger.info(f"✅ Volume profile for {ticker}: POC=${poc_price:.2f}, VAH=${vah:.2f}, VAL=${val:.2f}")
        return result

    except Exception as e:
        logger.error(f"Volume profile error for {ticker}: {e}")
        return {"error": str(e), "ticker": ticker}


# =============================================================================
# GEX-BASED MODELS
# =============================================================================

def get_gex_regime(ticker: str, expiration: str = None) -> Dict:
    """
    GEX Volatility Regime Classifier

    Classifies the current market regime based on GEX:
    - PINNED (high positive GEX): Mean-reversion strategies win, fade breakouts, sell premium
    - VOLATILE (negative GEX): Trend-following wins, buy breakouts, reduce size or buy premium
    - TRANSITIONAL (near zero/gamma flip): Highest uncertainty, reduce exposure

    Returns:
        {
            'regime': str ('pinned', 'volatile', 'transitional'),
            'regime_score': float (-100 to +100),
            'gex_normalized': float (GEX / market cap proxy),
            'recommendation': str,
            'position_sizing': float (0.25, 0.5, 1.0),
            'strategy_bias': str,
            ...
        }
    """
    try:
        # Get GEX data
        gex_data = calculate_gex_by_strike(ticker, expiration)
        if 'error' in gex_data:
            return gex_data

        total_gex = gex_data.get('total_gex', 0)
        current_price = gex_data.get('current_price', 0)
        zero_gamma = gex_data.get('zero_gamma_level')
        gex_by_strike = gex_data.get('gex_by_strike', [])

        # Normalize GEX to billions for regime classification
        # With industry standard formula (Spot² / 100), GEX scales with price²
        # For SPY at ~$500, typical significant GEX is $2-5B per 1% move
        if current_price > 0:
            gex_normalized = total_gex / 1e9  # GEX in billions
        else:
            gex_normalized = 0

        # Thresholds calibrated for industry standard formula (Spot² / 100)
        # For SPY ~$500: positive >$2.5B, negative <-$1.5B per 1% move
        # Scale thresholds by (price/500)² for other tickers
        price_scale = (current_price / 500) ** 2 if current_price > 0 else 1
        POSITIVE_GEX_THRESHOLD = 2.5 * price_scale   # Strong positive GEX
        NEGATIVE_GEX_THRESHOLD = -1.5 * price_scale  # Negative GEX territory
        TRANSITIONAL_BAND = 1.0 * price_scale        # Near gamma flip zone

        # Determine regime
        # Scale factor for score: normalize to 0-100 range based on thresholds
        score_scale = 10 / price_scale if price_scale > 0 else 10

        if gex_normalized > POSITIVE_GEX_THRESHOLD:
            regime = 'pinned'
            regime_score = min(100, gex_normalized * score_scale)  # Scale to 0-100
            position_sizing = 1.0  # Full size
            strategy_bias = 'mean_reversion'
            recommendation = 'Dealers will dampen moves. Fade breakouts, sell premium, buy dips.'
        elif gex_normalized < NEGATIVE_GEX_THRESHOLD:
            regime = 'volatile'
            regime_score = max(-100, gex_normalized * score_scale)  # Scale to -100-0
            position_sizing = 0.25  # Quarter size - high risk
            strategy_bias = 'trend_following'
            recommendation = 'Dealers will amplify moves. Follow breakouts, buy premium for protection, reduce size.'
        else:
            regime = 'transitional'
            regime_score = gex_normalized * score_scale  # Near zero
            position_sizing = 0.5  # Half size
            strategy_bias = 'neutral'
            recommendation = 'Gamma flip zone - highest uncertainty. Wait for clarity or reduce exposure.'

        # Calculate distance to gamma flip
        flip_distance = None
        flip_distance_pct = None
        if zero_gamma and current_price > 0:
            flip_distance = zero_gamma - current_price
            flip_distance_pct = (flip_distance / current_price) * 100

        # Find key GEX levels (walls)
        call_wall = None
        put_wall = None
        max_call_gex = 0
        max_put_gex = 0

        for g in gex_by_strike:
            if g['call_gex'] > max_call_gex:
                max_call_gex = g['call_gex']
                call_wall = g['strike']
            if g['put_gex'] < max_put_gex:  # Most negative = strongest put wall
                max_put_gex = g['put_gex']
                put_wall = g['strike']

        # Calculate confidence based on how far into the regime we are
        # Higher absolute regime_score = higher confidence
        confidence = min(abs(regime_score) / 100, 1.0)

        return {
            'ticker': ticker.upper(),
            'expiration': gex_data.get('expiration'),
            'current_price': current_price,
            'regime': regime,
            'regime_score': round(regime_score, 1),
            'confidence': round(confidence, 2),
            'regime_emoji': '📌' if regime == 'pinned' else '🌊' if regime == 'volatile' else '⚖️',
            'total_gex': total_gex,
            'gex_billions': round(gex_normalized, 3),
            'zero_gamma_level': zero_gamma,
            'flip_distance': round(flip_distance, 2) if flip_distance else None,
            'flip_distance_pct': round(flip_distance_pct, 2) if flip_distance_pct else None,
            'position_sizing': position_sizing,
            'position_sizing_label': f'{int(position_sizing * 100)}% size',
            'strategy_bias': strategy_bias,
            'recommendation': recommendation,
            'call_wall': call_wall,
            'put_wall': put_wall,
            'is_futures': gex_data.get('is_futures', False)
        }

    except Exception as e:
        logger.error(f"GEX regime error for {ticker}: {e}")
        return {"error": str(e), "ticker": ticker}


def get_gex_levels(ticker: str, expiration: str = None) -> Dict:
    """
    GEX Support/Resistance Wall Mapper

    Maps GEX by strike to identify dealer hedging walls:
    - Call Wall: Strike with highest call GEX (likely resistance/ceiling)
    - Put Wall: Strike with most negative put GEX (likely support/floor)
    - High GEX Zones: Strikes with large positive GEX (magnets/sticky levels)
    - Low GEX Zones: Strikes with negative GEX (acceleration zones)

    Returns:
        {
            'call_wall': float (resistance level),
            'put_wall': float (support level),
            'gamma_flip': float (where dealers flip from long to short gamma),
            'key_levels': List[Dict],  # Sorted by importance
            'magnet_zones': List[float],  # High positive GEX - sticky
            'acceleration_zones': List[float],  # Negative GEX - fast moves
        }
    """
    try:
        gex_data = calculate_gex_by_strike(ticker, expiration)
        if 'error' in gex_data:
            return gex_data

        current_price = gex_data.get('current_price', 0)
        gex_by_strike = gex_data.get('gex_by_strike', [])
        zero_gamma = gex_data.get('zero_gamma_level')

        if not gex_by_strike:
            return {"error": "No GEX data available", "ticker": ticker}

        # Find walls (strikes with highest absolute GEX)
        call_wall = None
        put_wall = None
        max_call_gex = 0
        min_put_gex = 0  # Most negative

        # Categorize zones
        magnet_zones = []      # High positive GEX - price sticks here
        acceleration_zones = []  # Negative GEX - price moves fast through here
        key_levels = []

        # Calculate total absolute GEX for significance threshold
        total_abs_gex = sum(abs(g['net_gex']) for g in gex_by_strike)
        significance_threshold = total_abs_gex * 0.05  # 5% of total = significant

        for g in gex_by_strike:
            strike = g['strike']
            net_gex = g['net_gex']
            call_gex = g['call_gex']
            put_gex = g['put_gex']

            # Find call wall (highest call GEX)
            if call_gex > max_call_gex:
                max_call_gex = call_gex
                call_wall = strike

            # Find put wall (most negative put GEX)
            if put_gex < min_put_gex:
                min_put_gex = put_gex
                put_wall = strike

            # Categorize by GEX sign
            if net_gex > significance_threshold:
                magnet_zones.append(strike)
                level_type = 'magnet'
            elif net_gex < -significance_threshold:
                acceleration_zones.append(strike)
                level_type = 'acceleration'
            else:
                level_type = 'neutral'

            # Build key levels list
            if abs(net_gex) > significance_threshold:
                distance_pct = ((strike - current_price) / current_price * 100) if current_price > 0 else 0
                key_levels.append({
                    'strike': strike,
                    'net_gex': net_gex,
                    'gex_millions': round(net_gex / 1e6, 1),
                    'type': level_type,
                    'role': 'resistance' if strike > current_price else 'support',
                    'distance_pct': round(distance_pct, 2),
                    'call_oi': g['call_oi'],
                    'put_oi': g['put_oi']
                })

        # Sort key levels by absolute GEX (most important first)
        key_levels.sort(key=lambda x: abs(x['net_gex']), reverse=True)

        # Get nearest support and resistance
        supports = [l for l in key_levels if l['strike'] < current_price and l['type'] == 'magnet']
        resistances = [l for l in key_levels if l['strike'] > current_price and l['type'] == 'magnet']

        nearest_support = max(supports, key=lambda x: x['strike']) if supports else None
        nearest_resistance = min(resistances, key=lambda x: x['strike']) if resistances else None

        return {
            'ticker': ticker.upper(),
            'expiration': gex_data.get('expiration'),
            'current_price': current_price,
            'call_wall': call_wall,
            'call_wall_gex_millions': round(max_call_gex / 1e6, 1) if max_call_gex else 0,
            'put_wall': put_wall,
            'put_wall_gex_millions': round(min_put_gex / 1e6, 1) if min_put_gex else 0,
            'gamma_flip': zero_gamma,
            'nearest_support': nearest_support['strike'] if nearest_support else put_wall,
            'nearest_resistance': nearest_resistance['strike'] if nearest_resistance else call_wall,
            'key_levels': key_levels[:10],  # Top 10 most significant
            'magnet_zones': sorted(magnet_zones),
            'acceleration_zones': sorted(acceleration_zones),
            'total_gex': gex_data.get('total_gex', 0),
            'interpretation': _interpret_gex_levels(current_price, call_wall, put_wall, zero_gamma, magnet_zones)
        }

    except Exception as e:
        logger.error(f"GEX levels error for {ticker}: {e}")
        return {"error": str(e), "ticker": ticker}


def _interpret_gex_levels(price: float, call_wall: float, put_wall: float,
                          gamma_flip: float, magnet_zones: List[float]) -> str:
    """Generate human-readable interpretation of GEX levels."""
    parts = []

    if call_wall and price > 0:
        dist = ((call_wall - price) / price) * 100
        parts.append(f"Call wall at ${call_wall:.0f} ({dist:+.1f}%) - likely resistance")

    if put_wall and price > 0:
        dist = ((put_wall - price) / price) * 100
        parts.append(f"Put wall at ${put_wall:.0f} ({dist:+.1f}%) - likely support")

    if gamma_flip and price > 0:
        dist = ((gamma_flip - price) / price) * 100
        direction = "above" if gamma_flip > price else "below"
        parts.append(f"Gamma flip at ${gamma_flip:.0f} ({direction}, {abs(dist):.1f}% away)")

    if len(magnet_zones) > 2:
        parts.append(f"{len(magnet_zones)} high-GEX magnet zones identified")

    return " | ".join(parts) if parts else "Insufficient data for interpretation"


def get_gex_analysis(ticker: str, expiration: str = None) -> Dict:
    """
    Complete GEX Analysis combining regime + levels + trading signals.

    Returns comprehensive analysis for trading decisions.
    """
    try:
        # Get both regime and levels
        regime = get_gex_regime(ticker, expiration)
        if 'error' in regime:
            return regime

        levels = get_gex_levels(ticker, expiration)
        if 'error' in levels:
            levels = {}  # Continue with regime data

        # Generate trading signals
        signals = []

        # Regime-based signals
        if regime['regime'] == 'pinned':
            signals.append({
                'signal': 'SELL_PREMIUM',
                'strength': 'strong',
                'reason': 'High positive GEX - volatility suppressed'
            })
            signals.append({
                'signal': 'FADE_BREAKOUTS',
                'strength': 'strong',
                'reason': 'Dealers will buy dips and sell rips'
            })
        elif regime['regime'] == 'volatile':
            signals.append({
                'signal': 'BUY_PREMIUM',
                'strength': 'strong',
                'reason': 'Negative GEX - realized vol likely to overshoot implied'
            })
            signals.append({
                'signal': 'FOLLOW_BREAKOUTS',
                'strength': 'strong',
                'reason': 'Dealers will amplify directional moves'
            })
            signals.append({
                'signal': 'REDUCE_SIZE',
                'strength': 'strong',
                'reason': 'Tail risk elevated in negative GEX environment'
            })
        else:  # transitional
            signals.append({
                'signal': 'WAIT',
                'strength': 'moderate',
                'reason': 'Near gamma flip - wait for regime clarity'
            })

        # Level-based signals
        current_price = regime.get('current_price', 0)
        call_wall = levels.get('call_wall')
        put_wall = levels.get('put_wall')

        if call_wall and current_price > 0:
            dist_to_call = ((call_wall - current_price) / current_price) * 100
            if 0 < dist_to_call < 2:  # Within 2% of call wall
                signals.append({
                    'signal': 'NEAR_RESISTANCE',
                    'strength': 'strong',
                    'reason': f'Price near call wall at ${call_wall:.0f} - expect resistance'
                })

        if put_wall and current_price > 0:
            dist_to_put = ((put_wall - current_price) / current_price) * 100
            if -2 < dist_to_put < 0:  # Within 2% of put wall
                signals.append({
                    'signal': 'NEAR_SUPPORT',
                    'strength': 'strong',
                    'reason': f'Price near put wall at ${put_wall:.0f} - expect support'
                })

        return {
            'ticker': ticker.upper(),
            'timestamp': datetime.now().isoformat(),
            'expiration': regime.get('expiration'),
            'current_price': current_price,

            # Regime
            'regime': regime['regime'],
            'regime_score': regime['regime_score'],
            'regime_emoji': regime['regime_emoji'],
            'gex_billions': regime['gex_billions'],

            # Position sizing
            'position_sizing': regime['position_sizing'],
            'position_sizing_label': regime['position_sizing_label'],
            'strategy_bias': regime['strategy_bias'],

            # Levels
            'call_wall': call_wall,
            'put_wall': put_wall,
            'gamma_flip': levels.get('gamma_flip'),
            'nearest_support': levels.get('nearest_support'),
            'nearest_resistance': levels.get('nearest_resistance'),
            'key_levels': levels.get('key_levels', [])[:5],  # Top 5

            # Signals
            'signals': signals,
            'recommendation': regime['recommendation'],

            # Raw data reference
            'total_gex': regime.get('total_gex'),
            'is_futures': regime.get('is_futures', False)
        }

    except Exception as e:
        logger.error(f"GEX analysis error for {ticker}: {e}")
        return {"error": str(e), "ticker": ticker}


# =============================================================================
# PUT/CALL RATIO MODELS
# =============================================================================

def get_pc_ratio_analysis(ticker: str = 'SPY') -> Dict:
    """
    Put/Call Ratio Analysis with Z-Score normalization.

    Instead of fixed thresholds, uses rolling Z-score to identify
    extreme sentiment conditions regardless of regime shifts.

    Returns:
        {
            'pc_ratio': float,
            'pc_zscore': float (normalized),
            'sentiment': str,
            'signal': str,
            ...
        }
    """
    try:
        # Get current options flow
        flow = get_options_flow(ticker)
        if 'error' in flow:
            return flow

        pc_ratio = flow.get('put_call_ratio', 0)

        # For real Z-score, we'd need historical data
        # Using heuristic thresholds calibrated for SPY
        # SPY typical P/C: 0.8-1.2, extremes: <0.6 or >1.5

        # Historical mean and std approximations for SPY
        HISTORICAL_MEAN = 0.95
        HISTORICAL_STD = 0.25

        zscore = (pc_ratio - HISTORICAL_MEAN) / HISTORICAL_STD if HISTORICAL_STD > 0 else 0

        # Interpret Z-score
        if zscore > 2:
            sentiment = 'extreme_fear'
            signal = 'contrarian_bullish'
            recommendation = 'Extreme put buying - contrarian bullish setup'
        elif zscore > 1:
            sentiment = 'elevated_fear'
            signal = 'moderately_bullish'
            recommendation = 'Elevated fear - watch for reversal signals'
        elif zscore < -2:
            sentiment = 'extreme_complacency'
            signal = 'contrarian_bearish'
            recommendation = 'Extreme call buying/complacency - contrarian bearish'
        elif zscore < -1:
            sentiment = 'elevated_complacency'
            signal = 'moderately_bearish'
            recommendation = 'Low fear - consider reducing exposure'
        else:
            sentiment = 'neutral'
            signal = 'neutral'
            recommendation = 'P/C ratio in normal range - no extreme sentiment'

        return {
            'ticker': ticker.upper(),
            'pc_ratio': round(pc_ratio, 3),
            'pc_zscore': round(zscore, 2),
            'sentiment': sentiment,
            'sentiment_emoji': '😱' if 'fear' in sentiment else '😎' if 'complacency' in sentiment else '😐',
            'signal': signal,
            'recommendation': recommendation,
            'call_volume': flow.get('total_call_volume', 0),
            'put_volume': flow.get('total_put_volume', 0),
            'call_oi': flow.get('total_call_oi', 0),
            'put_oi': flow.get('total_put_oi', 0),
            'historical_mean': HISTORICAL_MEAN,
            'historical_std': HISTORICAL_STD
        }

    except Exception as e:
        logger.error(f"P/C ratio analysis error for {ticker}: {e}")
        return {"error": str(e), "ticker": ticker}


def get_combined_regime(ticker: str, expiration: str = None) -> Dict:
    """
    Combined GEX + P/C Ratio Regime Matrix

    Creates a 2x2 regime classification:
    - Fear + Positive GEX: Best buying opportunity
    - Fear + Negative GEX: Danger zone (crash risk)
    - Complacency + Positive GEX: Quiet melt-up
    - Complacency + Negative GEX: Most dangerous

    Returns comprehensive regime classification for strategy selection.
    """
    try:
        # Get GEX regime
        gex_regime = get_gex_regime(ticker, expiration)
        if 'error' in gex_regime:
            return gex_regime

        # Get P/C analysis
        pc_analysis = get_pc_ratio_analysis(ticker)
        if 'error' in pc_analysis:
            # Continue with just GEX
            pc_analysis = {'pc_zscore': 0, 'sentiment': 'neutral'}

        # Extract key metrics
        gex_regime_type = gex_regime['regime']
        gex_score = gex_regime['regime_score']
        pc_zscore = pc_analysis.get('pc_zscore', 0)

        # Determine combined regime
        is_positive_gex = gex_regime_type == 'pinned'
        is_negative_gex = gex_regime_type == 'volatile'
        is_fear = pc_zscore > 1  # Elevated or extreme fear
        is_complacency = pc_zscore < -1  # Elevated or extreme complacency

        # 2x2 Matrix classification
        if is_fear and is_positive_gex:
            combined_regime = 'opportunity'
            regime_emoji = '🎯'
            regime_color = 'green'
            recommendation = 'BEST SETUP: Fear + dealer support. Aggressive PCS, full size ORB, TQQQ entries.'
            risk_level = 'low'
            position_multiplier = 1.25  # Can go slightly above normal
        elif is_fear and is_negative_gex:
            combined_regime = 'danger'
            regime_emoji = '⚠️'
            regime_color = 'red'
            recommendation = 'DANGER ZONE: Fear + dealer amplification = crash risk. Sit on hands or buy puts.'
            risk_level = 'extreme'
            position_multiplier = 0.0  # No new positions
        elif is_complacency and is_positive_gex:
            combined_regime = 'melt_up'
            regime_emoji = '📈'
            regime_color = 'yellow'
            recommendation = 'Quiet melt-up. Normal trading, start tightening stops.'
            risk_level = 'moderate'
            position_multiplier = 0.75
        elif is_complacency and is_negative_gex:
            combined_regime = 'high_risk'
            regime_emoji = '🔴'
            regime_color = 'orange'
            recommendation = 'MOST DANGEROUS: Complacency + no dealer cushion. Reduce exposure, hedge, no new longs.'
            risk_level = 'high'
            position_multiplier = 0.25
        else:
            # Neutral P/C, use GEX regime primarily
            combined_regime = f'neutral_{gex_regime_type}'
            regime_emoji = gex_regime['regime_emoji']
            regime_color = 'gray'
            recommendation = gex_regime['recommendation']
            risk_level = 'moderate' if gex_regime_type != 'volatile' else 'elevated'
            position_multiplier = gex_regime['position_sizing']

        # Strategy recommendations based on regime
        strategies = {
            'opportunity': ['aggressive_pcs', 'full_size_orb', 'tqqq_entry', 'buy_dips'],
            'danger': ['cash', 'buy_puts', 'no_new_longs'],
            'melt_up': ['normal_trading', 'tighten_stops', 'trim_winners'],
            'high_risk': ['reduce_exposure', 'hedge', 'no_new_longs', 'raise_cash'],
        }

        return {
            'ticker': ticker.upper(),
            'timestamp': datetime.now().isoformat(),
            'expiration': gex_regime.get('expiration'),
            'current_price': gex_regime.get('current_price'),

            # Combined regime
            'combined_regime': combined_regime,
            'regime_emoji': regime_emoji,
            'regime_color': regime_color,
            'risk_level': risk_level,

            # Position sizing
            'position_multiplier': position_multiplier,
            'position_label': f'{int(position_multiplier * 100)}% of normal size',

            # Recommended strategies
            'recommended_strategies': strategies.get(combined_regime, ['normal_trading']),
            'recommendation': recommendation,

            # Component data
            'gex_regime': gex_regime_type,
            'gex_score': gex_score,
            'gex_billions': gex_regime['gex_billions'],
            'pc_zscore': pc_zscore,
            'pc_sentiment': pc_analysis.get('sentiment', 'neutral'),
            'pc_ratio': pc_analysis.get('pc_ratio', 0),

            # Key levels from GEX
            'call_wall': gex_regime.get('call_wall'),
            'put_wall': gex_regime.get('put_wall'),
            'gamma_flip': gex_regime.get('zero_gamma_level'),

            # Detailed breakdown
            'gex_data': gex_regime,
            'pc_data': pc_analysis
        }

    except Exception as e:
        logger.error(f"Combined regime error for {ticker}: {e}")
        return {"error": str(e), "ticker": ticker}


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
