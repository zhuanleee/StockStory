#!/usr/bin/env python3
"""
AI Ecosystem Generator

Automated DeepSeek-powered ecosystem research and generation:
1. Auto-generates ecosystem data for driver stocks via AI
2. Validates and stores relationships in the graph
3. Scheduled refresh for hot stocks and key drivers
4. News-based relationship discovery

Usage:
    from ai_ecosystem_generator import auto_generate_ecosystem, refresh_hot_stocks

    # Generate ecosystem for a driver
    ecosystem = await auto_generate_ecosystem('NVDA')

    # Refresh all hot stocks
    results = refresh_hot_stocks(min_score=80)
"""

import json
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import re

from config import config
from utils import get_logger

logger = get_logger(__name__)

# Import dependencies
try:
    from ai_learning import call_deepseek
except ImportError:
    def call_deepseek(prompt, system_prompt=None, max_tokens=2000):
        logger.error("ai_learning module not available")
        return None


# Key driver stocks to auto-generate ecosystems for
KEY_DRIVERS = {
    'ai_infrastructure': ['NVDA', 'AMD', 'AVGO', 'SMCI'],
    'ai_software': ['MSFT', 'GOOGL', 'META', 'CRM', 'PLTR'],
    'nuclear': ['CEG', 'VST', 'CCJ'],
    'glp1_obesity': ['LLY', 'NVO', 'VKTX'],
    'crypto': ['MSTR', 'COIN', 'MARA'],
    'defense': ['LMT', 'RTX', 'NOC', 'GD'],
    'space': ['RKLB', 'LUNR', 'ASTS'],
    'quantum': ['IONQ', 'RGTI', 'QBTS'],
    'clean_energy': ['FSLR', 'ENPH'],
    'china': ['BABA', 'PDD', 'NIO'],
}

# Flatten to list
ALL_KEY_DRIVERS = [ticker for tickers in KEY_DRIVERS.values() for ticker in tickers]

# Valid US tickers pattern
TICKER_PATTERN = re.compile(r'^[A-Z]{1,5}$')


def validate_ticker(ticker: str) -> bool:
    """Check if ticker is a valid US stock ticker."""
    if not ticker or not TICKER_PATTERN.match(ticker):
        return False

    # Known invalid tickers (private companies, foreign, etc.)
    invalid = {'SK', 'ASX'}  # These are foreign exchanges, not tickers

    return ticker not in invalid


def generate_ecosystem_prompt(ticker: str) -> str:
    """Generate DeepSeek prompt for ecosystem research."""
    return f"""You are a financial analyst. Analyze {ticker}'s business ecosystem.
Return ONLY valid JSON (no markdown, no explanation):

{{
    "ticker": "{ticker}",
    "company_name": "Full company name",
    "themes": ["primary_theme", "secondary_theme"],
    "market_cap_tier": "mega|large|mid|small",
    "suppliers": [
        {{"ticker": "XXX", "name": "Company Name", "relationship": "what they supply", "confidence": 0.9, "sub_theme": "category"}}
    ],
    "customers": [
        {{"ticker": "XXX", "name": "Company Name", "relationship": "what they buy", "confidence": 0.8}}
    ],
    "competitors": [
        {{"ticker": "XXX", "name": "Company Name", "overlap": "where they compete", "confidence": 0.85}}
    ],
    "picks_shovels": [
        {{"ticker": "XXX", "name": "Company Name", "role": "what they enable", "confidence": 0.75}}
    ],
    "infrastructure": [
        {{"ticker": "XXX", "name": "Company Name", "service": "what infrastructure", "confidence": 0.7}}
    ],
    "sub_themes": {{
        "ThemeName": {{
            "description": "What this niche is about",
            "tickers": ["XXX", "YYY"],
            "driver_correlation": 0.85
        }}
    }},
    "key_risks": ["Risk 1", "Risk 2"],
    "catalyst_sensitivity": ["What events move this ecosystem"]
}}

Requirements:
- Only include publicly traded US stocks (NYSE, NASDAQ)
- Do NOT include foreign stocks like SK Hynix (SK) or ASX
- Confidence 0.9+ = direct, verified relationship (in SEC filings)
- Confidence 0.7-0.9 = likely relationship (news, industry knowledge)
- Confidence <0.7 = possible relationship (speculation)
- Sub-themes should be specific niches (e.g., "HBM_Memory" not just "Semiconductors")
- Include 3-8 suppliers, 2-5 customers, 3-6 competitors, 2-5 picks_shovels
"""


