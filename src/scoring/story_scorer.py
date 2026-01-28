#!/usr/bin/env python3
"""
Story-First Stock Scorer

Primary focus: Find stocks with compelling stories/themes BEFORE the crowd.
Technical analysis is secondary confirmation only.

Story Score Components:
- Theme Heat (25%): Is stock part of a hot/emerging theme?
- Catalyst Score (20%): Upcoming earnings, FDA, product launches?
- News Momentum (15%): Is news volume accelerating?
- Sentiment (15%): Bullish/bearish tone of coverage
- Technical Confirmation (25%): RS, trend, volume combined

Data Sources:
- Polygon.io - Primary price data & fundamentals
- Finnhub - Professional news (free tier)
- Google News RSS - Fallback news source
- DeepSeek AI - Sentiment analysis
- StockTwits - Social sentiment & retail buzz
- Reddit (r/wallstreetbets, r/stocks) - Retail momentum
- X/Twitter - Real-time social sentiment via xAI x_search (engagement-weighted)
- SEC EDGAR - Institutional filings (13F, 8-K)
"""
import requests
from datetime import datetime
import re

from utils import get_logger, normalize_dataframe_columns
import param_helper as params  # Learned parameters

logger = get_logger(__name__)

# Import DeepSeek sentiment (replaces yfinance for news)
try:
    from src.sentiment.deepseek_sentiment import (
        fetch_news_free,
        calculate_sentiment_score as deepseek_sentiment_score,
    )
    HAS_DEEPSEEK_SENTIMENT = True
except ImportError:
    HAS_DEEPSEEK_SENTIMENT = False
    logger.debug("DeepSeek sentiment not available")

# Import Polygon provider for price data (replaces yfinance)
try:
    from src.data.polygon_provider import (
        get_aggregates_sync,
    )
    HAS_POLYGON = True
except ImportError:
    HAS_POLYGON = False
    logger.debug("Polygon provider not available")

# Try to import learned theme registry
try:
    from theme_registry import (
        get_theme_membership_for_scoring,
        get_all_theme_tickers as get_learned_theme_tickers,
    )
    HAS_THEME_REGISTRY = True
except ImportError:
    HAS_THEME_REGISTRY = False
    logger.debug("Theme registry not available, using hardcoded themes")


# =============================================================================
# ADDITIONAL DATA SOURCES - Social & Institutional
# =============================================================================

def fetch_stocktwits_sentiment(ticker: str) -> dict:
    """
    Fetch sentiment from StockTwits API.

    Returns:
        - sentiment: 'bullish', 'bearish', or 'neutral'
        - message_volume: number of messages
        - trending: bool if trending
    """
    try:
        url = f"https://api.stocktwits.com/api/2/streams/symbol/{ticker}.json"
        resp = requests.get(url, timeout=10)

        if resp.status_code != 200:
            return {'sentiment': 'neutral', 'message_volume': 0, 'trending': False}

        data = resp.json()
        symbol_data = data.get('symbol', {})
        messages = data.get('messages', [])

        # Count sentiment from messages
        bullish = sum(1 for m in messages if m.get('entities', {}).get('sentiment', {}).get('basic') == 'Bullish')
        bearish = sum(1 for m in messages if m.get('entities', {}).get('sentiment', {}).get('basic') == 'Bearish')

        total = bullish + bearish
        if total > 0:
            bullish_pct = bullish / total
            if bullish_pct > 0.6:
                sentiment = 'bullish'
            elif bullish_pct < 0.4:
                sentiment = 'bearish'
            else:
                sentiment = 'neutral'
        else:
            sentiment = 'neutral'

        return {
            'sentiment': sentiment,
            'bullish_count': bullish,
            'bearish_count': bearish,
            'message_volume': len(messages),
            'trending': symbol_data.get('is_following', False),
            'watchlist_count': symbol_data.get('watchlist_count', 0),
        }
    except Exception as e:
        logger.debug(f"StockTwits fetch failed for {ticker}: {e}")
        return {'sentiment': 'neutral', 'message_volume': 0, 'trending': False}


def fetch_reddit_mentions(ticker: str, days_back: int = 7, use_xai: bool = True) -> dict:
    """
    Fetch mentions from Reddit.

    Uses xAI web_search (LiveSearch) if available, falls back to direct Reddit API.

    Returns:
        - mention_count: number of recent mentions
        - sentiment: estimated from post content
        - hot_posts: list of relevant posts
    """
    import os

    # Option to disable xAI for Reddit (for debugging or performance)
    if not use_xai:
        return _fetch_reddit_direct(ticker)

    client = _get_xai_client()
    if not client:
        logger.debug(f"XAI client not available, using direct Reddit API for {ticker}")
        return _fetch_reddit_direct(ticker)

    try:
        from xai_sdk.chat import user
        from xai_sdk.tools import web_search

        chat = client.chat.create(
            model=os.environ.get('XAI_MODEL', 'grok-4-1-fast'),
            tools=[web_search()],
        )

        # Search prompt for Reddit mentions
        search_prompt = f"""Search Reddit for recent posts (last {days_back} days) about ${ticker} stock.

Focus on: r/wallstreetbets, r/stocks, r/investing, r/options

Return JSON only:
{{"posts_found": 10, "bullish_posts": 6, "bearish_posts": 2, "overall_sentiment": "bullish", "total_upvotes": 5000, "total_comments": 500, "key_discussions": ["topic1"], "hot_posts": [{{"subreddit": "wallstreetbets", "title": "title", "sentiment": "bullish", "upvotes": 1000}}]}}"""

        chat.append(user(search_prompt))
        response = chat.sample()
        output_text = response.content

        # Parse response
        import json as json_module
        json_match = re.search(r'\{[\s\S]*\}', output_text)
        if not json_match:
            logger.warning(f"No JSON in xAI Reddit response for {ticker}, using direct API")
            return _fetch_reddit_direct(ticker)

        data = json_module.loads(json_match.group())
        posts_found = data.get('posts_found', 0)
        overall = data.get('overall_sentiment', 'neutral')

        # Map sentiment
        if overall == 'bullish':
            sentiment = 'bullish'
        elif overall == 'bearish':
            sentiment = 'bearish'
        elif posts_found > 0:
            sentiment = 'neutral'
        else:
            sentiment = 'quiet'

        return {
            'mention_count': posts_found,
            'total_score': data.get('total_upvotes', 0),
            'total_comments': data.get('total_comments', 0),
            'sentiment': sentiment,
            'bullish_count': data.get('bullish_posts', 0),
            'bearish_count': data.get('bearish_posts', 0),
            'key_discussions': data.get('key_discussions', []),
            'hot_posts': data.get('hot_posts', [])[:3],
        }

    except ImportError as e:
        logger.warning(f"xai_sdk import error: {e}, using direct Reddit API")
        return _fetch_reddit_direct(ticker)
    except Exception as e:
        logger.error(f"Reddit xAI error for {ticker}: {type(e).__name__}: {e}")
        return _fetch_reddit_direct(ticker)


