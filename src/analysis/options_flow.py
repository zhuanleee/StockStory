#!/usr/bin/env python3
"""
Enhanced Options Flow Analyzer

Features:
1. Real-time unusual activity detection
2. Smart money flow tracking
3. GEX (Gamma Exposure) calculation
4. Max Pain analysis
5. IV Rank/Percentile
6. Historical flow tracking
7. Options screener
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
from pathlib import Path

from utils import get_logger

logger = get_logger(__name__)

# Try to import data providers
try:
    from src.data.polygon_provider import (
        get_options_flow_sync,
        get_unusual_options_sync,
        get_options_chain_sync,
        get_technical_summary_sync,
    )
    HAS_POLYGON = True
except ImportError:
    HAS_POLYGON = False
    logger.warning("Polygon provider not available")

try:
    import yfinance as yf
    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False


# =============================================================================
# CONSTANTS
# =============================================================================

# Premium thresholds for categorization
PREMIUM_THRESHOLDS = {
    'retail': 10000,      # < $10K
    'small': 50000,       # $10K - $50K
    'medium': 100000,     # $50K - $100K
    'large': 500000,      # $100K - $500K
    'whale': 1000000,     # > $1M
}

# Unusual activity thresholds
UNUSUAL_THRESHOLDS = {
    'volume_oi_ratio': 2.0,      # Volume > 2x Open Interest
    'volume_avg_ratio': 3.0,     # Volume > 3x average
    'premium_min': 25000,        # Minimum premium to track
}

# Smart money indicators
SMART_MONEY_SIGNALS = {
    'sweep': 'Aggressive buying across exchanges',
    'block': 'Single large block trade',
    'split': 'Large order split into smaller pieces',
    'dark_pool': 'Off-exchange / dark pool print',
}


# =============================================================================
# UNUSUAL ACTIVITY FEED
# =============================================================================

class UnusualActivityFeed:
    """Real-time unusual options activity tracker."""

    def __init__(self, cache_dir: str = "/data"):
        self.cache_dir = Path(cache_dir)
        self.cache_file = self.cache_dir / "unusual_options_feed.json"
        self._feed_cache = []
        self._load_cache()

    def _load_cache(self):
        """Load cached feed data."""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'r') as f:
                    data = json.load(f)
                    self._feed_cache = data.get('feed', [])
        except Exception as e:
            logger.error(f"Error loading feed cache: {e}")
            self._feed_cache = []

    def _save_cache(self):
        """Save feed data to cache."""
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file, 'w') as f:
                json.dump({
                    'feed': self._feed_cache[-500:],  # Keep last 500 entries
                    'updated_at': datetime.now().isoformat()
                }, f)
        except Exception as e:
            logger.error(f"Error saving feed cache: {e}")

    def add_activity(self, activity: Dict) -> None:
        """Add new unusual activity to feed."""
        activity['timestamp'] = datetime.now().isoformat()
        activity['id'] = f"{activity.get('ticker', 'UNK')}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self._feed_cache.append(activity)
        self._save_cache()

    def get_feed(self,
                 limit: int = 50,
                 min_premium: float = 0,
                 ticker: str = None,
                 sentiment: str = None) -> List[Dict]:
        """
        Get filtered unusual activity feed.

        Args:
            limit: Max entries to return
            min_premium: Minimum premium filter
            ticker: Filter by ticker
            sentiment: Filter by sentiment (bullish/bearish)
        """
        feed = self._feed_cache.copy()

        # Apply filters
        if min_premium > 0:
            feed = [f for f in feed if f.get('premium', 0) >= min_premium]
        if ticker:
            feed = [f for f in feed if f.get('ticker', '').upper() == ticker.upper()]
        if sentiment:
            feed = [f for f in feed if f.get('sentiment', '').lower() == sentiment.lower()]

        # Sort by timestamp descending and limit
        feed.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        return feed[:limit]

    def scan_tickers(self, tickers: List[str], min_premium: float = 25000) -> List[Dict]:
        """
        Scan multiple tickers for unusual activity.

        Returns list of unusual activities found.
        """
        unusual_activities = []

        for ticker in tickers:
            try:
                if HAS_POLYGON:
                    result = get_unusual_options_sync(ticker, threshold=2.0)
                    if result and result.get('unusual_activity'):
                        for contract in result.get('unusual_contracts', [])[:5]:
                            premium = contract.get('premium', 0)
                            if premium >= min_premium:
                                activity = {
                                    'ticker': ticker,
                                    'strike': contract.get('strike'),
                                    'expiry': contract.get('expiry'),
                                    'type': contract.get('type', 'unknown'),
                                    'premium': premium,
                                    'volume': contract.get('volume', 0),
                                    'open_interest': contract.get('open_interest', 0),
                                    'vol_oi_ratio': contract.get('vol_oi_ratio', 0),
                                    'sentiment': 'bullish' if contract.get('type') == 'call' else 'bearish',
                                    'category': self._categorize_premium(premium),
                                }
                                unusual_activities.append(activity)
                                self.add_activity(activity)
            except Exception as e:
                logger.debug(f"Error scanning {ticker}: {e}")
                continue

        # Sort by premium descending
        unusual_activities.sort(key=lambda x: x.get('premium', 0), reverse=True)
        return unusual_activities

    def _categorize_premium(self, premium: float) -> str:
        """Categorize premium size."""
        if premium >= PREMIUM_THRESHOLDS['whale']:
            return 'whale'
        elif premium >= PREMIUM_THRESHOLDS['large']:
            return 'large'
        elif premium >= PREMIUM_THRESHOLDS['medium']:
            return 'medium'
        elif premium >= PREMIUM_THRESHOLDS['small']:
            return 'small'
        else:
            return 'retail'


# =============================================================================
# SMART MONEY FLOW TRACKER
# =============================================================================

class SmartMoneyTracker:
    """Track institutional / smart money options flow."""

    def __init__(self):
        self.flow_history = defaultdict(list)

    def analyze_flow(self, ticker: str) -> Dict:
        """
        Analyze options flow for smart money signals.

        Returns:
            {
                'ticker': str,
                'smart_money_score': int (0-100),
                'signals': List[Dict],
                'flow_sentiment': str,
                'institutional_ratio': float,
                'sweep_count': int,
                'block_count': int,
                'total_premium': float
            }
        """
        result = {
            'ticker': ticker.upper(),
            'smart_money_score': 50,
            'signals': [],
            'flow_sentiment': 'neutral',
            'institutional_ratio': 0.0,
            'sweep_count': 0,
            'block_count': 0,
            'total_premium': 0,
            'call_premium': 0,
            'put_premium': 0,
        }

        try:
            if not HAS_POLYGON:
                return result

            # Get options flow data
            flow_data = get_options_flow_sync(ticker)
            unusual_data = get_unusual_options_sync(ticker, volume_threshold=1.5)

            if not flow_data or flow_data.get('error'):
                return result

            # Analyze flow patterns
            total_call_vol = flow_data.get('total_call_volume', 0)
            total_put_vol = flow_data.get('total_put_volume', 0)
            pc_ratio = flow_data.get('put_call_ratio', 1.0)

            # Smart money typically trades larger sizes
            unusual_contracts = unusual_data.get('unusual_contracts', []) if unusual_data else []

            large_trades = [c for c in unusual_contracts if c.get('premium', 0) >= 100000]
            whale_trades = [c for c in unusual_contracts if c.get('premium', 0) >= 500000]

            result['block_count'] = len(large_trades)
            result['sweep_count'] = len([c for c in unusual_contracts if c.get('vol_oi_ratio', 0) > 5])

            # Calculate total premiums (handle both 'type' and 'contract_type' field names)
            call_premium = sum(c.get('premium', 0) for c in unusual_contracts if (c.get('type') or c.get('contract_type')) == 'call')
            put_premium = sum(c.get('premium', 0) for c in unusual_contracts if (c.get('type') or c.get('contract_type')) == 'put')
            result['call_premium'] = call_premium
            result['put_premium'] = put_premium
            result['total_premium'] = call_premium + put_premium

            # Institutional ratio estimate (large trades / total)
            if len(unusual_contracts) > 0:
                result['institutional_ratio'] = len(large_trades) / len(unusual_contracts)

            # Calculate smart money score
            score = 50

            # Large block trades = smart money
            score += min(20, len(large_trades) * 5)

            # Whale trades = very smart money
            score += min(20, len(whale_trades) * 10)

            # High sweep count = aggressive positioning
            score += min(10, result['sweep_count'] * 2)

            result['smart_money_score'] = min(100, max(0, score))

            # Determine flow sentiment
            if call_premium > put_premium * 2:
                result['flow_sentiment'] = 'very_bullish'
            elif call_premium > put_premium * 1.3:
                result['flow_sentiment'] = 'bullish'
            elif put_premium > call_premium * 2:
                result['flow_sentiment'] = 'very_bearish'
            elif put_premium > call_premium * 1.3:
                result['flow_sentiment'] = 'bearish'
            else:
                result['flow_sentiment'] = 'neutral'

            # Add signals
            if whale_trades:
                result['signals'].append({
                    'type': 'whale',
                    'description': f'{len(whale_trades)} whale trade(s) detected (>$500K)',
                    'sentiment': 'bullish' if call_premium > put_premium else 'bearish'
                })

            if result['sweep_count'] >= 3:
                result['signals'].append({
                    'type': 'sweep',
                    'description': f'{result["sweep_count"]} sweep orders detected',
                    'sentiment': 'aggressive'
                })

            if result['institutional_ratio'] > 0.5:
                result['signals'].append({
                    'type': 'institutional',
                    'description': f'{result["institutional_ratio"]*100:.0f}% institutional flow',
                    'sentiment': 'smart_money'
                })

            # Add notable trades for UI display (top 10 by premium)
            notable = sorted(unusual_contracts, key=lambda x: x.get('premium', 0), reverse=True)[:10]
            result['notable_trades'] = [
                {
                    'strike': t.get('strike'),
                    'type': t.get('type') or t.get('contract_type', 'unknown'),
                    'premium': t.get('premium', 0),
                    'volume': t.get('volume', 0),
                    'vol_oi_ratio': t.get('vol_oi_ratio', 0),
                    'signal': t.get('signal', ''),
                    'expiration': t.get('expiration', ''),
                }
                for t in notable
            ]

            # Calculate net flow
            result['net_flow'] = call_premium - put_premium
            result['call_flow'] = call_premium
            result['put_flow'] = put_premium

        except Exception as e:
            logger.error(f"Error analyzing smart money flow for {ticker}: {e}")

        return result


# =============================================================================
# OPTIONS SENTIMENT ANALYZER
# =============================================================================

class OptionsSentimentAnalyzer:
    """Comprehensive options sentiment analysis."""

    def __init__(self):
        self.cache = {}

    def get_sentiment_dashboard(self, ticker: str) -> Dict:
        """
        Get comprehensive sentiment dashboard for a ticker.

        Returns:
            {
                'ticker': str,
                'put_call_ratio': float,
                'put_call_trend': str,
                'iv_rank': float,
                'iv_percentile': float,
                'current_iv': float,
                'gex': float,
                'max_pain': float,
                'sentiment_score': int,
                'sentiment_label': str,
                'skew': Dict,
                'key_levels': List[float]
            }
        """
        result = {
            'ticker': ticker.upper(),
            'put_call_ratio': 1.0,
            'put_call_trend': 'stable',
            'iv_rank': 50,
            'iv_percentile': 50,
            'current_iv': 0,
            'gex': 0,
            'max_pain': 0,
            'sentiment_score': 50,
            'sentiment_label': 'Neutral',
            'skew': {'call_iv': 0, 'put_iv': 0, 'skew_ratio': 1.0},
            'key_levels': [],
        }

        try:
            # Get options chain for analysis
            if HAS_POLYGON:
                chain = get_options_chain_sync(ticker)
                flow = get_options_flow_sync(ticker)

                if chain and not chain.get('error'):
                    result.update(self._analyze_chain(chain))

                if flow and not flow.get('error'):
                    result['put_call_ratio'] = flow.get('put_call_ratio', 1.0)

                    # Determine PC ratio trend
                    if result['put_call_ratio'] < 0.7:
                        result['put_call_trend'] = 'bullish'
                    elif result['put_call_ratio'] > 1.3:
                        result['put_call_trend'] = 'bearish'
                    else:
                        result['put_call_trend'] = 'neutral'

            # Get current price for max pain
            if HAS_YFINANCE:
                try:
                    stock = yf.Ticker(ticker)
                    hist = stock.history(period='1d')
                    if len(hist) > 0:
                        current_price = hist['Close'].iloc[-1]
                        result['current_price'] = round(current_price, 2)
                except:
                    pass

            # Calculate IV Rank (simplified)
            result['iv_rank'], result['iv_percentile'] = self._calculate_iv_rank(ticker)

            # Calculate overall sentiment score
            result['sentiment_score'] = self._calculate_sentiment_score(result)
            result['sentiment_label'] = self._get_sentiment_label(result['sentiment_score'])

        except Exception as e:
            logger.error(f"Error getting sentiment dashboard for {ticker}: {e}")

        return result

    def _analyze_chain(self, chain: Dict) -> Dict:
        """Analyze options chain for GEX, max pain, skew."""
        result = {}

        calls = chain.get('calls', [])
        puts = chain.get('puts', [])

        if not calls and not puts:
            return result

        # Calculate max pain (strike with max OI)
        strike_pain = defaultdict(float)

        for call in calls:
            strike = call.get('strike', 0)
            oi = call.get('open_interest', 0)
            strike_pain[strike] += oi

        for put in puts:
            strike = put.get('strike', 0)
            oi = put.get('open_interest', 0)
            strike_pain[strike] += oi

        if strike_pain:
            max_pain_strike = max(strike_pain.keys(), key=lambda x: strike_pain[x])
            result['max_pain'] = max_pain_strike

            # Key levels (top 5 strikes by OI)
            sorted_strikes = sorted(strike_pain.keys(), key=lambda x: strike_pain[x], reverse=True)
            result['key_levels'] = sorted_strikes[:5]

        # Calculate GEX (simplified - gamma * OI * 100)
        total_gex = 0
        for call in calls:
            gamma = call.get('gamma', 0) or 0
            oi = call.get('open_interest', 0) or 0
            total_gex += gamma * oi * 100

        for put in puts:
            gamma = put.get('gamma', 0) or 0
            oi = put.get('open_interest', 0) or 0
            total_gex -= gamma * oi * 100  # Puts have negative gamma effect

        result['gex'] = round(total_gex, 2)

        # Calculate IV skew
        call_ivs = [c.get('implied_volatility', 0) for c in calls if c.get('implied_volatility')]
        put_ivs = [p.get('implied_volatility', 0) for p in puts if p.get('implied_volatility')]

        if call_ivs and put_ivs:
            avg_call_iv = sum(call_ivs) / len(call_ivs)
            avg_put_iv = sum(put_ivs) / len(put_ivs)
            result['skew'] = {
                'call_iv': round(avg_call_iv * 100, 1),
                'put_iv': round(avg_put_iv * 100, 1),
                'skew_ratio': round(avg_put_iv / avg_call_iv, 2) if avg_call_iv > 0 else 1.0
            }
            result['current_iv'] = round((avg_call_iv + avg_put_iv) / 2 * 100, 1)

        return result

    def _calculate_iv_rank(self, ticker: str) -> Tuple[float, float]:
        """Calculate IV Rank and Percentile (simplified)."""
        try:
            if not HAS_YFINANCE:
                return 50, 50

            stock = yf.Ticker(ticker)
            hist = stock.history(period='1y')

            if len(hist) < 20:
                return 50, 50

            # Use historical volatility as proxy for IV
            returns = hist['Close'].pct_change().dropna()
            current_vol = returns.tail(20).std() * (252 ** 0.5) * 100

            # Calculate rolling 20-day volatility for past year
            rolling_vol = returns.rolling(20).std() * (252 ** 0.5) * 100
            rolling_vol = rolling_vol.dropna()

            if len(rolling_vol) == 0:
                return 50, 50

            min_vol = rolling_vol.min()
            max_vol = rolling_vol.max()

            # IV Rank
            if max_vol > min_vol:
                iv_rank = ((current_vol - min_vol) / (max_vol - min_vol)) * 100
            else:
                iv_rank = 50

            # IV Percentile
            iv_percentile = (rolling_vol < current_vol).sum() / len(rolling_vol) * 100

            return round(iv_rank, 1), round(iv_percentile, 1)

        except Exception as e:
            logger.debug(f"Error calculating IV rank for {ticker}: {e}")
            return 50, 50

    def _calculate_sentiment_score(self, data: Dict) -> int:
        """Calculate overall sentiment score (0-100)."""
        score = 50

        # Put/Call ratio impact
        pc_ratio = data.get('put_call_ratio', 1.0)
        if pc_ratio < 0.5:
            score += 20
        elif pc_ratio < 0.7:
            score += 10
        elif pc_ratio > 1.5:
            score -= 20
        elif pc_ratio > 1.2:
            score -= 10

        # GEX impact (positive = bullish pressure)
        gex = data.get('gex', 0)
        if gex > 1000000:
            score += 10
        elif gex < -1000000:
            score -= 10

        # IV impact (high IV = uncertainty)
        iv_rank = data.get('iv_rank', 50)
        if iv_rank > 80:
            score -= 5  # High IV = caution
        elif iv_rank < 20:
            score += 5  # Low IV = calm

        return max(0, min(100, score))

    def _get_sentiment_label(self, score: int) -> str:
        """Convert sentiment score to label."""
        if score >= 80:
            return 'Extreme Greed'
        elif score >= 60:
            return 'Bullish'
        elif score >= 40:
            return 'Neutral'
        elif score >= 20:
            return 'Bearish'
        else:
            return 'Extreme Fear'


# =============================================================================
# OPTIONS SCREENER
# =============================================================================

class OptionsScreener:
    """Screen options across universe based on criteria."""

    def __init__(self):
        pass

    def screen(self,
               tickers: List[str],
               min_iv_rank: float = None,
               max_iv_rank: float = None,
               min_premium: float = None,
               min_volume: int = None,
               min_vol_oi_ratio: float = None,
               sentiment: str = None,
               limit: int = 50) -> List[Dict]:
        """
        Screen tickers based on options criteria.

        Args:
            tickers: List of tickers to screen
            min_iv_rank: Minimum IV Rank (0-100)
            max_iv_rank: Maximum IV Rank (0-100)
            min_premium: Minimum unusual activity premium
            min_volume: Minimum options volume
            min_vol_oi_ratio: Minimum volume/OI ratio
            sentiment: Filter by sentiment (bullish/bearish)
            limit: Max results

        Returns:
            List of matching tickers with data
        """
        results = []
        sentiment_analyzer = OptionsSentimentAnalyzer()

        for ticker in tickers:
            try:
                # Get sentiment data
                sentiment_data = sentiment_analyzer.get_sentiment_dashboard(ticker)

                # Apply filters
                if min_iv_rank and sentiment_data.get('iv_rank', 0) < min_iv_rank:
                    continue
                if max_iv_rank and sentiment_data.get('iv_rank', 100) > max_iv_rank:
                    continue

                # Get flow data for additional filters
                if HAS_POLYGON:
                    flow = get_options_flow_sync(ticker)
                    unusual = get_unusual_options_sync(ticker)

                    if min_volume and flow:
                        total_vol = flow.get('total_call_volume', 0) + flow.get('total_put_volume', 0)
                        if total_vol < min_volume:
                            continue

                    if min_vol_oi_ratio and unusual:
                        max_ratio = max([c.get('vol_oi_ratio', 0) for c in unusual.get('unusual_contracts', [])] or [0])
                        if max_ratio < min_vol_oi_ratio:
                            continue

                    if min_premium and unusual:
                        max_premium = max([c.get('premium', 0) for c in unusual.get('unusual_contracts', [])] or [0])
                        if max_premium < min_premium:
                            continue

                # Sentiment filter
                if sentiment:
                    flow_sentiment = sentiment_data.get('put_call_trend', 'neutral')
                    if sentiment == 'bullish' and flow_sentiment not in ['bullish', 'very_bullish']:
                        continue
                    if sentiment == 'bearish' and flow_sentiment not in ['bearish', 'very_bearish']:
                        continue

                # Add to results
                results.append({
                    'ticker': ticker,
                    **sentiment_data
                })

            except Exception as e:
                logger.debug(f"Error screening {ticker}: {e}")
                continue

        # Sort by sentiment score descending
        results.sort(key=lambda x: x.get('sentiment_score', 0), reverse=True)

        return results[:limit]


# =============================================================================
# HISTORICAL FLOW TRACKER
# =============================================================================

class HistoricalFlowTracker:
    """Track and analyze historical options flow."""

    def __init__(self, cache_dir: str = "/data"):
        self.cache_dir = Path(cache_dir)
        self.history_file = self.cache_dir / "options_flow_history.json"
        self._history = {}
        self._load_history()

    def _load_history(self):
        """Load historical flow data."""
        try:
            if self.history_file.exists():
                with open(self.history_file, 'r') as f:
                    self._history = json.load(f)
        except Exception as e:
            logger.error(f"Error loading flow history: {e}")
            self._history = {}

    def _save_history(self):
        """Save historical flow data."""
        try:
            self.history_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.history_file, 'w') as f:
                json.dump(self._history, f)
        except Exception as e:
            logger.error(f"Error saving flow history: {e}")

    def record_flow(self, ticker: str, flow_data: Dict) -> None:
        """Record flow data point for a ticker."""
        if ticker not in self._history:
            self._history[ticker] = []

        entry = {
            'timestamp': datetime.now().isoformat(),
            'sentiment': flow_data.get('sentiment'),
            'put_call_ratio': flow_data.get('put_call_ratio'),
            'premium': flow_data.get('total_premium', 0),
            'smart_money_score': flow_data.get('smart_money_score', 50),
        }

        self._history[ticker].append(entry)

        # Keep last 100 entries per ticker
        self._history[ticker] = self._history[ticker][-100:]
        self._save_history()

    def get_history(self, ticker: str, days: int = 30) -> List[Dict]:
        """Get historical flow data for a ticker."""
        if ticker not in self._history:
            return []

        cutoff = datetime.now() - timedelta(days=days)
        history = []

        for entry in self._history.get(ticker, []):
            try:
                entry_time = datetime.fromisoformat(entry['timestamp'])
                if entry_time >= cutoff:
                    history.append(entry)
            except:
                continue

        return history

    def get_flow_accuracy(self, ticker: str) -> Dict:
        """
        Analyze historical flow accuracy for a ticker.

        Returns:
            {
                'total_signals': int,
                'bullish_signals': int,
                'bearish_signals': int,
                'accuracy': float (if price data available),
                'avg_return_after_bullish': float,
                'avg_return_after_bearish': float
            }
        """
        history = self.get_history(ticker, days=90)

        result = {
            'total_signals': len(history),
            'bullish_signals': len([h for h in history if h.get('sentiment') in ['bullish', 'very_bullish']]),
            'bearish_signals': len([h for h in history if h.get('sentiment') in ['bearish', 'very_bearish']]),
            'accuracy': None,
            'avg_return_after_bullish': None,
            'avg_return_after_bearish': None,
        }

        # TODO: Add price comparison for accuracy calculation
        # This would require storing and comparing price data

        return result


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

# Global instances
_unusual_feed = None
_smart_money_tracker = None
_sentiment_analyzer = None
_screener = None
_history_tracker = None


def get_unusual_feed() -> UnusualActivityFeed:
    """Get or create unusual activity feed instance."""
    global _unusual_feed
    if _unusual_feed is None:
        _unusual_feed = UnusualActivityFeed()
    return _unusual_feed


def get_smart_money_tracker() -> SmartMoneyTracker:
    """Get or create smart money tracker instance."""
    global _smart_money_tracker
    if _smart_money_tracker is None:
        _smart_money_tracker = SmartMoneyTracker()
    return _smart_money_tracker


def get_sentiment_analyzer() -> OptionsSentimentAnalyzer:
    """Get or create sentiment analyzer instance."""
    global _sentiment_analyzer
    if _sentiment_analyzer is None:
        _sentiment_analyzer = OptionsSentimentAnalyzer()
    return _sentiment_analyzer


def get_screener() -> OptionsScreener:
    """Get or create options screener instance."""
    global _screener
    if _screener is None:
        _screener = OptionsScreener()
    return _screener


def get_history_tracker() -> HistoricalFlowTracker:
    """Get or create historical flow tracker instance."""
    global _history_tracker
    if _history_tracker is None:
        _history_tracker = HistoricalFlowTracker()
    return _history_tracker


# =============================================================================
# HIGH-LEVEL API FUNCTIONS
# =============================================================================

def scan_unusual_activity(tickers: List[str], min_premium: float = 50000) -> List[Dict]:
    """Scan tickers for unusual options activity."""
    feed = get_unusual_feed()
    return feed.scan_tickers(tickers, min_premium)


def get_smart_money_flow(ticker: str) -> Dict:
    """Get smart money flow analysis for a ticker."""
    tracker = get_smart_money_tracker()
    return tracker.analyze_flow(ticker)


def get_options_sentiment(ticker: str) -> Dict:
    """Get comprehensive options sentiment for a ticker."""
    analyzer = get_sentiment_analyzer()
    return analyzer.get_sentiment_dashboard(ticker)


def screen_options(tickers: List[str], **filters) -> List[Dict]:
    """Screen options based on filters."""
    screener = get_screener()
    return screener.screen(tickers, **filters)


def get_unusual_feed_data(limit: int = 50, **filters) -> List[Dict]:
    """Get unusual activity feed data."""
    feed = get_unusual_feed()
    return feed.get_feed(limit=limit, **filters)


def get_whale_trades(min_premium: float = 500000) -> List[Dict]:
    """Get whale trades (>$500K premium)."""
    feed = get_unusual_feed()
    return feed.get_feed(min_premium=min_premium, limit=20)


def get_crisis_market_sentiment() -> Dict:
    """
    Get comprehensive market options sentiment for crisis alerts.
    Returns VIX, put/call ratios, GEX, and overall market fear indicators.
    """
    result = {
        'timestamp': datetime.now().isoformat(),
        'vix': None,
        'vix_change': None,
        'spy_price': None,
        'spy_change': None,
        'qqq_price': None,
        'qqq_change': None,
        'spy_put_call_ratio': None,
        'qqq_put_call_ratio': None,
        'spy_gex': None,
        'market_fear_level': 'unknown',
        'unusual_put_activity': [],
    }

    try:
        if HAS_YFINANCE:
            import yfinance as yf

            # Get VIX
            vix = yf.Ticker("^VIX")
            vix_hist = vix.history(period="5d")
            if len(vix_hist) >= 2:
                result['vix'] = round(vix_hist['Close'].iloc[-1], 2)
                vix_prev = vix_hist['Close'].iloc[-2]
                result['vix_change'] = round(((result['vix'] / vix_prev) - 1) * 100, 2)

            # Get SPY
            spy = yf.Ticker("SPY")
            spy_hist = spy.history(period="5d")
            if len(spy_hist) >= 2:
                result['spy_price'] = round(spy_hist['Close'].iloc[-1], 2)
                spy_prev = spy_hist['Close'].iloc[-2]
                result['spy_change'] = round(((result['spy_price'] / spy_prev) - 1) * 100, 2)

            # Get QQQ
            qqq = yf.Ticker("QQQ")
            qqq_hist = qqq.history(period="5d")
            if len(qqq_hist) >= 2:
                result['qqq_price'] = round(qqq_hist['Close'].iloc[-1], 2)
                qqq_prev = qqq_hist['Close'].iloc[-2]
                result['qqq_change'] = round(((result['qqq_price'] / qqq_prev) - 1) * 100, 2)

        # Get options sentiment for SPY
        spy_sentiment = get_options_sentiment('SPY')
        if spy_sentiment:
            result['spy_put_call_ratio'] = spy_sentiment.get('put_call_ratio')
            result['spy_gex'] = spy_sentiment.get('gex', {}).get('total', 0)

        # Get options sentiment for QQQ
        qqq_sentiment = get_options_sentiment('QQQ')
        if qqq_sentiment:
            result['qqq_put_call_ratio'] = qqq_sentiment.get('put_call_ratio')

        # Determine market fear level
        vix_val = result['vix'] or 16
        if vix_val >= 30:
            result['market_fear_level'] = 'EXTREME FEAR'
        elif vix_val >= 25:
            result['market_fear_level'] = 'HIGH FEAR'
        elif vix_val >= 20:
            result['market_fear_level'] = 'ELEVATED'
        elif vix_val >= 15:
            result['market_fear_level'] = 'NORMAL'
        else:
            result['market_fear_level'] = 'COMPLACENT'

        # Get unusual put activity (potential smart money hedging)
        try:
            unusual = scan_unusual_activity(['SPY', 'QQQ', 'IWM'], min_premium=100000)
            puts_only = [u for u in unusual if u.get('type') in ['P', 'put']]
            result['unusual_put_activity'] = puts_only[:5]
        except:
            pass

    except Exception as e:
        logger.error(f"Error getting crisis market sentiment: {e}")

    return result


def get_put_protection_recommendations(crisis_severity: int = 7, portfolio_value: float = 100000) -> Dict:
    """
    AI-analyzed put protection recommendations for crisis situations.

    Args:
        crisis_severity: Crisis severity level (1-10)
        portfolio_value: Estimated portfolio value to protect

    Returns:
        Dict with put recommendations for SPY and QQQ
    """
    recommendations = {
        'timestamp': datetime.now().isoformat(),
        'crisis_severity': crisis_severity,
        'portfolio_value': portfolio_value,
        'protection_level': 'standard',
        'spy_puts': [],
        'qqq_puts': [],
        'total_cost_estimate': 0,
        'protection_coverage': '0%',
        'ai_analysis': '',
    }

    try:
        # Determine protection level based on severity
        if crisis_severity >= 9:
            recommendations['protection_level'] = 'maximum'
            otm_pct = 0.03  # 3% OTM for aggressive protection
            exp_weeks = 4   # 4 weeks out
            hedge_pct = 0.10  # Hedge 10% of portfolio
        elif crisis_severity >= 7:
            recommendations['protection_level'] = 'elevated'
            otm_pct = 0.05  # 5% OTM
            exp_weeks = 3   # 3 weeks out
            hedge_pct = 0.05  # Hedge 5% of portfolio
        else:
            recommendations['protection_level'] = 'standard'
            otm_pct = 0.07  # 7% OTM
            exp_weeks = 2   # 2 weeks out
            hedge_pct = 0.03  # Hedge 3% of portfolio

        if HAS_YFINANCE:
            import yfinance as yf
            from datetime import date

            # Calculate expiration date (next Friday after exp_weeks)
            today = date.today()
            days_until_friday = (4 - today.weekday()) % 7
            if days_until_friday == 0:
                days_until_friday = 7
            target_exp = today + timedelta(days=days_until_friday + (exp_weeks - 1) * 7)
            exp_str = target_exp.strftime('%Y-%m-%d')

            # SPY Put Recommendation
            spy = yf.Ticker("SPY")
            spy_hist = spy.history(period="1d")
            if len(spy_hist) > 0:
                spy_price = spy_hist['Close'].iloc[-1]
                spy_strike = round(spy_price * (1 - otm_pct), 0)  # Round to whole number
                # Estimate put price (simplified - ~2% of strike for 3-week ATM)
                estimated_premium = spy_strike * 0.015 * (1 + (0.1 - otm_pct) * 5)

                # Calculate contracts needed
                hedge_amount = portfolio_value * hedge_pct
                contracts = max(1, int(hedge_amount / (spy_strike * 100)))
                total_cost = contracts * estimated_premium * 100

                recommendations['spy_puts'].append({
                    'ticker': 'SPY',
                    'type': 'PUT',
                    'strike': spy_strike,
                    'expiration': exp_str,
                    'current_price': round(spy_price, 2),
                    'otm_percent': f"{otm_pct * 100:.0f}%",
                    'contracts': contracts,
                    'est_premium': round(estimated_premium, 2),
                    'est_total_cost': round(total_cost, 0),
                    'protection_value': contracts * spy_strike * 100,
                })

            # QQQ Put Recommendation
            qqq = yf.Ticker("QQQ")
            qqq_hist = qqq.history(period="1d")
            if len(qqq_hist) > 0:
                qqq_price = qqq_hist['Close'].iloc[-1]
                qqq_strike = round(qqq_price * (1 - otm_pct), 0)
                estimated_premium = qqq_strike * 0.018 * (1 + (0.1 - otm_pct) * 5)  # QQQ slightly higher IV

                contracts = max(1, int(hedge_amount / (qqq_strike * 100)))
                total_cost = contracts * estimated_premium * 100

                recommendations['qqq_puts'].append({
                    'ticker': 'QQQ',
                    'type': 'PUT',
                    'strike': qqq_strike,
                    'expiration': exp_str,
                    'current_price': round(qqq_price, 2),
                    'otm_percent': f"{otm_pct * 100:.0f}%",
                    'contracts': contracts,
                    'est_premium': round(estimated_premium, 2),
                    'est_total_cost': round(total_cost, 0),
                    'protection_value': contracts * qqq_strike * 100,
                })

            # Calculate totals
            spy_cost = sum(p['est_total_cost'] for p in recommendations['spy_puts'])
            qqq_cost = sum(p['est_total_cost'] for p in recommendations['qqq_puts'])
            recommendations['total_cost_estimate'] = spy_cost + qqq_cost

            total_protection = sum(p['protection_value'] for p in recommendations['spy_puts'] + recommendations['qqq_puts'])
            recommendations['protection_coverage'] = f"{(total_protection / portfolio_value) * 100:.0f}%"

            # Generate AI analysis summary
            recommendations['ai_analysis'] = _generate_put_analysis(
                crisis_severity,
                recommendations,
                spy_price if 'spy_price' in dir() else 0,
                qqq_price if 'qqq_price' in dir() else 0
            )

    except Exception as e:
        logger.error(f"Error generating put recommendations: {e}")
        recommendations['ai_analysis'] = f"Error generating recommendations: {str(e)}"

    return recommendations


def _generate_put_analysis(severity: int, recs: Dict, spy_price: float, qqq_price: float) -> str:
    """Generate AI analysis text for put protection."""
    protection_level = recs.get('protection_level', 'standard')
    total_cost = recs.get('total_cost_estimate', 0)
    coverage = recs.get('protection_coverage', '0%')

    spy_puts = recs.get('spy_puts', [])
    qqq_puts = recs.get('qqq_puts', [])

    analysis = []

    if severity >= 9:
        analysis.append("⚠️ CRITICAL: Maximum protection recommended due to severe crisis risk.")
    elif severity >= 7:
        analysis.append("⚠️ ELEVATED: Increased hedging recommended as crisis develops.")
    else:
        analysis.append("📊 STANDARD: Precautionary hedging suggested.")

    if spy_puts:
        p = spy_puts[0]
        analysis.append(f"\n🛡️ SPY PUT: Buy {p['contracts']}x ${p['strike']:.0f}P exp {p['expiration']}")
        analysis.append(f"   Est. cost: ${p['est_total_cost']:,.0f} | {p['otm_percent']} OTM")

    if qqq_puts:
        p = qqq_puts[0]
        analysis.append(f"\n🛡️ QQQ PUT: Buy {p['contracts']}x ${p['strike']:.0f}P exp {p['expiration']}")
        analysis.append(f"   Est. cost: ${p['est_total_cost']:,.0f} | {p['otm_percent']} OTM")

    analysis.append(f"\n💰 Total Est. Cost: ${total_cost:,.0f}")
    analysis.append(f"📈 Portfolio Coverage: {coverage}")

    if severity >= 8:
        analysis.append("\n⚡ TIMING: Execute immediately at market open")
    else:
        analysis.append("\n⏰ TIMING: Consider entering on any relief rally")

    return "\n".join(analysis)
