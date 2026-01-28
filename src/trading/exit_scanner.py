"""
Exit Scanner - Story → AI → Technical Exit Signal Detection

Weighted Signal Priority:
- Story (50%): Theme lifecycle, catalyst status, narrative shifts
- AI (35%): Thesis validation, sentiment analysis
- Technical (15%): Price action, indicators (confirmation only)

Generates ExitSignal objects with confidence scores that roll up
into composite risk levels.
"""

import logging
from typing import List, Dict, Optional, Any

from .models import (
    Trade, ExitSignal, SignalSource, RiskLevel
)

logger = logging.getLogger(__name__)


class ExitScanner:
    """
    Scans trades for exit signals using Story → AI → Technical priority.
    """

    def __init__(self):
        self._cached_market_data: Dict[str, Any] = {}

    def scan_trade(
        self,
        trade: Trade,
        story_data: Dict[str, Any] = None,
        ai_analysis: Dict[str, Any] = None,
        technical_data: Dict[str, Any] = None,
        current_price: float = None,
    ) -> List[ExitSignal]:
        """
        Scan a trade for exit signals.

        Args:
            trade: Trade to scan
            story_data: Story scoring data (theme status, catalyst, news)
            ai_analysis: AI analysis results
            technical_data: Technical indicator data
            current_price: Current stock price

        Returns:
            List of ExitSignal objects, sorted by weighted confidence
        """
        signals = []

        # 1. STORY SIGNALS (50% weight) - Primary
        if story_data:
            story_signals = self._check_story_signals(trade, story_data)
            signals.extend(story_signals)

        # 2. AI SIGNALS (35% weight) - Secondary
        if ai_analysis:
            ai_signals = self._check_ai_signals(trade, ai_analysis)
            signals.extend(ai_signals)

        # 3. TECHNICAL SIGNALS (15% weight) - Confirmation only
        if technical_data and current_price:
            tech_signals = self._check_technical_signals(
                trade, technical_data, current_price
            )
            signals.extend(tech_signals)

        # Sort by weighted confidence (highest first)
        signals.sort(key=lambda s: s.weighted_confidence, reverse=True)

        return signals

    def _check_story_signals(
        self,
        trade: Trade,
        story_data: Dict[str, Any],
    ) -> List[ExitSignal]:
        """
        Check for story-based exit signals (50% weight).

        Story Signal Types:
        - theme_peaked: Theme at late/mature stage
        - catalyst_failed: Catalyst didn't materialize or disappointed
        - catalyst_passed: Catalyst event has passed (sell the news)
        - thesis_broken: Core thesis no longer valid
        - narrative_shift: Market narrative turning negative
        - sector_rotation: Money rotating out of sector
        """
        signals = []

        # Theme Lifecycle Check
        theme_stage = story_data.get('theme_stage', 'growth')
        theme_momentum = story_data.get('theme_momentum', 0)

        if theme_stage in ['late', 'mature', 'declining']:
            confidence = 80 if theme_stage == 'declining' else 65
            signals.append(ExitSignal(
                source=SignalSource.STORY,
                signal_type='theme_peaked',
                confidence=confidence,
                description=f"Theme '{trade.theme}' is in {theme_stage} stage",
                action='reduce' if confidence < 75 else 'exit',
                suggested_size=50.0 if confidence < 75 else 100.0,
                data={'theme_stage': theme_stage, 'momentum': theme_momentum}
            ))

        if theme_momentum < -30:
            signals.append(ExitSignal(
                source=SignalSource.STORY,
                signal_type='theme_declining',
                confidence=70,
                description=f"Theme momentum strongly negative ({theme_momentum})",
                action='reduce',
                suggested_size=33.0,
                data={'momentum': theme_momentum}
            ))

        # Catalyst Check
        catalyst_status = story_data.get('catalyst_status', 'pending')
        catalyst_result = story_data.get('catalyst_result', 'unknown')

        if catalyst_status == 'failed' or catalyst_result == 'missed':
            signals.append(ExitSignal(
                source=SignalSource.STORY,
                signal_type='catalyst_failed',
                confidence=85,
                description=f"Catalyst '{trade.catalyst}' failed or missed expectations",
                action='exit',
                suggested_size=100.0,
                data={'catalyst': trade.catalyst, 'result': catalyst_result}
            ))

        if catalyst_status == 'passed':
            # Sell the news - catalyst is behind us
            signals.append(ExitSignal(
                source=SignalSource.STORY,
                signal_type='catalyst_passed',
                confidence=55,
                description=f"Catalyst event has passed - evaluate continued thesis",
                action='reduce',
                suggested_size=25.0,
                data={'catalyst': trade.catalyst}
            ))

        # News Sentiment Check
        news_sentiment = story_data.get('news_sentiment', 0)  # -100 to 100
        news_momentum = story_data.get('news_momentum', 0)  # Change in sentiment

        if news_sentiment < -50 and news_momentum < -20:
            signals.append(ExitSignal(
                source=SignalSource.STORY,
                signal_type='narrative_shift',
                confidence=75,
                description=f"News narrative turning negative (sentiment: {news_sentiment})",
                action='reduce',
                suggested_size=50.0,
                data={'sentiment': news_sentiment, 'momentum': news_momentum}
            ))

        # Thesis Validation
        thesis_score = story_data.get('thesis_score', 100)  # How valid is original thesis
        if thesis_score < 40:
            signals.append(ExitSignal(
                source=SignalSource.STORY,
                signal_type='thesis_broken',
                confidence=90,
                description="Original investment thesis no longer valid",
                action='exit',
                suggested_size=100.0,
                data={'thesis_score': thesis_score}
            ))

        # Sector Rotation Check
        sector_flow = story_data.get('sector_flow', 0)  # Positive = inflow
        if sector_flow < -50:
            signals.append(ExitSignal(
                source=SignalSource.STORY,
                signal_type='sector_rotation',
                confidence=60,
                description=f"Money rotating out of sector (flow: {sector_flow})",
                action='reduce',
                suggested_size=25.0,
                data={'sector_flow': sector_flow}
            ))

        # Competition/Disruption Check
        competitive_threat = story_data.get('competitive_threat', 0)  # 0-100
        if competitive_threat > 70:
            signals.append(ExitSignal(
                source=SignalSource.STORY,
                signal_type='competitive_threat',
                confidence=65,
                description="Significant competitive threat emerging",
                action='reduce',
                suggested_size=33.0,
                data={'threat_level': competitive_threat}
            ))

        return signals

    def _check_ai_signals(
        self,
        trade: Trade,
        ai_analysis: Dict[str, Any],
    ) -> List[ExitSignal]:
        """
        Check for AI-based exit signals (35% weight).

        AI Signal Types:
        - ai_bearish: AI analysis turns bearish
        - sentiment_collapse: Dramatic sentiment shift
        - risk_elevated: AI identifies elevated risk
        - opportunity_cost: Better opportunities elsewhere
        """
        signals = []

        # AI Confidence/Sentiment
        ai_sentiment = ai_analysis.get('sentiment', 'neutral')
        ai_confidence = ai_analysis.get('confidence', 50)
        ai_recommendation = ai_analysis.get('recommendation', 'hold')

        if ai_sentiment == 'bearish' and ai_confidence > 70:
            signals.append(ExitSignal(
                source=SignalSource.AI,
                signal_type='ai_bearish',
                confidence=ai_confidence,
                description=f"AI analysis bearish with {ai_confidence}% confidence",
                action='reduce' if ai_confidence < 85 else 'exit',
                suggested_size=50.0 if ai_confidence < 85 else 100.0,
                data={'sentiment': ai_sentiment, 'ai_confidence': ai_confidence}
            ))

        if ai_recommendation in ['sell', 'strong_sell']:
            rec_confidence = 85 if ai_recommendation == 'strong_sell' else 70
            signals.append(ExitSignal(
                source=SignalSource.AI,
                signal_type='ai_sell_recommendation',
                confidence=rec_confidence,
                description=f"AI recommends {ai_recommendation}",
                action='exit' if ai_recommendation == 'strong_sell' else 'reduce',
                suggested_size=100.0 if ai_recommendation == 'strong_sell' else 50.0,
                data={'recommendation': ai_recommendation}
            ))

        # Sentiment Change Detection
        sentiment_change = ai_analysis.get('sentiment_change', 0)  # Change over period
        if sentiment_change < -40:  # Significant negative shift
            signals.append(ExitSignal(
                source=SignalSource.AI,
                signal_type='sentiment_collapse',
                confidence=75,
                description=f"Sentiment collapsed ({sentiment_change} point drop)",
                action='reduce',
                suggested_size=33.0,
                data={'sentiment_change': sentiment_change}
            ))

        # Risk Assessment
        risk_score = ai_analysis.get('risk_score', 50)  # 0-100
        if risk_score > 75:
            signals.append(ExitSignal(
                source=SignalSource.AI,
                signal_type='risk_elevated',
                confidence=risk_score,
                description=f"AI risk assessment elevated ({risk_score}/100)",
                action='reduce',
                suggested_size=25.0,
                data={'risk_score': risk_score}
            ))

        # Thesis Validation by AI
        thesis_valid = ai_analysis.get('thesis_valid', True)
        thesis_confidence = ai_analysis.get('thesis_confidence', 80)
        if not thesis_valid or thesis_confidence < 40:
            signals.append(ExitSignal(
                source=SignalSource.AI,
                signal_type='ai_thesis_invalid',
                confidence=85,
                description="AI assessment: Investment thesis no longer valid",
                action='exit',
                suggested_size=100.0,
                data={'thesis_valid': thesis_valid, 'thesis_confidence': thesis_confidence}
            ))

        return signals

    def _check_technical_signals(
        self,
        trade: Trade,
        technical_data: Dict[str, Any],
        current_price: float,
    ) -> List[ExitSignal]:
        """
        Check for technical exit signals (15% weight - confirmation only).

        Technical Signal Types:
        - ma_break: Price breaks key moving average
        - support_break: Price breaks support level
        - stop_loss_hit: Price hits stop loss
        - profit_target_hit: Price hits profit target
        - momentum_divergence: Price/momentum divergence
        - volume_collapse: Volume drying up
        """
        signals = []

        # Calculate P&L
        avg_cost = trade.average_cost
        if avg_cost > 0:
            pnl_pct = ((current_price - avg_cost) / avg_cost) * 100
        else:
            pnl_pct = 0

        # Stop Loss Check
        stop_loss = trade.scaling_plan.stop_loss_pct
        if pnl_pct <= -stop_loss:
            signals.append(ExitSignal(
                source=SignalSource.TECHNICAL,
                signal_type='stop_loss_hit',
                confidence=95,  # High confidence - hard rule
                description=f"Stop loss hit ({pnl_pct:.1f}% loss vs {stop_loss}% stop)",
                action='exit',
                suggested_size=100.0,
                data={'pnl_pct': pnl_pct, 'stop_loss': stop_loss}
            ))

        # Trailing Stop Check
        trailing_stop = trade.scaling_plan.trailing_stop_pct
        if trailing_stop and pnl_pct > 0:
            # Check if we've hit a trailing stop from high
            high_since_entry = technical_data.get('high_since_entry', current_price)
            drawdown_from_high = ((high_since_entry - current_price) / high_since_entry) * 100
            if drawdown_from_high >= trailing_stop:
                signals.append(ExitSignal(
                    source=SignalSource.TECHNICAL,
                    signal_type='trailing_stop_hit',
                    confidence=90,
                    description=f"Trailing stop hit ({drawdown_from_high:.1f}% from high)",
                    action='exit',
                    suggested_size=100.0,
                    data={'drawdown': drawdown_from_high, 'trailing_stop': trailing_stop}
                ))

        # Profit Target Check
        profit_targets = trade.scaling_plan.profit_targets
        scale_out_increments = trade.scaling_plan.scale_out_increments
        scale_outs_used = trade.scale_outs_used

        for i, target in enumerate(profit_targets):
            if pnl_pct >= target and scale_outs_used <= i:
                increment = scale_out_increments[i] if i < len(scale_out_increments) else 25.0
                signals.append(ExitSignal(
                    source=SignalSource.TECHNICAL,
                    signal_type=f'profit_target_{i+1}',
                    confidence=70,
                    description=f"Profit target {i+1} hit ({pnl_pct:.1f}% vs {target}% target)",
                    action='reduce',
                    suggested_size=increment,
                    data={'pnl_pct': pnl_pct, 'target': target, 'target_num': i+1}
                ))
                break  # Only trigger one target at a time

        # Moving Average Break
        ma20 = technical_data.get('ma20', 0)
        ma50 = technical_data.get('ma50', 0)

        if ma20 > 0 and current_price < ma20 * 0.97:  # 3% below MA20
            signals.append(ExitSignal(
                source=SignalSource.TECHNICAL,
                signal_type='ma20_break',
                confidence=50,
                description=f"Price broke below 20-day MA (${ma20:.2f})",
                action='reduce',
                suggested_size=25.0,
                data={'ma20': ma20, 'price': current_price}
            ))

        if ma50 > 0 and current_price < ma50 * 0.95:  # 5% below MA50
            signals.append(ExitSignal(
                source=SignalSource.TECHNICAL,
                signal_type='ma50_break',
                confidence=60,
                description=f"Price broke below 50-day MA (${ma50:.2f})",
                action='reduce',
                suggested_size=33.0,
                data={'ma50': ma50, 'price': current_price}
            ))

        # Support Break
        support_level = technical_data.get('support', 0)
        if support_level > 0 and current_price < support_level * 0.98:
            signals.append(ExitSignal(
                source=SignalSource.TECHNICAL,
                signal_type='support_break',
                confidence=65,
                description=f"Price broke support at ${support_level:.2f}",
                action='reduce',
                suggested_size=33.0,
                data={'support': support_level, 'price': current_price}
            ))

        # RS Rating Drop
        rs_rating = technical_data.get('rs_rating', 50)
        if rs_rating < 30:
            signals.append(ExitSignal(
                source=SignalSource.TECHNICAL,
                signal_type='rs_collapse',
                confidence=55,
                description=f"Relative Strength collapsed to {rs_rating}",
                action='reduce',
                suggested_size=25.0,
                data={'rs_rating': rs_rating}
            ))

        # Volume Analysis
        avg_volume = technical_data.get('avg_volume', 0)
        current_volume = technical_data.get('current_volume', 0)
        if avg_volume > 0 and current_volume < avg_volume * 0.3:
            signals.append(ExitSignal(
                source=SignalSource.TECHNICAL,
                signal_type='volume_collapse',
                confidence=40,
                description="Volume collapsed - lack of institutional interest",
                action='hold',  # Just a warning
                suggested_size=0,
                data={'volume_ratio': current_volume / avg_volume}
            ))

        return signals

    def get_composite_assessment(
        self,
        signals: List[ExitSignal],
    ) -> Dict[str, Any]:
        """
        Generate composite assessment from multiple signals.

        Returns:
            Dict with:
            - composite_confidence: Weighted confidence score
            - risk_level: RiskLevel enum
            - recommended_action: Overall action recommendation
            - action_size: Suggested position reduction %
            - primary_reason: Most important signal
            - signals_by_source: Grouped signals
        """
        if not signals:
            return {
                'composite_confidence': 0,
                'risk_level': RiskLevel.NONE,
                'recommended_action': 'hold',
                'action_size': 0,
                'primary_reason': None,
                'signals_by_source': {},
            }

        # Calculate weighted composite confidence
        # Using max signal from each source, then combining with weights
        best_by_source = {}
        for signal in signals:
            source = signal.source
            if source not in best_by_source or signal.confidence > best_by_source[source].confidence:
                best_by_source[source] = signal

        composite_confidence = sum(
            s.weighted_confidence for s in best_by_source.values()
        )
        composite_confidence = min(composite_confidence, 100)

        # Determine risk level
        risk_level = RiskLevel.from_confidence(composite_confidence)

        # Determine action based on highest weighted signal
        primary_signal = max(signals, key=lambda s: s.weighted_confidence)

        # Aggregate action size (take max suggested)
        action_signals = [s for s in signals if s.action in ['reduce', 'exit']]
        if action_signals:
            max_reduction = max(s.suggested_size or 0 for s in action_signals)
        else:
            max_reduction = 0

        # Determine recommended action
        if risk_level == RiskLevel.CRITICAL:
            recommended_action = 'exit'
            action_size = 100.0
        elif risk_level == RiskLevel.HIGH:
            recommended_action = 'reduce'
            action_size = max(max_reduction, 50.0)
        elif risk_level == RiskLevel.ELEVATED:
            recommended_action = 'reduce'
            action_size = max(max_reduction, 25.0)
        else:
            recommended_action = primary_signal.action
            action_size = max_reduction

        # Group signals by source
        signals_by_source = {}
        for signal in signals:
            source_name = signal.source.value
            if source_name not in signals_by_source:
                signals_by_source[source_name] = []
            signals_by_source[source_name].append(signal.to_dict())

        return {
            'composite_confidence': round(composite_confidence, 1),
            'risk_level': risk_level,
            'recommended_action': recommended_action,
            'action_size': action_size,
            'primary_reason': primary_signal.to_dict(),
            'signals_by_source': signals_by_source,
            'signal_count': len(signals),
        }

    def format_alert(
        self,
        trade: Trade,
        assessment: Dict[str, Any],
    ) -> str:
        """
        Format exit signal assessment as alert message.

        Returns formatted string for Telegram notification.
        """
        risk_emoji = {
            RiskLevel.CRITICAL: "🔴",
            RiskLevel.HIGH: "🟠",
            RiskLevel.ELEVATED: "🟡",
            RiskLevel.MODERATE: "🟢",
            RiskLevel.LOW: "⚪",
            RiskLevel.NONE: "✅",
        }

        risk_level = assessment['risk_level']
        emoji = risk_emoji.get(risk_level, "⚪")

        lines = [
            f"{emoji} **EXIT SIGNAL: {trade.ticker}**",
            f"Risk Level: {risk_level.value.upper()} ({assessment['composite_confidence']:.0f}%)",
            f"Action: {assessment['recommended_action'].upper()}",
        ]

        if assessment['action_size'] > 0:
            lines.append(f"Suggested: Reduce {assessment['action_size']:.0f}% of position")

        # Add primary reason
        primary = assessment.get('primary_reason')
        if primary:
            source = primary['source'].upper()
            lines.append(f"\nPrimary Signal ({source}):")
            lines.append(f"  {primary['description']}")

        # Add position info
        lines.append(f"\nPosition: {trade.total_shares} shares @ ${trade.average_cost:.2f}")
        lines.append(f"Days Held: {trade.days_held}")

        # Add thesis reminder
        if trade.thesis:
            lines.append(f"\nOriginal Thesis: {trade.thesis[:100]}...")

        return "\n".join(lines)


# Global scanner instance
_exit_scanner: Optional[ExitScanner] = None


def get_exit_scanner() -> ExitScanner:
    """Get or create global exit scanner instance."""
    global _exit_scanner
    if _exit_scanner is None:
        _exit_scanner = ExitScanner()
    return _exit_scanner
