#!/usr/bin/env python3
"""
xAI X (Twitter) Intelligence System

Real-time crisis detection using xAI's exclusive access to X data.
Detects breaking events BEFORE mainstream news.

Features:
- Multi-tier monitoring (cheap trending → expensive deep analysis)
- Crisis keyword tracking (wars, pandemics, disasters, terrorism, economic shocks)
- Stock-specific sentiment analysis
- Market panic detection
- Adaptive monitoring modes (normal/elevated/crisis)
- Cost controls (~$10-15/month budget)
- Smart caching to avoid duplicate analysis
- Verification and credibility scoring

Integration: Reports to Realtime Intelligence Director (Layer 2)
Component #37 in Evolutionary Agentic Brain
"""

import hashlib
import json
import logging
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set, Any
from dataclasses import dataclass, field
from enum import Enum
import threading
from pathlib import Path

logger = logging.getLogger(__name__)


class CrisisType(Enum):
    """Types of crises we monitor."""
    GEOPOLITICAL = "geopolitical"
    HEALTH = "health"
    NATURAL_DISASTER = "natural_disaster"
    TERRORISM = "terrorism"
    ECONOMIC = "economic"
    CYBER = "cyber"
    UNKNOWN = "unknown"


class MonitoringMode(Enum):
    """Adaptive monitoring modes."""
    NORMAL = "normal"        # Calm markets, check every 15 min
    ELEVATED = "elevated"    # Some concerns, check every 5 min
    CRISIS = "crisis"        # Active crisis, check every 1 min


@dataclass
class CrisisAlert:
    """Structured crisis alert from X intelligence."""
    topic: str
    crisis_type: CrisisType
    severity: int  # 1-10
    description: str
    verified: bool
    confidence: float  # 0-1
    verification_sources: List[str]
    sample_posts: List[str]
    geographic_focus: str
    detected_at: datetime
    minutes_ago: int
    market_impact: Dict[str, Any]
    immediate_actions: List[str]
    affected_sectors: List[str]
    safe_haven_recommendation: List[str]
    timeline_estimate: str
    historical_comparison: str
    credibility_score: float  # 0-1


@dataclass
class StockSentiment:
    """X sentiment for specific stock."""
    ticker: str
    sentiment: str  # bullish/bearish/neutral
    sentiment_score: float  # -1 to +1
    mention_volume: str  # normal/elevated/spiking
    key_topics: List[str]
    has_red_flags: bool
    red_flags: List[str]
    catalysts: List[str]
    confidence: float
    sample_posts: List[str]
    unusual_activity: bool


@dataclass
class PanicIndicator:
    """Market panic level from X sentiment."""
    panic_level: int  # 1-10
    sentiment_score: float  # -10 to +10
    volume_spike: bool
    key_concerns: List[str]
    retail_vs_institutional: str
    specific_stocks_mentioned: List[str]
    recommended_action: str
    detected_at: datetime


class XAnalysisCache:
    """Cache to avoid duplicate xAI API calls."""

    def __init__(self, ttl_hours: int = 24):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl_hours = ttl_hours

    def get(self, event_key: str) -> Optional[Any]:
        """Get cached analysis if still valid."""
        if event_key in self.cache:
            cached = self.cache[event_key]
            age = datetime.now() - cached['timestamp']
            if age < timedelta(hours=self.ttl_hours):
                return cached['data']
            else:
                # Expired
                del self.cache[event_key]
        return None

    def set(self, event_key: str, data: Any):
        """Cache analysis."""
        self.cache[event_key] = {
            'timestamp': datetime.now(),
            'data': data
        }

    def clear_old(self):
        """Clear expired entries."""
        now = datetime.now()
        expired = [
            key for key, val in self.cache.items()
            if now - val['timestamp'] >= timedelta(hours=self.ttl_hours)
        ]
        for key in expired:
            del self.cache[key]


