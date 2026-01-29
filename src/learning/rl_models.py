#!/usr/bin/env python3
"""
Data Models for Self-Learning Reinforcement Learning System

Defines core data structures for:
- Trade records with full context
- Decision records with component scores
- Learning metrics and statistics
- Market regimes
- Component weights
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, Dict, List, Any
from enum import Enum
import json


# =============================================================================
# ENUMS
# =============================================================================

class TradeOutcome(str, Enum):
    """Trade outcome classification."""
    WIN = "win"
    LOSS = "loss"
    BREAKEVEN = "breakeven"
    OPEN = "open"


class MarketRegimeType(str, Enum):
    """Market regime classifications."""
    BULL_MOMENTUM = "bull_momentum"
    BEAR_DEFENSIVE = "bear_defensive"
    CHOPPY_RANGE = "choppy_range"
    CRISIS_MODE = "crisis_mode"
    THEME_DRIVEN = "theme_driven"
    UNKNOWN = "unknown"


class LearnerType(str, Enum):
    """Types of meta-learners."""
    CONSERVATIVE = "conservative"
    AGGRESSIVE = "aggressive"
    BALANCED = "balanced"


# =============================================================================
# CORE DATA MODELS
# =============================================================================

@dataclass
class ComponentScores:
    """Scores from all 40 components at decision time (added earnings, institutional flow)."""
    # Core scores (top-level components for learning)
    theme_score: float = 0.0
    technical_score: float = 0.0
    ai_confidence: float = 0.0
    x_sentiment_score: float = 0.0
    earnings_confidence: float = 0.5  # Component #38: Earnings Intelligence
    institutional_flow_score: float = 0.5  # Component #40: Institutional Flow (smart money)

    # Detailed component scores (all 37 original + earnings)
    rs_rating: Optional[int] = None
    momentum_score: Optional[float] = None
    volume_ratio: Optional[float] = None
    story_strength: Optional[str] = None
    theme_strength: Optional[int] = None
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    revenue_growth: Optional[float] = None
    earnings_growth: Optional[float] = None

    # Additional component outputs
    conviction_score: Optional[float] = None
    supplychain_score: Optional[float] = None
    ma_radar_score: Optional[float] = None
    earnings_catalyst: Optional[bool] = None
    sec_intel_score: Optional[float] = None

    # Add all other components as needed
    raw_components: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MarketContext:
    """Market context at decision time."""
    regime: MarketRegimeType = MarketRegimeType.UNKNOWN
    regime_confidence: float = 0.0

    # Market indicators
    spy_change_pct: Optional[float] = None
    qqq_change_pct: Optional[float] = None
    vix_level: Optional[float] = None
    advance_decline: Optional[float] = None
    sector_rotation: Optional[str] = None

    # Market breadth
    stocks_above_ma50: Optional[float] = None
    stocks_above_ma200: Optional[float] = None
    new_highs: Optional[int] = None
    new_lows: Optional[int] = None

    # Crisis indicators
    crisis_active: bool = False
    crisis_type: Optional[str] = None
    emergency_override: bool = False

    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ComponentWeights:
    """Dynamic weights for each component (6 components: theme, technical, AI, sentiment, earnings, institutional)."""
    theme: float = 0.26
    technical: float = 0.22
    ai: float = 0.22
    sentiment: float = 0.18
    earnings: float = 0.05  # Component #38: Earnings Intelligence (start small)
    institutional: float = 0.07  # Component #40: Institutional Flow (smart money)

    # Confidence in these weights
    confidence: float = 0.5  # 0-1, starts at 0.5 (uncertain)

    # Statistics
    sample_size: int = 0  # Number of trades used to learn these weights
    last_updated: datetime = field(default_factory=datetime.now)

    # Regime-specific weights
    regime: Optional[MarketRegimeType] = None

    def normalize(self):
        """Ensure weights sum to 1.0."""
        total = self.theme + self.technical + self.ai + self.sentiment + self.earnings + self.institutional
        if total > 0:
            self.theme /= total
            self.technical /= total
            self.ai /= total
            self.sentiment /= total
            self.earnings /= total
            self.institutional /= total

    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary for easy access."""
        return {
            'theme': self.theme,
            'technical': self.technical,
            'ai': self.ai,
            'sentiment': self.sentiment,
            'earnings': self.earnings,
            'institutional': self.institutional
        }


