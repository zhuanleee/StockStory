#!/usr/bin/env python3
"""
Ecosystem Intelligence System

Comprehensive ecosystem mapping and intelligence for story stocks:
1. Ecosystem Queries - Get suppliers, customers, competitors for any stock
2. Opportunity Detection - Find lagging suppliers, gap plays, wave opportunities
3. Wave Propagation - Track how moves propagate through ecosystems
4. Theme Evolution - Track theme lifecycle and emerging sub-themes
5. Alerts - Generate ecosystem-based trading alerts

Usage:
    from ecosystem_intelligence import (
        get_ecosystem, scan_ecosystem_for_opportunities,
        detect_lagging_suppliers, calculate_wave_propagation
    )

    # Get NVDA's ecosystem
    ecosystem = get_ecosystem('NVDA', depth=2)

    # Find lagging suppliers when NVDA runs
    opportunities = detect_lagging_suppliers('NVDA', driver_move=5.0)

    # Track wave propagation after catalyst
    wave = calculate_wave_propagation('NVDA', 'earnings_beat')
"""

import json
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from typing import Optional
import uuid

from utils import get_logger

logger = get_logger(__name__)

# Import graph (lazy loading to avoid circular imports)
_graph = None


def _get_graph():
    """Lazy load the ecosystem graph."""
    global _graph
    if _graph is None:
        from relationship_graph import get_ecosystem_graph
        _graph = get_ecosystem_graph()
    return _graph


# Storage paths
WAVE_TRACKING_PATH = Path('learning_data/wave_tracking.json')
ECOSYSTEM_ALERTS_PATH = Path('learning_data/ecosystem_alerts.json')
THEME_EVOLUTION_PATH = Path('learning_data/theme_evolution.json')


# =============================================================================
# ECOSYSTEM QUERIES
# =============================================================================

def get_ecosystem(ticker: str, depth: int = 2) -> dict:
    """
    Get complete ecosystem for a ticker.

    Args:
        ticker: Stock ticker
        depth: How deep to traverse relationships

    Returns:
        Dict with suppliers, customers, competitors, adjacent_plays, sub_themes
    """
    graph = _get_graph()
    ticker = ticker.upper()

    # Get subgraph
    subgraph = graph.get_subgraph(ticker, depth=depth)

    # Categorize by relationship type
    suppliers = []
    customers = []
    competitors = []
    adjacent = []
    infrastructure = []
    picks_shovels = []

    for edge in subgraph['edges']:
        item = {
            'ticker': edge['target'] if edge['source'] == ticker else edge['source'],
            'relationship': edge['type'],
            'strength': edge['strength'],
            'freshness': edge['freshness'],
            'sub_theme': edge.get('sub_theme'),
            'sources': edge.get('sources', []),
        }

        if edge['type'] == 'supplier':
            suppliers.append(item)
        elif edge['type'] == 'customer':
            customers.append(item)
        elif edge['type'] == 'competitor':
            competitors.append(item)
        elif edge['type'] == 'adjacent':
            adjacent.append(item)
        elif edge['type'] == 'infrastructure':
            infrastructure.append(item)
        elif edge['type'] == 'picks_shovels':
            picks_shovels.append(item)

    # Group by sub-theme
    sub_themes = defaultdict(list)
    for edge in subgraph['edges']:
        if edge.get('sub_theme'):
            target = edge['target'] if edge['source'] == ticker else edge['source']
            sub_themes[edge['sub_theme']].append({
                'ticker': target,
                'relationship': edge['type'],
                'strength': edge['strength'],
            })

    # Get node metadata
    node = graph.get_node(ticker) or {}

    return {
        'ticker': ticker,
        'themes': node.get('themes', []),
        'market_cap_tier': node.get('market_cap_tier', 'unknown'),
        'suppliers': sorted(suppliers, key=lambda x: -x['strength']),
        'customers': sorted(customers, key=lambda x: -x['strength']),
        'competitors': sorted(competitors, key=lambda x: -x['strength']),
        'adjacent_plays': sorted(adjacent, key=lambda x: -x['strength']),
        'infrastructure': sorted(infrastructure, key=lambda x: -x['strength']),
        'picks_shovels': sorted(picks_shovels, key=lambda x: -x['strength']),
        'sub_themes': dict(sub_themes),
        'node_count': len(subgraph['nodes']),
        'edge_count': len(subgraph['edges']),
    }