class XAIXIntelligence:
    """
    Real-time crisis detection using xAI's exclusive X (Twitter) access.

    Cost-optimized: ~$10-15/month for 24/7 monitoring
    Value: Detect crises HOURS before mainstream news
    """

    def __init__(self):
        # Use existing AI service for xAI calls
        try:
            from src.services.ai_service import get_ai_service
            self.xai = get_ai_service()
            # Check if xAI is configured by checking the XAI_API_KEY
            import os
            self.xai_available = bool(os.getenv('XAI_API_KEY'))
        except Exception as e:
            logger.warning(f"Could not initialize xAI client: {e}")
            self.xai = None
            self.xai_available = False

        # Crisis keywords by category
        self.crisis_keywords = {
            CrisisType.GEOPOLITICAL: [
                'war declared', 'invasion', 'military strike', 'missile attack',
                'nuclear threat', 'coup', 'martial law', 'emergency declared',
                'airspace closed', 'borders closed', 'embassy evacuation',
                'troops deployed', 'ceasefire broken', 'sanctions announced'
            ],
            CrisisType.HEALTH: [
                'pandemic', 'outbreak', 'epidemic', 'virus spreading',
                'WHO declares', 'health emergency', 'lockdown announced',
                'mass casualties', 'quarantine', 'vaccine recall',
                'disease outbreak', 'contamination', 'public health crisis'
            ],
            CrisisType.NATURAL_DISASTER: [
                'earthquake', 'tsunami warning', 'hurricane', 'tornado',
                'volcanic eruption', 'wildfire', 'flooding', 'landslide',
                'nuclear accident', 'dam collapse', 'severe weather',
                'evacuation ordered', 'state of emergency'
            ],
            CrisisType.TERRORISM: [
                'terrorist attack', 'explosion', 'shooting', 'bombing',
                'hostage situation', 'security threat', 'evacuation ordered',
                'active shooter', 'bomb threat', 'suspicious package'
            ],
            CrisisType.ECONOMIC: [
                'bank collapse', 'market crash', 'trading halted',
                'currency crisis', 'default', 'bailout', 'bank run',
                'liquidity crisis', 'circuit breaker', 'bankruptcy filed',
                'credit freeze', 'financial contagion'
            ],
            CrisisType.CYBER: [
                'cyber attack', 'infrastructure hack', 'data breach',
                'ransomware', 'power grid down', 'internet outage',
                'ddos attack', 'security breach', 'systems compromised'
            ]
        }

        # Tracking
        self.analyzed_events: Set[str] = set()
        self.cache = XAnalysisCache(ttl_hours=24)

        # Cost controls
        self.daily_searches = 0
        self.MAX_DAILY_SEARCHES = 150  # Budget limit (~$15/month)
        self.last_reset = datetime.now().date()

        # Statistics
        self.stats = {
            'total_alerts': 0,
            'false_positives': 0,
            'true_positives': 0,
            'searches_today': 0,
            'cost_today': 0.0
        }

    def _reset_daily_limits(self):
        """Reset daily counters."""
        today = datetime.now().date()
        if today > self.last_reset:
            self.daily_searches = 0
            self.last_reset = today
            self.stats['searches_today'] = 0
            self.stats['cost_today'] = 0.0

    def _check_budget(self) -> bool:
        """Check if we're within budget."""
        self._reset_daily_limits()
        return self.daily_searches < self.MAX_DAILY_SEARCHES

    def _call_xai(self, system_prompt: str, user_prompt: str, max_tokens: int = 1000, temperature: float = 0.3) -> Optional[str]:
        """Helper method to call xAI using ai_service."""
        if not self.xai or not self.xai_available:
            return None

        try:
            response = self.xai.call_xai(
                prompt=user_prompt,
                system_prompt=system_prompt,
                max_tokens=max_tokens,
                temperature=temperature
            )
            return response
        except Exception as e:
            logger.error(f"xAI call error: {e}")
            return None

    def _increment_usage(self, estimated_cost: float = 0.10):
        """Track API usage."""
        self.daily_searches += 1
        self.stats['searches_today'] += 1
        self.stats['cost_today'] += estimated_cost

    def monitor_x_for_crises(self) -> List[CrisisAlert]:
        """
        Main monitoring function.
        TIER 1: Cheap trending check
        TIER 2: Deep analysis for spikes
        """

        if not self.xai:
            return []

        if not self._check_budget():
            logger.warning("Daily xAI budget reached, skipping X monitoring")
            return []

        alerts = []

        try:
            # Step 1: Cheap trending check
            trending_topics = self.get_trending_crisis_topics()

            # Step 2: Deep analysis for concerning topics
            for topic in trending_topics:
                if not self._check_budget():
                    break

                alert = self._analyze_topic_with_xai(topic)
                if alert and alert.severity >= 7:
                    alerts.append(alert)
                    self.stats['total_alerts'] += 1

        except Exception as e:
            logger.error(f"Error in X crisis monitoring: {e}")

        return alerts

    def get_trending_crisis_topics(self) -> List[str]:
        """
        Quick check: What's trending NOW that might be crisis-related?
        Single cheap API call.
        """

        if not self.xai or not self._check_budget():
            return []

        # Check cache
        cache_key = f"trending_{datetime.now().strftime('%Y%m%d%H')}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        prompt = """
