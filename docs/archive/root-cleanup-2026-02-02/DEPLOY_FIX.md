# Deploy Fix for Degraded Status

**Issue**: Backend API endpoints timing out due to blocking Yahoo Finance calls
**Status**: 🔧 READY TO DEPLOY

---

## Changes Made

### 1. ✅ Added Simple Health Check Endpoint

**File**: `src/api/app.py` (line ~110)

Added `/health` endpoint that responds instantly without external API calls:

```python
@app.route('/health')
def simple_health_check():
    """Simple health check for Digital Ocean monitoring."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'stock-scanner-bot',
        'workers': 4
    }), 200
```

**Test**:
```bash
curl https://stock-story-jy89o.ondigitalocean.app/health
# Should return: {"status":"healthy",...}
```

---

### 2. ✅ Added Timeouts to Yahoo Finance Calls

**File**: `src/api/app.py` (line ~2259)

Modified `safe_download()` function to timeout after 10 seconds:

```python
def safe_download(ticker, period='6mo', timeout=10):
    """Safely download and normalize data with timeout protection."""
    # Sets alarm signal to timeout after 10 seconds
    # Prevents workers from blocking indefinitely
```

**Impact**:
- Workers won't hang on slow Yahoo Finance responses
- Failed downloads return None quickly
- App stays responsive even if Yahoo Finance is down

---

### 3. ✅ Added Gevent for Better Async Support

**File**: `requirements.txt`

Added `gevent>=24.2.1` for non-blocking I/O operations.

---

## Required: Update Digital Ocean Run Command

### Current Run Command:
```bash
gunicorn --bind 0.0.0.0:$PORT --workers 4 --timeout 600 --access-logfile - --error-logfile - "src.api.app:app"
```

### Updated Run Command (Use This):
```bash
gunicorn --bind 0.0.0.0:$PORT --workers 8 --worker-class gevent --worker-connections 1000 --timeout 600 --access-logfile - --error-logfile - "src.api.app:app"
```

### Changes:
- `--workers 4` → `--workers 8` (double capacity)
- Added `--worker-class gevent` (non-blocking I/O)
- Added `--worker-connections 1000` (concurrent connections per worker)

---

## How to Update Digital Ocean

### Option 1: Using Digital Ocean Dashboard (Easiest)

1. Go to https://cloud.digitalocean.com/apps/54145811-faf1-4374-8cdd-b72cc5a3fd27
2. Click **Settings** → **Components** → **stock-scanner-bot**
3. Scroll to **Run Command**
4. Update to:
   ```
   gunicorn --bind 0.0.0.0:$PORT --workers 8 --worker-class gevent --worker-connections 1000 --timeout 600 --access-logfile - --error-logfile - "src.api.app:app"
   ```
5. Click **Save**
6. Click **Deploy** to apply changes

### Option 2: Using Digital Ocean API

```bash
# Load token
DO_TOKEN=$(cat ~/.claude/do_api_token)

# Update app spec (requires full spec update)
curl -X PUT \
  -H "Authorization: Bearer $DO_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "spec": {
      "services": [{
        "name": "stock-scanner-bot",
        "run_command": "gunicorn --bind 0.0.0.0:$PORT --workers 8 --worker-class gevent --worker-connections 1000 --timeout 600 --access-logfile - --error-logfile - \"src.api.app:app\""
      }]
    }
  }' \
  https://api.digitalocean.com/v2/apps/54145811-faf1-4374-8cdd-b72cc5a3fd27
```

---

## Deployment Steps

1. ✅ **Code changes made** (health check + timeouts)
2. ✅ **Dependencies updated** (gevent added)
3. ⏭️ **Commit and push** (trigger auto-deploy)
4. ⏭️ **Update run command** (in Digital Ocean dashboard)
5. ⏭️ **Wait for deployment** (~3-5 minutes)
6. ⏭️ **Test endpoints** (verify fix)

---

## Testing After Deploy

### 1. Test Simple Health Check
```bash
curl https://stock-story-jy89o.ondigitalocean.app/health
# Expected: {"status":"healthy","timestamp":"..."}
```

### 2. Test API Health (Should Work Now)
```bash
curl https://stock-story-jy89o.ondigitalocean.app/api/health
# Expected: JSON data (not HTML error)
```

### 3. Test Concurrent Requests
```bash
# All should succeed without blocking
for i in {1..20}; do
  curl -s https://stock-story-jy89o.ondigitalocean.app/health &
done
wait
```

### 4. Monitor Logs
```bash
# Using helper script
source .do_helper.sh
do_logs 50

# Look for:
# ✅ "Starting gunicorn" - App started
# ✅ "Booting worker with pid" - Workers running
# ❌ No timeout errors
# ❌ No connection errors
```

---

## Expected Results

### Before Fix:
- ❌ All workers blocked on Yahoo Finance calls
- ❌ 503 errors on all API endpoints
- ❌ Digital Ocean status: "Degraded"
- ❌ Frontend shows "SyntaxError: Unexpected token '<'"

### After Fix:
- ✅ Simple `/health` responds instantly
- ✅ Workers don't block indefinitely (10s timeout)
- ✅ More workers = more capacity (8 vs 4)
- ✅ Gevent = non-blocking I/O
- ✅ API endpoints work (may be slow but won't timeout)
- ✅ Digital Ocean status: "Active"
- ✅ Frontend loads data successfully

---

## Monitoring

### Key Metrics to Watch:

1. **Response Time**: `/health` should be <100ms
2. **Error Rate**: Should drop to near 0%
3. **Worker Availability**: All 8 workers should stay responsive
4. **Digital Ocean Status**: Should change from "Degraded" to "Active"

### Check Status:
```bash
# App status
source .do_helper.sh
do_status

# Recent logs
do_logs 100 | tail -50

# Test all endpoints
curl -s https://stock-story-jy89o.ondigitalocean.app/health
curl -s https://stock-story-jy89o.ondigitalocean.app/api/health | head -20
```

---

## If Issue Persists

### Additional Steps:

1. **Increase workers further**: Try `--workers 12`
2. **Add more aggressive timeouts**: Reduce timeout to `5` seconds
3. **Consider background tasks**: Move heavy operations to Celery/RQ
4. **Cache more aggressively**: Increase cache TTL to 30+ minutes

### Rollback Plan:

If the fix doesn't work, revert run command to:
```bash
gunicorn --bind 0.0.0.0:$PORT --workers 4 --timeout 600 --access-logfile - --error-logfile - "src.api.app:app"
```

---

## Files Modified

- ✅ `src/api/app.py` - Added health check + timeouts
- ✅ `requirements.txt` - Added gevent
- ✅ `DEPLOY_FIX.md` - This document

---

## Next Steps

Ready to deploy! Run:

```bash
git add src/api/app.py requirements.txt DEPLOY_FIX.md
git commit -m "fix: Add health check and timeouts to prevent worker blocking"
git push origin main
```

Then update the run command in Digital Ocean dashboard.

---

**Status**: ✅ READY TO DEPLOY