@dataclass
class DecisionRecord:
    """Record of a trading decision made by the brain."""
    decision_id: str  # Unique identifier
    ticker: str
    timestamp: datetime

    # Decision details
    action: str  # buy, sell, hold, pass
    position_size: float  # 0-100% of available capital
    conviction: float  # 0-1

    # Component scores at decision time
    component_scores: ComponentScores

    # Market context
    market_context: MarketContext

    # Weights used for this decision
    weights_used: ComponentWeights

    # Final computed scores
    overall_score: float  # 0-10
    signal_quality: str  # excellent, good, fair, poor
    setup_complete: bool

    # Reasoning
    ai_reasoning: Optional[str] = None

    # Entry details
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None

    # Metadata
    learner_type: Optional[LearnerType] = None
    regime_at_decision: Optional[MarketRegimeType] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class TradeRecord:
    """Complete record of a trade from decision to outcome."""
    trade_id: str
    decision_id: str  # Links back to decision

    # Basic info
    ticker: str
    entry_date: datetime
    exit_date: Optional[datetime] = None

    # Prices
    entry_price: float = 0.0
    exit_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None

    # Position details
    shares: int = 0
    position_size_pct: float = 0.0  # % of account

    # Outcome
    outcome: TradeOutcome = TradeOutcome.OPEN
    pnl_dollars: Optional[float] = None
    pnl_pct: Optional[float] = None

    # Performance metrics
    days_held: Optional[int] = None
    max_favorable_excursion: Optional[float] = None  # Best unrealized gain
    max_adverse_excursion: Optional[float] = None  # Worst unrealized loss

    # Context
    component_scores: ComponentScores = field(default_factory=ComponentScores)
    market_context: MarketContext = field(default_factory=MarketContext)
    weights_used: ComponentWeights = field(default_factory=ComponentWeights)

    # Exit reason
    exit_reason: Optional[str] = None  # stop_hit, target_hit, time_stop, manual

    # Attribution - which components were most responsible
    attribution: Dict[str, float] = field(default_factory=dict)

    def calculate_outcome(self):
        """Calculate trade outcome metrics."""
        if self.exit_price and self.entry_price:
            self.pnl_pct = ((self.exit_price - self.entry_price) / self.entry_price) * 100
            self.pnl_dollars = (self.exit_price - self.entry_price) * self.shares

            # Classify outcome
            if self.pnl_pct > 1.0:
                self.outcome = TradeOutcome.WIN
            elif self.pnl_pct < -1.0:
                self.outcome = TradeOutcome.LOSS
            else:
                self.outcome = TradeOutcome.BREAKEVEN

        if self.exit_date and self.entry_date:
            self.days_held = (self.exit_date - self.entry_date).days

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class LearningMetrics:
    """Metrics tracking learning progress."""
    # Overall performance
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0

    # Returns
    total_return_pct: float = 0.0
    avg_win_pct: float = 0.0
    avg_loss_pct: float = 0.0
    profit_factor: float = 0.0

    # Risk metrics
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    max_drawdown_pct: float = 0.0
    current_drawdown_pct: float = 0.0

    # Component performance
    component_attribution: Dict[str, float] = field(default_factory=dict)
    best_performing_component: Optional[str] = None
    worst_performing_component: Optional[str] = None

    # Regime performance
    performance_by_regime: Dict[str, Dict[str, float]] = field(default_factory=dict)
    best_regime: Optional[MarketRegimeType] = None

    # Learning progress
    current_weights: ComponentWeights = field(default_factory=ComponentWeights)
    weight_evolution: List[Dict[str, Any]] = field(default_factory=list)

    # Timestamps
    last_updated: datetime = field(default_factory=datetime.now)
    learning_start_date: datetime = field(default_factory=datetime.now)

    def update_from_trades(self, trades: List[TradeRecord]):
        """Update metrics from a list of completed trades."""
        if not trades:
            return

        closed_trades = [t for t in trades if t.outcome != TradeOutcome.OPEN]
        if not closed_trades:
            return

        self.total_trades = len(closed_trades)
        self.winning_trades = sum(1 for t in closed_trades if t.outcome == TradeOutcome.WIN)
        self.losing_trades = sum(1 for t in closed_trades if t.outcome == TradeOutcome.LOSS)
        self.win_rate = self.winning_trades / self.total_trades if self.total_trades > 0 else 0.0

        # Calculate returns
        wins = [t.pnl_pct for t in closed_trades if t.outcome == TradeOutcome.WIN and t.pnl_pct]
        losses = [t.pnl_pct for t in closed_trades if t.outcome == TradeOutcome.LOSS and t.pnl_pct]

        self.avg_win_pct = sum(wins) / len(wins) if wins else 0.0
        self.avg_loss_pct = sum(losses) / len(losses) if losses else 0.0

        total_wins = sum(wins) if wins else 0.0
        total_losses = abs(sum(losses)) if losses else 0.0
        self.profit_factor = total_wins / total_losses if total_losses > 0 else (float('inf') if total_wins > 0 else 0.0)

        # Total return
        all_returns = [t.pnl_pct for t in closed_trades if t.pnl_pct]
        self.total_return_pct = sum(all_returns) if all_returns else 0.0

        # Calculate Sharpe ratio (simplified - assumes 0 risk-free rate)
        if all_returns:
            import numpy as np
            returns_array = np.array(all_returns)
            mean_return = np.mean(returns_array)
            std_return = np.std(returns_array)
            self.sharpe_ratio = (mean_return / std_return) if std_return > 0 else 0.0

        self.last_updated = datetime.now()


