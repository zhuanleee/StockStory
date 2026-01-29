#!/usr/bin/env python3
"""
Agentic Brain - Hierarchical AI Intelligence System

Architecture:
- Chief Intelligence Officer (CIO) - Master coordinator
- Market Regime Monitor - Market context provider
- Sector Cycle Analyst - Cycle positioning provider
- Theme Intelligence Director - Theme research coordinator
- Trading Intelligence Director - Trade execution coordinator
- 8 Specialist Components - Focused intelligence gathering

Components report to leaders, share context, and work together.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

from src.ai.ai_enhancements import (
    get_ai_enhancements,
    SignalExplanation,
    EarningsAnalysis,
    MarketHealthNarrative,
    SectorRotationNarrative,
    FactCheckResult,
    TimeframeSynthesis,
    TAMAnalysis,
    CorporateActionImpact
)

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS & DATA CLASSES
# =============================================================================

class MarketStance(str, Enum):
    """Market positioning stance."""
    OFFENSIVE = "offensive"
    NEUTRAL = "neutral"
    DEFENSIVE = "defensive"


class CycleStage(str, Enum):
    """Market cycle stage."""
    EARLY = "early"
    MID = "mid"
    LATE = "late"
    RECESSION = "recession"


class Decision(str, Enum):
    """Trading decision."""
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    HOLD = "hold"
    SELL = "sell"
    STRONG_SELL = "strong_sell"


@dataclass
class MarketContext:
    """Shared market context for all components."""
    timestamp: str
    health: str  # healthy/neutral/warning/concerning
    risk_level: int  # 1-10
    stance: MarketStance
    breadth: float
    vix: float
    regime_narrative: str


@dataclass
class SectorContext:
    """Shared sector cycle context."""
    timestamp: str
    cycle_stage: CycleStage
    leading_sectors: List[str]
    lagging_sectors: List[str]
    rotation_confidence: float
    cycle_narrative: str


@dataclass
class ThemeIntelligence:
    """Theme intelligence report from Theme Director."""
    theme_name: str
    tam_analysis: Optional[TAMAnalysis]
    earnings_intelligence: Optional[EarningsAnalysis]
    fact_check_results: List[FactCheckResult]
    theme_score: int  # 1-10
    recommendation: str
    reasoning: str
    confidence: float
    timestamp: str


@dataclass
class TradingIntelligence:
    """Trading intelligence report from Trading Director."""
    ticker: str
    signal_explanation: Optional[SignalExplanation]
    timeframe_synthesis: Optional[TimeframeSynthesis]
    corporate_actions: List[CorporateActionImpact]
    trade_score: int  # 1-10
    execution_recommendation: str
    position_size_suggestion: str  # full/75%/50%/25%/0%
    reasoning: str
    confidence: float
    timestamp: str


@dataclass
class FinalDecision:
    """Final decision from Chief Intelligence Officer."""
    ticker: str
    decision: Decision
    position_size: str
    confidence: float
    reasoning: str
    market_context_summary: str
    sector_context_summary: str
    theme_score: int
    trade_score: int
    risks: List[str]
    stop_loss: Optional[float]
    targets: List[float]
    timestamp: str


# =============================================================================
# CONTEXT MANAGER
# =============================================================================

class ContextManager:
    """
    Manages shared context across all components.

    Provides market and sector context to all specialists.
    """

    def __init__(self):
        self.market_context: Optional[MarketContext] = None
        self.sector_context: Optional[SectorContext] = None
        self._listeners: List = []

    def update_market_context(self, context: MarketContext):
        """Update market context and notify listeners."""
        self.market_context = context
        logger.info(f"Market context updated: {context.health}, stance={context.stance}")
        self._notify_listeners('market_context_updated', context)

    def update_sector_context(self, context: SectorContext):
        """Update sector context and notify listeners."""
        self.sector_context = context
        logger.info(f"Sector context updated: {context.cycle_stage}")
        self._notify_listeners('sector_context_updated', context)

    def get_full_context(self) -> Dict[str, Any]:
        """Get complete context for components."""
        return {
            'market': asdict(self.market_context) if self.market_context else None,
            'sector': asdict(self.sector_context) if self.sector_context else None
        }

    def subscribe(self, listener):
        """Subscribe to context updates."""
        self._listeners.append(listener)

    def _notify_listeners(self, event: str, data: Any):
        """Notify all listeners of context changes."""
        for listener in self._listeners:
            if hasattr(listener, 'on_context_update'):
                try:
                    listener.on_context_update(event, data)
                except Exception as e:
                    logger.error(f"Error notifying listener: {e}")


# =============================================================================
# THEME INTELLIGENCE DIRECTOR
# =============================================================================

class ThemeIntelligenceDirector:
    """
    Coordinates theme-level analysis.

    Reports to: Chief Intelligence Officer
    Manages: TAM Estimator, Fact Checker, Earnings Intelligence
    """

    def __init__(self, context_manager: ContextManager):
        self.context_manager = context_manager
        self.engine = get_ai_enhancements()

    def analyze_theme(
        self,
        theme_name: str,
        players: List[str],
        earnings_data: Optional[Dict] = None,
        claims_to_verify: Optional[List[Dict]] = None
    ) -> ThemeIntelligence:
        """
        Comprehensive theme analysis using all specialists.

        Args:
            theme_name: Investment theme name
            players: Key stocks in theme
            earnings_data: Recent earnings (optional)
            claims_to_verify: Claims to fact-check (optional)

        Returns:
            ThemeIntelligence report
        """
        logger.info(f"Theme Director analyzing: {theme_name}")

        # Get current context
        context = self.context_manager.get_full_context()
        market_context = context.get('market', {})
        sector_context = context.get('sector', {})

        # 1. TAM Analysis (adjusted for cycle stage)
        tam_analysis = None
        try:
            tam_context = f"Market cycle: {sector_context.get('cycle_stage', 'unknown')}"
            tam_analysis = self.engine.analyze_tam_expansion(
                theme=theme_name,
                current_players=players,
                context=tam_context
            )
            logger.info(f"TAM analysis complete: CAGR {tam_analysis.cagr_estimate}%")
        except Exception as e:
            logger.error(f"TAM analysis failed: {e}")

        # 2. Earnings Intelligence (if data provided)
        earnings_intel = None
        if earnings_data:
            try:
                earnings_intel = self.engine.analyze_earnings_call(
                    ticker=earnings_data.get('ticker'),
                    transcript=earnings_data.get('transcript', ''),
                    earnings_data=earnings_data
                )
                logger.info(f"Earnings analysis complete: {earnings_intel.management_tone}")
            except Exception as e:
                logger.error(f"Earnings analysis failed: {e}")

        # 3. Fact Checking (if claims provided)
        fact_check_results = []
        if claims_to_verify:
            for claim_data in claims_to_verify:
                try:
                    result = self.engine.fact_check_claim(
                        claim=claim_data.get('claim', ''),
                        sources=claim_data.get('sources', [])
                    )
                    if result:
                        fact_check_results.append(result)
                except Exception as e:
                    logger.error(f"Fact check failed: {e}")

        # 4. Synthesize theme intelligence
        theme_score = self._calculate_theme_score(
            tam_analysis,
            earnings_intel,
            fact_check_results,
            market_context,
            sector_context
        )

        recommendation = self._generate_recommendation(
            theme_score,
            market_context.get('stance'),
            sector_context.get('cycle_stage')
        )

        reasoning = self._generate_reasoning(
            tam_analysis,
            earnings_intel,
            fact_check_results,
            theme_score
        )

        return ThemeIntelligence(
            theme_name=theme_name,
            tam_analysis=tam_analysis,
            earnings_intelligence=earnings_intel,
            fact_check_results=fact_check_results,
            theme_score=theme_score,
            recommendation=recommendation,
            reasoning=reasoning,
            confidence=self._calculate_confidence(tam_analysis, earnings_intel, fact_check_results),
            timestamp=datetime.now().isoformat()
        )

    def _calculate_theme_score(
        self,
        tam: Optional[TAMAnalysis],
        earnings: Optional[EarningsAnalysis],
        facts: List[FactCheckResult],
        market_ctx: Dict,
        sector_ctx: Dict
    ) -> int:
        """Calculate overall theme score 1-10."""
        score = 5  # Base score

        # TAM contribution (0-3 points)
        if tam:
            if tam.cagr_estimate > 30 and tam.adoption_stage == 'early':
                score += 3
            elif tam.cagr_estimate > 20:
                score += 2
            elif tam.cagr_estimate > 10:
                score += 1

        # Earnings contribution (0-3 points)
        if earnings:
            if earnings.management_tone == 'bullish' and earnings.confidence > 0.8:
                score += 3
            elif earnings.management_tone == 'bullish':
                score += 2
            elif earnings.management_tone == 'neutral':
                score += 1

        # Fact check contribution (0-2 points)
        if facts:
            verified_count = sum(1 for f in facts if f.verified == 'true')
            if verified_count == len(facts):
                score += 2
            elif verified_count > len(facts) / 2:
                score += 1

        # Market context adjustment (-2 to +2)
        if market_ctx.get('health') == 'healthy':
            score += 1
        elif market_ctx.get('health') == 'concerning':
            score -= 2

        # Sector context adjustment (-1 to +1)
        if sector_ctx.get('cycle_stage') == 'early':
            score += 1
        elif sector_ctx.get('cycle_stage') == 'late':
            score -= 1

        return max(1, min(10, score))  # Clamp to 1-10

    def _generate_recommendation(self, score: int, stance: str, cycle: str) -> str:
        """Generate recommendation based on score and context."""
        if score >= 8:
            return "Strong invest"
        elif score >= 6:
            if stance == "offensive":
                return "Invest"
            else:
                return "Watchlist"
        elif score >= 4:
            return "Monitor"
        else:
            return "Avoid"

    def _generate_reasoning(
        self,
        tam: Optional[TAMAnalysis],
        earnings: Optional[EarningsAnalysis],
        facts: List[FactCheckResult],
        score: int
    ) -> str:
        """Generate human-readable reasoning."""
        reasons = []

        if tam:
            reasons.append(f"TAM: {tam.cagr_estimate}% CAGR, {tam.adoption_stage} stage")

        if earnings:
            reasons.append(f"Earnings: {earnings.management_tone} tone")

        if facts:
            verified = sum(1 for f in facts if f.verified == 'true')
            reasons.append(f"Fact check: {verified}/{len(facts)} verified")

        reasons.append(f"Theme score: {score}/10")

        return "; ".join(reasons)

    def _calculate_confidence(
        self,
        tam: Optional[TAMAnalysis],
        earnings: Optional[EarningsAnalysis],
        facts: List[FactCheckResult]
    ) -> float:
        """Calculate overall confidence score."""
        confidences = []

        if tam:
            confidences.append(tam.confidence)
        if earnings:
            confidences.append(earnings.confidence)
        if facts:
            confidences.extend([f.confidence for f in facts])

        return sum(confidences) / len(confidences) if confidences else 0.5


# =============================================================================
# TRADING INTELLIGENCE DIRECTOR
# =============================================================================

class TradingIntelligenceDirector:
    """
    Coordinates trade-level analysis.

    Reports to: Chief Intelligence Officer
    Manages: Signal Explainer, Timeframe Synthesizer, Corporate Action Analyzer
    """

    def __init__(self, context_manager: ContextManager):
        self.context_manager = context_manager
        self.engine = get_ai_enhancements()

    def analyze_trade(
        self,
        ticker: str,
        signal_type: str,
        signal_data: Dict,
        timeframe_data: Optional[Dict] = None,
        corporate_actions: Optional[List[Dict]] = None
    ) -> TradingIntelligence:
        """
        Comprehensive trade analysis using all specialists.

        Args:
            ticker: Stock ticker
            signal_type: Type of signal
            signal_data: Signal metadata
            timeframe_data: Multi-timeframe data (optional)
            corporate_actions: Recent actions (optional)

        Returns:
            TradingIntelligence report
        """
        logger.info(f"Trading Director analyzing: {ticker} {signal_type}")

        # Get current context
        context = self.context_manager.get_full_context()
        market_context = context.get('market', {})
        sector_context = context.get('sector', {})

        # 1. Signal Explanation
        signal_explanation = None
        try:
            signal_explanation = self.engine.explain_signal(
                ticker=ticker,
                signal_type=signal_type,
                signal_data=signal_data
            )
            logger.info(f"Signal explanation complete: confidence {signal_explanation.confidence}")
        except Exception as e:
            logger.error(f"Signal explanation failed: {e}")

        # 2. Timeframe Synthesis (if data provided)
        timeframe_synthesis = None
        if timeframe_data:
            try:
                timeframe_synthesis = self.engine.synthesize_timeframes(
                    ticker=ticker,
                    timeframe_data=timeframe_data
                )
                logger.info(f"Timeframe synthesis complete: score {timeframe_synthesis.trade_quality_score}/10")
            except Exception as e:
                logger.error(f"Timeframe synthesis failed: {e}")

        # 3. Corporate Action Analysis (if actions provided)
        action_analyses = []
        if corporate_actions:
            for action in corporate_actions:
                try:
                    analysis = self.engine.analyze_corporate_action(
                        ticker=ticker,
                        action_type=action.get('type'),
                        details=action.get('details', '')
                    )
                    if analysis:
                        action_analyses.append(analysis)
                except Exception as e:
                    logger.error(f"Corporate action analysis failed: {e}")

        # 4. Synthesize trading intelligence
        trade_score = self._calculate_trade_score(
            signal_explanation,
            timeframe_synthesis,
            action_analyses,
            market_context,
            sector_context
        )

        execution_rec = self._generate_execution_recommendation(
            trade_score,
            market_context.get('stance'),
            market_context.get('risk_level')
        )

        position_size = self._calculate_position_size(
            trade_score,
            market_context.get('risk_level'),
            signal_explanation
        )

        reasoning = self._generate_reasoning(
            signal_explanation,
            timeframe_synthesis,
            action_analyses,
            trade_score
        )

        return TradingIntelligence(
            ticker=ticker,
            signal_explanation=signal_explanation,
            timeframe_synthesis=timeframe_synthesis,
            corporate_actions=action_analyses,
            trade_score=trade_score,
            execution_recommendation=execution_rec,
            position_size_suggestion=position_size,
            reasoning=reasoning,
            confidence=self._calculate_confidence(signal_explanation, timeframe_synthesis),
            timestamp=datetime.now().isoformat()
        )

    def _calculate_trade_score(
        self,
        signal: Optional[SignalExplanation],
        timeframe: Optional[TimeframeSynthesis],
        actions: List[CorporateActionImpact],
        market_ctx: Dict,
        sector_ctx: Dict
    ) -> int:
        """Calculate overall trade score 1-10."""
        score = 5  # Base score

        # Signal quality (0-3 points)
        if signal and signal.confidence > 0.8:
            score += 3
        elif signal and signal.confidence > 0.6:
            score += 2
        elif signal:
            score += 1

        # Timeframe alignment (0-3 points)
        if timeframe:
            if timeframe.trade_quality_score >= 8:
                score += 3
            elif timeframe.trade_quality_score >= 6:
                score += 2
            elif timeframe.trade_quality_score >= 4:
                score += 1

        # Corporate actions (0-2 points)
        bullish_actions = sum(1 for a in actions if a.typical_reaction == 'bullish')
        if bullish_actions > 0:
            score += min(2, bullish_actions)

        # Market context adjustment (-2 to +1)
        if market_ctx.get('health') == 'healthy':
            score += 1
        elif market_ctx.get('health') == 'concerning':
            score -= 2

        # Risk level adjustment
        risk = market_ctx.get('risk_level', 5)
        if risk > 7:
            score -= 1

        return max(1, min(10, score))

    def _generate_execution_recommendation(self, score: int, stance: str, risk: int) -> str:
        """Generate execution recommendation."""
        if score >= 8 and stance == "offensive" and risk <= 5:
            return "Buy now"
        elif score >= 7:
            return "Buy on pullback"
        elif score >= 5:
            return "Watchlist"
        else:
            return "Pass"

    def _calculate_position_size(self, score: int, risk: int, signal: Optional[SignalExplanation]) -> str:
        """Calculate position size suggestion."""
        if score >= 9 and risk <= 3:
            return "full"
        elif score >= 7 and risk <= 5:
            return "75%"
        elif score >= 5 and risk <= 7:
            return "50%"
        elif score >= 4:
            return "25%"
        else:
            return "0%"

    def _generate_reasoning(
        self,
        signal: Optional[SignalExplanation],
        timeframe: Optional[TimeframeSynthesis],
        actions: List[CorporateActionImpact],
        score: int
    ) -> str:
        """Generate human-readable reasoning."""
        reasons = []

        if signal:
            reasons.append(f"Signal: {signal.catalyst[:50]}...")

        if timeframe:
            reasons.append(f"Timeframes: {timeframe.overall_alignment}")

        if actions:
            reasons.append(f"Actions: {len(actions)} pending")

        reasons.append(f"Trade score: {score}/10")

        return "; ".join(reasons)

    def _calculate_confidence(
        self,
        signal: Optional[SignalExplanation],
        timeframe: Optional[TimeframeSynthesis]
    ) -> float:
        """Calculate overall confidence."""
        confidences = []

        if signal:
            confidences.append(signal.confidence)
        if timeframe:
            confidences.append(timeframe.trade_quality_score / 10)

        return sum(confidences) / len(confidences) if confidences else 0.5


# =============================================================================
# CHIEF INTELLIGENCE OFFICER (CIO)
# =============================================================================

class ChiefIntelligenceOfficer:
    """
    Master coordinator and final decision maker.

    Manages:
    - Market Regime Monitor
    - Sector Cycle Analyst
    - Theme Intelligence Director
    - Trading Intelligence Director

    Makes final trading decisions based on all intelligence.
    """

    def __init__(self):
        self.context_manager = ContextManager()
        self.theme_director = ThemeIntelligenceDirector(self.context_manager)
        self.trading_director = TradingIntelligenceDirector(self.context_manager)
        self.engine = get_ai_enhancements()

    def update_market_regime(self, health_metrics: Dict) -> MarketContext:
        """
        Update market regime context.

        Args:
            health_metrics: Market breadth, VIX, etc.

        Returns:
            MarketContext
        """
        # Generate market narrative using Market Health Monitor
        narrative = self.engine.generate_market_narrative(health_metrics)

        if narrative:
            # Map health rating to stance
            stance_map = {
                'healthy': MarketStance.OFFENSIVE,
                'neutral': MarketStance.NEUTRAL,
                'warning': MarketStance.DEFENSIVE,
                'concerning': MarketStance.DEFENSIVE
            }

            # Calculate risk level (1-10)
            risk_level = self._calculate_risk_level(
                health_metrics.get('vix', 15),
                health_metrics.get('breadth', 50),
                narrative.health_rating
            )

            market_context = MarketContext(
                timestamp=datetime.now().isoformat(),
                health=narrative.health_rating,
                risk_level=risk_level,
                stance=stance_map.get(narrative.health_rating, MarketStance.NEUTRAL),
                breadth=health_metrics.get('breadth', 0),
                vix=health_metrics.get('vix', 0),
                regime_narrative=narrative.narrative
            )

            self.context_manager.update_market_context(market_context)
            return market_context

        return None

    def update_sector_cycle(self, rotation_data: Dict) -> SectorContext:
        """
        Update sector cycle context.

        Args:
            rotation_data: Sector performance, rotation patterns

        Returns:
            SectorContext
        """
        # Generate sector narrative using Sector Rotation Analyst
        narrative = self.engine.explain_sector_rotation(rotation_data)

        if narrative:
            # Map cycle stage
            cycle_map = {
                'early': CycleStage.EARLY,
                'mid': CycleStage.MID,
                'late': CycleStage.LATE,
                'recession': CycleStage.RECESSION
            }

            sector_context = SectorContext(
                timestamp=datetime.now().isoformat(),
                cycle_stage=cycle_map.get(narrative.market_cycle_stage, CycleStage.MID),
                leading_sectors=narrative.leading_sectors,
                lagging_sectors=narrative.lagging_sectors,
                rotation_confidence=0.80,  # Could calculate from data
                cycle_narrative=narrative.reasoning
            )

            self.context_manager.update_sector_context(sector_context)
            return sector_context

        return None

    def analyze_opportunity(
        self,
        ticker: str,
        signal_type: str,
        signal_data: Dict,
        theme_data: Optional[Dict] = None,
        timeframe_data: Optional[Dict] = None,
        earnings_data: Optional[Dict] = None,
        corporate_actions: Optional[List[Dict]] = None
    ) -> FinalDecision:
        """
        Master analysis function - coordinates all intelligence.

        Args:
            ticker: Stock ticker
            signal_type: Type of signal
            signal_data: Signal metadata
            theme_data: Theme information (optional)
            timeframe_data: Multi-timeframe data (optional)
            earnings_data: Earnings data (optional)
            corporate_actions: Corporate actions (optional)

        Returns:
            FinalDecision with comprehensive analysis
        """
        logger.info(f"CIO analyzing opportunity: {ticker} {signal_type}")

        # Get Theme Intelligence
        theme_intelligence = None
        if theme_data:
            theme_intelligence = self.theme_director.analyze_theme(
                theme_name=theme_data.get('name', 'Unknown'),
                players=theme_data.get('players', [ticker]),
                earnings_data=earnings_data,
                claims_to_verify=theme_data.get('claims')
            )

        # Get Trading Intelligence
        trading_intelligence = self.trading_director.analyze_trade(
            ticker=ticker,
            signal_type=signal_type,
            signal_data=signal_data,
            timeframe_data=timeframe_data,
            corporate_actions=corporate_actions
        )

        # Synthesize Final Decision
        return self._synthesize_decision(
            ticker=ticker,
            theme_intel=theme_intelligence,
            trading_intel=trading_intelligence
        )

    def _synthesize_decision(
        self,
        ticker: str,
        theme_intel: Optional[ThemeIntelligence],
        trading_intel: TradingIntelligence
    ) -> FinalDecision:
        """Synthesize final trading decision."""
        market_ctx = self.context_manager.market_context
        sector_ctx = self.context_manager.sector_context

        # Calculate final scores
        theme_score = theme_intel.theme_score if theme_intel else 5
        trade_score = trading_intel.trade_score

        # Apply decision matrix
        decision = self._apply_decision_matrix(
            market_ctx,
            sector_ctx,
            theme_score,
            trade_score
        )

        # Generate reasoning
        reasoning = self._generate_final_reasoning(
            market_ctx,
            sector_ctx,
            theme_intel,
            trading_intel
        )

        # Collect risks
        risks = self._collect_risks(theme_intel, trading_intel)

        return FinalDecision(
            ticker=ticker,
            decision=decision,
            position_size=trading_intel.position_size_suggestion,
            confidence=self._calculate_final_confidence(theme_intel, trading_intel),
            reasoning=reasoning,
            market_context_summary=market_ctx.regime_narrative if market_ctx else "",
            sector_context_summary=sector_ctx.cycle_narrative if sector_ctx else "",
            theme_score=theme_score,
            trade_score=trade_score,
            risks=risks,
            stop_loss=None,  # Could calculate from timeframe data
            targets=[],      # Could calculate from timeframe data
            timestamp=datetime.now().isoformat()
        )

    def _apply_decision_matrix(
        self,
        market_ctx: Optional[MarketContext],
        sector_ctx: Optional[SectorContext],
        theme_score: int,
        trade_score: int
    ) -> Decision:
        """Apply decision matrix to determine final decision."""
        # Veto conditions
        if market_ctx and market_ctx.health == 'concerning':
            return Decision.SELL

        if theme_score < 4 or trade_score < 4:
            return Decision.HOLD

        # Decision matrix
        avg_score = (theme_score + trade_score) / 2

        if avg_score >= 8 and market_ctx and market_ctx.stance == MarketStance.OFFENSIVE:
            return Decision.STRONG_BUY
        elif avg_score >= 7:
            return Decision.BUY
        elif avg_score >= 5:
            return Decision.HOLD
        elif avg_score >= 3:
            return Decision.SELL
        else:
            return Decision.STRONG_SELL

    def _generate_final_reasoning(
        self,
        market_ctx: Optional[MarketContext],
        sector_ctx: Optional[SectorContext],
        theme_intel: Optional[ThemeIntelligence],
        trading_intel: TradingIntelligence
    ) -> str:
        """Generate final decision reasoning."""
        parts = []

        if market_ctx:
            parts.append(f"Market: {market_ctx.health} (risk {market_ctx.risk_level}/10)")

        if sector_ctx:
            parts.append(f"Cycle: {sector_ctx.cycle_stage.value}")

        if theme_intel:
            parts.append(f"Theme: {theme_intel.theme_score}/10")

        if trading_intel:
            parts.append(f"Trade: {trading_intel.trade_score}/10")

        return "; ".join(parts)

    def _collect_risks(
        self,
        theme_intel: Optional[ThemeIntelligence],
        trading_intel: TradingIntelligence
    ) -> List[str]:
        """Collect all identified risks."""
        risks = []

        if trading_intel and trading_intel.signal_explanation:
            risks.append(trading_intel.signal_explanation.key_risk)

        if theme_intel and theme_intel.earnings_intelligence:
            risks.extend(theme_intel.earnings_intelligence.risks_concerns[:2])

        return risks

    def _calculate_risk_level(self, vix: float, breadth: float, health: str) -> int:
        """Calculate market risk level 1-10."""
        risk = 5

        # VIX contribution
        if vix > 30:
            risk += 3
        elif vix > 20:
            risk += 2
        elif vix < 15:
            risk -= 1

        # Breadth contribution
        if breadth < 40:
            risk += 2
        elif breadth > 60:
            risk -= 1

        # Health contribution
        if health == 'concerning':
            risk += 2
        elif health == 'healthy':
            risk -= 1

        return max(1, min(10, risk))

    def _calculate_final_confidence(
        self,
        theme_intel: Optional[ThemeIntelligence],
        trading_intel: TradingIntelligence
    ) -> float:
        """Calculate final confidence score."""
        confidences = []

        if theme_intel:
            confidences.append(theme_intel.confidence)

        if trading_intel:
            confidences.append(trading_intel.confidence)

        return sum(confidences) / len(confidences) if confidences else 0.5


# =============================================================================
# SINGLETON & CONVENIENCE FUNCTIONS
# =============================================================================

_cio: Optional[ChiefIntelligenceOfficer] = None

def get_cio() -> ChiefIntelligenceOfficer:
    """Get or create the singleton Chief Intelligence Officer."""
    global _cio
    if _cio is None:
        _cio = ChiefIntelligenceOfficer()
    return _cio
