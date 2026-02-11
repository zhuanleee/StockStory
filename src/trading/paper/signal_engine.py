"""
Signal Engine — Generate trading signals from GEX, regime, macro, and IV data.

Four signal types:
1. GEX Regime Flip: GEX flips positive/negative
2. Combined Regime Shift: Combined GEX+P/C regime changes
3. Macro Event Catalyst: Major event within 3 days
4. IV Mean Reversion: IV Rank extremes (>80 sell, <20 buy)

Phase 1a: Confidence adjusted by historical win rates (adaptive_engine.py)
Phase 3b: Strategy auto-selection based on regime
"""

import json
import logging
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


def _load_prev_regimes(volume_path: str) -> Dict:
    """Load previous regimes from persistent storage (Modal volume)."""
    try:
        regimes_file = Path(volume_path) / "paper_trading" / "prev_regimes.json"
        if regimes_file.exists():
            return json.loads(regimes_file.read_text())
    except Exception as e:
        logger.warning(f"Failed to load prev_regimes: {e}")
    return {}


def _save_prev_regimes(volume_path: str, regimes: Dict):
    """Save previous regimes to persistent storage (Modal volume)."""
    try:
        pt_dir = Path(volume_path) / "paper_trading"
        pt_dir.mkdir(parents=True, exist_ok=True)
        regimes_file = pt_dir / "prev_regimes.json"
        regimes_file.write_text(json.dumps(regimes))
    except Exception as e:
        logger.warning(f"Failed to save prev_regimes: {e}")


