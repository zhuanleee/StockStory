"""
Theme Intelligence Hub
======================
Institutional-grade theme detection combining multiple signal sources.

Architecture:
- Google Trends (leading indicator, 1-3 days ahead)
- Social Sentiment (confirming indicator)
- News/SEC (lagging indicator, institutional awareness)

Theme Lifecycle:
    EMERGING -> ACCELERATING -> PEAK -> DECLINING -> DEAD

Usage:
    from src.intelligence.theme_intelligence import (
        get_theme_hub,
        ThemeLifecycle,
    )

    hub = get_theme_hub()

    # Run full analysis
    report = hub.analyze_all_themes()

    # Get breakout alerts
    alerts = hub.get_breakout_alerts()

    # Get theme boost for a ticker
    boost = hub.get_ticker_theme_boost('NVDA')
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS & DATA CLASSES
# =============================================================================

class ThemeLifecycle(Enum):
    """Theme lifecycle stages."""
    DEAD = "dead"           # No interest, search volume minimal
    EMERGING = "emerging"   # Google Trends rising, no news yet
    ACCELERATING = "accelerating"  # Trends + social confirming
    PEAK = "peak"           # News mainstream, max attention
    DECLINING = "declining" # Search volume dropping


@dataclass
class ThemeSignal:
    """Combined signal for a theme."""
    theme_id: str
    theme_name: str

    # Individual scores (0-100)
    trends_score: float = 0
    social_score: float = 0
    news_score: float = 0
    sec_score: float = 0

    # Computed metrics
    fused_score: float = 0
    velocity: float = 0  # Rate of change
    acceleration: float = 0  # Change in velocity

    # Lifecycle
    lifecycle: str = "dead"
    days_in_stage: int = 0

    # Flags
    is_breakout: bool = False
    is_accelerating: bool = False
    is_rotating_in: bool = False
    is_rotating_out: bool = False

    # Metadata
    last_updated: str = ""
    tickers: List[str] = None

    def __post_init__(self):
        if self.tickers is None:
            self.tickers = []


@dataclass
class ThemeAlert:
    """Alert for theme changes."""
    alert_type: str  # breakout, acceleration, rotation, lifecycle_change
    theme_id: str
    theme_name: str
    message: str
    severity: str  # high, medium, low
    score: float
    timestamp: str
    tickers: List[str] = None


# =============================================================================
# THEME TO TICKER MAPPING
# =============================================================================

THEME_TICKER_MAP = {
    'ai_chips': ['NVDA', 'AMD', 'AVGO', 'MRVL', 'ARM', 'INTC', 'QCOM', 'TSM'],
    'nuclear': ['SMR', 'NNE', 'CCJ', 'UEC', 'LEU', 'UUUU', 'DNN', 'NXE'],
    'ev': ['TSLA', 'RIVN', 'LCID', 'NIO', 'LI', 'XPEV', 'F', 'GM'],
    'bitcoin': ['MSTR', 'COIN', 'MARA', 'RIOT', 'CLSK', 'HUT', 'BITF'],
    'weight_loss': ['LLY', 'NVO', 'VKTX', 'AMGN', 'PFE'],
    'defense': ['LMT', 'RTX', 'NOC', 'GD', 'BA', 'HII', 'LHX'],
    'cybersecurity': ['CRWD', 'PANW', 'ZS', 'FTNT', 'S', 'OKTA', 'NET'],
    'cloud': ['AMZN', 'MSFT', 'GOOGL', 'CRM', 'NOW', 'SNOW', 'MDB'],
    'solar': ['ENPH', 'SEDG', 'FSLR', 'RUN', 'NOVA', 'ARRY'],
    'quantum': ['IONQ', 'RGTI', 'QBTS', 'IBM', 'GOOGL'],
    'space': ['RKLB', 'LUNR', 'ASTS', 'SPCE', 'RDW', 'MNTS'],
    'robotics': ['ISRG', 'ABB', 'ROK', 'EMR', 'TER', 'IRBT'],
    'biotech': ['MRNA', 'BNTX', 'REGN', 'VRTX', 'BIIB', 'GILD'],
    'fintech': ['SQ', 'PYPL', 'AFRM', 'SOFI', 'NU', 'UPST'],
    'metaverse': ['META', 'RBLX', 'U', 'SNAP', 'MTTR'],
    'infrastructure': ['CAT', 'DE', 'VMC', 'MLM', 'URI', 'PWR'],
    'china': ['BABA', 'JD', 'PDD', 'BIDU', 'NIO', 'LI'],
    'gold': ['NEM', 'GOLD', 'AEM', 'FNV', 'WPM', 'KGC'],
    'oil': ['XOM', 'CVX', 'OXY', 'COP', 'SLB', 'HAL'],
    'retail': ['AMZN', 'WMT', 'COST', 'TGT', 'HD', 'LOW'],
}

# Display names for themes
THEME_NAMES = {
    'ai_chips': 'AI Semiconductors',
    'nuclear': 'Nuclear Energy',
    'ev': 'Electric Vehicles',
    'bitcoin': 'Bitcoin/Crypto',
    'weight_loss': 'Weight Loss Drugs',
    'defense': 'Defense/Aerospace',
    'cybersecurity': 'Cybersecurity',
    'cloud': 'Cloud Computing',
    'solar': 'Solar Energy',
    'quantum': 'Quantum Computing',
    'space': 'Space Exploration',
    'robotics': 'Robotics/Automation',
    'biotech': 'Biotech/Pharma',
    'fintech': 'Fintech/Payments',
    'metaverse': 'Metaverse/VR',
    'infrastructure': 'Infrastructure',
    'china': 'China Tech',
    'gold': 'Gold/Precious Metals',
    'oil': 'Oil/Energy',
    'retail': 'Retail/Consumer',
}


# =============================================================================
# SIGNAL WEIGHTS
# =============================================================================

SIGNAL_WEIGHTS = {
    'trends': 0.40,   # Leading indicator - highest weight
    'social': 0.30,   # Confirming indicator
    'news': 0.20,     # Lagging indicator
    'sec': 0.10,      # Deal activity
}

LIFECYCLE_THRESHOLDS = {
    'emerging': {'fused': 40, 'velocity': 5},
    'accelerating': {'fused': 60, 'velocity': 15},
    'peak': {'fused': 80, 'velocity': -5},  # High score but slowing
    'declining': {'fused': 40, 'velocity': -10},
}


# =============================================================================
# PERSISTENCE
# =============================================================================

DATA_DIR = Path("data/theme_intelligence")
HISTORY_FILE = DATA_DIR / "theme_history.json"
ALERTS_FILE = DATA_DIR / "theme_alerts.json"


def ensure_data_dir():
    """Ensure data directory exists."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_theme_history() -> Dict:
    """Load theme history from disk."""
    ensure_data_dir()
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE) as f:
                return json.load(f)
        except:
            pass
    return {'themes': {}, 'last_update': None}


