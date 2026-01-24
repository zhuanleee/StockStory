#!/usr/bin/env python3
"""
Story Detector - Identifies emerging market themes and stories

Features:
1. Theme Scanner - Aggregates news across 50+ tickers to identify themes
2. Theme Momentum - Tracks theme mentions over time
3. Early Story Detection - Finds themes not yet priced in
4. Story-to-Stock Mapping - Connects themes to beneficiary stocks
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
    Run full story detection pipeline.
    """
    # 1. Aggregate news
    headlines = aggregate_market_news(tickers, max_per_ticker=8)

    if not headlines:
        return {
            'themes': [],
            'momentum': {},
            'early_signals': [],
            'market_narrative': 'No news data available.',
        }

    # 2. Detect themes with AI
    detected = detect_themes_ai(headlines)

    # 3. Update momentum tracking
    momentum = update_theme_momentum(detected)

    # 4. Find early stories
    early = find_early_stories(headlines, detected)

    # 5. Enhance themes with momentum
    for theme in detected.get('themes', []):
        name = theme['name'].upper().replace(' ', '_')
        if name in momentum:
            theme['momentum'] = momentum[name]

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

    detected['headline_count'] = len(headlines)
    detected['tickers_scanned'] = len(set(h['ticker'] for h in headlines))

    return detected


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

            msg += f"*{i}. {name}* {heat_emoji.get(heat, '')}\n"

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

            losers = theme.get('potential_losers', [])
            if losers:
                msg += f"   ⚠️ At risk: `{'`, `'.join(losers[:2])}`\n"

            msg += "\n"
    else:
        msg += "_No major themes detected_\n\n"

    # Early signals
    early = result.get('early_signals', [])
    if early:
        msg += "*🔍 EARLY SIGNALS:*\n"
        for signal in early[:3]:
            name = signal.get('name', 'Unknown')
            watch = signal.get('watch_list', [])
            msg += f"• {name}\n"
            if signal.get('signal'):
                msg += f"  _{signal['signal']}_\n"
            if watch:
                msg += f"  Watch: `{'`, `'.join(watch[:4])}`\n"
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
