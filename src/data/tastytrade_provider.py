"""
Tastytrade Data Provider

Provides options chain data, Greeks, and market data from Tastytrade API.
Supports all expirations including 120+ DTE for ratio spread analysis.
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from functools import lru_cache
import asyncio

logger = logging.getLogger(__name__)

# Global session cache
_session = None
_session_expiry = None

def get_tastytrade_session():
    """
    Get or create a Tastytrade session.
    Sessions are cached and reused until they expire.
    """
    global _session, _session_expiry

    # Check if we have a valid cached session
    if _session is not None and _session_expiry and datetime.now() < _session_expiry:
        return _session

    username = os.environ.get('TASTYTRADE_USERNAME')
    password = os.environ.get('TASTYTRADE_PASSWORD')

    if not username or not password:
        logger.warning("TASTYTRADE_USERNAME or TASTYTRADE_PASSWORD not set")
        return None

    try:
        from tastytrade import Session

        logger.info("Creating new Tastytrade session...")
        _session = Session(username, password)
        # Sessions typically last 24 hours, refresh after 23 hours
        _session_expiry = datetime.now() + timedelta(hours=23)
        logger.info("Tastytrade session created successfully")
        return _session

    except Exception as e:
        logger.error(f"Failed to create Tastytrade session: {e}")
        _session = None
        _session_expiry = None
        return None


def get_options_chain_tastytrade(ticker: str) -> Optional[Dict]:
    """
    Get full options chain from Tastytrade including all expirations.

    Returns:
        Dict with structure:
        {
            'ticker': str,
            'expirations': [
                {
                    'date': '2026-06-19',
                    'dte': 134,
                    'strikes': [
                        {
                            'strike': 500.0,
                            'call': { symbol, bid, ask, iv, delta, gamma, theta, vega, oi, volume },
                            'put': { symbol, bid, ask, iv, delta, gamma, theta, vega, oi, volume }
                        },
                        ...
                    ]
                },
                ...
            ]
        }
    """
    session = get_tastytrade_session()
    if not session:
        return None

    try:
        from tastytrade.instruments import get_option_chain, NestedOptionChain
        from tastytrade import DXLinkStreamer
        from tastytrade.dxfeed import Greeks, Quote

        logger.info(f"Fetching options chain for {ticker} from Tastytrade")

        # Get the nested option chain structure
        chain = get_option_chain(session, ticker)

        if not chain:
            logger.warning(f"No options chain found for {ticker}")
            return None

        today = datetime.now().date()
        expirations_data = []

        for expiration in chain.expirations:
            exp_date = expiration.expiration_date
            dte = (exp_date - today).days

            strikes_data = []
            for strike in expiration.strikes:
                strike_data = {
                    'strike': float(strike.strike_price),
                    'call': None,
                    'put': None
                }

                # Get call data
                if strike.call:
                    strike_data['call'] = {
                        'symbol': strike.call,
                        'bid': None,
                        'ask': None,
                        'iv': None,
                        'delta': None,
                        'gamma': None,
                        'theta': None,
                        'vega': None,
                        'oi': None,
                        'volume': None
                    }

                # Get put data
                if strike.put:
                    strike_data['put'] = {
                        'symbol': strike.put,
                        'bid': None,
                        'ask': None,
                        'iv': None,
                        'delta': None,
                        'gamma': None,
                        'theta': None,
                        'vega': None,
                        'oi': None,
                        'volume': None
                    }

                strikes_data.append(strike_data)

            expirations_data.append({
                'date': exp_date.strftime('%Y-%m-%d'),
                'dte': dte,
                'strikes': strikes_data
            })

        # Sort by DTE
        expirations_data.sort(key=lambda x: x['dte'])

        logger.info(f"Found {len(expirations_data)} expirations for {ticker}")

        return {
            'ticker': ticker.upper(),
            'expirations': expirations_data
        }

    except Exception as e:
        logger.error(f"Error fetching Tastytrade options chain for {ticker}: {e}")
        return None


def get_options_with_greeks_tastytrade(ticker: str, expiration: str = None, target_dte: int = None) -> Optional[Dict]:
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
        from tastytrade.instruments import get_option_chain, Option
        from tastytrade import DXLinkStreamer
        from tastytrade.dxfeed import Greeks, Quote

        logger.info(f"Fetching options with Greeks for {ticker} (target_dte={target_dte})")

        # Get the option chain
        chain = get_option_chain(session, ticker)
        if not chain:
            return None

        today = datetime.now().date()

        # Find the target expiration
        target_exp = None

        if expiration:
            # Use specified expiration
            for exp in chain.expirations:
                if exp.expiration_date.strftime('%Y-%m-%d') == expiration:
                    target_exp = exp
                    break
        elif target_dte:
            # Find closest to target DTE
            best_diff = float('inf')
            for exp in chain.expirations:
                dte = (exp.expiration_date - today).days
                diff = abs(dte - target_dte)
                if diff < best_diff:
                    best_diff = diff
                    target_exp = exp
        else:
            # Default to first available expiration > 7 DTE
            for exp in chain.expirations:
                dte = (exp.expiration_date - today).days
                if dte >= 7:
                    target_exp = exp
                    break

        if not target_exp:
            logger.warning(f"No suitable expiration found for {ticker}")
            return None

        exp_date = target_exp.expiration_date
        dte = (exp_date - today).days

        logger.info(f"Using expiration {exp_date} ({dte} DTE)")

        # Collect all option symbols for streaming
        call_symbols = []
        put_symbols = []
        strikes = []

        for strike in target_exp.strikes:
            strikes.append(float(strike.strike_price))
            if strike.call:
                call_symbols.append(strike.call)
            if strike.put:
                put_symbols.append(strike.put)

        # Stream Greeks for all options
        greeks_data = {}
        quotes_data = {}

        async def fetch_greeks():
            async with DXLinkStreamer(session) as streamer:
                all_symbols = call_symbols + put_symbols

                # Subscribe to Greeks
                await streamer.subscribe(Greeks, all_symbols)

                # Collect data (with timeout)
                received = 0
                target = len(all_symbols)

                async for greek in streamer.listen(Greeks):
                    greeks_data[greek.eventSymbol] = {
                        'iv': greek.volatility,
                        'delta': greek.delta,
                        'gamma': greek.gamma,
                        'theta': greek.theta,
                        'vega': greek.vega,
                        'price': greek.price
                    }
                    received += 1
                    if received >= target:
                        break

        # Run async fetch
        try:
            asyncio.run(fetch_greeks())
        except Exception as e:
            logger.warning(f"Error streaming Greeks: {e}")

        # Build response
        options_data = []
        for strike in target_exp.strikes:
            strike_price = float(strike.strike_price)

            call_data = None
            put_data = None

            if strike.call and strike.call in greeks_data:
                g = greeks_data[strike.call]
                call_data = {
                    'symbol': strike.call,
                    'strike': strike_price,
                    'type': 'call',
                    'iv': g.get('iv'),
                    'delta': g.get('delta'),
                    'gamma': g.get('gamma'),
                    'theta': g.get('theta'),
                    'vega': g.get('vega'),
                    'price': g.get('price')
                }

            if strike.put and strike.put in greeks_data:
                g = greeks_data[strike.put]
                put_data = {
                    'symbol': strike.put,
                    'strike': strike_price,
                    'type': 'put',
                    'iv': g.get('iv'),
                    'delta': abs(g.get('delta', 0)),  # Put delta as positive
                    'gamma': g.get('gamma'),
                    'theta': g.get('theta'),
                    'vega': g.get('vega'),
                    'price': g.get('price')
                }

            options_data.append({
                'strike': strike_price,
                'call': call_data,
                'put': put_data
            })

        return {
            'ticker': ticker.upper(),
            'expiration': exp_date.strftime('%Y-%m-%d'),
            'dte': dte,
            'options': options_data,
            'source': 'tastytrade'
        }

    except Exception as e:
        logger.error(f"Error fetching Tastytrade Greeks for {ticker}: {e}")
        return None


def get_expirations_tastytrade(ticker: str) -> Optional[List[Dict]]:
    """
    Get all available expirations for a ticker.

    Returns:
        List of dicts with 'date' and 'dte' keys
    """
    session = get_tastytrade_session()
    if not session:
        return None

    try:
        from tastytrade.instruments import get_option_chain

        chain = get_option_chain(session, ticker)
        if not chain:
            return None

        today = datetime.now().date()
        expirations = []

        for exp in chain.expirations:
            exp_date = exp.expiration_date
            dte = (exp_date - today).days
            expirations.append({
                'date': exp_date.strftime('%Y-%m-%d'),
                'dte': dte
            })

        # Sort by DTE
        expirations.sort(key=lambda x: x['dte'])

        return expirations

    except Exception as e:
        logger.error(f"Error fetching Tastytrade expirations for {ticker}: {e}")
        return None


def get_quote_tastytrade(ticker: str) -> Optional[Dict]:
    """
    Get current quote for a ticker.
    """
    session = get_tastytrade_session()
    if not session:
        return None

    try:
        from tastytrade import DXLinkStreamer
        from tastytrade.dxfeed import Quote

        quote_data = {}

        async def fetch_quote():
            async with DXLinkStreamer(session) as streamer:
                await streamer.subscribe(Quote, [ticker])
                async for quote in streamer.listen(Quote):
                    quote_data['bid'] = quote.bidPrice
                    quote_data['ask'] = quote.askPrice
                    quote_data['last'] = (quote.bidPrice + quote.askPrice) / 2
                    break

        asyncio.run(fetch_quote())

        return quote_data if quote_data else None

    except Exception as e:
        logger.error(f"Error fetching Tastytrade quote for {ticker}: {e}")
        return None


def get_iv_by_delta_tastytrade(ticker: str, expiration: str = None, target_dte: int = 120) -> Optional[Dict]:
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
    data = get_options_with_greeks_tastytrade(ticker, expiration, target_dte)
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
            delta = put['delta']
            iv = put['iv']

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
            delta = call['delta']
            iv = call['iv']

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


def get_term_structure_tastytrade(ticker: str, front_dte: int = 30, back_dte: int = 120) -> Optional[Dict]:
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
    front_data = get_iv_by_delta_tastytrade(ticker, target_dte=front_dte)
    if not front_data or not front_data.get('atm_iv'):
        return None

    # Get back month IV
    back_data = get_iv_by_delta_tastytrade(ticker, target_dte=back_dte)
    if not back_data or not back_data.get('atm_iv'):
        return None

    front_iv = front_data['atm_iv']
    back_iv = back_data['atm_iv']

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


def get_expected_move_tastytrade(ticker: str, target_dte: int = 120) -> Optional[Dict]:
    """
    Calculate expected move for a specific DTE.

    Uses ATM straddle price × 0.85 for expected move.
    """
    data = get_options_with_greeks_tastytrade(ticker, target_dte=target_dte)
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
                current_price = opt['strike']
                break

    if not current_price:
        return None

    # Find ATM strike
    atm_strike = None
    atm_call_price = None
    atm_put_price = None
    best_diff = float('inf')

    for opt in data['options']:
        diff = abs(opt['strike'] - current_price)
        if diff < best_diff:
            best_diff = diff
            atm_strike = opt['strike']
            if opt.get('call'):
                atm_call_price = opt['call'].get('price')
            if opt.get('put'):
                atm_put_price = opt['put'].get('price')

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


def is_tastytrade_available() -> bool:
    """Check if Tastytrade credentials are configured."""
    return bool(os.environ.get('TASTYTRADE_USERNAME') and os.environ.get('TASTYTRADE_PASSWORD'))


# Export all functions
__all__ = [
    'get_tastytrade_session',
    'get_options_chain_tastytrade',
    'get_options_with_greeks_tastytrade',
    'get_expirations_tastytrade',
    'get_quote_tastytrade',
    'get_iv_by_delta_tastytrade',
    'get_term_structure_tastytrade',
    'get_expected_move_tastytrade',
    'is_tastytrade_available'
]
