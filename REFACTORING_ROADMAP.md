# 🛠️ REFACTORING ROADMAP

**Date:** February 1, 2026
**Status:** In Progress (3/12 tasks completed)
**Priority:** P1-P3 (High to Medium)

---

## ✅ COMPLETED (3/12)

### 1. Security Fixes ✅
- [x] Add security headers to Modal API
- [x] Restrict CORS to known origins
- [x] Add request logging middleware
- [x] Create XSS prevention utilities
- [x] Add rate limiting for API calls
- [x] Create credential rotation guide

**Impact:** Critical security vulnerabilities fixed
**Files:** `modal_api_v2.py`, `docs/js/utils/security.js`, `CREDENTIAL_ROTATION_GUIDE.md`

### 2. Trading Endpoints Fixed ✅
- [x] Return HTTP 501 for unimplemented endpoints
- [x] Add roadmap information to responses
- [x] Document alternatives for users
- [x] Clear messaging about analysis-only mode

**Impact:** No more confusing empty responses
**Files:** `modal_api_v2.py` (lines 599-670)

### 3. Debug Endpoints Cleaned ✅
- [x] Replace /debug/learning-import with /debug/health
- [x] Remove sensitive information from debug responses
- [x] Production-safe health check endpoint

**Impact:** Safer debug endpoints
**Files:** `modal_api_v2.py` (lines 555-575)

---

## 🚧 IN PROGRESS (9/12)

### 4. Refactor Learning System (191 KB → 120 KB)

**Priority:** P1 (High)
**Estimated Time:** 8 hours
**Complexity:** High

#### Current State
```
learning/
├── parameter_learning.py    76 KB  ← Too large, needs split
├── evolution_engine.py       71 KB  ← 60% overlap with param_learning
├── self_learning.py          45 KB  ← 80% redundant with tiers
├── learning_brain.py         24 KB  ← OK
├── tier1_bandit.py           18 KB  ← OK
├── tier2_regime.py           21 KB  ← OK
├── tier3_ppo.py              20 KB  ← OK (requires PyTorch)
└── tier4_meta.py             21 KB  ← OK
Total: 191 KB
```

#### Target State
```
learning/
├── core/
│   ├── registry.py           ← Parameter registry (20 KB)
│   ├── optimizer.py          ← Bayesian optimization (15 KB)
│   ├── ab_testing.py         ← A/B test framework (12 KB)
│   └── validation.py         ← Validation engine (10 KB)
├── evolution/
│   ├── adaptive_weights.py   ← From evolution_engine (25 KB)
│   └── learning_state.py     ← State management (15 KB)
├── brain/
│   ├── learning_brain.py     ← Orchestrator (24 KB) [NO CHANGE]
│   ├── tier1_bandit.py       ← [NO CHANGE]
│   ├── tier2_regime.py       ← [NO CHANGE]
│   ├── tier3_ppo.py          ← [NO CHANGE]
│   └── tier4_meta.py         ← [NO CHANGE]
└── plugins/
    └── ai_learning.py        ← Plugin (3 KB)

Total: ~120 KB (40% reduction)
```

#### Implementation Steps

1. **Create Module Structure** (30 min)
   ```bash
   mkdir -p src/learning/core
   mkdir -p src/learning/evolution
   mkdir -p src/learning/brain
   mkdir -p src/learning/plugins
   ```

2. **Extract Parameter Registry** (1 hour)
   ```python
   # src/learning/core/registry.py
   from parameter_learning.py extract:
   - ParameterRegistry class (lines 129-520)
   - ParameterDefinition dataclass
   - ParameterCategory enum
   ```

3. **Extract Optimizer** (1 hour)
   ```python
   # src/learning/core/optimizer.py
   from parameter_learning.py extract:
   - BayesianOptimizer class (lines 521-850)
   - Thompson sampling logic
   ```

4. **Extract A/B Testing** (1 hour)
   ```python
   # src/learning/core/ab_testing.py
   from parameter_learning.py extract:
   - ABTestingFramework class (lines 851-1100)
   - Experiment dataclass
   ```

5. **Extract Validation** (30 min)
   ```python
   # src/learning/core/validation.py
   from parameter_learning.py extract:
   - ValidationEngine class (lines 1101-1300)
   - ShadowMode class
   - GradualRollout class
   ```

