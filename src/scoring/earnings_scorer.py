"""
Earnings Intelligence Scorer - Component #38

Scores stocks based on earnings timing, historical performance, and forward guidance.
Integrates with the 4-tier learning system to learn optimal earnings strategies.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime
from pathlib import Path
import logging
import json

logger = logging.getLogger(__name__)

# Persistent cache for AI analysis results
CACHE_DIR = Path("data/earnings_analysis")
ANALYSIS_CACHE_FILE = CACHE_DIR / "ai_analysis_cache.json"


def ensure_cache_dir():
    """Ensure cache directory exists."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class EarningsFeatures:
    """Earnings intelligence features for learning."""

    # Timing
    has_earnings_soon: bool  # Within 3 days
    days_until_earnings: Optional[int]
    days_since_earnings: Optional[int]  # Negative days_until means post-earnings

    # Historical Performance
    beat_rate: Optional[float]  # 0-100%
    avg_surprise: Optional[float]  # Average EPS surprise %

    # Forward Guidance (if available from recent analysis)
    guidance_tone: Optional[str]  # bullish/neutral/bearish
    guidance_strength: float  # 0-1 confidence

    # Risk Flags
    high_impact: bool  # Market-moving stock
    earnings_risk_high: bool  # Earnings within risk window

    # Composite Score
    earnings_confidence: float  # 0-1 overall score


