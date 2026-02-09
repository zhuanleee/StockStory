"""
Adaptive Engine — Closes feedback loops between trading outcomes and signal generation.

Phase 1a: Signal confidence adjustment from win rates
Phase 1b: Composite weight adaptation via Thompson Sampling
Phase 1c: Greeks P&L attribution + adaptive exit parameters
Phase 3a: Unified edge score
Phase 3b: Strategy auto-selector
Phase 4c: Regime-specific Kelly position sizing
"""

import json
import math
import logging
import random
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

logger = logging.getLogger(__name__)


# =============================================================================
# PHASE 1a: Signal Performance Tracker
# =============================================================================

class SignalPerformanceTracker:
    """Tracks win rates and adjusts signal confidence based on historical outcomes."""

    def __init__(self, volume_path: str):
        self.perf_file = Path(volume_path) / "paper_trading" / "signal_performance.json"
        self._cache = None
        self._cache_ts = 0

    def _load(self) -> Dict:
        import time as _t
        now = _t.time()
        if self._cache and (now - self._cache_ts) < 30:
            return self._cache
        if self.perf_file.exists():
            try:
                self._cache = json.loads(self.perf_file.read_text())
                self._cache_ts = now
                return self._cache
            except Exception:
                pass
        default = {
            'signal_types': {},  # signal_type -> {wins, losses, total_pnl, avg_win, avg_loss}
            'strategies': {},   # strategy -> same
            'tickers': {},      # ticker -> same
            'last_updated': None,
        }
        self._cache = default
        return default

    def _save(self, data: Dict):
        self.perf_file.parent.mkdir(parents=True, exist_ok=True)
        data['last_updated'] = datetime.utcnow().isoformat()
        self.perf_file.write_text(json.dumps(data, indent=2))
        self._cache = data

    def update_from_journal(self, closed_trades: List[dict]):
        """Rebuild performance stats from closed trades."""
        data = {'signal_types': {}, 'strategies': {}, 'tickers': {}, 'last_updated': None}

        for t in closed_trades:
            pnl = t.get('pnl_dollars', 0) or 0
            is_win = pnl > 0

            for group_key, group_val in [
                ('signal_types', t.get('signal_type', 'unknown')),
                ('strategies', t.get('strategy', 'Manual')),
                ('tickers', t.get('ticker', 'UNKNOWN')),
            ]:
                if group_val not in data[group_key]:
                    data[group_key][group_val] = {
                        'wins': 0, 'losses': 0, 'total': 0,
                        'total_pnl': 0, 'win_pnl': 0, 'loss_pnl': 0,
                        'avg_win': 0, 'avg_loss': 0, 'win_rate': 0,
                        'expectancy': 0, 'kelly_fraction': 0,
                    }
                rec = data[group_key][group_val]
                rec['total'] += 1
                rec['total_pnl'] += pnl
                if is_win:
                    rec['wins'] += 1
                    rec['win_pnl'] += pnl
                else:
                    rec['losses'] += 1
                    rec['loss_pnl'] += pnl

                # Recompute derived metrics
                rec['win_rate'] = round(rec['wins'] / rec['total'] * 100, 1) if rec['total'] > 0 else 0
                rec['avg_win'] = round(rec['win_pnl'] / rec['wins'], 2) if rec['wins'] > 0 else 0
                rec['avg_loss'] = round(rec['loss_pnl'] / rec['losses'], 2) if rec['losses'] > 0 else 0
                rec['expectancy'] = round(
                    (rec['win_rate'] / 100 * rec['avg_win']) +
                    ((1 - rec['win_rate'] / 100) * rec['avg_loss']), 2
                )
                # Kelly fraction: f* = (p*b - q) / b where b = avg_win/|avg_loss|
                if rec['avg_loss'] != 0 and rec['avg_win'] > 0:
                    b = rec['avg_win'] / abs(rec['avg_loss'])
                    p = rec['win_rate'] / 100
                    q = 1 - p
                    kelly = (p * b - q) / b if b > 0 else 0
                    rec['kelly_fraction'] = round(max(0, kelly), 4)
                else:
                    rec['kelly_fraction'] = 0

        self._save(data)
        return data

    def get_confidence_adjustment(self, signal_type: str, min_samples: int = 5) -> float:
        """
        Returns a confidence multiplier (0.5 to 1.5) based on historical performance.
        Requires min_samples trades before adjusting (Bayesian smoothing).
        """
        data = self._load()
        rec = data.get('signal_types', {}).get(signal_type)
        if not rec or rec.get('total', 0) < min_samples:
            return 1.0  # No adjustment until enough data

        win_rate = rec.get('win_rate', 50)
        # Bayesian smoothing: blend with prior (50% win rate) based on sample size
        n = rec['total']
        prior_weight = max(0, (min_samples * 2 - n) / (min_samples * 2))
        smoothed_wr = win_rate * (1 - prior_weight) + 50 * prior_weight

        # Map win rate to multiplier: 30% -> 0.6, 50% -> 1.0, 70% -> 1.4
        multiplier = 0.2 + (smoothed_wr / 100) * 1.6
        return round(max(0.5, min(1.5, multiplier)), 3)

    def get_signal_stats(self, signal_type: str) -> Optional[Dict]:
        data = self._load()
        return data.get('signal_types', {}).get(signal_type)

    def get_all_stats(self) -> Dict:
        return self._load()


# =============================================================================
# PHASE 1b: Adaptive Composite Weights (Thompson Sampling)
# =============================================================================

