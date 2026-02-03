"""
X Intelligence - Social Sentiment via xAI Search
================================================
Uses xAI's Grok to search and analyze X/Twitter sentiment without Twitter API.

xAI Grok has real-time access to X posts and can analyze sentiment,
trending topics, and viral discussions.

Usage:
    from src.intelligence.x_intelligence import get_x_sentiment

    # Get X sentiment for a ticker
    sentiment = get_x_sentiment('NVDA')

    # Get trending topics
    trending = get_trending_stocks()
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from pathlib import Path
import time

logger = logging.getLogger(__name__)

# xAI API Configuration
XAI_API_KEY = os.environ.get('XAI_API_KEY', '')
XAI_BASE_URL = "https://api.x.ai/v1"

# Cache
DATA_DIR = Path("data/x_intelligence")
CACHE_FILE = DATA_DIR / "x_sentiment_cache.json"
CACHE_TTL = 900  # 15 minutes (X sentiment changes fast)


def ensure_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class XSentiment:
    """X/Twitter sentiment data for a ticker."""
    ticker: str
    sentiment: str  # bullish, bearish, neutral
    sentiment_score: float  # 0-1 (0=very bearish, 0.5=neutral, 1=very bullish)
    mention_count: int
    viral_posts: List[Dict]  # Top viral posts about the ticker
    trending: bool
    influencer_mentions: int  # Mentions by accounts with >100k followers
    timestamp: str


class XIntelligence:
    """
    X Intelligence using xAI Grok for sentiment analysis.

    No Twitter API needed - uses xAI's search capabilities.
    """

    def __init__(self):
        ensure_data_dir()
        self._cache = self._load_cache()
        self._cache_times = {}

    def _load_cache(self) -> Dict:
        """Load sentiment cache."""
        if CACHE_FILE.exists():
            try:
                with open(CACHE_FILE) as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load X sentiment cache: {e}")
        return {}

    def _save_cache(self):
        """Save sentiment cache."""
        try:
            with open(CACHE_FILE, 'w') as f:
                json.dump(self._cache, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save X sentiment cache: {e}")

    def _get_cached(self, key: str) -> Optional[Dict]:
        """Get cached data if still valid."""
        if key in self._cache:
            cached_time = self._cache[key].get('cached_at', 0)
            if time.time() - cached_time < CACHE_TTL:
                return self._cache[key].get('data')
        return None

    def _set_cached(self, key: str, data: Dict):
        """Cache data with timestamp."""
        self._cache[key] = {
            'cached_at': time.time(),
            'data': data
        }
        self._save_cache()

    def _call_xai_with_search(self, prompt: str, ticker: str = None) -> Optional[str]:
        """
        Call xAI Grok API with X search using the official xai_sdk.

        Args:
            prompt: The prompt to send
            ticker: Optional ticker for focused search
        """
        if not XAI_API_KEY:
            logger.warning("XAI_API_KEY not set - X Intelligence disabled")
            return None

        try:
            from xai_sdk import Client
            from xai_sdk.chat import user
            from xai_sdk.tools import x_search

            client = Client(api_key=XAI_API_KEY)

            # Create chat with X search tool enabled
            chat = client.chat.create(
                model="grok-3-fast",  # Fast model for quick responses
                tools=[
                    x_search(),  # Enable X search
                ],
            )

            # Append user message
            chat.append(user(prompt))

            # Get response (non-streaming)
            response_text = ""
            for chunk in chat.sample():
                if hasattr(chunk, 'text'):
                    response_text += chunk.text
                elif isinstance(chunk, str):
                    response_text += chunk

            return response_text if response_text else None

        except ImportError:
            logger.warning("xai_sdk not installed - falling back to REST API")
            return self._call_xai_rest(prompt)
        except Exception as e:
            logger.error(f"xAI SDK call failed: {e}")
            return self._call_xai_rest(prompt)

    def _call_xai_rest(self, prompt: str) -> Optional[str]:
        """Fallback REST API call without X search."""
        if not XAI_API_KEY:
            return None

        try:
            import requests

            headers = {
                'Authorization': f'Bearer {XAI_API_KEY}',
                'Content-Type': 'application/json'
            }

            payload = {
                'messages': [
                    {
                        'role': 'system',
                        'content': 'You are Grok. Analyze stock sentiment and provide JSON responses only.'
                    },
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ],
                'model': 'grok-3-fast',
                'stream': False,
                'temperature': 0
            }

            response = requests.post(
                f"{XAI_BASE_URL}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                return data['choices'][0]['message'].get('content', '')
            else:
                logger.error(f"xAI REST API error: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"xAI REST API call failed: {e}")
            return None

    def get_ticker_sentiment(self, ticker: str) -> XSentiment:
        """
        Get X sentiment for a ticker using xAI search.

        Args:
            ticker: Stock ticker symbol

        Returns:
            XSentiment object with analysis
        """
        # Check cache first
        cache_key = f"sentiment:{ticker}"
        cached = self._get_cached(cache_key)
        if cached:
            return XSentiment(**cached)

        # Build xAI search prompt
        prompt = f"""Search X for recent posts (last 24 hours) about ${ticker} stock ticker.

Analyze and return ONLY valid JSON (no markdown, no extra text) with this exact structure:
{{
    "ticker": "{ticker}",
    "sentiment": "bullish|bearish|neutral",
    "sentiment_score": 0.0-1.0,
    "mention_count": <number>,
    "viral_posts": [
        {{"text": "post text", "likes": <number>, "author": "username"}}
    ],
    "trending": true|false,
    "influencer_mentions": <number>
}}

