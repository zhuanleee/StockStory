#!/usr/bin/env python3
"""
Tier 1: Bayesian Multi-Armed Bandit for Component Weight Optimization

Uses Thompson Sampling to learn optimal weights for trading components:
- Theme Score
- Technical Score
- AI Confidence
- X Sentiment

Each component is treated as an "arm" in a bandit problem.
The bandit learns which components predict profitable trades best.

Algorithm: Thompson Sampling with Beta distributions
- Fast convergence (10-20 trades)
- Naturally handles exploration vs exploitation
- Bayesian approach provides uncertainty quantification
"""

import logging
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json
from pathlib import Path

logger = logging.getLogger(__name__)

from .rl_models import (
    TradeRecord,
    TradeOutcome,
    ComponentWeights,
    MarketRegimeType,
    LearningDataEncoder
)


# =============================================================================
# BAYESIAN BANDIT IMPLEMENTATION
# =============================================================================

@dataclass
class BetaDistribution:
    """Beta distribution for modeling component performance."""
    alpha: float = 1.0  # Success count (starts at 1 for uninformative prior)
    beta: float = 1.0   # Failure count (starts at 1 for uninformative prior)

    def sample(self) -> float:
        """Draw a random sample from this Beta distribution."""
        return np.random.beta(self.alpha, self.beta)

    def mean(self) -> float:
        """Expected value of this distribution."""
        return self.alpha / (self.alpha + self.beta)

    def variance(self) -> float:
        """Variance of this distribution."""
        a, b = self.alpha, self.beta
        return (a * b) / ((a + b) ** 2 * (a + b + 1))

    def credible_interval(self, confidence=0.95) -> Tuple[float, float]:
        """Get credible interval (Bayesian confidence interval)."""
        from scipy import stats
        lower = (1 - confidence) / 2
        upper = 1 - lower
        return (
            stats.beta.ppf(lower, self.alpha, self.beta),
            stats.beta.ppf(upper, self.alpha, self.beta)
        )

    def update(self, success: bool):
        """Update distribution based on outcome."""
        if success:
            self.alpha += 1
        else:
            self.beta += 1


@dataclass
class ComponentArm:
    """One arm in the multi-armed bandit (one component)."""
    name: str
    distribution: BetaDistribution = field(default_factory=BetaDistribution)

    # Statistics
    total_pulls: int = 0
    total_wins: int = 0
    total_losses: int = 0

    # Recent performance
    recent_pnl: List[float] = field(default_factory=list)
    max_recent_samples: int = 50

    def pull(self) -> float:
        """Pull this arm (sample from its distribution)."""
        self.total_pulls += 1
        return self.distribution.sample()

    def update(self, trade_won: bool, pnl_pct: float):
        """Update this arm based on trade outcome."""
        self.distribution.update(trade_won)

        if trade_won:
            self.total_wins += 1
        else:
            self.total_losses += 1

        # Track recent P&L
        self.recent_pnl.append(pnl_pct)
        if len(self.recent_pnl) > self.max_recent_samples:
            self.recent_pnl.pop(0)

    def get_stats(self) -> dict:
        """Get statistics for this arm."""
        mean = self.distribution.mean()
        ci_lower, ci_upper = self.distribution.credible_interval()

        avg_pnl = np.mean(self.recent_pnl) if self.recent_pnl else 0.0

        return {
            'name': self.name,
            'mean_win_prob': mean,
            'credible_interval': (ci_lower, ci_upper),
            'total_pulls': self.total_pulls,
            'win_rate': self.total_wins / self.total_pulls if self.total_pulls > 0 else 0.0,
            'avg_pnl': avg_pnl,
            'uncertainty': self.distribution.variance()
        }


