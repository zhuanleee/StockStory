#!/usr/bin/env python3
"""
Self-Learning Brain - Main Orchestrator

Integrates all 4 tiers:
- Tier 1: Bayesian Bandit
- Tier 2: Regime Detection
- Tier 3: PPO Agent
- Tier 4: Meta-Learning

Provides unified interface for trading decisions and learning.
"""

import logging
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import json

logger = logging.getLogger(__name__)

from .tier1_bandit import BayesianBandit
from .tier2_regime import RegimeDetector, MarketFeatures
from .tier3_ppo import PPOAgent, TradingState, TradingAction
from .tier4_meta import MetaLearner
from .rl_models import (
    TradeRecord,
    DecisionRecord,
    ComponentScores,
    MarketContext,
    ComponentWeights,
    MarketRegimeType,
    LearningMetrics,
    LearnerType,
    TradeOutcome,
    create_decision_id,
    create_trade_id,
    LearningDataEncoder
)


# =============================================================================
# CONFIGURATION
# =============================================================================

@dataclass
class LearningConfig:
    """Configuration for learning system."""
    # Which tiers to enable
    use_tier1: bool = True  # Bayesian Bandit
    use_tier2: bool = True  # Regime Detection
    use_tier3: bool = False  # PPO Agent (more advanced)
    use_tier4: bool = False  # Meta-Learning (most advanced)

    # Learning parameters
    min_trades_before_learning: int = 5  # Wait for this many trades before trusting learning
    learning_rate: float = 0.01  # How quickly to adapt
    exploration_rate: float = 0.1  # % of time to explore vs exploit

    # Safety
    max_position_size: float = 0.20  # 20% max
    max_daily_loss: float = 0.02  # 2% max daily loss
    max_drawdown: float = 0.15  # 15% max drawdown
    enable_circuit_breaker: bool = True

    # Storage
    storage_dir: Optional[Path] = None


# =============================================================================
# SELF-LEARNING BRAIN
# =============================================================================

