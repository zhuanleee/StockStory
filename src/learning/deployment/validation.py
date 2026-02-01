"""
Validation Engine - Pre-Deployment Parameter Validation

Validates parameter changes before deployment to prevent overfitting.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.registry import ParameterRegistry
    from ..tracking.outcomes import OutcomeTracker

logger = logging.getLogger('parameter_learning.validation')


class ValidationEngine:
    """
    Validates parameter changes before deployment.
    Prevents overfitting and ensures robustness.
    """

    MIN_SAMPLES = 50
    MIN_IMPROVEMENT = 0.02  # 2%
    P_VALUE_THRESHOLD = 0.05
    MAX_CHANGE_RATE = 0.10  # 10% max change per update

    def __init__(self, registry: 'ParameterRegistry', outcome_tracker: 'OutcomeTracker'):
        self.registry = registry
        self.outcomes = outcome_tracker

    def validate_change(self, param_name: str, new_value: float,
                        evidence: Dict[str, Any]) -> Tuple[bool, Dict[str, bool]]:
        """Validate a proposed parameter change"""
        param = self.registry.get_with_metadata(param_name)

        checks = {
            'within_bounds': param.min_value <= new_value <= param.max_value,
            'min_samples': evidence.get('samples', 0) >= self.MIN_SAMPLES,
            'statistical_significance': evidence.get('p_value', 1) < self.P_VALUE_THRESHOLD,
            'meaningful_improvement': abs(evidence.get('improvement', 0)) >= self.MIN_IMPROVEMENT,
            'reasonable_change': abs(new_value - param.current_value) / abs(param.current_value) <= self.MAX_CHANGE_RATE if param.current_value != 0 else True,
            'holdout_validated': evidence.get('holdout_validated', False),
            'consistent_across_regimes': evidence.get('consistent_across_regimes', True),
        }

        passed = all(checks.values())

        return passed, checks

    def check_for_degradation(self, days: int = 7) -> List[Dict[str, Any]]:
        """Check if any recently changed parameters are causing degradation"""
        degraded = []

        # Get recent outcomes
        recent = self.outcomes.get_recent_outcomes(days)
        if len(recent) < 20:
            return []

        # Compare recent win rate to historical
        recent_wins = sum(1 for o in recent if o.outcome_class == 'win')
        recent_rate = recent_wins / len(recent)

        historical = self.outcomes.get_recent_outcomes(90)
        historical = [o for o in historical if o not in recent]

        if len(historical) < 50:
            return []

        hist_wins = sum(1 for o in historical if o.outcome_class == 'win')
        hist_rate = hist_wins / len(historical)

        if recent_rate < hist_rate - 0.05:  # 5% degradation
            # Find recently changed parameters
            for name, param in self.registry.parameters.items():
                if param.last_updated:
                    update_time = datetime.fromisoformat(param.last_updated)
                    if update_time > datetime.now() - timedelta(days=days):
                        degraded.append({
                            'parameter': name,
                            'changed_at': param.last_updated,
                            'current_value': param.current_value,
                            'recent_win_rate': recent_rate,
                            'historical_win_rate': hist_rate,
                            'degradation': hist_rate - recent_rate
                        })

        return degraded
