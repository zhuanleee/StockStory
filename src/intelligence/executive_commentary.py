"""
Executive Commentary Intelligence
==================================
Track and analyze CEO/CFO commentary from multiple sources:

1. SEC 8-K Filings (significant events, often contain forward guidance)
2. Recent news articles mentioning executives
3. Social media (X/Twitter) - executive accounts
4. Press releases

Provides sentiment and guidance signals from management commentary.
"""

import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from pathlib import Path
import json

logger = logging.getLogger(__name__)

# Cache
DATA_DIR = Path("data/executive_commentary")
CACHE_FILE = DATA_DIR / "commentary_cache.json"
CACHE_TTL_HOURS = 12  # Commentary is time-sensitive


def ensure_data_dir():
    """Ensure data directory exists."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class ExecutiveComment:
    """A single executive comment or statement."""
    ticker: str
    executive_name: Optional[str]
    executive_title: Optional[str]  # CEO, CFO, etc.
    source: str  # sec_filing, news, social, press_release
    source_url: str
    date: str
    content: str  # The actual commentary
    sentiment: str  # bullish, neutral, bearish
    topics: List[str]  # [guidance, growth, margins, products, etc.]
    confidence: float  # 0-1


@dataclass
class ExecutiveCommentarySummary:
    """Summary of executive commentary for a ticker."""
    ticker: str
    recent_comments: List[ExecutiveComment]
    overall_sentiment: str  # bullish, neutral, bearish
    sentiment_score: float  # -1 to +1
    guidance_tone: str  # raised, maintained, lowered, none
    key_themes: List[str]
    has_recent_commentary: bool
    last_comment_date: Optional[str]
    timestamp: str


class ExecutiveCommentaryTracker:
    """
    Track and analyze executive commentary from multiple sources.
    """

    def __init__(self):
        ensure_data_dir()
        self.cache = self._load_cache()

    def _load_cache(self) -> Dict:
        """Load commentary cache."""
        if CACHE_FILE.exists():
            try:
                with open(CACHE_FILE) as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load commentary cache: {e}")
        return {}

    def _save_cache(self):
        """Save commentary cache."""
        try:
            with open(CACHE_FILE, 'w') as f:
                json.dump(self.cache, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save commentary cache: {e}")

    def _get_cached(self, ticker: str) -> Optional[ExecutiveCommentarySummary]:
        """Get cached commentary if still valid."""
        cache_key = f"commentary:{ticker}"
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            cached_time = datetime.fromisoformat(cached.get('timestamp', ''))
            age_hours = (datetime.now() - cached_time).seconds / 3600

            if age_hours < CACHE_TTL_HOURS:
                # Reconstruct objects
                summary = ExecutiveCommentarySummary(**cached)
                summary.recent_comments = [
                    ExecutiveComment(**c) for c in cached.get('recent_comments', [])
                ]
                return summary

        return None

    def _set_cached(self, ticker: str, summary: ExecutiveCommentarySummary):
        """Cache commentary summary."""
        cache_key = f"commentary:{ticker}"
        self.cache[cache_key] = asdict(summary)
        self._save_cache()

    def get_commentary(
        self,
        ticker: str,
        days_back: int = 30
    ) -> ExecutiveCommentarySummary:
        """
        Get executive commentary for ticker.

        Args:
            ticker: Stock ticker
            days_back: How many days back to look

        Returns:
            ExecutiveCommentarySummary
        """
        # Check cache
        cached = self._get_cached(ticker)
        if cached:
            logger.debug(f"Using cached commentary for {ticker}")
            return cached

        comments = []

        # Source 1: SEC 8-K filings (significant events)
        comments.extend(self._fetch_sec_8k_commentary(ticker, days_back))

        # Source 2: Recent news with executive quotes
        comments.extend(self._fetch_news_commentary(ticker, days_back))

        # Source 3: Social media (if we have executive handles)
        # Disabled for now as it requires Twitter API
        # comments.extend(self._fetch_social_commentary(ticker, days_back))

        # Source 4: Press releases
        comments.extend(self._fetch_press_releases(ticker, days_back))

        # Analyze comments
        summary = self._analyze_commentary(ticker, comments)

        # Cache result
        self._set_cached(ticker, summary)

        return summary

    def _fetch_sec_8k_commentary(
        self,
        ticker: str,
        days_back: int
    ) -> List[ExecutiveComment]:
        """Fetch commentary from SEC 8-K filings."""
        comments = []

        try:
            from src.data.sec_edgar import SECEdgarClient

            client = SECEdgarClient()
            filings = client.get_company_filings(
                ticker,
                form_types=['8-K'],
                days_back=days_back
            )

            for filing in filings[:5]:  # Limit to 5 most recent
                # 8-K filings contain significant events
                # Item 2.02: Results of Operations (earnings)
                # Item 7.01: Regulation FD Disclosure (often guidance)
                # Item 8.01: Other Events

                # Extract text from filing (simplified)
                content = filing.text_url if hasattr(filing, 'text_url') else ''

                if not content:
                    continue

                # Simple keyword extraction for guidance/commentary
                guidance_keywords = [
                    'outlook', 'guidance', 'expect', 'forecast',
                    'target', 'project', 'estimate', 'anticipate'
                ]

                content_lower = content.lower() if isinstance(content, str) else ''
                has_guidance = any(kw in content_lower for kw in guidance_keywords)

                if has_guidance:
                    # Detect sentiment from keywords
                    sentiment = self._detect_sentiment(content_lower)

                    comments.append(ExecutiveComment(
                        ticker=ticker,
                        executive_name=None,  # 8-K doesn't specify
                        executive_title='Management',
                        source='sec_8k',
                        source_url=filing.filing_url if hasattr(filing, 'filing_url') else '',
                        date=filing.filed_date if hasattr(filing, 'filed_date') else '',
                        content=content[:500],  # Preview
                        sentiment=sentiment,
                        topics=['guidance', 'outlook'],
                        confidence=0.6
                    ))

        except Exception as e:
            logger.debug(f"Error fetching 8-K for {ticker}: {e}")

        return comments

    def _fetch_news_commentary(
        self,
        ticker: str,
        days_back: int
    ) -> List[ExecutiveComment]:
        """Fetch executive quotes from news articles."""
        comments = []

        try:
            from src.data.polygon_provider import PolygonDataProvider

            provider = PolygonDataProvider()
            news = provider.get_ticker_news_sync(ticker, limit=20)

            if not news:
                return comments

            # Look for articles with executive quotes
            executive_keywords = [
                'ceo', 'chief executive', 'cfo', 'chief financial',
                'president', 'founder', 'chairman', 'said', 'commented'
            ]

            for article in news[:10]:  # Limit to 10 most recent
                title = article.get('title', '').lower()
                description = article.get('description', '').lower()

                # Check if article mentions executives
                has_executive_mention = any(
                    kw in title or kw in description
                    for kw in executive_keywords
                )

                if has_executive_mention:
                    # Extract executive name if possible
                    exec_name = self._extract_executive_name(
                        title + ' ' + description
                    )

                    sentiment = self._detect_sentiment(title + ' ' + description)

                    comments.append(ExecutiveComment(
                        ticker=ticker,
                        executive_name=exec_name,
                        executive_title=None,
                        source='news',
                        source_url=article.get('article_url', ''),
                        date=article.get('published_utc', ''),
                        content=description[:300],
                        sentiment=sentiment,
                        topics=self._extract_topics(title + ' ' + description),
                        confidence=0.7
                    ))

        except Exception as e:
            logger.debug(f"Error fetching news commentary for {ticker}: {e}")

        return comments

    def _fetch_press_releases(
        self,
        ticker: str,
        days_back: int
    ) -> List[ExecutiveComment]:
        """Fetch press releases (often contain executive quotes)."""
        comments = []

        try:
            from src.data.polygon_provider import PolygonDataProvider

            provider = PolygonDataProvider()
            news = provider.get_ticker_news_sync(ticker, limit=20)

            if not news:
                return comments

            # Filter for press releases
            for article in news:
                title = article.get('title', '').lower()
                publisher = article.get('publisher', {}).get('name', '').lower()

                # Common press release indicators
                is_press_release = (
                    'press release' in title or
                    'announces' in title or
                    'reports' in title or
                    'business wire' in publisher or
                    'pr newswire' in publisher or
                    'globe newswire' in publisher
                )

                if is_press_release:
                    description = article.get('description', '')
                    sentiment = self._detect_sentiment(title + ' ' + description)

                    comments.append(ExecutiveComment(
                        ticker=ticker,
                        executive_name=None,
                        executive_title='Management',
                        source='press_release',
                        source_url=article.get('article_url', ''),
                        date=article.get('published_utc', ''),
                        content=description[:300],
                        sentiment=sentiment,
                        topics=self._extract_topics(title + ' ' + description),
                        confidence=0.8  # Press releases are official
                    ))

        except Exception as e:
            logger.debug(f"Error fetching press releases for {ticker}: {e}")

        return comments

    def _detect_sentiment(self, text: str) -> str:
        """Simple sentiment detection from text."""
        text_lower = text.lower()

        # Bullish keywords
        bullish = [
            'strong', 'growth', 'increase', 'improve', 'beat',
            'exceed', 'outperform', 'expand', 'accelerate', 'positive',
            'optimistic', 'confident', 'raised guidance', 'upgrade'
        ]

        # Bearish keywords
        bearish = [
            'weak', 'decline', 'decrease', 'miss', 'disappoint',
            'challenge', 'headwind', 'concern', 'lower', 'cut',
            'reduce', 'downgrade', 'lowered guidance', 'risk'
        ]

        bullish_count = sum(1 for word in bullish if word in text_lower)
        bearish_count = sum(1 for word in bearish if word in text_lower)

        if bullish_count > bearish_count * 1.5:
            return 'bullish'
        elif bearish_count > bullish_count * 1.5:
            return 'bearish'
        else:
            return 'neutral'

    def _extract_executive_name(self, text: str) -> Optional[str]:
        """Extract executive name from text."""
        # Simple pattern: "CEO John Smith" or "John Smith, CEO"
        patterns = [
            r'CEO\s+([A-Z][a-z]+\s+[A-Z][a-z]+)',
            r'CFO\s+([A-Z][a-z]+\s+[A-Z][a-z]+)',
            r'([A-Z][a-z]+\s+[A-Z][a-z]+),?\s+CEO',
            r'([A-Z][a-z]+\s+[A-Z][a-z]+),?\s+CFO',
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)

        return None

    def _extract_topics(self, text: str) -> List[str]:
        """Extract topics from text."""
        topics = []

        topic_keywords = {
            'guidance': ['guidance', 'outlook', 'forecast', 'expect'],
            'growth': ['growth', 'expand', 'increase', 'accelerate'],
            'margins': ['margin', 'profitability', 'profit'],
            'products': ['product', 'launch', 'new offering'],
            'revenue': ['revenue', 'sales', 'top line'],
            'earnings': ['earnings', 'eps', 'profit'],
            'strategy': ['strategy', 'strategic', 'initiative'],
            'market': ['market share', 'competition', 'competitive'],
        }

        text_lower = text.lower()

        for topic, keywords in topic_keywords.items():
            if any(kw in text_lower for kw in keywords):
                topics.append(topic)

        return topics[:3]  # Limit to top 3

    def _analyze_commentary(
        self,
        ticker: str,
        comments: List[ExecutiveComment]
    ) -> ExecutiveCommentarySummary:
        """Analyze all comments and create summary."""

        if not comments:
            return ExecutiveCommentarySummary(
                ticker=ticker,
                recent_comments=[],
                overall_sentiment='neutral',
                sentiment_score=0.0,
                guidance_tone='none',
                key_themes=[],
                has_recent_commentary=False,
                last_comment_date=None,
                timestamp=datetime.now().isoformat()
            )

        # Sort by date (most recent first)
        comments.sort(key=lambda c: c.date, reverse=True)

        # Calculate overall sentiment
        sentiment_map = {'bullish': 1, 'neutral': 0, 'bearish': -1}
        weighted_scores = [
            sentiment_map[c.sentiment] * c.confidence
            for c in comments
        ]
        sentiment_score = sum(weighted_scores) / len(weighted_scores) if weighted_scores else 0.0

        # Determine overall sentiment
        if sentiment_score > 0.3:
            overall_sentiment = 'bullish'
        elif sentiment_score < -0.3:
            overall_sentiment = 'bearish'
        else:
            overall_sentiment = 'neutral'

        # Detect guidance tone
        guidance_comments = [c for c in comments if 'guidance' in c.topics]
        guidance_tone = 'none'

        if guidance_comments:
            recent_guidance = guidance_comments[0]
            if 'raised' in recent_guidance.content.lower() or 'upgrade' in recent_guidance.content.lower():
                guidance_tone = 'raised'
            elif 'lowered' in recent_guidance.content.lower() or 'cut' in recent_guidance.content.lower():
                guidance_tone = 'lowered'
            else:
                guidance_tone = 'maintained'

        # Extract key themes
        all_topics = []
        for comment in comments:
            all_topics.extend(comment.topics)

        # Count frequency
        topic_counts = {}
        for topic in all_topics:
            topic_counts[topic] = topic_counts.get(topic, 0) + 1

        key_themes = sorted(topic_counts.keys(), key=lambda t: topic_counts[t], reverse=True)[:5]

        # Get last comment date
        last_comment_date = comments[0].date if comments else None

        return ExecutiveCommentarySummary(
            ticker=ticker,
            recent_comments=comments[:10],  # Keep top 10
            overall_sentiment=overall_sentiment,
            sentiment_score=sentiment_score,
            guidance_tone=guidance_tone,
            key_themes=key_themes,
            has_recent_commentary=True,
            last_comment_date=last_comment_date,
            timestamp=datetime.now().isoformat()
        )


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

_tracker_instance = None


def get_commentary_tracker() -> ExecutiveCommentaryTracker:
    """Get singleton commentary tracker."""
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = ExecutiveCommentaryTracker()
    return _tracker_instance


def get_executive_commentary(ticker: str, days_back: int = 30) -> ExecutiveCommentarySummary:
    """Get executive commentary for ticker."""
    tracker = get_commentary_tracker()
    return tracker.get_commentary(ticker, days_back)


def has_recent_executive_commentary(ticker: str, days: int = 14) -> bool:
    """Check if ticker has recent executive commentary."""
    tracker = get_commentary_tracker()
    commentary = tracker.get_commentary(ticker, days_back=days)
    return commentary.has_recent_commentary


def get_executive_sentiment(ticker: str) -> str:
    """Get executive sentiment (bullish/neutral/bearish)."""
    tracker = get_commentary_tracker()
    commentary = tracker.get_commentary(ticker)
    return commentary.overall_sentiment


# =============================================================================
# TELEGRAM FORMATTING
# =============================================================================

def format_commentary_message(commentary: ExecutiveCommentarySummary) -> str:
    """Format executive commentary for Telegram."""
    msg = f"🎤 *EXECUTIVE COMMENTARY: ${commentary.ticker}*\n"
    msg += f"_Management sentiment and guidance_\n\n"

    # Sentiment
    sentiment_emoji = {
        'bullish': '📈',
        'neutral': '➡️',
        'bearish': '📉'
    }
    emoji = sentiment_emoji.get(commentary.overall_sentiment, '❓')

    msg += f"{emoji} *Sentiment:* {commentary.overall_sentiment.upper()}\n"
    msg += f"📊 *Score:* {commentary.sentiment_score:+.2f}\n\n"

    # Guidance
    if commentary.guidance_tone != 'none':
        guidance_emoji = {
            'raised': '⬆️',
            'maintained': '➡️',
            'lowered': '⬇️'
        }
        g_emoji = guidance_emoji.get(commentary.guidance_tone, '')
        msg += f"{g_emoji} *Guidance:* {commentary.guidance_tone.upper()}\n\n"

    # Key themes
    if commentary.key_themes:
        msg += f"💡 *Key Themes:*\n"
        for theme in commentary.key_themes[:3]:
            msg += f"  • {theme.title()}\n"
        msg += "\n"

    # Recent comments
    if commentary.recent_comments:
        msg += f"📝 *Recent Commentary:*\n"
        for comment in commentary.recent_comments[:3]:
            source_icon = {
                'sec_8k': '📄',
                'news': '📰',
                'press_release': '📢'
            }.get(comment.source, '💬')

            msg += f"{source_icon} {comment.source.replace('_', ' ').title()}\n"
            msg += f"   _{comment.content[:100]}..._\n\n"

    msg += f"_Last updated: {commentary.last_comment_date}_"

    return msg


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)

    test_ticker = sys.argv[1] if len(sys.argv) > 1 else 'NVDA'

    print(f"Fetching executive commentary for {test_ticker}...")
    print("=" * 60)

    tracker = ExecutiveCommentaryTracker()
    commentary = tracker.get_commentary(test_ticker, days_back=30)

    print(f"\n✓ Found commentary:")
    print(f"  Overall Sentiment: {commentary.overall_sentiment}")
    print(f"  Sentiment Score: {commentary.sentiment_score:.2f}")
    print(f"  Guidance Tone: {commentary.guidance_tone}")
    print(f"  Key Themes: {', '.join(commentary.key_themes)}")
    print(f"  Recent Comments: {len(commentary.recent_comments)}")

    if commentary.recent_comments:
        print(f"\n  Latest Comment:")
        latest = commentary.recent_comments[0]
        print(f"    Source: {latest.source}")
        print(f"    Date: {latest.date}")
        print(f"    Sentiment: {latest.sentiment}")
        print(f"    Content: {latest.content[:200]}...")
