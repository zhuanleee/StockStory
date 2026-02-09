"""
Strategy Builder — Constructs multi-leg option orders from strategy recommendations.

Uses delta-based strike selection, adaptive wing widths, liquidity filtering,
and Greek scoring to build optimal multi-leg structures from live chain data.

Chain data format (from get_options_with_greeks_tastytrade):
  options[]: {strike, call: {delta, gamma, theta, vega, iv, price, open_interest, volume},
                      put:  {delta, gamma, theta, vega, iv, price, open_interest, volume}}
  Note: put deltas are stored as abs(delta) in the chain.
"""

import logging
import math
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Liquidity thresholds
MIN_OI = 50
MIN_PRICE = 0.05
PREF_OI = 500

# Wing width as % of underlying
MIN_WING_PCT = 0.5
MAX_WING_PCT = 3.0
DEFAULT_WING_PCT = 1.0


class StrategyBuilder:
    """Builds multi-leg option structures using Greeks, liquidity, and IV data."""

    def build_legs(
        self,
        strategy_name: str,
        ticker: str,
        direction: str,
        chain_data: Dict,
        underlying_price: float,
        delta_target: float = None,
        iv_rank: float = None,
        dte: int = None,
    ) -> Dict:
        """
        Build leg definitions for a given strategy using delta-based selection.

        Args:
            strategy_name: From StrategySelector
            ticker: Underlying symbol
            direction: From strategy selector (bullish/bearish/neutral/etc.)
            chain_data: From get_options_with_greeks_tastytrade()
            underlying_price: Current underlying price
            delta_target: Target delta from StrategySelector (e.g., 0.16)
            iv_rank: Current IV Rank (0-100) for context
            dte: Days to expiration of the chain

        Returns:
            Dict with legs, strategy_name, max_loss, max_profit, net_premium,
            greeks, quality_score, notes
        """
        options = chain_data.get('options', [])
        expiration = chain_data.get('expiration', '')

        if not options or not expiration:
            return self._build_single_leg(
                ticker, direction, underlying_price, expiration, chain_data, delta_target,
            )

        calls = self._extract_options(options, 'call')
        puts = self._extract_options(options, 'put')
        wing_width = self._adaptive_wing_width(underlying_price, options)

        name_lower = strategy_name.lower()

        if 'credit spread' in name_lower or 'premium harvest' in name_lower or 'vrp harvest' in name_lower or 'backwardation credit' in name_lower:
            return self._build_credit_spread(
                ticker, direction, calls, puts, underlying_price, expiration,
                delta_target or 0.16, wing_width, iv_rank, dte,
            )
        elif 'iron butterfly' in name_lower:
            return self._build_iron_butterfly(
                ticker, calls, puts, underlying_price, expiration,
                wing_width, iv_rank, dte,
            )
        elif 'iron condor' in name_lower or 'range bound' in name_lower:
            return self._build_iron_condor(
                ticker, calls, puts, underlying_price, expiration,
                delta_target or 0.16, wing_width, iv_rank, dte,
            )
        elif 'straddle' in name_lower or 'event vol' in name_lower:
            return self._build_straddle(
                ticker, calls, puts, underlying_price, expiration, iv_rank, dte,
            )
        elif 'debit spread' in name_lower or 'melt-up' in name_lower or 'bear put' in name_lower:
            return self._build_debit_spread(
                ticker, direction, calls, puts, underlying_price, expiration,
                delta_target or 0.40, wing_width, iv_rank, dte,
            )
        elif 'ratio spread' in name_lower or 'skew harvest' in name_lower:
            return self._build_ratio_spread(
                ticker, direction, calls, puts, underlying_price, expiration,
                delta_target or 0.25, wing_width, iv_rank, dte,
            )
        else:
            return self._build_single_leg(
                ticker, direction, underlying_price, expiration, chain_data, delta_target,
            )

    # -----------------------------------------------------------------
    # Option data extraction
    # -----------------------------------------------------------------

    def _extract_options(self, options: list, opt_type: str) -> List[Dict]:
        """Extract and enrich options of one type from chain data."""
        result = []
        for opt in options:
            side = opt.get(opt_type)
            if not side:
                continue
            delta = side.get('delta')
            if delta is None:
                continue

            price = float(side.get('price', 0) or 0)
            oi = int(side.get('open_interest', 0) or 0)
            volume = int(side.get('volume', 0) or 0)
            gamma = float(side.get('gamma', 0) or 0)
            theta = float(side.get('theta', 0) or 0)
            vega = float(side.get('vega', 0) or 0)
            iv = float(side.get('iv', 0) or 0)

            theta_abs = abs(theta) if theta else 0.001
            result.append({
                'strike': opt['strike'],
                'delta': float(delta),
                'gamma': gamma,
                'theta': theta,
                'vega': vega,
                'iv': iv,
                'price': price,
                'oi': oi,
                'volume': volume,
                'type': opt_type,
                'gamma_theta_ratio': gamma / theta_abs,
                'liquid': oi >= MIN_OI and price >= MIN_PRICE,
            })

        result.sort(key=lambda x: x['strike'])
        return result

    # -----------------------------------------------------------------
    # Delta-based strike selection
    # -----------------------------------------------------------------

    def _find_by_delta(self, options: List[Dict], target_delta: float,
                       prefer_liquid: bool = True) -> Optional[Dict]:
        """Find option closest to target delta, preferring liquid strikes."""
        if not options:
            return None
        liquid = [o for o in options if o['liquid']] if prefer_liquid else options
        candidates = liquid if liquid else options
        return min(candidates, key=lambda o: abs(o['delta'] - target_delta))

    def _find_by_strike(self, options: List[Dict], target_strike: float) -> Optional[Dict]:
        """Find option closest to a target strike."""
        if not options:
            return None
        return min(options, key=lambda o: abs(o['strike'] - target_strike))

    def _find_wing(self, options: List[Dict], anchor_strike: float,
                   wing_width: float, direction: str) -> Optional[Dict]:
        """Find wing option at anchor ± wing_width, preferring liquid strikes."""
        target = anchor_strike + wing_width if direction == 'higher' else anchor_strike - wing_width
        if direction == 'higher':
            valid = [o for o in options if o['strike'] > anchor_strike]
        else:
            valid = [o for o in options if o['strike'] < anchor_strike]

        if not valid:
            return None
        liquid = [o for o in valid if o['liquid']]
        pool = liquid if liquid else valid
        return min(pool, key=lambda o: abs(o['strike'] - target))

    # -----------------------------------------------------------------
    # Adaptive wing width
    # -----------------------------------------------------------------

    def _adaptive_wing_width(self, underlying_price: float, options: list) -> float:
        """Wing width as ~1% of underlying, snapped to available strike spacing."""
        target = underlying_price * (DEFAULT_WING_PCT / 100)
        strikes = sorted(set(opt['strike'] for opt in options if 'strike' in opt))
        if len(strikes) < 2:
            return target

        atm_idx = min(range(len(strikes)), key=lambda i: abs(strikes[i] - underlying_price))
        spacings = []
        lo = max(0, atm_idx - 5)
        hi = min(len(strikes) - 1, atm_idx + 5)
        for i in range(lo, hi):
            spacings.append(strikes[i + 1] - strikes[i])

        if not spacings:
            return target
        typical = sorted(spacings)[len(spacings) // 2]  # median
        n = max(1, round(target / typical))
        width = n * typical
        return max(underlying_price * MIN_WING_PCT / 100,
                   min(width, underlying_price * MAX_WING_PCT / 100))

    # -----------------------------------------------------------------
    # Greek helpers
    # -----------------------------------------------------------------

    def _leg_greeks(self, opt: Dict, action: str, opt_type: str,
                    qty: int = 1, dte: int = None) -> Dict:
        """Position Greeks for one leg, accounting for put sign convention.
        Chain stores abs(delta) for puts; real put delta is negative.
        If dte provided, also computes vega_30d (vega normalized to 30-DTE)."""
        sign = 1 if action == 'BUY' else -1
        delta = opt['delta']
        if opt_type == 'put':
            delta = -delta  # convert abs → real
        raw_vega = sign * opt['vega'] * qty
        result = {
            'delta': round(sign * delta * qty, 4),
            'gamma': round(sign * opt['gamma'] * qty, 4),
            'theta': round(sign * opt['theta'] * qty, 4),
            'vega': round(raw_vega, 4),
        }
        # DTE-normalized vega: vega scales as √T, normalize to 30-DTE equivalent
        if dte and dte > 0:
            result['vega_30d'] = round(raw_vega * math.sqrt(30 / dte), 4)
        return result

    def _sum_greeks(self, greek_list: list) -> Dict:
        """Sum a list of per-leg Greeks dicts."""
        net = {'delta': 0, 'gamma': 0, 'theta': 0, 'vega': 0, 'vega_30d': 0}
        has_vega_30d = False
        for g in greek_list:
            for k in ('delta', 'gamma', 'theta', 'vega'):
                net[k] += g.get(k, 0)
            if 'vega_30d' in g:
                net['vega_30d'] += g['vega_30d']
                has_vega_30d = True
        result = {k: round(v, 4) for k, v in net.items()}
        if not has_vega_30d:
            del result['vega_30d']
        return result

    # -----------------------------------------------------------------
    # Quality scoring
    # -----------------------------------------------------------------

    def _liquidity_score(self, opt: Dict) -> float:
        """Composite liquidity score (0-30) from OI + spread proxy.
        Spread proxy: options with high OI + volume + moderate IV tend
        to have tighter bid-ask spreads."""
        oi_score = min(15, (opt['oi'] / PREF_OI) * 15)
        # Spread proxy: volume/OI ratio as turnover signal + IV penalty for wide markets
        vol = opt.get('volume', 0)
        oi = max(1, opt['oi'])
        turnover = min(1.0, vol / oi)  # 0-1: higher = tighter spread
        iv_penalty = max(0, opt['iv'] - 0.5) * 5  # high IV = wider spreads
        spread_proxy = min(15, turnover * 15 - iv_penalty)
        return oi_score + max(0, spread_proxy)

    def _score_for_selling(self, opt: Dict) -> float:
        """Score an option for selling (credit). Higher = better to sell."""
        s = 0
        s += min(30, abs(opt['theta']) * 100)        # high theta decay
        s += self._liquidity_score(opt)               # OI + spread proxy (0-30)
        s += min(20, opt['iv'] * 50)                  # rich IV = more premium
        s += min(15, opt['price'] * 3)                 # meaningful premium
        return s

    def _score_for_buying(self, opt: Dict) -> float:
        """Score an option for buying (debit). Higher = better to buy."""
        s = 0
        s += min(30, opt['gamma_theta_ratio'] * 300)  # gamma leverage
        s += max(0, 30 - opt['iv'] * 80)              # cheap IV
        s += self._liquidity_score(opt)               # OI + spread proxy (0-30)
        s += min(20, opt['vega'] * 40)                 # vega exposure
        return s

    # -----------------------------------------------------------------
    # Strategy builders
    # -----------------------------------------------------------------

    def _build_credit_spread(
        self, ticker, direction, calls, puts, price, expiration,
        delta_target, wing_width, iv_rank, dte,
    ) -> Dict:
        """Credit spread: sell at delta_target + buy further OTM wing."""
        # Call credit spread for bearish; put credit spread for bullish/neutral
        if direction in ('bearish', 'neutral_bearish'):
            opt_type = 'call'
            opts = calls
            short = self._find_by_delta(opts, delta_target)
            if not short:
                return self._fail(ticker, 'Credit Spread', 'No short strike')
            long = self._find_wing(opts, short['strike'], wing_width, 'higher')
        else:
            opt_type = 'put'
            opts = puts
            short = self._find_by_delta(opts, delta_target)
            if not short:
                return self._fail(ticker, 'Credit Spread', 'No short strike')
            long = self._find_wing(opts, short['strike'], wing_width, 'lower')

        if not long:
            return self._fail(ticker, 'Credit Spread', 'No wing strike')

        net = short['price'] - long['price']
        width = abs(short['strike'] - long['strike'])
        if net <= 0:
            return self._fail(ticker, 'Credit Spread', f'No credit (net {net:.2f})')

        max_profit = net * 100
        max_loss = (width - net) * 100
        prob_otm = (1 - short['delta']) * 100

        greeks = self._sum_greeks([
            self._leg_greeks(short, 'SELL', opt_type, dte=dte),
            self._leg_greeks(long, 'BUY', opt_type, dte=dte),
        ])

        quality = (
            self._score_for_selling(short) * 0.5
            + (net / width * 40 if width > 0 else 0)
            + min(20, prob_otm / 5)
        )

        notes = (
            f"Sell {short['delta']:.0%}Δ {opt_type} ${short['strike']} "
            f"(OI:{short['oi']}, IV:{short['iv']:.1%}, θ:{short['theta']:.3f}), "
            f"Buy ${long['strike']} (OI:{long['oi']}). "
            f"Width ${width:.0f}, Credit ${net:.2f}, "
            f"P(OTM) ~{prob_otm:.0f}%."
        )

        legs = [
            {'action': 'SELL', 'option_type': opt_type, 'strike': short['strike'],
             'expiration': expiration, 'quantity': 1},
            {'action': 'BUY', 'option_type': opt_type, 'strike': long['strike'],
             'expiration': expiration, 'quantity': 1},
        ]

        return self._result(
            legs, f"Credit Spread ({opt_type.upper()} {short['strike']}/{long['strike']})",
            max_loss, max_profit, net, greeks, quality, notes,
        )

    def _build_iron_condor(
        self, ticker, calls, puts, price, expiration,
        delta_target, wing_width, iv_rank, dte,
    ) -> Dict:
        """Iron condor: sell strangle at delta_target + buy wings."""
        short_put = self._find_by_delta(puts, delta_target)
        short_call = self._find_by_delta(calls, delta_target)
        if not short_put or not short_call:
            return self._fail(ticker, 'Iron Condor', 'No short strikes')

        long_put = self._find_wing(puts, short_put['strike'], wing_width, 'lower')
        long_call = self._find_wing(calls, short_call['strike'], wing_width, 'higher')
        if not long_put or not long_call:
            return self._fail(ticker, 'Iron Condor', 'No wing strikes')

        put_credit = short_put['price'] - long_put['price']
        call_credit = short_call['price'] - long_call['price']
        net = put_credit + call_credit

        if net <= 0:
            return self._fail(ticker, 'Iron Condor', f'No net credit ({net:.2f})')

        put_w = abs(short_put['strike'] - long_put['strike'])
        call_w = abs(short_call['strike'] - long_call['strike'])
        max_w = max(put_w, call_w)
        max_loss = (max_w - net) * 100
        max_profit = net * 100
        prob_profit = (1 - 2 * delta_target) * 100

        greeks = self._sum_greeks([
            self._leg_greeks(long_put, 'BUY', 'put', dte=dte),
            self._leg_greeks(short_put, 'SELL', 'put', dte=dte),
            self._leg_greeks(short_call, 'SELL', 'call', dte=dte),
            self._leg_greeks(long_call, 'BUY', 'call', dte=dte),
        ])

        quality = (
            self._score_for_selling(short_put) * 0.25
            + self._score_for_selling(short_call) * 0.25
            + (net / max_w * 40 if max_w > 0 else 0)
            + min(15, prob_profit / 5)
        )

        notes = (
            f"Sell {short_put['delta']:.0%}Δ put ${short_put['strike']} + "
            f"{short_call['delta']:.0%}Δ call ${short_call['strike']}. "
            f"Wings: put ${long_put['strike']} / call ${long_call['strike']}. "
            f"Net credit ${net:.2f}, P(profit) ~{prob_profit:.0f}%, "
            f"Net θ: {greeks['theta']:.3f}/day."
        )

        legs = [
            {'action': 'BUY', 'option_type': 'put', 'strike': long_put['strike'],
             'expiration': expiration, 'quantity': 1},
            {'action': 'SELL', 'option_type': 'put', 'strike': short_put['strike'],
             'expiration': expiration, 'quantity': 1},
            {'action': 'SELL', 'option_type': 'call', 'strike': short_call['strike'],
             'expiration': expiration, 'quantity': 1},
            {'action': 'BUY', 'option_type': 'call', 'strike': long_call['strike'],
             'expiration': expiration, 'quantity': 1},
        ]

        return self._result(
            legs,
            f"Iron Condor ({long_put['strike']}/{short_put['strike']}"
            f"/{short_call['strike']}/{long_call['strike']})",
            max_loss, max_profit, net, greeks, quality, notes,
        )

    def _build_straddle(
        self, ticker, calls, puts, price, expiration, iv_rank, dte,
    ) -> Dict:
        """Straddle: buy ATM call + ATM put for vol expansion."""
        atm_call = self._find_by_delta(calls, 0.50)
        atm_put = self._find_by_delta(puts, 0.50)
        if not atm_call or not atm_put:
            return self._fail(ticker, 'Straddle', 'No ATM options')

        # Align to same strike
        if atm_call['strike'] != atm_put['strike']:
            if abs(atm_call['strike'] - price) <= abs(atm_put['strike'] - price):
                atm_put = self._find_by_strike(puts, atm_call['strike']) or atm_put
            else:
                atm_call = self._find_by_strike(calls, atm_put['strike']) or atm_call

        debit = atm_call['price'] + atm_put['price']
        max_loss = debit * 100
        be_pct = (debit / price) * 100 if price > 0 else 0

        greeks = self._sum_greeks([
            self._leg_greeks(atm_call, 'BUY', 'call', dte=dte),
            self._leg_greeks(atm_put, 'BUY', 'put', dte=dte),
        ])

        # Break-even levels and daily move needed
        strike = atm_call['strike']
        upper_be = strike + debit
        lower_be = strike - debit
        daily_be_move = 0.0
        if greeks.get('gamma', 0) > 0 and greeks.get('theta', 0) < 0:
            daily_be_move = math.sqrt(2 * abs(greeks['theta']) / greeks['gamma'])

        break_even = {
            'upper': round(upper_be, 2),
            'lower': round(lower_be, 2),
            'range_pct': round(be_pct, 2),
            'daily_move_needed': round(daily_be_move, 2),
        }

        iv_note = ''
        iv_bonus = 0
        if iv_rank is not None:
            if iv_rank < 30:
                iv_note = ' Cheap vol — good for buying.'
                iv_bonus = 15
            elif iv_rank > 70:
                iv_note = ' Expensive vol — CAUTION.'
                iv_bonus = -10

        quality = (
            self._score_for_buying(atm_call) * 0.35
            + self._score_for_buying(atm_put) * 0.35
            + max(0, 20 - be_pct * 3)  # lower breakeven = better
            + iv_bonus
        )

        be_note = f" BE: ${lower_be:.0f}/${upper_be:.0f}."
        if daily_be_move > 0:
            be_note += f" Daily move needed: ${daily_be_move:.2f}."

        notes = (
            f"Buy ATM call+put ${strike}. "
            f"Debit ${debit:.2f}, breakeven ±{be_pct:.1f}%.{be_note} "
            f"Net Γ:{greeks['gamma']:.4f}, ν:{greeks['vega']:.3f}, "
            f"θ:{greeks['theta']:.3f}/day.{iv_note}"
        )

        legs = [
            {'action': 'BUY', 'option_type': 'call', 'strike': strike,
             'expiration': expiration, 'quantity': 1},
            {'action': 'BUY', 'option_type': 'put', 'strike': atm_put['strike'],
             'expiration': expiration, 'quantity': 1},
        ]

        result = self._result(
            legs, f"Straddle (${strike})",
            max_loss, 999999, round(-debit, 2), greeks, quality, notes,
        )
        result['break_even'] = break_even
        return result

    def _build_iron_butterfly(
        self, ticker, calls, puts, price, expiration,
        wing_width, iv_rank, dte,
    ) -> Dict:
        """Iron butterfly: sell ATM straddle + buy OTM wings."""
        short_call = self._find_by_delta(calls, 0.50)
        short_put = self._find_by_delta(puts, 0.50)
        if not short_call or not short_put:
            return self._fail(ticker, 'Iron Butterfly', 'No ATM strikes')

        # Align to same strike
        if short_call['strike'] != short_put['strike']:
            if abs(short_call['strike'] - price) <= abs(short_put['strike'] - price):
                short_put = self._find_by_strike(puts, short_call['strike']) or short_put
            else:
                short_call = self._find_by_strike(calls, short_put['strike']) or short_call

        long_call = self._find_wing(calls, short_call['strike'], wing_width, 'higher')
        long_put = self._find_wing(puts, short_put['strike'], wing_width, 'lower')
        if not long_call or not long_put:
            return self._fail(ticker, 'Iron Butterfly', 'No wing strikes')

        # Credit = ATM straddle premium - wing cost
        straddle_credit = short_call['price'] + short_put['price']
        wing_cost = long_call['price'] + long_put['price']
        net = straddle_credit - wing_cost

        if net <= 0:
            return self._fail(ticker, 'Iron Butterfly', f'No net credit ({net:.2f})')

        call_w = abs(short_call['strike'] - long_call['strike'])
        put_w = abs(short_put['strike'] - long_put['strike'])
        max_w = max(call_w, put_w)
        max_loss = (max_w - net) * 100
        max_profit = net * 100

        greeks = self._sum_greeks([
            self._leg_greeks(long_put, 'BUY', 'put', dte=dte),
            self._leg_greeks(short_put, 'SELL', 'put', dte=dte),
            self._leg_greeks(short_call, 'SELL', 'call', dte=dte),
            self._leg_greeks(long_call, 'BUY', 'call', dte=dte),
        ])

        quality = (
            self._score_for_selling(short_call) * 0.25
            + self._score_for_selling(short_put) * 0.25
            + (net / max_w * 40 if max_w > 0 else 0)  # credit/width ratio
            + min(15, max_profit / 50)
        )

        strike = short_call['strike']
        notes = (
            f"Sell ATM straddle ${strike}, "
            f"buy wings ${long_put['strike']}p/${long_call['strike']}c. "
            f"Credit ${net:.2f}, max profit at ${strike}. "
            f"Width ${max_w:.0f}, R:R {max_profit/max_loss:.1f}:1."
        )

        legs = [
            {'action': 'BUY', 'option_type': 'put', 'strike': long_put['strike'],
             'expiration': expiration, 'quantity': 1},
            {'action': 'SELL', 'option_type': 'put', 'strike': short_put['strike'],
             'expiration': expiration, 'quantity': 1},
            {'action': 'SELL', 'option_type': 'call', 'strike': short_call['strike'],
             'expiration': expiration, 'quantity': 1},
            {'action': 'BUY', 'option_type': 'call', 'strike': long_call['strike'],
             'expiration': expiration, 'quantity': 1},
        ]

        return self._result(
            legs,
            f"Iron Butterfly (${long_put['strike']}/{strike}/{long_call['strike']})",
            max_loss, max_profit, net, greeks, quality, notes,
        )

    def _build_debit_spread(
        self, ticker, direction, calls, puts, price, expiration,
        delta_target, wing_width, iv_rank, dte,
    ) -> Dict:
        """Debit spread: buy near ATM + sell OTM."""
        if direction in ('bearish', 'neutral_bearish'):
            opt_type = 'put'
            opts = puts
            long_opt = self._find_by_delta(opts, max(delta_target, 0.40))
            if not long_opt:
                return self._fail(ticker, 'Debit Spread', 'No long strike')
            short_opt = self._find_wing(opts, long_opt['strike'], wing_width, 'lower')
        else:
            opt_type = 'call'
            opts = calls
            long_opt = self._find_by_delta(opts, max(delta_target, 0.40))
            if not long_opt:
                return self._fail(ticker, 'Debit Spread', 'No long strike')
            short_opt = self._find_wing(opts, long_opt['strike'], wing_width, 'higher')

        if not short_opt:
            return self._fail(ticker, 'Debit Spread', 'No short strike')

        debit = long_opt['price'] - short_opt['price']
        width = abs(long_opt['strike'] - short_opt['strike'])
        if debit <= 0:
            return self._fail(ticker, 'Debit Spread', 'Zero/negative debit')

        max_loss = debit * 100
        max_profit = (width - debit) * 100
        rr = max_profit / max_loss if max_loss > 0 else 0

        greeks = self._sum_greeks([
            self._leg_greeks(long_opt, 'BUY', opt_type, dte=dte),
            self._leg_greeks(short_opt, 'SELL', opt_type, dte=dte),
        ])

        quality = (
            self._score_for_buying(long_opt) * 0.45
            + min(25, rr * 10)
            + max(0, 15 - (iv_rank or 50) / 4)  # low IV bonus
            + min(15, (short_opt['oi'] / PREF_OI) * 15)
        )

        notes = (
            f"Buy {long_opt['delta']:.0%}Δ {opt_type} ${long_opt['strike']} "
            f"(Γ:{long_opt['gamma']:.4f}, Γ/θ:{long_opt['gamma_theta_ratio']:.2f}), "
            f"Sell ${short_opt['strike']}. "
            f"Debit ${debit:.2f}, R:R {rr:.1f}:1, Width ${width:.0f}."
        )

        legs = [
            {'action': 'BUY', 'option_type': opt_type, 'strike': long_opt['strike'],
             'expiration': expiration, 'quantity': 1},
            {'action': 'SELL', 'option_type': opt_type, 'strike': short_opt['strike'],
             'expiration': expiration, 'quantity': 1},
        ]

        return self._result(
            legs, f"Debit Spread ({opt_type.upper()} {long_opt['strike']}/{short_opt['strike']})",
            max_loss, max_profit, round(-debit, 2), greeks, quality, notes,
        )

    def _build_ratio_spread(
        self, ticker, direction, calls, puts, price, expiration,
        delta_target, wing_width, iv_rank, dte,
    ) -> Dict:
        """Ratio spread: buy 1 near-ATM + sell 2 OTM."""
        if direction in ('bearish', 'neutral_bearish'):
            opt_type = 'put'
            opts = puts
            long_opt = self._find_by_delta(opts, 0.45)
            short_opt = self._find_by_delta(opts, delta_target or 0.20)
        else:
            opt_type = 'call'
            opts = calls
            long_opt = self._find_by_delta(opts, 0.45)
            short_opt = self._find_by_delta(opts, delta_target or 0.20)

        if not long_opt or not short_opt:
            return self._fail(ticker, 'Ratio Spread', 'Missing strikes')

        net = (2 * short_opt['price']) - long_opt['price']
        width = abs(long_opt['strike'] - short_opt['strike'])
        max_profit = (width + net) * 100 if net > 0 else (width - abs(net)) * 100

        greeks = self._sum_greeks([
            self._leg_greeks(long_opt, 'BUY', opt_type, 1, dte=dte),
            self._leg_greeks(short_opt, 'SELL', opt_type, 2, dte=dte),
        ])

        quality = (
            self._score_for_selling(short_opt) * 0.4
            + self._score_for_buying(long_opt) * 0.3
            + (25 if net > 0 else 10)
        )

        cd = 'credit' if net > 0 else 'debit'
        notes = (
            f"Buy 1x {long_opt['delta']:.0%}Δ {opt_type} ${long_opt['strike']}, "
            f"Sell 2x {short_opt['delta']:.0%}Δ ${short_opt['strike']}. "
            f"Net {cd} ${abs(net):.2f}. "
            f"WARNING: unlimited risk beyond ${short_opt['strike']}."
        )

        legs = [
            {'action': 'BUY', 'option_type': opt_type, 'strike': long_opt['strike'],
             'expiration': expiration, 'quantity': 1},
            {'action': 'SELL', 'option_type': opt_type, 'strike': short_opt['strike'],
             'expiration': expiration, 'quantity': 2},
        ]

        return self._result(
            legs,
            f"Ratio Spread ({opt_type.upper()} 1x{long_opt['strike']}/2x{short_opt['strike']})",
            999999, max_profit, round(net, 2), greeks, quality, notes,
        )

    def _build_single_leg(
        self, ticker, direction, price, expiration, chain_data, delta_target=None,
    ) -> Dict:
        """Fallback: single-leg with delta targeting."""
        options = chain_data.get('options', []) if chain_data else []
        if direction in ('short',):
            action, opt_type, tgt = 'SELL', 'call', delta_target or 0.30
        elif direction in ('bearish', 'neutral_bearish'):
            action, opt_type, tgt = 'BUY', 'put', delta_target or 0.40
        else:
            action, opt_type, tgt = 'BUY', 'call', delta_target or 0.50

        sel = None
        if options:
            opts = self._extract_options(options, opt_type)
            sel = self._find_by_delta(opts, tgt)

        strike = sel['strike'] if sel else round(price)
        opt_price = sel['price'] if sel else 0

        greeks = {}
        if sel:
            greeks = self._leg_greeks(sel, action, opt_type)

        legs = [
            {'action': action, 'option_type': opt_type, 'strike': strike,
             'expiration': expiration, 'quantity': 1},
        ]

        ml = opt_price * 100 if action == 'BUY' else 999999
        mp = 999999 if action == 'BUY' else opt_price * 100

        return self._result(
            legs, f"Single {opt_type.upper()} ({strike})",
            ml, mp, round(-opt_price if action == 'BUY' else opt_price, 2),
            greeks, 50,
            f"Single {action} {opt_type} at {tgt:.0%}Δ, strike ${strike}.",
        )

    # -----------------------------------------------------------------
    # Result helpers
    # -----------------------------------------------------------------

    def _result(self, legs, name, max_loss, max_profit, net_premium,
                greeks, quality, notes) -> Dict:
        return {
            'legs': legs,
            'strategy_name': name,
            'max_loss': round(max_loss, 2),
            'max_profit': round(max_profit, 2),
            'net_premium': round(net_premium, 2) if isinstance(net_premium, float) else net_premium,
            'greeks': greeks,
            'quality_score': round(min(100, max(0, quality)), 1),
            'notes': notes,
        }

    def _fail(self, ticker, strategy, reason) -> Dict:
        logger.warning(f"Strategy build failed for {ticker} ({strategy}): {reason}")
        return {
            'legs': [],
            'strategy_name': strategy,
            'max_loss': 0, 'max_profit': 0, 'net_premium': 0,
            'greeks': {}, 'quality_score': 0,
            'notes': f"Build failed: {reason}",
        }
