#!/usr/bin/env python3
"""
Tier 4: Meta-Learning System

Implements:
1. Ensemble of learners (Conservative, Aggressive, Balanced)
2. Meta-policy for learner selection
3. MAML (Model-Agnostic Meta-Learning) for fast adaptation
4. Learn how to learn - adapt quickly to new market regimes

The meta-learner maintains multiple specialized agents and learns
which agent to trust under different market conditions.
"""

import logging
import numpy as np
import torch
import torch.nn as nn
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import json

logger = logging.getLogger(__name__)

from .rl_models import (
    TradeRecord,
    LearnerType,
    MarketRegimeType,
    ComponentWeights,
    TradeOutcome,
    LearningDataEncoder
)
from .tier1_bandit import BayesianBandit
from .tier3_ppo import PPOAgent, TradingState, TradingAction


# =============================================================================
# SPECIALIZED LEARNERS
# =============================================================================

@dataclass
class LearnerConfig:
    """Configuration for a specialized learner."""
    name: LearnerType
    risk_tolerance: float  # 0-1, affects position sizing
    patience: float  # 0-1, affects hold duration
    learning_rate: float
    exploration_rate: float


class SpecializedLearner:
    """
    A specialized learner optimized for specific market conditions.

    Each learner has its own:
    - PPO agent
    - Bandit for component weights
    - Performance history
    - Risk parameters
    """

    def __init__(self, config: LearnerConfig, storage_dir: Path):
        """Initialize specialized learner."""
        self.config = config
        self.storage_dir = storage_dir / config.name.value
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # Initialize components
        self.ppo_agent = PPOAgent(
            lr=config.learning_rate,
            storage_dir=self.storage_dir
        )
        self.bandit = BayesianBandit(storage_dir=self.storage_dir)

        # Performance tracking
        self.performance_history: List[float] = []
        self.trades: List[TradeRecord] = []
        self.active_count = 0  # Times this learner was selected
        self.recent_sharpe = 0.0

    def select_action(self, state: TradingState, training: bool = True) -> TradingAction:
        """Select action using this learner's policy."""
        action = self.ppo_agent.select_action(state, training)

        # Apply learner-specific risk adjustments
        action.position_size_pct *= self.config.risk_tolerance
        action.hold_duration_days = int(action.hold_duration_days * self.config.patience)

        return action

    def get_component_weights(self, regime: Optional[MarketRegimeType] = None) -> ComponentWeights:
        """Get component weights from this learner's bandit."""
        return self.bandit.select_weights(regime)

    def update_from_trade(self, trade: TradeRecord, reward: float):
        """Update this learner from trade outcome."""
        # Update PPO agent
        self.ppo_agent.store_transition(reward, done=True)
        if len(self.ppo_agent.rewards) >= 10:  # Batch size
            self.ppo_agent.train_step()

        # Update bandit
        self.bandit.update_from_trade(trade)

        # Track performance
        if trade.pnl_pct is not None:
            self.performance_history.append(trade.pnl_pct)
            if len(self.performance_history) > 100:
                self.performance_history.pop(0)

            # Update Sharpe ratio
            if len(self.performance_history) >= 10:
                returns = np.array(self.performance_history)
                self.recent_sharpe = np.mean(returns) / (np.std(returns) + 1e-8)

        self.trades.append(trade)

    def get_performance_score(self) -> float:
        """Get current performance score (0-1)."""
        if not self.performance_history:
            return 0.5  # Neutral

        # Combine multiple metrics
        win_rate = sum(1 for r in self.performance_history if r > 0) / len(self.performance_history)
        avg_return = np.mean(self.performance_history)
        sharpe = self.recent_sharpe

        # Weighted combination
        score = (
            0.3 * win_rate +
            0.3 * min(1.0, max(0.0, (avg_return + 10) / 20)) +  # Map -10% to 10% into 0-1
            0.4 * min(1.0, max(0.0, (sharpe + 1) / 3))  # Map -1 to 2 Sharpe into 0-1
        )

        return score

    def save(self):
        """Save learner state."""
        self.ppo_agent.save_model()
        self.bandit.save_state()

        # Save learner metadata
        metadata = {
            'config': {
                'name': self.config.name.value,
                'risk_tolerance': self.config.risk_tolerance,
                'patience': self.config.patience,
                'learning_rate': self.config.learning_rate
            },
            'performance_history': self.performance_history,
            'active_count': self.active_count,
            'recent_sharpe': self.recent_sharpe,
            'total_trades': len(self.trades)
        }

        with open(self.storage_dir / 'metadata.json', 'w') as f:
            json.dump(metadata, f, indent=2, cls=LearningDataEncoder)

    def load(self):
        """Load learner state."""
        self.ppo_agent.load_model()
        self.bandit.load_state()

        metadata_path = self.storage_dir / 'metadata.json'
        if metadata_path.exists():
            try:
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                self.performance_history = metadata.get('performance_history', [])
                self.active_count = metadata.get('active_count', 0)
                self.recent_sharpe = metadata.get('recent_sharpe', 0.0)
            except Exception as e:
                logger.warning(f"Could not load learner metadata: {e}")