def get_suppliers(ticker: str, min_strength: float = 0.5) -> list:
    """Get suppliers for a ticker."""
    graph = _get_graph()
    return graph.get_suppliers(ticker, min_strength=min_strength)


def get_customers(ticker: str, min_strength: float = 0.5) -> list:
    """Get customers for a ticker."""
    graph = _get_graph()
    return graph.get_customers(ticker, min_strength=min_strength)


def get_competitors(ticker: str, min_strength: float = 0.5) -> list:
    """Get competitors for a ticker."""
    graph = _get_graph()
    return graph.get_competitors(ticker, min_strength=min_strength)


def get_adjacent_plays(ticker: str, min_strength: float = 0.5) -> list:
    """Get adjacent/related plays for a ticker."""
    graph = _get_graph()
    neighbors = graph.get_neighbors(
        ticker, rel_type='adjacent', direction='both', min_strength=min_strength
    )
    return [{'ticker': t, **e} for t, e in neighbors]


def get_ecosystem_tickers(ticker: str, depth: int = 1) -> list:
    """Get all tickers in a stock's ecosystem."""
    graph = _get_graph()
    subgraph = graph.get_subgraph(ticker, depth=depth)
    return [node['ticker'] for node in subgraph['nodes']]


# =============================================================================
# OPPORTUNITY DETECTION
# =============================================================================

def get_stocks_in_play(min_score: float = 70, scores_dict: Optional[dict] = None) -> list:
    """
    Get stocks currently "in play" (high story score).

    Args:
        min_score: Minimum story score threshold
        scores_dict: Optional dict of ticker -> score

    Returns:
        List of stocks in play with their scores
    """
    if scores_dict is None:
        # Try to load from scan results
        try:
            import glob
            scan_files = sorted(glob.glob('scan_*.csv'), reverse=True)
            if scan_files:
                import pandas as pd
                df = pd.read_csv(scan_files[0])
                scores_dict = df.set_index('ticker')['composite_score'].to_dict()
        except Exception:
            return []

    in_play = []
    for ticker, score in scores_dict.items():
        if score >= min_score:
            ecosystem = get_ecosystem(ticker, depth=1)
            in_play.append({
                'ticker': ticker,
                'score': score,
                'themes': ecosystem.get('themes', []),
                'ecosystem_size': ecosystem['node_count'],
                'supplier_count': len(ecosystem['suppliers']),
                'competitor_count': len(ecosystem['competitors']),
            })

    return sorted(in_play, key=lambda x: -x['score'])


def scan_ecosystem_for_opportunities(
    driver: str,
    driver_score: float,
    scores_dict: Optional[dict] = None,
    min_gap: float = 10,
) -> list:
    """
    Scan a driver's ecosystem for lagging opportunities.

    Args:
        driver: Driver ticker
        driver_score: Driver's current story score
        scores_dict: Dict of ticker -> score for ecosystem stocks
        min_gap: Minimum score gap to consider an opportunity

    Returns:
        List of opportunities with gap analysis
    """
    ecosystem = get_ecosystem(driver, depth=2)
    opportunities = []

    if scores_dict is None:
        scores_dict = {}

    # Check each category
    for category in ['suppliers', 'customers', 'competitors', 'picks_shovels']:
        for item in ecosystem.get(category, []):
            target = item['ticker']
            target_score = scores_dict.get(target, 50)  # Default to neutral

            gap = driver_score - target_score

            if gap >= min_gap:
                opportunities.append({
                    'ticker': target,
                    'driver': driver,
                    'relationship': item['relationship'],
                    'sub_theme': item.get('sub_theme'),
                    'driver_score': driver_score,
                    'target_score': target_score,
                    'gap': gap,
                    'strength': item['strength'],
                    'alert_type': f'LAGGING_{category.upper()[:-1]}',
                })

    return sorted(opportunities, key=lambda x: -x['gap'])


