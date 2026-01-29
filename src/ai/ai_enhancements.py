#!/usr/bin/env python3
"""
AI Enhancements Module - xAI-Powered Features

Leverages xAI's 2x speed advantage to enable real-time AI features:
1. Trading signal explanations
2. Earnings call analysis
3. Market health narratives
4. Sector rotation explanations
5. AI fact checking
6. Multi-timeframe synthesis
7. TAM expansion analysis
8. Corporate actions impact analysis

All features use the unified AI service with automatic xAI routing.
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

from src.services.ai_service import get_ai_service

logger = logging.getLogger(__name__)


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class SignalExplanation:
    """Explanation for why a trading signal triggered."""
    ticker: str
    signal_type: str
    reasoning: str
    catalyst: str
    key_risk: str
    confidence: float
    generated_at: str


@dataclass
class EarningsAnalysis:
    """AI analysis of earnings call."""
    ticker: str
    management_tone: str  # bullish/neutral/bearish
    guidance_changes: List[str]
    growth_catalysts: List[str]
    risks_concerns: List[str]
    competitive_positioning: str
    overall_assessment: str
    confidence: float
    generated_at: str


@dataclass
class MarketHealthNarrative:
    """Daily market health commentary."""
    date: str
    health_rating: str  # healthy/neutral/warning/concerning
    concerning_signals: List[str]
    positive_signals: List[str]
    recommended_stance: str  # offensive/neutral/defensive
    narrative: str
    generated_at: str


@dataclass
class SectorRotationNarrative:
    """Explanation of sector rotation pattern."""
    date: str
    market_cycle_stage: str  # early/mid/late/recession
    leading_sectors: List[str]
    lagging_sectors: List[str]
    reasoning: str
    next_rotation_likely: str
    generated_at: str


@dataclass
class FactCheckResult:
    """AI fact-check result."""
    claim: str
    verified: str  # true/false/partial/unverifiable
    confidence: float
    reasoning: str
    contradictions: List[str]
    sources_checked: int
    generated_at: str


@dataclass
class TimeframeSynthesis:
    """Multi-timeframe synthesis."""
    ticker: str
    overall_alignment: str  # aligned_bullish/aligned_bearish/mixed
    best_entry_timeframe: Optional[str]
    key_levels: Dict[str, float]
    trade_quality_score: int  # 1-10
    synthesis: str
    generated_at: str


@dataclass
class TAMAnalysis:
    """TAM expansion analysis."""
    theme: str
    cagr_estimate: float
    adoption_stage: str  # early/mid/mature
    growth_drivers: List[str]
    expansion_catalysts: List[str]
    competitive_intensity: str  # low/medium/high
    confidence: float
    generated_at: str


@dataclass
class CorporateActionImpact:
    """Corporate action impact analysis."""
    ticker: str
    action_type: str
    typical_reaction: str  # bullish/bearish/neutral
    reasoning: str
    historical_precedents: str
    expected_impact: str
    key_risks: List[str]
    generated_at: str


# =============================================================================
# AI ENHANCEMENT ENGINE
# =============================================================================

class AIEnhancementEngine:
    """
    Main engine for AI-powered enhancements.

    Uses xAI for 2x faster responses, enabling real-time features.
    """

    def __init__(self):
        self.service = get_ai_service()

    # =========================================================================
    # FEATURE #2: TRADING SIGNAL EXPLANATIONS
    # =========================================================================

    def explain_signal(
        self,
        ticker: str,
        signal_type: str,
        signal_data: Dict[str, Any]
    ) -> Optional[SignalExplanation]:
        """
        Explain why a trading signal triggered.

        Args:
            ticker: Stock ticker
            signal_type: Type of signal (breakout, momentum, etc.)
            signal_data: Signal metadata (RS, volume, theme, news, etc.)

        Returns:
            SignalExplanation or None if AI call fails
        """
        try:
            # Build context
            rs = signal_data.get('rs', 'N/A')
            volume_trend = signal_data.get('volume_trend', 'N/A')
            theme = signal_data.get('theme', 'N/A')
            recent_news = signal_data.get('recent_news', '')[:200]

            prompt = f"""{ticker} triggered {signal_type} signal.

Data:
- Relative Strength (RS): {rs}
- Volume Trend: {volume_trend}
- Theme: {theme}
- Recent News: {recent_news}