class SelfLearningBrain:
    """
    Main orchestrator for self-learning trading system.

    Coordinates all 4 tiers and provides unified interface.
    """

    def __init__(self, config: Optional[LearningConfig] = None):
        """Initialize self-learning brain."""
        self.config = config or LearningConfig()
        self.storage_dir = self.config.storage_dir or Path('user_data/learning')
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # Initialize tiers based on configuration
        self.bandit = BayesianBandit(self.storage_dir) if self.config.use_tier1 else None
        self.regime_detector = RegimeDetector(self.storage_dir) if self.config.use_tier2 else None
        self.ppo_agent = PPOAgent(storage_dir=self.storage_dir) if self.config.use_tier3 else None
        self.meta_learner = MetaLearner(self.storage_dir) if self.config.use_tier4 else None

        # State tracking
        self.total_trades = 0
        self.learning_active = False
        self.circuit_breaker_active = False

        # Performance metrics
        self.metrics = LearningMetrics()

        # Trade history
        self.trade_history: List[TradeRecord] = []
        self.decision_history: List[DecisionRecord] = []

        # Current state
        self.current_regime = MarketRegimeType.UNKNOWN
        self.current_weights = ComponentWeights()
        self.current_learner: Optional[LearnerType] = None

        # Load state
        self.load_state()

    # =========================================================================
    # DECISION MAKING
    # =========================================================================

    def get_trading_decision(
        self,
        ticker: str,
        component_scores: ComponentScores,
        market_context: MarketContext,
        portfolio_state: Optional[Dict] = None,
        training: bool = True
    ) -> DecisionRecord:
        """
        Get a trading decision using learned parameters.

        This is the main entry point for getting trading decisions.

        Args:
            ticker: Stock ticker
            component_scores: Scores from all 38 components (including earnings)
            market_context: Current market state
            portfolio_state: Current portfolio state (for Tier 3+)
            training: Whether to explore (True) or exploit (False)

        Returns:
            DecisionRecord with action, weights, and reasoning
        """
        # Detect regime (Tier 2)
        if self.regime_detector:
            regime_state = self.regime_detector.detect_regime(market_context)
            self.current_regime = regime_state.current_regime
            market_context.regime = self.current_regime
            market_context.regime_confidence = regime_state.confidence
        else:
            self.current_regime = MarketRegimeType.UNKNOWN

        # Get component weights (Tier 1 or Tier 4)
        if self.meta_learner:
            # Tier 4: Meta-learner provides weights
            weights, self.current_learner = self.meta_learner.get_component_weights(self.current_regime)
        elif self.bandit:
            # Tier 1: Bandit provides weights
            if self.current_regime != MarketRegimeType.UNKNOWN:
                weights = self.bandit.get_regime_weights(self.current_regime)
            else:
                weights = self.bandit.select_weights()
            self.current_learner = None
        else:
            # Default weights
            weights = ComponentWeights()

        self.current_weights = weights

        # Calculate overall score using learned weights
        overall_score = self._calculate_overall_score(component_scores, weights)
        signal_quality = self._classify_signal_quality(overall_score)
        setup_complete = self._check_setup_complete(component_scores, overall_score)

        # Get action parameters (Tier 3 or Tier 4)
        if self.meta_learner and portfolio_state:
            # Tier 4: Meta-learner provides action
            trading_state = self._build_trading_state(component_scores, market_context, portfolio_state)
            action, self.current_learner = self.meta_learner.get_action(
                trading_state,
                self.current_regime,
                training
            )
            position_size = action.position_size_pct
            stop_loss = action.stop_loss_pct
            take_profit = action.take_profit_pct
        elif self.ppo_agent and portfolio_state:
            # Tier 3: PPO agent provides action
            trading_state = self._build_trading_state(component_scores, market_context, portfolio_state)
            action = self.ppo_agent.select_action(trading_state, training)
            position_size = action.position_size_pct
            stop_loss = action.stop_loss_pct
            take_profit = action.take_profit_pct
        else:
            # Default: Use rule-based position sizing
            position_size = self._default_position_size(overall_score)
            stop_loss = 10.0  # 10% default stop
            take_profit = 20.0  # 20% default target

        # Apply safety constraints
        if self.circuit_breaker_active:
            position_size = 0.0  # No trading during circuit breaker

        position_size = min(position_size, self.config.max_position_size * 100)

        # Determine action
        action_str = "buy" if setup_complete and overall_score >= 6.0 else "pass"

        # Create decision record
        decision = DecisionRecord(
            decision_id=create_decision_id(ticker, datetime.now()),
            ticker=ticker,
            timestamp=datetime.now(),
            action=action_str,
            position_size=position_size,
            conviction=min(1.0, overall_score / 10),
            component_scores=component_scores,
            market_context=market_context,
            weights_used=weights,
            overall_score=overall_score,
            signal_quality=signal_quality,
            setup_complete=setup_complete,
            entry_price=None,  # To be filled when trade executes
            stop_loss=stop_loss,
            take_profit=take_profit,
            learner_type=self.current_learner,
            regime_at_decision=self.current_regime
        )

        # Record decision
        self.decision_history.append(decision)

        return decision

    def _calculate_overall_score(
        self,
        scores: ComponentScores,
        weights: ComponentWeights
    ) -> float:
        """Calculate weighted overall score (5 components including earnings)."""
        theme_contrib = scores.theme_score * weights.theme
        technical_contrib = scores.technical_score * weights.technical
        ai_contrib = scores.ai_confidence * 10 * weights.ai
        sentiment_contrib = ((scores.x_sentiment_score + 1) * 5 if scores.x_sentiment_score else 5) * weights.sentiment
        earnings_contrib = scores.earnings_confidence * 10 * weights.earnings

        overall = theme_contrib + technical_contrib + ai_contrib + sentiment_contrib + earnings_contrib
        return min(10.0, max(0.0, overall))

    def _classify_signal_quality(self, score: float) -> str:
        """Classify signal quality based on score."""
        if score >= 8.0:
            return "excellent"
        elif score >= 6.0:
            return "good"
        elif score >= 4.0:
            return "fair"
        else:
            return "poor"

    def _check_setup_complete(self, scores: ComponentScores, overall_score: float) -> bool:
        """Check if setup is complete for trading."""
        return (
            overall_score >= 6.0 and
            scores.theme_score > 0 and
            scores.technical_score > 0
        )

    def _default_position_size(self, score: float) -> float:
        """Default position sizing based on score."""
        if score >= 8.0:
            return 15.0  # 15% for excellent setups
        elif score >= 6.0:
            return 10.0  # 10% for good setups
        else:
            return 5.0  # 5% for fair setups

    def _build_trading_state(
        self,
        scores: ComponentScores,
        market_context: MarketContext,
        portfolio_state: Dict
    ) -> TradingState:
        """Build TradingState for PPO/Meta-learner."""
        # Extract regime probabilities
        regime_probs = {
            MarketRegimeType.BULL_MOMENTUM: 0.2,
            MarketRegimeType.BEAR_DEFENSIVE: 0.2,
            MarketRegimeType.CHOPPY_RANGE: 0.2
        }

        if self.regime_detector and self.regime_detector.current_state:
            regime_probs = self.regime_detector.current_state.regime_probabilities

        return TradingState(
            cash_pct=portfolio_state.get('cash_pct', 100.0),
            num_positions=portfolio_state.get('num_positions', 0),
            total_exposure_pct=portfolio_state.get('total_exposure_pct', 0.0),
            unrealized_pnl_pct=portfolio_state.get('unrealized_pnl_pct', 0.0),
            current_drawdown_pct=portfolio_state.get('current_drawdown_pct', 0.0),
            total_return_pct=portfolio_state.get('total_return_pct', 0.0),
            spy_change_pct=market_context.spy_change_pct or 0.0,
            vix_level=market_context.vix_level or 20.0,
            advance_decline=market_context.advance_decline or 1.0,
            stocks_above_ma50=market_context.stocks_above_ma50 or 50.0,
            regime_bull_prob=regime_probs.get(MarketRegimeType.BULL_MOMENTUM, 0.2),
            regime_bear_prob=regime_probs.get(MarketRegimeType.BEAR_DEFENSIVE, 0.2),
            regime_choppy_prob=regime_probs.get(MarketRegimeType.CHOPPY_RANGE, 0.2),
            crisis_active=1.0 if market_context.crisis_active else 0.0,
            theme_score=scores.theme_score,
            technical_score=scores.technical_score,
            ai_confidence=scores.ai_confidence,
            x_sentiment_score=scores.x_sentiment_score or 0.0,
            win_rate_last_10=self.metrics.win_rate if self.total_trades >= 10 else 0.5,
            sharpe_last_20=self.metrics.sharpe_ratio
        )

    # =========================================================================
    # LEARNING
    # =========================================================================

    def learn_from_trade(
        self,
        trade: TradeRecord,
        portfolio_state: Optional[Dict] = None
    ):
        """
        Learn from a completed trade.

        Updates all active tiers based on trade outcome.

        Args:
            trade: Completed trade record
            portfolio_state: Current portfolio state (for reward calculation)
        """
        if trade.outcome == TradeOutcome.OPEN:
            return  # Don't learn from open trades

        self.total_trades += 1
        self.trade_history.append(trade)

        # Activate learning after minimum trades
        if self.total_trades >= self.config.min_trades_before_learning:
            self.learning_active = True

        if not self.learning_active:
            return

        # Update Tier 1: Bandit
        if self.bandit:
            self.bandit.update_from_trade(trade)

        # Update Tier 2: Regime Detector
        if self.regime_detector:
            self.regime_detector.update_from_trade(trade)

        # Update Tier 3+4: PPO/Meta-learner
        if portfolio_state:
            reward = self._calculate_reward(trade, portfolio_state)

            if self.meta_learner and self.current_learner:
                self.meta_learner.update_from_trade(trade, self.current_learner, reward)
            elif self.ppo_agent:
                self.ppo_agent.store_transition(reward, done=True)
                if len(self.ppo_agent.rewards) >= 10:
                    self.ppo_agent.train_step()

        # Update metrics
        self.metrics.update_from_trades(self.trade_history)

        # Check circuit breaker
        self._check_circuit_breaker()

        # Save state periodically
        if self.total_trades % 10 == 0:
            self.save_state()

    def _calculate_reward(self, trade: TradeRecord, portfolio_state: Dict) -> float:
        """Calculate reward for RL agents."""
        if self.ppo_agent:
            return self.ppo_agent.calculate_reward(trade, portfolio_state)

        # Simple reward: risk-adjusted return
        pnl = trade.pnl_pct or 0.0
        if trade.outcome == TradeOutcome.WIN:
            return pnl / 10  # Normalize
        else:
            return pnl / 20  # Smaller penalty

    def _check_circuit_breaker(self):
        """Check if circuit breaker should activate."""
        if not self.config.enable_circuit_breaker:
            return

        # Activate circuit breaker if:
        # 1. Sharpe ratio too low
        # 2. Drawdown too high
        # 3. Too many recent losses

        if self.total_trades < 20:
            return  # Need more data

        if self.metrics.sharpe_ratio < -0.5:
            self.circuit_breaker_active = True
            logger.warning("Circuit breaker activated: Sharpe ratio too low")

        if self.metrics.current_drawdown_pct > self.config.max_drawdown:
            self.circuit_breaker_active = True
            logger.warning("Circuit breaker activated: Max drawdown exceeded")

        # Deactivate if conditions improve
        if self.circuit_breaker_active:
            if (self.metrics.sharpe_ratio > 0.5 and
                self.metrics.current_drawdown_pct < self.config.max_drawdown * 0.5):
                self.circuit_breaker_active = False
                logger.info("Circuit breaker deactivated: Conditions improved")

    # =========================================================================
    # STATISTICS & REPORTING
    # =========================================================================

    def get_statistics(self) -> Dict:
        """Get comprehensive statistics."""
        stats = {
            'overview': {
                'total_trades': self.total_trades,
                'learning_active': self.learning_active,
                'circuit_breaker_active': self.circuit_breaker_active,
                'current_regime': self.current_regime.value,
                'current_learner': self.current_learner.value if self.current_learner else None
            },
            'performance': {
                'win_rate': self.metrics.win_rate,
                'sharpe_ratio': self.metrics.sharpe_ratio,
                'profit_factor': self.metrics.profit_factor,
                'max_drawdown': self.metrics.max_drawdown_pct,
                'current_drawdown': self.metrics.current_drawdown_pct,
                'total_return': self.metrics.total_return_pct
            },
            'current_weights': self.current_weights.to_dict(),
            'tiers': {}
        }

        # Tier-specific stats
        if self.bandit:
            stats['tiers']['bandit'] = self.bandit.get_statistics()

        if self.regime_detector:
            stats['tiers']['regime'] = self.regime_detector.get_statistics()

        if self.meta_learner:
            stats['tiers']['meta_learner'] = self.meta_learner.get_statistics()

        return stats

    def print_report(self):
        """Print comprehensive learning report."""
        print("\n" + "=" * 80)
        print("SELF-LEARNING BRAIN REPORT")
        print("=" * 80)

        stats = self.get_statistics()

        print(f"\n📊 Overview:")
        print(f"  Total Trades: {stats['overview']['total_trades']}")
        print(f"  Learning Active: {'✅' if stats['overview']['learning_active'] else '❌'}")
        print(f"  Circuit Breaker: {'🔴 ACTIVE' if stats['overview']['circuit_breaker_active'] else '🟢 OK'}")
        print(f"  Current Regime: {stats['overview']['current_regime']}")

        print(f"\n💰 Performance:")
        perf = stats['performance']
        print(f"  Win Rate: {perf['win_rate']:.1%}")
        print(f"  Sharpe Ratio: {perf['sharpe_ratio']:.2f}")
        print(f"  Profit Factor: {perf['profit_factor']:.2f}")
        print(f"  Total Return: {perf['total_return']:.2f}%")
        print(f"  Max Drawdown: {perf['max_drawdown']:.2f}%")
        print(f"  Current Drawdown: {perf['current_drawdown']:.2f}%")

        print(f"\n⚖️ Current Component Weights:")
        for comp, weight in stats['current_weights'].items():
            print(f"  {comp.capitalize()}: {weight:.1%}")

        # Tier-specific reports
        if self.bandit:
            print("\n" + "-" * 80)
            self.bandit.print_report()

        if self.regime_detector:
            print("\n" + "-" * 80)
            self.regime_detector.print_report()

        if self.meta_learner:
            print("\n" + "-" * 80)
            self.meta_learner.print_report()

        print("\n" + "=" * 80)

    # =========================================================================
    # PERSISTENCE
    # =========================================================================

    def save_state(self):
        """Save learning brain state."""
        # Save individual tiers
        if self.bandit:
            self.bandit.save_state()
        if self.regime_detector:
            self.regime_detector.save_state()
        if self.ppo_agent:
            self.ppo_agent.save_model()
        if self.meta_learner:
            self.meta_learner.save()

        # Save brain state
        state = {
            'total_trades': self.total_trades,
            'learning_active': self.learning_active,
            'circuit_breaker_active': self.circuit_breaker_active,
            'metrics': {
                'win_rate': self.metrics.win_rate,
                'sharpe_ratio': self.metrics.sharpe_ratio,
                'total_return_pct': self.metrics.total_return_pct
            },
            'last_updated': datetime.now().isoformat()
        }

        with open(self.storage_dir / 'brain_state.json', 'w') as f:
            json.dump(state, f, indent=2, cls=LearningDataEncoder)

    def load_state(self):
        """Load learning brain state."""
        # Load individual tiers (they load their own state in __init__)

        # Load brain state
        state_path = self.storage_dir / 'brain_state.json'
        if state_path.exists():
            try:
                with open(state_path, 'r') as f:
                    state = json.load(f)

                self.total_trades = state.get('total_trades', 0)
                self.learning_active = state.get('learning_active', False)
                self.circuit_breaker_active = state.get('circuit_breaker_active', False)

            except Exception as e:
                logger.warning(f"Could not load brain state: {e}")

    # =========================================================================
    # UTILITIES
    # =========================================================================

    def reset_learning(self):
        """Reset all learning (use with caution!)."""
        if input("Are you sure you want to reset all learning? (yes/no): ").lower() == 'yes':
            self.total_trades = 0
            self.learning_active = False
            self.circuit_breaker_active = False
            self.trade_history = []
            self.decision_history = []
            self.metrics = LearningMetrics()

            # Reinitialize tiers
            if self.bandit:
                self.bandit = BayesianBandit(self.storage_dir)
            if self.regime_detector:
                self.regime_detector = RegimeDetector(self.storage_dir)
            if self.ppo_agent:
                self.ppo_agent = PPOAgent(storage_dir=self.storage_dir)
            if self.meta_learner:
                self.meta_learner = MetaLearner(self.storage_dir)

            logger.info("Learning system reset complete")


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

