"""
Outcome Tracking - Attribution of Alert Outcomes to Parameters

Tracks which parameter values lead to wins/losses for continuous learning.
"""
import json
import logging
import math
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
from collections import defaultdict
from dataclasses import asdict

# Import from core
from ..core.types import OutcomeRecord
from ..core.paths import OUTCOMES_FILE, _ensure_data_dir

# Lazy import to avoid circular dependency
def _get_registry():
    """Lazy import of ParameterRegistry"""
    from ..core.registry import ParameterRegistry
    return ParameterRegistry()


logger = logging.getLogger('parameter_learning.outcomes')


class OutcomeTracker:
    """
    Tracks alert outcomes and attributes them to parameter values.
    Essential for learning which parameters lead to wins/losses.
    """

    def __init__(self):
        self.outcomes: List[OutcomeRecord] = []
        self._load_outcomes()

    def _load_outcomes(self):
        """Load outcome history from disk"""
        if OUTCOMES_FILE.exists():
            try:
                with open(OUTCOMES_FILE, 'r') as f:
                    data = json.load(f)
                self.outcomes = [OutcomeRecord(**o) for o in data.get('outcomes', [])]
                logger.info(f"Loaded {len(self.outcomes)} outcome records")
            except Exception as e:
                logger.error(f"Failed to load outcomes: {e}")

    def _save_outcomes(self):
        """Save outcome history to disk"""
        _ensure_data_dir()
        # Keep last 10000 outcomes to prevent unbounded growth
        recent = self.outcomes[-10000:]
        data = {
            'version': '1.0',
            'last_updated': datetime.now().isoformat(),
            'total_outcomes': len(recent),
            'outcomes': [asdict(o) for o in recent]
        }
        with open(OUTCOMES_FILE, 'w') as f:
            json.dump(data, f)

    def record_alert(self, ticker: str, score: float, parameters_used: Dict[str, float],
                     score_breakdown: Dict[str, Dict[str, float]], market_regime: str) -> str:
        """Record an alert with its parameter snapshot. Returns alert_id."""
        alert_id = f"{ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        record = OutcomeRecord(
            alert_id=alert_id,
            ticker=ticker,
            timestamp=datetime.now().isoformat(),
            score=score,
            parameters_used=parameters_used,
            score_breakdown=score_breakdown,
            outcomes={},  # To be filled when outcomes are known
            outcome_class='pending',
            market_regime=market_regime
        )

        self.outcomes.append(record)
        self._save_outcomes()

        return alert_id

    def update_outcome(self, alert_id: str, outcomes: Dict[str, float]) -> bool:
        """Update an alert with its actual outcomes"""
        for record in self.outcomes:
            if record.alert_id == alert_id:
                record.outcomes = outcomes

                # Classify outcome based on 3-day return
                pct_3d = outcomes.get('3d', 0)
                registry = _get_registry()
                win_threshold = registry.get('outcome.win_threshold')
                loss_threshold = registry.get('outcome.loss_threshold')

                if pct_3d >= win_threshold:
                    record.outcome_class = 'win'
                elif pct_3d <= loss_threshold:
                    record.outcome_class = 'loss'
                else:
                    record.outcome_class = 'neutral'

                self._save_outcomes()
                return True

        return False

    def get_outcomes_for_parameter(self, param_name: str,
                                    min_date: datetime = None) -> List[Tuple[float, str]]:
        """Get all outcomes where a parameter was used, with its value"""
        results = []

        for record in self.outcomes:
            if record.outcome_class == 'pending':
                continue
            if min_date and datetime.fromisoformat(record.timestamp) < min_date:
                continue

            if param_name in record.parameters_used:
                value = record.parameters_used[param_name]
                results.append((value, record.outcome_class))

        return results

    def get_parameter_performance(self, param_name: str) -> Dict[str, Any]:
        """Calculate performance metrics for a parameter"""
        outcomes = self.get_outcomes_for_parameter(param_name)

        if not outcomes:
            return {'samples': 0, 'win_rate': None, 'confidence': 0}

        values_by_outcome = defaultdict(list)
        for value, outcome in outcomes:
            values_by_outcome[outcome].append(value)

        total = len(outcomes)
        wins = len(values_by_outcome['win'])
        losses = len(values_by_outcome['loss'])

        win_rate = wins / total if total > 0 else 0

        # Wilson score confidence interval
        if total > 0:
            z = 1.96  # 95% confidence
            p = win_rate
            n = total
            denominator = 1 + z**2 / n
            center = (p + z**2 / (2*n)) / denominator
            spread = z * math.sqrt((p*(1-p) + z**2/(4*n)) / n) / denominator
            ci_lower = max(0, center - spread)
            ci_upper = min(1, center + spread)
        else:
            ci_lower, ci_upper = 0, 1

        return {
            'samples': total,
            'wins': wins,
            'losses': losses,
            'neutral': total - wins - losses,
            'win_rate': win_rate,
            'confidence_interval': (ci_lower, ci_upper),
            'avg_value_wins': statistics.mean(values_by_outcome['win']) if values_by_outcome['win'] else None,
            'avg_value_losses': statistics.mean(values_by_outcome['loss']) if values_by_outcome['loss'] else None,
        }

    def get_recent_outcomes(self, days: int = 30) -> List[OutcomeRecord]:
        """Get outcomes from the last N days"""
        cutoff = datetime.now() - timedelta(days=days)
        return [o for o in self.outcomes
                if datetime.fromisoformat(o.timestamp) >= cutoff and o.outcome_class != 'pending']
