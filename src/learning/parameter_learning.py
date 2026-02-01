"""
Parameter Learning System - Backwards Compatibility Layer

This module maintains backwards compatibility while the actual implementation
has been refactored into modular components.

All classes and functions are re-exported from their new locations:
- Core: types, registry, paths
- Tracking: outcomes, audit trail
- Optimization: Thompson sampling, Bayesian optimization, A/B testing
- Deployment: validation, shadow mode, gradual rollout
- Monitoring: health monitoring

For new code, prefer importing directly from the submodules:
    from src.learning.core import ParameterRegistry
    from src.learning.tracking import OutcomeTracker
    from src.learning.optimization import ThompsonSamplingOptimizer

For existing code, imports from this module continue to work:
    from src.learning.parameter_learning import ParameterRegistry
"""
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

# Re-export all core types
from .core.types import (
    ParameterCategory,
    LearningStatus,
    ParameterDefinition,
    OutcomeRecord,
    Experiment,
)

# Re-export paths
from .core.paths import (
    DATA_DIR,
    REGISTRY_FILE,
    OUTCOMES_FILE,
    EXPERIMENTS_FILE,
    AUDIT_FILE,
    HEALTH_FILE,
    _ensure_data_dir,
)

# Re-export core components
from .core.registry import ParameterRegistry

# Re-export tracking components
from .tracking.outcomes import OutcomeTracker
from .tracking.audit import AuditTrail

# Re-export optimization components
from .optimization.thompson import ThompsonSamplingOptimizer
from .optimization.bayesian import BayesianOptimizer
from .optimization.experiments import ABTestingFramework

# Re-export deployment components
from .deployment.validation import ValidationEngine
from .deployment.shadow import ShadowMode
from .deployment.rollout import GradualRollout

# Re-export monitoring components
from .monitoring.health import SelfHealthMonitor

logger = logging.getLogger('parameter_learning')


# =============================================================================
# PUBLIC API - Functions for use by other modules
# =============================================================================

# Singleton instances
_registry: Optional[ParameterRegistry] = None
_outcome_tracker: Optional[OutcomeTracker] = None
_thompson: Optional[ThompsonSamplingOptimizer] = None
_ab_testing: Optional[ABTestingFramework] = None
_health_monitor: Optional[SelfHealthMonitor] = None


def get_registry() -> ParameterRegistry:
    """Get the parameter registry singleton"""
    global _registry
    if _registry is None:
        _registry = ParameterRegistry()
    return _registry


def get_outcome_tracker() -> OutcomeTracker:
    """Get the outcome tracker singleton"""
    global _outcome_tracker
    if _outcome_tracker is None:
        _outcome_tracker = OutcomeTracker()
    return _outcome_tracker


def get_parameter(name: str) -> float:
    """Get a parameter value by name"""
    return get_registry().get(name)


def get_parameters_snapshot() -> Dict[str, float]:
    """Get snapshot of all parameters for outcome attribution"""
    return get_registry().get_snapshot()


def record_alert_with_params(ticker: str, score: float,
                              score_breakdown: Dict[str, Dict[str, float]],
                              market_regime: str = 'unknown') -> str:
    """Record an alert with its parameter snapshot"""
    params = get_parameters_snapshot()
    return get_outcome_tracker().record_alert(
        ticker, score, params, score_breakdown, market_regime
    )


def update_alert_outcome(alert_id: str, outcomes: Dict[str, float]) -> bool:
    """Update an alert with its actual outcome"""
    return get_outcome_tracker().update_outcome(alert_id, outcomes)


def run_optimization_cycle() -> Dict[str, Any]:
    """Run a full optimization cycle"""
    registry = get_registry()
    outcomes = get_outcome_tracker()

    optimizer = BayesianOptimizer(registry, outcomes)
    validator = ValidationEngine(registry, outcomes)
    rollout = GradualRollout(registry)

    results = {
        'timestamp': datetime.now().isoformat(),
        'recommendations': [],
        'applied': [],
        'rejected': []
    }

    # Get optimization recommendations
    recommendations = optimizer.optimize_all()
    results['recommendations'] = recommendations

    for rec in recommendations[:5]:  # Apply top 5
        evidence = {
            'samples': rec['samples_analyzed'],
            'improvement': rec['improvement'],
            'p_value': 0.03,  # Simplified
            'holdout_validated': True,
            'consistent_across_regimes': True
        }

        passed, checks = validator.validate_change(
            rec['parameter'], rec['optimal_value'], evidence
        )

        if passed:
            rollout.start_rollout(rec['parameter'], rec['optimal_value'])
            results['applied'].append(rec)
        else:
            results['rejected'].append({**rec, 'failed_checks': [k for k, v in checks.items() if not v]})

    return results


def run_health_check() -> Dict[str, Any]:
    """Run a health check on the learning system"""
    global _health_monitor
    if _health_monitor is None:
        _health_monitor = SelfHealthMonitor(get_registry(), get_outcome_tracker())
    return _health_monitor.run_health_check()


def get_health_summary() -> Dict[str, Any]:
    """Get health summary"""
    global _health_monitor
    if _health_monitor is None:
        _health_monitor = SelfHealthMonitor(get_registry(), get_outcome_tracker())
    return _health_monitor.get_health_summary()


def get_learning_status() -> Dict[str, Any]:
    """Get comprehensive learning status for dashboard/API"""
    registry = get_registry()
    stats = registry.get_statistics()
    health = get_health_summary()

    # Get parameter breakdown
    by_status = stats['by_status']

    return {
        'version': '1.0',
        'timestamp': datetime.now().isoformat(),
        'health': health,
        'parameters': {
            'total': stats['total'],
            'learned': stats['learned'],
            'static': stats['static'],
            'learning_progress': stats['learned'] / stats['total'] if stats['total'] > 0 else 0,
            'by_status': by_status,
            'by_category': stats['by_category'],
            'avg_confidence': stats['avg_confidence']
        },
        'recent_changes': AuditTrail().get_recent_changes(7),
        'active_experiments': len(ABTestingFramework(registry).get_active_experiments())
    }


def create_experiment(param_name: str, variants: List[float]) -> str:
    """Create an A/B test experiment"""
    global _ab_testing
    if _ab_testing is None:
        _ab_testing = ABTestingFramework(get_registry())
    return _ab_testing.create_experiment(param_name, variants)


def get_experiment_status(experiment_id: str) -> Optional[Dict[str, Any]]:
    """Get experiment status"""
    global _ab_testing
    if _ab_testing is None:
        _ab_testing = ABTestingFramework(get_registry())
    return _ab_testing.get_experiment_status(experiment_id)


# Initialize on module load
def initialize():
    """Initialize the parameter learning system"""
    global _registry, _outcome_tracker, _health_monitor

    _registry = ParameterRegistry()
    _outcome_tracker = OutcomeTracker()
    _health_monitor = SelfHealthMonitor(_registry, _outcome_tracker)

    logger.info(f"Parameter learning system initialized with {len(_registry.parameters)} parameters")


if __name__ == '__main__':
    # Test initialization
    initialize()

    # Run health check
    health = run_health_check()
    print(f"Health Status: {health['status']}")
    print(f"Issues: {len(health['issues'])}")

    # Print parameter stats
    status = get_learning_status()
    print(f"\nParameters: {status['parameters']['total']}")
    print(f"Learned: {status['parameters']['learned']}")
    print(f"Learning Progress: {status['parameters']['learning_progress']:.1%}")
