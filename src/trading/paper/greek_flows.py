"""
Greek Flows — Vanna, Charm, and Combined Dealer Flow Forecast.

Phase 2a: Vanna + Charm Exposure Engine
Phase 2b: Combined Dealer Flow Forecast (GEX + Vanna + Charm)

All formulas derived from BSM framework:
  Vanna = -n(d1) * d2 / sigma
  Charm = -n(d1) * [r/(sigma*sqrt(T)) - d2/(2T)]
  n(x)  = (1/sqrt(2*pi)) * exp(-x^2/2)
  d1    = [ln(S/K) + (r + sigma^2/2)*T] / (sigma*sqrt(T))
  d2    = d1 - sigma*sqrt(T)
"""

import math
import logging
from typing import Dict, List, Optional
from datetime import date

logger = logging.getLogger(__name__)

# Standard normal PDF
def _norm_pdf(x: float) -> float:
    return (1.0 / math.sqrt(2 * math.pi)) * math.exp(-0.5 * x * x)


def _compute_d1_d2(S: float, K: float, T: float, sigma: float, r: float = 0.05) -> tuple:
    """Compute d1 and d2 from BSM."""
    if S <= 0 or K <= 0 or T <= 0 or sigma <= 0:
        return 0, 0
    d1 = (math.log(S / K) + (r + sigma ** 2 / 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    return d1, d2


# =============================================================================
# Per-Option Greek Calculations
# =============================================================================

def compute_vanna(S: float, K: float, T: float, sigma: float, r: float = 0.05) -> float:
    """
    Vanna = dDelta/dsigma = dVega/dS = -n(d1) * d2 / sigma
    Units: change in delta per 1 unit change in sigma (absolute)
    """
    if sigma <= 0 or T <= 0 or S <= 0 or K <= 0:
        return 0.0
    d1, d2 = _compute_d1_d2(S, K, T, sigma, r)
    return -_norm_pdf(d1) * d2 / sigma


def compute_charm(S: float, K: float, T: float, sigma: float, r: float = 0.05) -> float:
    """
    Charm = dDelta/dt (per day of time passing)
    Charm_call = -n(d1) * [2*r*T - d2*sigma*sqrt(T)] / [2*T*sigma*sqrt(T)]

    Positive charm for OTM calls = delta decays toward 0
    Negative charm for ITM calls = delta approaches 1
    """
    if sigma <= 0 or T <= 0 or S <= 0 or K <= 0:
        return 0.0
    d1, d2 = _compute_d1_d2(S, K, T, sigma, r)
    sqrt_T = math.sqrt(T)
    denom = 2 * T * sigma * sqrt_T
    if abs(denom) < 1e-12:
        return 0.0
    charm = -_norm_pdf(d1) * (2 * r * T - d2 * sigma * sqrt_T) / denom
    # Convert from per-year to per-day
    return charm / 365.0


def compute_volga(S: float, K: float, T: float, sigma: float, r: float = 0.05) -> float:
    """
    Volga = dVega/dsigma = Vega * (d1*d2) / sigma
    Volga = S * sqrt(T) * n(d1) * d1 * d2 / sigma
    """
    if sigma <= 0 or T <= 0 or S <= 0 or K <= 0:
        return 0.0
    d1, d2 = _compute_d1_d2(S, K, T, sigma, r)
    vega = S * math.sqrt(T) * _norm_pdf(d1)
    return vega * d1 * d2 / sigma


# =============================================================================
# Phase 2a: Aggregate Exposure Calculations
# =============================================================================

def calculate_vanna_exposure(
    current_price: float,
    options: list,
    dte: int,
    multiplier: int = 100,
    r: float = 0.05,
) -> Dict:
    """
    Calculate aggregate Vanna Exposure across all strikes.
    Similar pattern to GEX calculation.

    Returns total vanna exposure and per-strike breakdown.
    """
    if not options or current_price <= 0 or dte <= 0:
        return {'total_vanna_exposure': 0, 'vanna_by_strike': [], 'error': 'Insufficient data'}

    T = dte / 365.0
    vanna_by_strike = []
    total_vanna = 0.0

    for o in options:
        strike = float(o.get('strike', 0))
        if strike <= 0:
            continue

        call = o.get('call', {})
        put = o.get('put', {})

        call_oi = float(call.get('open_interest', 0) or 0)
        put_oi = float(put.get('open_interest', 0) or 0)
        call_iv = float(call.get('iv', 0) or 0)
        put_iv = float(put.get('iv', 0) or 0)

        # Use provider IV, fallback to ATM estimate
        sigma_call = call_iv if call_iv > 0 else 0.25
        sigma_put = put_iv if put_iv > 0 else 0.25

        # Per-contract vanna
        call_vanna = compute_vanna(current_price, strike, T, sigma_call, r)
        put_vanna = compute_vanna(current_price, strike, T, sigma_put, r)

        # Dealer vanna exposure:
        # Dealers are typically SHORT options (they sell to customers)
        # So dealer vanna = -customer_vanna * OI * multiplier * S
        # When IV drops: dealer delta from calls decreases (sell underlying)
        #                dealer delta from puts becomes less negative (buy underlying)
        # Net effect depends on aggregate OI imbalance
        call_vanna_exp = -call_vanna * call_oi * multiplier * current_price / 100
        put_vanna_exp = -put_vanna * put_oi * multiplier * current_price / 100  # Same dealer-short convention as calls
        net_vanna = call_vanna_exp + put_vanna_exp

        vanna_by_strike.append({
            'strike': strike,
            'call_vanna_exp': round(call_vanna_exp, 2),
            'put_vanna_exp': round(put_vanna_exp, 2),
            'net_vanna': round(net_vanna, 2),
            'call_oi': int(call_oi),
            'put_oi': int(put_oi),
        })
        total_vanna += net_vanna

    # Find key vanna levels
    vanna_sorted = sorted(vanna_by_strike, key=lambda x: abs(x['net_vanna']), reverse=True)
    max_vanna_strike = vanna_sorted[0]['strike'] if vanna_sorted else 0
    max_vanna_call = max(vanna_by_strike, key=lambda x: x['call_vanna_exp'])['strike'] if vanna_by_strike else 0
    max_vanna_put = min(vanna_by_strike, key=lambda x: x['put_vanna_exp'])['strike'] if vanna_by_strike else 0

    return {
        'total_vanna_exposure': round(total_vanna, 2),
        'vanna_billions': round(total_vanna / 1e9, 4),
        'vanna_by_strike': vanna_by_strike,
        'max_vanna_strike': max_vanna_strike,
        'max_call_vanna_strike': max_vanna_call,
        'max_put_vanna_strike': max_vanna_put,
        'current_price': current_price,
        'dte': dte,
        'interpretation': _interpret_vanna(total_vanna, current_price),
    }


def calculate_charm_exposure(
    current_price: float,
    options: list,
    dte: int,
    multiplier: int = 100,
    r: float = 0.05,
) -> Dict:
    """
    Calculate aggregate Charm Exposure across all strikes.
    Charm = how delta changes with time passage.
    """
    if not options or current_price <= 0 or dte <= 0:
        return {'total_charm_exposure': 0, 'charm_by_strike': [], 'error': 'Insufficient data'}

    T = dte / 365.0
    charm_by_strike = []
    total_charm = 0.0

    for o in options:
        strike = float(o.get('strike', 0))
        if strike <= 0:
            continue

        call = o.get('call', {})
        put = o.get('put', {})

        call_oi = float(call.get('open_interest', 0) or 0)
        put_oi = float(put.get('open_interest', 0) or 0)
        call_iv = float(call.get('iv', 0) or 0)
        put_iv = float(put.get('iv', 0) or 0)

        sigma_call = call_iv if call_iv > 0 else 0.25
        sigma_put = put_iv if put_iv > 0 else 0.25

        # Per-contract charm (delta change per day)
        call_charm = compute_charm(current_price, strike, T, sigma_call, r)
        put_charm = compute_charm(current_price, strike, T, sigma_put, r)

        # Dealer charm exposure:
        # Dealers short options → charm tells how much delta they must rebalance per day
        # Positive charm on short call = delta decaying → dealer sells underlying
        # Negative charm on short put = put delta strengthening → dealer buys underlying
        call_charm_exp = -call_charm * call_oi * multiplier * current_price / 100
        put_charm_exp = -put_charm * put_oi * multiplier * current_price / 100  # Same dealer-short convention as calls
        net_charm = call_charm_exp + put_charm_exp

        charm_by_strike.append({
            'strike': strike,
            'call_charm_exp': round(call_charm_exp, 2),
            'put_charm_exp': round(put_charm_exp, 2),
            'net_charm': round(net_charm, 2),
            'call_oi': int(call_oi),
            'put_oi': int(put_oi),
        })
        total_charm += net_charm

    # Key charm levels
    charm_sorted = sorted(charm_by_strike, key=lambda x: abs(x['net_charm']), reverse=True)
    max_charm_strike = charm_sorted[0]['strike'] if charm_sorted else 0

    return {
        'total_charm_exposure': round(total_charm, 2),
        'charm_billions': round(total_charm / 1e9, 4),
        'charm_by_strike': charm_by_strike,
        'max_charm_strike': max_charm_strike,
        'current_price': current_price,
        'dte': dte,
        'interpretation': _interpret_charm(total_charm, dte, current_price),
    }


# =============================================================================
# Phase 2b: Combined Dealer Flow Forecast
# =============================================================================

def compute_dealer_flow_forecast(
    gex_data: Dict,
    vanna_data: Dict,
    charm_data: Dict,
    dte: int,
    iv_change_1d: float = 0,  # Recent 1-day IV change
) -> Dict:
    """
    Combine GEX + Vanna + Charm into a unified dealer flow forecast.

    Time-weighting:
    - Near OpEx (DTE < 7): Charm dominates (delta decay accelerates)
    - After vol spike (|IV change| > 2%): Vanna dominates (delta-vol rehedging)
    - Steady state: GEX dominates (ongoing gamma hedging)
    """
    total_gex = gex_data.get('total_gex', 0) if gex_data else 0
    total_vanna = vanna_data.get('total_vanna_exposure', 0) if vanna_data else 0
    total_charm = charm_data.get('total_charm_exposure', 0) if charm_data else 0

    # Time-weighted blending
    if dte <= 3:
        # Expiration imminent: charm is everything
        w_gex, w_vanna, w_charm = 0.2, 0.1, 0.7
    elif dte <= 7:
        # Expiration week: charm dominates
        w_gex, w_vanna, w_charm = 0.3, 0.2, 0.5
    elif abs(iv_change_1d) > 2:
        # Vol spike: vanna dominates
        w_gex, w_vanna, w_charm = 0.2, 0.6, 0.2
    elif abs(iv_change_1d) > 1:
        # Moderate vol change: balanced vanna/gex
        w_gex, w_vanna, w_charm = 0.3, 0.4, 0.3
    else:
        # Steady state: GEX is primary
        w_gex, w_vanna, w_charm = 0.5, 0.3, 0.2

    # Normalize to billions for comparison
    gex_b = total_gex / 1e9
    vanna_b = total_vanna / 1e9
    charm_b = total_charm / 1e9

    # Weighted net flow (in billions)
    net_flow = w_gex * gex_b + w_vanna * vanna_b + w_charm * charm_b

    # Direction
    if net_flow > 0.1:
        direction = 'net_buying'
        action = 'Dealers must BUY underlying to maintain hedges'
    elif net_flow < -0.1:
        direction = 'net_selling'
        action = 'Dealers must SELL underlying to maintain hedges'
    else:
        direction = 'balanced'
        action = 'Dealer flows approximately balanced'

    # Magnitude
    abs_flow = abs(net_flow)
    if abs_flow > 2.0:
        magnitude = 'extreme'
    elif abs_flow > 1.0:
        magnitude = 'strong'
    elif abs_flow > 0.3:
        magnitude = 'moderate'
    else:
        magnitude = 'weak'

    # Score (0-100): 50 = neutral, >50 = bullish flow, <50 = bearish flow
    # Using tanh to map unbounded flow to bounded score
    flow_score = round(50 + 50 * max(-1, min(1, math.tanh(net_flow * 2))))

    # Dominant driver
    components = {
        'gex': abs(gex_b * w_gex),
        'vanna': abs(vanna_b * w_vanna),
        'charm': abs(charm_b * w_charm),
    }
    dominant = max(components, key=components.get)

    return {
        'net_flow_billions': round(net_flow, 4),
        'direction': direction,
        'magnitude': magnitude,
        'action': action,
        'flow_score': flow_score,
        'dominant_driver': dominant,
        'weights': {'gex': w_gex, 'vanna': w_vanna, 'charm': w_charm},
        'components': {
            'gex_billions': round(gex_b, 4),
            'vanna_billions': round(vanna_b, 4),
            'charm_billions': round(charm_b, 4),
        },
        'gex_contribution': round(gex_b * w_gex, 4),
        'vanna_contribution': round(vanna_b * w_vanna, 4),
        'charm_contribution': round(charm_b * w_charm, 4),
        'iv_change_1d': round(iv_change_1d, 2),
        'dte': dte,
    }


# =============================================================================
# Interpretation Helpers
# =============================================================================

def _interpret_vanna(total_vanna: float, current_price: float) -> str:
    vanna_b = total_vanna / 1e9
    if abs(vanna_b) < 0.1:
        return 'Vanna exposure is minimal — IV changes will have limited dealer rehedging impact.'
    if vanna_b > 0:
        return (
            f'Positive vanna exposure (${vanna_b:.2f}B). '
            'If IV drops, dealers must BUY underlying (bullish vanna flow). '
            'If IV rises, dealers must SELL (bearish vanna flow).'
        )
    return (
        f'Negative vanna exposure (${vanna_b:.2f}B). '
        'If IV drops, dealers must SELL underlying (bearish vanna flow). '
        'If IV rises, dealers must BUY (bullish vanna flow).'
    )


def _interpret_charm(total_charm: float, dte: int, current_price: float) -> str:
    charm_b = total_charm / 1e9
    urgency = 'accelerating rapidly' if dte <= 7 else ('building' if dte <= 21 else 'gradual')
    if abs(charm_b) < 0.05:
        return f'Charm exposure is minimal. Delta decay {urgency} ({dte} DTE).'
    if charm_b > 0:
        return (
            f'Positive charm exposure (${charm_b:.2f}B/day). '
            f'Dealers must BUY ${abs(charm_b):.2f}B/day as time passes. '
            f'Decay is {urgency} ({dte} DTE).'
        )
    return (
        f'Negative charm exposure (${charm_b:.2f}B/day). '
        f'Dealers must SELL ${abs(charm_b):.2f}B/day as time passes. '
        f'Decay is {urgency} ({dte} DTE).'
    )
