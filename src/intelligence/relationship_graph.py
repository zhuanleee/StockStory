"""
Stock Relationship Graph - Sympathy Play Detection
==================================================
Identify related stocks that move together for basket trading strategies.

Uses:
- Supply chain relationships (from theme_discovery)
- Sector relationships
- Correlation analysis (future)

Usage:
    from src.intelligence.relationship_graph import get_related_stocks

    # Find stocks related to NVDA
    related = get_related_stocks('NVDA')
    # Returns: {'leaders': [...], 'suppliers': [...], 'beneficiaries': [...]}

    # Get all stocks in a theme
    theme_stocks = get_theme_basket('ai_infrastructure')
"""

import logging
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class RelatedStock:
    """A stock related to the target."""
    ticker: str
    relationship: str  # co-leader, supplier, beneficiary, competitor, customer
    theme: str  # Common theme
    strength: float  # 0-1, relationship strength


class RelationshipGraph:
    """
    Stock relationship graph for sympathy play detection.

    Leverages supply chain maps and theme data.
    """

    def __init__(self):
        self._load_supply_chains()

    def _load_supply_chains(self):
        """Load supply chain relationships."""
        try:
            from src.core.story_scoring import SUPPLY_CHAIN_MAP, THEME_NAME_TO_SUPPLY_CHAIN
            self.supply_chains = SUPPLY_CHAIN_MAP
            self.theme_map = THEME_NAME_TO_SUPPLY_CHAIN
        except ImportError:
            logger.warning("Could not import supply chain maps")
            self.supply_chains = {}
            self.theme_map = {}

    def get_related_stocks(self, ticker: str, max_results: int = 20) -> Dict[str, List[RelatedStock]]:
        """
        Find stocks related to target ticker.

        Args:
            ticker: Target ticker
            max_results: Maximum related stocks to return

        Returns:
            Dict with relationship categories
        """
        related = {
            'co_leaders': [],
            'suppliers': [],
            'equipment': [],
            'materials': [],
            'beneficiaries': [],
            'infrastructure': []
        }

        # Find ticker in supply chains
        ticker_themes = []

        for theme_id, chain in self.supply_chains.items():
            # Check each role
            for role, tickers in chain.items():
                if ticker in tickers:
                    ticker_themes.append((theme_id, role))

        # For each theme the ticker is in, get related stocks
        for theme_id, ticker_role in ticker_themes:
            chain = self.supply_chains[theme_id]

            for role, tickers in chain.items():
                for related_ticker in tickers:
                    if related_ticker == ticker:
                        continue  # Skip self

                    # Determine relationship type
                    if role == ticker_role:
                        category = 'co_leaders'
                        strength = 0.9  # Same role = strong relationship
                    elif role == 'suppliers':
                        category = 'suppliers'
                        strength = 0.7
                    elif role == 'equipment':
                        category = 'equipment'
                        strength = 0.6
                    elif role == 'materials':
                        category = 'materials'
                        strength = 0.5
                    elif role == 'beneficiaries':
                        category = 'beneficiaries'
                        strength = 0.7
                    elif role == 'infrastructure':
                        category = 'infrastructure'
                        strength = 0.5
                    else:
                        category = 'co_leaders'
                        strength = 0.5

                    # Create RelatedStock
                    related_stock = RelatedStock(
                        ticker=related_ticker,
                        relationship=role,
                        theme=theme_id,
                        strength=strength
                    )

                    # Add to appropriate category
                    if category in related:
                        # Avoid duplicates
                        existing_tickers = [s.ticker for s in related[category]]
                        if related_ticker not in existing_tickers:
                            related[category].append(related_stock)

        # Sort each category by strength
        for category in related:
            related[category] = sorted(related[category], key=lambda x: x.strength, reverse=True)[:max_results]

        return related

    def get_theme_basket(self, theme_id: str) -> Dict[str, List[str]]:
        """
        Get all stocks in a theme basket.

        Args:
            theme_id: Theme identifier (e.g., 'ai_infrastructure')

        Returns:
            Dict with stocks by role
        """
        if theme_id not in self.supply_chains:
            return {}

        return self.supply_chains[theme_id]

    def find_sympathy_plays(self, leader_ticker: str) -> List[Dict]:
        """
        Find sympathy plays for a leading stock.

        When leader moves, these stocks likely to follow.

        Args:
            leader_ticker: Leading stock ticker

        Returns:
            List of potential sympathy plays ranked by strength
        """
        related = self.get_related_stocks(leader_ticker)

        # Sympathy plays are suppliers and beneficiaries
        sympathy_candidates = []

        # Suppliers follow leaders (lag by days/weeks)
        for stock in related['suppliers']:
            sympathy_candidates.append({
                'ticker': stock.ticker,
                'type': 'supplier',
                'theme': stock.theme,
                'strength': stock.strength,
                'lag_estimate': '1-2 weeks'
            })

        # Beneficiaries follow leaders
        for stock in related['beneficiaries']:
            sympathy_candidates.append({
                'ticker': stock.ticker,
                'type': 'beneficiary',
                'theme': stock.theme,
                'strength': stock.strength,
                'lag_estimate': '1-3 weeks'
            })

        # Equipment providers follow
        for stock in related['equipment']:
            sympathy_candidates.append({
                'ticker': stock.ticker,
                'type': 'equipment',
                'theme': stock.theme,
                'strength': stock.strength,
                'lag_estimate': '2-4 weeks'
            })

        # Sort by strength
        sympathy_candidates.sort(key=lambda x: x['strength'], reverse=True)

        return sympathy_candidates[:10]  # Top 10

    def get_basket_for_tickers(self, tickers: List[str]) -> Set[str]:
        """
        Get complete basket of related stocks for given tickers.

        Useful for theme basket trading.

        Args:
            tickers: List of core tickers

        Returns:
            Set of all related tickers
        """
        basket = set(tickers)

        for ticker in tickers:
            related = self.get_related_stocks(ticker, max_results=50)

            # Add co-leaders (same theme, same role)
            for stock in related['co_leaders']:
                basket.add(stock.ticker)

        return basket


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

