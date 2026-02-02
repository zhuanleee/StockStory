"""
Web Intelligence - Real-time Web Search Integration

Uses xAI SDK with web_search tool for ACTUAL real-time web access.
Verifies social intelligence (X/Twitter) with authoritative news sources.

3-Layer Intelligence System:
- Layer 1: X Intelligence (social sentiment, early detection)
- Layer 2: Web Intelligence (verified news, official sources) ← THIS
- Layer 3: Data Intelligence (market data, fundamentals)
"""

import os
import logging
from typing import List, Optional, Dict
from datetime import datetime

logger = logging.getLogger(__name__)

# Try to import xAI SDK
try:
    from xai_sdk import Client
    from xai_sdk.chat import user
    from xai_sdk.tools import web_search
    XAI_SDK_AVAILABLE = True
except ImportError:
    XAI_SDK_AVAILABLE = False
    logger.warning("xai_sdk not available - Web Intelligence will not work")


class WebIntelligence:
    """
    Web Intelligence using xAI SDK with real web search.

    Verifies crisis events, company news, and market events using
    authoritative sources (news sites, official websites, SEC).
    """

    # Major news sources for crisis verification
    NEWS_SOURCES = [
        "reuters.com",
        "bloomberg.com",
        "cnbc.com",
        "apnews.com",
        "wsj.com",
        "ft.com",
        "marketwatch.com"
    ]

    # Financial data sources
    FINANCIAL_SOURCES = [
        "sec.gov",
        "finance.yahoo.com",
        "marketwatch.com",
        "seekingalpha.com"
    ]

    def __init__(self):
        self.api_key = os.environ.get('XAI_API_KEY', '')
        self.available = XAI_SDK_AVAILABLE and bool(self.api_key)

        if not self.available:
            logger.warning("Web Intelligence not available - missing SDK or API key")
            return

        try:
            self.client = Client(api_key=self.api_key)
            logger.info("✓ Web Intelligence initialized with real web search")
        except Exception as e:
            logger.error(f"Failed to initialize Web Intelligence: {e}")
            self.available = False

    def verify_crisis(self, crisis_topic: str, x_severity: int) -> Optional[Dict]:
        """
        Verify a crisis detected on X/Twitter by searching news sites.

        Args:
            crisis_topic: The crisis topic from X Intelligence
            x_severity: Severity level from X (1-10)

        Returns:
            Dict with verification results including:
            - verified: bool (confirmed by news sources)
            - news_severity: int (1-10 based on news coverage)
            - sources: list of news sites covering it
            - credibility: float (0-1)
            - headlines: list of actual headlines
        """
        if not self.available:
            return None

        try:
            # Use reasoning model for crisis verification (accuracy critical)
            from src.ai.model_selector import get_crisis_model
            model = get_crisis_model()

            # Create chat with web search for news sites
            chat = self.client.chat.create(
                model=model,
                tools=[
                    web_search(allowed_domains=self.NEWS_SOURCES)
                ],
            )

            prompt = f"""
Search Reuters, Bloomberg, CNBC, AP News, and WSJ RIGHT NOW for information about:

"{crisis_topic}"

CRITICAL VERIFICATION TASK:

1. IS THIS REAL?
   - Are major news outlets reporting this?
   - Which specific outlets (Reuters, Bloomberg, etc.)?
   - Do you find actual articles published recently?

2. SEVERITY ASSESSMENT:
   - How prominently are they covering it?
   - Breaking news / Top story / Minor mention?
   - News severity (1-10): 1=minor mention, 10=breaking global news

3. CREDIBILITY:
   - Multiple independent sources confirming?
   - Official statements included?
   - Credibility score (0-10)

4. ACTUAL HEADLINES:
   - Quote 2-3 actual headlines you found
   - Include publication time if available

5. KEY DETAILS:
   - What exactly happened?
   - When did it happen?
   - Current status

CONTEXT: This was detected on X/Twitter with severity {x_severity}/10.
Your job is to verify if mainstream news confirms it.

Return structured analysis. If NO major news coverage found, clearly state that.
"""

            chat.append(user(prompt))
            response = chat.sample()

            logger.info(f"Crisis verification completed for '{crisis_topic}': {len(response.content)} chars")

            # Parse verification results
            verification = self._parse_crisis_verification(response.content, crisis_topic, x_severity)

            return verification

        except Exception as e:
            logger.error(f"Error verifying crisis '{crisis_topic}': {e}")
            return None

    def search_company_news(self, ticker: str, days_back: int = 7) -> Optional[Dict]:
        """
        Search for company-specific news and announcements.

        Args:
            ticker: Stock ticker symbol
            days_back: How many days to search back

        Returns:
            Dict with company news including:
            - headlines: list of recent headlines
            - sentiment: overall sentiment (positive/negative/neutral)
            - material_events: list of material events found
            - red_flags: list of concerning news
        """
        if not self.available:
            return None

        try:
            # Search both news sites and company IR
            domains = self.NEWS_SOURCES + [
                f"ir.{ticker.lower()}.com",  # Investor relations
                f"{ticker.lower()}.com"      # Company website
            ]

            chat = self.client.chat.create(
                model="grok-4-1-fast",
                tools=[
                    web_search(allowed_domains=domains)
                ],
            )

            prompt = f"""
Search news sites and company websites for ${ticker} from the last {days_back} days.

Find:

1. MAJOR HEADLINES:
   - Top 3-5 most important news stories
   - Publication date and source

2. MATERIAL EVENTS:
   - Earnings announcements
   - Product launches
   - Partnerships/acquisitions
   - Management changes
   - Regulatory issues

3. SENTIMENT:
   - Overall tone (bullish/bearish/neutral)
   - Positive developments
   - Negative developments

4. RED FLAGS:
   - Lawsuits, investigations
   - Accounting issues
   - Product failures
   - Executive departures

Return recent, relevant news. Be specific with dates and sources.
"""

            chat.append(user(prompt))
            response = chat.sample()

            logger.info(f"Company news search completed for {ticker}: {len(response.content)} chars")

            # Parse company news
            news_data = self._parse_company_news(response.content, ticker)

            return news_data

        except Exception as e:
            logger.error(f"Error searching company news for {ticker}: {e}")
            return None

    def verify_market_event(self, event_description: str) -> Optional[Dict]:
        """
        Verify a market-moving event (earnings, Fed decision, etc.).

        Args:
            event_description: Description of the market event

        Returns:
            Dict with event verification
        """
        if not self.available:
            return None

        try:
            chat = self.client.chat.create(
                model="grok-4-1-fast",
                tools=[
                    web_search(allowed_domains=self.NEWS_SOURCES + self.FINANCIAL_SOURCES)
                ],
            )

            prompt = f"""
Search financial news sites for information about this market event:

"{event_description}"

Verify:
1. Did this event actually happen?
2. When did it happen? (exact time if possible)
3. What are the market implications?
4. Which sources are reporting it?
5. What's the market reaction so far?

Provide factual verification with sources.
"""

            chat.append(user(prompt))
            response = chat.sample()

            logger.info(f"Market event verification completed: {len(response.content)} chars")

            verification = self._parse_market_event(response.content, event_description)

            return verification

        except Exception as e:
            logger.error(f"Error verifying market event: {e}")
            return None

    def _parse_crisis_verification(self, content: str, topic: str, x_severity: int) -> Dict:
        """Parse crisis verification results."""
        import re

        verification = {
            'topic': topic,
            'x_severity': x_severity,
            'verified': False,
            'news_severity': 0,
            'credibility': 0.0,
            'sources': [],
            'headlines': [],
            'raw_content': content,
            'timestamp': datetime.now().isoformat()
        }

        content_lower = content.lower()

        # Check if verified by news
        verification['verified'] = any(source.split('.')[0] in content_lower
                                      for source in self.NEWS_SOURCES)

        # Extract severity
        severity_match = re.search(r'severity[:\s]+(\d+)', content_lower)
        if severity_match:
            verification['news_severity'] = int(severity_match.group(1))

        # Extract credibility
        cred_match = re.search(r'credibility[:\s]+(\d+)', content_lower)
        if cred_match:
            verification['credibility'] = int(cred_match.group(1)) / 10

        # Identify sources mentioned
        for source in self.NEWS_SOURCES:
            source_name = source.split('.')[0]
            if source_name in content_lower:
                verification['sources'].append(source_name.title())

        # Look for "no coverage" indicators
        no_coverage = any(phrase in content_lower for phrase in [
            'no major news', 'not found', 'no articles', 'no coverage',
            'not reporting', 'no confirmation'
        ])

        if no_coverage:
            verification['verified'] = False
            verification['news_severity'] = 0
            verification['credibility'] = 0.0

        return verification

    def _parse_company_news(self, content: str, ticker: str) -> Dict:
        """Parse company news results."""
        import re

        news_data = {
            'ticker': ticker,
            'headlines': [],
            'sentiment': 'neutral',
            'material_events': [],
            'red_flags': [],
            'raw_content': content,
            'timestamp': datetime.now().isoformat()
        }

        content_lower = content.lower()

        # Detect sentiment
        positive_words = ['beat', 'strong', 'growth', 'partnership', 'launch', 'success']
        negative_words = ['lawsuit', 'investigation', 'decline', 'loss', 'failure', 'concern']

        positive_count = sum(1 for word in positive_words if word in content_lower)
        negative_count = sum(1 for word in negative_words if word in content_lower)

        if positive_count > negative_count + 1:
            news_data['sentiment'] = 'positive'
        elif negative_count > positive_count + 1:
            news_data['sentiment'] = 'negative'

        # Detect red flags
        red_flag_keywords = ['lawsuit', 'investigation', 'fraud', 'accounting',
                            'departure', 'resignation', 'failure']

        for keyword in red_flag_keywords:
            if keyword in content_lower:
                news_data['red_flags'].append(keyword.title())

        return news_data

    def _parse_market_event(self, content: str, event: str) -> Dict:
        """Parse market event verification."""

        verification = {
            'event': event,
            'verified': False,
            'when': None,
            'sources': [],
            'market_reaction': 'unknown',
            'raw_content': content,
            'timestamp': datetime.now().isoformat()
        }

        content_lower = content.lower()

        # Check if verified
        verification['verified'] = any(phrase in content_lower for phrase in [
            'confirmed', 'reported', 'announced', 'happened', 'occurred'
        ])

        # Identify sources
        for source in self.NEWS_SOURCES:
            source_name = source.split('.')[0]
            if source_name in content_lower:
                verification['sources'].append(source_name.title())

        return verification


def get_web_intelligence() -> Optional[WebIntelligence]:
    """Get Web Intelligence instance (singleton pattern)."""
    global _web_intel_instance
    if '_web_intel_instance' not in globals():
        _web_intel_instance = WebIntelligence()
    return _web_intel_instance if _web_intel_instance.available else None
