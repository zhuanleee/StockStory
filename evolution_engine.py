#!/usr/bin/env python3
"""
Self-Evolving Intelligence System

Coordinates all learning systems to make the bot smarter every day:
- FeedbackLoopManager: Closes all feedback loops (alerts -> weights)
- ThemeEvolutionEngine: Auto-discovers emerging themes
- CorrelationLearner: Learns relationships from price movements
- AdaptiveScoringEngine: Dynamically adjusts scoring weights
- PredictiveIntelligence: Forward-looking predictions
- ValidationMonitor: Continuous accuracy monitoring
- EvolutionScheduler: Automated learning cycles
"""

import json
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict
import threading

from config import config
from utils import get_logger

logger = get_logger(__name__)

# =============================================================================
# CONSTANTS & FILE PATHS
# =============================================================================

EVOLUTION_DATA_DIR = Path('evolution_data')
LEARNING_STATE_FILE = EVOLUTION_DATA_DIR / 'learning_state.json'
JOB_STATE_FILE = EVOLUTION_DATA_DIR / 'job_state.json'
LEARNING_DATA_DIR = Path('learning_data')

# Default weights (from config)
DEFAULT_WEIGHTS = {
    'theme_heat': 0.18,
    'catalyst': 0.18,
    'news_momentum': 0.10,
    'sentiment': 0.07,
    'social_buzz': 0.12,
    'ecosystem': 0.10,
    'technical': 0.25,
}