def _fetch_reddit_direct(ticker: str) -> dict:
    """
    Fallback: Fetch mentions from Reddit using direct JSON API.
    Often rate-limited but works as backup.
    """
    subreddits = ['wallstreetbets', 'stocks', 'investing', 'options']
    mentions = []

    for sub in subreddits:
        try:
            url = f"https://www.reddit.com/r/{sub}/search.json"
            params = {
                'q': ticker,
                'restrict_sr': 'on',
                'sort': 'new',
                't': 'week',
                'limit': 10
            }
            headers = {'User-Agent': 'StockScanner/1.0'}

            resp = requests.get(url, params=params, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                posts = data.get('data', {}).get('children', [])

                for post in posts:
                    post_data = post.get('data', {})
                    title = post_data.get('title', '').upper()

                    if re.search(rf'\b{ticker}\b', title):
                        mentions.append({
                            'subreddit': sub,
                            'title': post_data.get('title', ''),
                            'score': post_data.get('score', 0),
                            'num_comments': post_data.get('num_comments', 0),
                            'created': post_data.get('created_utc', 0),
                        })
        except Exception as e:
            logger.debug(f"Reddit direct fetch failed for {ticker} in r/{sub}: {e}")
            continue

    total_score = sum(m['score'] for m in mentions)
    total_comments = sum(m['num_comments'] for m in mentions)

    if len(mentions) >= 3 and total_score > 100:
        sentiment = 'bullish'
    elif len(mentions) >= 1:
        sentiment = 'neutral'
    else:
        sentiment = 'quiet'

    return {
        'mention_count': len(mentions),
        'total_score': total_score,
        'total_comments': total_comments,
        'sentiment': sentiment,
        'hot_posts': mentions[:3],
    }


def fetch_x_sentiment(ticker: str, days_back: int = 7) -> dict:
    """
    Fetch sentiment from X/Twitter using xAI SDK with x_search tool.

    Uses xai_sdk with x_search capability for real-time X/Twitter data.
    Analyzes posts mentioning the stock ticker and determines sentiment.

    Returns:
        - post_count: number of relevant posts found
        - engagement_score: weighted engagement (0-100)
        - sentiment: 'bullish', 'bearish', or 'neutral'
        - top_posts: list of high-engagement posts
    """
    import os
    import math
    from datetime import datetime, timedelta

    api_key = os.environ.get('XAI_API_KEY', '')
    if not api_key:
        logger.debug(f"XAI_API_KEY not set, skipping X sentiment for {ticker}")
        return {
            'post_count': 0,
            'engagement_score': 0,
            'sentiment': 'unknown',
            'top_posts': [],
            'error': 'XAI_API_KEY not configured'
        }

    try:
        from xai_sdk import Client
        from xai_sdk.chat import user
        from xai_sdk.tools import x_search

        client = Client(api_key=api_key)
        chat = client.chat.create(
            model=os.environ.get('XAI_MODEL', 'grok-4-1-fast'),
            tools=[x_search()],
        )

        # Search prompt for stock sentiment - include date range in query
        search_prompt = f"""Search X/Twitter for recent posts (last {days_back} days) about ${ticker} stock.

Find posts discussing ${ticker} as an investment. Analyze the overall sentiment.

Return a JSON summary:
{{
    "posts_found": 5,
    "bullish_posts": 3,
    "bearish_posts": 1,
    "neutral_posts": 1,
    "overall_sentiment": "bullish",
    "key_themes": ["earnings beat", "AI growth"],
    "notable_posts": [
        {{"text": "summary of post", "sentiment": "bullish"}}
    ]
}}"""

        chat.append(user(search_prompt))
        response = chat.sample()
        output_text = response.content

        # Parse response
        import json as json_module
        json_match = re.search(r'\{[\s\S]*\}', output_text)
        if not json_match:
            logger.debug(f"No JSON found in xAI response for {ticker}")
            return {
                'post_count': 0,
                'engagement_score': 0,
                'sentiment': 'unknown',
                'top_posts': [],
            }

        data = json_module.loads(json_match.group())
        posts_found = data.get('posts_found', 0)
        bullish = data.get('bullish_posts', 0)
        bearish = data.get('bearish_posts', 0)
        overall = data.get('overall_sentiment', 'neutral')
        notable = data.get('notable_posts', [])

        # Calculate engagement score based on post volume and sentiment strength
        if posts_found > 0:
            sentiment_ratio = bullish / posts_found if posts_found > 0 else 0.5
            engagement_score = min(100, int(posts_found * 5 + sentiment_ratio * 50))
        else:
            engagement_score = 0

        return {
            'post_count': posts_found,
            'engagement_score': engagement_score,
            'sentiment': overall,
            'bullish_count': bullish,
            'bearish_count': bearish,
            'key_themes': data.get('key_themes', []),
            'top_posts': notable[:3],
        }

    except Exception as e:
        logger.error(f"X sentiment fetch failed for {ticker}: {e}")
        return {
            'post_count': 0,
            'engagement_score': 0,
            'sentiment': 'unknown',
            'top_posts': [],
            'error': str(e)
        }


def _fetch_x_sentiment_http(ticker: str, days_back: int = 7) -> dict:
    """Fallback HTTP implementation when xai_sdk is not available."""
    # Return empty result - SDK is preferred
    return {
        'post_count': 0,
        'engagement_score': 0,
        'sentiment': 'unknown',
        'top_posts': [],
        'error': 'xai_sdk not available, install with: pip install xai-sdk'
    }


def fetch_sec_filings(ticker: str) -> dict:
    """
    Fetch recent SEC filings from EDGAR.

    Key filings:
    - 8-K: Material events (earnings, M&A, leadership changes)
    - 13F: Institutional holdings (quarterly)
    - 4: Insider transactions
    - SC 13D/G: Large shareholder disclosures

    Returns:
        - recent_filings: list of filings
        - has_8k: bool if recent 8-K
        - insider_activity: bool if recent insider trades
    """
    try:
        # SEC EDGAR company search
        cik_url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={ticker}&type=&dateb=&owner=include&count=20&output=json"
        headers = {'User-Agent': 'StockScanner research@example.com'}

        resp = requests.get(cik_url, headers=headers, timeout=10)
        if resp.status_code != 200:
            return {'recent_filings': [], 'has_8k': False, 'insider_activity': False}

        # Try to parse filings
        filings = []
        has_8k = False
        insider_activity = False

        # Alternative: use SEC full-text search API
        search_url = f"https://efts.sec.gov/LATEST/search-index?q={ticker}&dateRange=custom&startdt=2024-01-01&enddt=2026-12-31"

        try:
            search_resp = requests.get(search_url, headers=headers, timeout=10)
            if search_resp.status_code == 200:
                search_data = search_resp.json()
                hits = search_data.get('hits', {}).get('hits', [])

                for hit in hits[:10]:
                    source = hit.get('_source', {})
                    form_type = source.get('form', '')
                    filed_date = source.get('file_date', '')

                    filings.append({
                        'form': form_type,
                        'date': filed_date,
                        'description': source.get('display_names', [''])[0] if source.get('display_names') else '',
                    })

                    if '8-K' in form_type:
                        has_8k = True
                    if form_type in ['4', '3', '5']:
                        insider_activity = True
        except Exception:
            pass

        return {
            'recent_filings': filings[:5],
            'filing_count': len(filings),
            'has_8k': has_8k,
            'insider_activity': insider_activity,
        }
    except Exception as e:
        logger.debug(f"SEC EDGAR fetch failed for {ticker}: {e}")
        return {'recent_filings': [], 'has_8k': False, 'insider_activity': False}


def get_social_buzz_score(ticker: str, include_x: bool = True) -> dict:
    """
    Combine all social sources into a unified buzz score.

    Sources:
        - StockTwits: Retail trader sentiment
        - Reddit: r/wallstreetbets, r/stocks, r/investing, r/options (via xAI web_search)
        - X/Twitter: Via xAI x_search (engagement-weighted)
        - SEC: 8-K filings, insider activity

    Returns:
        - buzz_score: 0-100
        - sources: breakdown by source
        - trending: bool
    """
    logger.info(f"[SOCIAL] Starting social buzz for {ticker}, include_x={include_x}")

    # X/Twitter via xAI x_search FIRST (to isolate any ordering issues)
    x_data = {'post_count': 0, 'engagement_score': 0, 'sentiment': 'unknown'}
    if include_x:
        try:
            logger.info(f"[SOCIAL] Fetching X for {ticker}")
            x_data = fetch_x_sentiment(ticker, days_back=7)
            logger.info(f"[SOCIAL] X done for {ticker}: {x_data.get('post_count', 0)} posts")
        except Exception as e:
            logger.error(f"[SOCIAL] X fetch failed for {ticker}: {type(e).__name__}: {e}")

    # Quick fetches (non-xAI)
    logger.info(f"[SOCIAL] Fetching StockTwits for {ticker}")
    stocktwits = fetch_stocktwits_sentiment(ticker)
    logger.info(f"[SOCIAL] StockTwits done for {ticker}")

    logger.info(f"[SOCIAL] Fetching SEC for {ticker}")
    sec = fetch_sec_filings(ticker)
    logger.info(f"[SOCIAL] SEC done for {ticker}")

    # Reddit: Use direct API
    reddit = {'mention_count': 0, 'total_score': 0, 'sentiment': 'quiet'}
    try:
        logger.info(f"[SOCIAL] Fetching Reddit for {ticker}")
        reddit = _fetch_reddit_direct(ticker)
        logger.info(f"[SOCIAL] Reddit done for {ticker}: {reddit.get('mention_count', 0)} mentions")
    except Exception as e:
        logger.error(f"[SOCIAL] Reddit fetch failed for {ticker}: {type(e).__name__}: {e}")

    # Calculate component scores using learned thresholds
    st_score = 0
    if stocktwits['message_volume'] > params.threshold_stocktwits_high():
        st_score = params.score_stocktwits_high()
    elif stocktwits['message_volume'] > params.threshold_stocktwits_medium():
        st_score = params.score_stocktwits_medium()
    elif stocktwits['message_volume'] > params.threshold_stocktwits_low():
        st_score = params.score_stocktwits_low()

    if stocktwits['sentiment'] == 'bullish':
        st_score += params.score_stocktwits_bullish_boost()

    reddit_score = 0
    if reddit['mention_count'] >= params.threshold_reddit_high():
        reddit_score = params.score_stocktwits_high()  # Same scale as stocktwits
    elif reddit['mention_count'] >= params.threshold_reddit_medium():
        reddit_score = params.score_stocktwits_medium()
    elif reddit['mention_count'] >= 1:
        reddit_score = params.score_stocktwits_low()

    if reddit['total_score'] > params.threshold_reddit_score_high():
        reddit_score += params.score_stocktwits_bullish_boost()
    elif reddit['total_score'] > params.threshold_reddit_score_medium():
        reddit_score += params.score_stocktwits_low()

    # X/Twitter score (engagement-weighted)
    x_score = 0
    if x_data.get('post_count', 0) > 0:
        # Base score from engagement (already 0-100)
        x_score = min(30, x_data.get('engagement_score', 0) * 0.3)  # Cap at 30 pts

        # Sentiment boost
        if x_data.get('sentiment') == 'bullish':
            x_score += 10
        elif x_data.get('sentiment') == 'bearish':
            x_score -= 5  # Slight penalty for bearish

        # Volume boost for high post count
        if x_data.get('post_count', 0) >= 10:
            x_score += 5
        elif x_data.get('post_count', 0) >= 5:
            x_score += 2

    sec_score = 0
    if sec['has_8k']:
        sec_score += params.score_sec_8k()  # Material event
    if sec['insider_activity']:
        sec_score += params.score_sec_insider()  # Insider buying/selling

    # Combined buzz score (now includes X/Twitter)
    buzz_score = min(100, st_score + reddit_score + x_score + sec_score)

    # Is it trending?
    trending = (
        stocktwits.get('trending', False) or
        reddit['mention_count'] >= params.threshold_trending_reddit_mentions() or
        x_data.get('engagement_score', 0) >= 50 or  # High X engagement
        sec['has_8k']
    )

    return {
        'buzz_score': buzz_score,
        'trending': trending,
        'stocktwits': stocktwits,
        'reddit': reddit,
        'x_twitter': x_data,  # New: X/Twitter data
        'sec': sec,
        'component_scores': {  # New: breakdown for debugging
            'stocktwits': st_score,
            'reddit': reddit_score,
            'x_twitter': x_score,
            'sec': sec_score,
        }
    }


# =============================================================================
# THEME DEFINITIONS - The stories that move markets
# =============================================================================

THEMES = {
    # AI / Semiconductors
    'ai_infrastructure': {
        'name': 'AI Infrastructure',
        'drivers': ['NVDA', 'AMD', 'AVGO'],
        'beneficiaries': ['SMCI', 'DELL', 'HPE', 'VRT', 'ANET'],
        'picks_shovels': ['MRVL', 'ARM', 'CDNS', 'SNPS', 'ASML', 'KLAC', 'LRCX', 'AMAT'],
        'keywords': ['ai', 'artificial intelligence', 'gpu', 'data center', 'nvidia', 'chip'],
        'stage': 'middle',  # early, middle, late

        # Sub-themes for deeper ecosystem mapping
        'sub_themes': {
            'HBM_Memory': {
                'tickers': ['MU'],
                'driver_correlation': 0.87,
            },
            'CoWoS_Packaging': {
                'tickers': ['TSM'],
                'driver_correlation': 0.82,
            },
            'AI_Networking': {
                'tickers': ['AVGO', 'MRVL', 'ANET'],
                'driver_correlation': 0.79,
            },
            'AI_Power_Cooling': {
                'tickers': ['VRT', 'ETN', 'PWR'],
                'driver_correlation': 0.71,
            },
        },

        # Infrastructure enablers
        'infrastructure': ['EQIX', 'DLR', 'AMT'],
    },
    'ai_software': {
        'name': 'AI Software & Applications',
        'drivers': ['MSFT', 'GOOGL', 'META'],
        'beneficiaries': ['CRM', 'NOW', 'PLTR', 'AI', 'PATH', 'SNOW'],
        'picks_shovels': ['MDB', 'DDOG', 'NET', 'CRWD'],
        'keywords': ['copilot', 'chatgpt', 'generative ai', 'llm', 'machine learning'],
        'stage': 'middle',
    },

    # Energy Transition
    'nuclear_renaissance': {
        'name': 'Nuclear Renaissance',
        'drivers': ['CEG', 'VST'],
        'beneficiaries': ['CCJ', 'UEC', 'DNN', 'LEU', 'UUUU'],
        'picks_shovels': ['SMR', 'OKLO', 'NNE'],
        'keywords': ['nuclear', 'uranium', 'smr', 'small modular', 'power demand', 'data center power'],
        'stage': 'early',
    },
    'clean_energy': {
        'name': 'Clean Energy',
        'drivers': ['FSLR', 'ENPH'],
        'beneficiaries': ['SEDG', 'RUN', 'NOVA', 'ARRY'],
        'picks_shovels': ['ALB', 'SQM', 'LAC', 'LTHM'],
        'keywords': ['solar', 'renewable', 'clean energy', 'ira', 'tax credit'],
        'stage': 'middle',
    },

    # Healthcare
    'glp1_obesity': {
        'name': 'GLP-1 / Obesity',
        'drivers': ['LLY', 'NVO'],
        'beneficiaries': ['VKTX', 'AMGN', 'GPCR'],
        'picks_shovels': ['TMO', 'WST', 'CRL'],
        'keywords': ['glp-1', 'obesity', 'weight loss', 'ozempic', 'wegovy', 'mounjaro', 'zepbound'],
        'stage': 'middle',
    },
    'biotech_catalysts': {
        'name': 'Biotech Catalysts',
        'drivers': [],  # Dynamic based on FDA calendar
        'beneficiaries': [],
        'picks_shovels': ['ICLR', 'MEDP', 'CRL'],
        'keywords': ['fda', 'approval', 'pdufa', 'phase 3', 'clinical trial'],
        'stage': 'ongoing',
    },

    # Crypto / Digital Assets
    'crypto_cycle': {
        'name': 'Crypto Cycle',
        'drivers': ['MSTR', 'COIN'],
        'beneficiaries': ['MARA', 'RIOT', 'CLSK', 'HUT', 'BITF'],
        'picks_shovels': ['SQ', 'PYPL', 'HOOD'],
        'keywords': ['bitcoin', 'crypto', 'etf', 'halving', 'btc', 'ethereum'],
        'stage': 'middle',
    },

    # Defense / Aerospace
    'defense_spending': {
        'name': 'Defense Spending',
        'drivers': ['LMT', 'RTX', 'NOC'],
        'beneficiaries': ['GD', 'BA', 'HII', 'LHX'],
        'picks_shovels': ['HWM', 'TDG', 'AXON'],
        'keywords': ['defense', 'military', 'pentagon', 'ukraine', 'nato', 'missile'],
        'stage': 'middle',
    },

    # Consumer
    'china_recovery': {
        'name': 'China Recovery',
        'drivers': ['BABA', 'PDD', 'JD'],
        'beneficiaries': ['BIDU', 'NIO', 'XPEV', 'LI'],
        'picks_shovels': ['WYNN', 'LVS', 'SBUX'],
        'keywords': ['china', 'stimulus', 'reopening', 'chinese consumer'],
        'stage': 'early',
    },

    # Financials
    'rate_sensitive': {
        'name': 'Rate Sensitive',
        'drivers': ['JPM', 'GS', 'MS'],
        'beneficiaries': ['SCHW', 'IBKR', 'HOOD'],
        'picks_shovels': ['CME', 'ICE', 'CBOE'],
        'keywords': ['fed', 'rate cut', 'interest rate', 'yield curve', 'banking'],
        'stage': 'middle',
    },

    # Infrastructure
    'reshoring': {
        'name': 'Reshoring / CHIPS Act',
        'drivers': ['INTC', 'TSM'],
        'beneficiaries': ['AMAT', 'LRCX', 'KLAC', 'TER'],
        'picks_shovels': ['VMC', 'MLM', 'URI', 'CAT'],
        'keywords': ['reshoring', 'chips act', 'semiconductor', 'onshoring', 'manufacturing'],
        'stage': 'early',
    },

    # Space
    'space_economy': {
        'name': 'Space Economy',
        'drivers': ['RKLB', 'LUNR'],
        'beneficiaries': ['ASTS', 'BKSY', 'PL'],
        'picks_shovels': ['BA', 'LMT', 'RTX'],
        'keywords': ['space', 'satellite', 'launch', 'spacex', 'starlink', 'rocket'],
        'stage': 'early',
    },

    # Quantum
    'quantum_computing': {
        'name': 'Quantum Computing',
        'drivers': ['IONQ', 'RGTI'],
        'beneficiaries': ['QBTS', 'QUBT'],
        'picks_shovels': ['IBM', 'GOOGL', 'MSFT'],
        'keywords': ['quantum', 'qubit', 'quantum computer', 'quantum computing'],
        'stage': 'early',
    },
}

# Catalyst types and their typical impact
CATALYST_TYPES = {
    'earnings': {'impact': 'high', 'window_days': 14, 'keywords': ['earnings', 'q1', 'q2', 'q3', 'q4', 'results', 'guidance']},
    'fda': {'impact': 'very_high', 'window_days': 30, 'keywords': ['fda', 'approval', 'pdufa', 'nda', 'bla']},
    'product_launch': {'impact': 'high', 'window_days': 30, 'keywords': ['launch', 'unveil', 'announce', 'release', 'new product']},
    'conference': {'impact': 'medium', 'window_days': 7, 'keywords': ['conference', 'investor day', 'analyst day', 'presentation']},
    'merger': {'impact': 'very_high', 'window_days': 90, 'keywords': ['merger', 'acquisition', 'deal', 'buyout', 'takeover']},
    'split': {'impact': 'medium', 'window_days': 30, 'keywords': ['split', 'stock split']},
    'dividend': {'impact': 'low', 'window_days': 14, 'keywords': ['dividend', 'special dividend', 'payout']},
    'buyback': {'impact': 'medium', 'window_days': 30, 'keywords': ['buyback', 'repurchase', 'share repurchase']},
}


# =============================================================================
# STORY SCORING FUNCTIONS
# =============================================================================

def get_theme_membership(ticker: str) -> list:
    """Get all themes a ticker belongs to, including learned and discovered themes."""
    themes = []

    # PRIORITY 1: Check learned theme registry (dynamic membership)
    if HAS_THEME_REGISTRY:
        try:
            learned_themes = get_theme_membership_for_scoring(ticker)
            for theme in learned_themes:
                themes.append({
                    'theme_id': theme['theme_id'],
                    'theme_name': theme['theme_name'],
                    'role': theme['role'],
                    'stage': theme['stage'],
                    'confidence': theme.get('confidence', 0.8),
                    'is_learned': True,
                })
        except Exception as e:
            logger.debug(f"Could not load learned themes: {e}")

    # PRIORITY 2: Check hardcoded themes (fallback / bootstrap)
    for theme_id, theme in THEMES.items():
        # Skip if already found in learned themes
        if any(t['theme_id'] == theme_id for t in themes):
            continue

        all_tickers = (
            theme.get('drivers', []) +
            theme.get('beneficiaries', []) +
            theme.get('picks_shovels', [])
        )
        if ticker in all_tickers:
            role = 'driver' if ticker in theme.get('drivers', []) else \
                   'beneficiary' if ticker in theme.get('beneficiaries', []) else 'picks_shovels'
            themes.append({
                'theme_id': theme_id,
                'theme_name': theme['name'],
                'role': role,
                'stage': theme.get('stage', 'unknown'),
                'is_learned': False,
            })

    # PRIORITY 3: Check discovered themes from evolution engine
    try:
        from evolution_engine import get_discovered_themes
        for theme in get_discovered_themes():
            # Skip if already found
            if any(t['theme_id'] == theme['id'] for t in themes):
                continue

            if ticker in theme.get('stocks', []):
                themes.append({
                    'theme_id': theme['id'],
                    'theme_name': theme['name'],
                    'role': 'discovered',
                    'stage': theme.get('lifecycle_stage', 'unknown'),
                    'confidence': theme.get('confidence', 0.7),
                    'discovery_method': theme.get('discovery_method', 'auto'),
                })
    except ImportError:
        pass
    except Exception as e:
        logger.debug(f"Could not load discovered themes: {e}")

    return themes


def calculate_theme_heat(ticker: str, news_data: list = None) -> dict:
    """
    Calculate theme heat score for a ticker.

    Returns:
        - score: 0-100 theme heat score
        - themes: list of active themes
        - hottest_theme: the most active theme
    """
    themes = get_theme_membership(ticker)

    if not themes:
        return {'score': 0, 'themes': [], 'hottest_theme': None, 'role': None}

    # Score based on:
    # 1. Number of themes (more = higher potential)
    # 2. Role in theme (driver > beneficiary > picks_shovels)
    # 3. Theme stage (early > middle > late for alpha)
    # 4. News mentions of theme keywords

    role_scores = params.get_role_scores()
    stage_scores = params.get_stage_scores()

    best_score = 0
    hottest_theme = None
    best_role = None

    for theme in themes:
        role_score = role_scores.get(theme['role'], 50)
        stage_score = stage_scores.get(theme['stage'], 50)

        # Combined theme score
        theme_score = (role_score * 0.6) + (stage_score * 0.4)

        # Bonus for early stage themes (alpha opportunity)
        if theme['stage'] == 'early':
            theme_score *= params.multiplier_early_stage_boost()

        if theme_score > best_score:
            best_score = theme_score
            hottest_theme = theme['theme_name']
            best_role = theme['role']

    # Check news for theme keyword mentions (if provided)
    if news_data:
        keyword_boost = 0
        for theme in themes:
            theme_def = THEMES.get(theme['theme_id'], {})
            keywords = theme_def.get('keywords', [])
            for article in news_data:
                title = article.get('title', '').lower()
                summary = article.get('summary', '').lower()
                text = title + ' ' + summary
                if any(kw in text for kw in keywords):
                    keyword_boost += 5
        best_score = min(100, best_score + keyword_boost)

    return {
        'score': round(min(100, best_score), 1),
        'themes': themes,
        'hottest_theme': hottest_theme,
        'role': best_role,
    }


def detect_catalysts(ticker: str, news_data: list = None) -> dict:
    """
    Detect upcoming catalysts for a ticker.

    Uses Polygon API for dividends/splits and news-based earnings detection.

    Returns:
        - score: 0-100 catalyst proximity score
        - catalysts: list of detected catalysts
        - next_catalyst: nearest upcoming catalyst
    """
    import os
    catalysts = []

    # Check for earnings mentions in news (keyword-based detection)
    if news_data:
        earnings_keywords = ['earnings', 'quarterly results', 'q1', 'q2', 'q3', 'q4',
                           'fiscal', 'revenue report', 'guidance']
        for article in news_data[:10]:
            title = article.get('title', '').lower()
            if any(kw in title for kw in earnings_keywords):
                # Check if it mentions upcoming vs past
                if any(word in title for word in ['upcoming', 'ahead', 'preview', 'expect', 'tomorrow', 'next week']):
                    catalysts.append({
                        'type': 'earnings',
                        'date': 'upcoming',
                        'days_away': 7,  # Approximate
                        'impact': 'high',
                        'source': 'news',
                    })
                    break

    # Check for upcoming dividends (Polygon)
    polygon_key = os.environ.get('POLYGON_API_KEY', '')
    if polygon_key:
        try:
            from src.data.polygon_provider import get_dividends_sync, get_stock_splits_sync

            # Check dividends
            dividends = get_dividends_sync(ticker, limit=5)
            for div in dividends:
                ex_date = div.get('ex_dividend_date')
                if ex_date:
                    try:
                        ex_date_obj = datetime.strptime(ex_date, '%Y-%m-%d').date()
                        days_away = (ex_date_obj - datetime.now().date()).days
                        if 0 <= days_away <= 14:
                            catalysts.append({
                                'type': 'dividend',
                                'date': ex_date,
                                'days_away': days_away,
                                'impact': 'low',
                                'amount': div.get('cash_amount'),
                                'pay_date': div.get('pay_date'),
                            })
                            break  # Only add nearest dividend
                    except ValueError:
                        pass

            # Check stock splits
            splits = get_stock_splits_sync(ticker, limit=5)
            for split in splits:
                exec_date = split.get('execution_date')
                if exec_date:
                    try:
                        exec_date_obj = datetime.strptime(exec_date, '%Y-%m-%d').date()
                        days_away = (exec_date_obj - datetime.now().date()).days
                        if -7 <= days_away <= 30:  # Include recent splits
                            catalysts.append({
                                'type': 'split',
                                'date': exec_date,
                                'days_away': days_away,
                                'impact': 'medium',
                                'ratio': split.get('ratio_str'),
                                'is_forward': split.get('is_forward_split'),
                            })
                            break  # Only add nearest split
                    except ValueError:
                        pass
        except Exception as e:
            logger.debug(f"Polygon catalyst check failed for {ticker}: {e}")

    # Check news for catalyst keywords
    if news_data:
        for cat_type, cat_info in CATALYST_TYPES.items():
            for article in news_data[:10]:
                title = article.get('title', '').lower()
                summary = article.get('summary', '').lower()
                text = title + ' ' + summary

                if any(kw in text for kw in cat_info['keywords']):
                    # Avoid duplicates
                    if not any(c['type'] == cat_type for c in catalysts):
                        catalysts.append({
                            'type': cat_type,
                            'source': 'news',
                            'headline': article.get('title', '')[:100],
                            'impact': cat_info['impact'],
                        })

    # Calculate score
    if not catalysts:
        return {'score': 0, 'catalysts': [], 'next_catalyst': None}

    impact_scores = params.get_catalyst_impact_scores()
    best_score = 0
    next_catalyst = None

    for cat in catalysts:
        impact = impact_scores.get(cat.get('impact', 'medium'), 50)

        # Boost for imminent catalysts
        days = cat.get('days_away', 14)
        if days <= 7:
            impact *= params.multiplier_catalyst_near_7d()
        elif days <= 14:
            impact *= params.multiplier_catalyst_near_14d()

        if impact > best_score:
            best_score = impact
            next_catalyst = cat

    return {
        'score': round(min(100, best_score), 1),
        'catalysts': catalysts,
        'next_catalyst': next_catalyst,
    }


def calculate_news_momentum(ticker: str, news_data: list = None) -> dict:
    """
    Calculate news momentum - is coverage increasing?

    Returns:
        - score: 0-100 news momentum score
        - article_count: number of recent articles
        - momentum: 'accelerating', 'stable', 'declining'
    """
    if not news_data:
        # Try to fetch news from free sources
        if HAS_DEEPSEEK_SENTIMENT:
            try:
                news_data = fetch_news_free(ticker, limit=20)
            except Exception:
                news_data = []
        else:
            news_data = []

    if not news_data:
        return {'score': 30, 'article_count': 0, 'momentum': 'unknown'}

    # Count articles by recency
    now = datetime.now()
    last_24h = 0
    last_3d = 0
    last_7d = 0

    for article in news_data:
        try:
            # Handle different date formats
            content = article.get('content', article)
            pub_date = content.get('pubDate', content.get('providerPublishTime', ''))

            if isinstance(pub_date, str):
                pub_dt = datetime.fromisoformat(pub_date.replace('Z', '+00:00'))
            elif isinstance(pub_date, (int, float)):
                pub_dt = datetime.fromtimestamp(pub_date)
            else:
                continue

            pub_dt = pub_dt.replace(tzinfo=None)
            age = now - pub_dt

            if age.days < 1:
                last_24h += 1
            if age.days < 3:
                last_3d += 1
            if age.days < 7:
                last_7d += 1
        except Exception:
            continue

    # Calculate momentum
    if last_3d > 0:
        daily_avg_recent = last_3d / 3
        daily_avg_older = (last_7d - last_3d) / 4 if last_7d > last_3d else 0.5

        if daily_avg_recent > daily_avg_older * 1.5:
            momentum = 'accelerating'
            score = 80 + min(20, last_24h * 5)
        elif daily_avg_recent > daily_avg_older * 0.8:
            momentum = 'stable'
            score = 50 + min(30, last_3d * 5)
        else:
            momentum = 'declining'
            score = 30
    else:
        momentum = 'quiet'
        score = 20

    return {
        'score': round(min(100, score), 1),
        'article_count': last_7d,
        'last_24h': last_24h,
        'momentum': momentum,
    }


def calculate_sentiment_score(ticker: str, news_data: list = None) -> dict:
    """
    Calculate sentiment from news headlines.

    Uses DeepSeek AI for sentiment analysis if available, otherwise falls back
    to keyword-based sentiment scoring.

    Returns:
        - score: 0-100 (50 = neutral, >50 = bullish, <50 = bearish)
        - sentiment: 'bullish', 'bearish', 'neutral'
        - confidence: how confident we are in the sentiment
    """
    # Try DeepSeek sentiment first (more accurate)
    if HAS_DEEPSEEK_SENTIMENT:
        try:
            result = deepseek_sentiment_score(ticker, news_data)
            sentiment = 'bullish' if result['score'] >= 60 else 'bearish' if result['score'] <= 40 else 'neutral'
            confidence = 'high' if result.get('article_count', 0) >= 10 else 'medium' if result.get('article_count', 0) >= 5 else 'low'
            return {
                'score': result['score'],
                'sentiment': sentiment,
                'confidence': confidence,
                'label': result.get('label', sentiment),
                'positive_ratio': result.get('positive_ratio', 0.5),
                'article_count': result.get('article_count', 0),
            }
        except Exception as e:
            logger.debug(f"DeepSeek sentiment failed for {ticker}: {e}")

    # Fallback to keyword-based sentiment
    if not news_data:
        if HAS_DEEPSEEK_SENTIMENT:
            try:
                news_data = fetch_news_free(ticker, limit=15)
            except Exception:
                news_data = []
        else:
            news_data = []

    if not news_data:
        return {'score': 50, 'sentiment': 'neutral', 'confidence': 'low'}

    bullish_words = [
        'beat', 'beats', 'surge', 'surges', 'jump', 'jumps', 'soar', 'soars',
        'record', 'high', 'upgrade', 'buy', 'bullish', 'growth', 'strong',
        'outperform', 'raises', 'boost', 'accelerate', 'breakout', 'rally',
        'demand', 'opportunity', 'positive', 'exceed', 'exceeds'
    ]

    bearish_words = [
        'miss', 'misses', 'drop', 'drops', 'fall', 'falls', 'plunge', 'plunges',
        'low', 'downgrade', 'sell', 'bearish', 'weak', 'concern', 'risk',
        'underperform', 'cuts', 'slowing', 'decline', 'warning', 'trouble',
        'investigation', 'lawsuit', 'recall', 'negative', 'disappointing'
    ]

    bullish_count = 0
    bearish_count = 0
    total_articles = 0

    for article in news_data[:15]:
        try:
            content = article.get('content', article)
            title = str(content.get('title', '')).lower()
            summary = str(content.get('summary', '')).lower()
            text = title + ' ' + summary

            total_articles += 1

            bull_matches = sum(1 for w in bullish_words if w in text)
            bear_matches = sum(1 for w in bearish_words if w in text)

            if bull_matches > bear_matches:
                bullish_count += 1
            elif bear_matches > bull_matches:
                bearish_count += 1
        except Exception:
            continue

    if total_articles == 0:
        return {'score': 50, 'sentiment': 'neutral', 'confidence': 'low'}

    # Calculate score
    total_sentiment = bullish_count + bearish_count
    if total_sentiment > 0:
        bullish_pct = bullish_count / total_sentiment
        score = 50 + (bullish_pct - 0.5) * 100  # -50 to +50 range added to 50
    else:
        score = 50

    score = max(0, min(100, score))

    # Determine sentiment label using learned thresholds
    if score >= params.threshold_sentiment_bullish():
        sentiment = 'bullish'
    elif score <= params.threshold_sentiment_bearish():
        sentiment = 'bearish'
    else:
        sentiment = 'neutral'

    # Confidence based on article count
    if total_articles >= params.get('threshold.confidence.high_articles', 10):
        confidence = 'high'
    elif total_articles >= params.get('threshold.confidence.medium_articles', 5):
        confidence = 'medium'
    else:
        confidence = 'low'

    return {
        'score': round(score, 1),
        'sentiment': sentiment,
        'confidence': confidence,
        'bullish_count': bullish_count,
        'bearish_count': bearish_count,
    }


def calculate_technical_confirmation(ticker: str, price_data=None) -> dict:
    """
    Calculate technical confirmation score (secondary to story).

    Returns:
        - score: 0-100 technical confirmation score
        - rs: relative strength vs SPY
        - trend: 'strong_up', 'up', 'neutral', 'down', 'strong_down'
        - volume: volume ratio
    """
    try:
        if price_data is None:
            # Use Polygon for price data
            if HAS_POLYGON:
                df = get_aggregates_sync(ticker, days=90)
                if df is not None:
                    df = normalize_dataframe_columns(df)
                else:
                    return {'score': 50, 'rs': 0, 'trend': 'unknown', 'volume': 1}
            else:
                return {'score': 50, 'rs': 0, 'trend': 'unknown', 'volume': 1}
        else:
            df = price_data

        if df is None or len(df) < 20:
            return {'score': 50, 'rs': 0, 'trend': 'unknown', 'volume': 1}

        close = df['Close']
        volume = df['Volume']

        # Handle case where close might be a Series with multi-index (from batch download)
        def safe_float(val):
            """Safely convert value to float, handling Series."""
            if hasattr(val, 'item'):
                return float(val.item())
            elif hasattr(val, 'iloc'):
                return float(val.iloc[0]) if len(val) > 0 else 0.0
            return float(val)

        current = safe_float(close.iloc[-1])

        # Moving averages
        sma_20 = safe_float(close.rolling(20).mean().iloc[-1])
        sma_50 = safe_float(close.rolling(50).mean().iloc[-1]) if len(close) >= 50 else sma_20

        # Trend score
        above_20 = current > sma_20
        above_50 = current > sma_50
        ma_aligned = sma_20 > sma_50

        trend_points = sum([above_20, above_50, ma_aligned])

        if trend_points == 3:
            trend = 'strong_up'
            trend_score = params.score_technical_trend_3()
        elif trend_points == 2:
            trend = 'up'
            trend_score = params.score_technical_trend_2()
        elif trend_points == 1:
            trend = 'neutral'
            trend_score = params.score_technical_trend_1()
        else:
            trend = 'down'
            trend_score = params.score_technical_trend_0()

        # Volume
        avg_vol = safe_float(volume.iloc[-20:].mean())
        vol_ratio = safe_float(volume.iloc[-1]) / avg_vol if avg_vol > 0 else 1

        vol_score = min(100, vol_ratio * params.multiplier_volume_score())

        # RS vs SPY (simplified)
        ret_20d = (current / safe_float(close.iloc[-20]) - 1) * 100 if len(close) >= 20 else 0

        try:
            # Use Polygon for SPY data
            if HAS_POLYGON:
                spy = get_aggregates_sync('SPY', days=30)
                if spy is not None:
                    spy = normalize_dataframe_columns(spy)
                    spy_close = spy['Close']
                    spy_ret = (safe_float(spy_close.iloc[-1]) / safe_float(spy_close.iloc[-20]) - 1) * 100
                    rs = ret_20d - spy_ret
                else:
                    rs = ret_20d
            else:
                rs = ret_20d
        except Exception:
            rs = ret_20d

        rs_score = max(0, min(100, 50 + rs * 5))  # +-10% RS = 0-100

        # Combined technical score
        score = (trend_score * 0.4) + (rs_score * 0.4) + (vol_score * 0.2)

        return {
            'score': round(score, 1),
            'rs': round(rs, 2),
            'trend': trend,
            'volume': round(vol_ratio, 2),
            'above_20sma': above_20,
            'above_50sma': above_50,
        }
    except Exception as e:
        logger.error(f"Technical calc error for {ticker}: {e}")
        return {'score': 50, 'rs': 0, 'trend': 'unknown', 'volume': 1}


# =============================================================================
# MAIN STORY SCORING FUNCTION
# =============================================================================

def calculate_story_score(ticker: str, news_data: list = None, price_data=None, include_social: bool = True) -> dict:
    """
    Calculate comprehensive story-first score for a ticker.

    Weights (updated with social):
    - Theme Heat: 20%
    - Catalyst: 20%
    - Social Buzz: 15% (StockTwits, Reddit, SEC)
    - News Momentum: 10%
    - Sentiment: 10%
    - Technical Confirmation: 25%

    Returns complete story profile for the ticker.
    """
    # Get news if not provided
    if news_data is None:
        if HAS_DEEPSEEK_SENTIMENT:
            try:
                news_data = fetch_news_free(ticker, limit=20)
            except Exception:
                news_data = []
        else:
            news_data = []

    # Ensure news_data is a list
    if news_data is None:
        news_data = []

    # Backwards compatibility: handle old yfinance format if present
    if news_data and len(news_data) > 0 and isinstance(news_data[0], dict) and 'content' in news_data[0]:
        processed_news = []
        for item in news_data:
            content = item.get('content', item)
            processed_news.append({
                'title': content.get('title', ''),
                'summary': content.get('summary', ''),
                'pubDate': content.get('pubDate', ''),
            })
        news_data = processed_news

    # Calculate all components
    theme = calculate_theme_heat(ticker, news_data)
    catalyst = detect_catalysts(ticker, news_data)
    news_momentum = calculate_news_momentum(ticker, news_data)
    sentiment = calculate_sentiment_score(ticker, news_data)
    technical = calculate_technical_confirmation(ticker, price_data)

    # Social buzz (StockTwits, Reddit, SEC EDGAR)
    if include_social:
        try:
            social = get_social_buzz_score(ticker)
        except Exception:
            social = {'buzz_score': 0, 'trending': False, 'stocktwits': {}, 'reddit': {}, 'sec': {}}
    else:
        social = {'buzz_score': 0, 'trending': False, 'stocktwits': {}, 'reddit': {}, 'sec': {}}

    # Calculate ecosystem score
    try:
        from ecosystem_intelligence import calculate_ecosystem_score
        ecosystem_data = calculate_ecosystem_score(ticker)
        ecosystem_score = ecosystem_data.get('score', 50)
    except Exception:
        ecosystem_data = {'score': 50, 'breakdown': {}, 'in_ecosystem': False}
        ecosystem_score = 50

    # Weighted composite score using learned weights
    weights = params.get_scoring_weights()
    composite = (
        theme['score'] * weights['theme_heat'] +
        catalyst['score'] * weights['catalyst'] +
        social['buzz_score'] * weights['social_buzz'] +
        news_momentum['score'] * weights['news_momentum'] +
        sentiment['score'] * weights['sentiment'] +
        ecosystem_score * weights['ecosystem'] +
        technical['score'] * weights['technical']
    )

    # Boost for trending stocks (social momentum)
    if social.get('trending', False):
        composite = min(100, composite * 1.1)

    # Boost for recent 8-K filings (material events)
    if social.get('sec', {}).get('has_8k', False):
        composite = min(100, composite + 5)

    # Theme Intelligence boost (Google Trends + multi-signal fusion)
    theme_intel_boost = 0
    theme_intel_data = {}
    try:
        from src.intelligence.theme_intelligence import get_ticker_theme_boost
        theme_intel_data = get_ticker_theme_boost(ticker)
        theme_intel_boost = theme_intel_data.get('boost', 0)
        if theme_intel_boost != 0:
            composite = max(0, min(100, composite + theme_intel_boost))
    except ImportError:
        pass
    except Exception as e:
        logger.debug(f"Theme intel boost error for {ticker}: {e}")

    # Story strength label
    if composite >= 80:
        story_strength = 'STRONG_STORY'
    elif composite >= 60:
        story_strength = 'GOOD_STORY'
    elif composite >= 40:
        story_strength = 'MODERATE_STORY'
    else:
        story_strength = 'WEAK_STORY'

    # Story stage (for stocks in themes)
    if theme['themes']:
        stages = [t['stage'] for t in theme['themes']]
        if 'early' in stages:
            story_stage = 'early'
        elif 'middle' in stages:
            story_stage = 'middle'
        else:
            story_stage = 'late'
    else:
        story_stage = 'no_theme'

    return {
        'ticker': ticker,
        'story_score': round(composite, 1),
        'story_strength': story_strength,
        'story_stage': story_stage,

        # Components
        'theme': theme,
        'catalyst': catalyst,
        'social': social,
        'news_momentum': news_momentum,
        'sentiment': sentiment,
        'technical': technical,
        'ecosystem': ecosystem_data,

        # Quick summary
        'hottest_theme': theme.get('hottest_theme'),
        'theme_role': theme.get('role'),
        'next_catalyst': catalyst.get('next_catalyst'),
        'news_trend': news_momentum.get('momentum'),
        'sentiment_label': sentiment.get('sentiment'),
        'trend': technical.get('trend'),

        # Social summary
        'social_buzz': social.get('buzz_score', 0),
        'is_trending': social.get('trending', False),
        'reddit_mentions': social.get('reddit', {}).get('mention_count', 0),
        'stocktwits_volume': social.get('stocktwits', {}).get('message_volume', 0),
        'has_8k_filing': social.get('sec', {}).get('has_8k', False),

        # Ecosystem summary
        'ecosystem_score': ecosystem_score,
        'in_ecosystem': ecosystem_data.get('in_ecosystem', False),
        'ecosystem_themes': ecosystem_data.get('themes', []),

        # Theme Intelligence (Google Trends fusion)
        'theme_intel_boost': theme_intel_boost,
        'theme_intel': theme_intel_data,

        # For sorting/filtering
        'has_theme': len(theme.get('themes', [])) > 0,
        'has_catalyst': len(catalyst.get('catalysts', [])) > 0,
        'is_early_stage': story_stage == 'early',
    }


def scan_for_stories(tickers: list, max_workers: int = 10) -> list:
    """
    Scan multiple tickers for story scores.
    Returns sorted list with best stories first.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    results = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(calculate_story_score, ticker): ticker for ticker in tickers}

        for future in as_completed(futures, timeout=120):
            try:
                result = future.result(timeout=10)
                if result:
                    results.append(result)
            except Exception as e:
                ticker = futures[future]
                logger.debug(f"Story scan failed for {ticker}: {e}")

    # Sort by story score (best stories first)
    results.sort(key=lambda x: x['story_score'], reverse=True)

    return results


def get_theme_stocks(theme_id: str) -> dict:
    """Get all stocks in a specific theme with their roles."""
    if theme_id not in THEMES:
        return None

    theme = THEMES[theme_id]
    return {
        'theme_id': theme_id,
        'name': theme['name'],
        'stage': theme.get('stage', 'unknown'),
        'drivers': theme.get('drivers', []),
        'beneficiaries': theme.get('beneficiaries', []),
        'picks_shovels': theme.get('picks_shovels', []),
        'keywords': theme.get('keywords', []),
        'all_tickers': (
            theme.get('drivers', []) +
            theme.get('beneficiaries', []) +
            theme.get('picks_shovels', [])
        ),
    }


def get_all_theme_tickers() -> list:
    """Get all tickers that belong to any theme (learned + hardcoded)."""
    all_tickers = set()

    # Add learned theme tickers
    if HAS_THEME_REGISTRY:
        try:
            all_tickers.update(get_learned_theme_tickers())
        except Exception as e:
            logger.debug(f"Could not get learned theme tickers: {e}")

    # Add hardcoded theme tickers
    for theme in THEMES.values():
        all_tickers.update(theme.get('drivers', []))
        all_tickers.update(theme.get('beneficiaries', []))
        all_tickers.update(theme.get('picks_shovels', []))

    return list(all_tickers)


def get_early_stage_themes() -> list:
    """Get themes that are in early stage (highest alpha potential)."""
    early = []
    for theme_id, theme in THEMES.items():
        if theme.get('stage') == 'early':
            early.append({
                'theme_id': theme_id,
                'name': theme['name'],
                'drivers': theme.get('drivers', []),
                'beneficiaries': theme.get('beneficiaries', []),
            })
    return early


# =============================================================================
# CLI TESTING
# =============================================================================

if __name__ == '__main__':
    print("Testing Story Scorer...")

    # Test single stock
    test_tickers = ['NVDA', 'SMCI', 'CEG', 'LLY', 'MSTR', 'AAPL']

    for ticker in test_tickers:
        result = calculate_story_score(ticker)
        print(f"\n{'='*50}")
        print(f"{ticker}: {result['story_score']:.0f}/100 ({result['story_strength']})")
        print(f"  Theme: {result['hottest_theme'] or 'None'} ({result['theme_role'] or 'N/A'})")
        print(f"  Stage: {result['story_stage']}")
        print(f"  Catalyst: {result['next_catalyst']['type'] if result['next_catalyst'] else 'None'}")
        print(f"  News: {result['news_trend']} ({result['news_momentum']['article_count']} articles)")
        print(f"  Sentiment: {result['sentiment_label']}")
        print(f"  Technical: {result['trend']} (RS: {result['technical']['rs']:+.1f}%)")
