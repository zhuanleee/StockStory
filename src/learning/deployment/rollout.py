"""
Gradual Rollout - Staged Parameter Deployment

Gradually rolls out parameter changes to minimize risk.
"""
import logging
import random
from datetime import datetime
from typing import Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.registry import ParameterRegistry
    from ..tracking.audit import AuditTrail

logger = logging.getLogger('parameter_learning.rollout')


class GradualRollout:
    """
    Gradually rolls out parameter changes to minimize risk.
    Starts at 10% and increases if outcomes remain positive.
    """

    STAGES = [0.10, 0.25, 0.50, 0.75, 1.0]
    MIN_SAMPLES_PER_STAGE = 20

    def __init__(self, registry: 'ParameterRegistry'):
        self.registry = registry
        self.rollouts: Dict[str, Dict] = {}

    def start_rollout(self, param_name: str, new_value: float):
        """Start a gradual rollout"""
        param = self.registry.get_with_metadata(param_name)

        self.rollouts[param_name] = {
            'old_value': param.current_value,
            'new_value': new_value,
            'current_stage': 0,
            'stage_samples': 0,
            'stage_wins': 0,
            'started_at': datetime.now().isoformat()
        }

        param.status = 'validated'
        self.registry._save_registry()

        logger.info(f"Started gradual rollout for {param_name}: {param.current_value} -> {new_value}")

    def get_value(self, param_name: str, random_val: float = None) -> float:
        """Get the value to use, considering rollout percentage"""
        if param_name not in self.rollouts:
            return self.registry.get(param_name)

        rollout = self.rollouts[param_name]
        stage_pct = self.STAGES[rollout['current_stage']]

        # Use random value if not provided
        if random_val is None:
            random_val = random.random()

        if random_val < stage_pct:
            return rollout['new_value']
        else:
            return rollout['old_value']

    def record_outcome(self, param_name: str, used_new: bool, outcome: str):
        """Record an outcome during rollout"""
        if param_name not in self.rollouts:
            return

        rollout = self.rollouts[param_name]

        if used_new:
            rollout['stage_samples'] += 1
            if outcome == 'win':
                rollout['stage_wins'] += 1

        # Check if ready to advance stage
        if rollout['stage_samples'] >= self.MIN_SAMPLES_PER_STAGE:
            win_rate = rollout['stage_wins'] / rollout['stage_samples']

            if win_rate >= 0.45:  # Acceptable win rate
                if rollout['current_stage'] < len(self.STAGES) - 1:
                    rollout['current_stage'] += 1
                    rollout['stage_samples'] = 0
                    rollout['stage_wins'] = 0
                    logger.info(f"Advanced {param_name} rollout to stage {rollout['current_stage']} ({self.STAGES[rollout['current_stage']]:.0%})")
                else:
                    # Rollout complete
                    self._complete_rollout(param_name)
            else:
                # Rollback
                self._rollback(param_name)

    def _complete_rollout(self, param_name: str):
        """Complete a rollout and adopt the new value"""
        rollout = self.rollouts[param_name]

        self.registry.set(param_name, rollout['new_value'], 'gradual_rollout_complete')

        param = self.registry.get_with_metadata(param_name)
        param.status = 'deployed'
        self.registry._save_registry()

        del self.rollouts[param_name]

        logger.info(f"Completed rollout for {param_name}: now using {rollout['new_value']}")

    def _rollback(self, param_name: str):
        """Rollback a failed rollout"""
        rollout = self.rollouts[param_name]

        param = self.registry.get_with_metadata(param_name)
        param.status = 'rolled_back'
        self.registry._save_registry()

        # Import here to avoid circular dependency
        from ..tracking.audit import AuditTrail
        AuditTrail().log_change(param_name, rollout['new_value'], rollout['old_value'], 'rollback')

        del self.rollouts[param_name]

        logger.info(f"Rolled back {param_name} to {rollout['old_value']}")
