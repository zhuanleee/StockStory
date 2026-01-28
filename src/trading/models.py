"""
Core Data Models for Trade Management System

Story-First Philosophy:
- Stories drive markets, technicals only confirm
- Exit signals weighted: Story (50%) → AI (35%) → Technical (15%)
- Confidence levels determine urgency of action
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Dict, Optional, Any
import uuid


class TradeStatus(Enum):
    """Trade lifecycle status."""
    WATCHING = "watching"      # On watchlist, not entered
    OPEN = "open"              # Active position
    SCALING_IN = "scaling_in"  # Building position
    SCALING_OUT = "scaling_out"  # Reducing position
    CLOSED = "closed"          # Fully exited


class SignalSource(Enum):
    """Source of exit/entry signal."""
    STORY = "story"            # Theme lifecycle, catalyst status
    AI = "ai"                  # AI thesis validation
    TECHNICAL = "technical"    # Price action, indicators


class RiskLevel(Enum):
    """Confidence-based risk levels for advisory."""
    CRITICAL = "critical"      # 90-100%: Exit immediately
    HIGH = "high"              # 75-89%: Strong exit signal
    ELEVATED = "elevated"      # 60-74%: Consider reducing
    MODERATE = "moderate"      # 40-59%: Monitor closely
    LOW = "low"                # 20-39%: Normal monitoring
    NONE = "none"              # 0-19%: No action needed

    @classmethod
    def from_confidence(cls, confidence: float) -> 'RiskLevel':
        """Get risk level from confidence score (0-100)."""
        if confidence >= 90:
            return cls.CRITICAL
        elif confidence >= 75:
            return cls.HIGH
        elif confidence >= 60:
            return cls.ELEVATED
        elif confidence >= 40:
            return cls.MODERATE
        elif confidence >= 20:
            return cls.LOW
        else:
            return cls.NONE


class ScalingStrategy(Enum):
    """Pre-built scaling strategies."""
    CONSERVATIVE = "conservative"      # Scale slowly, tight stops
    AGGRESSIVE_PYRAMID = "aggressive"  # Front-load, pyramid up
    CORE_TRADE = "core_trade"          # 60% core + 40% trading
    MOMENTUM_RIDER = "momentum"        # Add on strength only


@dataclass
class Tranche:
    """
    Individual transaction within a trade.
    Tracks each buy/sell with full context.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    action: str = "buy"  # "buy" or "sell"
    shares: int = 0
    price: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

    # Context at time of transaction
    reason: str = ""  # Why this action was taken
    story_score: Optional[float] = None
    ai_confidence: Optional[float] = None
    technical_score: Optional[float] = None

    # Market context
    market_regime: str = ""  # bull_trending, bear_volatile, range_bound
    spy_change: Optional[float] = None
    vix_level: Optional[float] = None

    # Cost tracking
    commission: float = 0.0

    @property
    def value(self) -> float:
        """Total value of this tranche."""
        return self.shares * self.price

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'action': self.action,
            'shares': self.shares,
            'price': self.price,
            'timestamp': self.timestamp.isoformat(),
            'reason': self.reason,
            'story_score': self.story_score,
            'ai_confidence': self.ai_confidence,
            'technical_score': self.technical_score,
            'market_regime': self.market_regime,
            'spy_change': self.spy_change,
            'vix_level': self.vix_level,
            'commission': self.commission,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Tranche':
        """Create from dictionary."""
        data = data.copy()
        if isinstance(data.get('timestamp'), str):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


