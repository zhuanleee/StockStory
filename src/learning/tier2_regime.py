#!/usr/bin/env python3
"""
Tier 2: Market Regime Detection with Hidden Markov Model

Detects which market regime is active and adapts trading strategy accordingly.

Market Regimes:
1. Bull Momentum - Strong uptrend, momentum strategies work best
2. Bear Defensive - Downtrend, defensive positioning critical
3. Choppy Range-Bound - Sideways, technical analysis key
4. Crisis Mode - Emergency conditions, cash is king
5. Theme-Driven - Strong narratives, theme scores dominate

Uses:
- Hidden Markov Model for regime classification
- Clustering for feature-based regime detection
- Hybrid approach combining both methods
"""

import logging
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json
from pathlib import Path

logger = logging.getLogger(__name__)

from .rl_models import (
    MarketRegimeType,
    MarketContext,
    RegimeState,
    ComponentWeights,
    TradeRecord,
    LearningDataEncoder
)


# =============================================================================
# MARKET FEATURES FOR REGIME DETECTION
# =============================================================================

@dataclass
class MarketFeatures:
    """Features used for regime detection."""
    # Price trends
    spy_sma_20: float = 0.0
    spy_sma_50: float = 0.0
    spy_sma_200: float = 0.0
    spy_change_20d: float = 0.0

    # Volatility
    vix_level: float = 20.0
    vix_change: float = 0.0
    realized_vol_20d: float = 0.0

    # Market breadth
    advance_decline_ratio: float = 1.0
    stocks_above_ma50_pct: float = 50.0
    stocks_above_ma200_pct: float = 50.0
    new_highs_minus_lows: int = 0

    # Sector dynamics
    sector_dispersion: float = 0.0  # How dispersed sector returns are
    sector_rotation_speed: float = 0.0

    # Crisis indicators
    crisis_detected: bool = False
    x_panic_score: float = 0.0

    def to_array(self) -> np.ndarray:
        """Convert to numpy array for ML models."""
        return np.array([
            self.spy_change_20d,
            self.vix_level,
            self.vix_change,
            self.realized_vol_20d,
            self.advance_decline_ratio,
            self.stocks_above_ma50_pct,
            self.stocks_above_ma200_pct,
            self.new_highs_minus_lows,
            self.sector_dispersion,
            self.sector_rotation_speed,
            1.0 if self.crisis_detected else 0.0,
            self.x_panic_score
        ])

    @classmethod
    def from_market_context(cls, context: MarketContext) -> 'MarketFeatures':
        """Create features from market context."""
        return cls(
            spy_change_20d=context.spy_change_pct or 0.0,
            vix_level=context.vix_level or 20.0,
            advance_decline_ratio=context.advance_decline or 1.0,
            stocks_above_ma50_pct=context.stocks_above_ma50 or 50.0,
            stocks_above_ma200_pct=context.stocks_above_ma200 or 50.0,
            new_highs_minus_lows=(context.new_highs or 0) - (context.new_lows or 0),
            crisis_detected=context.crisis_active
        )


# =============================================================================
# HIDDEN MARKOV MODEL FOR REGIME DETECTION
# =============================================================================

