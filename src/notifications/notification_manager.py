"""
Centralized Notification Manager

Handles all system notifications across multiple channels:
- Telegram
- Email (SMTP)
- Slack (future)

Used by all automated alerts and reports.
"""

import os
import logging
from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class NotificationChannel(Enum):
    """Supported notification channels"""
    TELEGRAM = "telegram"
    EMAIL = "email"
    SLACK = "slack"


class NotificationPriority(Enum):
    """Notification priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationManager:
    """
    Centralized notification manager for all system alerts.

    Environment variables required:
    - TELEGRAM_BOT_TOKEN: Telegram bot token
    - TELEGRAM_CHAT_ID: Telegram chat ID
    - SMTP_HOST: Email SMTP host (optional)
    - SMTP_PORT: Email SMTP port (optional)
    - SMTP_USER: Email username (optional)
    - SMTP_PASSWORD: Email password (optional)
    - NOTIFICATION_EMAIL: Recipient email (optional)
    """

    def __init__(self):
        self.telegram_enabled = self._check_telegram_config()
        self.email_enabled = self._check_email_config()
        self.slack_enabled = False  # Future implementation

        logger.info(f"Notification channels: Telegram={self.telegram_enabled}, Email={self.email_enabled}")

    def _check_telegram_config(self) -> bool:
        """Check if Telegram is configured"""
        return bool(os.environ.get('TELEGRAM_BOT_TOKEN') and os.environ.get('TELEGRAM_CHAT_ID'))

    def _check_email_config(self) -> bool:
        """Check if Email is configured"""
        return bool(
            os.environ.get('SMTP_HOST') and
            os.environ.get('SMTP_USER') and
            os.environ.get('NOTIFICATION_EMAIL')
        )

    def send(
        self,
        message: str,
        title: Optional[str] = None,
        channels: Optional[List[NotificationChannel]] = None,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        parse_mode: str = "Markdown"
    ) -> Dict[str, bool]:
        """
        Send notification to specified channels.

        Args:
            message: Notification message content
            title: Optional message title
            channels: List of channels to send to (default: all enabled)
            priority: Message priority level
            parse_mode: Message format (Markdown, HTML, or None)

        Returns:
            Dict mapping channel names to success status
        """
        if channels is None:
            channels = self._get_enabled_channels()

        results = {}

        for channel in channels:
            try:
                if channel == NotificationChannel.TELEGRAM and self.telegram_enabled:
                    results['telegram'] = self._send_telegram(message, title, parse_mode)
                elif channel == NotificationChannel.EMAIL and self.email_enabled:
                    results['email'] = self._send_email(message, title)
                elif channel == NotificationChannel.SLACK and self.slack_enabled:
                    results['slack'] = self._send_slack(message, title)
                else:
                    logger.debug(f"Channel {channel.value} not enabled or configured")
                    results[channel.value] = False
            except Exception as e:
                logger.error(f"Failed to send {channel.value} notification: {e}")
                results[channel.value] = False

        return results

    def _get_enabled_channels(self) -> List[NotificationChannel]:
        """Get list of enabled notification channels"""
        channels = []
        if self.telegram_enabled:
            channels.append(NotificationChannel.TELEGRAM)
        if self.email_enabled:
            channels.append(NotificationChannel.EMAIL)
        if self.slack_enabled:
            channels.append(NotificationChannel.SLACK)
        return channels

    def _send_telegram(self, message: str, title: Optional[str], parse_mode: str) -> bool:
        """Send Telegram notification"""
        try:
            import requests

            bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
            chat_id = os.environ.get('TELEGRAM_CHAT_ID')

            # Format message with title
            full_message = message
            if title:
                if parse_mode == "Markdown":
                    full_message = f"*{title}*\n\n{message}"
                elif parse_mode == "HTML":
                    full_message = f"<b>{title}</b>\n\n{message}"
                else:
                    full_message = f"{title}\n\n{message}"

            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": full_message,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True
            }

            response = requests.post(url, json=payload, timeout=10)
            success = response.status_code == 200

            if success:
                logger.info("Telegram notification sent successfully")
            else:
                logger.error(f"Telegram notification failed: {response.status_code} {response.text}")

            return success

        except Exception as e:
            logger.error(f"Telegram notification error: {e}")
            return False

    def _send_email(self, message: str, title: Optional[str]) -> bool:
        """Send Email notification"""
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            smtp_host = os.environ.get('SMTP_HOST')
            smtp_port = int(os.environ.get('SMTP_PORT', '587'))
            smtp_user = os.environ.get('SMTP_USER')
            smtp_password = os.environ.get('SMTP_PASSWORD')
            recipient = os.environ.get('NOTIFICATION_EMAIL')

            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = title or "Stock Scanner Notification"
            msg['From'] = smtp_user
            msg['To'] = recipient

            # Convert Markdown to plain text (simple conversion)
            plain_text = message.replace('*', '').replace('_', '').replace('`', '')

            # Attach plain text
            msg.attach(MIMEText(plain_text, 'plain'))

            # Send email
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.send_message(msg)

            logger.info("Email notification sent successfully")
            return True

        except Exception as e:
            logger.error(f"Email notification error: {e}")
            return False

    def _send_slack(self, message: str, title: Optional[str]) -> bool:
        """Send Slack notification (future implementation)"""
        logger.warning("Slack notifications not yet implemented")
        return False

    def send_alert(
        self,
        alert_type: str,
        data: Dict,
        priority: NotificationPriority = NotificationPriority.MEDIUM
    ) -> Dict[str, bool]:
        """
        Send formatted alert using templates.

        Args:
            alert_type: Type of alert (theme_discovery, conviction, rotation, etc.)
            data: Alert-specific data
            priority: Alert priority level

        Returns:
            Dict mapping channel names to success status
        """
        message = self._format_alert(alert_type, data)
        title = self._get_alert_title(alert_type)

        return self.send(message, title=title, priority=priority)

    def _get_alert_title(self, alert_type: str) -> str:
        """Get title for alert type"""
        titles = {
            'theme_discovery': '🔍 New Themes Discovered',
            'conviction': '🎯 High Conviction Alert',
            'unusual_options': '🔥 Unusual Options Activity',
            'rotation': '🔄 Sector Rotation Alert',
            'institutional': '💼 Institutional Flow Alert',
            'executive': '📢 Executive Commentary',
            'learning_health': '⚙️ Learning System Health',
            'data_staleness': '⚠️ Data Staleness Warning',
            'briefing': '📊 Daily Market Briefing',
            'weekly_summary': '📈 Weekly Summary Report',
            'crisis_alert': '🚨 CRISIS ALERT',
            'crisis_emergency': '🚨🚨🚨 EMERGENCY PROTOCOL',
            'crisis_major': '⚠️ MAJOR CRISIS DETECTED'
        }
        return titles.get(alert_type, '📬 Stock Scanner Alert')

    def _format_alert(self, alert_type: str, data: Dict) -> str:
        """Format alert message using templates"""
        formatters = {
            'theme_discovery': self._format_theme_discovery,
            'conviction': self._format_conviction_alert,
            'unusual_options': self._format_options_alert,
            'rotation': self._format_rotation_alert,
            'institutional': self._format_institutional_alert,
            'executive': self._format_executive_alert,
            'learning_health': self._format_learning_health,
            'data_staleness': self._format_staleness_alert,
            'briefing': self._format_briefing,
            'weekly_summary': self._format_weekly_summary,
            'crisis_alert': self._format_crisis_alert,
            'crisis_emergency': self._format_crisis_alert,
            'crisis_major': self._format_crisis_alert
        }

        formatter = formatters.get(alert_type, self._format_generic)
        return formatter(data)

    def _format_theme_discovery(self, data: Dict) -> str:
        """Format theme discovery alert"""
        themes = data.get('themes', [])
        timestamp = data.get('timestamp', datetime.now().isoformat())

        message = f"Discovered {len(themes)} emerging themes:\n\n"

        for i, theme in enumerate(themes[:5], 1):
            name = theme.get('name', 'Unknown')
            confidence = theme.get('confidence', 0)
            laggards = theme.get('laggards', 0)
            method = theme.get('method', 'unknown')

            message += f"{i}. *{name}*\n"
            message += f"   Confidence: {confidence:.1f}%\n"
            message += f"   Laggards: {laggards}\n"
            message += f"   Method: {method}\n\n"

        message += f"\n_Updated: {timestamp}_"
        return message

    def _format_conviction_alert(self, data: Dict) -> str:
        """Format conviction alert"""
        stocks = data.get('stocks', [])

        message = f"Found {len(stocks)} high-conviction opportunities:\n\n"

        for stock in stocks[:10]:
            ticker = stock.get('ticker', 'Unknown')
            score = stock.get('score', 0)
            theme = stock.get('theme', 'No theme')

            message += f"*{ticker}* - Score: {score:.1f}\n"
            message += f"   Theme: {theme}\n\n"

        return message

    def _format_options_alert(self, data: Dict) -> str:
        """Format unusual options activity alert"""
        activities = data.get('activities', [])

        message = f"Unusual options activity detected:\n\n"

        for activity in activities[:10]:
            ticker = activity.get('ticker', 'Unknown')
            volume = activity.get('volume', 0)
            sentiment = activity.get('sentiment', 'neutral')

            message += f"*{ticker}*\n"
            message += f"   Volume: {volume:,}\n"
            message += f"   Sentiment: {sentiment}\n\n"

        return message

    def _format_rotation_alert(self, data: Dict) -> str:
        """Format sector rotation alert"""
        rotations = data.get('rotations', [])
        peaks = data.get('peaks', [])

        message = ""

        if rotations:
            message += f"*Sector Rotations:*\n"
            for rotation in rotations[:5]:
                from_sector = rotation.get('from', 'Unknown')
                to_sector = rotation.get('to', 'Unknown')
                strength = rotation.get('strength', 0)
                message += f"• {from_sector} → {to_sector} ({strength:.1f}%)\n"
            message += "\n"

        if peaks:
            message += f"*Peak Warnings:*\n"
            for peak in peaks[:5]:
                sector = peak.get('sector', 'Unknown')
                risk = peak.get('risk', 'low')
                message += f"• {sector}: {risk} risk\n"

        return message

    def _format_institutional_alert(self, data: Dict) -> str:
        """Format institutional flow alert"""
        flows = data.get('flows', [])

        message = f"Institutional activity detected:\n\n"

        for flow in flows[:10]:
            ticker = flow.get('ticker', 'Unknown')
            flow_type = flow.get('type', 'unknown')
            magnitude = flow.get('magnitude', 0)

            message += f"*{ticker}*\n"
            message += f"   Type: {flow_type}\n"
            message += f"   Magnitude: ${magnitude:,.0f}\n\n"

        return message

    def _format_executive_alert(self, data: Dict) -> str:
        """Format executive commentary alert"""
        commentaries = data.get('commentaries', [])

        message = f"Executive commentary updates:\n\n"

        for commentary in commentaries[:5]:
            ticker = commentary.get('ticker', 'Unknown')
            executive = commentary.get('executive', 'Unknown')
            sentiment = commentary.get('sentiment', 'neutral')
            summary = commentary.get('summary', 'No summary')

            message += f"*{ticker}* - {executive}\n"
            message += f"   Sentiment: {sentiment}\n"
            message += f"   {summary}\n\n"

        return message

    def _format_learning_health(self, data: Dict) -> str:
        """Format learning system health alert"""
        status = data.get('status', 'unknown')
        win_rate = data.get('win_rate', 0)
        stale_params = data.get('stale_params', 0)

        message = f"Learning System Status: *{status}*\n\n"
        message += f"Win Rate: {win_rate:.1f}%\n"
        message += f"Stale Parameters: {stale_params}\n"

        if status != 'healthy':
            issues = data.get('issues', [])
            message += f"\n*Issues:*\n"
            for issue in issues:
                message += f"• {issue}\n"

        return message

    def _format_staleness_alert(self, data: Dict) -> str:
        """Format data staleness alert"""
        stale_sources = data.get('stale_sources', [])

        message = f"⚠️ Data staleness detected:\n\n"

        for source in stale_sources:
            name = source.get('name', 'Unknown')
            age = source.get('age_hours', 0)
            message += f"• {name}: {age:.1f} hours old\n"

        return message

    def _format_briefing(self, data: Dict) -> str:
        """Format daily executive briefing"""
        return data.get('message', 'No briefing available')

    def _format_weekly_summary(self, data: Dict) -> str:
        """Format weekly summary report"""
        return data.get('message', 'No summary available')

    def _format_crisis_alert(self, data: Dict) -> str:
        """Format crisis alert from X Intelligence"""
        severity = data.get('severity', 0)
        topic = data.get('topic', 'Unknown Crisis')
        crisis_type = data.get('crisis_type', 'unknown')
        description = data.get('description', 'No description available')
        verified = data.get('verified', False)
        credibility = data.get('credibility_score', 0)
        affected_sectors = data.get('affected_sectors', [])
        affected_tickers = data.get('affected_tickers', [])
        immediate_actions = data.get('immediate_actions', [])
        protocol_type = data.get('protocol_type', 'warning')

        # Severity indicator
        if severity >= 9:
            severity_icon = "🚨🚨🚨"
            severity_text = "CRITICAL"
        elif severity >= 7:
            severity_icon = "⚠️⚠️"
            severity_text = "MAJOR"
        else:
            severity_icon = "⚠️"
            severity_text = "WARNING"

        message = f"{severity_icon} *{severity_text} CRISIS*\n\n"
        message += f"*Topic:* {topic}\n"
        message += f"*Type:* {crisis_type}\n"
        message += f"*Severity:* {severity}/10\n"
        message += f"*Verified:* {'✓ Yes' if verified else '✗ No'}\n"
        message += f"*Credibility:* {credibility:.0%}\n\n"

        message += f"*Description:*\n{description}\n\n"

        if affected_sectors:
            message += f"*Affected Sectors:*\n"
            for sector in affected_sectors[:5]:
                message += f"  ⛔ {sector}\n"
            message += "\n"

        if affected_tickers:
            message += f"*Affected Tickers:*\n"
            ticker_str = ", ".join(affected_tickers[:10])
            if len(affected_tickers) > 10:
                ticker_str += f" (+{len(affected_tickers) - 10} more)"
            message += f"{ticker_str}\n\n"

        # Protocol-specific actions
        if protocol_type == 'emergency':
            message += "🛑 *EMERGENCY PROTOCOL ACTIVATED*\n"
            message += "• ALL TRADING HALTED\n"
            message += "• Manual intervention required to resume\n\n"
        elif protocol_type == 'major':
            message += "⚠️ *MAJOR CRISIS PROTOCOL ACTIVATED*\n"
            message += "• Risk controls tightened\n"
            message += "• Affected sectors avoided\n"
            message += "• Cautious trading mode\n\n"

        if immediate_actions:
            message += "*Immediate Actions:*\n"
            for action in immediate_actions[:5]:
                message += f"  • {action}\n"
            message += "\n"

        message += f"_X Intelligence Monitor - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_"
        return message

    def _format_generic(self, data: Dict) -> str:
        """Generic formatter for unknown alert types"""
        return str(data)


# Singleton instance
_notification_manager = None


def get_notification_manager() -> NotificationManager:
    """Get singleton notification manager instance"""
    global _notification_manager
    if _notification_manager is None:
        _notification_manager = NotificationManager()
    return _notification_manager
