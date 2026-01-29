"""
Self-Learning Trading Brain System

A production-grade reinforcement learning system with 4 tiers:
- Tier 1: Bayesian Multi-Armed Bandit for component weighting
- Tier 2: Market Regime Detection with HMM
- Tier 3: Deep RL with Proximal Policy Optimization (PPO)
- Tier 4: Meta-Learning with MAML

Author: Stock Scanner Bot
Version: 1.0.0
"""

# Data models
from .rl_models import (
    TradeRecord,
    DecisionRecord,
    LearningMetrics,
    MarketRegimeType,
    MarketContext,
    ComponentWeights,
    ComponentScores,
    RegimeState,
    TradeOutcome,
    LearnerType,
    create_decision_id,
    create_trade_id,
    LearningDataEncoder
)

# Tier implementations
from .tier1_bandit import BayesianBandit
from .tier2_regime import RegimeDetector, MarketFeatures
from .tier3_ppo import PPOAgent, TradingState, TradingAction
from .tier4_meta import MetaLearner

# Main orchestrator
from .learning_brain import SelfLearningBrain, LearningConfig, get_learning_brain

# API
from .learning_api import learning_bp

__all__ = [
    # Models
    'TradeRecord',
    'DecisionRecord',
    'LearningMetrics',
    'MarketRegimeType',
    'MarketContext',
    'ComponentWeights',
    'ComponentScores',
    'RegimeState',
    'TradeOutcome',
    'LearnerType',
    'create_decision_id',
    'create_trade_id',
    'LearningDataEncoder',

    # Tiers
    'BayesianBandit',
    'RegimeDetector',
    'MarketFeatures',
    'PPOAgent',
    'TradingState',
    'TradingAction',
    'MetaLearner',

    # Main
    'SelfLearningBrain',
    'LearningConfig',
    'get_learning_brain',

    # API
    'learning_bp'
]

__version__ = '1.0.0'