def save_theme_history(data: Dict):
    """Save theme history to disk."""
    ensure_data_dir()
    with open(HISTORY_FILE, 'w') as f:
        json.dump(data, f, indent=2, default=str)


def load_alerts_history() -> List[Dict]:
    """Load alerts history."""
    ensure_data_dir()
    if ALERTS_FILE.exists():
        try:
            with open(ALERTS_FILE) as f:
                return json.load(f)
        except:
            pass
    return []


def save_alert(alert: ThemeAlert):
    """Save an alert to history."""
    ensure_data_dir()
    alerts = load_alerts_history()
    alerts.append(asdict(alert))
    # Keep last 100 alerts
    alerts = alerts[-100:]
    with open(ALERTS_FILE, 'w') as f:
        json.dump(alerts, f, indent=2)


# =============================================================================
# THEME INTELLIGENCE HUB
# =============================================================================

class ThemeIntelligenceHub:
    """
    Central hub for theme intelligence.

    Combines signals from multiple sources to detect and track
    investment themes through their lifecycle.
    """

    def __init__(self):
        self.history = load_theme_history()
        self._trends_client = None
        self._social_cache = {}
        self._news_cache = {}

    def _get_trends_client(self):
        """Lazy load Google Trends client."""
        if self._trends_client is None:
            try:
                from src.data.google_trends import GoogleTrendsClient, HAS_PYTRENDS
                if HAS_PYTRENDS:
                    self._trends_client = GoogleTrendsClient()
            except ImportError:
                pass
        return self._trends_client

    def _fetch_trends_score(self, theme_id: str) -> Tuple[float, float, bool]:
        """
        Fetch Google Trends score for a theme.
        Uses aggressive caching to avoid rate limits.

        Returns: (score, trend_pct, is_breakout)
        """
        try:
            from src.data.google_trends import get_trend_score, THEME_KEYWORDS, _check_rate_limit

            keywords = THEME_KEYWORDS.get(theme_id, [])
            if not keywords:
                return 0, 0, False

            # Check rate limit before making request
            if not _check_rate_limit():
                logger.debug(f"Skipping trends for {theme_id} due to rate limit")
                # Return cached score from theme state if available
                if theme_id in self.theme_states:
                    state = self.theme_states[theme_id]
                    # Use 40% of current score as fallback (trends weight)
                    return state.current_score * 0.4, 0, False
                return 0, 0, False

            result = get_trend_score(keywords[0])

            if result is None or result.get('error'):
                # Rate limited or error - use fallback
                logger.debug(f"No trends data for {theme_id}, using fallback")
                return 0, 0, False

            return (
                result.get('score', 0),
                result.get('trend_pct', 0),
                result.get('is_breakout', False)
            )
        except Exception as e:
            logger.error(f"Trends fetch error for {theme_id}: {e}")
            return 0, 0, False

    def _fetch_social_score(self, theme_id: str) -> float:
        """
        Fetch social sentiment score for a theme.
        Uses representative tickers from the theme.
        """
        try:
            from src.scoring.story_scorer import get_social_buzz_score

            tickers = THEME_TICKER_MAP.get(theme_id, [])[:3]
            if not tickers:
                return 0

            scores = []
            for ticker in tickers:
                try:
                    result = get_social_buzz_score(ticker)
                    if result and result.get('buzz_score'):
                        scores.append(result['buzz_score'])
                except:
                    continue

            return sum(scores) / len(scores) if scores else 0

        except Exception as e:
            logger.debug(f"Social fetch error for {theme_id}: {e}")
            return 0

    def _fetch_news_score(self, theme_id: str) -> float:
        """
        Fetch news score for a theme.
        Based on news volume and sentiment for theme tickers.
        """
        try:
            from src.sentiment.deepseek_sentiment import fetch_news_free

            tickers = THEME_TICKER_MAP.get(theme_id, [])[:2]
            if not tickers:
                return 0

            total_articles = 0
            for ticker in tickers:
                try:
                    news = fetch_news_free(ticker, num_articles=10)
                    total_articles += len(news)
                except:
                    continue

            # Score based on news volume (max 100)
            return min(100, total_articles * 5)

        except Exception as e:
            logger.debug(f"News fetch error for {theme_id}: {e}")
            return 0

    def _fetch_sec_score(self, theme_id: str) -> float:
        """
        Fetch SEC activity score for a theme.
        Checks for M&A activity in theme tickers.
        """
        try:
            from src.data.sec_edgar import detect_ma_activity

            tickers = THEME_TICKER_MAP.get(theme_id, [])[:3]
            if not tickers:
                return 0

            scores = []
            for ticker in tickers:
                try:
                    result = detect_ma_activity(ticker)
                    scores.append(result.get('ma_score', 0))
                except:
                    continue

            return sum(scores) / len(scores) if scores else 0

        except Exception as e:
            logger.debug(f"SEC fetch error for {theme_id}: {e}")
            return 0

    def _calculate_fused_score(
        self,
        trends: float,
        social: float,
        news: float,
        sec: float
    ) -> float:
        """Calculate weighted fused signal score."""
        return (
            trends * SIGNAL_WEIGHTS['trends'] +
            social * SIGNAL_WEIGHTS['social'] +
            news * SIGNAL_WEIGHTS['news'] +
            sec * SIGNAL_WEIGHTS['sec']
        )

    def _determine_lifecycle(
        self,
        fused_score: float,
        velocity: float,
        prev_lifecycle: str
    ) -> str:
        """Determine theme lifecycle stage based on metrics."""

        # Dead: Very low score
        if fused_score < 20:
            return ThemeLifecycle.DEAD.value

        # Peak: High score but velocity slowing/negative
        if fused_score >= 70 and velocity < 5:
            return ThemeLifecycle.PEAK.value

        # Accelerating: High score with strong positive velocity
        if fused_score >= 50 and velocity >= 15:
            return ThemeLifecycle.ACCELERATING.value

        # Emerging: Moderate score with positive velocity
        if fused_score >= 30 and velocity >= 5:
            return ThemeLifecycle.EMERGING.value

        # Declining: Score dropping
        if velocity < -10:
            return ThemeLifecycle.DECLINING.value

        # Stay in current stage if no clear signal
        if prev_lifecycle and fused_score >= 30:
            return prev_lifecycle

        return ThemeLifecycle.DEAD.value

    def _calculate_velocity(self, theme_id: str, current_score: float) -> Tuple[float, float]:
        """
        Calculate velocity (rate of change) and acceleration.

        Returns: (velocity, acceleration)
        """
        theme_history = self.history.get('themes', {}).get(theme_id, {})
        scores = theme_history.get('score_history', [])

        if not scores:
            return 0, 0

        # Velocity: Change from last reading
        last_score = scores[-1].get('fused_score', current_score)
        velocity = current_score - last_score

        # Acceleration: Change in velocity
        if len(scores) >= 2:
            prev_velocity = scores[-1].get('fused_score', 0) - scores[-2].get('fused_score', 0)
            acceleration = velocity - prev_velocity
        else:
            acceleration = 0

        return velocity, acceleration

    def analyze_theme(self, theme_id: str, quick: bool = False) -> ThemeSignal:
        """
        Analyze a single theme.

        Args:
            theme_id: Theme identifier
            quick: If True, only fetch Google Trends (faster)
        """
        theme_name = THEME_NAMES.get(theme_id, theme_id)
        tickers = THEME_TICKER_MAP.get(theme_id, [])

        # Fetch scores
        trends_score, trend_pct, is_breakout = self._fetch_trends_score(theme_id)

        if quick:
            social_score = 0
            news_score = 0
            sec_score = 0
        else:
            social_score = self._fetch_social_score(theme_id)
            news_score = self._fetch_news_score(theme_id)
            sec_score = self._fetch_sec_score(theme_id)

        # Calculate fused score
        fused_score = self._calculate_fused_score(
            trends_score, social_score, news_score, sec_score
        )

        # Calculate velocity and acceleration
        velocity, acceleration = self._calculate_velocity(theme_id, fused_score)

        # Get previous lifecycle
        prev_data = self.history.get('themes', {}).get(theme_id, {})
        prev_lifecycle = prev_data.get('lifecycle', ThemeLifecycle.DEAD.value)
        prev_stage_start = prev_data.get('stage_start_date')

        # Determine current lifecycle
        lifecycle = self._determine_lifecycle(fused_score, velocity, prev_lifecycle)

        # Calculate days in stage
        if lifecycle != prev_lifecycle or not prev_stage_start:
            days_in_stage = 0
            stage_start = datetime.now().isoformat()
        else:
            try:
                stage_start = prev_stage_start
                start_date = datetime.fromisoformat(stage_start)
                days_in_stage = (datetime.now() - start_date).days
            except:
                days_in_stage = 0
                stage_start = datetime.now().isoformat()

        # Detect rotation
        is_rotating_in = (
            prev_lifecycle in [ThemeLifecycle.DEAD.value, ThemeLifecycle.DECLINING.value] and
            lifecycle in [ThemeLifecycle.EMERGING.value, ThemeLifecycle.ACCELERATING.value]
        )
        is_rotating_out = (
            prev_lifecycle in [ThemeLifecycle.PEAK.value, ThemeLifecycle.ACCELERATING.value] and
            lifecycle == ThemeLifecycle.DECLINING.value
        )

        signal = ThemeSignal(
            theme_id=theme_id,
            theme_name=theme_name,
            trends_score=trends_score,
            social_score=social_score,
            news_score=news_score,
            sec_score=sec_score,
            fused_score=fused_score,
            velocity=velocity,
            acceleration=acceleration,
            lifecycle=lifecycle,
            days_in_stage=days_in_stage,
            is_breakout=is_breakout,
            is_accelerating=acceleration > 5 and velocity > 10,
            is_rotating_in=is_rotating_in,
            is_rotating_out=is_rotating_out,
            last_updated=datetime.now().isoformat(),
            tickers=tickers[:8]
        )

        # Update history
        self._update_history(theme_id, signal, stage_start)

        return signal

    def _update_history(self, theme_id: str, signal: ThemeSignal, stage_start: str):
        """Update theme history with new signal."""
        if 'themes' not in self.history:
            self.history['themes'] = {}

        if theme_id not in self.history['themes']:
            self.history['themes'][theme_id] = {
                'score_history': [],
                'lifecycle_history': []
            }

        theme_data = self.history['themes'][theme_id]

        # Add to score history (keep last 30 readings)
        theme_data['score_history'].append({
            'fused_score': signal.fused_score,
            'trends_score': signal.trends_score,
            'velocity': signal.velocity,
            'timestamp': signal.last_updated
        })
        theme_data['score_history'] = theme_data['score_history'][-30:]

        # Track lifecycle changes
        if theme_data.get('lifecycle') != signal.lifecycle:
            theme_data['lifecycle_history'].append({
                'from': theme_data.get('lifecycle', 'unknown'),
                'to': signal.lifecycle,
                'timestamp': signal.last_updated
            })
            theme_data['lifecycle_history'] = theme_data['lifecycle_history'][-10:]

        # Update current state
        theme_data['lifecycle'] = signal.lifecycle
        theme_data['stage_start_date'] = stage_start
        theme_data['last_updated'] = signal.last_updated
        theme_data['fused_score'] = signal.fused_score

        self.history['last_update'] = datetime.now().isoformat()
        save_theme_history(self.history)

    def analyze_all_themes(self, quick: bool = True) -> Dict:
        """
        Analyze all tracked themes.

        Args:
            quick: If True, only use Google Trends (faster)

        Returns:
            Dict with categorized themes and alerts
        """
        import time
        from src.data.google_trends import _check_rate_limit, RATE_LIMIT_MAX_PER_HOUR

        signals = []
        themes_analyzed = 0
        max_trends_calls = min(RATE_LIMIT_MAX_PER_HOUR, 10)  # Max 10 trends calls per run

        for theme_id in THEME_TICKER_MAP.keys():
            try:
                # Check if we still have rate limit budget for Google Trends
                use_trends = _check_rate_limit() and themes_analyzed < max_trends_calls

                signal = self.analyze_theme(theme_id, quick=quick if use_trends else True)
                signals.append(signal)
                themes_analyzed += 1

                # Only delay if we made a trends call
                if use_trends:
                    time.sleep(3.5)  # Increased delay for rate limiting
            except Exception as e:
                logger.error(f"Error analyzing {theme_id}: {e}")
                continue

        # Categorize by lifecycle
        by_lifecycle = {stage.value: [] for stage in ThemeLifecycle}
        for signal in signals:
            by_lifecycle[signal.lifecycle].append(asdict(signal))

        # Generate alerts
        alerts = self._generate_alerts(signals)

        # Sort each category by fused score
        for lifecycle in by_lifecycle:
            by_lifecycle[lifecycle].sort(
                key=lambda x: x['fused_score'],
                reverse=True
            )

        return {
            'ok': True,
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_themes': len(signals),
                'emerging': len(by_lifecycle['emerging']),
                'accelerating': len(by_lifecycle['accelerating']),
                'peak': len(by_lifecycle['peak']),
                'declining': len(by_lifecycle['declining']),
                'dead': len(by_lifecycle['dead']),
            },
            'by_lifecycle': by_lifecycle,
            'alerts': [asdict(a) for a in alerts],
            'all_signals': [asdict(s) for s in signals]
        }

    def _generate_alerts(self, signals: List[ThemeSignal]) -> List[ThemeAlert]:
        """Generate alerts from signals."""
        alerts = []

        for signal in signals:
            # Breakout alert
            if signal.is_breakout:
                alert = ThemeAlert(
                    alert_type='breakout',
                    theme_id=signal.theme_id,
                    theme_name=signal.theme_name,
                    message=f"{signal.theme_name} search interest spiking! Score: {signal.fused_score:.0f}",
                    severity='high',
                    score=signal.fused_score,
                    timestamp=datetime.now().isoformat(),
                    tickers=signal.tickers[:5]
                )
                alerts.append(alert)
                save_alert(alert)

            # Acceleration alert
            elif signal.is_accelerating:
                alert = ThemeAlert(
                    alert_type='acceleration',
                    theme_id=signal.theme_id,
                    theme_name=signal.theme_name,
                    message=f"{signal.theme_name} momentum accelerating. Velocity: +{signal.velocity:.0f}",
                    severity='medium',
                    score=signal.fused_score,
                    timestamp=datetime.now().isoformat(),
                    tickers=signal.tickers[:5]
                )
                alerts.append(alert)
                save_alert(alert)

            # Rotation alerts
            if signal.is_rotating_in:
                alert = ThemeAlert(
                    alert_type='rotation_in',
                    theme_id=signal.theme_id,
                    theme_name=signal.theme_name,
                    message=f"{signal.theme_name} rotating IN - new interest emerging",
                    severity='medium',
                    score=signal.fused_score,
                    timestamp=datetime.now().isoformat(),
                    tickers=signal.tickers[:5]
                )
                alerts.append(alert)
                save_alert(alert)

            if signal.is_rotating_out:
                alert = ThemeAlert(
                    alert_type='rotation_out',
                    theme_id=signal.theme_id,
                    theme_name=signal.theme_name,
                    message=f"{signal.theme_name} rotating OUT - interest fading",
                    severity='low',
                    score=signal.fused_score,
                    timestamp=datetime.now().isoformat(),
                    tickers=signal.tickers[:5]
                )
                alerts.append(alert)
                save_alert(alert)

        return alerts

    def get_breakout_alerts(self) -> List[ThemeAlert]:
        """Get recent breakout alerts."""
        alerts = load_alerts_history()

        # Filter to last 24 hours
        cutoff = datetime.now() - timedelta(hours=24)
        recent = []

        for a in alerts:
            try:
                ts = datetime.fromisoformat(a['timestamp'])
                if ts > cutoff:
                    recent.append(ThemeAlert(**a))
            except:
                continue

        return recent

    def get_ticker_theme_boost(self, ticker: str) -> Dict:
        """
        Get theme boost for a ticker based on its theme's lifecycle.

        Returns:
            Dict with boost points and reasoning
        """
        ticker = ticker.upper()

        # Find which themes this ticker belongs to
        ticker_themes = []
        for theme_id, tickers in THEME_TICKER_MAP.items():
            if ticker in tickers:
                ticker_themes.append(theme_id)

        if not ticker_themes:
            return {
                'ticker': ticker,
                'boost': 0,
                'themes': [],
                'reason': 'Ticker not mapped to any tracked theme'
            }

        # Get theme signals
        total_boost = 0
        theme_info = []

        for theme_id in ticker_themes:
            theme_data = self.history.get('themes', {}).get(theme_id, {})
            lifecycle = theme_data.get('lifecycle', 'dead')
            score = theme_data.get('fused_score', 0)

            # Calculate boost based on lifecycle
            boost_map = {
                'emerging': 15,
                'accelerating': 25,
                'peak': 10,
                'declining': -10,
                'dead': 0
            }
            boost = boost_map.get(lifecycle, 0)

            # Adjust for score strength
            if score >= 70:
                boost = int(boost * 1.2)
            elif score < 40:
                boost = int(boost * 0.8)

            total_boost += boost
            theme_info.append({
                'theme_id': theme_id,
                'theme_name': THEME_NAMES.get(theme_id, theme_id),
                'lifecycle': lifecycle,
                'score': score,
                'boost': boost
            })

        return {
            'ticker': ticker,
            'boost': total_boost,
            'themes': theme_info,
            'reason': f"Based on {len(ticker_themes)} theme(s): {', '.join(ticker_themes)}"
        }

    def get_theme_radar_data(self) -> Dict:
        """
        Get data formatted for dashboard theme radar visualization.
        Returns all themes, using history data if available, defaults otherwise.
        """
        themes_data = self.history.get('themes', {})

        radar_data = []

        # Include ALL themes from THEME_TICKER_MAP, not just ones in history
        for theme_id in THEME_TICKER_MAP.keys():
            data = themes_data.get(theme_id, {})
            score_history = data.get('score_history', [])

            # Get trend direction from recent history
            if len(score_history) >= 2:
                trend = score_history[-1].get('fused_score', 0) - score_history[-2].get('fused_score', 0)
            else:
                trend = 0

            # Use defaults for themes not yet analyzed
            radar_data.append({
                'theme_id': theme_id,
                'theme_name': THEME_NAMES.get(theme_id, theme_id),
                'score': data.get('fused_score', 20),  # Default score
                'lifecycle': data.get('lifecycle', 'unknown'),
                'trend': trend,
                'tickers': THEME_TICKER_MAP.get(theme_id, [])[:5],
                'last_updated': data.get('last_updated', 'Not analyzed yet')
            })

        # Sort by score
        radar_data.sort(key=lambda x: x['score'], reverse=True)

        return {
            'ok': True,
            'timestamp': datetime.now().isoformat(),
            'radar': radar_data,
            'total_themes': len(radar_data),
            'analyzed_themes': len(themes_data)
        }

    def get_theme_history(self, theme_id: str) -> Dict:
        """Get historical data for a specific theme."""
        theme_data = self.history.get('themes', {}).get(theme_id, {})

        return {
            'theme_id': theme_id,
            'theme_name': THEME_NAMES.get(theme_id, theme_id),
            'current_lifecycle': theme_data.get('lifecycle', 'unknown'),
            'current_score': theme_data.get('fused_score', 0),
            'score_history': theme_data.get('score_history', []),
            'lifecycle_history': theme_data.get('lifecycle_history', []),
            'tickers': THEME_TICKER_MAP.get(theme_id, [])
        }