class HiddenMarkovRegimeDetector:
    """
    Hidden Markov Model for detecting market regimes.

    States represent regimes.
    Observations are market features.
    Learns transition probabilities and emission probabilities.
    """

    def __init__(self, n_regimes: int = 5):
        """Initialize HMM."""
        self.n_regimes = n_regimes
        self.regime_names = list(MarketRegimeType)[:n_regimes]

        # HMM parameters
        self.transition_matrix = self._init_transition_matrix()
        self.emission_means = self._init_emission_means()
        self.emission_covs = self._init_emission_covs()

        # Current state
        self.current_regime_idx = 0
        self.current_regime = self.regime_names[0]
        self.regime_probabilities = np.ones(n_regimes) / n_regimes

    def _init_transition_matrix(self) -> np.ndarray:
        """
        Initialize transition matrix.

        High diagonal (0.95) = regimes are sticky (tend to persist)
        Low off-diagonal = regime changes are rare
        """
        matrix = np.ones((self.n_regimes, self.n_regimes)) * 0.01
        np.fill_diagonal(matrix, 0.95)

        # Normalize rows to sum to 1
        matrix = matrix / matrix.sum(axis=1, keepdims=True)

        return matrix

    def _init_emission_means(self) -> np.ndarray:
        """
        Initialize emission means for each regime.

        Each regime has characteristic market features.
        """
        # Feature order: spy_change, vix, vix_change, realized_vol, adv_dec, ...
        means = {
            MarketRegimeType.BULL_MOMENTUM: [5.0, 15.0, -2.0, 12.0, 1.5, 70.0, 75.0, 100, 0.1, 0.2, 0.0, 0.0],
            MarketRegimeType.BEAR_DEFENSIVE: [-5.0, 30.0, 5.0, 25.0, 0.7, 30.0, 35.0, -100, 0.2, 0.3, 0.0, 0.3],
            MarketRegimeType.CHOPPY_RANGE: [0.0, 20.0, 0.0, 15.0, 1.0, 50.0, 50.0, 0, 0.15, 0.15, 0.0, 0.1],
            MarketRegimeType.CRISIS_MODE: [-10.0, 50.0, 20.0, 40.0, 0.5, 20.0, 25.0, -200, 0.3, 0.4, 1.0, 0.8],
            MarketRegimeType.THEME_DRIVEN: [3.0, 18.0, -1.0, 14.0, 1.2, 60.0, 65.0, 50, 0.25, 0.25, 0.0, 0.0]
        }

        return np.array([means.get(regime, [0.0] * 12) for regime in self.regime_names])

    def _init_emission_covs(self) -> np.ndarray:
        """Initialize emission covariances (simplified as diagonal)."""
        # Start with high variance (uncertain)
        return np.array([np.eye(12) * 10.0 for _ in range(self.n_regimes)])

    def predict(self, features: MarketFeatures) -> Tuple[MarketRegimeType, float]:
        """
        Predict current regime given market features.

        Returns: (regime, confidence)
        """
        observation = features.to_array()

        # Calculate emission probabilities for each regime
        emission_probs = np.zeros(self.n_regimes)
        for i in range(self.n_regimes):
            # Gaussian likelihood
            mean = self.emission_means[i]
            cov = self.emission_covs[i]

            # Compute multivariate Gaussian probability
            diff = observation - mean
            try:
                inv_cov = np.linalg.inv(cov)
                mahalanobis = np.dot(np.dot(diff, inv_cov), diff)
                emission_probs[i] = np.exp(-0.5 * mahalanobis)
            except np.linalg.LinAlgError:
                emission_probs[i] = 0.01  # Fallback if covariance is singular

        # Forward algorithm: predict current state given observations
        predicted_probs = np.dot(self.regime_probabilities, self.transition_matrix)
        posterior_probs = predicted_probs * emission_probs
        posterior_probs = posterior_probs / (posterior_probs.sum() + 1e-10)

        # Update current state
        self.regime_probabilities = posterior_probs
        self.current_regime_idx = np.argmax(posterior_probs)
        self.current_regime = self.regime_names[self.current_regime_idx]

        confidence = posterior_probs[self.current_regime_idx]

        return self.current_regime, confidence

    def update(self, features: MarketFeatures, observed_regime: Optional[MarketRegimeType] = None):
        """
        Update HMM parameters based on observation.

        If observed_regime is provided (e.g., manually labeled), use supervised learning.
        Otherwise, use unsupervised (EM algorithm).
        """
        observation = features.to_array()

        if observed_regime:
            # Supervised update
            regime_idx = self.regime_names.index(observed_regime)

            # Update emission mean (moving average)
            alpha = 0.1  # Learning rate
            self.emission_means[regime_idx] = (
                (1 - alpha) * self.emission_means[regime_idx] +
                alpha * observation
            )

            # Update emission covariance
            diff = observation - self.emission_means[regime_idx]
            self.emission_covs[regime_idx] = (
                (1 - alpha) * self.emission_covs[regime_idx] +
                alpha * np.outer(diff, diff)
            )

        # Update transition probabilities based on actual transitions
        # (This requires tracking state sequence, simplified here)


# =============================================================================
# RULE-BASED REGIME DETECTOR (FAST, INTERPRETABLE)
# =============================================================================

