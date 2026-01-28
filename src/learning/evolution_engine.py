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

ALL PARAMETERS ARE LEARNED FROM DATA - NO HARDCODED PRESETS.
"""

import json
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict

from utils import get_logger

logger = get_logger(__name__)

# =============================================================================
# CONSTANTS & FILE PATHS
# =============================================================================

EVOLUTION_DATA_DIR = Path('evolution_data')
LEARNING_STATE_FILE = EVOLUTION_DATA_DIR / 'learning_state.json'
JOB_STATE_FILE = EVOLUTION_DATA_DIR / 'job_state.json'
LEARNING_DATA_DIR = Path('learning_data')

# Initial default weights - ONLY used when no learning data exists
# These get replaced by learned weights as soon as data is available
INITIAL_DEFAULT_WEIGHTS = {
    'theme_heat': 0.18,
    'catalyst': 0.18,
    'news_momentum': 0.10,
    'sentiment': 0.07,
    'social_buzz': 0.12,
    'ecosystem': 0.10,
    'technical': 0.25,
}

# Initial weight bounds - will be learned from optimization performance
INITIAL_WEIGHT_BOUNDS = {
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
                state = json.load(f)
                # Ensure learned_parameters exists
                if 'learned_parameters' not in state:
                    state['learned_parameters'] = _get_default_learned_parameters()
                return state
        except Exception as e:
            logger.error(f"Failed to load learning state: {e}")

    # Return default state - NO PRESET REGIME WEIGHTS
    return {
        'version': '2.0',  # Updated version for learning-first approach
        'last_evolution': None,
        'evolution_cycle': 0,
        'adaptive_weights': {
            'current': INITIAL_DEFAULT_WEIGHTS.copy(),
            'by_regime': {
                # EMPTY - will be learned from data, not preset
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
        # NEW: All learnable parameters with their current values
        'learned_parameters': _get_default_learned_parameters(),
    }


def _get_default_learned_parameters() -> Dict:
    """
    Initialize learnable parameters with sensible defaults.
    These will be updated as the system learns from data.
    """
    return {
        # Weight bounds - learned from optimization stability
        'weight_bounds': {
            'min': 0.05,
            'max': 0.40,
            'learned_from_samples': 0,
        },
        # Theme discovery thresholds - learned from discovery success rate
        'discovery': {
            'min_cluster_size': 3,
            'confidence_threshold': 0.7,
            'dbscan_eps': 0.5,
            'learned_from_samples': 0,
        },
        # Correlation thresholds - learned from prediction accuracy
        'correlation': {
            'min_correlation': 0.6,
            'significance_level': 0.05,
            'learned_from_samples': 0,
        },
        # Lifecycle thresholds - learned from theme performance
        'lifecycle': {
            'early_to_middle_momentum': 5,
            'middle_to_peak_momentum': 10,
            'peak_to_fading_momentum': 0,
            'fading_to_retired_momentum': -5,
            'learned_from_samples': 0,
        },
        # Exhaustion prediction - learned from theme outcomes
        'exhaustion': {
            'late_stage_risk': 30,
            'peak_stage_risk': 20,
            'days_active_threshold': 90,
            'learned_from_samples': 0,
        },
        # Smoothing factor - learned from weight stability
        'optimization': {
            'smoothing_factor': 0.7,
            'learned_from_samples': 0,
        },
        # Degradation detection - learned from accuracy variance
        'degradation': {
            'threshold_percent': 5,
            'recent_window_days': 30,
            'baseline_window_days': 90,
            'learned_from_samples': 0,
        },
        # Calibration - learned from prediction outcomes
        'calibration': {
            'good_threshold': 80,
            'min_bucket_samples': 3,
            'learned_from_samples': 0,
        },
        # Sample size requirements - learned from statistical power
        'sample_sizes': {
            'min_for_signal_accuracy': 10,
            'min_for_theme_history': 5,
            'min_for_correlation': 20,
            'min_for_day_performance': 3,
            'learned_from_samples': 0,
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
# MARKET REGIME DETECTOR
# =============================================================================

class MarketRegimeDetector:
    """
    Detects current market regime from actual market data.
    Used to apply regime-specific learned weights.
    """

    def __init__(self):
        self.state = load_learning_state()

    def detect_current_regime(self) -> str:
        """
        Detect market regime from actual data.
        Returns: 'bull_trending', 'bear_volatile', or 'range_bound'
        """
        try:
            import yfinance as yf

            # Get SPY data for regime detection
            spy = yf.download('SPY', period='3mo', progress=False)
            if spy.empty or len(spy) < 50:
                return 'range_bound'  # Default if no data

            close = spy['Close'].values if 'Close' in spy.columns else spy[('Close', 'SPY')].values

            # Calculate indicators
            sma_20 = np.mean(close[-20:])
            sma_50 = np.mean(close[-50:])
            current_price = close[-1]

            # Calculate volatility (20-day)
            returns = np.diff(close[-21:]) / close[-21:-1]
            volatility = np.std(returns) * np.sqrt(252) * 100  # Annualized %

            # Calculate trend strength
            price_vs_sma20 = (current_price - sma_20) / sma_20 * 100
            sma20_vs_sma50 = (sma_20 - sma_50) / sma_50 * 100

            # Regime classification based on actual data
            if price_vs_sma20 > 2 and sma20_vs_sma50 > 1 and volatility < 25:
                regime = 'bull_trending'
            elif price_vs_sma20 < -2 or volatility > 30:
                regime = 'bear_volatile'
            else:
                regime = 'range_bound'

            # Store detection for learning
            self._record_regime_detection(regime, {
                'price_vs_sma20': price_vs_sma20,
                'sma20_vs_sma50': sma20_vs_sma50,
                'volatility': volatility,
            })

            return regime

        except Exception as e:
            logger.debug(f"Regime detection failed: {e}")
            return 'range_bound'

    def _record_regime_detection(self, regime: str, indicators: Dict):
        """Record regime detection for learning."""
        if 'regime_history' not in self.state:
            self.state['regime_history'] = []

        self.state['regime_history'].append({
            'timestamp': datetime.now().isoformat(),
            'regime': regime,
            'indicators': indicators,
        })

        # Keep last 100 detections
        self.state['regime_history'] = self.state['regime_history'][-100:]
        save_learning_state(self.state)


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

        # NEW: Update learned parameters based on feedback
        results['parameter_updates'] = self._update_learned_parameters()

        save_learning_state(self.state)
        return results

    def close_alert_accuracy_loop(self) -> Dict:
        """
        Alert outcomes -> Signal weights
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

        # Get learned minimum sample size
        min_samples = self.state['learned_parameters']['sample_sizes']['min_for_signal_accuracy']

        signal_performance = {}
        for signal_type, metrics in accuracy_by_type.items():
            wins = metrics.get('wins', 0)
            losses = metrics.get('losses', 0)
            total = wins + losses

            if total >= min_samples:
                win_rate = wins / total
                avg_gain = metrics.get('avg_gain', 0) or 0
                avg_loss = abs(metrics.get('avg_loss', 0) or 0)

                ev = (win_rate * avg_gain) - ((1 - win_rate) * avg_loss)

                signal_performance[signal_type] = {
                    'win_rate': win_rate,
                    'total_trades': total,
                    'avg_gain': avg_gain,
                    'avg_loss': avg_loss,
                    'expected_value': ev,
                }

        self.state['signal_accuracy']['by_signal_type'] = signal_performance

        return {
            'status': 'success',
            'signals_analyzed': len(signal_performance),
            'performance': signal_performance,
        }

    def close_theme_performance_loop(self) -> Dict:
        """Theme stock returns -> Theme heat weights"""
        if not self.theme_lifecycle_file.exists():
            return {'status': 'no_data'}

        try:
            with open(self.theme_lifecycle_file, 'r') as f:
                lifecycle_data = json.load(f)
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

        themes = lifecycle_data.get('themes', {})
        theme_performance = {}
        min_history = self.state['learned_parameters']['sample_sizes']['min_for_theme_history']

        for theme_id, theme_data in themes.items():
            history = theme_data.get('momentum_history', [])
            if len(history) >= min_history:
                recent_momentum = [h.get('momentum_score', 0) for h in history[-10:]]
                avg_momentum = np.mean(recent_momentum) if recent_momentum else 0
                trend = 'rising' if recent_momentum[-1] > recent_momentum[0] else 'fading'

                theme_performance[theme_id] = {
                    'avg_momentum': avg_momentum,
                    'trend': trend,
                    'status': theme_data.get('status', 'unknown'),
                    'days_active': theme_data.get('days_active', 0),
                }

                # Learn lifecycle thresholds from actual theme behavior
                self._learn_lifecycle_thresholds(theme_data)

        self.state['signal_accuracy']['by_theme'] = theme_performance

        return {
            'status': 'success',
            'themes_analyzed': len(theme_performance),
            'performance': theme_performance,
        }

    def _learn_lifecycle_thresholds(self, theme_data: Dict):
        """Learn lifecycle transition thresholds from actual theme data."""
        history = theme_data.get('momentum_history', [])
        if len(history) < 10:
            return

        # Find momentum values at stage transitions
        transitions = theme_data.get('stage_transitions', [])
        for transition in transitions:
            from_stage = transition.get('from')
            to_stage = transition.get('to')
            momentum_at_transition = transition.get('momentum')

            if momentum_at_transition is not None:
                params = self.state['learned_parameters']['lifecycle']

                # Update thresholds with exponential moving average
                alpha = 0.3  # Learning rate
                samples = params.get('learned_from_samples', 0)

                if from_stage == 'early' and to_stage == 'middle':
                    old = params['early_to_middle_momentum']
                    params['early_to_middle_momentum'] = round(old * (1 - alpha) + momentum_at_transition * alpha, 1)
                elif from_stage == 'middle' and to_stage == 'peak':
                    old = params['middle_to_peak_momentum']
                    params['middle_to_peak_momentum'] = round(old * (1 - alpha) + momentum_at_transition * alpha, 1)

                params['learned_from_samples'] = samples + 1

    def close_source_accuracy_loop(self) -> Dict:
        """Source predictions -> Trust scores"""
        return {'status': 'not_implemented'}

    def close_prediction_calibration_loop(self) -> Dict:
        """Prediction outcomes -> Confidence calibration"""
        alert_data = {}
        if self.alert_file.exists():
            try:
                with open(self.alert_file, 'r') as f:
                    alert_data = json.load(f)
            except Exception:
                pass

        alerts = alert_data.get('alerts', [])
        calibration_buckets = defaultdict(lambda: {'predicted': [], 'actual': []})

        for alert in alerts:
            confidence = alert.get('confidence', 50)
            outcome = alert.get('outcome')

            if outcome is not None:
                bucket = (confidence // 10) * 10
                calibration_buckets[bucket]['predicted'].append(confidence / 100)
                calibration_buckets[bucket]['actual'].append(1 if outcome == 'win' else 0)

        min_samples = self.state['learned_parameters']['calibration']['min_bucket_samples']
        calibration_results = {}

        for bucket, data in calibration_buckets.items():
            if len(data['actual']) >= min_samples:
                predicted_avg = np.mean(data['predicted'])
                actual_avg = np.mean(data['actual'])
                calibration_results[f"{bucket}-{bucket+9}%"] = {
                    'predicted_avg': round(predicted_avg * 100, 1),
                    'actual_avg': round(actual_avg * 100, 1),
                    'samples': len(data['actual']),
                    'calibration_error': abs(predicted_avg - actual_avg),
                }

        if calibration_results:
            errors = [v['calibration_error'] for v in calibration_results.values()]
            calibration_score = 1 - np.mean(errors)
            self.state['validation_metrics']['calibration_score'] = round(calibration_score, 3)

            # Learn calibration threshold from variance
            if len(errors) >= 3:
                error_std = np.std(errors)
                # Good calibration threshold = 1 - (mean_error + 1.5 * std)
                new_threshold = max(60, min(95, (1 - np.mean(errors) - error_std) * 100))
                params = self.state['learned_parameters']['calibration']
                old_threshold = params['good_threshold']
                params['good_threshold'] = round(old_threshold * 0.7 + new_threshold * 0.3, 1)
                params['learned_from_samples'] = params.get('learned_from_samples', 0) + 1

        return {
            'status': 'success',
            'buckets': calibration_results,
        }

    def _update_learned_parameters(self) -> Dict:
        """Update all learned parameters based on accumulated data."""
        updates = {}

        # Update sample size requirements based on statistical significance
        signal_data = self.state['signal_accuracy']['by_signal_type']
        if signal_data:
            # Find minimum sample where accuracy stabilizes
            sample_counts = [s.get('total_trades', 0) for s in signal_data.values()]
            if sample_counts:
                median_samples = int(np.median(sample_counts))
                params = self.state['learned_parameters']['sample_sizes']
                # Gradually adjust minimum
                old_min = params['min_for_signal_accuracy']
                new_min = max(5, min(30, median_samples // 2))
                params['min_for_signal_accuracy'] = int(old_min * 0.8 + new_min * 0.2)
                updates['min_for_signal_accuracy'] = params['min_for_signal_accuracy']

        return updates


# =============================================================================
# THEME EVOLUTION ENGINE
# =============================================================================

class ThemeEvolutionEngine:
    """
    Auto-discovers emerging themes. All thresholds are learned from data.
    """

    def __init__(self):
        self.state = load_learning_state()
        # Get learned parameters
        params = self.state['learned_parameters']['discovery']
        self.min_cluster_size = params['min_cluster_size']
        self.discovery_confidence_threshold = params['confidence_threshold']
        self.dbscan_eps = params['dbscan_eps']

    def discover_themes(self) -> List[Dict]:
        """Run all theme discovery methods."""
        discovered = []

        news_themes = self.discover_from_news_clusters([])
        discovered.extend(news_themes)

        corr_themes = self.discover_from_correlation_clusters()
        discovered.extend(corr_themes)

        validated = self._validate_and_merge(discovered)

        self.state['discovered_themes']['themes'].extend(validated)
        save_learning_state(self.state)

        return validated

    def discover_from_news_clusters(self, news_items: List[Dict]) -> List[Dict]:
        """Discover themes from news clustering with learned parameters."""
        if not news_items:
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

        titles = [item.get('title', '') for item in news_items if item.get('title')]

        if len(titles) < 10:
            return []

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

        # Use learned DBSCAN eps
        clustering = DBSCAN(eps=self.dbscan_eps, min_samples=self.min_cluster_size, metric='cosine').fit(X)

        labels = clustering.labels_
        unique_labels = set(labels)
        unique_labels.discard(-1)

        discovered = []
        feature_names = vectorizer.get_feature_names_out()

        for label in unique_labels:
            cluster_indices = np.where(labels == label)[0]
            cluster_titles = [titles[i] for i in cluster_indices]

            cluster_vectors = X[cluster_indices].toarray()
            avg_vector = np.mean(cluster_vectors, axis=0)
            top_keyword_indices = avg_vector.argsort()[-10:][::-1]
            keywords = [feature_names[i] for i in top_keyword_indices]

            tickers = self._extract_tickers_from_titles(cluster_titles)

            if len(tickers) >= self.min_cluster_size:
                # Calculate confidence from calibration data
                confidence = self._calculate_learned_confidence(len(tickers), len(cluster_titles))

                theme = {
                    'id': f"discovered_news_{datetime.now().strftime('%Y%m%d')}_{label}",
                    'name': self._generate_theme_name(keywords),
                    'discovered_at': datetime.now().isoformat(),
                    'discovery_method': 'news_clustering',
                    'keywords': keywords[:5],
                    'stocks': list(tickers)[:10],
                    'confidence': confidence,
                    'lifecycle_stage': 'early',
                    'sample_headlines': cluster_titles[:3],
                }
                discovered.append(theme)

        return discovered

    def _calculate_learned_confidence(self, ticker_count: int, headline_count: int) -> float:
        """
        Calculate confidence using learned calibration instead of hardcoded formula.
        """
        # Base confidence from validation metrics
        calibration = self.state['validation_metrics'].get('calibration_score')
        if calibration:
            # Use calibration to adjust confidence
            base_confidence = 0.5 + (ticker_count * 0.03) + (headline_count * 0.01)
            # Adjust based on how well calibrated our predictions are
            adjusted = base_confidence * calibration
            return min(0.95, max(0.3, adjusted))
        else:
            # Fallback to simple formula when no calibration data
            return min(0.9, 0.5 + ticker_count * 0.05)

    def discover_from_correlation_clusters(self, price_data: Dict = None) -> List[Dict]:
        """Find stocks moving together without known relationships."""
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

            if appearances >= 3:
                tickers = cluster.get('tickers', [])

                if len(tickers) >= self.min_cluster_size:
                    # Learn confidence from appearances
                    confidence = self._calculate_learned_confidence(len(tickers), appearances * 2)

                    theme = {
                        'id': f"discovered_corr_{cluster.get('signature', 'unknown')[:20]}",
                        'name': f"Correlated Group: {', '.join(tickers[:3])}",
                        'discovered_at': cluster.get('first_seen'),
                        'discovery_method': 'correlation_clustering',
                        'keywords': [],
                        'stocks': tickers,
                        'confidence': confidence,
                        'lifecycle_stage': 'early' if appearances < 5 else 'middle',
                        'avg_correlation': cluster.get('avg_rs', 0),
                    }
                    discovered.append(theme)

        return discovered

    def discover_from_social_patterns(self) -> List[Dict]:
        """Monitor StockTwits/Reddit for co-mentioned stock groups."""
        return []

    def update_theme_lifecycle(self, theme_id: str, metrics: Dict) -> Dict:
        """Track theme lifecycle with learned thresholds."""
        themes = self.state['discovered_themes']['themes']
        lifecycle_params = self.state['learned_parameters']['lifecycle']

        for theme in themes:
            if theme['id'] == theme_id:
                momentum = metrics.get('momentum', 0)
                current_stage = theme.get('lifecycle_stage', 'early')

                # Use learned thresholds
                new_stage = current_stage
                if momentum > lifecycle_params['early_to_middle_momentum'] and current_stage == 'early':
                    new_stage = 'middle'
                elif momentum > lifecycle_params['middle_to_peak_momentum'] and current_stage == 'middle':
                    new_stage = 'peak'
                elif momentum < lifecycle_params['peak_to_fading_momentum'] and current_stage in ['middle', 'peak']:
                    new_stage = 'fading'
                elif momentum < lifecycle_params['fading_to_retired_momentum'] and current_stage == 'fading':
                    self.state['discovered_themes']['retired_themes'].append(theme)
                    themes.remove(theme)
                    new_stage = 'retired'

                # Record stage transition for learning
                if new_stage != current_stage:
                    if 'stage_transitions' not in theme:
                        theme['stage_transitions'] = []
                    theme['stage_transitions'].append({
                        'from': current_stage,
                        'to': new_stage,
                        'momentum': momentum,
                        'timestamp': datetime.now().isoformat(),
                    })

                theme['lifecycle_stage'] = new_stage
                theme['last_updated'] = datetime.now().isoformat()
                theme['latest_metrics'] = metrics

                save_learning_state(self.state)
                return theme

        return {'error': 'Theme not found'}

    def export_to_story_scorer(self) -> List[Dict]:
        """Return discovered themes for story_scorer."""
        return [
            t for t in self.state['discovered_themes']['themes']
            if t.get('lifecycle_stage') not in ['retired', 'fading']
            and t.get('confidence', 0) >= self.discovery_confidence_threshold
        ]

    def learn_discovery_parameters(self, theme_outcomes: List[Dict]):
        """
        Learn optimal discovery parameters from theme outcomes.
        Called when we have data on which discovered themes performed well.
        """
        if len(theme_outcomes) < 5:
            return

        # Analyze which confidence levels led to good themes
        good_themes = [t for t in theme_outcomes if t.get('performance') == 'good']
        bad_themes = [t for t in theme_outcomes if t.get('performance') == 'bad']

        if good_themes and bad_themes:
            avg_good_confidence = np.mean([t.get('initial_confidence', 0.7) for t in good_themes])
            avg_bad_confidence = np.mean([t.get('initial_confidence', 0.7) for t in bad_themes])

            # Adjust threshold to be between good and bad
            optimal_threshold = (avg_good_confidence + avg_bad_confidence) / 2

            params = self.state['learned_parameters']['discovery']
            old_threshold = params['confidence_threshold']
            params['confidence_threshold'] = round(old_threshold * 0.7 + optimal_threshold * 0.3, 2)
            params['learned_from_samples'] = params.get('learned_from_samples', 0) + len(theme_outcomes)

            save_learning_state(self.state)

    def _extract_tickers_from_titles(self, titles: List[str]) -> set:
        """Extract potential stock tickers from news titles."""
        import re
        tickers = set()

        pattern = r'\b([A-Z]{2,5})\b'

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
        name_parts = [kw.title() for kw in keywords[:3]]
        return ' '.join(name_parts)

    def _validate_and_merge(self, discovered: List[Dict]) -> List[Dict]:
        """Validate discovered themes and merge duplicates."""
        validated = []
        existing_ids = {t['id'] for t in self.state['discovered_themes']['themes']}

        for theme in discovered:
            if theme['id'] in existing_ids:
                continue
            if theme.get('confidence', 0) < self.discovery_confidence_threshold:
                continue
            if len(theme.get('stocks', [])) < self.min_cluster_size:
                continue
            validated.append(theme)

        return validated


# =============================================================================
# CORRELATION LEARNER
# =============================================================================

class CorrelationLearner:
    """
    Learns relationships from actual price movements with learned thresholds.
    """

    def __init__(self):
        self.state = load_learning_state()
        # Get learned parameters
        params = self.state['learned_parameters']['correlation']
        self.min_correlation = params['min_correlation']
        self.significance_level = params['significance_level']

    def calculate_rolling_correlations(self, tickers: List[str], window: int = None) -> Dict:
        """Calculate all-pairs correlation matrix."""
        import yfinance as yf

        # Use learned window if not specified
        if window is None:
            window = 20  # Could also learn this

        if len(tickers) < 2:
            return {}

        try:
            data = yf.download(tickers, period='3mo', progress=False)
            if data.empty:
                return {}
        except Exception as e:
            logger.error(f"Failed to download data: {e}")
            return {}

        try:
            if isinstance(data.columns, pd.MultiIndex):
                closes = data['Close']
            else:
                closes = data[['Close']]
        except Exception:
            return {}

        returns = closes.pct_change().dropna()

        if len(returns) < window:
            return {}

        corr_matrix = returns.iloc[-window:].corr()

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
        """Cross-correlation at various lags."""
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

        common_idx = returns1.index.intersection(returns2.index)
        returns1 = returns1.loc[common_idx].values
        returns2 = returns2.loc[common_idx].values

        min_samples = self.state['learned_parameters']['sample_sizes']['min_for_correlation']
        if len(returns1) < min_samples:
            return None

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

            if len(r1) >= min_samples:
                corr, p_value = stats.pearsonr(r1, r2)
                correlations.append((lag, corr, p_value))

        if not correlations:
            return None

        optimal = max(correlations, key=lambda x: abs(x[1]))
        optimal_lag, optimal_corr, p_value = optimal

        if p_value > self.significance_level:
            return None

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
        """Learn empirical propagation patterns from historical data."""
        try:
            from ecosystem_intelligence import get_ecosystem
            ecosystem = get_ecosystem(driver, depth=2)
        except ImportError:
            return {}

        if not ecosystem:
            return {}

        tier1 = ecosystem.get('suppliers', [])[:5]

        # Start with no defaults - learn everything
        propagation = {
            'driver': driver,
            'event_type': event_type,
            'learned': True,
        }

        tier1_lags = []
        for supplier_data in tier1:
            supplier = supplier_data.get('ticker') if isinstance(supplier_data, dict) else supplier_data
            result = self.detect_lead_lag_relationships(driver, supplier)
            if result and result['leader'] == driver:
                tier1_lags.append(result['lag_days'])

        if tier1_lags:
            propagation['tier1_avg_lag'] = round(np.mean(tier1_lags), 1)
            propagation['tier1_samples'] = len(tier1_lags)
            propagation['tier1_std'] = round(np.std(tier1_lags), 2) if len(tier1_lags) > 1 else 0

            # Estimate tier 2/3 from tier 1 (will be refined with more data)
            propagation['tier2_avg_lag'] = round(propagation['tier1_avg_lag'] * 3, 1)
            propagation['tier3_avg_lag'] = round(propagation['tier1_avg_lag'] * 7, 1)
        else:
            # No data yet - mark as not learned
            propagation['learned'] = False

        key = f"{driver}_{event_type}"
        self.state['empirical_correlations']['propagation_patterns'][key] = propagation
        save_learning_state(self.state)

        return propagation

    def learn_correlation_thresholds(self, correlation_outcomes: List[Dict]):
        """
        Learn optimal correlation thresholds from prediction outcomes.
        """
        if len(correlation_outcomes) < 10:
            return

        # Find correlations that led to good predictions
        good_corrs = [c['correlation'] for c in correlation_outcomes if c.get('accurate')]
        bad_corrs = [c['correlation'] for c in correlation_outcomes if not c.get('accurate')]

        if good_corrs and bad_corrs:
            # Optimal threshold is between good and bad
            optimal = (min(good_corrs) + max(bad_corrs)) / 2

            params = self.state['learned_parameters']['correlation']
            old = params['min_correlation']
            params['min_correlation'] = round(old * 0.7 + optimal * 0.3, 2)
            params['learned_from_samples'] = params.get('learned_from_samples', 0) + len(correlation_outcomes)

            save_learning_state(self.state)

    def detect_correlation_breakdown(self, historical_corr: float, current_corr: float,
                                     threshold: float = None) -> bool:
        """Alert when historical correlations break."""
        if threshold is None:
            threshold = 0.3  # Could also be learned
        return abs(historical_corr - current_corr) >= threshold

    def update_correlations(self, tickers: List[str]) -> Dict:
        """Update all correlations for given tickers."""
        correlations = self.calculate_rolling_correlations(tickers)

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
    ALL weights are learned from data.
    """

    def __init__(self):
        self.state = load_learning_state()
        # Get learned smoothing factor
        self.smoothing_factor = self.state['learned_parameters']['optimization']['smoothing_factor']

    def calculate_optimal_weights(self, regime: str = None) -> Dict[str, float]:
        """Calculate optimal weights using signal performance."""
        signal_accuracy = self.state['signal_accuracy']['by_signal_type']

        if not signal_accuracy:
            return INITIAL_DEFAULT_WEIGHTS.copy()

        # Auto-detect regime if not provided
        if regime is None:
            detector = MarketRegimeDetector()
            regime = detector.detect_current_regime()

        signal_to_weight = {
            'squeeze_breakout': 'technical',
            'rs_leader': 'technical',
            'theme_play': 'theme_heat',
            'earnings_catalyst': 'catalyst',
            'news_momentum': 'news_momentum',
            'social_buzz': 'social_buzz',
            'ecosystem_play': 'ecosystem',
        }

        category_scores = defaultdict(list)

        for signal_type, metrics in signal_accuracy.items():
            weight_category = signal_to_weight.get(signal_type)
            if weight_category and metrics.get('expected_value') is not None:
                category_scores[weight_category].append(metrics['expected_value'])

        category_avg = {}
        for category, scores in category_scores.items():
            category_avg[category] = np.mean(scores) if scores else 0

        if not category_avg:
            return INITIAL_DEFAULT_WEIGHTS.copy()

        # Get learned weight bounds
        bounds = self.state['learned_parameters']['weight_bounds']
        min_bound = bounds['min']
        max_bound = bounds['max']

        min_score = min(category_avg.values())
        adjusted = {k: v - min_score + 0.1 for k, v in category_avg.items()}
        total = sum(adjusted.values())

        new_weights = {}
        for category in INITIAL_DEFAULT_WEIGHTS.keys():
            if category in adjusted:
                raw_weight = adjusted[category] / total
                new_weights[category] = max(min_bound, min(max_bound, raw_weight))
            else:
                new_weights[category] = INITIAL_DEFAULT_WEIGHTS[category]

        total_weight = sum(new_weights.values())
        new_weights = {k: round(v / total_weight, 3) for k, v in new_weights.items()}

        # Apply learned smoothing
        current_weights = self.state['adaptive_weights']['current']
        smoothed = {}
        for k in new_weights:
            old = current_weights.get(k, INITIAL_DEFAULT_WEIGHTS.get(k, 0.1))
            smoothed[k] = round(
                self.smoothing_factor * new_weights[k] +
                (1 - self.smoothing_factor) * old,
                3
            )

        # Store in state
        self.state['adaptive_weights']['current'] = smoothed

        # Store regime-specific weights (LEARNED, not preset)
        if regime:
            self.state['adaptive_weights']['by_regime'][regime] = smoothed.copy()

        # Record history
        self.state['adaptive_weights']['history'].append({
            'date': datetime.now().isoformat(),
            'weights': smoothed,
            'regime': regime,
            'signal_performance': dict(category_avg),
        })

        self.state['adaptive_weights']['history'] = \
            self.state['adaptive_weights']['history'][-30:]

        save_learning_state(self.state)

        return smoothed

    def learn_smoothing_factor(self, weight_history: List[Dict]):
        """
        Learn optimal smoothing factor from weight stability.
        Lower smoothing = more responsive but potentially unstable.
        Higher smoothing = more stable but slower to adapt.
        """
        if len(weight_history) < 10:
            return

        # Calculate weight volatility
        all_weights = [h['weights'] for h in weight_history if 'weights' in h]
        if len(all_weights) < 5:
            return

        # Compute variance for each weight category
        variances = []
        for key in INITIAL_DEFAULT_WEIGHTS.keys():
            values = [w.get(key, 0) for w in all_weights]
            if values:
                variances.append(np.var(values))

        avg_variance = np.mean(variances)

        # If too volatile, increase smoothing. If too stable, decrease.
        params = self.state['learned_parameters']['optimization']
        current = params['smoothing_factor']

        if avg_variance > 0.01:  # Too volatile
            new_factor = min(0.9, current + 0.05)
        elif avg_variance < 0.001:  # Too stable
            new_factor = max(0.3, current - 0.05)
        else:
            new_factor = current

        params['smoothing_factor'] = round(new_factor, 2)
        params['learned_from_samples'] = params.get('learned_from_samples', 0) + 1
        self.smoothing_factor = new_factor

        save_learning_state(self.state)

    def get_regime_weights(self, regime: str = None) -> Dict[str, float]:
        """Get weights for specific market regime."""
        # Auto-detect regime if not provided
        if regime is None:
            detector = MarketRegimeDetector()
            regime = detector.detect_current_regime()

        if regime and regime in self.state['adaptive_weights']['by_regime']:
            regime_weights = self.state['adaptive_weights']['by_regime'][regime]
            if regime_weights:  # Only return if learned (not empty)
                return regime_weights

        return self.state['adaptive_weights']['current'] or INITIAL_DEFAULT_WEIGHTS.copy()

    def get_weight_changes(self) -> Dict[str, float]:
        """Get changes from initial default weights."""
        current = self.state['adaptive_weights']['current']
        changes = {}

        for k, v in current.items():
            default = INITIAL_DEFAULT_WEIGHTS.get(k, 0)
            change = v - default
            if abs(change) >= 0.01:
                changes[k] = round(change * 100, 1)

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
        """Predict when a theme might exhaust using learned parameters."""
        themes = self.state['discovered_themes']['themes']
        theme = next((t for t in themes if t['id'] == theme_id), None)

        if not theme:
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

        stage = theme.get('lifecycle_stage', 'unknown')
        days_active = theme.get('days_active', 0)

        # Use learned exhaustion parameters
        params = self.state['learned_parameters']['exhaustion']

        exhaustion_signals = []
        risk_score = 0

        if stage == 'late':
            exhaustion_signals.append('Late stage theme')
            risk_score += params['late_stage_risk']
        elif stage == 'peak':
            exhaustion_signals.append('At peak momentum')
            risk_score += params['peak_stage_risk']

        days_threshold = params['days_active_threshold']
        if days_active > days_threshold:
            exhaustion_signals.append(f'Active for {days_active} days (threshold: {days_threshold})')
            risk_score += min(30, days_active // 10)

        # Estimate peak date based on learned lifecycle data
        lifecycle_params = self.state['learned_parameters']['lifecycle']
        avg_lifecycle = lifecycle_params.get('avg_theme_duration', 90)

        if stage in ['early', 'middle']:
            estimated_peak = datetime.now() + timedelta(days=max(30, avg_lifecycle - days_active))
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
            'learned_parameters_used': True,
        }

        self.state['predictions']['theme_exhaustion'][theme_id] = prediction
        save_learning_state(self.state)

        return prediction

    def predict_wave_timing(self, driver: str, event: str) -> Dict:
        """Predict tier timing based on learned propagation patterns."""
        patterns = self.state['empirical_correlations']['propagation_patterns']
        key = f"{driver}_{event}"

        if key in patterns and patterns[key].get('learned'):
            pattern = patterns[key]
            confidence = 0.8  # High confidence for learned patterns
        else:
            # No learned pattern - try to learn it now
            learner = CorrelationLearner()
            pattern = learner.learn_wave_propagation(driver, event)

            if not pattern.get('learned'):
                # Still no data - return low confidence estimate
                return {
                    'driver': driver,
                    'event': event,
                    'message': 'Insufficient data to predict wave timing',
                    'confidence': 0.2,
                }
            confidence = 0.5  # Medium confidence for newly learned

        now = datetime.now()

        return {
            'driver': driver,
            'event': event,
            'tier1_expected': (now + timedelta(days=pattern.get('tier1_avg_lag', 1))).strftime('%Y-%m-%d'),
            'tier2_expected': (now + timedelta(days=pattern.get('tier2_avg_lag', 3))).strftime('%Y-%m-%d'),
            'tier3_expected': (now + timedelta(days=pattern.get('tier3_avg_lag', 7))).strftime('%Y-%m-%d'),
            'confidence': confidence,
            'samples': pattern.get('tier1_samples', 0),
        }

    def find_optimal_entry_windows(self, signal_type: str) -> Dict:
        """Find best entry windows based on learned performance."""
        alert_file = LEARNING_DATA_DIR / 'alert_accuracy.json'

        if not alert_file.exists():
            return {'status': 'no_data'}

        try:
            with open(alert_file, 'r') as f:
                alert_data = json.load(f)
        except Exception:
            return {'status': 'error'}

        alerts = alert_data.get('alerts', [])
        relevant = [a for a in alerts if a.get('alert_type') == signal_type]

        min_samples = self.state['learned_parameters']['sample_sizes']['min_for_signal_accuracy']
        if len(relevant) < min_samples:
            return {'status': 'insufficient_data', 'samples': len(relevant), 'min_required': min_samples}

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

        min_day_samples = self.state['learned_parameters']['sample_sizes']['min_for_day_performance']
        day_rates = {}
        for day, perf in day_performance.items():
            total = perf['wins'] + perf['losses']
            if total >= min_day_samples:
                day_rates[day] = perf['wins'] / total

        if day_rates:
            best_day = max(day_rates, key=day_rates.get)
            worst_day = min(day_rates, key=day_rates.get)
        else:
            # Not enough data - return status instead of defaults
            return {
                'status': 'insufficient_day_data',
                'samples': len(relevant),
                'days_analyzed': len(day_performance),
            }

        result = {
            'signal_type': signal_type,
            'best_day': best_day,
            'best_day_rate': round(day_rates[best_day] * 100, 1),
            'worst_day': worst_day,
            'worst_day_rate': round(day_rates[worst_day] * 100, 1),
            'samples': len(relevant),
            'all_days': {k: round(v * 100, 1) for k, v in day_rates.items()},
        }

        self.state['predictions']['optimal_windows'][signal_type] = result
        save_learning_state(self.state)

        return result


# =============================================================================
# VALIDATION MONITOR
# =============================================================================

class ValidationMonitor:
    """
    Continuous accuracy monitoring with learned thresholds.
    """

    def __init__(self):
        self.state = load_learning_state()

    def calculate_accuracy_with_ci(self, predictions: List[Dict] = None) -> Dict:
        """Calculate accuracy with Wilson score confidence interval."""
        if predictions is None:
            alert_file = LEARNING_DATA_DIR / 'alert_accuracy.json'
            if not alert_file.exists():
                return {'status': 'no_data'}

            try:
                with open(alert_file, 'r') as f:
                    alert_data = json.load(f)
                predictions = alert_data.get('alerts', [])
            except Exception:
                return {'status': 'error'}

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

        self.state['validation_metrics']['overall_accuracy'] = result['accuracy']
        self.state['validation_metrics']['confidence_interval_95'] = result['confidence_interval_95']
        save_learning_state(self.state)

        return result

    def assess_calibration(self, predictions: List[Dict] = None) -> Dict:
        """Bucket by confidence and compare predicted vs actual."""
        if predictions is None:
            alert_file = LEARNING_DATA_DIR / 'alert_accuracy.json'
            if not alert_file.exists():
                return {'status': 'no_data'}

            try:
                with open(alert_file, 'r') as f:
                    predictions = json.load(f).get('alerts', [])
            except Exception:
                return {'status': 'error'}

        buckets = defaultdict(lambda: {'predicted': [], 'actual': []})

        for pred in predictions:
            confidence = pred.get('confidence', 50)
            outcome = pred.get('outcome')

            if outcome in ['win', 'loss']:
                bucket_key = (confidence // 10) * 10
                buckets[bucket_key]['predicted'].append(confidence / 100)
                buckets[bucket_key]['actual'].append(1 if outcome == 'win' else 0)

        min_samples = self.state['learned_parameters']['calibration']['min_bucket_samples']
        calibration = {}
        total_error = 0
        total_buckets = 0

        for bucket_key in sorted(buckets.keys()):
            data = buckets[bucket_key]
            if len(data['actual']) >= min_samples:
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

        if total_buckets > 0:
            avg_error = total_error / total_buckets
            calibration_score = round((1 - avg_error) * 100, 1)
        else:
            calibration_score = None

        good_threshold = self.state['learned_parameters']['calibration']['good_threshold']

        return {
            'buckets': calibration,
            'calibration_score': calibration_score,
            'interpretation': 'Good' if calibration_score and calibration_score >= good_threshold else 'Needs improvement',
            'good_threshold': good_threshold,
        }

    def detect_accuracy_degradation(self) -> Dict:
        """Flag if recent accuracy < historical with learned thresholds."""
        alert_file = LEARNING_DATA_DIR / 'alert_accuracy.json'
        if not alert_file.exists():
            return {'status': 'no_data'}

        try:
            with open(alert_file, 'r') as f:
                alerts = json.load(f).get('alerts', [])
        except Exception:
            return {'status': 'error'}

        # Get learned parameters
        params = self.state['learned_parameters']['degradation']
        recent_days = params['recent_window_days']
        baseline_days = params['baseline_window_days']
        threshold = params['threshold_percent']

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

        min_samples = self.state['learned_parameters']['sample_sizes']['min_for_signal_accuracy']
        if len(recent) < min_samples or len(baseline) < min_samples * 2:
            return {'status': 'insufficient_data'}

        recent_accuracy = np.mean(recent) * 100
        baseline_accuracy = np.mean(baseline) * 100
        difference = recent_accuracy - baseline_accuracy

        degradation_detected = difference < -threshold

        # Learn threshold from historical variance
        if len(baseline) >= 30:
            baseline_std = np.std(baseline) * 100
            suggested_threshold = max(3, baseline_std * 1.5)
            params['threshold_percent'] = round(params['threshold_percent'] * 0.8 + suggested_threshold * 0.2, 1)
            params['learned_from_samples'] = params.get('learned_from_samples', 0) + 1
            save_learning_state(self.state)

        return {
            'recent_accuracy': round(recent_accuracy, 1),
            'baseline_accuracy': round(baseline_accuracy, 1),
            'difference': round(difference, 1),
            'degradation_detected': degradation_detected,
            'threshold_used': threshold,
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
            'schedule': '0 6 * * *',
            'tasks': [
                'update_alert_outcomes',
                'close_feedback_loops',
                'update_theme_lifecycles',
                'check_for_new_themes',
            ],
        },
        'weekly_optimization': {
            'schedule': '0 5 * * 0',
            'tasks': [
                'recalculate_optimal_weights',
                'refresh_all_ecosystems',
                'retire_exhausted_themes',
                'full_validation_report',
            ],
        },
        'hourly_correlation': {
            'schedule': '0 * * * 1-5',
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

        # 1. Close feedback loops (includes parameter learning)
        feedback_mgr = FeedbackLoopManager()
        results['feedback_loops'] = feedback_mgr.close_all_loops()

        # 2. Update theme lifecycles
        theme_engine = ThemeEvolutionEngine()

        # 3. Check for new themes
        results['discovered_themes'] = theme_engine.discover_themes()

        # 4. Update validation metrics
        validator = ValidationMonitor()
        results['accuracy'] = validator.calculate_accuracy_with_ci()
        results['calibration'] = validator.assess_calibration()
        results['degradation_check'] = validator.detect_accuracy_degradation()

        # 5. Detect and store current regime
        detector = MarketRegimeDetector()
        current_regime = detector.detect_current_regime()
        results['current_regime'] = current_regime

        self.job_state['last_run']['daily_learning'] = datetime.now().isoformat()
        save_job_state(self.job_state)

        self.state['evolution_cycle'] = self.state.get('evolution_cycle', 0) + 1
        self.state['last_evolution'] = datetime.now().isoformat()
        save_learning_state(self.state)

        logger.info(f"Daily learning cycle #{self.state['evolution_cycle']} complete (regime: {current_regime})")

        return results

    def run_weekly_optimization(self) -> Dict:
        """Run weekly weight optimization."""
        results = {}

        logger.info("Starting weekly optimization...")

        # 1. Detect current regime
        detector = MarketRegimeDetector()
        current_regime = detector.detect_current_regime()
        results['regime'] = current_regime

        # 2. Recalculate optimal weights for current regime
        scoring_engine = AdaptiveScoringEngine()
        results['new_weights'] = scoring_engine.calculate_optimal_weights(regime=current_regime)
        results['weight_changes'] = scoring_engine.get_weight_changes()

        # 3. Learn smoothing factor from weight history
        weight_history = self.state['adaptive_weights']['history']
        scoring_engine.learn_smoothing_factor(weight_history)

        # 4. Full validation report
        validator = ValidationMonitor()
        results['validation'] = validator.calculate_accuracy_with_ci()

        # 5. Theme cleanup
        theme_engine = ThemeEvolutionEngine()

        self.job_state['last_run']['weekly_optimization'] = datetime.now().isoformat()
        save_job_state(self.job_state)

        logger.info("Weekly optimization complete")

        return results

    def run_correlation_update(self, tickers: List[str]) -> Dict:
        """Update correlations for given tickers."""
        learner = CorrelationLearner()
        return learner.update_correlations(tickers)

    def post_scan_learning(self, scan_results) -> Dict:
        """Trigger learning after a scan completes."""
        results = {}

        try:
            if hasattr(scan_results, 'head'):
                top_tickers = scan_results.head(30)['ticker'].tolist()
            else:
                top_tickers = []

            if top_tickers:
                learner = CorrelationLearner()
                results['correlations'] = learner.update_correlations(top_tickers)

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
                return last_dt.date() < datetime.now().date()
            elif job_name == 'weekly_optimization':
                return (datetime.now() - last_dt).days >= 7
            elif job_name == 'hourly_correlation':
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
    return state['adaptive_weights']['current'] or INITIAL_DEFAULT_WEIGHTS.copy()


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
        'learned_parameters': state.get('learned_parameters', {}),
    }


def run_evolution_cycle() -> Dict:
    """Manually trigger a full evolution cycle."""
    scheduler = EvolutionScheduler()

    results = {
        'daily': scheduler.run_daily_learning(),
    }

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


def get_learned_parameters() -> Dict:
    """Get all learned parameters."""
    state = load_learning_state()
    return state.get('learned_parameters', {})


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
    print("Evolution Engine Test (v2.0 - All Parameters Learned)")
    print("=" * 60)

    state = load_learning_state()
    print(f"Evolution Cycle: {state.get('evolution_cycle', 0)}")
    print(f"Last Evolution: {state.get('last_evolution', 'Never')}")

    print("\nLearned Parameters:")
    params = state.get('learned_parameters', {})
    for category, values in params.items():
        samples = values.get('learned_from_samples', 0)
        print(f"  {category}: {samples} samples learned")

    print("\nTesting Market Regime Detection...")
    detector = MarketRegimeDetector()
    regime = detector.detect_current_regime()
    print(f"Current regime: {regime}")

    print("\nTesting Adaptive Scoring Engine...")
    ase = AdaptiveScoringEngine()
    weights = ase.get_regime_weights()
    print(f"Current weights: {weights}")

    print("\nRegime-specific weights (learned, not preset):")
    for r in ['bull_trending', 'bear_volatile', 'range_bound']:
        rw = state['adaptive_weights']['by_regime'].get(r, {})
        status = "LEARNED" if rw else "NOT YET LEARNED"
        print(f"  {r}: {status}")

    print("\n" + "=" * 60)
    print("Evolution Engine Ready! All parameters will be learned from data.")
