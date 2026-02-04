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

# Standard equity options contract multiplier (100 shares per contract)
CONTRACT_MULTIPLIER = 100


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
        multiplier = CONTRACT_MULTIPLIER

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
            'contract_multiplier': multiplier
        }

        logger.info(f"✅ Max pain for {ticker} ({used_expiration}): ${max_pain_price:.2f} (current: ${current_price:.2f}, {direction} by {abs(distance_pct):.1f}%)")
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

        # Calculate GEX per strike
        # GEX = Gamma × OI × Multiplier × Spot Price (in $ terms)
        # Calls: positive contribution (dealers long gamma)
        # Puts: negative contribution (dealers short gamma on puts they sold)
        multiplier = CONTRACT_MULTIPLIER

        gex_by_strike = []
        total_gex = 0

        for strike in sorted(strikes):
            call_info = call_data.get(strike, {'gamma': 0, 'oi': 0})
            put_info = put_data.get(strike, {'gamma': 0, 'oi': 0})

            # GEX in dollar terms (gamma × OI × multiplier × spot)
            call_gex = call_info['gamma'] * call_info['oi'] * multiplier * current_price
            # Puts: dealers are SHORT gamma, so it's negative
            put_gex = -put_info['gamma'] * put_info['oi'] * multiplier * current_price
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
