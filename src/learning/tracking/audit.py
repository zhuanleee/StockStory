"""
Audit Trail - Complete History of Parameter Changes

Maintains a complete audit log of all parameter modifications for debugging
and compliance.
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List

# Import from core
from ..core.paths import AUDIT_FILE

logger = logging.getLogger('parameter_learning.audit')


class AuditTrail:
    """
    Complete audit trail of all parameter changes.
    Essential for debugging and compliance.
    """

    def __init__(self):
        self.entries: List[Dict] = []
        self._load_audit()

    def _load_audit(self):
        """Load audit trail from disk"""
        if AUDIT_FILE.exists():
            try:
                with open(AUDIT_FILE, 'r') as f:
                    data = json.load(f)
                self.entries = data.get('entries', [])
            except Exception as e:
                logger.error(f"Failed to load audit trail: {e}")

    def _save_audit(self):
        """Save audit trail to disk"""
        # Keep last 10000 entries
        recent = self.entries[-10000:]

        data = {
            'version': '1.0',
            'last_updated': datetime.now().isoformat(),
            'total_entries': len(recent),
            'entries': recent
        }
        with open(AUDIT_FILE, 'w') as f:
            json.dump(data, f)

    def log_change(self, param_name: str, old_value: float, new_value: float,
                   reason: str, evidence: Dict = None):
        """Log a parameter change"""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'parameter': param_name,
            'old_value': old_value,
            'new_value': new_value,
            'change_pct': (new_value - old_value) / abs(old_value) if old_value != 0 else 0,
            'reason': reason,
            'evidence': evidence or {}
        }

        self.entries.append(entry)
        self._save_audit()

        logger.info(f"Audit: {param_name} changed from {old_value} to {new_value} ({reason})")

    def get_changes_for_parameter(self, param_name: str,
                                   days: int = None) -> List[Dict]:
        """Get change history for a parameter"""
        entries = [e for e in self.entries if e['parameter'] == param_name]

        if days:
            cutoff = datetime.now() - timedelta(days=days)
            entries = [e for e in entries
                      if datetime.fromisoformat(e['timestamp']) >= cutoff]

        return entries

    def get_recent_changes(self, days: int = 7) -> List[Dict]:
        """Get all recent changes"""
        cutoff = datetime.now() - timedelta(days=days)
        return [e for e in self.entries
                if datetime.fromisoformat(e['timestamp']) >= cutoff]
