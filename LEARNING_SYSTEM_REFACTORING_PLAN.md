# Learning System Refactoring Plan

**File:** `src/learning/parameter_learning.py`
**Current Size:** 74 KB, 1,756 lines
**Target:** Modular structure with ~120 KB total (multiple files)
**Risk Level:** High (many imports, complex dependencies)
**Estimated Time:** 8 hours
**Status:** Planned (not yet executed)

---

## Executive Summary

The parameter learning system is currently in a single 1,756-line file. While functional, this makes it hard to maintain and test. This plan outlines a safe, step-by-step refactoring into a modular structure.

**Recommendation:** Execute this refactoring during a maintenance window with comprehensive testing.

---

## Current Structure Analysis

### File Breakdown

| Section | Lines | Size | Description |
|---------|-------|------|-------------|
| **Imports & Setup** | 1-51 | 2 KB | Imports, logging, paths |
| **Core Types** | 52-130 | 3 KB | Enums, dataclasses |
| **ParameterRegistry** | 131-650 | 20 KB | Central parameter storage |
| **OutcomeTracker** | 651-795 | 6 KB | Outcome attribution |
| **Optimizers** | 796-919 | 5 KB | Thompson, Bayesian |
| **ABTestingFramework** | 920-1120 | 8 KB | Experiments |
| **Validation** | 1121-1194 | 3 KB | ValidationEngine |
| **Deployment** | 1195-1355 | 6 KB | Shadow, Rollout |
| **Monitoring** | 1356-1505 | 6 KB | Health checks |
| **AuditTrail** | 1506-1588 | 3 KB | Change history |
| **Public API** | 1589-1756 | 7 KB | Helper functions |

### Dependencies

```
parameter_learning.py
├── Used by: 15+ files
│   ├── src/scoring/param_helper.py (heavy usage)
│   ├── src/scoring/story_scorer.py
│   ├── src/core/async_scanner.py
│   ├── modal_api_v2.py (learning endpoints)
│   ├── telegram_bot.py
│   └── ...
│
└── Imports from:
    ├── Standard library only (json, math, random, etc.)
    └── No internal dependencies
```

**Import Pattern (everywhere):**
```python
from src.learning.parameter_learning import (
    get_registry,
    get_parameter,
    record_alert_with_params,
    update_alert_outcome
)
```

---

## Proposed Modular Structure

### New Directory Structure

```
src/learning/
├── __init__.py (public API re-exports)
├── parameter_learning.py (legacy, imports from submodules)
│
├── core/
│   ├── __init__.py
│   ├── types.py (Enums, dataclasses, ParameterCategory, LearningStatus)
│   ├── registry.py (ParameterRegistry class)
│   └── paths.py (DATA_DIR, file paths, _ensure_data_dir)
│
├── tracking/
│   ├── __init__.py
│   ├── outcomes.py (OutcomeTracker class)
│   └── audit.py (AuditTrail class)
│
├── optimization/
│   ├── __init__.py
│   ├── bayesian.py (BayesianOptimizer)
│   ├── thompson.py (ThompsonSamplingOptimizer)
│   └── experiments.py (ABTestingFramework)
│
├── deployment/
│   ├── __init__.py
│   ├── validation.py (ValidationEngine)
│   ├── shadow.py (ShadowMode)
│   └── rollout.py (GradualRollout)
│
└── monitoring/
    ├── __init__.py
    └── health.py (SelfHealthMonitor)
```

### File Sizes (After Split)