Check X (Twitter) trending topics RIGHT NOW.

Identify any trending topics related to CRISES:
- Geopolitical events (wars, conflicts, military actions, political instability)
- Natural disasters (earthquakes, hurricanes, floods, fires)
- Economic crises (bank failures, market crashes, currency crises)
- Health emergencies (disease outbreaks, pandemics, contamination)
- Terrorist attacks or security threats
- Major accidents (nuclear, industrial, infrastructure)

Return ONLY topics that represent REAL POTENTIAL CRISES.
Filter out: celebrity gossip, sports, entertainment, normal politics.

Format: JSON list of topics
Example: ["Ukraine military escalation", "Magnitude 7.2 earthquake Turkey", "SVB bank run"]

If nothing concerning is trending, return empty list: []
"""

        try:
            content = self._call_xai(
                system_prompt="You monitor X for breaking crisis events. Filter noise, report only serious potential crises.",
                user_prompt=prompt,
                max_tokens=400,
                temperature=0.2
            )

            if not content:
                return []

            self._increment_usage(estimated_cost=0.05)

            content = content.strip()

            # Parse JSON
            try:
                topics = json.loads(content)
                if isinstance(topics, list):
                    # Cache for 1 hour
                    self.cache.set(cache_key, topics)
                    return topics
            except json.JSONDecodeError:
                # Try to extract topics from text
                topics = [line.strip('- ').strip('"').strip()
                         for line in content.split('\n')
                         if line.strip() and not line.startswith('[')]
                return topics[:5]  # Limit to top 5

        except Exception as e:
            logger.error(f"Error getting trending topics: {e}")
            return []

        return []

    def _analyze_topic_with_xai(self, topic: str) -> Optional[CrisisAlert]:
        """
        Deep dive into specific topic.
        Expensive call - only for confirmed spikes.
        """

        if not self.xai or not self._check_budget():
            return None

        # Check if analyzed recently
        event_hash = hashlib.md5(
            f"{topic}_{datetime.now().strftime('%Y%m%d%H')}".encode()
        ).hexdigest()

        if event_hash in self.analyzed_events:
            return None

        # Check cache
        cached = self.cache.get(f"deep_{event_hash}")
        if cached:
            return cached

        prompt = f"""
URGENT X INTELLIGENCE REQUEST

Detected trending topic: "{topic}"

Use your real-time X access to perform DEEP ANALYSIS:

1. VERIFICATION (Critical - avoid false alarms):
   - Search X for latest posts about this (last 30 minutes)
   - Are verified accounts posting about it?
   - Is there photo/video evidence?
   - Official sources (government, news agencies) confirming?
   - CREDIBILITY SCORE (0-10): How confident are you this is real vs rumor?

2. WHAT'S HAPPENING:
   - Describe the event clearly
   - Where is it happening?
   - When did it start? (how many minutes/hours ago)
   - Scale/magnitude

