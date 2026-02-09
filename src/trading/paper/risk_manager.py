"""
Risk Manager — Pre-trade checks and position sizing for paper trading.
"""

import json
import logging
from datetime import datetime, date
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    "starting_capital": 50000,
    "auto_trade_enabled": False,
    "multi_leg_enabled": False,
    "watched_tickers": ["SPY", "QQQ", "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "IBIT", "GLD"],
    "min_confidence": 60,
    "max_positions": 5,
    "max_position_pct": 5,
    "max_exposure_pct": 30,
    "max_daily_trades": 10,
    "max_daily_loss_pct": 5,
    "default_dte_range": [30, 45],
    "stop_loss_pct": -50,
    "take_profit_pct": 100,
    "min_dte_to_open": 14,
    "time_exit_dte": 7,
    "signal_check_interval_min": 5,
    "max_same_sector": 3,
}


def load_config(volume_path: str) -> dict:
    config_path = Path(volume_path) / "paper_trading" / "config.json"
    if config_path.exists():
        try:
            return json.loads(config_path.read_text())
        except Exception:
            pass
    return dict(DEFAULT_CONFIG)


def save_config(volume_path: str, config: dict):
    config_dir = Path(volume_path) / "paper_trading"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "config.json").write_text(json.dumps(config, indent=2))


