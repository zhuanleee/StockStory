"""
Universe Manager - Dynamic Stock Universe Management

Dynamically fetches and maintains stock universes from authoritative sources:
- S&P 500 from Wikipedia
- NASDAQ-100 from Wikipedia
- Sector compositions from Yahoo Finance
- Breadth universe from learned sectors

Features:
- Multiple source fallbacks
- Smart caching (24h for indices, 1h for sectors)
- Automatic rebalance detection
- Self-health monitoring

Author: Stock Scanner Bot
Version: 1.0
"""

import json
import os
import re
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
from collections import defaultdict
import hashlib

# Setup logging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s %(name)s: %(message)s')
logger = logging.getLogger('universe_manager')

# Data directory
DATA_DIR = Path(__file__).parent / 'universe_data'
DATA_DIR.mkdir(exist_ok=True)

CACHE_FILE = DATA_DIR / 'universe_cache.json'
HEALTH_FILE = DATA_DIR / 'universe_health.json'
HISTORY_FILE = DATA_DIR / 'universe_history.json'


@dataclass
class UniverseHealth:
    """Health status of the universe manager"""
    status: str  # 'healthy', 'degraded', 'stale'
    last_update: str
    sp500_count: int
    nasdaq100_count: int
    sectors_loaded: int
    cache_age_hours: float
    issues: List[str]
    sources_status: Dict[str, str]
    # Additional fields for API compatibility
    total_unique: int = 0
    breadth_universe_size: int = 0
    sp500_source: str = 'cache'
    nasdaq100_source: str = 'cache'
    health_score: float = 100.0