def parse_ecosystem_response(response: str) -> Optional[dict]:
    """Parse and validate DeepSeek response."""
    if not response:
        return None

    try:
        # Try to extract JSON from response
        # Sometimes DeepSeek wraps JSON in markdown code blocks
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            response = json_match.group(0)

        data = json.loads(response)

        # Validate required fields
        if 'ticker' not in data:
            logger.warning("Missing ticker in response")
            return None

        return data
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse ecosystem JSON: {e}")
        logger.debug(f"Response was: {response[:500]}...")
        return None


def validate_and_filter_ecosystem(raw: dict) -> dict:
    """Validate DeepSeek response and filter invalid entries."""
    validated = {
        'ticker': raw['ticker'],
        'company_name': raw.get('company_name', ''),
        'themes': raw.get('themes', []),
        'market_cap_tier': raw.get('market_cap_tier', 'unknown'),
        'suppliers': [],
        'customers': [],
        'competitors': [],
        'picks_shovels': [],
        'infrastructure': [],
        'sub_themes': {},
        'key_risks': raw.get('key_risks', []),
        'catalyst_sensitivity': raw.get('catalyst_sensitivity', []),
        'generated_at': datetime.now().isoformat(),
        'source': 'deepseek_auto',
    }

    # Validate suppliers
    for item in raw.get('suppliers', []):
        ticker = item.get('ticker', '').upper()
        if validate_ticker(ticker):
            validated['suppliers'].append({
                'ticker': ticker,
                'name': item.get('name', ''),
                'relationship': item.get('relationship', ''),
                'confidence': min(1.0, max(0.0, float(item.get('confidence', 0.7)))),
                'sub_theme': item.get('sub_theme'),
                'verified_at': datetime.now().isoformat(),
                'source': 'deepseek_auto',
            })

    # Validate customers
    for item in raw.get('customers', []):
        ticker = item.get('ticker', '').upper()
        if validate_ticker(ticker):
            validated['customers'].append({
                'ticker': ticker,
                'name': item.get('name', ''),
                'relationship': item.get('relationship', ''),
                'confidence': min(1.0, max(0.0, float(item.get('confidence', 0.7)))),
                'verified_at': datetime.now().isoformat(),
                'source': 'deepseek_auto',
            })

    # Validate competitors
    for item in raw.get('competitors', []):
        ticker = item.get('ticker', '').upper()
        if validate_ticker(ticker):
            validated['competitors'].append({
                'ticker': ticker,
                'name': item.get('name', ''),
                'overlap': item.get('overlap', ''),
                'confidence': min(1.0, max(0.0, float(item.get('confidence', 0.7)))),
                'verified_at': datetime.now().isoformat(),
                'source': 'deepseek_auto',
            })

    # Validate picks_shovels
    for item in raw.get('picks_shovels', []):
        ticker = item.get('ticker', '').upper()
        if validate_ticker(ticker):
            validated['picks_shovels'].append({
                'ticker': ticker,
                'name': item.get('name', ''),
                'role': item.get('role', ''),
                'confidence': min(1.0, max(0.0, float(item.get('confidence', 0.7)))),
                'verified_at': datetime.now().isoformat(),
                'source': 'deepseek_auto',
            })

    # Validate infrastructure
    for item in raw.get('infrastructure', []):
        ticker = item.get('ticker', '').upper()
        if validate_ticker(ticker):
            validated['infrastructure'].append({
                'ticker': ticker,
                'name': item.get('name', ''),
                'service': item.get('service', ''),
                'confidence': min(1.0, max(0.0, float(item.get('confidence', 0.7)))),
                'verified_at': datetime.now().isoformat(),
                'source': 'deepseek_auto',
            })

    # Validate sub_themes
    for theme_name, theme_data in raw.get('sub_themes', {}).items():
        valid_tickers = [
            t.upper() for t in theme_data.get('tickers', [])
            if validate_ticker(t.upper())
        ]
        if valid_tickers:
            validated['sub_themes'][theme_name] = {
                'description': theme_data.get('description', ''),
                'tickers': valid_tickers,
                'driver_correlation': min(1.0, max(0.0, float(theme_data.get('driver_correlation', 0.7)))),
            }

    return validated