class EarningsScorer:
    """
    Score stocks based on earnings intelligence.

    Integrates with learning system as Component #38.
    """

    def __init__(self):
        self.earnings_cache = {}  # Simple cache to avoid repeated API calls
        self.cache_ttl = 3600  # 1 hour cache
        self.analysis_cache_ttl = 86400 * 7  # 7 days (transcripts don't change)
        self.analysis_cache = self._load_analysis_cache()  # Load persistent cache

    def _load_analysis_cache(self) -> Dict:
        """Load persistent analysis cache from disk."""
        if ANALYSIS_CACHE_FILE.exists():
            try:
                with open(ANALYSIS_CACHE_FILE) as f:
                    cache_data = json.load(f)
                    logger.debug(f"Loaded {len(cache_data)} cached earnings analyses")
                    return cache_data
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load analysis cache: {e}")
        return {}

    def _save_analysis_cache(self):
        """Save analysis cache to disk."""
        try:
            ensure_cache_dir()
            # Only save ticker->timestamp mapping, not full analysis objects
            # (EarningsAnalysis objects can't be JSON serialized directly)
            cache_simplified = {}
            for ticker, (timestamp, analysis) in self.analysis_cache.items():
                if analysis:
                    # Store simplified version with key fields
                    cache_simplified[ticker] = {
                        'timestamp': timestamp,
                        'management_tone': getattr(analysis, 'management_tone', 'neutral'),
                        'guidance_changes': getattr(analysis, 'guidance_changes', []),
                        'growth_catalysts': getattr(analysis, 'growth_catalysts', []),
                        'confidence': getattr(analysis, 'confidence', 0.5)
                    }

            with open(ANALYSIS_CACHE_FILE, 'w') as f:
                json.dump(cache_simplified, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save analysis cache: {e}")

    def _get_earnings_analysis(self, ticker: str):
        """
        Get AI analysis of earnings call transcript.

        Fetches transcript from Alpha Vantage, runs AI analysis, and caches result.

        Returns:
            EarningsAnalysis object or None (or simplified dict from cache)
        """
        # Check cache first (simplified format from disk)
        if ticker in self.analysis_cache:
            cached_data = self.analysis_cache[ticker]

            # Handle both formats: tuple (timestamp, analysis) or dict from disk
            if isinstance(cached_data, dict):
                cached_time = cached_data.get('timestamp', 0)
            else:
                cached_time, _ = cached_data

            if (datetime.now().timestamp() - cached_time) < self.analysis_cache_ttl:
                # Return simplified cached data as object-like dict
                if isinstance(cached_data, dict):
                    # Create a simple namespace object
                    from types import SimpleNamespace
                    analysis = SimpleNamespace(**{
                        'management_tone': cached_data.get('management_tone', 'neutral'),
                        'guidance_changes': cached_data.get('guidance_changes', []),
                        'growth_catalysts': cached_data.get('growth_catalysts', []),
                        'confidence': cached_data.get('confidence', 0.5)
                    })
                    return analysis
                else:
                    return cached_data[1]  # Return analysis from tuple

        try:
            # Fetch transcript
            from src.data.transcript_fetcher import get_transcript_summary

            transcript = get_transcript_summary(ticker, max_length=2000)

            if not transcript:
                logger.debug(f"No transcript available for {ticker}")
                return None

            # Get earnings data for context
            from src.analysis.earnings import get_earnings_info
            earnings_data = get_earnings_info(ticker)

            # Run AI analysis
            from src.ai.ai_enhancements import analyze_earnings

            analysis = analyze_earnings(
                ticker=ticker,
                transcript=transcript,
                earnings_data=earnings_data
            )

            if analysis:
                # Cache result in memory
                self.analysis_cache[ticker] = (datetime.now().timestamp(), analysis)

                # Save to disk (async to avoid blocking)
                try:
                    self._save_analysis_cache()
                except Exception as e:
                    logger.debug(f"Failed to save analysis cache: {e}")

                logger.info(f"Analyzed earnings call for {ticker}: {analysis.management_tone}")
                return analysis

        except Exception as e:
            logger.debug(f"Error analyzing earnings for {ticker}: {e}")

        return None

    def score(self, ticker: str, use_cache: bool = True) -> float:
        """
        Return 0-1 earnings confidence score.

        Higher score = better earnings setup
        Lower score = higher earnings risk

        Args:
            ticker: Stock ticker
            use_cache: Use cached data if available

        Returns:
            0-1 confidence score
        """
        try:
            features = self.get_features(ticker, use_cache=use_cache)
            return features.earnings_confidence

        except Exception as e:
            logger.warning(f"Error scoring earnings for {ticker}: {e}")
            return 0.5  # Neutral score on error

    def get_features(self, ticker: str, use_cache: bool = True) -> EarningsFeatures:
        """
        Get all earnings features for a ticker.

        Args:
            ticker: Stock ticker
            use_cache: Use cached data if available

        Returns:
            EarningsFeatures dataclass
        """
        # Check cache
        if use_cache and ticker in self.earnings_cache:
            cached_time, cached_features = self.earnings_cache[ticker]
            if (datetime.now().timestamp() - cached_time) < self.cache_ttl:
                return cached_features

        # Get earnings data
        from src.analysis.earnings import get_earnings_info

        info = get_earnings_info(ticker)

        # Extract features
        days_until = info.get('days_until')
        has_earnings_soon = days_until is not None and 0 <= days_until <= 3
        days_since = -days_until if days_until and days_until < 0 else None

        beat_rate = info.get('beat_rate')
        avg_surprise = info.get('historical_surprise')
        high_impact = info.get('high_impact', False)

        # Calculate timing score (0-1)
        timing_score = self._calculate_timing_score(days_until, days_since)

        # Calculate performance score (0-1)
        performance_score = self._calculate_performance_score(beat_rate, avg_surprise)

        # Calculate guidance score (0-1)
        guidance_score = self._calculate_guidance_score(ticker)

        # Composite earnings confidence
        # Weighting: timing 40%, performance 40%, guidance 20%
        earnings_confidence = (
            timing_score * 0.4 +
            performance_score * 0.4 +
            guidance_score * 0.2
        )

        # Build features
        features = EarningsFeatures(
            has_earnings_soon=has_earnings_soon,
            days_until_earnings=days_until if days_until and days_until >= 0 else None,
            days_since_earnings=days_since,
            beat_rate=beat_rate,
            avg_surprise=avg_surprise,
            guidance_tone=None,  # Would come from recent AI analysis
            guidance_strength=guidance_score,
            high_impact=high_impact,
            earnings_risk_high=has_earnings_soon,
            earnings_confidence=earnings_confidence
        )

        # Cache result
        self.earnings_cache[ticker] = (datetime.now().timestamp(), features)

        return features

    def _calculate_timing_score(
        self,
        days_until: Optional[int],
        days_since: Optional[int]
    ) -> float:
        """
        Calculate timing score (0-1).

        Strategy:
        - Post-earnings (days_since 0-30): High score (opportunity)
        - Far from earnings (>14 days): Good score (safe)
        - Near earnings (3-14 days): Moderate score (caution)
        - Very near earnings (0-2 days): Low score (avoid)
        - Unknown: Neutral score

        Returns:
            0-1 score
        """
        # Post-earnings window (positive signal)
        if days_since is not None:
            if days_since <= 7:
                return 0.95  # Strong post-earnings momentum window
            elif days_since <= 30:
                return 0.80  # Good post-earnings window
            else:
                # Treat as unknown timing after 30 days
                return 0.65

        # Pre-earnings timing
        if days_until is None:
            return 0.65  # Unknown = slightly favorable (no imminent risk)

        if days_until < 0:
            # Should have been caught by days_since above, but handle anyway
            return 0.80

        if days_until == 0:
            return 0.10  # Earnings today - very risky

        if days_until <= 2:
            return 0.20  # Earnings very soon - high risk

        if days_until <= 5:
            return 0.40  # Earnings soon - moderate risk

        if days_until <= 10:
            return 0.60  # Earnings approaching - mild risk

        if days_until <= 14:
            return 0.70  # Two weeks out - minimal risk

        # Far from earnings
        return 0.80  # Safe timing

    def _calculate_performance_score(
        self,
        beat_rate: Optional[float],
        avg_surprise: Optional[float]
    ) -> float:
        """
        Calculate historical performance score (0-1).

        Based on:
        - Beat rate: % of times company beat estimates
        - Avg surprise: Average EPS surprise %

        Returns:
            0-1 score
        """
        if beat_rate is None and avg_surprise is None:
            return 0.5  # No data = neutral

        scores = []
        weights = []

        # Beat rate component
        if beat_rate is not None:
            # Normalize 0-100% to 0-1
            beat_score = beat_rate / 100.0
            scores.append(beat_score)
            weights.append(0.6)  # 60% weight

        # Surprise component
        if avg_surprise is not None:
            # Map -20% to +20% surprise onto 0 to 1
            # -20% or worse = 0, +20% or better = 1
            surprise_score = max(0.0, min(1.0, (avg_surprise + 20) / 40))
            scores.append(surprise_score)
            weights.append(0.4)  # 40% weight

        # Weighted average
        total_weight = sum(weights)
        if total_weight == 0:
            return 0.5

        performance_score = sum(s * w for s, w in zip(scores, weights)) / total_weight

        return performance_score

    def _calculate_guidance_score(self, ticker: str) -> float:
        """
        Calculate forward guidance score (0-1).

        Uses:
        1. AI analysis of earnings call transcripts
        2. Executive commentary from news/filings
        3. Recent guidance changes

        Returns:
            0-1 score
        """
        score = 0.5  # Start neutral

        # Check for recent AI earnings analysis (from transcripts)
        try:
            analysis = self._get_earnings_analysis(ticker)

            if analysis:
                # Management tone component (0-40% impact)
                tone_map = {
                    'bullish': 0.8,
                    'neutral': 0.5,
                    'bearish': 0.2
                }
                tone_score = tone_map.get(analysis.management_tone, 0.5)

                # Guidance changes bonus/penalty
                guidance_modifier = 0.0
                if analysis.guidance_changes:
                    for change in analysis.guidance_changes:
                        change_lower = change.lower()
                        if 'raised' in change_lower or 'increased' in change_lower:
                            guidance_modifier += 0.1
                        elif 'lowered' in change_lower or 'reduced' in change_lower:
                            guidance_modifier -= 0.1

                # Growth catalysts boost
                catalyst_boost = min(0.1, len(analysis.growth_catalysts) * 0.03)

                # Calculate AI-based score
                ai_score = min(1.0, max(0.0, tone_score + guidance_modifier + catalyst_boost))

                # Weight AI analysis by confidence
                score = score * (1 - analysis.confidence) + ai_score * analysis.confidence

                logger.debug(f"{ticker} earnings AI: tone={analysis.management_tone}, "
                           f"guidance_changes={len(analysis.guidance_changes)}, score={ai_score:.2f}")

        except Exception as e:
            logger.debug(f"Could not get earnings analysis for {ticker}: {e}")

        # Also check executive commentary for recent guidance signals
        try:
            from src.intelligence.executive_commentary import get_executive_commentary

            commentary = get_executive_commentary(ticker, days_back=30)

            if commentary.has_recent_commentary:
                # Guidance tone from recent commentary
                guidance_tone_map = {
                    'raised': 0.9,
                    'maintained': 0.6,
                    'lowered': 0.3,
                    'none': 0.5
                }
                commentary_score = guidance_tone_map.get(commentary.guidance_tone, 0.5)

                # Blend with existing score (30% weight to commentary)
                score = score * 0.7 + commentary_score * 0.3

                logger.debug(f"{ticker} exec commentary: guidance={commentary.guidance_tone}, "
                           f"sentiment={commentary.overall_sentiment}")

        except Exception as e:
            logger.debug(f"Could not get executive commentary for {ticker}: {e}")

        return score

    def score_multiple(self, tickers: list) -> Dict[str, float]:
        """
        Score multiple tickers efficiently.

        Args:
            tickers: List of tickers

        Returns:
            Dict of {ticker: score}
        """
        scores = {}
        for ticker in tickers:
            scores[ticker] = self.score(ticker)
        return scores

    def get_earnings_risk_level(self, ticker: str) -> str:
        """
        Get human-readable risk level.

        Returns:
            "very_high", "high", "moderate", "low", or "very_low"
        """
        score = self.score(ticker)

        if score >= 0.8:
            return "very_low"  # Great earnings setup
        elif score >= 0.6:
            return "low"  # Good setup
        elif score >= 0.4:
            return "moderate"  # Neutral
        elif score >= 0.2:
            return "high"  # Risky
        else:
            return "very_high"  # Very risky (earnings imminent)

    def should_avoid_entry(self, ticker: str, threshold: float = 0.3) -> bool:
        """
        Check if ticker should be avoided due to earnings risk.

        Args:
            ticker: Stock ticker
            threshold: Score threshold below which to avoid (default 0.3)

        Returns:
            True if should avoid, False otherwise
        """
        score = self.score(ticker)
        return score < threshold


# Singleton instance
_earnings_scorer = None


def get_earnings_scorer() -> EarningsScorer:
    """Get singleton earnings scorer instance."""
    global _earnings_scorer
    if _earnings_scorer is None:
        _earnings_scorer = EarningsScorer()
    return _earnings_scorer


if __name__ == "__main__":
    # Quick test
    scorer = get_earnings_scorer()

    test_tickers = ['NVDA', 'AAPL', 'TSLA']

    print("Earnings Scorer Test")
    print("=" * 60)

    for ticker in test_tickers:
        score = scorer.score(ticker)
        risk = scorer.get_earnings_risk_level(ticker)
        avoid = scorer.should_avoid_entry(ticker)

        print(f"\n{ticker}:")
        print(f"  Confidence Score: {score:.2f}/1.0")
        print(f"  Risk Level: {risk}")
        print(f"  Avoid Entry: {avoid}")

        features = scorer.get_features(ticker)
        print(f"  Days Until Earnings: {features.days_until_earnings}")
        print(f"  Beat Rate: {features.beat_rate}%")
        print(f"  Avg Surprise: {features.avg_surprise}%")
        print(f"  High Impact: {features.high_impact}")
