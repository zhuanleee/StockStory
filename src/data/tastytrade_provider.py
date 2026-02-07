"""
Tastytrade Data Provider

Provides options chain data, Greeks, and market data from Tastytrade API.
Supports all expirations including 120+ DTE for ratio spread analysis.

Authentication: Uses OAuth2 with client_id, client_secret, and refresh_token.
"""

import os
import re
import math
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from functools import lru_cache
import asyncio

logger = logging.getLogger(__name__)

# Global session cache
_session = None
_session_expiry = None
_tasty_client = None

# GEX calculation cache to prevent concurrent DXLinkStreamer connections
import time as _time
_gex_cache = {}  # key: (ticker, expiration) -> {'result': dict, 'ts': float}
_gex_locks = {}  # key: (ticker, expiration) -> asyncio.Lock
_GEX_CACHE_TTL = 120  # seconds (2 min - GEX data doesn't change frequently)

# Max Pain calculation cache (same pattern as GEX)
_maxpain_cache = {}  # key: (ticker, expiration) -> {'result': dict, 'ts': float}
_maxpain_locks = {}  # key: (ticker, expiration) -> asyncio.Lock
_MAXPAIN_CACHE_TTL = 120  # seconds

# X-Ray calculation cache (same pattern as GEX)
_xray_cache = {}  # key: (ticker, expiration) -> {'result': dict, 'ts': float}
_xray_locks = {}  # key: (ticker, expiration) -> asyncio.Lock
_XRAY_CACHE_TTL = 120  # seconds

def get_tastytrade_session():
    """
    Get or create a Tastytrade session using OAuth2.
    Sessions are cached and reused until they expire.

    Required environment variables:
    - TASTYTRADE_CLIENT_ID: OAuth client ID
    - TASTYTRADE_CLIENT_SECRET: OAuth client secret
    - TASTYTRADE_REFRESH_TOKEN: OAuth refresh token (long-lived)
    """
    global _session, _session_expiry, _tasty_client

    # Check if we have a valid cached session
    if _session is not None and _session_expiry and datetime.now() < _session_expiry:
        return _session

    client_secret = os.environ.get('TASTYTRADE_CLIENT_SECRET')
    refresh_token = os.environ.get('TASTYTRADE_REFRESH_TOKEN')

    if not client_secret:
        logger.warning("TASTYTRADE_CLIENT_SECRET not set")
        return None

    if not refresh_token:
        logger.warning("TASTYTRADE_REFRESH_TOKEN not set")
        return None

    try:
        # Use unofficial SDK (tastytrade from tastyware) - it's more mature
        # Session takes (client_secret, refresh_token) directly
        from tastytrade import Session
        logger.info("Creating Tastytrade session via unofficial SDK (OAuth2)...")
        logger.info(f"Using client_secret: {client_secret[:10]}... refresh_token: {refresh_token[:20]}...")

        _session = Session(client_secret, refresh_token)
        _session_expiry = datetime.now() + timedelta(minutes=14)
        logger.info("Tastytrade OAuth2 session created successfully")
        return _session

    except ImportError as e:
        logger.error(f"Tastytrade SDK not installed: {e}")
        _session = None
        _session_expiry = None
        return None
    except Exception as e:
        logger.error(f"Failed to create Tastytrade session: {e}")
        import traceback
        logger.error(traceback.format_exc())
        _session = None
        _session_expiry = None
        return None


def invalidate_session():
    """Force the next call to create a fresh Tastytrade session."""
    global _session, _session_expiry
    _session = None
    _session_expiry = None
    logger.info("Tastytrade session invalidated — will refresh on next call")


def is_futures_ticker(ticker: str) -> bool:
    """Check if ticker is a futures symbol (starts with /)."""
    return ticker.startswith('/')