_global_brain: Optional[SelfLearningBrain] = None


def get_learning_brain(config: Optional[LearningConfig] = None) -> SelfLearningBrain:
    """Get or create global learning brain instance."""
    global _global_brain
    if _global_brain is None:
        _global_brain = SelfLearningBrain(config)
    return _global_brain


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    print("Testing Self-Learning Brain...")

    # Test with Tier 1+2 only (simple, safe)
    config = LearningConfig(
        use_tier1=True,
        use_tier2=True,
        use_tier3=False,
        use_tier4=False
    )

    brain = SelfLearningBrain(config)

    # Simulate a decision
    scores = ComponentScores(
        theme_score=8.5,
        technical_score=7.2,
        ai_confidence=0.85,
        x_sentiment_score=0.6
    )

    market_context = MarketContext(
        spy_change_pct=2.5,
        vix_level=15.0,
        stocks_above_ma50=70.0
    )

    decision = brain.get_trading_decision(
        ticker="NVDA",
        component_scores=scores,
        market_context=market_context
    )

    print(f"\n📊 Decision for NVDA:")
    print(f"  Action: {decision.action}")
    print(f"  Overall Score: {decision.overall_score:.1f}/10")
    print(f"  Signal Quality: {decision.signal_quality}")
    print(f"  Setup Complete: {decision.setup_complete}")
    print(f"  Regime: {decision.regime_at_decision.value}")
    print(f"\n⚖️ Weights Used:")
    for comp, weight in decision.weights_used.to_dict().items():
        print(f"  {comp}: {weight:.1%}")

    # Simulate a trade outcome
    trade = TradeRecord(
        trade_id=create_trade_id("NVDA", datetime.now()),
        decision_id=decision.decision_id,
        ticker="NVDA",
        entry_date=datetime.now(),
        entry_price=850.0,
        exit_price=875.0,
        shares=100,
        component_scores=scores,
        market_context=market_context,
        weights_used=decision.weights_used
    )
    trade.calculate_outcome()

    # Learn from it
    brain.learn_from_trade(trade)

    print(f"\n✅ Learned from trade:")
    print(f"  Outcome: {trade.outcome.value}")
    print(f"  P&L: {trade.pnl_pct:.2f}%")

    # Print report
    brain.print_report()

    print("\n✅ Self-Learning Brain test complete!")