# =============================================================================
# SINGLETON
# =============================================================================

_hub_instance = None


def get_theme_hub() -> ThemeIntelligenceHub:
    """Get singleton theme intelligence hub."""
    global _hub_instance
    if _hub_instance is None:
        _hub_instance = ThemeIntelligenceHub()
    return _hub_instance


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def analyze_all_themes(quick: bool = True) -> Dict:
    """Analyze all themes."""
    return get_theme_hub().analyze_all_themes(quick=quick)


def get_ticker_theme_boost(ticker: str) -> Dict:
    """Get theme boost for a ticker."""
    return get_theme_hub().get_ticker_theme_boost(ticker)


def get_breakout_alerts() -> List[ThemeAlert]:
    """Get recent breakout alerts."""
    return get_theme_hub().get_breakout_alerts()


def get_theme_radar() -> Dict:
    """Get theme radar data."""
    return get_theme_hub().get_theme_radar_data()


# =============================================================================
# TELEGRAM FORMATTING
# =============================================================================

def format_theme_intelligence_message(report: Dict) -> str:
    """Format theme intelligence report for Telegram."""
    if not report.get('ok'):
        return f"Error: {report.get('error', 'Unknown error')}"

    summary = report.get('summary', {})
    by_lifecycle = report.get('by_lifecycle', {})
    alerts = report.get('alerts', [])

    msg = "🎯 *THEME INTELLIGENCE HUB*\n"
    msg += "_Multi-signal fusion analysis_\n\n"

    # Alerts first
    if alerts:
        msg += "🚨 *ALERTS:*\n"
        for a in alerts[:5]:
            emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(a['severity'], '⚪')
            msg += f"{emoji} {a['message']}\n"
        msg += "\n"

    # Accelerating themes (hottest)
    accel = by_lifecycle.get('accelerating', [])
    if accel:
        msg += "🚀 *ACCELERATING:*\n"
        for t in accel[:5]:
            msg += f"• `{t['theme_id'].upper()}` | Score: {t['fused_score']:.0f} | +{t['velocity']:.0f}%\n"
            if t['tickers']:
                msg += f"  _{', '.join(t['tickers'][:4])}_\n"
        msg += "\n"

    # Emerging themes
    emerging = by_lifecycle.get('emerging', [])
    if emerging:
        msg += "🌱 *EMERGING:*\n"
        for t in emerging[:5]:
            msg += f"• `{t['theme_id'].upper()}` | Score: {t['fused_score']:.0f}\n"
        msg += "\n"

    # Peak themes
    peak = by_lifecycle.get('peak', [])
    if peak:
        msg += "🔥 *AT PEAK:*\n"
        for t in peak[:3]:
            msg += f"• `{t['theme_id'].upper()}` | Score: {t['fused_score']:.0f} _(watch for rotation)_\n"
        msg += "\n"

    # Declining themes
    declining = by_lifecycle.get('declining', [])
    if declining:
        msg += "📉 *DECLINING:*\n"
        for t in declining[:3]:
            msg += f"• `{t['theme_id'].upper()}` | {t['velocity']:.0f}%\n"
        msg += "\n"

    # Summary
    msg += f"*📊 Summary:*\n"
    msg += f"Tracking {summary.get('total_themes', 0)} themes | "
    msg += f"🚀 {summary.get('accelerating', 0)} | 🌱 {summary.get('emerging', 0)} | "
    msg += f"🔥 {summary.get('peak', 0)} | 📉 {summary.get('declining', 0)}"

    return msg


