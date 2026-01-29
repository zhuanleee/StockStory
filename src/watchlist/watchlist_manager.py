"""
Watchlist Manager - Enhanced watchlist with automatic updates from scans

Features:
- Manual addition of stocks from scans
- Automatic data updates (sentiment, fundamentals, technicals)
- Auto-calibration using evolutionary brain
- X Intelligence sentiment integration
- Real-time price updates
- Fully editable by user
- Persistence to JSON
"""

import json
import logging
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum

logger = logging.getLogger(__name__)

# Storage
WATCHLIST_DIR = Path('user_data/watchlist')
WATCHLIST_DIR.mkdir(parents=True, exist_ok=True)
WATCHLIST_FILE = WATCHLIST_DIR / 'watchlist.json'


class WatchlistPriority(Enum):
    """Priority levels for watchlist items."""
    HIGH = "high"        # Ready to enter soon
    MEDIUM = "medium"    # Monitor closely
    LOW = "low"          # Long-term watch
    ARCHIVE = "archive"  # Historical reference


class SignalQuality(Enum):
    """Quality of the setup."""
    EXCELLENT = "excellent"  # All criteria met
    GOOD = "good"           # Most criteria met
    FAIR = "fair"           # Some concerns
    POOR = "poor"           # Weak setup
    UNKNOWN = "unknown"     # Not enough data


@dataclass
class WatchlistItem:
    """
    Enhanced watchlist item with automatic updates.
    """
    # Basic Info
    ticker: str
    added_at: str = field(default_factory=lambda: datetime.now().isoformat())
    added_from: str = "manual"  # "manual", "scan", "theme", "alert"

    # User Editable Fields
    notes: str = ""
    thesis: str = ""
    catalyst: str = ""
    target_entry: Optional[float] = None
    stop_loss: Optional[float] = None
    position_size: str = "normal"  # "small", "normal", "large"
    priority: str = WatchlistPriority.MEDIUM.value
    tags: List[str] = field(default_factory=list)

    # Auto-Updated from Scans (DO NOT manually edit)
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())

    # Price Data
    current_price: Optional[float] = None
    price_change_pct: Optional[float] = None
    volume: Optional[int] = None
    avg_volume: Optional[int] = None
    volume_ratio: Optional[float] = None

    # Technical Scores
    rs_rating: Optional[int] = None  # 0-100
    technical_score: Optional[int] = None  # 0-10
    momentum_score: Optional[int] = None  # 0-10

    # Fundamental Data
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    revenue_growth: Optional[float] = None
    earnings_growth: Optional[float] = None

    # Theme & Story
    theme: str = ""
    theme_strength: Optional[int] = None  # 0-10
    theme_stage: str = ""  # "emerging", "developing", "mature", "declining"
    story_score: Optional[int] = None  # 0-10

    # AI Sentiment (from X Intelligence)
    x_sentiment: str = "neutral"  # "bullish", "bearish", "neutral"
    x_sentiment_score: Optional[float] = None  # -1 to +1
    x_red_flags: List[str] = field(default_factory=list)
    x_catalysts: List[str] = field(default_factory=list)
    x_last_checked: Optional[str] = None

    # AI Analysis (from Evolutionary Brain)
    ai_confidence: Optional[float] = None  # 0-1
    ai_decision: str = "hold"  # "buy", "hold", "sell"
    ai_reasoning: str = ""
    ai_last_analyzed: Optional[str] = None

    # Composite Scores
    overall_score: Optional[int] = None  # 0-10 weighted composite
    signal_quality: str = SignalQuality.UNKNOWN.value
    setup_complete: bool = False

    # Alerts & Triggers
    price_alerts: List[Dict[str, Any]] = field(default_factory=list)
    triggered_alerts: List[str] = field(default_factory=list)

    # Metadata
    scan_count: int = 0  # How many times seen in scans
    last_seen_in_scan: Optional[str] = None

    # Performance Tracking (once entered)
    entered_at: Optional[str] = None
    entry_price: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WatchlistItem':
        """Create from dictionary."""
        return cls(**data)

    def calculate_overall_score(self, learned_weights=None) -> int:
        """
        Calculate weighted overall score (0-10).

        Args:
            learned_weights: Optional ComponentWeights from learning system.
                           If None, uses default weights.

        Default Weighting:
        - Theme/Story: 30%
        - Technical: 25%
        - AI Confidence: 25%
        - Sentiment: 20%

        With learned_weights, uses weights learned from real trade outcomes.
        """
        scores = []
        weights = []

        # Get weights (learned or default)
        if learned_weights:
            theme_weight = learned_weights.theme
            technical_weight = learned_weights.technical
            ai_weight = learned_weights.ai
            sentiment_weight = learned_weights.sentiment
        else:
            # Fallback to default weights
            theme_weight = 0.30
            technical_weight = 0.25
            ai_weight = 0.25
            sentiment_weight = 0.20

        # Theme/Story
        if self.story_score is not None:
            scores.append(self.story_score)
            weights.append(theme_weight)

        # Technical
        if self.technical_score is not None:
            scores.append(self.technical_score)
            weights.append(technical_weight)

        # AI Confidence
        if self.ai_confidence is not None:
            scores.append(self.ai_confidence * 10)  # Convert 0-1 to 0-10
            weights.append(ai_weight)

        # X Sentiment
        if self.x_sentiment_score is not None:
            # Convert -1 to +1 → 0 to 10
            sentiment_score = (self.x_sentiment_score + 1) * 5
            scores.append(sentiment_score)
            weights.append(sentiment_weight)

        if not scores:
            return 0

        # Normalize weights
        total_weight = sum(weights)
        normalized_weights = [w / total_weight for w in weights]

        # Calculate weighted average
        overall = sum(s * w for s, w in zip(scores, normalized_weights))
        return int(round(overall))

    def determine_signal_quality(self) -> SignalQuality:
        """Determine setup quality based on scores."""
        if self.overall_score is None:
            return SignalQuality.UNKNOWN

        if self.overall_score >= 8:
            return SignalQuality.EXCELLENT
        elif self.overall_score >= 6:
            return SignalQuality.GOOD
        elif self.overall_score >= 4:
            return SignalQuality.FAIR
        else:
            return SignalQuality.POOR

    def check_setup_complete(self) -> bool:
        """Check if setup is complete and ready to trade."""
        required_fields = [
            self.current_price is not None,
            self.rs_rating is not None,
            self.technical_score is not None,
            len(self.theme) > 0,
            self.story_score is not None,
            self.overall_score is not None and self.overall_score >= 6,
        ]
        return all(required_fields)


