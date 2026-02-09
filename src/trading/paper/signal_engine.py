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

import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Previous regime cache for detecting flips
_prev_regimes = {}  # ticker -> {'gex_regime': str, 'combined_regime': str, 'ts': str}


class SignalEngine:
    def __init__(self, volume_path: str):
        self.volume_path = volume_path
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

    async def evaluate_signals(self, ticker: str, config: dict) -> List[dict]:
        """Evaluate all signal sources for a ticker, return actionable signals."""
        signals = []
        all_raw_signals = []
        min_confidence = config.get('min_confidence', 60)
        multi_leg_enabled = config.get('multi_leg_enabled', False)

        # Run signal evaluators
        gex_sig = await self._check_gex_flip(ticker)
        regime_sig = await self._check_regime_shift(ticker)
        macro_sig = await self._check_macro_event(ticker)
        iv_sig = await self._check_iv_reversion(ticker)

        # Collect all non-None signals for transition composite
        for sig in [gex_sig, regime_sig, macro_sig, iv_sig]:
            if sig:
                all_raw_signals.append(sig)

        # Compute regime transition probability from all signals
        transition = self._compute_transition_probability(all_raw_signals)

        for sig in all_raw_signals:
            if sig.get('confidence', 0) >= min_confidence:
                # Attach transition info to each signal
                sig['transition'] = transition
                # Multi-leg: attach strategy recommendation when enabled
                if multi_leg_enabled and self.strategy_selector:
                    try:
                        strategy_rec = self._attach_strategy_recommendation(sig, ticker)
                        if strategy_rec:
                            sig['strategy_recommendation'] = strategy_rec
                    except Exception as e:
                        logger.debug(f"Strategy recommendation skipped for {ticker}: {e}")
                signals.append(sig)

        signals.sort(key=lambda s: s.get('confidence', 0), reverse=True)
        max_signals = config.get('max_signals_per_check', 3)
        return signals[:max_signals]

    def _attach_strategy_recommendation(self, signal: dict, ticker: str) -> Optional[dict]:
        """Build regime state from signal data and get strategy recommendation."""
        if not self.strategy_selector:
            return None

        regime_data = signal.get('regime_data', {})
        iv_data = signal.get('iv_data', {})
        event_data = signal.get('event_data', {})

        iv_rank = iv_data.get('iv_rank', 50)
        regime_state = {
            'vrp': (iv_rank - 30) / 10,  # calibrated: IV Rank 70 → VRP 4.0
            'gex_regime': regime_data.get('regime', regime_data.get('gex_regime', 'transitional')),
            'combined_regime': regime_data.get('combined_regime', 'neutral_transitional'),
            'flow_toxicity': 0.3,  # default; real value computed in paper_engine
            'term_structure': signal.get('term_structure', 'contango'),
            'skew_steep': signal.get('skew_steep', False),
            'skew_ratio': signal.get('skew_ratio', 1.0),
            'iv_rank': iv_rank,
            'vanna_flow': 0.0,
            'macro_event_days': event_data.get('days_until', 99),
        }

        strategies = self.strategy_selector.select_strategy(regime_state)
        if strategies and strategies[0].get('name') != 'Wait / Reduce Size':
            return strategies[0]
        return None

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
        """Detect GEX flip from positive to negative or vice versa."""
        try:
            from src.data.tastytrade_provider import get_gex_regime_tastytrade
            regime_data = await get_gex_regime_tastytrade(ticker)
            if 'error' in regime_data:
                return None

            current_regime = regime_data.get('regime', 'transitional')
            prev = _prev_regimes.get(ticker, {})
            prev_regime = prev.get('gex_regime', current_regime)

            # Update cache
            _prev_regimes.setdefault(ticker, {})['gex_regime'] = current_regime
            _prev_regimes[ticker]['ts'] = datetime.utcnow().isoformat()

            # Detect flip
            if prev_regime == current_regime:
                return None

            flip_type = f'{prev_regime}_to_{current_regime}'
            raw_confidence = regime_data.get('confidence', 0) * 100
            confidence = self._adjust_confidence(raw_confidence, 'gex_flip')

            # Determine trade direction
            if current_regime == 'volatile':
                direction = 'long'
                option_type = 'put'
                notes = f'GEX flipped negative ({flip_type}). Bearish setup.'
            elif current_regime == 'pinned':
                direction = 'long'
                option_type = 'call'
                notes = f'GEX flipped positive ({flip_type}). Bullish setup.'
            else:
                return None  # Transitional not actionable

            dte_range = [30, 45]
            current_price = regime_data.get('current_price', 0)

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
                'tags': ['gex_flip', flip_type],
                'notes': notes,
                'regime_data': {
                    'regime': current_regime,
                    'prev_regime': prev_regime,
                    'gex_score': regime_data.get('regime_score'),
                    'gex_billions': regime_data.get('gex_billions'),
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
            prev = _prev_regimes.get(ticker, {})
            prev_combined = prev.get('combined_regime', current)

            _prev_regimes.setdefault(ticker, {})['combined_regime'] = current

            if prev_combined == current:
                return None

            risk_level = combined.get('risk_level', 'moderate')
            current_price = combined.get('current_price', 0)

            # Only act on significant regime changes
            actionable = {
                'opportunity': ('long', 'call', 85),
                'danger': ('long', 'put', 80),
                'high_risk': ('long', 'put', 70),
                'melt_up': ('long', 'call', 65),
            }

            if current not in actionable:
                return None

            direction, option_type, base_confidence = actionable[current]
            # Scale by position_multiplier
            multiplier = combined.get('position_multiplier', 0.5)
            raw_confidence = base_confidence * max(multiplier, 0.3)
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
        try:
            from src.data.tastytrade_provider import get_gex_regime_tastytrade
            regime = await get_gex_regime_tastytrade(ticker)
            current_price = regime.get('current_price', 0) if regime and 'error' not in regime else 0

            # Check upcoming events
            events = self._get_upcoming_events()
            if not events:
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
        """Check IV Rank for mean reversion signals."""
        try:
            from src.data.tastytrade_provider import get_gex_regime_tastytrade
            regime = await get_gex_regime_tastytrade(ticker)
            if not regime or 'error' in regime:
                return None

            current_price = regime.get('current_price', 0)

            # Try to get IV data from options analysis
            from src.data.tastytrade_provider import get_options_with_greeks_tastytrade
            chain = await get_options_with_greeks_tastytrade(ticker)
            if not chain:
                return None

            iv_rank = chain.get('iv_rank', 50)

            if iv_rank > 80:
                # High IV - sell premium (credit spread)
                direction = 'short'
                option_type = 'call'
                delta_target = 0.16
                raw_conf = min(90, 60 + (iv_rank - 80))
                confidence = self._adjust_confidence(raw_conf, 'iv_reversion')
                notes = f'IV Rank at {iv_rank}%. Sell premium - credit spread setup.'
                tags = ['iv_reversion', 'high_iv', 'sell_premium']
            elif iv_rank < 20:
                # Low IV - buy premium (debit spread)
                direction = 'long'
                option_type = 'call'
                delta_target = 0.35
                raw_conf = min(85, 55 + (20 - iv_rank))
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