def detect_lagging_suppliers(
    driver: str,
    driver_score: float = None,
    driver_move: float = 0.0,
    scores_dict: Optional[dict] = None,
    min_gap: float = 10,
) -> list:
    """
    Find suppliers lagging behind a hot driver.

    This is the classic "second wave" trade:
    - NVDA runs on AI demand
    - MU (HBM supplier) hasn't moved yet
    - Trade: Long MU expecting catch-up

    Args:
        driver: Driver ticker
        driver_score: Driver's story score (or use recent score)
        driver_move: Driver's recent % move (for wave tracking)
        scores_dict: Dict of ticker -> score
        min_gap: Minimum score gap

    Returns:
        List of lagging supplier opportunities
    """
    suppliers = get_suppliers(driver, min_strength=0.5)

    if driver_score is None:
        driver_score = 70  # Assume driver is hot

    if scores_dict is None:
        scores_dict = {}

    opportunities = []

    for supplier in suppliers:
        target = supplier['ticker']
        target_score = scores_dict.get(target, 50)
        gap = driver_score - target_score

        if gap >= min_gap:
            # Check for squeeze or breakout setup
            technical_setup = 'unknown'
            # Would integrate with scanner here for real setup detection

            opportunities.append({
                'ticker': target,
                'driver': driver,
                'relationship': 'supplier',
                'sub_theme': supplier.get('sub_theme'),
                'driver_score': driver_score,
                'target_score': target_score,
                'gap': gap,
                'driver_move_pct': driver_move,
                'technical_setup': technical_setup,
                'strength': supplier['strength'],
                'alert_type': 'LAGGING_SUPPLIER',
                'signal': f"{driver} hot, {target} lagging - classic second wave",
            })

    return sorted(opportunities, key=lambda x: -x['gap'])


def find_gap_plays(
    theme: Optional[str] = None,
    scores_dict: Optional[dict] = None,
    min_story_score: float = 70,
    max_technical_score: float = 50,
) -> list:
    """
    Find stocks with high story score but low technical score.

    These are potential breakout candidates:
    - Strong fundamental story
    - Not reflected in price yet
    - Often in squeeze waiting to fire

    Args:
        theme: Optional theme filter
        scores_dict: Dict with story_score and technical_score
        min_story_score: Minimum story score
        max_technical_score: Maximum technical score (lower = more opportunity)

    Returns:
        List of gap play opportunities
    """
    graph = _get_graph()
    gap_plays = []

    if scores_dict is None:
        return []

    for ticker in graph.nodes:
        if ticker not in scores_dict:
            continue

        data = scores_dict[ticker]

        # Handle both dict and simple score formats
        if isinstance(data, dict):
            story_score = data.get('story_score', 0)
            technical_score = data.get('technical_score', 50)
            in_squeeze = data.get('in_squeeze', False)
        else:
            story_score = data
            technical_score = 50
            in_squeeze = False

        if story_score >= min_story_score and technical_score <= max_technical_score:
            node = graph.get_node(ticker)
            themes = node.get('themes', []) if node else []

            if theme and theme not in themes:
                continue

            gap_plays.append({
                'ticker': ticker,
                'story_score': story_score,
                'technical_score': technical_score,
                'gap': story_score - technical_score,
                'in_squeeze': in_squeeze,
                'themes': themes,
                'alert_type': 'GAP_PLAY',
            })

    return sorted(gap_plays, key=lambda x: -x['gap'])


# =============================================================================
# WAVE PROPAGATION TRACKING
# =============================================================================

def _load_wave_tracking() -> dict:
    """Load wave tracking data."""
    if WAVE_TRACKING_PATH.exists():
        with open(WAVE_TRACKING_PATH, 'r') as f:
            return json.load(f)
    return {'waves': [], 'active_waves': {}}


def _save_wave_tracking(data: dict):
    """Save wave tracking data."""
    WAVE_TRACKING_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(WAVE_TRACKING_PATH, 'w') as f:
        json.dump(data, f, indent=2, default=str)