class BayesianBandit:
    """
    Bayesian Multi-Armed Bandit for learning optimal component weights.

    Uses Thompson Sampling to balance exploration and exploitation.
    Each component (Theme, Technical, AI, Sentiment) is an arm.
    """

    def __init__(self, storage_dir: Optional[Path] = None):
        """Initialize the bandit."""
        self.storage_dir = storage_dir or Path('user_data/learning')
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # Initialize arms for each component (5 components including earnings)
        self.arms = {
            'theme': ComponentArm('theme'),
            'technical': ComponentArm('technical'),
            'ai': ComponentArm('ai'),
            'sentiment': ComponentArm('sentiment'),
            'earnings': ComponentArm('earnings')
        }

        # Regime-specific bandits
        self.regime_bandits: Dict[MarketRegimeType, Dict[str, ComponentArm]] = {}

        # Learning history
        self.weight_history: List[Dict] = []

        # Load existing state if available
        self.load_state()

    # =========================================================================
    # CORE THOMPSON SAMPLING
    # =========================================================================

    def select_weights(self, regime: Optional[MarketRegimeType] = None) -> ComponentWeights:
        """
        Select component weights using Thompson Sampling.

        For each component, sample from its Beta distribution.
        Normalize samples to get weights that sum to 1.0.
        """
        # Use regime-specific bandit if available
        if regime and regime in self.regime_bandits:
            arms = self.regime_bandits[regime]
        else:
            arms = self.arms

        # Thompson Sampling: sample from each arm
        samples = {
            name: arm.pull()
            for name, arm in arms.items()
        }

        # Normalize to get weights
        total = sum(samples.values())
        if total == 0:
            total = 1.0  # Avoid division by zero

        weights = ComponentWeights(
            theme=samples['theme'] / total,
            technical=samples['technical'] / total,
            ai=samples['ai'] / total,
            sentiment=samples['sentiment'] / total,
            earnings=samples['earnings'] / total,
            sample_size=arms['theme'].total_pulls,
            last_updated=datetime.now(),
            regime=regime
        )

        # Calculate confidence based on total samples
        min_samples = min(arm.total_pulls for arm in arms.values())
        weights.confidence = min(1.0, min_samples / 50)  # Full confidence after 50 trades

        return weights

    def update_from_trade(self, trade: TradeRecord):
        """
        Update the bandit based on a completed trade.

        Determines which components contributed to success/failure
        and updates their distributions accordingly.
        """
        if trade.outcome == TradeOutcome.OPEN:
            return  # Don't learn from open trades

        # Determine if trade was successful
        trade_won = trade.outcome == TradeOutcome.WIN
        pnl_pct = trade.pnl_pct or 0.0

        # Get component scores from the trade
        scores = trade.component_scores

        # Attribute responsibility: which components were "correct"?
        # A component is "correct" if it was high when trade won, or low when trade lost
        component_values = {
            'theme': scores.theme_score,
            'technical': scores.technical_score,
            'ai': scores.ai_confidence * 10,  # Scale to 0-10
            'sentiment': (scores.x_sentiment_score + 1) * 5 if scores.x_sentiment_score else 5,  # Scale -1 to 1 -> 0 to 10
            'earnings': scores.earnings_confidence * 10  # Scale 0-1 to 0-10
        }

        # Normalize component values to 0-1 for fair comparison
        max_val = max(component_values.values()) if component_values.values() else 1.0
        if max_val == 0:
            max_val = 1.0

        normalized_values = {
            name: val / max_val
            for name, val in component_values.items()
        }

        # Update each arm based on its contribution
        for name, arm in self.arms.items():
            component_value = normalized_values.get(name, 0.5)

            # If component was high (>0.7) and trade won, or low (<0.3) and trade lost
            # then component was "correct"
            if trade_won:
                component_correct = component_value > 0.6
            else:
                component_correct = component_value < 0.4

            arm.update(component_correct, pnl_pct)

        # Also update regime-specific bandit if regime is known
        regime = trade.market_context.regime
        if regime and regime != MarketRegimeType.UNKNOWN:
            self._ensure_regime_bandit(regime)
            for name, arm in self.regime_bandits[regime].items():
                component_value = normalized_values.get(name, 0.5)
                if trade_won:
                    component_correct = component_value > 0.6
                else:
                    component_correct = component_value < 0.4
                arm.update(component_correct, pnl_pct)

        # Record weight evolution
        current_weights = self.select_weights()
        self.weight_history.append({
            'timestamp': datetime.now().isoformat(),
            'weights': current_weights.to_dict(),
            'confidence': current_weights.confidence,
            'trade_outcome': trade.outcome.value,
            'trade_pnl': pnl_pct
        })

        # Keep history manageable
        if len(self.weight_history) > 1000:
            self.weight_history = self.weight_history[-1000:]

        # Save state
        self.save_state()

    def update_batch(self, trades: List[TradeRecord]):
        """Update from multiple trades at once (faster for backtesting)."""
        for trade in trades:
            self.update_from_trade(trade)

    # =========================================================================
    # REGIME-SPECIFIC LEARNING
    # =========================================================================

    def _ensure_regime_bandit(self, regime: MarketRegimeType):
        """Ensure regime-specific bandit exists."""
        if regime not in self.regime_bandits:
            self.regime_bandits[regime] = {
                'theme': ComponentArm('theme'),
                'technical': ComponentArm('technical'),
                'ai': ComponentArm('ai'),
                'sentiment': ComponentArm('sentiment'),
                'earnings': ComponentArm('earnings')
            }

    def get_regime_weights(self, regime: MarketRegimeType) -> ComponentWeights:
        """Get optimal weights for a specific regime."""
        if regime in self.regime_bandits:
            return self.select_weights(regime)
        else:
            # Fall back to general weights
            return self.select_weights()

    # =========================================================================
    # STATISTICS & REPORTING
    # =========================================================================

    def get_statistics(self, regime: Optional[MarketRegimeType] = None) -> dict:
        """Get statistics for all components."""
        arms = self.regime_bandits.get(regime, self.arms) if regime else self.arms

        stats = {}
        for name, arm in arms.items():
            stats[name] = arm.get_stats()

        # Add overall statistics
        total_trades = arms['theme'].total_pulls
        current_weights = self.select_weights(regime)

        return {
            'components': stats,
            'total_trades': total_trades,
            'current_weights': current_weights.to_dict(),
            'confidence': current_weights.confidence,
            'regime': regime.value if regime else 'all',
            'best_component': max(stats.items(), key=lambda x: x[1]['mean_win_prob'])[0] if stats else None,
            'worst_component': min(stats.items(), key=lambda x: x[1]['mean_win_prob'])[0] if stats else None
        }

    def get_weight_evolution(self) -> List[Dict]:
        """Get history of weight changes."""
        return self.weight_history

    def print_report(self):
        """Print a human-readable report."""
        print("\n" + "=" * 80)
        print("BAYESIAN BANDIT REPORT - Component Weight Learning")
        print("=" * 80)

        stats = self.get_statistics()

        print(f"\nTotal Trades Learned From: {stats['total_trades']}")
        print(f"Learning Confidence: {stats['confidence']:.1%}")

        print("\n📊 Current Optimal Weights:")
        weights = stats['current_weights']
        for name, weight in weights.items():
            print(f"  {name.capitalize()}: {weight:.1%}")

        print("\n🎯 Component Performance:")
        for name, comp_stats in stats['components'].items():
            ci_lower, ci_upper = comp_stats['credible_interval']
            print(f"\n  {name.upper()}:")
            print(f"    Win Probability: {comp_stats['mean_win_prob']:.1%} (95% CI: {ci_lower:.1%} - {ci_upper:.1%})")
            print(f"    Sample Size: {comp_stats['total_pulls']} trades")
            print(f"    Win Rate: {comp_stats['win_rate']:.1%}")
            print(f"    Avg P&L: {comp_stats['avg_pnl']:+.2f}%")
            print(f"    Uncertainty: {comp_stats['uncertainty']:.4f}")

        print(f"\n✅ Best Component: {stats['best_component'].upper()}")
        print(f"❌ Worst Component: {stats['worst_component'].upper()}")

        print("\n" + "=" * 80)

    # =========================================================================
    # PERSISTENCE
    # =========================================================================

    def save_state(self):
        """Save bandit state to disk."""
        state = {
            'arms': {
                name: {
                    'alpha': arm.distribution.alpha,
                    'beta': arm.distribution.beta,
                    'total_pulls': arm.total_pulls,
                    'total_wins': arm.total_wins,
                    'total_losses': arm.total_losses,
                    'recent_pnl': arm.recent_pnl
                }
                for name, arm in self.arms.items()
            },
            'regime_bandits': {
                regime.value: {
                    name: {
                        'alpha': arm.distribution.alpha,
                        'beta': arm.distribution.beta,
                        'total_pulls': arm.total_pulls,
                        'total_wins': arm.total_wins,
                        'total_losses': arm.total_losses,
                        'recent_pnl': arm.recent_pnl
                    }
                    for name, arm in arms.items()
                }
                for regime, arms in self.regime_bandits.items()
            },
            'weight_history': self.weight_history,
            'last_updated': datetime.now().isoformat()
        }

        path = self.storage_dir / 'bandit_state.json'
        with open(path, 'w') as f:
            json.dump(state, f, indent=2, cls=LearningDataEncoder)

    def load_state(self):
        """Load bandit state from disk."""
        path = self.storage_dir / 'bandit_state.json'
        if not path.exists():
            return

        try:
            with open(path, 'r') as f:
                state = json.load(f)

            # Restore arms
            for name, arm_data in state.get('arms', {}).items():
                self.arms[name].distribution.alpha = arm_data['alpha']
                self.arms[name].distribution.beta = arm_data['beta']
                self.arms[name].total_pulls = arm_data['total_pulls']
                self.arms[name].total_wins = arm_data['total_wins']
                self.arms[name].total_losses = arm_data['total_losses']
                self.arms[name].recent_pnl = arm_data['recent_pnl']

            # Restore regime bandits
            for regime_str, arms_data in state.get('regime_bandits', {}).items():
                regime = MarketRegimeType(regime_str)
                self._ensure_regime_bandit(regime)
                for name, arm_data in arms_data.items():
                    self.regime_bandits[regime][name].distribution.alpha = arm_data['alpha']
                    self.regime_bandits[regime][name].distribution.beta = arm_data['beta']
                    self.regime_bandits[regime][name].total_pulls = arm_data['total_pulls']
                    self.regime_bandits[regime][name].total_wins = arm_data['total_wins']
                    self.regime_bandits[regime][name].total_losses = arm_data['total_losses']
                    self.regime_bandits[regime][name].recent_pnl = arm_data['recent_pnl']

            # Restore weight history
            self.weight_history = state.get('weight_history', [])

        except Exception as e:
            logger.warning(f"Could not load bandit state: {e}")


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    from .rl_models import ComponentScores, MarketContext

    print("Testing Bayesian Bandit...")

    bandit = BayesianBandit()

    # Simulate some trades
    print("\nSimulating 50 trades...")

    for i in range(50):
        # Select weights
        weights = bandit.select_weights()

        # Simulate a trade with random outcome
        # In reality, this would come from actual trades
        trade = TradeRecord(
            trade_id=f"TEST_{i}",
            decision_id=f"DEC_{i}",
            ticker="TEST",
            entry_date=datetime.now(),
            entry_price=100.0,
            exit_price=100.0 + np.random.randn() * 5,  # Random outcome
            shares=100,
            component_scores=ComponentScores(
                theme_score=np.random.rand() * 10,
                technical_score=np.random.rand() * 10,
                ai_confidence=np.random.rand(),
                x_sentiment_score=np.random.rand() * 2 - 1
            ),
            market_context=MarketContext(),
            weights_used=weights
        )
        trade.calculate_outcome()

        # Update bandit
        bandit.update_from_trade(trade)

    # Print report
    bandit.print_report()

    print("\n✅ Bayesian Bandit test complete!")