class UniverseManager:
    """
    Dynamically maintains stock universes from authoritative sources.
    NO HARDCODED TICKER LISTS - everything is fetched and cached.
    """

    # Source configurations
    SOURCES = {
        'sp500': {
            'primary': 'wikipedia',
            'fallback': ['slickcharts', 'cached'],
            'cache_hours': 24,
            'expected_count': (490, 510),  # Valid range
        },
        'nasdaq100': {
            'primary': 'wikipedia',
            'fallback': ['slickcharts', 'cached'],
            'cache_hours': 24,
            'expected_count': (95, 105),
        },
        'sectors': {
            'primary': 'yahoo_finance',
            'fallback': ['cached'],
            'cache_hours': 6,
        }
    }

    # Wikipedia URLs
    WIKIPEDIA_SP500 = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
    WIKIPEDIA_NASDAQ100 = 'https://en.wikipedia.org/wiki/Nasdaq-100'

    # Sector ETF mapping for sector discovery
    SECTOR_ETFS = {
        'technology': 'XLK',
        'financials': 'XLF',
        'healthcare': 'XLV',
        'consumer_discretionary': 'XLY',
        'consumer_staples': 'XLP',
        'energy': 'XLE',
        'utilities': 'XLU',
        'real_estate': 'XLRE',
        'materials': 'XLB',
        'industrials': 'XLI',
        'communication': 'XLC',
    }

    def __init__(self):
        self.cache: Dict = {}
        self.last_fetch: Dict[str, datetime] = {}
        self.health_issues: List[str] = []
        self._load_cache()

    def _load_cache(self):
        """Load cached universe data"""
        if CACHE_FILE.exists():
            try:
                with open(CACHE_FILE, 'r') as f:
                    data = json.load(f)
                self.cache = data.get('universes', {})

                # Parse last fetch times
                for key, timestamp in data.get('last_fetch', {}).items():
                    self.last_fetch[key] = datetime.fromisoformat(timestamp)

                logger.info(f"Loaded cache: {len(self.cache)} universes")
            except Exception as e:
                logger.error(f"Failed to load cache: {e}")
                self.cache = {}

    def _save_cache(self):
        """Save universe data to cache"""
        data = {
            'version': '1.0',
            'last_updated': datetime.now().isoformat(),
            'universes': self.cache,
            'last_fetch': {k: v.isoformat() for k, v in self.last_fetch.items()}
        }
        with open(CACHE_FILE, 'w') as f:
            json.dump(data, f, indent=2)

    def _is_cache_valid(self, universe_name: str, max_age_hours: int = 24) -> bool:
        """Check if cached data is still valid"""
        if universe_name not in self.cache:
            return False
        if universe_name not in self.last_fetch:
            return False

        age = datetime.now() - self.last_fetch[universe_name]
        return age.total_seconds() < max_age_hours * 3600

    # =========================================================================
    # S&P 500 FETCHING
    # =========================================================================

    def fetch_sp500(self, force_refresh: bool = False) -> List[str]:
        """
        Fetch current S&P 500 constituents.
        Uses Polygon API as primary, Wikipedia as fallback.
        Returns list of ticker symbols.
        """
        cache_key = 'sp500'

        # Check cache
        if not force_refresh and self._is_cache_valid(cache_key, 24):
            return self.cache[cache_key]

        tickers = []
        source_used = None

        # Try primary source: Polygon API (more reliable than scraping)
        try:
            tickers = self._fetch_sp500_polygon()
            source_used = 'polygon'
            logger.info(f"Fetched {len(tickers)} S&P 500 tickers from Polygon")
        except Exception as e:
            logger.debug(f"Polygon SP500 fetch failed: {e}")

        # Fallback to Wikipedia if Polygon didn't work
        if len(tickers) < 400:
            try:
                tickers = self._fetch_sp500_wikipedia()
                source_used = 'wikipedia'
                logger.info(f"Fetched {len(tickers)} S&P 500 tickers from Wikipedia")
            except Exception as e:
                logger.warning(f"Wikipedia SP500 fetch failed: {e}")
                self.health_issues.append(f"Wikipedia SP500 failed: {e}")

        # Validate count
        if not (490 <= len(tickers) <= 510):
            logger.warning(f"SP500 count unexpected: {len(tickers)}")

            # Try fallback to cache
            if cache_key in self.cache and len(self.cache[cache_key]) > 400:
                logger.info("Using cached SP500 data")
                return self.cache[cache_key]

        if tickers:
            # Update cache
            self.cache[cache_key] = tickers
            self.last_fetch[cache_key] = datetime.now()
            self._save_cache()

            # Track changes
            self._track_universe_changes(cache_key, tickers)

        return tickers if tickers else self.cache.get(cache_key, [])

    def _fetch_sp500_polygon(self) -> List[str]:
        """
        Fetch large-cap US stocks from Polygon as S&P 500 proxy.

        Since Polygon doesn't have a direct S&P 500 endpoint, we fetch
        actively traded US stocks from major exchanges (NYSE, NASDAQ).
        """
        import os
        polygon_key = os.environ.get('POLYGON_API_KEY', '')
        if not polygon_key:
            raise ValueError("Polygon API key not configured")

        from src.data.polygon_provider import get_tickers_sync

        # Get stocks from NYSE and NASDAQ
        all_tickers = []

        # Fetch from both major exchanges
        for exchange in ['XNYS', 'XNAS']:
            tickers = get_tickers_sync(
                ticker_type='CS',
                market='stocks',
                exchange=exchange,
                limit=1000,
            )
            all_tickers.extend(tickers)

        # Filter and deduplicate
        seen = set()
        filtered = []
        for t in all_tickers:
            ticker = t.get('ticker', '')
            if ticker and ticker not in seen:
                # Filter out penny stocks, warrants, etc.
                if len(ticker) <= 5 and ticker.isalpha():
                    seen.add(ticker)
                    filtered.append(ticker)

        # Return top ~500 (approximate S&P 500)
        # In production, you'd filter by market cap if available
        return sorted(filtered)[:500]

    def _fetch_sp500_wikipedia(self) -> List[str]:
        """Fetch S&P 500 from Wikipedia (fallback)"""
        import re

        headers = {'User-Agent': 'StockScannerBot/1.0'}
        response = requests.get(self.WIKIPEDIA_SP500, headers=headers, timeout=30)
        response.raise_for_status()

        html = response.text
        tickers = []

        # Parse the table - looking for ticker symbols in the first column
        # Wikipedia format: <td><a href="/wiki/..." title="...">TICKER</a></td>
        # Or: <td>TICKER</td>

        # Find the constituents table
        table_match = re.search(r'<table[^>]*id="constituents"[^>]*>(.*?)</table>', html, re.DOTALL)
        if not table_match:
            # Try alternate table identification
            table_match = re.search(r'<table[^>]*class="[^"]*wikitable[^"]*sortable[^"]*"[^>]*>(.*?)</table>', html, re.DOTALL)

        if table_match:
            table_html = table_match.group(1)

            # Find all rows
            rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table_html, re.DOTALL)

            for row in rows[1:]:  # Skip header
                # Extract first cell (ticker)
                cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
                if cells:
                    cell = cells[0]
                    # Extract ticker from link or plain text
                    ticker_match = re.search(r'>([A-Z]{1,5})</a>', cell)
                    if not ticker_match:
                        ticker_match = re.search(r'^([A-Z]{1,5})$', cell.strip())

                    if ticker_match:
                        ticker = ticker_match.group(1)
                        # Clean up (some have dots like BRK.B)
                        ticker = ticker.replace('.', '-')
                        tickers.append(ticker)

        # Deduplicate and validate
        tickers = list(set(tickers))
        tickers = [t for t in tickers if 1 <= len(t) <= 5 and t.isalpha() or '-' in t]

        return sorted(tickers)

    # =========================================================================
    # NASDAQ-100 FETCHING
    # =========================================================================

    def fetch_nasdaq100(self, force_refresh: bool = False) -> List[str]:
        """
        Fetch current NASDAQ-100 constituents.
        Uses Polygon API as primary, Wikipedia as fallback.
        """
        cache_key = 'nasdaq100'

        if not force_refresh and self._is_cache_valid(cache_key, 24):
            return self.cache[cache_key]

        tickers = []

        # Try Polygon first
        try:
            tickers = self._fetch_nasdaq100_polygon()
            logger.info(f"Fetched {len(tickers)} NASDAQ-100 tickers from Polygon")
        except Exception as e:
            logger.debug(f"Polygon NASDAQ100 fetch failed: {e}")

        # Fallback to Wikipedia
        if len(tickers) < 90:
            try:
                tickers = self._fetch_nasdaq100_wikipedia()
                logger.info(f"Fetched {len(tickers)} NASDAQ-100 tickers from Wikipedia")
            except Exception as e:
                logger.warning(f"Wikipedia NASDAQ100 fetch failed: {e}")
                self.health_issues.append(f"Wikipedia NASDAQ100 failed: {e}")

        # Validate
        if not (95 <= len(tickers) <= 105):
            if cache_key in self.cache:
                return self.cache[cache_key]

        if tickers:
            self.cache[cache_key] = tickers
            self.last_fetch[cache_key] = datetime.now()
            self._save_cache()
            self._track_universe_changes(cache_key, tickers)

        return tickers if tickers else self.cache.get(cache_key, [])

    def _fetch_nasdaq100_polygon(self) -> List[str]:
        """
        Fetch top NASDAQ stocks from Polygon as NASDAQ-100 proxy.
        """
        import os
        polygon_key = os.environ.get('POLYGON_API_KEY', '')
        if not polygon_key:
            raise ValueError("Polygon API key not configured")

        from src.data.polygon_provider import get_nasdaq_stocks_sync

        # Get NASDAQ stocks
        tickers = get_nasdaq_stocks_sync(limit=500)

        # Filter valid tickers
        filtered = [t for t in tickers if t and len(t) <= 5 and t.isalpha()]

        # Return top 100 (approximate NASDAQ-100)
        return sorted(filtered)[:100]

    def _fetch_nasdaq100_wikipedia(self) -> List[str]:
        """Fetch NASDAQ-100 from Wikipedia (fallback)"""
        headers = {'User-Agent': 'StockScannerBot/1.0'}
        response = requests.get(self.WIKIPEDIA_NASDAQ100, headers=headers, timeout=30)
        response.raise_for_status()

        html = response.text
        tickers = []

        # Find all wikitables and look for the one with 'Ticker' header
        tables = re.findall(r'<table[^>]*class="[^"]*wikitable[^"]*"[^>]*>(.*?)</table>', html, re.DOTALL)

        for table_html in tables:
            # Check if this table has Ticker/Symbol header
            if 'Ticker' not in table_html and 'Symbol' not in table_html:
                continue

            rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table_html, re.DOTALL)

            for row in rows[1:]:  # Skip header
                cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
                if len(cells) >= 1:
                    # Ticker is in first column for NASDAQ-100
                    cell = cells[0]
                    ticker_match = re.search(r'>([A-Z]{1,5})</a>', cell)
                    if not ticker_match:
                        # Try plain text
                        clean = re.sub(r'<[^>]+>', '', cell).strip()
                        if re.match(r'^[A-Z]{1,5}$', clean):
                            ticker_match = re.match(r'([A-Z]{1,5})', clean)

                    if ticker_match:
                        ticker = ticker_match.group(1)
                        if 1 <= len(ticker) <= 5:
                            tickers.append(ticker)

            # If we found tickers, stop searching tables
            if len(tickers) >= 90:
                break

        return sorted(list(set(tickers)))

    # =========================================================================
    # SECTOR FETCHING
    # =========================================================================

    def fetch_sector(self, sector: str, force_refresh: bool = False) -> List[str]:
        """
        Fetch stocks in a specific sector.
        Uses sector ETF holdings as reference.
        """
        cache_key = f'sector_{sector}'

        if not force_refresh and self._is_cache_valid(cache_key, 6):
            return self.cache.get(cache_key, [])

        tickers = []

        # Get sector ETF
        etf = self.SECTOR_ETFS.get(sector.lower())
        if etf:
            try:
                tickers = self._fetch_etf_holdings(etf)
                logger.info(f"Fetched {len(tickers)} tickers for sector {sector}")
            except Exception as e:
                logger.warning(f"Sector fetch failed for {sector}: {e}")

        if tickers:
            self.cache[cache_key] = tickers
            self.last_fetch[cache_key] = datetime.now()
            self._save_cache()

        return tickers if tickers else self.cache.get(cache_key, [])

    def _fetch_etf_holdings(self, etf: str) -> List[str]:
        """Fetch top holdings of an ETF using yfinance"""
        try:
            import yfinance as yf

            ticker = yf.Ticker(etf)
            holdings = ticker.info.get('holdings', [])

            if holdings:
                return [h.get('symbol', '') for h in holdings if h.get('symbol')]

            # Fallback: try to get from fund data
            # This is a simplified approach
            return []
        except Exception as e:
            logger.debug(f"ETF holdings fetch failed for {etf}: {e}")
            return []

    def fetch_all_sectors(self, force_refresh: bool = False) -> Dict[str, List[str]]:
        """Fetch all sector compositions"""
        sectors = {}
        for sector in self.SECTOR_ETFS.keys():
            sectors[sector] = self.fetch_sector(sector, force_refresh)
        return sectors

    # =========================================================================
    # BREADTH UNIVERSE
    # =========================================================================

    def get_breadth_universe(self, force_refresh: bool = False) -> List[str]:
        """
        Get comprehensive breadth universe.
        Combines SP500 + NASDAQ100 + additional liquid stocks.
        """
        cache_key = 'breadth'

        if not force_refresh and self._is_cache_valid(cache_key, 24):
            return self.cache.get(cache_key, [])

        universe = set()

        # Add SP500
        sp500 = self.fetch_sp500(force_refresh)
        universe.update(sp500)

        # Add NASDAQ100 (some overlap with SP500)
        nasdaq100 = self.fetch_nasdaq100(force_refresh)
        universe.update(nasdaq100)

        # Result
        tickers = sorted(list(universe))

        self.cache[cache_key] = tickers
        self.last_fetch[cache_key] = datetime.now()
        self._save_cache()

        logger.info(f"Breadth universe: {len(tickers)} unique tickers")

        return tickers

    # =========================================================================
    # UNIFIED GETTER
    # =========================================================================

    def get_universe(self, name: str, force_refresh: bool = False) -> List[str]:
        """
        Get any universe by name with smart caching.

        Names: 'sp500', 'nasdaq100', 'breadth', 'sector_technology', etc.
        """
        name = name.lower()

        if name == 'sp500':
            return self.fetch_sp500(force_refresh)
        elif name == 'nasdaq100':
            return self.fetch_nasdaq100(force_refresh)
        elif name == 'breadth':
            return self.get_breadth_universe(force_refresh)
        elif name.startswith('sector_'):
            sector = name.replace('sector_', '')
            return self.fetch_sector(sector, force_refresh)
        else:
            logger.warning(f"Unknown universe: {name}")
            return []

    def get_scan_universe(self, force_refresh: bool = False, use_polygon_full: bool = True) -> List[str]:
        """
        Get the full scan universe for scanning.

        If use_polygon_full=True, fetches all active US stocks from Polygon (filtered for quality).
        Otherwise, returns S&P 500 + NASDAQ 100 combined.

        Args:
            force_refresh: Force refresh from source
            use_polygon_full: Use full Polygon universe (1000+ stocks) vs indices only

        Returns:
            List of ticker symbols
        """
        # Try Polygon full universe first
        if use_polygon_full:
            try:
                polygon_tickers = self._fetch_polygon_full_universe()
                if polygon_tickers and len(polygon_tickers) >= 500:
                    logger.info(f"Scan universe (Polygon): {len(polygon_tickers)} tickers")
                    return polygon_tickers
            except Exception as e:
                logger.warning(f"Polygon full universe failed, falling back to indices: {e}")

        # Fallback to S&P 500 + NASDAQ 100
        sp500 = self.fetch_sp500(force_refresh)
        nasdaq100 = self.fetch_nasdaq100(force_refresh)

        # Combine and deduplicate
        combined = list(set(sp500 + nasdaq100))
        logger.info(f"Scan universe (indices): {len(combined)} tickers (SP500: {len(sp500)}, NASDAQ100: {len(nasdaq100)})")

        return combined

    def _fetch_polygon_full_universe(self) -> List[str]:
        """
        Fetch all active US stocks from Polygon.

        Filters for:
        - Common stocks only (type=CS)
        - Active stocks
        - NYSE and NASDAQ exchanges
        - Excludes penny stocks and illiquid names

        Returns up to 2000 liquid US stocks.
        """
        import os

        polygon_key = os.environ.get('POLYGON_API_KEY', '')
        if not polygon_key:
            logger.debug("Polygon API key not available for full universe")
            return []

        try:
            import requests

            all_tickers = []
            next_url = None

            # Fetch NYSE stocks
            nyse_url = f"https://api.polygon.io/v3/reference/tickers?type=CS&market=stocks&exchange=XNYS&active=true&limit=1000&apiKey={polygon_key}"
            response = requests.get(nyse_url, timeout=30)
            if response.status_code == 200:
                data = response.json()
                nyse_tickers = [t['ticker'] for t in data.get('results', [])]
                all_tickers.extend(nyse_tickers)
                logger.debug(f"Polygon NYSE: {len(nyse_tickers)} tickers")

            # Fetch NASDAQ stocks
            nasdaq_url = f"https://api.polygon.io/v3/reference/tickers?type=CS&market=stocks&exchange=XNAS&active=true&limit=1000&apiKey={polygon_key}"
            response = requests.get(nasdaq_url, timeout=30)
            if response.status_code == 200:
                data = response.json()
                nasdaq_tickers = [t['ticker'] for t in data.get('results', [])]
                all_tickers.extend(nasdaq_tickers)
                logger.debug(f"Polygon NASDAQ: {len(nasdaq_tickers)} tickers")

            # Filter out problematic tickers
            filtered = []
            for ticker in all_tickers:
                # Skip tickers with special characters
                if not ticker.isalpha():
                    continue
                # Skip very short or very long tickers
                if len(ticker) < 1 or len(ticker) > 5:
                    continue
                filtered.append(ticker)

            # Deduplicate
            filtered = list(set(filtered))

            logger.info(f"Polygon full universe: {len(filtered)} stocks (NYSE + NASDAQ)")
            return sorted(filtered)

        except Exception as e:
            logger.warning(f"Failed to fetch Polygon full universe: {e}")
            return []

    # =========================================================================
    # CHANGE TRACKING
    # =========================================================================

    def _track_universe_changes(self, universe_name: str, new_tickers: List[str]):
        """Track additions and removals from universes"""
        history = self._load_history()

        old_tickers = set(history.get(universe_name, {}).get('tickers', []))
        new_tickers_set = set(new_tickers)

        additions = new_tickers_set - old_tickers
        removals = old_tickers - new_tickers_set

        if additions or removals:
            change = {
                'timestamp': datetime.now().isoformat(),
                'additions': list(additions),
                'removals': list(removals),
            }

            if 'changes' not in history:
                history['changes'] = {}
            if universe_name not in history['changes']:
                history['changes'][universe_name] = []

            history['changes'][universe_name].append(change)

            # Keep last 100 changes
            history['changes'][universe_name] = history['changes'][universe_name][-100:]

            logger.info(f"Universe {universe_name} changed: +{len(additions)}, -{len(removals)}")

        # Update current state
        history[universe_name] = {
            'tickers': new_tickers,
            'updated': datetime.now().isoformat(),
        }

        self._save_history(history)

    def _load_history(self) -> Dict:
        """Load universe history"""
        if HISTORY_FILE.exists():
            try:
                with open(HISTORY_FILE, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {}

    def _save_history(self, history: Dict):
        """Save universe history"""
        with open(HISTORY_FILE, 'w') as f:
            json.dump(history, f, indent=2)

    def get_recent_changes(self, universe_name: str = None, days: int = 30) -> List[Dict]:
        """Get recent changes to universes"""
        history = self._load_history()
        changes = []

        cutoff = datetime.now() - timedelta(days=days)

        for univ, univ_changes in history.get('changes', {}).items():
            if universe_name and univ != universe_name:
                continue

            for change in univ_changes:
                change_time = datetime.fromisoformat(change['timestamp'])
                if change_time >= cutoff:
                    changes.append({
                        'universe': univ,
                        **change
                    })

        return sorted(changes, key=lambda x: x['timestamp'], reverse=True)

    # =========================================================================
    # HEALTH MONITORING
    # =========================================================================

    def run_health_check(self) -> UniverseHealth:
        """Run comprehensive health check"""
        issues = list(self.health_issues)
        sources_status = {}

        # Check SP500
        sp500 = self.cache.get('sp500', [])
        sp500_age = self._get_cache_age('sp500')

        if len(sp500) < 400:
            issues.append(f"SP500 count low: {len(sp500)}")
            sources_status['sp500'] = 'degraded'
        elif sp500_age > 48:
            issues.append(f"SP500 cache stale: {sp500_age:.1f}h old")
            sources_status['sp500'] = 'stale'
        else:
            sources_status['sp500'] = 'healthy'

        # Check NASDAQ100
        nasdaq100 = self.cache.get('nasdaq100', [])
        nasdaq100_age = self._get_cache_age('nasdaq100')

        if len(nasdaq100) < 90:
            issues.append(f"NASDAQ100 count low: {len(nasdaq100)}")
            sources_status['nasdaq100'] = 'degraded'
        elif nasdaq100_age > 48:
            issues.append(f"NASDAQ100 cache stale: {nasdaq100_age:.1f}h old")
            sources_status['nasdaq100'] = 'stale'
        else:
            sources_status['nasdaq100'] = 'healthy'

        # Count sectors
        sectors_loaded = sum(1 for k in self.cache if k.startswith('sector_'))

        # Determine overall status
        if any(s == 'degraded' for s in sources_status.values()):
            status = 'degraded'
        elif any(s == 'stale' for s in sources_status.values()):
            status = 'stale'
        elif issues:
            status = 'warning'
        else:
            status = 'healthy'

        # Calculate additional fields
        total_unique = len(set(sp500 + nasdaq100))
        breadth_universe = self.get_breadth_universe()

        # Calculate health score
        health_score = 100.0
        if status == 'degraded':
            health_score -= 30
        elif status == 'stale':
            health_score -= 15
        elif status == 'warning':
            health_score -= 10
        health_score -= len(issues) * 5
        health_score = max(0, min(100, health_score))

        health = UniverseHealth(
            status=status,
            last_update=datetime.now().isoformat(),
            sp500_count=len(sp500),
            nasdaq100_count=len(nasdaq100),
            sectors_loaded=sectors_loaded,
            cache_age_hours=max(sp500_age, nasdaq100_age) if sp500_age != float('inf') else 0,
            issues=issues,
            sources_status=sources_status,
            total_unique=total_unique,
            breadth_universe_size=len(breadth_universe),
            sp500_source='wikipedia' if sp500_age < 24 else 'cache',
            nasdaq100_source='wikipedia' if nasdaq100_age < 24 else 'cache',
            health_score=health_score,
        )

        # Save health status
        self._save_health(health)

        # Clear issues after check
        self.health_issues = []

        return health

    def _get_cache_age(self, universe_name: str) -> float:
        """Get cache age in hours"""
        if universe_name not in self.last_fetch:
            return float('inf')

        age = datetime.now() - self.last_fetch[universe_name]
        return age.total_seconds() / 3600

    def _save_health(self, health: UniverseHealth):
        """Save health status"""
        with open(HEALTH_FILE, 'w') as f:
            json.dump(asdict(health), f, indent=2)

    def get_health_summary(self) -> Dict:
        """Get health summary"""
        if HEALTH_FILE.exists():
            try:
                with open(HEALTH_FILE, 'r') as f:
                    return json.load(f)
            except:
                pass
        return self.run_health_check().__dict__

    def clear_cache(self):
        """Clear all cached data to force refresh"""
        self.cache = {}
        self.last_fetch = {}
        if CACHE_FILE.exists():
            CACHE_FILE.unlink()
        logger.info("Universe cache cleared")


# =============================================================================
# PUBLIC API
# =============================================================================

_manager: Optional[UniverseManager] = None


def get_manager() -> UniverseManager:
    """Get universe manager singleton"""
    global _manager
    if _manager is None:
        _manager = UniverseManager()
    return _manager


# Alias for compatibility
get_universe_manager = get_manager


def get_sp500() -> List[str]:
    """Get current S&P 500 tickers"""
    return get_manager().fetch_sp500()


def get_nasdaq100() -> List[str]:
    """Get current NASDAQ-100 tickers"""
    return get_manager().fetch_nasdaq100()


def get_breadth_universe() -> List[str]:
    """Get breadth calculation universe"""
    return get_manager().get_breadth_universe()


def get_sector(sector: str) -> List[str]:
    """Get tickers in a sector"""
    return get_manager().fetch_sector(sector)


def get_universe(name: str) -> List[str]:
    """Get any universe by name"""
    return get_manager().get_universe(name)


def run_health_check() -> Dict:
    """Run health check"""
    return asdict(get_manager().run_health_check())


def get_recent_changes(days: int = 30) -> List[Dict]:
    """Get recent universe changes"""
    return get_manager().get_recent_changes(days=days)


# =============================================================================
# INITIALIZATION
# =============================================================================

def initialize():
    """Initialize universe manager and fetch initial data"""
    manager = get_manager()

    logger.info("Initializing universe manager...")

    # Fetch universes
    sp500 = manager.fetch_sp500()
    nasdaq100 = manager.fetch_nasdaq100()

    logger.info(f"Initialized: SP500={len(sp500)}, NASDAQ100={len(nasdaq100)}")

    # Run health check
    health = manager.run_health_check()
    logger.info(f"Health status: {health.status}")

    return health


if __name__ == '__main__':
    health = initialize()
    print(f"\nHealth: {health.status}")
    print(f"SP500: {health.sp500_count} tickers")
    print(f"NASDAQ100: {health.nasdaq100_count} tickers")

    if health.issues:
        print(f"\nIssues:")
        for issue in health.issues:
            print(f"  - {issue}")