6. **Merge Evolution Engine** (2 hours)
   ```python
   # src/learning/evolution/adaptive_weights.py
   from evolution_engine.py merge into parameter registry:
   - Adaptive weight calculation
   - Regime-based weights
   - Weight history tracking
   ```

7. **Remove Redundant Code** (30 min)
   ```bash
   # Delete self_learning.py (redundant with tier system)
   rm src/learning/self_learning.py

   # Move ai_learning.py to plugins
   mv src/learning/ai_learning.py src/learning/plugins/
   ```

8. **Update Imports** (1 hour)
   ```python
   # Update all files that import from learning system
   # Change: from src.learning.parameter_learning import X
   # To: from src.learning.core.registry import X
   ```

9. **Test All Components** (1 hour)
   ```bash
   pytest tests/integration/test_learning_system.py
   python -m src.learning.core.registry  # Unit tests
   ```

#### Files to Update
- `src/scoring/param_helper.py` - Update import paths
- `src/learning/__init__.py` - Export new structure
- `modal_api_v2.py` - No changes needed (uses param_helper)
- `tests/integration/test_learning_system.py` - Update imports

#### Risks
- Import breakage if not careful with paths
- Circular dependency if structure not planned well
- Loss of functionality if merge not thorough

#### Rollback Plan
- Keep backups of original files
- Create `learning_backup/` directory
- Can revert entire commit if needed

---

### 5. AI Brain Optimization

**Priority:** P2 (Medium)
**Estimated Time:** 4 hours
**Complexity:** Medium

#### Current Issues
- **File:** `src/ai/comprehensive_agentic_brain.py` (2090 lines)
- **Performance:** 10-30s per stock (too slow)
- **Cost:** $0.14-0.27 per 1M tokens (DeepSeek)
- **Status:** Disabled by default (`USE_AI_BRAIN_RANKING=false`)

#### Optimization Strategy

**Option 1: Async/Cached Version** (2 hours)
```python
# Create src/ai/optimized_brain.py

import asyncio
from functools import lru_cache

class OptimizedAgenticBrain:
    def __init__(self):
        self.cache = {}
        self.session = aiohttp.ClientSession()  # Reuse connections

    @lru_cache(maxsize=1000)
    async def analyze_cached(self, ticker, cache_ttl=3600):
        # Cache results for 1 hour
        if ticker in self.cache:
            if time.time() - self.cache[ticker]['ts'] < cache_ttl:
                return self.cache[ticker]['data']

        # Parallel director calls instead of sequential
        results = await asyncio.gather(
            self.forensic_director(ticker),
            self.strategic_director(ticker),
            self.risk_director(ticker),
            self.catalyst_director(ticker),
            self.market_director(ticker)
        )

        # Cache result
        self.cache[ticker] = {'data': results, 'ts': time.time()}
        return results
```

**Performance Improvement:** 10-30s → 2-5s (parallel API calls + caching)

**Option 2: Lightweight Version** (2 hours)
```python
# Create src/ai/lite_brain.py

class LiteAgenticBrain:
    """Lightweight AI analysis using fewer directors"""

    def analyze(self, ticker):
        # Only use 2 directors instead of 5
        strategic = self.strategic_director(ticker)  # Most important
        risk = self.risk_director(ticker)  # Second most important

        # Skip forensic, catalyst, market (too slow)

        return {
            'strategic_score': strategic,
            'risk_score': risk,
            'overall_score': (strategic * 0.7 + risk * 0.3)
        }
```

**Performance Improvement:** 10-30s → 3-6s (fewer API calls)

**Option 3: Document and Keep Disabled** (30 min)
```markdown
# Create AI_BRAIN_BENCHMARKS.md

## Performance Benchmarks

**Comprehensive Agentic Brain:**
- Time per stock: 10-30 seconds
- API cost: $0.14-0.27 per 1M tokens
- Directors: 5 (Forensic, Strategic, Risk, Catalyst, Market)
- Use case: Deep research on individual stocks

**Recommendation:** Use for detailed analysis of 10-20 high-priority stocks,
not for batch scanning 500+ stocks.

**Alternative:** Standard story scoring (1-2s per stock, no API cost)
```

