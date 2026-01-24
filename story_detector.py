#!/usr/bin/env python3
"""
Story Detector - Identifies emerging market themes and stories

Features:
1. Theme Scanner - Aggregates news across 50+ tickers to identify themes
2. Theme Momentum - Tracks theme mentions over time
3. Early Story Detection - Finds themes not yet priced in
4. Story-to-Stock Mapping - Connects themes to beneficiary stocks
5. SELF-LEARNING - Automatically learns new themes and builds stock mappings
"""

import os
import json
import requests
from datetime import datetime, timedelta
from collections import Counter, defaultdict
from pathlib import Path
import re

# Import news sources
from news_analyzer import (
    scrape_finviz_news,
    scrape_google_news,
    scrape_yahoo_news,
    DEEPSEEK_API_KEY,
    DEEPSEEK_API_URL
)

# Import alternative sources (podcasts, newsletters)
try:
    from alt_sources import aggregate_alt_sources, extract_themes_from_alt_sources
    ALT_SOURCES_AVAILABLE = True
except ImportError:
    ALT_SOURCES_AVAILABLE = False

# Import signal ranker
try:
    from signal_ranker import (
        rank_signals, calculate_overall_score, record_signal,
        check_signal_accuracy, format_ranked_signals,
        get_source_leaderboard, format_source_leaderboard
    )
    RANKER_AVAILABLE = True
except ImportError:
    RANKER_AVAILABLE = False

# ============================================================
# CONFIGURATION
# ============================================================

# Tickers to scan for theme detection (broad market coverage)
SCAN_UNIVERSE = [
    # Mega cap tech
    'NVDA', 'AAPL', 'MSFT', 'GOOGL', 'META', 'AMZN', 'TSLA',
    # Semiconductors
    'AMD', 'AVGO', 'MRVL', 'QCOM', 'INTC', 'MU', 'AMAT', 'LRCX', 'KLAC', 'ASML',
    # AI Infrastructure
    'VRT', 'ANET', 'SMCI', 'DELL', 'HPE',
    # Cloud/Software
    'CRM', 'NOW', 'SNOW', 'PLTR', 'DDOG', 'NET', 'MDB', 'CRWD',
    # Energy/Utilities
    'VST', 'CEG', 'NEE', 'SO', 'DUK',
    # Nuclear
    'SMR', 'OKLO', 'CCJ', 'UEC',
    # Healthcare/Biotech
    'LLY', 'NVO', 'MRNA', 'PFE', 'ABBV', 'VKTX', 'HIMS',
    # Financials
    'JPM', 'GS', 'MS', 'BAC', 'V', 'MA',
    # Industrials
    'CAT', 'DE', 'GE', 'HON', 'LMT', 'RTX',
    # Consumer
    'COST', 'WMT', 'HD', 'NKE', 'SBUX',
    # EV/Auto
    'RIVN', 'LCID', 'F', 'GM',
    # Crypto-adjacent
    'COIN', 'MSTR', 'MARA', 'RIOT',
]

