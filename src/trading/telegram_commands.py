"""
Telegram Commands for Trade Management System

Commands:
- /trade <ticker> - View or create trade for ticker
- /buy <ticker> <shares> <price> [reason] - Log a buy
- /sell <ticker> <shares> <price> [reason] - Log a sell
- /watchlist - Show watchlist
- /positions - Show open positions
- /risk - Show portfolio risk assessment
- /scan - Scan all positions for exit signals
- /close <ticker> <price> - Close a position
"""

import logging
import re
from typing import Optional, Dict, Any, Tuple

from .models import Trade, ScalingStrategy, TradeStatus, RiskLevel
from .trade_manager import get_trade_manager
from .exit_scanner import get_exit_scanner
from .risk_advisor import get_risk_advisor
from .scaling_engine import get_scaling_engine
from .scan_integration import get_scan_integration

logger = logging.getLogger(__name__)


class TradeCommandHandler:
    """Handles Telegram commands for trade management."""

    def __init__(self):
        self.manager = get_trade_manager()
        self.scanner = get_exit_scanner()
        self.risk_advisor = get_risk_advisor()
        self.scaling_engine = get_scaling_engine()
        self.integration = get_scan_integration()

    def handle_command(self, text: str) -> Optional[str]:
        """
        Route command to appropriate handler.

        Args:
            text: Full command text

        Returns:
            Response message or None if not a trade command
        """
        text = text.strip()
        parts = text.split()

        if not parts:
            return None

        command = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []

        handlers = {
            '/trade': self._handle_trade,
            '/buy': self._handle_buy,
            '/sell': self._handle_sell,
            '/watchlist': self._handle_watchlist,
            '/watch': self._handle_watch,
            '/positions': self._handle_positions,
            '/pos': self._handle_positions,
            '/risk': self._handle_risk,
            '/scan': self._handle_scan,
            '/close': self._handle_close,
            '/scale': self._handle_scale,
            '/tradehelp': self._handle_trade_help,
        }

        handler = handlers.get(command)
        if handler:
            try:
                return handler(args)
            except Exception as e:
                logger.error(f"Error handling {command}: {e}")
                return f"Error: {str(e)}"

        return None

    def _handle_trade(self, args: list) -> str:
        """Handle /trade <ticker> [thesis] command."""
        if not args:
            return "Usage: `/trade TICKER [thesis...]`\nExample: `/trade NVDA AI chip leader`"

        ticker = args[0].upper()
        thesis = " ".join(args[1:]) if len(args) > 1 else ""

        # Check if trade exists
        existing = self.manager.get_trade_by_ticker(ticker)

        if existing:
            # Show existing trade
            return self._format_trade_detail(existing)
        elif thesis:
            # Create new trade on watchlist
            trade = self.manager.create_trade(
                ticker=ticker,
                thesis=thesis,
                scaling_strategy=ScalingStrategy.CONSERVATIVE,
            )
            return f"✅ Added {ticker} to watchlist\n\nThesis: {thesis}\n\nUse `/buy {ticker} <shares> <price>` to enter position"
        else:
            return f"No trade found for {ticker}.\n\nTo add to watchlist:\n`/trade {ticker} <your thesis>`"

    def _handle_buy(self, args: list) -> str:
        """Handle /buy <ticker> <shares> <price> [reason] command."""
        if len(args) < 3:
            return "Usage: `/buy TICKER SHARES PRICE [reason]`\nExample: `/buy NVDA 100 125.50 breakout entry`"

        try:
            ticker = args[0].upper()
            shares = int(args[1])
            price = float(args[2])
            reason = " ".join(args[3:]) if len(args) > 3 else "Manual entry"
        except ValueError:
            return "Invalid shares or price. Example: `/buy NVDA 100 125.50`"

        # Get or create trade
        trade = self.manager.get_trade_by_ticker(ticker)
        if not trade:
            trade = self.manager.create_trade(
                ticker=ticker,
                thesis=reason,
                scaling_strategy=ScalingStrategy.CONSERVATIVE,
            )

        # Add buy tranche
        tranche = self.manager.add_buy(
            trade_id=trade.id,
            shares=shares,
            price=price,
            reason=reason,
        )

        if tranche:
            return (
                f"✅ *BUY LOGGED*\n\n"
                f"Ticker: {ticker}\n"
                f"Shares: {shares} @ ${price:.2f}\n"
                f"Total: ${shares * price:,.2f}\n"
                f"Reason: {reason}\n\n"
                f"Position: {trade.total_shares} shares\n"
                f"Avg Cost: ${trade.average_cost:.2f}"
            )
        return "Failed to log buy"

    def _handle_sell(self, args: list) -> str:
        """Handle /sell <ticker> <shares> <price> [reason] command."""
        if len(args) < 3:
            return "Usage: `/sell TICKER SHARES PRICE [reason]`\nExample: `/sell NVDA 50 150.00 profit target 1`"

        try:
            ticker = args[0].upper()
            shares = int(args[1])
            price = float(args[2])
            reason = " ".join(args[3:]) if len(args) > 3 else "Manual exit"
        except ValueError:
            return "Invalid shares or price. Example: `/sell NVDA 50 150.00`"

        trade = self.manager.get_trade_by_ticker(ticker)
        if not trade:
            return f"No open trade found for {ticker}"

        if shares > trade.total_shares:
            shares = trade.total_shares

        tranche = self.manager.add_sell(
            trade_id=trade.id,
            shares=shares,
            price=price,
            reason=reason,
        )

        if tranche:
            pnl = (price - trade.average_cost) * shares
            pnl_pct = ((price / trade.average_cost) - 1) * 100

            status = "CLOSED" if trade.total_shares == 0 else f"{trade.total_shares} remaining"

            return (
                f"✅ *SELL LOGGED*\n\n"
                f"Ticker: {ticker}\n"
                f"Shares: {shares} @ ${price:.2f}\n"
                f"P&L: ${pnl:+,.2f} ({pnl_pct:+.1f}%)\n"
                f"Reason: {reason}\n\n"
                f"Position: {status}"
            )
        return "Failed to log sell"

    def _handle_watchlist(self, args: list) -> str:
        """Handle /watchlist command."""
        watchlist = self.manager.get_watchlist()

        if not watchlist:
            return "📋 Watchlist is empty\n\nAdd with: `/trade TICKER <thesis>`"

        lines = ["📋 *WATCHLIST*\n"]

        for trade in watchlist:
            lines.append(f"• *{trade.ticker}*")
            if trade.thesis:
                lines.append(f"  _{trade.thesis[:50]}..._" if len(trade.thesis) > 50 else f"  _{trade.thesis}_")
            if trade.theme:
                lines.append(f"  Theme: {trade.theme}")

        lines.append(f"\nTotal: {len(watchlist)} items")

        return "\n".join(lines)

    def _handle_watch(self, args: list) -> str:
        """Handle /watch <ticker> [thesis] - shortcut to add to watchlist."""
        if not args:
            return "Usage: `/watch TICKER [thesis]`"

        return self._handle_trade(args)

    def _handle_positions(self, args: list) -> str:
        """Handle /positions command."""
        positions = self.manager.get_open_trades()

        if not positions:
            return "📊 No open positions\n\nAdd with: `/buy TICKER SHARES PRICE`"

        lines = ["📊 *OPEN POSITIONS*\n"]

        total_value = 0
        for trade in positions:
            # Get current price (simplified)
            try:
                import yfinance as yf
                stock = yf.Ticker(trade.ticker)
                hist = stock.history(period='1d')
                current_price = float(hist['Close'].iloc[-1]) if not hist.empty else trade.average_cost
            except:
                current_price = trade.average_cost

            value = trade.total_shares * current_price
            total_value += value

            pnl_pct = ((current_price / trade.average_cost) - 1) * 100 if trade.average_cost > 0 else 0
            pnl_emoji = "🟢" if pnl_pct >= 0 else "🔴"

            risk_level = trade.current_risk_level
            risk_emoji = "⚠️" if risk_level in [RiskLevel.CRITICAL, RiskLevel.HIGH] else ""

            lines.append(
                f"{pnl_emoji} *{trade.ticker}* {risk_emoji}\n"
                f"  {trade.total_shares} shares @ ${trade.average_cost:.2f}\n"
                f"  P&L: {pnl_pct:+.1f}% | ${(current_price - trade.average_cost) * trade.total_shares:+,.0f}"
            )

        lines.append(f"\n*Total Value:* ${total_value:,.0f}")

        return "\n".join(lines)

    def _handle_risk(self, args: list) -> str:
        """Handle /risk [ticker] command."""
        if args:
            # Risk for specific ticker
            ticker = args[0].upper()
            result = self.integration.scan_single_position(ticker)

            if 'error' in result:
                return result['error']

            risk = result.get('risk', {})
            return self.risk_advisor.format_risk_alert(risk, result.get('trade'))

        # Portfolio risk
        positions = self.manager.get_open_trades()
        if not positions:
            return "No open positions to assess"

        results = self.integration.scan_all_positions()

        if results.get('risk_summary'):
            rs = results['risk_summary']
            lines = [
                f"🎯 *PORTFOLIO RISK*\n",
                f"Overall: *{rs['overall_risk'].upper()}* ({rs['risk_score']:.0f}/100)",
                f"Positions: {results['scanned']}",
                f"High Risk: {rs['high_risk_count']}",
            ]

            if results.get('alerts'):
                lines.append("\n*Alerts:*")
                for alert in results['alerts'][:3]:
                    lines.append(f"  ⚠️ {alert['ticker']}: {alert['risk_level'].upper()}")

            return "\n".join(lines)

        return "Could not calculate portfolio risk"

    def _handle_scan(self, args: list) -> str:
        """Handle /scan [ticker] command."""
        if args:
            # Scan specific ticker
            ticker = args[0].upper()
            result = self.integration.scan_single_position(ticker)

            if 'error' in result:
                return result['error']

            assessment = result.get('assessment', {})
            scaling = result.get('scaling_advice', {})

            lines = [
                f"🔍 *SCAN: {ticker}*\n",
                f"Price: ${result.get('current_price', 0):.2f}",
                f"P&L: {result.get('pnl_pct', 0):+.1f}%\n",
                f"*Exit Signals:*",
                f"  Confidence: {assessment.get('composite_confidence', 0):.0f}%",
                f"  Risk Level: {assessment.get('risk_level', 'unknown').upper()}",
                f"  Action: {assessment.get('recommended_action', 'hold').upper()}",
            ]

            if scaling.get('action') != 'hold':
                lines.append(f"\n*Scaling Advice:*")
                lines.append(f"  {scaling.get('action', 'hold').upper()}: {scaling.get('size_pct', 0):.0f}%")
                lines.append(f"  {scaling.get('reasoning', '')[:50]}")

            return "\n".join(lines)

        # Scan all positions
        results = self.integration.scan_all_positions()

        lines = [
            f"🔍 *POSITION SCAN*\n",
            f"Scanned: {results['scanned']} positions",
        ]

        if results.get('positions'):
            lines.append("\n*Results:*")
            for pos in sorted(results['positions'], key=lambda x: -x.get('exit_confidence', 0))[:5]:
                emoji = "🔴" if pos['risk_level'] in ['critical', 'high'] else "🟢"
                lines.append(
                    f"  {emoji} {pos['ticker']}: {pos['risk_level'].upper()} "
                    f"({pos.get('exit_confidence', 0):.0f}%)"
                )

        if results.get('alerts'):
            lines.append(f"\n⚠️ {len(results['alerts'])} alerts generated")

        return "\n".join(lines)

    def _handle_close(self, args: list) -> str:
        """Handle /close <ticker> <price> command."""
        if len(args) < 2:
            return "Usage: `/close TICKER PRICE`\nExample: `/close NVDA 150.00`"

        try:
            ticker = args[0].upper()
            price = float(args[1])
        except ValueError:
            return "Invalid price. Example: `/close NVDA 150.00`"

        trade = self.manager.get_trade_by_ticker(ticker)
        if not trade:
            return f"No open trade found for {ticker}"

        shares = trade.total_shares
        avg_cost = trade.average_cost

        if self.manager.close_trade(trade.id, price, "Manual close"):
            pnl = (price - avg_cost) * shares
            pnl_pct = ((price / avg_cost) - 1) * 100

            return (
                f"✅ *POSITION CLOSED*\n\n"
                f"Ticker: {ticker}\n"
                f"Shares: {shares} @ ${price:.2f}\n"
                f"Avg Cost: ${avg_cost:.2f}\n\n"
                f"*P&L: ${pnl:+,.2f} ({pnl_pct:+.1f}%)*"
            )

        return "Failed to close position"

    def _handle_scale(self, args: list) -> str:
        """Handle /scale <ticker> command - get scaling advice."""
        if not args:
            return "Usage: `/scale TICKER`\nExample: `/scale NVDA`"

        ticker = args[0].upper()
        result = self.integration.scan_single_position(ticker)

        if 'error' in result:
            return result['error']

        scaling = result.get('scaling_advice', {})
        trade = self.manager.get_trade_by_ticker(ticker)

        lines = [
            f"📈 *SCALING ADVICE: {ticker}*\n",
            f"Position: {trade.total_shares if trade else 0} shares",
            f"Strategy: {trade.scaling_plan.strategy.value if trade else 'N/A'}\n",
            f"*Recommendation:*",
            f"  Action: {scaling.get('action', 'hold').upper()}",
            f"  Confidence: {scaling.get('confidence', 0):.0f}%",
        ]

        if scaling.get('size_pct', 0) > 0:
            lines.append(f"  Size: {scaling.get('size_pct', 0):.0f}% of position")

        if scaling.get('reasoning'):
            lines.append(f"\n_{scaling.get('reasoning')}_")

        if scaling.get('considerations'):
            lines.append("\n*Factors:*")
            for factor in scaling.get('considerations', [])[:3]:
                lines.append(f"  • {factor}")

        return "\n".join(lines)

    def _handle_trade_help(self, args: list) -> str:
        """Handle /tradehelp command."""
        return (
            "*TRADE MANAGEMENT COMMANDS*\n\n"
            "*Position Entry/Exit:*\n"
            "`/buy TICKER SHARES PRICE [reason]`\n"
            "`/sell TICKER SHARES PRICE [reason]`\n"
            "`/close TICKER PRICE` - Close entire position\n\n"
            "*Watchlist:*\n"
            "`/trade TICKER [thesis]` - View/add trade\n"
            "`/watch TICKER [thesis]` - Add to watchlist\n"
            "`/watchlist` - Show watchlist\n\n"
            "*Analysis:*\n"
            "`/positions` or `/pos` - Show open positions\n"
            "`/risk [TICKER]` - Risk assessment\n"
            "`/scan [TICKER]` - Scan for exit signals\n"
            "`/scale TICKER` - Get scaling advice\n\n"
            "*Info:*\n"
            "`/tradehelp` - Show this help"
        )

    def _format_trade_detail(self, trade: Trade) -> str:
        """Format detailed trade info."""
        # Get current price
        try:
            import yfinance as yf
            stock = yf.Ticker(trade.ticker)
            hist = stock.history(period='1d')
            current_price = float(hist['Close'].iloc[-1]) if not hist.empty else trade.average_cost
        except:
            current_price = trade.average_cost

        pnl_pct = ((current_price / trade.average_cost) - 1) * 100 if trade.average_cost > 0 else 0
        pnl_value = (current_price - trade.average_cost) * trade.total_shares

        lines = [
            f"📊 *{trade.ticker}*\n",
            f"Status: {trade.status.value.upper()}",
            f"Shares: {trade.total_shares}",
            f"Avg Cost: ${trade.average_cost:.2f}",
            f"Current: ${current_price:.2f}",
            f"P&L: {pnl_pct:+.1f}% (${pnl_value:+,.0f})\n",
        ]

        if trade.thesis:
            lines.append(f"*Thesis:* {trade.thesis}\n")

        if trade.theme:
            lines.append(f"*Theme:* {trade.theme}")

        lines.append(f"\n*Risk Level:* {trade.current_risk_level.value.upper()}")
        lines.append(f"Days Held: {trade.days_held}")

        # Scaling info
        plan = trade.scaling_plan
        lines.append(f"\n*Scaling:* {plan.strategy.value}")
        lines.append(f"  Scale-ins: {trade.scale_ins_used}/{plan.max_scale_ins}")
        lines.append(f"  Scale-outs: {trade.scale_outs_used}")
        lines.append(f"  Stop: {plan.stop_loss_pct}%")

        return "\n".join(lines)


# Global handler instance
_command_handler: Optional[TradeCommandHandler] = None


def get_command_handler() -> TradeCommandHandler:
    """Get or create global command handler."""
    global _command_handler
    if _command_handler is None:
        _command_handler = TradeCommandHandler()
    return _command_handler


def handle_trade_command(text: str) -> Optional[str]:
    """
    Handle a potential trade command.

    Args:
        text: Command text

    Returns:
        Response message or None if not a trade command
    """
    return get_command_handler().handle_command(text)