_relationship_graph = None


def get_relationship_graph() -> RelationshipGraph:
    """Get or create singleton relationship graph."""
    global _relationship_graph
    if _relationship_graph is None:
        _relationship_graph = RelationshipGraph()
    return _relationship_graph


def get_related_stocks(ticker: str, max_results: int = 20) -> Dict:
    """Get related stocks for ticker."""
    graph = get_relationship_graph()
    related = graph.get_related_stocks(ticker, max_results)

    # Convert to dict format
    return {
        category: [asdict(stock) for stock in stocks]
        for category, stocks in related.items()
    }


def find_sympathy_plays(leader_ticker: str) -> List[Dict]:
    """Find sympathy plays for a leader stock."""
    graph = get_relationship_graph()
    return graph.find_sympathy_plays(leader_ticker)


def get_theme_basket(theme_id: str) -> Dict[str, List[str]]:
    """Get all stocks in a theme basket."""
    graph = get_relationship_graph()
    return graph.get_theme_basket(theme_id)


# =============================================================================
# TELEGRAM FORMATTING
# =============================================================================

def format_related_stocks_message(ticker: str, related_data: Dict) -> str:
    """Format related stocks for Telegram."""
    msg = f"🔗 *RELATED STOCKS: ${ticker}*\n"
    msg += f"_Sympathy plays and basket trades_\n\n"

    # Co-leaders
    if related_data.get('co_leaders'):
        msg += f"👥 *CO-LEADERS* (same theme/role):\n"
        for stock in related_data['co_leaders'][:5]:
            msg += f"  • ${stock['ticker']} ({stock['theme']})\n"
        msg += "\n"

    # Suppliers
    if related_data.get('suppliers'):
        msg += f"🏭 *SUPPLIERS* (equipment/chips):\n"
        for stock in related_data['suppliers'][:5]:
            msg += f"  • ${stock['ticker']} ({stock['theme']})\n"
        msg += "\n"

    # Beneficiaries
    if related_data.get('beneficiaries'):
        msg += f"📈 *BENEFICIARIES* (software/services):\n"
        for stock in related_data['beneficiaries'][:5]:
            msg += f"  • ${stock['ticker']} ({stock['theme']})\n"
        msg += "\n"

    msg += f"💡 *Usage:*\n"
    msg += f"• Sympathy plays when ${ticker} moves\n"
    msg += f"• Basket trading opportunities\n"
    msg += f"• Supply chain exposure\n"

    return msg


def format_sympathy_plays_message(leader: str, plays: List[Dict]) -> str:
    """Format sympathy plays for Telegram."""
    msg = f"🎯 *SYMPATHY PLAYS: ${leader}*\n"
    msg += f"_Stocks that follow when ${leader} moves_\n\n"

    if not plays:
        msg += "No sympathy plays found.\n"
        return msg

    for i, play in enumerate(plays[:5], 1):
        ticker = play['ticker']
        play_type = play['type']
        theme = play['theme']
        lag = play['lag_estimate']

        msg += f"{i}. *${ticker}* ({play_type})\n"
        msg += f"   Theme: {theme}\n"
        msg += f"   Lag: {lag}\n\n"

    msg += f"💡 When ${leader} rallies, watch these for follow-through!\n"

    return msg
