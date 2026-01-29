#!/usr/bin/env python3
"""
Exit Strategy Analyzer
======================
Dynamic exit targets and alerts using all 38 components.

Features:
- Multi-component exit signal detection
- Dynamic price target calculation (bull/base/bear cases)
- Exit urgency scoring (1-10)
- Component-based exit reasons
- Real-time degradation monitoring
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
import json
from pathlib import Path

from src.utils import get_logger

logger = get_logger(__name__)


class ExitReason(Enum):
    """Exit signal reasons."""
    PROFIT_TARGET = "profit_target"
    TECHNICAL_BREAKDOWN = "technical_breakdown"
    CATALYST_EXPIRED = "catalyst_expired"
    SENTIMENT_DETERIORATION = "sentiment_deterioration"
    THEME_WEAKNESS = "theme_weakness"
    RISK_MANAGEMENT = "risk_management"
    COMPONENT_DEGRADATION = "component_degradation"
    AI_RECOMMENDATION = "ai_recommendation"
    EARNINGS_RISK = "earnings_risk"
    INSTITUTIONAL_EXIT = "institutional_exit"


class ExitUrgency(Enum):
    """Exit urgency levels."""
    NONE = 0           # No exit needed
    LOW = 3            # Consider exit, no rush
    MODERATE = 5       # Exit soon, within 1-2 days
    HIGH = 7           # Exit today
    CRITICAL = 9       # Exit immediately
    EMERGENCY = 10     # Exit at market, urgent


@dataclass
class PriceTarget:
    """Dynamic price target with confidence."""
    target: float
    confidence: float  # 0-1
    timeframe_days: int
    reasoning: str
    components_supporting: List[str]


@dataclass
class ExitSignal:
    """Exit signal with detailed reasoning."""
    ticker: str
    urgency: ExitUrgency
    reason: ExitReason
    current_price: float
    entry_price: float
    current_pnl_pct: float

    # Exit targets
    immediate_exit: bool
    target_exit_price: Optional[float]
    stop_loss_price: Optional[float]

    # Component breakdown
    components_degraded: List[str]  # Components showing weakness
    component_scores: Dict[str, float]  # Current scores
    component_changes: Dict[str, float]  # Change since entry

    # Reasoning
    primary_reason: str
    detailed_analysis: str
    confidence: float  # 0-1

    # Recommendations
    recommended_action: str
    alternative_actions: List[str]

    timestamp: datetime


@dataclass
class ExitAnalysis:
    """Complete exit analysis for a position."""
    ticker: str

    # Current state
    current_price: float
    entry_price: float
    current_pnl_pct: float
    holding_days: int

    # Price targets (dynamic)
    bull_target: PriceTarget
    base_target: PriceTarget
    bear_target: PriceTarget
    current_target: float  # Active target based on conditions

    # Risk levels
    stop_loss: float
    trailing_stop: float
    max_acceptable_loss_pct: float

    # Exit signals
    exit_signals: List[ExitSignal]
    highest_urgency: ExitUrgency
    should_exit: bool

    # Component health
    overall_health_score: float  # 0-100
    component_health: Dict[str, float]  # Individual component scores
    degradation_rate: float  # How fast it's degrading

    # Recommendations
    recommended_action: str
    action_timeframe: str  # "immediate", "today", "this_week", "monitor"

    timestamp: datetime


class ExitAnalyzer:
    """
    Analyzes positions and generates exit signals using all 38 components.

    38 Components Utilized:

    CATEGORY 1: TECHNICAL (8 components)
    1. Price momentum (MA crossovers, trend strength)
    2. Volume profile (OBV, volume trends)
    3. Relative strength (RS vs SPY)
    4. Support/resistance levels
    5. Volatility (ATR, Bollinger Bands)
    6. Price patterns (breakouts, breakdowns)
    7. Moving average health (20/50/200 day)
    8. MACD signals

    CATEGORY 2: SENTIMENT (6 components)
    9. X/Twitter sentiment
    10. Reddit sentiment
    11. StockTwits sentiment
    12. Sentiment trend direction
    13. Viral post activity
    14. Social volume changes

    CATEGORY 3: THEME/CATALYST (8 components)
    15. Theme strength score
    16. Theme leadership position
    17. Supply chain relationships
    18. Catalyst freshness
    19. Narrative consistency
    20. Sector rotation signals
    21. Related stocks performance
    22. Theme concentration risk

    CATEGORY 4: AI ANALYSIS (4 components)
    23. AI conviction score
    24. AI risk assessment
    25. AI opportunity score
    26. AI pattern recognition

    CATEGORY 5: EARNINGS (4 components)
    27. Earnings call transcript tone
    28. Guidance direction
    29. Beat/miss rate
    30. Earnings surprise trend

    CATEGORY 6: INSTITUTIONAL (4 components)
    31. Institutional ownership changes
    32. Dark pool activity
    33. Options flow (call/put ratio)
    34. Smart money indicators

    CATEGORY 7: FUNDAMENTAL (4 components)
    35. Revenue growth trajectory
    36. Margin trends
    37. Valuation metrics vs peers
    38. Insider trading activity
    """

    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.component_weights = self._initialize_weights()

        # Exit thresholds
        self.DEGRADATION_THRESHOLD = 0.7  # Exit if overall score drops below 70%
        self.COMPONENT_FAIL_THRESHOLD = 0.5  # Component considered failed
        self.CRITICAL_COMPONENT_COUNT = 3  # Exit if 3+ critical components fail

        # Target calculation parameters
        self.BULL_MULTIPLIER = 1.5  # 50% upside for bull case
        self.BASE_MULTIPLIER = 1.2  # 20% upside for base case
        self.BEAR_MULTIPLIER = 1.05  # 5% upside for bear case

        logger.info("Exit Analyzer initialized with 38-component analysis")

    def _initialize_weights(self) -> Dict[str, float]:
        """Initialize component weights for exit analysis."""
        return {
            # Technical (higher weight for exits)
            'price_momentum': 0.08,
            'volume_profile': 0.06,
            'relative_strength': 0.07,
            'support_resistance': 0.06,
            'volatility': 0.05,
            'price_patterns': 0.07,
            'ma_health': 0.06,
            'macd_signals': 0.05,

            # Sentiment (moderate weight)
            'x_sentiment': 0.05,
            'reddit_sentiment': 0.03,
            'stocktwits_sentiment': 0.03,
            'sentiment_trend': 0.04,
            'viral_activity': 0.03,
            'social_volume': 0.03,

            # Theme/Catalyst (high weight)
            'theme_strength': 0.06,
            'theme_leadership': 0.05,
            'supply_chain': 0.04,
            'catalyst_freshness': 0.06,
            'narrative_consistency': 0.04,
            'sector_rotation': 0.04,
            'related_performance': 0.03,
            'theme_concentration': 0.02,

            # AI (moderate weight)
            'ai_conviction': 0.04,
            'ai_risk': 0.03,
            'ai_opportunity': 0.03,
            'ai_patterns': 0.02,

            # Earnings (moderate weight)
            'earnings_tone': 0.03,
            'guidance': 0.04,
            'beat_rate': 0.02,
            'surprise_trend': 0.02,

            # Institutional (high weight for exits)
            'institutional_ownership': 0.05,
            'dark_pool': 0.04,
            'options_flow': 0.04,
            'smart_money': 0.04,

            # Fundamental (moderate weight)
            'revenue_growth': 0.03,
            'margin_trends': 0.02,
            'valuation': 0.02,
            'insider_trading': 0.04,
        }

    def analyze_exit(
        self,
        ticker: str,
        entry_price: float,
        entry_date: datetime,
        current_price: float,
        component_data: Dict,
        position_size: float = None
    ) -> ExitAnalysis:
        """
        Comprehensive exit analysis using all 38 components.

        Args:
            ticker: Stock ticker
            entry_price: Entry price
            entry_date: Entry date
            current_price: Current price
            component_data: Data from all 38 components
            position_size: Position size (for risk calculation)

        Returns:
            Complete exit analysis with targets and signals
        """
        # Calculate current state
        holding_days = (datetime.now() - entry_date).days
        current_pnl_pct = ((current_price - entry_price) / entry_price) * 100

        # Analyze component health
        component_health = self._analyze_component_health(component_data)
        overall_health = self._calculate_overall_health(component_health)
        degradation_rate = self._calculate_degradation_rate(
            component_data.get('historical_scores', {})
        )

        # Calculate dynamic price targets
        bull_target = self._calculate_bull_target(
            ticker, current_price, component_data
        )
        base_target = self._calculate_base_target(
            ticker, current_price, component_data
        )
        bear_target = self._calculate_bear_target(
            ticker, current_price, component_data
        )

        # Select active target based on conditions
        current_target = self._select_active_target(
            overall_health, bull_target, base_target, bear_target
        )

        # Calculate risk levels
        stop_loss = self._calculate_stop_loss(
            entry_price, current_price, component_data
        )
        trailing_stop = self._calculate_trailing_stop(
            entry_price, current_price, current_pnl_pct
        )

        # Generate exit signals
        exit_signals = self._generate_exit_signals(
            ticker=ticker,
            current_price=current_price,
            entry_price=entry_price,
            current_pnl_pct=current_pnl_pct,
            component_health=component_health,
            component_data=component_data,
            overall_health=overall_health,
            stop_loss=stop_loss,
        )

        # Determine highest urgency
        highest_urgency = max(
            [s.urgency for s in exit_signals],
            default=ExitUrgency.NONE
        )

        # Should exit decision
        should_exit = self._should_exit(
            exit_signals, overall_health, current_pnl_pct
        )

        # Generate recommendations
        recommended_action, action_timeframe = self._generate_recommendation(
            should_exit, highest_urgency, exit_signals, current_pnl_pct
        )

        return ExitAnalysis(
            ticker=ticker,
            current_price=current_price,
            entry_price=entry_price,
            current_pnl_pct=current_pnl_pct,
            holding_days=holding_days,
            bull_target=bull_target,
            base_target=base_target,
            bear_target=bear_target,
            current_target=current_target,
            stop_loss=stop_loss,
            trailing_stop=trailing_stop,
            max_acceptable_loss_pct=-7.0,  # Max 7% loss
            exit_signals=exit_signals,
            highest_urgency=highest_urgency,
            should_exit=should_exit,
            overall_health_score=overall_health,
            component_health=component_health,
            degradation_rate=degradation_rate,
            recommended_action=recommended_action,
            action_timeframe=action_timeframe,
            timestamp=datetime.now()
        )

    def _analyze_component_health(
        self, component_data: Dict
    ) -> Dict[str, float]:
        """Analyze health of each component (0-100 scale)."""
        health = {}

        # Technical components
        health['price_momentum'] = self._score_price_momentum(component_data)
        health['volume_profile'] = self._score_volume_profile(component_data)
        health['relative_strength'] = self._score_relative_strength(component_data)
        health['support_resistance'] = self._score_support_resistance(component_data)
        health['volatility'] = self._score_volatility(component_data)
        health['price_patterns'] = self._score_price_patterns(component_data)
        health['ma_health'] = self._score_ma_health(component_data)
        health['macd_signals'] = self._score_macd(component_data)

        # Sentiment components
        health['x_sentiment'] = self._score_x_sentiment(component_data)
        health['reddit_sentiment'] = self._score_reddit_sentiment(component_data)
        health['stocktwits_sentiment'] = self._score_stocktwits_sentiment(component_data)
        health['sentiment_trend'] = self._score_sentiment_trend(component_data)
        health['viral_activity'] = self._score_viral_activity(component_data)
        health['social_volume'] = self._score_social_volume(component_data)

        # Theme components
        health['theme_strength'] = self._score_theme_strength(component_data)
        health['theme_leadership'] = self._score_theme_leadership(component_data)
        health['supply_chain'] = self._score_supply_chain(component_data)
        health['catalyst_freshness'] = self._score_catalyst_freshness(component_data)
        health['narrative_consistency'] = self._score_narrative(component_data)
        health['sector_rotation'] = self._score_sector_rotation(component_data)
        health['related_performance'] = self._score_related_performance(component_data)
        health['theme_concentration'] = self._score_theme_concentration(component_data)

        # AI components
        health['ai_conviction'] = self._score_ai_conviction(component_data)
        health['ai_risk'] = self._score_ai_risk(component_data)
        health['ai_opportunity'] = self._score_ai_opportunity(component_data)
        health['ai_patterns'] = self._score_ai_patterns(component_data)

        # Earnings components
        health['earnings_tone'] = self._score_earnings_tone(component_data)
        health['guidance'] = self._score_guidance(component_data)
        health['beat_rate'] = self._score_beat_rate(component_data)
        health['surprise_trend'] = self._score_surprise_trend(component_data)

        # Institutional components
        health['institutional_ownership'] = self._score_institutional(component_data)
        health['dark_pool'] = self._score_dark_pool(component_data)
        health['options_flow'] = self._score_options_flow(component_data)
        health['smart_money'] = self._score_smart_money(component_data)

        # Fundamental components
        health['revenue_growth'] = self._score_revenue_growth(component_data)
        health['margin_trends'] = self._score_margin_trends(component_data)
        health['valuation'] = self._score_valuation(component_data)
        health['insider_trading'] = self._score_insider_trading(component_data)

        return health

    def _calculate_overall_health(self, component_health: Dict[str, float]) -> float:
        """Calculate weighted overall health score."""
        total_score = 0.0
        total_weight = 0.0

        for component, score in component_health.items():
            weight = self.component_weights.get(component, 0.0)
            total_score += score * weight
            total_weight += weight

        return (total_score / total_weight) if total_weight > 0 else 50.0

    def _calculate_degradation_rate(
        self, historical_scores: Dict
    ) -> float:
        """
        Calculate how fast the position is degrading.

        Returns:
            Degradation rate: positive = improving, negative = degrading
        """
        if not historical_scores or len(historical_scores) < 2:
            return 0.0

        # Get last 7 days of scores
        recent_scores = sorted(historical_scores.items())[-7:]
        if len(recent_scores) < 2:
            return 0.0

        # Linear regression slope
        scores = [s[1] for s in recent_scores]
        n = len(scores)

        # Simple slope calculation
        x_mean = (n - 1) / 2
        y_mean = sum(scores) / n

        numerator = sum((i - x_mean) * (scores[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))

        slope = numerator / denominator if denominator != 0 else 0.0

        return slope

    def _calculate_bull_target(
        self, ticker: str, current_price: float, component_data: Dict
    ) -> PriceTarget:
        """Calculate bull case target (everything goes right)."""
        # Bull case assumes all positive catalysts play out
        theme_multiplier = component_data.get('theme_strength', 50) / 50.0
        ai_multiplier = component_data.get('ai_conviction', 50) / 50.0
        earnings_multiplier = component_data.get('earnings_quality', 50) / 50.0

        avg_multiplier = (theme_multiplier + ai_multiplier + earnings_multiplier) / 3.0
        target_multiplier = self.BULL_MULTIPLIER * avg_multiplier

        target = current_price * target_multiplier
        confidence = min(0.95, avg_multiplier * 0.8)

        supporting = [
            comp for comp, score in component_data.items()
            if isinstance(score, (int, float)) and score > 70
        ]

        return PriceTarget(
            target=target,
            confidence=confidence,
            timeframe_days=90,
            reasoning="Bull case assumes strong theme continuation, positive earnings, and sustained momentum",
            components_supporting=supporting[:5]
        )

    def _calculate_base_target(
        self, ticker: str, current_price: float, component_data: Dict
    ) -> PriceTarget:
        """Calculate base case target (normal conditions)."""
        target = current_price * self.BASE_MULTIPLIER
        confidence = 0.7

        return PriceTarget(
            target=target,
            confidence=confidence,
            timeframe_days=60,
            reasoning="Base case assumes moderate continuation of current trends",
            components_supporting=["general_momentum", "sector_performance"]
        )

    def _calculate_bear_target(
        self, ticker: str, current_price: float, component_data: Dict
    ) -> PriceTarget:
        """Calculate bear case target (things weaken)."""
        target = current_price * self.BEAR_MULTIPLIER
        confidence = 0.5

        return PriceTarget(
            target=target,
            confidence=confidence,
            timeframe_days=30,
            reasoning="Bear case assumes weakening catalysts and rotation out of theme",
            components_supporting=[]
        )

    def _select_active_target(
        self,
        overall_health: float,
        bull_target: PriceTarget,
        base_target: PriceTarget,
        bear_target: PriceTarget
    ) -> float:
        """Select active target based on current health."""
        if overall_health >= 80:
            return bull_target.target
        elif overall_health >= 60:
            return base_target.target
        else:
            return bear_target.target

    def _calculate_stop_loss(
        self, entry_price: float, current_price: float, component_data: Dict
    ) -> float:
        """Calculate dynamic stop loss."""
        # Base stop at -7%
        base_stop = entry_price * 0.93

        # Adjust based on volatility
        volatility = component_data.get('volatility', 0.02)
        volatility_buffer = entry_price * (volatility * 2)

        # Wider stop for volatile stocks
        adjusted_stop = base_stop - volatility_buffer

        # Never below -10%
        min_stop = entry_price * 0.90

        return max(adjusted_stop, min_stop)

    def _calculate_trailing_stop(
        self, entry_price: float, current_price: float, current_pnl_pct: float
    ) -> float:
        """Calculate trailing stop based on profit."""
        if current_pnl_pct < 5:
            # No trailing stop until 5% profit
            return self._calculate_stop_loss(entry_price, current_price, {})
        elif current_pnl_pct < 15:
            # Trail at breakeven + 2%
            return entry_price * 1.02
        elif current_pnl_pct < 30:
            # Trail at +10%
            return entry_price * 1.10
        else:
            # Trail at +20% for big winners
            return entry_price * 1.20

    def _generate_exit_signals(
        self,
        ticker: str,
        current_price: float,
        entry_price: float,
        current_pnl_pct: float,
        component_health: Dict[str, float],
        component_data: Dict,
        overall_health: float,
        stop_loss: float
    ) -> List[ExitSignal]:
        """Generate all exit signals from components."""
        signals = []

        # Check stop loss
        if current_price <= stop_loss:
            signals.append(self._create_stop_loss_signal(
                ticker, current_price, entry_price, current_pnl_pct,
                stop_loss, component_health
            ))

        # Check technical breakdown
        if component_health.get('price_momentum', 100) < 40:
            signals.append(self._create_technical_breakdown_signal(
                ticker, current_price, entry_price, current_pnl_pct,
                component_health
            ))

        # Check catalyst expiration
        if component_health.get('catalyst_freshness', 100) < 30:
            signals.append(self._create_catalyst_expired_signal(
                ticker, current_price, entry_price, current_pnl_pct,
                component_health
            ))

        # Check sentiment deterioration
        sentiment_avg = sum([
            component_health.get('x_sentiment', 50),
            component_health.get('reddit_sentiment', 50),
            component_health.get('stocktwits_sentiment', 50)
        ]) / 3.0

        if sentiment_avg < 35:
            signals.append(self._create_sentiment_deterioration_signal(
                ticker, current_price, entry_price, current_pnl_pct,
                component_health, sentiment_avg
            ))

        # Check theme weakness
        if component_health.get('theme_strength', 100) < 40:
            signals.append(self._create_theme_weakness_signal(
                ticker, current_price, entry_price, current_pnl_pct,
                component_health
            ))

        # Check institutional exit
        if component_health.get('institutional_ownership', 100) < 30:
            signals.append(self._create_institutional_exit_signal(
                ticker, current_price, entry_price, current_pnl_pct,
                component_health
            ))

        # Check profit target
        if current_pnl_pct >= 50:
            signals.append(self._create_profit_target_signal(
                ticker, current_price, entry_price, current_pnl_pct,
                component_health
            ))

        # Check overall degradation
        if overall_health < 50:
            signals.append(self._create_degradation_signal(
                ticker, current_price, entry_price, current_pnl_pct,
                component_health, overall_health
            ))

        return signals

    def _create_stop_loss_signal(
        self, ticker, current_price, entry_price, current_pnl_pct,
        stop_loss, component_health
    ) -> ExitSignal:
        """Create stop loss exit signal."""
        return ExitSignal(
            ticker=ticker,
            urgency=ExitUrgency.EMERGENCY,
            reason=ExitReason.RISK_MANAGEMENT,
            current_price=current_price,
            entry_price=entry_price,
            current_pnl_pct=current_pnl_pct,
            immediate_exit=True,
            target_exit_price=current_price,
            stop_loss_price=stop_loss,
            components_degraded=self._get_degraded_components(component_health),
            component_scores=component_health,
            component_changes={},
            primary_reason="Stop loss triggered",
            detailed_analysis=f"Price ${current_price:.2f} hit stop loss ${stop_loss:.2f}. Risk management requires immediate exit.",
            confidence=0.95,
            recommended_action="EXIT IMMEDIATELY at market price",
            alternative_actions=["Set limit order slightly below market"],
            timestamp=datetime.now()
        )

    def _create_technical_breakdown_signal(
        self, ticker, current_price, entry_price, current_pnl_pct, component_health
    ) -> ExitSignal:
        """Create technical breakdown signal."""
        return ExitSignal(
            ticker=ticker,
            urgency=ExitUrgency.HIGH,
            reason=ExitReason.TECHNICAL_BREAKDOWN,
            current_price=current_price,
            entry_price=entry_price,
            current_pnl_pct=current_pnl_pct,
            immediate_exit=False,
            target_exit_price=current_price * 0.98,
            stop_loss_price=None,
            components_degraded=['price_momentum', 'ma_health', 'relative_strength'],
            component_scores=component_health,
            component_changes={},
            primary_reason="Technical indicators showing breakdown",
            detailed_analysis="Price momentum weak, MA breakdown, RS deteriorating. Technical structure damaged.",
            confidence=0.80,
            recommended_action="EXIT today before further deterioration",
            alternative_actions=[
                "Wait for bounce to resistance",
                "Scale out 50% immediately, 50% on bounce"
            ],
            timestamp=datetime.now()
        )

    def _create_catalyst_expired_signal(
        self, ticker, current_price, entry_price, current_pnl_pct, component_health
    ) -> ExitSignal:
        """Create catalyst expiration signal."""
        return ExitSignal(
            ticker=ticker,
            urgency=ExitUrgency.MODERATE,
            reason=ExitReason.CATALYST_EXPIRED,
            current_price=current_price,
            entry_price=entry_price,
            current_pnl_pct=current_pnl_pct,
            immediate_exit=False,
            target_exit_price=current_price * 0.99,
            stop_loss_price=None,
            components_degraded=['catalyst_freshness', 'narrative_consistency'],
            component_scores=component_health,
            component_changes={},
            primary_reason="Catalyst has expired or weakened",
            detailed_analysis="Original catalyst no longer driving price. Story momentum fading.",
            confidence=0.70,
            recommended_action="EXIT within 1-2 days",
            alternative_actions=[
                "Look for new catalyst emergence",
                "Scale out 70%, keep 30% runner"
            ],
            timestamp=datetime.now()
        )

    def _create_sentiment_deterioration_signal(
        self, ticker, current_price, entry_price, current_pnl_pct,
        component_health, sentiment_avg
    ) -> ExitSignal:
        """Create sentiment deterioration signal."""
        return ExitSignal(
            ticker=ticker,
            urgency=ExitUrgency.MODERATE,
            reason=ExitReason.SENTIMENT_DETERIORATION,
            current_price=current_price,
            entry_price=entry_price,
            current_pnl_pct=current_pnl_pct,
            immediate_exit=False,
            target_exit_price=current_price * 0.98,
            stop_loss_price=None,
            components_degraded=['x_sentiment', 'reddit_sentiment', 'social_volume'],
            component_scores=component_health,
            component_changes={},
            primary_reason=f"Sentiment deteriorated to {sentiment_avg:.0f}/100",
            detailed_analysis="Social sentiment turning negative across X, Reddit, StockTwits. Community losing interest.",
            confidence=0.65,
            recommended_action="EXIT within 2-3 days or on next bounce",
            alternative_actions=[
                "Monitor for sentiment reversal",
                "Reduce position by 50%"
            ],
            timestamp=datetime.now()
        )

    def _create_theme_weakness_signal(
        self, ticker, current_price, entry_price, current_pnl_pct, component_health
    ) -> ExitSignal:
        """Create theme weakness signal."""
        return ExitSignal(
            ticker=ticker,
            urgency=ExitUrgency.MODERATE,
            reason=ExitReason.THEME_WEAKNESS,
            current_price=current_price,
            entry_price=entry_price,
            current_pnl_pct=current_pnl_pct,
            immediate_exit=False,
            target_exit_price=current_price * 0.97,
            stop_loss_price=None,
            components_degraded=['theme_strength', 'sector_rotation', 'related_performance'],
            component_scores=component_health,
            component_changes={},
            primary_reason="Theme showing weakness",
            detailed_analysis="Theme strength declining, sector rotating out, related stocks underperforming.",
            confidence=0.70,
            recommended_action="EXIT this week",
            alternative_actions=[
                "Rotate to stronger theme",
                "Hold if leadership position maintained"
            ],
            timestamp=datetime.now()
        )

    def _create_institutional_exit_signal(
        self, ticker, current_price, entry_price, current_pnl_pct, component_health
    ) -> ExitSignal:
        """Create institutional exit signal."""
        return ExitSignal(
            ticker=ticker,
            urgency=ExitUrgency.HIGH,
            reason=ExitReason.INSTITUTIONAL_EXIT,
            current_price=current_price,
            entry_price=entry_price,
            current_pnl_pct=current_pnl_pct,
            immediate_exit=False,
            target_exit_price=current_price * 0.98,
            stop_loss_price=None,
            components_degraded=['institutional_ownership', 'dark_pool', 'smart_money'],
            component_scores=component_health,
            component_changes={},
            primary_reason="Institutional selling detected",
            detailed_analysis="Dark pool activity negative, institutional ownership declining, smart money exiting.",
            confidence=0.85,
            recommended_action="EXIT today - follow the smart money",
            alternative_actions=["Monitor for institutional re-entry"],
            timestamp=datetime.now()
        )

    def _create_profit_target_signal(
        self, ticker, current_price, entry_price, current_pnl_pct, component_health
    ) -> ExitSignal:
        """Create profit target reached signal."""
        return ExitSignal(
            ticker=ticker,
            urgency=ExitUrgency.LOW,
            reason=ExitReason.PROFIT_TARGET,
            current_price=current_price,
            entry_price=entry_price,
            current_pnl_pct=current_pnl_pct,
            immediate_exit=False,
            target_exit_price=current_price,
            stop_loss_price=None,
            components_degraded=[],
            component_scores=component_health,
            component_changes={},
            primary_reason=f"Profit target reached: +{current_pnl_pct:.1f}%",
            detailed_analysis=f"Position up {current_pnl_pct:.1f}%. Consider taking profits or trailing stop.",
            confidence=0.60,
            recommended_action="Consider scaling out 50-70%",
            alternative_actions=[
                "Take full profits",
                "Trail stop at +20% and let it run",
                "Scale out 2/3, keep 1/3 runner"
            ],
            timestamp=datetime.now()
        )

    def _create_degradation_signal(
        self, ticker, current_price, entry_price, current_pnl_pct,
        component_health, overall_health
    ) -> ExitSignal:
        """Create overall degradation signal."""
        degraded = self._get_degraded_components(component_health)

        urgency = ExitUrgency.CRITICAL if overall_health < 30 else ExitUrgency.HIGH

        return ExitSignal(
            ticker=ticker,
            urgency=urgency,
            reason=ExitReason.COMPONENT_DEGRADATION,
            current_price=current_price,
            entry_price=entry_price,
            current_pnl_pct=current_pnl_pct,
            immediate_exit=overall_health < 30,
            target_exit_price=current_price * 0.98,
            stop_loss_price=None,
            components_degraded=degraded,
            component_scores=component_health,
            component_changes={},
            primary_reason=f"Overall health degraded to {overall_health:.0f}/100",
            detailed_analysis=f"Multiple components failing: {', '.join(degraded[:5])}. Position quality severely compromised.",
            confidence=0.85,
            recommended_action="EXIT today" if overall_health < 30 else "EXIT this week",
            alternative_actions=[
                "Monitor for improvement over 2-3 days",
                "Scale out 70%, monitor remainder"
            ] if overall_health >= 30 else ["Exit immediately"],
            timestamp=datetime.now()
        )

    def _get_degraded_components(self, component_health: Dict[str, float]) -> List[str]:
        """Get list of components below threshold."""
        return [
            comp for comp, score in component_health.items()
            if score < (self.COMPONENT_FAIL_THRESHOLD * 100)
        ]

    def _should_exit(
        self,
        exit_signals: List[ExitSignal],
        overall_health: float,
        current_pnl_pct: float
    ) -> bool:
        """Determine if should exit position."""
        if not exit_signals:
            return False

        # Emergency/Critical signals = immediate exit
        if any(s.urgency in [ExitUrgency.EMERGENCY, ExitUrgency.CRITICAL] for s in exit_signals):
            return True

        # Multiple HIGH urgency signals = exit
        high_signals = [s for s in exit_signals if s.urgency == ExitUrgency.HIGH]
        if len(high_signals) >= 2:
            return True

        # Overall health critical = exit
        if overall_health < 40:
            return True

        # Large loss + any signal = exit
        if current_pnl_pct < -5 and len(exit_signals) >= 1:
            return True

        return False

    def _generate_recommendation(
        self,
        should_exit: bool,
        highest_urgency: ExitUrgency,
        exit_signals: List[ExitSignal],
        current_pnl_pct: float
    ) -> Tuple[str, str]:
        """Generate recommendation and timeframe."""
        if not should_exit:
            return "HOLD - Monitor closely", "ongoing"

        if highest_urgency == ExitUrgency.EMERGENCY:
            return "EXIT IMMEDIATELY at market", "immediate"
        elif highest_urgency == ExitUrgency.CRITICAL:
            return "EXIT TODAY at best available price", "today"
        elif highest_urgency == ExitUrgency.HIGH:
            return "EXIT within 24 hours", "today"
        elif highest_urgency == ExitUrgency.MODERATE:
            return "EXIT this week, preferably on bounce", "this_week"
        else:
            if current_pnl_pct > 30:
                return "Consider taking partial profits", "this_week"
            else:
                return "Monitor and prepare to exit", "monitor"

    # Component scoring methods (placeholders - implement based on actual data)
    def _score_price_momentum(self, data: Dict) -> float:
        return data.get('technical', {}).get('momentum', 50.0)

    def _score_volume_profile(self, data: Dict) -> float:
        return data.get('technical', {}).get('volume_score', 50.0)

    def _score_relative_strength(self, data: Dict) -> float:
        rs = data.get('technical', {}).get('rs_rating', 50.0)
        return rs

    def _score_support_resistance(self, data: Dict) -> float:
        return data.get('technical', {}).get('support_strength', 50.0)

    def _score_volatility(self, data: Dict) -> float:
        # Lower volatility = higher score for exits
        vol = data.get('technical', {}).get('volatility', 0.02)
        return max(0, 100 - (vol * 1000))

    def _score_price_patterns(self, data: Dict) -> float:
        return data.get('technical', {}).get('pattern_score', 50.0)

    def _score_ma_health(self, data: Dict) -> float:
        return data.get('technical', {}).get('ma_health', 50.0)

    def _score_macd(self, data: Dict) -> float:
        return data.get('technical', {}).get('macd_score', 50.0)

    def _score_x_sentiment(self, data: Dict) -> float:
        return data.get('sentiment', {}).get('x_score', 50.0)

    def _score_reddit_sentiment(self, data: Dict) -> float:
        return data.get('sentiment', {}).get('reddit_score', 50.0)

    def _score_stocktwits_sentiment(self, data: Dict) -> float:
        return data.get('sentiment', {}).get('stocktwits_score', 50.0)

    def _score_sentiment_trend(self, data: Dict) -> float:
        return data.get('sentiment', {}).get('trend_score', 50.0)

    def _score_viral_activity(self, data: Dict) -> float:
        return data.get('sentiment', {}).get('viral_score', 50.0)

    def _score_social_volume(self, data: Dict) -> float:
        return data.get('sentiment', {}).get('volume_score', 50.0)

    def _score_theme_strength(self, data: Dict) -> float:
        return data.get('theme', {}).get('strength', 50.0)

    def _score_theme_leadership(self, data: Dict) -> float:
        return data.get('theme', {}).get('leadership', 50.0)

    def _score_supply_chain(self, data: Dict) -> float:
        return data.get('theme', {}).get('supply_chain_score', 50.0)

    def _score_catalyst_freshness(self, data: Dict) -> float:
        return data.get('catalyst', {}).get('freshness', 50.0)

    def _score_narrative(self, data: Dict) -> float:
        return data.get('theme', {}).get('narrative_score', 50.0)

    def _score_sector_rotation(self, data: Dict) -> float:
        return data.get('theme', {}).get('rotation_score', 50.0)

    def _score_related_performance(self, data: Dict) -> float:
        return data.get('theme', {}).get('related_score', 50.0)

    def _score_theme_concentration(self, data: Dict) -> float:
        # Lower concentration = higher score
        conc = data.get('theme', {}).get('concentration', 0.5)
        return max(0, 100 - (conc * 100))

    def _score_ai_conviction(self, data: Dict) -> float:
        return data.get('ai', {}).get('conviction', 50.0)

    def _score_ai_risk(self, data: Dict) -> float:
        # Lower risk = higher score
        risk = data.get('ai', {}).get('risk', 50.0)
        return 100 - risk

    def _score_ai_opportunity(self, data: Dict) -> float:
        return data.get('ai', {}).get('opportunity', 50.0)

    def _score_ai_patterns(self, data: Dict) -> float:
        return data.get('ai', {}).get('pattern_score', 50.0)

    def _score_earnings_tone(self, data: Dict) -> float:
        return data.get('earnings', {}).get('tone_score', 50.0)

    def _score_guidance(self, data: Dict) -> float:
        return data.get('earnings', {}).get('guidance_score', 50.0)

    def _score_beat_rate(self, data: Dict) -> float:
        return data.get('earnings', {}).get('beat_rate', 50.0)

    def _score_surprise_trend(self, data: Dict) -> float:
        return data.get('earnings', {}).get('surprise_trend', 50.0)

    def _score_institutional(self, data: Dict) -> float:
        return data.get('institutional', {}).get('ownership_score', 50.0)

    def _score_dark_pool(self, data: Dict) -> float:
        return data.get('institutional', {}).get('dark_pool_score', 50.0)

    def _score_options_flow(self, data: Dict) -> float:
        return data.get('institutional', {}).get('options_score', 50.0)

    def _score_smart_money(self, data: Dict) -> float:
        return data.get('institutional', {}).get('smart_money_score', 50.0)

    def _score_revenue_growth(self, data: Dict) -> float:
        return data.get('fundamental', {}).get('revenue_score', 50.0)

    def _score_margin_trends(self, data: Dict) -> float:
        return data.get('fundamental', {}).get('margin_score', 50.0)

    def _score_valuation(self, data: Dict) -> float:
        return data.get('fundamental', {}).get('valuation_score', 50.0)

    def _score_insider_trading(self, data: Dict) -> float:
        return data.get('fundamental', {}).get('insider_score', 50.0)


def format_exit_analysis(analysis: ExitAnalysis) -> str:
    """Format exit analysis for display."""
    lines = []

    lines.append(f"🎯 EXIT ANALYSIS: {analysis.ticker}")
    lines.append("=" * 60)
    lines.append(f"Entry: ${analysis.entry_price:.2f} | Current: ${analysis.current_price:.2f} | P/L: {analysis.current_pnl_pct:+.1f}%")
    lines.append(f"Holding: {analysis.holding_days} days")
    lines.append("")

    lines.append("📊 PRICE TARGETS")
    lines.append(f"  Bull:  ${analysis.bull_target.target:.2f} ({analysis.bull_target.confidence:.0%} confidence)")
    lines.append(f"  Base:  ${analysis.base_target.target:.2f} ({analysis.base_target.confidence:.0%} confidence)")
    lines.append(f"  Bear:  ${analysis.bear_target.target:.2f} ({analysis.bear_target.confidence:.0%} confidence)")
    lines.append(f"  Current Target: ${analysis.current_target:.2f}")
    lines.append("")

    lines.append("🛡️ RISK LEVELS")
    lines.append(f"  Stop Loss: ${analysis.stop_loss:.2f} ({((analysis.stop_loss/analysis.current_price-1)*100):+.1f}%)")
    lines.append(f"  Trailing Stop: ${analysis.trailing_stop:.2f} ({((analysis.trailing_stop/analysis.current_price-1)*100):+.1f}%)")
    lines.append("")

    lines.append(f"💊 HEALTH SCORE: {analysis.overall_health_score:.0f}/100")
    lines.append(f"📉 Degradation Rate: {analysis.degradation_rate:+.2f}/day")
    lines.append("")

    if analysis.exit_signals:
        lines.append(f"🚨 EXIT SIGNALS ({len(analysis.exit_signals)})")
        for signal in analysis.exit_signals[:3]:
            lines.append(f"  • {signal.urgency.name}: {signal.primary_reason}")
            lines.append(f"    {signal.detailed_analysis[:100]}")
        lines.append("")

    lines.append("💡 RECOMMENDATION")
    lines.append(f"  Action: {analysis.recommended_action}")
    lines.append(f"  Timeframe: {analysis.action_timeframe.upper()}")
    lines.append(f"  Should Exit: {'YES' if analysis.should_exit else 'NO'}")

    return "\n".join(lines)