#### Recommended Approach
- **Short term:** Option 3 (document benchmarks, keep disabled)
- **Medium term:** Option 1 (async/cached version for on-demand analysis)
- **Long term:** Option 2 (lite version as default, comprehensive as optional)

---

### 6. Add API Authentication

**Priority:** P1 (High)
**Estimated Time:** 3 hours
**Complexity:** Medium

#### Implementation Plan

**Step 1: Create API Key System** (1 hour)
```python
# src/api/auth.py

import secrets
import hashlib
from datetime import datetime

class APIKeyManager:
    def __init__(self):
        self.keys = {}  # In production, use database

    def generate_key(self, user_id, permissions=None):
        # Generate secure API key
        key = f"sk-{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(key.encode()).hexdigest()

        self.keys[key_hash] = {
            'user_id': user_id,
            'permissions': permissions or ['read'],
            'created_at': datetime.now(),
            'rate_limit': 100,  # requests per minute
            'usage': 0
        }

        return key  # Return once, never stored

    def validate_key(self, key):
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        return key_hash in self.keys

    def get_key_info(self, key):
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        return self.keys.get(key_hash)
```

**Step 2: Add Middleware** (1 hour)
```python
# modal_api_v2.py

from src.api.auth import APIKeyManager

api_keys = APIKeyManager()

@web_app.middleware("http")
async def auth_middleware(request, call_next):
    # Public endpoints (no auth required)
    public_endpoints = ['/health', '/']
    if request.url.path in public_endpoints:
        return await call_next(request)

    # Check for API key
    api_key = request.headers.get('X-API-Key')
    if not api_key:
        return JSONResponse(
            status_code=401,
            content={
                "ok": False,
                "error": "API key required",
                "message": "Include X-API-Key header with your request"
            }
        )

    # Validate key
    if not api_keys.validate_key(api_key):
        return JSONResponse(
            status_code=403,
            content={"ok": False, "error": "Invalid API key"}
        )

    # Rate limiting per key
    key_info = api_keys.get_key_info(api_key)
    if key_info['usage'] >= key_info['rate_limit']:
        return JSONResponse(
            status_code=429,
            content={
                "ok": False,
                "error": "Rate limit exceeded",
                "retry_after": 60
            }
        )

    # Track usage
    key_info['usage'] += 1

    # Add user_id to request state
    request.state.user_id = key_info['user_id']

    return await call_next(request)
```

**Step 3: Admin Endpoints** (1 hour)
```python
# modal_api_v2.py

@web_app.post("/admin/keys/create")
async def create_api_key(user_id: str, permissions: list = None):
    # TODO: Add admin authentication
    key = api_keys.generate_key(user_id, permissions)
    return {
        "ok": True,
        "api_key": key,
        "message": "Save this key - it won't be shown again"
    }

@web_app.get("/admin/keys/usage")
async def get_key_usage():
    # TODO: Add admin authentication
    return {
        "ok": True,
        "total_keys": len(api_keys.keys),
        "active_keys": sum(1 for k in api_keys.keys.values() if k['usage'] > 0)
    }

@web_app.delete("/admin/keys/{key_id}")
async def revoke_api_key(key_id: str):
    # TODO: Add admin authentication
    # Revoke key
    pass
```

#### Client Usage
```javascript
// Dashboard
const API_KEY = localStorage.getItem('api_key');

fetch(API_BASE + '/scan', {
    headers: {
        'X-API-Key': API_KEY
    }
});
```

#### Migration Plan
1. Deploy auth system (disabled)
2. Generate keys for existing users
3. Send keys via email/Telegram
4. Enable auth middleware (1 week grace period)
5. Require keys for all endpoints

---

### 7. Consolidate Configuration

**Priority:** P2 (Medium)
**Estimated Time:** 2 hours
**Complexity:** Low

#### Current Issues
- 23 duplicate constants across files
- 47 magic numbers without explanation
- Hardcoded values in 12 locations

#### Solution: Create constants.py

