"""
Hard Data Scanner - Multi-Signal Conviction System
===================================================

Prioritizes objective, leading indicators over sentiment:
1. Insider Activity (SEC Form 4) - Management confidence
2. Options Flow (Polygon) - Smart money positioning
3. Patents (PatentsView) - R&D investment signals
4. Gov Contracts (USASpending) - Revenue visibility
5. Sentiment (AI) - Narrative validation (not discovery)
6. Technical - Entry timing

The key insight: Hard data leads, sentiment follows.
Best trades = Hard data BEFORE sentiment catches up.

Usage:
    from src.intelligence.hard_data_scanner import get_hard_data_scanner

    scanner = get_hard_data_scanner()

    # Scan a single ticker
    conviction = scanner.scan_ticker('NVDA')

    # Scan watchlist for high-conviction setups
    results = scanner.scan_watchlist(['NVDA', 'PLTR', 'LMT'])

    # Get high-conviction alerts
    alerts = scanner.get_high_conviction_alerts(min_score=70)
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

logger = logging.getLogger(__name__)


@dataclass
class InsiderSignal:
    """Insider trading signal from SEC Form 4."""
    ticker: str
    total_bought: float = 0  # Dollar value
    total_sold: float = 0
    buy_transactions: int = 0
    sell_transactions: int = 0
    net_activity: float = 0  # Positive = net buying
    notable_buyers: List[str] = field(default_factory=list)
    days_lookback: int = 90
    score: float = 0  # 0-100
    signal: str = "neutral"  # bullish, bearish, neutral

    def calculate_score(self):
        """Calculate insider signal score."""
        if self.total_bought > 500000 and self.buy_transactions >= 2:
            self.score = min(100, 60 + (self.total_bought / 100000))
            self.signal = "strong_bullish"
        elif self.total_bought > 200000:
            self.score = min(80, 40 + (self.total_bought / 50000))
            self.signal = "bullish"
        elif self.total_sold > 1000000 and self.sell_transactions >= 3:
            self.score = max(0, 30 - (self.total_sold / 500000))
            self.signal = "bearish"
        elif self.net_activity > 0:
            self.score = 50 + min(30, self.net_activity / 100000)
            self.signal = "slightly_bullish"
        else:
            self.score = 50
            self.signal = "neutral"


@dataclass
class OptionsSignal:
    """Options flow signal from Polygon."""
    ticker: str
    call_volume: int = 0
    put_volume: int = 0
    call_premium: float = 0  # Total premium
    put_premium: float = 0
    unusual_calls: List[Dict] = field(default_factory=list)
    unusual_puts: List[Dict] = field(default_factory=list)
    put_call_ratio: float = 1.0
    score: float = 0
    signal: str = "neutral"

    def calculate_score(self):
        """Calculate options flow score."""
        # Bullish: Low P/C ratio, high call premium
        if self.put_call_ratio < 0.5 and self.call_premium > 1000000:
            self.score = min(100, 70 + len(self.unusual_calls) * 5)
            self.signal = "strong_bullish"
        elif self.put_call_ratio < 0.7 and self.call_premium > 500000:
            self.score = min(85, 55 + len(self.unusual_calls) * 5)
            self.signal = "bullish"
        elif self.put_call_ratio > 1.5 and self.put_premium > 1000000:
            self.score = max(0, 30 - len(self.unusual_puts) * 5)
            self.signal = "bearish"
        elif self.put_call_ratio < 0.8:
            self.score = 55 + (0.8 - self.put_call_ratio) * 50
            self.signal = "slightly_bullish"
        else:
            self.score = 50
            self.signal = "neutral"


@dataclass
class PatentSignal:
    """Patent activity signal from PatentsView."""
    ticker: str
    patent_count: int = 0
    yoy_change: float = 0  # Year-over-year change %
    recent_patents: List[Dict] = field(default_factory=list)
    top_keywords: List[str] = field(default_factory=list)
    in_hot_theme: bool = False
    theme_name: str = ""
    score: float = 0
    signal: str = "neutral"

    def calculate_score(self):
        """Calculate patent signal score."""
        if self.yoy_change > 50 and self.in_hot_theme:
            self.score = min(100, 70 + self.yoy_change / 5)
            self.signal = "strong_bullish"
        elif self.yoy_change > 30:
            self.score = min(85, 50 + self.yoy_change)
            self.signal = "bullish"
        elif self.yoy_change > 10:
            self.score = 50 + self.yoy_change
            self.signal = "slightly_bullish"
        elif self.yoy_change < -20:
            self.score = max(20, 50 + self.yoy_change)
            self.signal = "bearish"
        else:
            self.score = 50
            self.signal = "neutral"


@dataclass
class ContractSignal:
    """Government contract signal from USASpending."""
    ticker: str
    total_value: float = 0  # Total contract value
    contract_count: int = 0
    recent_awards: List[Dict] = field(default_factory=list)
    top_agencies: List[str] = field(default_factory=list)
    yoy_change: float = 0
    in_hot_theme: bool = False
    score: float = 0
    signal: str = "neutral"

    def calculate_score(self):
        """Calculate contract signal score."""
        value_billions = self.total_value / 1e9
        if value_billions > 1 and self.yoy_change > 20:
            self.score = min(100, 70 + value_billions * 5)
            self.signal = "strong_bullish"
        elif value_billions > 0.5 or self.yoy_change > 30:
            self.score = min(85, 55 + value_billions * 10)
            self.signal = "bullish"
        elif value_billions > 0.1:
            self.score = 50 + value_billions * 20
            self.signal = "slightly_bullish"
        else:
            self.score = 50
            self.signal = "neutral"


@dataclass
class SentimentSignal:
    """Sentiment validation signal from AI analysis."""
    ticker: str
    news_sentiment: float = 0  # -1 to 1
    social_sentiment: float = 0
    analyst_sentiment: float = 0
    news_volume: int = 0
    is_euphoric: bool = False  # Warning flag - might be too late
    narrative_strength: float = 0  # 0-100
    score: float = 0
    signal: str = "neutral"

    def calculate_score(self):
        """Calculate sentiment validation score."""
        avg_sentiment = (self.news_sentiment + self.social_sentiment) / 2

        # Euphoric sentiment is actually a WARNING (might be late)
        if self.is_euphoric:
            self.score = 40  # Penalize - crowd already in
            self.signal = "warning_euphoric"
        elif avg_sentiment > 0.5 and not self.is_euphoric:
            self.score = min(80, 60 + avg_sentiment * 30)
            self.signal = "bullish_not_crowded"
        elif avg_sentiment > 0.2:
            self.score = 55 + avg_sentiment * 25
            self.signal = "slightly_bullish"
        elif avg_sentiment < -0.3:
            self.score = max(30, 50 + avg_sentiment * 30)
            self.signal = "bearish"
        else:
            self.score = 50
            self.signal = "neutral"


@dataclass
class TechnicalSignal:
    """Technical setup signal for entry timing."""
    ticker: str
    price: float = 0
    above_20sma: bool = False
    above_50sma: bool = False
    above_200sma: bool = False
    in_squeeze: bool = False
    volume_ratio: float = 1.0  # vs 20-day avg
    rs_rating: float = 0  # Relative strength
    distance_from_high: float = 0  # % from 52-week high
    is_extended: bool = False  # Warning - might be too extended
    score: float = 0
    signal: str = "neutral"

    def calculate_score(self):
        """Calculate technical score for entry timing."""
        base_score = 50

        # Trend alignment
        if self.above_20sma:
            base_score += 10
        if self.above_50sma:
            base_score += 10
        if self.above_200sma:
            base_score += 5

        # Setup quality
        if self.in_squeeze:
            base_score += 15  # Tight consolidation is good
        if self.volume_ratio > 1.5:
            base_score += 5

        # Relative strength
        if self.rs_rating > 80:
            base_score += 10
        elif self.rs_rating > 60:
            base_score += 5

        # Penalize if extended
        if self.is_extended or self.distance_from_high < 5:
            base_score -= 15
            self.signal = "warning_extended"
        elif base_score >= 75:
            self.signal = "buyable"
        elif base_score >= 60:
            self.signal = "watchable"
        else:
            self.signal = "not_ready"

        self.score = min(100, max(0, base_score))


@dataclass
class ConvictionResult:
    """Final conviction score combining all signals."""
    ticker: str
    conviction_score: float = 0

    # Component signals
    insider: Optional[InsiderSignal] = None
    options: Optional[OptionsSignal] = None
    patents: Optional[PatentSignal] = None
    contracts: Optional[ContractSignal] = None
    sentiment: Optional[SentimentSignal] = None
    technical: Optional[TechnicalSignal] = None

    # Summary
    bullish_signals: int = 0
    bearish_signals: int = 0
    warnings: List[str] = field(default_factory=list)
    recommendation: str = "HOLD"
    reasoning: List[str] = field(default_factory=list)

    timestamp: str = ""

    def calculate_conviction(self):
        """Calculate overall conviction score with proper weighting."""
        weights = {
            'insider': 0.25,    # Highest weight - management knows
            'options': 0.25,    # Smart money positioning
            'patents': 0.12,    # Long-term signal
            'contracts': 0.13,  # Revenue visibility
            'sentiment': 0.10,  # Validation only
            'technical': 0.15,  # Entry timing
        }

        total_weight = 0
        weighted_score = 0

        signals = [
            ('insider', self.insider),
            ('options', self.options),
            ('patents', self.patents),
            ('contracts', self.contracts),
            ('sentiment', self.sentiment),
            ('technical', self.technical),
        ]

        for name, signal in signals:
            if signal and signal.score > 0:
                weighted_score += signal.score * weights[name]
                total_weight += weights[name]

                # Count bullish/bearish
                if 'bullish' in signal.signal:
                    self.bullish_signals += 1
                    self.reasoning.append(f"{name.title()}: {signal.signal}")
                elif 'bearish' in signal.signal:
                    self.bearish_signals += 1
                    self.reasoning.append(f"{name.title()}: {signal.signal}")

                # Track warnings
                if 'warning' in signal.signal:
                    self.warnings.append(f"{name}: {signal.signal}")

        if total_weight > 0:
            self.conviction_score = weighted_score / total_weight

        # Determine recommendation
        if self.conviction_score >= 75 and self.bullish_signals >= 3:
            self.recommendation = "STRONG BUY"
        elif self.conviction_score >= 65 and self.bullish_signals >= 2:
            self.recommendation = "BUY"
        elif self.conviction_score >= 55:
            self.recommendation = "WATCH"
        elif self.conviction_score <= 35:
            self.recommendation = "AVOID"
        else:
            self.recommendation = "HOLD"

        # Warnings can downgrade
        if len(self.warnings) >= 2:
            if self.recommendation == "STRONG BUY":
                self.recommendation = "BUY"
            elif self.recommendation == "BUY":
                self.recommendation = "WATCH"

        self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Convert to dictionary for API response."""
        return {
            'ticker': self.ticker,
            'conviction_score': round(self.conviction_score, 1),
            'recommendation': self.recommendation,
            'bullish_signals': self.bullish_signals,
            'bearish_signals': self.bearish_signals,
            'warnings': self.warnings,
            'reasoning': self.reasoning,
            'signals': {
                'insider': asdict(self.insider) if self.insider else None,
                'options': asdict(self.options) if self.options else None,
                'patents': asdict(self.patents) if self.patents else None,
                'contracts': asdict(self.contracts) if self.contracts else None,
                'sentiment': asdict(self.sentiment) if self.sentiment else None,
                'technical': asdict(self.technical) if self.technical else None,
            },
            'timestamp': self.timestamp
        }


