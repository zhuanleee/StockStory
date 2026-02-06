#!/usr/bin/env python3
"""
Options Data Aggregator

Centralized wrapper around options functions for easy API consumption.
Uses Tastytrade as primary data source with Polygon as fallback.

Data Source Priority:
1. Tastytrade - Full options chain with Greeks, IV, all expirations (120+ DTE)
2. Polygon - Fallback for real-time flow data and when Tastytrade unavailable
"""

from src.data.polygon_provider import (
    get_options_flow_sync as get_options_flow_sync_polygon,
    get_unusual_options_sync as get_unusual_options_sync_polygon,
    get_options_chain_sync as get_options_chain_sync_polygon,
    get_technical_summary_sync,
    get_options_contracts_sync,
    get_snapshot_sync,
    get_price_data_sync
)
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# =============================================================================
# TASTYTRADE INTEGRATION
# =============================================================================

def _is_tastytrade_available() -> bool:
    """Check if Tastytrade is available as data source."""
    try:
        from src.data.tastytrade_provider import is_tastytrade_available
        return is_tastytrade_available()
    except ImportError:
        return False


def _get_tastytrade_chain(ticker: str, expiration: str = None, target_dte: int = None) -> Optional[Dict]:
    """Get options chain from Tastytrade (sync wrapper - runs async in thread)."""
    try:
        from src.data.tastytrade_provider import get_options_chain_sync_tastytrade
        import asyncio
        import concurrent.futures
        # get_options_chain_sync_tastytrade is now async, run it properly
        async def _run():
            return await get_options_chain_sync_tastytrade(ticker, expiration, target_dte)
        try:
            asyncio.get_running_loop()
            # Already in event loop - run in thread
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, _run()).result(timeout=30)
        except RuntimeError:
            return asyncio.run(_run())
    except Exception as e:
        logger.warning(f"Tastytrade chain fetch failed for {ticker}: {e}")
        return None


async def _get_tastytrade_chain_async(ticker: str, expiration: str = None, target_dte: int = None) -> Optional[Dict]:
    """Get options chain from Tastytrade (async)."""
    try:
        from src.data.tastytrade_provider import get_options_chain_sync_tastytrade
        return await get_options_chain_sync_tastytrade(ticker, expiration, target_dte)
    except Exception as e:
        logger.warning(f"Tastytrade chain fetch failed for {ticker}: {e}")
        return None


def _get_tastytrade_flow(ticker: str, target_dte: int = 30) -> Optional[Dict]:
    """Get options flow from Tastytrade."""
    try:
        from src.data.tastytrade_provider import get_options_flow_sync_tastytrade
        return get_options_flow_sync_tastytrade(ticker, target_dte)
    except Exception as e:
        logger.warning(f"Tastytrade flow fetch failed for {ticker}: {e}")
        return None


def _get_tastytrade_unusual(ticker: str, target_dte: int = 30) -> Optional[List]:
    """Get unusual options from Tastytrade."""
    try:
        from src.data.tastytrade_provider import get_unusual_options_sync_tastytrade
        return get_unusual_options_sync_tastytrade(ticker, target_dte)
    except Exception as e:
        logger.warning(f"Tastytrade unusual fetch failed for {ticker}: {e}")
        return None


def _get_tastytrade_quote(ticker: str) -> Optional[Dict]:
    """Get real-time quote from Tastytrade (works for futures like /ES).

    Uses inline session creation and async execution matching the working
    debug endpoint pattern for reliability.
    """
    import os
    import asyncio

    try:
        from tastytrade import Session, DXLinkStreamer
        from tastytrade.dxfeed import Quote
        from tastytrade.instruments import Future
        from src.data.tastytrade_provider import get_futures_front_month_symbol, is_futures_ticker

        client_secret = os.environ.get('TASTYTRADE_CLIENT_SECRET')
        refresh_token = os.environ.get('TASTYTRADE_REFRESH_TOKEN')

        if not client_secret or not refresh_token:
            logger.warning("Tastytrade credentials not available")
            return None

        # Create fresh session (like debug endpoint)
        session = Session(client_secret, refresh_token)
        logger.info(f"Created fresh Tastytrade session for {ticker}")

        # For futures, get the streamer symbol
        quote_ticker = ticker
        if is_futures_ticker(ticker) and len(ticker) <= 4:  # /ES, /NQ, /CL, /GC
            front_month = get_futures_front_month_symbol(ticker)
            logger.info(f"Front month for {ticker}: {front_month}")

            try:
                futures = Future.get(session, [front_month])
                if futures and len(futures) > 0:
                    streamer_sym = getattr(futures[0], 'streamer_symbol', None)
                    if streamer_sym:
                        quote_ticker = streamer_sym
                        logger.info(f"Using streamer symbol {quote_ticker} for {ticker}")
            except Exception as e:
                logger.warning(f"Could not get futures instrument for {front_month}: {e}")
                quote_ticker = front_month

        quote_data = {}

        async def fetch_quote():
            import time
            try:
                async with DXLinkStreamer(session) as streamer:
                    await streamer.subscribe(Quote, [quote_ticker])
                    logger.info(f"Subscribed to quote for {quote_ticker}")

                    start = time.time()
                    async for quote in streamer.listen(Quote):
                        # Quote uses snake_case: bid_price, ask_price
                        # Convert to float to avoid Decimal type issues
                        bid = getattr(quote, 'bid_price', None)
                        ask = getattr(quote, 'ask_price', None)
                        bid = float(bid) if bid is not None else None
                        ask = float(ask) if ask is not None else None
                        quote_data['bid'] = bid
                        quote_data['ask'] = ask
                        quote_data['last'] = (bid + ask) / 2 if bid and ask else None
                        quote_data['symbol'] = quote_ticker
                        logger.info(f"Got quote for {quote_ticker}: bid={bid}, ask={ask}, last={quote_data['last']}")
                        break  # Got first quote, exit

                        # Timeout check (shouldn't reach here but just in case)
                        if time.time() - start > 8:
                            logger.warning(f"Quote streaming timed out for {quote_ticker}")
                            break
            except Exception as e:
                import traceback
                logger.warning(f"Error in quote streaming for {quote_ticker}: {e}")
                logger.warning(f"Traceback: {traceback.format_exc()}")

        # Run async code - try asyncio.run first, fallback to loop.run_until_complete
        try:
            asyncio.run(fetch_quote())
        except RuntimeError as e:
            logger.info(f"asyncio.run failed ({e}), trying loop.run_until_complete")
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(fetch_quote())
                loop.close()
            except Exception as e2:
                logger.warning(f"loop.run_until_complete also failed: {e2}")

        if quote_data and quote_data.get('last'):
            return quote_data
        else:
            logger.warning(f"Quote data empty or invalid for {ticker}: {quote_data}")
            return None

    except Exception as e:
        import traceback
        logger.warning(f"Tastytrade quote fetch failed for {ticker}: {e}")
        logger.warning(f"Traceback: {traceback.format_exc()}")
        return None


# =============================================================================
# UNIFIED OPTIONS DATA FUNCTIONS (Tastytrade first, Polygon fallback)
# =============================================================================

def get_options_flow_sync(ticker: str, target_dte: int = 30) -> Dict:
    """Get options flow - Tastytrade first, Polygon fallback."""
    if _is_tastytrade_available():
        result = _get_tastytrade_flow(ticker, target_dte)
        if result:
            logger.info(f"Options flow for {ticker}: using Tastytrade")
            return result

    logger.info(f"Options flow for {ticker}: using Polygon fallback")
    return get_options_flow_sync_polygon(ticker)


def get_unusual_options_sync(ticker: str, target_dte: int = 30) -> List:
    """Get unusual options - Tastytrade first, Polygon fallback."""
    if _is_tastytrade_available():
        result = _get_tastytrade_unusual(ticker, target_dte)
        if result is not None:
            logger.info(f"Unusual options for {ticker}: using Tastytrade")
            return result

    logger.info(f"Unusual options for {ticker}: using Polygon fallback")
    return get_unusual_options_sync_polygon(ticker)


def get_options_chain_sync(ticker: str, expiration: str = None, target_dte: int = None) -> Dict:
    """Get options chain - Tastytrade first, Polygon fallback."""
    if _is_tastytrade_available():
        result = _get_tastytrade_chain(ticker, expiration, target_dte)
        if result:
            logger.info(f"Options chain for {ticker}: using Tastytrade")
            return result

    logger.info(f"Options chain for {ticker}: using Polygon fallback")
    return get_options_chain_sync_polygon(ticker)