| File | Lines | Size | Description |
|------|-------|------|-------------|
| `core/types.py` | ~130 | 5 KB | Shared types |
| `core/registry.py` | ~520 | 20 KB | ParameterRegistry |
| `core/paths.py` | ~20 | 1 KB | Path configuration |
| `tracking/outcomes.py` | ~150 | 6 KB | OutcomeTracker |
| `tracking/audit.py` | ~90 | 3 KB | AuditTrail |
| `optimization/bayesian.py` | ~80 | 3 KB | BayesianOptimizer |
| `optimization/thompson.py` | ~60 | 2 KB | ThompsonSampling |
| `optimization/experiments.py` | ~210 | 8 KB | ABTesting |
| `deployment/validation.py` | ~80 | 3 KB | ValidationEngine |
| `deployment/shadow.py` | ~60 | 2 KB | ShadowMode |
| `deployment/rollout.py` | ~110 | 4 KB | GradualRollout |
| `monitoring/health.py` | ~160 | 6 KB | SelfHealthMonitor |
| `__init__.py` (public API) | ~50 | 2 KB | Re-exports |
| `parameter_learning.py` (legacy) | ~50 | 2 KB | Backwards compat |
| **Total** | **~1820** | **~70 KB** | Modular |

---

## Step-by-Step Migration Plan

### Phase 1: Preparation (1 hour)

**1.1. Create Backup**
```bash
cp src/learning/parameter_learning.py src/learning/parameter_learning.py.backup
git add -A && git commit -m "Backup before learning system refactor"
```

**1.2. Create Directory Structure**
```bash
mkdir -p src/learning/{core,tracking,optimization,deployment,monitoring}
touch src/learning/{core,tracking,optimization,deployment,monitoring}/__init__.py
```

**1.3. Run All Tests (Baseline)**
```bash
pytest tests/ -v > test_results_before.txt
```

### Phase 2: Extract Core Types (1 hour)

**2.1. Create `src/learning/core/types.py`**

Extract (lines 53-130):
- `ParameterCategory` enum
- `LearningStatus` enum
- `ParameterDefinition` dataclass
- `OutcomeRecord` dataclass
- `Experiment` dataclass

**2.2. Create `src/learning/core/paths.py`**

Extract (lines 39-51):
- `DATA_DIR` constant
- `_ensure_data_dir()` function
- All file path constants

**2.3. Update Imports**

In `parameter_learning.py`:
```python
from src.learning.core.types import (
    ParameterCategory,
    LearningStatus,
    ParameterDefinition,
    OutcomeRecord,
    Experiment
)
from src.learning.core.paths import (
    DATA_DIR,
    _ensure_data_dir,
    REGISTRY_FILE,
    OUTCOMES_FILE,
    EXPERIMENTS_FILE,
    AUDIT_FILE,
    HEALTH_FILE
)
```

**2.4. Test**
```bash
python -c "from src.learning.parameter_learning import get_registry; print(get_registry())"
pytest tests/test_parameter_learning.py
```

### Phase 3: Extract ParameterRegistry (1.5 hours)

**3.1. Create `src/learning/core/registry.py`**

Extract (lines 132-650):
- Complete `ParameterRegistry` class (~520 lines)

**3.2. Add Imports at Top**
```python
import json
import logging
from typing import Dict, List, Optional
from pathlib import Path
from .types import ParameterDefinition, ParameterCategory, LearningStatus
from .paths import REGISTRY_FILE, _ensure_data_dir

logger = logging.getLogger(__name__)
```

**3.3. Update `parameter_learning.py`**
```python
from src.learning.core.registry import ParameterRegistry
```

**3.4. Test Registry Independently**
```python
# Test script
from src.learning.core.registry import ParameterRegistry

registry = ParameterRegistry()
registry.register_parameter(
    name="test_param",
    default_value=0.5,
    min_value=0.0,
    max_value=1.0,
    category="threshold",
    description="Test",
    source_file="test.py",
    source_line=1
)
print(registry.get_parameter("test_param"))
```

### Phase 4: Extract Tracking Components (1 hour)

**4.1. Create `src/learning/tracking/outcomes.py`**

Extract (lines 651-795):
- `OutcomeTracker` class

Dependencies:
```python
from ..core.types import OutcomeRecord, ParameterDefinition
from ..core.paths import OUTCOMES_FILE, _ensure_data_dir
from ..core.registry import ParameterRegistry
```