@dataclass
class RegimeState:
    """Current market regime state."""
    current_regime: MarketRegimeType = MarketRegimeType.UNKNOWN
    confidence: float = 0.0

    # Regime probabilities
    regime_probabilities: Dict[MarketRegimeType, float] = field(default_factory=dict)

    # Regime history
    regime_changes: List[Dict[str, Any]] = field(default_factory=list)
    last_change: Optional[datetime] = None

    # Optimal weights for current regime
    optimal_weights: Optional[ComponentWeights] = None

    timestamp: datetime = field(default_factory=datetime.now)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def create_decision_id(ticker: str, timestamp: datetime) -> str:
    """Generate unique decision ID."""
    return f"DEC_{ticker}_{timestamp.strftime('%Y%m%d_%H%M%S_%f')}"


def create_trade_id(ticker: str, timestamp: datetime) -> str:
    """Generate unique trade ID."""
    return f"TRD_{ticker}_{timestamp.strftime('%Y%m%d_%H%M%S_%f')}"


class LearningDataEncoder(json.JSONEncoder):
    """Custom JSON encoder for learning data models."""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, Enum):
            return obj.value
        if hasattr(obj, 'to_dict'):
            return obj.to_dict()
        if hasattr(obj, '__dict__'):
            return asdict(obj)
        return super().default(obj)


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    # Test data models
    print("Testing data models...")

    # Create component scores
    scores = ComponentScores(
        theme_score=8.5,
        technical_score=7.2,
        ai_confidence=0.85,
        x_sentiment_score=0.6
    )

    # Create market context
    context = MarketContext(
        regime=MarketRegimeType.BULL_MOMENTUM,
        regime_confidence=0.8,
        spy_change_pct=1.2,
        vix_level=15.5
    )

    # Create weights
    weights = ComponentWeights()
    print(f"Default weights: {weights.to_dict()}")

    # Create decision record
    decision = DecisionRecord(
        decision_id=create_decision_id("NVDA", datetime.now()),
        ticker="NVDA",
        timestamp=datetime.now(),
        action="buy",
        position_size=15.0,
        conviction=0.85,
        component_scores=scores,
        market_context=context,
        weights_used=weights,
        overall_score=8.2,
        signal_quality="excellent",
        setup_complete=True,
        entry_price=850.00
    )

    print(f"\nDecision created: {decision.decision_id}")
    print(f"Action: {decision.action} {decision.ticker}")
    print(f"Overall Score: {decision.overall_score}/10")

    # Create trade record
    trade = TradeRecord(
        trade_id=create_trade_id("NVDA", datetime.now()),
        decision_id=decision.decision_id,
        ticker="NVDA",
        entry_date=datetime.now(),
        entry_price=850.00,
        shares=100,
        position_size_pct=15.0,
        component_scores=scores,
        market_context=context,
        weights_used=weights
    )

    print(f"\nTrade created: {trade.trade_id}")
    print(f"Status: {trade.outcome}")

    # Simulate trade completion
    trade.exit_price = 875.00
    trade.exit_date = datetime.now()
    trade.calculate_outcome()

    print(f"Trade closed: {trade.outcome}")
    print(f"P&L: {trade.pnl_pct:.2f}%")

    # Create metrics
    metrics = LearningMetrics()
    metrics.update_from_trades([trade])

    print(f"\nLearning Metrics:")
    print(f"Total Trades: {metrics.total_trades}")
    print(f"Win Rate: {metrics.win_rate:.1%}")
    print(f"Sharpe Ratio: {metrics.sharpe_ratio:.2f}")

    print("\n✅ All data models working correctly!")