class AdaptiveWeights:
    """
    Adapts the 7-factor composite weights using Thompson Sampling.
    Each factor has alpha/beta parameters updated by trade outcomes.
    """

    DEFAULT_WEIGHTS = {
        'dealer_flow': 20, 'squeeze': 15, 'smart_money': 20,
        'price_vs_maxpain': 10, 'skew': 10, 'term': 10, 'price_vs_walls': 15,
        'dealer_flow_forecast': 0,  # Phase 2b: starts at 0, learns its weight
    }

    def __init__(self, volume_path: str):
        self.weights_file = Path(volume_path) / "paper_trading" / "adaptive_weights.json"
        self._cache = None

    def _load(self) -> Dict:
        if self._cache:
            return self._cache
        if self.weights_file.exists():
            try:
                self._cache = json.loads(self.weights_file.read_text())
                return self._cache
            except Exception:
                pass
        # Initialize with default priors (alpha=beta=2 = uniform-ish)
        default = {
            'factors': {},
            'regime_weights': {},  # regime -> factor weights
            'total_updates': 0,
            'last_updated': None,
        }
        for name, default_weight in self.DEFAULT_WEIGHTS.items():
            default['factors'][name] = {
                'alpha': 2.0 + default_weight / 10,  # Prior biased toward default
                'beta': 2.0,
                'current_weight': default_weight,
                'wins_when_high': 0,
                'losses_when_high': 0,
                'wins_when_low': 0,
                'losses_when_low': 0,
            }
        self._cache = default
        return default

    def _save(self, data: Dict):
        self.weights_file.parent.mkdir(parents=True, exist_ok=True)
        data['last_updated'] = datetime.utcnow().isoformat()
        self.weights_file.write_text(json.dumps(data, indent=2))
        self._cache = data

    def get_weights(self, regime: str = None) -> Dict[str, float]:
        """
        Get current adaptive weights. Uses Thompson Sampling to sample
        from posterior distributions, then normalizes to sum=100.
        """
        data = self._load()

        # If regime-specific weights exist and enough data, use them
        if regime and regime in data.get('regime_weights', {}):
            rw = data['regime_weights'][regime]
            if rw.get('total_updates', 0) >= 10:
                return rw.get('weights', dict(self.DEFAULT_WEIGHTS))

        # Not enough data yet — use default weights with minor Thompson exploration
        if data.get('total_updates', 0) < 20:
            return dict(self.DEFAULT_WEIGHTS)

        # Thompson Sampling: sample from Beta(alpha, beta) for each factor
        sampled = {}
        for name, factor in data['factors'].items():
            alpha = max(1.0, factor.get('alpha', 2.0))
            beta = max(1.0, factor.get('beta', 2.0))
            sampled[name] = random.betavariate(alpha, beta)

        # Normalize to sum = 100
        total = sum(sampled.values())
        if total <= 0:
            return dict(self.DEFAULT_WEIGHTS)

        weights = {}
        for name, val in sampled.items():
            weights[name] = round(val / total * 100, 1)

        return weights

    def update_from_trade(self, trade: dict, factor_scores: dict):
        """
        Update Thompson Sampling parameters based on a closed trade outcome.
        trade: closed trade with pnl_dollars
        factor_scores: dict of {factor_name: score (0-100)} at time of entry
        """
        data = self._load()
        pnl = trade.get('pnl_dollars', 0) or 0
        is_win = pnl > 0

        for name, score in factor_scores.items():
            if name not in data['factors']:
                data['factors'][name] = {
                    'alpha': 2.0, 'beta': 2.0, 'current_weight': 5,
                    'wins_when_high': 0, 'losses_when_high': 0,
                    'wins_when_low': 0, 'losses_when_low': 0,
                }
            factor = data['factors'][name]
            is_high = score >= 60  # Factor was "agreeing" with bullish thesis

            if is_high:
                if is_win:
                    factor['alpha'] += 1.0  # Factor was right when it agreed
                    factor['wins_when_high'] += 1
                else:
                    factor['beta'] += 1.0  # Factor was wrong when it agreed (symmetric update)
                    factor['losses_when_high'] += 1
            else:
                if is_win:
                    factor['beta'] += 0.5  # Factor disagreed but trade won (factor less useful)
                    factor['wins_when_low'] += 1
                else:
                    factor['alpha'] += 0.5  # Factor disagreed and trade lost (factor was right to disagree)
                    factor['losses_when_low'] += 1

            # Recompute current weight from posterior mean
            total_ab = factor['alpha'] + factor['beta']
            factor['current_weight'] = round(factor['alpha'] / total_ab * 100, 1)

        data['total_updates'] = data.get('total_updates', 0) + 1

        # Update regime-specific weights
        regime = trade.get('entry_regime', trade.get('tags', [''])[0] if trade.get('tags') else '')
        if regime:
            if regime not in data['regime_weights']:
                data['regime_weights'][regime] = {'weights': dict(self.DEFAULT_WEIGHTS), 'total_updates': 0}
            rw = data['regime_weights'][regime]
            rw['total_updates'] += 1
            # Simple exponential moving average for regime weights
            alpha_lr = 0.1  # Learning rate
            for name, score in factor_scores.items():
                if name in rw['weights']:
                    if is_win:
                        rw['weights'][name] = round(
                            rw['weights'][name] * (1 - alpha_lr) + (score / 100 * 20) * alpha_lr, 1
                        )

        self._save(data)

    def get_stats(self) -> Dict:
        return self._load()


# =============================================================================
# PHASE 1c: Greeks P&L Attribution
# =============================================================================

