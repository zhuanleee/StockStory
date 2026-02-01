"""
Shadow Mode - Test Parameters Without Affecting Live Alerts

Runs new parameter values in shadow mode to calculate hypothetical outcomes.
"""
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.registry import ParameterRegistry

logger = logging.getLogger('parameter_learning.shadow')


class ShadowMode:
    """
    Runs new parameter values in shadow mode before deployment.
    Calculates what outcomes WOULD have been without affecting live alerts.
    """

    def __init__(self, registry: 'ParameterRegistry'):
        self.registry = registry
        self.shadow_results: Dict[str, List[Dict]] = {}

    def add_to_shadow(self, param_name: str, shadow_value: float):
        """Add a parameter to shadow testing"""
        if param_name not in self.shadow_results:
            self.shadow_results[param_name] = []

        param = self.registry.get_with_metadata(param_name)
        param.status = 'shadow'
        self.registry._save_registry()

        logger.info(f"Added {param_name}={shadow_value} to shadow mode (current={param.current_value})")

    def record_shadow_outcome(self, param_name: str, shadow_value: float,
                              live_score: float, shadow_score: float,
                              outcome: str):
        """Record a shadow mode comparison"""
        if param_name not in self.shadow_results:
            self.shadow_results[param_name] = []

        self.shadow_results[param_name].append({
            'timestamp': datetime.now().isoformat(),
            'shadow_value': shadow_value,
            'live_score': live_score,
            'shadow_score': shadow_score,
            'outcome': outcome,
            'shadow_would_win': shadow_score > live_score and outcome == 'win'
        })

    def evaluate_shadow(self, param_name: str) -> Optional[Dict[str, Any]]:
        """Evaluate shadow mode results"""
        results = self.shadow_results.get(param_name, [])

        if len(results) < 50:
            return None

        shadow_wins = sum(1 for r in results if r['shadow_would_win'])
        live_wins = sum(1 for r in results if r['outcome'] == 'win')

        return {
            'parameter': param_name,
            'samples': len(results),
            'shadow_improvement': (shadow_wins - live_wins) / len(results),
            'ready_to_deploy': shadow_wins > live_wins * 1.05  # 5% better
        }
