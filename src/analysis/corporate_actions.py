"""
Corporate Actions Intelligence
==============================
Track spinoffs, mergers, and M&A for alpha generation.

Features:
- Spinoff tracking (parent + child)
- M&A deal monitoring
- Merger arbitrage spread calculation
- Catalyst alerts
"""

import os
import logging
from datetime import datetime
from typing import Dict, List

logger = logging.getLogger(__name__)


class CorporateActionsTracker:
    """
    Track and analyze corporate actions for trading opportunities.

    Spinoff Strategy:
    - Parent often rallies into spinoff (positive catalyst)
    - Spinoff child often has forced selling (index funds can't hold)
    - Creates buying opportunity in quality spinoffs

    M&A Strategy:
    - Calculate deal spread (current price vs offer price)
    - Monitor deal status (pending, approved, failed)
    - Alert on spread changes
    """

    def __init__(self):
        self.polygon_key = os.environ.get('POLYGON_API_KEY', '')

    async def get_upcoming_spinoffs(self, days_ahead: int = 90) -> List[Dict]:
        """
        Get announced spinoffs.

        Returns:
            List of spinoffs with parent, child, dates, and ratios
        """
        if not self.polygon_key:
            return []

        try:
            from src.data.polygon_provider import PolygonProvider

            provider = PolygonProvider()
            try:
                # Get stock splits (spinoffs are a type of split with new ticker)
                splits = await provider.get_stock_splits(limit=100)

                spinoffs = []
                for split in splits:
                    # Spinoffs typically have different tickers or special ratios
                    if split.get('split_type') == 'spinoff' or split.get('is_spinoff'):
                        spinoffs.append({
                            'parent_ticker': split.get('ticker'),
                            'child_ticker': split.get('new_ticker'),
                            'record_date': split.get('record_date'),
                            'ex_date': split.get('execution_date'),
                            'ratio': split.get('ratio_str'),
                            'status': 'announced'
                        })

                return spinoffs
            finally:
                await provider.close()
        except Exception as e:
            logger.error(f"Error fetching spinoffs: {e}")
            return []

    async def get_pending_mergers(self) -> List[Dict]:
        """
        Get pending M&A deals.

        Note: Polygon free tier may not have full M&A data.
        This can be enhanced with SEC EDGAR integration.
        """
        # For high-standard M&A tracking, we'd integrate:
        # 1. SEC EDGAR - DEFM14A (merger proxy), S-4 (registration)
        # 2. News APIs for deal announcements
        # 3. Manual deal database

        # Placeholder for Polygon corporate actions
        mergers = []

        try:
            from src.data.polygon_provider import PolygonProvider

            provider = PolygonProvider()
            try:
                # Check for merger-related corporate actions
                # This would need Polygon's corporate actions endpoint
                pass
            finally:
                await provider.close()
        except Exception as e:
            logger.error(f"Error fetching mergers: {e}")

        return mergers

    def calculate_merger_spread(
        self,
        current_price: float,
        deal_price: float,
        deal_type: str = 'cash'
    ) -> Dict:
        """
        Calculate merger arbitrage spread.

        Args:
            current_price: Current trading price of target
            deal_price: Announced deal price
            deal_type: 'cash', 'stock', or 'mixed'

        Returns:
            Spread analysis with risk/reward
        """
        if deal_type == 'cash':
            spread = deal_price - current_price
            spread_pct = (spread / current_price) * 100

            return {
                'spread': round(spread, 2),
                'spread_pct': round(spread_pct, 2),
                'upside': round(spread_pct, 2),
                'downside_estimate': round(spread_pct * -3, 2),  # If deal fails, ~3x downside
                'risk_reward': round(spread_pct / (spread_pct * 3), 2) if spread_pct > 0 else 0,
                'signal': 'attractive' if spread_pct > 5 else 'fair' if spread_pct > 2 else 'tight'
            }
        else:
            # Stock deals need acquirer price tracking
            return {
                'spread': 0,
                'spread_pct': 0,
                'note': 'Stock deal - spread depends on acquirer price'
            }

    def score_spinoff_opportunity(self, spinoff: Dict, days_to_ex: int) -> Dict:
        """
        Score a spinoff opportunity.

        Factors:
        - Time to ex-date (closer = more catalyst)
        - Parent quality (is it S&P 500?)
        - Child expected forced selling
        """
        score = 50  # Base score
        signals = []

        # Time factor
        if days_to_ex <= 7:
            score += 20
            signals.append("Ex-date imminent - high catalyst")
        elif days_to_ex <= 30:
            score += 10
            signals.append("Ex-date approaching")

        # This can be enhanced with:
        # - Index membership check (S&P 500 spinoffs have more forced selling)
        # - Historical spinoff performance
        # - Sector analysis

        return {
            'score': score,
            'signals': signals,
            'recommendation': 'watch_parent' if days_to_ex > 14 else 'watch_both'
        }


def get_spinoff_catalyst_score(ticker: str) -> int:
    """
    Get catalyst score boost for spinoff involvement.

    Used by story_scorer to boost stocks involved in spinoffs.
    """
    # This would check if ticker is involved in any spinoff
    # Returns score boost (0-20)
    return 0  # Placeholder