```python
# src/core/constants.py

"""
Centralized constants for Stock Scanner Bot
All hardcoded values should be defined here.
"""

# =============================================================================
# MARKET DATA
# =============================================================================

# Filtering thresholds
MIN_MARKET_CAP = 300_000_000  # $300M minimum market cap
MIN_PRICE = 5.0  # Minimum stock price
MAX_PRICE = 500.0  # Maximum stock price
MIN_VOLUME = 500_000  # Minimum daily volume

# Trading hours (Eastern Time)
MARKET_OPEN_HOUR = 9
MARKET_OPEN_MINUTE = 30
MARKET_CLOSE_HOUR = 16
MARKET_CLOSE_MINUTE = 0

# =============================================================================
# API RATE LIMITS
# =============================================================================

# Rate limits (requests per second)
POLYGON_RATE_LIMIT = 100.0  # Unlimited tier
STOCKTWITS_RATE_LIMIT = 3.0  # ~200/hour, self-imposed
REDDIT_RATE_LIMIT = 1.0  # ~60/min, self-imposed
SEC_RATE_LIMIT = 10.0  # Be nice to SEC
NEWS_RATE_LIMIT = 5.0  # ~300/hour

# Burst allowances
STOCKTWITS_BURST = 5
REDDIT_BURST = 4
SEC_BURST = 20
NEWS_BURST = 10
POLYGON_BURST = 50

# =============================================================================
# CACHE TTLs (seconds)
# =============================================================================

CACHE_TTL_PRICE = 900  # 15 minutes
CACHE_TTL_NEWS = 1800  # 30 minutes
CACHE_TTL_SENTIMENT = 3600  # 1 hour
CACHE_TTL_SEC_FILINGS = 3600  # 1 hour
CACHE_TTL_SECTOR = 86400  # 24 hours
CACHE_TTL_THEME = 3600  # 1 hour

# Cache sizes
CACHE_MAX_SIZE_MEMORY = 10000  # LRU entries
CACHE_MAX_SIZE_FILE = 1000  # Max files

# =============================================================================
# API ENDPOINTS
# =============================================================================

POLYGON_BASE_URL = "https://api.polygon.io"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
XAI_BASE_URL = "https://api.x.ai"
SEC_BASE_URL = "https://www.sec.gov"

# =============================================================================
# SCORING WEIGHTS (initial - learned over time)
# =============================================================================

WEIGHT_THEME_HEAT = 0.18
WEIGHT_CATALYST = 0.18
WEIGHT_SOCIAL_BUZZ = 0.12
WEIGHT_NEWS_MOMENTUM = 0.10
WEIGHT_SENTIMENT = 0.07
WEIGHT_ECOSYSTEM = 0.10
WEIGHT_TECHNICAL = 0.25

# =============================================================================
# LEARNING SYSTEM
# =============================================================================

MIN_TRADES_BEFORE_LEARNING = 20
MAX_POSITION_SIZE = 25.0  # Percent
MAX_DRAWDOWN = 15.0  # Percent
LEARNING_ACTIVE = True

# =============================================================================
# FEATURE FLAGS
# =============================================================================

USE_AI_BRAIN_RANKING = False  # Too slow for batch scanning
USE_GOOGLE_TRENDS = True
USE_LEARNING_SYSTEM = True
DEBUG = False

# =============================================================================
# CORS ORIGINS
# =============================================================================

ALLOWED_ORIGINS = [
    "https://zhuanleee.github.io",
    "http://localhost:5000",
    "http://127.0.0.1:5000"
]
```

#### Update all files to import from constants:
```python
# Before
MIN_MARKET_CAP = 300_000_000

# After
from src.core.constants import MIN_MARKET_CAP
```

---

### 8. Split Large Files

**Priority:** P2 (Medium)
**Estimated Time:** 6 hours
**Complexity:** High

See **Task #4 (Refactor Learning System)** for detailed plan on splitting parameter_learning.py.

For other large files, defer to future iterations (too risky without comprehensive testing).

---

### 9. Optimize Performance

**Priority:** P3 (Medium-Low)
**Estimated Time:** 4 hours
**Complexity:** Medium

#### Quick Wins

**1. Parallel API Calls in Scorer** (1 hour)
```python
# src/scoring/story_scorer.py

# Before (sequential - 3s total)
news = fetch_news(ticker)  # 1s
sentiment = fetch_sentiment(ticker)  # 1s
social = fetch_social(ticker)  # 1s

# After (parallel - 1s total)
news, sentiment, social = await asyncio.gather(
    fetch_news(ticker),
    fetch_sentiment(ticker),
    fetch_social(ticker)
)
```