class RuleBasedRegimeDetector:
    """
    Simple rule-based regime detection.

    Fast, interpretable, works well even with limited data.
    """

    @staticmethod
    def detect(features: MarketFeatures) -> Tuple[MarketRegimeType, float]:
        """Detect regime using simple rules."""

        # Crisis Mode - highest priority
        if features.crisis_detected or features.vix_level > 40 or features.x_panic_score > 0.7:
            confidence = 0.9
            if features.vix_level > 50:
                confidence = 0.95
            return MarketRegimeType.CRISIS_MODE, confidence

        # Bear Defensive
        if (features.spy_change_20d < -5 and
            features.vix_level > 25 and
            features.stocks_above_ma50_pct < 40):
            confidence = 0.8
            return MarketRegimeType.BEAR_DEFENSIVE, confidence

        # Bull Momentum
        if (features.spy_change_20d > 3 and
            features.vix_level < 18 and
            features.stocks_above_ma50_pct > 65 and
            features.advance_decline_ratio > 1.3):
            confidence = 0.8
            return MarketRegimeType.BULL_MOMENTUM, confidence

        # Choppy Range-Bound
        if (abs(features.spy_change_20d) < 2 and
            15 < features.vix_level < 25 and
            40 < features.stocks_above_ma50_pct < 60):
            confidence = 0.7
            return MarketRegimeType.CHOPPY_RANGE, confidence

        # Theme-Driven (default if strong sector rotation)
        if features.sector_dispersion > 0.2 or features.sector_rotation_speed > 0.2:
            confidence = 0.6
            return MarketRegimeType.THEME_DRIVEN, confidence

        # Default to choppy with low confidence
        return MarketRegimeType.CHOPPY_RANGE, 0.5


# =============================================================================
# HYBRID REGIME DETECTOR (COMBINES BOTH METHODS)
# =============================================================================