class GreeksPnLTracker:
    """Decomposes P&L into delta/gamma/theta/vega contributions."""

    @staticmethod
    def decompose_pnl(
        entry_price: float, current_price: float,
        entry_underlying: float, current_underlying: float,
        delta: float, gamma: float, theta: float, vega: float,
        entry_iv: float, current_iv: float,
        days_held: float, quantity: int = 1, multiplier: int = 100,
        vanna: float = 0.0, charm: float = 0.0,
    ) -> Dict:
        """
        Decompose option P&L into Greek components.

        Returns dict with delta_pnl, gamma_pnl, theta_pnl, vega_pnl,
        vanna_pnl, charm_pnl, unexplained.
        Second-order cross-terms (vanna, charm) explain 5-15% of previously
        'unexplained' P&L.
        """
        dS = current_underlying - entry_underlying
        d_sigma = current_iv - entry_iv  # IV change
        dt = days_held / 365  # Time in years

        # Greek-attributed P&L (per contract)
        delta_pnl = delta * dS
        gamma_pnl = 0.5 * gamma * (dS ** 2)
        theta_pnl = theta * days_held  # Theta is per-day
        vega_pnl = vega * d_sigma * 100  # Vega is per 1% IV change

        # Second-order cross-terms
        vanna_pnl = vanna * dS * d_sigma * 100  # dDelta/dVol × ΔS × Δσ
        charm_pnl = charm * dS * dt              # dDelta/dTime × ΔS × Δt

        # Total attributed
        total_attributed = (delta_pnl + gamma_pnl + theta_pnl + vega_pnl
                            + vanna_pnl + charm_pnl)

        # Actual P&L
        actual_pnl = (current_price - entry_price)

        # Unexplained (higher-order Greeks, model error)
        unexplained = actual_pnl - total_attributed

        return {
            'delta_pnl': round(delta_pnl * quantity * multiplier, 2),
            'gamma_pnl': round(gamma_pnl * quantity * multiplier, 2),
            'theta_pnl': round(theta_pnl * quantity * multiplier, 2),
            'vega_pnl': round(vega_pnl * quantity * multiplier, 2),
            'vanna_pnl': round(vanna_pnl * quantity * multiplier, 2),
            'charm_pnl': round(charm_pnl * quantity * multiplier, 2),
            'unexplained': round(unexplained * quantity * multiplier, 2),
            'total_attributed': round(total_attributed * quantity * multiplier, 2),
            'actual_pnl': round(actual_pnl * quantity * multiplier, 2),
            'attribution_accuracy': round(
                (1 - abs(unexplained) / max(abs(actual_pnl), 0.01)) * 100, 1
            ) if actual_pnl != 0 else 100,
        }


def gamma_breakeven_move(theta: float, gamma: float) -> float:
    """Daily break-even move: the underlying move needed to offset theta decay.

    Derived from: gamma P&L = 0.5 × Γ × ΔS² must equal |θ|
    ΔS = √(2 × |θ| / Γ)

    Returns the break-even move in price terms (dollars).
    """
    if gamma <= 0 or theta >= 0:
        return 0.0
    import math
    return math.sqrt(2 * abs(theta) / gamma)


# =============================================================================
# PHASE 1c: Adaptive Exit Parameters
# =============================================================================

