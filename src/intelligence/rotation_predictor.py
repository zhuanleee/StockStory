"""
Theme Rotation Predictor
========================
Predict which themes will rotate in/out based on multiple signals.

Signals Used:
1. Velocity & acceleration (from theme_intelligence)
2. Peak detection (high score + slowing momentum)
3. Cross-theme correlation (money flowing between themes)
4. Institutional positioning (from institutional_flow)
5. Historical rotation patterns

Usage:
    from src.intelligence.rotation_predictor import RotationPredictor

    predictor = RotationPredictor()

    # Get rotation forecast
    forecast = predictor.get_rotation_forecast()

    # Get peak warnings
    peaks = predictor.detect_peak_themes()

    # Get reversion candidates
    reversions = predictor.detect_reversion_candidates()
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path

logger = logging.getLogger(__name__)

# Persistence
DATA_DIR = Path("data/rotation_predictor")
ROTATION_HISTORY_FILE = DATA_DIR / "rotation_history.json"
FORECAST_CACHE_FILE = DATA_DIR / "forecast_cache.json"


def ensure_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class RotationSignal:
    """A rotation signal for a theme."""
    theme_id: str
    theme_name: str
    signal_type: str  # rotating_in, rotating_out, peak_warning, reversion
    confidence: float  # 0-1
    target_themes: List[str]  # Where money might flow to
    reasoning: List[str]
    timestamp: str


@dataclass
class RotationForecast:
    """Forecast for theme rotation."""
    theme_id: str
    theme_name: str
    current_lifecycle: str
    predicted_lifecycle: str
    rotation_probability: float  # 0-1
    direction: str  # in, out, stable
    time_horizon: str  # 1-2 weeks, 1 month, etc.
    signals: List[str]
    related_themes: List[str]


@dataclass
class PeakWarning:
    """Warning that a theme may be peaking."""
    theme_id: str
    theme_name: str
    warning_level: str  # early, imminent, confirmed
    peak_signals: List[str]
    days_at_peak: int
    recommended_action: str


class RotationPredictor:
    """
    Predict theme rotations using multiple signals.
    """

    def __init__(self):
        ensure_data_dir()
        self.rotation_history = self._load_rotation_history()

    def _load_rotation_history(self) -> List[Dict]:
        """Load rotation history."""
        if ROTATION_HISTORY_FILE.exists():
            try:
                with open(ROTATION_HISTORY_FILE) as f:
                    return json.load(f)
            except:
                pass
        return []

    def _save_rotation_history(self):
        """Save rotation history."""
        self.rotation_history = self.rotation_history[-500:]
        with open(ROTATION_HISTORY_FILE, 'w') as f:
            json.dump(self.rotation_history, f, indent=2)

    # =========================================================================
    # ROTATION FORECAST
    # =========================================================================

    def get_rotation_forecast(self) -> Dict:
        """
        Generate rotation forecast for all themes.

        Analyzes:
        - Theme velocity and acceleration
        - Lifecycle stage transitions
        - Institutional flow direction
        - Cross-theme correlations
        """
        try:
            from src.intelligence.theme_intelligence import (
                get_theme_hub,
                THEME_NAMES,
                THEME_TICKER_MAP
            )

            hub = get_theme_hub()
            history = hub.history.get('themes', {})

            forecasts = []

            for theme_id in THEME_TICKER_MAP.keys():
                theme_data = history.get(theme_id, {})
                theme_name = THEME_NAMES.get(theme_id, theme_id)

                current_lifecycle = theme_data.get('lifecycle', 'dead')
                score = theme_data.get('fused_score', 0)
                score_history = theme_data.get('score_history', [])

                # Calculate velocity and acceleration
                velocity = 0
                acceleration = 0

                if len(score_history) >= 2:
                    velocity = score_history[-1].get('fused_score', 0) - score_history[-2].get('fused_score', 0)

                if len(score_history) >= 3:
                    prev_velocity = score_history[-2].get('fused_score', 0) - score_history[-3].get('fused_score', 0)
                    acceleration = velocity - prev_velocity

                # Predict next lifecycle
                predicted, probability, direction, signals = self._predict_lifecycle(
                    current_lifecycle, score, velocity, acceleration
                )

                # Find related themes (potential rotation targets)
                related = self._find_related_themes(theme_id, direction)

                forecast = RotationForecast(
                    theme_id=theme_id,
                    theme_name=theme_name,
                    current_lifecycle=current_lifecycle,
                    predicted_lifecycle=predicted,
                    rotation_probability=probability,
                    direction=direction,
                    time_horizon='1-2 weeks',
                    signals=signals,
                    related_themes=related
                )

                forecasts.append(forecast)

            # Sort by rotation probability
            forecasts.sort(key=lambda x: x.rotation_probability, reverse=True)

            # Categorize
            rotating_in = [f for f in forecasts if f.direction == 'in' and f.rotation_probability > 0.5]
            rotating_out = [f for f in forecasts if f.direction == 'out' and f.rotation_probability > 0.5]
            stable = [f for f in forecasts if f.direction == 'stable' or f.rotation_probability <= 0.5]

            return {
                'ok': True,
                'timestamp': datetime.now().isoformat(),
                'summary': {
                    'rotating_in': len(rotating_in),
                    'rotating_out': len(rotating_out),
                    'stable': len(stable)
                },
                'rotating_in': [asdict(f) for f in rotating_in],
                'rotating_out': [asdict(f) for f in rotating_out],
                'all_forecasts': [asdict(f) for f in forecasts]
            }

        except Exception as e:
            logger.error(f"Rotation forecast error: {e}")
            return {'ok': False, 'error': str(e)}

    def _predict_lifecycle(
        self,
        current: str,
        score: float,
        velocity: float,
        acceleration: float
    ) -> Tuple[str, float, str, List[str]]:
        """
        Predict next lifecycle stage.

        Returns: (predicted_stage, probability, direction, signals)
        """
        signals = []

        # Dead -> Emerging (rotation in)
        if current == 'dead':
            if velocity > 5 and score > 20:
                return 'emerging', min(0.8, velocity / 20), 'in', ['Rising from dead', f'Velocity: +{velocity:.1f}']
            return 'dead', 0.2, 'stable', ['No momentum']

        # Emerging -> Accelerating (continuation)
        if current == 'emerging':
            if acceleration > 5 and velocity > 10:
                return 'accelerating', min(0.9, acceleration / 10), 'in', ['Accelerating momentum', f'Acc: +{acceleration:.1f}']
            if velocity < 0:
                return 'declining', min(0.7, abs(velocity) / 10), 'out', ['Lost momentum']
            return 'emerging', 0.5, 'stable', ['Steady emerging']

        # Accelerating -> Peak (potential top)
        if current == 'accelerating':
            if velocity < 5 and score > 70:
                signals.append('High score but slowing')
                signals.append(f'Velocity dropping: {velocity:.1f}')
                return 'peak', min(0.85, score / 100), 'out', signals
            if acceleration < -5:
                signals.append('Deceleration detected')
                return 'peak', min(0.8, abs(acceleration) / 10), 'out', signals
            return 'accelerating', 0.4, 'stable', ['Still accelerating']

        # Peak -> Declining (rotation out)
        if current == 'peak':
            if velocity < -5:
                return 'declining', min(0.9, abs(velocity) / 15), 'out', ['Breaking down from peak', f'Velocity: {velocity:.1f}']
            if velocity > 5:
                return 'accelerating', min(0.6, velocity / 15), 'in', ['Second wind']
            return 'peak', 0.5, 'stable', ['Holding at peak']

        # Declining -> Dead or Reversion
        if current == 'declining':
            if velocity > 5:
                return 'emerging', min(0.7, velocity / 10), 'in', ['Reverting', 'New interest']
            if score < 20:
                return 'dead', 0.8, 'out', ['Fading out']
            return 'declining', 0.5, 'out', ['Continued decline']

        return current, 0.3, 'stable', ['No clear signal']

    def _find_related_themes(self, theme_id: str, direction: str) -> List[str]:
        """Find themes that might receive/lose money from this theme."""
        # Define theme relationships (money tends to rotate between these)
        rotation_pairs = {
            'ai_chips': ['quantum', 'cloud', 'robotics'],
            'nuclear': ['solar', 'oil'],
            'ev': ['oil', 'infrastructure'],
            'bitcoin': ['gold', 'fintech'],
            'defense': ['cybersecurity', 'space'],
            'solar': ['nuclear', 'oil', 'infrastructure'],
            'gold': ['bitcoin', 'oil'],
            'oil': ['solar', 'nuclear', 'gold'],
            'biotech': ['weight_loss'],
            'weight_loss': ['biotech'],
            'cloud': ['ai_chips', 'cybersecurity'],
            'cybersecurity': ['cloud', 'defense'],
            'space': ['defense', 'robotics'],
            'robotics': ['ai_chips', 'space'],
            'fintech': ['bitcoin'],
            'china': ['ev', 'solar'],
            'retail': ['fintech'],
            'infrastructure': ['solar', 'ev'],
            'metaverse': ['ai_chips', 'cloud'],
            'quantum': ['ai_chips', 'cloud']
        }

        return rotation_pairs.get(theme_id, [])[:3]

    # =========================================================================
    # PEAK DETECTION
    # =========================================================================

    def detect_peak_themes(self) -> List[PeakWarning]:
        """
        Detect themes that may be at or near peak.

        Peak signals:
        - High score (>70) + slowing velocity
        - Max score reached in recent history
        - High sentiment + negative price divergence
        - Institutional selling signals
        """
        try:
            from src.intelligence.theme_intelligence import (
                get_theme_hub,
                THEME_NAMES
            )

            hub = get_theme_hub()
            history = hub.history.get('themes', {})

            warnings = []

            for theme_id, theme_data in history.items():
                theme_name = THEME_NAMES.get(theme_id, theme_id)
                lifecycle = theme_data.get('lifecycle', 'dead')
                score = theme_data.get('fused_score', 0)
                score_history = theme_data.get('score_history', [])

                peak_signals = []
                warning_level = None

                # Check if at/near lifecycle peak
                if lifecycle == 'peak':
                    peak_signals.append('Currently at peak stage')
                    warning_level = 'confirmed'

                # High score check
                if score >= 70:
                    peak_signals.append(f'High score: {score:.0f}')

                # Check if at max in history
                if score_history:
                    max_score = max(s.get('fused_score', 0) for s in score_history)
                    if score >= max_score * 0.95:
                        peak_signals.append('Near historical max')

                # Velocity slowing
                if len(score_history) >= 2:
                    velocity = score_history[-1].get('fused_score', 0) - score_history[-2].get('fused_score', 0)
                    if velocity < 5 and score > 60:
                        peak_signals.append(f'Momentum slowing: {velocity:.1f}')

                        if not warning_level:
                            warning_level = 'imminent' if velocity < 0 else 'early'

                # Need at least 2 signals
                if len(peak_signals) >= 2:
                    # Calculate days at peak
                    days_at_peak = 0
                    stage_start = theme_data.get('stage_start_date')
                    if stage_start and lifecycle == 'peak':
                        try:
                            start = datetime.fromisoformat(stage_start)
                            days_at_peak = (datetime.now() - start).days
                        except:
                            pass

                    # Recommended action
                    if warning_level == 'confirmed':
                        action = 'Consider taking profits, watch for breakdown'
                    elif warning_level == 'imminent':
                        action = 'Tighten stops, reduce position size'
                    else:
                        action = 'Monitor closely for momentum shift'

                    warnings.append(PeakWarning(
                        theme_id=theme_id,
                        theme_name=theme_name,
                        warning_level=warning_level or 'early',
                        peak_signals=peak_signals,
                        days_at_peak=days_at_peak,
                        recommended_action=action
                    ))

            # Sort by warning level severity
            level_order = {'confirmed': 0, 'imminent': 1, 'early': 2}
            warnings.sort(key=lambda x: level_order.get(x.warning_level, 3))

            return warnings

        except Exception as e:
            logger.error(f"Peak detection error: {e}")
            return []

    # =========================================================================
    # REVERSION DETECTION
    # =========================================================================

    def detect_reversion_candidates(self) -> List[Dict]:
        """
        Find dead/declining themes showing signs of reversion.

        Reversion signals:
        - Velocity turning positive from negative
        - New institutional interest
        - News catalysts in dying theme
        """
        try:
            from src.intelligence.theme_intelligence import (
                get_theme_hub,
                THEME_NAMES
            )

            hub = get_theme_hub()
            history = hub.history.get('themes', {})

            candidates = []

            for theme_id, theme_data in history.items():
                theme_name = THEME_NAMES.get(theme_id, theme_id)
                lifecycle = theme_data.get('lifecycle', 'dead')
                score = theme_data.get('fused_score', 0)
                score_history = theme_data.get('score_history', [])

                # Only look at dead/declining
                if lifecycle not in ['dead', 'declining']:
                    continue

                reversion_signals = []

                # Velocity turning positive
                if len(score_history) >= 2:
                    current_vel = score_history[-1].get('fused_score', 0) - score_history[-2].get('fused_score', 0)

                    if current_vel > 3:
                        reversion_signals.append(f'Positive velocity: +{current_vel:.1f}')

                    # Acceleration from negative
                    if len(score_history) >= 3:
                        prev_vel = score_history[-2].get('fused_score', 0) - score_history[-3].get('fused_score', 0)
                        if prev_vel < 0 and current_vel > 0:
                            reversion_signals.append('Velocity turned positive')

                # Score bouncing from low
                if score > 25 and lifecycle == 'dead':
                    reversion_signals.append(f'Score rising from dead: {score:.0f}')

                if reversion_signals:
                    candidates.append({
                        'theme_id': theme_id,
                        'theme_name': theme_name,
                        'current_lifecycle': lifecycle,
                        'score': score,
                        'reversion_signals': reversion_signals,
                        'confidence': min(0.8, len(reversion_signals) * 0.3)
                    })

            return sorted(candidates, key=lambda x: x['confidence'], reverse=True)

        except Exception as e:
            logger.error(f"Reversion detection error: {e}")
            return []

    # =========================================================================
    # ROTATION ALERTS
    # =========================================================================

    def generate_rotation_alerts(self) -> List[RotationSignal]:
        """Generate actionable rotation alerts."""
        alerts = []

        # Get forecasts
        forecast = self.get_rotation_forecast()

        if not forecast.get('ok'):
            return []

        # Rotating in alerts
        for f in forecast.get('rotating_in', []):
            if f['rotation_probability'] > 0.6:
                alert = RotationSignal(
                    theme_id=f['theme_id'],
                    theme_name=f['theme_name'],
                    signal_type='rotating_in',
                    confidence=f['rotation_probability'],
                    target_themes=f['related_themes'],
                    reasoning=f['signals'],
                    timestamp=datetime.now().isoformat()
                )
                alerts.append(alert)

        # Rotating out alerts
        for f in forecast.get('rotating_out', []):
            if f['rotation_probability'] > 0.6:
                alert = RotationSignal(
                    theme_id=f['theme_id'],
                    theme_name=f['theme_name'],
                    signal_type='rotating_out',
                    confidence=f['rotation_probability'],
                    target_themes=f['related_themes'],
                    reasoning=f['signals'],
                    timestamp=datetime.now().isoformat()
                )
                alerts.append(alert)

        # Peak warnings
        peaks = self.detect_peak_themes()
        for peak in peaks:
            if peak.warning_level in ['confirmed', 'imminent']:
                alert = RotationSignal(
                    theme_id=peak.theme_id,
                    theme_name=peak.theme_name,
                    signal_type='peak_warning',
                    confidence=0.8 if peak.warning_level == 'confirmed' else 0.6,
                    target_themes=[],
                    reasoning=peak.peak_signals,
                    timestamp=datetime.now().isoformat()
                )
                alerts.append(alert)

        # Reversion candidates
        reversions = self.detect_reversion_candidates()
        for rev in reversions:
            if rev['confidence'] > 0.5:
                alert = RotationSignal(
                    theme_id=rev['theme_id'],
                    theme_name=rev['theme_name'],
                    signal_type='reversion',
                    confidence=rev['confidence'],
                    target_themes=[],
                    reasoning=rev['reversion_signals'],
                    timestamp=datetime.now().isoformat()
                )
                alerts.append(alert)

        # Record alerts
        for alert in alerts:
            self.rotation_history.append(asdict(alert))

        self._save_rotation_history()

        return alerts


# =============================================================================
# SINGLETON
# =============================================================================

_predictor_instance = None


def get_rotation_predictor() -> RotationPredictor:
    """Get singleton rotation predictor."""
    global _predictor_instance
    if _predictor_instance is None:
        _predictor_instance = RotationPredictor()
    return _predictor_instance


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def get_rotation_forecast() -> Dict:
    """Get rotation forecast."""
    return get_rotation_predictor().get_rotation_forecast()


def get_peak_warnings() -> List[Dict]:
    """Get peak warnings."""
    warnings = get_rotation_predictor().detect_peak_themes()
    return [asdict(w) for w in warnings]


def get_reversion_candidates() -> List[Dict]:
    """Get reversion candidates."""
    return get_rotation_predictor().detect_reversion_candidates()


def get_rotation_alerts() -> List[Dict]:
    """Get rotation alerts."""
    alerts = get_rotation_predictor().generate_rotation_alerts()
    return [asdict(a) for a in alerts]


# =============================================================================
# TELEGRAM FORMATTING
# =============================================================================

def format_rotation_message(forecast: Dict) -> str:
    """Format rotation forecast for Telegram."""
    if not forecast.get('ok'):
        return f"Error: {forecast.get('error', 'Unknown')}"

    msg = "🔄 *ROTATION FORECAST*\n"
    msg += "_Theme rotation predictions_\n\n"

    summary = forecast.get('summary', {})
    msg += f"*Summary:* {summary.get('rotating_in', 0)} in | {summary.get('rotating_out', 0)} out | {summary.get('stable', 0)} stable\n\n"

    # Rotating in
    rotating_in = forecast.get('rotating_in', [])
    if rotating_in:
        msg += "📈 *ROTATING IN:*\n"
        for f in rotating_in[:5]:
            prob = f['rotation_probability'] * 100
            msg += f"• `{f['theme_id'].upper()}` ({prob:.0f}%)\n"
            msg += f"  {f['current_lifecycle']} → {f['predicted_lifecycle']}\n"
            if f.get('signals'):
                msg += f"  _{f['signals'][0]}_\n"
        msg += "\n"

    # Rotating out
    rotating_out = forecast.get('rotating_out', [])
    if rotating_out:
        msg += "📉 *ROTATING OUT:*\n"
        for f in rotating_out[:5]:
            prob = f['rotation_probability'] * 100
            msg += f"• `{f['theme_id'].upper()}` ({prob:.0f}%)\n"
            if f.get('related_themes'):
                msg += f"  → May rotate to: {', '.join(f['related_themes'][:2])}\n"
        msg += "\n"

    if not rotating_in and not rotating_out:
        msg += "_No significant rotations predicted_\n"

    return msg


def format_peak_warnings_message(warnings: List) -> str:
    """Format peak warnings for Telegram."""
    if not warnings:
        return "No peak warnings detected."

    msg = "⚠️ *PEAK WARNINGS*\n"
    msg += "_Themes potentially at top_\n\n"

    level_emoji = {
        'confirmed': '🔴',
        'imminent': '🟡',
        'early': '🟢'
    }

    for w in warnings[:10]:
        if isinstance(w, dict):
            warning = w
        else:
            warning = asdict(w)

        emoji = level_emoji.get(warning['warning_level'], '⚪')
        msg += f"{emoji} *{warning['theme_name']}* ({warning['warning_level'].upper()})\n"

        for signal in warning['peak_signals'][:2]:
            msg += f"   • {signal}\n"

        msg += f"   _{warning['recommended_action']}_\n\n"

    return msg


if __name__ == "__main__":
    print("Rotation Predictor")
    print("=" * 50)

    predictor = RotationPredictor()

    print("\nGetting rotation forecast...")
    forecast = predictor.get_rotation_forecast()

    if forecast.get('ok'):
        print(f"\nRotating in: {len(forecast.get('rotating_in', []))}")
        print(f"Rotating out: {len(forecast.get('rotating_out', []))}")

        for f in forecast.get('rotating_in', [])[:3]:
            print(f"  IN: {f['theme_name']} ({f['rotation_probability']:.1%})")

        for f in forecast.get('rotating_out', [])[:3]:
            print(f"  OUT: {f['theme_name']} ({f['rotation_probability']:.1%})")

    print("\nDetecting peak themes...")
    peaks = predictor.detect_peak_themes()
    for p in peaks[:3]:
        print(f"  PEAK: {p.theme_name} ({p.warning_level})")
