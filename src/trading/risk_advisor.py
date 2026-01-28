"""
Risk Advisor - Confidence-Based Risk Advisory System

Provides risk assessment and recommendations based on:
- Composite exit signal confidence
- Story strength
- Market regime
- Position size relative to portfolio

Risk Levels:
- Critical (90-100%): Exit immediately
- High (75-89%): Strong exit signal
- Elevated (60-74%): Consider reducing
- Moderate (40-59%): Monitor closely
- Low (20-39%): Normal monitoring
- None (0-19%): No action needed
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any

from .models import (
    Trade, ExitSignal, RiskLevel, SignalSource, TradeStatus
)

logger = logging.getLogger(__name__)


class RiskAdvisor:
    """
    Confidence-based risk advisory system.

    Analyzes trades and portfolio for risk, providing
    actionable recommendations prioritized by urgency.
    """

    def __init__(self):
        self._risk_thresholds = {
            RiskLevel.CRITICAL: 90,
            RiskLevel.HIGH: 75,
            RiskLevel.ELEVATED: 60,
            RiskLevel.MODERATE: 40,
            RiskLevel.LOW: 20,
            RiskLevel.NONE: 0,
        }

    def assess_trade_risk(
        self,
        trade: Trade,
        exit_signals: List[ExitSignal] = None,
        current_price: float = None,
        portfolio_value: float = None,
    ) -> Dict[str, Any]:
        """
        Comprehensive risk assessment for a single trade.

        Returns:
            Dict with:
            - risk_level: RiskLevel enum
            - confidence: 0-100
            - factors: List of risk factors
            - recommendation: Action recommendation
            - urgency: 'immediate', 'soon', 'monitor', 'none'
            - position_risk: Position-specific risk metrics
        """
        factors = []
        confidence_components = []

        # 1. Exit Signal Risk (primary)
        if exit_signals:
            signal_confidence = self._calculate_signal_risk(exit_signals)
            confidence_components.append(('exit_signals', signal_confidence, 0.5))

            if signal_confidence >= 75:
                factors.append({
                    'type': 'exit_signals',
                    'severity': 'high',
                    'description': f"Exit signals triggered ({signal_confidence:.0f}% confidence)"
                })
        else:
            confidence_components.append(('exit_signals', 0, 0.5))

        # 2. Story Risk
        story_risk = self._assess_story_risk(trade)
        confidence_components.append(('story', story_risk['confidence'], 0.3))
        if story_risk['factors']:
            factors.extend(story_risk['factors'])

        # 3. Position Risk
        if current_price and portfolio_value:
            position_risk = self._assess_position_risk(trade, current_price, portfolio_value)
            confidence_components.append(('position', position_risk['confidence'], 0.2))
            if position_risk['factors']:
                factors.extend(position_risk['factors'])
        else:
            confidence_components.append(('position', 0, 0.2))

        # Calculate weighted confidence
        total_confidence = sum(conf * weight for _, conf, weight in confidence_components)
        total_confidence = min(total_confidence, 100)

        # Determine risk level
        risk_level = RiskLevel.from_confidence(total_confidence)

        # Generate recommendation
        recommendation = self._generate_recommendation(trade, risk_level, factors, current_price)

        # Determine urgency
        urgency = self._determine_urgency(risk_level, factors)

        return {
            'trade_id': trade.id,
            'ticker': trade.ticker,
            'risk_level': risk_level,
            'confidence': round(total_confidence, 1),
            'factors': factors,
            'recommendation': recommendation,
            'urgency': urgency,
            'confidence_breakdown': {
                name: round(conf, 1) for name, conf, _ in confidence_components
            },
        }

    def _calculate_signal_risk(self, exit_signals: List[ExitSignal]) -> float:
        """Calculate risk confidence from exit signals."""
        if not exit_signals:
            return 0

        # Get best signal from each source
        best_by_source = {}
        for signal in exit_signals:
            source = signal.source
            if source not in best_by_source or signal.confidence > best_by_source[source].confidence:
                best_by_source[source] = signal

        # Calculate weighted sum
        total = sum(s.weighted_confidence for s in best_by_source.values())
        return min(total, 100)

    def _assess_story_risk(self, trade: Trade) -> Dict[str, Any]:
        """Assess story-related risk factors."""
        factors = []
        confidence = 0

        # Check latest scores
        if trade.latest_story_score is not None:
            if trade.latest_story_score < 40:
                confidence += 30
                factors.append({
                    'type': 'story_score',
                    'severity': 'high',
                    'description': f"Story score weak ({trade.latest_story_score:.0f}/100)"
                })
            elif trade.latest_story_score < 60:
                confidence += 15
                factors.append({
                    'type': 'story_score',
                    'severity': 'medium',
                    'description': f"Story score declining ({trade.latest_story_score:.0f}/100)"
                })

        # Check thesis age
        if trade.days_held > 60 and not trade.catalyst_date:
            confidence += 10
            factors.append({
                'type': 'time_decay',
                'severity': 'low',
                'description': f"Position held {trade.days_held} days without catalyst"
            })

        # Check catalyst status
        if trade.catalyst_date:
            days_until = (trade.catalyst_date - datetime.now()).days
            if days_until < 0:
                confidence += 20
                factors.append({
                    'type': 'catalyst_passed',
                    'severity': 'medium',
                    'description': "Catalyst date has passed - reevaluate thesis"
                })
            elif days_until < 7:
                factors.append({
                    'type': 'catalyst_approaching',
                    'severity': 'info',
                    'description': f"Catalyst in {days_until} days - prepare for volatility"
                })

        return {
            'confidence': min(confidence, 100),
            'factors': factors
        }

    def _assess_position_risk(
        self,
        trade: Trade,
        current_price: float,
        portfolio_value: float,
    ) -> Dict[str, Any]:
        """Assess position-related risk factors."""
        factors = []
        confidence = 0

        # Calculate position metrics
        position_value = trade.total_shares * current_price
        position_pct = (position_value / portfolio_value) * 100 if portfolio_value > 0 else 0

        avg_cost = trade.average_cost
        if avg_cost > 0:
            pnl_pct = ((current_price - avg_cost) / avg_cost) * 100
        else:
            pnl_pct = 0

        # Check concentration risk
        max_position = trade.scaling_plan.max_position_pct
        if position_pct > max_position:
            confidence += 25
            factors.append({
                'type': 'concentration',
                'severity': 'high',
                'description': f"Position oversized ({position_pct:.1f}% vs {max_position}% max)"
            })
        elif position_pct > max_position * 0.8:
            confidence += 10
            factors.append({
                'type': 'concentration',
                'severity': 'medium',
                'description': f"Position near max size ({position_pct:.1f}%)"
            })

        # Check drawdown risk
        stop_loss = trade.scaling_plan.stop_loss_pct
        if pnl_pct < 0:
            drawdown_severity = abs(pnl_pct) / stop_loss if stop_loss > 0 else 0
            if drawdown_severity > 0.8:
                confidence += 30
                factors.append({
                    'type': 'drawdown',
                    'severity': 'high',
                    'description': f"Near stop loss ({pnl_pct:.1f}% vs {stop_loss}% stop)"
                })
            elif drawdown_severity > 0.5:
                confidence += 15
                factors.append({
                    'type': 'drawdown',
                    'severity': 'medium',
                    'description': f"Position underwater ({pnl_pct:.1f}%)"
                })

        return {
            'confidence': min(confidence, 100),
            'factors': factors,
            'metrics': {
                'position_value': position_value,
                'position_pct': position_pct,
                'pnl_pct': pnl_pct,
            }
        }

    def _generate_recommendation(
        self,
        trade: Trade,
        risk_level: RiskLevel,
        factors: List[Dict],
        current_price: float = None,
    ) -> Dict[str, Any]:
        """Generate actionable recommendation based on risk assessment."""
        recommendations = {
            RiskLevel.CRITICAL: {
                'action': 'exit',
                'message': "EXIT IMMEDIATELY - Multiple high-confidence exit signals",
                'size_pct': 100,
            },
            RiskLevel.HIGH: {
                'action': 'reduce',
                'message': "REDUCE POSITION - Strong exit signals present",
                'size_pct': 50,
            },
            RiskLevel.ELEVATED: {
                'action': 'reduce',
                'message': "CONSIDER REDUCING - Elevated risk factors",
                'size_pct': 25,
            },
            RiskLevel.MODERATE: {
                'action': 'monitor',
                'message': "MONITOR CLOSELY - Some risk factors present",
                'size_pct': 0,
            },
            RiskLevel.LOW: {
                'action': 'hold',
                'message': "HOLD - Normal risk levels",
                'size_pct': 0,
            },
            RiskLevel.NONE: {
                'action': 'hold',
                'message': "NO ACTION - Position healthy",
                'size_pct': 0,
            },
        }

        rec = recommendations.get(risk_level, recommendations[RiskLevel.NONE]).copy()

        # Add specific guidance based on factors
        if factors:
            high_severity = [f for f in factors if f.get('severity') == 'high']
            if high_severity:
                rec['primary_concern'] = high_severity[0]['description']

        # Calculate shares to sell if applicable
        if rec['size_pct'] > 0 and trade.total_shares > 0:
            shares_to_sell = int(trade.total_shares * rec['size_pct'] / 100)
            rec['shares_to_sell'] = shares_to_sell
            if current_price:
                rec['estimated_proceeds'] = shares_to_sell * current_price

        return rec

    def _determine_urgency(
        self,
        risk_level: RiskLevel,
        factors: List[Dict],
    ) -> str:
        """Determine urgency of action."""
        if risk_level == RiskLevel.CRITICAL:
            return 'immediate'
        elif risk_level == RiskLevel.HIGH:
            return 'soon'
        elif risk_level == RiskLevel.ELEVATED:
            return 'soon'
        elif risk_level == RiskLevel.MODERATE:
            return 'monitor'
        else:
            return 'none'

    # Portfolio-Level Risk

    def assess_portfolio_risk(
        self,
        trades: List[Trade],
        trade_signals: Dict[str, List[ExitSignal]] = None,
        current_prices: Dict[str, float] = None,
        portfolio_value: float = None,
    ) -> Dict[str, Any]:
        """
        Assess risk across entire portfolio.

        Returns:
            Dict with:
            - overall_risk: Portfolio risk level
            - risk_score: 0-100
            - high_risk_trades: List of trades needing attention
            - concentration_risk: Sector/theme concentration
            - recommendations: Prioritized action list
        """
        trade_signals = trade_signals or {}
        current_prices = current_prices or {}

        # Assess each trade
        trade_assessments = []
        for trade in trades:
            if trade.status == TradeStatus.CLOSED:
                continue

            signals = trade_signals.get(trade.ticker, [])
            price = current_prices.get(trade.ticker)

            assessment = self.assess_trade_risk(
                trade, signals, price, portfolio_value
            )
            trade_assessments.append(assessment)

        # Identify high-risk trades
        high_risk_trades = [
            a for a in trade_assessments
            if a['risk_level'] in [RiskLevel.CRITICAL, RiskLevel.HIGH, RiskLevel.ELEVATED]
        ]

        # Sort by confidence (highest first)
        high_risk_trades.sort(key=lambda x: x['confidence'], reverse=True)

        # Calculate portfolio risk score
        if trade_assessments:
            # Weighted by position size would be better, but using simple average
            avg_confidence = sum(a['confidence'] for a in trade_assessments) / len(trade_assessments)
            max_confidence = max(a['confidence'] for a in trade_assessments)
            # Portfolio risk influenced more by worst position
            portfolio_risk_score = (avg_confidence * 0.3) + (max_confidence * 0.7)
        else:
            portfolio_risk_score = 0

        overall_risk = RiskLevel.from_confidence(portfolio_risk_score)

        # Check concentration risk
        concentration = self._check_concentration(trades, current_prices, portfolio_value)

        # Generate prioritized recommendations
        recommendations = self._prioritize_recommendations(high_risk_trades)

        return {
            'overall_risk': overall_risk,
            'risk_score': round(portfolio_risk_score, 1),
            'trade_count': len(trade_assessments),
            'high_risk_count': len(high_risk_trades),
            'high_risk_trades': high_risk_trades[:5],  # Top 5
            'concentration_risk': concentration,
            'recommendations': recommendations,
            'all_assessments': trade_assessments,
        }

    def _check_concentration(
        self,
        trades: List[Trade],
        current_prices: Dict[str, float],
        portfolio_value: float,
    ) -> Dict[str, Any]:
        """Check for concentration risk by theme/sector."""
        if not portfolio_value:
            return {'has_concentration_risk': False}

        theme_exposure = {}
        for trade in trades:
            if trade.status == TradeStatus.CLOSED:
                continue

            price = current_prices.get(trade.ticker, 0)
            value = trade.total_shares * price

            theme = trade.theme or 'Unknown'
            theme_exposure[theme] = theme_exposure.get(theme, 0) + value

        # Calculate percentages
        theme_pcts = {
            theme: (value / portfolio_value) * 100
            for theme, value in theme_exposure.items()
        }

        # Check for concentration (>30% in one theme)
        concentrated_themes = {
            theme: pct for theme, pct in theme_pcts.items()
            if pct > 30
        }

        return {
            'has_concentration_risk': bool(concentrated_themes),
            'concentrated_themes': concentrated_themes,
            'theme_exposure': theme_pcts,
        }

    def _prioritize_recommendations(
        self,
        high_risk_trades: List[Dict],
    ) -> List[Dict[str, Any]]:
        """Generate prioritized list of recommendations."""
        recommendations = []

        for assessment in high_risk_trades:
            rec = assessment['recommendation']
            priority = 1 if assessment['urgency'] == 'immediate' else (
                2 if assessment['urgency'] == 'soon' else 3
            )

            recommendations.append({
                'priority': priority,
                'ticker': assessment['ticker'],
                'action': rec['action'],
                'message': rec['message'],
                'risk_level': assessment['risk_level'].value,
                'confidence': assessment['confidence'],
            })

        # Sort by priority, then confidence
        recommendations.sort(key=lambda x: (x['priority'], -x['confidence']))

        return recommendations

    # Alerts

    def format_risk_alert(
        self,
        assessment: Dict[str, Any],
        trade: Trade = None,
    ) -> str:
        """Format risk assessment as alert message."""
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
            f"{emoji} **RISK ALERT: {assessment['ticker']}**",
            f"Risk Level: {risk_level.value.upper()} ({assessment['confidence']:.0f}%)",
            f"Urgency: {assessment['urgency'].upper()}",
        ]

        # Add recommendation
        rec = assessment['recommendation']
        lines.append(f"\n**Recommendation:** {rec['message']}")

        if rec.get('shares_to_sell'):
            lines.append(f"Suggested: Sell {rec['shares_to_sell']} shares")
            if rec.get('estimated_proceeds'):
                lines.append(f"Est. proceeds: ${rec['estimated_proceeds']:,.0f}")

        # Add key factors
        if assessment['factors']:
            lines.append("\n**Risk Factors:**")
            for factor in assessment['factors'][:3]:  # Top 3
                severity_icon = "⚠️" if factor['severity'] == 'high' else "📍"
                lines.append(f"  {severity_icon} {factor['description']}")

        # Add position info
        if trade:
            lines.append(f"\n**Position:** {trade.total_shares} shares @ ${trade.average_cost:.2f}")
            lines.append(f"Days Held: {trade.days_held}")

        return "\n".join(lines)

    def format_portfolio_alert(
        self,
        portfolio_assessment: Dict[str, Any],
    ) -> str:
        """Format portfolio risk assessment as alert message."""
        risk_emoji = {
            RiskLevel.CRITICAL: "🔴",
            RiskLevel.HIGH: "🟠",
            RiskLevel.ELEVATED: "🟡",
            RiskLevel.MODERATE: "🟢",
            RiskLevel.LOW: "⚪",
            RiskLevel.NONE: "✅",
        }

        overall = portfolio_assessment['overall_risk']
        emoji = risk_emoji.get(overall, "⚪")

        lines = [
            f"{emoji} **PORTFOLIO RISK SUMMARY**",
            f"Overall Risk: {overall.value.upper()} ({portfolio_assessment['risk_score']:.0f}/100)",
            f"Positions: {portfolio_assessment['trade_count']} | High Risk: {portfolio_assessment['high_risk_count']}",
        ]

        # Add high-risk trades
        if portfolio_assessment['high_risk_trades']:
            lines.append("\n**Attention Required:**")
            for trade in portfolio_assessment['high_risk_trades'][:3]:
                t_emoji = risk_emoji.get(trade['risk_level'], "⚪")
                lines.append(f"  {t_emoji} {trade['ticker']}: {trade['risk_level'].value} ({trade['confidence']:.0f}%)")

        # Add concentration warning
        conc = portfolio_assessment['concentration_risk']
        if conc.get('has_concentration_risk'):
            lines.append("\n⚠️ **Concentration Risk:**")
            for theme, pct in conc.get('concentrated_themes', {}).items():
                lines.append(f"  • {theme}: {pct:.1f}%")

        # Add top recommendations
        if portfolio_assessment['recommendations']:
            lines.append("\n**Priority Actions:**")
            for rec in portfolio_assessment['recommendations'][:3]:
                lines.append(f"  {rec['priority']}. {rec['ticker']}: {rec['action'].upper()}")

        return "\n".join(lines)


# Global advisor instance
_risk_advisor: Optional[RiskAdvisor] = None


def get_risk_advisor() -> RiskAdvisor:
    """Get or create global risk advisor instance."""
    global _risk_advisor
    if _risk_advisor is None:
        _risk_advisor = RiskAdvisor()
    return _risk_advisor