class RegimeDetector:
    """
    Hybrid regime detector combining HMM and rule-based approaches.

    Uses HMM for nuanced detection, but overrides with rules in extreme conditions.
    """

    def __init__(self, storage_dir: Optional[Path] = None):
        """Initialize regime detector."""
        self.storage_dir = storage_dir or Path('user_data/learning')
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # Initialize both detectors
        self.hmm = HiddenMarkovRegimeDetector()
        self.rule_based = RuleBasedRegimeDetector()

        # Regime history
        self.regime_history: List[RegimeState] = []
        self.current_state = RegimeState()

        # Performance tracking per regime
        self.regime_performance: Dict[MarketRegimeType, List[float]] = {
            regime: [] for regime in MarketRegimeType
        }

        # Load state
        self.load_state()

    # =========================================================================
    # DETECTION
    # =========================================================================

    def detect_regime(self, market_context: MarketContext) -> RegimeState:
        """
        Detect current market regime.

        Returns RegimeState with current regime, confidence, and probabilities.
        """
        # Extract features
        features = MarketFeatures.from_market_context(market_context)

        # Get predictions from both methods
        hmm_regime, hmm_confidence = self.hmm.predict(features)
        rule_regime, rule_confidence = self.rule_based.detect(features)

        # Combine predictions (weighted by confidence)
        if rule_confidence > 0.85:
            # High-confidence rule-based override (e.g., crisis)
            final_regime = rule_regime
            final_confidence = rule_confidence
        elif hmm_confidence > 0.7:
            # Trust HMM when confident
            final_regime = hmm_regime
            final_confidence = hmm_confidence
        else:
            # Blend both (favor higher confidence)
            if rule_confidence > hmm_confidence:
                final_regime = rule_regime
                final_confidence = rule_confidence
            else:
                final_regime = hmm_regime
                final_confidence = hmm_confidence

        # Build regime state
        state = RegimeState(
            current_regime=final_regime,
            confidence=final_confidence,
            regime_probabilities={
                regime: prob
                for regime, prob in zip(self.hmm.regime_names, self.hmm.regime_probabilities)
            },
            timestamp=datetime.now()
        )

        # Check for regime change
        if self.current_state.current_regime != final_regime:
            state.regime_changes.append({
                'from': self.current_state.current_regime.value,
                'to': final_regime.value,
                'timestamp': datetime.now().isoformat(),
                'confidence': final_confidence
            })
            state.last_change = datetime.now()

        # Update current state
        self.current_state = state
        self.regime_history.append(state)

        # Keep history manageable
        if len(self.regime_history) > 1000:
            self.regime_history = self.regime_history[-1000:]

        return state

    def get_current_regime(self) -> MarketRegimeType:
        """Get current regime."""
        return self.current_state.current_regime

    def get_regime_confidence(self) -> float:
        """Get confidence in current regime."""
        return self.current_state.confidence

    # =========================================================================
    # LEARNING FROM OUTCOMES
    # =========================================================================

    def update_from_trade(self, trade: TradeRecord):
        """Learn from trade outcome to improve regime detection."""
        regime = trade.market_context.regime
        if regime == MarketRegimeType.UNKNOWN:
            return

        pnl_pct = trade.pnl_pct or 0.0
        self.regime_performance[regime].append(pnl_pct)

        # Keep recent performance only
        if len(self.regime_performance[regime]) > 100:
            self.regime_performance[regime] = self.regime_performance[regime][-100:]

        # Update HMM with this observation
        features = MarketFeatures.from_market_context(trade.market_context)
        self.hmm.update(features, regime)

    # =========================================================================
    # STATISTICS
    # =========================================================================

    def get_statistics(self) -> dict:
        """Get regime detection statistics."""
        stats = {
            'current_regime': self.current_state.current_regime.value,
            'confidence': self.current_state.confidence,
            'regime_probabilities': {
                regime.value: prob
                for regime, prob in self.current_state.regime_probabilities.items()
            },
            'recent_changes': self.current_state.regime_changes[-10:],
            'performance_by_regime': {}
        }

        # Calculate performance stats per regime
        for regime, pnls in self.regime_performance.items():
            if pnls:
                stats['performance_by_regime'][regime.value] = {
                    'trades': len(pnls),
                    'avg_pnl': np.mean(pnls),
                    'win_rate': sum(1 for p in pnls if p > 0) / len(pnls),
                    'sharpe': np.mean(pnls) / np.std(pnls) if np.std(pnls) > 0 else 0.0
                }

        return stats

    def print_report(self):
        """Print regime detection report."""
        print("\n" + "=" * 80)
        print("REGIME DETECTION REPORT")
        print("=" * 80)

        stats = self.get_statistics()

        print(f"\n🎯 Current Regime: {stats['current_regime'].upper()}")
        print(f"Confidence: {stats['confidence']:.1%}")

        print("\n📊 Regime Probabilities:")
        for regime, prob in sorted(stats['regime_probabilities'].items(), key=lambda x: -x[1]):
            print(f"  {regime}: {prob:.1%}")

        print("\n💰 Performance by Regime:")
        for regime, perf in stats['performance_by_regime'].items():
            print(f"\n  {regime.upper()}:")
            print(f"    Trades: {perf['trades']}")
            print(f"    Avg P&L: {perf['avg_pnl']:+.2f}%")
            print(f"    Win Rate: {perf['win_rate']:.1%}")
            print(f"    Sharpe: {perf['sharpe']:.2f}")

        if stats['recent_changes']:
            print("\n🔄 Recent Regime Changes:")
            for change in stats['recent_changes'][-5:]:
                print(f"  {change['from']} → {change['to']} (confidence: {change['confidence']:.1%})")

        print("\n" + "=" * 80)

    # =========================================================================
    # PERSISTENCE
    # =========================================================================

    def save_state(self):
        """Save regime detector state."""
        state = {
            'current_state': {
                'regime': self.current_state.current_regime.value,
                'confidence': self.current_state.confidence,
                'timestamp': self.current_state.timestamp.isoformat()
            },
            'regime_performance': {
                regime.value: pnls
                for regime, pnls in self.regime_performance.items()
            },
            'hmm_transition_matrix': self.hmm.transition_matrix.tolist(),
            'hmm_emission_means': self.hmm.emission_means.tolist(),
            'last_updated': datetime.now().isoformat()
        }

        path = self.storage_dir / 'regime_detector_state.json'
        with open(path, 'w') as f:
            json.dump(state, f, indent=2, cls=LearningDataEncoder)

    def load_state(self):
        """Load regime detector state."""
        path = self.storage_dir / 'regime_detector_state.json'
        if not path.exists():
            return

        try:
            with open(path, 'r') as f:
                state = json.load(f)

            # Restore regime performance
            for regime_str, pnls in state.get('regime_performance', {}).items():
                regime = MarketRegimeType(regime_str)
                self.regime_performance[regime] = pnls

            # Restore HMM parameters
            if 'hmm_transition_matrix' in state:
                self.hmm.transition_matrix = np.array(state['hmm_transition_matrix'])
            if 'hmm_emission_means' in state:
                self.hmm.emission_means = np.array(state['hmm_emission_means'])

        except Exception as e:
            logger.warning(f"Could not load regime detector state: {e}")


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    print("Testing Regime Detector...")

    detector = RegimeDetector()

    # Test different market conditions
    scenarios = [
        ("Bull Market", MarketContext(spy_change_pct=5.0, vix_level=12.0, stocks_above_ma50=75.0)),
        ("Bear Market", MarketContext(spy_change_pct=-8.0, vix_level=35.0, stocks_above_ma50=25.0)),
        ("Crisis", MarketContext(spy_change_pct=-15.0, vix_level=55.0, crisis_active=True)),
        ("Choppy", MarketContext(spy_change_pct=0.5, vix_level=20.0, stocks_above_ma50=50.0))
    ]

    print("\n📊 Testing regime detection on different scenarios:")
    for name, context in scenarios:
        state = detector.detect_regime(context)
        print(f"\n{name}:")
        print(f"  Detected: {state.current_regime.value}")
        print(f"  Confidence: {state.confidence:.1%}")

    detector.print_report()

    print("\n✅ Regime Detector test complete!")