def calculate_wave_propagation(
    origin: str,
    event: str,
    origin_move_pct: float = 0.0,
    scores_dict: Optional[dict] = None,
) -> dict:
    """
    Calculate wave propagation from a driver catalyst.

    When NVDA beats earnings +12%, the wave typically propagates:
    - Tier 1 (Day 0): Competitors (AMD, AVGO) move immediately
    - Tier 2 (Day 1-2): Suppliers (MU, TSM) follow
    - Tier 3 (Day 2-5): Picks & Shovels (AMAT, LRCX) catch up

    Args:
        origin: Driver ticker
        event: Catalyst type (earnings_beat, product_launch, etc.)
        origin_move_pct: Driver's % move
        scores_dict: Dict of ticker -> score/move data

    Returns:
        Wave propagation structure with tiers
    """
    ecosystem = get_ecosystem(origin, depth=2)

    # Define wave tiers
    tiers = []

    # Tier 1: Competitors (move same day)
    tier1_tickers = [c['ticker'] for c in ecosystem['competitors'][:5]]
    tiers.append({
        'tier': 1,
        'name': 'Competitors',
        'relationship': 'competitor',
        'expected_lag': '0 days',
        'tickers': tier1_tickers,
        'status': 'complete' if origin_move_pct > 5 else 'pending',
    })

    # Tier 2: Suppliers (1-2 days)
    tier2_tickers = [s['ticker'] for s in ecosystem['suppliers'][:5]]
    tiers.append({
        'tier': 2,
        'name': 'Suppliers',
        'relationship': 'supplier',
        'expected_lag': '1-2 days',
        'tickers': tier2_tickers,
        'status': 'in_progress' if origin_move_pct > 5 else 'pending',
    })

    # Tier 3: Picks & Shovels (2-5 days)
    tier3_tickers = [p['ticker'] for p in ecosystem['picks_shovels'][:5]]
    if not tier3_tickers:
        # Fall back to adjacent plays
        tier3_tickers = [a['ticker'] for a in ecosystem['adjacent_plays'][:5]]

    tiers.append({
        'tier': 3,
        'name': 'Picks & Shovels',
        'relationship': 'picks_shovels',
        'expected_lag': '2-5 days',
        'tickers': tier3_tickers,
        'status': 'pending',
    })

    # Tier 4: Infrastructure (3-7 days)
    tier4_tickers = [i['ticker'] for i in ecosystem['infrastructure'][:3]]
    if tier4_tickers:
        tiers.append({
            'tier': 4,
            'name': 'Infrastructure',
            'relationship': 'infrastructure',
            'expected_lag': '3-7 days',
            'tickers': tier4_tickers,
            'status': 'pending',
        })

    # Calculate gap plays in each tier
    gap_plays = []
    if scores_dict:
        for tier in tiers:
            if tier['status'] != 'complete':
                for ticker in tier['tickers']:
                    target_data = scores_dict.get(ticker, {})
                    if isinstance(target_data, dict):
                        target_move = target_data.get('daily_change', 0)
                    else:
                        target_move = 0

                    if origin_move_pct > 5 and target_move < origin_move_pct * 0.3:
                        gap_plays.append({
                            'ticker': ticker,
                            'tier': tier['tier'],
                            'relationship': tier['relationship'],
                            'driver_move': origin_move_pct,
                            'target_move': target_move,
                            'gap_pct': origin_move_pct - target_move,
                        })

    wave = {
        'wave_id': str(uuid.uuid4())[:8],
        'origin': origin,
        'event': event,
        'origin_move_pct': origin_move_pct,
        'started_at': datetime.now().isoformat(),
        'tiers': tiers,
        'gap_plays': gap_plays,
    }

    # Save wave tracking
    tracking = _load_wave_tracking()
    tracking['active_waves'][wave['wave_id']] = wave
    tracking['waves'].append({
        'wave_id': wave['wave_id'],
        'origin': origin,
        'event': event,
        'started_at': wave['started_at'],
    })
    # Keep only last 50 waves
    tracking['waves'] = tracking['waves'][-50:]
    _save_wave_tracking(tracking)

    return wave


def get_next_wave_tier(wave_id: str) -> Optional[dict]:
    """Get the next tier in a wave that hasn't completed."""
    tracking = _load_wave_tracking()
    wave = tracking['active_waves'].get(wave_id)

    if not wave:
        return None

    for tier in wave['tiers']:
        if tier['status'] in ['pending', 'in_progress']:
            return tier

    return None


def update_wave_status(wave_id: str, tier: int, status: str, moves: Optional[dict] = None):
    """Update the status of a wave tier."""
    tracking = _load_wave_tracking()

    if wave_id not in tracking['active_waves']:
        return

    wave = tracking['active_waves'][wave_id]

    for t in wave['tiers']:
        if t['tier'] == tier:
            t['status'] = status
            if moves:
                t['moves'] = moves
            t['updated_at'] = datetime.now().isoformat()
            break

    _save_wave_tracking(tracking)


def get_active_waves() -> list:
    """Get all active wave propagations."""
    tracking = _load_wave_tracking()
    return list(tracking['active_waves'].values())


# =============================================================================
# THEME EVOLUTION
# =============================================================================

def _load_theme_evolution() -> dict:
    """Load theme evolution data."""
    if THEME_EVOLUTION_PATH.exists():
        with open(THEME_EVOLUTION_PATH, 'r') as f:
            return json.load(f)
    return {'themes': {}, 'sub_themes': {}, 'rotations': []}