class HardDataScanner:
    """
    Multi-signal conviction scanner prioritizing hard data.

    Scan priority:
    1. Insider Activity (SEC) - 25%
    2. Options Flow (Polygon) - 25%
    3. Patents (PatentsView) - 12%
    4. Gov Contracts - 13%
    5. Sentiment (validate) - 10%
    6. Technical (timing) - 15%
    """

    def __init__(self):
        self._cache: Dict[str, ConvictionResult] = {}
        self._cache_ttl = 300  # 5 minutes
        self._cache_times: Dict[str, datetime] = {}
        self._lock = threading.Lock()

        logger.info("HardDataScanner initialized")

    def _get_insider_signal(self, ticker: str) -> InsiderSignal:
        """Fetch insider trading data from SEC."""
        signal = InsiderSignal(ticker=ticker)

        try:
            from src.data.sec_edgar import SECEdgarClient

            client = SECEdgarClient()
            transactions = client.get_insider_transactions(ticker, days_back=90)

            if transactions:
                signal.buy_transactions = len([t for t in transactions if t.get('form') == '4'])
                # Note: Actual buy/sell parsing would require deeper Form 4 analysis
                # For now, count of Form 4 filings as activity indicator
                signal.total_bought = signal.buy_transactions * 100000  # Estimate
                signal.notable_buyers = [f"Form 4 filing #{i+1}" for i in range(min(3, len(transactions)))]

            signal.calculate_score()

        except ImportError:
            logger.debug("SEC Edgar not available")
        except Exception as e:
            logger.warning(f"Insider signal error for {ticker}: {e}")

        return signal

    def _get_options_signal(self, ticker: str) -> OptionsSignal:
        """Fetch options flow data from Polygon."""
        signal = OptionsSignal(ticker=ticker)

        try:
            from src.data.polygon_provider import (
                get_options_flow_summary_sync,
                analyze_unusual_options_sync
            )

            flow = get_options_flow_summary_sync(ticker)
            unusual = analyze_unusual_options_sync(ticker, volume_threshold=2.0)

            if flow:
                signal.call_volume = flow.get('total_call_volume', 0)
                signal.put_volume = flow.get('total_put_volume', 0)
                signal.call_premium = flow.get('total_call_premium', 0)
                signal.put_premium = flow.get('total_put_premium', 0)

                if signal.put_volume > 0:
                    signal.put_call_ratio = signal.call_volume / signal.put_volume

            if unusual and unusual.get('has_unusual_activity'):
                signal.unusual_calls = unusual.get('unusual_calls', [])[:5]
                signal.unusual_puts = unusual.get('unusual_puts', [])[:5]

            signal.calculate_score()

        except ImportError:
            logger.debug("Polygon options not available")
        except Exception as e:
            logger.warning(f"Options signal error for {ticker}: {e}")

        return signal

    def _get_patent_signal(self, ticker: str) -> PatentSignal:
        """Fetch patent data from PatentsView."""
        signal = PatentSignal(ticker=ticker)

        try:
            from src.data.patents import get_patent_intelligence

            intel = get_patent_intelligence()
            activity = intel.get_company_patents(ticker)

            if activity:
                signal.patent_count = activity.patent_count
                signal.yoy_change = activity.yoy_change
                signal.recent_patents = [asdict(p) if hasattr(p, '__dataclass_fields__') else p
                                         for p in activity.recent_patents[:5]]
                signal.top_keywords = activity.top_keywords[:5]
                signal.in_hot_theme = activity.signal_strength > 0.6

            signal.calculate_score()

        except ImportError:
            logger.debug("Patents module not available")
        except Exception as e:
            logger.warning(f"Patent signal error for {ticker}: {e}")

        return signal

    def _get_contract_signal(self, ticker: str) -> ContractSignal:
        """Fetch government contract data."""
        signal = ContractSignal(ticker=ticker)

        try:
            from src.data.gov_contracts import get_contract_intelligence

            intel = get_contract_intelligence()
            activity = intel.get_company_contracts(ticker)

            if activity:
                signal.total_value = activity.total_value
                signal.contract_count = activity.contract_count
                signal.recent_awards = activity.recent_contracts[:5] if hasattr(activity, 'recent_contracts') else []
                signal.top_agencies = activity.top_agencies[:3] if hasattr(activity, 'top_agencies') else []
                signal.yoy_change = getattr(activity, 'yoy_change', 0)

            signal.calculate_score()

        except ImportError:
            logger.debug("Contracts module not available")
        except Exception as e:
            logger.warning(f"Contract signal error for {ticker}: {e}")

        return signal

    def _get_sentiment_signal(self, ticker: str) -> SentimentSignal:
        """Fetch sentiment as validation (not discovery)."""
        signal = SentimentSignal(ticker=ticker)

        try:
            from src.analysis.news_analyzer import get_ticker_sentiment

            sentiment_data = get_ticker_sentiment(ticker)

            if sentiment_data:
                signal.news_sentiment = sentiment_data.get('overall_score', 0)
                signal.news_volume = sentiment_data.get('news_count', 0)
                signal.narrative_strength = sentiment_data.get('confidence', 50)

                # Check for euphoria (warning sign)
                if signal.news_sentiment > 0.7 and signal.news_volume > 20:
                    signal.is_euphoric = True

            signal.calculate_score()

        except ImportError:
            logger.debug("Sentiment module not available")
        except Exception as e:
            logger.warning(f"Sentiment signal error for {ticker}: {e}")

        return signal

    def _get_technical_signal(self, ticker: str) -> TechnicalSignal:
        """Fetch technical data for entry timing."""
        signal = TechnicalSignal(ticker=ticker)

        try:
            import yfinance as yf
            import pandas as pd

            stock = yf.Ticker(ticker)
            df = stock.history(period='6mo')

            if len(df) >= 50:
                close = df['Close']
                volume = df['Volume']

                signal.price = float(close.iloc[-1])

                # Moving averages
                sma_20 = close.rolling(20).mean().iloc[-1]
                sma_50 = close.rolling(50).mean().iloc[-1]
                sma_200 = close.rolling(200).mean().iloc[-1] if len(df) >= 200 else sma_50

                signal.above_20sma = bool(signal.price > sma_20)
                signal.above_50sma = bool(signal.price > sma_50)
                signal.above_200sma = bool(signal.price > sma_200)

                # Volume
                avg_volume = volume.rolling(20).mean().iloc[-1]
                signal.volume_ratio = float(volume.iloc[-1] / avg_volume) if avg_volume > 0 else 1.0

                # Squeeze detection (Bollinger inside Keltner)
                bb_upper = close.rolling(20).mean() + 2 * close.rolling(20).std()
                bb_lower = close.rolling(20).mean() - 2 * close.rolling(20).std()
                atr = (df['High'] - df['Low']).rolling(20).mean()
                kc_upper = sma_20 + 1.5 * atr.iloc[-1]
                kc_lower = sma_20 - 1.5 * atr.iloc[-1]

                signal.in_squeeze = bool(bb_upper.iloc[-1] < kc_upper and bb_lower.iloc[-1] > kc_lower)

                # Distance from high
                high_52w = close.rolling(252).max().iloc[-1] if len(df) >= 252 else close.max()
                signal.distance_from_high = float(((high_52w - signal.price) / high_52w) * 100)

                # Extended check
                signal.is_extended = bool(signal.price > sma_20 * 1.15)  # More than 15% above 20 SMA

            signal.calculate_score()

        except Exception as e:
            logger.warning(f"Technical signal error for {ticker}: {e}")

        return signal

    def scan_ticker(self, ticker: str, use_cache: bool = True) -> ConvictionResult:
        """
        Scan a single ticker for conviction score.

        Args:
            ticker: Stock symbol
            use_cache: Whether to use cached results

        Returns:
            ConvictionResult with all signals and final score
        """
        ticker = ticker.upper()

        # Check cache
        if use_cache:
            with self._lock:
                if ticker in self._cache:
                    cache_time = self._cache_times.get(ticker)
                    if cache_time and (datetime.now() - cache_time).seconds < self._cache_ttl:
                        logger.debug(f"Returning cached result for {ticker}")
                        return self._cache[ticker]

        logger.info(f"Scanning {ticker} for conviction signals...")

        result = ConvictionResult(ticker=ticker)

        # Fetch all signals in parallel
        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = {
                executor.submit(self._get_insider_signal, ticker): 'insider',
                executor.submit(self._get_options_signal, ticker): 'options',
                executor.submit(self._get_patent_signal, ticker): 'patents',
                executor.submit(self._get_contract_signal, ticker): 'contracts',
                executor.submit(self._get_sentiment_signal, ticker): 'sentiment',
                executor.submit(self._get_technical_signal, ticker): 'technical',
            }

            for future in as_completed(futures):
                signal_type = futures[future]
                try:
                    signal = future.result(timeout=30)
                    setattr(result, signal_type, signal)
                except Exception as e:
                    logger.warning(f"Failed to get {signal_type} for {ticker}: {e}")

        # Calculate final conviction
        result.calculate_conviction()

        # Cache result
        with self._lock:
            self._cache[ticker] = result
            self._cache_times[ticker] = datetime.now()

        logger.info(f"{ticker}: Conviction {result.conviction_score:.1f}, {result.recommendation}")

        return result

    def scan_watchlist(self, tickers: List[str], min_score: float = 0) -> List[ConvictionResult]:
        """
        Scan multiple tickers and return sorted by conviction.

        Args:
            tickers: List of stock symbols
            min_score: Minimum conviction score to include

        Returns:
            List of ConvictionResults sorted by score descending
        """
        results = []

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(self.scan_ticker, t): t for t in tickers}

            for future in as_completed(futures):
                ticker = futures[future]
                try:
                    result = future.result(timeout=60)
                    if result.conviction_score >= min_score:
                        results.append(result)
                except Exception as e:
                    logger.warning(f"Failed to scan {ticker}: {e}")

        # Sort by conviction score
        results.sort(key=lambda x: x.conviction_score, reverse=True)

        return results

    def get_high_conviction_alerts(self, min_score: float = 70) -> List[ConvictionResult]:
        """
        Get high-conviction setups from default watchlist.

        Args:
            min_score: Minimum conviction score (default 70)

        Returns:
            List of high-conviction results
        """
        # Default watchlist - top institutional holdings + theme leaders
        default_tickers = [
            'NVDA', 'AMD', 'PLTR', 'CRWD', 'NET',  # AI/Tech
            'LMT', 'RTX', 'NOC', 'GD', 'BA',       # Defense
            'CEG', 'VST', 'SMR', 'NNE',            # Nuclear/Energy
            'LLY', 'NVO', 'MRNA',                   # Biotech
            'TSLA', 'RIVN',                         # EV
            'META', 'GOOGL', 'MSFT', 'AMZN',       # Big Tech
        ]

        return self.scan_watchlist(default_tickers, min_score=min_score)

    def clear_cache(self):
        """Clear the results cache."""
        with self._lock:
            self._cache.clear()
            self._cache_times.clear()


# Singleton instance
_scanner: Optional[HardDataScanner] = None
_scanner_lock = threading.Lock()


def get_hard_data_scanner() -> HardDataScanner:
    """Get or create the singleton scanner instance."""
    global _scanner
    if _scanner is None:
        with _scanner_lock:
            if _scanner is None:
                _scanner = HardDataScanner()
    return _scanner