class SignalEngine:
    def __init__(self, volume_path: str):
        self.volume_path = volume_path
        self._prev_regimes = _load_prev_regimes(volume_path)
        self._market_data_cache = {}  # ticker -> {data} — cleared each evaluate_signals batch
        # Phase 1a: Load signal performance tracker for adaptive confidence
        try:
            from .adaptive_engine import SignalPerformanceTracker
            self.perf_tracker = SignalPerformanceTracker(volume_path)
        except Exception:
            self.perf_tracker = None
        # Multi-leg: Load strategy selector for attaching recommendations
        try:
            from .adaptive_engine import StrategySelector
            self.strategy_selector = StrategySelector()
        except Exception:
            self.strategy_selector = None

    def _adjust_confidence(self, raw_confidence: float, signal_type: str) -> int:
        """Phase 1a: Adjust confidence based on historical performance."""
        if not self.perf_tracker:
            return round(raw_confidence)
        multiplier = self.perf_tracker.get_confidence_adjustment(signal_type)
        adjusted = raw_confidence * multiplier
        return round(max(10, min(99, adjusted)))

    async def evaluate_signals(self, ticker: str, config: dict, debug: bool = False) -> List[dict]:
        """Evaluate all signal sources for a ticker, return actionable signals."""
        signals = []
        all_raw_signals = []
        debug_info = {} if debug else None
        min_confidence = config.get('min_confidence', 60)
        self._current_risk_mode = config.get('risk_mode', 'limited')
        self._market_data_cache = {}  # Clear per-ticker cache for fresh batch
        multi_leg_enabled = config.get('multi_leg_enabled', False)

        # Run signal evaluators with error capture
        evaluators = [
            ('gex_flip', self._check_gex_flip),
            ('regime_shift', self._check_regime_shift),
            ('macro_event', self._check_macro_event),
            ('iv_reversion', self._check_iv_reversion),
        ]

        for name, evaluator in evaluators:
            try:
                sig = await evaluator(ticker)
                if sig:
                    all_raw_signals.append(sig)
                    if debug:
                        debug_info[name] = {
                            'status': 'signal_generated',
                            'confidence': sig.get('confidence', 0),
                            'passed_threshold': sig.get('confidence', 0) >= min_confidence,
                        }
                elif debug:
                    # Provide reason for None
                    prev = self._prev_regimes.get(ticker, {})
                    if name == 'gex_flip':
                        debug_info[name] = {
                            'status': 'no_trigger',
                            'prev_regime': prev.get('gex_regime', 'unknown'),
                            'prev_gex_billions': prev.get('gex_billions', 'N/A'),
                            'note': 'no regime flip, zero crossing, magnitude shift, or wall proximity detected',
                        }
                    elif name == 'regime_shift':
                        debug_info[name] = {'status': 'no_shift', 'prev_combined': prev.get('combined_regime', 'unknown'), 'note': 'no combined regime change'}
                    elif name == 'macro_event':
                        macro_dbg = getattr(self, '_last_macro_debug', {})
                        debug_info[name] = {'status': 'no_event', **macro_dbg}
                    elif name == 'iv_reversion':
                        debug_info[name] = {'status': 'iv_normal', 'note': 'IV rank between 30-70 (no extreme)', 'iv_rank_method': 'per_ticker_rolling'}
            except Exception as e:
                logger.error(f"Signal evaluator {name} error for {ticker}: {e}")
                if debug:
                    debug_info[name] = {'status': 'error', 'error': str(e)}

        # Compute regime transition probability from all signals
        transition = self._compute_transition_probability(all_raw_signals)

        for sig in all_raw_signals:
            if sig.get('confidence', 0) >= min_confidence:
                sig['transition'] = transition
                if multi_leg_enabled and self.strategy_selector:
                    try:
                        strategy_rec = await self._attach_strategy_recommendation(sig, ticker)
                        if strategy_rec:
                            sig['strategy_recommendation'] = strategy_rec
                    except Exception as e:
                        logger.debug(f"Strategy recommendation skipped for {ticker}: {e}")
                signals.append(sig)

        # Persist regime state after evaluation
        _save_prev_regimes(self.volume_path, self._prev_regimes)

        signals.sort(key=lambda s: s.get('confidence', 0), reverse=True)
        max_signals = config.get('max_signals_per_check', 3)
        result = signals[:max_signals]

        if debug:
            # Attach debug info to the return (caller checks for it)
            for sig in result:
                sig['_debug'] = debug_info
            if not result:
                # Return debug info as a special signal-like dict
                result.append({'_debug_only': True, '_debug': debug_info, 'ticker': ticker})

        return result

    def _get_reliable_price(self, ticker: str, gex_price: float = 0) -> float:
        """Get reliable current price using multiple fallback sources.
        Works during market hours and after hours."""
        if gex_price and gex_price > 0:
            return gex_price
        # Fallback 1: Tastytrade quote (fresh session, works after hours)
        try:
            from src.data.options import _get_tastytrade_quote
            quote = _get_tastytrade_quote(ticker)
            if quote and quote.get('last') and quote['last'] > 0:
                return quote['last']
        except Exception:
            pass
        # Fallback 2: Polygon snapshot (equities only)
        try:
            from src.data.options import get_snapshot_sync
            snap = get_snapshot_sync(ticker)
            if snap:
                price = snap.get('price') or snap.get('last_price') or 0
                if price > 0:
                    return price
        except Exception:
            pass
        return 0

    async def _attach_strategy_recommendation(self, signal: dict, ticker: str) -> Optional[dict]:
        """Build regime state from REAL market data and get strategy recommendation.

        Fetches term structure, skew, IV, and regime data to ensure all 14
        strategies can trigger based on actual conditions — not defaults.
        Returns dict with 'primary' strategy and 'alternatives' list (top 3).
        """
        if not self.strategy_selector:
            return None

        regime_data = signal.get('regime_data', {})
        iv_data = signal.get('iv_data', {})
        event_data = signal.get('event_data', {})

        # --- Fetch missing market data (cached per ticker within a batch) ---
        import asyncio

        # Use cached data if already fetched for this ticker in current batch
        if ticker in self._market_data_cache:
            fetched = self._market_data_cache[ticker]
        else:
            fetch_tasks = {}

            # Need GEX regime if signal is macro_event or iv_reversion (no regime_data)
            if not regime_data.get('regime') and not regime_data.get('gex_regime'):
                try:
                    from src.data.tastytrade_provider import get_gex_regime_tastytrade
                    fetch_tasks['gex'] = get_gex_regime_tastytrade(ticker)
                except ImportError:
                    pass

            # Need combined regime if missing
            if not regime_data.get('combined_regime') or regime_data.get('combined_regime') == 'neutral_transitional':
                try:
                    from src.data.tastytrade_provider import get_combined_regime_tastytrade
                    fetch_tasks['combined'] = get_combined_regime_tastytrade(ticker)
                except ImportError:
                    pass

            # Need IV data if signal is gex_flip or regime_shift (no iv_data)
            if not iv_data.get('iv_rank'):
                try:
                    from src.data.tastytrade_provider import get_iv_rank_tastytrade
                    fetch_tasks['iv'] = get_iv_rank_tastytrade(ticker, volume_path=self.volume_path)
                except ImportError:
                    pass

            # Always fetch term structure and skew — no signal carries these
            try:
                from src.data.tastytrade_provider import (
                    get_term_structure_tastytrade,
                    get_iv_by_delta_tastytrade,
                )
                fetch_tasks['term'] = get_term_structure_tastytrade(ticker)
                fetch_tasks['skew'] = get_iv_by_delta_tastytrade(ticker)
            except ImportError:
                pass

            # Execute all fetches in parallel
            fetched = {}
            if fetch_tasks:
                try:
                    keys = list(fetch_tasks.keys())
                    results = await asyncio.gather(*fetch_tasks.values(), return_exceptions=True)
                    for k, v in zip(keys, results):
                        if isinstance(v, dict) and 'error' not in v:
                            fetched[k] = v
                except Exception as e:
                    logger.debug(f"Strategy data fetch partial failure for {ticker}: {e}")
            self._market_data_cache[ticker] = fetched

        # --- Merge fetched data into regime_data / iv_data ---
        if 'gex' in fetched:
            gex = fetched['gex']
            regime_data = {**regime_data,
                          'regime': regime_data.get('regime') or gex.get('regime', 'transitional'),
                          'gex_regime': regime_data.get('gex_regime') or gex.get('regime', 'transitional')}
        if 'combined' in fetched:
            comb = fetched['combined']
            regime_data = {**regime_data,
                          'combined_regime': regime_data.get('combined_regime', 'neutral_transitional')
                          if regime_data.get('combined_regime') not in (None, 'neutral_transitional')
                          else comb.get('combined_regime', 'neutral_transitional'),
                          'pc_ratio': regime_data.get('pc_ratio') or comb.get('pc_ratio', 1.0)}
        if 'iv' in fetched:
            iv = fetched['iv']
            if not iv_data.get('iv_rank'):
                iv_data = {**iv_data,
                           'iv_rank': iv.get('iv_rank', 50),
                           'atm_iv': iv.get('atm_iv'),
                           'put_25d_iv': iv_data.get('put_25d_iv') or iv.get('put_25d_iv'),
                           'call_25d_iv': iv_data.get('call_25d_iv') or iv.get('call_25d_iv'),
                           'risk_reversal': iv_data.get('risk_reversal') or iv.get('risk_reversal'),
                           'skew_ratio': iv_data.get('skew_ratio') or iv.get('skew_ratio')}

        # Extract term structure (unlocks Ratio Spread, Backwardation Credit Spread)
        term_structure = 'contango'
        if 'term' in fetched:
            term_structure = fetched['term'].get('structure', 'contango')

        # Extract skew data (unlocks Ratio Spread via skew_steep)
        skew_ratio = iv_data.get('skew_ratio', 1.0) or 1.0
        if 'skew' in fetched and fetched['skew'].get('skew_ratio'):
            skew_ratio = fetched['skew']['skew_ratio']
        skew_steep = skew_ratio > 1.15  # 25d put/call IV ratio > 1.15 = steep skew

        # --- Build enriched regime_state ---
        iv_rank = iv_data.get('iv_rank', 50)

        risk_reversal = iv_data.get('risk_reversal', 0)
        if not risk_reversal:
            p25 = iv_data.get('put_25d_iv')
            c25 = iv_data.get('call_25d_iv')
            if p25 and c25:
                risk_reversal = round(float(p25) - float(c25), 4)
        # Also try skew data
        if not risk_reversal and 'skew' in fetched:
            p25 = fetched['skew'].get('put_25d_iv')
            c25 = fetched['skew'].get('call_25d_iv')
            if p25 and c25:
                risk_reversal = round(float(p25) - float(c25), 4)

        # --- Compute real flow_toxicity ---
        pc_ratio = regime_data.get('pc_ratio', 1.0) or 1.0
        gex_regime = regime_data.get('regime', regime_data.get('gex_regime', 'transitional'))
        combined_regime = regime_data.get('combined_regime', 'neutral_transitional')

        flow_toxicity = 0.3
        if pc_ratio > 1.5:
            flow_toxicity = 0.7
        elif pc_ratio > 1.2:
            flow_toxicity = 0.5
        elif pc_ratio < 0.7:
            flow_toxicity = 0.15
        elif pc_ratio < 0.9:
            flow_toxicity = 0.25
        if gex_regime == 'volatile':
            flow_toxicity = min(1.0, flow_toxicity + 0.15)
        if combined_regime in ('danger', 'high_risk'):
            flow_toxicity = min(1.0, flow_toxicity + 0.2)

        # --- Compute real vanna_flow ---
        vanna_flow = 0.0
        if risk_reversal:
            vanna_flow = -risk_reversal * 10
            vanna_flow = max(-1.0, min(1.0, vanna_flow))
        if combined_regime == 'opportunity':
            vanna_flow = max(vanna_flow, 0.5)

        regime_state = {
            'vrp': (iv_rank - 30) / 10,
            'gex_regime': gex_regime,
            'combined_regime': combined_regime,
            'flow_toxicity': round(flow_toxicity, 2),
            'term_structure': term_structure,
            'skew_steep': skew_steep,
            'skew_ratio': skew_ratio,
            'iv_rank': iv_rank,
            'vanna_flow': round(vanna_flow, 2),
            'macro_event_days': event_data.get('days_until', 99),
            'risk_reversal': risk_reversal,
        }

        # Read risk_mode from config (passed through evaluate_signals → _attach_strategy_recommendation)
        risk_mode = getattr(self, '_current_risk_mode', 'limited')
        strategies = self.strategy_selector.select_strategy(regime_state, risk_mode=risk_mode)
        if not strategies or strategies[0].get('name') == 'Wait / Reduce Size':
            return None

        # Return primary + up to 2 alternatives for diversification
        primary = strategies[0]
        alternatives = [s for s in strategies[1:3] if s.get('name') != 'Wait / Reduce Size']
        result = dict(primary)
        result['regime_state_used'] = regime_state  # Attach for debugging/logging
        if alternatives:
            result['alternatives'] = alternatives
        return result

    # -------------------------------------------------------------------------
    # Regime Transition Composite
    # -------------------------------------------------------------------------

    def _compute_transition_probability(self, signals: List[dict]) -> Dict:
        """Weighted composite of all signal sources to estimate regime transition.

        Signal weights (research-derived):
          GEX flip: 0.25, regime shift: 0.30, macro event: 0.10,
          IV reversion: 0.15, term structure: 0.20

        Returns {probability: 0-1, contributing_signals: [...], action: str}
        """
        WEIGHTS = {
            'gex_flip': 0.25,
            'regime_shift': 0.30,
            'macro_event': 0.10,
            'iv_reversion': 0.15,
            'term_structure': 0.20,
        }

        weighted_sum = 0.0
        contributing = []

        for sig in signals:
            sig_type = sig.get('signal_type', '')
            conf = sig.get('confidence', 0) / 100.0  # Normalize to 0-1

            weight = WEIGHTS.get(sig_type, 0)
            if weight > 0:
                weighted_sum += weight * conf
                contributing.append({
                    'signal': sig_type,
                    'confidence': sig.get('confidence', 0),
                    'weight': weight,
                    'contribution': round(weight * conf, 3),
                })

        probability = min(1.0, weighted_sum)

        if probability > 0.8:
            action = 'halt_new_entries'
        elif probability > 0.6:
            action = 'halve_position_sizes'
        else:
            action = 'normal'

        return {
            'transition_probability': round(probability, 3),
            'action': action,
            'contributing_signals': contributing,
        }

    # -------------------------------------------------------------------------
    # Signal 1: GEX Regime Flip
    # -------------------------------------------------------------------------

    async def _check_gex_flip(self, ticker: str) -> Optional[dict]:
        """Detect GEX regime flip, magnitude shift, zero crossing, or wall proximity."""
        try:
            from src.data.tastytrade_provider import get_gex_regime_tastytrade
            regime_data = await get_gex_regime_tastytrade(ticker)
            if 'error' in regime_data:
                return None

            current_regime = regime_data.get('regime', 'transitional')
            prev = self._prev_regimes.get(ticker, {})
            prev_regime = prev.get('gex_regime', current_regime)

            current_gex = regime_data.get('gex_billions', 0) or 0
            prev_gex = prev.get('gex_billions', 0) or 0
            call_wall = regime_data.get('call_wall')
            put_wall = regime_data.get('put_wall')
            current_price = self._get_reliable_price(ticker, regime_data.get('current_price', 0))

            # Update persistent cache with GEX magnitude + walls
            self._prev_regimes.setdefault(ticker, {})['gex_regime'] = current_regime
            self._prev_regimes[ticker]['ts'] = datetime.utcnow().isoformat()
            self._prev_regimes[ticker]['gex_billions'] = current_gex
            self._prev_regimes[ticker]['call_wall'] = call_wall
            self._prev_regimes[ticker]['put_wall'] = put_wall

            # --- Signal detection: check all triggers ---
            signal_trigger = None
            direction = None
            option_type = None
            notes = None
            tags = ['gex_flip']
            raw_confidence = 0

            # Trigger 1: Regime label flip (original logic)
            if prev_regime != current_regime:
                flip_type = f'{prev_regime}_to_{current_regime}'
                raw_confidence = regime_data.get('confidence', 0) * 100
                if current_regime == 'volatile':
                    direction = 'long'
                    option_type = 'put'
                    notes = f'GEX flipped negative ({flip_type}). Bearish setup.'
                elif current_regime == 'pinned':
                    direction = 'long'
                    option_type = 'call'
                    notes = f'GEX flipped positive ({flip_type}). Bullish setup.'
                if direction:
                    signal_trigger = 'regime_flip'
                    tags.append(flip_type)

            # Trigger 2: GEX zero crossing (highest conviction sub-signal)
            # Only require prev_gex != 0 — current can be 0 (crossed to zero)
            if not signal_trigger and prev_gex != 0:
                if prev_gex * current_gex < 0 or (current_gex == 0 and prev_gex != 0):  # sign change or crossed to zero
                    signal_trigger = 'zero_crossing'
                    raw_confidence = 80
                    if current_gex < 0:
                        direction = 'long'
                        option_type = 'put'
                        notes = f'GEX crossed zero → negative ({prev_gex:.2f}B → {current_gex:.2f}B). Dealer selling pressure.'
                    else:
                        direction = 'long'
                        option_type = 'call'
                        notes = f'GEX crossed zero → positive ({prev_gex:.2f}B → {current_gex:.2f}B). Dealer support emerging.'
                    tags.append('zero_crossing')

            # Trigger 3: GEX magnitude shift (>50% change)
            if not signal_trigger and prev_gex != 0:
                pct_change = abs(current_gex - prev_gex) / abs(prev_gex)
                if pct_change > 0.50:
                    signal_trigger = 'magnitude_shift'
                    raw_confidence = 70
                    if current_gex < prev_gex:
                        direction = 'long'
                        option_type = 'put'
                        notes = f'GEX dropped {pct_change:.0%} ({prev_gex:.2f}B → {current_gex:.2f}B). Dealer support weakening.'
                    else:
                        direction = 'long'
                        option_type = 'call'
                        notes = f'GEX surged {pct_change:.0%} ({prev_gex:.2f}B → {current_gex:.2f}B). Dealer support strengthening.'
                    tags.append('magnitude_shift')

            # Trigger 4: Wall proximity (price within 1.0% of call/put wall)
            if not signal_trigger and current_price > 0:
                if call_wall and call_wall > 0:
                    pct_from_call = abs(current_price - call_wall) / current_price
                    if pct_from_call < 0.01:
                        signal_trigger = 'wall_proximity'
                        raw_confidence = 60
                        direction = 'short'
                        option_type = 'call'
                        notes = f'Price near call wall ${call_wall:.0f} ({pct_from_call:.1%} away). Dealer resistance — fade the move.'
                        tags.append('call_wall_proximity')
                if not signal_trigger and put_wall and put_wall > 0:
                    pct_from_put = abs(current_price - put_wall) / current_price
                    if pct_from_put < 0.01:
                        signal_trigger = 'wall_proximity'
                        raw_confidence = 60
                        direction = 'long'
                        option_type = 'call'
                        notes = f'Price near put wall ${put_wall:.0f} ({pct_from_put:.1%} away). Dealer support — bounce expected.'
                        tags.append('put_wall_proximity')

            if not signal_trigger or not direction:
                return None

            confidence = self._adjust_confidence(raw_confidence, 'gex_flip')
            dte_range = [30, 45]

            return {
                'signal_id': f'SIG-{date.today().strftime("%Y%m%d")}-GEX-{ticker}',
                'signal_type': 'gex_flip',
                'ticker': ticker.upper(),
                'direction': direction,
                'option_type': option_type,
                'strike': round(current_price),  # ATM
                'expiration': self._get_target_expiration(dte_range),
                'confidence': round(confidence),
                'underlying_price': current_price,
                'delta_target': 0.40,
                'dte_range': dte_range,
                'tags': tags,
                'notes': notes,
                'regime_data': {
                    'regime': current_regime,
                    'prev_regime': prev_regime,
                    'gex_score': regime_data.get('regime_score'),
                    'gex_billions': current_gex,
                    'prev_gex_billions': prev_gex,
                    'call_wall': call_wall,
                    'put_wall': put_wall,
                    'signal_trigger': signal_trigger,
                },
            }
        except Exception as e:
            logger.error(f"GEX flip check error for {ticker}: {e}")
            return None

    # -------------------------------------------------------------------------
    # Signal 2: Combined Regime Shift
    # -------------------------------------------------------------------------

    async def _check_regime_shift(self, ticker: str) -> Optional[dict]:
        """Detect combined GEX+P/C regime changes."""
        try:
            from src.data.tastytrade_provider import get_combined_regime_tastytrade
            combined = await get_combined_regime_tastytrade(ticker)
            if 'error' in combined:
                return None

            current = combined.get('combined_regime', 'neutral_transitional')
            prev = self._prev_regimes.get(ticker, {})
            prev_combined = prev.get('combined_regime', current)

            self._prev_regimes.setdefault(ticker, {})['combined_regime'] = current

            if prev_combined == current:
                return None

            risk_level = combined.get('risk_level', 'moderate')
            current_price = self._get_reliable_price(ticker, combined.get('current_price', 0))

            # Only act on significant regime changes
            actionable = {
                'opportunity': ('long', 'call', 85),
                'danger': ('long', 'put', 80),
                'high_risk': ('long', 'put', 75),
                'melt_up': ('long', 'call', 70),
                'volatile': ('long', 'put', 65),
                'neutral_volatile': ('long', 'put', 60),
                'pinned': ('short', 'call', 65),  # Sell premium in pinned regime
            }

            if current not in actionable:
                return None

            direction, option_type, base_confidence = actionable[current]
            # Scale by position_multiplier — use min 0.7 so signals can clear min_confidence
            multiplier = combined.get('position_multiplier', 0.5)
            raw_confidence = base_confidence * max(multiplier, 0.7)
            confidence = self._adjust_confidence(raw_confidence, 'regime_shift')

            return {
                'signal_id': f'SIG-{date.today().strftime("%Y%m%d")}-REGIME-{ticker}',
                'signal_type': 'regime_shift',
                'ticker': ticker.upper(),
                'direction': direction,
                'option_type': option_type,
                'strike': round(current_price),
                'expiration': self._get_target_expiration([30, 45]),
                'confidence': round(confidence),
                'underlying_price': current_price,
                'delta_target': 0.45,
                'dte_range': [30, 45],
                'tags': ['regime_shift', current, f'from_{prev_combined}'],
                'notes': combined.get('recommendation', ''),
                'regime_data': {
                    'combined_regime': current,
                    'prev_regime': prev_combined,
                    'gex_regime': combined.get('gex_regime'),
                    'pc_ratio': combined.get('pc_ratio'),
                    'risk_level': risk_level,
                },
            }
        except Exception as e:
            logger.error(f"Regime shift check error for {ticker}: {e}")
            return None

    # -------------------------------------------------------------------------
    # Signal 3: Macro Event Catalyst
    # -------------------------------------------------------------------------

    async def _check_macro_event(self, ticker: str) -> Optional[dict]:
        """Check for major macro event within 3 days (straddle play)."""
        self._last_macro_debug = {}
        try:
            from src.data.tastytrade_provider import get_gex_regime_tastytrade
            regime = await get_gex_regime_tastytrade(ticker)
            gex_price = regime.get('current_price', 0) if regime and 'error' not in regime else 0
            current_price = self._get_reliable_price(ticker, gex_price)

            self._last_macro_debug['price'] = current_price
            self._last_macro_debug['gex_price'] = gex_price
            self._last_macro_debug['regime_ok'] = regime is not None and 'error' not in (regime or {})

            # Check upcoming events
            events = self._get_upcoming_events()
            self._last_macro_debug['events_found'] = len(events) if events else 0
            self._last_macro_debug['events'] = [{'name': e.get('name'), 'days': e.get('days_until'), 'sev': e.get('severity')} for e in (events or [])]
            if not events:
                self._last_macro_debug['reason'] = 'no_events_generated'
                return None

            # Find most significant event within 3 days
            best_event = None
            best_severity = 0
            for event in events:
                days_until = event.get('days_until', 99)
                severity = event.get('severity', 0)
                if days_until <= 3 and severity > best_severity:
                    best_event = event
                    best_severity = severity

            if not best_event or best_severity < 3:
                self._last_macro_debug['reason'] = f'no_event_within_3d_sev3+ (best_sev={best_severity})'
                return None

            # Require valid price — skip signal if API failed
            if current_price <= 0:
                self._last_macro_debug['reason'] = 'no_price'
                logger.warning(f"Skipping macro_event signal for {ticker}: no valid price data")
                return None

            # Vol expansion play - buy straddle before event
            raw_confidence = min(90, 50 + best_severity * 8)
            confidence = self._adjust_confidence(raw_confidence, 'macro_event')

            return {
                'signal_id': f'SIG-{date.today().strftime("%Y%m%d")}-MACRO-{ticker}',
                'signal_type': 'macro_event',
                'ticker': ticker.upper(),
                'direction': 'long',
                'option_type': 'call',  # Buy ATM call (straddle half)
                'strike': round(current_price) if current_price > 0 else 0,
                'expiration': self._get_target_expiration([14, 30]),
                'confidence': confidence,
                'underlying_price': current_price,
                'delta_target': 0.50,
                'dte_range': [14, 30],
                'tags': ['macro_event', best_event.get('name', 'unknown')],
                'notes': f"Macro catalyst: {best_event.get('name', '')} in {best_event.get('days_until', '?')} days. Vol expansion play.",
                'event_data': best_event,
            }
        except Exception as e:
            logger.error(f"Macro event check error for {ticker}: {e}")
            return None

    # -------------------------------------------------------------------------
    # Signal 4: IV Mean Reversion
    # -------------------------------------------------------------------------

    async def _check_iv_reversion(self, ticker: str) -> Optional[dict]:
        """Check IV Rank for mean reversion signals using per-ticker rolling history."""
        try:
            from src.data.tastytrade_provider import get_gex_regime_tastytrade
            regime = await get_gex_regime_tastytrade(ticker)
            if not regime or 'error' in regime:
                return None

            current_price = self._get_reliable_price(ticker, regime.get('current_price', 0))

            # Per-ticker IV Rank using rolling 20-day+ history
            from src.data.tastytrade_provider import get_iv_rank_tastytrade
            iv_result = await get_iv_rank_tastytrade(ticker, volume_path=self.volume_path)
            iv_rank = iv_result.get('iv_rank', 50)
            atm_iv = iv_result.get('atm_iv')
            risk_reversal = None
            put_25d = iv_result.get('put_25d_iv')
            call_25d = iv_result.get('call_25d_iv')
            if put_25d and call_25d:
                risk_reversal = round(put_25d - call_25d, 4)

            if iv_rank > 70:
                # High IV - sell premium (credit spread)
                direction = 'short'
                option_type = 'call'
                delta_target = 0.16
                # Scale confidence: 70-80 range gets 55-65, >80 gets 65-90
                if iv_rank > 80:
                    raw_conf = min(90, 65 + (iv_rank - 80))
                else:
                    raw_conf = min(65, 55 + (iv_rank - 70))
                confidence = self._adjust_confidence(raw_conf, 'iv_reversion')
                notes = f'IV Rank at {iv_rank}%. Sell premium - credit spread setup.'
                tags = ['iv_reversion', 'high_iv', 'sell_premium']
            elif iv_rank < 30:
                # Low IV - buy premium (debit spread)
                direction = 'long'
                option_type = 'call'
                delta_target = 0.35
                # Scale confidence: 20-30 range gets 50-60, <20 gets 60-85
                if iv_rank < 20:
                    raw_conf = min(85, 60 + (20 - iv_rank))
                else:
                    raw_conf = min(60, 50 + (30 - iv_rank))
                confidence = self._adjust_confidence(raw_conf, 'iv_reversion')
                notes = f'IV Rank at {iv_rank}%. Buy premium - debit spread setup.'
                tags = ['iv_reversion', 'low_iv', 'buy_premium']
            else:
                return None

            return {
                'signal_id': f'SIG-{date.today().strftime("%Y%m%d")}-IV-{ticker}',
                'signal_type': 'iv_reversion',
                'ticker': ticker.upper(),
                'direction': direction,
                'option_type': option_type,
                'strike': round(current_price),
                'expiration': self._get_target_expiration([30, 45]),
                'confidence': round(confidence),
                'underlying_price': current_price,
                'delta_target': delta_target,
                'dte_range': [30, 45],
                'tags': tags,
                'notes': notes,
                'iv_data': {
                    'iv_rank': iv_rank,
                    'atm_iv': atm_iv,
                    'history_length': iv_result.get('history_length', 0),
                    'percentile_method': iv_result.get('percentile_method', 'unknown'),
                    'risk_reversal': risk_reversal,
                    'put_25d_iv': put_25d,
                    'call_25d_iv': call_25d,
                    'skew_ratio': iv_result.get('skew_ratio'),
                },
            }
        except Exception as e:
            logger.error(f"IV reversion check error for {ticker}: {e}")
            return None

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _get_target_expiration(self, dte_range: list) -> str:
        """Get a target expiration date string within DTE range."""
        target_dte = dte_range[0] + (dte_range[1] - dte_range[0]) // 2
        target_date = date.today() + timedelta(days=target_dte)
        # Align to Friday
        days_to_friday = (4 - target_date.weekday()) % 7
        target_date += timedelta(days=days_to_friday)
        return target_date.strftime('%Y-%m-%d')

    def _get_upcoming_events(self) -> List[dict]:
        """Get upcoming macro events from filesystem cache."""
        import json
        from pathlib import Path

        # Check for cached macro events
        events_file = Path(self.volume_path) / "paper_trading" / "macro_events.json"
        if events_file.exists():
            try:
                events = json.loads(events_file.read_text())
                return events
            except Exception:
                pass

        # Hardcoded major recurring events with typical severity
        today = date.today()
        recurring = [
            {'name': 'FOMC Decision', 'severity': 5, 'day_of_month': [15, 16]},
            {'name': 'CPI Report', 'severity': 4, 'day_of_month': [10, 11, 12, 13]},
            {'name': 'NFP Report', 'severity': 4, 'day_of_month': [1, 2, 3, 4, 5, 6, 7]},
            {'name': 'PCE Data', 'severity': 3, 'day_of_month': [28, 29, 30]},
            {'name': 'PPI Report', 'severity': 3, 'day_of_month': [14, 15]},
        ]

        events = []
        for r in recurring:
            for dom in r['day_of_month']:
                try:
                    event_date = today.replace(day=dom)
                    if event_date < today:
                        # Check next month
                        if today.month == 12:
                            event_date = event_date.replace(year=today.year + 1, month=1)
                        else:
                            event_date = event_date.replace(month=today.month + 1)
                    days_until = (event_date - today).days
                    if days_until <= 7:
                        events.append({
                            'name': r['name'],
                            'severity': r['severity'],
                            'date': event_date.isoformat(),
                            'days_until': days_until,
                        })
                        break  # Only first match per event type
                except ValueError:
                    continue

        return events