def get_options_chain_with_oi(ticker: str, expiration: str = None, target_dte: int = None) -> Dict:
    """
    Get options chain with open interest - Tastytrade first, Polygon fallback.

    Tastytrade's Summary stream provides OI data via the open_interest field.
    Falls back to Polygon if Tastytrade is unavailable.
    """
    if _is_tastytrade_available():
        result = _get_tastytrade_chain(ticker, expiration, target_dte)
        if result and result.get('total_call_oi', 0) > 0:
            logger.info(f"Options chain with OI for {ticker}: using Tastytrade (OI={result.get('total_call_oi', 0)})")
            return result

    logger.info(f"Options chain with OI for {ticker}: using Polygon fallback")
    return get_options_chain_sync_polygon(ticker)

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


def normalize_futures_ticker(ticker: str) -> str:
    """Normalize futures ticker - strip leading / if present."""
    return ticker.lstrip('/').upper()


def is_futures_ticker(ticker: str) -> bool:
    """Check if ticker is a futures contract (with or without / prefix)."""
    normalized = normalize_futures_ticker(ticker)
    return normalized in FUTURES_SPECS or ticker.startswith('/')


def get_futures_info(ticker: str) -> Dict:
    """Get futures contract info if it's a futures ticker."""
    normalized = normalize_futures_ticker(ticker)
    if normalized in FUTURES_SPECS:
        return {
            'is_futures': True,
            'ticker': normalized,
            **FUTURES_SPECS[normalized]
        }
    if ticker.startswith('/'):
        # Unknown futures - use defaults
        return {'is_futures': True, 'ticker': normalized, 'name': f'{normalized} Futures', 'multiplier': 50, 'tick_size': 0.25}
    return {'is_futures': False, 'ticker': ticker.upper(), 'multiplier': 100}  # Default for equities


def get_contract_multiplier(ticker: str) -> int:
    """Get contract multiplier for a ticker (futures or equity options)."""
    normalized = normalize_futures_ticker(ticker)
    if normalized in FUTURES_SPECS:
        return FUTURES_SPECS[normalized]['multiplier']
    if ticker.startswith('/'):
        return 50  # Default futures multiplier
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


