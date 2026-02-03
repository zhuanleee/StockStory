"""
Unified Watchlist + Scan Management System

Manages:
- Watchlist stocks with performance tracking
- Starred scans (never auto-delete)
- Archived scans (searchable history)
- Links between stocks and their source scans
"""

import os
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field

logger = logging.getLogger(__name__)

# Storage paths
VOLUME_PATH = os.environ.get('VOLUME_PATH', '/data')
WATCHLIST_FILE = 'watchlist.json'
SCANS_INDEX_FILE = 'scans_index.json'


@dataclass
class WatchlistItem:
    """A stock in the watchlist"""
    ticker: str
    added_date: str
    source_scan_id: Optional[int] = None
    entry_price: Optional[float] = None
    current_price: Optional[float] = None
    themes: List[str] = field(default_factory=list)
    notes: str = ""
    alerts_enabled: bool = True

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'WatchlistItem':
        return cls(**data)


@dataclass
class ScanRecord:
    """Metadata for a scan"""
    scan_id: int
    date: str
    filename: str
    top_picks: List[str] = field(default_factory=list)
    themes: List[str] = field(default_factory=list)
    total_stocks: int = 0
    starred: bool = False
    archived: bool = False
    archived_date: Optional[str] = None
    notes: str = ""

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'ScanRecord':
        return cls(**data)


