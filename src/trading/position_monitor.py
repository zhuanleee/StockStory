#!/usr/bin/env python3
"""
Position Monitor
================
Continuously monitors open positions and generates exit alerts.

Features:
- Real-time position monitoring
- Automatic exit signal detection
- Telegram alerts for urgent exits
- Dashboard integration
- Learning from exit decisions
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
from pathlib import Path
import json
import asyncio

from src.trading.exit_analyzer import ExitAnalyzer, ExitAnalysis, ExitUrgency
from src.utils import get_logger, send_message
from src.config import config

logger = get_logger(__name__)


class PositionMonitor:
    """Monitors positions and triggers exit alerts."""

    def __init__(self):
        self.exit_analyzer = ExitAnalyzer()
        self.cache_dir = Path("data/position_monitoring")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Alert thresholds
        self.ALERT_URGENCIES = [
            ExitUrgency.EMERGENCY,
            ExitUrgency.CRITICAL,
            ExitUrgency.HIGH
        ]

        # Alert history (prevent spam)
        self.last_alert_time: Dict[str, datetime] = {}
        self.MIN_ALERT_INTERVAL_MINUTES = 60  # Don't alert same ticker within 1 hour

        logger.info("Position Monitor initialized")

    async def monitor_position(
        self,
        ticker: str,
        entry_price: float,
        entry_date: datetime,
        current_price: float,
        position_size: float = None
    ) -> ExitAnalysis:
        """
        Monitor a single position and return exit analysis.

        Args:
            ticker: Stock ticker
            entry_price: Entry price
            entry_date: Entry datetime
            current_price: Current price
            position_size: Position size (optional)

        Returns:
            Exit analysis with signals and recommendations
        """
        logger.info(f"Monitoring position: {ticker}")

        # Gather component data
        component_data = await self._gather_component_data(ticker)

        # Run exit analysis
        analysis = self.exit_analyzer.analyze_exit(
            ticker=ticker,
            entry_price=entry_price,
            entry_date=entry_date,
            current_price=current_price,
            component_data=component_data,
            position_size=position_size
        )

        # Save analysis
        self._save_analysis(ticker, analysis)

        # Send alerts if needed
        await self._send_alerts_if_needed(ticker, analysis)

        return analysis

    async def monitor_all_positions(self, positions: List[Dict]) -> List[ExitAnalysis]:
        """
        Monitor all open positions.

        Args:
            positions: List of position dicts with keys:
                - ticker
                - entry_price
                - entry_date
                - shares
                - current_price (optional, will fetch if missing)

        Returns:
            List of exit analyses
        """
        logger.info(f"Monitoring {len(positions)} positions")

        analyses = []

        for position in positions:
            try:
                ticker = position['ticker']
                entry_price = position['entry_price']
                entry_date = position['entry_date']
                shares = position.get('shares', 0)

                # Get current price
                current_price = position.get('current_price')
                if not current_price:
                    current_price = await self._fetch_current_price(ticker)

                # Monitor position
                analysis = await self.monitor_position(
                    ticker=ticker,
                    entry_price=entry_price,
                    entry_date=entry_date,
                    current_price=current_price,
                    position_size=shares
                )

                analyses.append(analysis)

            except Exception as e:
                logger.error(f"Error monitoring {position.get('ticker', 'unknown')}: {e}")
                continue

        # Sort by urgency
        analyses.sort(key=lambda a: a.highest_urgency.value, reverse=True)

        # Send summary if critical positions
        await self._send_summary_if_critical(analyses)

        return analyses

    async def _gather_component_data(self, ticker: str) -> Dict:
        """
        Gather data from all 38 components.

        This integrates with existing scanner/intelligence modules.
        """
        try:
            # Import scanner components
            from src.core.async_scanner import AsyncScanner
            from src.intelligence.x_intelligence import XIntelligence
            from src.intelligence.google_trends import GoogleTrendsTracker
            from src.scoring.ai_scorer import AIScorer
            from src.scoring.earnings_scorer import EarningsScorer

            component_data = {}

            # Scan ticker (gets technical, theme, sentiment data)
            scanner = AsyncScanner()
            scan_result = await scanner.scan_ticker(ticker)

            if scan_result:
                component_data['technical'] = {
                    'momentum': scan_result.get('technical_score', 50),
                    'volume_score': scan_result.get('volume_score', 50),
                    'rs_rating': scan_result.get('rs_rating', 50),
                    'volatility': scan_result.get('volatility', 0.02),
                    'ma_health': scan_result.get('ma_health', 50),
                }

                component_data['theme'] = {
                    'strength': scan_result.get('theme_strength', 50),
                    'leadership': scan_result.get('theme_leadership', 50),
                }

                component_data['sentiment'] = {
                    'x_score': scan_result.get('x_sentiment', 50),
                    'reddit_score': scan_result.get('reddit_sentiment', 50),
                    'stocktwits_score': scan_result.get('stocktwits_sentiment', 50),
                }

            # Get X intelligence
            try:
                x_intel = XIntelligence()
                x_data = x_intel.get_ticker_intelligence(ticker)
                if x_data:
                    component_data.setdefault('sentiment', {})['x_score'] = x_data.get('sentiment_score', 50) * 100
                    component_data.setdefault('sentiment', {})['viral_score'] = x_data.get('viral_posts', 0) * 10
            except Exception as e:
                logger.debug(f"X intelligence unavailable: {e}")

            # Get Google Trends
            try:
                trends = GoogleTrendsTracker()
                trend_data = trends.get_ticker_trend(ticker)
                if trend_data:
                    component_data.setdefault('catalyst', {})['freshness'] = trend_data.get('interest_score', 50)
            except Exception as e:
                logger.debug(f"Trends unavailable: {e}")

            # Get AI scores
            try:
                ai_scorer = AIScorer()
                ai_score = ai_scorer.score_ticker(ticker, scan_result or {})
                component_data['ai'] = {
                    'conviction': ai_score.get('conviction', 50),
                    'risk': ai_score.get('risk', 50),
                    'opportunity': ai_score.get('opportunity', 50),
                }
            except Exception as e:
                logger.debug(f"AI scoring unavailable: {e}")

            # Get earnings data
            try:
                earnings_scorer = EarningsScorer()
                earnings_score = earnings_scorer.score(ticker, {})
                component_data['earnings'] = {
                    'tone_score': earnings_score.get('tone', 50),
                    'guidance_score': earnings_score.get('guidance', 50),
                    'beat_rate': earnings_score.get('beat_rate', 50),
                }
            except Exception as e:
                logger.debug(f"Earnings scoring unavailable: {e}")

            # Add placeholder data for components we don't have real-time access to
            component_data.setdefault('institutional', {}).update({
                'ownership_score': 50,
                'dark_pool_score': 50,
                'options_score': 50,
                'smart_money_score': 50,
            })

            component_data.setdefault('fundamental', {}).update({
                'revenue_score': 50,
                'margin_score': 50,
                'valuation_score': 50,
                'insider_score': 50,
            })

            return component_data

        except Exception as e:
            logger.error(f"Error gathering component data for {ticker}: {e}")
            return {}

    async def _fetch_current_price(self, ticker: str) -> float:
        """Fetch current price for ticker."""
        try:
            import yfinance as yf
            stock = yf.Ticker(ticker)
            hist = stock.history(period='1d')
            if not hist.empty:
                return float(hist['Close'].iloc[-1])
        except Exception as e:
            logger.error(f"Error fetching price for {ticker}: {e}")

        return 0.0

    def _save_analysis(self, ticker: str, analysis: ExitAnalysis):
        """Save exit analysis to cache."""
        try:
            cache_file = self.cache_dir / f"{ticker}_exit_analysis.json"

            data = {
                'ticker': ticker,
                'timestamp': analysis.timestamp.isoformat(),
                'current_price': analysis.current_price,
                'entry_price': analysis.entry_price,
                'current_pnl_pct': analysis.current_pnl_pct,
                'holding_days': analysis.holding_days,
                'overall_health': analysis.overall_health_score,
                'should_exit': analysis.should_exit,
                'highest_urgency': analysis.highest_urgency.name,
                'recommended_action': analysis.recommended_action,
                'action_timeframe': analysis.action_timeframe,
                'targets': {
                    'bull': analysis.bull_target.target,
                    'base': analysis.base_target.target,
                    'bear': analysis.bear_target.target,
                    'current': analysis.current_target,
                },
                'risk': {
                    'stop_loss': analysis.stop_loss,
                    'trailing_stop': analysis.trailing_stop,
                },
                'signals': [
                    {
                        'urgency': s.urgency.name,
                        'reason': s.reason.value,
                        'primary_reason': s.primary_reason,
                        'recommended_action': s.recommended_action,
                    }
                    for s in analysis.exit_signals
                ],
                'component_health': analysis.component_health,
            }

            with open(cache_file, 'w') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.error(f"Error saving analysis for {ticker}: {e}")

    async def _send_alerts_if_needed(self, ticker: str, analysis: ExitAnalysis):
        """Send Telegram alerts for urgent exit signals."""
        # Check if should alert
        if analysis.highest_urgency not in self.ALERT_URGENCIES:
            return

        # Check alert cooldown
        last_alert = self.last_alert_time.get(ticker)
        if last_alert:
            minutes_since = (datetime.now() - last_alert).total_seconds() / 60
            if minutes_since < self.MIN_ALERT_INTERVAL_MINUTES:
                return

        # Send alert
        message = self._format_alert_message(ticker, analysis)
        await self._send_telegram_alert(message)

        # Update last alert time
        self.last_alert_time[ticker] = datetime.now()

    def _format_alert_message(self, ticker: str, analysis: ExitAnalysis) -> str:
        """Format Telegram alert message."""
        urgency_emoji = {
            ExitUrgency.EMERGENCY: "🚨🚨🚨",
            ExitUrgency.CRITICAL: "🚨🚨",
            ExitUrgency.HIGH: "⚠️",
            ExitUrgency.MODERATE: "⚡",
            ExitUrgency.LOW: "💡",
        }

        emoji = urgency_emoji.get(analysis.highest_urgency, "📊")

        lines = [
            f"{emoji} EXIT ALERT: {ticker}",
            "",
            f"💰 Entry: ${analysis.entry_price:.2f} → Current: ${analysis.current_price:.2f}",
            f"📈 P/L: {analysis.current_pnl_pct:+.1f}% ({analysis.holding_days} days)",
            f"💊 Health: {analysis.overall_health_score:.0f}/100",
            "",
            f"🎯 Urgency: {analysis.highest_urgency.name}",
            f"📋 Action: {analysis.recommended_action}",
            f"⏰ Timeframe: {analysis.action_timeframe.upper()}",
            "",
        ]

        # Add top exit signals
        if analysis.exit_signals:
            lines.append("🚨 Exit Signals:")
            for signal in analysis.exit_signals[:2]:
                lines.append(f"  • {signal.primary_reason}")

            lines.append("")

        # Add targets
        lines.append(f"🎯 Targets:")
        lines.append(f"  Stop Loss: ${analysis.stop_loss:.2f}")
        lines.append(f"  Trailing: ${analysis.trailing_stop:.2f}")
        lines.append(f"  Target: ${analysis.current_target:.2f}")

        return "\n".join(lines)

    async def _send_telegram_alert(self, message: str):
        """Send Telegram alert."""
        try:
            send_message(config.get('TELEGRAM_CHAT_ID'), message)
            logger.info("Exit alert sent via Telegram")
        except Exception as e:
            logger.error(f"Error sending Telegram alert: {e}")

    async def _send_summary_if_critical(self, analyses: List[ExitAnalysis]):
        """Send summary if multiple critical positions."""
        critical = [
            a for a in analyses
            if a.highest_urgency in [ExitUrgency.EMERGENCY, ExitUrgency.CRITICAL]
        ]

        if len(critical) >= 2:
            message = "🚨 PORTFOLIO ALERT: Multiple positions need attention\n\n"

            for analysis in critical[:5]:
                message += f"• {analysis.ticker}: {analysis.highest_urgency.name}\n"
                message += f"  {analysis.recommended_action}\n\n"

            message += f"\nTotal positions requiring action: {len(critical)}"

            await self._send_telegram_alert(message)

    def get_cached_analysis(self, ticker: str) -> Optional[Dict]:
        """Get cached exit analysis for ticker."""
        try:
            cache_file = self.cache_dir / f"{ticker}_exit_analysis.json"
            if cache_file.exists():
                with open(cache_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading cached analysis for {ticker}: {e}")

        return None


# Singleton instance
_monitor = None

def get_position_monitor() -> PositionMonitor:
    """Get singleton position monitor instance."""
    global _monitor
    if _monitor is None:
        _monitor = PositionMonitor()
    return _monitor
