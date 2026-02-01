"""
A/B Testing Framework - Controlled Parameter Experiments

Runs statistically rigorous A/B tests before adopting parameter changes.
"""
import json
import logging
import math
import random
import statistics
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any, TYPE_CHECKING
from dataclasses import asdict

# Import from core
from ..core.types import Experiment
from ..core.paths import EXPERIMENTS_FILE, _ensure_data_dir

if TYPE_CHECKING:
    from ..core.registry import ParameterRegistry

logger = logging.getLogger('parameter_learning.experiments')


class ABTestingFramework:
    """
    Framework for running controlled A/B tests on parameters.
    Ensures statistical rigor before adopting changes.
    """

    def __init__(self, registry: 'ParameterRegistry'):
        self.registry = registry
        self.experiments: Dict[str, Experiment] = {}
        self._load_experiments()

    def _load_experiments(self):
        """Load experiments from disk"""
        if EXPERIMENTS_FILE.exists():
            try:
                with open(EXPERIMENTS_FILE, 'r') as f:
                    data = json.load(f)
                for exp_data in data.get('experiments', []):
                    exp = Experiment(**exp_data)
                    self.experiments[exp.experiment_id] = exp
                logger.info(f"Loaded {len(self.experiments)} experiments")
            except Exception as e:
                logger.error(f"Failed to load experiments: {e}")

    def _save_experiments(self):
        """Save experiments to disk"""
        _ensure_data_dir()
        data = {
            'version': '1.0',
            'last_updated': datetime.now().isoformat(),
            'experiments': [asdict(exp) for exp in self.experiments.values()]
        }
        with open(EXPERIMENTS_FILE, 'w') as f:
            json.dump(data, f, indent=2)

    def create_experiment(self, param_name: str, variants: List[float],
                          min_samples: int = 100, duration_days: int = 14) -> str:
        """Create a new A/B test experiment"""
        param = self.registry.get_with_metadata(param_name)

        exp_id = f"exp_{param_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        experiment = Experiment(
            experiment_id=exp_id,
            parameter_name=param_name,
            variants=variants,
            control_value=param.current_value,
            start_time=datetime.now().isoformat(),
            end_time=None,
            status='running',
            min_samples_per_variant=min_samples // len(variants),
            assignments={},
            outcomes={i: [] for i in range(len(variants))}
        )

        self.experiments[exp_id] = experiment

        # Update parameter status
        param.status = 'experimenting'
        self.registry._save_registry()
        self._save_experiments()

        logger.info(f"Created experiment {exp_id} for {param_name} with variants {variants}")

        return exp_id

    def assign_variant(self, experiment_id: str, ticker: str) -> Tuple[int, float]:
        """Assign a ticker to a variant, return (variant_index, value)"""
        exp = self.experiments.get(experiment_id)
        if not exp or exp.status != 'running':
            return (0, self.registry.get(exp.parameter_name) if exp else 0)

        # Check if already assigned
        if ticker in exp.assignments:
            variant_idx = exp.assignments[ticker]
        else:
            # Random assignment
            variant_idx = random.randint(0, len(exp.variants) - 1)
            exp.assignments[ticker] = variant_idx
            self._save_experiments()

        return (variant_idx, exp.variants[variant_idx])

    def record_outcome(self, experiment_id: str, ticker: str, outcome_value: float):
        """Record an outcome for an experiment"""
        exp = self.experiments.get(experiment_id)
        if not exp or ticker not in exp.assignments:
            return

        variant_idx = exp.assignments[ticker]
        exp.outcomes[variant_idx].append(outcome_value)
        self._save_experiments()

        # Check if experiment can be concluded
        self._check_experiment_completion(experiment_id)

    def _check_experiment_completion(self, experiment_id: str):
        """Check if experiment has enough data to conclude"""
        exp = self.experiments.get(experiment_id)
        if not exp or exp.status != 'running':
            return

        # Check if all variants have minimum samples
        all_have_min = all(
            len(outcomes) >= exp.min_samples_per_variant
            for outcomes in exp.outcomes.values()
        )

        if not all_have_min:
            return

        # Perform statistical analysis
        self._analyze_experiment(experiment_id)

    def _analyze_experiment(self, experiment_id: str):
        """Analyze experiment results and determine winner"""
        exp = self.experiments.get(experiment_id)
        if not exp:
            return

        # Calculate mean outcome for each variant
        means = {}
        for variant_idx, outcomes in exp.outcomes.items():
            if outcomes:
                means[variant_idx] = statistics.mean(outcomes)

        if len(means) < 2:
            return

        # Find best variant
        best_variant = max(means, key=means.get)
        best_mean = means[best_variant]

        # Compare to control (variant 0)
        control_outcomes = exp.outcomes.get(0, [])
        best_outcomes = exp.outcomes.get(best_variant, [])

        if not control_outcomes or not best_outcomes:
            return

        # Simple t-test approximation
        control_mean = statistics.mean(control_outcomes)
        control_std = statistics.stdev(control_outcomes) if len(control_outcomes) > 1 else 1
        best_std = statistics.stdev(best_outcomes) if len(best_outcomes) > 1 else 1

        n1, n2 = len(control_outcomes), len(best_outcomes)
        pooled_se = math.sqrt(control_std**2/n1 + best_std**2/n2)
        t_stat = (best_mean - control_mean) / pooled_se if pooled_se > 0 else 0

        # Approximate p-value (two-tailed)
        # Using normal approximation for large samples
        from math import erf
        p_value = 2 * (1 - 0.5 * (1 + erf(abs(t_stat) / math.sqrt(2))))

        exp.p_value = p_value
        exp.improvement = (best_mean - control_mean) / abs(control_mean) if control_mean != 0 else 0

        if p_value < 0.05 and exp.improvement > 0.02:
            exp.winner = best_variant
            exp.status = 'completed'
            exp.end_time = datetime.now().isoformat()

            logger.info(f"Experiment {experiment_id} completed. Winner: variant {best_variant} "
                       f"with {exp.improvement:.1%} improvement (p={p_value:.4f})")

        self._save_experiments()

    def get_active_experiments(self) -> List[Experiment]:
        """Get all running experiments"""
        return [exp for exp in self.experiments.values() if exp.status == 'running']

    def get_experiment_status(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed status of an experiment"""
        exp = self.experiments.get(experiment_id)
        if not exp:
            return None

        variant_stats = {}
        for variant_idx, outcomes in exp.outcomes.items():
            if outcomes:
                variant_stats[variant_idx] = {
                    'value': exp.variants[variant_idx],
                    'samples': len(outcomes),
                    'mean': statistics.mean(outcomes),
                    'std': statistics.stdev(outcomes) if len(outcomes) > 1 else 0
                }

        return {
            'experiment_id': exp.experiment_id,
            'parameter': exp.parameter_name,
            'status': exp.status,
            'variants': exp.variants,
            'control_value': exp.control_value,
            'variant_stats': variant_stats,
            'total_samples': sum(len(o) for o in exp.outcomes.values()),
            'winner': exp.winner,
            'p_value': exp.p_value,
            'improvement': exp.improvement
        }
