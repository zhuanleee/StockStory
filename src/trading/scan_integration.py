"""
Scan Integration - Connect Trade Management with Scanner

Integrates the trade management system with the stock scanner
to automatically scan positions and generate exit signals.
"""

import logging
from datetime import datetime
from typing import List, Dict, Optional, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

from .models import Trade
from .trade_manager import get_trade_manager
from .exit_scanner import get_exit_scanner
from .risk_advisor import get_risk_advisor
from .scaling_engine import get_scaling_engine

logger = logging.getLogger(__name__)


class TradeScanIntegration:
    """
    Integrates trade management with the stock scanner.

    Automatically scans all watched/open positions and generates
    exit signals based on Story → AI → Technical priority.
    """

    def __init__(self):
        self.trade_manager = get_trade_manager()
        self.exit_scanner = get_exit_scanner()
        self.risk_advisor = get_risk_advisor()
        self.scaling_engine = get_scaling_engine()

    def scan_all_positions(
        self,
        include_watchlist: bool = True,
    ) -> Dict[str, Any]:
        """
        Scan all positions for exit signals.

        Args:
            include_watchlist: Also scan watchlist items

        Returns:
            Dict with:
            - scanned: Number of positions scanned
            - alerts: List of alert messages
            - risk_summary: Portfolio risk summary
            - positions: Individual position details
        """
        results = {
            'scanned': 0,
            'alerts': [],
            'positions': [],
            'errors': [],
            'scan_time': datetime.now().isoformat(),
        }

        # Get trades to scan
        trades_to_scan = self.trade_manager.get_open_trades()
        if include_watchlist:
            trades_to_scan.extend(self.trade_manager.get_watchlist())

        if not trades_to_scan:
            return results

        tickers = [t.ticker for t in trades_to_scan]
        results['scanned'] = len(tickers)

        # Fetch data for all tickers
        try:
            ticker_data = self._fetch_all_ticker_data(tickers)
        except Exception as e:
            logger.error(f"Error fetching ticker data: {e}")
            results['errors'].append(str(e))
            return results

        # Scan each trade
        trade_signals = {}
        current_prices = {}

        for trade in trades_to_scan:
            try:
                data = ticker_data.get(trade.ticker, {})
                current_prices[trade.ticker] = data.get('current_price', 0)

                # Generate exit signals
                signals = self.exit_scanner.scan_trade(
                    trade=trade,
                    story_data=data.get('story_data'),
                    ai_analysis=data.get('ai_analysis'),
                    technical_data=data.get('technical_data'),
                    current_price=data.get('current_price'),
                )

                trade_signals[trade.ticker] = signals

                # Store signals on trade
                for signal in signals:
                    trade.add_exit_signal(signal)

                # Get assessment
                assessment = self.exit_scanner.get_composite_assessment(signals)

                # Update trade scores
                if data.get('story_data'):
                    trade.latest_story_score = data['story_data'].get('score')
                if data.get('ai_analysis'):
                    trade.latest_ai_confidence = data['ai_analysis'].get('confidence')
                if data.get('technical_data'):
                    trade.latest_technical_score = data['technical_data'].get('rs_rating')

                trade.latest_composite_score = 100 - assessment['composite_confidence']

                # Save updated trade
                self.trade_manager.update_trade(trade)

                # Check scaling opportunities
                scale_in_opp = self.scaling_engine.check_scale_in_opportunity(
                    trade=trade,
                    story_data=data.get('story_data'),
                    technical_data=data.get('technical_data'),
                    current_price=data.get('current_price'),
                )

                scale_out_opp = self.scaling_engine.check_scale_out_opportunity(
                    trade=trade,
                    exit_signals=signals,
                    current_price=data.get('current_price'),
                )

                # Add to results
                position_result = {
                    'ticker': trade.ticker,
                    'status': trade.status.value,
                    'shares': trade.total_shares,
                    'avg_cost': trade.average_cost,
                    'current_price': data.get('current_price'),
                    'pnl_pct': self._calculate_pnl(trade, data.get('current_price')),
                    'risk_level': assessment['risk_level'].value,
                    'exit_confidence': assessment['composite_confidence'],
                    'signals_count': len(signals),
                    'recommended_action': assessment['recommended_action'],
                    # Scaling info
                    'scale_in': {
                        'should_scale': scale_in_opp.get('should_scale', False),
                        'trigger': scale_in_opp.get('trigger'),
                        'size_pct': scale_in_opp.get('suggested_size', 0),
                        'reasoning': scale_in_opp.get('reasoning', ''),
                    },
                    'scale_out': {
                        'should_scale': scale_out_opp.get('should_scale', False),
                        'trigger': scale_out_opp.get('trigger'),
                        'size_pct': scale_out_opp.get('suggested_size', 0),
                        'reasoning': scale_out_opp.get('reasoning', ''),
                        'source': scale_out_opp.get('source', ''),
                    },
                }
                results['positions'].append(position_result)

                # Generate scaling alert if opportunity detected
                if scale_in_opp.get('should_scale') and scale_in_opp.get('confidence', 0) >= 70:
                    results['alerts'].append({
                        'ticker': trade.ticker,
                        'risk_level': 'scale_in',
                        'message': self._format_scale_alert(trade, 'in', scale_in_opp, data.get('current_price')),
                    })

                if scale_out_opp.get('should_scale') and scale_out_opp.get('source') == 'story':
                    # Story-based scale-out is high priority
                    results['alerts'].append({
                        'ticker': trade.ticker,
                        'risk_level': 'scale_out',
                        'message': self._format_scale_alert(trade, 'out', scale_out_opp, data.get('current_price')),
                    })

                # Generate alert if needed
                if assessment['risk_level'].value in ['critical', 'high', 'elevated']:
                    alert = self.exit_scanner.format_alert(trade, assessment)
                    results['alerts'].append({
                        'ticker': trade.ticker,
                        'risk_level': assessment['risk_level'].value,
                        'message': alert,
                    })

            except Exception as e:
                logger.error(f"Error scanning {trade.ticker}: {e}")
                results['errors'].append(f"{trade.ticker}: {str(e)}")

        # Calculate portfolio risk
        try:
            portfolio_value = self._estimate_portfolio_value(trades_to_scan, current_prices)
            risk_summary = self.risk_advisor.assess_portfolio_risk(
                trades=trades_to_scan,
                trade_signals=trade_signals,
                current_prices=current_prices,
                portfolio_value=portfolio_value,
            )
            results['risk_summary'] = {
                'overall_risk': risk_summary['overall_risk'].value,
                'risk_score': risk_summary['risk_score'],
                'high_risk_count': risk_summary['high_risk_count'],
            }
        except Exception as e:
            logger.error(f"Error calculating portfolio risk: {e}")
            results['errors'].append(f"Portfolio risk: {str(e)}")

        return results

    def scan_single_position(
        self,
        ticker: str,
    ) -> Dict[str, Any]:
        """
        Scan a single position.

        Args:
            ticker: Ticker symbol

        Returns:
            Full scan result for the position
        """
        trade = self.trade_manager.get_trade_by_ticker(ticker)
        if not trade:
            return {'error': f"No active trade found for {ticker}"}

        # Fetch data
        data = self._fetch_ticker_data(ticker)

        # Generate signals
        signals = self.exit_scanner.scan_trade(
            trade=trade,
            story_data=data.get('story_data'),
            ai_analysis=data.get('ai_analysis'),
            technical_data=data.get('technical_data'),
            current_price=data.get('current_price'),
        )

        # Get assessment
        assessment = self.exit_scanner.get_composite_assessment(signals)

        # Get risk assessment
        risk = self.risk_advisor.assess_trade_risk(
            trade=trade,
            exit_signals=signals,
            current_price=data.get('current_price'),
        )

        # Get scaling advice
        scaling = self.scaling_engine.get_ai_scaling_advice(
            trade=trade,
            story_data=data.get('story_data'),
            technical_data=data.get('technical_data'),
            current_price=data.get('current_price'),
        )

        return {
            'ticker': ticker,
            'trade': trade.to_dict(),
            'current_price': data.get('current_price'),
            'pnl_pct': self._calculate_pnl(trade, data.get('current_price')),
            'signals': [s.to_dict() for s in signals],
            'assessment': {
                'composite_confidence': assessment['composite_confidence'],
                'risk_level': assessment['risk_level'].value,
                'recommended_action': assessment['recommended_action'],
                'action_size': assessment['action_size'],
            },
            'risk': risk,
            'scaling_advice': scaling,
        }

    def _fetch_all_ticker_data(
        self,
        tickers: List[str],
    ) -> Dict[str, Dict[str, Any]]:
        """Fetch data for all tickers in parallel."""
        results = {}

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {
                executor.submit(self._fetch_ticker_data, ticker): ticker
                for ticker in tickers
            }

            for future in as_completed(futures):
                ticker = futures[future]
                try:
                    results[ticker] = future.result()
                except Exception as e:
                    logger.error(f"Error fetching {ticker}: {e}")
                    results[ticker] = {}

        return results

    def _fetch_ticker_data(self, ticker: str) -> Dict[str, Any]:
        """Fetch all data needed for a ticker."""
        data = {}

        try:
            import yfinance as yf

            # Get price data
            stock = yf.Ticker(ticker)
            hist = stock.history(period='3mo')

            if not hist.empty:
                data['current_price'] = float(hist['Close'].iloc[-1])

                # Technical data
                data['technical_data'] = {
                    'ma20': float(hist['Close'].tail(20).mean()) if len(hist) >= 20 else 0,
                    'ma50': float(hist['Close'].tail(50).mean()) if len(hist) >= 50 else 0,
                    'high_since_entry': float(hist['High'].max()),
                    'support': float(hist['Low'].tail(10).min()),
                    'avg_volume': float(hist['Volume'].mean()),
                    'current_volume': float(hist['Volume'].iloc[-1]),
                    'volume_ratio': float(hist['Volume'].iloc[-1] / hist['Volume'].mean()) if hist['Volume'].mean() > 0 else 1.0,
                }

                # Calculate RS rating (simplified)
                spy = yf.Ticker('SPY')
                spy_hist = spy.history(period='3mo')
                if not spy_hist.empty and len(hist) >= 20:
                    stock_return = (hist['Close'].iloc[-1] / hist['Close'].iloc[-20] - 1) * 100
                    spy_return = (spy_hist['Close'].iloc[-1] / spy_hist['Close'].iloc[-20] - 1) * 100
                    data['technical_data']['rs_rating'] = 50 + (stock_return - spy_return)

        except Exception as e:
            logger.error(f"Error fetching price data for {ticker}: {e}")

        # Get story data (from story scorer if available)
        try:
            from story_scorer import calculate_story_score
            story_result = calculate_story_score(ticker, None)
            if story_result:
                data['story_data'] = {
                    'score': story_result.get('score', 50),
                    'theme_stage': story_result.get('theme_stage', 'growth'),
                    'theme_momentum': story_result.get('theme_momentum', 0),
                    'catalyst_status': story_result.get('catalyst_status', 'pending'),
                    'thesis_score': story_result.get('thesis_score', 70),
                    'news_sentiment': story_result.get('news_sentiment', 0),
                }
        except ImportError:
            # Story scorer not available, use defaults
            data['story_data'] = {
                'score': 50,
                'theme_stage': 'growth',
                'theme_momentum': 0,
                'catalyst_status': 'pending',
                'thesis_score': 70,
            }
        except Exception as e:
            logger.error(f"Error getting story data for {ticker}: {e}")

        # Get AI analysis
        try:
            from src.ai.ai_learning import call_ai

            prompt = f"""Analyze {ticker} as an investment. Provide JSON:
{{
    "sentiment": "bullish" | "bearish" | "neutral",
    "confidence": 0-100,
    "recommendation": "buy" | "hold" | "sell",
    "thesis_valid": true/false,
    "risk_score": 0-100,
    "key_factors": ["factor1", "factor2"]
}}"""

            response = call_ai(prompt, max_tokens=200, task_type="simple")
            if response:
                import json
                import re
                json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', response, re.DOTALL)
                if json_match:
                    response = json_match.group(1)
                data['ai_analysis'] = json.loads(response)
        except Exception as e:
            logger.debug(f"AI analysis failed for {ticker}: {e}")
            data['ai_analysis'] = {
                'sentiment': 'neutral',
                'confidence': 50,
                'recommendation': 'hold',
            }

        return data

    def _calculate_pnl(self, trade: Trade, current_price: float) -> float:
        """Calculate P&L percentage."""
        if not current_price or trade.average_cost <= 0:
            return 0.0
        return ((current_price - trade.average_cost) / trade.average_cost) * 100

    def _estimate_portfolio_value(
        self,
        trades: List[Trade],
        current_prices: Dict[str, float],
    ) -> float:
        """Estimate total portfolio value from positions."""
        total = 0.0
        for trade in trades:
            price = current_prices.get(trade.ticker, trade.average_cost)
            total += trade.total_shares * price
        return total if total > 0 else 100000  # Default if no data

    def _format_scale_alert(
        self,
        trade: Trade,
        direction: str,
        opportunity: Dict[str, Any],
        current_price: float,
    ) -> str:
        """Format scaling opportunity as alert message."""
        if direction == 'in':
            emoji = "📈"
            action = "SCALE IN"
        else:
            emoji = "📉"
            action = "SCALE OUT"

        lines = [
            f"{emoji} **{action} OPPORTUNITY: {trade.ticker}**",
            f"Trigger: {opportunity.get('trigger', 'N/A')}",
            f"Confidence: {opportunity.get('confidence', 0):.0f}%",
            f"Suggested Size: {opportunity.get('suggested_size', 0):.0f}%",
        ]

        if opportunity.get('reasoning'):
            lines.append(f"\n_{opportunity['reasoning']}_")

        if current_price:
            lines.append(f"\nCurrent Price: ${current_price:.2f}")

        lines.append(f"Position: {trade.total_shares} shares @ ${trade.average_cost:.2f}")

        if direction == 'out' and opportunity.get('source'):
            lines.append(f"Source: {opportunity['source'].upper()}")

        return "\n".join(lines)

    # Scheduled Scanning

    def get_scan_schedule(self) -> Dict[str, Any]:
        """Get recommended scan schedule based on positions."""
        open_trades = self.trade_manager.get_open_trades()
        watchlist = self.trade_manager.get_watchlist()

        # More positions = more frequent scans needed
        total_positions = len(open_trades) + len(watchlist)

        if total_positions == 0:
            return {'frequency': 'none', 'reason': 'No positions to scan'}
        elif total_positions <= 5:
            return {'frequency': 'daily', 'reason': 'Small portfolio'}
        elif total_positions <= 15:
            return {'frequency': 'twice_daily', 'reason': 'Medium portfolio'}
        else:
            return {'frequency': 'every_4_hours', 'reason': 'Large portfolio'}

    def generate_daily_report(self) -> str:
        """Generate daily position report."""
        results = self.scan_all_positions()

        lines = [
            "📊 **DAILY POSITION REPORT**",
            f"Scanned: {results['scanned']} positions",
            f"Time: {results['scan_time']}",
            "",
        ]

        # Risk summary
        if results.get('risk_summary'):
            rs = results['risk_summary']
            lines.append(f"**Portfolio Risk:** {rs['overall_risk'].upper()} ({rs['risk_score']:.0f}/100)")
            lines.append(f"High-Risk Positions: {rs['high_risk_count']}")
            lines.append("")

        # Position summary
        if results['positions']:
            lines.append("**Positions:**")
            for pos in sorted(results['positions'], key=lambda x: -x.get('exit_confidence', 0)):
                emoji = "🔴" if pos['risk_level'] in ['critical', 'high'] else "🟢"
                pnl = pos.get('pnl_pct', 0)
                pnl_str = f"+{pnl:.1f}%" if pnl >= 0 else f"{pnl:.1f}%"
                lines.append(f"  {emoji} {pos['ticker']}: {pnl_str} | {pos['risk_level'].upper()}")

        # Scaling Opportunities
        scale_ins = [p for p in results['positions'] if p.get('scale_in', {}).get('should_scale')]
        scale_outs = [p for p in results['positions'] if p.get('scale_out', {}).get('should_scale')]

        if scale_ins:
            lines.append("")
            lines.append("**📈 Scale-In Opportunities:**")
            for pos in scale_ins:
                si = pos['scale_in']
                lines.append(f"  • {pos['ticker']}: {si['trigger']} ({si['size_pct']:.0f}%)")

        if scale_outs:
            lines.append("")
            lines.append("**📉 Scale-Out Signals:**")
            for pos in scale_outs:
                so = pos['scale_out']
                source = f" [{so['source']}]" if so.get('source') else ""
                lines.append(f"  • {pos['ticker']}: {so['trigger']}{source} ({so['size_pct']:.0f}%)")

        # Alerts
        if results['alerts']:
            lines.append("")
            lines.append("**⚠️ Alerts:**")
            for alert in results['alerts']:
                lines.append(f"  • {alert['ticker']}: {alert['risk_level'].upper()}")

        return "\n".join(lines)


# Global instance
_integration: Optional[TradeScanIntegration] = None


def get_scan_integration() -> TradeScanIntegration:
    """Get or create global scan integration instance."""
    global _integration
    if _integration is None:
        _integration = TradeScanIntegration()
    return _integration


# Convenience functions

def scan_positions() -> Dict[str, Any]:
    """Scan all positions and return results."""
    return get_scan_integration().scan_all_positions()


def scan_ticker(ticker: str) -> Dict[str, Any]:
    """Scan a single ticker."""
    return get_scan_integration().scan_single_position(ticker)


def get_daily_report() -> str:
    """Generate daily position report."""
    return get_scan_integration().generate_daily_report()