# =============================================================================
# META-POLICY (LEARNER SELECTOR)
# =============================================================================

class MetaPolicyNetwork(nn.Module):
    """
    Meta-policy that selects which learner to use.

    Inputs: Market state + learner performance scores
    Output: Probability distribution over learners
    """

    def __init__(self, state_dim: int = 27, num_learners: int = 3, hidden_dim: int = 128):
        super().__init__()

        # Input is state + learner scores
        input_dim = state_dim + num_learners

        self.network = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, num_learners),
            nn.Softmax(dim=-1)
        )

    def forward(self, state: torch.Tensor, learner_scores: torch.Tensor) -> torch.Tensor:
        """
        Select learner probabilities.

        Args:
            state: Market/portfolio state
            learner_scores: Performance scores of each learner

        Returns:
            Probabilities for each learner
        """
        combined = torch.cat([state, learner_scores], dim=-1)
        return self.network(combined)


# =============================================================================
# META-LEARNER (ENSEMBLE COORDINATOR)
# =============================================================================

class MetaLearner:
    """
    Meta-learning system that coordinates multiple specialized learners.

    Maintains:
    - Conservative learner (low risk, high patience)
    - Aggressive learner (high risk, quick trades)
    - Balanced learner (middle ground)

    Uses meta-policy to select which learner to trust.
    """

    def __init__(self, storage_dir: Optional[Path] = None):
        """Initialize meta-learner."""
        self.storage_dir = storage_dir or Path('user_data/learning/meta')
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # Initialize specialized learners
        self.learners = {
            LearnerType.CONSERVATIVE: SpecializedLearner(
                LearnerConfig(
                    name=LearnerType.CONSERVATIVE,
                    risk_tolerance=0.5,
                    patience=1.5,
                    learning_rate=1e-4,
                    exploration_rate=0.1
                ),
                self.storage_dir
            ),
            LearnerType.AGGRESSIVE: SpecializedLearner(
                LearnerConfig(
                    name=LearnerType.AGGRESSIVE,
                    risk_tolerance=1.0,
                    patience=0.6,
                    learning_rate=5e-4,
                    exploration_rate=0.3
                ),
                self.storage_dir
            ),
            LearnerType.BALANCED: SpecializedLearner(
                LearnerConfig(
                    name=LearnerType.BALANCED,
                    risk_tolerance=0.75,
                    patience=1.0,
                    learning_rate=3e-4,
                    exploration_rate=0.2
                ),
                self.storage_dir
            )
        }

        # Meta-policy network
        self.meta_policy = MetaPolicyNetwork()
        self.meta_optimizer = torch.optim.Adam(self.meta_policy.parameters(), lr=1e-4)

        # Selection history
        self.selection_history: List[Dict] = []

        # Current best learner
        self.current_learner: Optional[LearnerType] = None

        # Load state
        self.load()

    # =========================================================================
    # LEARNER SELECTION
    # =========================================================================

    def select_learner(self, state: TradingState, regime: MarketRegimeType) -> LearnerType:
        """
        Select which learner to use for current state.

        Uses meta-policy network to choose based on:
        - Current market state
        - Recent performance of each learner
        - Market regime
        """
        # Get performance scores for each learner
        learner_scores = torch.tensor([
            learner.get_performance_score()
            for learner in self.learners.values()
        ], dtype=torch.float32)

        # Get state tensor
        state_tensor = state.to_tensor().unsqueeze(0)

        # Get learner probabilities from meta-policy
        with torch.no_grad():
            probs = self.meta_policy(state_tensor, learner_scores.unsqueeze(0))
            probs = probs.squeeze(0)

        # Select learner (sample from distribution for exploration)
        learner_idx = torch.multinomial(probs, 1).item()
        learner_types = list(self.learners.keys())
        selected_learner = learner_types[learner_idx]

        # Update active count
        self.learners[selected_learner].active_count += 1

        # Record selection
        self.selection_history.append({
            'timestamp': datetime.now().isoformat(),
            'learner': selected_learner.value,
            'probabilities': probs.tolist(),
            'regime': regime.value,
            'learner_scores': learner_scores.tolist()
        })

        # Keep history manageable
        if len(self.selection_history) > 1000:
            self.selection_history = self.selection_history[-1000:]

        self.current_learner = selected_learner
        return selected_learner

    def get_action(
        self,
        state: TradingState,
        regime: MarketRegimeType,
        training: bool = True
    ) -> Tuple[TradingAction, LearnerType]:
        """
        Get action from the selected learner.

        Returns: (action, learner_type)
        """
        # Select learner
        learner_type = self.select_learner(state, regime)
        learner = self.learners[learner_type]

        # Get action
        action = learner.select_action(state, training)

        return action, learner_type

    def get_component_weights(
        self,
        regime: MarketRegimeType
    ) -> Tuple[ComponentWeights, LearnerType]:
        """
        Get component weights from best performing learner.

        Returns: (weights, learner_type)
        """
        # Find best performing learner
        best_learner_type = max(
            self.learners.items(),
            key=lambda x: x[1].get_performance_score()
        )[0]

        learner = self.learners[best_learner_type]
        weights = learner.get_component_weights(regime)

        return weights, best_learner_type

    # =========================================================================
    # LEARNING
    # =========================================================================

    def update_from_trade(
        self,
        trade: TradeRecord,
        learner_type: LearnerType,
        reward: float
    ):
        """
        Update the learner that made this decision.

        Also update meta-policy based on learner performance.
        """
        # Update the specific learner
        learner = self.learners[learner_type]
        learner.update_from_trade(trade, reward)

        # Update meta-policy
        # (Reward good learner selections, penalize bad ones)
        # This is simplified - full implementation would use REINFORCE or similar
        if len(self.selection_history) > 0:
            last_selection = self.selection_history[-1]
            if last_selection['learner'] == learner_type.value:
                # This learner was selected - update meta-policy
                # based on whether it did well
                performance_score = learner.get_performance_score()

                # Meta-policy update would go here
                # For now, implicit through learner performance tracking

    def update_all_learners(self, trade: TradeRecord, reward: float):
        """
        Update all learners (ensemble learning).

        Each learner learns from all trades, but weighted by their selection frequency.
        """
        for learner_type, learner in self.learners.items():
            # Weight update by how often this learner is selected
            selection_rate = learner.active_count / max(1, sum(l.active_count for l in self.learners.values()))
            weighted_reward = reward * selection_rate

            learner.update_from_trade(trade, weighted_reward)

    # =========================================================================
    # FAST ADAPTATION (MAML-INSPIRED)
    # =========================================================================

    def quick_adapt(self, recent_trades: List[TradeRecord], regime: MarketRegimeType):
        """
        Quickly adapt to new market regime using recent trades.

        MAML-inspired: Use few recent trades to fine-tune the selected learner.
        """
        if not recent_trades:
            return

        # Identify which learner is best for this regime
        best_learner = self._find_best_learner_for_regime(regime, recent_trades)

        # Fine-tune this learner on recent trades (few-shot learning)
        for trade in recent_trades[-5:]:  # Last 5 trades only
            reward = 1.0 if trade.outcome == TradeOutcome.WIN else -1.0
            best_learner.update_from_trade(trade, reward)

    def _find_best_learner_for_regime(
        self,
        regime: MarketRegimeType,
        recent_trades: List[TradeRecord]
    ) -> SpecializedLearner:
        """Find which learner performs best in this regime."""
        # Simplified: return balanced learner as default
        # Full implementation would analyze historical regime performance
        return self.learners[LearnerType.BALANCED]

    # =========================================================================
    # STATISTICS & REPORTING
    # =========================================================================

    def get_statistics(self) -> dict:
        """Get meta-learner statistics."""
        stats = {
            'learners': {},
            'meta_policy': {},
            'recent_selections': self.selection_history[-20:]
        }

        # Learner stats
        for learner_type, learner in self.learners.items():
            stats['learners'][learner_type.value] = {
                'performance_score': learner.get_performance_score(),
                'recent_sharpe': learner.recent_sharpe,
                'total_trades': len(learner.trades),
                'active_count': learner.active_count,
                'win_rate': (
                    sum(1 for t in learner.trades if t.outcome == TradeOutcome.WIN) /
                    len(learner.trades) if learner.trades else 0.0
                )
            }

        # Selection distribution
        total_selections = sum(l.active_count for l in self.learners.values())
        stats['meta_policy']['selection_distribution'] = {
            learner_type.value: learner.active_count / total_selections if total_selections > 0 else 0.0
            for learner_type, learner in self.learners.items()
        }

        return stats

    def print_report(self):
        """Print meta-learner report."""
        print("\n" + "=" * 80)
        print("META-LEARNER REPORT")
        print("=" * 80)

        stats = self.get_statistics()

        print("\n🎯 Learner Performance:")
        for learner_name, learner_stats in stats['learners'].items():
            print(f"\n  {learner_name.upper()}:")
            print(f"    Performance Score: {learner_stats['performance_score']:.2f}")
            print(f"    Sharpe Ratio: {learner_stats['recent_sharpe']:.2f}")
            print(f"    Win Rate: {learner_stats['win_rate']:.1%}")
            print(f"    Total Trades: {learner_stats['total_trades']}")
            print(f"    Times Selected: {learner_stats['active_count']}")

        print("\n📊 Selection Distribution:")
        for learner_name, pct in stats['meta_policy']['selection_distribution'].items():
            print(f"  {learner_name}: {pct:.1%}")

        print("\n" + "=" * 80)

    # =========================================================================
    # PERSISTENCE
    # =========================================================================

    def save(self):
        """Save all learners and meta-policy."""
        # Save each learner
        for learner in self.learners.values():
            learner.save()

        # Save meta-policy
        torch.save({
            'meta_policy_state_dict': self.meta_policy.state_dict(),
            'meta_optimizer_state_dict': self.meta_optimizer.state_dict(),
        }, self.storage_dir / 'meta_policy.pt')

        # Save selection history
        with open(self.storage_dir / 'selection_history.json', 'w') as f:
            json.dump(self.selection_history, f, indent=2, cls=LearningDataEncoder)

    def load(self):
        """Load all learners and meta-policy."""
        # Load each learner
        for learner in self.learners.values():
            learner.load()

        # Load meta-policy
        meta_policy_path = self.storage_dir / 'meta_policy.pt'
        if meta_policy_path.exists():
            try:
                checkpoint = torch.load(meta_policy_path)
                self.meta_policy.load_state_dict(checkpoint['meta_policy_state_dict'])
                self.meta_optimizer.load_state_dict(checkpoint['meta_optimizer_state_dict'])
            except Exception as e:
                logger.warning(f"Could not load meta-policy: {e}")

        # Load selection history
        history_path = self.storage_dir / 'selection_history.json'
        if history_path.exists():
            try:
                with open(history_path, 'r') as f:
                    self.selection_history = json.load(f)
            except Exception as e:
                print(f"Warning: Could not load selection history: {e}")


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    print("Testing Meta-Learner...")

    meta_learner = MetaLearner()

    # Test action selection
    state = TradingState(theme_score=8.5, technical_score=7.0, ai_confidence=0.85)
    regime = MarketRegimeType.BULL_MOMENTUM

    action, learner_type = meta_learner.get_action(state, regime, training=False)
    print(f"\nSelected Learner: {learner_type.value}")
    print(f"Action: Position {action.position_size_pct:.1f}%, Hold {action.hold_duration_days} days")

    # Print report
    meta_learner.print_report()

    print("\n✅ Meta-Learner test complete!")