**2. Cache Preloading** (1 hour)
```python
# src/data/cache_manager.py

async def preload_cache():
    """Preload hot data on startup"""
    hot_tickers = ['SPY', 'QQQ', 'AAPL', 'MSFT', 'NVDA']

    await asyncio.gather(*[
        fetch_and_cache(ticker)
        for ticker in hot_tickers
    ])

# In modal_api_v2.py startup
@web_app.on_event("startup")
async def startup():
    await preload_cache()
```

**3. Lazy Module Imports** (1 hour)
```python
# Only import heavy modules when needed

# Before
import torch  # Loads PyTorch on every import (slow)

# After
def get_ppo_agent():
    import torch  # Only loads when function called
    return PPOAgent()
```

**4. Response Compression** (1 hour)
```python
# modal_api_v2.py

from fastapi.middleware.gzip import GZipMiddleware

web_app.add_middleware(GZipMiddleware, minimum_size=1000)
```

---

### 10. Create Monitoring Dashboard

**Priority:** P2 (Medium)
**Estimated Time:** 3 hours
**Complexity:** Low

```python
# modal_api_v2.py

# Global metrics
metrics = {
    'requests': 0,
    'errors': 0,
    'latencies': [],
    'cache_hits': 0,
    'cache_misses': 0
}

@web_app.get("/admin/metrics")
def get_metrics():
    return {
        "ok": True,
        "metrics": {
            "total_requests": metrics['requests'],
            "error_rate": metrics['errors'] / max(metrics['requests'], 1),
            "avg_latency_ms": sum(metrics['latencies']) / len(metrics['latencies']) if metrics['latencies'] else 0,
            "cache_hit_rate": metrics['cache_hits'] / max(metrics['cache_hits'] + metrics['cache_misses'], 1)
        }
    }
```

---

### 11. Complete API Documentation

**Priority:** P3 (Low)
**Estimated Time:** 4 hours
**Complexity:** Low

Create OpenAPI documentation:

```python
# modal_api_v2.py

web_app = FastAPI(
    title="Stock Scanner API v2",
    version="2.0",
    description="""
    AI-powered stock screening API with 4-tier learning system.

    ## Features
    - Real-time market scanning
    - Options flow analysis
    - SEC intelligence
    - Theme discovery
    - Self-learning parameters
    """,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add response models
from pydantic import BaseModel

class ScanResponse(BaseModel):
    ok: bool
    data: dict

@web_app.get("/scan", response_model=ScanResponse)
def scan():
    """
    Get latest scan results

    Returns ranked stocks based on multi-factor analysis.
    """
    ...
```

---

## 📊 PROGRESS SUMMARY

### Completed: 3/12 tasks (25%)
- ✅ Security fixes
- ✅ Trading endpoints
- ✅ Debug endpoints

### Remaining: 9/12 tasks (75%)
- 🔄 Learning system refactor (P1, 8h)
- 🔄 AI Brain optimization (P2, 4h)
- 🔄 API authentication (P1, 3h)
- 🔄 Configuration consolidation (P2, 2h)
- 🔄 Split large files (P2, 6h)
- 🔄 Performance optimization (P3, 4h)
- 🔄 Monitoring dashboard (P2, 3h)
- 🔄 API documentation (P3, 4h)
- 🔄 Error tracking (deferred)

### Total Estimated Time: 34 hours remaining

---

## 🎯 RECOMMENDED PRIORITIES

### Week 1 (16 hours)
1. ✅ Security fixes (DONE)
2. ✅ Trading endpoints (DONE)
3. ✅ Debug endpoints (DONE)
4. API authentication (3h)
5. Learning system refactor (8h)
6. Configuration consolidation (2h)
7. AI Brain documentation (2h)

### Week 2 (12 hours)
8. Performance optimization (4h)
9. Monitoring dashboard (3h)
10. Split parameter_learning.py only (5h)

### Week 3 (6 hours)
11. API documentation (4h)
12. Final testing and deployment (2h)

---

**Status:** ✅ 25% Complete (3/12 tasks)
**Next:** API Authentication (Task #109)
**Updated:** February 1, 2026
