"""
Ecosystem Intelligence - Supply Chain Analysis

Provides theme-based supply chain mapping and analysis.
"""

from typing import Dict, List, Optional
from datetime import datetime
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


def ai_discover_supply_chain(ticker: str = None, theme: str = None) -> Dict:
    """
    AI-powered supply chain discovery using xAI/DeepSeek.

    Analyzes company relationships, filings, and news to discover
    supply chain connections beyond manual maps.

    Args:
        ticker: Optional ticker to analyze supply chain for
        theme: Optional theme to discover supply chain for

    Returns:
        Dict with discovered relationships and confidence scores
    """
    import logging
    logger = logging.getLogger(__name__)

    try:
        from src.services.ai_service import get_ai_service

        ai_service = get_ai_service()
        if not ai_service:
            return {
                'status': 'unavailable',
                'message': 'AI service not configured',
                'available_themes': get_supply_chain_themes()
            }

        # Build analysis prompt
        if ticker:
            prompt = f"""Analyze the supply chain relationships for {ticker}.

Identify:
1. Key suppliers (who provides components/materials to {ticker})
2. Key customers (who buys from {ticker})
3. Competitors in the same space
4. Complementary companies (benefit from {ticker}'s success)

Format response as JSON:
{{
    "suppliers": ["TICKER1", "TICKER2", ...],
    "customers": ["TICKER1", "TICKER2", ...],
    "competitors": ["TICKER1", "TICKER2", ...],
    "complementary": ["TICKER1", "TICKER2", ...],
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation"
}}

Only include publicly traded US companies with clear relationships.
"""
        elif theme:
            prompt = f"""Analyze the supply chain for the {theme} theme/sector.

Identify:
1. Market leaders
2. Key suppliers/enablers
3. Emerging players
4. Infrastructure providers

Format response as JSON:
{{
    "leaders": ["TICKER1", "TICKER2", ...],
    "suppliers": ["TICKER1", "TICKER2", ...],
    "emerging": ["TICKER1", "TICKER2", ...],
    "infrastructure": ["TICKER1", "TICKER2", ...],
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation"
}}

Only include publicly traded US companies.
"""
        else:
            return {
                'status': 'error',
                'message': 'Must provide either ticker or theme parameter'
            }

        # Call AI service
        logger.info(f"AI supply chain discovery for ticker={ticker}, theme={theme}")

        response = ai_service.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=1000
        )

        # Parse JSON response
        import json
        response_text = response.get('content', '{}')

        # Try to extract JSON from response
        try:
            if '```json' in response_text:
                json_start = response_text.index('```json') + 7
                json_end = response_text.index('```', json_start)
                response_text = response_text[json_start:json_end].strip()
            elif '```' in response_text:
                json_start = response_text.index('```') + 3
                json_end = response_text.index('```', json_start)
                response_text = response_text[json_start:json_end].strip()

            discovered = json.loads(response_text)
        except Exception as e:
            logger.error(f"Failed to parse AI response: {e}")
            return {
                'status': 'parse_error',
                'message': f'Failed to parse AI response: {e}',
                'raw_response': response_text[:500]
            }

        return {
            'status': 'success',
            'analysis_type': 'ticker' if ticker else 'theme',
            'ticker': ticker,
            'theme': theme,
            'discovered': discovered,
            'timestamp': datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"AI supply chain discovery failed: {e}")
        return {
            'status': 'error',
            'message': str(e),
            'available_themes': get_supply_chain_themes()
        }
