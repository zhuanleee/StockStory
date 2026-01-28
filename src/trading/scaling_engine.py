"""
Scaling Engine - Professional Scale-In/Scale-Out with AI Advisor

Integrates with story-first exit signals to provide intelligent
position scaling recommendations.

Features:
- Pre-built scaling strategies
- Scale-in triggers (thesis confirmed, theme accelerating)
- Scale-out triggers (profit targets + story-based overrides)
- AI-powered scaling advisor
"""

import logging
from typing import List, Dict, Optional, Any

from .models import (
    Trade, ScalingStrategy, ExitSignal, SignalSource
)

logger = logging.getLogger(__name__)


class ScalingEngine:
    """
    Intelligent position scaling with story-first philosophy.
    """

    def __init__(self):
        self._ai_enabled = True

    # Scale-In Logic

    def check_scale_in_opportunity(
        self,
        trade: Trade,
        story_data: Dict[str, Any] = None,
        technical_data: Dict[str, Any] = None,
        current_price: float = None,
    ) -> Dict[str, Any]:
        """
        Check if conditions are right to scale into a position.

        Returns:
            Dict with:
            - should_scale: bool
            - confidence: 0-100
            - trigger: Which trigger was hit
            - suggested_size: % of max position to add
            - reasoning: Explanation
        """
        plan = trade.scaling_plan

        # Check if we can still scale in
        if trade.scale_ins_used >= plan.max_scale_ins:
            return {
                'should_scale': False,
                'confidence': 0,
                'trigger': None,
                'suggested_size': 0,
                'reasoning': f"Max scale-ins reached ({plan.max_scale_ins})"
            }

        triggers_hit = []
        reasoning_parts = []

        # Story-based scale-in triggers
        if story_data:
            # Thesis confirmed
            if 'thesis_confirmed' in plan.scale_in_triggers:
                thesis_score = story_data.get('thesis_score', 0)
                if thesis_score >= 75:
                    triggers_hit.append('thesis_confirmed')
                    reasoning_parts.append(f"Thesis strengthening ({thesis_score}/100)")

            # Theme accelerating
            if 'theme_accelerating' in plan.scale_in_triggers:
                theme_momentum = story_data.get('theme_momentum', 0)
                if theme_momentum > 30:
                    triggers_hit.append('theme_accelerating')
                    reasoning_parts.append(f"Theme momentum positive ({theme_momentum})")

            # Catalyst confirmed
            if 'catalyst_confirmed' in plan.scale_in_triggers:
                catalyst_status = story_data.get('catalyst_status', '')
                if catalyst_status == 'confirmed':
                    triggers_hit.append('catalyst_confirmed')
                    reasoning_parts.append("Catalyst event confirmed")

        # Technical scale-in triggers
        if technical_data and current_price:
            avg_cost = trade.average_cost

            # Pullback to support
            if 'pullback_support' in plan.scale_in_triggers:
                support = technical_data.get('support', 0)
                if support > 0 and abs(current_price - support) / support < 0.02:
                    triggers_hit.append('pullback_support')
                    reasoning_parts.append(f"Price at support (${support:.2f})")

            # New high (momentum strategy)
            if 'new_high' in plan.scale_in_triggers:
                high_52w = technical_data.get('high_52w', 0)
                if high_52w > 0 and current_price >= high_52w * 0.98:
                    triggers_hit.append('new_high')
                    reasoning_parts.append("Making new highs")

            # Volume surge
            if 'volume_surge' in plan.scale_in_triggers:
                volume_ratio = technical_data.get('volume_ratio', 1.0)
                if volume_ratio > 2.0:
                    triggers_hit.append('volume_surge')
                    reasoning_parts.append(f"Volume surge ({volume_ratio:.1f}x avg)")

            # Theme momentum (for momentum strategy)
            if 'theme_momentum' in plan.scale_in_triggers and story_data:
                theme_momentum = story_data.get('theme_momentum', 0)
                if theme_momentum > 50:
                    triggers_hit.append('theme_momentum')
                    reasoning_parts.append(f"Strong theme momentum ({theme_momentum})")

        if not triggers_hit:
            return {
                'should_scale': False,
                'confidence': 0,
                'trigger': None,
                'suggested_size': 0,
                'reasoning': "No scale-in triggers hit"
            }

        # Calculate confidence based on triggers hit
        confidence = min(50 + len(triggers_hit) * 20, 95)

        return {
            'should_scale': True,
            'confidence': confidence,
            'trigger': triggers_hit[0],  # Primary trigger
            'all_triggers': triggers_hit,
            'suggested_size': plan.scale_in_increment,
            'reasoning': " | ".join(reasoning_parts),
            'scale_in_number': trade.scale_ins_used + 1,
            'max_scale_ins': plan.max_scale_ins,
        }

    # Scale-Out Logic

    def check_scale_out_opportunity(
        self,
        trade: Trade,
        exit_signals: List[ExitSignal] = None,
        current_price: float = None,
    ) -> Dict[str, Any]:
        """
        Check if conditions are right to scale out of a position.

        Integrates story-first exit signals with profit target logic.

        Returns:
            Dict with:
            - should_scale: bool
            - confidence: 0-100
            - trigger: Which trigger was hit
            - suggested_size: % of position to sell
            - reasoning: Explanation
            - override_reason: If story overrides technical
        """
        if trade.total_shares <= 0:
            return {
                'should_scale': False,
                'confidence': 0,
                'trigger': None,
                'suggested_size': 0,
                'reasoning': "No position to scale out of"
            }

        plan = trade.scaling_plan
        triggers_hit = []
        reasoning_parts = []
        override_reason = None

        # Calculate P&L
        avg_cost = trade.average_cost
        if avg_cost > 0 and current_price:
            pnl_pct = ((current_price - avg_cost) / avg_cost) * 100
        else:
            pnl_pct = 0

        # 1. Check story-based exit signals (highest priority)
        if exit_signals and plan.story_override_enabled:
            story_signals = [s for s in exit_signals if s.source == SignalSource.STORY]
            critical_signals = [s for s in story_signals if s.confidence >= 75]

            if critical_signals:
                # Story override - exit regardless of profit
                best_signal = max(critical_signals, key=lambda s: s.confidence)
                triggers_hit.append(best_signal.signal_type)
                reasoning_parts.append(best_signal.description)
                override_reason = f"Story override: {best_signal.signal_type}"

                return {
                    'should_scale': True,
                    'confidence': best_signal.confidence,
                    'trigger': best_signal.signal_type,
                    'suggested_size': best_signal.suggested_size or 50.0,
                    'reasoning': best_signal.description,
                    'override_reason': override_reason,
                    'source': 'story',
                }

        # 2. Check AI-based exit signals
        if exit_signals:
            ai_signals = [s for s in exit_signals if s.source == SignalSource.AI and s.confidence >= 70]
            if ai_signals:
                best_signal = max(ai_signals, key=lambda s: s.confidence)
                triggers_hit.append(best_signal.signal_type)
                reasoning_parts.append(best_signal.description)

        # 3. Check technical profit targets
        profit_targets = plan.profit_targets
        scale_out_increments = plan.scale_out_increments

        for i, target in enumerate(profit_targets):
            if pnl_pct >= target and trade.scale_outs_used <= i:
                # Check if story is still strong enough to override technical exit
                if plan.ignore_technicals_if_story_strong and exit_signals:
                    story_signals = [s for s in exit_signals if s.source == SignalSource.STORY]
                    avg_story_conf = sum(s.confidence for s in story_signals) / len(story_signals) if story_signals else 0

                    # If story confidence is LOW (< 40), story is strong, don't exit
                    if avg_story_conf < 40:
                        reasoning_parts.append(f"Profit target {i+1} hit but story still strong")
                        continue

                increment = scale_out_increments[i] if i < len(scale_out_increments) else 25.0
                triggers_hit.append(f'profit_target_{i+1}')
                reasoning_parts.append(f"Profit target {i+1}: {pnl_pct:.1f}% vs {target}% target")

                return {
                    'should_scale': True,
                    'confidence': 70,
                    'trigger': f'profit_target_{i+1}',
                    'suggested_size': increment,
                    'reasoning': reasoning_parts[-1],
                    'pnl_pct': pnl_pct,
                    'target_hit': i + 1,
                    'source': 'technical',
                }

        if not triggers_hit:
            return {
                'should_scale': False,
                'confidence': 0,
                'trigger': None,
                'suggested_size': 0,
                'reasoning': "No scale-out triggers hit",
                'pnl_pct': pnl_pct,
            }

        # Return combined assessment if AI signals but no profit target
        return {
            'should_scale': True,
            'confidence': 65,
            'trigger': triggers_hit[0],
            'suggested_size': 25.0,
            'reasoning': " | ".join(reasoning_parts),
            'source': 'ai',
        }

    # AI Advisor

    def get_ai_scaling_advice(
        self,
        trade: Trade,
        story_data: Dict[str, Any] = None,
        technical_data: Dict[str, Any] = None,
        current_price: float = None,
        market_context: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Get AI-powered scaling advice for a trade.

        Combines story, technical, and market context for intelligent
        scaling recommendations.

        Returns:
            Dict with:
            - action: 'scale_in', 'scale_out', 'hold'
            - confidence: 0-100
            - size_pct: Recommended size
            - reasoning: AI explanation
            - considerations: List of factors considered
        """
        if not self._ai_enabled:
            return {
                'action': 'hold',
                'confidence': 0,
                'size_pct': 0,
                'reasoning': "AI advisor disabled",
                'considerations': [],
            }

        try:
            from src.ai.ai_learning import call_ai

            # Build context prompt
            context = self._build_scaling_context(
                trade, story_data, technical_data, current_price, market_context
            )

            prompt = f"""Analyze this trade position and provide scaling advice.

TRADE CONTEXT:
{context}

Provide a JSON response with:
{{
    "action": "scale_in" | "scale_out" | "hold",
    "confidence": 0-100,
    "size_pct": 0-100 (% of position to add/remove),
    "reasoning": "Brief explanation",
    "considerations": ["factor1", "factor2", ...]
}}

Consider:
1. Story strength (thesis validity, theme momentum, catalyst status)
2. Risk/reward at current levels
3. Position sizing relative to conviction
4. Market regime and volatility
5. Opportunity cost

Be conservative with scale-ins, disciplined with scale-outs."""

            response = call_ai(
                prompt,
                system_prompt="You are a professional trading advisor focused on risk management and position sizing.",
                max_tokens=300,
                task_type="strategy"
            )

            if response:
                # Parse JSON response
                import json
                import re

                # Handle markdown code blocks
                json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', response, re.DOTALL)
                if json_match:
                    response = json_match.group(1)

                result = json.loads(response)
                return result

        except Exception as e:
            logger.error(f"AI scaling advice error: {e}")

        # Fallback to rule-based advice
        return self._get_fallback_advice(trade, story_data, technical_data, current_price)

    def _build_scaling_context(
        self,
        trade: Trade,
        story_data: Dict[str, Any] = None,
        technical_data: Dict[str, Any] = None,
        current_price: float = None,
        market_context: Dict[str, Any] = None,
    ) -> str:
        """Build context string for AI scaling advice."""
        lines = []

        # Trade info
        lines.append(f"Ticker: {trade.ticker}")
        lines.append(f"Position: {trade.total_shares} shares @ ${trade.average_cost:.2f}")
        lines.append(f"Days Held: {trade.days_held}")
        lines.append(f"Thesis: {trade.thesis}")
        lines.append(f"Theme: {trade.theme}")
        lines.append(f"Strategy: {trade.scaling_plan.strategy.value}")

        # P&L
        if current_price and trade.average_cost > 0:
            pnl_pct = ((current_price - trade.average_cost) / trade.average_cost) * 100
            lines.append(f"Current Price: ${current_price:.2f}")
            lines.append(f"P&L: {pnl_pct:+.1f}%")

        # Scaling status
        lines.append(f"Scale-ins used: {trade.scale_ins_used}/{trade.scaling_plan.max_scale_ins}")
        lines.append(f"Scale-outs used: {trade.scale_outs_used}")

        # Story data
        if story_data:
            lines.append(f"\nStory Score: {story_data.get('score', 'N/A')}")
            lines.append(f"Theme Stage: {story_data.get('theme_stage', 'N/A')}")
            lines.append(f"Theme Momentum: {story_data.get('theme_momentum', 'N/A')}")
            lines.append(f"Catalyst Status: {story_data.get('catalyst_status', 'N/A')}")

        # Technical data
        if technical_data:
            lines.append(f"\nRS Rating: {technical_data.get('rs_rating', 'N/A')}")
            lines.append(f"Trend: {technical_data.get('trend', 'N/A')}")
            lines.append(f"Volume Ratio: {technical_data.get('volume_ratio', 'N/A')}")

        # Market context
        if market_context:
            lines.append(f"\nMarket Regime: {market_context.get('regime', 'N/A')}")
            lines.append(f"SPY Change: {market_context.get('spy_change', 'N/A')}%")
            lines.append(f"VIX: {market_context.get('vix', 'N/A')}")

        return "\n".join(lines)

    def _get_fallback_advice(
        self,
        trade: Trade,
        story_data: Dict[str, Any] = None,
        technical_data: Dict[str, Any] = None,
        current_price: float = None,
    ) -> Dict[str, Any]:
        """Fallback rule-based advice if AI fails."""
        considerations = []

        # Check scale-in
        scale_in = self.check_scale_in_opportunity(trade, story_data, technical_data, current_price)
        if scale_in['should_scale']:
            considerations.append(f"Scale-in trigger: {scale_in['trigger']}")
            return {
                'action': 'scale_in',
                'confidence': scale_in['confidence'],
                'size_pct': scale_in['suggested_size'],
                'reasoning': scale_in['reasoning'],
                'considerations': considerations,
            }

        # Check scale-out
        scale_out = self.check_scale_out_opportunity(trade, current_price=current_price)
        if scale_out['should_scale']:
            considerations.append(f"Scale-out trigger: {scale_out['trigger']}")
            return {
                'action': 'scale_out',
                'confidence': scale_out['confidence'],
                'size_pct': scale_out['suggested_size'],
                'reasoning': scale_out['reasoning'],
                'considerations': considerations,
            }

        return {
            'action': 'hold',
            'confidence': 50,
            'size_pct': 0,
            'reasoning': "No clear scaling trigger",
            'considerations': ['No scale-in conditions met', 'No scale-out conditions met'],
        }

    # Position Sizing

    def calculate_position_size(
        self,
        trade: Trade,
        portfolio_value: float,
        current_price: float,
        risk_per_trade_pct: float = 2.0,
    ) -> Dict[str, Any]:
        """
        Calculate recommended position size based on risk parameters.

        Args:
            trade: Trade object with scaling plan
            portfolio_value: Total portfolio value
            current_price: Current stock price
            risk_per_trade_pct: Max risk per trade as % of portfolio

        Returns:
            Dict with:
            - max_shares: Maximum shares based on position limit
            - risk_shares: Shares based on risk calculation
            - recommended_shares: Final recommendation
            - dollar_amount: Dollar value of position
        """
        plan = trade.scaling_plan

        # Max position based on portfolio %
        max_position_value = portfolio_value * (plan.max_position_pct / 100)
        max_shares = int(max_position_value / current_price)

        # Initial position size
        if trade.total_shares == 0:
            target_pct = plan.initial_size_pct / 100
        else:
            target_pct = plan.scale_in_increment / 100

        target_value = max_position_value * target_pct
        target_shares = int(target_value / current_price)

        # Risk-based sizing (stop loss)
        stop_loss_pct = plan.stop_loss_pct / 100
        risk_amount = portfolio_value * (risk_per_trade_pct / 100)
        risk_per_share = current_price * stop_loss_pct
        risk_shares = int(risk_amount / risk_per_share) if risk_per_share > 0 else target_shares

        # Take the minimum of target and risk-based
        recommended_shares = min(target_shares, risk_shares)

        return {
            'max_shares': max_shares,
            'target_shares': target_shares,
            'risk_shares': risk_shares,
            'recommended_shares': recommended_shares,
            'dollar_amount': recommended_shares * current_price,
            'portfolio_pct': (recommended_shares * current_price / portfolio_value) * 100,
            'current_position': trade.total_shares,
            'total_after': trade.total_shares + recommended_shares,
        }

    # Strategy Descriptions

    def get_strategy_description(self, strategy: ScalingStrategy) -> Dict[str, Any]:
        """Get detailed description of a scaling strategy."""
        descriptions = {
            ScalingStrategy.CONSERVATIVE: {
                'name': 'Conservative',
                'description': 'Start small, scale slowly, tight stops',
                'initial_size': '25% of max',
                'scale_increments': '15% per add',
                'max_adds': 4,
                'stop_loss': '5%',
                'trailing_stop': '3% after first target',
                'best_for': 'High uncertainty, volatile markets, new traders',
                'risk_profile': 'Low risk, lower potential reward',
            },
            ScalingStrategy.AGGRESSIVE_PYRAMID: {
                'name': 'Aggressive Pyramid',
                'description': 'Front-load position, pyramid into winners',
                'initial_size': '50% of max',
                'scale_increments': '25% per add',
                'max_adds': 2,
                'stop_loss': '10%',
                'trailing_stop': None,
                'best_for': 'High conviction trades, strong trends',
                'risk_profile': 'Higher risk, higher potential reward',
            },
            ScalingStrategy.CORE_TRADE: {
                'name': 'Core + Trade',
                'description': '60% core position + 40% trading portion',
                'initial_size': '60% core (hold)',
                'scale_increments': '20% trading adds',
                'max_adds': 2,
                'stop_loss': '8%',
                'trailing_stop': None,
                'best_for': 'Long-term conviction with swing opportunities',
                'risk_profile': 'Moderate risk, balanced approach',
            },
            ScalingStrategy.MOMENTUM_RIDER: {
                'name': 'Momentum Rider',
                'description': 'Add only on strength, ride the trend',
                'initial_size': '33% of max',
                'scale_increments': '33% on new highs',
                'max_adds': 2,
                'stop_loss': '12%',
                'trailing_stop': '8% after first target',
                'best_for': 'Strong momentum stocks, trending markets',
                'risk_profile': 'Moderate risk, trend-following',
            },
        }
        return descriptions.get(strategy, {})


# Global engine instance
_scaling_engine: Optional[ScalingEngine] = None


def get_scaling_engine() -> ScalingEngine:
    """Get or create global scaling engine instance."""
    global _scaling_engine
    if _scaling_engine is None:
        _scaling_engine = ScalingEngine()
    return _scaling_engine