3. SEVERITY ASSESSMENT (1-10):
   1-3: Minor, local impact
   4-6: Moderate, regional impact
   7-8: Major, significant market impact
   9-10: Critical, global market impact

4. CRISIS TYPE:
   Classify as: geopolitical, health, natural_disaster, terrorism, economic, cyber, or unknown

5. MARKET IMPACT:
   - Expected market reaction (% drop/rally, timeline)
   - Affected sectors (be specific: Airlines, Energy, Tech, etc.)
   - Safe haven recommendations (Gold, Treasuries, USD, etc.)
   - Historical comparison (similar to what past event?)

6. IMMEDIATE TRADING ACTIONS:
   - Halt trading? (YES/NO with reasoning)
   - Sectors to EXIT immediately
   - Sectors to ENTER (if any opportunities)
   - Position size adjustment (e.g., "Reduce to 50%", "Go to cash")

7. GEOGRAPHIC FOCUS:
   - What country/region is primary focus?

8. SAMPLE POSTS:
   - Provide 2-3 key recent posts (paraphrased, show variety of sources)

Return detailed structured analysis. This will drive AUTOMATED trading decisions.
"""

        try:
            analysis_text = self._call_xai(
                system_prompt="You are an elite crisis intelligence analyst with real-time X access. Lives and money depend on accurate assessment. Verify carefully. Distinguish confirmed events from rumors.",
                user_prompt=prompt,
                max_tokens=1500,
                temperature=0.2
            )

            if not analysis_text:
                return None

            self._increment_usage(estimated_cost=0.15)
            self.analyzed_events.add(event_hash)

            # Parse the analysis
            alert = self._parse_crisis_analysis(analysis_text, topic)

            # Cache result
            self.cache.set(f"deep_{event_hash}", alert)

            # Log
            if alert:
                print(f"\n{'='*80}")
                print(f"🔍 xAI X INTELLIGENCE ANALYSIS")
                print(f"{'='*80}")
                print(f"Topic: {topic}")
                print(f"Type: {alert.crisis_type.value}")
                print(f"Severity: {alert.severity}/10")
                print(f"Verified: {alert.verified}")
                print(f"Credibility: {alert.credibility_score:.1%}")
                print(f"Confidence: {alert.confidence:.1%}")
                print(f"Geographic Focus: {alert.geographic_focus}")
                print(f"Market Impact: {alert.market_impact.get('expected_reaction', 'Unknown')}")
                if alert.immediate_actions:
                    print(f"Immediate Actions:")
                    for action in alert.immediate_actions[:3]:
                        print(f"  - {action}")
                print(f"{'='*80}\n")

            return alert

        except Exception as e:
            logger.error(f"Error analyzing topic '{topic}': {e}")
            return None

    def _parse_crisis_analysis(self, analysis_text: str, topic: str) -> Optional[CrisisAlert]:
        """Parse xAI response into structured CrisisAlert."""

        try:
            # Extract key information from text
            severity = self._extract_number(analysis_text, ['severity', 'score'], default=5)
            credibility = self._extract_number(analysis_text, ['credibility'], default=5) / 10

            # Determine crisis type
            crisis_type = CrisisType.UNKNOWN
            text_lower = analysis_text.lower()
            for ctype in CrisisType:
                if ctype.value in text_lower:
                    crisis_type = ctype
                    break

            # Extract verification
            verified = any(word in text_lower for word in ['confirmed', 'verified', 'official'])

            # Extract description (first few sentences)
            lines = [l.strip() for l in analysis_text.split('\n') if l.strip()]
            description = ' '.join(lines[:3])[:500]

            # Extract sectors
            affected_sectors = []
            sector_keywords = ['airlines', 'energy', 'tech', 'finance', 'healthcare',
                             'defense', 'retail', 'hospitality', 'manufacturing']
            for sector in sector_keywords:
                if sector in text_lower:
                    affected_sectors.append(sector.title())

            # Extract actions
            immediate_actions = []
            if 'halt trading' in text_lower or 'stop trading' in text_lower:
                immediate_actions.append('HALT ALL TRADING')
            if 'exit' in text_lower or 'sell' in text_lower:
                immediate_actions.append('Exit affected positions')
            if 'reduce position' in text_lower or 'reduce exposure' in text_lower:
                immediate_actions.append('Reduce position sizes')

            # Safe havens
            safe_havens = []
            if 'gold' in text_lower:
                safe_havens.append('Gold')
            if 'treasur' in text_lower:
                safe_havens.append('Treasuries')
            if 'usd' in text_lower or 'dollar' in text_lower:
                safe_havens.append('USD')

            # Create alert
            alert = CrisisAlert(
                topic=topic,
                crisis_type=crisis_type,
                severity=severity,
                description=description,
                verified=verified,
                confidence=credibility,
                verification_sources=['X verified accounts', 'Multiple sources'] if verified else ['Social media'],
                sample_posts=[],
                geographic_focus=self._extract_location(analysis_text),
                detected_at=datetime.now(),
                minutes_ago=self._extract_time_ago(analysis_text),
                market_impact={
                    'expected_reaction': self._extract_market_reaction(analysis_text),
                    'timeline': self._extract_timeline(analysis_text)
                },
                immediate_actions=immediate_actions,
                affected_sectors=affected_sectors,
                safe_haven_recommendation=safe_havens,
                timeline_estimate=self._extract_timeline(analysis_text),
                historical_comparison=self._extract_historical_comparison(analysis_text),
                credibility_score=credibility
            )

            return alert

        except Exception as e:
            logger.error(f"Error parsing crisis analysis: {e}")
            return None

    def _extract_number(self, text: str, keywords: List[str], default: int = 0) -> int:
        """Extract numeric value from text."""
        import re
        text_lower = text.lower()
        for keyword in keywords:
            pattern = rf'{keyword}[:\s]+(\d+)'
            match = re.search(pattern, text_lower)
            if match:
                return int(match.group(1))
        return default

    def _extract_location(self, text: str) -> str:
        """Extract geographic location."""
        # Simple keyword extraction
        countries = ['usa', 'china', 'russia', 'ukraine', 'europe', 'middle east',
                    'asia', 'japan', 'india', 'global', 'worldwide']
        text_lower = text.lower()
        for country in countries:
            if country in text_lower:
                return country.title()
        return 'Unknown'

    def _extract_time_ago(self, text: str) -> int:
        """Extract how long ago event started."""
        import re
        # Look for patterns like "30 minutes ago", "2 hours ago"
        patterns = [
            r'(\d+)\s*minutes?\s*ago',
            r'(\d+)\s*hours?\s*ago'
        ]
        for pattern in patterns:
            match = re.search(pattern, text.lower())
            if match:
                num = int(match.group(1))
                if 'hour' in pattern:
                    return num * 60
                return num
        return 0

    def _extract_market_reaction(self, text: str) -> str:
        """Extract expected market reaction."""
        text_lower = text.lower()
        if 'drop' in text_lower or 'fall' in text_lower or 'down' in text_lower:
            import re
            pct_match = re.search(r'(\d+)%', text_lower)
            if pct_match:
                return f"-{pct_match.group(1)}% expected"
            return "Negative"
        elif 'rally' in text_lower or 'rise' in text_lower or 'up' in text_lower:
            return "Positive"
        return "Unknown"

    def _extract_timeline(self, text: str) -> str:
        """Extract timeline estimate."""
        text_lower = text.lower()
        if 'days' in text_lower:
            return 'Days'
        elif 'weeks' in text_lower:
            return 'Weeks'
        elif 'months' in text_lower:
            return 'Months'
        return 'Unknown'

    def _extract_historical_comparison(self, text: str) -> str:
        """Extract historical event comparison."""
        events = ['covid', '9/11', 'ukraine', 'lehman', 'fukushima', 'gulf war']
        text_lower = text.lower()
        for event in events:
            if event in text_lower:
                return event.title()
        return 'Unknown'

    def monitor_specific_stocks_on_x(self, tickers: List[str]) -> Dict[str, StockSentiment]:
        """
        Track X sentiment for specific stocks.
        Use BEFORE entering positions.
        """

        if not self.xai or not self._check_budget():
            return {}

        # Limit to avoid excessive costs
        tickers = tickers[:5]

        ticker_str = ", ".join([f"${t}" for t in tickers])

        prompt = f"""
