"""
Exit Signal Detector - Protect Capital with AI Intelligence

Monitors holdings for negative sentiment shifts and red flags.
Sends alerts when positions should be exited.

Features:
- Daily sentiment checks for all holdings
- Red flag detection (lawsuits, fraud, etc.)
- Sentiment deterioration tracking
- Web verification of concerns
- Automatic exit recommendations

ROI: Avoiding ONE -20% crash pays for 10+ years of service.
"""

import os
import logging
from typing import List, Optional, Dict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ExitSignalDetector:
    """
    Monitors holdings for exit signals using X + Web Intelligence.

    Exit triggers:
    - Red flags detected (fraud, lawsuit, investigation)
    - Sentiment score < -5 (bearish momentum)
    - Sentiment shift from +5 to -3 in 24h (reversal)
    - Web confirms negative news
    """

    def __init__(self):
        self.x_intel = None
        self.web_intel = None
        self.sentiment_history = {}  # Track sentiment over time

        try:
            from src.ai.xai_x_intelligence_v2 import get_x_intelligence_v2
            from src.ai.web_intelligence import get_web_intelligence

            self.x_intel = get_x_intelligence_v2()
            self.web_intel = get_web_intelligence()

            if self.x_intel:
                logger.info("✓ Exit Signal Detector initialized")
            else:
                logger.warning("Exit Signal Detector: X Intelligence not available")
        except Exception as e:
            logger.error(f"Failed to initialize Exit Signal Detector: {e}")

    def check_holdings(self, tickers: List[str]) -> Dict[str, Dict]:
        """
        Check all holdings for exit signals.

        Args:
            tickers: List of ticker symbols currently held

        Returns:
            Dict mapping ticker -> exit signal data
        """
        if not self.x_intel:
            return {}

        logger.info(f"🔍 Checking {len(tickers)} holdings for exit signals...")

        exit_signals = {}

        for ticker in tickers:
            signal = self._check_single_holding(ticker)
            if signal:
                exit_signals[ticker] = signal

        return exit_signals

    def _check_single_holding(self, ticker: str) -> Optional[Dict]:
        """Check a single holding for exit signals."""

        try:
            # Get current X sentiment with quality filters (accuracy critical for exit decisions)
            sentiment_data = self.x_intel.search_stock_sentiment(
                [ticker],
                deep_analysis=False,  # Use fast model (daily checks)
                verified_only=True,   # Verified accounts only for accuracy
                min_followers=5000,   # Established voices
                min_engagement=20     # Quality signals
            )

            if ticker not in sentiment_data:
                logger.debug(f"No sentiment data for {ticker}")
                return None

            current = sentiment_data[ticker]

            # Check for immediate red flags
            if current.get('has_red_flags', False):
                red_flags = current.get('red_flags', [])

                # Verify with web intelligence
                web_verified = False
                if self.web_intel:
                    news = self.web_intel.search_company_news(ticker, days_back=3)
                    if news and news.get('red_flags'):
                        web_verified = True

                return {
                    'ticker': ticker,
                    'signal_type': 'RED_FLAG',
                    'severity': 'CRITICAL',
                    'reason': f"Red flags detected: {', '.join(red_flags[:3])}",
                    'web_verified': web_verified,
                    'sentiment_score': current.get('sentiment_score', 0),
                    'action': 'EXIT_IMMEDIATELY',
                    'confidence': 0.95 if web_verified else 0.75,
                    'timestamp': datetime.now().isoformat()
                }

            # Check sentiment score
            sentiment_score = current.get('sentiment_score', 0)

            if sentiment_score < -5:
                # Strong bearish sentiment
                return {
                    'ticker': ticker,
                    'signal_type': 'NEGATIVE_SENTIMENT',
                    'severity': 'HIGH',
                    'reason': f"Strong bearish sentiment (score: {sentiment_score})",
                    'sentiment_score': sentiment_score,
                    'action': 'CONSIDER_EXIT',
                    'confidence': 0.70,
                    'timestamp': datetime.now().isoformat()
                }

            # Check for sentiment reversal
            if ticker in self.sentiment_history:
                prev = self.sentiment_history[ticker]
                prev_score = prev.get('sentiment_score', 0)
                prev_time = datetime.fromisoformat(prev.get('timestamp'))

                hours_since = (datetime.now() - prev_time).total_seconds() / 3600

                # Sentiment reversal: was bullish, now bearish
                if hours_since <= 48 and prev_score >= 3 and sentiment_score <= -2:
                    return {
                        'ticker': ticker,
                        'signal_type': 'SENTIMENT_REVERSAL',
                        'severity': 'MEDIUM',
                        'reason': f"Sentiment reversed from +{prev_score} to {sentiment_score}",
                        'sentiment_score': sentiment_score,
                        'previous_score': prev_score,
                        'action': 'REDUCE_POSITION',
                        'confidence': 0.65,
                        'timestamp': datetime.now().isoformat()
                    }

            # Update sentiment history
            self.sentiment_history[ticker] = {
                'sentiment_score': sentiment_score,
                'timestamp': datetime.now().isoformat()
            }

            # No exit signal
            return None

        except Exception as e:
            logger.error(f"Error checking exit signal for {ticker}: {e}")
            return None

    def get_summary(self, exit_signals: Dict[str, Dict]) -> Dict:
        """Get summary of exit signals."""

        critical = sum(1 for s in exit_signals.values() if s['severity'] == 'CRITICAL')
        high = sum(1 for s in exit_signals.values() if s['severity'] == 'HIGH')
        medium = sum(1 for s in exit_signals.values() if s['severity'] == 'MEDIUM')

        return {
            'total_holdings_checked': len(self.sentiment_history),
            'exit_signals_detected': len(exit_signals),
            'critical': critical,
            'high': high,
            'medium': medium,
            'tickers_to_exit': [s['ticker'] for s in exit_signals.values() if s['action'] == 'EXIT_IMMEDIATELY'],
            'tickers_to_reduce': [s['ticker'] for s in exit_signals.values() if s['action'] in ['CONSIDER_EXIT', 'REDUCE_POSITION']]
        }


def get_exit_signal_detector():
    """Get exit signal detector instance (singleton)."""
    global _exit_detector_instance
    if '_exit_detector_instance' not in globals():
        _exit_detector_instance = ExitSignalDetector()
    return _exit_detector_instance