# Known theme patterns and their beneficiaries
THEME_DATABASE = {
    'AI_INFRASTRUCTURE': {
        'keywords': ['ai infrastructure', 'data center', 'gpu', 'accelerator', 'ai chip',
                    'hyperscaler', 'capex', 'ai spending', 'compute', 'training'],
        'primary': ['NVDA', 'AVGO', 'MRVL', 'AMD'],
        'secondary': ['VRT', 'ANET', 'SMCI', 'DELL', 'AMAT', 'LRCX'],
        'supply_chain': ['MU', 'SK Hynix', 'Samsung', 'TSMC'],
    },
    'HBM_MEMORY': {
        'keywords': ['hbm', 'high bandwidth memory', 'hbm3', 'hbm4', 'ai memory',
                    'memory bandwidth', 'dram', 'memory demand'],
        'primary': ['MU', 'SK Hynix'],
        'secondary': ['AMAT', 'LRCX', 'KLAC'],
        'supply_chain': ['NVDA', 'AMD'],
    },
    'NUCLEAR_REVIVAL': {
        'keywords': ['nuclear', 'nuclear power', 'smr', 'small modular reactor',
                    'nuclear energy', 'nuclear deal', 'clean energy', 'uranium'],
        'primary': ['VST', 'CEG', 'SMR', 'OKLO'],
        'secondary': ['CCJ', 'UEC', 'NNE'],
        'supply_chain': ['MSFT', 'GOOGL', 'AMZN'],
    },
    'DATA_CENTER_POWER': {
        'keywords': ['data center power', 'power demand', 'electricity demand',
                    'grid', 'power infrastructure', 'energy consumption'],
        'primary': ['VST', 'CEG', 'VRT'],
        'secondary': ['NEE', 'SO', 'ETN', 'PWR'],
        'supply_chain': ['NVDA', 'MSFT', 'GOOGL'],
    },
    'GLP1_OBESITY': {
        'keywords': ['glp-1', 'glp1', 'ozempic', 'wegovy', 'mounjaro', 'weight loss',
                    'obesity', 'semaglutide', 'tirzepatide'],
        'primary': ['LLY', 'NVO'],
        'secondary': ['HIMS', 'VKTX', 'AMGN'],
        'disrupted': ['DXCM', 'PODD', 'MDT'],
    },
    'ROBOTICS_AUTOMATION': {
        'keywords': ['robotics', 'automation', 'humanoid', 'robot', 'optimus',
                    'industrial automation', 'manufacturing automation'],
        'primary': ['TSLA', 'ISRG', 'ROK'],
        'secondary': ['NVDA', 'FANUY', 'ABB'],
        'supply_chain': ['AMAT', 'ONTO'],
    },
    'QUANTUM_COMPUTING': {
        'keywords': ['quantum', 'quantum computing', 'qubit', 'quantum supremacy',
                    'quantum chip'],
        'primary': ['IONQ', 'RGTI', 'QBTS'],
        'secondary': ['GOOGL', 'IBM', 'MSFT'],
        'supply_chain': [],
    },
    'SPACE_ECONOMY': {
        'keywords': ['space', 'satellite', 'starlink', 'rocket', 'spacex',
                    'space economy', 'lunar', 'mars'],
        'primary': ['RKLB', 'LUNR', 'RDW'],
        'secondary': ['LMT', 'NOC', 'BA'],
        'supply_chain': [],
    },
    'CYBERSECURITY': {
        'keywords': ['cybersecurity', 'cyber attack', 'ransomware', 'hack',
                    'data breach', 'security threat', 'zero trust'],
        'primary': ['CRWD', 'PANW', 'ZS'],
        'secondary': ['FTNT', 'S', 'NET'],
        'supply_chain': [],
    },
    'CHINA_TRADE': {
        'keywords': ['china tariff', 'trade war', 'china ban', 'export control',
                    'china restriction', 'decoupling', 'reshoring'],
        'primary': [],
        'secondary': [],
        'affected': ['AAPL', 'NVDA', 'QCOM', 'MU', 'INTC'],
    },
    'INTEREST_RATES': {
        'keywords': ['fed rate', 'interest rate', 'rate cut', 'rate hike',
                    'fomc', 'powell', 'monetary policy', 'inflation'],
        'primary': ['JPM', 'GS', 'BAC'],
        'secondary': ['V', 'MA', 'PYPL'],
        'affected': ['growth stocks', 'REITs'],
    },
    'CRYPTO_RALLY': {
        'keywords': ['bitcoin', 'crypto', 'ethereum', 'btc', 'cryptocurrency',
                    'bitcoin etf', 'crypto rally'],
        'primary': ['COIN', 'MSTR', 'MARA', 'RIOT'],
        'secondary': ['SQ', 'HOOD'],
        'supply_chain': [],
    },
}

# File to store theme momentum history
THEME_HISTORY_FILE = Path('theme_history.json')

# File to store learned stories (self-learning)
LEARNED_STORIES_FILE = Path('learned_stories.json')

# Thresholds for self-learning
MIN_MENTIONS_TO_TRACK = 3       # Minimum mentions to start tracking a new theme
MIN_DAYS_TO_PROMOTE = 3         # Days of sustained mentions to promote to known theme
MIN_STOCKS_FOR_MAPPING = 2      # Minimum stocks to build a mapping


# ============================================================
# SELF-LEARNING SYSTEM
# ============================================================

def load_learned_stories():
    """Load learned stories from file."""
    if LEARNED_STORIES_FILE.exists():
        with open(LEARNED_STORIES_FILE, 'r') as f:
            return json.load(f)
    return {
        'emerging': {},      # New themes being tracked
        'promoted': {},      # Themes promoted to known status
        'stock_mappings': {},  # Auto-learned stock mappings
        'last_updated': None,
    }


