"""
Bayesian Optimizer - Batch Parameter Optimization

Uses outcome history to find optimal parameter values through Bayesian analysis.
"""
from typing import Optional, Dict, List, Any, TYPE_CHECKING
from collections import defaultdict

if TYPE_CHECKING:
    from ..core.registry import ParameterRegistry
    from ..tracking.outcomes import OutcomeTracker


class BayesianOptimizer:
    """
    Uses Bayesian optimization for finding optimal parameter values.
    Better for periodic batch optimization than real-time updates.
    """

    def __init__(self, registry: 'ParameterRegistry', outcome_tracker: 'OutcomeTracker'):
        self.registry = registry
        self.outcomes = outcome_tracker

    def optimize_parameter(self, param_name: str) -> Optional[Dict[str, Any]]:
        """Find the optimal value for a parameter based on outcome history"""
        outcomes = self.outcomes.get_outcomes_for_parameter(param_name)

        if len(outcomes) < 20:
            return None  # Not enough data

        # Group outcomes by value ranges
        param = self.registry.get_with_metadata(param_name)
        range_size = (param.max_value - param.min_value) / 10  # 10 buckets

        buckets = defaultdict(lambda: {'wins': 0, 'total': 0})
        for value, outcome in outcomes:
            bucket = int((value - param.min_value) / range_size)
            bucket = max(0, min(9, bucket))  # Clamp to valid range
            buckets[bucket]['total'] += 1
            if outcome == 'win':
                buckets[bucket]['wins'] += 1

        # Find bucket with highest win rate (with minimum sample requirement)
        best_bucket = None
        best_rate = 0

        for bucket, stats in buckets.items():
            if stats['total'] >= 5:  # Minimum samples
                rate = stats['wins'] / stats['total']
                if rate > best_rate:
                    best_rate = rate
                    best_bucket = bucket

        if best_bucket is None:
            return None

        # Calculate optimal value (center of best bucket)
        optimal_value = param.min_value + (best_bucket + 0.5) * range_size

        return {
            'parameter': param_name,
            'current_value': param.current_value,
            'optimal_value': optimal_value,
            'expected_win_rate': best_rate,
            'samples_analyzed': len(outcomes),
            'improvement': best_rate - (sum(1 for _, o in outcomes if o == 'win') / len(outcomes))
        }

    def optimize_all(self) -> List[Dict[str, Any]]:
        """Optimize all parameters and return recommendations"""
        recommendations = []

        for param_name in self.registry.parameters:
            result = self.optimize_parameter(param_name)
            if result and result['improvement'] > 0.02:  # 2% improvement threshold
                recommendations.append(result)

        # Sort by improvement potential
        recommendations.sort(key=lambda x: x['improvement'], reverse=True)

        return recommendations
