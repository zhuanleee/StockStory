"""
Earnings Call Transcript Fetcher
=================================
Fetch earnings call transcripts from Alpha Vantage API.

Alpha Vantage provides:
- Earnings call transcripts (quarterly)
- Press releases
- Executive interviews

API Endpoint: EARNINGS_CALL_TRANSCRIPT
URL: https://www.alphavantage.co/query?function=EARNINGS_CALL_TRANSCRIPT&symbol=IBM&apikey=demo

Cache transcripts to avoid repeated API calls.
"""

import os
import json
import logging
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from dataclasses import dataclass, asdict
from pathlib import Path

logger = logging.getLogger(__name__)

# Cache directory
DATA_DIR = Path("data/earnings_transcripts")
CACHE_FILE = DATA_DIR / "transcript_cache.json"
CACHE_TTL_DAYS = 90  # Transcripts don't change, cache for 90 days


def ensure_data_dir():
    """Ensure data directory exists."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class EarningsTranscript:
    """Earnings call transcript data."""
    ticker: str
    quarter: str  # e.g., "2024-Q4"
    year: int
    fiscal_date_ending: str
    transcript: str
    fetched_at: str
    source: str = "alpha_vantage"


class TranscriptFetcher:
    """
    Fetch earnings call transcripts from Alpha Vantage.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize transcript fetcher.

        Args:
            api_key: Alpha Vantage API key (reads from env if not provided)
        """
        self.api_key = api_key or os.environ.get('ALPHA_VANTAGE_API_KEY', '')
        self.base_url = "https://www.alphavantage.co/query"
        self.cache = self._load_cache()
        ensure_data_dir()

    def _load_cache(self) -> Dict:
        """Load transcript cache."""
        if CACHE_FILE.exists():
            try:
                with open(CACHE_FILE) as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load transcript cache: {e}")
        return {}

    def _save_cache(self):
        """Save transcript cache."""
        try:
            ensure_data_dir()
            with open(CACHE_FILE, 'w') as f:
                json.dump(self.cache, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save transcript cache: {e}")

    def _get_cached(self, cache_key: str) -> Optional[EarningsTranscript]:
        """Get cached transcript if still valid."""
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            fetched_at = datetime.fromisoformat(cached.get('fetched_at', ''))
            age_days = (datetime.now() - fetched_at).days

            if age_days < CACHE_TTL_DAYS:
                return EarningsTranscript(**cached)

        return None

    def _set_cached(self, cache_key: str, transcript: EarningsTranscript):
        """Cache transcript."""
        self.cache[cache_key] = asdict(transcript)
        self._save_cache()

    def fetch_latest_transcript(self, ticker: str) -> Optional[EarningsTranscript]:
        """
        Fetch the most recent earnings call transcript.

        Args:
            ticker: Stock ticker symbol

        Returns:
            EarningsTranscript or None if not available
        """
        if not self.api_key:
            logger.warning("Alpha Vantage API key not set")
            return None

        cache_key = f"{ticker}:latest"

        # Check cache first
        cached = self._get_cached(cache_key)
        if cached:
            logger.debug(f"Using cached transcript for {ticker}")
            return cached

        try:
            # Fetch from Alpha Vantage
            params = {
                'function': 'EARNINGS_CALL_TRANSCRIPT',
                'symbol': ticker,
                'apikey': self.api_key
            }

            response = requests.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()

            # Check for error
            if 'Error Message' in data:
                logger.warning(f"Alpha Vantage error for {ticker}: {data['Error Message']}")
                return None

            if 'Note' in data:
                # API rate limit
                logger.warning(f"Alpha Vantage rate limit: {data['Note']}")
                return None

            # Extract transcript (Alpha Vantage returns array of quarterly transcripts)
            if not data:
                logger.debug(f"No transcript data for {ticker}")
                return None

            # Get most recent transcript
            # Alpha Vantage returns data in format: list of quarterly reports
            # Structure: [{"fiscalDateEnding": "2024-12-31", "transcript": "..."}]
            transcripts = data if isinstance(data, list) else []

            if not transcripts:
                logger.debug(f"No transcripts available for {ticker}")
                return None

            latest = transcripts[0]  # Most recent is first

            # Parse fiscal date to get quarter and year
            fiscal_date = latest.get('fiscalDateEnding', '')
            if fiscal_date:
                date_obj = datetime.strptime(fiscal_date, '%Y-%m-%d')
                year = date_obj.year
                quarter = f"{year}-Q{(date_obj.month - 1) // 3 + 1}"
            else:
                year = datetime.now().year
                quarter = f"{year}-Q{(datetime.now().month - 1) // 3 + 1}"

            transcript_obj = EarningsTranscript(
                ticker=ticker,
                quarter=quarter,
                year=year,
                fiscal_date_ending=fiscal_date,
                transcript=latest.get('transcript', ''),
                fetched_at=datetime.now().isoformat(),
                source='alpha_vantage'
            )

            # Cache result
            self._set_cached(cache_key, transcript_obj)

            logger.info(f"Fetched transcript for {ticker} ({quarter})")
            return transcript_obj

        except requests.RequestException as e:
            logger.error(f"Request error fetching transcript for {ticker}: {e}")
            return None
        except (KeyError, ValueError, json.JSONDecodeError) as e:
            logger.error(f"Parse error for {ticker} transcript: {e}")
            return None

    def fetch_transcript_by_quarter(
        self,
        ticker: str,
        quarter: str,
        year: int
    ) -> Optional[EarningsTranscript]:
        """
        Fetch transcript for specific quarter.

        Args:
            ticker: Stock ticker
            quarter: Quarter number (1-4)
            year: Year

        Returns:
            EarningsTranscript or None
        """
        cache_key = f"{ticker}:{year}-Q{quarter}"

        # Check cache
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        # Alpha Vantage doesn't support quarter-specific requests easily
        # So we fetch latest and check if it matches
        latest = self.fetch_latest_transcript(ticker)

        if latest and latest.quarter == f"{year}-Q{quarter}":
            return latest

        logger.debug(f"Transcript for {ticker} {year}-Q{quarter} not found")
        return None

    def get_transcript_summary(self, ticker: str, max_length: int = 2000) -> Optional[str]:
        """
        Get a summary/preview of the latest transcript.

        Useful for AI analysis without sending full transcript.

        Args:
            ticker: Stock ticker
            max_length: Maximum characters to return

        Returns:
            Truncated transcript or None
        """
        transcript = self.fetch_latest_transcript(ticker)

        if not transcript or not transcript.transcript:
            return None

        # Return first N characters (usually contains key opening statements)
        summary = transcript.transcript[:max_length]

        # Try to break at sentence boundary
        last_period = summary.rfind('. ')
        if last_period > max_length * 0.8:  # If we can break near the end
            summary = summary[:last_period + 1]

        return summary

    def has_recent_transcript(self, ticker: str, days: int = 45) -> bool:
        """
        Check if ticker has a recent transcript.

        Args:
            ticker: Stock ticker
            days: Number of days to consider "recent"

        Returns:
            True if recent transcript exists
        """
        transcript = self.fetch_latest_transcript(ticker)

        if not transcript:
            return False

        # Check if fiscal date is recent
        try:
            fiscal_date = datetime.strptime(transcript.fiscal_date_ending, '%Y-%m-%d')
            age = (datetime.now() - fiscal_date).days
            return age <= days
        except (ValueError, TypeError):
            return False

    def clear_cache(self, ticker: Optional[str] = None):
        """
        Clear transcript cache.

        Args:
            ticker: If provided, only clear cache for this ticker
        """
        if ticker:
            keys_to_remove = [k for k in self.cache.keys() if k.startswith(f"{ticker}:")]
            for key in keys_to_remove:
                del self.cache[key]
            logger.info(f"Cleared cache for {ticker}")
        else:
            self.cache = {}
            logger.info("Cleared all transcript cache")

        self._save_cache()


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

_fetcher_instance = None


def get_transcript_fetcher() -> TranscriptFetcher:
    """Get singleton transcript fetcher."""
    global _fetcher_instance
    if _fetcher_instance is None:
        _fetcher_instance = TranscriptFetcher()
    return _fetcher_instance


def fetch_latest_transcript(ticker: str) -> Optional[EarningsTranscript]:
    """Fetch latest earnings transcript for ticker."""
    fetcher = get_transcript_fetcher()
    return fetcher.fetch_latest_transcript(ticker)


def get_transcript_summary(ticker: str, max_length: int = 2000) -> Optional[str]:
    """Get transcript summary for AI analysis."""
    fetcher = get_transcript_fetcher()
    return fetcher.get_transcript_summary(ticker, max_length)


def has_recent_earnings_call(ticker: str, days: int = 45) -> bool:
    """Check if ticker has recent earnings call."""
    fetcher = get_transcript_fetcher()
    return fetcher.has_recent_transcript(ticker, days)


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)

    test_ticker = sys.argv[1] if len(sys.argv) > 1 else 'IBM'

    print(f"Fetching transcript for {test_ticker}...")
    print("=" * 60)

    fetcher = TranscriptFetcher()

    # Test latest transcript
    transcript = fetcher.fetch_latest_transcript(test_ticker)

    if transcript:
        print(f"\n✓ Found transcript:")
        print(f"  Ticker: {transcript.ticker}")
        print(f"  Quarter: {transcript.quarter}")
        print(f"  Fiscal Date: {transcript.fiscal_date_ending}")
        print(f"  Length: {len(transcript.transcript)} characters")
        print(f"  Preview: {transcript.transcript[:200]}...")
    else:
        print(f"\n✗ No transcript found for {test_ticker}")

    # Test summary
    print(f"\n\nTesting summary...")
    summary = fetcher.get_transcript_summary(test_ticker)
    if summary:
        print(f"Summary ({len(summary)} chars):\n{summary}")