async def get_futures_option_chain_tastytrade(ticker: str) -> Optional[Dict]:
    """
    Get futures options chain from Tastytrade.

    Args:
        ticker: Futures symbol starting with / (e.g., /ES, /NQ, /CL, /GC)

    Returns:
        Dict with futures options chain data
    """
    session = get_tastytrade_session()
    if not session:
        return None

    try:
        from tastytrade.instruments import get_future_option_chain
        from datetime import date
        import inspect

        logger.info(f"Fetching futures options chain for {ticker} from Tastytrade")

        # Get the futures option chain (SDK function may be async)
        result = get_future_option_chain(session, ticker)
        chain = await result if inspect.iscoroutine(result) else result

        if not chain:
            logger.warning(f"No futures options chain found for {ticker}")
            return None

        today = date.today()
        expirations_data = []

        # Chain is keyed by expiration date
        for exp_date in sorted(chain.keys()):
            dte = (exp_date - today).days
            options_list = chain[exp_date]

            # Handle both list and dict structures
            if isinstance(options_list, dict):
                # Keyed by strike price
                strikes_map = {}
                for strike_price, opt in options_list.items():
                    strike_float = float(strike_price)
                    opt_type = getattr(opt, 'option_type', None)
                    streamer_sym = getattr(opt, 'streamer_symbol', None)
                    symbol = getattr(opt, 'symbol', None)

                    if strike_float not in strikes_map:
                        strikes_map[strike_float] = {'call': None, 'put': None}

                    if opt_type == 'C':
                        strikes_map[strike_float]['call'] = {
                            'symbol': str(symbol) if symbol else streamer_sym,
                            'streamer_symbol': streamer_sym,
                        }
                    elif opt_type == 'P':
                        strikes_map[strike_float]['put'] = {
                            'symbol': str(symbol) if symbol else streamer_sym,
                            'streamer_symbol': streamer_sym,
                        }
            else:
                # List of options
                strikes_map = {}
                for opt in options_list:
                    strike_price = getattr(opt, 'strike_price', None)
                    opt_type = getattr(opt, 'option_type', None)
                    symbol = getattr(opt, 'symbol', None)
                    streamer_sym = getattr(opt, 'streamer_symbol', None)

                    if strike_price is None:
                        continue

                    strike_float = float(strike_price)
                    if strike_float not in strikes_map:
                        strikes_map[strike_float] = {'call': None, 'put': None}

                    if opt_type == 'C':
                        strikes_map[strike_float]['call'] = {
                            'symbol': str(symbol) if symbol else streamer_sym,
                            'streamer_symbol': streamer_sym,
                        }
                    elif opt_type == 'P':
                        strikes_map[strike_float]['put'] = {
                            'symbol': str(symbol) if symbol else streamer_sym,
                            'streamer_symbol': streamer_sym,
                        }

            strikes_data = [
                {'strike': strike, 'call': data['call'], 'put': data['put']}
                for strike, data in sorted(strikes_map.items())
            ]

            expirations_data.append({
                'date': exp_date.strftime('%Y-%m-%d') if hasattr(exp_date, 'strftime') else str(exp_date),
                'dte': dte,
                'strikes': strikes_data
            })

        expirations_data.sort(key=lambda x: x['dte'])

        logger.info(f"Found {len(expirations_data)} expirations for futures {ticker}")

        return {
            'ticker': ticker,
            'is_futures': True,
            'expirations': expirations_data
        }

    except Exception as e:
        logger.error(f"Error fetching Tastytrade futures options chain for {ticker}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None


async def get_options_with_greeks_tastytrade(ticker: str, expiration: str = None, target_dte: int = None) -> Optional[Dict]:
    """
    Get options chain with live Greeks from Tastytrade.

    Args:
        ticker: Stock symbol
        expiration: Specific expiration date (YYYY-MM-DD) or None for auto-select
        target_dte: Target DTE to find closest expiration (e.g., 120)

    Returns:
        Dict with full options data including Greeks
    """
    session = get_tastytrade_session()
    if not session:
        return None

    try:
        from tastytrade import DXLinkStreamer
        from tastytrade.dxfeed import Greeks
        from datetime import date
        import inspect

        logger.info(f"Fetching options with Greeks for {ticker} (target_dte={target_dte})")

        # Use appropriate chain function for futures vs equities
        if is_futures_ticker(ticker):
            from tastytrade.instruments import get_future_option_chain
            result = get_future_option_chain(session, ticker)
        else:
            from tastytrade.instruments import get_option_chain
            result = get_option_chain(session, ticker)

        chain = await result if inspect.iscoroutine(result) else result

        if not chain:
            return None

        today = date.today()
        exp_dates = sorted(chain.keys())

        if not exp_dates:
            logger.warning(f"No expirations found for {ticker}")
            return None

        # Find the target expiration date
        target_exp_date = None

        if expiration:
            # Use specified expiration
            from datetime import datetime as dt
            target_date = dt.strptime(expiration, '%Y-%m-%d').date()
            if target_date in chain:
                target_exp_date = target_date
        elif target_dte:
            # Find closest to target DTE
            best_diff = float('inf')
            for exp_date in exp_dates:
                dte = (exp_date - today).days
                diff = abs(dte - target_dte)
                if diff < best_diff:
                    best_diff = diff
                    target_exp_date = exp_date
        else:
            # Default to first available expiration > 7 DTE
            for exp_date in exp_dates:
                dte = (exp_date - today).days
                if dte >= 7:
                    target_exp_date = exp_date
                    break

        if not target_exp_date:
            # Fall back to first available
            target_exp_date = exp_dates[0] if exp_dates else None

        if not target_exp_date:
            logger.warning(f"No suitable expiration found for {ticker}")
            return None

        dte = (target_exp_date - today).days
        logger.info(f"Using expiration {target_exp_date} ({dte} DTE)")

        # Get options for the target expiration
        # SDK v11: chain[exp_date] is a LIST of Option objects
        options_list = chain[target_exp_date]
        logger.info(f"Found {len(options_list)} options for {target_exp_date}")

        # Collect all option symbols for streaming
        call_symbols = []
        put_symbols = []
        strike_to_symbols = {}  # Map strike -> {'call': symbol, 'put': symbol}

        # SDK v11: each item in the list is an Option object with attributes like:
        # - strike_price: Decimal
        # - option_type: 'C' or 'P'
        # - streamer_symbol: string for DXLinkStreamer
        # - symbol: string ticker symbol
        for opt in options_list:
            strike_price = getattr(opt, 'strike_price', None)
            opt_type = getattr(opt, 'option_type', None)
            streamer_sym = getattr(opt, 'streamer_symbol', None)

            if strike_price is None or opt_type is None or streamer_sym is None:
                continue

            strike_float = float(strike_price)

            if strike_float not in strike_to_symbols:
                strike_to_symbols[strike_float] = {'call': None, 'put': None}

            if opt_type == 'C':
                call_symbols.append(streamer_sym)
                strike_to_symbols[strike_float]['call'] = streamer_sym
            elif opt_type == 'P':
                put_symbols.append(streamer_sym)
                strike_to_symbols[strike_float]['put'] = streamer_sym

        logger.info(f"Found {len(call_symbols)} calls, {len(put_symbols)} puts")

        # Stream Greeks and Summary (for OI) for all options
        greeks_data = {}
        summary_data = {}

        async def fetch_greeks_and_summary():
            import time
            try:
                async with DXLinkStreamer(session) as streamer:
                    all_symbols = call_symbols + put_symbols
                    if not all_symbols:
                        return

                    logger.info(f"Subscribing to Greeks and Summary for {len(all_symbols)} symbols")

                    # Import Summary event type
                    from tastytrade.dxfeed import Summary

                    # Subscribe to both Greeks and Summary (for OI)
                    await streamer.subscribe(Greeks, all_symbols)
                    await streamer.subscribe(Summary, all_symbols)

                    # Collect data with manual timeout
                    greeks_received = 0
                    summary_received = 0
                    target = len(all_symbols)
                    start_time = time.time()
                    timeout_sec = 30.0

                    # Listen for Greeks
                    async for greek in streamer.listen(Greeks):
                        greeks_data[greek.event_symbol] = {
                            'iv': greek.volatility,
                            'delta': greek.delta,
                            'gamma': greek.gamma,
                            'theta': greek.theta,
                            'vega': greek.vega,
                            'price': greek.price
                        }
                        greeks_received += 1

                        if greeks_received >= target:
                            logger.info(f"Received all {greeks_received} Greeks")
                            break
                        if time.time() - start_time > timeout_sec:
                            logger.warning(f"Greeks streaming timed out after {greeks_received}/{target}")
                            break

                    # Listen for Summary (OI data)
                    start_time = time.time()
                    async for summary in streamer.listen(Summary):
                        summary_data[summary.event_symbol] = {
                            'open_interest': summary.open_interest,
                            'day_volume': getattr(summary, 'prev_day_volume', None),
                        }
                        summary_received += 1

                        if summary_received >= target:
                            logger.info(f"Received all {summary_received} Summary events")
                            break
                        if time.time() - start_time > timeout_sec:
                            logger.warning(f"Summary streaming timed out after {summary_received}/{target}")
                            break

            except Exception as e:
                logger.warning(f"Error in Greeks/Summary streaming: {e}")
                import traceback
                logger.warning(traceback.format_exc())

        # Run async fetch (we're already in async context)
        await fetch_greeks_and_summary()

        logger.info(f"Received Greeks for {len(greeks_data)} options, Summary for {len(summary_data)} options")

        # Build response
        options_data = []
        for strike_price in sorted(strike_to_symbols.keys()):
            symbols = strike_to_symbols[strike_price]

            call_data = None
            put_data = None

            call_sym = symbols.get('call')
            put_sym = symbols.get('put')

            if call_sym and call_sym in greeks_data:
                g = greeks_data[call_sym]
                s = summary_data.get(call_sym, {})
                call_data = {
                    'symbol': call_sym,
                    'strike': strike_price,
                    'type': 'call',
                    'iv': g.get('iv'),
                    'delta': g.get('delta'),
                    'gamma': g.get('gamma'),
                    'theta': g.get('theta'),
                    'vega': g.get('vega'),
                    'price': g.get('price'),
                    'open_interest': s.get('open_interest', 0),
                    'volume': s.get('day_volume', 0),
                }

            if put_sym and put_sym in greeks_data:
                g = greeks_data[put_sym]
                s = summary_data.get(put_sym, {})
                put_data = {
                    'symbol': put_sym,
                    'strike': strike_price,
                    'type': 'put',
                    'iv': g.get('iv'),
                    'delta': abs(g.get('delta', 0)) if g.get('delta') else None,
                    'gamma': g.get('gamma'),
                    'theta': g.get('theta'),
                    'vega': g.get('vega'),
                    'price': g.get('price'),
                    'open_interest': s.get('open_interest', 0),
                    'volume': s.get('day_volume', 0),
                }

            options_data.append({
                'strike': strike_price,
                'call': call_data,
                'put': put_data
            })

        return {
            'ticker': ticker.upper(),
            'expiration': target_exp_date.strftime('%Y-%m-%d'),
            'dte': dte,
            'options': options_data,
            'source': 'tastytrade'
        }

    except Exception as e:
        logger.error(f"Error fetching Tastytrade Greeks for {ticker}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None


async def get_expirations_tastytrade_async(ticker: str) -> Optional[Dict]:
    """
    Get all available expirations for a ticker (equities or futures).
    Async version that properly awaits SDK calls.

    Returns:
        Dict with 'ticker', 'is_futures', and 'expirations' list
    """
    session = get_tastytrade_session()
    if not session:
        return None

    try:
        from datetime import date
        import inspect

        # Use appropriate chain function for futures vs equities
        if is_futures_ticker(ticker):
            from tastytrade.instruments import get_future_option_chain
            result = get_future_option_chain(session, ticker)
        else:
            from tastytrade.instruments import get_option_chain
            result = get_option_chain(session, ticker)

        # Await if async
        if inspect.iscoroutine(result):
            chain = await result
        else:
            chain = result

        if not chain:
            return None

        today = date.today()
        expirations = []

        # Chain is a dict keyed by expiration date
        for exp_date in chain.keys():
            dte = (exp_date - today).days
            # Count strikes at this expiration
            options_at_exp = chain[exp_date]
            if isinstance(options_at_exp, dict):
                strike_count = len(options_at_exp)
            else:
                strike_count = len(options_at_exp) // 2  # Calls + puts

            expirations.append({
                'date': exp_date.strftime('%Y-%m-%d') if hasattr(exp_date, 'strftime') else str(exp_date),
                'dte': dte,
                'strike_count': strike_count
            })

        # Sort by DTE
        expirations.sort(key=lambda x: x['dte'])

        return {
            'ticker': ticker,
            'is_futures': is_futures_ticker(ticker),
            'expiration_count': len(expirations),
            'expirations': expirations
        }

    except Exception as e:
        logger.error(f"Error fetching Tastytrade expirations for {ticker}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None


def get_expirations_tastytrade(ticker: str) -> Optional[Dict]:
    """Sync wrapper for get_expirations_tastytrade_async."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # We're already in an async context, can't use run_until_complete
            # Create a new thread to run the async function
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, get_expirations_tastytrade_async(ticker))
                return future.result(timeout=30)
        else:
            return loop.run_until_complete(get_expirations_tastytrade_async(ticker))
    except Exception as e:
        logger.error(f"Error in sync wrapper for expirations: {e}")
        return None


async def calculate_max_pain_tastytrade(ticker: str, expiration: str = None) -> Dict:
    """
    Calculate Max Pain for futures using Tastytrade chain data + OI from DXLinkStreamer.
    Uses a TTL cache + async lock to prevent concurrent DXLinkStreamer connections.
    """
    cache_key = (ticker.upper(), expiration)

    # Check cache
    cached = _maxpain_cache.get(cache_key)
    if cached and (_time.time() - cached['ts']) < _MAXPAIN_CACHE_TTL:
        logger.info(f"MaxPain cache hit for {cache_key}")
        return cached['result']

    # Acquire per-key lock to prevent concurrent DXLink streams
    if cache_key not in _maxpain_locks:
        _maxpain_locks[cache_key] = asyncio.Lock()
    async with _maxpain_locks[cache_key]:
        # Double-check cache after acquiring lock
        cached = _maxpain_cache.get(cache_key)
        if cached and (_time.time() - cached['ts']) < _MAXPAIN_CACHE_TTL:
            logger.info(f"MaxPain cache hit (post-lock) for {cache_key}")
            return cached['result']

        result = await _calculate_max_pain_tastytrade_impl(ticker, expiration)
        if 'error' not in result:
            _maxpain_cache[cache_key] = {'result': result, 'ts': _time.time()}
        return result


async def _calculate_max_pain_tastytrade_impl(ticker: str, expiration: str = None) -> Dict:
    """Internal implementation of Max Pain calculation (not cached)."""
    session = get_tastytrade_session()
    if not session:
        return {"error": "Tastytrade session not available"}

    try:
        from tastytrade.instruments import get_future_option_chain
        from tastytrade import DXLinkStreamer
        from tastytrade.dxfeed import Summary
        from datetime import date
        import inspect, time

        result = get_future_option_chain(session, ticker)
        chain = await result if inspect.iscoroutine(result) else result
        if not chain:
            return {"error": f"No futures options chain for {ticker}"}

        today = date.today()
        exp_dates = sorted(chain.keys())

        # Pick expiration
        target_exp = None
        if expiration:
            from datetime import datetime as dt
            target_date = dt.strptime(expiration, '%Y-%m-%d').date()
            if target_date in chain:
                target_exp = target_date
        if not target_exp:
            # Pick first expiration with DTE >= 1
            for ed in exp_dates:
                if (ed - today).days >= 1:
                    target_exp = ed
                    break
        if not target_exp and exp_dates:
            target_exp = exp_dates[0]
        if not target_exp:
            return {"error": "No valid expiration found"}

        dte = (target_exp - today).days
        options_list = chain[target_exp]

        # Collect strikes and streamer symbols
        strike_data = {}  # strike -> {call_sym, put_sym}
        all_symbols = []
        for opt in options_list:
            strike = float(getattr(opt, 'strike_price', 0))
            opt_type = getattr(opt, 'option_type', None)
            sym = getattr(opt, 'streamer_symbol', None)
            if not strike or not opt_type or not sym:
                continue
            if strike not in strike_data:
                strike_data[strike] = {'call_sym': None, 'put_sym': None}
            if opt_type == 'C':
                strike_data[strike]['call_sym'] = sym
            elif opt_type == 'P':
                strike_data[strike]['put_sym'] = sym
            all_symbols.append(sym)

        if not all_symbols:
            return {"error": "No option symbols found"}

        # Stream OI data + underlying quote for current price
        oi_data = {}
        current_price = 0.0
        from tastytrade.dxfeed import Quote

        # Build streamer symbol for underlying futures
        FUTURES_EXCHANGE = {
            '/ES': ':XCME', '/NQ': ':XCME', '/YM': ':XCME', '/RTY': ':XCME',
            '/CL': ':XNYM', '/NG': ':XNYM',
            '/GC': ':XCEC', '/SI': ':XCEC', '/HG': ':XCEC',
            '/ZB': ':XCBT', '/ZN': ':XCBT', '/ZC': ':XCBT', '/ZS': ':XCBT', '/ZW': ':XCBT',
        }
        t = ticker.upper()
        suffix = FUTURES_EXCHANGE.get(t, ':XCME')
        for root, exch in FUTURES_EXCHANGE.items():
            if t.startswith(root) and len(t) > len(root):
                suffix = exch
                break
        underlying_sym = t + suffix

        async with DXLinkStreamer(session) as streamer:
            await streamer.subscribe(Summary, all_symbols)
            await streamer.subscribe(Quote, [underlying_sym])

            # Get underlying quote first (fast)
            try:
                import asyncio as _asyncio
                quote = await _asyncio.wait_for(streamer.get_event(Quote), timeout=5)
                bid = float(quote.bid_price) if quote.bid_price else 0.0
                ask = float(quote.ask_price) if quote.ask_price else 0.0
                current_price = (bid + ask) / 2 if bid and ask else bid or ask
            except Exception:
                pass

            # Collect OI (0.5s per-event timeout — events arrive in rapid bursts)
            import asyncio as _aio
            summary_iter = streamer.listen(Summary).__aiter__()
            received = 0
            start = time.time()
            while received < len(all_symbols) and time.time() - start < 10:
                try:
                    summary = await _aio.wait_for(summary_iter.__anext__(), timeout=0.5)
                    oi_data[summary.event_symbol] = int(getattr(summary, 'open_interest', 0) or 0)
                    received += 1
                except (_aio.TimeoutError, StopAsyncIteration):
                    break

        # Calculate max pain
        strikes = sorted(strike_data.keys())
        total_call_oi = 0
        total_put_oi = 0
        call_oi_map = {}
        put_oi_map = {}

        for strike in strikes:
            sd = strike_data[strike]
            c_oi = oi_data.get(sd['call_sym'], 0) if sd['call_sym'] else 0
            p_oi = oi_data.get(sd['put_sym'], 0) if sd['put_sym'] else 0
            call_oi_map[strike] = c_oi
            put_oi_map[strike] = p_oi
            total_call_oi += c_oi
            total_put_oi += p_oi

        if total_call_oi == 0 and total_put_oi == 0:
            return {"error": "No open interest data available", "ticker": ticker}

        # Max pain = strike where total pain (for all option holders) is minimized
        pain_by_strike = []
        min_pain = float('inf')
        max_pain_strike = strikes[len(strikes) // 2]

        # Use correct futures multiplier
        root = ticker.lstrip('/').upper()
        mp_multiplier_map = {'ES': 50, 'MES': 5, 'NQ': 20, 'MNQ': 2, 'YM': 5, 'RTY': 50,
                             'CL': 1000, 'NG': 10000, 'GC': 100, 'SI': 5000, 'HG': 25000,
                             'ZB': 1000, 'ZN': 1000, 'ZC': 50, 'ZS': 50, 'ZW': 50}
        contract_multiplier = mp_multiplier_map.get(root, 50)

        for test_strike in strikes:
            total_pain = 0
            for s in strikes:
                # Call pain: calls are worthless below strike, lose money above
                if test_strike > s:
                    total_pain += (test_strike - s) * call_oi_map.get(s, 0) * contract_multiplier
                # Put pain: puts are worthless above strike, lose money below
                if test_strike < s:
                    total_pain += (s - test_strike) * put_oi_map.get(s, 0) * contract_multiplier

            pain_by_strike.append({
                'strike': test_strike,
                'total_pain': total_pain,
                'call_oi': call_oi_map.get(test_strike, 0),
                'put_oi': put_oi_map.get(test_strike, 0),
            })

            if total_pain < min_pain:
                min_pain = total_pain
                max_pain_strike = test_strike

        return {
            'ticker': ticker,
            'expiration': target_exp.strftime('%Y-%m-%d'),
            'max_pain_price': max_pain_strike,
            'current_price': current_price,
            'pain_by_strike': pain_by_strike,
            'total_call_oi': total_call_oi,
            'total_put_oi': total_put_oi,
            'days_to_expiry': dte,
            'source': 'tastytrade',
        }

    except Exception as e:
        logger.error(f"Error calculating max pain for {ticker}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {"error": str(e)}


async def calculate_gex_tastytrade(ticker: str, expiration: str = None) -> Dict:
    """
    Calculate GEX for futures using Tastytrade chain data + Greeks/OI from DXLinkStreamer.
    Uses a TTL cache + async lock to prevent concurrent DXLinkStreamer connections
    when multiple endpoints (gex, gex-levels, gex-regime, combined-regime) are called in parallel.
    """
    cache_key = (ticker.upper(), expiration)

    # Check cache
    cached = _gex_cache.get(cache_key)
    if cached and (_time.time() - cached['ts']) < _GEX_CACHE_TTL:
        logger.info(f"GEX cache hit for {cache_key}")
        return cached['result']

    # Acquire per-key lock to prevent concurrent DXLink streams
    if cache_key not in _gex_locks:
        _gex_locks[cache_key] = asyncio.Lock()
    async with _gex_locks[cache_key]:
        # Double-check cache after acquiring lock
        cached = _gex_cache.get(cache_key)
        if cached and (_time.time() - cached['ts']) < _GEX_CACHE_TTL:
            logger.info(f"GEX cache hit (post-lock) for {cache_key}")
            return cached['result']

        result = await _calculate_gex_tastytrade_impl(ticker, expiration)
        if 'error' not in result:
            _gex_cache[cache_key] = {'result': result, 'ts': _time.time()}
        return result


async def _calculate_gex_tastytrade_impl(ticker: str, expiration: str = None) -> Dict:
    """Internal implementation of GEX calculation (not cached)."""
    session = get_tastytrade_session()
    if not session:
        return {"error": "Tastytrade session not available"}

    try:
        from tastytrade.instruments import get_future_option_chain
        from tastytrade import DXLinkStreamer
        from tastytrade.dxfeed import Greeks, Summary
        from datetime import date
        import inspect, time

        result = get_future_option_chain(session, ticker)
        chain = await result if inspect.iscoroutine(result) else result
        if not chain:
            return {"error": f"No futures options chain for {ticker}"}

        today = date.today()
        exp_dates = sorted(chain.keys())

        # Pick expiration
        target_exp = None
        if expiration:
            from datetime import datetime as dt
            target_date = dt.strptime(expiration, '%Y-%m-%d').date()
            if target_date in chain:
                target_exp = target_date
        if not target_exp:
            for ed in exp_dates:
                if (ed - today).days >= 1:
                    target_exp = ed
                    break
        if not target_exp and exp_dates:
            target_exp = exp_dates[0]
        if not target_exp:
            return {"error": "No valid expiration found"}

        dte = (target_exp - today).days
        options_list = chain[target_exp]

        # Collect strikes and symbols
        strike_data = {}
        all_symbols = []
        for opt in options_list:
            strike = float(getattr(opt, 'strike_price', 0))
            opt_type = getattr(opt, 'option_type', None)
            sym = getattr(opt, 'streamer_symbol', None)
            if not strike or not opt_type or not sym:
                continue
            if strike not in strike_data:
                strike_data[strike] = {'call_sym': None, 'put_sym': None}
            if opt_type == 'C':
                strike_data[strike]['call_sym'] = sym
            elif opt_type == 'P':
                strike_data[strike]['put_sym'] = sym
            all_symbols.append(sym)

        if not all_symbols:
            return {"error": "No option symbols found"}

        # Stream Greeks + OI + underlying quote
        greeks_map = {}
        oi_map = {}
        current_price = 0.0
        from tastytrade.dxfeed import Quote

        # Build streamer symbol for underlying futures
        FUTURES_EXCHANGE = {
            '/ES': ':XCME', '/NQ': ':XCME', '/YM': ':XCME', '/RTY': ':XCME',
            '/CL': ':XNYM', '/NG': ':XNYM',
            '/GC': ':XCEC', '/SI': ':XCEC', '/HG': ':XCEC',
            '/ZB': ':XCBT', '/ZN': ':XCBT', '/ZC': ':XCBT', '/ZS': ':XCBT', '/ZW': ':XCBT',
        }
        t = ticker.upper()
        suffix = FUTURES_EXCHANGE.get(t, ':XCME')
        for root, exch in FUTURES_EXCHANGE.items():
            if t.startswith(root) and len(t) > len(root):
                suffix = exch
                break
        underlying_sym = t + suffix

        async with DXLinkStreamer(session) as streamer:
            await streamer.subscribe(Greeks, all_symbols)
            await streamer.subscribe(Summary, all_symbols)
            await streamer.subscribe(Quote, [underlying_sym])

            # Get underlying quote first (fast)
            try:
                import asyncio as _asyncio
                quote = await _asyncio.wait_for(streamer.get_event(Quote), timeout=5)
                bid = float(quote.bid_price) if quote.bid_price else 0.0
                ask = float(quote.ask_price) if quote.ask_price else 0.0
                current_price = (bid + ask) / 2 if bid and ask else bid or ask
            except Exception:
                pass

            # Collect Greeks (0.5s per-event timeout — events arrive in rapid bursts)
            import asyncio as _aio
            greeks_iter = streamer.listen(Greeks).__aiter__()
            received = 0
            start = time.time()
            while received < len(all_symbols) and time.time() - start < 10:
                try:
                    greek = await _aio.wait_for(greeks_iter.__anext__(), timeout=0.5)
                    greeks_map[greek.event_symbol] = {
                        'gamma': float(greek.gamma) if greek.gamma else 0.0,
                        'delta': float(greek.delta) if greek.delta else 0.0,
                    }
                    received += 1
                except (_aio.TimeoutError, StopAsyncIteration):
                    break

            # Collect OI (0.5s per-event timeout — events arrive in rapid bursts)
            summary_iter = streamer.listen(Summary).__aiter__()
            received = 0
            start = time.time()
            while received < len(all_symbols) and time.time() - start < 10:
                try:
                    summary = await _aio.wait_for(summary_iter.__anext__(), timeout=0.5)
                    oi_map[summary.event_symbol] = int(getattr(summary, 'open_interest', 0) or 0)
                    received += 1
                except (_aio.TimeoutError, StopAsyncIteration):
                    break

        # Calculate GEX by strike
        # Futures multiplier
        multiplier = 50  # ES = $50 per point
        root = ticker.lstrip('/').upper()
        multiplier_map = {'ES': 50, 'MES': 5, 'NQ': 20, 'MNQ': 2, 'YM': 5, 'RTY': 50,
                         'CL': 1000, 'NG': 10000, 'GC': 100, 'SI': 5000, 'HG': 25000,
                         'ZB': 1000, 'ZN': 1000, 'ZC': 50, 'ZS': 50, 'ZW': 50}
        multiplier = multiplier_map.get(root, 50)

        gex_by_strike = []
        total_gex = 0.0

        for strike in sorted(strike_data.keys()):
            sd = strike_data[strike]
            call_gamma = greeks_map.get(sd['call_sym'], {}).get('gamma', 0) if sd['call_sym'] else 0
            put_gamma = greeks_map.get(sd['put_sym'], {}).get('gamma', 0) if sd['put_sym'] else 0
            call_oi = oi_map.get(sd['call_sym'], 0) if sd['call_sym'] else 0
            put_oi = oi_map.get(sd['put_sym'], 0) if sd['put_sym'] else 0

            call_gex = call_gamma * call_oi * multiplier * (current_price ** 2) / 100
            put_gex = -put_gamma * put_oi * multiplier * (current_price ** 2) / 100
            net_gex = call_gex + put_gex

            gex_by_strike.append({
                'strike': strike,
                'call_gex': round(call_gex, 2),
                'put_gex': round(put_gex, 2),
                'net_gex': round(net_gex, 2),
                'call_oi': call_oi,
                'put_oi': put_oi,
            })
            total_gex += net_gex

        # Find zero-gamma level (gamma flip): the last negative-to-positive GEX
        # transition below current price, ignoring empty (zero-OI) strikes.
        # This represents where dealer positioning flips from amplifying to stabilizing.
        zero_gamma = 0
        active_strikes = [g for g in gex_by_strike if g['call_oi'] > 0 or g['put_oi'] > 0]
        lower_bound = current_price * 0.90 if current_price > 0 else 0
        for i in range(1, len(active_strikes)):
            strike = active_strikes[i]['strike']
            if strike < lower_bound or strike > current_price:
                continue
            if active_strikes[i-1]['net_gex'] < 0 and active_strikes[i]['net_gex'] > 0:
                zero_gamma = strike  # keep searching — want the LAST transition below price

        # Sum total OI
        total_call_oi = sum(g.get('call_oi', 0) for g in gex_by_strike)
        total_put_oi = sum(g.get('put_oi', 0) for g in gex_by_strike)

        return {
            'ticker': ticker,
            'expiration': target_exp.strftime('%Y-%m-%d'),
            'current_price': current_price,
            'total_gex': round(total_gex, 2),
            'total_call_oi': total_call_oi,
            'total_put_oi': total_put_oi,
            'gex_by_strike': gex_by_strike,
            'zero_gamma_level': zero_gamma,
            'days_to_expiry': dte,
            'source': 'tastytrade',
        }

    except Exception as e:
        logger.error(f"Error calculating GEX for {ticker}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {"error": str(e)}


async def get_gex_levels_tastytrade(ticker: str, expiration: str = None) -> Dict:
    """
    GEX Support/Resistance Wall Mapper for futures.
    Uses calculate_gex_tastytrade() then derives levels from the GEX data.
    """
    gex_data = await calculate_gex_tastytrade(ticker, expiration)
    if 'error' in gex_data:
        return gex_data

    current_price = gex_data.get('current_price', 0)
    gex_by_strike = gex_data.get('gex_by_strike', [])
    zero_gamma = gex_data.get('zero_gamma_level')

    if not gex_by_strike:
        return {"error": "No GEX data available", "ticker": ticker}

    call_wall = None
    put_wall = None
    max_call_gex = 0
    min_put_gex = 0
    magnet_zones = []
    acceleration_zones = []
    key_levels = []

    total_abs_gex = sum(abs(g['net_gex']) for g in gex_by_strike)
    significance_threshold = total_abs_gex * 0.05 if total_abs_gex > 0 else 0

    for g in gex_by_strike:
        strike = g['strike']
        net_gex = g['net_gex']
        call_gex = g['call_gex']
        put_gex = g['put_gex']

        if call_gex > max_call_gex:
            max_call_gex = call_gex
            call_wall = strike
        if put_gex < min_put_gex:
            min_put_gex = put_gex
            put_wall = strike

        if significance_threshold > 0:
            if net_gex > significance_threshold:
                magnet_zones.append(strike)
                level_type = 'magnet'
            elif net_gex < -significance_threshold:
                acceleration_zones.append(strike)
                level_type = 'acceleration'
            else:
                level_type = 'neutral'

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

    key_levels.sort(key=lambda x: abs(x['net_gex']), reverse=True)

    supports = [l for l in key_levels if l['strike'] < current_price and l['type'] == 'magnet']
    resistances = [l for l in key_levels if l['strike'] > current_price and l['type'] == 'magnet']
    nearest_support = max(supports, key=lambda x: x['strike']) if supports else None
    nearest_resistance = min(resistances, key=lambda x: x['strike']) if resistances else None

    # Interpretation
    parts = []
    if call_wall and current_price > 0:
        dist = ((call_wall - current_price) / current_price) * 100
        parts.append(f"Call wall at ${call_wall:.0f} ({dist:+.1f}%) - likely resistance")
    if put_wall and current_price > 0:
        dist = ((put_wall - current_price) / current_price) * 100
        parts.append(f"Put wall at ${put_wall:.0f} ({dist:+.1f}%) - likely support")
    if zero_gamma and current_price > 0:
        dist = ((zero_gamma - current_price) / current_price) * 100
        direction = "above" if zero_gamma > current_price else "below"
        parts.append(f"Gamma flip at ${zero_gamma:.0f} ({direction}, {abs(dist):.1f}% away)")
    interpretation = " | ".join(parts) if parts else "Insufficient data for interpretation"

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
        'key_levels': key_levels[:10],
        'magnet_zones': sorted(magnet_zones),
        'acceleration_zones': sorted(acceleration_zones),
        'total_gex': gex_data.get('total_gex', 0),
        'interpretation': interpretation
    }


async def get_gex_regime_tastytrade(ticker: str, expiration: str = None) -> Dict:
    """
    GEX Volatility Regime Classifier for futures.
    Uses calculate_gex_tastytrade() then derives regime from the GEX data.
    """
    gex_data = await calculate_gex_tastytrade(ticker, expiration)
    if 'error' in gex_data:
        return gex_data

    total_gex = gex_data.get('total_gex', 0)
    current_price = gex_data.get('current_price', 0)
    zero_gamma = gex_data.get('zero_gamma_level')
    gex_by_strike = gex_data.get('gex_by_strike', [])

    if current_price > 0:
        gex_normalized = total_gex / 1e9
    else:
        gex_normalized = 0

    # Thresholds scaled by price
    price_scale = (current_price / 500) ** 2 if current_price > 0 else 1
    POSITIVE_GEX_THRESHOLD = 2.5 * price_scale
    NEGATIVE_GEX_THRESHOLD = -1.5 * price_scale
    score_scale = 10 / price_scale if price_scale > 0 else 10

    if gex_normalized > POSITIVE_GEX_THRESHOLD:
        regime = 'pinned'
        regime_score = min(100, gex_normalized * score_scale)
        position_sizing = 1.0
        strategy_bias = 'mean_reversion'
        recommendation = 'Dealers will dampen moves. Fade breakouts, sell premium, buy dips.'
    elif gex_normalized < NEGATIVE_GEX_THRESHOLD:
        regime = 'volatile'
        regime_score = max(-100, gex_normalized * score_scale)
        position_sizing = 0.25
        strategy_bias = 'trend_following'
        recommendation = 'Dealers will amplify moves. Follow breakouts, buy premium for protection, reduce size.'
    else:
        regime = 'transitional'
        regime_score = gex_normalized * score_scale
        position_sizing = 0.5
        strategy_bias = 'neutral'
        recommendation = 'Gamma flip zone - highest uncertainty. Wait for clarity or reduce exposure.'

    flip_distance = None
    flip_distance_pct = None
    if zero_gamma and current_price > 0:
        flip_distance = zero_gamma - current_price
        flip_distance_pct = (flip_distance / current_price) * 100

    call_wall = None
    put_wall = None
    max_call_gex = 0
    min_put_gex = 0
    for g in gex_by_strike:
        if g['call_gex'] > max_call_gex:
            max_call_gex = g['call_gex']
            call_wall = g['strike']
        if g['put_gex'] < min_put_gex:
            min_put_gex = g['put_gex']
            put_wall = g['strike']

    confidence = min(abs(regime_score) / 100, 1.0)

    return {
        'ticker': ticker.upper(),
        'expiration': gex_data.get('expiration'),
        'current_price': current_price,
        'regime': regime,
        'regime_score': round(regime_score, 1),
        'confidence': round(confidence, 2),
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
        'is_futures': True
    }


async def get_combined_regime_tastytrade(ticker: str, expiration: str = None) -> Dict:
    """
    Combined GEX + P/C Ratio Regime for futures.
    Computes GEX data once and derives both regime and P/C from it.
    """
    # Get raw GEX data once (single streamer connection)
    gex_data = await calculate_gex_tastytrade(ticker, expiration)
    if 'error' in gex_data:
        return gex_data

    # Derive regime from the GEX data
    total_gex = gex_data.get('total_gex', 0)
    current_price = gex_data.get('current_price', 0)
    gex_normalized = total_gex / 1e9 if current_price > 0 else 0
    price_scale = (current_price / 500) ** 2 if current_price > 0 else 1
    POSITIVE_GEX_THRESHOLD = 2.5 * price_scale
    NEGATIVE_GEX_THRESHOLD = -1.5 * price_scale
    score_scale = 10 / price_scale if price_scale > 0 else 10

    if gex_normalized > POSITIVE_GEX_THRESHOLD:
        gex_regime_type = 'pinned'
        gex_score = min(100, gex_normalized * score_scale)
        strategy_bias = 'mean_reversion'
    elif gex_normalized < NEGATIVE_GEX_THRESHOLD:
        gex_regime_type = 'volatile'
        gex_score = max(-100, gex_normalized * score_scale)
        strategy_bias = 'trend_following'
    else:
        gex_regime_type = 'transitional'
        gex_score = gex_normalized * score_scale
        strategy_bias = 'neutral'

    # Derive P/C from OI
    total_call_oi = gex_data.get('total_call_oi', 0)
    total_put_oi = gex_data.get('total_put_oi', 0)
    pc_ratio = total_put_oi / total_call_oi if total_call_oi > 0 else 1.0

    HISTORICAL_MEAN = 0.95
    HISTORICAL_STD = 0.25
    pc_zscore = (pc_ratio - HISTORICAL_MEAN) / HISTORICAL_STD if HISTORICAL_STD > 0 else 0

    is_positive_gex = gex_regime_type == 'pinned'
    is_negative_gex = gex_regime_type == 'volatile'
    is_fear = pc_zscore > 1
    is_complacency = pc_zscore < -1

    if is_fear and is_positive_gex:
        combined_regime = 'opportunity'
        recommendation = 'BEST SETUP: Fear + dealer support. Aggressive entries, full size.'
        risk_level = 'low'
        position_multiplier = 1.25
    elif is_fear and is_negative_gex:
        combined_regime = 'danger'
        recommendation = 'DANGER ZONE: Fear + dealer amplification = crash risk. Reduce exposure.'
        risk_level = 'extreme'
        position_multiplier = 0.0
    elif is_complacency and is_positive_gex:
        combined_regime = 'melt_up'
        recommendation = 'Quiet melt-up. Normal trading, tighten stops.'
        risk_level = 'moderate'
        position_multiplier = 0.75
    elif is_complacency and is_negative_gex:
        combined_regime = 'high_risk'
        recommendation = 'MOST DANGEROUS: Complacency + negative GEX. Hedge or reduce.'
        risk_level = 'high'
        position_multiplier = 0.25
    else:
        combined_regime = f'neutral_{gex_regime_type}'
        # Preserve GEX-based position sizing when P/C is neutral
        gex_position_map = {'pinned': 1.0, 'volatile': 0.5, 'transitional': 0.75}
        position_multiplier = gex_position_map.get(gex_regime_type, 0.75)
        if gex_regime_type == 'volatile':
            recommendation = 'Negative GEX with neutral P/C. Reduce size, favor trend-following.'
            risk_level = 'high'
        elif gex_regime_type == 'pinned':
            recommendation = 'Positive GEX with neutral P/C. Normal trading, mean-reversion setups.'
            risk_level = 'low'
        else:
            recommendation = 'Gamma flip zone - highest uncertainty. Wait for clarity or reduce exposure.'
            risk_level = 'moderate'

    return {
        'ticker': ticker.upper(),
        'expiration': gex_data.get('expiration'),
        'current_price': current_price,
        'combined_regime': combined_regime,
        'gex_regime': gex_regime_type,
        'gex_score': round(gex_score, 1),
        'pc_ratio': round(pc_ratio, 3),
        'pc_zscore': round(pc_zscore, 2),
        'recommendation': recommendation,
        'risk_level': risk_level,
        'position_multiplier': position_multiplier,
        'position_sizing_label': f'{int(position_multiplier * 100)}% size',
        'strategy_bias': strategy_bias,
        'is_futures': True
    }


def get_futures_front_month_symbol(root_symbol: str) -> str:
    """
    Get the front month contract symbol for a futures root.
    E.g., /ES -> /ESH6 (March 2026)

    Month codes: F=Jan, G=Feb, H=Mar, J=Apr, K=May, M=Jun,
                 N=Jul, Q=Aug, U=Sep, V=Oct, X=Nov, Z=Dec
    """
    from datetime import date
    today = date.today()

    # ES, NQ, RTY, YM have quarterly expirations (H, M, U, Z = Mar, Jun, Sep, Dec)
    quarterly_futures = ['ES', 'NQ', 'RTY', 'YM', 'MES', 'MNQ']
    # CL, GC have monthly expirations
    monthly_codes = ['F', 'G', 'H', 'J', 'K', 'M', 'N', 'Q', 'U', 'V', 'X', 'Z']
    quarterly_codes = ['H', 'M', 'U', 'Z']  # Mar, Jun, Sep, Dec

    # Extract root without /
    root = root_symbol.lstrip('/')

    # Determine which month codes to use
    if root in quarterly_futures:
        codes = quarterly_codes
    else:
        codes = monthly_codes

    # Find next expiration month
    current_month = today.month
    current_year = today.year % 10  # Last digit of year

    # For quarterly, find next quarter
    if root in quarterly_futures:
        quarter_months = [3, 6, 9, 12]
        for qm in quarter_months:
            if current_month <= qm:
                month_code = quarterly_codes[quarter_months.index(qm)]
                year_digit = current_year if current_month <= qm else (current_year + 1) % 10
                return f"/{root}{month_code}{year_digit}"
        # Wrap to next year's March
        return f"/{root}H{(current_year + 1) % 10}"
    else:
        # Monthly - use next month
        next_month = current_month if today.day < 15 else (current_month % 12) + 1
        year_digit = current_year if next_month >= current_month else (current_year + 1) % 10
        month_code = monthly_codes[next_month - 1]
        return f"/{root}{month_code}{year_digit}"


def get_futures_streamer_symbol(session, root_symbol: str) -> Optional[str]:
    """
    Get the streamer symbol for a futures contract using Tastytrade API.
    This gets the active/front month contract's streamer symbol.
    """
    try:
        from tastytrade.instruments import Future

        # Get the front month contract symbol
        contract_symbol = get_futures_front_month_symbol(root_symbol)
        logger.info(f"Looking up futures contract: {contract_symbol}")

        # Get the futures instrument from Tastytrade
        futures = Future.get(session, [contract_symbol])
        if futures and len(futures) > 0:
            future = futures[0]
            streamer_sym = getattr(future, 'streamer_symbol', None)
            logger.info(f"Got futures streamer symbol: {streamer_sym} for {contract_symbol}")
            return streamer_sym
        else:
            logger.warning(f"No futures found for {contract_symbol}")
            return None
    except Exception as e:
        logger.error(f"Error getting futures streamer symbol for {root_symbol}: {e}")
        return None


def get_quote_tastytrade(ticker: str) -> Optional[Dict]:
    """
    Get current quote for a ticker.
    For futures like /ES, uses Future.get() to find the active contract's streamer symbol.
    """
    session = get_tastytrade_session()
    if not session:
        return None

    try:
        from tastytrade import DXLinkStreamer
        from tastytrade.dxfeed import Quote

        # For root futures symbols, get the proper streamer symbol from Tastytrade API
        quote_ticker = ticker
        if is_futures_ticker(ticker) and len(ticker) <= 4:  # /ES, /NQ, /CL, /GC
            streamer_sym = get_futures_streamer_symbol(session, ticker)
            if streamer_sym:
                quote_ticker = streamer_sym
                logger.info(f"Using streamer symbol {quote_ticker} for {ticker}")
            else:
                # Fallback to calculated front month
                quote_ticker = get_futures_front_month_symbol(ticker)
                logger.info(f"Fallback to front month {quote_ticker} for {ticker}")

        quote_data = {}

        async def fetch_quote():
            try:
                async with DXLinkStreamer(session) as streamer:
                    await streamer.subscribe(Quote, [quote_ticker])
                    import asyncio as aio
                    try:
                        async for quote in aio.wait_for(streamer.listen(Quote), timeout=5.0):
                            # Quote uses snake_case: bid_price, ask_price
                            bid = getattr(quote, 'bid_price', None) or getattr(quote, 'bidPrice', None)
                            ask = getattr(quote, 'ask_price', None) or getattr(quote, 'askPrice', None)
                            quote_data['bid'] = bid
                            quote_data['ask'] = ask
                            quote_data['last'] = (bid + ask) / 2 if bid and ask else None
                            quote_data['symbol'] = quote_ticker
                            logger.info(f"Got quote for {quote_ticker}: bid={bid}, ask={ask}")
                            break
                    except aio.TimeoutError:
                        logger.warning(f"Quote streaming timed out for {quote_ticker}")
            except Exception as e:
                logger.warning(f"Error in quote streaming for {quote_ticker}: {e}")

        try:
            asyncio.run(fetch_quote())
        except RuntimeError:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(fetch_quote())

        return quote_data if quote_data else None

    except Exception as e:
        logger.error(f"Error fetching Tastytrade quote for {ticker}: {e}")
        return None


async def get_iv_by_delta_tastytrade(ticker: str, expiration: str = None, target_dte: int = 120) -> Optional[Dict]:
    """
    Get IV at specific delta points for skew analysis.

    Returns:
        {
            'atm_iv': float (50 delta),
            'put_25d_iv': float (25 delta put),
            'put_10d_iv': float (10 delta put),
            'call_25d_iv': float (25 delta call),
            'skew_25d': float (put_25d_iv - atm_iv),
            'skew_ratio': float (put_25d_iv / atm_iv)
        }
    """
    data = await get_options_with_greeks_tastytrade(ticker, expiration, target_dte)
    if not data or not data.get('options'):
        return None

    options = data['options']

    # Find options by delta
    atm_iv = None
    put_25d_iv = None
    put_10d_iv = None
    call_25d_iv = None

    best_atm_diff = float('inf')
    best_25d_diff = float('inf')
    best_10d_diff = float('inf')
    best_call_25d_diff = float('inf')

    for opt in options:
        put = opt.get('put')
        call = opt.get('call')

        if put and put.get('delta') and put.get('iv'):
            # Convert to float in case of Decimal
            delta = float(put['delta'])
            iv = float(put['iv'])

            # ATM (~50 delta)
            diff = abs(delta - 0.50)
            if diff < best_atm_diff:
                best_atm_diff = diff
                atm_iv = iv

            # 25 delta put
            diff = abs(delta - 0.25)
            if diff < best_25d_diff:
                best_25d_diff = diff
                put_25d_iv = iv

            # 10 delta put
            diff = abs(delta - 0.10)
            if diff < best_10d_diff:
                best_10d_diff = diff
                put_10d_iv = iv

        if call and call.get('delta') and call.get('iv'):
            # Convert to float in case of Decimal
            delta = float(call['delta'])
            iv = float(call['iv'])

            # 25 delta call
            diff = abs(delta - 0.25)
            if diff < best_call_25d_diff:
                best_call_25d_diff = diff
                call_25d_iv = iv

    if not atm_iv:
        return None

    return {
        'ticker': ticker.upper(),
        'expiration': data.get('expiration'),
        'dte': data.get('dte'),
        'atm_iv': atm_iv,
        'atm_iv_pct': round(atm_iv * 100, 1) if atm_iv else None,
        'put_25d_iv': put_25d_iv,
        'put_25d_iv_pct': round(put_25d_iv * 100, 1) if put_25d_iv else None,
        'put_10d_iv': put_10d_iv,
        'put_10d_iv_pct': round(put_10d_iv * 100, 1) if put_10d_iv else None,
        'call_25d_iv': call_25d_iv,
        'skew_25d': round((put_25d_iv - atm_iv) * 100, 2) if put_25d_iv and atm_iv else None,
        'skew_ratio': round(put_25d_iv / atm_iv, 3) if put_25d_iv and atm_iv else None,
        'source': 'tastytrade'
    }


async def get_term_structure_tastytrade(ticker: str, front_dte: int = 30, back_dte: int = 120) -> Optional[Dict]:
    """
    Get IV term structure comparing front and back month ATM IVs.

    Args:
        ticker: Stock symbol
        front_dte: Target DTE for front month (default 30)
        back_dte: Target DTE for back month (default 120)

    Returns:
        {
            'front_iv': float,
            'front_dte': int,
            'back_iv': float,
            'back_dte': int,
            'slope': float (back_iv - front_iv) / back_iv,
            'structure': 'contango' | 'backwardation' | 'flat'
        }
    """
    # Get front month IV
    front_data = await get_iv_by_delta_tastytrade(ticker, target_dte=front_dte)
    if not front_data or not front_data.get('atm_iv'):
        return None

    # Get back month IV
    back_data = await get_iv_by_delta_tastytrade(ticker, target_dte=back_dte)
    if not back_data or not back_data.get('atm_iv'):
        return None

    front_iv = float(front_data['atm_iv'])
    back_iv = float(back_data['atm_iv'])

    # Calculate slope
    slope = (back_iv - front_iv) / back_iv if back_iv > 0 else 0
    slope_pct = slope * 100

    # Determine structure
    if slope > 0.05:
        structure = 'contango'
        signal = 'normal'
    elif slope < -0.05:
        structure = 'backwardation'
        signal = 'inverted'
    else:
        structure = 'flat'
        signal = 'neutral'

    return {
        'ticker': ticker.upper(),
        'front_expiration': front_data.get('expiration'),
        'front_dte': front_data.get('dte'),
        'front_iv': front_iv,
        'front_iv_pct': round(front_iv * 100, 1),
        'back_expiration': back_data.get('expiration'),
        'back_dte': back_data.get('dte'),
        'back_iv': back_iv,
        'back_iv_pct': round(back_iv * 100, 1),
        'slope': round(slope, 4),
        'slope_pct': round(slope_pct, 1),
        'structure': structure,
        'signal': signal,
        'source': 'tastytrade'
    }


async def get_expected_move_tastytrade(ticker: str, target_dte: int = 120) -> Optional[Dict]:
    """
    Calculate expected move for a specific DTE.

    Uses ATM straddle price × 0.85 for expected move.
    """
    data = await get_options_with_greeks_tastytrade(ticker, target_dte=target_dte)
    if not data or not data.get('options'):
        return None

    # Get current price
    quote = get_quote_tastytrade(ticker)
    current_price = quote.get('last') if quote else None

    if not current_price:
        # Estimate from options
        for opt in data['options']:
            if opt.get('call') and opt.get('put'):
                # Use put-call parity estimate
                current_price = float(opt['strike'])
                break

    if not current_price:
        return None

    current_price = float(current_price)

    # Find ATM strike
    atm_strike = None
    atm_call_price = None
    atm_put_price = None
    best_diff = float('inf')

    for opt in data['options']:
        strike = float(opt['strike'])
        diff = abs(strike - current_price)
        if diff < best_diff:
            best_diff = diff
            atm_strike = strike
            if opt.get('call') and opt['call'].get('price'):
                atm_call_price = float(opt['call']['price'])
            if opt.get('put') and opt['put'].get('price'):
                atm_put_price = float(opt['put']['price'])

    if not atm_call_price or not atm_put_price:
        return None

    straddle_price = atm_call_price + atm_put_price
    expected_move = straddle_price * 0.85
    expected_move_pct = (expected_move / current_price) * 100

    return {
        'ticker': ticker.upper(),
        'current_price': round(current_price, 2),
        'expiration': data.get('expiration'),
        'dte': data.get('dte'),
        'atm_strike': atm_strike,
        'call_price': round(atm_call_price, 2),
        'put_price': round(atm_put_price, 2),
        'straddle_price': round(straddle_price, 2),
        'expected_move': round(expected_move, 2),
        'expected_move_pct': round(expected_move_pct, 2),
        'upper_expected': round(current_price + expected_move, 2),
        'lower_expected': round(current_price - expected_move, 2),
        'lower_1_5x_em': round(current_price - (expected_move * 1.5), 2),
        'lower_2x_em': round(current_price - (expected_move * 2), 2),
        'source': 'tastytrade'
    }


async def compute_market_xray(ticker: str, expiration: str = None) -> Dict:
    """Market X-Ray: institutional edge scanner combining 6 derived signal modules."""
    cache_key = (ticker.upper(), expiration)
    cached = _xray_cache.get(cache_key)
    if cached and (_time.time() - cached['ts']) < _XRAY_CACHE_TTL:
        return cached['result']
    if cache_key not in _xray_locks:
        _xray_locks[cache_key] = asyncio.Lock()
    async with _xray_locks[cache_key]:
        cached = _xray_cache.get(cache_key)
        if cached and (_time.time() - cached['ts']) < _XRAY_CACHE_TTL:
            return cached['result']
        result = await _compute_market_xray_impl(ticker, expiration)
        if 'error' not in result:
            _xray_cache[cache_key] = {'result': result, 'ts': _time.time()}
        return result


async def _xray_fetch_quote(ticker: str) -> Optional[float]:
    """Fetch current price via Tastytrade REST API (no streaming needed)."""
    try:
        session = get_tastytrade_session()
        if not session:
            return None
        from tastytrade.market_data import get_market_data
        from tastytrade.order import InstrumentType
        if is_futures_ticker(ticker):
            sym = get_futures_streamer_symbol(session, ticker) or get_futures_front_month_symbol(ticker)
            md = await get_market_data(session, sym, InstrumentType.FUTURE)
        else:
            md = await get_market_data(session, ticker.upper(), InstrumentType.EQUITY)
        if md:
            for attr in ('mark', 'last', 'mid', 'close', 'prev_close', 'day_close'):
                val = getattr(md, attr, None)
                if val is not None and float(val) > 0:
                    logger.info(f"X-Ray price for {ticker} from REST ({attr}): {val}")
                    return float(val)
    except Exception as e:
        logger.warning(f"X-Ray REST quote failed for {ticker}: {e}")
    return None


async def _compute_market_xray_impl(ticker: str, expiration: str = None) -> Dict:
    """Internal implementation of Market X-Ray (not cached)."""
    try:
        # Fetch all data in parallel (including live quote)
        chain, gex, maxpain, gex_levels, iv_delta, term, em, live_price = await asyncio.gather(
            get_options_with_greeks_tastytrade(ticker, expiration),
            calculate_gex_tastytrade(ticker, expiration),
            calculate_max_pain_tastytrade(ticker, expiration),
            get_gex_levels_tastytrade(ticker, expiration),
            get_iv_by_delta_tastytrade(ticker, expiration),
            get_term_structure_tastytrade(ticker),
            get_expected_move_tastytrade(ticker),
            _xray_fetch_quote(ticker),
            return_exceptions=True
        )

        # Handle exceptions from gather
        if isinstance(chain, Exception) or chain is None:
            return {'error': f'Failed to fetch options chain: {chain}', 'ticker': ticker}
        if isinstance(gex, Exception):
            gex = None
        if isinstance(maxpain, Exception):
            maxpain = None
        if isinstance(gex_levels, Exception):
            gex_levels = None
        if isinstance(iv_delta, Exception):
            iv_delta = None
        if isinstance(term, Exception):
            term = None
        if isinstance(em, Exception):
            em = None
        if isinstance(live_price, Exception):
            live_price = None

        # Determine current price — try multiple sources
        current_price = None
        # 1) Live quote (most reliable)
        if live_price and live_price > 0:
            current_price = float(live_price)
        # 2) GEX current_price
        if not current_price and gex and isinstance(gex, dict) and gex.get('current_price'):
            current_price = float(gex['current_price'])
        # 3) Expected move current_price
        if not current_price and em and isinstance(em, dict) and em.get('current_price'):
            current_price = float(em['current_price'])
        # 4) ATM strike from chain — multiple strategies
        if not current_price:
            options_list = chain.get('options', [])
            # 4a) Put-call parity: strike where |call_price - put_price| is smallest
            best_atm = None
            best_diff = float('inf')
            for o in options_list:
                call = o.get('call')
                put = o.get('put')
                if call and put and call.get('price') and put.get('price'):
                    cp = float(call['price'])
                    pp = float(put['price'])
                    if cp > 0 and pp > 0:
                        diff = abs(cp - pp)
                        if diff < best_diff:
                            best_diff = diff
                            best_atm = float(o['strike'])
            if best_atm and best_atm > 0:
                current_price = best_atm
                logger.info(f"X-Ray price from put-call parity: {current_price}")
        if not current_price:
            # 4b) Delta-based: strike where call delta ≈ 0.5
            options_list = chain.get('options', [])
            best_atm = None
            best_diff = float('inf')
            for o in options_list:
                call = o.get('call')
                if call and call.get('delta') is not None:
                    diff = abs(abs(float(call['delta'])) - 0.5)
                    if diff < best_diff:
                        best_diff = diff
                        best_atm = float(o['strike'])
            if best_atm and best_atm > 0:
                current_price = best_atm
                logger.info(f"X-Ray price from delta: {current_price}")

        if not current_price or current_price <= 0:
            return {'error': 'Could not determine current price', 'ticker': ticker}

        # Get expiration and DTE from chain
        expiration_used = chain.get('expiration')
        dte = chain.get('dte')

        # Determine futures multiplier
        is_futures = ticker.startswith('/')
        if is_futures:
            root = ticker.lstrip('/').split(':')[0].upper()
            multiplier_map = {
                'ES': 50, 'MES': 5, 'NQ': 20, 'MNQ': 2, 'YM': 5, 'RTY': 50,
                'CL': 1000, 'NG': 10000, 'GC': 100, 'SI': 5000, 'HG': 25000,
                'ZB': 1000, 'ZN': 1000, 'ZC': 50, 'ZS': 50, 'ZW': 50
            }
            multiplier = multiplier_map.get(root, 50)
        else:
            multiplier = 100

        options = chain.get('options', [])
        gex_by_strike = gex.get('gex_by_strike', []) if gex and isinstance(gex, dict) else []
        total_gex = gex.get('total_gex', 0) if gex and isinstance(gex, dict) else 0

        # Check if tastytrade GEX data is usable (non-zero)
        gex_usable = gex_by_strike and any(abs(g.get('net_gex', 0)) > 0 for g in gex_by_strike)

        # Fallback to Polygon for equities when tastytrade GEX is empty/zero
        if not is_futures and not gex_usable:
            try:
                from src.data.options import calculate_gex_by_strike, get_gex_levels

                poly_gex = calculate_gex_by_strike(ticker, expiration_used)
                if poly_gex and 'error' not in poly_gex:
                    gex_by_strike = poly_gex.get('gex_by_strike', [])
                    total_gex = poly_gex.get('total_gex', 0) or 0
                    logger.info(f"X-Ray: Using Polygon GEX fallback for {ticker} ({len(gex_by_strike)} strikes)")

                poly_levels = get_gex_levels(ticker, expiration_used)
                if poly_levels and 'error' not in poly_levels:
                    gex_levels = poly_levels
                    logger.info(f"X-Ray: Using Polygon GEX levels fallback for {ticker}")
            except Exception as e:
                logger.warning(f"Polygon GEX fallback failed for {ticker}: {e}")

        # Check if max pain is usable
        mp_usable = (maxpain and isinstance(maxpain, dict) and
                     (maxpain.get('max_pain_price') or maxpain.get('max_pain_strike') or maxpain.get('max_pain')))

        if not is_futures and not mp_usable:
            try:
                from src.data.options import calculate_max_pain

                poly_mp = calculate_max_pain(ticker, expiration_used)
                if poly_mp and 'error' not in poly_mp:
                    maxpain = poly_mp
                    logger.info(f"X-Ray: Using Polygon max pain fallback for {ticker}")
            except Exception as e:
                logger.warning(f"Polygon max pain fallback failed for {ticker}: {e}")

        # =====================================================================
        # MODULE 1 - DEALER HEDGING FLOW MAP
        # =====================================================================
        dealer_flow = _xray_dealer_flow(current_price, gex_by_strike)

        # =====================================================================
        # MODULE 2 - GAMMA SQUEEZE / PIN RISK
        # =====================================================================
        squeeze_pin = _xray_squeeze_pin(current_price, options, gex_by_strike, total_gex, dte)

        # =====================================================================
        # MODULE 3 - VOLATILITY SURFACE DISTORTION
        # =====================================================================
        vol_surface = _xray_vol_surface(options, iv_delta, term)

        # =====================================================================
        # MODULE 4 - SMART MONEY FOOTPRINT
        # =====================================================================
        smart_money = _xray_smart_money(options, multiplier)

        # =====================================================================
        # MODULE 5 - OPTIMAL TRADE ZONES
        # =====================================================================
        trade_zones = _xray_trade_zones(current_price, maxpain, gex_levels, gex, iv_delta, dte)

        # =====================================================================
        # MODULE 6 - COMPOSITE EDGE SCORE
        # =====================================================================
        composite = _xray_composite(
            total_gex, squeeze_pin, smart_money, current_price,
            maxpain, vol_surface, term, trade_zones, dte,
            options=options, expiration=expiration_used, iv_delta=iv_delta
        )

        return {
            'ticker': ticker.upper(),
            'expiration': expiration_used,
            'current_price': current_price,
            'dte': dte,
            'dealer_flow': dealer_flow,
            'squeeze_pin': squeeze_pin,
            'vol_surface': vol_surface,
            'smart_money': smart_money,
            'trade_zones': trade_zones,
            'composite': composite,
            'source': 'tastytrade',
            'timestamp': datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error computing Market X-Ray for {ticker}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {'error': str(e), 'ticker': ticker}


def _xray_dealer_flow(current_price: float, gex_by_strike: list) -> Dict:
    """MODULE 1: Dealer Hedging Flow Map."""
    levels = []
    air_pockets = []

    # Build price grid: 0.95x to 1.05x in 0.5% steps (21 levels)
    price_levels = [current_price * (0.95 + i * 0.005) for i in range(21)]

    for price in price_levels:
        # Find closest strike's net_gex
        closest_gex = 0
        closest_dist = float('inf')
        for g in gex_by_strike:
            dist = abs(float(g['strike']) - price)
            if dist < closest_dist:
                closest_dist = dist
                closest_gex = float(g.get('net_gex', 0))

        regime = 'stabilizing' if closest_gex >= 0 else 'amplifying'
        levels.append({
            'price': round(price, 2),
            'gex_value': round(closest_gex, 2),
            'regime': regime
        })

    # Find air pockets: consecutive negative GEX below current price
    below_levels = [l for l in levels if l['price'] < current_price]
    pocket_start = None
    for lv in below_levels:
        if lv['regime'] == 'amplifying':
            if pocket_start is None:
                pocket_start = lv['price']
        else:
            if pocket_start is not None:
                air_pockets.append({
                    'from_price': round(pocket_start, 2),
                    'to_price': round(lv['price'], 2)
                })
                pocket_start = None
    # Close any open pocket at the bottom
    if pocket_start is not None and below_levels:
        air_pockets.append({
            'from_price': round(pocket_start, 2),
            'to_price': round(below_levels[-1]['price'], 2)
        })

    return {
        'levels': levels,
        'air_pockets': air_pockets,
        'current_price': current_price
    }


def _xray_squeeze_pin(current_price: float, options: list, gex_by_strike: list,
                       total_gex: float, dte) -> Dict:
    """MODULE 2: Gamma Squeeze / Pin Risk."""
    # ATM range: within 2% of current price
    atm_range = current_price * 0.02
    atm_options = [o for o in options if abs(float(o['strike']) - current_price) <= atm_range]

    # --- Squeeze Score ---
    call_gamma_sum = 0
    put_gamma_sum = 0
    call_vol_sum = 0
    put_vol_sum = 0
    call_oi_sum = 0
    put_oi_sum = 0
    max_call_gamma_strike = None
    max_call_gamma_val = 0
    max_put_gamma_strike = None
    max_put_gamma_val = 0

    for o in atm_options:
        call = o.get('call')
        put = o.get('put')
        strike = float(o['strike'])

        if call:
            cg = float(call.get('gamma', 0) or 0)
            cv = float(call.get('volume', 0) or 0)
            co = float(call.get('open_interest', 0) or 0)
            call_gamma_sum += cg
            call_vol_sum += cv
            call_oi_sum += co
            if cg > max_call_gamma_val:
                max_call_gamma_val = cg
                max_call_gamma_strike = strike

        if put:
            pg = float(put.get('gamma', 0) or 0)
            pv = float(put.get('volume', 0) or 0)
            po = float(put.get('open_interest', 0) or 0)
            put_gamma_sum += pg
            put_vol_sum += pv
            put_oi_sum += po
            if pg > max_put_gamma_val:
                max_put_gamma_val = pg
                max_put_gamma_strike = strike

    call_vol_oi_ratio = call_vol_sum / max(call_oi_sum, 1)
    put_vol_oi_ratio = put_vol_sum / max(put_oi_sum, 1)

    # Check negative GEX below/above current price
    neg_gex_below = any(
        float(g.get('net_gex', 0)) < 0 and float(g['strike']) < current_price
        for g in gex_by_strike
    )
    neg_gex_above = any(
        float(g.get('net_gex', 0)) < 0 and float(g['strike']) > current_price
        for g in gex_by_strike
    )

    # Normalize gamma concentration (0-1 scale)
    call_gamma_conc = min(1.0, call_gamma_sum / max(0.001, call_gamma_sum + put_gamma_sum))
    put_gamma_conc = min(1.0, put_gamma_sum / max(0.001, call_gamma_sum + put_gamma_sum))

    squeeze_up = min(100, int(
        call_gamma_conc * 30 +
        min(1.0, call_vol_oi_ratio) * 40 +
        (30 if neg_gex_below else 0)
    ))
    squeeze_down = min(100, int(
        put_gamma_conc * 30 +
        min(1.0, put_vol_oi_ratio) * 40 +
        (30 if neg_gex_above else 0)
    ))

    squeeze_score = max(squeeze_up, squeeze_down)
    squeeze_direction = 'up' if squeeze_up > squeeze_down else 'down'
    squeeze_trigger = max_call_gamma_strike if squeeze_direction == 'up' else max_put_gamma_strike

    # --- Pin Score ---
    pin_range = current_price * 0.03
    nearby_options = [o for o in options if abs(float(o['strike']) - current_price) <= pin_range]

    max_total_oi = 0
    pin_strike = None
    oi_values = []

    for o in nearby_options:
        call_oi = float((o.get('call') or {}).get('open_interest', 0) or 0)
        put_oi = float((o.get('put') or {}).get('open_interest', 0) or 0)
        total_oi = call_oi + put_oi
        oi_values.append(total_oi)
        if total_oi > max_total_oi:
            max_total_oi = total_oi
            pin_strike = float(o['strike'])

    avg_oi = sum(oi_values) / max(len(oi_values), 1)
    max_oi_concentration = min(1.0, max_total_oi / max(avg_oi, 1))

    dte_val = float(dte) if dte else 0
    dte_factor = max(0, 1 - dte_val / 7) if dte_val > 0 else 0
    positive_gex_factor = min(1, max(0, total_gex / 1e8)) if total_gex > 0 else 0

    pin_score = min(100, int(
        max_oi_concentration * 40 +
        dte_factor * 40 +
        positive_gex_factor * 20
    ))

    # Explanation
    parts = []
    if squeeze_score >= 60:
        parts.append(f"High squeeze potential {squeeze_direction} (score: {squeeze_score})")
    elif squeeze_score >= 30:
        parts.append(f"Moderate squeeze risk {squeeze_direction} (score: {squeeze_score})")
    else:
        parts.append(f"Low squeeze risk (score: {squeeze_score})")
    if pin_score >= 60:
        parts.append(f"Strong pin at {pin_strike} (score: {pin_score})")
    elif pin_score >= 30:
        parts.append(f"Moderate pin risk at {pin_strike} (score: {pin_score})")
    else:
        parts.append(f"Low pin risk (score: {pin_score})")

    return {
        'squeeze_score': squeeze_score,
        'squeeze_direction': squeeze_direction,
        'squeeze_trigger_price': squeeze_trigger,
        'pin_score': pin_score,
        'pin_strike': pin_strike,
        'dte': dte,
        'explanation': ' | '.join(parts)
    }


def _xray_vol_surface(options: list, iv_delta, term) -> Dict:
    """MODULE 3: Volatility Surface Distortion."""
    # Skew
    skew_25d = None
    skew_label = 'unknown'
    if iv_delta and isinstance(iv_delta, dict):
        p25 = iv_delta.get('put_25d_iv')
        c25 = iv_delta.get('call_25d_iv')
        if p25 is not None and c25 is not None:
            skew_25d = float(p25) - float(c25)
            if skew_25d > 0.05:
                skew_label = 'steep'
            elif skew_25d < 0.01:
                skew_label = 'flat'
            else:
                skew_label = 'normal'

    # Term structure
    term_structure = None
    term_signal = 'unknown'
    if term and isinstance(term, dict):
        term_structure = term.get('structure')
        term_signal = term.get('signal', 'unknown')

    # Cheapest gamma and richest theta from chain
    gamma_theta_entries = []
    for o in options:
        for opt_type in ['call', 'put']:
            leg = o.get(opt_type)
            if not leg:
                continue
            gamma = float(leg.get('gamma', 0) or 0)
            theta = float(leg.get('theta', 0) or 0)
            if gamma > 0 and theta != 0:
                ratio = abs(theta) / max(gamma, 0.0001)
                gamma_theta_entries.append({
                    'strike': float(o['strike']),
                    'theta': theta,
                    'gamma': gamma,
                    'ratio': round(ratio, 4),
                    'type': opt_type
                })

    # Sort ascending for cheapest gamma (lowest theta/gamma ratio)
    sorted_asc = sorted(gamma_theta_entries, key=lambda x: x['ratio'])
    cheapest_gamma = sorted_asc[:3]

    # Sort descending for richest theta (highest theta/gamma ratio)
    sorted_desc = sorted(gamma_theta_entries, key=lambda x: x['ratio'], reverse=True)
    richest_theta = sorted_desc[:3]

    return {
        'skew_25d': round(skew_25d, 4) if skew_25d is not None else None,
        'skew_label': skew_label,
        'term_structure': term_structure,
        'term_signal': term_signal,
        'cheapest_gamma': cheapest_gamma,
        'richest_theta': richest_theta
    }


def _xray_smart_money(options: list, multiplier: int) -> Dict:
    """MODULE 4: Smart Money Footprint."""
    fresh_positions = []
    oi_by_strike = {}
    call_notionals = {}
    put_notionals = {}
    total_call_notional = 0.0
    total_put_notional = 0.0

    for o in options:
        strike = float(o['strike'])
        call = o.get('call')
        put = o.get('put')
        call_oi = 0
        put_oi = 0

        if call:
            c_vol = float(call.get('volume', 0) or 0)
            c_oi = float(call.get('open_interest', 0) or 0)
            c_price = float(call.get('price', 0) or 0)
            call_oi = c_oi
            c_notional = c_vol * c_price * multiplier
            total_call_notional += c_notional
            call_notionals[strike] = c_notional
            if c_oi > 0 and c_vol / max(c_oi, 1) > 2.0:
                fresh_positions.append({
                    'type': 'call',
                    'strike': strike,
                    'volume': c_vol,
                    'oi': c_oi,
                    'ratio': round(c_vol / max(c_oi, 1), 2),
                    'notional': round(c_notional, 2)
                })

        if put:
            p_vol = float(put.get('volume', 0) or 0)
            p_oi = float(put.get('open_interest', 0) or 0)
            p_price = float(put.get('price', 0) or 0)
            put_oi = p_oi
            p_notional = p_vol * p_price * multiplier
            total_put_notional += p_notional
            put_notionals[strike] = p_notional
            if p_oi > 0 and p_vol / max(p_oi, 1) > 2.0:
                fresh_positions.append({
                    'type': 'put',
                    'strike': strike,
                    'volume': p_vol,
                    'oi': p_oi,
                    'ratio': round(p_vol / max(p_oi, 1), 2),
                    'notional': round(p_notional, 2)
                })

        oi_by_strike[strike] = call_oi + put_oi

    # OI Walls: strikes where OI > 3x average of 10 neighbors
    sorted_strikes = sorted(oi_by_strike.keys())
    oi_walls = []
    for i, strike in enumerate(sorted_strikes):
        total_oi = oi_by_strike[strike]
        if total_oi == 0:
            continue
        # Get 5 above and 5 below
        start = max(0, i - 5)
        end = min(len(sorted_strikes), i + 6)
        neighbors = [oi_by_strike[sorted_strikes[j]] for j in range(start, end) if j != i]
        avg_neighbor_oi = sum(neighbors) / max(len(neighbors), 1)
        if avg_neighbor_oi > 0 and total_oi > 3 * avg_neighbor_oi:
            oi_walls.append({
                'strike': strike,
                'total_oi': total_oi,
                'avg_neighbor_oi': round(avg_neighbor_oi, 0)
            })

    # Sort and limit
    fresh_positions.sort(key=lambda x: x.get('notional', 0), reverse=True)
    oi_walls.sort(key=lambda x: x.get('total_oi', 0), reverse=True)

    net_flow = 'bullish' if total_call_notional > total_put_notional else 'bearish'

    return {
        'net_flow': net_flow,
        'total_call_notional': round(total_call_notional, 2),
        'total_put_notional': round(total_put_notional, 2),
        'fresh_positions': fresh_positions[:5],
        'oi_walls': oi_walls[:5]
    }


def _xray_trade_zones(current_price: float, maxpain, gex_levels, gex, iv_delta, dte) -> Dict:
    """MODULE 5: Optimal Trade Zones."""
    # Max pain
    max_pain_price = None
    if maxpain and isinstance(maxpain, dict):
        max_pain_price = maxpain.get('max_pain_price') or maxpain.get('max_pain_strike') or maxpain.get('max_pain')

    dte_val = float(dte) if dte else 0
    max_pain_pull = 1 / (1 + dte_val / 7) if dte_val > 0 else 0

    # Support / Resistance from GEX levels
    support = None
    resistance = None
    gamma_flip = None
    if gex_levels and isinstance(gex_levels, dict):
        support = gex_levels.get('put_wall') or gex_levels.get('nearest_support')
        resistance = gex_levels.get('call_wall') or gex_levels.get('nearest_resistance')
        gamma_flip = gex_levels.get('gamma_flip')
    if gamma_flip is None and gex and isinstance(gex, dict):
        gamma_flip = gex.get('zero_gamma_level')

    # Expected move bands using asymmetric IV
    upper_1sd = None
    lower_1sd = None
    upper_2sd = None
    lower_2sd = None
    if iv_delta and isinstance(iv_delta, dict) and current_price and dte_val > 0:
        atm_iv_fallback = float(iv_delta.get('atm_iv', 0.3) or 0.3)
        put_iv = float(iv_delta.get('put_25d_iv') or atm_iv_fallback)
        call_iv = float(iv_delta.get('call_25d_iv') or atm_iv_fallback)
        t = dte_val / 365.0
        em_down_1sd = current_price * put_iv * (t ** 0.5)
        em_up_1sd = current_price * call_iv * (t ** 0.5)
        upper_1sd = round(current_price + em_up_1sd, 2)
        lower_1sd = round(current_price - em_down_1sd, 2)
        upper_2sd = round(current_price + 2 * em_up_1sd, 2)
        lower_2sd = round(current_price - 2 * em_down_1sd, 2)

    return {
        'current_price': current_price,
        'max_pain': max_pain_price,
        'max_pain_pull': round(max_pain_pull, 4),
        'support': support,
        'resistance': resistance,
        'gamma_flip': gamma_flip,
        'upper_1sd': upper_1sd,
        'lower_1sd': lower_1sd,
        'upper_2sd': upper_2sd,
        'lower_2sd': lower_2sd
    }


def _bs_price(S, K, T, sigma, opt_type, r=0.045):
    """Black-Scholes option price. S=spot, K=strike, T=years, sigma=IV, r=risk-free."""
    if S <= 0 or K <= 0:
        return 0.0
    if T <= 0 or sigma <= 0:
        if opt_type == 'call':
            return max(0.0, S - K)
        return max(0.0, K - S)
    sqrt_T = math.sqrt(T)
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * sqrt_T)
    d2 = d1 - sigma * sqrt_T
    nd1 = 0.5 * (1 + math.erf(d1 / math.sqrt(2)))
    nd2 = 0.5 * (1 + math.erf(d2 / math.sqrt(2)))
    if opt_type == 'call':
        return S * nd1 - K * math.exp(-r * T) * nd2
    else:
        return K * math.exp(-r * T) * (1 - nd2) - S * (1 - nd1)


def _xray_composite(total_gex: float, squeeze_pin: Dict, smart_money: Dict,
                     current_price: float, maxpain, vol_surface: Dict,
                     term, trade_zones: Dict, dte: int = None,
                     options: list = None, expiration: str = None,
                     iv_delta: Dict = None) -> Dict:
    """MODULE 6: Composite Edge Score (0-100)."""
    factors = []

    # 1. Dealer flow score (weight=20)
    dealer_flow_score = 70 if total_gex > 0 else 30
    factors.append({'name': 'dealer_flow', 'score': dealer_flow_score, 'weight': 20,
                    'contribution': round(dealer_flow_score * 20 / 100, 2)})

    # 2. Squeeze score (weight=15)
    sq_dir = squeeze_pin.get('squeeze_direction', 'up')
    sq_up = squeeze_pin.get('squeeze_score', 50)
    # Infer squeeze_down vs squeeze_up
    squeeze_score_adj = 70 if sq_dir == 'up' else 30
    if sq_up == 0:
        squeeze_score_adj = 50
    factors.append({'name': 'squeeze', 'score': squeeze_score_adj, 'weight': 15,
                    'contribution': round(squeeze_score_adj * 15 / 100, 2)})

    # 3. Smart money score (weight=20)
    total_call = smart_money.get('total_call_notional', 0)
    total_put = smart_money.get('total_put_notional', 0)
    total_flow = total_call + total_put
    if total_flow > 0 and total_call > total_put:
        smart_money_score = 50 + 50 * min(1, (total_call - total_put) / total_flow)
    elif total_flow > 0:
        smart_money_score = 50 - 50 * min(1, (total_put - total_call) / total_flow)
    else:
        smart_money_score = 50
    smart_money_score = round(smart_money_score)
    factors.append({'name': 'smart_money', 'score': smart_money_score, 'weight': 20,
                    'contribution': round(smart_money_score * 20 / 100, 2)})

    # 4. Price vs max pain (weight=10)
    max_pain_price = None
    if maxpain and isinstance(maxpain, dict):
        max_pain_price = maxpain.get('max_pain_price') or maxpain.get('max_pain_strike') or maxpain.get('max_pain')
    if max_pain_price and current_price:
        mp = float(max_pain_price)
        if current_price < mp:
            # Price below max pain -> pull up -> bullish
            maxpain_score = 60 + 40 * min(1, (mp - current_price) / (current_price * 0.03))
        else:
            # Price above max pain -> pull down -> bearish
            maxpain_score = 40 - 40 * min(1, (current_price - mp) / (current_price * 0.03))
            maxpain_score = max(0, maxpain_score)
    else:
        maxpain_score = 50
    maxpain_score = round(maxpain_score)
    factors.append({'name': 'price_vs_maxpain', 'score': maxpain_score, 'weight': 10,
                    'contribution': round(maxpain_score * 10 / 100, 2)})

    # 5. Skew score (weight=10)
    skew_val = vol_surface.get('skew_25d')
    if skew_val is not None:
        if 0.01 <= skew_val <= 0.05:
            skew_score = 70  # normal
        elif skew_val > 0.05:
            skew_score = 40  # steep / panic
        else:
            skew_score = 50  # flat
    else:
        skew_score = 50
    factors.append({'name': 'skew', 'score': skew_score, 'weight': 10,
                    'contribution': round(skew_score * 10 / 100, 2)})

    # 6. Term structure score (weight=10)
    term_struct = None
    if term and isinstance(term, dict):
        term_struct = term.get('structure')
    if term_struct == 'contango':
        term_score = 75
    elif term_struct == 'backwardation':
        term_score = 25
    else:
        term_score = 50
    factors.append({'name': 'term', 'score': term_score, 'weight': 10,
                    'contribution': round(term_score * 10 / 100, 2)})

    # 7. Wall score (weight=15)
    support = trade_zones.get('support')
    resistance = trade_zones.get('resistance')
    if support and resistance and current_price:
        dist_support = abs(current_price - float(support))
        dist_resistance = abs(float(resistance) - current_price)
        total_dist = dist_support + dist_resistance
        wall_score = round(dist_support / max(total_dist, 0.01) * 100) if total_dist > 0 else 50
    else:
        wall_score = 50
    factors.append({'name': 'price_vs_walls', 'score': wall_score, 'weight': 15,
                    'contribution': round(wall_score * 15 / 100, 2)})

    # Composite
    composite_score = sum(f['contribution'] for f in factors)
    composite_score = round(min(100, max(0, composite_score)))

    # Label
    if composite_score >= 75:
        label = 'STRONG BULLISH'
    elif composite_score >= 60:
        label = 'BULLISH'
    elif composite_score >= 45:
        label = 'NEUTRAL'
    elif composite_score >= 30:
        label = 'BEARISH'
    else:
        label = 'STRONG BEARISH'

    interpretation_parts = []
    if dealer_flow_score >= 50:
        interpretation_parts.append('Positive dealer gamma (stabilizing)')
    else:
        interpretation_parts.append('Negative dealer gamma (amplifying)')
    if smart_money_score >= 60:
        interpretation_parts.append('Bullish options flow')
    elif smart_money_score <= 40:
        interpretation_parts.append('Bearish options flow')
    if maxpain_score >= 60:
        interpretation_parts.append(f'Price pulled toward max pain ({max_pain_price})')
    interpretation = '. '.join(interpretation_parts) + '.' if interpretation_parts else 'Insufficient data.'

    # === Generate Action Plan ===
    actions = []

    # 1. Directional bias
    if composite_score >= 75:
        actions.append({'type': 'bias', 'icon': 'bull', 'text': f'Strong bullish bias (score {composite_score}/100). Favor long delta strategies — calls, call spreads, or put credit spreads.'})
    elif composite_score >= 60:
        actions.append({'type': 'bias', 'icon': 'bull', 'text': f'Moderate bullish bias (score {composite_score}/100). Consider call debit spreads or put credit spreads with defined risk.'})
    elif composite_score >= 45:
        actions.append({'type': 'bias', 'icon': 'neutral', 'text': f'Neutral bias (score {composite_score}/100). Range-bound strategies favored — iron condors, strangles, or butterflies.'})
    elif composite_score >= 30:
        actions.append({'type': 'bias', 'icon': 'bear', 'text': f'Moderate bearish bias (score {composite_score}/100). Consider put debit spreads or call credit spreads with defined risk.'})
    else:
        actions.append({'type': 'bias', 'icon': 'bear', 'text': f'Strong bearish bias (score {composite_score}/100). Favor short delta strategies — puts, put spreads, or call credit spreads.'})

    # 2. Dealer flow regime advice
    if dealer_flow_score >= 60:
        actions.append({'type': 'regime', 'icon': 'shield', 'text': 'Positive GEX regime — dealers are stabilizing. Mean reversion likely. Sell premium on extremes; fade moves away from max pain.'})
    elif dealer_flow_score <= 35:
        actions.append({'type': 'regime', 'icon': 'warning', 'text': 'Negative GEX regime — dealers amplify moves. Expect trending/volatile action. Avoid selling naked premium; use defined-risk or directional trades.'})
    else:
        actions.append({'type': 'regime', 'icon': 'info', 'text': 'Transitional GEX regime — mixed dealer positioning. Smaller size recommended until regime clarifies.'})

    # 3. Squeeze/Pin advice
    sq_score = squeeze_pin.get('squeeze_score', 0)
    pin_score_val = squeeze_pin.get('pin_score', 0)
    sq_dir = squeeze_pin.get('squeeze_direction', 'none')
    if sq_score >= 70:
        sq_trigger = squeeze_pin.get('squeeze_trigger_price', '')
        trigger_txt = f' above ${sq_trigger}' if sq_trigger and sq_dir == 'up' else (f' below ${sq_trigger}' if sq_trigger else '')
        actions.append({'type': 'squeeze', 'icon': 'rocket', 'text': f'High gamma squeeze potential {sq_dir}{trigger_txt} (score {sq_score}). Breakout{trigger_txt} could accelerate sharply. Consider long options or debit spreads in the squeeze direction.'})
    if pin_score_val >= 70:
        pin_strike = squeeze_pin.get('pin_strike', '')
        actions.append({'type': 'pin', 'icon': 'pin', 'text': f'High pin risk at ${pin_strike} (score {pin_score_val}). Price likely magnetized to this strike into expiry. Consider butterflies centered at ${pin_strike}.'})

    # 4. Vol surface advice
    skew_label = vol_surface.get('skew_label', '')
    term_label = vol_surface.get('term_signal', vol_surface.get('term_label', ''))
    cheapest = vol_surface.get('cheapest_gamma', [])
    richest = vol_surface.get('richest_theta', [])
    if skew_label == 'steep':
        actions.append({'type': 'vol', 'icon': 'chart', 'text': 'Put skew is steep — downside protection is expensive. Consider selling put spreads (high premium) or risk reversals (sell puts, buy calls).'})
    elif skew_label == 'flat':
        actions.append({'type': 'vol', 'icon': 'chart', 'text': 'Put skew is flat — downside protection is cheap. Good time to buy protective puts or put debit spreads.'})
    if term_label == 'inverted' or (term and isinstance(term, dict) and term.get('structure') == 'backwardation'):
        actions.append({'type': 'vol', 'icon': 'warning', 'text': 'Term structure inverted (backwardation) — near-term fear elevated. Calendar spreads risky. Prefer front-month defined risk or wait for resolution.'})
    if cheapest and len(cheapest) > 0:
        cg = cheapest[0]
        tg = cg.get("ratio", cg.get("tg_ratio", ""))
        try:
            tg_str = f'{float(tg):.1f}'
        except (ValueError, TypeError):
            tg_str = str(tg)
        actions.append({'type': 'vol', 'icon': 'target', 'text': f'Cheapest gamma: {cg.get("type","").upper()} ${cg.get("strike","")} (|T|/G ratio {tg_str}). Best bang-for-buck directional bet if expecting a move.'})

    # 5. Smart money insight
    net_flow = smart_money.get('net_flow', 'neutral')
    total_call_n = float(smart_money.get('total_call_notional', 0) or 0)
    total_put_n = float(smart_money.get('total_put_notional', 0) or 0)
    if net_flow == 'bullish' and total_call_n > 0:
        actions.append({'type': 'flow', 'icon': 'money', 'text': f'Institutional flow is bullish — ${total_call_n/1e6:.1f}M calls vs ${total_put_n/1e6:.1f}M puts. Smart money positioning supports upside.'})
    elif net_flow == 'bearish' and total_put_n > 0:
        actions.append({'type': 'flow', 'icon': 'money', 'text': f'Institutional flow is bearish — ${total_put_n/1e6:.1f}M puts vs ${total_call_n/1e6:.1f}M calls. Smart money positioning favors downside.'})

    # 6. Key levels
    tz = trade_zones
    level_parts = []
    if tz.get('support'):
        level_parts.append(f"Support: ${tz['support']}")
    if tz.get('gamma_flip'):
        level_parts.append(f"Gamma Flip: ${tz['gamma_flip']}")
    if max_pain_price:
        level_parts.append(f"Max Pain: ${max_pain_price}")
    if tz.get('resistance'):
        level_parts.append(f"Resistance: ${tz['resistance']}")
    if level_parts:
        actions.append({'type': 'levels', 'icon': 'levels', 'text': 'Key levels — ' + ' | '.join(level_parts) + '. Set alerts at these prices for entry/exit triggers.'})

    # 7. Risk warning
    if dte is not None and dte <= 3:
        actions.append({'type': 'risk', 'icon': 'warning', 'text': f'Expiration in {dte} days — gamma risk extreme. Expect large intraday swings. Reduce position size or close before expiry.'})
    elif dte is not None and dte <= 7:
        actions.append({'type': 'risk', 'icon': 'info', 'text': f'Expiration in {dte} days — theta decay accelerating. Time spreads and short premium benefit; long options lose value fast.'})

    # === Generate Trade Ideas (2-3 max) ===
    def _fp(price):
        """Format price: 2 decimals <100, 1 decimal <1000, 0 decimals >=1000."""
        try:
            p = float(price)
            if p >= 1000:
                return f'{p:,.0f}'
            elif p >= 100:
                return f'{p:,.1f}'
            else:
                return f'{p:,.2f}'
        except (ValueError, TypeError):
            return str(price)

    def _find_by_delta(target_delta, opt_type, opts):
        """Find option closest to target |delta|. Skips zero-priced."""
        if not opts:
            return None
        best = None
        best_dist = float('inf')
        for o in opts:
            leg = o.get(opt_type)
            if not leg:
                continue
            price = float(leg.get('price', 0) or 0)
            if price <= 0:
                continue
            raw_delta = leg.get('delta')
            if raw_delta is None:
                continue
            try:
                d = abs(float(raw_delta))
            except (ValueError, TypeError):
                continue
            dist = abs(d - target_delta)
            if dist < best_dist:
                best_dist = dist
                best = {'strike': float(o['strike']), 'price': round(price, 2), 'delta': round(d, 2)}
        return best

    def _find_by_strike(target_price, opt_type, opts):
        """Find option nearest to a target strike price. Skips zero-priced."""
        if not opts:
            return None
        best = None
        best_dist = float('inf')
        for o in opts:
            leg = o.get(opt_type)
            if not leg:
                continue
            price = float(leg.get('price', 0) or 0)
            if price <= 0:
                continue
            strike = float(o['strike'])
            dist = abs(strike - target_price)
            if dist < best_dist:
                best_dist = dist
                raw_delta = leg.get('delta')
                try:
                    d = abs(float(raw_delta)) if raw_delta is not None else None
                except (ValueError, TypeError):
                    d = None
                best = {'strike': strike, 'price': round(price, 2), 'delta': round(d, 2) if d is not None else None}
        return best

    def _calc_rr(premium, strike, target_p, opt_type):
        """Risk:Reward using Black-Scholes. Estimates option value at target including time value."""
        if not premium or premium <= 0 or not target_p:
            return None
        tp = float(target_p)
        T = max(dte - 1, 0) / 365.0 if dte and dte > 0 else 0
        iv = atm_iv if atm_iv and atm_iv > 0 else None
        if iv and T > 0:
            value_at_target = _bs_price(tp, strike, T, iv, opt_type)
        else:
            # Fallback to intrinsic-only for 0DTE or missing IV
            if opt_type == 'call':
                value_at_target = max(0.0, tp - strike)
            else:
                value_at_target = max(0.0, strike - tp)
        reward = value_at_target - premium
        if reward <= 0:
            return None
        return round(reward / premium, 1)

    def _fmt_action(opt, opt_type, exp_l, dte_l):
        """Format action string from option match."""
        if not opt:
            return None
        delta_txt = f' | Δ.{int(opt["delta"]*100):02d}' if opt.get('delta') else ''
        s = f'Buy ${_fp(opt["strike"])} {opt_type} @ ${opt["price"]:.2f}{delta_txt}'
        if exp_l:
            s += f' ({exp_l}, {dte_l})'
        return s

    # --- Gather all inputs ---
    tz = trade_zones
    support_p = tz.get('support')
    resistance_p = tz.get('resistance')
    gamma_flip_p = tz.get('gamma_flip')
    upper_1sd = tz.get('upper_1sd')
    lower_1sd = tz.get('lower_1sd')
    eff_support = support_p or lower_1sd
    eff_resistance = resistance_p or upper_1sd

    net_flow = smart_money.get('net_flow', 'neutral')
    sq_score_raw = squeeze_pin.get('squeeze_score', 0)
    sq_trigger = squeeze_pin.get('squeeze_trigger_price')
    sq_dir_raw = squeeze_pin.get('squeeze_direction', 'up')
    opts = options or []

    # ATM IV for context
    atm_iv = None
    if iv_delta and isinstance(iv_delta, dict):
        atm_iv = iv_delta.get('atm_iv')
        try:
            atm_iv = float(atm_iv) if atm_iv else None
        except (ValueError, TypeError):
            atm_iv = None
    iv_pct = round(atm_iv * 100) if atm_iv else None

    # Expiry label
    exp_label = ''
    if expiration:
        try:
            exp_dt = datetime.strptime(str(expiration), '%Y-%m-%d')
            exp_label = exp_dt.strftime('%b %d')
        except (ValueError, TypeError):
            exp_label = str(expiration)
    dte_label = f'{dte}d' if dte else ''

    # --- Confidence: count agreeing directional signals ---
    bullish_signals = 0
    bearish_signals = 0
    total_signals = 0
    # Score direction
    if composite_score >= 55:
        bullish_signals += 1
    elif composite_score < 45:
        bearish_signals += 1
    total_signals += 1
    # Smart money flow
    if net_flow == 'bullish':
        bullish_signals += 1
    elif net_flow == 'bearish':
        bearish_signals += 1
    total_signals += 1
    # GEX regime
    if dealer_flow_score >= 60:
        bullish_signals += 1
    elif dealer_flow_score <= 35:
        bearish_signals += 1
    total_signals += 1
    # Skew signal
    skew_label = vol_surface.get('skew_label', '')
    if skew_label == 'flat':
        bullish_signals += 1  # cheap puts = less fear
    elif skew_label == 'steep':
        bearish_signals += 1  # expensive puts = fear
    total_signals += 1
    # Term structure
    term_struct = None
    if term and isinstance(term, dict):
        term_struct = term.get('structure')
    if term_struct == 'contango':
        bullish_signals += 1
    elif term_struct == 'backwardation':
        bearish_signals += 1
    total_signals += 1

    max_agreement = max(bullish_signals, bearish_signals)
    if max_agreement >= 4:
        confidence = 'high'
    elif max_agreement >= 3:
        confidence = 'medium'
    else:
        confidence = 'low'

    # --- IV context for rationale ---
    iv_note = ''
    if iv_pct:
        if iv_pct > 50:
            iv_note = f'IV {iv_pct}% (elevated — options expensive)'
        elif iv_pct > 30:
            iv_note = f'IV {iv_pct}%'
        else:
            iv_note = f'IV {iv_pct}% (low — options cheap)'

    # --- DTE context ---
    dte_note = ''
    if dte is not None:
        if dte <= 3:
            dte_note = 'Expiring soon — gamma risk extreme'
        elif dte <= 7:
            dte_note = 'Theta accelerating'

    trade_ideas = []

    # =====================================================================
    # 1. PRIMARY DIRECTIONAL TRADE — Position-aware
    # =====================================================================
    dir_delta = 0.50 if (dte is not None and dte <= 5) else 0.35
    NEAR_PCT = 1.0  # within 1% = "near" a level

    # --- Position analysis ---
    def _abs_pct(level):
        """Absolute % distance from current price to level."""
        if not level or not current_price:
            return None
        return round(abs((float(level) - current_price) / current_price * 100), 2)

    d_sup = _abs_pct(eff_support)
    d_res = _abs_pct(eff_resistance)
    price_above_sup = eff_support and current_price > float(eff_support)
    price_below_res = eff_resistance and current_price < float(eff_resistance)

    near_sup = price_above_sup and d_sup is not None and d_sup <= NEAR_PCT
    near_res = price_below_res and d_res is not None and d_res <= NEAR_PCT
    above_res = eff_resistance and current_price >= float(eff_resistance)
    below_sup = eff_support and current_price <= float(eff_support)

    pos_gex = dealer_flow_score >= 60
    neg_gex = dealer_flow_score <= 35

    sup_lbl = 'support' if support_p else '-1σ'
    res_lbl = 'resistance' if resistance_p else '+1σ'

    # --- Rationale builder ---
    def _rationale():
        parts = [f'Score {composite_score}']
        if net_flow != 'neutral':
            parts.append(f'{net_flow} flow')
        if pos_gex:
            parts.append('+GEX (stabilizing)')
        elif neg_gex:
            parts.append('-GEX (amplifying)')
        if iv_note:
            parts.append(iv_note)
        if dte_note:
            parts.append(dte_note)
        return ' + '.join(parts)

    rat = _rationale()

    # --- Helper to build a trade dict with R:R ---
    def _mk_trade(title, ttype, opt, opt_type, cond, target_p, target_lbl, stop_p, stop_lbl):
        action = _fmt_action(opt, opt_type, exp_label, dte_label) or f'Buy {opt_type} (~Δ.{int(dir_delta*100)})'
        rr = _calc_rr(opt['price'], opt['strike'], target_p, opt_type) if opt and target_p else None
        target_txt = f'${_fp(target_p)} ({target_lbl})' if target_p else f'Next {"resistance" if opt_type == "call" else "support"}'
        if rr:
            target_txt += f' — R:R {rr}:1'
        stop_txt = f'${_fp(stop_p)} ({stop_lbl})' if stop_p else ''
        if opt:
            stop_txt += f' — max loss ${opt["price"]:.2f}' if stop_txt else f'Max loss ${opt["price"]:.2f}'
        return {
            'title': title,
            'type': ttype,
            'confidence': confidence,
            'condition': cond,
            'action': action,
            'target': target_txt,
            'stop': stop_txt,
            'rationale': rat
        }

    # --- Scenario-based primary trade ---
    if above_res:
        # EXTENDED ABOVE RESISTANCE
        cond = f'Price ${_fp(current_price)} above {res_lbl} ${_fp(eff_resistance)} (+{d_res:.1f}%)'
        if pos_gex or composite_score < 55:
            # Mean reversion / fade
            opt = _find_by_delta(dir_delta, 'put', opts)
            target_p = eff_resistance  # revert back to resistance
            stop_p = upper_1sd if upper_1sd and float(upper_1sd) > current_price else None
            trade_ideas.append(_mk_trade(
                'FADE EXTENSION', 'bearish', opt, 'put',
                cond + ' — dealers stabilizing, reversion likely' if pos_gex else cond + ' — no bullish conviction',
                target_p, res_lbl, stop_p, '+1σ' if stop_p else ''
            ))
        else:
            # Bullish momentum
            opt = _find_by_delta(dir_delta, 'call', opts)
            target_p = upper_1sd or None
            stop_p = eff_resistance  # now acts as support
            trade_ideas.append(_mk_trade(
                'MOMENTUM CALL', 'bullish', opt, 'call',
                cond + f' — {res_lbl} now support, -GEX amplifying' if neg_gex else cond + f' — breakout continuation',
                target_p, '+1σ', stop_p, f'{res_lbl} (now support)'
            ))

    elif below_sup:
        # EXTENDED BELOW SUPPORT
        cond = f'Price ${_fp(current_price)} below {sup_lbl} ${_fp(eff_support)} (-{d_sup:.1f}%)'
        if pos_gex or composite_score >= 45:
            # Mean reversion / bounce
            opt = _find_by_delta(dir_delta, 'call', opts)
            target_p = eff_support  # bounce back to support
            stop_p = lower_1sd if lower_1sd and float(lower_1sd) < current_price else None
            trade_ideas.append(_mk_trade(
                'BOUNCE CALL', 'bullish', opt, 'call',
                cond + ' — dealers stabilizing, bounce likely' if pos_gex else cond + ' — not bearish, bounce setup',
                target_p, sup_lbl, stop_p, '-1σ' if stop_p else ''
            ))
        else:
            # Bearish momentum
            opt = _find_by_delta(dir_delta, 'put', opts)
            target_p = lower_1sd or None
            stop_p = eff_support  # now acts as resistance
            trade_ideas.append(_mk_trade(
                'MOMENTUM PUT', 'bearish', opt, 'put',
                cond + f' — {sup_lbl} now resistance, -GEX amplifying' if neg_gex else cond + f' — breakdown continuation',
                target_p, '-1σ', stop_p, f'{sup_lbl} (now resistance)'
            ))

    elif near_sup:
        # AT SUPPORT
        cond = f'Price ${_fp(current_price)} near {sup_lbl} ${_fp(eff_support)} ({d_sup:.1f}% above)'
        if composite_score >= 45:
            # Not bearish → bounce
            opt = _find_by_delta(dir_delta, 'call', opts)
            target_p = eff_resistance or max_pain_price
            t_lbl = res_lbl if eff_resistance else 'max pain'
            stop_p = eff_support
            trade_ideas.append(_mk_trade(
                'SUPPORT BOUNCE', 'bullish', opt, 'call',
                cond + ' — hold = bounce setup',
                target_p, t_lbl, stop_p, f'below {sup_lbl}'
            ))
        else:
            # Bearish → break
            opt = _find_by_delta(dir_delta, 'put', opts)
            target_p = lower_1sd or None
            stop_p = eff_support
            # Adjust stop slightly above support for break trade
            trade_ideas.append(_mk_trade(
                'SUPPORT BREAK', 'bearish', opt, 'put',
                cond + ' — bearish pressure, breakdown setup',
                target_p, '-1σ', stop_p, f'above {sup_lbl}'
            ))

    elif near_res:
        # AT RESISTANCE
        cond = f'Price ${_fp(current_price)} near {res_lbl} ${_fp(eff_resistance)} ({d_res:.1f}% below)'
        if composite_score >= 55:
            # Bullish → breakout
            opt = _find_by_delta(dir_delta, 'call', opts)
            target_p = upper_1sd or None
            stop_p = eff_resistance
            trade_ideas.append(_mk_trade(
                'BREAKOUT CALL', 'bullish', opt, 'call',
                cond + ' — bullish flow targeting breakout',
                target_p, '+1σ', stop_p, f'below {res_lbl}'
            ))
        else:
            # Not bullish → rejection
            opt = _find_by_delta(dir_delta, 'put', opts)
            target_p = eff_support or max_pain_price
            t_lbl = sup_lbl if eff_support else 'max pain'
            stop_p = eff_resistance
            trade_ideas.append(_mk_trade(
                'RESISTANCE REJECTION', 'bearish', opt, 'put',
                cond + ' — rejection likely' if composite_score < 45 else cond + ' — no bullish conviction, fade likely',
                target_p, t_lbl, stop_p, f'above {res_lbl}'
            ))

    else:
        # MID-RANGE
        if composite_score >= 55:
            opt = _find_by_delta(dir_delta, 'call', opts)
            target_p = eff_resistance or max_pain_price
            t_lbl = res_lbl if eff_resistance else 'max pain'
            stop_p = eff_support
            mid_cond = f'Price ${_fp(current_price)}'
            if d_res is not None:
                mid_cond += f', {d_res:.1f}% below {res_lbl} ${_fp(eff_resistance)} — bullish flow targeting breakout'
            else:
                mid_cond += ' — bullish bias holds'
            trade_ideas.append(_mk_trade(
                'BULLISH CALL', 'bullish', opt, 'call',
                mid_cond, target_p, t_lbl, stop_p, sup_lbl if eff_support else ''
            ))

        elif composite_score < 45:
            opt = _find_by_delta(dir_delta, 'put', opts)
            target_p = eff_support or max_pain_price
            t_lbl = sup_lbl if eff_support else 'max pain'
            stop_p = eff_resistance
            mid_cond = f'Price ${_fp(current_price)}'
            if d_sup is not None:
                mid_cond += f', {d_sup:.1f}% above {sup_lbl} ${_fp(eff_support)} — bearish flow targeting breakdown'
            else:
                mid_cond += ' — bearish bias holds'
            trade_ideas.append(_mk_trade(
                'BEARISH PUT', 'bearish', opt, 'put',
                mid_cond, target_p, t_lbl, stop_p, res_lbl if eff_resistance else ''
            ))

        else:
            # Neutral mid-range
            parts = [f'Score {composite_score}']
            if iv_note:
                parts.append(iv_note)
            if dte_note:
                parts.append(dte_note)

            if confidence == 'low' or (not eff_support and not eff_resistance):
                trade_ideas.append({
                    'title': 'NO CLEAR EDGE',
                    'type': 'neutral',
                    'confidence': 'low',
                    'condition': 'Signals are mixed — wait for clarity',
                    'action': 'Stay flat or reduce size',
                    'target': '--',
                    'stop': '--',
                    'rationale': ' + '.join(parts)
                })
            else:
                call_opt = _find_by_delta(0.40, 'call', opts) if eff_support else None
                put_opt = _find_by_delta(0.40, 'put', opts) if eff_resistance else None
                action_parts = []
                if call_opt:
                    action_parts.append(f'At {sup_lbl} → ${_fp(call_opt["strike"])} call @ ${call_opt["price"]:.2f}')
                if put_opt:
                    action_parts.append(f'At {res_lbl} → ${_fp(put_opt["strike"])} put @ ${put_opt["price"]:.2f}')
                action_txt = ' | '.join(action_parts) if action_parts else 'Buy call at support / put at resistance'
                if exp_label and action_parts:
                    action_txt += f' ({exp_label}, {dte_label})'
                max_loss_parts = []
                if call_opt:
                    max_loss_parts.append(f'${call_opt["price"]:.2f}')
                if put_opt:
                    max_loss_parts.append(f'${put_opt["price"]:.2f}')
                trade_ideas.append({
                    'title': 'RANGE PLAY',
                    'type': 'neutral',
                    'confidence': confidence,
                    'condition': f'Price ${_fp(current_price)} mid-range between {sup_lbl} ${_fp(eff_support)} and {res_lbl} ${_fp(eff_resistance)}',
                    'action': action_txt,
                    'target': f'${_fp(max_pain_price)} (max pain)' if max_pain_price else 'Mid-range reversion',
                    'stop': f'Break beyond level — max loss {" or ".join(max_loss_parts)}' if max_loss_parts else 'Break beyond level',
                    'rationale': ' + '.join(parts)
                })

    # =====================================================================
    # 2. BREAKOUT TRADE (only if squeeze_score >= 60)
    # =====================================================================
    if sq_score_raw >= 60 and sq_trigger:
        # Target ~.30 delta OTM for leveraged breakout
        if sq_dir_raw == 'up':
            opt = _find_by_delta(0.30, 'call', opts)
            bk_target = upper_1sd or resistance_p
            action = _fmt_action(opt, 'call', exp_label, dte_label) or f'Buy OTM call above ${_fp(sq_trigger)}'
            rr = _calc_rr(opt['price'], opt['strike'], bk_target, 'call') if opt and bk_target else None
            stop_txt = f'${_fp(gamma_flip_p)} (gamma flip)' if gamma_flip_p else f'Below ${_fp(sq_trigger)}'
            if opt:
                stop_txt += f' — max loss ${opt["price"]:.2f}'
            target_txt = f'${_fp(bk_target)} (+1σ)'
            if rr:
                target_txt += f' — R:R {rr}:1'
            elif not bk_target:
                target_txt = 'Next resistance'
        else:
            opt = _find_by_delta(0.30, 'put', opts)
            bk_target = lower_1sd or support_p
            action = _fmt_action(opt, 'put', exp_label, dte_label) or f'Buy OTM put below ${_fp(sq_trigger)}'
            rr = _calc_rr(opt['price'], opt['strike'], bk_target, 'put') if opt and bk_target else None
            stop_txt = f'${_fp(gamma_flip_p)} (gamma flip)' if gamma_flip_p else f'Above ${_fp(sq_trigger)}'
            if opt:
                stop_txt += f' — max loss ${opt["price"]:.2f}'
            target_txt = f'${_fp(bk_target)} (-1σ)'
            if rr:
                target_txt += f' — R:R {rr}:1'
            elif not bk_target:
                target_txt = 'Next support'

        bk_parts = [f'Squeeze {sq_score_raw}']
        if iv_note:
            bk_parts.append(iv_note)
        trade_ideas.append({
            'title': f'BREAKOUT {"CALL" if sq_dir_raw == "up" else "PUT"}',
            'type': 'breakout',
            'confidence': 'high' if sq_score_raw >= 80 else 'medium',
            'condition': f'Price breaks {"above" if sq_dir_raw == "up" else "below"} ${_fp(sq_trigger)}',
            'action': action,
            'target': target_txt,
            'stop': stop_txt,
            'rationale': ' + '.join(bk_parts)
        })

    # =====================================================================
    # 3. VALUE PICK — OTM only, reasonable premium, Δ .15-.50
    # =====================================================================
    if cheapest and len(cheapest) > 0:
        cg = cheapest[0]
        cg_strike = cg.get('strike')
        cg_type = (cg.get('type') or '').lower()
        if cg_strike and cg_type:
            is_otm = (cg_type == 'call' and float(cg_strike) > current_price) or \
                     (cg_type == 'put' and float(cg_strike) < current_price)
            opt = _find_by_strike(float(cg_strike), cg_type, opts) if is_otm else None
            # Filter: must be OTM, premium < 5% of underlying, delta .15-.50
            if opt and opt['price'] < current_price * 0.05 and opt.get('delta') and 0.15 <= opt['delta'] <= 0.50:
                # Check it's different from primary idea strike
                primary_strike = trade_ideas[0].get('_strike') if trade_ideas else None
                if not primary_strike or abs(opt['strike'] - (primary_strike or 0)) > 1:
                    val_target = upper_1sd if cg_type == 'call' else lower_1sd
                    val_stop = gamma_flip_p
                    action = _fmt_action(opt, cg_type, exp_label, dte_label)
                    rr = _calc_rr(opt['price'], opt['strike'], val_target, cg_type) if val_target else None

                    target_txt = f'${_fp(val_target)} ({"+" if cg_type == "call" else "-"}1σ)'
                    if rr:
                        target_txt += f' — R:R {rr}:1'
                    elif not val_target:
                        target_txt = 'Next level'
                    stop_txt = f'${_fp(val_stop)} (gamma flip) — max loss ${opt["price"]:.2f}' if val_stop else f'Max loss ${opt["price"]:.2f}'

                    trade_ideas.append({
                        'title': f'VALUE {cg_type.upper()}',
                        'type': 'value',
                        'confidence': confidence,
                        'condition': f'Best gamma/cost ratio — OTM Δ.{int(opt["delta"]*100):02d}',
                        'action': action,
                        'target': target_txt,
                        'stop': stop_txt,
                        'rationale': f'Cheapest gamma + {"low" if iv_pct and iv_pct < 30 else "fair" if iv_pct and iv_pct <= 50 else "high"} IV' if iv_pct else 'Cheapest gamma'
                    })

    # Cap at 3 ideas
    trade_ideas = trade_ideas[:3]

    return {
        'score': composite_score,
        'label': label,
        'factors': factors,
        'interpretation': interpretation,
        'action_plan': actions,
        'trade_ideas': trade_ideas
    }


# =============================================================================
# SWING TRADE TRACKER — Position Health Analysis
# =============================================================================

def _compute_hold_score(pnl_pct, dte, composite_score, composite_label,
                        entry_label, opt_type, support_intact, resistance_intact,
                        support_shifted_pct, resistance_shifted_pct,
                        iv_helping, iv_change_pct, net_flow, entry_flow,
                        squeeze_score, entry_squeeze, squeeze_building):
    """Compute 0-100 hold score from 7 weighted factors."""
    factors = []

    # 1. P&L Momentum (15%)
    if pnl_pct >= 100: s = 95
    elif pnl_pct >= 50: s = 85
    elif pnl_pct >= 20: s = 75
    elif pnl_pct >= 0: s = 60
    elif pnl_pct >= -20: s = 35
    elif pnl_pct >= -50: s = 15
    else: s = 5
    factors.append({'name': 'pnl_momentum', 'score': s, 'weight': 15,
                    'contribution': round(s * 15 / 100, 2)})

    # 2. Time Decay Risk (15%)
    if dte is None or dte >= 45: s = 85
    elif dte >= 30: s = 70
    elif dte >= 21: s = 55
    elif dte >= 14: s = 35
    elif dte >= 7: s = 20
    else: s = 5
    factors.append({'name': 'time_decay', 'score': s, 'weight': 15,
                    'contribution': round(s * 15 / 100, 2)})

    # 3. Regime Alignment (20%)
    if opt_type == 'call':
        s = min(100, max(0, composite_score))
    else:
        s = min(100, max(0, 100 - composite_score))
    if entry_label and composite_label and entry_label != composite_label:
        s = max(0, s - 20)
    factors.append({'name': 'regime_alignment', 'score': s, 'weight': 20,
                    'contribution': round(s * 20 / 100, 2)})

    # 4. Level Integrity (15%)
    s = 50
    if opt_type == 'call':
        if support_intact: s += 25
        if support_shifted_pct and support_shifted_pct > 0: s += 25
        elif support_shifted_pct and support_shifted_pct < -2: s -= 20
    else:
        if resistance_intact: s += 25
        if resistance_shifted_pct and resistance_shifted_pct < 0: s += 25
        elif resistance_shifted_pct and resistance_shifted_pct > 2: s -= 20
    s = min(100, max(0, s))
    factors.append({'name': 'level_integrity', 'score': s, 'weight': 15,
                    'contribution': round(s * 15 / 100, 2)})

    # 5. IV Trend (10%)
    s = 50
    if iv_helping is True:
        s = 70
        if iv_change_pct and abs(iv_change_pct) > 10: s += 15
    elif iv_helping is False:
        s = 30
        if iv_change_pct and abs(iv_change_pct) > 10: s -= 15
    s = min(100, max(0, s))
    factors.append({'name': 'iv_trend', 'score': s, 'weight': 10,
                    'contribution': round(s * 10 / 100, 2)})

    # 6. Smart Money (15%)
    s = 50
    flow_match = (opt_type == 'call' and net_flow == 'bullish') or \
                 (opt_type == 'put' and net_flow == 'bearish')
    if flow_match: s += 30
    entry_match = (entry_flow and net_flow == entry_flow)
    if entry_match: s += 20
    s = min(100, max(0, s))
    factors.append({'name': 'smart_money', 'score': s, 'weight': 15,
                    'contribution': round(s * 15 / 100, 2)})

    # 7. Squeeze/Catalyst (10%)
    s = 50
    if squeeze_building: s += 30
    if squeeze_score and squeeze_score >= 60: s += 20
    if entry_squeeze and squeeze_score and squeeze_score < entry_squeeze - 20:
        s -= 25  # fizzled
    s = min(100, max(0, s))
    factors.append({'name': 'squeeze_catalyst', 'score': s, 'weight': 10,
                    'contribution': round(s * 10 / 100, 2)})

    total = sum(f['contribution'] for f in factors)
    total = min(100, max(0, round(total)))

    if total >= 80: label = 'STRONG HOLD'
    elif total >= 60: label = 'HOLD'
    elif total >= 45: label = 'MONITOR'
    elif total >= 30: label = 'REDUCE'
    else: label = 'EXIT'

    return {'score': total, 'label': label, 'factors': factors}


def _generate_action_signal(hold_label, pnl_pct, pnl_dollar, opt_type, dte,
                            composite_label, entry_label, support, resistance,
                            iv_helping, net_flow):
    """Generate actionable text advice based on hold score and conditions."""
    parts = []

    if hold_label == 'STRONG HOLD':
        parts.append(f'Trade profitable +{pnl_pct:.1f}%' if pnl_pct > 0 else 'Position healthy')
        if composite_label:
            parts.append(f'regime {composite_label}')
        if support and opt_type == 'call':
            parts.append(f'trail stop to ${support:.0f}')
        elif resistance and opt_type == 'put':
            parts.append(f'trail stop to ${resistance:.0f}')
        return '. '.join(parts) + '. Hold and let it run.'

    elif hold_label == 'HOLD':
        parts.append(f'P&L {pnl_pct:+.1f}%')
        if dte and dte < 21:
            parts.append(f'{dte} DTE — watch theta')
        return '. '.join(parts) + '. Continue holding, set alerts at key levels.'

    elif hold_label == 'MONITOR':
        if entry_label and composite_label and entry_label != composite_label:
            parts.append(f'Regime shifted from {entry_label} to {composite_label}')
        if iv_helping is False:
            parts.append('IV moving against position')
        if dte and dte < 14:
            parts.append(f'Only {dte} DTE remaining')
        return '. '.join(parts) + '. Consider reducing size or tightening stops.' if parts else 'Mixed signals. Tighten stops and watch closely.'

    elif hold_label == 'REDUCE':
        if pnl_pct < -20:
            parts.append(f'Down {pnl_pct:.1f}%')
        if entry_label and composite_label and entry_label != composite_label:
            parts.append(f'regime flipped to {composite_label}')
        if iv_helping is False:
            parts.append('IV declining')
        return '. '.join(parts) + '. Consider reducing 50%.' if parts else 'Conditions deteriorating. Consider reducing 50%.'

    else:  # EXIT
        if dte and dte <= 5 and pnl_pct < -30:
            return f'Only {dte} DTE, deep loss {pnl_pct:.1f}%. Exit to preserve capital.'
        if entry_label and composite_label and entry_label != composite_label:
            return f'Regime flipped from {entry_label} to {composite_label}. P&L {pnl_pct:+.1f}%. Exit now.'
        return f'P&L {pnl_pct:+.1f}%, conditions unfavorable. Exit position.'


def _analyze_single_trade(trade, xray, chain_options):
    """Analyze a single swing trade against fresh X-Ray and chain data."""
    try:
        opt_type = trade.get('opt_type', 'call')
        strike = float(trade.get('strike', 0))
        entry_premium = float(trade.get('entry_premium', 0))
        entry_date = trade.get('entry_date', '')
        expiration = trade.get('expiration', '')

        current_price = xray.get('current_price', 0)
        dte = xray.get('dte')

        # --- Look up current option in chain ---
        current_premium = None
        greeks = {}
        for o in (chain_options or []):
            leg = o.get(opt_type)
            if not leg:
                continue
            s = float(o.get('strike', 0))
            if abs(s - strike) < 0.01:
                p = float(leg.get('price', 0) or 0)
                if p > 0:
                    current_premium = p
                greeks = {
                    'delta': leg.get('delta'),
                    'gamma': leg.get('gamma'),
                    'theta': leg.get('theta'),
                    'vega': leg.get('vega'),
                    'iv': leg.get('iv'),
                }
                break

        # BS fallback for current premium
        if not current_premium and current_price > 0 and strike > 0 and dte:
            atm_iv = None
            iv_delta = xray.get('vol_surface', {})
            if iv_delta:
                # Try to get ATM IV from vol surface
                atm_iv_raw = iv_delta.get('atm_iv')
                if atm_iv_raw:
                    try:
                        atm_iv = float(atm_iv_raw)
                    except (ValueError, TypeError):
                        pass
            if atm_iv and atm_iv > 0:
                T = max(dte, 0) / 365.0
                current_premium = round(_bs_price(current_price, strike, T, atm_iv, opt_type), 2)

        if current_premium is None:
            return {'error': 'Could not determine current premium', 'strike': strike,
                    'opt_type': opt_type, 'signal': 'MANUAL CHECK'}

        # --- P&L Block ---
        pnl_dollar = round(current_premium - entry_premium, 2)
        pnl_pct = round((pnl_dollar / entry_premium) * 100, 2) if entry_premium > 0 else 0
        pnl_dollar_100 = round(pnl_dollar * 100, 2)

        if opt_type == 'call':
            intrinsic = max(0, current_price - strike)
        else:
            intrinsic = max(0, strike - current_price)
        extrinsic = max(0, round(current_premium - intrinsic, 2))

        if opt_type == 'call':
            breakeven = strike + entry_premium
        else:
            breakeven = strike - entry_premium

        pnl = {
            'current_premium': round(current_premium, 2),
            'entry_premium': round(entry_premium, 2),
            'pnl_dollar': pnl_dollar,
            'pnl_percent': pnl_pct,
            'pnl_dollar_100': pnl_dollar_100,
            'intrinsic': round(intrinsic, 2),
            'extrinsic': round(extrinsic, 2),
            'breakeven': round(breakeven, 2)
        }

        # --- Greeks Block ---
        theta_val = None
        vega_val = None
        iv_val = None
        try:
            if greeks.get('theta'): theta_val = float(greeks['theta'])
            if greeks.get('vega'): vega_val = float(greeks['vega'])
            if greeks.get('iv'): iv_val = float(greeks['iv'])
        except (ValueError, TypeError):
            pass

        greeks_out = {
            'delta': greeks.get('delta'),
            'gamma': greeks.get('gamma'),
            'theta': greeks.get('theta'),
            'vega': greeks.get('vega'),
            'iv': greeks.get('iv'),
            'theta_dollar': round(abs(theta_val) * 100, 2) if theta_val else None,
            'vega_dollar': round(abs(vega_val) * 100, 2) if vega_val else None,
        }

        # --- Theta Burn Block ---
        daily_decay = abs(theta_val) if theta_val else None
        total_extrinsic = extrinsic
        days_of_theta = round(total_extrinsic / daily_decay, 1) if daily_decay and daily_decay > 0 else None
        breakeven_days = round(pnl_dollar / daily_decay, 1) if daily_decay and daily_decay > 0 and pnl_dollar > 0 else None
        decay_accelerating = dte is not None and dte < 21

        theta_burn = {
            'dte': dte,
            'daily_decay_cost': round(daily_decay * 100, 2) if daily_decay else None,
            'total_extrinsic': round(total_extrinsic, 2),
            'days_of_theta': days_of_theta,
            'breakeven_days': breakeven_days,
            'decay_accelerating': decay_accelerating
        }

        # --- Regime Monitor ---
        composite = xray.get('composite', {})
        current_score = composite.get('score', 50)
        current_label = composite.get('label', 'NEUTRAL')
        entry_score = trade.get('entry_composite_score')
        entry_label = trade.get('entry_composite_label')
        entry_flow = trade.get('entry_net_flow')
        entry_gex = trade.get('entry_gex_regime')

        smart_money = xray.get('smart_money', {})
        net_flow = smart_money.get('net_flow', 'neutral')

        # GEX regime from dealer flow
        dealer_flow = xray.get('dealer_flow', {})
        gex_regime = 'stabilizing'
        levels = dealer_flow.get('levels', [])
        if levels:
            at_price = min(levels, key=lambda l: abs(l.get('price', 0) - current_price), default={})
            gex_regime = at_price.get('regime', 'stabilizing')

        label_changed = bool(entry_label and current_label != entry_label)
        flow_aligned = (opt_type == 'call' and net_flow == 'bullish') or \
                       (opt_type == 'put' and net_flow == 'bearish')
        gex_aligned = (opt_type == 'call' and gex_regime == 'stabilizing') or \
                      (opt_type == 'put' and gex_regime == 'amplifying')

        regime = {
            'current_score': current_score,
            'current_label': current_label,
            'entry_score': entry_score,
            'entry_label': entry_label,
            'label_changed': label_changed,
            'net_flow': net_flow,
            'entry_flow': entry_flow,
            'flow_aligned': flow_aligned,
            'gex_regime': gex_regime,
            'entry_gex': entry_gex,
            'gex_aligned': gex_aligned
        }

        # --- Level Proximity ---
        trade_zones = xray.get('trade_zones', {})
        support = trade_zones.get('support')
        resistance = trade_zones.get('resistance')
        gamma_flip = trade_zones.get('gamma_flip')
        max_pain = trade_zones.get('max_pain')

        entry_support = trade.get('entry_support')
        entry_resistance = trade.get('entry_resistance')

        def _dist_pct(level):
            if not level or not current_price: return None
            return round((float(level) - current_price) / current_price * 100, 2)

        support_intact = bool(support and entry_support and float(support) >= float(entry_support) * 0.98)
        resistance_intact = bool(resistance and entry_resistance and float(resistance) <= float(entry_resistance) * 1.02)
        support_shifted_pct = round((float(support) - float(entry_support)) / float(entry_support) * 100, 2) \
            if support and entry_support and float(entry_support) > 0 else None
        resistance_shifted_pct = round((float(resistance) - float(entry_resistance)) / float(entry_resistance) * 100, 2) \
            if resistance and entry_resistance and float(entry_resistance) > 0 else None

        levels_out = {
            'support': support, 'resistance': resistance,
            'gamma_flip': gamma_flip, 'max_pain': max_pain,
            'dist_to_support': _dist_pct(support),
            'dist_to_resistance': _dist_pct(resistance),
            'dist_to_gamma_flip': _dist_pct(gamma_flip),
            'support_intact': support_intact,
            'resistance_intact': resistance_intact,
            'support_shifted_pct': support_shifted_pct,
            'resistance_shifted_pct': resistance_shifted_pct,
        }

        # --- IV Monitor ---
        entry_iv = trade.get('entry_atm_iv')
        current_atm_iv = None
        vol_surface = xray.get('vol_surface', {})
        if vol_surface:
            raw = vol_surface.get('atm_iv')
            if raw:
                try: current_atm_iv = float(raw)
                except (ValueError, TypeError): pass

        iv_change_pct = None
        vega_pnl = None
        iv_helping = None
        if current_atm_iv and entry_iv:
            try:
                entry_iv_f = float(entry_iv)
                if entry_iv_f > 0:
                    iv_change_pct = round((current_atm_iv - entry_iv_f) / entry_iv_f * 100, 2)
                    if vega_val:
                        iv_diff_abs = current_atm_iv - entry_iv_f
                        vega_pnl = round(iv_diff_abs * abs(vega_val) * 100, 2)
                    # Long options: IV up helps, IV down hurts
                    iv_helping = iv_change_pct > 0
            except (ValueError, TypeError):
                pass

        iv_monitor = {
            'current_atm_iv': current_atm_iv,
            'entry_iv': entry_iv,
            'iv_change_pct': iv_change_pct,
            'vega_pnl': vega_pnl,
            'iv_helping': iv_helping
        }

        # --- Squeeze Status ---
        squeeze = xray.get('squeeze_pin', {})
        squeeze_score = squeeze.get('squeeze_score', 0)
        entry_squeeze = trade.get('entry_squeeze_score')
        catalyst_building = bool(entry_squeeze is not None and squeeze_score > (entry_squeeze or 0))
        squeeze_triggered = squeeze.get('squeeze_trigger_price') is not None and \
            ((opt_type == 'call' and current_price >= float(squeeze.get('squeeze_trigger_price', 0))) or
             (opt_type == 'put' and current_price <= float(squeeze.get('squeeze_trigger_price', 0))))

        squeeze_status = {
            'current_score': squeeze_score,
            'entry_score': entry_squeeze,
            'catalyst_building': catalyst_building,
            'squeeze_triggered': squeeze_triggered
        }

        # --- Dynamic Targets ---
        if opt_type == 'call':
            new_target = resistance if resistance else None
            new_stop = support if support else None
        else:
            new_target = support if support else None
            new_stop = resistance if resistance else None

        # Revised R:R
        revised_rr = None
        if new_target and current_premium > 0 and dte:
            T = max(dte - 1, 0) / 365.0
            iv_for_rr = current_atm_iv or (float(entry_iv) if entry_iv else None)
            if iv_for_rr and T > 0:
                val_at_tgt = _bs_price(float(new_target), strike, T, iv_for_rr, opt_type)
                reward = val_at_tgt - current_premium
                if reward > 0:
                    revised_rr = round(reward / current_premium, 1)

        dynamic_targets = {
            'target': new_target,
            'stop': new_stop,
            'revised_rr': revised_rr,
        }

        # --- Hold Score ---
        hold = _compute_hold_score(
            pnl_pct=pnl_pct, dte=dte,
            composite_score=current_score, composite_label=current_label,
            entry_label=entry_label, opt_type=opt_type,
            support_intact=support_intact, resistance_intact=resistance_intact,
            support_shifted_pct=support_shifted_pct, resistance_shifted_pct=resistance_shifted_pct,
            iv_helping=iv_helping, iv_change_pct=iv_change_pct,
            net_flow=net_flow, entry_flow=entry_flow,
            squeeze_score=squeeze_score, entry_squeeze=entry_squeeze,
            squeeze_building=catalyst_building
        )

        # --- Action Signal ---
        signal = _generate_action_signal(
            hold_label=hold['label'], pnl_pct=pnl_pct, pnl_dollar=pnl_dollar,
            opt_type=opt_type, dte=dte, composite_label=current_label,
            entry_label=entry_label, support=float(support) if support else None,
            resistance=float(resistance) if resistance else None,
            iv_helping=iv_helping, net_flow=net_flow
        )

        return {
            'ticker': trade.get('ticker'),
            'strike': strike,
            'opt_type': opt_type,
            'expiration': expiration,
            'current_price': current_price,
            'pnl': pnl,
            'greeks': greeks_out,
            'theta_burn': theta_burn,
            'regime': regime,
            'levels': levels_out,
            'iv_monitor': iv_monitor,
            'squeeze': squeeze_status,
            'dynamic_targets': dynamic_targets,
            'hold': hold,
            'signal': signal,
            'timestamp': datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error analyzing swing trade {trade.get('ticker')} {trade.get('strike')}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {'error': str(e), 'ticker': trade.get('ticker'),
                'strike': trade.get('strike'), 'signal': 'MANUAL CHECK'}


async def analyze_swing_trades(trades: list) -> Dict:
    """Analyze multiple swing trades. Groups by ticker to minimize API calls."""
    if not trades or len(trades) == 0:
        return {'trades': [], 'batch_meta': {'count': 0}}

    trades = trades[:10]  # Max 10

    # Group trades by ticker
    from collections import defaultdict
    by_ticker = defaultdict(list)
    for t in trades:
        tk = t.get('ticker', '').upper()
        if tk:
            by_ticker[tk].append(t)

    results = []

    for ticker, ticker_trades in by_ticker.items():
        try:
            # Fetch X-Ray data (has built-in 120s cache)
            xray = await compute_market_xray(ticker)
            if 'error' in xray:
                for t in ticker_trades:
                    results.append({'error': xray['error'], 'ticker': ticker,
                                    'strike': t.get('strike'), 'signal': 'MANUAL CHECK'})
                continue

            # Get chain options for strike lookup
            chain_options = []
            try:
                chain = await get_options_with_greeks_tastytrade(ticker, xray.get('expiration'))
                if chain and isinstance(chain, dict):
                    chain_options = chain.get('options', [])
            except Exception:
                pass

            for t in ticker_trades:
                result = _analyze_single_trade(t, xray, chain_options)
                results.append(result)

        except Exception as e:
            logger.error(f"Error analyzing trades for {ticker}: {e}")
            for t in ticker_trades:
                results.append({'error': str(e), 'ticker': ticker,
                                'strike': t.get('strike'), 'signal': 'MANUAL CHECK'})

    return {
        'trades': results,
        'batch_meta': {
            'count': len(results),
            'tickers': list(by_ticker.keys()),
            'timestamp': datetime.now().isoformat()
        }
    }


def is_tastytrade_available() -> bool:
    """Check if Tastytrade OAuth2 credentials are configured."""
    # Unofficial SDK only needs client_secret and refresh_token
    return bool(
        os.environ.get('TASTYTRADE_CLIENT_SECRET') and
        os.environ.get('TASTYTRADE_REFRESH_TOKEN')
    )


# =============================================================================
# POLYGON-COMPATIBLE WRAPPER FUNCTIONS
# These functions provide a Polygon-like interface for Tastytrade data
# =============================================================================

async def get_options_chain_sync_tastytrade(ticker: str, expiration: str = None, target_dte: int = None) -> Optional[Dict]:
    """
    Get options chain in Polygon-compatible format.

    Returns format matching Polygon's options chain response:
    {
        'ticker': str,
        'expiration': str,
        'calls': [...],
        'puts': [...],
        'underlying_price': float,
        'source': 'tastytrade'
    }
    """
    data = await get_options_with_greeks_tastytrade(ticker, expiration, target_dte)
    if not data:
        return None

    # Get underlying price - try Polygon snapshot first (more reliable for equities)
    underlying_price = None
    try:
        from src.data.polygon_provider import get_snapshot_sync
        snapshot = get_snapshot_sync(ticker)
        if snapshot:
            underlying_price = snapshot.get('price') or snapshot.get('last_price')
    except Exception as e:
        logger.warning(f"Polygon snapshot failed for {ticker}: {e}")

    # Fallback to Tastytrade quote streaming
    if not underlying_price:
        quote = get_quote_tastytrade(ticker)
        underlying_price = quote.get('last') if quote else None

    calls = []
    puts = []

    for opt in data.get('options', []):
        strike = float(opt['strike'])
        if opt.get('call'):
            c = opt['call']
            calls.append({
                'strike': strike,  # Alias for compatibility
                'strike_price': strike,
                'expiration_date': data.get('expiration'),
                'contract_type': 'call',
                'ticker': c.get('symbol', ''),
                'implied_volatility': float(c['iv']) if c.get('iv') else None,
                'iv': float(c['iv']) if c.get('iv') else None,  # Alias
                'delta': float(c['delta']) if c.get('delta') else None,
                'gamma': float(c['gamma']) if c.get('gamma') else None,
                'theta': float(c['theta']) if c.get('theta') else None,
                'vega': float(c['vega']) if c.get('vega') else None,
                'open_interest': c.get('open_interest', 0),  # From Summary stream
                'volume': c.get('volume', 0),  # From Summary stream
                'last_price': float(c['price']) if c.get('price') else None,
                'bid': None,
                'ask': None,
                'underlying_price': underlying_price,
            })

        if opt.get('put'):
            p = opt['put']
            puts.append({
                'strike': strike,  # Alias for compatibility
                'strike_price': strike,
                'expiration_date': data.get('expiration'),
                'contract_type': 'put',
                'ticker': p.get('symbol', ''),
                'implied_volatility': float(p['iv']) if p.get('iv') else None,
                'iv': float(p['iv']) if p.get('iv') else None,  # Alias
                'delta': float(p['delta']) if p.get('delta') else None,
                'gamma': float(p['gamma']) if p.get('gamma') else None,
                'theta': float(p['theta']) if p.get('theta') else None,
                'vega': float(p['vega']) if p.get('vega') else None,
                'open_interest': p.get('open_interest', 0),  # From Summary stream
                'volume': p.get('volume', 0),  # From Summary stream
                'last_price': float(p['price']) if p.get('price') else None,
                'bid': None,
                'ask': None,
                'underlying_price': underlying_price,
            })

    return {
        'ticker': ticker.upper(),
        'expiration': data.get('expiration'),
        'dte': data.get('dte'),
        'calls': sorted(calls, key=lambda x: x['strike_price']),
        'puts': sorted(puts, key=lambda x: x['strike_price']),
        'underlying_price': underlying_price,
        'total_call_volume': sum(c.get('volume') or 0 for c in calls),
        'total_put_volume': sum(p.get('volume') or 0 for p in puts),
        'total_call_oi': sum(c.get('open_interest') or 0 for c in calls),
        'total_put_oi': sum(p.get('open_interest') or 0 for p in puts),
        'source': 'tastytrade'
    }


def get_options_flow_sync_tastytrade(ticker: str, target_dte: int = 30) -> Optional[Dict]:
    """
    Get options flow summary in Polygon-compatible format.

    Note: Tastytrade doesn't provide real-time flow data like Polygon,
    so this generates a summary from the current chain state.
    """
    chain = get_options_chain_sync_tastytrade(ticker, target_dte=target_dte)
    if not chain:
        return None

    calls = chain.get('calls', [])
    puts = chain.get('puts', [])

    # Calculate aggregate metrics
    total_call_volume = sum(c.get('volume', 0) for c in calls)
    total_put_volume = sum(p.get('volume', 0) for p in puts)
    total_call_oi = sum(c.get('open_interest', 0) for c in calls)
    total_put_oi = sum(p.get('open_interest', 0) for p in puts)

    # Calculate average IV
    call_ivs = [c['implied_volatility'] for c in calls if c.get('implied_volatility')]
    put_ivs = [p['implied_volatility'] for p in puts if p.get('implied_volatility')]
    avg_call_iv = sum(call_ivs) / len(call_ivs) if call_ivs else None
    avg_put_iv = sum(put_ivs) / len(put_ivs) if put_ivs else None

    # Put/Call ratio
    pc_ratio = total_put_volume / total_call_volume if total_call_volume > 0 else 0
    oi_pc_ratio = total_put_oi / total_call_oi if total_call_oi > 0 else 0

    # Sentiment based on put/call ratio
    if pc_ratio < 0.7:
        sentiment = 'bullish'
        sentiment_score = 70
    elif pc_ratio > 1.3:
        sentiment = 'bearish'
        sentiment_score = 30
    else:
        sentiment = 'neutral'
        sentiment_score = 50

    return {
        'ticker': ticker.upper(),
        'expiration': chain.get('expiration'),
        'dte': chain.get('dte'),
        'underlying_price': chain.get('underlying_price'),
        'total_call_volume': total_call_volume,
        'total_put_volume': total_put_volume,
        'total_call_oi': total_call_oi,
        'total_put_oi': total_put_oi,
        'put_call_ratio': round(pc_ratio, 3),
        'oi_put_call_ratio': round(oi_pc_ratio, 3),
        'avg_call_iv': round(avg_call_iv * 100, 1) if avg_call_iv else None,
        'avg_put_iv': round(avg_put_iv * 100, 1) if avg_put_iv else None,
        'sentiment': sentiment,
        'sentiment_score': sentiment_score,
        'source': 'tastytrade'
    }


def get_unusual_options_sync_tastytrade(ticker: str, target_dte: int = 30) -> Optional[List[Dict]]:
    """
    Detect unusual options activity from Tastytrade chain data.

    Note: Without real-time flow data, this identifies options with
    high IV relative to ATM or unusual Greeks patterns.
    """
    chain = get_options_chain_sync_tastytrade(ticker, target_dte=target_dte)
    if not chain:
        return None

    calls = chain.get('calls', [])
    puts = chain.get('puts', [])
    underlying_price = chain.get('underlying_price')

    if not underlying_price:
        return []

    unusual = []

    # Calculate ATM IV for reference
    atm_call_iv = None
    atm_put_iv = None
    best_diff = float('inf')

    for c in calls:
        diff = abs(c['strike_price'] - underlying_price)
        if diff < best_diff and c.get('implied_volatility'):
            best_diff = diff
            atm_call_iv = c['implied_volatility']

    best_diff = float('inf')
    for p in puts:
        diff = abs(p['strike_price'] - underlying_price)
        if diff < best_diff and p.get('implied_volatility'):
            best_diff = diff
            atm_put_iv = p['implied_volatility']

    atm_iv = (atm_call_iv + atm_put_iv) / 2 if atm_call_iv and atm_put_iv else atm_call_iv or atm_put_iv

    if not atm_iv:
        return []

    # Find options with unusual IV (>1.5x ATM) or high absolute delta OTM
    for opt in calls + puts:
        iv = opt.get('implied_volatility')
        delta = opt.get('delta')
        strike = opt['strike_price']

        if not iv:
            continue

        # Check for elevated IV
        iv_ratio = iv / atm_iv if atm_iv else 1
        is_otm = (opt['contract_type'] == 'call' and strike > underlying_price) or \
                 (opt['contract_type'] == 'put' and strike < underlying_price)

        # Flag as unusual if IV is significantly elevated
        if iv_ratio > 1.3 and is_otm:
            unusual.append({
                'ticker': ticker.upper(),
                'strike': strike,
                'expiration': opt.get('expiration_date'),
                'contract_type': opt['contract_type'],
                'implied_volatility': round(iv * 100, 1),
                'iv_ratio': round(iv_ratio, 2),
                'delta': round(delta, 3) if delta else None,
                'reason': f"IV {round(iv_ratio * 100 - 100)}% above ATM",
                'sentiment': 'bullish' if opt['contract_type'] == 'call' else 'bearish',
                'source': 'tastytrade'
            })

    # Sort by IV ratio
    unusual.sort(key=lambda x: x.get('iv_ratio', 0), reverse=True)

    return unusual[:20]  # Return top 20


# Export all functions
__all__ = [
    'get_tastytrade_session',
    'get_options_with_greeks_tastytrade',
    'get_expirations_tastytrade',
    'get_quote_tastytrade',
    'get_iv_by_delta_tastytrade',
    'get_term_structure_tastytrade',
    'get_expected_move_tastytrade',
    'is_tastytrade_available',
    # Polygon-compatible wrappers
    'get_options_chain_sync_tastytrade',
    'get_options_flow_sync_tastytrade',
    'get_unusual_options_sync_tastytrade',
    # Futures support
    'is_futures_ticker',
    'get_futures_option_chain_tastytrade',
    'get_futures_front_month_symbol',
    # Swing trade tracker
    'analyze_swing_trades',
]