**4.2. Create `src/learning/tracking/audit.py`**

Extract (lines 1506-1588):
- `AuditTrail` class

**4.3. Update `parameter_learning.py`**
```python
from src.learning.tracking.outcomes import OutcomeTracker
from src.learning.tracking.audit import AuditTrail
```

### Phase 5: Extract Optimizers (1 hour)

**5.1. Create `src/learning/optimization/thompson.py`**

Extract (lines 796-849):
- `ThompsonSamplingOptimizer` class

**5.2. Create `src/learning/optimization/bayesian.py`**

Extract (lines 850-919):
- `BayesianOptimizer` class

**5.3. Create `src/learning/optimization/experiments.py`**

Extract (lines 920-1120):
- `ABTestingFramework` class

**5.4. Update Imports**

Each optimizer needs:
```python
from ..core.types import ParameterDefinition, Experiment
from ..core.registry import ParameterRegistry
from ..tracking.outcomes import OutcomeTracker
```

### Phase 6: Extract Deployment Components (1 hour)

**6.1. Create `src/learning/deployment/validation.py`**

Extract (lines 1121-1194):
- `ValidationEngine` class

**6.2. Create `src/learning/deployment/shadow.py`**

Extract (lines 1195-1249):
- `ShadowMode` class

**6.3. Create `src/learning/deployment/rollout.py`**

Extract (lines 1250-1355):
- `GradualRollout` class

### Phase 7: Extract Monitoring (30 minutes)

**7.1. Create `src/learning/monitoring/health.py`**

Extract (lines 1356-1505):
- `SelfHealthMonitor` class

Dependencies:
```python
from ..core.registry import ParameterRegistry
from ..tracking.outcomes import OutcomeTracker
from ..core.paths import HEALTH_FILE
```

### Phase 8: Create Public API (30 minutes)

**8.1. Update `src/learning/__init__.py`**

Re-export all public functions:
```python
"""
Learning System Public API

Provides a stable interface to the parameter learning system.
Internal structure is modular but external interface remains simple.
"""

# Core
from .core.registry import ParameterRegistry
from .core.types import (
    ParameterCategory,
    LearningStatus,
    ParameterDefinition,
    OutcomeRecord,
    Experiment
)

# Tracking
from .tracking.outcomes import OutcomeTracker
from .tracking.audit import AuditTrail

# Optimization
from .optimization.bayesian import BayesianOptimizer
from .optimization.thompson import ThompsonSamplingOptimizer
from .optimization.experiments import ABTestingFramework

# Deployment
from .deployment.validation import ValidationEngine
from .deployment.shadow import ShadowMode
from .deployment.rollout import GradualRollout

# Monitoring
from .monitoring.health import SelfHealthMonitor

# Singleton instances
_registry = None
_outcome_tracker = None

def get_registry() -> ParameterRegistry:
    """Get global ParameterRegistry instance"""
    global _registry
    if _registry is None:
        _registry = ParameterRegistry()
    return _registry

def get_outcome_tracker() -> OutcomeTracker:
    """Get global OutcomeTracker instance"""
    global _outcome_tracker
    if _outcome_tracker is None:
        _outcome_tracker = OutcomeTracker(get_registry())
    return _outcome_tracker

def get_parameter(name: str) -> float:
    """Get current value of a parameter"""
    return get_registry().get_parameter(name)

def get_parameters_snapshot() -> Dict[str, float]:
    """Get snapshot of all parameters"""
    return get_registry().get_parameters_snapshot()

# ... (all other public helper functions)

__all__ = [
    # Core types
    'ParameterCategory',
    'LearningStatus',
    'ParameterDefinition',
    # ... (list all exports)
]
```

**8.2. Create Backwards-Compatible `parameter_learning.py`**

