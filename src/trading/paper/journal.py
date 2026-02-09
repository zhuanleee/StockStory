"""
Trade Journal — Persistent storage for paper trading records.
"""

import json
import logging
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class TradeJournal:
    def __init__(self, volume_path: str):
        self.volume_path = volume_path
        self.journal_dir = Path(volume_path) / "paper_trading"
        self.journal_dir.mkdir(parents=True, exist_ok=True)
        self.journal_file = self.journal_dir / "journal.json"
        self.signals_file = self.journal_dir / "signals.json"
        self.equity_file = self.journal_dir / "equity_curve.json"

    def _load_journal(self) -> List[dict]:
        if self.journal_file.exists():
            try:
                return json.loads(self.journal_file.read_text())
            except Exception:
                pass
        return []

    def _save_journal(self, trades: list):
        self.journal_file.write_text(json.dumps(trades, indent=2, default=str))

    def _load_signals(self) -> List[dict]:
        if self.signals_file.exists():
            try:
                return json.loads(self.signals_file.read_text())
            except Exception:
                pass
        return []

    def _save_signals(self, signals: list):
        self.signals_file.write_text(json.dumps(signals, indent=2, default=str))

    def _next_trade_id(self, trades: list) -> str:
        today = date.today().strftime('%Y%m%d')
        today_count = sum(1 for t in trades if t.get('id', '').startswith(f'TRD-{today}'))
        return f'TRD-{today}-{today_count + 1:03d}'

    def _next_signal_id(self, signal_type: str, ticker: str) -> str:
        today = date.today().strftime('%Y%m%d')
        signals = self._load_signals()
        prefix = f'SIG-{today}-{signal_type.upper()}-{ticker.upper()}'
        count = sum(1 for s in signals if s.get('id', '').startswith(prefix))
        return f'{prefix}-{count + 1:03d}'

    def record_trade(self, signal: dict, order_response: dict, config: dict) -> dict:
        """Record a new trade entry from a signal execution."""
        trades = self._load_journal()
        trade_id = self._next_trade_id(trades)

        trade = {
            'id': trade_id,
            'signal_id': signal.get('signal_id', ''),
            'signal_type': signal.get('signal_type', 'manual'),
            'strategy': self._classify_strategy(signal),
            'ticker': signal.get('ticker', '').upper(),
            'direction': signal.get('direction', 'long'),
            'option_type': signal.get('option_type', 'call'),
            'strike': signal.get('strike'),
            'expiration': signal.get('expiration'),
            'quantity': signal.get('quantity', 1),
            'entry_price': signal.get('entry_price', 0),
            'entry_time': datetime.utcnow().isoformat() + 'Z',
            'entry_underlying': signal.get('underlying_price', 0),
            'entry_iv': signal.get('iv', 0),
            'entry_delta': signal.get('delta', 0),
            'stop_loss_pct': config.get('stop_loss_pct', -50),
            'take_profit_pct': config.get('take_profit_pct', 100),
            'status': 'open',
            'exit_price': None,
            'exit_time': None,
            'exit_reason': None,
            'pnl_dollars': None,
            'pnl_pct': None,
            'tt_order_id': order_response.get('order_id'),
            'tags': signal.get('tags', []),
            'notes': signal.get('notes', ''),
        }

        trades.append(trade)
        self._save_journal(trades)
        logger.info(f"Recorded trade {trade_id}: {trade['ticker']} {trade['direction']} {trade['option_type']}")
        return trade

    def close_trade(self, trade_id: str, exit_price: float, exit_reason: str) -> Optional[dict]:
        """Close an open trade with exit details."""
        trades = self._load_journal()
        for trade in trades:
            if trade['id'] == trade_id and trade['status'] == 'open':
                trade['exit_price'] = exit_price
                trade['exit_time'] = datetime.utcnow().isoformat() + 'Z'
                trade['exit_reason'] = exit_reason
                trade['status'] = 'closed'

                # Calculate P&L
                entry = trade['entry_price'] or 0
                qty = trade['quantity'] or 1
                multiplier = 100  # options multiplier

                if trade['direction'] == 'long':
                    pnl = (exit_price - entry) * qty * multiplier
                else:
                    pnl = (entry - exit_price) * qty * multiplier

                trade['pnl_dollars'] = round(pnl, 2)
                trade['pnl_pct'] = round((pnl / (entry * qty * multiplier)) * 100, 2) if entry > 0 else 0

                self._save_journal(trades)
                logger.info(f"Closed trade {trade_id}: {exit_reason}, P&L ${pnl:.2f}")
                return trade
        return None

    def get_open_trades(self) -> List[dict]:
        return [t for t in self._load_journal() if t['status'] == 'open']

    def get_closed_trades(self) -> List[dict]:
        return [t for t in self._load_journal() if t['status'] == 'closed']

    def get_all_trades(self, status: str = None, signal_type: str = None,
                       ticker: str = None, limit: int = 50) -> List[dict]:
        trades = self._load_journal()
        if status:
            trades = [t for t in trades if t['status'] == status]
        if signal_type:
            trades = [t for t in trades if t['signal_type'] == signal_type]
        if ticker:
            trades = [t for t in trades if t['ticker'].upper() == ticker.upper()]
        return trades[-limit:]

    def get_trade_by_symbol(self, symbol: str) -> Optional[dict]:
        """Find open trade matching an OCC option symbol."""
        for t in self._load_journal():
            if t['status'] == 'open' and t.get('occ_symbol') == symbol:
                return t
        return None

    def get_open_trade_for_ticker(self, ticker: str, direction: str = None) -> Optional[dict]:
        for t in self._load_journal():
            if t['status'] != 'open':
                continue
            if t['ticker'].upper() != ticker.upper():
                continue
            if direction and t['direction'] != direction:
                continue
            return t
        return None

    def _classify_strategy(self, signal: dict) -> str:
        """Classify trade into a strategy category for performance tracking."""
        sig_type = signal.get('signal_type', 'manual')
        direction = signal.get('direction', 'long')
        tags = signal.get('tags', [])

        # Strategy mapping
        STRATEGIES = {
            'gex_flip': 'GEX Flip',
            'regime_shift': 'Regime Shift',
            'macro_event': 'Macro Catalyst',
            'iv_reversion': 'IV Reversion',
            'manual': 'Manual',
        }

        base = STRATEGIES.get(sig_type, 'Manual')

        # Sub-categorize
        if sig_type == 'iv_reversion':
            if 'sell_premium' in tags:
                return f'{base} — Credit Spread'
            elif 'buy_premium' in tags:
                return f'{base} — Debit Spread'
        elif sig_type == 'gex_flip':
            if direction == 'long' and signal.get('option_type') == 'put':
                return f'{base} — Bearish'
            elif direction == 'long' and signal.get('option_type') == 'call':
                return f'{base} — Bullish'
        elif sig_type == 'regime_shift':
            regime = ''
            if signal.get('regime_data'):
                regime = signal['regime_data'].get('combined_regime', '')
            if regime in ('opportunity', 'melt_up'):
                return f'{base} — Bullish'
            elif regime in ('danger', 'high_risk'):
                return f'{base} — Bearish'
        elif sig_type == 'macro_event':
            return f'{base} — Vol Expansion'

        return base

    def get_strategies(self) -> List[str]:
        """Get list of all unique strategies used in journal."""
        trades = self._load_journal()
        strategies = set()
        for t in trades:
            s = t.get('strategy')
            if s:
                strategies.add(s)
        return sorted(strategies)

    def get_trades_by_strategy(self, strategy: str) -> List[dict]:
        """Get all trades for a specific strategy."""
        return [t for t in self._load_journal() if t.get('strategy') == strategy]

    def record_signal(self, signal: dict):
        """Record a signal evaluation (whether traded or not)."""
        signals = self._load_signals()
        signal['recorded_at'] = datetime.utcnow().isoformat() + 'Z'
        signals.append(signal)
        # Keep last 500 signals
        if len(signals) > 500:
            signals = signals[-500:]
        self._save_signals(signals)

    def get_signals(self, limit: int = 50, signal_type: str = None) -> List[dict]:
        signals = self._load_signals()
        if signal_type:
            signals = [s for s in signals if s.get('signal_type') == signal_type]
        return signals[-limit:]

    def record_equity_snapshot(self, equity: float, cash: float, positions_value: float):
        """Record daily equity snapshot for equity curve."""
        curve = self._load_equity_curve()
        today = date.today().isoformat()
        # Update today's entry or append
        updated = False
        for entry in curve:
            if entry['date'] == today:
                entry['equity'] = round(equity, 2)
                entry['cash'] = round(cash, 2)
                entry['positions_value'] = round(positions_value, 2)
                updated = True
                break
        if not updated:
            curve.append({
                'date': today,
                'equity': round(equity, 2),
                'cash': round(cash, 2),
                'positions_value': round(positions_value, 2),
            })
        self.equity_file.write_text(json.dumps(curve, indent=2))

    def _load_equity_curve(self) -> List[dict]:
        if self.equity_file.exists():
            try:
                return json.loads(self.equity_file.read_text())
            except Exception:
                pass
        return []

    def get_equity_curve(self) -> List[dict]:
        return self._load_equity_curve()

    def reset(self, starting_capital: float = 50000):
        """Reset all paper trading data."""
        self._save_journal([])
        self._save_signals([])
        self.equity_file.write_text(json.dumps([{
            'date': date.today().isoformat(),
            'equity': starting_capital,
            'cash': starting_capital,
            'positions_value': 0,
        }], indent=2))
        logger.info(f"Paper trading reset to ${starting_capital}")
