"""
Trade Manager - CRUD operations and persistence for trades.

Handles:
- Trade creation, updates, and deletion
- JSON file persistence
- Trade queries and filtering
- Position summary calculations
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any

from .models import Trade, Tranche, TradeStatus, ScalingPlan, ScalingStrategy

logger = logging.getLogger(__name__)

# Storage configuration
TRADES_DIR = Path('user_data/trades')
TRADES_DIR.mkdir(parents=True, exist_ok=True)


class TradeManager:
    """
    Manages trade lifecycle and persistence.
    """

    def __init__(self, storage_dir: Path = TRADES_DIR):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._trades_cache: Dict[str, Trade] = {}
        self._load_all_trades()

    def _get_trade_file(self, trade_id: str) -> Path:
        """Get file path for a trade."""
        return self.storage_dir / f"trade_{trade_id}.json"

    def _load_all_trades(self) -> None:
        """Load all trades from storage into cache."""
        self._trades_cache.clear()
        for trade_file in self.storage_dir.glob("trade_*.json"):
            try:
                with open(trade_file, 'r') as f:
                    data = json.load(f)
                    trade = Trade.from_dict(data)
                    self._trades_cache[trade.id] = trade
            except Exception as e:
                logger.error(f"Error loading trade {trade_file}: {e}")

    def _save_trade(self, trade: Trade) -> None:
        """Save a trade to storage."""
        trade_file = self._get_trade_file(trade.id)
        with open(trade_file, 'w') as f:
            json.dump(trade.to_dict(), f, indent=2)

    def _delete_trade_file(self, trade_id: str) -> None:
        """Delete a trade file from storage."""
        trade_file = self._get_trade_file(trade_id)
        if trade_file.exists():
            trade_file.unlink()

    # CRUD Operations

    def create_trade(
        self,
        ticker: str,
        thesis: str = "",
        theme: str = "",
        catalyst: str = "",
        catalyst_date: datetime = None,
        scaling_strategy: ScalingStrategy = ScalingStrategy.CONSERVATIVE,
        tags: List[str] = None,
    ) -> Trade:
        """
        Create a new trade on the watchlist.

        Args:
            ticker: Stock ticker symbol
            thesis: Your investment thesis (the story)
            theme: Associated theme (e.g., "AI Infrastructure")
            catalyst: Expected catalyst event
            catalyst_date: When catalyst is expected
            scaling_strategy: Pre-built scaling strategy to use
            tags: Optional tags for organization

        Returns:
            Created Trade object
        """
        trade = Trade(
            ticker=ticker.upper(),
            thesis=thesis,
            theme=theme,
            catalyst=catalyst,
            catalyst_date=catalyst_date,
            scaling_plan=ScalingPlan.get_preset(scaling_strategy),
            tags=tags or [],
            status=TradeStatus.WATCHING,
        )

        self._trades_cache[trade.id] = trade
        self._save_trade(trade)
        return trade

    def get_trade(self, trade_id: str) -> Optional[Trade]:
        """Get a trade by ID."""
        return self._trades_cache.get(trade_id)

    def get_trade_by_ticker(self, ticker: str) -> Optional[Trade]:
        """Get the active trade for a ticker (if any)."""
        ticker = ticker.upper()
        for trade in self._trades_cache.values():
            if trade.ticker == ticker and trade.status not in [TradeStatus.CLOSED]:
                return trade
        return None

    def get_all_trades(self) -> List[Trade]:
        """Get all trades."""
        return list(self._trades_cache.values())

    def get_open_trades(self) -> List[Trade]:
        """Get all trades with open positions."""
        return [
            t for t in self._trades_cache.values()
            if t.status in [TradeStatus.OPEN, TradeStatus.SCALING_IN, TradeStatus.SCALING_OUT]
        ]

    def get_watchlist(self) -> List[Trade]:
        """Get trades on watchlist (not entered yet)."""
        return [
            t for t in self._trades_cache.values()
            if t.status == TradeStatus.WATCHING
        ]

    def get_closed_trades(self, limit: int = 100) -> List[Trade]:
        """Get closed trades, most recent first."""
        closed = [
            t for t in self._trades_cache.values()
            if t.status == TradeStatus.CLOSED
        ]
        return sorted(closed, key=lambda t: t.closed_at or datetime.min, reverse=True)[:limit]

    def update_trade(self, trade: Trade) -> None:
        """Update a trade in storage."""
        trade.updated_at = datetime.now()
        self._trades_cache[trade.id] = trade
        self._save_trade(trade)

    def delete_trade(self, trade_id: str) -> bool:
        """Delete a trade permanently."""
        if trade_id in self._trades_cache:
            del self._trades_cache[trade_id]
            self._delete_trade_file(trade_id)
            return True
        return False

    # Position Management

    def add_buy(
        self,
        trade_id: str,
        shares: int,
        price: float,
        reason: str = "",
        story_score: float = None,
        ai_confidence: float = None,
        technical_score: float = None,
    ) -> Optional[Tranche]:
        """
        Add a buy tranche to a trade.

        Args:
            trade_id: Trade ID
            shares: Number of shares to buy
            price: Price per share
            reason: Why this buy (thesis confirmed, scaling in, etc.)
            story_score: Current story score (0-100)
            ai_confidence: Current AI confidence (0-100)
            technical_score: Current technical score (0-100)

        Returns:
            Created Tranche or None if trade not found
        """
        trade = self.get_trade(trade_id)
        if not trade:
            return None

        tranche = Tranche(
            action="buy",
            shares=shares,
            price=price,
            reason=reason,
            story_score=story_score,
            ai_confidence=ai_confidence,
            technical_score=technical_score,
        )

        trade.add_tranche(tranche)
        self.update_trade(trade)
        return tranche

    def add_sell(
        self,
        trade_id: str,
        shares: int,
        price: float,
        reason: str = "",
        story_score: float = None,
        ai_confidence: float = None,
        technical_score: float = None,
    ) -> Optional[Tranche]:
        """
        Add a sell tranche to a trade.

        Args:
            trade_id: Trade ID
            shares: Number of shares to sell
            price: Price per share
            reason: Why this sell (profit target, story broken, etc.)
            story_score: Current story score (0-100)
            ai_confidence: Current AI confidence (0-100)
            technical_score: Current technical score (0-100)

        Returns:
            Created Tranche or None if trade not found
        """
        trade = self.get_trade(trade_id)
        if not trade:
            return None

        # Validate shares
        if shares > trade.total_shares:
            shares = trade.total_shares

        tranche = Tranche(
            action="sell",
            shares=shares,
            price=price,
            reason=reason,
            story_score=story_score,
            ai_confidence=ai_confidence,
            technical_score=technical_score,
        )

        trade.add_tranche(tranche)
        self.update_trade(trade)
        return tranche

    def close_trade(
        self,
        trade_id: str,
        price: float,
        reason: str = "Manual close",
    ) -> bool:
        """
        Close out entire position.

        Args:
            trade_id: Trade ID
            price: Closing price
            reason: Why closing

        Returns:
            True if closed successfully
        """
        trade = self.get_trade(trade_id)
        if not trade or trade.total_shares <= 0:
            return False

        self.add_sell(trade_id, trade.total_shares, price, reason)
        return True

    # Queries

    def get_trades_by_theme(self, theme: str) -> List[Trade]:
        """Get all trades associated with a theme."""
        theme_lower = theme.lower()
        return [
            t for t in self._trades_cache.values()
            if theme_lower in t.theme.lower()
        ]

    def get_trades_by_tag(self, tag: str) -> List[Trade]:
        """Get all trades with a specific tag."""
        tag_lower = tag.lower()
        return [
            t for t in self._trades_cache.values()
            if any(tag_lower in t_tag.lower() for t_tag in t.tags)
        ]

    def get_high_risk_trades(self) -> List[Trade]:
        """Get trades with HIGH or CRITICAL risk level."""
        from .models import RiskLevel
        high_risk = [RiskLevel.CRITICAL, RiskLevel.HIGH, RiskLevel.ELEVATED]
        return [
            t for t in self.get_open_trades()
            if t.current_risk_level in high_risk
        ]

    def get_tickers_to_scan(self) -> List[str]:
        """Get list of tickers that need scanning (watchlist + open)."""
        tickers = set()
        for trade in self._trades_cache.values():
            if trade.status != TradeStatus.CLOSED:
                tickers.add(trade.ticker)
        return list(tickers)

    # Analytics

    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get summary of entire portfolio."""
        open_trades = self.get_open_trades()

        total_invested = sum(t.total_invested for t in open_trades)
        total_shares = sum(t.total_shares for t in open_trades)
        realized_pnl = sum(t.realized_pnl for t in self.get_closed_trades())

        return {
            'open_positions': len(open_trades),
            'watchlist_count': len(self.get_watchlist()),
            'total_invested': total_invested,
            'total_shares': total_shares,
            'realized_pnl': realized_pnl,
            'high_risk_count': len(self.get_high_risk_trades()),
            'tickers': [t.ticker for t in open_trades],
        }

    def get_trade_summary(self, trade_id: str, current_price: float = None) -> Dict[str, Any]:
        """Get detailed summary for a single trade."""
        trade = self.get_trade(trade_id)
        if not trade:
            return {}

        summary = trade.to_dict()

        # Add current price info if provided
        if current_price and trade.total_shares > 0:
            cost_basis = trade.average_cost * trade.total_shares
            current_value = current_price * trade.total_shares
            unrealized_pnl = current_value - cost_basis
            unrealized_pnl_pct = (unrealized_pnl / cost_basis * 100) if cost_basis > 0 else 0

            summary['current_price'] = current_price
            summary['current_value'] = current_value
            summary['unrealized_pnl'] = unrealized_pnl
            summary['unrealized_pnl_pct'] = unrealized_pnl_pct

        return summary

    def export_trades(self, include_closed: bool = True) -> List[Dict[str, Any]]:
        """Export all trades as list of dictionaries."""
        trades = self.get_all_trades() if include_closed else self.get_open_trades()
        return [t.to_dict() for t in trades]

    def import_trades(self, trades_data: List[Dict[str, Any]]) -> int:
        """Import trades from list of dictionaries."""
        count = 0
        for data in trades_data:
            try:
                trade = Trade.from_dict(data)
                self._trades_cache[trade.id] = trade
                self._save_trade(trade)
                count += 1
            except Exception as e:
                logger.error(f"Error importing trade: {e}")
        return count


# Global instance
_trade_manager: Optional[TradeManager] = None


def get_trade_manager() -> TradeManager:
    """Get or create global trade manager instance."""
    global _trade_manager
    if _trade_manager is None:
        _trade_manager = TradeManager()
    return _trade_manager