Replace entire file with:
```python
"""
Legacy parameter_learning.py - Backwards Compatibility Wrapper

This file maintains backwards compatibility by re-exporting from the new modular structure.
All functionality has been moved to submodules under src/learning/

Deprecated: Import from src.learning instead
"""

import warnings
warnings.warn(
    "Importing from parameter_learning.py directly is deprecated. "
    "Use 'from src.learning import ...' instead.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export everything from new structure
from src.learning import *

# This maintains 100% backwards compatibility
# Old code: from src.learning.parameter_learning import get_registry
# New code: from src.learning import get_registry
# Both work!
```

### Phase 9: Testing & Validation (1.5 hours)

**9.1. Run Full Test Suite**
```bash
pytest tests/ -v > test_results_after.txt
diff test_results_before.txt test_results_after.txt
```

**9.2. Integration Tests**

Test all import patterns:
```python
# Pattern 1: New imports (preferred)
from src.learning import get_registry, get_parameter

# Pattern 2: Old imports (deprecated but working)
from src.learning.parameter_learning import get_registry

# Pattern 3: Direct module imports
from src.learning.core.registry import ParameterRegistry

# All three should work!
```

**9.3. Load Test**

Run scanner with learning enabled:
```bash
python -m src.core.async_scanner --mode daily
```

**9.4. Verify Data Persistence**

Check all data files are created correctly:
```bash
ls -lh src/learning/parameter_data/
# Should see: parameter_registry.json, outcome_history.json, etc.
```

### Phase 10: Deployment (30 minutes)

**10.1. Commit Changes**
```bash
git add src/learning/
git commit -m "Refactor learning system into modular structure

- Split 1756-line file into 13 focused modules
- Maintained 100% backwards compatibility
- Added deprecation warnings for old imports
- All tests passing

Modules:
- core/ (types, registry, paths)
- tracking/ (outcomes, audit)
- optimization/ (bayesian, thompson, experiments)
- deployment/ (validation, shadow, rollout)
- monitoring/ (health)
"
```

**10.2. Deploy to Modal**
```bash
modal deploy modal_api_v2.py
modal deploy modal_scanner.py
```

**10.3. Monitor**

Check logs for any import errors:
```bash
modal app logs stock-scanner-api-v2 --follow
```

---

## Backwards Compatibility Strategy

### Option 1: Deprecation Warnings (Recommended)

Keep `parameter_learning.py` as a thin wrapper with warnings:
```python
# parameter_learning.py
import warnings
warnings.warn("Import from src.learning instead", DeprecationWarning)
from src.learning import *
```

**Pros:**
- 100% backwards compatible
- Encourages migration to new imports
- Can remove wrapper in 3-6 months

**Cons:**
- Extra layer of indirection

### Option 2: Direct Migration

Delete `parameter_learning.py` and update all imports immediately.

**Pros:**
- Clean break, no technical debt
- Forces adoption of new structure

**Cons:**
- Requires updating 15+ files simultaneously
- Higher risk of missing an import

**Recommendation:** Use Option 1 (deprecation warnings) for safety.

---

## Risk Mitigation

### Risk 1: Import Breakage

**Mitigation:**
- Keep `parameter_learning.py` as backwards-compatible wrapper
- Add deprecation warnings, don't break immediately
- Test all known import locations

### Risk 2: Circular Dependencies

**Problem:** Module A imports B, B imports A

**Mitigation:**
- Careful dependency ordering (types → paths → registry → everything else)
- Use `from typing import TYPE_CHECKING` for type hints only
- Move shared types to `core/types.py`

### Risk 3: Data File Conflicts

**Problem:** Multiple modules trying to write same JSON files

**Mitigation:**
- All file I/O stays in the class that owns it
- Registry owns REGISTRY_FILE
- OutcomeTracker owns OUTCOMES_FILE
- No shared writes

### Risk 4: Modal Deployment Issues

**Problem:** Modal image doesn't include new files

**Mitigation:**
- Modal `.add_local_dir("src")` includes all subdirectories
- Test deployment to Modal staging first
- Keep backwards-compatible wrapper as fallback

