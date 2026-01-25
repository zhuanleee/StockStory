#!/usr/bin/env python3
"""
Fast Story Detection with Parallel Fetching, Caching, and Background Refresh

Optimizations:
1. Parallel fetching - All sources fetched simultaneously
2. Caching - Results cached for 10 minutes
3. Background refresh - Auto-updates every 5 minutes
"""

import os
import json
import time
import threading
import requests
from datetime import datetime, timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict

# Cache configuration
CACHE_DIR = Path('cache')
CACHE_DIR.mkdir(exist_ok=True)
CACHE_DURATION = 600  # 10 minutes
BACKGROUND_REFRESH_INTERVAL = 300  # 5 minutes

# Global cache
_story_cache = {
    'data': None,
    'timestamp': 0,
    'lock': threading.Lock()
}

# Background refresh thread
_refresh_thread = None
_refresh_running = False


# =============================================================================
# PARALLEL NEWS FETCHING
# =============================================================================

def fetch_finviz_news(ticker):
    """Fetch news from Finviz."""
    try:
        url = f"https://finviz.com/quote.ashx?t={ticker}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)

        if response.status_code != 200:
            return []

        import re
        news_pattern = r'<a[^>]*class="tab-link-news"[^>]*>([^<]+)</a>'
        headlines = re.findall(news_pattern, response.text)

        return [{'title': h, 'source': 'finviz', 'ticker': ticker} for h in headlines[:5]]
    except:
        return []


def fetch_yahoo_news(ticker):
    """Fetch news from Yahoo Finance."""
    try:
        import yfinance as yf
        stock = yf.Ticker(ticker)
        news = stock.news or []

        return [{'title': n.get('title', ''), 'source': 'yahoo', 'ticker': ticker}
                for n in news[:5] if n.get('title')]
    except:
        return []


def fetch_google_news(query):
    """Fetch from Google News RSS."""
    try:
        import feedparser
        url = f"https://news.google.com/rss/search?q={query}+stock&hl=en-US&gl=US&ceid=US:en"
        feed = feedparser.parse(url)

        return [{'title': e.title, 'source': 'google', 'ticker': query}
                for e in feed.entries[:5]]
    except:
        return []


def fetch_stocktwits(ticker):
    """Fetch from StockTwits."""
    try:
        url = f"https://api.stocktwits.com/api/2/streams/symbol/{ticker}.json"
        response = requests.get(url, timeout=5)

        if response.status_code != 200:
            return []

        data = response.json()
        messages = data.get('messages', [])[:10]

        return [{'title': m.get('body', '')[:100], 'source': 'stocktwits', 'ticker': ticker,
                'sentiment': m.get('entities', {}).get('sentiment', {}).get('basic')}
                for m in messages]
    except:
        return []


def fetch_all_sources_parallel(tickers, max_workers=10):
    """Fetch from all sources in parallel."""
    all_headlines = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []

        for ticker in tickers:
            # Submit all fetch tasks
            futures.append(executor.submit(fetch_finviz_news, ticker))
            futures.append(executor.submit(fetch_yahoo_news, ticker))
            futures.append(executor.submit(fetch_stocktwits, ticker))

        # Also fetch general market news
        futures.append(executor.submit(fetch_google_news, 'stock+market'))
        futures.append(executor.submit(fetch_google_news, 'AI+semiconductor'))
        futures.append(executor.submit(fetch_google_news, 'tech+stocks'))

        # Collect results as they complete
        for future in as_completed(futures):
            try:
                result = future.result()
                if result:
                    all_headlines.extend(result)
            except:
                pass

    return all_headlines


# =============================================================================
# FAST THEME DETECTION (Keyword-based for speed)
# =============================================================================