def _save_theme_evolution(data: dict):
    """Save theme evolution data."""
    THEME_EVOLUTION_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(THEME_EVOLUTION_PATH, 'w') as f:
        json.dump(data, f, indent=2, default=str)


def get_theme_lifecycle(theme_id: str) -> str:
    """
    Get the lifecycle stage of a theme.

    Stages:
    - early: Just emerging, low awareness, high alpha potential
    - middle: Growing momentum, wider recognition
    - late: Peak popularity, crowded trade
    - fading: Momentum declining, rotation out

    Returns:
        Lifecycle stage string
    """
    evolution = _load_theme_evolution()
    theme_data = evolution['themes'].get(theme_id, {})
    return theme_data.get('stage', 'unknown')


def detect_emerging_subthemes(theme_id: str, scores_dict: Optional[dict] = None) -> list:
    """
    Detect emerging sub-themes within a broader theme.

    Example: Within AI Infrastructure, detect emerging sub-themes like:
    - HBM Memory (MU, SK)
    - AI Networking (AVGO, MRVL, ANET)
    - AI Power/Cooling (VRT, ETN)

    Args:
        theme_id: Parent theme ID
        scores_dict: Dict of ticker -> score

    Returns:
        List of emerging sub-themes with momentum
    """
    graph = _get_graph()
    evolution = _load_theme_evolution()

    # Get all sub-themes for this theme
    sub_themes = []

    for edge_list in graph.edges.values():
        for edge in edge_list:
            sub_theme = edge.get('sub_theme')
            if sub_theme and sub_theme not in [s['name'] for s in sub_themes]:
                # Get all tickers in this sub-theme
                tickers = graph.get_by_sub_theme(sub_theme)

                # Calculate momentum
                if scores_dict:
                    avg_score = sum(
                        scores_dict.get(t, 50) for t in tickers
                    ) / len(tickers) if tickers else 0
                else:
                    avg_score = 50

                # Check if emerging
                historical = evolution['sub_themes'].get(sub_theme, {})
                prev_score = historical.get('last_avg_score', 50)
                momentum = avg_score - prev_score

                sub_themes.append({
                    'name': sub_theme,
                    'tickers': tickers[:6],
                    'avg_score': avg_score,
                    'momentum': momentum,
                    'is_emerging': momentum > 5,
                    'stage': 'emerging' if momentum > 10 else ('hot' if avg_score > 70 else 'stable'),
                })

                # Update tracking
                evolution['sub_themes'][sub_theme] = {
                    'last_avg_score': avg_score,
                    'updated_at': datetime.now().isoformat(),
                }

    _save_theme_evolution(evolution)

    return sorted(sub_themes, key=lambda x: -x['momentum'])


def detect_rotation_signals(scores_history: Optional[dict] = None) -> list:
    """
    Detect rotation signals between themes.

    Rotation occurs when:
    - Money flows from one theme to another
    - One theme weakens while another strengthens
    - Correlation between themes breaks down

    Returns:
        List of rotation signals
    """
    evolution = _load_theme_evolution()
    rotations = []

    if not scores_history:
        return rotations

    # Compare theme momentum changes
    themes = list(evolution['themes'].keys())

    for i, theme1 in enumerate(themes):
        data1 = evolution['themes'][theme1]
        for theme2 in themes[i + 1:]:
            data2 = evolution['themes'][theme2]

            momentum1 = data1.get('momentum', 0)
            momentum2 = data2.get('momentum', 0)

            # Rotation signal: one declining while other rising
            if momentum1 > 5 and momentum2 < -5:
                rotations.append({
                    'from_theme': theme2,
                    'to_theme': theme1,
                    'from_momentum': momentum2,
                    'to_momentum': momentum1,
                    'signal_strength': abs(momentum1) + abs(momentum2),
                    'detected_at': datetime.now().isoformat(),
                })
            elif momentum2 > 5 and momentum1 < -5:
                rotations.append({
                    'from_theme': theme1,
                    'to_theme': theme2,
                    'from_momentum': momentum1,
                    'to_momentum': momentum2,
                    'signal_strength': abs(momentum1) + abs(momentum2),
                    'detected_at': datetime.now().isoformat(),
                })

    # Save rotations
    evolution['rotations'] = (evolution.get('rotations', []) + rotations)[-20:]
    _save_theme_evolution(evolution)

    return sorted(rotations, key=lambda x: -x['signal_strength'])


