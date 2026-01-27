"""
Self-Learning System

Parameter learning, outcome tracking, and evolution engine.
"""

from src.learning.parameter_learning import (
    ParameterRegistry,
    get_parameters_snapshot,
    get_parameter,
    get_registry,
    OutcomeTracker,
    BayesianOptimizer,
    ABTestingFramework,
)

# Alias for backward compatibility
get_params = get_parameters_snapshot

__all__ = [
    'ParameterRegistry',
    'get_params',
    'get_parameters_snapshot',
    'get_parameter',
    'get_registry',
    'OutcomeTracker',
    'BayesianOptimizer',
    'ABTestingFramework',
]