THEME_KEYWORDS = {
    'AI_INFRASTRUCTURE': ['nvidia', 'nvda', 'ai chip', 'gpu', 'data center', 'artificial intelligence', 'chatgpt', 'openai', 'llm', 'inference', 'ai server'],
    'HBM_MEMORY': ['hbm', 'high bandwidth memory', 'micron', 'sk hynix', 'memory', 'dram', 'hbm3', 'hbm4'],
    'SEMICONDUCTOR': ['semiconductor', 'chip', 'foundry', 'tsmc', 'asml', 'amd', 'intel', 'fab', 'wafer'],
    'GLP1_OBESITY': ['glp-1', 'ozempic', 'wegovy', 'mounjaro', 'obesity', 'weight loss', 'eli lilly', 'novo nordisk', 'zepbound'],
    'NUCLEAR': ['nuclear', 'uranium', 'smr', 'small modular reactor', 'constellation', 'cameco', 'nuclear power', 'reactor'],
    'EV_BATTERY': ['ev', 'electric vehicle', 'tesla', 'battery', 'lithium', 'charging', 'solid state'],
    'CRYPTO_BITCOIN': ['bitcoin', 'crypto', 'btc', 'ethereum', 'coinbase', 'microstrategy', 'etf', 'btc etf'],
    'CLOUD_INFRASTRUCTURE': ['cloud', 'aws', 'azure', 'google cloud', 'data center', 'saas', 'hyperscaler'],
    'CYBERSECURITY': ['cybersecurity', 'security', 'crowdstrike', 'palo alto', 'hack', 'breach', 'ransomware', 'zero trust'],
    'QUANTUM': ['quantum', 'quantum computing', 'ionq', 'rigetti', 'qubit', 'supremacy'],
    'ROBOTICS': ['robot', 'humanoid', 'automation', 'boston dynamics', 'figure', 'optimus'],
    'SPACE': ['space', 'spacex', 'rocket', 'satellite', 'starlink', 'lunar', 'orbit'],
    # New themes
    'DEFENSE_AEROSPACE': ['defense', 'aerospace', 'military', 'pentagon', 'lockheed', 'raytheon', 'boeing'],
    'CHINA_TRADE': ['china', 'tariff', 'trade war', 'xi jinping', 'beijing', 'decoupling'],
    'INTEREST_RATES': ['fed', 'rate cut', 'rate hike', 'powell', 'fomc', 'inflation', 'cpi'],
    'EARNINGS_SEASON': ['earnings', 'beat', 'miss', 'guidance', 'outlook', 'eps'],
    'FINTECH_PAYMENTS': ['fintech', 'payments', 'visa', 'mastercard', 'paypal', 'square', 'digital payments'],
    'STREAMING_MEDIA': ['streaming', 'netflix', 'disney+', 'hulu', 'subscriber', 'content'],
    'BIOTECH_PHARMA': ['biotech', 'fda', 'approval', 'trial', 'drug', 'pipeline', 'clinical'],
    'REAL_ESTATE': ['real estate', 'housing', 'mortgage', 'reit', 'commercial', 'homebuilder'],
}

THEME_TICKERS = {
    'AI_INFRASTRUCTURE': ['NVDA', 'AMD', 'AVGO', 'MRVL', 'TSM', 'SMCI', 'ARM', 'DELL'],
    'HBM_MEMORY': ['MU', 'WDC', 'STX', 'LRCX'],
    'SEMICONDUCTOR': ['NVDA', 'AMD', 'INTC', 'TSM', 'ASML', 'AMAT', 'LRCX', 'KLAC', 'ON', 'NXPI'],
    'GLP1_OBESITY': ['LLY', 'NVO', 'AMGN', 'VKTX', 'PFE'],
    'NUCLEAR': ['CEG', 'VST', 'CCJ', 'UEC', 'SMR', 'OKLO', 'NRG'],
    'EV_BATTERY': ['TSLA', 'RIVN', 'LCID', 'ALB', 'SQM', 'LAC', 'QS'],
    'CRYPTO_BITCOIN': ['MSTR', 'COIN', 'MARA', 'RIOT', 'CLSK', 'HUT'],
    'CLOUD_INFRASTRUCTURE': ['AMZN', 'MSFT', 'GOOGL', 'CRM', 'NOW', 'SNOW', 'NET'],
    'CYBERSECURITY': ['CRWD', 'PANW', 'FTNT', 'ZS', 'S', 'OKTA'],
    'QUANTUM': ['IONQ', 'RGTI', 'QBTS', 'IBM', 'GOOGL'],
    'ROBOTICS': ['ISRG', 'ROK', 'TER', 'ABB'],
    'SPACE': ['RKLB', 'LUNR', 'ASTS', 'SPCE', 'BA'],
    # New theme tickers
    'DEFENSE_AEROSPACE': ['LMT', 'RTX', 'NOC', 'GD', 'BA', 'HII'],
    'CHINA_TRADE': ['BABA', 'JD', 'PDD', 'NIO', 'BIDU'],
    'INTEREST_RATES': ['JPM', 'BAC', 'WFC', 'GS', 'MS'],
    'EARNINGS_SEASON': [],  # Dynamic based on earnings
    'FINTECH_PAYMENTS': ['V', 'MA', 'PYPL', 'SQ', 'AFRM', 'SOFI'],
    'STREAMING_MEDIA': ['NFLX', 'DIS', 'WBD', 'PARA', 'ROKU'],
    'BIOTECH_PHARMA': ['MRNA', 'REGN', 'VRTX', 'BIIB', 'GILD', 'BMY'],
    'REAL_ESTATE': ['AMT', 'PLD', 'CCI', 'SPG', 'DHI', 'LEN'],
}


