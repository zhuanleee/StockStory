"""
Path Configuration for Learning System

Defines all file paths for data storage.
"""
from pathlib import Path

# Data directory (created lazily to support read-only filesystems like Modal)
DATA_DIR = Path(__file__).parent.parent / 'parameter_data'


def _ensure_data_dir():
    """Ensure data directory exists (lazy initialization)"""
    DATA_DIR.mkdir(exist_ok=True)


# File paths
REGISTRY_FILE = DATA_DIR / 'parameter_registry.json'
OUTCOMES_FILE = DATA_DIR / 'outcome_history.json'
EXPERIMENTS_FILE = DATA_DIR / 'experiments.json'
AUDIT_FILE = DATA_DIR / 'audit_trail.json'
HEALTH_FILE = DATA_DIR / 'system_health.json'
