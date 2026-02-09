"""
Paper Trading System — Automated Forward Testing with Adaptive Intelligence.

Uses Tastytrade certification (sandbox) API for realistic order execution.
Includes adaptive feedback loops, Greek flow analysis, and Kelly sizing.
"""

from .risk_manager import RiskManager
from .journal import TradeJournal
from .paper_engine import PaperEngine
from .signal_engine import SignalEngine
from .analytics import PerformanceAnalytics
from .adaptive_engine import (
    SignalPerformanceTracker,
    AdaptiveWeights,
    GreeksPnLTracker,
    AdaptiveExitEngine,
    EdgeScoreEngine,
    StrategySelector,
    KellyPositionSizer,
    FlowToxicityAnalyzer,
    LearningTierConnector,
    ABTestEngine,
)
from .greek_flows import (
    calculate_vanna_exposure,
    calculate_charm_exposure,
    compute_dealer_flow_forecast,
    compute_vanna,
    compute_charm,
    compute_volga,
)

__all__ = [
    'RiskManager',
    'TradeJournal',
    'PaperEngine',
    'SignalEngine',
    'PerformanceAnalytics',
    'SignalPerformanceTracker',
    'AdaptiveWeights',
    'GreeksPnLTracker',
    'AdaptiveExitEngine',
    'EdgeScoreEngine',
    'StrategySelector',
    'KellyPositionSizer',
    'FlowToxicityAnalyzer',
    'LearningTierConnector',
    'ABTestEngine',
    'calculate_vanna_exposure',
    'calculate_charm_exposure',
    'compute_dealer_flow_forecast',
    'compute_vanna',
    'compute_charm',
    'compute_volga',
]
