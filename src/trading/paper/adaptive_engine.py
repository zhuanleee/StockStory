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
        **kwargs,
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

        # Risk reversal signal: put_25d_iv - call_25d_iv
        risk_rev = kwargs.get('risk_reversal', 0) or 0
        risk_rev_adj = 0
        if risk_rev > 0.03 and strategy_type == 'short_premium':
            risk_rev_adj = 4  # Puts overpriced relative to calls — edge for selling puts
        elif risk_rev < -0.02 and strategy_type == 'long_premium':
            risk_rev_adj = 3  # Calls cheap — edge for buying calls
        edge += risk_rev_adj

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
            risk_rev_adj > 0,
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
                'risk_reversal_adj': risk_rev_adj,
                'term_structure': term_structure,
                'skew_ratio': round(skew_ratio, 3),
                'risk_reversal': round(risk_rev, 4) if risk_rev else 0,
            },
        }


# =============================================================================
# PHASE 3b: Strategy Auto-Selector
# =============================================================================

class StrategySelector:
    """
    Selects optimal strategy based on current regime + VRP + GEX + term structure.
    """

    # risk_profile: 'limited' = defined max loss (spreads, long options)
    #               'unlimited' = theoretically unlimited loss (ratio, naked, short straddles)
    STRATEGY_MATRIX = [
        {
            'name': 'Credit Spread (Premium Harvest)',
            'conditions': lambda r: (
                r['vrp'] > 4 and
                r['gex_regime'] == 'pinned' and
                r['flow_toxicity'] < 0.5
            ) or (
                r['vrp'] > 3 and
                r['gex_regime'] == 'pinned' and
                r.get('risk_reversal', 0) > 0.02
            ),
            'type': 'short_premium',
            'risk_profile': 'limited',
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
            ) or (
                r['vrp'] < 2 and
                r['gex_regime'] == 'volatile' and
                r.get('risk_reversal', 0) < -0.01
            ),
            'type': 'long_premium',
            'risk_profile': 'limited',
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
            'risk_profile': 'unlimited',
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
            'risk_profile': 'limited',
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
            'risk_profile': 'limited',
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
            'risk_profile': 'limited',
            'direction': 'neutral',
            'dte_range': [30, 45],
            'delta_target': 0.16,
            'description': 'Pinned regime + mild VRP + quiet flow. Sell wings.',
        },
        {
            'name': 'Straddle (Event Vol)',
            'conditions': lambda r: (
                r.get('macro_event_days', 99) <= 3
                and r.get('iv_rank', 50) < 50
            ),
            'type': 'long_premium',
            'risk_profile': 'limited',
            'direction': 'neutral',
            'dte_range': [7, 21],
            'delta_target': 0.50,
            'description': 'Major macro event imminent + IV not yet expanded. Buy vol.',
        },
        {
            'name': 'Melt-Up Debit Spread',
            'conditions': lambda r: r['combined_regime'] == 'melt_up',
            'type': 'long_premium',
            'risk_profile': 'limited',
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
            'risk_profile': 'limited',
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
            'risk_profile': 'limited',
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
            'risk_profile': 'limited',
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
            'risk_profile': 'limited',
            'direction': 'neutral_bullish',
            'dte_range': [21, 35],
            'delta_target': 0.18,
            'description': 'Backwardation = elevated front IV. Sell rich front-month premium.',
        },
        {
            'name': 'Cash-Secured Put',
            'conditions': lambda r: (
                r['vrp'] > 0 and
                r['combined_regime'] not in ('danger', 'high_risk') and
                r['flow_toxicity'] < 0.7
            ),
            'type': 'short_premium',
            'risk_profile': 'unlimited',
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
            'risk_profile': 'limited',
            'direction': 'bullish',
            'dte_range': [30, 60],
            'delta_target': 0.40,
            'description': 'IV below realized — options are cheap. Buy calls for directional exposure.',
        },
    ]

    def select_strategy(self, regime_state: Dict, risk_mode: str = 'all') -> List[Dict]:
        """
        Returns ranked list of suitable strategies for current conditions.

        Args:
            regime_state: dict with vrp, gex_regime, combined_regime, flow_toxicity,
                         term_structure, skew_steep, vanna_flow, macro_event_days
            risk_mode: 'limited' (defined risk only), 'unlimited' (all), or 'all' (default)
        """
        results = []
        for strat in self.STRATEGY_MATRIX:
            try:
                # Filter by risk_mode
                if risk_mode == 'limited' and strat.get('risk_profile') == 'unlimited':
                    continue

                if strat['conditions'](regime_state):
                    results.append({
                        'name': strat['name'],
                        'type': strat['type'],
                        'risk_profile': strat.get('risk_profile', 'limited'),
                        'direction': strat['direction'],
                        'dte_range': strat['dte_range'],
                        'delta_target': strat['delta_target'],
                        'description': strat['description'],
                    })
            except Exception:
                continue

        if not results:
            results.append({
                'name': 'Wait / Reduce Size',
                'type': 'none',
                'risk_profile': 'limited',
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


# =============================================================================
# ENHANCEMENT 1: Regime-Aware Weight Adaptation
# =============================================================================

class RegimeAwareWeights:
    """
    Extends Thompson Sampling to learn SEPARATE factor weights per regime.

    Each regime (opportunity, danger, pinned, volatile, etc.) maintains its own
    Beta(alpha, beta) distributions per factor. This allows the system to learn
    that e.g. 'squeeze' matters in volatile regimes but not pinned.

    Falls back to global weights when regime-specific sample size < min_samples.
    """

    def __init__(self, volume_path: str):
        self.regime_file = Path(volume_path) / "paper_trading" / "regime_aware_weights.json"
        self._cache = None

    def _load(self) -> Dict:
        if self._cache:
            return self._cache
        if self.regime_file.exists():
            try:
                self._cache = json.loads(self.regime_file.read_text())
                return self._cache
            except Exception:
                pass
        self._cache = {
            'regimes': {},  # regime -> {factors: {name: {alpha, beta, wins_high, losses_high}}, total_updates}
            'global': {     # fallback global distribution
                'factors': {},
                'total_updates': 0,
            },
            'last_updated': None,
        }
        return self._cache

    def _save(self, data: Dict):
        self.regime_file.parent.mkdir(parents=True, exist_ok=True)
        data['last_updated'] = datetime.utcnow().isoformat()
        self.regime_file.write_text(json.dumps(data, indent=2))
        self._cache = data

    def _ensure_factor(self, factors: dict, name: str, default_weight: float = 12.5):
        if name not in factors:
            factors[name] = {
                'alpha': 2.0 + default_weight / 10,
                'beta': 2.0,
                'wins_high': 0, 'losses_high': 0,
                'wins_low': 0, 'losses_low': 0,
            }

    def update(self, regime: str, factor_scores: dict, is_win: bool):
        """Update regime-specific AND global distributions."""
        data = self._load()

        for target_key in [regime, '__global__']:
            if target_key == '__global__':
                bucket = data['global']
            else:
                if target_key not in data['regimes']:
                    data['regimes'][target_key] = {'factors': {}, 'total_updates': 0}
                bucket = data['regimes'][target_key]

            for name, score in factor_scores.items():
                self._ensure_factor(bucket['factors'], name)
                f = bucket['factors'][name]
                is_high = score >= 60

                if is_high:
                    if is_win:
                        f['alpha'] += 1.0
                        f['wins_high'] += 1
                    else:
                        f['beta'] += 1.0
                        f['losses_high'] += 1
                else:
                    if is_win:
                        f['beta'] += 0.3
                        f['wins_low'] += 1
                    else:
                        f['alpha'] += 0.3
                        f['losses_low'] += 1

            bucket['total_updates'] = bucket.get('total_updates', 0) + 1

        self._save(data)

    def get_weights(self, regime: str = None, min_samples: int = 10) -> Dict[str, float]:
        """Get weights for a specific regime, falling back to global if sparse."""
        data = self._load()
        DEFAULT = AdaptiveWeights.DEFAULT_WEIGHTS

        # Determine which bucket to sample from
        bucket = None
        if regime and regime in data.get('regimes', {}):
            rb = data['regimes'][regime]
            if rb.get('total_updates', 0) >= min_samples:
                bucket = rb

        if not bucket:
            bucket = data.get('global', {})
            if bucket.get('total_updates', 0) < 10:
                return dict(DEFAULT)

        # Thompson Sampling from the selected bucket
        sampled = {}
        for name in DEFAULT:
            f = bucket.get('factors', {}).get(name)
            if f:
                alpha = max(1.0, f.get('alpha', 2.0))
                beta_v = max(1.0, f.get('beta', 2.0))
                sampled[name] = random.betavariate(alpha, beta_v)
            else:
                sampled[name] = DEFAULT.get(name, 10) / 100

        total = sum(sampled.values())
        if total <= 0:
            return dict(DEFAULT)
        return {n: round(v / total * 100, 1) for n, v in sampled.items()}

    def get_stats(self) -> Dict:
        data = self._load()
        stats = {'global_updates': data.get('global', {}).get('total_updates', 0)}
        for regime, bucket in data.get('regimes', {}).items():
            stats[regime] = {
                'updates': bucket.get('total_updates', 0),
                'status': 'warm' if bucket.get('total_updates', 0) >= 20
                          else 'learning' if bucket.get('total_updates', 0) >= 5 else 'cold',
            }
        return stats


# =============================================================================
# ENHANCEMENT 2: Ticker Cluster Transfer Learning
# =============================================================================

class TickerClusterLearner:
    """
    Groups tickers by correlation tier and transfers learning across similar tickers.

    When NVDA has only 2 trades but we have 15 trades across the 'large_cap' cluster,
    we blend NVDA-specific stats with cluster-level stats using Bayesian shrinkage.

    Clusters match CORRELATION_TIERS from risk_manager.py.
    """

    CLUSTERS = {
        'large_cap': ['SPY', 'QQQ', 'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META'],
        'high_vol': ['TSLA', 'AMD', 'COIN'],
        'sector': ['XLE', 'XLF', 'XBI'],
        'defensive': ['TLT', 'XLU'],
        'alternatives': ['GLD', 'SLV', 'IBIT'],
    }

    # Reverse lookup: ticker -> cluster
    TICKER_TO_CLUSTER = {}
    for _cluster, _tickers in CLUSTERS.items():
        for _t in _tickers:
            TICKER_TO_CLUSTER[_t] = _cluster

    def __init__(self, volume_path: str):
        self.cluster_file = Path(volume_path) / "paper_trading" / "ticker_clusters.json"
        self._cache = None

    def _load(self) -> Dict:
        if self._cache:
            return self._cache
        if self.cluster_file.exists():
            try:
                self._cache = json.loads(self.cluster_file.read_text())
                return self._cache
            except Exception:
                pass
        self._cache = {
            'tickers': {},   # ticker -> {wins, losses, total_pnl, strategies: {name: {wins, losses}}}
            'clusters': {},  # cluster -> same aggregate
            'last_updated': None,
        }
        return self._cache

    def _save(self, data: Dict):
        self.cluster_file.parent.mkdir(parents=True, exist_ok=True)
        data['last_updated'] = datetime.utcnow().isoformat()
        self.cluster_file.write_text(json.dumps(data, indent=2))
        self._cache = data

    def update_from_trades(self, closed_trades: List[dict]):
        """Rebuild ticker and cluster stats from all closed trades."""
        data = {'tickers': {}, 'clusters': {}, 'last_updated': None}

        for t in closed_trades:
            ticker = t.get('ticker', 'UNKNOWN').upper()
            pnl = t.get('pnl_dollars', 0) or 0
            is_win = pnl > 0
            strategy = t.get('strategy', 'unknown')
            signal_type = t.get('signal_type', 'unknown')
            cluster = self.TICKER_TO_CLUSTER.get(ticker, 'other')

            for key, name in [('tickers', ticker), ('clusters', cluster)]:
                if name not in data[key]:
                    data[key][name] = {
                        'wins': 0, 'losses': 0, 'total': 0, 'total_pnl': 0,
                        'strategies': {}, 'signal_types': {},
                    }
                rec = data[key][name]
                rec['total'] += 1
                rec['total_pnl'] += pnl
                if is_win:
                    rec['wins'] += 1
                else:
                    rec['losses'] += 1

                # Strategy breakdown
                if strategy not in rec['strategies']:
                    rec['strategies'][strategy] = {'wins': 0, 'losses': 0, 'total': 0}
                sr = rec['strategies'][strategy]
                sr['total'] += 1
                if is_win:
                    sr['wins'] += 1
                else:
                    sr['losses'] += 1

                # Signal type breakdown
                if signal_type not in rec['signal_types']:
                    rec['signal_types'][signal_type] = {'wins': 0, 'losses': 0, 'total': 0}
                st = rec['signal_types'][signal_type]
                st['total'] += 1
                if is_win:
                    st['wins'] += 1
                else:
                    st['losses'] += 1

        self._save(data)
        return data

    def get_blended_win_rate(self, ticker: str, strategy: str = None,
                             min_ticker_samples: int = 5) -> Dict:
        """
        Get win rate blended between ticker-specific and cluster-level stats.

        Uses Bayesian shrinkage: weight = n_ticker / (n_ticker + shrinkage_factor)
        When ticker has few trades, leans heavily on cluster stats.
        """
        data = self._load()
        ticker = ticker.upper()
        cluster = self.TICKER_TO_CLUSTER.get(ticker, 'other')
        SHRINKAGE = 10  # Higher = more cluster influence

        # Get ticker-level stats
        ticker_rec = data.get('tickers', {}).get(ticker, {})
        if strategy and ticker_rec:
            ticker_rec = ticker_rec.get('strategies', {}).get(strategy, ticker_rec)

        # Get cluster-level stats
        cluster_rec = data.get('clusters', {}).get(cluster, {})
        if strategy and cluster_rec:
            cluster_rec = cluster_rec.get('strategies', {}).get(strategy, cluster_rec)

        n_ticker = ticker_rec.get('total', 0) if ticker_rec else 0
        n_cluster = cluster_rec.get('total', 0) if cluster_rec else 0

        ticker_wr = (ticker_rec.get('wins', 0) / n_ticker * 100) if n_ticker > 0 else 50
        cluster_wr = (cluster_rec.get('wins', 0) / n_cluster * 100) if n_cluster > 0 else 50

        # Bayesian shrinkage: blend = w * ticker_wr + (1-w) * cluster_wr
        w = n_ticker / (n_ticker + SHRINKAGE)
        blended_wr = w * ticker_wr + (1 - w) * cluster_wr

        return {
            'ticker': ticker,
            'cluster': cluster,
            'ticker_win_rate': round(ticker_wr, 1),
            'cluster_win_rate': round(cluster_wr, 1),
            'blended_win_rate': round(blended_wr, 1),
            'ticker_trades': n_ticker,
            'cluster_trades': n_cluster,
            'shrinkage_weight': round(w, 3),
            'confidence': 'high' if n_ticker >= min_ticker_samples else
                         'medium' if n_cluster >= 10 else 'low',
        }

    def get_best_strategy_for_ticker(self, ticker: str) -> Optional[str]:
        """Return the strategy with highest blended win rate for this ticker."""
        data = self._load()
        ticker = ticker.upper()
        cluster = self.TICKER_TO_CLUSTER.get(ticker, 'other')

        # Collect all strategies seen for this ticker's cluster
        all_strategies = set()
        cluster_rec = data.get('clusters', {}).get(cluster, {})
        all_strategies.update(cluster_rec.get('strategies', {}).keys())
        ticker_rec = data.get('tickers', {}).get(ticker, {})
        all_strategies.update(ticker_rec.get('strategies', {}).keys())

        best_strategy = None
        best_wr = 0
        for strat in all_strategies:
            info = self.get_blended_win_rate(ticker, strategy=strat)
            if info['blended_win_rate'] > best_wr and (info['ticker_trades'] + info['cluster_trades']) >= 3:
                best_wr = info['blended_win_rate']
                best_strategy = strat

        return best_strategy

    def get_stats(self) -> Dict:
        data = self._load()
        return {
            'tickers_tracked': len(data.get('tickers', {})),
            'clusters_tracked': len(data.get('clusters', {})),
            'cluster_summary': {
                cluster: {
                    'total': rec.get('total', 0),
                    'win_rate': round(rec.get('wins', 0) / max(rec.get('total', 1), 1) * 100, 1),
                }
                for cluster, rec in data.get('clusters', {}).items()
            },
        }


# =============================================================================
# ENHANCEMENT 3: Regime Transition Predictor (Markov Chain)
# =============================================================================

class RegimeTransitionPredictor:
    """
    Learns regime transition probabilities from observed data using a Markov chain.

    Tracks actual regime transitions and builds a transition matrix:
      P(next_regime | current_regime)

    Uses Laplace smoothing to handle unseen transitions.
    Predicts most likely next regime + probability.
    """

    ALL_REGIMES = [
        'opportunity', 'melt_up', 'neutral_pinned', 'neutral_transitional',
        'neutral_volatile', 'high_risk', 'danger',
    ]

    def __init__(self, volume_path: str):
        self.transition_file = Path(volume_path) / "paper_trading" / "regime_transitions.json"
        self._cache = None

    def _load(self) -> Dict:
        if self._cache:
            return self._cache
        if self.transition_file.exists():
            try:
                self._cache = json.loads(self.transition_file.read_text())
                return self._cache
            except Exception:
                pass
        self._cache = {
            'transitions': {},     # {from_regime: {to_regime: count}}
            'dwell_times': {},     # {regime: [durations_in_hours]}
            'regime_history': [],  # [{regime, timestamp}] — last 500 observations
            'total_observations': 0,
            'last_updated': None,
        }
        return self._cache

    def _save(self, data: Dict):
        self.transition_file.parent.mkdir(parents=True, exist_ok=True)
        data['last_updated'] = datetime.utcnow().isoformat()
        self.transition_file.write_text(json.dumps(data, indent=2))
        self._cache = data

    def observe(self, current_regime: str, timestamp: str = None):
        """Record a regime observation. Detects transitions automatically."""
        data = self._load()
        ts = timestamp or datetime.utcnow().isoformat()

        history = data['regime_history']
        if history and history[-1]['regime'] != current_regime:
            # Transition detected
            prev_regime = history[-1]['regime']
            if prev_regime not in data['transitions']:
                data['transitions'][prev_regime] = {}
            trans = data['transitions'][prev_regime]
            trans[current_regime] = trans.get(current_regime, 0) + 1

            # Dwell time calculation
            try:
                prev_ts = datetime.fromisoformat(history[-1]['timestamp'].replace('Z', '+00:00'))
                curr_ts = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                dwell_hours = (curr_ts - prev_ts).total_seconds() / 3600
                if prev_regime not in data['dwell_times']:
                    data['dwell_times'][prev_regime] = []
                data['dwell_times'][prev_regime].append(round(dwell_hours, 1))
                # Keep last 50 dwell times per regime
                data['dwell_times'][prev_regime] = data['dwell_times'][prev_regime][-50:]
            except Exception:
                pass

        history.append({'regime': current_regime, 'timestamp': ts})
        data['regime_history'] = history[-500:]  # Keep last 500
        data['total_observations'] = data.get('total_observations', 0) + 1

        self._save(data)

    def predict(self, current_regime: str) -> Dict:
        """
        Predict next regime transition using learned Markov chain.

        Returns: {
            predictions: [{regime, probability}...],
            expected_dwell_hours,
            transition_imminent (bool),
            confidence
        }
        """
        data = self._load()
        LAPLACE = 0.5  # Smoothing constant

        trans = data.get('transitions', {}).get(current_regime, {})
        total_trans = sum(trans.values())

        n_regimes = len(self.ALL_REGIMES)
        predictions = []
        for regime in self.ALL_REGIMES:
            count = trans.get(regime, 0)
            # Laplace-smoothed probability
            prob = (count + LAPLACE) / (total_trans + LAPLACE * n_regimes)
            predictions.append({'regime': regime, 'probability': round(prob, 3), 'count': count})

        predictions.sort(key=lambda x: x['probability'], reverse=True)

        # Expected dwell time
        dwell_times = data.get('dwell_times', {}).get(current_regime, [])
        avg_dwell = sum(dwell_times) / len(dwell_times) if dwell_times else 24.0

        # Check if we've been in this regime longer than average
        history = data.get('regime_history', [])
        current_dwell = 0
        if history:
            try:
                last_ts = datetime.fromisoformat(history[-1]['timestamp'].replace('Z', '+00:00'))
                # Walk backwards to find when this regime started
                for i in range(len(history) - 2, -1, -1):
                    if history[i]['regime'] != current_regime:
                        start_ts = datetime.fromisoformat(history[i + 1]['timestamp'].replace('Z', '+00:00'))
                        current_dwell = (last_ts - start_ts).total_seconds() / 3600
                        break
            except Exception:
                pass

        transition_imminent = current_dwell > avg_dwell * 1.2 if avg_dwell > 0 else False

        return {
            'current_regime': current_regime,
            'predictions': predictions[:5],  # Top 5 most likely next regimes
            'most_likely_next': predictions[0]['regime'] if predictions else current_regime,
            'most_likely_probability': predictions[0]['probability'] if predictions else 0,
            'expected_dwell_hours': round(avg_dwell, 1),
            'current_dwell_hours': round(current_dwell, 1),
            'transition_imminent': transition_imminent,
            'total_transitions_observed': total_trans,
            'confidence': 'high' if total_trans >= 30 else 'medium' if total_trans >= 10 else 'low',
        }

    def get_transition_matrix(self) -> Dict:
        """Return full transition probability matrix for dashboard display."""
        data = self._load()
        LAPLACE = 0.5
        n_regimes = len(self.ALL_REGIMES)
        matrix = {}

        for from_regime in self.ALL_REGIMES:
            trans = data.get('transitions', {}).get(from_regime, {})
            total = sum(trans.values())
            row = {}
            for to_regime in self.ALL_REGIMES:
                count = trans.get(to_regime, 0)
                prob = (count + LAPLACE) / (total + LAPLACE * n_regimes) if total > 0 else 1.0 / n_regimes
                row[to_regime] = round(prob, 3)
            matrix[from_regime] = row

        return matrix

    def get_stats(self) -> Dict:
        data = self._load()
        return {
            'total_observations': data.get('total_observations', 0),
            'total_transitions': sum(
                sum(v.values()) for v in data.get('transitions', {}).values()
            ),
            'regimes_seen': list(data.get('transitions', {}).keys()),
            'avg_dwell_hours': {
                regime: round(sum(times) / len(times), 1) if times else 0
                for regime, times in data.get('dwell_times', {}).items()
            },
        }


# =============================================================================
# ENHANCEMENT 4: Parameter Auto-Tuner
# =============================================================================

class ParameterAutoTuner:
    """
    Learns optimal signal thresholds from trade outcome data instead of hard-coding.

    Tracks which parameter values (IV thresholds, VRP cutoffs, wall proximity, etc.)
    led to winning vs losing trades. Uses percentile analysis to find optimal ranges.

    Parameters tuned:
    - iv_reversion_high: IV Rank threshold for 'sell IV' signal (default 70)
    - iv_reversion_low: IV Rank threshold for 'buy IV' signal (default 30)
    - vrp_min: Minimum VRP for short premium strategies (default 1.5)
    - wall_proximity_pct: GEX wall proximity threshold (default 1.0%)
    - flow_toxicity_high: Threshold for 'informed flow' signal (default 0.7)
    - min_confidence: Minimum signal confidence to act (default 60)
    """

    TUNABLE_PARAMS = {
        'iv_reversion_high': {'default': 70, 'min': 60, 'max': 90, 'step': 5},
        'iv_reversion_low': {'default': 30, 'min': 10, 'max': 40, 'step': 5},
        'vrp_min_short_premium': {'default': 1.5, 'min': 0.5, 'max': 5.0, 'step': 0.5},
        'wall_proximity_pct': {'default': 1.0, 'min': 0.3, 'max': 2.0, 'step': 0.1},
        'flow_toxicity_high': {'default': 0.7, 'min': 0.4, 'max': 0.9, 'step': 0.05},
        'min_confidence': {'default': 60, 'min': 40, 'max': 80, 'step': 5},
    }

    def __init__(self, volume_path: str):
        self.tuner_file = Path(volume_path) / "paper_trading" / "param_auto_tuner.json"
        self._cache = None

    def _load(self) -> Dict:
        if self._cache:
            return self._cache
        if self.tuner_file.exists():
            try:
                self._cache = json.loads(self.tuner_file.read_text())
                return self._cache
            except Exception:
                pass
        self._cache = {
            'observations': {},  # param_name -> [{value, outcome (win/loss), pnl}]
            'learned_params': {},  # param_name -> {optimal_value, confidence}
            'total_updates': 0,
            'last_updated': None,
        }
        return self._cache

    def _save(self, data: Dict):
        self.tuner_file.parent.mkdir(parents=True, exist_ok=True)
        data['last_updated'] = datetime.utcnow().isoformat()
        self.tuner_file.write_text(json.dumps(data, indent=2))
        self._cache = data

    def record_observation(self, param_name: str, param_value: float,
                           is_win: bool, pnl: float = 0):
        """Record what parameter value was used and whether the trade won."""
        if param_name not in self.TUNABLE_PARAMS:
            return
        data = self._load()
        if param_name not in data['observations']:
            data['observations'][param_name] = []
        data['observations'][param_name].append({
            'value': param_value,
            'win': is_win,
            'pnl': round(pnl, 2),
            'ts': datetime.utcnow().isoformat(),
        })
        # Keep last 200 observations per param
        data['observations'][param_name] = data['observations'][param_name][-200:]
        data['total_updates'] = data.get('total_updates', 0) + 1
        self._save(data)

    def learn_from_trades(self, closed_trades: List[dict]):
        """Extract parameter observations from closed trades."""
        data = self._load()

        for t in closed_trades:
            pnl = t.get('pnl_dollars', 0) or 0
            is_win = pnl > 0
            signal_data = t.get('signal_data', {})

            # Extract parameter values that were in effect at entry
            iv_rank = signal_data.get('iv_rank')
            if iv_rank is not None:
                direction = signal_data.get('direction', t.get('direction', ''))
                if direction == 'short' or 'credit' in t.get('strategy', '').lower():
                    self.record_observation('iv_reversion_high', iv_rank, is_win, pnl)
                elif direction == 'long':
                    self.record_observation('iv_reversion_low', iv_rank, is_win, pnl)

            vrp = signal_data.get('vrp')
            if vrp is not None and 'credit' in t.get('strategy', '').lower():
                self.record_observation('vrp_min_short_premium', vrp, is_win, pnl)

            toxicity = signal_data.get('flow_toxicity')
            if toxicity is not None:
                self.record_observation('flow_toxicity_high', toxicity, is_win, pnl)

            confidence = signal_data.get('confidence') or t.get('signal_confidence')
            if confidence is not None:
                self.record_observation('min_confidence', confidence, is_win, pnl)

        # Recompute optimal values
        self._optimize_params(data)
        self._save(data)

    def _optimize_params(self, data: Dict):
        """Find optimal parameter values by maximizing win rate at each value."""
        for param_name, spec in self.TUNABLE_PARAMS.items():
            obs = data.get('observations', {}).get(param_name, [])
            if len(obs) < 10:
                continue

            # Bin observations by parameter value and compute win rate per bin
            step = spec['step']
            bins = defaultdict(lambda: {'wins': 0, 'losses': 0, 'total': 0, 'pnl': 0})
            for o in obs:
                # Round to nearest step
                binned = round(o['value'] / step) * step
                binned = max(spec['min'], min(spec['max'], binned))
                b = bins[binned]
                b['total'] += 1
                b['pnl'] += o.get('pnl', 0)
                if o['win']:
                    b['wins'] += 1
                else:
                    b['losses'] += 1

            # Find bin with best risk-adjusted performance (win_rate * avg_pnl)
            best_val = spec['default']
            best_score = -999
            for val, b in bins.items():
                if b['total'] < 3:
                    continue
                wr = b['wins'] / b['total']
                avg_pnl = b['pnl'] / b['total']
                score = wr * 0.6 + (avg_pnl / max(abs(avg_pnl), 1)) * 0.4
                if score > best_score:
                    best_score = score
                    best_val = val

            n_total = sum(b['total'] for b in bins.values())
            data['learned_params'][param_name] = {
                'optimal_value': best_val,
                'default_value': spec['default'],
                'changed': abs(best_val - spec['default']) > spec['step'] * 0.5,
                'sample_size': n_total,
                'confidence': 'high' if n_total >= 30 else 'medium' if n_total >= 15 else 'low',
                'score': round(best_score, 3),
            }

    def get_param(self, param_name: str, min_confidence: str = 'medium') -> float:
        """Get learned parameter value, falling back to default if not confident."""
        data = self._load()
        learned = data.get('learned_params', {}).get(param_name)
        spec = self.TUNABLE_PARAMS.get(param_name, {})

        if not learned:
            return spec.get('default', 0)

        confidence_rank = {'low': 0, 'medium': 1, 'high': 2}
        if confidence_rank.get(learned.get('confidence', 'low'), 0) >= confidence_rank.get(min_confidence, 1):
            return learned['optimal_value']

        return spec.get('default', 0)

    def get_all_params(self) -> Dict:
        """Get all parameter values (learned or default)."""
        result = {}
        for name, spec in self.TUNABLE_PARAMS.items():
            learned = self.get_param(name)
            result[name] = {
                'value': learned,
                'default': spec['default'],
                'tuned': abs(learned - spec['default']) > spec['step'] * 0.5,
            }
        return result

    def get_stats(self) -> Dict:
        data = self._load()
        return {
            'total_observations': data.get('total_updates', 0),
            'params_learned': len(data.get('learned_params', {})),
            'params': data.get('learned_params', {}),
        }


# =============================================================================
# ENHANCEMENT 5: Reinforcement Learning Layer (Policy Gradient)
# =============================================================================

class ReinforcementLearner:
    """
    Lightweight policy gradient learner for entry/exit decision refinement.

    State: [regime_idx, vrp_norm, toxicity, iv_rank_norm, edge_score_norm, dwell_norm]
    Actions: [enter, skip, exit_now, hold]
    Policy: Linear softmax — lightweight enough for production without GPU.

    Uses REINFORCE algorithm with baseline subtraction.
    """

    ACTIONS = ['enter', 'skip', 'exit_now', 'hold']
    STATE_DIM = 6  # regime, vrp, toxicity, iv_rank, edge_score, dwell_ratio

    REGIME_IDX = {
        'opportunity': 0.0, 'melt_up': 0.15, 'neutral_pinned': 0.35,
        'neutral_transitional': 0.5, 'neutral_volatile': 0.65,
        'high_risk': 0.8, 'danger': 1.0,
    }

    def __init__(self, volume_path: str, learning_rate: float = 0.01):
        self.rl_file = Path(volume_path) / "paper_trading" / "rl_policy.json"
        self.lr = learning_rate
        self._cache = None

    def _load(self) -> Dict:
        if self._cache:
            return self._cache
        if self.rl_file.exists():
            try:
                self._cache = json.loads(self.rl_file.read_text())
                return self._cache
            except Exception:
                pass
        # Initialize weights: (n_actions x state_dim) matrix
        n_actions = len(self.ACTIONS)
        self._cache = {
            'weights': [[0.0] * self.STATE_DIM for _ in range(n_actions)],
            'bias': [0.0] * n_actions,
            'baseline_reward': 0.0,  # Running average reward for variance reduction
            'episodes': [],  # [{state, action_idx, reward}] — last 500
            'total_updates': 0,
            'cumulative_reward': 0.0,
            'last_updated': None,
        }
        # Initialize with prior: slight preference for 'enter' when edge is high
        self._cache['weights'][0][4] = 0.5  # enter weight on edge_score
        self._cache['weights'][1][4] = -0.3  # skip weight (negative on edge)
        self._cache['weights'][2][0] = 0.3   # exit_now weight on danger regime
        self._cache['weights'][3][4] = 0.2   # hold weight on edge_score
        return self._cache

    def _save(self, data: Dict):
        self.rl_file.parent.mkdir(parents=True, exist_ok=True)
        data['last_updated'] = datetime.utcnow().isoformat()
        self.rl_file.write_text(json.dumps(data, indent=2))
        self._cache = data

    def _encode_state(self, regime: str, vrp: float, toxicity: float,
                      iv_rank: float, edge_score: float, dwell_ratio: float) -> List[float]:
        """Encode market state into normalized feature vector."""
        return [
            self.REGIME_IDX.get(regime, 0.5),
            max(-1, min(1, vrp / 10)),           # VRP normalized to [-1, 1]
            max(0, min(1, toxicity)),             # Already 0-1
            max(0, min(1, iv_rank / 100)),        # Normalize to 0-1
            max(0, min(1, edge_score / 100)),     # Normalize to 0-1
            max(0, min(2, dwell_ratio)),           # >1 means past average dwell
        ]

    def _softmax(self, logits: List[float]) -> List[float]:
        """Compute softmax probabilities from logits."""
        max_l = max(logits)
        exp_l = [math.exp(l - max_l) for l in logits]
        total = sum(exp_l)
        return [e / total for e in exp_l]

    def _compute_logits(self, state: List[float], data: Dict) -> List[float]:
        """Compute action logits = W * state + bias."""
        weights = data['weights']
        bias = data['bias']
        logits = []
        for a in range(len(self.ACTIONS)):
            logit = bias[a]
            for i in range(self.STATE_DIM):
                logit += weights[a][i] * state[i]
            logits.append(logit)
        return logits

    def get_action_probs(self, regime: str, vrp: float, toxicity: float,
                         iv_rank: float, edge_score: float,
                         dwell_ratio: float = 0.5) -> Dict:
        """Get action probabilities for current state."""
        data = self._load()
        state = self._encode_state(regime, vrp, toxicity, iv_rank, edge_score, dwell_ratio)
        logits = self._compute_logits(state, data)
        probs = self._softmax(logits)

        return {
            'action_probs': {self.ACTIONS[i]: round(probs[i], 4) for i in range(len(self.ACTIONS))},
            'recommended_action': self.ACTIONS[probs.index(max(probs))],
            'confidence': round(max(probs), 3),
            'state': state,
            'total_episodes': data.get('total_updates', 0),
        }

    def record_episode(self, state_dict: Dict, action: str, reward: float):
        """
        Record an episode (state, action, reward) and update policy.

        reward: Normalized P&L (e.g., pnl_dollars / premium / 100)
                +1 for good entry that won, -1 for bad entry that lost,
                +0.5 for correct skip, -0.5 for missed opportunity.
        """
        data = self._load()
        action_idx = self.ACTIONS.index(action) if action in self.ACTIONS else 0

        state = self._encode_state(
            state_dict.get('regime', 'neutral_transitional'),
            state_dict.get('vrp', 0),
            state_dict.get('toxicity', 0),
            state_dict.get('iv_rank', 50),
            state_dict.get('edge_score', 50),
            state_dict.get('dwell_ratio', 0.5),
        )

        # Store episode
        data['episodes'].append({
            'state': state, 'action_idx': action_idx,
            'reward': round(reward, 4),
            'ts': datetime.utcnow().isoformat(),
        })
        data['episodes'] = data['episodes'][-500:]

        # REINFORCE update with baseline subtraction
        baseline = data.get('baseline_reward', 0)
        advantage = reward - baseline

        # Update baseline (exponential moving average)
        data['baseline_reward'] = baseline * 0.95 + reward * 0.05

        # Policy gradient: Δw = lr * advantage * ∇log π(a|s)
        logits = self._compute_logits(state, data)
        probs = self._softmax(logits)

        for a in range(len(self.ACTIONS)):
            # Gradient of log softmax: 1(a=a_taken) - π(a|s)
            grad = (1.0 if a == action_idx else 0.0) - probs[a]
            for i in range(self.STATE_DIM):
                data['weights'][a][i] += self.lr * advantage * grad * state[i]
            data['bias'][a] += self.lr * advantage * grad

            # Weight clipping to prevent divergence
            for i in range(self.STATE_DIM):
                data['weights'][a][i] = max(-5.0, min(5.0, data['weights'][a][i]))
            data['bias'][a] = max(-3.0, min(3.0, data['bias'][a]))

        data['total_updates'] = data.get('total_updates', 0) + 1
        data['cumulative_reward'] = data.get('cumulative_reward', 0) + reward

        self._save(data)

    def get_stats(self) -> Dict:
        data = self._load()
        episodes = data.get('episodes', [])
        recent = episodes[-20:] if episodes else []
        recent_reward = sum(e.get('reward', 0) for e in recent) / max(len(recent), 1)

        return {
            'total_episodes': data.get('total_updates', 0),
            'cumulative_reward': round(data.get('cumulative_reward', 0), 2),
            'baseline_reward': round(data.get('baseline_reward', 0), 4),
            'recent_avg_reward': round(recent_reward, 4),
            'status': 'warm' if data.get('total_updates', 0) >= 50
                      else 'learning' if data.get('total_updates', 0) >= 10 else 'cold',
            'policy_weights_norm': round(sum(
                sum(abs(w) for w in row) for row in data.get('weights', [])
            ), 2),
        }
