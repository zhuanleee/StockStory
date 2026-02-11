"""
Performance Analytics — Compute trading metrics from journal data.
"""

import math
import re
import logging
from typing import Dict, List
from collections import defaultdict

logger = logging.getLogger(__name__)


class PerformanceAnalytics:
    def __init__(self, journal):
        self.journal = journal

    def compute(self) -> Dict:
        """Compute all performance metrics."""
        closed = self.journal.get_closed_trades()
        open_trades = self.journal.get_open_trades()
        equity_curve = self.journal.get_equity_curve()

        if not closed:
            return {
                'total_trades': 0,
                'open_trades': len(open_trades),
                'win_rate': 0,
                'profit_factor': 0,
                'sharpe_ratio': 0,
                'max_drawdown_pct': 0,
                'current_drawdown_pct': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'expectancy': 0,
                'total_pnl': 0,
                'daily_pnl': 0,
                'best_trade': None,
                'worst_trade': None,
                'avg_holding_days': 0,
                'signal_attribution': {},
                'strategy_breakdown': {},
            }

        winners = [t for t in closed if (t.get('pnl_dollars') or 0) > 0]
        losers = [t for t in closed if (t.get('pnl_dollars') or 0) < 0]
        breakeven = [t for t in closed if (t.get('pnl_dollars') or 0) == 0]

        total = len(closed)
        win_count = len(winners)
        loss_count = len(losers)

        win_rate = (win_count / total * 100) if total > 0 else 0

        gross_profit = sum(t['pnl_dollars'] for t in winners)
        gross_loss = abs(sum(t['pnl_dollars'] for t in losers))
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float('inf') if gross_profit > 0 else 0

        avg_win = (gross_profit / win_count) if win_count > 0 else 0
        avg_loss = (-gross_loss / loss_count) if loss_count > 0 else 0

        total_pnl = sum(t.get('pnl_dollars', 0) or 0 for t in closed)
        expectancy = (win_rate / 100 * avg_win) + ((1 - win_rate / 100) * avg_loss)

        # Sharpe ratio (annualized, using daily returns from equity curve)
        sharpe = self._compute_sharpe(equity_curve)

        # Drawdown
        max_dd, current_dd = self._compute_drawdown(equity_curve)

        # Daily P&L (from today's closed trades)
        from datetime import date as _date
        today_str = _date.today().isoformat()
        daily_pnl = sum(
            (t.get('pnl_dollars', 0) or 0) for t in closed
            if t.get('exit_time', '').startswith(today_str)
        )

        # Best / worst trades
        best = max(closed, key=lambda t: t.get('pnl_dollars', 0) or 0)
        worst = min(closed, key=lambda t: t.get('pnl_dollars', 0) or 0)

        # Avg holding time
        avg_holding = self._avg_holding_days(closed)

        # Signal attribution
        attribution = self._signal_attribution(closed)

        # Strategy breakdown (per-strategy performance)
        strategy_breakdown = self._strategy_breakdown(closed)

        return {
            'total_trades': total,
            'open_trades': len(open_trades),
            'winners': win_count,
            'losers': loss_count,
            'breakeven': len(breakeven),
            'win_rate': round(win_rate, 1),
            'profit_factor': round(profit_factor, 2) if profit_factor != float('inf') else 999,
            'sharpe_ratio': round(sharpe, 2),
            'max_drawdown_pct': round(max_dd, 2),
            'current_drawdown_pct': round(current_dd, 2),
            'avg_win': round(avg_win, 2),
            'avg_loss': round(avg_loss, 2),
            'expectancy': round(expectancy, 2),
            'total_pnl': round(total_pnl, 2),
            'daily_pnl': round(daily_pnl, 2),
            'gross_profit': round(gross_profit, 2),
            'gross_loss': round(-gross_loss, 2),
            'best_trade': {'id': best['id'], 'ticker': best['ticker'], 'pnl': best.get('pnl_dollars', 0)},
            'worst_trade': {'id': worst['id'], 'ticker': worst['ticker'], 'pnl': worst.get('pnl_dollars', 0)},
            'avg_holding_days': round(avg_holding, 1),
            'signal_attribution': attribution,
            'strategy_breakdown': strategy_breakdown,
        }

    def _compute_sharpe(self, equity_curve: List[dict], risk_free_rate: float = 0.05) -> float:
        if len(equity_curve) < 3:
            return 0
        equities = [e['equity'] for e in equity_curve]
        returns = []
        for i in range(1, len(equities)):
            if equities[i - 1] > 0:
                returns.append((equities[i] - equities[i - 1]) / equities[i - 1])
        if not returns or len(returns) < 2:
            return 0
        mean_ret = sum(returns) / len(returns)
        std_ret = math.sqrt(sum((r - mean_ret) ** 2 for r in returns) / (len(returns) - 1))
        if std_ret == 0:
            return 0
        daily_rf = risk_free_rate / 252
        sharpe = (mean_ret - daily_rf) / std_ret * math.sqrt(252)
        return sharpe

    def _compute_drawdown(self, equity_curve: List[dict]) -> tuple:
        if not equity_curve:
            return 0, 0
        equities = [e['equity'] for e in equity_curve]
        peak = equities[0]
        max_dd = 0
        for eq in equities:
            if eq > peak:
                peak = eq
            dd = ((peak - eq) / peak) * 100 if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd
        # Current drawdown
        current_peak = max(equities)
        current_dd = ((current_peak - equities[-1]) / current_peak) * 100 if current_peak > 0 else 0
        return max_dd, current_dd

    def _avg_holding_days(self, closed: List[dict]) -> float:
        from datetime import datetime
        days_list = []
        for t in closed:
            entry = t.get('entry_time')
            exit_t = t.get('exit_time')
            if entry and exit_t:
                try:
                    e = datetime.fromisoformat(entry.replace('Z', '+00:00'))
                    x = datetime.fromisoformat(exit_t.replace('Z', '+00:00'))
                    days_list.append((x - e).total_seconds() / 86400)
                except Exception:
                    pass
        return (sum(days_list) / len(days_list)) if days_list else 0

    @staticmethod
    def _normalize_strategy_name(name: str) -> str:
        """Strip strike/expiry info to group by strategy type.
        'Credit Spread (PUT 295.0/290.0)' → 'Credit Spread'
        'Iron Condor (CALL 300/305 PUT 280/275)' → 'Iron Condor'
        """
        return re.sub(r'\s*\(.*\)\s*$', '', name).strip() or name

    def _strategy_breakdown(self, closed: List[dict]) -> Dict:
        """Per-strategy performance breakdown."""
        by_strategy = defaultdict(list)
        for t in closed:
            strat = self._normalize_strategy_name(t.get('strategy', 'Manual'))
            by_strategy[strat].append(t)

        result = {}
        for strat, trades in by_strategy.items():
            winners = [t for t in trades if (t.get('pnl_dollars') or 0) > 0]
            losers = [t for t in trades if (t.get('pnl_dollars') or 0) < 0]
            total_pnl = sum(t.get('pnl_dollars', 0) or 0 for t in trades)
            win_rate = (len(winners) / len(trades) * 100) if trades else 0
            avg_pnl = (total_pnl / len(trades)) if trades else 0
            gross_p = sum(t['pnl_dollars'] for t in winners) if winners else 0
            gross_l = abs(sum(t['pnl_dollars'] for t in losers)) if losers else 0
            pf = (gross_p / gross_l) if gross_l > 0 else (999 if gross_p > 0 else 0)
            avg_win = (gross_p / len(winners)) if winners else 0
            avg_loss = (-gross_l / len(losers)) if losers else 0

            result[strat] = {
                'count': len(trades),
                'winners': len(winners),
                'losers': len(losers),
                'win_rate': round(win_rate, 1),
                'total_pnl': round(total_pnl, 2),
                'avg_pnl': round(avg_pnl, 2),
                'avg_win': round(avg_win, 2),
                'avg_loss': round(avg_loss, 2),
                'profit_factor': round(pf, 2) if pf != float('inf') else 999,
                'expectancy': round((win_rate / 100 * avg_win) + ((1 - win_rate / 100) * avg_loss), 2),
            }
        return result

    def _signal_attribution(self, closed: List[dict]) -> Dict:
        by_type = defaultdict(list)
        for t in closed:
            sig_type = t.get('signal_type', 'unknown')
            by_type[sig_type].append(t)

        result = {}
        for sig_type, trades in by_type.items():
            winners = [t for t in trades if (t.get('pnl_dollars') or 0) > 0]
            total_pnl = sum(t.get('pnl_dollars', 0) or 0 for t in trades)
            win_rate = (len(winners) / len(trades) * 100) if trades else 0
            avg_pnl = (total_pnl / len(trades)) if trades else 0
            result[sig_type] = {
                'count': len(trades),
                'win_rate': round(win_rate, 1),
                'total_pnl': round(total_pnl, 2),
                'avg_pnl': round(avg_pnl, 2),
            }
        return result