def store_ecosystem_in_graph(ecosystem: dict) -> bool:
    """Store validated ecosystem data in the relationship graph."""
    try:
        from relationship_graph import get_ecosystem_graph

        graph = get_ecosystem_graph()
        ticker = ecosystem['ticker']

        # Add/update main node
        graph.add_node(ticker, {
            'themes': ecosystem.get('themes', []),
            'market_cap_tier': ecosystem.get('market_cap_tier', 'unknown'),
            'company_name': ecosystem.get('company_name', ''),
        })

        # Add supplier edges
        for supplier in ecosystem.get('suppliers', []):
            graph.add_node(supplier['ticker'])
            graph.add_edge(
                ticker,
                supplier['ticker'],
                'supplier',
                strength=supplier['confidence'],
                sub_theme=supplier.get('sub_theme'),
                sources=['deepseek_auto'],
            )

        # Add customer edges
        for customer in ecosystem.get('customers', []):
            graph.add_node(customer['ticker'])
            graph.add_edge(
                ticker,
                customer['ticker'],
                'customer',
                strength=customer['confidence'],
                sources=['deepseek_auto'],
            )

        # Add competitor edges (bidirectional)
        for competitor in ecosystem.get('competitors', []):
            graph.add_node(competitor['ticker'])
            graph.add_edge(
                ticker,
                competitor['ticker'],
                'competitor',
                strength=competitor['confidence'],
                sources=['deepseek_auto'],
            )

        # Add picks_shovels edges
        for item in ecosystem.get('picks_shovels', []):
            graph.add_node(item['ticker'])
            graph.add_edge(
                ticker,
                item['ticker'],
                'picks_shovels',
                strength=item['confidence'],
                sources=['deepseek_auto'],
            )

        # Add infrastructure edges
        for item in ecosystem.get('infrastructure', []):
            graph.add_node(item['ticker'])
            graph.add_edge(
                ticker,
                item['ticker'],
                'infrastructure',
                strength=item['confidence'],
                sources=['deepseek_auto'],
            )

        # Save graph
        graph.save()

        logger.info(f"Stored ecosystem for {ticker}: {len(ecosystem.get('suppliers', []))} suppliers, "
                    f"{len(ecosystem.get('competitors', []))} competitors")

        return True

    except Exception as e:
        logger.error(f"Failed to store ecosystem: {e}")
        return False


def generate_ecosystem_sync(ticker: str) -> Optional[dict]:
    """
    Synchronously generate ecosystem for a ticker.

    Args:
        ticker: Stock ticker

    Returns:
        Validated ecosystem data or None
    """
    ticker = ticker.upper()

    # Generate prompt
    prompt = generate_ecosystem_prompt(ticker)

    # Call DeepSeek
    response = call_deepseek(prompt, max_tokens=2000)

    if not response:
        logger.error(f"No response from DeepSeek for {ticker}")
        return None

    # Parse response
    raw_ecosystem = parse_ecosystem_response(response)

    if not raw_ecosystem:
        logger.error(f"Failed to parse ecosystem for {ticker}")
        return None

    # Validate and filter
    validated = validate_and_filter_ecosystem(raw_ecosystem)

    # Store in graph
    store_ecosystem_in_graph(validated)

    return validated


async def auto_generate_ecosystem(ticker: str) -> Optional[dict]:
    """
    Async wrapper for ecosystem generation.

    Bot automatically calls DeepSeek to research ecosystem.
    Called on schedule or when new driver is detected.
    """
    # Run sync version in thread pool
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, generate_ecosystem_sync, ticker)