def format_alerts_message(alerts: List) -> str:
    """Format alerts for Telegram."""
    if not alerts:
        return "No recent theme alerts (last 24h)."

    msg = "🚨 *THEME ALERTS* (24h)\n\n"

    for a in alerts[:10]:
        if isinstance(a, ThemeAlert):
            a = asdict(a)

        emoji = {
            'breakout': '💥',
            'acceleration': '🚀',
            'rotation_in': '📈',
            'rotation_out': '📉'
        }.get(a['alert_type'], '⚪')

        severity_emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(a['severity'], '⚪')

        msg += f"{emoji} *{a['theme_name']}* {severity_emoji}\n"
        msg += f"   {a['message']}\n"
        if a.get('tickers'):
            msg += f"   Tickers: {', '.join(a['tickers'][:4])}\n"
        msg += "\n"

    return msg


# =============================================================================
# DEMO
# =============================================================================

if __name__ == "__main__":
    print("Theme Intelligence Hub")
    print("=" * 50)

    hub = get_theme_hub()

    # Analyze single theme
    print("\nAnalyzing 'ai_chips' theme...")
    signal = hub.analyze_theme('ai_chips', quick=True)
    print(f"  Score: {signal.fused_score:.0f}")
    print(f"  Lifecycle: {signal.lifecycle}")
    print(f"  Velocity: {signal.velocity:.1f}")
    print(f"  Breakout: {signal.is_breakout}")

    # Get ticker boost
    print("\nGetting theme boost for NVDA...")
    boost = hub.get_ticker_theme_boost('NVDA')
    print(f"  Boost: {boost['boost']} points")
    print(f"  Reason: {boost['reason']}")