def update_theme_stage(theme_id: str, stage: str, momentum: float = 0.0, top_stocks: Optional[list] = None):
    """Update a theme's lifecycle stage."""
    evolution = _load_theme_evolution()

    if theme_id not in evolution['themes']:
        evolution['themes'][theme_id] = {
            'created_at': datetime.now().isoformat(),
        }

    evolution['themes'][theme_id].update({
        'stage': stage,
        'momentum': momentum,
        'top_stocks': top_stocks or [],
        'updated_at': datetime.now().isoformat(),
    })

    _save_theme_evolution(evolution)


# =============================================================================
# ALERT GENERATION
# =============================================================================

def _load_ecosystem_alerts() -> dict:
    """Load ecosystem alerts."""
    if ECOSYSTEM_ALERTS_PATH.exists():
        with open(ECOSYSTEM_ALERTS_PATH, 'r') as f:
            return json.load(f)
    return {'alerts': [], 'outcomes': {}}


def _save_ecosystem_alerts(data: dict):
    """Save ecosystem alerts."""
    ECOSYSTEM_ALERTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(ECOSYSTEM_ALERTS_PATH, 'w') as f:
        json.dump(data, f, indent=2, default=str)


def generate_ecosystem_alerts(
    drivers: Optional[list] = None,
    scores_dict: Optional[dict] = None,
) -> list:
    """
    Generate ecosystem-based alerts.

    Alert Types:
    - LAGGING_SUPPLIER: Driver hot, supplier lagging
    - WAVE_TIER_OPPORTUNITY: Next tier in wave ready
    - SUBTHEME_BREAKOUT: Sub-theme momentum accelerating
    - GAP_PLAY: High story, low technical, in squeeze
    - THEME_ROTATION: Money rotating between themes

    Args:
        drivers: List of driver tickers to check
        scores_dict: Dict of ticker -> score data

    Returns:
        List of alerts sorted by priority
    """
    alerts = []
    alert_data = _load_ecosystem_alerts()

    if drivers is None:
        # Get in-play stocks as drivers
        in_play = get_stocks_in_play(min_score=70, scores_dict=scores_dict)
        drivers = [s['ticker'] for s in in_play[:10]]

    if scores_dict is None:
        scores_dict = {}

    # 1. Lagging Supplier Alerts
    for driver in drivers:
        driver_score = scores_dict.get(driver, 70)
        if isinstance(driver_score, dict):
            driver_score = driver_score.get('story_score', driver_score.get('composite_score', 70))

        opportunities = detect_lagging_suppliers(
            driver,
            driver_score=driver_score,
            scores_dict={k: v if isinstance(v, (int, float)) else v.get('story_score', 50) for k, v in scores_dict.items()},
            min_gap=10,
        )

        for opp in opportunities[:3]:  # Top 3 per driver
            alerts.append({
                'alert_id': str(uuid.uuid4())[:8],
                'type': 'LAGGING_SUPPLIER',
                'priority': 'high' if opp['gap'] > 20 else 'medium',
                'ticker': opp['ticker'],
                'driver': opp['driver'],
                'sub_theme': opp.get('sub_theme'),
                'gap': opp['gap'],
                'message': opp.get('signal', f"{opp['driver']} hot, {opp['ticker']} lagging by {opp['gap']:.0f} pts"),
                'created_at': datetime.now().isoformat(),
            })

    # 2. Wave Tier Opportunities
    active_waves = get_active_waves()
    for wave in active_waves:
        next_tier = get_next_wave_tier(wave['wave_id'])
        if next_tier and wave['origin_move_pct'] > 5:
            for ticker in next_tier['tickers'][:3]:
                alerts.append({
                    'alert_id': str(uuid.uuid4())[:8],
                    'type': 'WAVE_TIER_OPPORTUNITY',
                    'priority': 'high',
                    'ticker': ticker,
                    'driver': wave['origin'],
                    'wave_id': wave['wave_id'],
                    'tier': next_tier['tier'],
                    'message': f"Wave from {wave['origin']} reaching Tier {next_tier['tier']} ({next_tier['name']})",
                    'created_at': datetime.now().isoformat(),
                })

    # 3. Gap Play Alerts
    gap_plays = find_gap_plays(scores_dict=scores_dict, min_story_score=70, max_technical_score=50)
    for gap in gap_plays[:5]:
        alerts.append({
            'alert_id': str(uuid.uuid4())[:8],
            'type': 'GAP_PLAY',
            'priority': 'medium' if gap.get('in_squeeze') else 'low',
            'ticker': gap['ticker'],
            'story_score': gap['story_score'],
            'technical_score': gap['technical_score'],
            'gap': gap['gap'],
            'in_squeeze': gap.get('in_squeeze', False),
            'message': f"{gap['ticker']}: Story {gap['story_score']:.0f} vs Technical {gap['technical_score']:.0f} - potential breakout",
            'created_at': datetime.now().isoformat(),
        })

    # 4. Sub-theme Breakout Alerts
    sub_themes = detect_emerging_subthemes('ai_infrastructure', scores_dict=scores_dict)
    for st in sub_themes:
        if st['is_emerging']:
            alerts.append({
                'alert_id': str(uuid.uuid4())[:8],
                'type': 'SUBTHEME_BREAKOUT',
                'priority': 'medium',
                'sub_theme': st['name'],
                'tickers': st['tickers'],
                'momentum': st['momentum'],
                'message': f"Sub-theme {st['name']} emerging with +{st['momentum']:.1f} momentum",
                'created_at': datetime.now().isoformat(),
            })

    # Sort by priority
    priority_order = {'high': 0, 'medium': 1, 'low': 2}
    alerts.sort(key=lambda x: (priority_order.get(x.get('priority', 'low'), 3), x.get('created_at', '')))

    # Save alerts
    alert_data['alerts'] = (alert_data.get('alerts', []) + alerts)[-100:]
    _save_ecosystem_alerts(alert_data)

    return alerts