# Minimum/maximum weight bounds for optimization
WEIGHT_BOUNDS = {
    'min': 0.05,
    'max': 0.40,
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def ensure_dirs():
    """Ensure data directories exist."""
    EVOLUTION_DATA_DIR.mkdir(exist_ok=True)
    LEARNING_DATA_DIR.mkdir(exist_ok=True)


def load_learning_state() -> Dict:
    """Load unified learning state."""
    ensure_dirs()
    if LEARNING_STATE_FILE.exists():
        try:
            with open(LEARNING_STATE_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load learning state: {e}")

    # Return default state
    return {
        'version': '1.0',
        'last_evolution': None,
        'evolution_cycle': 0,
        'adaptive_weights': {
            'current': DEFAULT_WEIGHTS.copy(),
            'by_regime': {
                'bull_trending': {},
                'bear_volatile': {},
                'range_bound': {},
            },
            'history': [],
        },
        'signal_accuracy': {
            'by_signal_type': {},
            'by_theme': {},
            'by_market_regime': {},
        },
        'discovered_themes': {
            'themes': [],
            'retired_themes': [],
        },
        'empirical_correlations': {
            'pairs': {},
            'propagation_patterns': {},
        },
        'predictions': {
            'theme_exhaustion': {},
            'optimal_windows': {},
        },
        'validation_metrics': {
            'overall_accuracy': None,
            'confidence_interval_95': None,
            'calibration_score': None,
        },
    }


def save_learning_state(state: Dict):
    """Save unified learning state."""
    ensure_dirs()
    state['last_updated'] = datetime.now().isoformat()
    with open(LEARNING_STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2, default=str)


def load_job_state() -> Dict:
    """Load job execution state."""
    ensure_dirs()
    if JOB_STATE_FILE.exists():
        try:
            with open(JOB_STATE_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load job state: {e}")
    return {'jobs': {}, 'last_run': {}}


def save_job_state(state: Dict):
    """Save job execution state."""
    ensure_dirs()
    with open(JOB_STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2, default=str)


def wilson_score_interval(wins: int, total: int, confidence: float = 0.95) -> Tuple[float, float]:
    """
    Calculate Wilson score confidence interval for win rate.
    More accurate than normal approximation for small samples.
    """
    if total == 0:
        return (0.0, 1.0)

    from scipy import stats
    z = stats.norm.ppf(1 - (1 - confidence) / 2)

    p_hat = wins / total
    denominator = 1 + z**2 / total

    center = (p_hat + z**2 / (2 * total)) / denominator
    margin = z * np.sqrt((p_hat * (1 - p_hat) + z**2 / (4 * total)) / total) / denominator

    return (max(0, center - margin), min(1, center + margin))


# =============================================================================
# FEEDBACK LOOP MANAGER
# =============================================================================

class FeedbackLoopManager:
    """
    Closes all feedback loops that collect data but don't feed it back.
    Transforms raw data into actionable weight adjustments.
    """

    def __init__(self):
        self.state = load_learning_state()
        self.alert_file = LEARNING_DATA_DIR / 'alert_accuracy.json'
        self.theme_lifecycle_file = LEARNING_DATA_DIR / 'theme_lifecycle.json'

    def close_all_loops(self) -> Dict[str, Any]:
        """Run all feedback loop closures."""
        results = {}

        results['alert_accuracy'] = self.close_alert_accuracy_loop()
        results['theme_performance'] = self.close_theme_performance_loop()
        results['source_accuracy'] = self.close_source_accuracy_loop()
        results['prediction_calibration'] = self.close_prediction_calibration_loop()

        save_learning_state(self.state)
        return results

    def close_alert_accuracy_loop(self) -> Dict:
        """
        Alert outcomes -> Signal weights

        Process:
        1. Load alert_accuracy.json
        2. Calculate win rate by signal type
        3. Adjust weights: high accuracy = higher weight
        4. Store new weights
        """
        if not self.alert_file.exists():
            return {'status': 'no_data', 'message': 'No alert accuracy data found'}

        try:
            with open(self.alert_file, 'r') as f:
                alert_data = json.load(f)
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

        accuracy_by_type = alert_data.get('accuracy_by_type', {})
        if not accuracy_by_type:
            return {'status': 'no_data', 'message': 'No signal type accuracy data'}

        # Calculate information ratio for each signal type
        signal_performance = {}
        for signal_type, metrics in accuracy_by_type.items():
            wins = metrics.get('wins', 0)
            losses = metrics.get('losses', 0)
            total = wins + losses

            if total >= 10:  # Minimum sample size
                win_rate = wins / total
                avg_gain = metrics.get('avg_gain', 0) or 0
                avg_loss = abs(metrics.get('avg_loss', 0) or 0)

                # Calculate expected value per trade
                ev = (win_rate * avg_gain) - ((1 - win_rate) * avg_loss)

                signal_performance[signal_type] = {
                    'win_rate': win_rate,
                    'total_trades': total,
                    'avg_gain': avg_gain,
                    'avg_loss': avg_loss,
                    'expected_value': ev,
                }

        # Update signal accuracy in state
        self.state['signal_accuracy']['by_signal_type'] = signal_performance

        return {
            'status': 'success',
            'signals_analyzed': len(signal_performance),
            'performance': signal_performance,
        }

    def close_theme_performance_loop(self) -> Dict:
        """
        Theme stock returns -> Theme heat weights

        Compare theme stocks vs non-theme stocks.
        Promote/demote themes based on alpha generation.
        """
        if not self.theme_lifecycle_file.exists():
            return {'status': 'no_data'}

        try:
            with open(self.theme_lifecycle_file, 'r') as f:
                lifecycle_data = json.load(f)
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

        themes = lifecycle_data.get('themes', {})
        theme_performance = {}

        for theme_id, theme_data in themes.items():
            history = theme_data.get('momentum_history', [])
            if len(history) >= 5:
                # Calculate average momentum over recent period
                recent_momentum = [h.get('momentum_score', 0) for h in history[-10:]]
                avg_momentum = np.mean(recent_momentum) if recent_momentum else 0
                trend = 'rising' if recent_momentum[-1] > recent_momentum[0] else 'fading'

                theme_performance[theme_id] = {
                    'avg_momentum': avg_momentum,
                    'trend': trend,
                    'status': theme_data.get('status', 'unknown'),
                    'days_active': theme_data.get('days_active', 0),
                }

        self.state['signal_accuracy']['by_theme'] = theme_performance

        return {
            'status': 'success',
            'themes_analyzed': len(theme_performance),
            'performance': theme_performance,
        }

    def close_source_accuracy_loop(self) -> Dict:
        """
        Source predictions -> Trust scores

        Track which data sources are most reliable.
        Update trust weights dynamically.
        """
        # Placeholder for source tracking
        return {'status': 'not_implemented'}

    def close_prediction_calibration_loop(self) -> Dict:
        """
        Prediction outcomes -> Confidence calibration

        Adjust over/under-confident predictions.
        """
        alert_data = {}
        if self.alert_file.exists():
            try:
                with open(self.alert_file, 'r') as f:
                    alert_data = json.load(f)
            except Exception:
                pass

        alerts = alert_data.get('alerts', [])

        # Bucket predictions by confidence level
        calibration_buckets = defaultdict(lambda: {'predicted': [], 'actual': []})

        for alert in alerts:
            confidence = alert.get('confidence', 50)
            outcome = alert.get('outcome')

            if outcome is not None:
                bucket = (confidence // 10) * 10  # 50-59, 60-69, etc.
                calibration_buckets[bucket]['predicted'].append(confidence / 100)
                calibration_buckets[bucket]['actual'].append(1 if outcome == 'win' else 0)

        calibration_results = {}
        for bucket, data in calibration_buckets.items():
            if len(data['actual']) >= 5:
                predicted_avg = np.mean(data['predicted'])
                actual_avg = np.mean(data['actual'])
                calibration_results[f"{bucket}-{bucket+9}%"] = {
                    'predicted_avg': round(predicted_avg * 100, 1),
                    'actual_avg': round(actual_avg * 100, 1),
                    'samples': len(data['actual']),
                    'calibration_error': abs(predicted_avg - actual_avg),
                }

        # Calculate overall calibration score (lower is better)
        if calibration_results:
            errors = [v['calibration_error'] for v in calibration_results.values()]
            calibration_score = 1 - np.mean(errors)  # Higher = better calibrated
            self.state['validation_metrics']['calibration_score'] = round(calibration_score, 3)

        return {
            'status': 'success',
            'buckets': calibration_results,
        }


# =============================================================================
# THEME EVOLUTION ENGINE
# =============================================================================

class ThemeEvolutionEngine:
    """
    Auto-discovers emerging themes instead of relying on hardcoded THEMES dict.
    Uses clustering, pattern recognition, and AI validation.
    """

    def __init__(self):
        self.state = load_learning_state()
        self.min_cluster_size = 3
        self.discovery_confidence_threshold = 0.7

    def discover_themes(self) -> List[Dict]:
        """Run all theme discovery methods."""
        discovered = []

        # Method 1: News clustering
        news_themes = self.discover_from_news_clusters([])
        discovered.extend(news_themes)

        # Method 2: Correlation clustering (from existing price data)
        corr_themes = self.discover_from_correlation_clusters()
        discovered.extend(corr_themes)

        # Deduplicate and validate
        validated = self._validate_and_merge(discovered)

        # Update state
        self.state['discovered_themes']['themes'].extend(validated)
        save_learning_state(self.state)

        return validated

    def discover_from_news_clusters(self, news_items: List[Dict]) -> List[Dict]:
        """
        Discover themes from news clustering.

        Algorithm:
        1. Collect recent news
        2. TF-IDF vectorization
        3. DBSCAN clustering
        4. Extract clusters not matching existing themes
        5. Validate with keyword analysis
        """
        if not news_items:
            # Try to load from cached news
            news_file = Path('cache/news_cache.json')
            if news_file.exists():
                try:
                    with open(news_file, 'r') as f:
                        news_items = json.load(f)
                except Exception:
                    pass

        if len(news_items) < 10:
            return []

        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.cluster import DBSCAN
        except ImportError:
            logger.warning("sklearn not available for news clustering")
            return []

        # Extract titles
        titles = [item.get('title', '') for item in news_items if item.get('title')]

        if len(titles) < 10:
            return []

        # TF-IDF vectorization
        vectorizer = TfidfVectorizer(
            max_features=500,
            stop_words='english',
            ngram_range=(1, 2),
            min_df=2,
        )

        try:
            X = vectorizer.fit_transform(titles)
        except Exception as e:
            logger.debug(f"TF-IDF failed: {e}")
            return []

        # DBSCAN clustering
        clustering = DBSCAN(eps=0.5, min_samples=self.min_cluster_size, metric='cosine').fit(X)

        # Extract clusters
        labels = clustering.labels_
        unique_labels = set(labels)
        unique_labels.discard(-1)  # Remove noise label

        discovered = []
        feature_names = vectorizer.get_feature_names_out()

        for label in unique_labels:
            cluster_indices = np.where(labels == label)[0]
            cluster_titles = [titles[i] for i in cluster_indices]

            # Get top keywords for this cluster
            cluster_vectors = X[cluster_indices].toarray()
            avg_vector = np.mean(cluster_vectors, axis=0)
            top_keyword_indices = avg_vector.argsort()[-10:][::-1]
            keywords = [feature_names[i] for i in top_keyword_indices]

            # Extract potential tickers mentioned
            tickers = self._extract_tickers_from_titles(cluster_titles)

            if len(tickers) >= self.min_cluster_size:
                theme = {
                    'id': f"discovered_news_{datetime.now().strftime('%Y%m%d')}_{label}",
                    'name': self._generate_theme_name(keywords),
                    'discovered_at': datetime.now().isoformat(),
                    'discovery_method': 'news_clustering',
                    'keywords': keywords[:5],
                    'stocks': list(tickers)[:10],
                    'confidence': min(0.9, 0.5 + len(tickers) * 0.05),
                    'lifecycle_stage': 'early',
                    'sample_headlines': cluster_titles[:3],
                }
                discovered.append(theme)

        return discovered

    def discover_from_correlation_clusters(self, price_data: Dict = None) -> List[Dict]:
        """
        Find stocks moving together without known relationships.
        """
        # Load from cluster history if available
        cluster_file = Path('cluster_history.json')
        if not cluster_file.exists():
            return []

        try:
            with open(cluster_file, 'r') as f:
                cluster_history = json.load(f)
        except Exception:
            return []

        discovered = []
        for cluster in cluster_history.get('clusters', []):
            appearances = cluster.get('appearances', 0)

            # Only consider clusters that have appeared multiple times
            if appearances >= 3:
                tickers = cluster.get('tickers', [])

                if len(tickers) >= self.min_cluster_size:
                    theme = {
                        'id': f"discovered_corr_{cluster.get('signature', 'unknown')[:20]}",
                        'name': f"Correlated Group: {', '.join(tickers[:3])}",
                        'discovered_at': cluster.get('first_seen'),
                        'discovery_method': 'correlation_clustering',
                        'keywords': [],
                        'stocks': tickers,
                        'confidence': min(0.95, 0.5 + appearances * 0.1),
                        'lifecycle_stage': 'early' if appearances < 5 else 'middle',
                        'avg_correlation': cluster.get('avg_rs', 0),
                    }
                    discovered.append(theme)

        return discovered

    def discover_from_social_patterns(self) -> List[Dict]:
        """Monitor StockTwits/Reddit for co-mentioned stock groups."""
        # Placeholder for social discovery
        return []

    def update_theme_lifecycle(self, theme_id: str, metrics: Dict) -> Dict:
        """
        Track theme lifecycle: early -> middle -> peak -> fading -> retired
        """
        themes = self.state['discovered_themes']['themes']

        for theme in themes:
            if theme['id'] == theme_id:
                # Update metrics
                momentum = metrics.get('momentum', 0)
                news_volume = metrics.get('news_volume', 0)

                current_stage = theme.get('lifecycle_stage', 'early')

                # Determine new stage based on metrics
                if momentum > 5 and current_stage == 'early':
                    theme['lifecycle_stage'] = 'middle'
                elif momentum > 10 and current_stage == 'middle':
                    theme['lifecycle_stage'] = 'peak'
                elif momentum < 0 and current_stage in ['middle', 'peak']:
                    theme['lifecycle_stage'] = 'fading'
                elif momentum < -5 and current_stage == 'fading':
                    # Move to retired
                    self.state['discovered_themes']['retired_themes'].append(theme)
                    themes.remove(theme)
                    theme['lifecycle_stage'] = 'retired'

                theme['last_updated'] = datetime.now().isoformat()
                theme['latest_metrics'] = metrics

                save_learning_state(self.state)
                return theme

        return {'error': 'Theme not found'}

    def export_to_story_scorer(self) -> List[Dict]:
        """Return discovered themes in format compatible with story_scorer."""
        return [
            t for t in self.state['discovered_themes']['themes']
            if t.get('lifecycle_stage') not in ['retired', 'fading']
            and t.get('confidence', 0) >= self.discovery_confidence_threshold
        ]

    def _extract_tickers_from_titles(self, titles: List[str]) -> set:
        """Extract potential stock tickers from news titles."""
        import re
        tickers = set()

        # Common ticker patterns
        pattern = r'\b([A-Z]{2,5})\b'

        # Words to exclude (common non-ticker words)
        exclude = {'THE', 'AND', 'FOR', 'ARE', 'BUT', 'NOT', 'YOU', 'ALL', 'CAN',
                   'HER', 'WAS', 'ONE', 'OUR', 'OUT', 'NEW', 'HAS', 'ITS', 'SAY',
                   'CEO', 'CFO', 'IPO', 'ETF', 'GDP', 'CPI', 'FDA', 'SEC', 'FED',
                   'NYSE', 'NASDAQ', 'DOW', 'USA', 'USD'}

        for title in titles:
            matches = re.findall(pattern, title)
            for match in matches:
                if match not in exclude and len(match) <= 5:
                    tickers.add(match)

        return tickers

    def _generate_theme_name(self, keywords: List[str]) -> str:
        """Generate a readable theme name from keywords."""
        if not keywords:
            return "Unknown Theme"

        # Use top 2-3 keywords
        name_parts = [kw.title() for kw in keywords[:3]]
        return ' '.join(name_parts)

    def _validate_and_merge(self, discovered: List[Dict]) -> List[Dict]:
        """Validate discovered themes and merge duplicates."""
        validated = []
        existing_ids = {t['id'] for t in self.state['discovered_themes']['themes']}

        for theme in discovered:
            # Check for duplicates
            if theme['id'] in existing_ids:
                continue

            # Check minimum confidence
            if theme.get('confidence', 0) < self.discovery_confidence_threshold:
                continue

            # Check stock count
            if len(theme.get('stocks', [])) < self.min_cluster_size:
                continue

            validated.append(theme)

        return validated


# =============================================================================
# CORRELATION LEARNER
# =============================================================================

class CorrelationLearner:
    """
    Learns relationships from actual price movements, not just manual/AI labels.
    """

    def __init__(self):
        self.state = load_learning_state()
        self.min_correlation = 0.6
        self.significance_level = 0.05

    def calculate_rolling_correlations(self, tickers: List[str], window: int = 20) -> Dict:
        """Calculate all-pairs correlation matrix."""
        import yfinance as yf

        if len(tickers) < 2:
            return {}

        # Download data
        try:
            data = yf.download(tickers, period='3mo', progress=False)
            if data.empty:
                return {}
        except Exception as e:
            logger.error(f"Failed to download data: {e}")
            return {}

        # Get close prices
        try:
            if isinstance(data.columns, pd.MultiIndex):
                closes = data['Close']
            else:
                closes = data[['Close']]
        except Exception:
            return {}

        # Calculate returns
        returns = closes.pct_change().dropna()

        if len(returns) < window:
            return {}

        # Calculate correlation matrix
        corr_matrix = returns.iloc[-window:].corr()

        # Convert to dict format
        correlations = {}
        for i, t1 in enumerate(corr_matrix.columns):
            for j, t2 in enumerate(corr_matrix.columns):
                if i < j:
                    corr = corr_matrix.loc[t1, t2]
                    if abs(corr) >= self.min_correlation:
                        key = f"{t1}_{t2}"
                        correlations[key] = {
                            'ticker1': t1,
                            'ticker2': t2,
                            'correlation': round(corr, 3),
                            'calculated_at': datetime.now().isoformat(),
                        }

        return correlations

    def detect_lead_lag_relationships(self, ticker1: str, ticker2: str, max_lag: int = 5) -> Optional[Dict]:
        """
        Cross-correlation at lags -5 to +5 days.
        Returns: {leader, follower, lag_days, confidence}
        """
        import yfinance as yf
        from scipy import stats

        try:
            data = yf.download([ticker1, ticker2], period='6mo', progress=False)
            if data.empty:
                return None
        except Exception:
            return None

        try:
            if isinstance(data.columns, pd.MultiIndex):
                returns1 = data['Close'][ticker1].pct_change().dropna()
                returns2 = data['Close'][ticker2].pct_change().dropna()
            else:
                return None
        except Exception:
            return None

        # Align indices
        common_idx = returns1.index.intersection(returns2.index)
        returns1 = returns1.loc[common_idx].values
        returns2 = returns2.loc[common_idx].values

        if len(returns1) < 30:
            return None

        # Cross-correlation at various lags
        correlations = []
        for lag in range(-max_lag, max_lag + 1):
            if lag < 0:
                r1 = returns1[:lag]
                r2 = returns2[-lag:]
            elif lag > 0:
                r1 = returns1[lag:]
                r2 = returns2[:-lag]
            else:
                r1 = returns1
                r2 = returns2

            if len(r1) >= 20:
                corr, p_value = stats.pearsonr(r1, r2)
                correlations.append((lag, corr, p_value))

        if not correlations:
            return None

        # Find optimal lag (highest absolute correlation)
        optimal = max(correlations, key=lambda x: abs(x[1]))
        optimal_lag, optimal_corr, p_value = optimal

        # Check significance
        if p_value > self.significance_level:
            return None

        # Determine leader/follower
        if optimal_lag > 0:
            leader, follower = ticker1, ticker2
        elif optimal_lag < 0:
            leader, follower = ticker2, ticker1
            optimal_lag = abs(optimal_lag)
        else:
            leader, follower = (ticker1, ticker2) if optimal_corr > 0 else (ticker2, ticker1)

        return {
            'leader': leader,
            'follower': follower,
            'lag_days': optimal_lag,
            'correlation': round(optimal_corr, 3),
            'confidence': round(1 - p_value, 3),
            'calculated_at': datetime.now().isoformat(),
        }

    def learn_wave_propagation(self, driver: str, event_type: str) -> Dict:
        """
        Learn empirical propagation patterns from historical data.
        """
        # Load ecosystem data
        try:
            from ecosystem_intelligence import get_ecosystem
            ecosystem = get_ecosystem(driver, depth=2)
        except ImportError:
            return {}

        if not ecosystem:
            return {}

        # Group by tier (direct vs indirect relationships)
        tier1 = ecosystem.get('suppliers', [])[:5]
        tier2 = [s for s in ecosystem.get('suppliers', [])[5:10]]

        propagation = {
            'driver': driver,
            'event_type': event_type,
            'tier1_avg_lag': 0.5,  # Default estimates
            'tier2_avg_lag': 2.0,
            'tier3_avg_lag': 4.5,
        }

        # Calculate actual lags for tier 1
        tier1_lags = []
        for supplier_data in tier1:
            supplier = supplier_data.get('ticker') if isinstance(supplier_data, dict) else supplier_data
            result = self.detect_lead_lag_relationships(driver, supplier)
            if result and result['leader'] == driver:
                tier1_lags.append(result['lag_days'])

        if tier1_lags:
            propagation['tier1_avg_lag'] = round(np.mean(tier1_lags), 1)
            propagation['tier1_samples'] = len(tier1_lags)

        # Store in state
        key = f"{driver}_{event_type}"
        self.state['empirical_correlations']['propagation_patterns'][key] = propagation
        save_learning_state(self.state)

        return propagation

    def detect_correlation_breakdown(self, historical_corr: float, current_corr: float,
                                     threshold: float = 0.3) -> bool:
        """
        Alert when historical correlations break.
        Often precedes big moves.
        """
        return abs(historical_corr - current_corr) >= threshold

    def update_correlations(self, tickers: List[str]) -> Dict:
        """Update all correlations for given tickers."""
        correlations = self.calculate_rolling_correlations(tickers)

        # Merge with existing
        existing = self.state['empirical_correlations']['pairs']
        for key, data in correlations.items():
            existing[key] = data

        save_learning_state(self.state)

        return {
            'updated': len(correlations),
            'total': len(existing),
        }


# =============================================================================
# ADAPTIVE SCORING ENGINE
# =============================================================================

class AdaptiveScoringEngine:
    """
    Dynamically adjusts scoring weights based on signal accuracy by market regime.
    """

    def __init__(self):
        self.state = load_learning_state()
        self.smoothing_factor = 0.7  # 70% new, 30% old

    def calculate_optimal_weights(self, regime: str = None) -> Dict[str, float]:
        """
        Calculate optimal weights using signal performance.

        Algorithm:
        1. Calculate information ratio per signal
        2. Constrained optimization (sum=1, min=0.05, max=0.40)
        3. Smooth with previous weights (avoid overfitting)
        """
        signal_accuracy = self.state['signal_accuracy']['by_signal_type']

        if not signal_accuracy:
            return DEFAULT_WEIGHTS.copy()

        # Map signal types to weight categories
        signal_to_weight = {
            'squeeze_breakout': 'technical',
            'rs_leader': 'technical',
            'theme_play': 'theme_heat',
            'earnings_catalyst': 'catalyst',
            'news_momentum': 'news_momentum',
            'social_buzz': 'social_buzz',
            'ecosystem_play': 'ecosystem',
        }

        # Calculate performance score for each weight category
        category_scores = defaultdict(list)

        for signal_type, metrics in signal_accuracy.items():
            weight_category = signal_to_weight.get(signal_type)
            if weight_category and metrics.get('expected_value') is not None:
                category_scores[weight_category].append(metrics['expected_value'])

        # Average scores per category
        category_avg = {}
        for category, scores in category_scores.items():
            category_avg[category] = np.mean(scores) if scores else 0

        if not category_avg:
            return DEFAULT_WEIGHTS.copy()

        # Normalize to get weights (ensure positive)
        min_score = min(category_avg.values())
        adjusted = {k: v - min_score + 0.1 for k, v in category_avg.items()}
        total = sum(adjusted.values())

        new_weights = {}
        for category in DEFAULT_WEIGHTS.keys():
            if category in adjusted:
                raw_weight = adjusted[category] / total
                # Apply bounds
                new_weights[category] = max(WEIGHT_BOUNDS['min'],
                                           min(WEIGHT_BOUNDS['max'], raw_weight))
            else:
                new_weights[category] = DEFAULT_WEIGHTS[category]

        # Normalize to sum to 1
        total_weight = sum(new_weights.values())
        new_weights = {k: round(v / total_weight, 3) for k, v in new_weights.items()}

        # Smooth with previous weights
        current_weights = self.state['adaptive_weights']['current']
        smoothed = {}
        for k in new_weights:
            old = current_weights.get(k, DEFAULT_WEIGHTS.get(k, 0.1))
            smoothed[k] = round(
                self.smoothing_factor * new_weights[k] +
                (1 - self.smoothing_factor) * old,
                3
            )

        # Store in state
        self.state['adaptive_weights']['current'] = smoothed

        if regime:
            self.state['adaptive_weights']['by_regime'][regime] = smoothed

        # Record history
        self.state['adaptive_weights']['history'].append({
            'date': datetime.now().isoformat(),
            'weights': smoothed,
            'regime': regime,
        })

        # Keep only last 30 entries
        self.state['adaptive_weights']['history'] = \
            self.state['adaptive_weights']['history'][-30:]

        save_learning_state(self.state)

        return smoothed

    def get_regime_weights(self, regime: str = None) -> Dict[str, float]:
        """Get weights for specific market regime."""
        if regime and regime in self.state['adaptive_weights']['by_regime']:
            regime_weights = self.state['adaptive_weights']['by_regime'][regime]
            if regime_weights:
                return regime_weights

        return self.state['adaptive_weights']['current'] or DEFAULT_WEIGHTS.copy()

    def get_weight_changes(self) -> Dict[str, float]:
        """Get changes from default weights."""
        current = self.state['adaptive_weights']['current']
        changes = {}

        for k, v in current.items():
            default = DEFAULT_WEIGHTS.get(k, 0)
            change = v - default
            if abs(change) >= 0.01:
                changes[k] = round(change * 100, 1)  # As percentage points

        return changes


# =============================================================================
# PREDICTIVE INTELLIGENCE
# =============================================================================

class PredictiveIntelligence:
    """
    Forward-looking predictions based on learned patterns.
    """

    def __init__(self):
        self.state = load_learning_state()

    def predict_theme_exhaustion(self, theme_id: str) -> Dict:
        """
        Predict when a theme might exhaust.

        Features: days active, news deceleration, valuation stretch,
                  institutional selling, momentum decay
        """
        # Find theme in state
        themes = self.state['discovered_themes']['themes']
        theme = next((t for t in themes if t['id'] == theme_id), None)

        if not theme:
            # Try to find in story_scorer THEMES
            try:
                from story_scorer import THEMES
                theme_data = THEMES.get(theme_id)
                if theme_data:
                    theme = {
                        'id': theme_id,
                        'name': theme_data.get('name'),
                        'lifecycle_stage': theme_data.get('stage', 'unknown'),
                    }
            except ImportError:
                pass

        if not theme:
            return {'error': 'Theme not found'}

        # Calculate exhaustion signals
        stage = theme.get('lifecycle_stage', 'unknown')
        days_active = theme.get('days_active', 0)

        # Simple heuristic-based prediction
        exhaustion_signals = []
        risk_score = 0

        if stage == 'late':
            exhaustion_signals.append('Late stage theme')
            risk_score += 30
        elif stage == 'peak':
            exhaustion_signals.append('At peak momentum')
            risk_score += 20

        if days_active > 90:
            exhaustion_signals.append(f'Active for {days_active} days')
            risk_score += min(30, days_active // 10)

        # Estimate peak date
        if stage in ['early', 'middle']:
            estimated_peak = datetime.now() + timedelta(days=max(30, 90 - days_active))
        elif stage == 'peak':
            estimated_peak = datetime.now() + timedelta(days=14)
        else:
            estimated_peak = datetime.now()

        prediction = {
            'theme_id': theme_id,
            'theme_name': theme.get('name'),
            'current_stage': stage,
            'predicted_peak_date': estimated_peak.strftime('%Y-%m-%d'),
            'confidence': max(0.3, 1 - risk_score / 100),
            'warning_signs': exhaustion_signals,
            'risk_score': risk_score,
        }

        # Store prediction
        self.state['predictions']['theme_exhaustion'][theme_id] = prediction
        save_learning_state(self.state)

        return prediction

    def predict_wave_timing(self, driver: str, event: str) -> Dict:
        """
        Predict when tier 2/3 stocks will move.
        Expected magnitude based on historical patterns.
        """
        patterns = self.state['empirical_correlations']['propagation_patterns']
        key = f"{driver}_{event}"

        if key not in patterns:
            # Use defaults
            pattern = {
                'tier1_avg_lag': 0.5,
                'tier2_avg_lag': 2.0,
                'tier3_avg_lag': 4.5,
            }
        else:
            pattern = patterns[key]

        now = datetime.now()

        return {
            'driver': driver,
            'event': event,
            'tier1_expected': (now + timedelta(days=pattern['tier1_avg_lag'])).strftime('%Y-%m-%d'),
            'tier2_expected': (now + timedelta(days=pattern['tier2_avg_lag'])).strftime('%Y-%m-%d'),
            'tier3_expected': (now + timedelta(days=pattern['tier3_avg_lag'])).strftime('%Y-%m-%d'),
            'confidence': pattern.get('confidence', 0.6),
        }

    def find_optimal_entry_windows(self, signal_type: str) -> Dict:
        """
        Find best time of day, day of week, conditions to avoid.
        Based on historical alert performance.
        """
        alert_file = LEARNING_DATA_DIR / 'alert_accuracy.json'

        if not alert_file.exists():
            return {'status': 'no_data'}

        try:
            with open(alert_file, 'r') as f:
                alert_data = json.load(f)
        except Exception:
            return {'status': 'error'}

        alerts = alert_data.get('alerts', [])

        # Filter by signal type
        relevant = [a for a in alerts if a.get('alert_type') == signal_type]

        if len(relevant) < 10:
            return {'status': 'insufficient_data', 'samples': len(relevant)}

        # Analyze by time of day (if available)
        # Analyze by day of week
        day_performance = defaultdict(lambda: {'wins': 0, 'losses': 0})

        for alert in relevant:
            alert_time = alert.get('timestamp')
            outcome = alert.get('outcome')

            if alert_time and outcome:
                try:
                    dt = datetime.fromisoformat(alert_time.replace('Z', '+00:00'))
                    day = dt.strftime('%A')
                    if outcome == 'win':
                        day_performance[day]['wins'] += 1
                    else:
                        day_performance[day]['losses'] += 1
                except Exception:
                    continue

        # Find best/worst days
        day_rates = {}
        for day, perf in day_performance.items():
            total = perf['wins'] + perf['losses']
            if total >= 3:
                day_rates[day] = perf['wins'] / total

        if day_rates:
            best_day = max(day_rates, key=day_rates.get)
            worst_day = min(day_rates, key=day_rates.get)
        else:
            best_day = 'Tuesday'  # Default
            worst_day = 'Monday'

        result = {
            'signal_type': signal_type,
            'best_day': best_day,
            'best_day_rate': round(day_rates.get(best_day, 0.5) * 100, 1),
            'worst_day': worst_day,
            'worst_day_rate': round(day_rates.get(worst_day, 0.5) * 100, 1),
            'samples': len(relevant),
        }

        # Store
        self.state['predictions']['optimal_windows'][signal_type] = result
        save_learning_state(self.state)

        return result


# =============================================================================
# VALIDATION MONITOR
# =============================================================================

class ValidationMonitor:
    """
    Continuous accuracy monitoring with statistical rigor.
    """

    def __init__(self):
        self.state = load_learning_state()

    def calculate_accuracy_with_ci(self, predictions: List[Dict] = None) -> Dict:
        """
        Calculate accuracy with Wilson score confidence interval.
        """
        if predictions is None:
            # Load from alert accuracy
            alert_file = LEARNING_DATA_DIR / 'alert_accuracy.json'
            if not alert_file.exists():
                return {'status': 'no_data'}

            try:
                with open(alert_file, 'r') as f:
                    alert_data = json.load(f)
                predictions = alert_data.get('alerts', [])
            except Exception:
                return {'status': 'error'}

        # Count wins/losses
        wins = sum(1 for p in predictions if p.get('outcome') == 'win')
        losses = sum(1 for p in predictions if p.get('outcome') == 'loss')
        total = wins + losses

        if total == 0:
            return {'status': 'no_outcomes'}

        accuracy = wins / total
        ci_low, ci_high = wilson_score_interval(wins, total)

        result = {
            'accuracy': round(accuracy * 100, 1),
            'confidence_interval_95': [round(ci_low * 100, 1), round(ci_high * 100, 1)],
            'wins': wins,
            'losses': losses,
            'total': total,
        }

        # Update state
        self.state['validation_metrics']['overall_accuracy'] = result['accuracy']
        self.state['validation_metrics']['confidence_interval_95'] = result['confidence_interval_95']
        save_learning_state(self.state)

        return result

    def assess_calibration(self, predictions: List[Dict] = None) -> Dict:
        """
        Bucket by confidence and compare predicted vs actual.
        Good calibration: predicted ~= actual in all buckets.
        """
        if predictions is None:
            alert_file = LEARNING_DATA_DIR / 'alert_accuracy.json'
            if not alert_file.exists():
                return {'status': 'no_data'}

            try:
                with open(alert_file, 'r') as f:
                    predictions = json.load(f).get('alerts', [])
            except Exception:
                return {'status': 'error'}

        # Bucket by confidence
        buckets = defaultdict(lambda: {'predicted': [], 'actual': []})

        for pred in predictions:
            confidence = pred.get('confidence', 50)
            outcome = pred.get('outcome')

            if outcome in ['win', 'loss']:
                bucket_key = (confidence // 10) * 10
                buckets[bucket_key]['predicted'].append(confidence / 100)
                buckets[bucket_key]['actual'].append(1 if outcome == 'win' else 0)

        calibration = {}
        total_error = 0
        total_buckets = 0

        for bucket_key in sorted(buckets.keys()):
            data = buckets[bucket_key]
            if len(data['actual']) >= 3:
                predicted_avg = np.mean(data['predicted'])
                actual_avg = np.mean(data['actual'])
                error = abs(predicted_avg - actual_avg)

                calibration[f"{bucket_key}-{bucket_key+9}%"] = {
                    'predicted': round(predicted_avg * 100, 1),
                    'actual': round(actual_avg * 100, 1),
                    'error': round(error * 100, 1),
                    'samples': len(data['actual']),
                }

                total_error += error
                total_buckets += 1

        # Overall calibration score
        if total_buckets > 0:
            avg_error = total_error / total_buckets
            calibration_score = round((1 - avg_error) * 100, 1)
        else:
            calibration_score = None

        return {
            'buckets': calibration,
            'calibration_score': calibration_score,
            'interpretation': 'Good' if calibration_score and calibration_score >= 80 else 'Needs improvement',
        }

    def detect_accuracy_degradation(self, recent_days: int = 30, baseline_days: int = 90) -> Dict:
        """
        Flag if recent accuracy < historical by significant margin.
        """
        alert_file = LEARNING_DATA_DIR / 'alert_accuracy.json'
        if not alert_file.exists():
            return {'status': 'no_data'}

        try:
            with open(alert_file, 'r') as f:
                alerts = json.load(f).get('alerts', [])
        except Exception:
            return {'status': 'error'}

        now = datetime.now()
        recent_cutoff = now - timedelta(days=recent_days)
        baseline_cutoff = now - timedelta(days=baseline_days)

        recent = []
        baseline = []

        for alert in alerts:
            timestamp = alert.get('timestamp')
            outcome = alert.get('outcome')

            if timestamp and outcome in ['win', 'loss']:
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    dt = dt.replace(tzinfo=None)

                    if dt >= recent_cutoff:
                        recent.append(1 if outcome == 'win' else 0)
                    elif dt >= baseline_cutoff:
                        baseline.append(1 if outcome == 'win' else 0)
                except Exception:
                    continue

        if len(recent) < 10 or len(baseline) < 20:
            return {'status': 'insufficient_data'}

        recent_accuracy = np.mean(recent) * 100
        baseline_accuracy = np.mean(baseline) * 100
        difference = recent_accuracy - baseline_accuracy

        degradation_detected = difference < -5  # 5% threshold

        return {
            'recent_accuracy': round(recent_accuracy, 1),
            'baseline_accuracy': round(baseline_accuracy, 1),
            'difference': round(difference, 1),
            'degradation_detected': degradation_detected,
            'recent_samples': len(recent),
            'baseline_samples': len(baseline),
        }


# =============================================================================
# EVOLUTION SCHEDULER
# =============================================================================

class EvolutionScheduler:
    """
    Automated learning cycles with cron-like scheduling.
    """

    JOBS = {
        'daily_learning': {
            'schedule': '0 6 * * *',  # 6 AM daily
            'tasks': [
                'update_alert_outcomes',
                'close_feedback_loops',
                'update_theme_lifecycles',
                'check_for_new_themes',
            ],
        },
        'weekly_optimization': {
            'schedule': '0 5 * * 0',  # Sunday 5 AM
            'tasks': [
                'recalculate_optimal_weights',
                'refresh_all_ecosystems',
                'retire_exhausted_themes',
                'full_validation_report',
            ],
        },
        'hourly_correlation': {
            'schedule': '0 * * * 1-5',  # Hourly Mon-Fri
            'market_hours_only': True,
            'tasks': [
                'update_rolling_correlations',
                'check_correlation_breakdowns',
                'update_active_waves',
            ],
        },
    }

    def __init__(self):
        self.job_state = load_job_state()
        self.state = load_learning_state()

    def run_daily_learning(self) -> Dict:
        """Run daily learning cycle."""
        results = {}

        logger.info("Starting daily learning cycle...")

        # 1. Close feedback loops
        feedback_mgr = FeedbackLoopManager()
        results['feedback_loops'] = feedback_mgr.close_all_loops()

        # 2. Update theme lifecycles
        theme_engine = ThemeEvolutionEngine()
        # This would be called with actual metrics from scan

        # 3. Check for new themes
        results['discovered_themes'] = theme_engine.discover_themes()

        # 4. Update validation metrics
        validator = ValidationMonitor()
        results['accuracy'] = validator.calculate_accuracy_with_ci()
        results['calibration'] = validator.assess_calibration()
        results['degradation_check'] = validator.detect_accuracy_degradation()

        # Record job execution
        self.job_state['last_run']['daily_learning'] = datetime.now().isoformat()
        save_job_state(self.job_state)

        # Increment cycle counter
        self.state['evolution_cycle'] = self.state.get('evolution_cycle', 0) + 1
        self.state['last_evolution'] = datetime.now().isoformat()
        save_learning_state(self.state)

        logger.info(f"Daily learning cycle #{self.state['evolution_cycle']} complete")

        return results

    def run_weekly_optimization(self) -> Dict:
        """Run weekly weight optimization."""
        results = {}

        logger.info("Starting weekly optimization...")

        # 1. Recalculate optimal weights
        scoring_engine = AdaptiveScoringEngine()
        results['new_weights'] = scoring_engine.calculate_optimal_weights()
        results['weight_changes'] = scoring_engine.get_weight_changes()

        # 2. Full validation report
        validator = ValidationMonitor()
        results['validation'] = validator.calculate_accuracy_with_ci()

        # 3. Theme cleanup
        theme_engine = ThemeEvolutionEngine()
        # Retire exhausted themes (placeholder)

        # Record execution
        self.job_state['last_run']['weekly_optimization'] = datetime.now().isoformat()
        save_job_state(self.job_state)

        logger.info("Weekly optimization complete")

        return results

    def run_correlation_update(self, tickers: List[str]) -> Dict:
        """Update correlations for given tickers."""
        learner = CorrelationLearner()
        return learner.update_correlations(tickers)

    def post_scan_learning(self, scan_results) -> Dict:
        """
        Trigger learning after a scan completes.
        Called from scanner_automation.py.
        """
        results = {}

        try:
            # Extract top tickers for correlation update
            if hasattr(scan_results, 'head'):
                top_tickers = scan_results.head(30)['ticker'].tolist()
            else:
                top_tickers = []

            # Update correlations
            if top_tickers:
                learner = CorrelationLearner()
                results['correlations'] = learner.update_correlations(top_tickers)

            # Close feedback loops
            feedback_mgr = FeedbackLoopManager()
            results['feedback'] = feedback_mgr.close_alert_accuracy_loop()

        except Exception as e:
            logger.error(f"Post-scan learning error: {e}")
            results['error'] = str(e)

        return results

    def should_run_job(self, job_name: str) -> bool:
        """Check if a job should run based on its schedule."""
        last_run = self.job_state.get('last_run', {}).get(job_name)

        if not last_run:
            return True

        try:
            last_dt = datetime.fromisoformat(last_run)

            if job_name == 'daily_learning':
                # Run if not run today
                return last_dt.date() < datetime.now().date()
            elif job_name == 'weekly_optimization':
                # Run if not run this week
                return (datetime.now() - last_dt).days >= 7
            elif job_name == 'hourly_correlation':
                # Run if not run this hour
                return (datetime.now() - last_dt).total_seconds() >= 3600

        except Exception:
            return True

        return False


# =============================================================================
# PUBLIC API FUNCTIONS
# =============================================================================

def get_current_weights() -> Dict[str, float]:
    """Get current adaptive weights for use in scoring."""
    state = load_learning_state()
    return state['adaptive_weights']['current'] or DEFAULT_WEIGHTS.copy()


def get_regime_weights(regime: str = None) -> Dict[str, float]:
    """Get weights for specific market regime."""
    engine = AdaptiveScoringEngine()
    return engine.get_regime_weights(regime)


def get_discovered_themes() -> List[Dict]:
    """Get discovered themes for story_scorer integration."""
    engine = ThemeEvolutionEngine()
    return engine.export_to_story_scorer()


def get_evolution_status() -> Dict:
    """Get current evolution system status."""
    state = load_learning_state()
    job_state = load_job_state()

    return {
        'evolution_cycle': state.get('evolution_cycle', 0),
        'last_evolution': state.get('last_evolution'),
        'validation_metrics': state.get('validation_metrics', {}),
        'weight_changes': AdaptiveScoringEngine().get_weight_changes(),
        'discovered_themes_count': len(state.get('discovered_themes', {}).get('themes', [])),
        'correlations_count': len(state.get('empirical_correlations', {}).get('pairs', {})),
        'last_jobs': job_state.get('last_run', {}),
    }


def run_evolution_cycle() -> Dict:
    """Manually trigger a full evolution cycle."""
    scheduler = EvolutionScheduler()

    results = {
        'daily': scheduler.run_daily_learning(),
    }

    # Run weekly if due
    if scheduler.should_run_job('weekly_optimization'):
        results['weekly'] = scheduler.run_weekly_optimization()

    return results


def get_learned_correlations() -> Dict:
    """Get learned correlations and lead-lag relationships."""
    state = load_learning_state()
    return state.get('empirical_correlations', {})


def get_accuracy_report() -> Dict:
    """Get comprehensive accuracy report."""
    validator = ValidationMonitor()

    return {
        'accuracy': validator.calculate_accuracy_with_ci(),
        'calibration': validator.assess_calibration(),
        'degradation': validator.detect_accuracy_degradation(),
    }


# =============================================================================
# PANDAS IMPORT (for correlation calculations)
# =============================================================================

try:
    import pandas as pd
except ImportError:
    pd = None
    logger.warning("pandas not available - some features disabled")


# =============================================================================
# CLI TESTING
# =============================================================================

if __name__ == '__main__':
    print("Evolution Engine Test")
    print("=" * 50)

    # Test loading state
    state = load_learning_state()
    print(f"Evolution Cycle: {state.get('evolution_cycle', 0)}")
    print(f"Last Evolution: {state.get('last_evolution', 'Never')}")

    # Test feedback loop manager
    print("\nTesting Feedback Loop Manager...")
    flm = FeedbackLoopManager()
    result = flm.close_alert_accuracy_loop()
    print(f"Alert accuracy loop: {result.get('status')}")

    # Test adaptive scoring
    print("\nTesting Adaptive Scoring Engine...")
    ase = AdaptiveScoringEngine()
    weights = ase.get_regime_weights()
    print(f"Current weights: {weights}")

    # Test theme discovery
    print("\nTesting Theme Evolution Engine...")
    tee = ThemeEvolutionEngine()
    themes = tee.export_to_story_scorer()
    print(f"Discovered themes: {len(themes)}")

    # Test validation
    print("\nTesting Validation Monitor...")
    vm = ValidationMonitor()
    accuracy = vm.calculate_accuracy_with_ci()
    print(f"Accuracy: {accuracy}")

    print("\n" + "=" * 50)
    print("Evolution Engine Ready!")