class RiskManager:
    def __init__(self, volume_path: str):
        self.volume_path = volume_path
        self.config = load_config(volume_path)

    def reload(self):
        self.config = load_config(self.volume_path)

    def check_all(self, signal: dict, open_trades: list, equity: float) -> Dict:
        """Run all pre-trade risk checks. Returns {'passed': bool, 'reason': str}."""
        checks = [
            self._check_max_positions(open_trades),
            self._check_max_exposure(open_trades, equity),
            self._check_max_position_size(signal, equity),
            self._check_daily_trades(open_trades),
            self._check_daily_loss(open_trades, equity),
            self._check_duplicate(signal, open_trades),
            self._check_min_dte(signal),
            self._check_sector_concentration(signal, open_trades),
        ]
        for check in checks:
            if not check['passed']:
                return check
        return {'passed': True, 'reason': 'All checks passed'}

    def _check_max_positions(self, open_trades: list, extra: int = 0) -> Dict:
        limit = self.config.get('max_positions', 5) + extra
        count = len(open_trades)
        if count >= limit:
            return {'passed': False, 'reason': f'Max positions reached ({count}/{limit})'}
        return {'passed': True, 'reason': f'Positions OK ({count}/{limit})'}

    def _check_max_exposure(self, open_trades: list, equity: float) -> Dict:
        limit_pct = self.config.get('max_exposure_pct', 30)
        if equity <= 0:
            return {'passed': False, 'reason': 'Invalid equity'}
        total_cost = sum(
            abs(t.get('entry_price', 0)) * t.get('quantity', 0) * 100
            for t in open_trades
        )
        exposure_pct = (total_cost / equity) * 100
        if exposure_pct >= limit_pct:
            return {'passed': False, 'reason': f'Max exposure reached ({exposure_pct:.1f}%/{limit_pct}%)'}
        return {'passed': True, 'reason': f'Exposure OK ({exposure_pct:.1f}%/{limit_pct}%)'}

    def _check_max_position_size(self, signal: dict, equity: float) -> Dict:
        limit_pct = self.config.get('max_position_pct', 5)
        if equity <= 0:
            return {'passed': False, 'reason': 'Invalid equity'}
        cost = abs(signal.get('estimated_cost', 0))
        if cost <= 0:
            return {'passed': True, 'reason': 'No cost estimate'}
        size_pct = (cost / equity) * 100
        if size_pct > limit_pct:
            return {'passed': False, 'reason': f'Position too large ({size_pct:.1f}%/{limit_pct}%)'}
        return {'passed': True, 'reason': f'Size OK ({size_pct:.1f}%/{limit_pct}%)'}

    def _check_daily_trades(self, open_trades: list) -> Dict:
        limit = self.config.get('max_daily_trades', 10)
        today = date.today().isoformat()
        count = sum(1 for t in open_trades if t.get('entry_time', '').startswith(today))
        if count >= limit:
            return {'passed': False, 'reason': f'Max daily trades reached ({count}/{limit})'}
        return {'passed': True, 'reason': f'Daily trades OK ({count}/{limit})'}

    def _check_daily_loss(self, open_trades: list, equity: float) -> Dict:
        limit_pct = self.config.get('max_daily_loss_pct', 5)
        if equity <= 0:
            return {'passed': False, 'reason': 'Invalid equity'}
        today = date.today().isoformat()
        # Realized P&L: trades closed today
        realized_pnl = sum(
            t.get('pnl_dollars', 0) or 0
            for t in open_trades
            if t.get('exit_time', '') and t['exit_time'].startswith(today) and t.get('status') == 'closed'
        )
        # Unrealized P&L: open positions opened today
        unrealized_pnl = sum(
            t.get('unrealized_pnl', 0) or 0
            for t in open_trades
            if t.get('status') == 'open' and t.get('entry_time', '').startswith(today)
        )
        daily_pnl = realized_pnl + unrealized_pnl
        loss_pct = abs(daily_pnl / equity) * 100 if daily_pnl < 0 else 0
        if loss_pct >= limit_pct:
            return {'passed': False, 'reason': f'Daily loss limit hit (-{loss_pct:.1f}%/-{limit_pct}%)'}
        return {'passed': True, 'reason': f'Daily P&L OK (realized: ${realized_pnl:.0f}, unrealized: ${unrealized_pnl:.0f})'}

    def _check_duplicate(self, signal: dict, open_trades: list) -> Dict:
        ticker = signal.get('ticker', '').upper()
        direction = signal.get('direction', '')
        for t in open_trades:
            if t.get('status') == 'open' and t.get('ticker', '').upper() == ticker and t.get('direction') == direction:
                return {'passed': False, 'reason': f'Duplicate position: {ticker} {direction} already open'}
        return {'passed': True, 'reason': 'No duplicate'}

    def _check_min_dte(self, signal: dict) -> Dict:
        min_dte = self.config.get('min_dte_to_open', 14)
        expiration = signal.get('expiration')
        if not expiration:
            return {'passed': True, 'reason': 'No expiration to check'}
        try:
            exp_date = datetime.strptime(expiration, '%Y-%m-%d').date()
            dte = (exp_date - date.today()).days
            if dte < min_dte:
                return {'passed': False, 'reason': f'DTE too low ({dte} < {min_dte})'}
            return {'passed': True, 'reason': f'DTE OK ({dte})'}
        except ValueError:
            return {'passed': True, 'reason': 'Could not parse expiration'}

    def _check_sector_concentration(self, signal: dict, open_trades: list) -> Dict:
        max_same = self.config.get('max_same_sector', 3)
        ticker = signal.get('ticker', '').upper()
        # Simple sector grouping by ticker similarity
        SECTOR_MAP = {
            'SPY': 'index', 'QQQ': 'index', 'IWM': 'index', 'DIA': 'index',
            'NVDA': 'tech', 'AMD': 'tech', 'INTC': 'tech', 'AVGO': 'tech', 'MU': 'tech',
            'AAPL': 'tech', 'MSFT': 'tech', 'GOOGL': 'tech', 'GOOG': 'tech', 'META': 'tech', 'AMZN': 'tech',
            'TSLA': 'auto', 'F': 'auto', 'GM': 'auto', 'RIVN': 'auto',
            '/ES': 'futures', '/NQ': 'futures', '/CL': 'energy', '/GC': 'metals',
        }
        sector = SECTOR_MAP.get(ticker, 'other')
        count = sum(1 for t in open_trades
                    if t.get('status') == 'open' and SECTOR_MAP.get(t.get('ticker', '').upper(), 'other') == sector)
        if count >= max_same:
            return {'passed': False, 'reason': f'Max {sector} sector positions ({count}/{max_same})'}
        return {'passed': True, 'reason': f'Sector OK ({sector}: {count}/{max_same})'}

    def compute_position_size(self, signal: dict, equity: float, max_loss: float = None) -> int:
        """Compute number of contracts based on risk limits.

        Args:
            max_loss: For defined-risk spreads, the max loss per contract.
                      When provided, uses this instead of premium * 100 for sizing.
        """
        max_pct = self.config.get('max_position_pct', 5)
        max_cost = equity * (max_pct / 100)

        if max_loss and max_loss > 0:
            # Defined-risk: size by max loss per contract
            risk_per_contract = max_loss
        else:
            premium = signal.get('estimated_premium', 5.0)
            if premium <= 0:
                premium = 5.0
            risk_per_contract = premium * 100

        max_contracts = int(max_cost / risk_per_contract)
        return max(1, min(max_contracts, 10))

    def check_all_multi_leg(self, signal: dict, open_trades: list, equity: float) -> Dict:
        """Risk checks for multi-leg trades. Defined-risk trades get +2 position allowance."""
        # Run standard checks but with relaxed position limit
        max_loss = signal.get('max_loss', 0)
        is_defined_risk = max_loss > 0 and max_loss < 999999

        checks = [
            self._check_max_positions(open_trades, extra=2 if is_defined_risk else 0),
            self._check_max_exposure(open_trades, equity),
            self._check_daily_trades(open_trades),
            self._check_daily_loss(open_trades, equity),
            self._check_duplicate(signal, open_trades),
            self._check_min_dte(signal),
            self._check_sector_concentration(signal, open_trades),
        ]

        # For defined-risk, check max_loss against position size limit instead of premium
        if is_defined_risk:
            max_pct = self.config.get('max_position_pct', 5)
            size_pct = (max_loss / equity) * 100 if equity > 0 else 999
            if size_pct > max_pct:
                checks.append({'passed': False, 'reason': f'Multi-leg max loss too large ({size_pct:.1f}%/{max_pct}%)'})

        for check in checks:
            if not check['passed']:
                return check
        return {'passed': True, 'reason': 'All checks passed'}
