# Digital Ocean Forensic Diagnosis - Complete Analysis

**Date**: January 30, 2026
**Time**: 7:10 PM
**App**: stock-story (stock-scanner-bot)
**Status**: 🟡 **PARTIALLY WORKING**

---

## Executive Summary

**Good News**: The immediate blocking issue is FIXED ✅
- Simple `/health` endpoint working (76ms response)
- `/api/health` endpoint working (returns data)
- Workers no longer hanging on external API calls

**Remaining Issues**: Several backend services unavailable ⚠️
- Missing PyTorch dependency
- Evolution engine not available
- Multiple 404 errors from frontend calling non-existent endpoints

---

## Current Status

### ✅ What's Working

| Endpoint | Status | Response Time | Notes |
|----------|--------|---------------|-------|
| `/` (Frontend) | ✅ 200 OK | 162ms | Static HTML loads fine |
| `/health` | ✅ 200 OK | 76ms | **NEW** - Fast health check |
| `/api/health` | ✅ 200 OK | ~2s | Market health data working |
| `/api/trades/watchlist` | ✅ 200 OK | 125ms | Watchlist API working |
| `/api/status` | ✅ Likely OK | - | App status endpoint |

### ❌ What's Broken

| Endpoint/Feature | Status | Error | Impact |
|------------------|--------|-------|--------|
| **Missing PyTorch** | ❌ CRITICAL | `No module named 'torch'` | Learning System API unavailable |
| `/api/themes` | ❌ 404 | Route doesn't exist | Frontend breaks |
| `/api/evolution` | ❌ 404 | Route doesn't exist | Frontend breaks |
| `/api/weights` | ❌ 404 | Route doesn't exist | Frontend breaks |
| `/api/ma-radar` | ❌ 404 | Route doesn't exist | Frontend breaks |
| `/api/radar` | ❌ 404 | Route doesn't exist | Frontend breaks |
| `/api/alerts` | ❌ 404 | Route doesn't exist | Frontend breaks |
| `/api/risk` | ❌ 404 | Route doesn't exist | Frontend breaks |
| `/api/evolution/status` | ❌ 500 | "Evolution engine not available" | Backend feature disabled |
| `/api/evolution/weights` | ❌ 500 | "Evolution engine not available" | Backend feature disabled |
| `/api/themes/list` | ❌ Empty | No data returned | Themes not loading |

---

## Issue #1: Missing PyTorch Dependency 🔴 CRITICAL

### Error in Logs:
```
WARNING src.api.app: Learning System API not available: No module named 'torch'
```

### Impact:
- Learning System APIs completely unavailable
- Evolution engine can't run
- AI-based features broken
- Multiple endpoints return errors

### Root Cause:
PyTorch is NOT in `requirements.txt`, but the code tries to import it.

### Fix:
Add to `requirements.txt`:
```
torch>=2.0.0
torchvision>=0.15.0
```

**Warning**: PyTorch is LARGE (~800MB). This will:
- Increase build time significantly
- Increase memory usage
- May require larger instance size

**Alternative**: Make PyTorch optional and gracefully degrade features:
```python
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logger.warning("PyTorch not available - Learning features disabled")
```

---

## Issue #2: Missing API Route Aggregators 🟡 HIGH PRIORITY

### Problem:
Frontend calls simple endpoints like `/api/themes` but backend only has specific routes like `/api/themes/list`, `/api/themes/registry`, etc.

### Missing Routes:

1. **`/api/themes`** - Should aggregate:
   - `/api/themes/list`
   - `/api/themes/registry`
   - `/api/evolution/themes`

2. **`/api/evolution`** - Should return:
   - `/api/evolution/status`
   - `/api/evolution/accuracy`
   - Summary data

3. **`/api/weights`** - Should redirect to:
   - `/api/evolution/weights`

4. **`/api/radar`** - Missing entirely, should exist

5. **`/api/ma-radar`** - Missing entirely, should exist

6. **`/api/alerts`** - Missing entirely, should exist

7. **`/api/risk`** - Missing entirely, should exist

### Fix Strategy:

**Option A: Add Wrapper Endpoints** (Recommended)

```python
@app.route('/api/themes')
def api_themes_summary():
    """Aggregate all theme data into one response."""
    try:
        # Call internal functions
        themes_list = get_themes_list()
        themes_registry = get_themes_registry()

        return jsonify({
            'ok': True,
            'themes': themes_list,
            'registry': themes_registry,
            'evolution_themes': get_evolution_themes()
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/evolution')
def api_evolution_summary():
    """Return evolution engine summary."""
    if not evolution_engine_available():
        return jsonify({
            'ok': False,
            'error': 'Evolution engine not available',
            'available': False
        })

    return jsonify({
        'ok': True,
        'available': True,
        'status': get_evolution_status(),
        'accuracy': get_evolution_accuracy(),
        'weights': get_evolution_weights()
    })
```

**Option B: Update Frontend** (More work)

Update frontend JavaScript to call correct endpoints:
- `/api/themes` → `/api/themes/list`
- `/api/evolution` → `/api/evolution/status`
- etc.

---

## Issue #3: Evolution Engine Unavailable 🟡 MEDIUM PRIORITY