def refresh_key_drivers(force: bool = False) -> dict:
    """
    Refresh ecosystems for all key drivers.

    Should be called weekly (Sunday 6 AM recommended).

    Args:
        force: Force refresh even if recently updated

    Returns:
        Dict with results
    """
    results = {
        'success': [],
        'failed': [],
        'skipped': [],
        'started_at': datetime.now().isoformat(),
    }

    for ticker in ALL_KEY_DRIVERS:
        try:
            ecosystem = generate_ecosystem_sync(ticker)
            if ecosystem:
                results['success'].append(ticker)
            else:
                results['failed'].append(ticker)
        except Exception as e:
            logger.error(f"Failed to refresh {ticker}: {e}")
            results['failed'].append(ticker)

    results['completed_at'] = datetime.now().isoformat()
    results['total'] = len(ALL_KEY_DRIVERS)
    results['success_rate'] = len(results['success']) / results['total'] * 100 if results['total'] > 0 else 0

    logger.info(f"Refreshed {len(results['success'])}/{results['total']} key drivers")

    return results


def refresh_hot_stocks(min_score: float = 80, scores_dict: Optional[dict] = None) -> dict:
    """
    Refresh ecosystems for "hot" stocks.

    Should be called daily (6 AM recommended).

    Args:
        min_score: Minimum score to consider hot
        scores_dict: Dict of ticker -> score

    Returns:
        Dict with results
    """
    results = {
        'success': [],
        'failed': [],
        'started_at': datetime.now().isoformat(),
    }

    hot_tickers = []

    if scores_dict:
        for ticker, score in scores_dict.items():
            if isinstance(score, dict):
                score = score.get('story_score', score.get('composite_score', 0))
            if score >= min_score:
                hot_tickers.append(ticker)
    else:
        # Try to load from scan results
        try:
            import glob
            import pandas as pd
            scan_files = sorted(glob.glob('scan_*.csv'), reverse=True)
            if scan_files:
                df = pd.read_csv(scan_files[0])
                hot_tickers = df[df['composite_score'] >= min_score]['ticker'].tolist()
        except Exception as e:
            logger.error(f"Failed to load hot stocks: {e}")

    for ticker in hot_tickers[:20]:  # Limit to top 20
        try:
            ecosystem = generate_ecosystem_sync(ticker)
            if ecosystem:
                results['success'].append(ticker)
            else:
                results['failed'].append(ticker)
        except Exception as e:
            logger.error(f"Failed to refresh {ticker}: {e}")
            results['failed'].append(ticker)

    results['completed_at'] = datetime.now().isoformat()
    results['total'] = len(hot_tickers)

    logger.info(f"Refreshed {len(results['success'])}/{results['total']} hot stocks")

    return results


def refresh_single_ticker(ticker: str) -> dict:
    """
    Manual refresh for a single ticker.

    Called via /refresh NVDA command.

    Args:
        ticker: Stock ticker

    Returns:
        Dict with ecosystem or error
    """
    ticker = ticker.upper()

    try:
        ecosystem = generate_ecosystem_sync(ticker)

        if ecosystem:
            return {
                'ok': True,
                'ticker': ticker,
                'ecosystem': ecosystem,
                'supplier_count': len(ecosystem.get('suppliers', [])),
                'competitor_count': len(ecosystem.get('competitors', [])),
                'sub_theme_count': len(ecosystem.get('sub_themes', {})),
            }
        else:
            return {
                'ok': False,
                'ticker': ticker,
                'error': 'Failed to generate ecosystem',
            }

    except Exception as e:
        return {
            'ok': False,
            'ticker': ticker,
            'error': str(e),
        }


# =============================================================================
# NEWS-BASED DISCOVERY
# =============================================================================