Provide concise analysis in JSON format:
{{
    "reasoning": "Why this setup is compelling (2-3 sentences)",
    "catalyst": "What's driving this move",
    "key_risk": "Primary risk to watch",
    "confidence": 0.0-1.0
}}"""

            result = self.service.call(
                prompt,
                system_prompt="You are a professional trader analyzing setups.",
                task_type="signal_analysis",
                max_tokens=300
            )

            if not result:
                logger.warning(f"AI call failed for {ticker} signal explanation")
                return None

            # Parse JSON
            parsed = self._parse_json(result)
            if not parsed:
                return None

            return SignalExplanation(
                ticker=ticker,
                signal_type=signal_type,
                reasoning=parsed.get('reasoning', ''),
                catalyst=parsed.get('catalyst', ''),
                key_risk=parsed.get('key_risk', ''),
                confidence=parsed.get('confidence', 0.5),
                generated_at=datetime.now().isoformat()
            )

        except Exception as e:
            logger.error(f"Error explaining signal for {ticker}: {e}")
            return None

    # =========================================================================
    # FEATURE #3: EARNINGS CALL ANALYSIS
    # =========================================================================

    def analyze_earnings_call(
        self,
        ticker: str,
        transcript: str,
        earnings_data: Optional[Dict] = None
    ) -> Optional[EarningsAnalysis]:
        """
        Analyze earnings call transcript with AI.

        Args:
            ticker: Stock ticker
            transcript: Earnings call transcript (or summary)
            earnings_data: Optional EPS/revenue data

        Returns:
            EarningsAnalysis or None
        """
        try:
            # Truncate transcript to manageable size
            transcript_preview = transcript[:1500] if transcript else "No transcript available"

            earnings_context = ""
            if earnings_data:
                earnings_context = f"\nEPS: {earnings_data.get('eps', 'N/A')} (Est: {earnings_data.get('eps_estimate', 'N/A')})\nRevenue: {earnings_data.get('revenue', 'N/A')}"

            prompt = f"""{ticker} earnings call analysis:

{earnings_context}

Transcript excerpt:
{transcript_preview}

Analyze and return JSON:
{{
    "management_tone": "bullish|neutral|bearish",
    "guidance_changes": ["change1", "change2"],
    "growth_catalysts": ["catalyst1", "catalyst2", "catalyst3"],
    "risks_concerns": ["risk1", "risk2", "risk3"],
    "competitive_positioning": "Brief assessment",
    "overall_assessment": "Summary (2-3 sentences)",
    "confidence": 0.0-1.0
}}"""

            result = self.service.call(
                prompt,
                system_prompt="You are an equity analyst analyzing earnings calls.",
                task_type="earnings",
                max_tokens=500
            )

            if not result:
                return None

            parsed = self._parse_json(result)
            if not parsed:
                return None

            return EarningsAnalysis(
                ticker=ticker,
                management_tone=parsed.get('management_tone', 'neutral'),
                guidance_changes=parsed.get('guidance_changes', []),
                growth_catalysts=parsed.get('growth_catalysts', []),
                risks_concerns=parsed.get('risks_concerns', []),
                competitive_positioning=parsed.get('competitive_positioning', ''),
                overall_assessment=parsed.get('overall_assessment', ''),
                confidence=parsed.get('confidence', 0.5),
                generated_at=datetime.now().isoformat()
            )

        except Exception as e:
            logger.error(f"Error analyzing earnings for {ticker}: {e}")
            return None

    # =========================================================================
    # FEATURE #4: MARKET HEALTH NARRATIVE
    # =========================================================================

    def generate_market_narrative(
        self,
        health_metrics: Dict[str, Any]
    ) -> Optional[MarketHealthNarrative]:
        """
        Generate daily market health commentary.

        Args:
            health_metrics: Dict with breadth, VIX, new highs/lows, etc.

        Returns:
            MarketHealthNarrative or None
        """
        try:
            prompt = f"""Generate market health assessment:

Breadth (% stocks above 200MA): {health_metrics.get('breadth', 'N/A')}%
VIX: {health_metrics.get('vix', 'N/A')}
New 52-Week Highs: {health_metrics.get('new_highs', 'N/A')}
New 52-Week Lows: {health_metrics.get('new_lows', 'N/A')}
Leading Sectors: {', '.join(health_metrics.get('leading_sectors', []))}
Lagging Sectors: {', '.join(health_metrics.get('lagging_sectors', []))}