Sentiment Rules:
- bullish if majority positive (buying, calls, moon, bullish)
- bearish if majority negative (selling, puts, crash, bearish)
- neutral if mixed or unclear
- sentiment_score: 0=very bearish, 0.5=neutral, 1.0=very bullish
- trending: true if >500 mentions in 24h
- influencer_mentions: count mentions from accounts >100k followers
- viral_posts: top 3 posts by engagement"""

        response_text = self._call_xai_with_search(prompt, ticker)

        if not response_text:
            # Return neutral default
            default = XSentiment(
                ticker=ticker,
                sentiment='neutral',
                sentiment_score=0.5,
                mention_count=0,
                viral_posts=[],
                trending=False,
                influencer_mentions=0,
                timestamp=datetime.now().isoformat()
            )
            return default

        # Parse JSON response
        try:
            # Clean response (remove markdown if present)
            cleaned = response_text.strip()
            if cleaned.startswith('```'):
                cleaned = '\n'.join(cleaned.split('\n')[1:-1])

            data = json.loads(cleaned)

            sentiment = XSentiment(
                ticker=data.get('ticker', ticker),
                sentiment=data.get('sentiment', 'neutral'),
                sentiment_score=float(data.get('sentiment_score', 0.5)),
                mention_count=int(data.get('mention_count', 0)),
                viral_posts=data.get('viral_posts', [])[:3],
                trending=bool(data.get('trending', False)),
                influencer_mentions=int(data.get('influencer_mentions', 0)),
                timestamp=datetime.now().isoformat()
            )

            # Cache result
            self._set_cached(cache_key, asdict(sentiment))

            return sentiment

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"Failed to parse xAI response for {ticker}: {e}")
            logger.debug(f"Response was: {response_text}")

            # Return neutral default
            default = XSentiment(
                ticker=ticker,
                sentiment='neutral',
                sentiment_score=0.5,
                mention_count=0,
                viral_posts=[],
                trending=False,
                influencer_mentions=0,
                timestamp=datetime.now().isoformat()
            )
            return default

    def get_trending_stocks(self, limit: int = 10) -> List[Dict]:
        """
        Get trending stock tickers on X.

        Returns list of tickers with mention counts.
        """
        cache_key = "trending_stocks"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        prompt = f"""Search X for the top {limit} most mentioned stock tickers in the last 24 hours.

Return ONLY valid JSON (no markdown, no extra text):
{{
    "trending_stocks": [
        {{"ticker": "NVDA", "mentions": 1234, "sentiment": "bullish"}},
        {{"ticker": "TSLA", "mentions": 987, "sentiment": "neutral"}}
    ]
}}

Focus on US stock tickers ($TICKER format).
Include mention count and overall sentiment."""

        response_text = self._call_xai_with_search(prompt)

        if not response_text:
            return []

        try:
            cleaned = response_text.strip()
            if cleaned.startswith('```'):
                cleaned = '\n'.join(cleaned.split('\n')[1:-1])

            data = json.loads(cleaned)
            trending = data.get('trending_stocks', [])

            # Cache result (5 minute cache for trending)
            self._cache[cache_key] = {
                'cached_at': time.time(),
                'data': trending
            }
            self._save_cache()

            return trending

        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse trending stocks: {e}")
            return []


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

_x_intelligence = None


def get_x_intelligence() -> XIntelligence:
    """Get or create singleton X Intelligence."""
    global _x_intelligence
    if _x_intelligence is None:
        _x_intelligence = XIntelligence()
    return _x_intelligence


def get_x_sentiment(ticker: str) -> Dict:
    """Get X sentiment for a ticker."""
    sentiment = get_x_intelligence().get_ticker_sentiment(ticker)
    return asdict(sentiment)


def get_trending_stocks(limit: int = 10) -> List[Dict]:
    """Get trending stocks on X."""
    return get_x_intelligence().get_trending_stocks(limit)


# =============================================================================
# TELEGRAM FORMATTING
# =============================================================================

def format_x_sentiment_message(data: Dict) -> str:
    """Format X sentiment for Telegram."""
    ticker = data.get('ticker', 'Unknown')
    sentiment = data.get('sentiment', 'neutral')
    score = data.get('sentiment_score', 0.5)
    mentions = data.get('mention_count', 0)
    trending = data.get('trending', False)
    influencers = data.get('influencer_mentions', 0)
    viral_posts = data.get('viral_posts', [])

    # Sentiment emoji
    if sentiment == 'bullish':
        emoji = '🟢'
    elif sentiment == 'bearish':
        emoji = '🔴'
    else:
        emoji = '🟡'

    msg = f"𝕏 *X INTELLIGENCE: ${ticker}*\n"
    msg += f"_Real-time social sentiment via xAI Grok_\n\n"

    msg += f"{emoji} *Sentiment:* {sentiment.upper()}\n"
    msg += f"📊 *Score:* {score:.2f} (0=bearish, 1=bullish)\n"
    msg += f"💬 *Mentions (24h):* {mentions:,}\n"

    if influencers > 0:
        msg += f"👥 *Influencer Mentions:* {influencers}\n"

    if trending:
        msg += f"🔥 *TRENDING* - High volume\n"

    if viral_posts:
        msg += f"\n📱 *Viral Posts:*\n"
        for i, post in enumerate(viral_posts[:3], 1):
            text = post.get('text', '')[:100]
            likes = post.get('likes', 0)
            author = post.get('author', 'unknown')
            msg += f"{i}. @{author} ({likes:,} likes)\n"
            msg += f"   _{text}_\n"

    msg += f"\n_Updated: {datetime.now().strftime('%H:%M:%S')}_"

    return msg