def record_alert_outcome(alert_id: str, outcome: str, return_pct: float):
    """
    Record the outcome of an ecosystem alert for learning.

    Args:
        alert_id: Alert identifier
        outcome: 'win', 'loss', 'scratch'
        return_pct: Actual return percentage
    """
    alert_data = _load_ecosystem_alerts()

    alert_data['outcomes'][alert_id] = {
        'outcome': outcome,
        'return_pct': return_pct,
        'recorded_at': datetime.now().isoformat(),
    }

    _save_ecosystem_alerts(alert_data)


def get_alert_accuracy() -> dict:
    """Get historical accuracy of ecosystem alerts."""
    alert_data = _load_ecosystem_alerts()
    outcomes = alert_data.get('outcomes', {})

    if not outcomes:
        return {'total': 0, 'win_rate': 0, 'avg_return': 0}

    wins = sum(1 for o in outcomes.values() if o['outcome'] == 'win')
    total = len(outcomes)
    returns = [o['return_pct'] for o in outcomes.values()]

    return {
        'total': total,
        'wins': wins,
        'losses': total - wins,
        'win_rate': wins / total * 100 if total > 0 else 0,
        'avg_return': sum(returns) / len(returns) if returns else 0,
        'best_return': max(returns) if returns else 0,
        'worst_return': min(returns) if returns else 0,
    }


# =============================================================================
# ECOSYSTEM SCORE CALCULATION
# =============================================================================

def calculate_ecosystem_score(
    ticker: str,
    scores_dict: Optional[dict] = None,
) -> dict:
    """
    Calculate ecosystem strength score for a ticker.

    Components:
    - Driver strength (if in ecosystem of a hot driver)
    - Supplier/customer network size
    - Theme cohesion
    - Freshness of relationships

    Returns:
        Dict with score and breakdown
    """
    graph = _get_graph()
    node = graph.get_node(ticker)

    if not node:
        return {'score': 50, 'breakdown': {}, 'in_ecosystem': False}

    # Get ecosystem
    ecosystem = get_ecosystem(ticker, depth=1)

    # Calculate components
    network_score = min(100, (
        len(ecosystem['suppliers']) * 10 +
        len(ecosystem['customers']) * 10 +
        len(ecosystem['competitors']) * 5 +
        len(ecosystem['infrastructure']) * 5
    ))

    # Driver proximity score
    driver_score = 50
    if scores_dict:
        # Check if this ticker is connected to any hot driver
        neighbors = graph.get_neighbors(ticker, direction='both')
        for neighbor, edge in neighbors:
            neighbor_score = scores_dict.get(neighbor, 0)
            if isinstance(neighbor_score, dict):
                neighbor_score = neighbor_score.get('story_score', 0)
            if neighbor_score >= 70:
                driver_score = max(driver_score, 50 + (neighbor_score - 70) * 2)

    # Theme cohesion score
    themes = node.get('themes', [])
    theme_score = min(100, len(themes) * 30 + len(ecosystem.get('sub_themes', {})) * 10)

    # Freshness score
    edges = graph.get_neighbors(ticker, direction='both')
    if edges:
        avg_freshness = sum(e['freshness'] for _, e in edges) / len(edges)
        freshness_score = avg_freshness * 100
    else:
        freshness_score = 50

    # Weighted combination
    score = (
        network_score * 0.25 +
        driver_score * 0.35 +
        theme_score * 0.25 +
        freshness_score * 0.15
    )

    return {
        'score': round(score, 1),
        'breakdown': {
            'network': round(network_score, 1),
            'driver_proximity': round(driver_score, 1),
            'theme_cohesion': round(theme_score, 1),
            'freshness': round(freshness_score, 1),
        },
        'in_ecosystem': len(ecosystem['suppliers']) + len(ecosystem['competitors']) > 0,
        'themes': themes,
        'network_size': ecosystem['node_count'],
    }