def load_theme_history():
    """Load previous theme counts for momentum tracking."""
    path = CACHE_DIR / 'theme_history.json'
    if path.exists():
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except:
            pass
    return {}


def save_theme_history(current_counts):
    """Save current theme counts for future comparison."""
    path = CACHE_DIR / 'theme_history.json'
    data = {
        'timestamp': time.time(),
        'counts': current_counts,
    }
    with open(path, 'w') as f:
        json.dump(data, f)


def detect_themes_fast(headlines):
    """Fast keyword-based theme detection with momentum tracking."""
    theme_counts = defaultdict(lambda: {'count': 0, 'headlines': [], 'sentiment': []})

    for item in headlines:
        title = item.get('title', '').lower()
        ticker = item.get('ticker', '').upper()
        sentiment = item.get('sentiment')

        for theme, keywords in THEME_KEYWORDS.items():
            # Check keyword match
            keyword_match = any(kw in title for kw in keywords)

            # Check ticker match
            ticker_match = ticker in THEME_TICKERS.get(theme, [])

            if keyword_match or ticker_match:
                theme_counts[theme]['count'] += 1
                theme_counts[theme]['headlines'].append(item)
                if sentiment:
                    theme_counts[theme]['sentiment'].append(sentiment)

    # Load previous counts for momentum
    prev_history = load_theme_history()
    prev_counts = prev_history.get('counts', {})

    # Sort by count
    sorted_themes = sorted(theme_counts.items(), key=lambda x: -x[1]['count'])

    # Format results with momentum
    themes = []
    current_counts = {}

    for theme_name, data in sorted_themes[:15]:  # Track more themes
        current_counts[theme_name] = data['count']

        if data['count'] >= 2:  # Minimum mentions
            # Calculate sentiment
            sentiments = data['sentiment']
            bullish = sentiments.count('Bullish')
            bearish = sentiments.count('Bearish')

            # Calculate momentum (vs previous scan)
            prev_count = prev_counts.get(theme_name, 0)
            momentum_change = data['count'] - prev_count

            if momentum_change > 2:
                momentum = 'HEATING_UP'
            elif momentum_change < -2:
                momentum = 'COOLING_DOWN'
            else:
                momentum = 'STABLE'

            # Determine heat level
            if bullish > bearish and data['count'] >= 5:
                heat = 'HOT'
            elif data['count'] >= 5:
                heat = 'WARM'
            elif momentum == 'HEATING_UP':
                heat = 'EMERGING'
            else:
                heat = 'NEUTRAL'

            themes.append({
                'name': theme_name.replace('_', ' ').title(),
                'heat': heat,
                'mention_count': data['count'],
                'momentum': momentum,
                'momentum_change': momentum_change,
                'primary_plays': THEME_TICKERS.get(theme_name, [])[:5],
                'sample_headlines': [h['title'][:60] for h in data['headlines'][:3]],
                'bullish_count': bullish,
                'bearish_count': bearish,
            })

    # Save current counts for next comparison
    save_theme_history(current_counts)

    return themes


