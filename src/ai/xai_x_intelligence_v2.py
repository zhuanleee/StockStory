"""
xAI X Intelligence v2 - Real X/Twitter Search Integration

Uses xAI SDK with x_search tool for ACTUAL real-time X/Twitter access.
This version replaces the prompt-based approach with proper tool usage.
"""

import os
import logging
from typing import List, Optional, Dict
from datetime import datetime

logger = logging.getLogger(__name__)

# Try to import xAI SDK
try:
    from xai_sdk import Client
    from xai_sdk.chat import user, assistant
    from xai_sdk.tools import x_search
    XAI_SDK_AVAILABLE = True
except ImportError:
    XAI_SDK_AVAILABLE = False
    logger.warning("xai_sdk not available - X Intelligence will not work")


class XAIXIntelligenceV2:
    """
    X Intelligence using xAI SDK with real X search.

    Key differences from v1:
    - Uses xai_sdk.Client (not HTTP requests)
    - Uses x_search tool (not prompts)
    - Actually searches X in real-time
    - Model: grok-4-1-fast (reasoning model)
    """

    def __init__(self):
        self.api_key = os.environ.get('XAI_API_KEY', '')
        self.available = XAI_SDK_AVAILABLE and bool(self.api_key)

        if not self.available:
            logger.warning("X Intelligence V2 not available - missing SDK or API key")
            return

        try:
            self.client = Client(api_key=self.api_key)
            logger.info("✓ X Intelligence V2 initialized with real X search")
        except Exception as e:
            logger.error(f"Failed to initialize X Intelligence V2: {e}")
            self.available = False

    def search_x_for_crises(self) -> List[Dict]:
        """
        Search X/Twitter for crisis-related trending topics.

        Returns list of crisis topics with real X data.
        """
        if not self.available:
            return []

        try:
            # Create chat with X search tool
            chat = self.client.chat.create(
                model="grok-4-1-fast",
                tools=[
                    x_search(
                        # Allow searching from major news sources
                        allowed_x_handles=[
                            "CNNBreaking", "BBCBreaking", "Reuters",
                            "AP", "nytimes", "WSJ", "Bloomberg",
                            "FinancialTimes", "CNBC", "MarketWatch"
                        ]
                    ),
                ],
            )

            # Ask Grok to search X for crisis topics
            prompt = """
Search X (Twitter) RIGHT NOW for trending topics related to market-moving crises:

Focus on:
1. Economic crises (bank failures, market crashes, currency crises)
2. Geopolitical events (wars, conflicts, sanctions, coups)
3. Natural disasters affecting major economies
4. Major corporate failures or scandals
5. Government/regulatory shocks

For each crisis topic you find:
- Topic name
- How many posts/mentions
- When it started trending
- Severity (1-10 scale)
- Verified sources posting about it

Return as JSON array. If no significant crises, return empty array [].
Only include topics with severity >= 7 (significant market impact expected).
"""

            chat.append(user(prompt))

            # Get response with X search results
            response = chat.sample()

            logger.info(f"X search query completed: {len(response.content)} chars")

            # Parse response to extract crisis topics
            crisis_topics = self._parse_x_search_results(response.content)

            return crisis_topics

        except Exception as e:
            logger.error(f"Error searching X for crises: {e}")
            return []

    def analyze_crisis_topic(self, topic: str) -> Optional[Dict]:
        """
        Deep analysis of a specific crisis topic using X search.

        Args:
            topic: The crisis topic to analyze

        Returns:
            Dict with detailed crisis analysis
        """
        if not self.available:
            return None

        try:
            # Create chat with X search focused on this topic
            chat = self.client.chat.create(
                model="grok-4-1-fast",
                tools=[x_search()],  # Search all of X
            )

            prompt = f"""
Search X (Twitter) for the latest posts about: "{topic}"

Provide DETAILED analysis:

1. VERIFICATION:
   - Are verified accounts posting about this?
   - Is there photo/video evidence?
   - Official sources confirming?
   - Credibility score (0-10)

2. SEVERITY ASSESSMENT (1-10):
   - 7-8: Major, significant market impact
   - 9-10: Critical, global market impact

3. MARKET IMPACT:
   - Expected market reaction
   - Affected sectors (Airlines, Energy, Tech, Finance, etc.)
   - Safe havens (Gold, USD, Treasuries)

4. IMMEDIATE ACTIONS:
   - Should trading be halted? YES/NO
   - Sectors to exit
   - Position size recommendations

5. TIMELINE:
   - When did this start?
   - How long ago? (minutes/hours)

6. SAMPLE POSTS:
   - Quote 2-3 actual recent posts with engagement numbers

Return structured analysis. Be accurate - this drives automated trading.
"""

            chat.append(user(prompt))
            response = chat.sample()

            # Parse the detailed analysis
            analysis = self._parse_crisis_analysis(response.content, topic)

            return analysis

        except Exception as e:
            logger.error(f"Error analyzing crisis topic '{topic}': {e}")
            return None

    def _parse_x_search_results(self, content: str) -> List[Dict]:
        """Parse X search results into crisis topics."""
        import json
        import re

        topics = []

        try:
            # Try to extract JSON from response
            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
                if isinstance(data, list):
                    return data

            # Fallback: parse text format
            lines = content.split('\n')
            current_topic = {}

            for line in lines:
                line = line.strip()
                if not line:
                    if current_topic:
                        topics.append(current_topic)
                        current_topic = {}
                    continue

                # Extract topic info from text
                if 'topic' in line.lower() or line.startswith('-'):
                    if current_topic:
                        topics.append(current_topic)
                    current_topic = {'topic': line.strip('- ').split(':')[-1].strip()}
                elif 'severity' in line.lower():
                    try:
                        severity = int(re.search(r'\d+', line).group())
                        current_topic['severity'] = severity
                    except:
                        pass

            if current_topic:
                topics.append(current_topic)

        except Exception as e:
            logger.debug(f"Could not parse JSON from X search: {e}")

        return topics

    def search_stock_sentiment(self, tickers: List[str]) -> Dict[str, Dict]:
        """
        Search X/Twitter for real-time stock sentiment.

        Args:
            tickers: List of ticker symbols to analyze (max 5)

        Returns:
            Dict mapping ticker -> sentiment analysis
        """
        if not self.available:
            return {}

        # Limit to avoid excessive costs
        tickers = tickers[:5]
        ticker_str = ", ".join([f"${t}" for t in tickers])

        try:
            # Create chat with X search
            chat = self.client.chat.create(
                model="grok-4-1-fast",
                tools=[x_search()],  # Search all of X
            )

            prompt = f"""
Search X (Twitter) RIGHT NOW for recent posts (last 1-2 hours) about: {ticker_str}

For each ticker, analyze the ACTUAL posts you find:

1. SENTIMENT (bullish/bearish/neutral):
   - Overall tone of posts you see
   - Sentiment score: -10 (extreme bearish) to +10 (extreme bullish)

2. VOLUME:
   - Are mentions at normal/elevated/spiking levels?
   - How many posts in last hour?

3. KEY TOPICS:
   - What are people discussing? (earnings, news, technicals, rumors)

4. RED FLAGS (Critical):
   - Accounting issues, fraud allegations
   - Lawsuits, regulatory problems
   - Negative earnings/guidance
   - Executive departures
   - Product failures

5. CATALYSTS (Positive):
   - Partnership announcements
   - Earnings beats
   - Product launches
   - Institutional buying

6. UNUSUAL ACTIVITY:
   - Options activity mentions
   - Insider buying/selling
   - Short squeeze potential

7. SAMPLE POSTS:
   - Quote 2-3 actual recent posts with engagement

Return JSON format:
{{
  "TICKER": {{
    "sentiment": "bullish/bearish/neutral",
    "sentiment_score": -10 to +10,
    "volume": "normal/elevated/spiking",
    "mentions_per_hour": number,
    "red_flags": ["list of red flags"],
    "catalysts": ["list of catalysts"],
    "unusual_activity": true/false,
    "key_topics": ["list of topics"],
    "sample_posts": ["actual post excerpts"]
  }}
}}
"""

            chat.append(user(prompt))
            response = chat.sample()

            logger.info(f"Stock sentiment search completed for {ticker_str}: {len(response.content)} chars")

            # Parse response
            sentiment_data = self._parse_stock_sentiment(response.content, tickers)

            return sentiment_data

        except Exception as e:
            logger.error(f"Error searching X for stock sentiment: {e}")
            return {}

    def _parse_stock_sentiment(self, content: str, tickers: List[str]) -> Dict[str, Dict]:
        """Parse stock sentiment from X search results."""
        import json
        import re

        sentiments = {}

        try:
            # Try to extract JSON
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))

                # Process each ticker
                for ticker in tickers:
                    if ticker in data:
                        info = data[ticker]
                        sentiments[ticker] = {
                            'ticker': ticker,
                            'sentiment': info.get('sentiment', 'neutral'),
                            'sentiment_score': info.get('sentiment_score', 0),
                            'volume': info.get('volume', 'normal'),
                            'mentions_per_hour': info.get('mentions_per_hour', 0),
                            'red_flags': info.get('red_flags', []),
                            'catalysts': info.get('catalysts', []),
                            'unusual_activity': info.get('unusual_activity', False),
                            'key_topics': info.get('key_topics', []),
                            'sample_posts': info.get('sample_posts', []),
                            'has_red_flags': len(info.get('red_flags', [])) > 0,
                            'timestamp': datetime.now().isoformat()
                        }
            else:
                # Fallback: basic parsing from text
                for ticker in tickers:
                    if ticker in content:
                        sentiment = 'neutral'
                        if any(word in content.lower() for word in ['bullish', 'buy', 'long', 'strong']):
                            sentiment = 'bullish'
                        elif any(word in content.lower() for word in ['bearish', 'sell', 'short', 'weak']):
                            sentiment = 'bearish'

                        sentiments[ticker] = {
                            'ticker': ticker,
                            'sentiment': sentiment,
                            'sentiment_score': 0,
                            'volume': 'unknown',
                            'mentions_per_hour': 0,
                            'red_flags': [],
                            'catalysts': [],
                            'unusual_activity': False,
                            'key_topics': [],
                            'sample_posts': [],
                            'has_red_flags': False,
                            'timestamp': datetime.now().isoformat()
                        }

        except Exception as e:
            logger.debug(f"Could not parse stock sentiment JSON: {e}")

        return sentiments

    def _parse_crisis_analysis(self, content: str, topic: str) -> Dict:
        """Parse detailed crisis analysis."""
        import re

        analysis = {
            'topic': topic,
            'raw_analysis': content,
            'severity': 5,
            'verified': False,
            'credibility': 0.5,
            'market_impact': 'Unknown',
            'halt_trading': False,
            'affected_sectors': [],
            'timestamp': datetime.now().isoformat()
        }

        content_lower = content.lower()

        # Extract severity
        severity_match = re.search(r'severity[:\s]+(\d+)', content_lower)
        if severity_match:
            analysis['severity'] = int(severity_match.group(1))

        # Check verification
        analysis['verified'] = any(word in content_lower for word in
                                  ['verified', 'confirmed', 'official'])

        # Extract credibility
        cred_match = re.search(r'credibility[:\s]+(\d+)', content_lower)
        if cred_match:
            analysis['credibility'] = int(cred_match.group(1)) / 10

        # Check if trading should halt
        analysis['halt_trading'] = 'yes' in content_lower and 'halt' in content_lower

        # Extract sectors
        sectors = ['airlines', 'energy', 'tech', 'finance', 'healthcare',
                  'defense', 'retail', 'banking']
        analysis['affected_sectors'] = [s.title() for s in sectors if s in content_lower]

        return analysis


def get_x_intelligence_v2() -> Optional[XAIXIntelligenceV2]:
    """Get X Intelligence V2 instance (singleton pattern)."""
    global _x_intel_v2_instance
    if '_x_intel_v2_instance' not in globals():
        _x_intel_v2_instance = XAIXIntelligenceV2()
    return _x_intel_v2_instance if _x_intel_v2_instance.available else None