@dataclass
class ExitSignal:
    """
    Exit signal with source and confidence.
    Weighted: Story (50%) → AI (35%) → Technical (15%)
    """
    source: SignalSource
    signal_type: str  # e.g., "theme_peaked", "thesis_broken", "ma_break"
    confidence: float  # 0-100
    description: str
    timestamp: datetime = field(default_factory=datetime.now)

    # Recommended action
    action: str = "hold"  # "hold", "reduce", "exit"
    suggested_size: Optional[float] = None  # % of position to exit

    # Supporting data
    data: Dict[str, Any] = field(default_factory=dict)

    @property
    def risk_level(self) -> RiskLevel:
        """Get risk level based on confidence."""
        return RiskLevel.from_confidence(self.confidence)

    @property
    def weight(self) -> float:
        """Get signal weight based on source."""
        weights = {
            SignalSource.STORY: 0.50,
            SignalSource.AI: 0.35,
            SignalSource.TECHNICAL: 0.15,
        }
        return weights.get(self.source, 0.0)

    @property
    def weighted_confidence(self) -> float:
        """Confidence weighted by source importance."""
        return self.confidence * self.weight

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'source': self.source.value,
            'signal_type': self.signal_type,
            'confidence': self.confidence,
            'description': self.description,
            'timestamp': self.timestamp.isoformat(),
            'action': self.action,
            'suggested_size': self.suggested_size,
            'data': self.data,
            'risk_level': self.risk_level.value,
            'weighted_confidence': self.weighted_confidence,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExitSignal':
        """Create from dictionary."""
        data = data.copy()
        data['source'] = SignalSource(data['source'])
        if isinstance(data.get('timestamp'), str):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        # Remove computed fields
        data.pop('risk_level', None)
        data.pop('weighted_confidence', None)
        return cls(**data)


@dataclass
class ScalingPlan:
    """
    Scaling strategy configuration for a trade.
    """
    strategy: ScalingStrategy = ScalingStrategy.CONSERVATIVE

    # Position sizing
    max_position_pct: float = 5.0  # Max % of portfolio
    initial_size_pct: float = 25.0  # % of max to start with

    # Scale-in triggers
    scale_in_triggers: List[str] = field(default_factory=lambda: [
        "thesis_confirmed",
        "theme_accelerating",
        "catalyst_confirmed"
    ])
    scale_in_increment: float = 25.0  # % of max per add
    max_scale_ins: int = 3

    # Scale-out triggers
    scale_out_triggers: List[str] = field(default_factory=lambda: [
        "profit_target_1",
        "profit_target_2",
        "story_weakening"
    ])
    scale_out_increments: List[float] = field(default_factory=lambda: [25.0, 25.0, 50.0])

    # Profit targets (% gain)
    profit_targets: List[float] = field(default_factory=lambda: [10.0, 20.0, 30.0])

    # Stop loss
    stop_loss_pct: float = 8.0  # Hard stop
    trailing_stop_pct: Optional[float] = None  # Trailing stop after first target

    # Story-based overrides
    story_override_enabled: bool = True  # Exit early if story breaks
    ignore_technicals_if_story_strong: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'strategy': self.strategy.value,
            'max_position_pct': self.max_position_pct,
            'initial_size_pct': self.initial_size_pct,
            'scale_in_triggers': self.scale_in_triggers,
            'scale_in_increment': self.scale_in_increment,
            'max_scale_ins': self.max_scale_ins,
            'scale_out_triggers': self.scale_out_triggers,
            'scale_out_increments': self.scale_out_increments,
            'profit_targets': self.profit_targets,
            'stop_loss_pct': self.stop_loss_pct,
            'trailing_stop_pct': self.trailing_stop_pct,
            'story_override_enabled': self.story_override_enabled,
            'ignore_technicals_if_story_strong': self.ignore_technicals_if_story_strong,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ScalingPlan':
        """Create from dictionary."""
        data = data.copy()
        data['strategy'] = ScalingStrategy(data['strategy'])
        return cls(**data)

    @classmethod
    def get_preset(cls, strategy: ScalingStrategy) -> 'ScalingPlan':
        """Get pre-configured scaling plan for a strategy."""
        presets = {
            ScalingStrategy.CONSERVATIVE: cls(
                strategy=ScalingStrategy.CONSERVATIVE,
                initial_size_pct=25.0,
                scale_in_increment=15.0,
                max_scale_ins=4,
                profit_targets=[8.0, 15.0, 25.0],
                stop_loss_pct=5.0,
                trailing_stop_pct=3.0,
            ),
            ScalingStrategy.AGGRESSIVE_PYRAMID: cls(
                strategy=ScalingStrategy.AGGRESSIVE_PYRAMID,
                initial_size_pct=50.0,
                scale_in_increment=25.0,
                max_scale_ins=2,
                profit_targets=[15.0, 30.0, 50.0],
                stop_loss_pct=10.0,
            ),
            ScalingStrategy.CORE_TRADE: cls(
                strategy=ScalingStrategy.CORE_TRADE,
                initial_size_pct=60.0,  # Core position
                scale_in_increment=20.0,  # Trading portion
                max_scale_ins=2,
                profit_targets=[10.0, 20.0],  # Trade portion targets
                stop_loss_pct=8.0,
                scale_out_increments=[50.0, 50.0],  # Only trade portion
            ),
            ScalingStrategy.MOMENTUM_RIDER: cls(
                strategy=ScalingStrategy.MOMENTUM_RIDER,
                initial_size_pct=33.0,
                scale_in_increment=33.0,
                max_scale_ins=2,
                scale_in_triggers=["new_high", "volume_surge", "theme_momentum"],
                profit_targets=[20.0, 40.0, 60.0],
                stop_loss_pct=12.0,
                trailing_stop_pct=8.0,
            ),
        }
        return presets.get(strategy, cls())


