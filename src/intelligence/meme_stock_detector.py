"""
Meme Stock Detector - Catch Viral Momentum Early

Detects stocks going viral on social media BEFORE they explode.
Uses X Intelligence to spot unusual social volume and sentiment.

Success stories: GME, AMC, BBBY all had early X signals.

Features:
- Unusual mention volume detection
- Viral momentum scoring
- Retail vs institutional sentiment
- Short squeeze potential
- Early entry signals

ROI: Catching ONE +100% meme move = 20+ years of service paid.
"""

import os
import logging
from typing import List, Optional, Dict
from datetime import datetime

logger = logging.getLogger(__name__)


class MemeStockDetector:
    """
    Detects stocks going viral on social media.

    Viral signals:
    - Mentions/hour > 1000 (10x normal)
    - Sentiment strongly bullish (>7)
    - Short squeeze mentions
    - Retail coordination keywords
    """

    # Keywords indicating meme stock activity
    MEME_KEYWORDS = [
        'short squeeze', 'squeeze', 'gamma squeeze',
        'apes', 'diamond hands', 'hodl', 'to the moon',
        'buying calls', 'yolo', 'wsb', 'wallstreetbets'
    ]

    def __init__(self):
        self.x_intel = None

        try:
            from src.ai.xai_x_intelligence_v2 import get_x_intelligence_v2
            self.x_intel = get_x_intelligence_v2()

            if self.x_intel:
                logger.info("✓ Meme Stock Detector initialized")
            else:
                logger.warning("Meme Stock Detector: X Intelligence not available")
        except Exception as e:
            logger.error(f"Failed to initialize Meme Stock Detector: {e}")

    def scan_universe(self, tickers: List[str], top_n: int = 10) -> List[Dict]:
        """
        Scan universe for stocks showing viral momentum.

        Args:
            tickers: List of tickers to scan (100-200 recommended)
            top_n: Return top N candidates

        Returns:
            List of potential meme stocks with scores
        """
        if not self.x_intel:
            return []

        logger.info(f"🔍 Scanning {len(tickers)} tickers for meme stock signals...")

        # Batch scan in groups (avoid rate limits)
        batch_size = 20
        candidates = []

        for i in range(0, len(tickers), batch_size):
            batch = tickers[i:i+batch_size]

            try:
                sentiment_data = self.x_intel.search_stock_sentiment(batch)

                for ticker, data in sentiment_data.items():
                    score = self._calculate_meme_score(ticker, data)

                    if score >= 6.0:  # Threshold for potential meme
                        candidates.append({
                            'ticker': ticker,
                            'meme_score': score,
                            'mentions_per_hour': data.get('mentions_per_hour', 0),
                            'sentiment': data.get('sentiment', 'unknown'),
                            'sentiment_score': data.get('sentiment_score', 0),
                            'unusual_activity': data.get('unusual_activity', False),
                            'key_topics': data.get('key_topics', []),
                            'has_meme_keywords': self._has_meme_keywords(data),
                            'timestamp': datetime.now().isoformat()
                        })

            except Exception as e:
                logger.error(f"Error scanning batch {i}-{i+batch_size}: {e}")
                continue

        # Sort by meme score
        candidates.sort(key=lambda x: x['meme_score'], reverse=True)

        logger.info(f"Found {len(candidates)} potential meme stocks")

        return candidates[:top_n]

    def _calculate_meme_score(self, ticker: str, sentiment_data: Dict) -> float:
        """
        Calculate meme stock score (0-10).

        Factors:
        - Mention volume (higher = more viral)
        - Bullish sentiment (memes are bullish)
        - Unusual activity flags
        - Meme keywords present
        """
        score = 0.0

        # Factor 1: Mention volume (0-4 points)
        mentions = sentiment_data.get('mentions_per_hour', 0)
        if mentions > 5000:
            score += 4.0
        elif mentions > 2000:
            score += 3.0
        elif mentions > 1000:
            score += 2.0
        elif mentions > 500:
            score += 1.0

        # Factor 2: Bullish sentiment (0-3 points)
        sentiment_score = sentiment_data.get('sentiment_score', 0)
        if sentiment_score > 7:
            score += 3.0
        elif sentiment_score > 5:
            score += 2.0
        elif sentiment_score > 3:
            score += 1.0

        # Factor 3: Unusual activity (0-2 points)
        if sentiment_data.get('unusual_activity', False):
            score += 2.0

        # Factor 4: Meme keywords (0-1 point)
        if self._has_meme_keywords(sentiment_data):
            score += 1.0

        return min(score, 10.0)

    def _has_meme_keywords(self, sentiment_data: Dict) -> bool:
        """Check if sentiment data contains meme keywords."""
        key_topics = sentiment_data.get('key_topics', [])
        sample_posts = sentiment_data.get('sample_posts', [])

        all_text = ' '.join(key_topics + sample_posts).lower()

        return any(keyword in all_text for keyword in self.MEME_KEYWORDS)

    def analyze_specific(self, ticker: str) -> Optional[Dict]:
        """
        Deep analysis of a specific stock for meme potential.

        Args:
            ticker: Stock ticker to analyze

        Returns:
            Detailed meme analysis
        """
        if not self.x_intel:
            return None

        try:
            sentiment_data = self.x_intel.search_stock_sentiment([ticker])

            if ticker not in sentiment_data:
                return None

            data = sentiment_data[ticker]

            meme_score = self._calculate_meme_score(ticker, data)
            has_keywords = self._has_meme_keywords(data)

            return {
                'ticker': ticker,
                'meme_score': meme_score,
                'meme_potential': self._classify_meme_potential(meme_score),
                'mentions_per_hour': data.get('mentions_per_hour', 0),
                'sentiment': data.get('sentiment', 'unknown'),
                'sentiment_score': data.get('sentiment_score', 0),
                'has_meme_keywords': has_keywords,
                'meme_keywords_found': [kw for kw in self.MEME_KEYWORDS
                                       if kw in ' '.join(data.get('key_topics', [])).lower()],
                'unusual_activity': data.get('unusual_activity', False),
                'key_topics': data.get('key_topics', []),
                'catalysts': data.get('catalysts', []),
                'recommendation': self._get_recommendation(meme_score, data),
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error analyzing {ticker} for meme potential: {e}")
            return None

    def _classify_meme_potential(self, score: float) -> str:
        """Classify meme potential based on score."""
        if score >= 8.0:
            return 'EXTREME_VIRAL'
        elif score >= 6.5:
            return 'HIGH_VIRAL'
        elif score >= 5.0:
            return 'MODERATE_VIRAL'
        else:
            return 'LOW_VIRAL'

    def _get_recommendation(self, score: float, data: Dict) -> str:
        """Get trading recommendation based on meme score."""
        if score >= 8.0 and data.get('sentiment_score', 0) > 7:
            return 'STRONG_BUY - Extreme viral momentum'
        elif score >= 6.5:
            return 'BUY - High meme potential, early entry'
        elif score >= 5.0:
            return 'WATCH - Building momentum, wait for confirmation'
        else:
            return 'PASS - Insufficient viral activity'


def get_meme_stock_detector():
    """Get meme stock detector instance (singleton)."""
    global _meme_detector_instance
    if '_meme_detector_instance' not in globals():
        _meme_detector_instance = MemeStockDetector()
    return _meme_detector_instance