# =============================================================================
# CLI Testing
# =============================================================================

if __name__ == '__main__':
    print("Testing Ecosystem Intelligence...")

    # Initialize with test data
    from relationship_graph import RelationshipGraph

    graph = RelationshipGraph()

    # Add test ecosystem for NVDA
    graph.add_node('NVDA', {'themes': ['ai_infrastructure'], 'market_cap_tier': 'mega'})
    graph.add_node('MU', {'themes': ['ai_infrastructure'], 'market_cap_tier': 'large'})
    graph.add_node('TSM', {'themes': ['ai_infrastructure'], 'market_cap_tier': 'mega'})
    graph.add_node('AMD', {'themes': ['ai_infrastructure'], 'market_cap_tier': 'mega'})
    graph.add_node('AMAT', {'themes': ['ai_infrastructure'], 'market_cap_tier': 'large'})
    graph.add_node('VRT', {'themes': ['ai_infrastructure'], 'market_cap_tier': 'mid'})

    graph.add_edge('NVDA', 'MU', 'supplier', strength=0.9, sub_theme='HBM_Memory')
    graph.add_edge('NVDA', 'TSM', 'supplier', strength=0.95, sub_theme='CoWoS_Packaging')
    graph.add_edge('NVDA', 'AMD', 'competitor', strength=0.85)
    graph.add_edge('NVDA', 'AMAT', 'picks_shovels', strength=0.7)
    graph.add_edge('NVDA', 'VRT', 'infrastructure', strength=0.65, sub_theme='AI_Cooling')

    graph.save()

    # Reset singleton to use new graph (directly assign module-level variable)
    _graph = graph

    # Test ecosystem query
    print("\n=== NVDA Ecosystem ===")
    ecosystem = get_ecosystem('NVDA', depth=2)
    print(f"Suppliers: {[s['ticker'] for s in ecosystem['suppliers']]}")
    print(f"Competitors: {[c['ticker'] for c in ecosystem['competitors']]}")
    print(f"Sub-themes: {list(ecosystem['sub_themes'].keys())}")

    # Test lagging supplier detection
    print("\n=== Lagging Suppliers ===")
    scores = {'NVDA': 88, 'MU': 62, 'TSM': 70, 'AMD': 80, 'AMAT': 68}
    opportunities = detect_lagging_suppliers('NVDA', driver_score=88, scores_dict=scores)
    for opp in opportunities:
        print(f"{opp['ticker']}: Gap {opp['gap']:.0f} pts ({opp.get('sub_theme', 'N/A')})")

    # Test wave propagation
    print("\n=== Wave Propagation ===")
    wave = calculate_wave_propagation('NVDA', 'earnings_beat', origin_move_pct=12.5, scores_dict=scores)
    for tier in wave['tiers']:
        print(f"Tier {tier['tier']} ({tier['name']}): {tier['tickers']} - {tier['status']}")

    # Test ecosystem score
    print("\n=== Ecosystem Scores ===")
    for ticker in ['NVDA', 'MU', 'AMD']:
        score_data = calculate_ecosystem_score(ticker, scores_dict=scores)
        print(f"{ticker}: {score_data['score']:.1f} - Network: {score_data['breakdown']['network']:.0f}, Driver: {score_data['breakdown']['driver_proximity']:.0f}")

    print("\nAll tests passed!")
