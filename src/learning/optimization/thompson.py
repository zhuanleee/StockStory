"""
Thompson Sampling Optimizer - Multi-Armed Bandit for Real-Time Optimization

Uses Thompson Sampling to balance exploration and exploitation for parameter values.
"""
import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.registry import ParameterRegistry


class ThompsonSamplingOptimizer:
    """
    Uses Thompson Sampling (multi-armed bandit) for real-time parameter optimization.
    Balances exploration of new values with exploitation of known good values.
    """

    def __init__(self, registry: 'ParameterRegistry'):
        self.registry = registry

    def sample_parameter_value(self, param_name: str) -> float:
        """Sample a value from the posterior distribution"""
        param = self.registry.get_with_metadata(param_name)

        # Use Beta distribution for bounded parameters
        # Transform to [min, max] range
        sample = random.betavariate(param.alpha, param.beta)
        value = param.min_value + sample * (param.max_value - param.min_value)

        return value

    def update_posterior(self, param_name: str, value_used: float, outcome: str):
        """Update the posterior distribution based on observed outcome"""
        param = self.registry.get_with_metadata(param_name)

        # Normalize value to [0, 1]
        normalized = (value_used - param.min_value) / (param.max_value - param.min_value)

        # Update based on outcome
        if outcome == 'win':
            # Increase alpha (successes) proportional to how close value was to what we sampled
            param.alpha += 1
        elif outcome == 'loss':
            # Increase beta (failures)
            param.beta += 1

        param.learned_from_samples += 1
        param.confidence = param.alpha / (param.alpha + param.beta)

        # Update status
        if param.learned_from_samples >= 10:
            param.status = 'learning'
        if param.learned_from_samples >= 50:
            param.status = 'deployed'

        self.registry._save_registry()

    def get_exploration_rate(self, param_name: str) -> float:
        """Get the current exploration rate for a parameter"""
        param = self.registry.get_with_metadata(param_name)
        # Higher variance = more exploration
        variance = (param.alpha * param.beta) / ((param.alpha + param.beta)**2 * (param.alpha + param.beta + 1))
        return variance