Search X (Twitter) for recent posts (last 1-2 hours) about: {ticker_str}

For each ticker, analyze:

1. SENTIMENT (bullish/bearish/neutral):
   - Overall tone of posts
   - Sentiment score: -10 (extreme bearish) to +10 (extreme bullish)

2. VOLUME:
   - Are mentions at normal/elevated/spiking levels?

3. KEY TOPICS:
   - What are people discussing? (earnings, news, technicals, rumors)

4. RED FLAGS (Critical - these prevent trades):
   - Accounting issues, fraud allegations
   - Lawsuits, regulatory problems
   - Negative earnings/guidance
   - Executive departures
   - Product failures

5. CATALYSTS (Positive signals):
   - Partnership announcements
   - Earnings beats
   - Product launches
   - Institutional buying

6. UNUSUAL ACTIVITY:
   - Options activity mentions
   - Insider buying/selling
   - Short squeeze potential

Return structured data per ticker in JSON format.
Example:
{{
  "NVDA": {{
    "sentiment": "bullish",
    "sentiment_score": 7,
    "volume": "elevated",
    "red_flags": [],
    "catalysts": ["AI demand strong", "Earnings beat expected"],
    "unusual_activity": true
  }}
}}
"""

        try:
            content = self._call_xai(
                system_prompt="You monitor X for stock sentiment. Be objective. Report both bullish and bearish signals.",
                user_prompt=prompt,
                max_tokens=1000,
                temperature=0.3
            )

            if not content:
                return {}

            self._increment_usage(estimated_cost=0.10)

            content = content.strip()

            # Parse JSON response
            try:
                data = json.loads(content)
                return self._parse_stock_sentiment(data, tickers)
            except json.JSONDecodeError:
                logger.error(f"Could not parse stock sentiment JSON: {content[:200]}")
                return {}

        except Exception as e:
            logger.error(f"Error monitoring stocks on X: {e}")
            return {}

    def _parse_stock_sentiment(self, data: Dict, tickers: List[str]) -> Dict[str, StockSentiment]:
        """Parse stock sentiment data."""

        sentiments = {}

        for ticker in tickers:
            if ticker in data:
                info = data[ticker]

                sentiment = StockSentiment(
                    ticker=ticker,
                    sentiment=info.get('sentiment', 'neutral'),
                    sentiment_score=info.get('sentiment_score', 0) / 10,  # Normalize to -1 to 1
                    mention_volume=info.get('volume', 'normal'),
                    key_topics=info.get('key_topics', []),
                    has_red_flags=len(info.get('red_flags', [])) > 0,
                    red_flags=info.get('red_flags', []),
                    catalysts=info.get('catalysts', []),
                    confidence=0.7,  # Default confidence
                    sample_posts=info.get('sample_posts', []),
                    unusual_activity=info.get('unusual_activity', False)
                )

                sentiments[ticker] = sentiment

        return sentiments

    def detect_market_panic_on_x(self) -> PanicIndicator:
        """
        Monitor X sentiment for market panic signals.
        Single cheap call, high value.
        """

        if not self.xai or not self._check_budget():
            return PanicIndicator(
                panic_level=5,
                sentiment_score=0,
                volume_spike=False,
                key_concerns=[],
                retail_vs_institutional='unknown',
                specific_stocks_mentioned=[],
                recommended_action='Continue monitoring',
                detected_at=datetime.now()
            )

        prompt = """