Return JSON:
{{
    "health_rating": "healthy|neutral|warning|concerning",
    "concerning_signals": ["signal1", "signal2", "signal3"],
    "positive_signals": ["signal1", "signal2", "signal3"],
    "recommended_stance": "offensive|neutral|defensive",
    "narrative": "2-3 sentence summary for traders"
}}"""

            result = self.service.call(
                prompt,
                system_prompt="You are a market strategist assessing market health.",
                task_type="market_health",
                max_tokens=400
            )

            if not result:
                return None

            parsed = self._parse_json(result)
            if not parsed:
                return None

            return MarketHealthNarrative(
                date=datetime.now().strftime('%Y-%m-%d'),
                health_rating=parsed.get('health_rating', 'neutral'),
                concerning_signals=parsed.get('concerning_signals', []),
                positive_signals=parsed.get('positive_signals', []),
                recommended_stance=parsed.get('recommended_stance', 'neutral'),
                narrative=parsed.get('narrative', ''),
                generated_at=datetime.now().isoformat()
            )

        except Exception as e:
            logger.error(f"Error generating market narrative: {e}")
            return None

    # =========================================================================
    # FEATURE #5: SECTOR ROTATION NARRATIVE
    # =========================================================================

    def explain_sector_rotation(
        self,
        rotation_data: Dict[str, Any]
    ) -> Optional[SectorRotationNarrative]:
        """
        Explain why sectors are rotating.

        Args:
            rotation_data: Dict with top/lagging sectors, money flow, etc.

        Returns:
            SectorRotationNarrative or None
        """
        try:
            prompt = f"""Explain this sector rotation pattern:

Top Performing Sectors (1-month): {', '.join(rotation_data.get('top_sectors', []))}
Lagging Sectors: {', '.join(rotation_data.get('lagging_sectors', []))}
Money Flow Direction: {rotation_data.get('money_flow', 'N/A')}

Return JSON:
{{
    "market_cycle_stage": "early|mid|late|recession",
    "reasoning": "Why these sectors are leading (2-3 sentences)",
    "next_rotation_likely": "Expected next rotation if pattern continues",
    "confidence": 0.0-1.0
}}"""

            result = self.service.call(
                prompt,
                system_prompt="You are a sector rotation expert analyzing market cycles.",
                task_type="sector_analysis",
                max_tokens=350
            )

            if not result:
                return None

            parsed = self._parse_json(result)
            if not parsed:
                return None

            return SectorRotationNarrative(
                date=datetime.now().strftime('%Y-%m-%d'),
                market_cycle_stage=parsed.get('market_cycle_stage', 'mid'),
                leading_sectors=rotation_data.get('top_sectors', []),
                lagging_sectors=rotation_data.get('lagging_sectors', []),
                reasoning=parsed.get('reasoning', ''),
                next_rotation_likely=parsed.get('next_rotation_likely', ''),
                generated_at=datetime.now().isoformat()
            )

        except Exception as e:
            logger.error(f"Error explaining sector rotation: {e}")
            return None

    # =========================================================================
    # FEATURE #6: AI FACT CHECKING
    # =========================================================================

    def fact_check_claim(
        self,
        claim: str,
        sources: List[Dict[str, str]]
    ) -> Optional[FactCheckResult]:
        """
        AI-powered fact checking across multiple sources.

        Args:
            claim: The claim to verify
            sources: List of dicts with 'source' and 'headline' keys

        Returns:
            FactCheckResult or None
        """
        try:
            sources_text = "\n".join([
                f"- {s.get('source', 'Unknown')}: {s.get('headline', '')}"
                for s in sources[:5]
            ])

            prompt = f"""Fact-check this claim:

CLAIM: {claim}

SOURCES:
{sources_text}

Return JSON:
{{
    "verified": "true|false|partial|unverifiable",
    "confidence": 0.0-1.0,
    "reasoning": "Explanation of verification",
    "contradictions": ["Any contradictions found"]
}}"""

            result = self.service.call(
                prompt,
                system_prompt="You are a fact-checker verifying financial claims.",
                task_type="fact_check",
                max_tokens=300
            )

            if not result:
                return None

            parsed = self._parse_json(result)
            if not parsed:
                return None

            return FactCheckResult(
                claim=claim,
                verified=parsed.get('verified', 'unverifiable'),
                confidence=parsed.get('confidence', 0.5),
                reasoning=parsed.get('reasoning', ''),
                contradictions=parsed.get('contradictions', []),
                sources_checked=len(sources),
                generated_at=datetime.now().isoformat()
            )

        except Exception as e:
            logger.error(f"Error fact-checking claim: {e}")
            return None

    # =========================================================================
    # FEATURE #7: MULTI-TIMEFRAME SYNTHESIS
    # =========================================================================

    def synthesize_timeframes(
        self,
        ticker: str,
        timeframe_data: Dict[str, Dict]
    ) -> Optional[TimeframeSynthesis]:
        """
        Synthesize multi-timeframe analysis.

        Args:
            ticker: Stock ticker
            timeframe_data: Dict with 'daily', 'weekly', 'monthly' timeframe data

        Returns:
            TimeframeSynthesis or None
        """
        try:
            daily = timeframe_data.get('daily', {})
            weekly = timeframe_data.get('weekly', {})
            monthly = timeframe_data.get('monthly', {})

            prompt = f"""{ticker} multi-timeframe analysis:

Daily: {daily.get('trend', 'N/A')} trend, strength {daily.get('strength', 'N/A')}
Weekly: {weekly.get('trend', 'N/A')} trend, strength {weekly.get('strength', 'N/A')}
Monthly: {monthly.get('trend', 'N/A')} trend, strength {monthly.get('strength', 'N/A')}

Return JSON:
{{
    "overall_alignment": "aligned_bullish|aligned_bearish|mixed",
    "best_entry_timeframe": "daily|weekly|monthly|wait",
    "key_levels": {{"support": 0.0, "resistance": 0.0}},
    "trade_quality_score": 1-10,
    "synthesis": "2-3 sentence summary"
}}"""

            result = self.service.call(
                prompt,
                system_prompt="You are a technical analyst synthesizing multiple timeframes.",
                task_type="timeframe_synthesis",
                max_tokens=300
            )

            if not result:
                return None

            parsed = self._parse_json(result)
            if not parsed:
                return None

            return TimeframeSynthesis(
                ticker=ticker,
                overall_alignment=parsed.get('overall_alignment', 'mixed'),
                best_entry_timeframe=parsed.get('best_entry_timeframe'),
                key_levels=parsed.get('key_levels', {}),
                trade_quality_score=parsed.get('trade_quality_score', 5),
                synthesis=parsed.get('synthesis', ''),
                generated_at=datetime.now().isoformat()
            )

        except Exception as e:
            logger.error(f"Error synthesizing timeframes for {ticker}: {e}")
            return None

    # =========================================================================
    # FEATURE #8: TAM EXPANSION ANALYSIS
    # =========================================================================

    def analyze_tam_expansion(
        self,
        theme: str,
        current_players: List[str],
        context: Optional[str] = None
    ) -> Optional[TAMAnalysis]:
        """
        Estimate TAM expansion potential for a theme.

        Args:
            theme: Investment theme name
            current_players: List of key players in the theme
            context: Optional additional context

        Returns:
            TAMAnalysis or None
        """
        try:
            players_str = ', '.join(current_players[:5])
            context_str = f"\nContext: {context}" if context else ""

            prompt = f"""Estimate TAM expansion for "{theme}" theme:

Current key players: {players_str}{context_str}

Return JSON:
{{
    "cagr_estimate": 0.0-100.0,
    "adoption_stage": "early|mid|mature",
    "growth_drivers": ["driver1", "driver2", "driver3"],
    "expansion_catalysts": ["catalyst1", "catalyst2"],
    "competitive_intensity": "low|medium|high",
    "confidence": 0.0-1.0
}}"""

            result = self.service.call(
                prompt,
                system_prompt="You are a market research analyst estimating TAM.",
                task_type="tam_analysis",
                max_tokens=400
            )

            if not result:
                return None

            parsed = self._parse_json(result)
            if not parsed:
                return None

            return TAMAnalysis(
                theme=theme,
                cagr_estimate=parsed.get('cagr_estimate', 0.0),
                adoption_stage=parsed.get('adoption_stage', 'mid'),
                growth_drivers=parsed.get('growth_drivers', []),
                expansion_catalysts=parsed.get('expansion_catalysts', []),
                competitive_intensity=parsed.get('competitive_intensity', 'medium'),
                confidence=parsed.get('confidence', 0.5),
                generated_at=datetime.now().isoformat()
            )

        except Exception as e:
            logger.error(f"Error analyzing TAM for {theme}: {e}")
            return None

    # =========================================================================
    # FEATURE #9: CORPORATE ACTIONS IMPACT
    # =========================================================================

    def analyze_corporate_action(
        self,
        ticker: str,
        action_type: str,
        action_details: str
    ) -> Optional[CorporateActionImpact]:
        """
        Analyze impact of corporate actions.

        Args:
            ticker: Stock ticker
            action_type: split/buyback/dividend/merger/acquisition
            action_details: Details of the action

        Returns:
            CorporateActionImpact or None
        """
        try:
            prompt = f"""{ticker} announced: {action_type}