def save_learned_stories(data):
    """Save learned stories to file."""
    data['last_updated'] = datetime.now().isoformat()
    with open(LEARNED_STORIES_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def learn_from_detection(detected_themes, headlines):
    """
    Self-learning: Track new themes and build stock mappings automatically.

    Process:
    1. For each AI-detected theme, check if it's new
    2. If new, add to emerging themes with stock mentions
    3. Track mentions over time
    4. Promote to known theme after sustained mentions
    5. Build stock mappings based on co-occurrence
    """
    learned = load_learned_stories()
    today = datetime.now().strftime('%Y-%m-%d')

    # Build headline-to-stock mapping
    headline_stocks = defaultdict(set)
    for h in headlines:
        # Extract key phrases from headline
        title_lower = h['title'].lower()
        headline_stocks[title_lower].add(h['ticker'])

    # Process each detected theme
    for theme in detected_themes.get('themes', []):
        theme_name = theme.get('name', '').upper().replace(' ', '_')
        if not theme_name:
            continue

        # Check if it's a known predefined theme
        is_known = theme_name in THEME_DATABASE

        # Get stocks mentioned with this theme
        mentioned_stocks = set()
        if theme.get('primary_plays'):
            mentioned_stocks.update(theme['primary_plays'])
        if theme.get('secondary_plays'):
            mentioned_stocks.update(theme['secondary_plays'])
        if theme.get('tickers_mentioned'):
            mentioned_stocks.update(theme['tickers_mentioned'])

        # Find additional stocks from headlines containing theme keywords
        theme_words = set(theme_name.lower().replace('_', ' ').split())
        for headline, stocks in headline_stocks.items():
            matching_words = sum(1 for w in theme_words if w in headline)
            if matching_words >= 1:
                mentioned_stocks.update(stocks)

        if not is_known:
            # Track as emerging theme
            if theme_name not in learned['emerging']:
                learned['emerging'][theme_name] = {
                    'first_seen': today,
                    'mentions': {},
                    'stocks': {},
                    'catalyst': theme.get('catalyst', ''),
                    'summary': theme.get('summary', ''),
                }

            # Update daily mentions
            emerging = learned['emerging'][theme_name]
            emerging['mentions'][today] = theme.get('mention_count', 1)

            # Update stock mappings
            for stock in mentioned_stocks:
                if stock not in emerging['stocks']:
                    emerging['stocks'][stock] = {'count': 0, 'first_seen': today}
                emerging['stocks'][stock]['count'] += 1

            # Update catalyst/summary if better info available
            if theme.get('catalyst') and len(theme['catalyst']) > len(emerging.get('catalyst', '')):
                emerging['catalyst'] = theme['catalyst']
            if theme.get('summary') and len(theme['summary']) > len(emerging.get('summary', '')):
                emerging['summary'] = theme['summary']

            # Check if should be promoted
            days_tracked = len(emerging['mentions'])
            total_mentions = sum(emerging['mentions'].values())

            if days_tracked >= MIN_DAYS_TO_PROMOTE and total_mentions >= MIN_MENTIONS_TO_TRACK * 2:
                # Promote to known theme
                promote_theme(theme_name, emerging, learned)

        else:
            # Update stock mappings for known themes
            if theme_name not in learned['stock_mappings']:
                learned['stock_mappings'][theme_name] = {
                    'additional_stocks': {},
                    'updated': today,
                }

            mapping = learned['stock_mappings'][theme_name]
            known_stocks = set(THEME_DATABASE[theme_name].get('primary', []) +
                             THEME_DATABASE[theme_name].get('secondary', []) +
                             THEME_DATABASE[theme_name].get('supply_chain', []))

            # Track new stocks not in predefined mapping
            for stock in mentioned_stocks:
                if stock not in known_stocks:
                    if stock not in mapping['additional_stocks']:
                        mapping['additional_stocks'][stock] = {'count': 0, 'first_seen': today}
                    mapping['additional_stocks'][stock]['count'] += 1

            mapping['updated'] = today

    # Process early signals for potential new themes
    for signal in detected_themes.get('early_signals', []):
        signal_name = signal.get('name', '').upper().replace(' ', '_').replace(':', '_')
        if not signal_name or signal_name in THEME_DATABASE:
            continue

        if signal_name not in learned['emerging']:
            learned['emerging'][signal_name] = {
                'first_seen': today,
                'mentions': {today: 1},
                'stocks': {},
                'catalyst': signal.get('signal', ''),
                'summary': '',
                'from_early_signal': True,
            }

        # Add watch list stocks
        for stock in signal.get('watch_list', []):
            if stock not in learned['emerging'][signal_name]['stocks']:
                learned['emerging'][signal_name]['stocks'][stock] = {'count': 0, 'first_seen': today}
            learned['emerging'][signal_name]['stocks'][stock]['count'] += 1

    # Clean up old emerging themes (no mentions in 14 days)
    cutoff = (datetime.now() - timedelta(days=14)).strftime('%Y-%m-%d')
    themes_to_remove = []
    for theme_name, data in learned['emerging'].items():
        recent_mentions = [d for d in data['mentions'].keys() if d >= cutoff]
        if not recent_mentions:
            themes_to_remove.append(theme_name)

    for theme_name in themes_to_remove:
        del learned['emerging'][theme_name]

    save_learned_stories(learned)
    return learned


def promote_theme(theme_name, emerging_data, learned):
    """
    Promote an emerging theme to known/promoted status.
    Build stock mappings based on learned data.
    """
    # Sort stocks by mention count
    stock_counts = [(s, d['count']) for s, d in emerging_data['stocks'].items()]
    stock_counts.sort(key=lambda x: -x[1])

    # Top stocks become primary, rest become secondary
    primary = [s for s, c in stock_counts[:4] if c >= 2]
    secondary = [s for s, c in stock_counts[4:8] if c >= 1]

    learned['promoted'][theme_name] = {
        'promoted_date': datetime.now().strftime('%Y-%m-%d'),
        'first_seen': emerging_data['first_seen'],
        'total_mentions': sum(emerging_data['mentions'].values()),
        'catalyst': emerging_data.get('catalyst', ''),
        'summary': emerging_data.get('summary', ''),
        'primary_plays': primary,
        'secondary_plays': secondary,
        'all_stocks': [s for s, _ in stock_counts],
    }

    # Remove from emerging
    if theme_name in learned['emerging']:
        del learned['emerging'][theme_name]

    return learned['promoted'][theme_name]


def get_learned_theme_info(theme_name):
    """Get info about a learned theme."""
    learned = load_learned_stories()

    # Check promoted themes
    if theme_name in learned.get('promoted', {}):
        return {
            'status': 'PROMOTED',
            'data': learned['promoted'][theme_name],
        }

    # Check emerging themes
    if theme_name in learned.get('emerging', {}):
        return {
            'status': 'EMERGING',
            'data': learned['emerging'][theme_name],
        }

    return None


def get_additional_stock_mappings(theme_name):
    """Get additional stocks learned for a known theme."""
    learned = load_learned_stories()

    if theme_name in learned.get('stock_mappings', {}):
        mapping = learned['stock_mappings'][theme_name]
        # Return stocks with at least 2 mentions
        return [s for s, d in mapping.get('additional_stocks', {}).items()
                if d['count'] >= 2]

    return []


def get_all_learned_themes():
    """Get all learned themes (emerging + promoted)."""
    learned = load_learned_stories()

    result = {
        'emerging': [],
        'promoted': [],
    }

    # Emerging themes
    for name, data in learned.get('emerging', {}).items():
        total_mentions = sum(data.get('mentions', {}).values())
        days_tracked = len(data.get('mentions', {}))
        top_stocks = sorted(data.get('stocks', {}).items(),
                          key=lambda x: -x[1]['count'])[:5]

        result['emerging'].append({
            'name': name,
            'first_seen': data.get('first_seen'),
            'total_mentions': total_mentions,
            'days_tracked': days_tracked,
            'top_stocks': [s for s, _ in top_stocks],
            'catalyst': data.get('catalyst', ''),
        })

    # Promoted themes
    for name, data in learned.get('promoted', {}).items():
        result['promoted'].append({
            'name': name,
            'promoted_date': data.get('promoted_date'),
            'total_mentions': data.get('total_mentions', 0),
            'primary_plays': data.get('primary_plays', []),
            'secondary_plays': data.get('secondary_plays', []),
        })

    # Sort by mentions
    result['emerging'].sort(key=lambda x: -x['total_mentions'])
    result['promoted'].sort(key=lambda x: -x['total_mentions'])

    return result


# ============================================================
# NEWS AGGREGATION
# ============================================================

def aggregate_market_news(tickers=None, max_per_ticker=5):
    """
    Aggregate news headlines from multiple tickers.
    Returns list of headlines with ticker info.
    """
    if tickers is None:
        tickers = SCAN_UNIVERSE

    all_headlines = []

    for ticker in tickers:
        try:
            # Get from multiple sources
            finviz = scrape_finviz_news(ticker)
            google = scrape_google_news(ticker)

            for h in (finviz + google)[:max_per_ticker]:
                if h.get('title'):
                    all_headlines.append({
                        'ticker': ticker,
                        'title': h['title'],
                        'source': h.get('source', 'Unknown'),
                    })
        except:
            continue

    return all_headlines


# ============================================================
# THEME DETECTION WITH AI
# ============================================================

def detect_themes_ai(headlines):
    """
    Use DeepSeek AI to identify themes from aggregated headlines.
    Returns list of detected themes with confidence.
    """
    if not headlines or not DEEPSEEK_API_KEY:
        return detect_themes_keywords(headlines)

    # Build headlines text
    headlines_text = ""
    for h in headlines[:100]:  # Limit to 100 headlines
        headlines_text += f"[{h['ticker']}] {h['title']}\n"

    prompt = f"""Analyze these stock market news headlines and identify the major THEMES/STORIES currently in play.

NEWS HEADLINES:
{headlines_text}

For each theme you identify, provide:
1. Theme name (short, memorable)
2. How "hot" it is (HOT/EMERGING/SUSTAINED/FADING)
3. Key catalyst driving it
4. Primary stocks that benefit
5. Secondary/supply chain plays
6. Any stocks that might be hurt

Respond in this exact JSON format:
{{
    "themes": [
        {{
            "name": "THEME_NAME",
            "heat": "HOT/EMERGING/SUSTAINED/FADING",
            "catalyst": "what's driving this theme",
            "mention_count": number of headlines mentioning this,
            "primary_plays": ["TICKER1", "TICKER2"],
            "secondary_plays": ["TICKER3", "TICKER4"],
            "supply_chain": ["TICKER5"],
            "potential_losers": ["TICKER6"],
            "summary": "1-2 sentence summary"
        }}
    ],
    "early_signals": [
        {{
            "name": "POTENTIAL_THEME",
            "signal": "what you're seeing",
            "watch_list": ["TICKER1", "TICKER2"]
        }}
    ],
    "market_narrative": "Overall market story in 1-2 sentences"
}}

Focus on actionable trading themes. Identify both obvious plays AND less obvious beneficiaries."""

    try:
        response = requests.post(
            DEEPSEEK_API_URL,
            headers={
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "You are an expert market strategist who identifies trading themes and connects news to stock opportunities. Always respond with valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 1500
            },
            timeout=60
        )

        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']

            # Parse JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            return json.loads(content.strip())
        else:
            return detect_themes_keywords(headlines)

    except Exception as e:
        print(f"AI theme detection error: {e}")
        return detect_themes_keywords(headlines)


def detect_themes_keywords(headlines):
    """
    Fallback: Detect themes using keyword matching.
    """
    theme_counts = defaultdict(int)
    theme_tickers = defaultdict(set)

    for h in headlines:
        text = h['title'].lower()
        ticker = h['ticker']

        for theme_name, theme_data in THEME_DATABASE.items():
            for keyword in theme_data['keywords']:
                if keyword in text:
                    theme_counts[theme_name] += 1
                    theme_tickers[theme_name].add(ticker)
                    break

    # Build result
    themes = []
    for theme_name, count in sorted(theme_counts.items(), key=lambda x: -x[1]):
        if count >= 2:  # At least 2 mentions
            theme_data = THEME_DATABASE[theme_name]
            heat = 'HOT' if count >= 10 else ('EMERGING' if count >= 5 else 'SUSTAINED')

            themes.append({
                'name': theme_name.replace('_', ' '),
                'heat': heat,
                'catalyst': 'Multiple news mentions',
                'mention_count': count,
                'primary_plays': theme_data.get('primary', []),
                'secondary_plays': theme_data.get('secondary', []),
                'supply_chain': theme_data.get('supply_chain', []),
                'tickers_mentioned': list(theme_tickers[theme_name]),
            })

    return {
        'themes': themes[:10],
        'early_signals': [],
        'market_narrative': 'Theme detection based on keyword analysis.',
    }


# ============================================================
# THEME MOMENTUM TRACKING
# ============================================================

def load_theme_history():
    """Load historical theme data."""
    if THEME_HISTORY_FILE.exists():
        with open(THEME_HISTORY_FILE, 'r') as f:
            return json.load(f)
    return {'daily': {}, 'weekly': {}}


def save_theme_history(history):
    """Save theme history."""
    with open(THEME_HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2)


def update_theme_momentum(detected_themes):
    """
    Update theme momentum by comparing to historical data.
    """
    history = load_theme_history()
    today = datetime.now().strftime('%Y-%m-%d')

    # Current theme counts
    current = {}
    for theme in detected_themes.get('themes', []):
        name = theme['name'].upper().replace(' ', '_')
        current[name] = theme.get('mention_count', 1)

    # Store today's data
    history['daily'][today] = current

    # Keep only last 30 days
    dates = sorted(history['daily'].keys())
    if len(dates) > 30:
        for old_date in dates[:-30]:
            del history['daily'][old_date]

    save_theme_history(history)

    # Calculate momentum
    momentum = {}
    dates = sorted(history['daily'].keys())

    for theme_name in current:
        # Get counts over time
        counts = []
        for date in dates[-7:]:  # Last 7 days
            counts.append(history['daily'].get(date, {}).get(theme_name, 0))

        if len(counts) >= 2:
            # Calculate trend
            recent = sum(counts[-3:]) if len(counts) >= 3 else counts[-1]
            older = sum(counts[:-3]) if len(counts) > 3 else counts[0]

            if older == 0:
                trend = 'NEW' if recent > 0 else 'FLAT'
            elif recent > older * 1.5:
                trend = 'RISING'
            elif recent < older * 0.5:
                trend = 'FADING'
            else:
                trend = 'STABLE'

            momentum[theme_name] = {
                'trend': trend,
                'current': current[theme_name],
                'week_total': sum(counts),
            }

    return momentum


# ============================================================
# EARLY STORY DETECTION
# ============================================================

def find_early_stories(headlines, detected_themes):
    """
    Find potential early-stage stories that aren't mainstream yet.
    Looks for:
    1. New keywords appearing in headlines
    2. Unusual ticker combinations
    3. Supply chain connections
    """
    # Count all significant words
    word_counts = Counter()
    ticker_pairs = Counter()

    for h in headlines:
        words = re.findall(r'\b[a-zA-Z]{4,}\b', h['title'].lower())
        for word in words:
            if word not in ['that', 'this', 'with', 'from', 'have', 'will', 'stock', 'shares']:
                word_counts[word] += 1

    # Find words not in known themes
    known_keywords = set()
    for theme_data in THEME_DATABASE.values():
        for kw in theme_data['keywords']:
            known_keywords.update(kw.split())

    # Potential new themes
    new_signals = []
    for word, count in word_counts.most_common(20):
        if word not in known_keywords and count >= 3:
            # Find tickers associated with this word
            associated_tickers = set()
            for h in headlines:
                if word in h['title'].lower():
                    associated_tickers.add(h['ticker'])

            if len(associated_tickers) >= 2:
                new_signals.append({
                    'keyword': word,
                    'mentions': count,
                    'tickers': list(associated_tickers)[:5],
                })

    return new_signals[:5]


# ============================================================
# MAIN STORY DETECTION
# ============================================================

def run_story_detection(tickers=None):
    """
    Run full story detection pipeline with self-learning.
    """
    # 1. Aggregate news
    headlines = aggregate_market_news(tickers, max_per_ticker=8)

    if not headlines:
        return {
            'themes': [],
            'momentum': {},
            'early_signals': [],
            'learned_themes': {},
            'market_narrative': 'No news data available.',
        }

    # 2. Detect themes with AI
    detected = detect_themes_ai(headlines)

    # 3. Update momentum tracking
    momentum = update_theme_momentum(detected)

    # 4. Find early stories
    early = find_early_stories(headlines, detected)

    # 5. SELF-LEARNING: Learn from this detection
    learned = learn_from_detection(detected, headlines)

    # 6. Enhance themes with momentum and learned data
    for theme in detected.get('themes', []):
        name = theme['name'].upper().replace(' ', '_')
        if name in momentum:
            theme['momentum'] = momentum[name]

        # Add additional stocks from learning
        additional = get_additional_stock_mappings(name)
        if additional:
            theme['learned_stocks'] = additional

    # 7. Add learned/promoted themes that AI might have missed
    for promoted_name, promoted_data in learned.get('promoted', {}).items():
        # Check if already in detected themes
        existing = [t for t in detected.get('themes', [])
                   if t['name'].upper().replace(' ', '_') == promoted_name]
        if not existing:
            # Add as a detected theme
            detected['themes'].append({
                'name': promoted_name.replace('_', ' '),
                'heat': 'LEARNED',
                'catalyst': promoted_data.get('catalyst', 'Auto-detected theme'),
                'mention_count': promoted_data.get('total_mentions', 0),
                'primary_plays': promoted_data.get('primary_plays', []),
                'secondary_plays': promoted_data.get('secondary_plays', []),
                'is_learned': True,
            })

    # Add early signals
    if early and not detected.get('early_signals'):
        detected['early_signals'] = [
            {
                'name': f"Emerging: {s['keyword'].upper()}",
                'signal': f"{s['mentions']} mentions across {len(s['tickers'])} stocks",
                'watch_list': s['tickers'],
            }
            for s in early
        ]

    # 8. Add emerging learned themes to early signals
    for emerging_name, emerging_data in learned.get('emerging', {}).items():
        total = sum(emerging_data.get('mentions', {}).values())
        if total >= MIN_MENTIONS_TO_TRACK:
            top_stocks = sorted(emerging_data.get('stocks', {}).items(),
                              key=lambda x: -x[1]['count'])[:4]
            detected['early_signals'].append({
                'name': f"Learning: {emerging_name.replace('_', ' ')}",
                'signal': f"{total} mentions over {len(emerging_data.get('mentions', {}))} days",
                'watch_list': [s for s, _ in top_stocks],
                'is_learning': True,
            })

    detected['headline_count'] = len(headlines)
    detected['tickers_scanned'] = len(set(h['ticker'] for h in headlines))

    # 8b. Track theme lifecycles in comprehensive self-learning system
    try:
        from self_learning import track_theme_lifecycle

        for theme in detected.get('themes', []):
            theme_name = theme['name'].upper().replace(' ', '_')
            heat = theme.get('heat', 'WARM')
            primary_plays = theme.get('primary_plays', [])

            # Determine status from heat level
            if heat in ['HOT', 'VERY_HOT']:
                status = 'rising'
            elif heat == 'WARM':
                status = 'stable'
            elif heat == 'COOLING':
                status = 'fading'
            elif theme.get('is_learned'):
                status = 'emerging'
            else:
                status = 'stable'

            # Estimate momentum score from mention count or RS
            mention_count = theme.get('mention_count', 0)
            momentum_score = min(10, mention_count / 2) if mention_count else 5

            track_theme_lifecycle(
                theme_name=theme_name,
                status=status,
                top_stocks=primary_plays[:5],
                momentum_score=momentum_score
            )
    except Exception as e:
        pass  # Silent fail - don't break detection if learning fails

    # 9. Add alternative sources (podcasts, newsletters)
    if ALT_SOURCES_AVAILABLE:
        try:
            alt_content = aggregate_alt_sources()
            alt_analysis = extract_themes_from_alt_sources(alt_content)
            detected['alt_sources'] = alt_analysis
            detected['alt_source_count'] = alt_analysis.get('total_items', 0)
        except:
            pass

    return detected


def run_alt_sources_scan():
    """Run standalone alternative sources scan."""
    if not ALT_SOURCES_AVAILABLE:
        return {'error': 'Alternative sources module not available'}

    content = aggregate_alt_sources()
    analysis = extract_themes_from_alt_sources(content)
    return analysis


def run_ranked_detection():
    """
    Run story detection with smart ranking.
    Returns signals ranked by quality score.
    """
    # Run standard detection
    result = run_story_detection()

    if not RANKER_AVAILABLE:
        return result

    # Prepare signals for ranking
    signals_to_rank = []

    for theme in result.get('themes', []):
        # Build signal data for ranker
        signal_data = {
            'theme': theme.get('name', 'Unknown'),
            'sources': theme.get('sources', []),
            'tickers_mentioned': (
                theme.get('primary_plays', []) +
                theme.get('secondary_plays', []) +
                theme.get('learned_stocks', [])
            ),
            'catalyst': theme.get('catalyst', ''),
            'mention_count': theme.get('mention_count', 1),
            'smart_money_sentiment': theme.get('heat', 'NEUTRAL'),
            'retail_sentiment': 'NEUTRAL',  # Could enhance with StockTwits data
        }

        # Determine sources from where theme was detected
        if theme.get('is_learned'):
            signal_data['sources'] = ['AI Detection']
        elif not signal_data['sources']:
            # Infer sources from alt_sources if available
            alt = result.get('alt_sources', {})
            alt_themes = alt.get('themes', {})
            theme_key = theme.get('name', '').lower()
            if theme_key in alt_themes:
                signal_data['sources'] = [m['source'] for m in alt_themes[theme_key]]

        signals_to_rank.append(signal_data)

    # Rank signals
    ranked = rank_signals(signals_to_rank)

    # Record signals for accuracy tracking
    for signal in ranked[:5]:  # Track top 5
        try:
            record_signal(
                signal['theme'],
                signal.get('sources', []),
                signal.get('tickers_mentioned', [])[:5],
                signal.get('catalyst', '')
            )
        except:
            pass

    # Check past signal accuracy
    try:
        check_signal_accuracy()
    except:
        pass

    result['ranked_signals'] = ranked

    return result


def get_source_accuracy():
    """Get source accuracy leaderboard."""
    if not RANKER_AVAILABLE:
        return []

    return get_source_leaderboard()


# ============================================================
# FORMATTING FOR TELEGRAM
# ============================================================

def format_stories_report(result):
    """Format story detection results for Telegram."""
    heat_emoji = {
        'HOT': '🔥🔥🔥',
        'EMERGING': '📈',
        'SUSTAINED': '➡️',
        'FADING': '📉',
        'LEARNED': '🧠',  # Auto-learned theme
    }

    trend_emoji = {
        'RISING': '↑↑↑',
        'NEW': '🆕',
        'STABLE': '→',
        'FADING': '↓↓',
    }

    msg = "🎯 *STORIES IN PLAY*\n"
    msg += f"_{result.get('tickers_scanned', 0)} stocks scanned, {result.get('headline_count', 0)} headlines_\n\n"

    # Main themes
    themes = result.get('themes', [])
    if themes:
        for i, theme in enumerate(themes[:6], 1):
            heat = theme.get('heat', 'SUSTAINED')
            name = theme.get('name', 'Unknown')

            # Mark learned themes
            learned_tag = " 🧠" if theme.get('is_learned') else ""
            msg += f"*{i}. {name}*{learned_tag} {heat_emoji.get(heat, '')}\n"

            # Momentum
            momentum = theme.get('momentum', {})
            if momentum:
                trend = momentum.get('trend', 'STABLE')
                msg += f"   Trend: {trend_emoji.get(trend, '')} ({momentum.get('current', 0)} today)\n"

            # Catalyst
            if theme.get('catalyst'):
                msg += f"   📌 {theme['catalyst'][:60]}\n"

            # Plays
            primary = theme.get('primary_plays', [])
            if primary:
                msg += f"   🎯 Primary: `{'`, `'.join(primary[:4])}`\n"

            secondary = theme.get('secondary_plays', [])
            if secondary:
                msg += f"   🔗 Secondary: `{'`, `'.join(secondary[:3])}`\n"

            supply = theme.get('supply_chain', [])
            if supply:
                msg += f"   ⛓️ Supply chain: `{'`, `'.join(supply[:3])}`\n"

            # Learned additional stocks
            learned_stocks = theme.get('learned_stocks', [])
            if learned_stocks:
                msg += f"   🧠 Learned: `{'`, `'.join(learned_stocks[:3])}`\n"

            losers = theme.get('potential_losers', [])
            if losers:
                msg += f"   ⚠️ At risk: `{'`, `'.join(losers[:2])}`\n"

            msg += "\n"
    else:
        msg += "_No major themes detected_\n\n"

    # Early signals (including learning themes)
    early = result.get('early_signals', [])
    if early:
        # Separate learning themes from new signals
        learning = [s for s in early if s.get('is_learning')]
        new_signals = [s for s in early if not s.get('is_learning')]

        if new_signals:
            msg += "*🔍 EARLY SIGNALS:*\n"
            for signal in new_signals[:3]:
                name = signal.get('name', 'Unknown')
                watch = signal.get('watch_list', [])
                msg += f"• {name}\n"
                if signal.get('signal'):
                    msg += f"  _{signal['signal']}_\n"
                if watch:
                    msg += f"  Watch: `{'`, `'.join(watch[:4])}`\n"
            msg += "\n"

        if learning:
            msg += "*🧠 LEARNING (auto-tracking):*\n"
            for signal in learning[:3]:
                name = signal.get('name', 'Unknown').replace('Learning: ', '')
                watch = signal.get('watch_list', [])
                msg += f"• {name}\n"
                if signal.get('signal'):
                    msg += f"  _{signal['signal']}_\n"
                if watch:
                    msg += f"  Stocks: `{'`, `'.join(watch[:4])}`\n"
            msg += "\n"

    # Alt sources summary (podcasts/newsletters)
    alt_count = result.get('alt_source_count', 0)
    if alt_count > 0:
        alt = result.get('alt_sources', {})
        alt_themes = alt.get('themes', {})
        if alt_themes:
            top_alt_themes = sorted(alt_themes.items(), key=lambda x: -len(x[1]))[:3]
            msg += "*📻 PODCAST/NEWSLETTER BUZZ:*\n"
            for theme, mentions in top_alt_themes:
                sources = list(set(m['source'] for m in mentions))[:2]
                msg += f"• {theme.upper()} ({len(mentions)}x) - _{', '.join(sources)}_\n"
            msg += "\n"

    # Market narrative
    narrative = result.get('market_narrative', '')
    if narrative:
        msg += f"*📊 Market Narrative:*\n_{narrative}_"

    return msg


def format_single_story(theme_name):
    """Get detailed info on a specific story/theme."""
    result = run_story_detection()

    for theme in result.get('themes', []):
        if theme_name.lower() in theme.get('name', '').lower():
            msg = f"🎯 *{theme['name']}*\n\n"

            if theme.get('heat'):
                msg += f"*Status:* {theme['heat']}\n"

            if theme.get('catalyst'):
                msg += f"*Catalyst:* {theme['catalyst']}\n"

            if theme.get('summary'):
                msg += f"\n_{theme['summary']}_\n"

            msg += "\n*How to Play:*\n"

            if theme.get('primary_plays'):
                msg += f"🎯 *Primary:* `{'`, `'.join(theme['primary_plays'])}`\n"
                msg += "   _Direct exposure to the theme_\n"

            if theme.get('secondary_plays'):
                msg += f"🔗 *Secondary:* `{'`, `'.join(theme['secondary_plays'])}`\n"
                msg += "   _Indirect beneficiaries_\n"

            if theme.get('supply_chain'):
                msg += f"⛓️ *Supply Chain:* `{'`, `'.join(theme['supply_chain'])}`\n"
                msg += "   _Less obvious plays_\n"

            if theme.get('potential_losers'):
                msg += f"\n⚠️ *Potential Losers:* `{'`, `'.join(theme['potential_losers'])}`\n"

            return msg

    return f"Theme '{theme_name}' not found in current stories."


# ============================================================
# MAIN
# ============================================================

if __name__ == '__main__':
    print("Running story detection...")
    result = run_story_detection()
    print(format_stories_report(result))