class WatchlistManager:
    """
    Manages watchlist stocks and scan records.

    Storage structure:
    /data/
      watchlist.json         - Watchlist items
      scans_index.json       - Scan metadata index
      scan_1.json            - Actual scan data
      scan_2.json
      ...
      archive/
        scan_old.json        - Archived scan data
    """

    def __init__(self, data_path: Optional[str] = None):
        self.data_path = Path(data_path or VOLUME_PATH)
        self.archive_path = self.data_path / 'archive'
        self.watchlist_file = self.data_path / WATCHLIST_FILE
        self.scans_index_file = self.data_path / SCANS_INDEX_FILE

        # Ensure directories exist
        self.data_path.mkdir(parents=True, exist_ok=True)
        self.archive_path.mkdir(parents=True, exist_ok=True)

        # Load data
        self.watchlist: Dict[str, WatchlistItem] = self._load_watchlist()
        self.scans_index: Dict[int, ScanRecord] = self._load_scans_index()
        self._next_scan_id = self._get_next_scan_id()

    # =========================================================================
    # Watchlist Operations
    # =========================================================================

    def add_to_watchlist(
        self,
        ticker: str,
        source_scan_id: Optional[int] = None,
        entry_price: Optional[float] = None,
        themes: Optional[List[str]] = None,
        notes: str = ""
    ) -> WatchlistItem:
        """Add a stock to the watchlist"""
        ticker = ticker.upper()

        if ticker in self.watchlist:
            # Update existing
            item = self.watchlist[ticker]
            if source_scan_id:
                item.source_scan_id = source_scan_id
            if entry_price:
                item.entry_price = entry_price
            if themes:
                item.themes = list(set(item.themes + themes))
            if notes:
                item.notes = notes
        else:
            # Create new
            item = WatchlistItem(
                ticker=ticker,
                added_date=datetime.now().isoformat(),
                source_scan_id=source_scan_id,
                entry_price=entry_price,
                themes=themes or [],
                notes=notes
            )
            self.watchlist[ticker] = item

        self._save_watchlist()
        logger.info(f"Added {ticker} to watchlist")
        return item

    def remove_from_watchlist(self, ticker: str) -> bool:
        """Remove a stock from the watchlist"""
        ticker = ticker.upper()
        if ticker in self.watchlist:
            del self.watchlist[ticker]
            self._save_watchlist()
            logger.info(f"Removed {ticker} from watchlist")
            return True
        return False

    def get_watchlist(self) -> List[WatchlistItem]:
        """Get all watchlist items"""
        return list(self.watchlist.values())

    def get_watchlist_item(self, ticker: str) -> Optional[WatchlistItem]:
        """Get a specific watchlist item"""
        return self.watchlist.get(ticker.upper())

    def update_watchlist_prices(self, prices: Dict[str, float]) -> None:
        """Update current prices for watchlist items"""
        for ticker, price in prices.items():
            ticker = ticker.upper()
            if ticker in self.watchlist:
                self.watchlist[ticker].current_price = price
        self._save_watchlist()

    def get_watchlist_with_performance(self) -> List[Dict]:
        """Get watchlist with performance metrics"""
        result = []
        for item in self.watchlist.values():
            data = item.to_dict()

            # Calculate performance
            if item.entry_price and item.current_price:
                change = item.current_price - item.entry_price
                change_pct = (change / item.entry_price) * 100
                data['change'] = change
                data['change_pct'] = change_pct
            else:
                data['change'] = None
                data['change_pct'] = None

            # Get source scan info
            if item.source_scan_id and item.source_scan_id in self.scans_index:
                scan = self.scans_index[item.source_scan_id]
                data['source_scan'] = {
                    'id': scan.scan_id,
                    'date': scan.date,
                    'themes': scan.themes
                }

            result.append(data)

        return result

    # =========================================================================
    # Scan Operations
    # =========================================================================

    def register_scan(
        self,
        filename: str,
        top_picks: List[str],
        themes: List[str] = None,
        total_stocks: int = 0
    ) -> ScanRecord:
        """Register a new scan and return its record"""
        scan_id = self._next_scan_id
        self._next_scan_id += 1

        record = ScanRecord(
            scan_id=scan_id,
            date=datetime.now().isoformat(),
            filename=filename,
            top_picks=top_picks[:10],  # Top 10
            themes=themes or [],
            total_stocks=total_stocks,
            starred=False,
            archived=False
        )

        self.scans_index[scan_id] = record
        self._save_scans_index()

        logger.info(f"Registered scan #{scan_id}: {filename}")
        return record

    def star_scan(self, scan_id: int, add_to_watchlist: bool = False) -> Optional[ScanRecord]:
        """Star a scan to prevent auto-deletion"""
        if scan_id not in self.scans_index:
            return None

        record = self.scans_index[scan_id]
        record.starred = True
        record.archived = False  # Unarchive if archived
        self._save_scans_index()

        # Optionally add top picks to watchlist
        if add_to_watchlist:
            scan_data = self._load_scan_data(record.filename)
            if scan_data:
                for ticker in record.top_picks[:5]:
                    # Find entry price from scan
                    entry_price = None
                    for result in scan_data.get('results', []):
                        if result.get('ticker') == ticker:
                            entry_price = result.get('price')
                            break

                    self.add_to_watchlist(
                        ticker=ticker,
                        source_scan_id=scan_id,
                        entry_price=entry_price,
                        themes=record.themes
                    )

        logger.info(f"Starred scan #{scan_id}")
        return record

    def unstar_scan(self, scan_id: int) -> Optional[ScanRecord]:
        """Unstar a scan"""
        if scan_id not in self.scans_index:
            return None

        record = self.scans_index[scan_id]
        record.starred = False
        self._save_scans_index()

        logger.info(f"Unstarred scan #{scan_id}")
        return record

    def archive_scan(self, scan_id: int) -> Optional[ScanRecord]:
        """Archive a scan"""
        if scan_id not in self.scans_index:
            return None

        record = self.scans_index[scan_id]
        record.archived = True
        record.archived_date = datetime.now().isoformat()
        self._save_scans_index()

        # Move scan file to archive
        src_file = self.data_path / record.filename
        if src_file.exists():
            dst_file = self.archive_path / record.filename
            src_file.rename(dst_file)
            record.filename = f"archive/{record.filename}"
            self._save_scans_index()

        logger.info(f"Archived scan #{scan_id}")
        return record

    def get_starred_scans(self) -> List[ScanRecord]:
        """Get all starred scans"""
        return [s for s in self.scans_index.values() if s.starred]

    def get_archived_scans(self) -> List[ScanRecord]:
        """Get all archived scans"""
        return [s for s in self.scans_index.values() if s.archived]

    def get_recent_scans(self, limit: int = 10) -> List[ScanRecord]:
        """Get recent scans (not archived)"""
        active = [s for s in self.scans_index.values() if not s.archived]
        return sorted(active, key=lambda x: x.date, reverse=True)[:limit]

    def get_scan(self, scan_id: int) -> Optional[ScanRecord]:
        """Get a scan record by ID"""
        return self.scans_index.get(scan_id)

    def get_latest_scan(self) -> Optional[ScanRecord]:
        """Get the most recent scan"""
        if not self.scans_index:
            return None
        return max(self.scans_index.values(), key=lambda x: x.date)

    def get_scan_data(self, scan_id: int) -> Optional[Dict]:
        """Get full scan data by ID"""
        record = self.scans_index.get(scan_id)
        if not record:
            return None
        return self._load_scan_data(record.filename)

    def get_stock_history(self, ticker: str) -> List[Dict]:
        """Get all scans where a stock appeared"""
        ticker = ticker.upper()
        history = []

        for scan in sorted(self.scans_index.values(), key=lambda x: x.date, reverse=True):
            # Check if ticker in top picks
            if ticker in scan.top_picks:
                scan_data = self._load_scan_data(scan.filename)
                stock_data = None

                if scan_data:
                    for result in scan_data.get('results', []):
                        if result.get('ticker') == ticker:
                            stock_data = result
                            break

                history.append({
                    'scan_id': scan.scan_id,
                    'date': scan.date,
                    'starred': scan.starred,
                    'themes': scan.themes,
                    'stock_data': stock_data
                })

        return history

    def cleanup_old_scans(self, days: int = 7) -> int:
        """Archive unstarred scans older than X days"""
        cutoff = datetime.now() - timedelta(days=days)
        archived_count = 0

        for scan in list(self.scans_index.values()):
            if scan.starred or scan.archived:
                continue

            scan_date = datetime.fromisoformat(scan.date)
            if scan_date < cutoff:
                self.archive_scan(scan.scan_id)
                archived_count += 1

        logger.info(f"Cleaned up {archived_count} old scans")
        return archived_count

    # =========================================================================
    # Private Methods
    # =========================================================================

    def _load_watchlist(self) -> Dict[str, WatchlistItem]:
        """Load watchlist from file"""
        if not self.watchlist_file.exists():
            return {}

        try:
            with open(self.watchlist_file) as f:
                data = json.load(f)
            return {k: WatchlistItem.from_dict(v) for k, v in data.items()}
        except Exception as e:
            logger.error(f"Error loading watchlist: {e}")
            return {}

    def _save_watchlist(self) -> None:
        """Save watchlist to file"""
        try:
            data = {k: v.to_dict() for k, v in self.watchlist.items()}
            with open(self.watchlist_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving watchlist: {e}")

    def _load_scans_index(self) -> Dict[int, ScanRecord]:
        """Load scans index from file"""
        if not self.scans_index_file.exists():
            # Migrate existing scans
            return self._migrate_existing_scans()

        try:
            with open(self.scans_index_file) as f:
                data = json.load(f)
            return {int(k): ScanRecord.from_dict(v) for k, v in data.items()}
        except Exception as e:
            logger.error(f"Error loading scans index: {e}")
            return {}

    def _save_scans_index(self) -> None:
        """Save scans index to file"""
        try:
            data = {str(k): v.to_dict() for k, v in self.scans_index.items()}
            with open(self.scans_index_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving scans index: {e}")

    def _migrate_existing_scans(self) -> Dict[int, ScanRecord]:
        """Migrate existing scan files to indexed format"""
        index = {}
        scan_files = sorted(self.data_path.glob("scan_*.json"))

        for i, scan_file in enumerate(scan_files, 1):
            try:
                with open(scan_file) as f:
                    data = json.load(f)

                # Extract metadata
                results = data.get('results', [])
                top_picks = [r.get('ticker') for r in results[:10] if r.get('ticker')]
                themes = list(set(
                    r.get('theme', '') for r in results[:20]
                    if r.get('theme')
                ))[:5]

                # Get date from filename or data
                scan_date = data.get('timestamp', datetime.now().isoformat())

                record = ScanRecord(
                    scan_id=i,
                    date=scan_date,
                    filename=scan_file.name,
                    top_picks=top_picks,
                    themes=themes,
                    total_stocks=len(results),
                    starred=False,
                    archived=False
                )
                index[i] = record

            except Exception as e:
                logger.error(f"Error migrating {scan_file}: {e}")

        # Save the index
        if index:
            self.scans_index = index
            self._save_scans_index()
            logger.info(f"Migrated {len(index)} existing scans")

        return index

    def _get_next_scan_id(self) -> int:
        """Get next available scan ID"""
        if not self.scans_index:
            return 1
        return max(self.scans_index.keys()) + 1

    def _load_scan_data(self, filename: str) -> Optional[Dict]:
        """Load full scan data from file"""
        try:
            filepath = self.data_path / filename
            if not filepath.exists():
                # Check archive
                filepath = self.archive_path / filename.replace('archive/', '')

            if filepath.exists():
                with open(filepath) as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading scan data {filename}: {e}")
        return None


# Singleton instance
_watchlist_manager = None


def get_watchlist_manager(data_path: Optional[str] = None) -> WatchlistManager:
    """Get singleton watchlist manager instance"""
    global _watchlist_manager
    if _watchlist_manager is None:
        _watchlist_manager = WatchlistManager(data_path)
    return _watchlist_manager