Analyze X (Twitter) sentiment RIGHT NOW for stock market panic signals:

Search for recent posts (last 30 minutes) mentioning:
- Market tickers: $SPY, $QQQ, $DIA
- Keywords: "stock market", "stocks", "market crash", "sell everything"
- Fear indicators: VIX, volatility, circuit breakers
- Panic phrases: "should I sell?", "recession", "bear market"

ANALYZE:

1. PANIC LEVEL (1-10):
   1 = Extreme greed, euphoria
   5 = Neutral
   10 = Extreme panic, capitulation

2. SENTIMENT SCORE (-10 to +10):
   -10 = Extreme bearish/panic
   0 = Neutral
   +10 = Extreme bullish/greed

3. VOLUME:
   - Are market-related posts spiking vs normal baseline?

4. KEY CONCERNS:
   - What specific issues are causing fear? (inflation, rates, geopolitics, etc.)

5. RETAIL VS INSTITUTIONAL:
   - Is this retail panic or are professional traders also concerned?

6. SPECIFIC STOCKS:
   - Are specific stocks being panic-sold?

7. RECOMMENDED ACTION:
   - "Go to cash" / "Reduce exposure" / "Continue monitoring" / "Buy the dip"

Return structured analysis in JSON format.
"""

        try:
            content = self._call_xai(
                system_prompt="You analyze market sentiment on X. Be objective - report actual sentiment, not your opinion.",
                user_prompt=prompt,
                max_tokens=800,
                temperature=0.3
            )

            if not content:
                return PanicIndicator(
                    panic_level=5,
                    sentiment_score=0,
                    volume_spike=False,
                    key_concerns=[],
                    retail_vs_institutional='unknown',
                    specific_stocks_mentioned=[],
                    recommended_action='Error - continue monitoring',
                    detected_at=datetime.now()
                )

            self._increment_usage(estimated_cost=0.08)

            content = content.strip()

            # Parse response
            return self._parse_panic_indicator(content)

        except Exception as e:
            logger.error(f"Error detecting panic: {e}")
            return PanicIndicator(
                panic_level=5,
                sentiment_score=0,
                volume_spike=False,
                key_concerns=[],
                retail_vs_institutional='unknown',
                specific_stocks_mentioned=[],
                recommended_action='Error - continue monitoring',
                detected_at=datetime.now()
            )

    def _parse_panic_indicator(self, content: str) -> PanicIndicator:
        """Parse panic indicator from text."""

        try:
            # Try JSON first
            data = json.loads(content)

            return PanicIndicator(
                panic_level=data.get('panic_level', 5),
                sentiment_score=data.get('sentiment_score', 0),
                volume_spike=data.get('volume_spike', False),
                key_concerns=data.get('key_concerns', []),
                retail_vs_institutional=data.get('retail_vs_institutional', 'mixed'),
                specific_stocks_mentioned=data.get('specific_stocks', []),
                recommended_action=data.get('recommended_action', 'Continue monitoring'),
                detected_at=datetime.now()
            )

        except json.JSONDecodeError:
            # Extract from text
            panic_level = self._extract_number(content, ['panic level', 'panic'], default=5)
            sentiment_score = self._extract_number(content, ['sentiment score'], default=0)

            return PanicIndicator(
                panic_level=panic_level,
                sentiment_score=sentiment_score,
                volume_spike='spike' in content.lower() or 'elevated' in content.lower(),
                key_concerns=[],
                retail_vs_institutional='unknown',
                specific_stocks_mentioned=[],
                recommended_action='Continue monitoring',
                detected_at=datetime.now()
            )

    def get_statistics(self) -> Dict[str, Any]:
        """Get usage statistics."""
        return {
            'daily_searches': self.daily_searches,
            'budget_remaining': self.MAX_DAILY_SEARCHES - self.daily_searches,
            'estimated_cost_today': f"${self.stats['cost_today']:.2f}",
            'total_alerts': self.stats['total_alerts'],
            'cache_size': len(self.cache.cache)
        }


class XMonitoringScheduler:
    """
    Adaptive monitoring scheduler.
    Adjusts frequency based on market conditions.
    """

    def __init__(self, x_intel: XAIXIntelligence):
        self.x_intel = x_intel
        self.current_mode = MonitoringMode.NORMAL
        self.crisis_callbacks = []
        self.running = False

    def add_crisis_callback(self, callback):
        """Register callback for crisis alerts."""
        self.crisis_callbacks.append(callback)

    def start(self):
        """Start adaptive monitoring."""
        self.running = True
        threading.Thread(target=self._monitor_loop, daemon=True).start()
        logger.info("X Intelligence Monitoring Started")
        logger.info(f"   Mode: {self.current_mode.value}")

    def stop(self):
        """Stop monitoring."""
        self.running = False
        logger.info("X Intelligence Monitoring Stopped")

    def _monitor_loop(self):
        """Main monitoring loop with adaptive frequency."""

        while self.running:
            try:
                # Determine check frequency based on mode
                if self.current_mode == MonitoringMode.NORMAL:
                    frequency = 900  # 15 minutes

                elif self.current_mode == MonitoringMode.ELEVATED:
                    frequency = 300  # 5 minutes

                elif self.current_mode == MonitoringMode.CRISIS:
                    frequency = 60   # 1 minute

                # Execute checks
                self._execute_checks()

                # Sleep until next check
                time.sleep(frequency)

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(60)  # Wait 1 minute on error

    def _execute_checks(self):
        """Execute appropriate checks for current mode."""

        try:
            if self.current_mode == MonitoringMode.NORMAL:
                # Cheap trending check
                trending = self.x_intel.get_trending_crisis_topics()

                if trending:
                    logger.warning(f"Trending crisis topics detected: {len(trending)}")
                    for topic in trending[:3]:
                        logger.warning(f"   - {topic}")
                    self.current_mode = MonitoringMode.ELEVATED
                    logger.warning(f"   Escalating to {self.current_mode.value.upper()} mode")

            elif self.current_mode == MonitoringMode.ELEVATED:
                # Volume spike detection + deep analysis
                alerts = self.x_intel.monitor_x_for_crises()

                if alerts:
                    for alert in alerts:
                        # Notify callbacks
                        for callback in self.crisis_callbacks:
                            callback(alert)

                        if alert.severity >= 8:
                            self.current_mode = MonitoringMode.CRISIS
                            logger.warning(f"CRISIS MODE ACTIVATED - Severity {alert.severity}/10")
                            break
                else:
                    # No serious alerts, can downgrade after some time
                    # For now, stay elevated
                    pass

            elif self.current_mode == MonitoringMode.CRISIS:
                # Intensive monitoring
                alerts = self.x_intel.monitor_x_for_crises()
                panic = self.x_intel.detect_market_panic_on_x()

                # Notify callbacks
                for alert in alerts:
                    for callback in self.crisis_callbacks:
                        callback(alert)

                # Check if crisis is de-escalating
                if not alerts or max((a.severity for a in alerts), default=0) < 7:
                    if panic.panic_level < 7:
                        self.current_mode = MonitoringMode.ELEVATED
                        logger.info(f"De-escalating to {self.current_mode.value.upper()} mode")

        except Exception as e:
            logger.error(f"Error executing checks: {e}")


# Singleton instance
_x_intelligence_instance = None

def get_x_intelligence() -> XAIXIntelligence:
    """Get singleton X intelligence instance."""
    global _x_intelligence_instance
    if _x_intelligence_instance is None:
        _x_intelligence_instance = XAIXIntelligence()
    return _x_intelligence_instance


if __name__ == "__main__":
    # Quick test
    print("Testing xAI X Intelligence System\n")

    x_intel = XAIXIntelligence()

    print("1. Checking trending crisis topics...")
    trending = x_intel.get_trending_crisis_topics()
    print(f"   Found {len(trending)} topics")
    for topic in trending:
        print(f"   - {topic}")

    print("\n2. Checking market panic level...")
    panic = x_intel.detect_market_panic_on_x()
    print(f"   Panic Level: {panic.panic_level}/10")
    print(f"   Sentiment: {panic.sentiment_score}")
    print(f"   Action: {panic.recommended_action}")

    print("\n3. Usage statistics:")
    stats = x_intel.get_statistics()
    for key, val in stats.items():
        print(f"   {key}: {val}")