### Error:
```json
{
  "error": "Evolution engine not available",
  "ok": false
}
```

### Endpoints Affected:
- `/api/evolution/status`
- `/api/evolution/weights`
- `/api/evolution/themes`
- `/api/evolution/accuracy`
- `/api/evolution/correlations`

### Root Cause:
Evolution engine depends on:
1. PyTorch (missing)
2. Learning system modules
3. Trained model files
4. Database/storage for weights

### Fix:
1. Add PyTorch dependency
2. Ensure model files are deployed
3. Initialize evolution engine on startup
4. Add graceful fallback if unavailable

---

## Issue #4: Run Command Not Updated ⚠️ PENDING

### Current:
```bash
--workers 4 --timeout 600
```

### Should Be:
```bash
--workers 8 --worker-class gevent --worker-connections 1000 --timeout 600
```

### Impact:
- Still only 4 workers (should be 8)
- Not using gevent async workers
- Lower concurrent capacity than optimal

### Fix:
Update in Digital Ocean dashboard (Settings → Components → Run Command)

---

## Issue #5: Memory/Resource Constraints 🔵 LOW PRIORITY

### Current Instance:
- **Type**: `apps-s-1vcpu-0.5gb`
- **CPU**: 1 vCPU
- **RAM**: 512 MB
- **Workers**: 4

### Recommendations:

**If adding PyTorch**:
- Upgrade to: `apps-s-1vcpu-1gb` or `apps-s-2vcpu-2gb`
- PyTorch alone uses ~800MB
- Need headroom for workers

**Current Config (No PyTorch)**:
- 512MB is barely adequate for 4 workers
- 8 workers will likely cause memory issues
- Recommend: `apps-s-1vcpu-1gb` minimum

---

## Detailed Log Analysis

### Startup (Successful ✅):
```
[INFO] Starting gunicorn 24.1.1
[INFO] Listening at: http://0.0.0.0:8080
[INFO] Using worker: sync
[INFO] Booting worker with pid: 13-16
```

### Warnings (Non-Critical ⚠️):
```
WARNING: SocketIO disabled - running without real-time sync
WARNING: Learning System API not available: No module named 'torch'
```

### Errors (Critical ❌):
```
ERROR: Unhandled exception: 404 Not Found
```
Repeated 13+ times in last 5 minutes - Frontend calling missing endpoints

---

## Recommended Fix Priority

### 🔴 CRITICAL (Do First):

**1. Add Missing API Route Aggregators** (30 min)
```python
# Add these routes to src/api/app.py
@app.route('/api/themes')
@app.route('/api/evolution')
@app.route('/api/weights')
@app.route('/api/radar')
@app.route('/api/ma-radar')
@app.route('/api/alerts')
@app.route('/api/risk')
```

**2. Update Run Command** (5 min)
- Go to Digital Ocean dashboard
- Update to 8 workers with gevent

### 🟡 HIGH PRIORITY (Do Today):

**3. Make PyTorch Optional** (20 min)
```python
# Gracefully handle missing torch
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

# Check before using
if TORCH_AVAILABLE:
    # Use learning features
else:
    # Return placeholder/fallback
```

**4. Add Endpoint Fallbacks** (30 min)
- Return empty/placeholder data instead of 404
- Better error messages
- Graceful degradation

### 🔵 MEDIUM PRIORITY (Do This Week):

**5. Upgrade Instance Size** (5 min)
- Change to `apps-s-1vcpu-1gb`
- More RAM = more workers possible
- Better performance

**6. Add PyTorch (Optional)** (1 hour)
- Only if you need Learning System features
- Requires larger instance
- Significantly increases build time

---

## Testing Commands

```bash
# Test all critical endpoints
curl https://stock-story-jy89o.ondigitalocean.app/health
curl https://stock-story-jy89o.ondigitalocean.app/api/health
curl https://stock-story-jy89o.ondigitalocean.app/api/themes
curl https://stock-story-jy89o.ondigitalocean.app/api/evolution
curl https://stock-story-jy89o.ondigitalocean.app/api/trades/watchlist

# Check logs
source .do_helper.sh
do_logs 50 | grep -E "ERROR|WARNING"

# Monitor status
do_status
```

---

## Summary: What to Fix

### Fix Now (Critical):
1. ✅ Health check - DONE
2. ✅ Timeouts on yfinance - DONE
3. ⏭️ Add missing API aggregator routes
4. ⏭️ Update run command to 8 workers + gevent

### Fix Soon (High):
5. ⏭️ Make PyTorch optional
6. ⏭️ Add graceful fallbacks for missing features
7. ⏭️ Upgrade instance size (512MB → 1GB)

### Fix Later (Medium):
8. ⏭️ Add PyTorch if needed
9. ⏭️ Implement full Evolution engine
10. ⏭️ Add real-time sync (SocketIO)

---

## Files to Modify

1. **src/api/app.py** - Add missing routes
2. **requirements.txt** - Optionally add torch
3. **Digital Ocean Settings** - Update run command
4. **Digital Ocean Settings** - Upgrade instance size

---

**Next Step**: Add missing API aggregator routes to fix 404 errors.