class WatchlistManager:
    """
    Manages watchlist with automatic updates.
    """

    def __init__(self):
        self.items: Dict[str, WatchlistItem] = {}
        self._load_watchlist()
        self._update_lock = threading.Lock()

        # Auto-update configuration
        self.auto_update_enabled = True
        self.update_interval = 300  # 5 minutes
        self._last_update = datetime.now()

        # Start background auto-update thread
        self._start_auto_update_thread()

    def _load_watchlist(self):
        """Load watchlist from disk."""
        if WATCHLIST_FILE.exists():
            try:
                with open(WATCHLIST_FILE, 'r') as f:
                    data = json.load(f)
                    for ticker, item_data in data.items():
                        self.items[ticker] = WatchlistItem.from_dict(item_data)
            except Exception as e:
                logger.error(f"Error loading watchlist: {e}")

    def _save_watchlist(self):
        """Save watchlist to disk."""
        try:
            with open(WATCHLIST_FILE, 'w') as f:
                data = {ticker: item.to_dict() for ticker, item in self.items.items()}
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving watchlist: {e}")

    # ==========================================================================
    # CRUD Operations
    # ==========================================================================

    def add_item(
        self,
        ticker: str,
        notes: str = "",
        thesis: str = "",
        catalyst: str = "",
        priority: WatchlistPriority = WatchlistPriority.MEDIUM,
        tags: List[str] = None,
        added_from: str = "manual"
    ) -> WatchlistItem:
        """
        Add item to watchlist manually.

        Args:
            ticker: Stock ticker
            notes: Your notes
            thesis: Investment thesis
            catalyst: Expected catalyst
            priority: Priority level
            tags: Tags for organization
            added_from: Source ("manual", "scan", "theme", "alert")

        Returns:
            Created WatchlistItem
        """
        ticker = ticker.upper()

        if ticker in self.items:
            # Update existing item
            item = self.items[ticker]
            item.notes = notes or item.notes
            item.thesis = thesis or item.thesis
            item.catalyst = catalyst or item.catalyst
            item.priority = priority.value
            if tags:
                item.tags = list(set(item.tags + tags))
        else:
            # Create new item
            item = WatchlistItem(
                ticker=ticker,
                notes=notes,
                thesis=thesis,
                catalyst=catalyst,
                priority=priority.value,
                tags=tags or [],
                added_from=added_from
            )
            self.items[ticker] = item

        self._save_watchlist()
        return item

    def add_from_scan(self, ticker: str, scan_data: Dict[str, Any]) -> WatchlistItem:
        """
        Add item from scan results with automatic data population.

        Args:
            ticker: Stock ticker
            scan_data: Data from scanner

        Returns:
            Created/updated WatchlistItem
        """
        ticker = ticker.upper()

        # Get or create item
        if ticker in self.items:
            item = self.items[ticker]
            item.scan_count += 1
        else:
            item = WatchlistItem(ticker=ticker, added_from="scan")
            self.items[ticker] = item

        # Update from scan data
        self._update_from_scan_data(item, scan_data)

        item.last_seen_in_scan = datetime.now().isoformat()
        self._save_watchlist()
        return item

    def update_item(self, ticker: str, **kwargs) -> Optional[WatchlistItem]:
        """
        Update watchlist item fields.
        User can edit any field.

        Args:
            ticker: Stock ticker
            **kwargs: Fields to update

        Returns:
            Updated item or None if not found
        """
        ticker = ticker.upper()
        if ticker not in self.items:
            return None

        item = self.items[ticker]

        # Update allowed fields
        for key, value in kwargs.items():
            if hasattr(item, key):
                setattr(item, key, value)

        item.last_updated = datetime.now().isoformat()
        self._save_watchlist()
        return item

    def remove_item(self, ticker: str) -> bool:
        """Remove item from watchlist."""
        ticker = ticker.upper()
        if ticker in self.items:
            del self.items[ticker]
            self._save_watchlist()
            return True
        return False

    def get_item(self, ticker: str) -> Optional[WatchlistItem]:
        """Get single watchlist item."""
        return self.items.get(ticker.upper())

    def get_all_items(self) -> List[WatchlistItem]:
        """Get all watchlist items."""
        return list(self.items.values())

    def get_by_priority(self, priority: WatchlistPriority) -> List[WatchlistItem]:
        """Get items by priority."""
        return [item for item in self.items.values() if item.priority == priority.value]

    def get_by_tag(self, tag: str) -> List[WatchlistItem]:
        """Get items by tag."""
        return [item for item in self.items.values() if tag in item.tags]

    def get_ready_to_trade(self) -> List[WatchlistItem]:
        """Get items with complete setups."""
        return [item for item in self.items.values() if item.setup_complete]

    def search(self, query: str) -> List[WatchlistItem]:
        """Search watchlist by ticker, notes, thesis, catalyst."""
        query = query.lower()
        results = []
        for item in self.items.values():
            if (query in item.ticker.lower() or
                query in item.notes.lower() or
                query in item.thesis.lower() or
                query in item.catalyst.lower() or
                query in item.theme.lower()):
                results.append(item)
        return results

    # ==========================================================================
    # Auto-Update Functions
    # ==========================================================================

    def _update_from_scan_data(self, item: WatchlistItem, scan_data: Dict[str, Any]):
        """Update item with data from scanner."""

        # Price data
        item.current_price = scan_data.get('price') or scan_data.get('close')
        item.price_change_pct = scan_data.get('change_pct')
        item.volume = scan_data.get('volume')
        item.avg_volume = scan_data.get('avg_volume')

        if item.volume and item.avg_volume:
            item.volume_ratio = item.volume / item.avg_volume

        # Technical scores
        item.rs_rating = scan_data.get('rs')
        item.technical_score = scan_data.get('technical_score')
        item.momentum_score = scan_data.get('momentum_score')

        # Fundamental data
        item.market_cap = scan_data.get('market_cap')
        item.pe_ratio = scan_data.get('pe_ratio')
        item.revenue_growth = scan_data.get('revenue_growth')
        item.earnings_growth = scan_data.get('earnings_growth')

        # Theme/Story
        item.theme = scan_data.get('theme') or item.theme
        item.theme_strength = scan_data.get('theme_strength')
        item.theme_stage = scan_data.get('theme_stage') or item.theme_stage
        item.story_score = scan_data.get('story_score')

        # Update composite scores
        item.overall_score = item.calculate_overall_score()
        item.signal_quality = item.determine_signal_quality().value
        item.setup_complete = item.check_setup_complete()

        item.last_updated = datetime.now().isoformat()

    def update_all_from_scans(self, scan_results: List[Dict[str, Any]]):
        """
        Bulk update from scan results.

        Args:
            scan_results: List of scan result dictionaries
        """
        with self._update_lock:
            for result in scan_results:
                ticker = result.get('ticker') or result.get('symbol')
                if ticker and ticker.upper() in self.items:
                    item = self.items[ticker.upper()]
                    self._update_from_scan_data(item, result)
                    item.last_seen_in_scan = datetime.now().isoformat()

            self._save_watchlist()

    def update_x_sentiment(self, ticker: str):
        """
        Update X Intelligence sentiment for a ticker.
        Integrates with Component #37.
        """
        ticker = ticker.upper()
        if ticker not in self.items:
            return

        item = self.items[ticker]

        try:
            # Import X Intelligence
            from src.ai.xai_x_intelligence import XAIXIntelligence

            x_intel = XAIXIntelligence()
            sentiments = x_intel.monitor_specific_stocks_on_x([ticker])

            if ticker in sentiments:
                sentiment = sentiments[ticker]
                item.x_sentiment = sentiment.sentiment
                item.x_sentiment_score = sentiment.sentiment_score
                item.x_red_flags = sentiment.red_flags
                item.x_catalysts = sentiment.catalysts
                item.x_last_checked = datetime.now().isoformat()

                # Recalculate overall score with new sentiment
                item.overall_score = item.calculate_overall_score()
                item.signal_quality = item.determine_signal_quality().value
                item.setup_complete = item.check_setup_complete()

                self._save_watchlist()

        except Exception as e:
            logger.error(f"Error updating X sentiment for {ticker}: {e}")

    def update_ai_analysis(self, ticker: str):
        """
        Update AI analysis from Evolutionary Brain.
        Uses all 37 components for comprehensive analysis.
        """
        ticker = ticker.upper()
        if ticker not in self.items:
            return

        item = self.items[ticker]

        try:
            # Import Evolutionary CIO
            from src.ai.evolutionary_agentic_brain import get_evolutionary_cio

            cio = get_evolutionary_cio()

            # Get current price for analysis
            import yfinance as yf
            stock = yf.Ticker(ticker)
            current_price = stock.info.get('currentPrice') or stock.info.get('regularMarketPrice')

            if not current_price:
                return

            # Analyze with full agentic brain
            decision = cio.analyze_opportunity(
                ticker=ticker,
                signal_type='watchlist_review',
                signal_data={
                    'price': current_price,
                    'rs': item.rs_rating or 50,
                    'volume_trend': f'{item.volume_ratio:.1f}x' if item.volume_ratio else '1x',
                    'theme': item.theme
                },
                theme_data={
                    'name': item.theme,
                    'stage': item.theme_stage
                } if item.theme else None,
                timeframe_data={
                    'daily': {'trend': 'bullish', 'strength': 'moderate'},
                    'weekly': {'trend': 'bullish', 'strength': 'moderate'}
                }
            )

            # Update AI fields
            item.ai_confidence = decision.confidence
            item.ai_decision = decision.decision.value
            item.ai_reasoning = decision.reasoning
            item.ai_last_analyzed = datetime.now().isoformat()

            # Recalculate overall score
            item.overall_score = item.calculate_overall_score()
            item.signal_quality = item.determine_signal_quality().value
            item.setup_complete = item.check_setup_complete()

            self._save_watchlist()

        except Exception as e:
            logger.error(f"Error updating AI analysis for {ticker}: {e}")

    def update_price_data(self, ticker: str):
        """Update real-time price data."""
        ticker = ticker.upper()
        if ticker not in self.items:
            return

        item = self.items[ticker]

        try:
            import yfinance as yf
            stock = yf.Ticker(ticker)
            info = stock.info

            # Update price data
            item.current_price = info.get('currentPrice') or info.get('regularMarketPrice')
            item.price_change_pct = info.get('regularMarketChangePercent')
            item.volume = info.get('volume')
            item.avg_volume = info.get('averageVolume')

            if item.volume and item.avg_volume:
                item.volume_ratio = item.volume / item.avg_volume

            # Update fundamental data
            item.market_cap = info.get('marketCap')
            item.pe_ratio = info.get('trailingPE')

            item.last_updated = datetime.now().isoformat()
            self._save_watchlist()

        except Exception as e:
            logger.error(f"Error updating price for {ticker}: {e}")

    def auto_update_all(self, include_sentiment: bool = False, include_ai: bool = False):
        """
        Auto-update all watchlist items.

        Args:
            include_sentiment: Update X Intelligence sentiment (costs API calls)
            include_ai: Update AI analysis (costs API calls)
        """
        logger.info(f"Auto-updating {len(self.items)} watchlist items...")

        with self._update_lock:
            for ticker in list(self.items.keys()):
                # Always update price data (free)
                self.update_price_data(ticker)

                # Optional updates (cost API calls)
                if include_sentiment:
                    self.update_x_sentiment(ticker)

                if include_ai:
                    self.update_ai_analysis(ticker)

                # Small delay to avoid rate limits
                time.sleep(0.5)

        self._last_update = datetime.now()
        logger.info("Watchlist auto-update complete")

    def _start_auto_update_thread(self):
        """Start background thread for automatic updates."""
        def update_loop():
            while True:
                try:
                    if self.auto_update_enabled:
                        # Check if it's time to update
                        if (datetime.now() - self._last_update).total_seconds() >= self.update_interval:
                            # Update prices frequently (free)
                            self.auto_update_all(
                                include_sentiment=False,  # Only on demand to save costs
                                include_ai=False          # Only on demand to save costs
                            )

                    # Sleep for a minute
                    time.sleep(60)

                except Exception as e:
                    logger.error(f"Auto-update error: {e}")
                    time.sleep(60)

        thread = threading.Thread(target=update_loop, daemon=True)
        thread.start()
        logger.info("Watchlist auto-update thread started")

    def update_scores_with_learned_weights(self):
        """
        Recalculate all watchlist scores using learned weights from learning system.

        This integrates the 4-tier learning system to use weights that have been
        learned from actual trade outcomes, rather than hardcoded defaults.

        Call this periodically (e.g., daily) to keep scores updated as the system learns.
        """
        try:
            # Import learning system
            from src.learning import get_learning_brain

            brain = get_learning_brain()
            learned_weights = brain.current_weights

            logger.info(f"Updating watchlist scores with learned weights:")
            logger.info(f"  Theme: {learned_weights.theme:.1%} (default: 30%)")
            logger.info(f"  Technical: {learned_weights.technical:.1%} (default: 25%)")
            logger.info(f"  AI: {learned_weights.ai:.1%} (default: 25%)")
            logger.info(f"  Sentiment: {learned_weights.sentiment:.1%} (default: 20%)")

            # Update all items
            updated_count = 0
            with self._update_lock:
                for ticker, item in self.items.items():
                    old_score = item.overall_score

                    # Recalculate with learned weights
                    item.overall_score = item.calculate_overall_score(learned_weights=learned_weights)
                    item.signal_quality = item.determine_signal_quality().value
                    item.setup_complete = item.check_setup_complete()

                    if old_score != item.overall_score:
                        updated_count += 1
                        logger.info(f"  {ticker}: {old_score or 0}/10 → {item.overall_score}/10")

                self._save_watchlist()

            logger.info(f"Updated {updated_count} items with learned weights")
            return updated_count

        except ImportError:
            logger.warning("Learning system not available, using default weights")
            return 0
        except Exception as e:
            logger.error(f"Error updating with learned weights: {e}")
            return 0

    # ==========================================================================
    # Bulk Operations
    # ==========================================================================

    def clear_all(self):
        """Clear entire watchlist."""
        self.items.clear()
        self._save_watchlist()

    def export_to_json(self, filepath: str):
        """Export watchlist to JSON file."""
        data = {ticker: item.to_dict() for ticker, item in self.items.items()}
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

    def import_from_json(self, filepath: str):
        """Import watchlist from JSON file."""
        with open(filepath, 'r') as f:
            data = json.load(f)
            for ticker, item_data in data.items():
                self.items[ticker] = WatchlistItem.from_dict(item_data)
        self._save_watchlist()

    def get_statistics(self) -> Dict[str, Any]:
        """Get watchlist statistics."""
        items = list(self.items.values())

        return {
            'total_items': len(items),
            'by_priority': {
                'high': len([i for i in items if i.priority == WatchlistPriority.HIGH.value]),
                'medium': len([i for i in items if i.priority == WatchlistPriority.MEDIUM.value]),
                'low': len([i for i in items if i.priority == WatchlistPriority.LOW.value]),
            },
            'by_quality': {
                'excellent': len([i for i in items if i.signal_quality == SignalQuality.EXCELLENT.value]),
                'good': len([i for i in items if i.signal_quality == SignalQuality.GOOD.value]),
                'fair': len([i for i in items if i.signal_quality == SignalQuality.FAIR.value]),
                'poor': len([i for i in items if i.signal_quality == SignalQuality.POOR.value]),
            },
            'ready_to_trade': len([i for i in items if i.setup_complete]),
            'with_x_sentiment': len([i for i in items if i.x_last_checked]),
            'with_ai_analysis': len([i for i in items if i.ai_last_analyzed]),
            'last_update': self._last_update.isoformat(),
        }


# Singleton instance
_watchlist_manager = None

def get_watchlist_manager() -> WatchlistManager:
    """Get singleton watchlist manager instance."""
    global _watchlist_manager
    if _watchlist_manager is None:
        _watchlist_manager = WatchlistManager()
    return _watchlist_manager


if __name__ == "__main__":
    # Quick test
    wm = get_watchlist_manager()
    print(f"Watchlist Manager initialized with {len(wm.items)} items")
    print(f"Statistics: {wm.get_statistics()}")