def get_unusual_activity(ticker: str, threshold: float = 2.0, target_dte: int = 30) -> Dict:
    """
    Detect unusual options activity for a ticker.

    Args:
        ticker: Stock symbol
        threshold: Volume/OI ratio threshold (default 2.0x) - used for Polygon
        target_dte: Target DTE for analysis (default 30)

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
        result = get_unusual_options_sync(ticker, target_dte)

        # Handle list result from Tastytrade
        if isinstance(result, list):
            return {
                'unusual_activity': len(result) > 0,
                'unusual_contracts': result,
                'signals': [],
                'summary': {'count': len(result), 'source': 'tastytrade'},
                'total_unusual_contracts': len(result)
            }

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

        # Get options chain data with OI (uses Polygon - OI required for max pain)
        chain = get_options_chain_with_oi(ticker, expiration)
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

        # Get options chain with gamma and OI data (uses Polygon - OI required for GEX)
        chain = get_options_chain_with_oi(ticker, expiration)
        if not chain or 'error' in chain:
            return {"error": "Could not fetch options chain", "ticker": ticker}

        calls = chain.get('calls', [])
        puts = chain.get('puts', [])

        if not calls and not puts:
            return {"error": "No options data", "ticker": ticker}

        # Get current price
        current_price = 0
        futures_info = get_futures_info(ticker)

        # For futures, try Tastytrade quote first (most accurate)
        if futures_info.get('is_futures'):
            try:
                logger.info(f"Attempting Tastytrade quote for {ticker}")
                quote = _get_tastytrade_quote(ticker)
                logger.info(f"Tastytrade quote result for {ticker}: {quote}")
                if quote and quote.get('last') and quote.get('last') > 100:
                    current_price = quote.get('last')
                    logger.info(f"✅ Got {ticker} LIVE price from Tastytrade: ${current_price}")
                else:
                    logger.warning(f"Tastytrade quote empty or invalid for {ticker}: {quote}")
            except Exception as e:
                import traceback
                logger.warning(f"Tastytrade quote failed for {ticker}: {e}")
                logger.warning(f"Traceback: {traceback.format_exc()}")

            # Fallback: Use SPY/QQQ price as reference for index futures
            if not current_price or current_price < 1000:
                normalized = ticker.lstrip('/').upper()
                logger.info(f"Trying ETF reference price for {ticker} (normalized: {normalized})")
                if normalized in ['ES', 'MES']:
                    try:
                        spy_snapshot = get_snapshot_sync('SPY')
                        logger.info(f"SPY snapshot: {spy_snapshot}")
                        if spy_snapshot and spy_snapshot.get('price'):
                            spy_price = spy_snapshot.get('price')
                            current_price = spy_price * 10  # ES ≈ SPY * 10
                            logger.info(f"Estimated {ticker} price from SPY: ${current_price:.2f}")
                    except Exception as e:
                        logger.error(f"Error getting SPY snapshot for {ticker}: {e}")
                elif normalized in ['NQ', 'MNQ']:
                    try:
                        qqq_snapshot = get_snapshot_sync('QQQ')
                        logger.info(f"QQQ snapshot: {qqq_snapshot}")
                        if qqq_snapshot and qqq_snapshot.get('price'):
                            qqq_price = qqq_snapshot.get('price')
                            current_price = qqq_price * 40  # NQ ≈ QQQ * 40
                            logger.info(f"Estimated {ticker} price from QQQ: ${current_price:.2f}")
                    except Exception as e:
                        logger.error(f"Error getting QQQ snapshot for {ticker}: {e}")

        # Try Polygon snapshot for equities (or as fallback)
        if not current_price:
            try:
                snapshot = get_snapshot_sync(ticker)
                if snapshot:
                    current_price = snapshot.get('price') or snapshot.get('last_price') or 0
            except:
                pass

        # Try underlying_price from options data
        if not current_price and calls:
            current_price = calls[len(calls)//2].get('underlying_price') or 0

        # For futures without live quote, estimate from options chain
        # Method 1: Find strike where call/put OI are most balanced (ATM indicator)
        # Method 2: Fall back to strike with highest gamma (ATM has highest gamma)
        if not current_price and (calls or puts):
            call_oi_by_strike = {}
            put_oi_by_strike = {}
            gamma_by_strike = {}

            for c in calls:
                s = c.get('strike', 0)
                if s > 0:
                    call_oi_by_strike[s] = c.get('open_interest') or 0
                    gamma_by_strike[s] = gamma_by_strike.get(s, 0) + (c.get('gamma') or 0)
            for p in puts:
                s = p.get('strike', 0)
                if s > 0:
                    put_oi_by_strike[s] = p.get('open_interest') or 0
                    gamma_by_strike[s] = gamma_by_strike.get(s, 0) + (p.get('gamma') or 0)

            # Find strike with most balanced call/put OI ratio (closest to 1.0)
            best_strike = None
            best_balance = float('inf')
            for strike in set(call_oi_by_strike.keys()) & set(put_oi_by_strike.keys()):
                call_oi = call_oi_by_strike.get(strike, 0)
                put_oi = put_oi_by_strike.get(strike, 0)
                if call_oi > 10 and put_oi > 10:  # Need meaningful OI on both sides
                    ratio = call_oi / put_oi if put_oi > 0 else float('inf')
                    balance = abs(1.0 - ratio)  # How close to 1:1 ratio
                    if balance < best_balance:
                        best_balance = balance
                        best_strike = strike

            if best_strike and best_balance < 2.0:  # Reasonable balance found
                current_price = best_strike
                logger.info(f"Estimated {ticker} price from balanced OI strike: ${current_price}")
            elif gamma_by_strike:
                # Fall back to highest gamma strike (ATM)
                max_gamma_strike = max(gamma_by_strike.keys(), key=lambda k: gamma_by_strike[k])
                current_price = max_gamma_strike
                logger.info(f"Estimated {ticker} price from max gamma strike: ${current_price}")

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

        # Find zero-gamma level (gamma flip): the last negative-to-positive GEX
        # transition below current price, ignoring empty (zero-OI) strikes.
        zero_gamma = None
        active_strikes = [g for g in gex_by_strike if g['call_oi'] > 0 or g['put_oi'] > 0]
        lower_bound = current_price * 0.90 if current_price > 0 else 0
        for i in range(1, len(active_strikes)):
            strike = active_strikes[i]['strike']
            if strike < lower_bound or strike > current_price:
                continue
            if active_strikes[i-1]['net_gex'] < 0 and active_strikes[i]['net_gex'] > 0:
                zero_gamma = strike  # keep searching — want the LAST transition below price

        # Filter to +/- 15% of current price
        if current_price > 0:
            min_s = current_price * 0.85
            max_s = current_price * 1.15
            gex_by_strike = [g for g in gex_by_strike if min_s <= g['strike'] <= max_s]

        # Get expiration used
        used_exp = expiration
        if not used_exp and calls:
            used_exp = calls[0].get('expiration')

        # Calculate total call/put OI
        total_call_oi = sum(call_data.get(s, {}).get('oi', 0) for s in strikes)
        total_put_oi = sum(put_data.get(s, {}).get('oi', 0) for s in strikes)

        # Calculate DTE
        days_to_expiry = 0
        if used_exp:
            try:
                from datetime import datetime
                exp_date = datetime.strptime(used_exp, '%Y-%m-%d').date()
                days_to_expiry = (exp_date - datetime.now().date()).days
            except:
                pass

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
            'contract_multiplier': multiplier,
            'total_call_oi': total_call_oi,
            'total_put_oi': total_put_oi,
            'days_to_expiry': days_to_expiry
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


# =============================================================================
# RATIO SPREAD CONDITION MODELS
# =============================================================================

def calculate_realized_volatility(ticker: str, days: int = 20) -> Dict:
    """
    Calculate historical realized volatility using close-to-close returns.

    Args:
        ticker: Stock symbol (equities only - futures not supported via Polygon)
        days: Lookback period (default 20 trading days)

    Returns:
        {
            'rv': float (annualized realized vol as decimal, e.g., 0.25 = 25%),
            'rv_5d': float (5-day RV for regime detection),
            'rv_20d': float (20-day RV),
            'rv_direction': str ('rising' or 'falling'),
            ...
        }
    """
    try:
        import math
        import pandas as pd

        # Check if ticker is a futures symbol (starts with '/')
        # Polygon doesn't support futures symbols, so we need to handle this case
        if ticker.startswith('/'):
            # Futures tickers like /ES, /NQ, /CL, /GC are not supported by Polygon
            # The Tastytrade SDK provides real-time streaming data but not historical
            # OHLCV bars needed for realized volatility calculation
            logger.warning(f"Futures RV calculation not supported for {ticker} - Polygon doesn't support futures")
            return {
                "error": "Futures RV calculation not supported. Polygon doesn't provide historical data for futures symbols like /ES, /NQ, /CL, /GC. Consider using the equity proxy (ES=F, NQ=F) or a futures data provider.",
                "ticker": ticker,
                "suggestion": "For futures volatility analysis, use IV from options chain instead of historical RV."
            }

        # Get historical price data (need extra days for return calculation)
        price_data = get_price_data_sync(ticker, days=days + 10)

        # Handle DataFrame or list return type
        if price_data is None:
            return {"error": "No price data available", "ticker": ticker}

        if isinstance(price_data, pd.DataFrame):
            if price_data.empty or len(price_data) < days:
                return {"error": "Insufficient price data", "ticker": ticker}
            # Extract close prices from DataFrame (Polygon uses 'Close' with capital C)
            if 'Close' in price_data.columns:
                closes = price_data['Close'].tolist()
            elif 'close' in price_data.columns:
                closes = price_data['close'].tolist()
            elif 'c' in price_data.columns:
                closes = price_data['c'].tolist()
            else:
                return {"error": f"No close price column found. Columns: {list(price_data.columns)}", "ticker": ticker}
        elif isinstance(price_data, list):
            if len(price_data) < days:
                return {"error": "Insufficient price data", "ticker": ticker}
            closes = [bar.get('close') or bar.get('c') for bar in price_data if bar.get('close') or bar.get('c')]
        else:
            return {"error": "Unexpected price data format", "ticker": ticker}

        # Ensure closes are in chronological order (oldest to newest)
        # Most APIs return newest first, so we may need to reverse
        if len(closes) < days + 1:
            return {"error": "Insufficient price data", "ticker": ticker}

        # Calculate log returns
        returns = []
        for i in range(1, len(closes)):
            if closes[i-1] > 0 and closes[i] > 0:
                returns.append(math.log(closes[i] / closes[i-1]))

        if len(returns) < 5:
            return {"error": "Insufficient returns data", "ticker": ticker}

        # Calculate RV for different periods
        def calc_rv(ret_list, period):
            if len(ret_list) < period:
                return None
            subset = ret_list[-period:]
            variance = sum(r**2 for r in subset) / len(subset)
            # Annualize: sqrt(252) for daily data
            return math.sqrt(variance * 252)

        rv_5d = calc_rv(returns, 5)
        rv_10d = calc_rv(returns, 10)
        rv_20d = calc_rv(returns, 20)
        rv_30d = calc_rv(returns, min(30, len(returns)))

        # Determine RV direction (regime)
        if rv_5d and rv_20d:
            if rv_5d > rv_20d * 1.1:
                rv_direction = 'rising'
                rv_regime = 'expanding'
            elif rv_5d < rv_20d * 0.9:
                rv_direction = 'falling'
                rv_regime = 'compressing'
            else:
                rv_direction = 'stable'
                rv_regime = 'stable'
        else:
            rv_direction = 'unknown'
            rv_regime = 'unknown'

        return {
            'ticker': ticker.upper(),
            'rv_5d': round(rv_5d, 4) if rv_5d else None,
            'rv_10d': round(rv_10d, 4) if rv_10d else None,
            'rv_20d': round(rv_20d, 4) if rv_20d else None,
            'rv_30d': round(rv_30d, 4) if rv_30d else None,
            'rv_direction': rv_direction,
            'rv_regime': rv_regime,
            'current_price': closes[-1] if closes else None
        }

    except Exception as e:
        logger.error(f"RV calculation error for {ticker}: {e}")
        return {"error": str(e), "ticker": ticker}


async def get_vrp_analysis(ticker: str, expiration: str = None) -> Dict:
    """
    Variance Risk Premium (VRP) Analysis.

    VRP = IV - RV
    Positive VRP = options overpriced = edge for sellers
    Negative VRP = options underpriced = edge for buyers

    For ratio put spreads (net short vol), want HIGH positive VRP.

    Supports futures tickers (/ES, /NQ, /CL, /GC) via Tastytrade.

    Returns:
        {
            'vrp': float (IV - RV),
            'vrp_percentile': float (how extreme is current VRP),
            'iv_30d': float,
            'rv_20d': float,
            'signal': str,
            'recommendation': str
        }
    """
    try:
        # Futures-to-ETF mapping for RV calculation (Polygon doesn't support futures)
        FUTURES_TO_ETF_PROXY = {
            'ES': 'SPY',   # E-mini S&P 500 -> SPY
            'MES': 'SPY',  # Micro E-mini S&P -> SPY
            'NQ': 'QQQ',   # E-mini Nasdaq -> QQQ
            'MNQ': 'QQQ',  # Micro E-mini Nasdaq -> QQQ
            'RTY': 'IWM',  # E-mini Russell 2000 -> IWM
            'YM': 'DIA',   # E-mini Dow -> DIA
            'CL': 'USO',   # Crude Oil -> USO (oil ETF)
            'GC': 'GLD',   # Gold -> GLD
            'SI': 'SLV',   # Silver -> SLV
            'ZB': 'TLT',   # 30-Year Treasury -> TLT
            'ZN': 'IEF',   # 10-Year Treasury -> IEF
        }

        # Check if this is a futures ticker
        is_futures = is_futures_ticker(ticker)
        normalized_ticker = normalize_futures_ticker(ticker)

        if is_futures:
            logger.info(f"VRP analysis for futures ticker {ticker} - using Tastytrade path")

            # For futures, use ETF proxy for realized volatility calculation
            rv_proxy = FUTURES_TO_ETF_PROXY.get(normalized_ticker)
            if not rv_proxy:
                return {"error": f"No RV proxy available for futures ticker {ticker}. Supported: {list(FUTURES_TO_ETF_PROXY.keys())}", "ticker": ticker}

            logger.info(f"Using {rv_proxy} as RV proxy for {ticker}")
            rv_data = calculate_realized_volatility(rv_proxy, days=30)
            if 'error' in rv_data:
                return {"error": f"Could not calculate RV using proxy {rv_proxy}: {rv_data.get('error')}", "ticker": ticker}

            rv_20d = rv_data.get('rv_20d', 0)

            # For futures, use Tastytrade for options chain (IV data)
            chain = await _get_tastytrade_chain_async(ticker, expiration)
            if not chain or not chain.get('calls'):
                return {"error": f"Could not fetch futures options chain from Tastytrade for {ticker}", "ticker": ticker}

            calls = chain.get('calls', [])
            puts = chain.get('puts', [])

            # Get current price from Tastytrade quote
            current_price = 0
            quote = _get_tastytrade_quote(ticker)
            if quote and quote.get('last'):
                current_price = quote.get('last')
                logger.info(f"Got {ticker} price from Tastytrade: ${current_price}")

            # Fallback: use underlying_price from chain or estimate from ATM strike
            if not current_price:
                if calls:
                    current_price = calls[len(calls)//2].get('underlying_price') or 0
                if not current_price and calls:
                    # Estimate from strike with highest gamma (ATM proxy)
                    atm_candidates = sorted(calls, key=lambda c: abs(c.get('gamma') or 0), reverse=True)
                    if atm_candidates:
                        current_price = atm_candidates[0].get('strike', 0)
                        logger.info(f"Estimated {ticker} price from ATM strike: ${current_price}")

            if not current_price:
                return {"error": f"Could not determine current price for {ticker}", "ticker": ticker}

        else:
            # Standard equity path
            # Get realized volatility
            rv_data = calculate_realized_volatility(ticker, days=30)
            if 'error' in rv_data:
                return rv_data

            rv_20d = rv_data.get('rv_20d', 0)

            # Get implied volatility from options chain
            chain = get_options_chain_sync(ticker, expiration)
            if not chain or 'error' in chain:
                return {"error": "Could not fetch options chain", "ticker": ticker}

            calls = chain.get('calls', [])
            puts = chain.get('puts', [])

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

        # Find ATM options and extract IV
        atm_iv_calls = []
        atm_iv_puts = []

        for c in calls:
            strike = c.get('strike', 0)
            iv = c.get('implied_volatility') or c.get('iv')
            if iv and current_price > 0:
                moneyness = abs(strike - current_price) / current_price
                if moneyness < 0.05:  # Within 5% of ATM
                    atm_iv_calls.append(iv)

        for p in puts:
            strike = p.get('strike', 0)
            iv = p.get('implied_volatility') or p.get('iv')
            if iv and current_price > 0:
                moneyness = abs(strike - current_price) / current_price
                if moneyness < 0.05:
                    atm_iv_puts.append(iv)

        # Average ATM IV
        all_atm_iv = atm_iv_calls + atm_iv_puts
        if not all_atm_iv:
            # Fallback: use all available IVs
            all_atm_iv = [c.get('implied_volatility') or c.get('iv') for c in calls + puts
                         if c.get('implied_volatility') or c.get('iv')]

        if not all_atm_iv:
            return {"error": "No IV data available", "ticker": ticker}

        iv_30d = sum(all_atm_iv) / len(all_atm_iv)

        # Calculate VRP
        vrp = iv_30d - rv_20d if rv_20d else 0
        vrp_pct = (vrp / rv_20d * 100) if rv_20d > 0 else 0

        # Historical VRP context (heuristic thresholds)
        # Typical VRP for SPY: 2-5% positive
        # These thresholds are calibrated for equity indices
        if vrp > 0.08:  # 8%+ spread
            vrp_signal = 'very_high'
            vrp_score = 100
            recommendation = 'Excellent conditions for ratio spreads - options significantly overpriced'
        elif vrp > 0.04:  # 4-8% spread
            vrp_signal = 'high'
            vrp_score = 75
            recommendation = 'Good conditions for ratio spreads - options overpriced'
        elif vrp > 0.02:  # 2-4% spread
            vrp_signal = 'moderate'
            vrp_score = 50
            recommendation = 'Acceptable for ratio spreads - slight premium edge'
        elif vrp > 0:  # 0-2% spread
            vrp_signal = 'low'
            vrp_score = 25
            recommendation = 'Marginal edge - consider smaller size'
        else:  # Negative VRP
            vrp_signal = 'negative'
            vrp_score = 0
            recommendation = 'AVOID ratio spreads - options underpriced, realized vol exceeds implied'

        result = {
            'ticker': ticker.upper(),
            'iv_30d': round(iv_30d, 4),
            'iv_30d_pct': round(iv_30d * 100, 1),
            'rv_20d': round(rv_20d, 4) if rv_20d else None,
            'rv_20d_pct': round(rv_20d * 100, 1) if rv_20d else None,
            'vrp': round(vrp, 4),
            'vrp_pct': round(vrp_pct, 1),
            'vrp_signal': vrp_signal,
            'vrp_score': vrp_score,
            'recommendation': recommendation,
            'rv_direction': rv_data.get('rv_direction'),
            'rv_regime': rv_data.get('rv_regime'),
            'current_price': current_price,
            'is_futures': is_futures
        }

        # Add futures-specific info
        if is_futures:
            result['rv_proxy'] = FUTURES_TO_ETF_PROXY.get(normalized_ticker)
            result['data_source'] = 'tastytrade'

        return result

    except Exception as e:
        logger.error(f"VRP analysis error for {ticker}: {e}")
        return {"error": str(e), "ticker": ticker}


def get_skew_analysis(ticker: str, expiration: str = None) -> Dict:
    """
    Put Skew Analysis for ratio spread entry timing.

    Skew = OTM Put IV / ATM IV (or 25-delta put IV - ATM IV)

    For ratio put spreads:
    - Steep skew = OTM puts are rich = better credit received = good entry
    - Flat skew = OTM puts are cheap = less credit = skip

    Returns:
        {
            'skew': float,
            'skew_percentile': float,
            'atm_iv': float,
            'otm_put_iv': float (25-delta equivalent),
            'signal': str,
            ...
        }
    """
    try:
        chain = get_options_chain_sync(ticker, expiration)
        if not chain or 'error' in chain:
            return {"error": "Could not fetch options chain", "ticker": ticker}

        puts = chain.get('puts', [])
        calls = chain.get('calls', [])

        if not puts:
            return {"error": "No put options data", "ticker": ticker}

        # Get current price
        current_price = 0
        try:
            snapshot = get_snapshot_sync(ticker)
            if snapshot:
                current_price = snapshot.get('price') or snapshot.get('last_price') or 0
        except:
            pass

        if not current_price and puts:
            current_price = puts[len(puts)//2].get('underlying_price') or 0

        if current_price <= 0:
            return {"error": "Could not determine current price", "ticker": ticker}

        # Categorize puts by moneyness
        # For 25-delta puts, typical moneyness is ~3-6% OTM (not 5-12%)
        # For 10-delta puts, typical moneyness is ~6-10% OTM
        atm_puts = []  # Within 1.5% of ATM
        otm_puts_25d = []  # 2-5% OTM (approximate 25-delta)
        otm_puts_10d = []  # 5-8% OTM (approximate 10-delta)

        for p in puts:
            strike = p.get('strike', 0)
            iv = p.get('implied_volatility') or p.get('iv')
            delta = p.get('delta', 0)

            if not iv or not strike:
                continue

            # Filter out obviously bad IV data (>100% IV is suspicious for near-ATM)
            if iv > 1.0:  # IV over 100%
                continue

            moneyness = (current_price - strike) / current_price  # Positive = OTM for puts

            if abs(moneyness) < 0.015:  # ATM (within 1.5%)
                atm_puts.append({'strike': strike, 'iv': iv, 'delta': delta})
            elif 0.02 <= moneyness <= 0.05:  # ~25 delta region (2-5% OTM)
                otm_puts_25d.append({'strike': strike, 'iv': iv, 'delta': delta, 'moneyness': moneyness})
            elif 0.05 < moneyness <= 0.08:  # ~10 delta region (5-8% OTM)
                otm_puts_10d.append({'strike': strike, 'iv': iv, 'delta': delta, 'moneyness': moneyness})

        # Also check ATM calls for better ATM IV estimate
        for c in calls:
            strike = c.get('strike', 0)
            iv = c.get('implied_volatility') or c.get('iv')
            if iv and strike:
                moneyness = abs(strike - current_price) / current_price
                if moneyness < 0.02:
                    atm_puts.append({'strike': strike, 'iv': iv, 'delta': c.get('delta', 0)})

        if not atm_puts:
            return {"error": "No ATM options found", "ticker": ticker}

        # Calculate average IVs
        atm_iv = sum(p['iv'] for p in atm_puts) / len(atm_puts)

        otm_25d_iv = None
        if otm_puts_25d:
            otm_25d_iv = sum(p['iv'] for p in otm_puts_25d) / len(otm_puts_25d)

        otm_10d_iv = None
        if otm_puts_10d:
            otm_10d_iv = sum(p['iv'] for p in otm_puts_10d) / len(otm_puts_10d)

        # Calculate skew metrics
        # Primary: 25-delta skew
        if otm_25d_iv and atm_iv > 0:
            skew_25d = otm_25d_iv - atm_iv  # Absolute difference
            skew_25d_ratio = otm_25d_iv / atm_iv  # Ratio
        else:
            skew_25d = None
            skew_25d_ratio = None

        # Secondary: 10-delta skew (wing)
        if otm_10d_iv and atm_iv > 0:
            skew_10d = otm_10d_iv - atm_iv
            skew_10d_ratio = otm_10d_iv / atm_iv
        else:
            skew_10d = None
            skew_10d_ratio = None

        # Score the skew (for ratio spreads, higher is better)
        # Typical equity skew: 25d puts are 2-8% higher IV than ATM
        skew_score = 0
        skew_signal = 'flat'

        if skew_25d_ratio:
            if skew_25d_ratio > 1.15:  # 15%+ skew
                skew_signal = 'very_steep'
                skew_score = 100
                recommendation = 'Excellent skew - OTM puts richly priced for ratio spreads'
            elif skew_25d_ratio > 1.08:  # 8-15% skew
                skew_signal = 'steep'
                skew_score = 75
                recommendation = 'Good skew - favorable for ratio spread entry'
            elif skew_25d_ratio > 1.03:  # 3-8% skew
                skew_signal = 'moderate'
                skew_score = 50
                recommendation = 'Normal skew - acceptable for ratio spreads'
            elif skew_25d_ratio > 1.0:  # 0-3% skew
                skew_signal = 'flat'
                skew_score = 25
                recommendation = 'Flat skew - reduced edge, consider smaller size'
            else:  # Inverted skew
                skew_signal = 'inverted'
                skew_score = 0
                recommendation = 'AVOID - skew inverted, OTM puts are cheap'
        else:
            recommendation = 'Insufficient data for skew analysis'

        return {
            'ticker': ticker.upper(),
            'current_price': current_price,
            'atm_iv': round(atm_iv, 4),
            'atm_iv_pct': round(atm_iv * 100, 1),
            'otm_25d_iv': round(otm_25d_iv, 4) if otm_25d_iv else None,
            'otm_25d_iv_pct': round(otm_25d_iv * 100, 1) if otm_25d_iv else None,
            'otm_10d_iv': round(otm_10d_iv, 4) if otm_10d_iv else None,
            'skew_25d': round(skew_25d, 4) if skew_25d else None,
            'skew_25d_pct': round(skew_25d * 100, 1) if skew_25d else None,
            'skew_25d_ratio': round(skew_25d_ratio, 3) if skew_25d_ratio else None,
            'skew_10d_ratio': round(skew_10d_ratio, 3) if skew_10d_ratio else None,
            'skew_signal': skew_signal,
            'skew_score': skew_score,
            'recommendation': recommendation
        }

    except Exception as e:
        logger.error(f"Skew analysis error for {ticker}: {e}")
        return {"error": str(e), "ticker": ticker}


def get_expected_move(ticker: str, expiration: str = None) -> Dict:
    """
    Calculate Expected Move from ATM straddle price.

    Expected Move = ATM Straddle Price × 0.85
    (0.85 factor accounts for typical straddle overpricing)

    For ratio spreads: ensure breakeven is beyond 1.5x expected move.

    Returns:
        {
            'expected_move': float (dollar amount),
            'expected_move_pct': float,
            'straddle_price': float,
            'atm_strike': float,
            'dte': int,
            ...
        }
    """
    try:
        # If no expiration provided, find one with reasonable DTE (7-14 days ideal)
        if not expiration:
            expirations = get_options_expirations(ticker)
            if expirations and expirations.get('expirations'):
                today = datetime.now()
                for exp in expirations['expirations']:
                    try:
                        exp_dt = datetime.strptime(exp, '%Y-%m-%d')
                        dte = (exp_dt - today).days
                        if 5 <= dte <= 14:  # Prefer weekly options
                            expiration = exp
                            break
                    except:
                        continue
                # If no 5-14 DTE, use first with positive DTE
                if not expiration:
                    for exp in expirations['expirations']:
                        try:
                            exp_dt = datetime.strptime(exp, '%Y-%m-%d')
                            dte = (exp_dt - today).days
                            if dte > 0:
                                expiration = exp
                                break
                        except:
                            continue

        chain = get_options_chain_sync(ticker, expiration)
        if not chain or 'error' in chain:
            return {"error": "Could not fetch options chain", "ticker": ticker}

        calls = chain.get('calls', [])
        puts = chain.get('puts', [])

        if not calls or not puts:
            return {"error": "Incomplete options chain", "ticker": ticker}

        # Get current price
        current_price = 0
        try:
            snapshot = get_snapshot_sync(ticker)
            if snapshot:
                current_price = snapshot.get('price') or snapshot.get('last_price') or 0
        except:
            pass

        if not current_price:
            current_price = calls[len(calls)//2].get('underlying_price') or 0

        if current_price <= 0:
            return {"error": "Could not determine current price", "ticker": ticker}

        # Find ATM strike
        strikes = set(c.get('strike') for c in calls if c.get('strike'))
        strikes.update(p.get('strike') for p in puts if p.get('strike'))

        atm_strike = min(strikes, key=lambda x: abs(x - current_price))

        # Get ATM call and put prices
        atm_call = None
        atm_put = None

        for c in calls:
            if c.get('strike') == atm_strike:
                atm_call = c
                break

        for p in puts:
            if p.get('strike') == atm_strike:
                atm_put = p
                break

        if not atm_call or not atm_put:
            return {"error": "Could not find ATM options", "ticker": ticker}

        # Use mid price for straddle
        call_mid = ((atm_call.get('bid') or 0) + (atm_call.get('ask') or 0)) / 2
        put_mid = ((atm_put.get('bid') or 0) + (atm_put.get('ask') or 0)) / 2

        # Fallback to last price if no bid/ask
        if call_mid == 0:
            call_mid = atm_call.get('last_price') or atm_call.get('close') or 0
        if put_mid == 0:
            put_mid = atm_put.get('last_price') or atm_put.get('close') or 0

        straddle_price = call_mid + put_mid

        if straddle_price <= 0:
            return {"error": "Could not calculate straddle price", "ticker": ticker}

        # Expected move calculation
        expected_move = straddle_price * 0.85
        expected_move_pct = (expected_move / current_price) * 100

        # Calculate key levels
        upper_expected = current_price + expected_move
        lower_expected = current_price - expected_move

        # 1.5x and 2x expected move (for ratio spread breakeven planning)
        lower_1_5x = current_price - (expected_move * 1.5)
        lower_2x = current_price - (expected_move * 2)

        # Get DTE
        dte = None
        exp_date = atm_call.get('expiration') or expiration
        if exp_date:
            try:
                exp_dt = datetime.strptime(exp_date, '%Y-%m-%d')
                dte = (exp_dt - datetime.now()).days
            except:
                pass

        # Calculate implied volatility from straddle
        # Straddle ≈ 0.8 × S × σ × √(T/365) for ATM
        # σ ≈ Straddle / (0.8 × S × √(T/365))
        implied_vol_from_straddle = None
        if dte and dte > 0:
            import math
            implied_vol_from_straddle = straddle_price / (0.8 * current_price * math.sqrt(dte / 365))

        return {
            'ticker': ticker.upper(),
            'current_price': round(current_price, 2),
            'atm_strike': atm_strike,
            'straddle_price': round(straddle_price, 2),
            'expected_move': round(expected_move, 2),
            'expected_move_pct': round(expected_move_pct, 2),
            'upper_expected': round(upper_expected, 2),
            'lower_expected': round(lower_expected, 2),
            'lower_1_5x_em': round(lower_1_5x, 2),
            'lower_2x_em': round(lower_2x, 2),
            'dte': dte,
            'expiration': exp_date,
            'implied_vol_straddle': round(implied_vol_from_straddle, 4) if implied_vol_from_straddle else None,
            'call_price': round(call_mid, 2),
            'put_price': round(put_mid, 2)
        }

    except Exception as e:
        logger.error(f"Expected move error for {ticker}: {e}")
        return {"error": str(e), "ticker": ticker}


def get_iv_term_structure(ticker: str) -> Dict:
    """
    IV Term Structure Analysis.

    Compares IV across different expirations to detect:
    - Contango (normal): near-term IV < far-term IV
    - Backwardation (stress): near-term IV > far-term IV

    For ratio spreads (short vol), backwardation is GOOD:
    - IV is spiked from near-term event
    - Likely to mean-revert lower = your short vol profits

    Returns:
        {
            'term_structure': str ('contango', 'backwardation', 'flat'),
            'slope': float,
            'front_iv': float,
            'back_iv': float,
            ...
        }
    """
    try:
        # Get available expirations
        expirations = get_options_expirations(ticker)
        if not expirations or 'error' in expirations:
            return {"error": "Could not fetch expirations", "ticker": ticker}

        exp_list = expirations.get('expirations', [])
        if len(exp_list) < 2:
            return {"error": "Need at least 2 expirations", "ticker": ticker}

        # Get current price
        current_price = 0
        try:
            snapshot = get_snapshot_sync(ticker)
            if snapshot:
                current_price = snapshot.get('price') or snapshot.get('last_price') or 0
        except:
            pass

        # Categorize expirations by DTE
        today = datetime.now()
        exp_data = []

        for exp in exp_list[:8]:  # Check up to 8 expirations
            try:
                exp_dt = datetime.strptime(exp, '%Y-%m-%d')
                dte = (exp_dt - today).days
                if dte > 0:
                    exp_data.append({'expiration': exp, 'dte': dte})
            except:
                continue

        if len(exp_data) < 2:
            return {"error": "Insufficient valid expirations", "ticker": ticker}

        # Sort by DTE
        exp_data.sort(key=lambda x: x['dte'])

        # Get ATM IV for front and back months
        def get_atm_iv(expiration):
            chain = get_options_chain_sync(ticker, expiration)
            if not chain:
                return None

            calls = chain.get('calls', [])
            puts = chain.get('puts', [])

            atm_ivs = []
            for opt in calls + puts:
                strike = opt.get('strike', 0)
                iv = opt.get('implied_volatility') or opt.get('iv')
                if iv and current_price > 0:
                    # Filter out unrealistic IVs (must be between 5% and 100%)
                    if iv < 0.05 or iv > 1.0:
                        continue
                    moneyness = abs(strike - current_price) / current_price
                    if moneyness < 0.02:  # Within 2% of ATM
                        atm_ivs.append(iv)

            return sum(atm_ivs) / len(atm_ivs) if atm_ivs else None

        # Get front month (~7-14 DTE) and back month (~30-45 DTE)
        # Skip 0-3 DTE options as they have distorted IV
        front_exp = None
        for exp in exp_data:
            if 5 <= exp['dte'] <= 14:  # ~1-2 weeks out
                front_exp = exp
                break

        # If no 7-14 DTE, use first expiration > 3 DTE
        if not front_exp:
            for exp in exp_data:
                if exp['dte'] > 3:
                    front_exp = exp
                    break

        if not front_exp:
            front_exp = exp_data[0]  # Fallback to nearest

        # Find back month (~30-45 DTE)
        back_exp = None
        for exp in exp_data:
            if 25 <= exp['dte'] <= 45:
                back_exp = exp
                break

        # If no 30-45 DTE, find anything >= 20 DTE
        if not back_exp:
            for exp in exp_data:
                if exp['dte'] >= 20:
                    back_exp = exp
                    break

        if not back_exp:
            back_exp = exp_data[-1]  # Use furthest available

        # Ensure front and back are different and back has greater DTE than front
        if front_exp['expiration'] == back_exp['expiration'] or back_exp['dte'] <= front_exp['dte']:
            if len(exp_data) > 1:
                # Find expiration with higher DTE than front
                for exp in exp_data:
                    if exp['dte'] > front_exp['dte']:
                        back_exp = exp
                        break
                # If no higher DTE found, search in reverse for the furthest expiration
                if back_exp['dte'] <= front_exp['dte']:
                    for exp in reversed(exp_data):
                        if exp['expiration'] != front_exp['expiration'] and exp['dte'] > front_exp['dte']:
                            back_exp = exp
                            break

        # If still same or invalid (back DTE <= front DTE), return error
        if front_exp['expiration'] == back_exp['expiration'] or back_exp['dte'] <= front_exp['dte']:
            return {
                "error": "Insufficient expiration data for term structure (need different front/back months with back > front DTE)",
                "ticker": ticker,
                "front_dte": front_exp['dte'],
                "available_expirations": [(e['expiration'], e['dte']) for e in exp_data]
            }

        front_iv = get_atm_iv(front_exp['expiration'])
        back_iv = get_atm_iv(back_exp['expiration'])

        if not front_iv or not back_iv:
            return {"error": "Could not calculate term structure IVs", "ticker": ticker}

        # Calculate slope
        # Positive slope = contango (normal)
        # Negative slope = backwardation (inverted)
        slope = (back_iv - front_iv) / back_iv if back_iv > 0 else 0
        slope_pct = slope * 100

        # Determine structure
        if slope > 0.05:  # Back IV >5% higher than front
            structure = 'contango'
            structure_signal = 'normal'
            score = 25  # Less favorable for short vol
            recommendation = 'Normal term structure - IV already low/calm, less room for contraction'
        elif slope < -0.05:  # Front IV >5% higher than back
            structure = 'backwardation'
            structure_signal = 'inverted'
            score = 100  # Favorable for short vol
            recommendation = 'Backwardated! Near-term IV elevated - expect mean reversion, good for ratio spreads'
        else:
            structure = 'flat'
            structure_signal = 'neutral'
            score = 50
            recommendation = 'Flat term structure - neutral signal'

        return {
            'ticker': ticker.upper(),
            'current_price': current_price,
            'term_structure': structure,
            'structure_signal': structure_signal,
            'slope': round(slope, 4),
            'slope_pct': round(slope_pct, 1),
            'structure_score': score,
            'front_expiration': front_exp['expiration'],
            'front_dte': front_exp['dte'],
            'front_iv': round(front_iv, 4),
            'front_iv_pct': round(front_iv * 100, 1),
            'back_expiration': back_exp['expiration'],
            'back_dte': back_exp['dte'],
            'back_iv': round(back_iv, 4),
            'back_iv_pct': round(back_iv * 100, 1),
            'recommendation': recommendation
        }

    except Exception as e:
        logger.error(f"Term structure error for {ticker}: {e}")
        return {"error": str(e), "ticker": ticker}


async def get_ratio_spread_score(ticker: str, expiration: str = None) -> Dict:
    """
    Combined Ratio Spread Scoring System.

    Aggregates all condition models into a single score (0-6):
    - VRP (IV vs RV): +1 if positive and above median
    - Skew: +1 if steep (OTM puts rich)
    - Term Structure: +1 if backwardated
    - GEX Regime: +1 if positive (dealers suppress moves)
    - RV Direction: +1 if falling (vol compressing)
    - Expected Move Buffer: +1 if breakeven > 1.5x EM

    Score interpretation:
    - 5-6: High conviction, full size
    - 3-4: Normal conditions, standard size
    - 1-2: Marginal, reduced size or skip
    - 0: Do not enter

    Returns complete analysis with individual scores and combined recommendation.
    """
    try:
        scores = {}
        factors = []
        total_score = 0

        # 1. VRP Analysis
        vrp = await get_vrp_analysis(ticker, expiration)
        if 'error' not in vrp:
            vrp_pass = vrp.get('vrp', 0) > 0.02  # At least 2% VRP
            scores['vrp'] = {
                'value': vrp.get('vrp_pct'),
                'pass': vrp_pass,
                'score': 1 if vrp_pass else 0,
                'label': f"VRP {vrp.get('vrp_pct', 0):.1f}%",
                'signal': vrp.get('vrp_signal')
            }
            if vrp_pass:
                total_score += 1
                factors.append('VRP positive')
        else:
            scores['vrp'] = {'error': vrp.get('error'), 'score': 0}

        # 2. Skew Analysis
        skew = get_skew_analysis(ticker, expiration)
        if 'error' not in skew:
            skew_pass = (skew.get('skew_25d_ratio') or 0) > 1.05  # At least 5% skew
            scores['skew'] = {
                'value': skew.get('skew_25d_ratio'),
                'pass': skew_pass,
                'score': 1 if skew_pass else 0,
                'label': f"Skew {((skew.get('skew_25d_ratio') or 1) - 1) * 100:.1f}%",
                'signal': skew.get('skew_signal')
            }
            if skew_pass:
                total_score += 1
                factors.append('Skew steep')
        else:
            scores['skew'] = {'error': skew.get('error'), 'score': 0}

        # 3. Term Structure
        term = get_iv_term_structure(ticker)
        if 'error' not in term:
            term_pass = term.get('slope', 0) < -0.02  # Backwardated
            scores['term_structure'] = {
                'value': term.get('slope_pct'),
                'pass': term_pass,
                'score': 1 if term_pass else 0,
                'label': f"Term {term.get('slope_pct', 0):.1f}%",
                'signal': term.get('structure_signal')
            }
            if term_pass:
                total_score += 1
                factors.append('Backwardated')
        else:
            scores['term_structure'] = {'error': term.get('error'), 'score': 0}

        # 4. GEX Regime
        gex = get_gex_regime(ticker, expiration)
        if 'error' not in gex:
            gex_pass = gex.get('regime') == 'pinned'  # Positive GEX
            scores['gex'] = {
                'value': gex.get('gex_billions'),
                'pass': gex_pass,
                'score': 1 if gex_pass else 0,
                'label': f"GEX ${gex.get('gex_billions', 0):.1f}B",
                'signal': gex.get('regime')
            }
            if gex_pass:
                total_score += 1
                factors.append('GEX positive')
        else:
            scores['gex'] = {'error': gex.get('error'), 'score': 0}

        # 5. RV Direction (use ETF proxy for futures)
        FUTURES_TO_ETF = {'ES': 'SPY', 'MES': 'SPY', 'NQ': 'QQQ', 'MNQ': 'QQQ', 'RTY': 'IWM', 'YM': 'DIA', 'CL': 'USO', 'GC': 'GLD', 'SI': 'SLV', 'ZB': 'TLT', 'ZN': 'IEF'}
        rv_ticker = ticker
        if is_futures_ticker(ticker):
            normalized = normalize_futures_ticker(ticker)
            rv_ticker = FUTURES_TO_ETF.get(normalized, ticker)
            logger.info(f"Using {rv_ticker} as RV proxy for {ticker}")
        rv = calculate_realized_volatility(rv_ticker)
        if 'error' not in rv:
            rv_pass = rv.get('rv_direction') == 'falling'
            scores['rv_direction'] = {
                'value': rv.get('rv_5d'),
                'pass': rv_pass,
                'score': 1 if rv_pass else 0,
                'label': f"RV {rv.get('rv_direction', 'unknown')}",
                'signal': rv.get('rv_regime')
            }
            if rv_pass:
                total_score += 1
                factors.append('RV falling')
        else:
            scores['rv_direction'] = {'error': rv.get('error'), 'score': 0}

        # 6. Expected Move (placeholder - needs breakeven input for full calc)
        em = get_expected_move(ticker, expiration)
        if 'error' not in em:
            # For scoring, we check if expected move is reasonable (>2% for weekly)
            em_pct = em.get('expected_move_pct', 0)
            em_pass = em_pct > 0  # Basic check that we have data
            scores['expected_move'] = {
                'value': em.get('expected_move'),
                'pass': em_pass,
                'score': 1 if em_pass else 0,
                'label': f"EM ±{em_pct:.1f}%",
                'levels': {
                    'upper': em.get('upper_expected'),
                    'lower': em.get('lower_expected'),
                    'lower_1_5x': em.get('lower_1_5x_em'),
                    'lower_2x': em.get('lower_2x_em')
                }
            }
            if em_pass:
                total_score += 1
                factors.append('EM calculated')
        else:
            scores['expected_move'] = {'error': em.get('error'), 'score': 0}

        # Generate overall recommendation
        if total_score >= 5:
            verdict = 'HIGH_CONVICTION'
            recommendation = 'Excellent conditions - full size entry recommended'
            risk_level = 'low'
            position_size = '100%'
        elif total_score >= 4:
            verdict = 'FAVORABLE'
            recommendation = 'Good conditions - standard size entry'
            risk_level = 'moderate'
            position_size = '75%'
        elif total_score >= 3:
            verdict = 'NEUTRAL'
            recommendation = 'Mixed signals - reduced size or wait for better setup'
            risk_level = 'elevated'
            position_size = '50%'
        elif total_score >= 2:
            verdict = 'UNFAVORABLE'
            recommendation = 'Poor conditions - minimal size only if must trade'
            risk_level = 'high'
            position_size = '25%'
        else:
            verdict = 'AVOID'
            recommendation = 'Do not enter ratio spread - conditions unfavorable'
            risk_level = 'extreme'
            position_size = '0%'

        return {
            'ticker': ticker.upper(),
            'timestamp': datetime.now().isoformat(),
            'expiration': expiration,

            # Overall score
            'total_score': total_score,
            'max_score': 6,
            'score_pct': round(total_score / 6 * 100),
            'verdict': verdict,
            'recommendation': recommendation,
            'risk_level': risk_level,
            'position_size': position_size,
            'passing_factors': factors,

            # Individual scores
            'scores': scores,

            # Full data for display
            'vrp_data': vrp if 'error' not in vrp else None,
            'skew_data': skew if 'error' not in skew else None,
            'term_data': term if 'error' not in term else None,
            'gex_data': gex if 'error' not in gex else None,
            'rv_data': rv if 'error' not in rv else None,
            'em_data': em if 'error' not in em else None,

            # Current price
            'current_price': vrp.get('current_price') if 'error' not in vrp else None
        }

    except Exception as e:
        logger.error(f"Ratio spread score error for {ticker}: {e}")
        return {"error": str(e), "ticker": ticker}


async def get_ratio_spread_score_v2(ticker: str, target_dte: int = 120) -> Dict:
    """
    Ratio Spread Score V2 - Uses Tastytrade for accurate 120 DTE analysis.

    Designed for back ratio put spread traders using longer-dated options.

    Factors (0-6 score):
    - VRP (IV vs RV): +1 if positive (options overpriced)
    - Skew at target DTE: +1 if steep (OTM puts rich)
    - Term Structure (30 vs 120 DTE): +1 if backwardated
    - GEX Regime: +1 if positive (dealers suppress moves)
    - RV Direction: +1 if falling (vol compressing)
    - Expected Move: +1 if calculated successfully

    Args:
        ticker: Stock symbol
        target_dte: Target DTE for your trade (default 120)

    Returns:
        Complete analysis with scores and recommendation
    """
    from datetime import datetime

    try:
        # Try to import Tastytrade provider
        try:
            from src.data.tastytrade_provider import (
                is_tastytrade_available,
                get_iv_by_delta_tastytrade,
                get_term_structure_tastytrade,
                get_expected_move_tastytrade
            )
            use_tastytrade = is_tastytrade_available()
        except ImportError:
            use_tastytrade = False

        scores = {}
        factors = []
        total_score = 0
        data_source = 'tastytrade' if use_tastytrade else 'polygon'

        logger.info(f"Ratio spread score V2 for {ticker} @ {target_dte} DTE (source: {data_source})")

        # 1. VRP Analysis (uses price data, not expiration-dependent)
        vrp = await get_vrp_analysis(ticker, None)
        if 'error' not in vrp:
            vrp_pass = vrp.get('vrp', 0) > 0.02  # At least 2% VRP
            scores['vrp'] = {
                'value': vrp.get('vrp_pct'),
                'pass': vrp_pass,
                'score': 1 if vrp_pass else 0,
                'label': f"VRP {vrp.get('vrp_pct', 0):.1f}%",
                'signal': vrp.get('vrp_signal')
            }
            if vrp_pass:
                total_score += 1
                factors.append('VRP positive')
        else:
            scores['vrp'] = {'error': vrp.get('error'), 'score': 0}

        # 2. Skew Analysis at target DTE
        skew = None
        if use_tastytrade:
            skew = await get_iv_by_delta_tastytrade(ticker, target_dte=target_dte)
            if skew:
                skew_ratio = skew.get('skew_ratio', 1)
                skew_pass = skew_ratio > 1.05  # At least 5% skew
                scores['skew'] = {
                    'value': skew_ratio,
                    'pass': skew_pass,
                    'score': 1 if skew_pass else 0,
                    'label': f"Skew {((skew_ratio or 1) - 1) * 100:.1f}%",
                    'signal': 'steep' if skew_pass else 'flat',
                    'dte': skew.get('dte')
                }
                if skew_pass:
                    total_score += 1
                    factors.append('Skew steep')

        if not skew or 'error' in (skew or {}):
            # Fallback to Polygon
            skew_polygon = get_skew_analysis(ticker, None)
            if 'error' not in skew_polygon:
                skew_pass = (skew_polygon.get('skew_25d_ratio') or 0) > 1.05
                scores['skew'] = {
                    'value': skew_polygon.get('skew_25d_ratio'),
                    'pass': skew_pass,
                    'score': 1 if skew_pass else 0,
                    'label': f"Skew {((skew_polygon.get('skew_25d_ratio') or 1) - 1) * 100:.1f}%",
                    'signal': skew_polygon.get('skew_signal'),
                    'note': 'Near-term data (Polygon)'
                }
                if skew_pass:
                    total_score += 1
                    factors.append('Skew steep')
                skew = skew_polygon
            else:
                scores['skew'] = {'error': skew_polygon.get('error'), 'score': 0}
                skew = skew_polygon

        # 3. Term Structure (30 DTE vs target DTE)
        term = None
        if use_tastytrade:
            term = await get_term_structure_tastytrade(ticker, front_dte=30, back_dte=target_dte)
            if term and 'error' not in term:
                term_pass = term.get('slope', 0) < -0.02  # Backwardated
                scores['term_structure'] = {
                    'value': term.get('slope_pct'),
                    'pass': term_pass,
                    'score': 1 if term_pass else 0,
                    'label': f"Term {term.get('slope_pct', 0):.1f}%",
                    'signal': term.get('signal'),
                    'front_dte': term.get('front_dte'),
                    'back_dte': term.get('back_dte')
                }
                if term_pass:
                    total_score += 1
                    factors.append('Backwardated')

        if not term or 'error' in (term or {}):
            # Fallback to Polygon (likely to fail for long-dated)
            term_polygon = get_iv_term_structure(ticker)
            if 'error' not in term_polygon:
                term_pass = term_polygon.get('slope', 0) < -0.02
                scores['term_structure'] = {
                    'value': term_polygon.get('slope_pct'),
                    'pass': term_pass,
                    'score': 1 if term_pass else 0,
                    'label': f"Term {term_polygon.get('slope_pct', 0):.1f}%",
                    'signal': term_polygon.get('structure_signal'),
                    'note': 'Near-term data only'
                }
                if term_pass:
                    total_score += 1
                    factors.append('Backwardated')
                term = term_polygon
            else:
                scores['term_structure'] = {'error': term_polygon.get('error'), 'score': 0}
                term = term_polygon

        # 4. GEX Regime (not expiration-dependent)
        gex = get_gex_regime(ticker, None)
        if 'error' not in gex:
            gex_pass = gex.get('regime') == 'pinned'  # Positive GEX
            scores['gex'] = {
                'value': gex.get('gex_billions'),
                'pass': gex_pass,
                'score': 1 if gex_pass else 0,
                'label': f"GEX ${gex.get('gex_billions', 0):.1f}B",
                'signal': gex.get('regime')
            }
            if gex_pass:
                total_score += 1
                factors.append('GEX positive')
        else:
            scores['gex'] = {'error': gex.get('error'), 'score': 0}

        # 5. RV Direction (use ETF proxy for futures)
        FUTURES_TO_ETF = {'ES': 'SPY', 'MES': 'SPY', 'NQ': 'QQQ', 'MNQ': 'QQQ', 'RTY': 'IWM', 'YM': 'DIA', 'CL': 'USO', 'GC': 'GLD', 'SI': 'SLV', 'ZB': 'TLT', 'ZN': 'IEF'}
        rv_ticker = ticker
        if is_futures_ticker(ticker):
            normalized = normalize_futures_ticker(ticker)
            rv_ticker = FUTURES_TO_ETF.get(normalized, ticker)
            logger.info(f"Using {rv_ticker} as RV proxy for {ticker}")
        rv = calculate_realized_volatility(rv_ticker)
        if 'error' not in rv:
            rv_pass = rv.get('rv_direction') == 'falling'
            scores['rv_direction'] = {
                'value': rv.get('rv_5d'),
                'pass': rv_pass,
                'score': 1 if rv_pass else 0,
                'label': f"RV {rv.get('rv_direction', 'unknown')}",
                'signal': rv.get('rv_regime')
            }
            if rv_pass:
                total_score += 1
                factors.append('RV falling')
        else:
            scores['rv_direction'] = {'error': rv.get('error'), 'score': 0}

        # 6. Expected Move at target DTE
        em = None
        if use_tastytrade:
            em = await get_expected_move_tastytrade(ticker, target_dte=target_dte)
            if em and 'error' not in em:
                em_pct = em.get('expected_move_pct', 0)
                em_pass = em_pct > 0
                scores['expected_move'] = {
                    'value': em.get('expected_move'),
                    'pass': em_pass,
                    'score': 1 if em_pass else 0,
                    'label': f"EM ±{em_pct:.1f}%",
                    'dte': em.get('dte'),
                    'levels': {
                        'upper': em.get('upper_expected'),
                        'lower': em.get('lower_expected'),
                        'lower_1_5x': em.get('lower_1_5x_em'),
                        'lower_2x': em.get('lower_2x_em')
                    }
                }
                if em_pass:
                    total_score += 1
                    factors.append('EM calculated')

        if not em or 'error' in (em or {}):
            # Fallback to Polygon
            em_polygon = get_expected_move(ticker, None)
            if 'error' not in em_polygon:
                em_pct = em_polygon.get('expected_move_pct', 0)
                em_pass = em_pct > 0
                scores['expected_move'] = {
                    'value': em_polygon.get('expected_move'),
                    'pass': em_pass,
                    'score': 1 if em_pass else 0,
                    'label': f"EM ±{em_pct:.1f}%",
                    'dte': em_polygon.get('dte'),
                    'levels': {
                        'upper': em_polygon.get('upper_expected'),
                        'lower': em_polygon.get('lower_expected'),
                        'lower_1_5x': em_polygon.get('lower_1_5x_em'),
                        'lower_2x': em_polygon.get('lower_2x_em')
                    },
                    'note': 'Near-term data (Polygon)'
                }
                if em_pass:
                    total_score += 1
                    factors.append('EM calculated')
                em = em_polygon
            else:
                scores['expected_move'] = {'error': em_polygon.get('error'), 'score': 0}
                em = em_polygon

        # Generate verdict
        if total_score >= 5:
            verdict = 'HIGH_CONVICTION'
            recommendation = 'Excellent conditions - full size entry recommended'
            risk_level = 'low'
            position_size = '100%'
        elif total_score >= 4:
            verdict = 'FAVORABLE'
            recommendation = 'Good conditions - standard size entry'
            risk_level = 'moderate'
            position_size = '75%'
        elif total_score >= 3:
            verdict = 'NEUTRAL'
            recommendation = 'Mixed signals - reduced size or wait for better setup'
            risk_level = 'elevated'
            position_size = '50%'
        elif total_score >= 2:
            verdict = 'UNFAVORABLE'
            recommendation = 'Poor conditions - minimal size only if must trade'
            risk_level = 'high'
            position_size = '25%'
        else:
            verdict = 'AVOID'
            recommendation = 'Do not enter ratio spread - conditions unfavorable'
            risk_level = 'extreme'
            position_size = '0%'

        return {
            'ticker': ticker.upper(),
            'timestamp': datetime.now().isoformat(),
            'target_dte': target_dte,
            'data_source': data_source,

            # Overall score
            'total_score': total_score,
            'max_score': 6,
            'score_pct': round(total_score / 6 * 100),
            'verdict': verdict,
            'recommendation': recommendation,
            'risk_level': risk_level,
            'position_size': position_size,
            'passing_factors': factors,

            # Individual scores
            'scores': scores,

            # Full data for display
            'vrp_data': vrp if 'error' not in vrp else None,
            'skew_data': skew if skew and 'error' not in skew else None,
            'term_data': term if term and 'error' not in term else None,
            'gex_data': gex if 'error' not in gex else None,
            'rv_data': rv if 'error' not in rv else None,
            'em_data': em if em and 'error' not in em else None,

            # Current price
            'current_price': vrp.get('current_price') if 'error' not in vrp else None
        }

    except Exception as e:
        logger.error(f"Ratio spread score V2 error for {ticker}: {e}")
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
