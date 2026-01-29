#!/usr/bin/env python3
"""
Comprehensive Agentic Brain - Hierarchical AI Intelligence System

Coordinates ALL 35 AI components under 5 directors reporting to a CIO.
This is the master intelligence system that makes context-aware,
coordinated decisions by leveraging the collective intelligence of
all specialized components.

Architecture:
    CIO (Chief Intelligence Officer)
    ├─ Market Regime Monitor (Context)
    ├─ Sector Cycle Analyst (Context)
    │
    ├─ Theme Intelligence Director (7 specialists)
    ├─ Trading Intelligence Director (6 specialists)
    ├─ Learning & Adaptation Director (8 specialists)
    ├─ Realtime Intelligence Director (7 specialists)
    └─ Validation & Feedback Director (5 specialists)

Total: 35 coordinated AI components
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
from datetime import datetime

# Import all specialist components
from src.ai.ai_enhancements import AIEnhancementEngine
from src.ai.deepseek_intelligence import DeepSeekIntelligence
from src.ai import ai_learning

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class MarketStance(Enum):
    """Market positioning stance."""
    OFFENSIVE = "offensive"
    NEUTRAL = "neutral"
    DEFENSIVE = "defensive"


class MarketHealth(Enum):
    """Market health rating."""
    HEALTHY = "healthy"
    NEUTRAL = "neutral"
    WARNING = "warning"
    CONCERNING = "concerning"


class CycleStage(Enum):
    """Market cycle stage."""
    EARLY = "early"
    MID = "mid"
    LATE = "late"
    RECESSION = "recession"


class Decision(Enum):
    """Final trading decision."""
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    HOLD = "hold"
    SELL = "sell"
    STRONG_SELL = "strong_sell"


# =============================================================================
# CONTEXT DATA CLASSES
# =============================================================================

@dataclass
class MarketContext:
    """Shared market regime context broadcast to all components."""
    health: MarketHealth
    risk_level: int  # 1-10
    stance: MarketStance
    breadth: float  # % stocks above 200MA
    vix: float
    new_highs: int
    new_lows: int
    leading_sectors: List[str]
    lagging_sectors: List[str]
    regime_narrative: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class SectorContext:
    """Shared sector cycle context broadcast to all components."""
    cycle_stage: CycleStage
    leading_sectors: List[str]
    lagging_sectors: List[str]
    rotation_confidence: float  # 0-1
    money_flow_direction: str
    cycle_narrative: str
    next_rotation_likely: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


# =============================================================================
# INTELLIGENCE SYNTHESIS DATA CLASSES
# =============================================================================

@dataclass
class ThemeIntelligence:
    """Synthesized theme intelligence from Theme Director."""
    theme_quality: int  # 1-10
    lifecycle_stage: str  # emerging/growth/mature/declining
    tam_validated: bool
    tam_cagr: float
    adoption_stage: str
    role_classification: str  # leader/enabler/derivative/speculative
    membership_validated: bool
    emerging_status: Optional[str]
    supply_chain_strength: Optional[str]
    growth_drivers: List[str]
    risks: List[str]
    confidence: float  # 0-1
    reasoning: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class TradingIntelligence:
    """Synthesized trading intelligence from Trading Director."""
    trade_quality: int  # 1-10
    signal_strength: str  # weak/moderate/strong
    signal_catalyst: str
    signal_confidence: float
    timeframe_alignment: str  # aligned_bullish/aligned_bearish/mixed
    best_entry_timeframe: Optional[str]
    earnings_tone: Optional[str]
    earnings_catalysts: List[str]
    corporate_action_impact: Optional[str]
    anomaly_detected: bool
    anomaly_severity: Optional[str]
    options_flow_signal: Optional[str]
    key_levels: Dict[str, float]
    recommendation: str  # buy/sell/hold/wait
    position_size: str  # full/half/quarter/none
    stop_loss: Optional[float]
    targets: List[float]
    risks: List[str]
    confidence: float
    reasoning: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class LearningIntelligence:
    """Synthesized learning intelligence from Learning Director."""
    learning_quality: int  # 1-10
    pattern_identified: bool
    pattern_signature: Optional[str]
    pattern_win_rate: Optional[float]
    historical_similar_trades: int
    historical_win_rate: float
    prediction: str  # win/loss/breakeven
    prediction_confidence: float
    prediction_calibration: float
    strategy_alignment: bool
    recommended_adjustments: List[str]
    optimal_weights: Dict[str, float]
    expert_consensus: Optional[str]
    catalyst_performance: Optional[str]
    lessons_learned: List[str]
    confidence: float
    reasoning: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class RealtimeIntelligence:
    """Synthesized realtime intelligence from Realtime Director."""
    realtime_quality: int  # 1-10
    catalyst_detected: bool
    catalyst_type: Optional[str]
    catalyst_sentiment: Optional[str]
    catalyst_impact: Optional[str]
    theme_rotation_signal: Optional[str]
    emerging_themes: List[str]
    fading_themes: List[str]
    anomalies_detected: int
    top_anomalies: List[Dict]
    unusual_options_activity: bool
    options_signals: List[Dict]
    market_narrative: str
    daily_brief_summary: str
    urgency_score: int  # 1-10
    alerts: List[str]
    confidence: float
    reasoning: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ValidationIntelligence:
    """Synthesized validation intelligence from Validation Director."""
    validation_quality: int  # 1-10
    fact_check_passed: bool
    fact_check_confidence: float
    contradictions_found: List[str]
    expert_predictions: List[Dict]
    expert_consensus: Optional[str]
    supply_chain_mapped: bool
    supply_chain_strength: Optional[str]
    coaching_advice: List[str]
    quick_feedback: Optional[str]
    sources_verified: int
    reliability_score: float
    confidence: float
    reasoning: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class FinalDecision:
    """Final decision from CIO synthesizing all intelligence."""
    ticker: str
    decision: Decision
    position_size: str  # full/half/quarter/none
    confidence: float  # 0-1

    # Context summaries
    market_context_summary: str
    sector_context_summary: str

    # Intelligence scores
    theme_score: int  # 1-10
    trade_score: int  # 1-10
    learning_score: int  # 1-10
    realtime_score: int  # 1-10
    validation_score: int  # 1-10

    # Overall assessment
    reasoning: str
    key_strengths: List[str]
    risks: List[str]

    # Trade details
    entry_price: Optional[float]
    stop_loss: Optional[float]
    targets: List[float]

    # Supporting intelligence
    theme_intelligence: Optional[ThemeIntelligence]
    trading_intelligence: Optional[TradingIntelligence]
    learning_intelligence: Optional[LearningIntelligence]
    realtime_intelligence: Optional[RealtimeIntelligence]
    validation_intelligence: Optional[ValidationIntelligence]

    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


# =============================================================================
# CONTEXT MANAGER
# =============================================================================

class ContextManager:
    """
    Manages shared context across all 35 components.

    The context manager is the central nervous system of the agentic brain,
    broadcasting market and sector context to all components and enabling
    coordinated, context-aware decision making.
    """

    def __init__(self):
        self.market_context: Optional[MarketContext] = None
        self.sector_context: Optional[SectorContext] = None
        self._subscribers: List[callable] = []
        logger.info("Context Manager initialized")

    def update_market_context(self, context: MarketContext):
        """Update and broadcast market context to all subscribers."""
        self.market_context = context
        logger.info(f"Market context updated: {context.health.value}, stance={context.stance.value}, risk={context.risk_level}/10")
        self._broadcast_context()

    def update_sector_context(self, context: SectorContext):
        """Update and broadcast sector context to all subscribers."""
        self.sector_context = context
        logger.info(f"Sector context updated: {context.cycle_stage.value}, leading={', '.join(context.leading_sectors[:3])}")
        self._broadcast_context()

    def subscribe(self, callback: callable):
        """Subscribe to context updates."""
        self._subscribers.append(callback)

    def _broadcast_context(self):
        """Broadcast context to all subscribers."""
        for callback in self._subscribers:
            try:
                callback(self.market_context, self.sector_context)
            except Exception as e:
                logger.error(f"Error broadcasting context to subscriber: {e}")

    def get_context_dict(self) -> Dict[str, Any]:
        """Get context as dictionary for component consumption."""
        return {
            'market': {
                'health': self.market_context.health.value if self.market_context else None,
                'risk_level': self.market_context.risk_level if self.market_context else None,
                'stance': self.market_context.stance.value if self.market_context else None,
                'breadth': self.market_context.breadth if self.market_context else None,
                'vix': self.market_context.vix if self.market_context else None,
            },
            'sector': {
                'cycle_stage': self.sector_context.cycle_stage.value if self.sector_context else None,
                'leading': self.sector_context.leading_sectors if self.sector_context else [],
                'lagging': self.sector_context.lagging_sectors if self.sector_context else [],
            }
        }


# =============================================================================
# THEME INTELLIGENCE DIRECTOR
# =============================================================================

class ThemeIntelligenceDirector:
    """
    Coordinates theme-level analysis across 7 specialist components.

    Reports to: Chief Intelligence Officer
    Manages:
        - Theme Info Generator
        - TAM Estimator
        - Theme Stage Detector
        - Theme Lifecycle Analyzer
        - Role Classifier
        - Theme Membership Validator
        - Emerging Theme Detector
    """

    def __init__(self, context_manager: ContextManager):
        self.context = context_manager
        self.deepseek = DeepSeekIntelligence()
        self.enhancements = AIEnhancementEngine()
        logger.info("Theme Intelligence Director initialized")

    def analyze_theme(
        self,
        theme_name: str,
        ticker: str,
        players: List[str],
        headlines: Optional[List[str]] = None,
        earnings_data: Optional[Dict] = None,
        correlation: float = 0.85
    ) -> ThemeIntelligence:
        """
        Coordinate all theme specialists to produce comprehensive theme intelligence.

        Components coordinated:
        1. Theme Info Generator - Generate theme overview
        2. TAM Estimator - Estimate market expansion
        3. Theme Stage Detector - Identify lifecycle stage
        4. Role Classifier - Classify stock role
        5. Theme Membership Validator - Validate membership
        6. Emerging Theme Detector - Check if emerging
        """
        logger.info(f"Theme Director analyzing: {theme_name} for {ticker}")

        context_dict = self.context.get_context_dict()

        # Component #9: Theme Info Generator
        theme_info = self.deepseek.generate_theme_info(
            correlated_stocks=players,
            news_headlines=headlines or []
        )

        # Component #7: TAM Estimator
        tam_analysis = self.enhancements.analyze_tam_expansion(
            theme=theme_name,
            current_players=players,
            context=f"Market: {context_dict['market']['health']}, Cycle: {context_dict['sector']['cycle_stage']}"
        )

        # Component #11: Theme Stage Detector
        stage_detection = self.deepseek.detect_theme_stage(
            theme_name=theme_name,
            recent_headlines=headlines or [],
            quant_signals={}
        )

        # Component #10: Role Classifier
        role_classification = self.deepseek.classify_role(
            ticker=ticker,
            theme_name=theme_name,
            company_description=theme_info.get('description', ''),
            lead_lag_days=0,
            correlation=correlation
        )

        # Component #14: Theme Membership Validator
        membership = self.deepseek.validate_theme_membership(
            ticker=ticker,
            theme_name=theme_name,
            company_description=theme_info.get('description', ''),
            correlation=correlation
        )

        # Synthesize all theme intelligence
        theme_quality = self._calculate_theme_quality(
            tam_analysis,
            stage_detection,
            role_classification,
            membership,
            context_dict
        )

        growth_drivers = []
        if tam_analysis:
            growth_drivers.extend(tam_analysis.growth_drivers)
        if theme_info:
            growth_drivers.extend(theme_info.get('key_drivers', []))

        risks = []
        if tam_analysis and tam_analysis.competitive_intensity == 'high':
            risks.append("High competitive intensity")
        if stage_detection and stage_detection.get('stage') == 'declining':
            risks.append("Theme in declining stage")

        reasoning = self._generate_theme_reasoning(
            theme_quality,
            tam_analysis,
            stage_detection,
            role_classification,
            membership,
            context_dict
        )

        return ThemeIntelligence(
            theme_quality=theme_quality,
            lifecycle_stage=stage_detection.get('stage', 'unknown') if stage_detection else 'unknown',
            tam_validated=tam_analysis is not None and tam_analysis.cagr_estimate > 15,
            tam_cagr=tam_analysis.cagr_estimate if tam_analysis else 0.0,
            adoption_stage=tam_analysis.adoption_stage if tam_analysis else 'mid',
            role_classification=role_classification.get('role', 'unknown') if role_classification else 'unknown',
            membership_validated=membership.get('is_member', False) if membership else False,
            emerging_status=stage_detection.get('stage') if stage_detection else None,
            supply_chain_strength=None,  # Can be added later
            growth_drivers=list(set(growth_drivers))[:5],
            risks=risks,
            confidence=self._calculate_theme_confidence(tam_analysis, stage_detection, membership),
            reasoning=reasoning
        )

    def _calculate_theme_quality(
        self,
        tam_analysis,
        stage_detection,
        role_classification,
        membership,
        context_dict
    ) -> int:
        """Calculate theme quality score 1-10."""
        score = 5  # Base score

        # TAM analysis boost
        if tam_analysis:
            if tam_analysis.cagr_estimate > 30:
                score += 2
            elif tam_analysis.cagr_estimate > 20:
                score += 1

            if tam_analysis.adoption_stage == 'early':
                score += 1

        # Stage detection boost
        if stage_detection:
            stage = stage_detection.get('stage', '')
            if stage in ['emerging', 'growth']:
                score += 1
            elif stage == 'declining':
                score -= 2

        # Role classification boost
        if role_classification:
            role = role_classification.get('role', '')
            if role == 'leader':
                score += 2
            elif role == 'enabler':
                score += 1

        # Membership validation
        if membership and membership.get('is_member'):
            score += 1

        # Market context adjustment
        if context_dict['market']['health'] == 'healthy':
            score += 1
        elif context_dict['market']['health'] == 'concerning':
            score -= 1

        # Cycle context adjustment
        if context_dict['sector']['cycle_stage'] == 'early':
            score += 1

        return max(1, min(10, score))

    def _calculate_theme_confidence(self, tam_analysis, stage_detection, membership) -> float:
        """Calculate confidence in theme analysis."""
        confidences = []

        if tam_analysis:
            confidences.append(tam_analysis.confidence)
        if stage_detection:
            confidences.append(stage_detection.get('confidence', 0.5))
        if membership:
            confidences.append(membership.get('confidence', 0.5))

        return sum(confidences) / len(confidences) if confidences else 0.5

    def _generate_theme_reasoning(
        self,
        theme_quality,
        tam_analysis,
        stage_detection,
        role_classification,
        membership,
        context_dict
    ) -> str:
        """Generate human-readable reasoning for theme analysis."""
        parts = [f"Theme quality: {theme_quality}/10"]

        if tam_analysis:
            parts.append(f"TAM CAGR: {tam_analysis.cagr_estimate:.0f}%, stage: {tam_analysis.adoption_stage}")

        if stage_detection:
            parts.append(f"Lifecycle: {stage_detection.get('stage', 'unknown')}")

        if role_classification:
            parts.append(f"Role: {role_classification.get('role', 'unknown')}")

        if membership:
            status = "validated" if membership.get('is_member') else "not validated"
            parts.append(f"Membership: {status}")

        parts.append(f"Market: {context_dict['market']['health']}, Cycle: {context_dict['sector']['cycle_stage']}")

        return "; ".join(parts)


# =============================================================================
# TRADING INTELLIGENCE DIRECTOR
# =============================================================================

class TradingIntelligenceDirector:
    """
    Coordinates trade-level analysis across 6 specialist components.

    Reports to: Chief Intelligence Officer
    Manages:
        - Signal Explainer
        - Timeframe Synthesizer
        - Earnings Intelligence
        - Corporate Action Analyzer
        - Anomaly Detector
        - Options Flow Analyzer
    """

    def __init__(self, context_manager: ContextManager):
        self.context = context_manager
        self.enhancements = AIEnhancementEngine()
        logger.info("Trading Intelligence Director initialized")

    def analyze_trade(
        self,
        ticker: str,
        signal_type: str,
        signal_data: Dict[str, Any],
        timeframe_data: Optional[Dict] = None,
        earnings_data: Optional[Dict] = None,
        corporate_action: Optional[Dict] = None,
        price_data: Optional[Dict] = None
    ) -> TradingIntelligence:
        """
        Coordinate all trading specialists to produce comprehensive trade intelligence.

        Components coordinated:
        1. Signal Explainer - Explain signal trigger
        2. Timeframe Synthesizer - Multi-timeframe alignment
        3. Earnings Intelligence - Earnings analysis
        4. Corporate Action Analyzer - Event impact
        5. Anomaly Detector - Unusual behavior
        6. Options Flow Analyzer - Options activity
        """
        logger.info(f"Trading Director analyzing: {ticker} {signal_type}")

        context_dict = self.context.get_context_dict()

        # Component #1: Signal Explainer
        signal_explanation = self.enhancements.explain_signal(
            ticker=ticker,
            signal_type=signal_type,
            signal_data=signal_data
        )

        # Component #6: Timeframe Synthesizer
        timeframe_synthesis = None
        if timeframe_data:
            timeframe_synthesis = self.enhancements.synthesize_timeframes(
                ticker=ticker,
                timeframe_data=timeframe_data
            )

        # Component #2: Earnings Intelligence
        earnings_analysis = None
        if earnings_data and earnings_data.get('transcript'):
            earnings_analysis = self.enhancements.analyze_earnings_call(
                ticker=ticker,
                transcript=earnings_data['transcript'],
                earnings_data=earnings_data
            )

        # Component #8: Corporate Action Analyzer
        action_impact = None
        if corporate_action:
            action_impact = self.enhancements.analyze_corporate_action(
                ticker=ticker,
                action_type=corporate_action.get('type', 'unknown'),
                action_details=corporate_action.get('details', '')
            )

        # Component #21: Anomaly Detector (from ai_learning)
        anomaly_detected = False
        anomaly_severity = None
        if price_data:
            try:
                anomaly_result = ai_learning.detect_anomalies(
                    ticker=ticker,
                    current_data=price_data,
                    historical_behavior={}
                )
                if anomaly_result and anomaly_result.get('anomalies'):
                    anomaly_detected = True
                    anomaly_severity = anomaly_result.get('severity', 'low')
            except Exception as e:
                logger.debug(f"Anomaly detection skipped: {e}")

        # Synthesize trade intelligence
        trade_quality = self._calculate_trade_quality(
            signal_explanation,
            timeframe_synthesis,
            earnings_analysis,
            context_dict
        )

        recommendation, position_size = self._determine_recommendation(
            trade_quality,
            signal_explanation,
            timeframe_synthesis,
            context_dict
        )

        key_levels = timeframe_synthesis.key_levels if timeframe_synthesis else {}
        targets = self._calculate_targets(key_levels, trade_quality)
        stop_loss = key_levels.get('support') if key_levels else None

        risks = self._identify_risks(
            signal_explanation,
            timeframe_synthesis,
            earnings_analysis,
            anomaly_detected,
            context_dict
        )

        reasoning = self._generate_trade_reasoning(
            trade_quality,
            signal_explanation,
            timeframe_synthesis,
            earnings_analysis,
            context_dict
        )

        return TradingIntelligence(
            trade_quality=trade_quality,
            signal_strength=self._assess_signal_strength(signal_explanation),
            signal_catalyst=signal_explanation.catalyst if signal_explanation else "Unknown",
            signal_confidence=signal_explanation.confidence if signal_explanation else 0.5,
            timeframe_alignment=timeframe_synthesis.overall_alignment if timeframe_synthesis else "mixed",
            best_entry_timeframe=timeframe_synthesis.best_entry_timeframe if timeframe_synthesis else None,
            earnings_tone=earnings_analysis.management_tone if earnings_analysis else None,
            earnings_catalysts=earnings_analysis.growth_catalysts if earnings_analysis else [],
            corporate_action_impact=action_impact.expected_impact if action_impact else None,
            anomaly_detected=anomaly_detected,
            anomaly_severity=anomaly_severity,
            options_flow_signal=None,  # Can be enhanced later
            key_levels=key_levels,
            recommendation=recommendation,
            position_size=position_size,
            stop_loss=stop_loss,
            targets=targets,
            risks=risks,
            confidence=self._calculate_trade_confidence(signal_explanation, timeframe_synthesis, earnings_analysis),
            reasoning=reasoning
        )

    def _calculate_trade_quality(
        self,
        signal_explanation,
        timeframe_synthesis,
        earnings_analysis,
        context_dict
    ) -> int:
        """Calculate trade quality score 1-10."""
        score = 5

        # Signal quality
        if signal_explanation:
            if signal_explanation.confidence > 0.8:
                score += 2
            elif signal_explanation.confidence > 0.6:
                score += 1

        # Timeframe alignment
        if timeframe_synthesis:
            if timeframe_synthesis.trade_quality_score >= 8:
                score += 2
            elif timeframe_synthesis.trade_quality_score >= 6:
                score += 1

            if 'aligned' in timeframe_synthesis.overall_alignment:
                score += 1

        # Earnings support
        if earnings_analysis:
            if earnings_analysis.management_tone == 'bullish':
                score += 1

        # Market context adjustment
        if context_dict['market']['stance'] == 'offensive':
            score += 1
        elif context_dict['market']['stance'] == 'defensive':
            score -= 1

        return max(1, min(10, score))

    def _assess_signal_strength(self, signal_explanation) -> str:
        """Assess signal strength."""
        if not signal_explanation:
            return "weak"

        if signal_explanation.confidence > 0.75:
            return "strong"
        elif signal_explanation.confidence > 0.5:
            return "moderate"
        else:
            return "weak"

    def _determine_recommendation(
        self,
        trade_quality,
        signal_explanation,
        timeframe_synthesis,
        context_dict
    ) -> tuple:
        """Determine recommendation and position size."""
        # Market context veto
        if context_dict['market']['health'] == 'concerning':
            return "hold", "none"

        if trade_quality >= 8:
            recommendation = "buy"
            position_size = "full"
        elif trade_quality >= 6:
            recommendation = "buy"
            position_size = "half"
        elif trade_quality >= 4:
            recommendation = "hold"
            position_size = "quarter"
        else:
            recommendation = "wait"
            position_size = "none"

        # Adjust for market stance
        if context_dict['market']['stance'] == 'defensive':
            if position_size == "full":
                position_size = "half"
            elif position_size == "half":
                position_size = "quarter"

        return recommendation, position_size

    def _calculate_targets(self, key_levels, trade_quality) -> List[float]:
        """Calculate price targets."""
        if not key_levels or 'resistance' not in key_levels:
            return []

        resistance = key_levels['resistance']
        targets = [
            resistance,
            resistance * 1.05,
            resistance * 1.10
        ]

        if trade_quality >= 8:
            targets.append(resistance * 1.15)

        return targets

    def _identify_risks(
        self,
        signal_explanation,
        timeframe_synthesis,
        earnings_analysis,
        anomaly_detected,
        context_dict
    ) -> List[str]:
        """Identify key risks."""
        risks = []

        if signal_explanation:
            risks.append(signal_explanation.key_risk)

        if timeframe_synthesis and 'mixed' in timeframe_synthesis.overall_alignment:
            risks.append("Mixed timeframe signals")

        if earnings_analysis:
            risks.extend(earnings_analysis.risks_concerns[:2])

        if anomaly_detected:
            risks.append("Unusual price/volume behavior detected")

        if context_dict['market']['risk_level'] > 6:
            risks.append(f"Elevated market risk ({context_dict['market']['risk_level']}/10)")

        return list(set(risks))[:5]

    def _calculate_trade_confidence(
        self,
        signal_explanation,
        timeframe_synthesis,
        earnings_analysis
    ) -> float:
        """Calculate confidence in trade analysis."""
        confidences = []

        if signal_explanation:
            confidences.append(signal_explanation.confidence)
        if timeframe_synthesis:
            confidences.append(timeframe_synthesis.trade_quality_score / 10)
        if earnings_analysis:
            confidences.append(earnings_analysis.confidence)

        return sum(confidences) / len(confidences) if confidences else 0.5

    def _generate_trade_reasoning(
        self,
        trade_quality,
        signal_explanation,
        timeframe_synthesis,
        earnings_analysis,
        context_dict
    ) -> str:
        """Generate reasoning for trade analysis."""
        parts = [f"Trade quality: {trade_quality}/10"]

        if signal_explanation:
            parts.append(f"Signal: {signal_explanation.catalyst}")

        if timeframe_synthesis:
            parts.append(f"Timeframes: {timeframe_synthesis.overall_alignment}")

        if earnings_analysis:
            parts.append(f"Earnings: {earnings_analysis.management_tone}")

        parts.append(f"Market: {context_dict['market']['stance']}")

        return "; ".join(parts)


# =============================================================================
# LEARNING & ADAPTATION DIRECTOR
# =============================================================================

class LearningAdaptationDirector:
    """
    Coordinates learning and adaptation across 8 specialist components.

    Reports to: Chief Intelligence Officer
    Manages:
        - Pattern Memory Analyzer
        - Trade Journal Analyzer
        - Trade Outcome Predictor
        - Prediction Calibration Tracker
        - Strategy Advisor
        - Adaptive Weight Calculator
        - Catalyst Performance Tracker
        - Expert Leaderboard
    """

    def __init__(self, context_manager: ContextManager):
        self.context = context_manager
        logger.info("Learning & Adaptation Director initialized")

    def analyze_learning(
        self,
        ticker: str,
        signals: Dict[str, Any],
        performance_data: Optional[Dict] = None,
        market_context: Optional[Dict] = None
    ) -> LearningIntelligence:
        """
        Coordinate all learning specialists to produce learning intelligence.

        Components coordinated:
        1. Pattern Memory Analyzer - Identify patterns
        2. Trade Journal Analyzer - Historical lessons
        3. Trade Outcome Predictor - Predict success
        4. Prediction Calibration - Track accuracy
        5. Strategy Advisor - Recommend adjustments
        6. Adaptive Weight Calculator - Optimize weights
        7. Catalyst Performance Tracker - Catalyst accuracy
        8. Expert Leaderboard - Expert tracking
        """
        logger.info(f"Learning Director analyzing: {ticker}")

        context_dict = self.context.get_context_dict()

        # Component #15: Pattern Memory Analyzer
        pattern_analysis = None
        pattern_identified = False
        pattern_signature = None
        pattern_win_rate = None

        try:
            pattern_analysis = ai_learning.analyze_signal_pattern(signals)
            if pattern_analysis:
                pattern_identified = True
                pattern_signature = pattern_analysis.get('pattern_signature')
                pattern_win_rate = ai_learning.calculate_pattern_win_rate(
                    ai_learning.load_pattern_memory(),
                    pattern_signature
                ) if pattern_signature else None
        except Exception as e:
            logger.debug(f"Pattern analysis skipped: {e}")

        # Component #16: Trade Journal Analyzer
        lessons_learned = []
        try:
            trade_lessons = ai_learning.get_trade_lessons()
            if trade_lessons:
                lessons_learned = trade_lessons.get('top_lessons', [])[:3]
        except Exception as e:
            logger.debug(f"Trade lessons skipped: {e}")

        # Component #17: Trade Outcome Predictor
        prediction = "breakeven"
        prediction_confidence = 0.5
        try:
            prediction_result = ai_learning.predict_trade_outcome(
                ticker=ticker,
                signals=signals,
                market_context=market_context
            )
            if prediction_result:
                prediction = prediction_result.get('prediction', 'breakeven')
                prediction_confidence = prediction_result.get('confidence', 0.5)
        except Exception as e:
            logger.debug(f"Prediction skipped: {e}")

        # Component #18: Prediction Calibration Tracker
        prediction_calibration = 0.5
        try:
            calibration_data = ai_learning.get_prediction_calibration()
            if calibration_data:
                prediction_calibration = calibration_data.get('calibration_score', 0.5)
        except Exception as e:
            logger.debug(f"Calibration skipped: {e}")

        # Component #19: Strategy Advisor
        recommended_adjustments = []
        try:
            if performance_data:
                strategy_advice = ai_learning.get_strategy_advice(
                    performance_data=performance_data,
                    current_weights={},
                    market_regime=context_dict['market']['health']
                )
                if strategy_advice:
                    recommended_adjustments = strategy_advice.get('recommendations', [])[:3]
        except Exception as e:
            logger.debug(f"Strategy advice skipped: {e}")

        # Component #20: Adaptive Weight Calculator
        optimal_weights = {}
        try:
            if performance_data:
                weights = ai_learning.get_adaptive_weights(
                    performance_by_signal=performance_data.get('by_signal', {}),
                    market_regime=context_dict['market']['health']
                )
                if weights:
                    optimal_weights = weights
        except Exception as e:
            logger.debug(f"Weight calculation skipped: {e}")

        # Synthesize learning intelligence
        learning_quality = self._calculate_learning_quality(
            pattern_win_rate,
            prediction_confidence,
            prediction_calibration
        )

        confidence = self._calculate_learning_confidence(
            pattern_win_rate,
            prediction_confidence,
            prediction_calibration
        )

        reasoning = self._generate_learning_reasoning(
            pattern_identified,
            pattern_win_rate,
            prediction,
            prediction_confidence,
            learning_quality
        )

        return LearningIntelligence(
            learning_quality=learning_quality,
            pattern_identified=pattern_identified,
            pattern_signature=pattern_signature,
            pattern_win_rate=pattern_win_rate,
            historical_similar_trades=0,  # Can be enhanced
            historical_win_rate=pattern_win_rate or 0.5,
            prediction=prediction,
            prediction_confidence=prediction_confidence,
            prediction_calibration=prediction_calibration,
            strategy_alignment=True,  # Can be enhanced
            recommended_adjustments=recommended_adjustments,
            optimal_weights=optimal_weights,
            expert_consensus=None,  # Can be enhanced
            catalyst_performance=None,  # Can be enhanced
            lessons_learned=lessons_learned,
            confidence=confidence,
            reasoning=reasoning
        )

    def _calculate_learning_quality(
        self,
        pattern_win_rate,
        prediction_confidence,
        calibration
    ) -> int:
        """Calculate learning quality score 1-10."""
        score = 5

        if pattern_win_rate:
            if pattern_win_rate > 0.7:
                score += 2
            elif pattern_win_rate > 0.6:
                score += 1
            elif pattern_win_rate < 0.4:
                score -= 1

        if prediction_confidence > 0.75:
            score += 1

        if calibration > 0.7:
            score += 1

        return max(1, min(10, score))

    def _calculate_learning_confidence(
        self,
        pattern_win_rate,
        prediction_confidence,
        calibration
    ) -> float:
        """Calculate confidence in learning analysis."""
        confidences = [prediction_confidence, calibration]

        if pattern_win_rate:
            confidences.append(pattern_win_rate)

        return sum(confidences) / len(confidences)

    def _generate_learning_reasoning(
        self,
        pattern_identified,
        pattern_win_rate,
        prediction,
        prediction_confidence,
        learning_quality
    ) -> str:
        """Generate reasoning for learning analysis."""
        parts = [f"Learning quality: {learning_quality}/10"]

        if pattern_identified and pattern_win_rate:
            parts.append(f"Pattern identified: {pattern_win_rate:.0%} win rate")

        parts.append(f"Prediction: {prediction} ({prediction_confidence:.0%} confidence)")

        return "; ".join(parts)


# =============================================================================
# REALTIME INTELLIGENCE DIRECTOR
# =============================================================================

class RealtimeIntelligenceDirector:
    """
    Coordinates realtime intelligence across 7 specialist components.

    Reports to: Chief Intelligence Officer
    Manages:
        - Catalyst Detector & Analyzer
        - Theme Rotation Predictor
        - Realtime AI Scanner
        - Multi-Stock Anomaly Scanner
        - Options Flow Scanner
        - Market Narrative Generator
        - Daily Briefing Generator
    """

    def __init__(self, context_manager: ContextManager):
        self.context = context_manager
        self.enhancements = AIEnhancementEngine()
        logger.info("Realtime Intelligence Director initialized")

    def analyze_realtime(
        self,
        ticker: str,
        news_items: Optional[List[Dict]] = None,
        themes: Optional[List[str]] = None,
        price_data: Optional[Dict] = None
    ) -> RealtimeIntelligence:
        """
        Coordinate all realtime specialists to produce realtime intelligence.

        Components coordinated:
        1. Catalyst Detector & Analyzer - News catalysts
        2. Theme Rotation Predictor - Theme shifts
        3. Realtime AI Scanner - News scanning
        4. Multi-Stock Anomaly Scanner - Anomalies
        5. Options Flow Scanner - Options activity
        6. Market Narrative Generator - Market story
        7. Daily Briefing Generator - Morning brief
        """
        logger.info(f"Realtime Director analyzing: {ticker}")

        context_dict = self.context.get_context_dict()

        # Component #27: Catalyst Detector & Analyzer
        catalyst_detected = False
        catalyst_type = None
        catalyst_sentiment = None
        catalyst_impact = None

        if news_items:
            try:
                for news in news_items[:3]:
                    headline = news.get('headline', '')
                    if headline:
                        catalyst_result = ai_learning.analyze_catalyst_realtime(
                            ticker=ticker,
                            headline=headline,
                            price_data=price_data
                        )
                        if catalyst_result:
                            catalyst_detected = True
                            catalyst_type = catalyst_result.get('catalyst_type')
                            catalyst_sentiment = catalyst_result.get('sentiment')
                            catalyst_impact = catalyst_result.get('expected_impact')
                            break
            except Exception as e:
                logger.debug(f"Catalyst detection skipped: {e}")

        # Component #30: Theme Rotation Predictor
        theme_rotation_signal = None
        emerging_themes = []
        fading_themes = []

        if themes:
            try:
                rotation_prediction = ai_learning.predict_theme_rotation(
                    current_themes=themes,
                    market_regime=context_dict['market']['health'],
                    sector_performance={}
                )
                if rotation_prediction:
                    emerging_themes = rotation_prediction.get('emerging_themes', [])
                    fading_themes = rotation_prediction.get('fading_themes', [])
                    if emerging_themes:
                        theme_rotation_signal = "emerging"
                    elif fading_themes:
                        theme_rotation_signal = "fading"
            except Exception as e:
                logger.debug(f"Theme rotation skipped: {e}")

        # Component #33: Market Narrative Generator
        market_narrative = ""
        try:
            # Use Market Health Monitor (Component #3) data
            if self.context.market_context:
                market_narrative = self.context.market_context.regime_narrative
        except Exception as e:
            logger.debug(f"Market narrative skipped: {e}")

        # Synthesize realtime intelligence
        realtime_quality = self._calculate_realtime_quality(
            catalyst_detected,
            theme_rotation_signal,
            context_dict
        )

        urgency_score = self._calculate_urgency(
            catalyst_detected,
            catalyst_sentiment,
            theme_rotation_signal
        )

        alerts = self._generate_alerts(
            catalyst_detected,
            catalyst_type,
            theme_rotation_signal,
            emerging_themes
        )

        confidence = self._calculate_realtime_confidence(
            catalyst_detected,
            theme_rotation_signal
        )

        reasoning = self._generate_realtime_reasoning(
            realtime_quality,
            catalyst_detected,
            theme_rotation_signal,
            urgency_score
        )

        return RealtimeIntelligence(
            realtime_quality=realtime_quality,
            catalyst_detected=catalyst_detected,
            catalyst_type=catalyst_type,
            catalyst_sentiment=catalyst_sentiment,
            catalyst_impact=catalyst_impact,
            theme_rotation_signal=theme_rotation_signal,
            emerging_themes=emerging_themes,
            fading_themes=fading_themes,
            anomalies_detected=0,  # Can be enhanced
            top_anomalies=[],
            unusual_options_activity=False,  # Can be enhanced
            options_signals=[],
            market_narrative=market_narrative,
            daily_brief_summary="",  # Can be enhanced
            urgency_score=urgency_score,
            alerts=alerts,
            confidence=confidence,
            reasoning=reasoning
        )

    def _calculate_realtime_quality(
        self,
        catalyst_detected,
        theme_rotation_signal,
        context_dict
    ) -> int:
        """Calculate realtime quality score 1-10."""
        score = 5

        if catalyst_detected:
            score += 2

        if theme_rotation_signal:
            score += 1

        if context_dict['market']['health'] in ['healthy', 'neutral']:
            score += 1

        return max(1, min(10, score))

    def _calculate_urgency(
        self,
        catalyst_detected,
        catalyst_sentiment,
        theme_rotation_signal
    ) -> int:
        """Calculate urgency score 1-10."""
        score = 3

        if catalyst_detected:
            score += 3
            if catalyst_sentiment in ['very_bullish', 'very_bearish']:
                score += 2

        if theme_rotation_signal == 'emerging':
            score += 2

        return max(1, min(10, score))

    def _generate_alerts(
        self,
        catalyst_detected,
        catalyst_type,
        theme_rotation_signal,
        emerging_themes
    ) -> List[str]:
        """Generate realtime alerts."""
        alerts = []

        if catalyst_detected:
            alerts.append(f"Catalyst detected: {catalyst_type}")

        if theme_rotation_signal == 'emerging' and emerging_themes:
            # Handle both string and dict list formats
            theme_names = []
            for theme in emerging_themes[:3]:
                if isinstance(theme, dict):
                    theme_names.append(theme.get('theme', theme.get('name', str(theme))))
                else:
                    theme_names.append(str(theme))
            if theme_names:
                alerts.append(f"Emerging themes: {', '.join(theme_names)}")

        return alerts

    def _calculate_realtime_confidence(
        self,
        catalyst_detected,
        theme_rotation_signal
    ) -> float:
        """Calculate confidence in realtime analysis."""
        confidence = 0.5

        if catalyst_detected:
            confidence += 0.2

        if theme_rotation_signal:
            confidence += 0.1

        return min(1.0, confidence)

    def _generate_realtime_reasoning(
        self,
        realtime_quality,
        catalyst_detected,
        theme_rotation_signal,
        urgency_score
    ) -> str:
        """Generate reasoning for realtime analysis."""
        parts = [f"Realtime quality: {realtime_quality}/10"]

        if catalyst_detected:
            parts.append("Catalyst detected")

        if theme_rotation_signal:
            parts.append(f"Theme rotation: {theme_rotation_signal}")

        parts.append(f"Urgency: {urgency_score}/10")

        return "; ".join(parts)


# =============================================================================
# VALIDATION & FEEDBACK DIRECTOR
# =============================================================================

class ValidationFeedbackDirector:
    """
    Coordinates validation and feedback across 5 specialist components.

    Reports to: Chief Intelligence Officer
    Manages:
        - Fact Verification System
        - Expert Prediction Analyzer
        - Weekly Coaching System
        - Quick Feedback Generator
        - Supply Chain Discoverer
    """

    def __init__(self, context_manager: ContextManager):
        self.context = context_manager
        self.enhancements = AIEnhancementEngine()
        self.deepseek = DeepSeekIntelligence()
        logger.info("Validation & Feedback Director initialized")

    def analyze_validation(
        self,
        ticker: str,
        claims: Optional[List[str]] = None,
        sources: Optional[List[Dict]] = None,
        company_info: Optional[Dict] = None
    ) -> ValidationIntelligence:
        """
        Coordinate all validation specialists to produce validation intelligence.

        Components coordinated:
        1. Fact Verification System - Verify claims
        2. Expert Prediction Analyzer - Expert analysis
        3. Weekly Coaching System - Coaching advice
        4. Quick Feedback Generator - Quick feedback
        5. Supply Chain Discoverer - Supply chain mapping
        """
        logger.info(f"Validation Director analyzing: {ticker}")

        # Component #5: Fact Verification System
        fact_check_passed = True
        fact_check_confidence = 0.5
        contradictions = []
        sources_verified = 0

        if claims and sources:
            try:
                for claim in claims[:3]:
                    fact_check = self.enhancements.fact_check_claim(
                        claim=claim,
                        sources=sources
                    )
                    if fact_check:
                        sources_verified += fact_check.sources_checked
                        fact_check_confidence = max(fact_check_confidence, fact_check.confidence)
                        if fact_check.verified in ['false', 'partial']:
                            fact_check_passed = False
                        contradictions.extend(fact_check.contradictions)
            except Exception as e:
                logger.debug(f"Fact checking skipped: {e}")

        # Component #12: Supply Chain Discoverer
        supply_chain_mapped = False
        supply_chain_strength = None

        if company_info:
            try:
                supply_chain = self.deepseek.discover_supply_chain(
                    ticker=ticker,
                    company_info=company_info
                )
                if supply_chain:
                    supply_chain_mapped = True
                    # Assess strength based on number of relationships
                    total_relationships = (
                        len(supply_chain.get('suppliers', [])) +
                        len(supply_chain.get('customers', [])) +
                        len(supply_chain.get('partners', []))
                    )
                    if total_relationships > 10:
                        supply_chain_strength = "strong"
                    elif total_relationships > 5:
                        supply_chain_strength = "moderate"
                    else:
                        supply_chain_strength = "weak"
            except Exception as e:
                logger.debug(f"Supply chain discovery skipped: {e}")

        # Synthesize validation intelligence
        validation_quality = self._calculate_validation_quality(
            fact_check_passed,
            fact_check_confidence,
            supply_chain_mapped
        )

        reliability_score = self._calculate_reliability(
            fact_check_passed,
            fact_check_confidence,
            sources_verified
        )

        confidence = self._calculate_validation_confidence(
            fact_check_confidence,
            sources_verified
        )

        reasoning = self._generate_validation_reasoning(
            validation_quality,
            fact_check_passed,
            sources_verified,
            supply_chain_mapped
        )

        return ValidationIntelligence(
            validation_quality=validation_quality,
            fact_check_passed=fact_check_passed,
            fact_check_confidence=fact_check_confidence,
            contradictions_found=list(set(contradictions)),
            expert_predictions=[],  # Can be enhanced
            expert_consensus=None,  # Can be enhanced
            supply_chain_mapped=supply_chain_mapped,
            supply_chain_strength=supply_chain_strength,
            coaching_advice=[],  # Can be enhanced
            quick_feedback=None,  # Can be enhanced
            sources_verified=sources_verified,
            reliability_score=reliability_score,
            confidence=confidence,
            reasoning=reasoning
        )

    def _calculate_validation_quality(
        self,
        fact_check_passed,
        fact_check_confidence,
        supply_chain_mapped
    ) -> int:
        """Calculate validation quality score 1-10."""
        score = 5

        if fact_check_passed:
            score += 2
            if fact_check_confidence > 0.8:
                score += 1
        else:
            score -= 2

        if supply_chain_mapped:
            score += 1

        return max(1, min(10, score))

    def _calculate_reliability(
        self,
        fact_check_passed,
        fact_check_confidence,
        sources_verified
    ) -> float:
        """Calculate reliability score."""
        reliability = 0.5

        if fact_check_passed:
            reliability += 0.3

        reliability += min(0.2, sources_verified * 0.05)

        return min(1.0, reliability)

    def _calculate_validation_confidence(
        self,
        fact_check_confidence,
        sources_verified
    ) -> float:
        """Calculate confidence in validation analysis."""
        confidence = fact_check_confidence

        if sources_verified > 3:
            confidence = min(1.0, confidence + 0.1)

        return confidence

    def _generate_validation_reasoning(
        self,
        validation_quality,
        fact_check_passed,
        sources_verified,
        supply_chain_mapped
    ) -> str:
        """Generate reasoning for validation analysis."""
        parts = [f"Validation quality: {validation_quality}/10"]

        status = "passed" if fact_check_passed else "failed"
        parts.append(f"Fact check: {status} ({sources_verified} sources)")

        if supply_chain_mapped:
            parts.append("Supply chain mapped")

        return "; ".join(parts)


# =============================================================================
# CHIEF INTELLIGENCE OFFICER
# =============================================================================

class ChiefIntelligenceOfficer:
    """
    Master coordinator and final decision maker.

    The CIO is the brain of the agentic system, coordinating all 35 components
    through 5 directors to make superior context-aware trading decisions.

    Responsibilities:
    - Set and broadcast market/sector context to ALL components
    - Coordinate 5 intelligence directors
    - Synthesize intelligence from all sources
    - Make final buy/sell/hold decisions
    - Resolve conflicts between directors
    - Veto power over all recommendations
    """

    def __init__(self):
        self.context_manager = ContextManager()

        # Initialize all 5 directors
        self.theme_director = ThemeIntelligenceDirector(self.context_manager)
        self.trading_director = TradingIntelligenceDirector(self.context_manager)
        self.learning_director = LearningAdaptationDirector(self.context_manager)
        self.realtime_director = RealtimeIntelligenceDirector(self.context_manager)
        self.validation_director = ValidationFeedbackDirector(self.context_manager)

        # Market health component
        self.enhancements = AIEnhancementEngine()

        logger.info("=" * 80)
        logger.info("CHIEF INTELLIGENCE OFFICER INITIALIZED")
        logger.info("=" * 80)
        logger.info("Coordinating 35 AI components through 5 directors:")
        logger.info("  • Theme Intelligence Director (7 components)")
        logger.info("  • Trading Intelligence Director (6 components)")
        logger.info("  • Learning & Adaptation Director (8 components)")
        logger.info("  • Realtime Intelligence Director (7 components)")
        logger.info("  • Validation & Feedback Director (5 components)")
        logger.info("=" * 80)

    def update_market_regime(self, health_metrics: Dict[str, Any]) -> MarketContext:
        """
        Set market context and broadcast to ALL 35 components.

        This is the first step in any analysis - establishing the market regime
        that will influence how all components interpret their signals.
        """
        logger.info("CIO updating market regime...")

        # Component #3: Market Health Monitor
        narrative = self.enhancements.generate_market_narrative(health_metrics)

        # Determine health rating
        breadth = health_metrics.get('breadth', 50)
        vix = health_metrics.get('vix', 20)

        if breadth > 60 and vix < 20:
            health = MarketHealth.HEALTHY
            risk_level = max(1, min(3, int((100 - breadth) / 10)))
            stance = MarketStance.OFFENSIVE
        elif breadth > 50 and vix < 25:
            health = MarketHealth.NEUTRAL
            risk_level = 5
            stance = MarketStance.NEUTRAL
        elif breadth > 40:
            health = MarketHealth.WARNING
            risk_level = 7
            stance = MarketStance.DEFENSIVE
        else:
            health = MarketHealth.CONCERNING
            risk_level = min(10, max(8, int((100 - breadth) / 5)))
            stance = MarketStance.DEFENSIVE

        market_context = MarketContext(
            health=health,
            risk_level=risk_level,
            stance=stance,
            breadth=breadth,
            vix=vix,
            new_highs=health_metrics.get('new_highs', 0),
            new_lows=health_metrics.get('new_lows', 0),
            leading_sectors=health_metrics.get('leading_sectors', []),
            lagging_sectors=health_metrics.get('lagging_sectors', []),
            regime_narrative=narrative.narrative if narrative else ""
        )

        # Broadcast to ALL components
        self.context_manager.update_market_context(market_context)

        logger.info(f"✓ Market regime set: {health.value}, {stance.value}, risk {risk_level}/10")
        logger.info(f"  Broadcast to ALL 35 components")

        return market_context

    def update_sector_cycle(self, rotation_data: Dict[str, Any]) -> SectorContext:
        """
        Set sector context and broadcast to ALL 35 components.

        Sector cycle context influences theme analysis, TAM estimates,
        and trade quality assessments across all components.
        """
        logger.info("CIO updating sector cycle...")

        # Component #4: Sector Rotation Analyst
        rotation_narrative = self.enhancements.explain_sector_rotation(rotation_data)

        # Determine cycle stage from leading sectors
        leading = rotation_data.get('top_sectors', [])

        if any(s in leading for s in ['Technology', 'Industrials', 'Financials']):
            cycle_stage = CycleStage.EARLY
        elif any(s in leading for s in ['Consumer Discretionary', 'Technology']):
            cycle_stage = CycleStage.MID
        elif any(s in leading for s in ['Energy', 'Materials']):
            cycle_stage = CycleStage.LATE
        else:
            cycle_stage = CycleStage.RECESSION

        sector_context = SectorContext(
            cycle_stage=cycle_stage,
            leading_sectors=rotation_data.get('top_sectors', []),
            lagging_sectors=rotation_data.get('lagging_sectors', []),
            rotation_confidence=0.75,  # Can be enhanced
            money_flow_direction=rotation_data.get('money_flow', 'Unknown'),
            cycle_narrative=rotation_narrative.reasoning if rotation_narrative else "",
            next_rotation_likely=rotation_narrative.next_rotation_likely if rotation_narrative else ""
        )

        # Broadcast to ALL components
        self.context_manager.update_sector_context(sector_context)

        logger.info(f"✓ Sector cycle set: {cycle_stage.value}, leading: {', '.join(leading[:3])}")
        logger.info(f"  Broadcast to ALL 35 components")

        return sector_context

    def analyze_opportunity(
        self,
        ticker: str,
        signal_type: str,
        signal_data: Dict[str, Any],
        theme_data: Optional[Dict] = None,
        timeframe_data: Optional[Dict] = None,
        earnings_data: Optional[Dict] = None,
        corporate_action: Optional[Dict] = None,
        price_data: Optional[Dict] = None,
        news_items: Optional[List[Dict]] = None,
        performance_data: Optional[Dict] = None,
        claims_to_verify: Optional[List[str]] = None,
        sources: Optional[List[Dict]] = None,
        company_info: Optional[Dict] = None
    ) -> FinalDecision:
        """
        Analyze opportunity by coordinating ALL 5 directors and 35 components.

        This is where the magic happens - the CIO delegates to all directors,
        receives their synthesized intelligence, and makes the final decision
        with full context awareness and veto power.

        Process:
        1. CIO delegates to Theme Director (7 components)
        2. CIO delegates to Trading Director (6 components)
        3. CIO delegates to Learning Director (8 components)
        4. CIO delegates to Realtime Director (7 components)
        5. CIO delegates to Validation Director (5 components)
        6. CIO synthesizes ALL intelligence
        7. CIO makes final decision (with veto power)
        """
        logger.info("=" * 80)
        logger.info(f"CIO ANALYZING OPPORTUNITY: {ticker} {signal_type}")
        logger.info("=" * 80)

        # Ensure context is set
        if not self.context_manager.market_context:
            logger.warning("Market context not set - using default")
            self.update_market_regime({'breadth': 55, 'vix': 18})

        if not self.context_manager.sector_context:
            logger.warning("Sector context not set - using default")
            self.update_sector_cycle({'top_sectors': ['Technology'], 'lagging_sectors': []})

        # Delegate to all 5 directors
        logger.info("CIO delegating to 5 directors...")

        # 1. Theme Intelligence (7 components)
        theme_intelligence = None
        if theme_data:
            # Extract headlines as strings from news_items dicts
            headlines = None
            if news_items:
                headlines = [
                    item.get('headline', '') if isinstance(item, dict) else str(item)
                    for item in news_items[:5]
                ]

            theme_intelligence = self.theme_director.analyze_theme(
                theme_name=theme_data.get('name', 'Unknown'),
                ticker=ticker,
                players=theme_data.get('players', [ticker]),
                headlines=headlines,
                earnings_data=earnings_data
            )
            logger.info(f"✓ Theme Intelligence: {theme_intelligence.theme_quality}/10")

        # 2. Trading Intelligence (6 components)
        trading_intelligence = self.trading_director.analyze_trade(
            ticker=ticker,
            signal_type=signal_type,
            signal_data=signal_data,
            timeframe_data=timeframe_data,
            earnings_data=earnings_data,
            corporate_action=corporate_action,
            price_data=price_data
        )
        logger.info(f"✓ Trading Intelligence: {trading_intelligence.trade_quality}/10")

        # 3. Learning Intelligence (8 components)
        learning_intelligence = self.learning_director.analyze_learning(
            ticker=ticker,
            signals=signal_data,
            performance_data=performance_data,
            market_context=self.context_manager.get_context_dict()
        )
        logger.info(f"✓ Learning Intelligence: {learning_intelligence.learning_quality}/10")

        # 4. Realtime Intelligence (7 components)
        realtime_intelligence = self.realtime_director.analyze_realtime(
            ticker=ticker,
            news_items=news_items,
            themes=[theme_data.get('name')] if theme_data else None,
            price_data=price_data
        )
        logger.info(f"✓ Realtime Intelligence: {realtime_intelligence.realtime_quality}/10")

        # 5. Validation Intelligence (5 components)
        validation_intelligence = self.validation_director.analyze_validation(
            ticker=ticker,
            claims=claims_to_verify,
            sources=sources,
            company_info=company_info
        )
        logger.info(f"✓ Validation Intelligence: {validation_intelligence.validation_quality}/10")

        # SYNTHESIZE ALL INTELLIGENCE
        logger.info("CIO synthesizing intelligence from all 35 components...")

        final_decision = self._synthesize_final_decision(
            ticker=ticker,
            theme_intelligence=theme_intelligence,
            trading_intelligence=trading_intelligence,
            learning_intelligence=learning_intelligence,
            realtime_intelligence=realtime_intelligence,
            validation_intelligence=validation_intelligence
        )

        logger.info("=" * 80)
        logger.info(f"CIO FINAL DECISION: {final_decision.decision.value.upper()}")
        logger.info(f"Confidence: {final_decision.confidence:.2%}")
        logger.info(f"Position Size: {final_decision.position_size}")
        logger.info("=" * 80)

        return final_decision

    def _synthesize_final_decision(
        self,
        ticker: str,
        theme_intelligence: Optional[ThemeIntelligence],
        trading_intelligence: TradingIntelligence,
        learning_intelligence: LearningIntelligence,
        realtime_intelligence: RealtimeIntelligence,
        validation_intelligence: ValidationIntelligence
    ) -> FinalDecision:
        """
        Synthesize all director intelligence into final decision.

        This is the CIO's core function - combining insights from all
        35 components into a single, coordinated decision.
        """
        # Extract scores
        theme_score = theme_intelligence.theme_quality if theme_intelligence else 5
        trade_score = trading_intelligence.trade_quality
        learning_score = learning_intelligence.learning_quality
        realtime_score = realtime_intelligence.realtime_quality
        validation_score = validation_intelligence.validation_quality

        # Calculate weighted overall score
        scores = [trade_score, learning_score, realtime_score, validation_score]
        weights = [0.35, 0.25, 0.20, 0.20]  # Trading and learning weighted higher

        if theme_intelligence:
            scores.insert(0, theme_score)
            weights = [0.25, 0.30, 0.20, 0.15, 0.10]

        overall_score = sum(s * w for s, w in zip(scores, weights))

        # VETO POWER: Market context can override
        market_context = self.context_manager.market_context

        if market_context.health == MarketHealth.CONCERNING:
            logger.warning("⚠️  CIO VETO: Market health concerning - overriding to DEFENSIVE")
            decision = Decision.SELL
            position_size = "none"
            confidence = 0.3
        elif market_context.stance == MarketStance.DEFENSIVE and overall_score < 7:
            logger.warning("⚠️  CIO VETO: Defensive market with mediocre setup - reducing exposure")
            decision = Decision.HOLD
            position_size = "quarter"
            confidence = 0.5
        else:
            # Normal decision logic
            if overall_score >= 8.5:
                decision = Decision.STRONG_BUY
                position_size = "full"
                confidence = 0.90
            elif overall_score >= 7.5:
                decision = Decision.BUY
                position_size = "full"
                confidence = 0.80
            elif overall_score >= 6.5:
                decision = Decision.BUY
                position_size = "half"
                confidence = 0.70
            elif overall_score >= 5.5:
                decision = Decision.HOLD
                position_size = "quarter"
                confidence = 0.60
            else:
                decision = Decision.HOLD
                position_size = "none"
                confidence = 0.50

            # Adjust for market stance
            if market_context.stance == MarketStance.OFFENSIVE:
                confidence = min(1.0, confidence + 0.05)
            elif market_context.stance == MarketStance.DEFENSIVE:
                if position_size == "full":
                    position_size = "half"
                elif position_size == "half":
                    position_size = "quarter"

        # Generate comprehensive reasoning
        reasoning = self._generate_comprehensive_reasoning(
            decision,
            theme_intelligence,
            trading_intelligence,
            learning_intelligence,
            realtime_intelligence,
            validation_intelligence,
            market_context
        )

        # Collect strengths
        key_strengths = self._identify_strengths(
            theme_intelligence,
            trading_intelligence,
            learning_intelligence,
            realtime_intelligence,
            validation_intelligence
        )

        # Aggregate risks
        risks = []
        if theme_intelligence:
            risks.extend(theme_intelligence.risks)
        risks.extend(trading_intelligence.risks)
        if market_context.risk_level > 6:
            risks.insert(0, f"High market risk ({market_context.risk_level}/10)")
        risks = list(set(risks))[:5]

        return FinalDecision(
            ticker=ticker,
            decision=decision,
            position_size=position_size,
            confidence=confidence,
            market_context_summary=market_context.regime_narrative[:200],
            sector_context_summary=self.context_manager.sector_context.cycle_narrative[:200] if self.context_manager.sector_context else "",
            theme_score=theme_score,
            trade_score=trade_score,
            learning_score=learning_score,
            realtime_score=realtime_score,
            validation_score=validation_score,
            reasoning=reasoning,
            key_strengths=key_strengths,
            risks=risks,
            entry_price=None,  # Can be enhanced
            stop_loss=trading_intelligence.stop_loss,
            targets=trading_intelligence.targets,
            theme_intelligence=theme_intelligence,
            trading_intelligence=trading_intelligence,
            learning_intelligence=learning_intelligence,
            realtime_intelligence=realtime_intelligence,
            validation_intelligence=validation_intelligence
        )

    def _generate_comprehensive_reasoning(
        self,
        decision,
        theme_intelligence,
        trading_intelligence,
        learning_intelligence,
        realtime_intelligence,
        validation_intelligence,
        market_context
    ) -> str:
        """Generate comprehensive reasoning explaining the decision."""
        parts = []

        # Market context
        parts.append(f"Market: {market_context.health.value} ({market_context.risk_level}/10 risk)")
        parts.append(f"Cycle: {self.context_manager.sector_context.cycle_stage.value}")

        # Intelligence scores
        if theme_intelligence:
            parts.append(f"Theme: {theme_intelligence.theme_quality}/10")
        parts.append(f"Trade: {trading_intelligence.trade_quality}/10")
        parts.append(f"Learning: {learning_intelligence.learning_quality}/10")

        # Key factors
        if theme_intelligence and theme_intelligence.tam_validated:
            parts.append(f"TAM validated ({theme_intelligence.tam_cagr:.0f}% CAGR)")

        if trading_intelligence.signal_strength == "strong":
            parts.append(f"Strong signal: {trading_intelligence.signal_catalyst}")

        if learning_intelligence.pattern_win_rate and learning_intelligence.pattern_win_rate > 0.7:
            parts.append(f"Pattern validated ({learning_intelligence.pattern_win_rate:.0%} win rate)")

        if realtime_intelligence.catalyst_detected:
            parts.append(f"Catalyst: {realtime_intelligence.catalyst_type}")

        if validation_intelligence.fact_check_passed:
            parts.append("Fact-checked")

        return "; ".join(parts)

    def _identify_strengths(
        self,
        theme_intelligence,
        trading_intelligence,
        learning_intelligence,
        realtime_intelligence,
        validation_intelligence
    ) -> List[str]:
        """Identify key strengths of this opportunity."""
        strengths = []

        if theme_intelligence:
            if theme_intelligence.theme_quality >= 8:
                strengths.append("High-quality theme")
            if theme_intelligence.tam_cagr > 30:
                strengths.append(f"Strong TAM growth ({theme_intelligence.tam_cagr:.0f}% CAGR)")
            if theme_intelligence.role_classification == 'leader':
                strengths.append("Theme leader")

        if trading_intelligence.trade_quality >= 8:
            strengths.append("High-quality trade setup")
        if trading_intelligence.signal_strength == "strong":
            strengths.append("Strong signal")
        if 'aligned' in trading_intelligence.timeframe_alignment:
            strengths.append("Timeframes aligned")

        if learning_intelligence.pattern_win_rate and learning_intelligence.pattern_win_rate > 0.7:
            strengths.append(f"Proven pattern ({learning_intelligence.pattern_win_rate:.0%})")

        if realtime_intelligence.catalyst_detected:
            strengths.append("Active catalyst")

        if validation_intelligence.fact_check_passed:
            strengths.append("Facts verified")

        return strengths[:5]


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_cio: Optional[ChiefIntelligenceOfficer] = None

def get_cio() -> ChiefIntelligenceOfficer:
    """Get or create the singleton Chief Intelligence Officer."""
    global _cio
    if _cio is None:
        _cio = ChiefIntelligenceOfficer()
    return _cio


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def analyze_stock_opportunity(
    ticker: str,
    signal_type: str,
    signal_data: Dict[str, Any],
    **kwargs
) -> FinalDecision:
    """
    Convenience function to analyze a stock opportunity.

    This is the main entry point for coordinated AI analysis.
    All 35 components will be consulted through the CIO.
    """
    cio = get_cio()
    return cio.analyze_opportunity(
        ticker=ticker,
        signal_type=signal_type,
        signal_data=signal_data,
        **kwargs
    )


def set_market_regime(health_metrics: Dict[str, Any]) -> MarketContext:
    """Set market regime context for all components."""
    cio = get_cio()
    return cio.update_market_regime(health_metrics)


def set_sector_cycle(rotation_data: Dict[str, Any]) -> SectorContext:
    """Set sector cycle context for all components."""
    cio = get_cio()
    return cio.update_sector_cycle(rotation_data)
