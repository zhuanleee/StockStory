"""
Self-Health Monitor - System Health Monitoring and Alerts

Monitors the health of the parameter learning system and detects issues.
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, TYPE_CHECKING

# Import from core
from ..core.paths import HEALTH_FILE, _ensure_data_dir

if TYPE_CHECKING:
    from ..core.registry import ParameterRegistry
    from ..tracking.outcomes import OutcomeTracker

logger = logging.getLogger('parameter_learning.health')


class SelfHealthMonitor:
    """
    Monitors the health of the parameter learning system.
    Detects issues and sends alerts.
    """

    def __init__(self, registry: 'ParameterRegistry', outcome_tracker: 'OutcomeTracker'):
        self.registry = registry
        self.outcomes = outcome_tracker
        self.health_history: List[Dict] = []
        self._load_health()

    def _load_health(self):
        """Load health history from disk"""
        if HEALTH_FILE.exists():
            try:
                with open(HEALTH_FILE, 'r') as f:
                    data = json.load(f)
                self.health_history = data.get('history', [])
            except Exception as e:
                logger.error(f"Failed to load health: {e}")

    def _save_health(self, health: Dict):
        """Save health check to disk"""
        _ensure_data_dir()
        self.health_history.append(health)
        # Keep last 1000 health checks
        self.health_history = self.health_history[-1000:]

        data = {
            'version': '1.0',
            'last_check': datetime.now().isoformat(),
            'history': self.health_history
        }
        with open(HEALTH_FILE, 'w') as f:
            json.dump(data, f)

    def run_health_check(self) -> Dict[str, Any]:
        """Run a comprehensive health check"""
        health = {
            'timestamp': datetime.now().isoformat(),
            'status': 'healthy',
            'issues': [],
            'metrics': {}
        }

        # 1. Check registry health
        registry_stats = self.registry.get_statistics()
        health['metrics']['total_parameters'] = registry_stats['total']
        health['metrics']['learned_parameters'] = registry_stats['learned']
        health['metrics']['learning_rate'] = registry_stats['learned'] / registry_stats['total'] if registry_stats['total'] > 0 else 0

        if registry_stats['learned'] < registry_stats['total'] * 0.1:
            health['issues'].append({
                'severity': 'warning',
                'message': f"Only {registry_stats['learned']}/{registry_stats['total']} parameters learned",
                'suggestion': 'Need more outcome data to learn parameters'
            })

        # 2. Check outcome collection
        recent_outcomes = self.outcomes.get_recent_outcomes(7)
        health['metrics']['outcomes_last_7d'] = len(recent_outcomes)

        if len(recent_outcomes) < 10:
            health['issues'].append({
                'severity': 'warning',
                'message': f"Only {len(recent_outcomes)} outcomes in last 7 days",
                'suggestion': 'Need more alerts with outcome tracking'
            })

        # 3. Check win rate
        if recent_outcomes:
            wins = sum(1 for o in recent_outcomes if o.outcome_class == 'win')
            win_rate = wins / len(recent_outcomes)
            health['metrics']['win_rate_7d'] = win_rate

            if win_rate < 0.4:
                health['issues'].append({
                    'severity': 'critical',
                    'message': f"Win rate is low: {win_rate:.1%}",
                    'suggestion': 'Review parameter values and consider rollback'
                })
                health['status'] = 'degraded'

        # 4. Check for stale parameters
        stale_count = 0
        for param in self.registry.parameters.values():
            if param.last_optimized:
                last_opt = datetime.fromisoformat(param.last_optimized)
                if datetime.now() - last_opt > timedelta(days=30):
                    stale_count += 1

        health['metrics']['stale_parameters'] = stale_count
        if stale_count > registry_stats['total'] * 0.5:
            health['issues'].append({
                'severity': 'info',
                'message': f"{stale_count} parameters haven't been optimized in 30+ days",
                'suggestion': 'Run optimization cycle'
            })

        # 5. Check confidence levels
        avg_confidence = registry_stats['avg_confidence']
        health['metrics']['avg_confidence'] = avg_confidence

        if avg_confidence < 0.3:
            health['issues'].append({
                'severity': 'info',
                'message': f"Average parameter confidence is low: {avg_confidence:.1%}",
                'suggestion': 'More data needed for confident learning'
            })

        # 6. Determine overall status
        critical_issues = [i for i in health['issues'] if i['severity'] == 'critical']
        if critical_issues:
            health['status'] = 'critical'
        elif len(health['issues']) > 3:
            health['status'] = 'degraded'

        self._save_health(health)

        return health

    def get_health_summary(self) -> Dict[str, Any]:
        """Get a summary of recent health checks"""
        if not self.health_history:
            return {'status': 'unknown', 'message': 'No health checks performed yet'}

        recent = self.health_history[-24:]  # Last 24 checks

        statuses = [h['status'] for h in recent]
        critical_count = statuses.count('critical')
        degraded_count = statuses.count('degraded')

        if critical_count > len(recent) * 0.3:
            overall = 'critical'
        elif degraded_count > len(recent) * 0.5:
            overall = 'degraded'
        else:
            overall = 'healthy'

        return {
            'overall_status': overall,
            'checks_performed': len(recent),
            'critical_count': critical_count,
            'degraded_count': degraded_count,
            'healthy_count': statuses.count('healthy'),
            'latest_metrics': self.health_history[-1].get('metrics', {}) if self.health_history else {}
        }