@dataclass
class Trade:
    """
    Complete trade record with multi-tranche support.
    Tracks full lifecycle from watchlist to closed.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    ticker: str = ""
    status: TradeStatus = TradeStatus.WATCHING

    # Thesis (the story)
    thesis: str = ""  # Why you're in this trade
    theme: str = ""  # Associated theme (e.g., "AI Infrastructure")
    catalyst: str = ""  # Expected catalyst
    catalyst_date: Optional[datetime] = None

    # Tranches
    tranches: List[Tranche] = field(default_factory=list)

    # Scaling
    scaling_plan: ScalingPlan = field(default_factory=ScalingPlan)
    scale_ins_used: int = 0
    scale_outs_used: int = 0

    # Exit signals
    exit_signals: List[ExitSignal] = field(default_factory=list)

    # Tracking
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    closed_at: Optional[datetime] = None

    # Notes
    notes: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    # Scores (latest)
    latest_story_score: Optional[float] = None
    latest_ai_confidence: Optional[float] = None
    latest_technical_score: Optional[float] = None
    latest_composite_score: Optional[float] = None

    @property
    def total_shares(self) -> int:
        """Calculate current position size."""
        buys = sum(t.shares for t in self.tranches if t.action == "buy")
        sells = sum(t.shares for t in self.tranches if t.action == "sell")
        return buys - sells

    @property
    def average_cost(self) -> float:
        """Calculate average cost basis."""
        total_cost = 0.0
        total_shares = 0
        for t in self.tranches:
            if t.action == "buy":
                total_cost += t.shares * t.price
                total_shares += t.shares
        return total_cost / total_shares if total_shares > 0 else 0.0

    @property
    def total_invested(self) -> float:
        """Total amount invested (all buys)."""
        return sum(t.value + t.commission for t in self.tranches if t.action == "buy")

    @property
    def total_returned(self) -> float:
        """Total amount returned (all sells)."""
        return sum(t.value - t.commission for t in self.tranches if t.action == "sell")

    @property
    def realized_pnl(self) -> float:
        """Realized P&L from closed tranches."""
        if not any(t.action == "sell" for t in self.tranches):
            return 0.0
        # Simple FIFO calculation
        sells_value = sum(t.value for t in self.tranches if t.action == "sell")
        sells_shares = sum(t.shares for t in self.tranches if t.action == "sell")
        avg_cost = self.average_cost
        return sells_value - (sells_shares * avg_cost)

    @property
    def unrealized_pnl(self, current_price: float = None) -> float:
        """Unrealized P&L at current price."""
        # Note: current_price needs to be provided when calling
        return 0.0  # Placeholder - calculated externally

    @property
    def is_open(self) -> bool:
        """Check if trade has open position."""
        return self.total_shares > 0

    @property
    def days_held(self) -> int:
        """Days since first entry."""
        if not self.tranches:
            return 0
        first_buy = min(
            (t.timestamp for t in self.tranches if t.action == "buy"),
            default=datetime.now()
        )
        end_date = self.closed_at or datetime.now()
        return (end_date - first_buy).days

    @property
    def composite_exit_confidence(self) -> float:
        """
        Calculate weighted composite exit confidence.
        Story (50%) → AI (35%) → Technical (15%)
        """
        if not self.exit_signals:
            return 0.0

        # Get latest signal from each source
        latest_by_source = {}
        for signal in sorted(self.exit_signals, key=lambda s: s.timestamp):
            latest_by_source[signal.source] = signal

        # Calculate weighted sum
        total_confidence = 0.0
        for source, signal in latest_by_source.items():
            total_confidence += signal.weighted_confidence

        return min(total_confidence, 100.0)

    @property
    def current_risk_level(self) -> RiskLevel:
        """Get current risk level based on composite exit confidence."""
        return RiskLevel.from_confidence(self.composite_exit_confidence)

    def add_tranche(self, tranche: Tranche) -> None:
        """Add a transaction to the trade."""
        self.tranches.append(tranche)
        self.updated_at = datetime.now()

        if tranche.action == "buy" and self.status == TradeStatus.WATCHING:
            self.status = TradeStatus.OPEN
        elif tranche.action == "buy":
            self.scale_ins_used += 1
        elif tranche.action == "sell":
            self.scale_outs_used += 1
            if self.total_shares <= 0:
                self.status = TradeStatus.CLOSED
                self.closed_at = datetime.now()

    def add_exit_signal(self, signal: ExitSignal) -> None:
        """Add an exit signal to the trade."""
        self.exit_signals.append(signal)
        self.updated_at = datetime.now()

    def add_note(self, note: str) -> None:
        """Add a note to the trade."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.notes.append(f"[{timestamp}] {note}")
        self.updated_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'ticker': self.ticker,
            'status': self.status.value,
            'thesis': self.thesis,
            'theme': self.theme,
            'catalyst': self.catalyst,
            'catalyst_date': self.catalyst_date.isoformat() if self.catalyst_date else None,
            'tranches': [t.to_dict() for t in self.tranches],
            'scaling_plan': self.scaling_plan.to_dict(),
            'scale_ins_used': self.scale_ins_used,
            'scale_outs_used': self.scale_outs_used,
            'exit_signals': [s.to_dict() for s in self.exit_signals],
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'closed_at': self.closed_at.isoformat() if self.closed_at else None,
            'notes': self.notes,
            'tags': self.tags,
            'latest_story_score': self.latest_story_score,
            'latest_ai_confidence': self.latest_ai_confidence,
            'latest_technical_score': self.latest_technical_score,
            'latest_composite_score': self.latest_composite_score,
            # Computed properties
            'total_shares': self.total_shares,
            'average_cost': self.average_cost,
            'days_held': self.days_held,
            'composite_exit_confidence': self.composite_exit_confidence,
            'current_risk_level': self.current_risk_level.value,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Trade':
        """Create from dictionary."""
        data = data.copy()

        # Convert enums
        data['status'] = TradeStatus(data['status'])

        # Convert datetime fields
        for field_name in ['catalyst_date', 'created_at', 'updated_at', 'closed_at']:
            if data.get(field_name) and isinstance(data[field_name], str):
                data[field_name] = datetime.fromisoformat(data[field_name])

        # Convert nested objects
        data['tranches'] = [Tranche.from_dict(t) for t in data.get('tranches', [])]
        data['scaling_plan'] = ScalingPlan.from_dict(data.get('scaling_plan', {}))
        data['exit_signals'] = [ExitSignal.from_dict(s) for s in data.get('exit_signals', [])]

        # Remove computed properties
        for prop in ['total_shares', 'average_cost', 'days_held',
                     'composite_exit_confidence', 'current_risk_level']:
            data.pop(prop, None)

        return cls(**data)
