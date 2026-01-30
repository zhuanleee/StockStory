"""
Ecosystem Intelligence - Supply Chain Analysis

Provides theme-based supply chain mapping and analysis.
"""

from typing import Dict, List, Optional
from src.core.story_scoring import SUPPLY_CHAIN_MAP, THEME_NAME_TO_SUPPLY_CHAIN


def get_supply_chain_themes() -> List[Dict]:
    """
    Get list of themes with supply chain data.

    Returns list of themes that have defined supply chains.
    """
    themes = []

    for theme_id, chain in SUPPLY_CHAIN_MAP.items():
        # Count total stocks in supply chain
        total_stocks = sum(len(stocks) for stocks in chain.values())

        # Format theme name
        theme_name = theme_id.replace('_', ' ').title()

        themes.append({
            'theme_id': theme_id,
            'theme_name': theme_name,
            'stock_count': total_stocks,
            'has_leaders': len(chain.get('leaders', [])) > 0,
            'has_suppliers': len(chain.get('suppliers', [])) > 0,
            'has_beneficiaries': len(chain.get('beneficiaries', [])) > 0,
        })

    # Sort by stock count
    themes.sort(key=lambda x: -x['stock_count'])

    return themes


def get_theme_supply_chain(theme_id: str) -> Dict:
    """
    Get supply chain breakdown for a specific theme.

    Args:
        theme_id: Theme identifier (e.g., 'ai_infrastructure', 'nuclear_energy')

    Returns:
        Supply chain data with leaders, suppliers, equipment, etc.
    """
    # Normalize theme_id
    theme_id_normalized = theme_id.lower().replace(' ', '_')

    # Check if theme exists
    if theme_id_normalized not in SUPPLY_CHAIN_MAP:
        # Try reverse lookup from theme name
        matching_id = THEME_NAME_TO_SUPPLY_CHAIN.get(theme_id.lower())
        if matching_id:
            theme_id_normalized = matching_id
        else:
            return {
                'ok': False,
                'error': f'Theme not found: {theme_id}',
                'available_themes': list(SUPPLY_CHAIN_MAP.keys())
            }

    chain = SUPPLY_CHAIN_MAP[theme_id_normalized]

    # Format response
    result = {
        'theme_id': theme_id_normalized,
        'theme_name': theme_id_normalized.replace('_', ' ').title(),
        'leaders': [
            {'ticker': t, 'role': 'leader', 'description': 'Theme leaders that move first'}
            for t in chain.get('leaders', [])
        ],
        'suppliers': [
            {'ticker': t, 'role': 'supplier', 'description': 'Equipment/chip suppliers'}
            for t in chain.get('suppliers', [])
        ],
        'equipment': [
            {'ticker': t, 'role': 'equipment', 'description': 'Infrastructure providers'}
            for t in chain.get('equipment', [])
        ],
        'materials': [
            {'ticker': t, 'role': 'material', 'description': 'Raw materials'}
            for t in chain.get('materials', [])
        ],
        'beneficiaries': [
            {'ticker': t, 'role': 'beneficiary', 'description': 'Software/service beneficiaries'}
            for t in chain.get('beneficiaries', [])
        ],
        'infrastructure': [
            {'ticker': t, 'role': 'infrastructure', 'description': 'Supporting infrastructure'}
            for t in chain.get('infrastructure', [])
        ],
    }

    # Add total count
    result['total_stocks'] = sum(
        len(result[key])
        for key in ['leaders', 'suppliers', 'equipment', 'materials', 'beneficiaries', 'infrastructure']
    )

    return result


def ai_discover_supply_chain() -> Dict:
    """
    AI-powered supply chain discovery.

    This is a placeholder for future AI-based supply chain discovery.
    Currently returns the existing manually-defined supply chains.
    """
    return {
        'status': 'manual_only',
        'message': 'AI discovery not yet implemented. Using manually-defined supply chains.',
        'available_themes': get_supply_chain_themes(),
        'note': 'Future versions will use AI to discover new supply chain relationships'
    }