def detect_momentum_stocks(headlines):
    """Detect stocks with high mention momentum."""
    ticker_counts = defaultdict(lambda: {'count': 0, 'bullish': 0, 'bearish': 0})

    for item in headlines:
        ticker = item.get('ticker', '').upper()
        if ticker and len(ticker) <= 5:
            ticker_counts[ticker]['count'] += 1

            sentiment = item.get('sentiment')
            if sentiment == 'Bullish':
                ticker_counts[ticker]['bullish'] += 1
            elif sentiment == 'Bearish':
                ticker_counts[ticker]['bearish'] += 1

    # Sort by count
    sorted_tickers = sorted(ticker_counts.items(), key=lambda x: -x[1]['count'])

    momentum = []
    for ticker, data in sorted_tickers[:10]:
        if data['count'] >= 3:
            sentiment_score = data['bullish'] - data['bearish']
            momentum.append({
                'ticker': ticker,
                'mentions': data['count'],
                'sentiment': 'Bullish' if sentiment_score > 0 else ('Bearish' if sentiment_score < 0 else 'Neutral'),
                'bullish': data['bullish'],
                'bearish': data['bearish'],
            })

    return momentum


# =============================================================================
# CACHING
# =============================================================================

def get_cache_path():
    """Get cache file path."""
    return CACHE_DIR / 'stories_cache.json'


def load_cache():
    """Load cached stories."""
    cache_path = get_cache_path()
    if cache_path.exists():
        try:
            with open(cache_path, 'r') as f:
                data = json.load(f)
                if time.time() - data.get('timestamp', 0) < CACHE_DURATION:
                    return data
        except:
            pass
    return None


def save_cache(data):
    """Save stories to cache."""
    cache_path = get_cache_path()
    data['timestamp'] = time.time()
    data['cached_at'] = datetime.now().isoformat()

    with open(cache_path, 'w') as f:
        json.dump(data, f, indent=2, default=str)


def invalidate_cache():
    """Force cache refresh on next call."""
    cache_path = get_cache_path()
    if cache_path.exists():
        cache_path.unlink()


# =============================================================================
# MAIN DETECTION FUNCTIONS
# =============================================================================

def run_fast_story_detection(tickers=None, use_cache=True):
    """
    Run fast story detection with parallel fetching and caching.

    Returns results in ~2-5 seconds instead of 30+ seconds.
    """
    # Check cache first
    if use_cache:
        cached = load_cache()
        if cached:
            cached['from_cache'] = True
            return cached

    # Expanded default tickers (40 stocks across hot themes)
    if tickers is None:
        tickers = [
            # AI/Semis
            'NVDA', 'AMD', 'AVGO', 'MRVL', 'MU', 'TSM', 'SMCI', 'ARM',
            # Big Tech
            'AAPL', 'MSFT', 'GOOGL', 'META', 'AMZN', 'TSLA',
            # Healthcare/GLP-1
            'LLY', 'NVO', 'AMGN', 'MRNA',
            # Nuclear/Energy
            'CEG', 'VST', 'CCJ', 'UEC', 'SMR', 'OKLO',
            # Crypto
            'MSTR', 'COIN', 'MARA', 'RIOT',
            # Cybersecurity
            'CRWD', 'PANW', 'ZS', 'FTNT',
            # Cloud/Software
            'CRM', 'NOW', 'PLTR', 'SNOW',
            # Quantum
            'IONQ', 'RGTI', 'QBTS',
            # Space
            'RKLB', 'LUNR', 'ASTS',
        ]

    start_time = time.time()

    # Parallel fetch from all sources
    headlines = fetch_all_sources_parallel(tickers)

    # Fast theme detection
    themes = detect_themes_fast(headlines)

    # Detect momentum stocks
    momentum = detect_momentum_stocks(headlines)

    elapsed = time.time() - start_time

    result = {
        'themes': themes,
        'momentum_stocks': momentum,
        'headline_count': len(headlines),
        'tickers_scanned': len(tickers),
        'detection_time': round(elapsed, 2),
        'timestamp': datetime.now().isoformat(),
        'from_cache': False,
    }

    # Save to cache
    save_cache(result)

    return result