class AdaptiveExitEngine:
    """Learns optimal exit parameters from historical trade outcomes."""

    def __init__(self, volume_path: str):
        self.exit_file = Path(volume_path) / "paper_trading" / "adaptive_exits.json"

    def _load(self) -> Dict:
        if self.exit_file.exists():
            try:
                return json.loads(self.exit_file.read_text())
            except Exception:
                pass
        return {
            'by_strategy': {},
            'by_signal_type': {},
            'optimal_exits': {
                'stop_loss_pct': -50,
                'take_profit_pct': 100,
                'time_exit_dte': 7,
            },
            'total_analyzed': 0,
        }

    def _save(self, data: Dict):
        self.exit_file.parent.mkdir(parents=True, exist_ok=True)
        self.exit_file.write_text(json.dumps(data, indent=2))

    def learn_from_trades(self, closed_trades: List[dict]):
        """Analyze closed trades to find optimal exit parameters."""
        data = self._load()

        for group_key in ['by_strategy', 'by_signal_type']:
            field = 'strategy' if group_key == 'by_strategy' else 'signal_type'
            by_group = defaultdict(list)
            for t in closed_trades:
                by_group[t.get(field, 'unknown')].append(t)

            for group_name, trades in by_group.items():
                winners = [t for t in trades if (t.get('pnl_dollars') or 0) > 0]
                losers = [t for t in trades if (t.get('pnl_dollars') or 0) < 0]

                # Analyze winner exit timing
                winner_pnl_pcts = [t.get('pnl_pct', 0) or 0 for t in winners]
                loser_pnl_pcts = [t.get('pnl_pct', 0) or 0 for t in losers]

                # Optimal take profit = median winner P&L %
                optimal_tp = (
                    sorted(winner_pnl_pcts)[len(winner_pnl_pcts) // 2]
                    if winner_pnl_pcts else 100
                )

                # Optimal stop loss = 75th percentile loser (cut losses tighter)
                optimal_sl = (
                    sorted(loser_pnl_pcts)[int(len(loser_pnl_pcts) * 0.75)]
                    if loser_pnl_pcts else -50
                )

                # Analyze DTE at exit for winners vs losers
                winner_dtes = []
                loser_dtes = []
                for t in trades:
                    if t.get('exit_reason') == 'time_exit':
                        dte = _calc_exit_dte(t)
                        if dte is not None:
                            if (t.get('pnl_dollars') or 0) > 0:
                                winner_dtes.append(dte)
                            else:
                                loser_dtes.append(dte)

                data[group_key][group_name] = {
                    'count': len(trades),
                    'optimal_take_profit': round(max(30, min(300, optimal_tp)), 0),
                    'optimal_stop_loss': round(max(-80, min(-20, optimal_sl)), 0),
                    'avg_winner_pnl_pct': round(sum(winner_pnl_pcts) / len(winner_pnl_pcts), 1) if winner_pnl_pcts else 0,
                    'avg_loser_pnl_pct': round(sum(loser_pnl_pcts) / len(loser_pnl_pcts), 1) if loser_pnl_pcts else 0,
                }

        data['total_analyzed'] = len(closed_trades)
        self._save(data)
        return data

    def get_exit_params(self, strategy: str = None, signal_type: str = None,
                        min_samples: int = 5) -> Dict:
        """Get learned exit parameters for a given strategy/signal type."""
        data = self._load()
        defaults = data.get('optimal_exits', {
            'stop_loss_pct': -50, 'take_profit_pct': 100, 'time_exit_dte': 7
        })

        # Try strategy-specific first, then signal-type, then defaults
        for group_key, key in [('by_strategy', strategy), ('by_signal_type', signal_type)]:
            if key and key in data.get(group_key, {}):
                rec = data[group_key][key]
                if rec.get('count', 0) >= min_samples:
                    return {
                        'stop_loss_pct': rec.get('optimal_stop_loss', defaults['stop_loss_pct']),
                        'take_profit_pct': rec.get('optimal_take_profit', defaults['take_profit_pct']),
                        'time_exit_dte': defaults.get('time_exit_dte', 7),
                        'source': f'adaptive_{group_key}',
                        'sample_size': rec['count'],
                    }

        return {**defaults, 'source': 'default', 'sample_size': 0}


# =============================================================================
# PHASE 3a: Unified Edge Score
# =============================================================================

class EdgeScoreEngine:
    """
    Synthesizes all signals into a single actionable edge score.
    Combines: regime state + dealer flow + VRP + flow toxicity + learning adjustments.
    """

    def compute_edge(
        self,
        composite_score: float,
        gex_regime: str,
        combined_regime: str,
        vrp: float,  # IV - RV
        flow_toxicity: float,  # 0-1
        dealer_flow_forecast: Dict,  # from Phase 2b
        signal_performance: Dict,  # from Phase 1a
        adaptive_weights: Dict,  # from Phase 1b
        term_structure: str = 'contango',
        skew_ratio: float = 1.0,
        strategy_type: str = 'short_premium',
    ) -> Dict:
        """
        Compute unified edge score (0-100) with confidence and Kelly sizing.
        Now includes term structure, skew, and boosted VRP weight.
        """
        # Base edge from composite (0-100)
        edge = composite_score

        # Regime adjustment: opportunity/melt_up boost, danger/high_risk penalize
        regime_adj = {
            'opportunity': 15, 'melt_up': 8, 'neutral_pinned': 5,
            'neutral_transitional': 0, 'neutral_volatile': -5,
            'high_risk': -15, 'danger': -25,
        }
        edge += regime_adj.get(combined_regime, 0)

        # VRP adjustment: boosted cap to 15 (research: VRP is strongest edge)
        vrp_adj = 0
        if vrp > 4:
            vrp_adj = min(15, vrp - 4)  # +1 per point above 4, cap 15
        elif vrp < 0:
            vrp_adj = -min(10, abs(vrp))  # Negative VRP = headwind
        edge += vrp_adj

        # Flow toxicity: high toxicity = informed flow = edge boost if aligned
        if flow_toxicity > 0.7:
            edge += 5  # Smart money is active — signals more reliable

        # Dealer flow forecast adjustment
        if dealer_flow_forecast:
            net_flow = dealer_flow_forecast.get('net_flow_billions', 0)
            if abs(net_flow) > 0.5:
                edge += min(8, abs(net_flow) * 3)

        # Term structure signal: favorable alignment boosts edge
        term_adj = 0
        if strategy_type == 'short_premium' and term_structure == 'contango':
            term_adj = 5  # Contango favors selling premium (front IV < back)
        elif strategy_type == 'long_premium' and term_structure == 'backwardation':
            term_adj = 5  # Backwardation = elevated near-term vol, good for buying
        edge += term_adj

        # Skew signal: steep skew benefits short premium strategies
        skew_adj = 0
        if skew_ratio > 1.15 and strategy_type == 'short_premium':
            skew_adj = 3  # Steep skew = overpriced tails, edge for selling
        edge += skew_adj

        # Clamp
        edge = max(0, min(100, round(edge)))

        # Direction
        if edge >= 55:
            direction = 'bullish'
        elif edge <= 45:
            direction = 'bearish'
        else:
            direction = 'neutral'

        # Confidence based on signal agreement and sample size
        n_factors_agree = sum(1 for s in [
            composite_score >= 55,
            combined_regime in ('opportunity', 'melt_up'),
            vrp > 2,
            flow_toxicity > 0.5,
            term_adj > 0,
        ] if s)

        confidence = 'low'
        if n_factors_agree >= 4:
            confidence = 'high'
        elif n_factors_agree >= 2:
            confidence = 'medium'

        # Kelly fraction from edge score
        win_prob = edge / 100
        avg_payoff = 1.5  # Default R:R assumption
        kelly_raw = (win_prob * avg_payoff - (1 - win_prob)) / avg_payoff
        kelly_fraction = max(0, round(kelly_raw * 0.5, 4))  # Half-Kelly

        return {
            'edge_score': edge,
            'direction': direction,
            'confidence': confidence,
            'kelly_fraction': kelly_fraction,
            'n_factors_agree': n_factors_agree,
            'components': {
                'composite_base': composite_score,
                'regime_adj': regime_adj.get(combined_regime, 0),
                'vrp_adj': round(vrp_adj, 2),
                'flow_toxicity': round(flow_toxicity, 3),
                'dealer_flow': dealer_flow_forecast.get('net_flow_billions', 0) if dealer_flow_forecast else 0,
                'term_structure_adj': term_adj,
                'skew_adj': skew_adj,
                'term_structure': term_structure,
                'skew_ratio': round(skew_ratio, 3),
            },
        }


# =============================================================================
# PHASE 3b: Strategy Auto-Selector
# =============================================================================

class StrategySelector:
    """
    Selects optimal strategy based on current regime + VRP + GEX + term structure.
    """

    STRATEGY_MATRIX = [
        # (conditions_fn, strategy, description)
        {
            'name': 'Credit Spread (Premium Harvest)',
            'conditions': lambda r: (
                r['vrp'] > 4 and
                r['gex_regime'] == 'pinned' and
                r['flow_toxicity'] < 0.5
            ),
            'type': 'short_premium',
            'direction': 'neutral_bullish',
            'dte_range': [30, 45],
            'delta_target': 0.16,
            'description': 'High VRP + dealer support + low toxicity. Harvest premium safely.',
        },
        {
            'name': 'Long Gamma (Momentum)',
            'conditions': lambda r: (
                r['vrp'] < 2 and
                r['gex_regime'] == 'volatile' and
                r['flow_toxicity'] > 0.6
            ),
            'type': 'long_premium',
            'direction': 'directional',
            'dte_range': [14, 30],
            'delta_target': 0.40,
            'description': 'Cheap options + dealer amplification + informed flow. Ride the move.',
        },
        {
            'name': 'Ratio Spread (Skew Harvest)',
            'conditions': lambda r: (
                r['vrp'] > 3 and
                r['term_structure'] == 'backwardation' and
                r['skew_steep']
            ),
            'type': 'short_premium',
            'direction': 'neutral_bearish',
            'dte_range': [30, 60],
            'delta_target': 0.25,
            'description': 'Rich skew + backwardation. Sell OTM put premium via ratio spread.',
        },
        {
            'name': 'Directional Call (Vanna Unwind)',
            'conditions': lambda r: (
                r['combined_regime'] == 'opportunity' and
                r.get('vanna_flow', 0) > 0.5
            ),
            'type': 'long_premium',
            'direction': 'bullish',
            'dte_range': [14, 30],
            'delta_target': 0.50,
            'description': 'Fear + dealer support + vanna buying pressure. Ride dealer flows.',
        },
        {
            'name': 'Protective Put (Hedge)',
            'conditions': lambda r: (
                r['combined_regime'] == 'danger' or
                (r['combined_regime'] == 'high_risk' and r['flow_toxicity'] > 0.7)
            ),
            'type': 'long_premium',
            'direction': 'bearish',
            'dte_range': [14, 30],
            'delta_target': 0.30,
            'description': 'Danger zone. Buy protection.',
        },
        {
            'name': 'Iron Condor (Range Bound)',
            'conditions': lambda r: (
                r['gex_regime'] == 'pinned' and
                r['vrp'] > 2 and
                r['flow_toxicity'] < 0.4 and
                r['combined_regime'] not in ('danger', 'high_risk')
            ),
            'type': 'short_premium',
            'direction': 'neutral',
            'dte_range': [30, 45],
            'delta_target': 0.16,
            'description': 'Pinned regime + mild VRP + quiet flow. Sell wings.',
        },
        {
            'name': 'Straddle (Event Vol)',
            'conditions': lambda r: (
                r.get('macro_event_days', 99) <= 3
                and r.get('iv_rank', 50) < 50  # Don't buy vol when IV already expanded
            ),
            'type': 'long_premium',
            'direction': 'neutral',
            'dte_range': [7, 21],
            'delta_target': 0.50,
            'description': 'Major macro event imminent + IV not yet expanded. Buy vol.',
        },
        # --- New strategies filling regime gaps ---
        {
            'name': 'Melt-Up Debit Spread',
            'conditions': lambda r: r['combined_regime'] == 'melt_up',
            'type': 'long_premium',
            'direction': 'bullish',
            'dte_range': [14, 30],
            'delta_target': 0.45,
            'description': 'Melt-up regime — strong bullish momentum + dealer support. Bull call spread.',
        },
        {
            'name': 'Moderate Credit Spread (VRP Harvest)',
            'conditions': lambda r: (
                r['vrp'] > 1.5 and
                r['flow_toxicity'] < 0.6 and
                r['combined_regime'] not in ('danger', 'high_risk', 'neutral_volatile')
            ),
            'type': 'short_premium',
            'direction': 'neutral_bullish',
            'dte_range': [30, 45],
            'delta_target': 0.20,
            'description': 'Moderate VRP + calm conditions. Harvest premium with wider delta.',
        },
        {
            'name': 'Iron Butterfly (Pinned)',
            'conditions': lambda r: (
                r['gex_regime'] == 'pinned' and
                r['flow_toxicity'] < 0.5 and
                r['combined_regime'] not in ('danger', 'high_risk')
            ),
            'type': 'short_premium',
            'direction': 'neutral',
            'dte_range': [14, 30],
            'delta_target': 0.50,
            'description': 'Pinned regime — sell ATM straddle + buy wings. Max decay at pin.',
        },
        {
            'name': 'Bear Put Debit Spread',
            'conditions': lambda r: (
                r['combined_regime'] == 'high_risk' and
                r['flow_toxicity'] > 0.5
            ),
            'type': 'long_premium',
            'direction': 'bearish',
            'dte_range': [14, 30],
            'delta_target': 0.35,
            'description': 'High risk + informed flow. Bearish directional with defined risk.',
        },
        {
            'name': 'Backwardation Credit Spread',
            'conditions': lambda r: (
                r['term_structure'] == 'backwardation' and
                r['vrp'] > 2 and
                r['combined_regime'] not in ('danger', 'high_risk')
            ),
            'type': 'short_premium',
            'direction': 'neutral_bullish',
            'dte_range': [21, 35],
            'delta_target': 0.18,
            'description': 'Backwardation = elevated front IV. Sell rich front-month premium.',
        },
        # --- Softer fallbacks for scanner context ---
        {
            'name': 'Cash-Secured Put',
            'conditions': lambda r: (
                r['vrp'] > 0 and
                r['combined_regime'] not in ('danger', 'high_risk') and
                r['flow_toxicity'] < 0.7
            ),
            'type': 'short_premium',
            'direction': 'neutral_bullish',
            'dte_range': [30, 45],
            'delta_target': 0.25,
            'description': 'Slightly rich IV + stable conditions. Sell puts for income.',
        },
        {
            'name': 'Long Call (Cheap IV)',
            'conditions': lambda r: (
                r['vrp'] < 0 and
                r['combined_regime'] not in ('danger', 'high_risk')
            ),
            'type': 'long_premium',
            'direction': 'bullish',
            'dte_range': [30, 60],
            'delta_target': 0.40,
            'description': 'IV below realized — options are cheap. Buy calls for directional exposure.',
        },
    ]

    def select_strategy(self, regime_state: Dict) -> List[Dict]:
        """
        Returns ranked list of suitable strategies for current conditions.
        regime_state should contain: vrp, gex_regime, combined_regime,
        flow_toxicity, term_structure, skew_steep, vanna_flow, macro_event_days
        """
        results = []
        for strat in self.STRATEGY_MATRIX:
            try:
                if strat['conditions'](regime_state):
                    results.append({
                        'name': strat['name'],
                        'type': strat['type'],
                        'direction': strat['direction'],
                        'dte_range': strat['dte_range'],
                        'delta_target': strat['delta_target'],
                        'description': strat['description'],
                    })
            except Exception:
                continue

        # If nothing matches, suggest neutral strategies
        if not results:
            results.append({
                'name': 'Wait / Reduce Size',
                'type': 'none',
                'direction': 'neutral',
                'dte_range': [30, 45],
                'delta_target': 0,
                'description': 'No clear edge identified. Reduce position size or wait.',
            })

        return results


# =============================================================================
# PHASE 4c: Regime-Specific Kelly Position Sizing
# =============================================================================

class KellyPositionSizer:
    """
    Computes Kelly-optimal position size adjusted for regime and strategy.
    Uses fractional Kelly (default half-Kelly) for safety.
    """

    # Regime risk multipliers
    REGIME_MULTIPLIERS = {
        'opportunity': 1.0,    # Max aggression (capped at 1.0 — never overbet Kelly)
        'melt_up': 0.75,
        'neutral_pinned': 1.0,
        'neutral_transitional': 0.5,
        'neutral_volatile': 0.25,
        'high_risk': 0.25,
        'danger': 0.0,        # No new trades
    }

    def compute_position_size(
        self,
        equity: float,
        premium: float,
        signal_type: str,
        combined_regime: str,
        signal_stats: Optional[Dict],
        kelly_fraction_override: float = 0.5,  # Half Kelly default
    ) -> Dict:
        """
        Compute optimal number of contracts using Kelly criterion.

        Returns: {contracts, kelly_raw, kelly_adjusted, regime_multiplier, rationale}
        """
        if premium <= 0 or equity <= 0:
            return {'contracts': 1, 'kelly_raw': 0, 'kelly_adjusted': 0,
                    'regime_multiplier': 0, 'rationale': 'Invalid inputs'}

        # Get regime multiplier
        regime_mult = self.REGIME_MULTIPLIERS.get(combined_regime, 0.5)
        if regime_mult == 0:
            return {'contracts': 0, 'kelly_raw': 0, 'kelly_adjusted': 0,
                    'regime_multiplier': 0, 'rationale': 'Danger regime — no new trades'}

        # Calculate Kelly fraction from historical stats
        if signal_stats and signal_stats.get('total', 0) >= 5:
            win_rate = signal_stats['win_rate'] / 100
            avg_win = signal_stats.get('avg_win', 0)
            avg_loss = abs(signal_stats.get('avg_loss', 1))

            if avg_loss > 0 and avg_win > 0:
                b = avg_win / avg_loss  # Payoff ratio
                kelly_raw = (win_rate * b - (1 - win_rate)) / b
            else:
                kelly_raw = 0
        else:
            # Default assumption: 55% win rate, 1.5:1 R:R
            kelly_raw = (0.55 * 1.5 - 0.45) / 1.5

        kelly_raw = max(0, kelly_raw)

        # Fat-tail discount: equity options exhibit kurtosis ~6-10,
        # standard Kelly overallocates 2-3x. 0.6 discount → effective 30% Kelly.
        TAIL_RISK_DISCOUNT = 0.6

        # Apply fractional Kelly × tail-risk discount × regime multiplier
        kelly_adjusted = kelly_raw * kelly_fraction_override * TAIL_RISK_DISCOUNT * regime_mult

        # Convert to contracts
        max_cost = equity * kelly_adjusted
        contracts = int(max_cost / (premium * 100))
        contracts = max(0, min(contracts, 10))  # Cap at 10

        # Safety floor: at least 1 contract if Kelly > 0
        if kelly_adjusted > 0 and contracts == 0:
            contracts = 1

        return {
            'contracts': contracts,
            'kelly_raw': round(kelly_raw, 4),
            'kelly_adjusted': round(kelly_adjusted, 4),
            'regime_multiplier': regime_mult,
            'kelly_fraction': kelly_fraction_override,
            'max_cost': round(max_cost, 2),
            'rationale': (
                f'Kelly {kelly_raw:.1%} × {kelly_fraction_override:.0%} fraction '
                f'× {TAIL_RISK_DISCOUNT:.0%} tail-risk '
                f'× {regime_mult:.0%} regime = {kelly_adjusted:.1%} of equity'
            ),
        }


# =============================================================================
# PHASE 2c: VPIN Flow Toxicity Proxy
# =============================================================================

class FlowToxicityAnalyzer:
    """
    Approximates VPIN (Volume-Synchronized Probability of Informed Trading)
    from options flow data. Uses premium imbalance as proxy.
    """

    @staticmethod
    def compute_toxicity(options: list, multiplier: int = 100) -> Dict:
        """
        Compute flow toxicity from options chain data.
        Returns toxicity score (0-1) and supporting metrics.
        """
        total_call_premium = 0
        total_put_premium = 0
        total_call_volume = 0
        total_put_volume = 0
        unusual_count = 0

        for o in (options or []):
            call = o.get('call', {})
            put = o.get('put', {})

            call_vol = float(call.get('volume', 0) or 0)
            put_vol = float(put.get('volume', 0) or 0)
            call_price = float(call.get('price', 0) or 0)
            put_price = float(put.get('price', 0) or 0)
            call_oi = float(call.get('open_interest', 0) or 0)
            put_oi = float(put.get('open_interest', 0) or 0)

            total_call_volume += call_vol
            total_put_volume += put_vol
            total_call_premium += call_vol * call_price * multiplier
            total_put_premium += put_vol * put_price * multiplier

            # Unusual activity: vol/OI > 2
            if call_oi > 0 and call_vol / call_oi > 2:
                unusual_count += 1
            if put_oi > 0 and put_vol / put_oi > 2:
                unusual_count += 1

        total_premium = total_call_premium + total_put_premium
        total_volume = total_call_volume + total_put_volume

        # VPIN proxy: |call_premium - put_premium| / total_premium
        if total_premium > 0:
            premium_imbalance = abs(total_call_premium - total_put_premium) / total_premium
        else:
            premium_imbalance = 0

        # Volume imbalance
        if total_volume > 0:
            volume_imbalance = abs(total_call_volume - total_put_volume) / total_volume
        else:
            volume_imbalance = 0

        # Unusual activity ratio
        total_strikes = len(options) * 2 if options else 1
        unusual_ratio = min(1.0, unusual_count / max(total_strikes * 0.1, 1))

        # Combined toxicity score (0-1)
        # Weight: 50% premium imbalance, 30% volume imbalance, 20% unusual activity
        toxicity = (
            0.50 * premium_imbalance +
            0.30 * volume_imbalance +
            0.20 * unusual_ratio
        )
        toxicity = round(min(1.0, toxicity), 3)

        # Direction of informed flow
        if total_call_premium > total_put_premium * 1.5:
            flow_direction = 'bullish'
        elif total_put_premium > total_call_premium * 1.5:
            flow_direction = 'bearish'
        else:
            flow_direction = 'neutral'

        # Label
        if toxicity >= 0.7:
            label = 'HIGH'
        elif toxicity >= 0.4:
            label = 'MODERATE'
        else:
            label = 'LOW'

        return {
            'toxicity': toxicity,
            'label': label,
            'flow_direction': flow_direction,
            'premium_imbalance': round(premium_imbalance, 3),
            'volume_imbalance': round(volume_imbalance, 3),
            'unusual_ratio': round(unusual_ratio, 3),
            'unusual_count': unusual_count,
            'total_call_premium': round(total_call_premium, 2),
            'total_put_premium': round(total_put_premium, 2),
            'total_volume': int(total_volume),
        }


# =============================================================================
# PHASE 4a: Learning Tier Connector
# =============================================================================

class LearningTierConnector:
    """
    Connects all four learning tiers into a unified self-improving loop.

    Tier 1 (Bandit): AdaptiveWeights → composite factor weights
    Tier 2 (Regime): StrategySelector → strategy auto-selection
    Tier 3 (Exit):   AdaptiveExitEngine → optimal stop/TP/time
    Tier 4 (Meta):   Adjusts confidence multipliers, detects degradation
    """

    def __init__(self, volume_path: str):
        self.meta_file = Path(volume_path) / "paper_trading" / "learning_meta.json"

    def _load(self) -> Dict:
        if self.meta_file.exists():
            try:
                return json.loads(self.meta_file.read_text())
            except Exception:
                pass
        return {
            'tier_health': {
                'bandit': {'status': 'cold', 'updates': 0, 'last_updated': None},
                'regime': {'status': 'cold', 'updates': 0, 'last_updated': None},
                'exit': {'status': 'cold', 'updates': 0, 'last_updated': None},
                'meta': {'status': 'cold', 'updates': 0, 'last_updated': None},
            },
            'meta_adjustments': {
                'confidence_scale': 1.0,  # Global confidence scaling
                'learning_rate': 0.1,     # How fast tiers adapt
                'exploration_rate': 0.2,  # Thompson sampling exploration
            },
            'degradation_log': [],  # {ts, tier, metric, old_val, new_val, action}
            'total_feedback_loops': 0,
        }

    def _save(self, data: Dict):
        self.meta_file.parent.mkdir(parents=True, exist_ok=True)
        data['last_updated'] = datetime.utcnow().isoformat()
        self.meta_file.write_text(json.dumps(data, indent=2))

    def run_feedback_cycle(
        self,
        perf_tracker: 'SignalPerformanceTracker',
        adaptive_weights: 'AdaptiveWeights',
        adaptive_exits: 'AdaptiveExitEngine',
        closed_trades: List[dict],
    ) -> Dict:
        """
        Run a full feedback cycle across all learning tiers.
        Called periodically (after each trade close or on schedule).
        """
        data = self._load()
        results = {}

        # --- Tier 1: Bandit (weights) health check ---
        if adaptive_weights:
            w_stats = adaptive_weights.get_stats()
            n_updates = w_stats.get('total_updates', 0)
            data['tier_health']['bandit']['updates'] = n_updates
            data['tier_health']['bandit']['status'] = (
                'warm' if n_updates >= 20 else 'learning' if n_updates >= 5 else 'cold'
            )
            data['tier_health']['bandit']['last_updated'] = w_stats.get('last_updated')
            results['bandit'] = data['tier_health']['bandit']

        # --- Tier 2: Regime (strategy) health check ---
        if perf_tracker:
            strat_stats = perf_tracker.get_all_stats().get('strategies', {})
            n_strategies = len(strat_stats)
            total_strat_trades = sum(s.get('total', 0) for s in strat_stats.values())
            data['tier_health']['regime']['updates'] = total_strat_trades
            data['tier_health']['regime']['status'] = (
                'warm' if total_strat_trades >= 30 else 'learning' if total_strat_trades >= 10 else 'cold'
            )
            results['regime'] = data['tier_health']['regime']

        # --- Tier 3: Exit health check ---
        if adaptive_exits:
            exit_data = adaptive_exits._load()
            n_analyzed = exit_data.get('total_analyzed', 0)
            data['tier_health']['exit']['updates'] = n_analyzed
            data['tier_health']['exit']['status'] = (
                'warm' if n_analyzed >= 20 else 'learning' if n_analyzed >= 5 else 'cold'
            )
            results['exit'] = data['tier_health']['exit']

        # --- Tier 4: Meta adjustments ---
        # Detect overall system degradation (rolling loss rate)
        if closed_trades and len(closed_trades) >= 10:
            recent = closed_trades[-10:]
            recent_wr = sum(1 for t in recent if (t.get('pnl_dollars') or 0) > 0) / len(recent)

            if recent_wr < 0.3:
                # System degrading — increase exploration, reduce confidence
                data['meta_adjustments']['confidence_scale'] = max(0.6,
                    data['meta_adjustments']['confidence_scale'] - 0.05)
                data['meta_adjustments']['exploration_rate'] = min(0.5,
                    data['meta_adjustments']['exploration_rate'] + 0.05)
                data['degradation_log'].append({
                    'ts': datetime.utcnow().isoformat(),
                    'tier': 'meta',
                    'metric': 'recent_win_rate',
                    'value': round(recent_wr, 2),
                    'action': 'increased_exploration',
                })
            elif recent_wr > 0.6:
                # System performing well — tighten slightly
                data['meta_adjustments']['confidence_scale'] = min(1.2,
                    data['meta_adjustments']['confidence_scale'] + 0.02)
                data['meta_adjustments']['exploration_rate'] = max(0.1,
                    data['meta_adjustments']['exploration_rate'] - 0.02)

            data['tier_health']['meta']['status'] = (
                'degraded' if recent_wr < 0.3 else 'healthy' if recent_wr > 0.45 else 'caution'
            )

        # Keep only last 50 degradation log entries
        data['degradation_log'] = data['degradation_log'][-50:]
        data['total_feedback_loops'] = data.get('total_feedback_loops', 0) + 1
        data['tier_health']['meta']['updates'] = data['total_feedback_loops']

        results['meta'] = data['meta_adjustments']
        results['tier_health'] = data['tier_health']

        self._save(data)
        return results

    def get_meta_adjustments(self) -> Dict:
        """Get current meta-level adjustments for other systems to use."""
        data = self._load()
        return data.get('meta_adjustments', {
            'confidence_scale': 1.0, 'learning_rate': 0.1, 'exploration_rate': 0.2
        })

    def get_status(self) -> Dict:
        return self._load()


# =============================================================================
# PHASE 4b: A/B Testing Engine
# =============================================================================

class ABTestEngine:
    """
    Runs A/B tests in paper trading to compare strategies/parameters.
    Tracks control vs variant performance with statistical significance.
    """

    def __init__(self, volume_path: str):
        self.ab_file = Path(volume_path) / "paper_trading" / "ab_tests.json"

    def _load(self) -> Dict:
        if self.ab_file.exists():
            try:
                return json.loads(self.ab_file.read_text())
            except Exception:
                pass
        return {'tests': {}, 'completed': [], 'last_updated': None}

    def _save(self, data: Dict):
        self.ab_file.parent.mkdir(parents=True, exist_ok=True)
        data['last_updated'] = datetime.utcnow().isoformat()
        self.ab_file.write_text(json.dumps(data, indent=2))

    def create_test(self, test_id: str, description: str,
                    control: Dict, variant: Dict,
                    min_trades: int = 20) -> Dict:
        """
        Create a new A/B test.
        control/variant: {name, params} — e.g., {name: 'default_exits', params: {stop: -50, tp: 100}}
        """
        data = self._load()
        data['tests'][test_id] = {
            'id': test_id,
            'description': description,
            'control': {**control, 'trades': [], 'wins': 0, 'losses': 0, 'total_pnl': 0},
            'variant': {**variant, 'trades': [], 'wins': 0, 'losses': 0, 'total_pnl': 0},
            'min_trades': min_trades,
            'status': 'active',
            'created_at': datetime.utcnow().isoformat(),
        }
        self._save(data)
        return data['tests'][test_id]

    def assign_group(self, test_id: str) -> str:
        """Randomly assign a trade to control or variant (50/50)."""
        return 'variant' if random.random() < 0.5 else 'control'

    def record_outcome(self, test_id: str, group: str, trade: dict):
        """Record a trade outcome for an A/B test group."""
        data = self._load()
        test = data.get('tests', {}).get(test_id)
        if not test or test['status'] != 'active':
            return

        pnl = trade.get('pnl_dollars', 0) or 0
        grp = test[group]
        grp['trades'].append({
            'trade_id': trade.get('id'),
            'pnl': pnl,
            'ts': datetime.utcnow().isoformat(),
        })
        if pnl > 0:
            grp['wins'] += 1
        else:
            grp['losses'] += 1
        grp['total_pnl'] += pnl

        # Check if test is complete
        n_control = len(test['control']['trades'])
        n_variant = len(test['variant']['trades'])
        if n_control >= test['min_trades'] and n_variant >= test['min_trades']:
            test['status'] = 'complete'
            test['completed_at'] = datetime.utcnow().isoformat()
            test['result'] = self._evaluate_test(test)
            data['completed'].append(test_id)

        self._save(data)

    def _evaluate_test(self, test: Dict) -> Dict:
        """Evaluate A/B test results with basic statistical comparison."""
        c = test['control']
        v = test['variant']

        c_n = len(c['trades'])
        v_n = len(v['trades'])
        c_wr = c['wins'] / max(c_n, 1) * 100
        v_wr = v['wins'] / max(v_n, 1) * 100
        c_avg_pnl = c['total_pnl'] / max(c_n, 1)
        v_avg_pnl = v['total_pnl'] / max(v_n, 1)

        # Simple z-test for proportions
        pooled_wr = (c['wins'] + v['wins']) / max(c_n + v_n, 1)
        se = math.sqrt(max(0.001, pooled_wr * (1 - pooled_wr) * (1 / max(c_n, 1) + 1 / max(v_n, 1))))
        z_score = (v_wr / 100 - c_wr / 100) / se if se > 0 else 0

        # Winner determination
        if abs(z_score) >= 1.96:
            winner = 'variant' if z_score > 0 else 'control'
            significant = True
        else:
            winner = 'inconclusive'
            significant = False

        return {
            'control_win_rate': round(c_wr, 1),
            'variant_win_rate': round(v_wr, 1),
            'control_avg_pnl': round(c_avg_pnl, 2),
            'variant_avg_pnl': round(v_avg_pnl, 2),
            'z_score': round(z_score, 3),
            'significant': significant,
            'winner': winner,
            'recommendation': (
                f'Adopt {winner} ({v.get("name", "variant") if winner == "variant" else c.get("name", "control")})'
                if significant else 'Need more data or no significant difference'
            ),
        }

    def get_active_tests(self) -> List[Dict]:
        data = self._load()
        return [t for t in data.get('tests', {}).values() if t['status'] == 'active']

    def get_all_tests(self) -> Dict:
        return self._load()


# =============================================================================
# Helpers
# =============================================================================

def _calc_exit_dte(trade: dict) -> Optional[int]:
    """Calculate DTE at time of exit."""
    if not trade.get('expiration') or not trade.get('exit_time'):
        return None
    try:
        exp = datetime.strptime(trade['expiration'], '%Y-%m-%d').date()
        exit_d = datetime.fromisoformat(trade['exit_time'].replace('Z', '+00:00')).date()
        return (exp - exit_d).days
    except Exception:
        return None