Details: {action_details}

Return JSON:
{{
    "typical_reaction": "bullish|bearish|neutral",
    "reasoning": "Why companies do this (2 sentences)",
    "historical_precedents": "How market usually reacts",
    "expected_impact": "Expected stock direction and magnitude",
    "key_risks": ["risk1", "risk2"]
}}"""

            result = self.service.call(
                prompt,
                system_prompt="You are a corporate finance analyst.",
                task_type="corporate_action",
                max_tokens=350
            )

            if not result:
                return None

            parsed = self._parse_json(result)
            if not parsed:
                return None

            return CorporateActionImpact(
                ticker=ticker,
                action_type=action_type,
                typical_reaction=parsed.get('typical_reaction', 'neutral'),
                reasoning=parsed.get('reasoning', ''),
                historical_precedents=parsed.get('historical_precedents', ''),
                expected_impact=parsed.get('expected_impact', ''),
                key_risks=parsed.get('key_risks', []),
                generated_at=datetime.now().isoformat()
            )

        except Exception as e:
            logger.error(f"Error analyzing corporate action for {ticker}: {e}")
            return None

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _parse_json(self, response: str) -> Optional[Dict]:
        """Parse JSON from AI response."""
        try:
            # Try to extract JSON from response
            if '```json' in response:
                response = response.split('```json')[1].split('```')[0].strip()
            elif '```' in response:
                response = response.split('```')[1].split('```')[0].strip()

            return json.loads(response)
        except Exception as e:
            logger.debug(f"Failed to parse JSON: {e}")
            # Try to find JSON object in response
            import re
            json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
            matches = re.findall(json_pattern, response)
            if matches:
                try:
                    return json.loads(matches[0])
                except json.JSONDecodeError:
                    pass
            return None


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_ai_enhancement_engine: Optional[AIEnhancementEngine] = None

def get_ai_enhancements() -> AIEnhancementEngine:
    """Get or create the singleton AI enhancement engine."""
    global _ai_enhancement_engine
    if _ai_enhancement_engine is None:
        _ai_enhancement_engine = AIEnhancementEngine()
    return _ai_enhancement_engine


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def explain_signal(ticker: str, signal_type: str, signal_data: Dict) -> Optional[SignalExplanation]:
    """Convenience function for signal explanation."""
    engine = get_ai_enhancements()
    return engine.explain_signal(ticker, signal_type, signal_data)


def analyze_earnings(ticker: str, transcript: str, earnings_data: Optional[Dict] = None) -> Optional[EarningsAnalysis]:
    """Convenience function for earnings analysis."""
    engine = get_ai_enhancements()
    return engine.analyze_earnings_call(ticker, transcript, earnings_data)


def generate_market_narrative(health_metrics: Dict) -> Optional[MarketHealthNarrative]:
    """Convenience function for market narrative."""
    engine = get_ai_enhancements()
    return engine.generate_market_narrative(health_metrics)


def explain_sector_rotation(rotation_data: Dict) -> Optional[SectorRotationNarrative]:
    """Convenience function for sector rotation."""
    engine = get_ai_enhancements()
    return engine.explain_sector_rotation(rotation_data)


def fact_check(claim: str, sources: List[Dict]) -> Optional[FactCheckResult]:
    """Convenience function for fact checking."""
    engine = get_ai_enhancements()
    return engine.fact_check_claim(claim, sources)


def synthesize_timeframes(ticker: str, timeframe_data: Dict) -> Optional[TimeframeSynthesis]:
    """Convenience function for timeframe synthesis."""
    engine = get_ai_enhancements()
    return engine.synthesize_timeframes(ticker, timeframe_data)


def analyze_tam(theme: str, players: List[str], context: Optional[str] = None) -> Optional[TAMAnalysis]:
    """Convenience function for TAM analysis."""
    engine = get_ai_enhancements()
    return engine.analyze_tam_expansion(theme, players, context)


def analyze_corporate_action(ticker: str, action_type: str, details: str) -> Optional[CorporateActionImpact]:
    """Convenience function for corporate action analysis."""
    engine = get_ai_enhancements()
    return engine.analyze_corporate_action(ticker, action_type, details)