def format_fast_stories_report(result):
    """Format stories for Telegram with momentum indicators."""
    from_cache = result.get('from_cache', False)
    cache_indicator = " (cached)" if from_cache else ""

    msg = f"🎯 *STORIES IN PLAY*{cache_indicator}\n\n"

    themes = result.get('themes', [])
    if themes:
        for t in themes[:8]:
            heat = t.get('heat', 'WARM')
            momentum = t.get('momentum', 'STABLE')

            # Heat emoji
            if heat == 'HOT':
                emoji = "🔥"
            elif heat == 'WARM':
                emoji = "📈"
            elif heat == 'EMERGING':
                emoji = "🌱"
            else:
                emoji = "⚪"

            # Momentum indicator
            if momentum == 'HEATING_UP':
                momentum_icon = "⬆️"
            elif momentum == 'COOLING_DOWN':
                momentum_icon = "⬇️"
            else:
                momentum_icon = ""

            msg += f"{emoji} *{t['name']}* ({t['mention_count']}){momentum_icon}\n"

            plays = t.get('primary_plays', [])
            if plays:
                msg += f"   `{'` `'.join(plays[:4])}`\n"
    else:
        msg += "_No hot themes detected_\n"

    # Heating up section
    heating = [t for t in themes if t.get('momentum') == 'HEATING_UP']
    if heating:
        msg += "\n*⬆️ HEATING UP:*\n"
        for t in heating[:3]:
            change = t.get('momentum_change', 0)
            msg += f"   {t['name']} (+{change} mentions)\n"

    # Momentum stocks
    momentum_stocks = result.get('momentum_stocks', [])
    if momentum_stocks:
        msg += "\n*📊 Trending Tickers:*\n"
        for m in momentum_stocks[:5]:
            sent_emoji = "🟢" if m['sentiment'] == 'Bullish' else ("🔴" if m['sentiment'] == 'Bearish' else "⚪")
            msg += f"{sent_emoji} `{m['ticker']}` - {m['mentions']} mentions\n"

    msg += f"\n_Scanned {result.get('headline_count', 0)} headlines in {result.get('detection_time', 0)}s_"

    return msg


# =============================================================================
# BACKGROUND REFRESH
# =============================================================================

def _background_refresh_worker():
    """Background worker that refreshes stories periodically."""
    global _refresh_running

    while _refresh_running:
        try:
            # Run detection (bypasses cache to get fresh data)
            result = run_fast_story_detection(use_cache=False)
            print(f"[Background] Stories refreshed: {len(result.get('themes', []))} themes detected")
        except Exception as e:
            print(f"[Background] Refresh error: {e}")

        # Wait for next refresh
        for _ in range(BACKGROUND_REFRESH_INTERVAL):
            if not _refresh_running:
                break
            time.sleep(1)


def start_background_refresh():
    """Start background refresh thread."""
    global _refresh_thread, _refresh_running

    if _refresh_thread is not None and _refresh_thread.is_alive():
        return  # Already running

    _refresh_running = True
    _refresh_thread = threading.Thread(target=_background_refresh_worker, daemon=True)
    _refresh_thread.start()
    print("[Background] Story refresh started (every 5 min)")


def stop_background_refresh():
    """Stop background refresh thread."""
    global _refresh_running
    _refresh_running = False
    print("[Background] Story refresh stopped")


# =============================================================================
# AI-ENHANCED DETECTION (Optional - uses DeepSeek for deeper analysis)
# =============================================================================

def enhance_with_ai(themes, headlines):
    """Optionally enhance theme detection with AI analysis."""
    api_key = os.environ.get('DEEPSEEK_API_KEY')
    if not api_key:
        return themes

    try:
        # Only call AI for top themes
        top_headlines = [h['title'] for h in headlines[:30]]

        prompt = f"""Analyze these stock market headlines and identify the top 3 emerging themes:

Headlines:
{json.dumps(top_headlines, indent=2)}

Current detected themes: {[t['name'] for t in themes[:5]]}

Respond in JSON:
{{
    "enhanced_themes": [
        {{"name": "theme name", "heat": "HOT/WARM/EMERGING", "catalyst": "what's driving it", "top_plays": ["TICKER1", "TICKER2"]}}
    ],
    "market_narrative": "one sentence summary"
}}"""

        response = requests.post(
            'https://api.deepseek.com/v1/chat/completions',
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 500,
                "temperature": 0.3,
            },
            timeout=10
        )

        if response.status_code == 200:
            content = response.json()['choices'][0]['message']['content']
            ai_result = json.loads(content)

            # Merge AI insights
            for ai_theme in ai_result.get('enhanced_themes', []):
                # Find matching theme and enhance it
                for theme in themes:
                    if ai_theme['name'].lower() in theme['name'].lower():
                        theme['catalyst'] = ai_theme.get('catalyst', '')
                        break

            return themes, ai_result.get('market_narrative', '')
    except:
        pass

    return themes, None


# =============================================================================
# STARTUP
# =============================================================================

# Auto-start background refresh when module is imported
# start_background_refresh()  # Uncomment to enable auto-start