def discover_from_news(ticker: str, news_items: list) -> list:
    """
    Discover relationships from news headlines.

    Looks for:
    - Partnership announcements
    - Supply agreements
    - M&A activity
    - Customer wins

    Args:
        ticker: Stock ticker
        news_items: List of news items with title/summary

    Returns:
        List of discovered relationships
    """
    if not news_items:
        return []

    # Combine news into prompt
    news_text = "\n".join([
        f"- {item.get('title', '')}: {item.get('summary', '')[:200]}"
        for item in news_items[:10]
    ])

    prompt = f"""Analyze these news headlines about {ticker} and identify any business relationships mentioned.

News:
{news_text}

Return ONLY valid JSON:
{{
    "relationships": [
        {{
            "type": "supplier|customer|partner|acquisition|competitor",
            "other_company": "Company Name",
            "ticker": "XXX",
            "confidence": 0.8,
            "source_headline": "headline that mentions this"
        }}
    ]
}}

Only include clearly stated relationships. If no relationships are mentioned, return empty list.
Only include US publicly traded companies with valid tickers.
"""

    response = call_deepseek(prompt, max_tokens=1000)

    if not response:
        return []

    try:
        data = json.loads(response)
        relationships = []

        for rel in data.get('relationships', []):
            ticker_other = rel.get('ticker', '').upper()
            if validate_ticker(ticker_other):
                relationships.append({
                    'source': ticker,
                    'target': ticker_other,
                    'type': rel.get('type', 'partner'),
                    'confidence': rel.get('confidence', 0.7),
                    'discovered_from': 'news',
                    'headline': rel.get('source_headline', ''),
                })

        return relationships

    except json.JSONDecodeError:
        return []


def store_news_relationships(relationships: list):
    """Store discovered relationships in the graph."""
    from relationship_graph import get_ecosystem_graph

    graph = get_ecosystem_graph()

    for rel in relationships:
        # Map news relationship types to graph types
        type_mapping = {
            'supplier': 'supplier',
            'customer': 'customer',
            'partner': 'adjacent',
            'acquisition': 'adjacent',
            'competitor': 'competitor',
        }

        rel_type = type_mapping.get(rel['type'], 'adjacent')

        graph.add_edge(
            rel['source'],
            rel['target'],
            rel_type,
            strength=rel['confidence'],
            sources=['news'],
            metadata={'headline': rel.get('headline', '')},
        )

    graph.save()


# =============================================================================
# SCHEDULED JOBS
# =============================================================================

def schedule_ecosystem_refresh():
    """
    Run ecosystem refresh on schedule.

    Weekly: Refresh all 50 drivers
    Daily: Refresh "hot" stocks (score > 80)
    """
    from datetime import datetime

    now = datetime.now()

    # Weekly job on Sunday
    if now.weekday() == 6:
        logger.info("Running weekly driver refresh...")
        refresh_key_drivers()

    # Daily job
    logger.info("Running daily hot stock refresh...")
    refresh_hot_stocks(min_score=80)


# =============================================================================
# INITIALIZATION - Generate initial ecosystems
# =============================================================================

def initialize_ecosystem_graph():
    """
    Initialize the ecosystem graph with key drivers.

    Called once to populate initial data.
    """
    from relationship_graph import get_ecosystem_graph, ECOSYSTEM_GRAPH_PATH

    # Check if already initialized
    if ECOSYSTEM_GRAPH_PATH.exists():
        graph = get_ecosystem_graph()
        if len(graph.nodes) > 20:
            logger.info("Ecosystem graph already initialized")
            return

    logger.info("Initializing ecosystem graph with key drivers...")

    # Generate ecosystems for key drivers
    results = refresh_key_drivers()

    logger.info(f"Initialization complete: {len(results['success'])} drivers added")

    return results


# =============================================================================
# CLI Testing
# =============================================================================

if __name__ == '__main__':
    print("Testing AI Ecosystem Generator...")

    # Test single ticker generation
    print("\n=== Generating NVDA Ecosystem ===")
    result = refresh_single_ticker('NVDA')

    if result['ok']:
        print(f"Success! Found:")
        print(f"  - {result['supplier_count']} suppliers")
        print(f"  - {result['competitor_count']} competitors")
        print(f"  - {result['sub_theme_count']} sub-themes")

        # Show some details
        ecosystem = result['ecosystem']
        print(f"\nSuppliers: {[s['ticker'] for s in ecosystem['suppliers'][:5]]}")
        print(f"Competitors: {[c['ticker'] for c in ecosystem['competitors'][:5]]}")
        print(f"Sub-themes: {list(ecosystem['sub_themes'].keys())}")
    else:
        print(f"Failed: {result.get('error', 'Unknown error')}")

    print("\nTest complete!")