---

## Testing Checklist

Before merging:

- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Old imports still work (via wrapper)
- [ ] New imports work
- [ ] Data files created in correct locations
- [ ] No circular import errors
- [ ] Scanner runs successfully
- [ ] Learning endpoints return data
- [ ] Parameter updates persist
- [ ] Audit trail records changes
- [ ] Health checks pass
- [ ] Modal deployment successful
- [ ] No runtime errors in logs

---

## Rollback Plan

If something goes wrong:

**1. Immediate Rollback**
```bash
git revert HEAD
modal deploy modal_api_v2.py
modal deploy modal_scanner.py
```

**2. Restore Backup**
```bash
cp src/learning/parameter_learning.py.backup src/learning/parameter_learning.py
rm -rf src/learning/{core,tracking,optimization,deployment,monitoring}
git add -A && git commit -m "Rollback learning system refactor"
```

**3. Investigate**
- Check logs for specific error
- Identify which import failed
- Fix issue in isolated branch
- Re-test before re-deploying

---

## Success Metrics

**Code Quality:**
- ✅ File size: 1756 lines → ~120 lines per file (avg)
- ✅ Max file size: 520 lines (ParameterRegistry)
- ✅ Modularity: 10 components in separate files
- ✅ Testability: Each module can be unit tested independently

**Backwards Compatibility:**
- ✅ All existing imports work
- ✅ All existing code runs unchanged
- ✅ Deprecation warnings guide migration

**Maintainability:**
- ✅ Clear separation of concerns
- ✅ Easy to find specific component
- ✅ Reduced cognitive load
- ✅ Better for onboarding new developers

---

## Post-Refactoring Tasks

After successful refactor:

**1. Update Documentation**
- Update import examples in README
- Document new module structure
- Add migration guide for users

**2. Update All Imports (Gradual)**

Find and replace across codebase:
```bash
grep -r "from src.learning.parameter_learning import" src/
# Update each file to use new imports
```

**3. Remove Deprecation Wrapper (3-6 months)**

Once all code uses new imports:
```bash
rm src/learning/parameter_learning.py
```

**4. Add Module-Specific Tests**

Create tests for each new module:
```bash
tests/
└── learning/
    ├── test_core_registry.py
    ├── test_tracking_outcomes.py
    ├── test_optimization_bayesian.py
    └── ...
```

---

## Alternative: Minimal Refactoring

If 8 hours is too much, consider a minimal approach:

**Extract Only the Largest Classes:**

1. Extract `ParameterRegistry` (520 lines) → `registry.py`
2. Extract `ABTestingFramework` (200 lines) → `experiments.py`
3. Extract `SelfHealthMonitor` (150 lines) → `health.py`

**Time:** 2 hours
**Reduction:** 870 lines → 886 lines remaining (50% reduction)
**Risk:** Lower (fewer changes)

**Structure:**
```
src/learning/
├── parameter_learning.py (886 lines - optimizers, tracking, deployment)
├── registry.py (520 lines - ParameterRegistry)
├── experiments.py (200 lines - ABTestingFramework)
└── health.py (150 lines - SelfHealthMonitor)
```

This gives you most of the benefits with half the work and risk.

---

## Recommendation

**Approach:** Full modular refactoring (Phase 1-10)
**Timeline:** 8 hours over 1-2 days
**Timing:** Execute during low-traffic period with rollback plan ready
**Testing:** Comprehensive (all phases include testing)

**Why Full Refactor:**
- Better long-term maintainability
- Enables independent module testing
- Easier onboarding for new developers
- Clearer separation of concerns
- Worth the one-time investment

**Why Not Minimal:**
- Technical debt remains
- Will need to refactor again later
- Missed opportunity for clean architecture

---

**Document Status:** Ready for execution
**Risk Level:** Manageable with proper testing
**Recommendation:** ✅ Proceed with full refactor during maintenance window

**Last Updated:** February 1, 2026