def get_merger_catalyst_score(ticker: str) -> int:
    """
    Get catalyst score boost for M&A involvement.

    Target in announced deal: +15-25 points
    Acquirer in deal: +5-10 points (often negative short-term)
    """
    # This would check if ticker is M&A target or acquirer
    return 0  # Placeholder


# =============================================================================
# TELEGRAM COMMAND HANDLERS
# =============================================================================

def format_spinoffs_message(spinoffs: List[Dict]) -> str:
    """Format spinoffs for Telegram."""
    if not spinoffs:
        return "📊 *SPINOFFS*\n\nNo upcoming spinoffs found."

    msg = "📊 *UPCOMING SPINOFFS*\n\n"

    for s in spinoffs[:10]:
        parent = s.get('parent_ticker', '?')
        child = s.get('child_ticker', 'TBD')
        ex_date = s.get('ex_date', 'TBD')
        ratio = s.get('ratio', '?')

        msg += f"🔄 *{parent}* → {child}\n"
        msg += f"   Ex-date: {ex_date}\n"
        msg += f"   Ratio: {ratio}\n\n"

    msg += "_Spinoffs often outperform in year 1_"
    return msg


def format_mergers_message(mergers: List[Dict]) -> str:
    """Format M&A deals for Telegram."""
    if not mergers:
        return "🤝 *M&A DEALS*\n\nNo pending deals tracked.\n\n_Add deals manually or integrate SEC EDGAR_"

    msg = "🤝 *PENDING M&A DEALS*\n\n"

    for m in mergers[:10]:
        target = m.get('target', '?')
        acquirer = m.get('acquirer', '?')
        deal_price = m.get('deal_price', 0)
        current = m.get('current_price', 0)
        spread_pct = ((deal_price - current) / current * 100) if current > 0 else 0

        emoji = "🟢" if spread_pct > 5 else "🟡" if spread_pct > 2 else "⚪"

        msg += f"{emoji} *{target}* ← {acquirer}\n"
        msg += f"   Deal: ${deal_price:.2f} | Current: ${current:.2f}\n"
        msg += f"   Spread: {spread_pct:.1f}%\n\n"

    msg += "_Wider spread = more upside but more risk_"
    return msg


# =============================================================================
# SEC EDGAR INTEGRATION (for high-standard M&A tracking)
# =============================================================================

async def fetch_sec_merger_filings(ticker: str) -> List[Dict]:
    """
    Fetch merger-related SEC filings.

    Key filings:
    - DEFM14A: Definitive merger proxy
    - S-4: Registration for stock deals
    - 8-K: Material events (deal announcements)
    """
    try:
        import aiohttp

        url = f"https://efts.sec.gov/LATEST/search-index?q={ticker}&forms=DEFM14A,S-4"

        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('hits', {}).get('hits', [])
        return []
    except Exception as e:
        logger.error(f"SEC filing fetch error: {e}")
        return []


# =============================================================================
# MANUAL DEAL TRACKING (for production use)
# =============================================================================

class DealTracker:
    """
    Manual deal database for high-standard M&A tracking.

    In production, you'd want:
    1. Database of active deals
    2. Daily price updates
    3. Status monitoring (regulatory approval, votes)
    4. Alerts on spread changes
    """

    def __init__(self, deals_file: str = "active_deals.json"):
        self.deals_file = deals_file
        self.deals = self._load_deals()

    def _load_deals(self) -> List[Dict]:
        """Load deals from file."""
        import json
        from pathlib import Path

        path = Path(self.deals_file)
        if path.exists():
            try:
                return json.loads(path.read_text())
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load deals from {self.deals_file}: {e}")
                return []
        return []

    def _save_deals(self):
        """Save deals to file."""
        import json
        from pathlib import Path

        Path(self.deals_file).write_text(json.dumps(self.deals, indent=2))

    def add_deal(
        self,
        target: str,
        acquirer: str,
        deal_price: float,
        deal_type: str = 'cash',
        expected_close: str = None,
        notes: str = ''
    ) -> Dict:
        """Add a new M&A deal to track."""
        deal = {
            'id': f"{target}_{acquirer}_{datetime.now().strftime('%Y%m%d')}",
            'target': target.upper(),
            'acquirer': acquirer.upper(),
            'deal_price': deal_price,
            'deal_type': deal_type,
            'expected_close': expected_close,
            'status': 'pending',
            'announced_date': datetime.now().isoformat(),
            'notes': notes
        }
        self.deals.append(deal)
        self._save_deals()
        return deal

    def update_deal_status(self, deal_id: str, status: str):
        """Update deal status (pending, approved, failed, completed)."""
        for deal in self.deals:
            if deal['id'] == deal_id:
                deal['status'] = status
                deal['updated'] = datetime.now().isoformat()
                self._save_deals()
                return True
        return False

    def get_active_deals(self) -> List[Dict]:
        """Get all pending/approved deals."""
        return [d for d in self.deals if d['status'] in ('pending', 'approved')]

    def calculate_all_spreads(self, price_fetcher) -> List[Dict]:
        """Calculate spreads for all active deals."""
        results = []
        for deal in self.get_active_deals():
            current_price = price_fetcher(deal['target'])
            if current_price:
                tracker = CorporateActionsTracker()
                spread = tracker.calculate_merger_spread(
                    current_price,
                    deal['deal_price'],
                    deal['deal_type']
                )
                results.append({
                    **deal,
                    'current_price': current_price,
                    **spread
                })
        return results
