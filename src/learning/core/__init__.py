"""
Core Learning System Components

Central types, registry, and path configuration.
"""

# Re-export types
from .types import (
    ParameterCategory,
    LearningStatus,
    ParameterDefinition,
    OutcomeRecord,
    Experiment,
)

# Re-export paths
from .paths import (
    DATA_DIR,
    REGISTRY_FILE,
    OUTCOMES_FILE,
    EXPERIMENTS_FILE,
    AUDIT_FILE,
    HEALTH_FILE,
    _ensure_data_dir,
)

__all__ = [
    # Types
    'ParameterCategory',
    'LearningStatus',
    'ParameterDefinition',
    'OutcomeRecord',
    'Experiment',
    # Paths
    'DATA_DIR',
    'REGISTRY_FILE',
    'OUTCOMES_FILE',
    'EXPERIMENTS_FILE',
    'AUDIT_FILE',
    'HEALTH_FILE',
    '_ensure_data_dir',
]
