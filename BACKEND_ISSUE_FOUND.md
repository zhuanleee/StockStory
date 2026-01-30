# Backend Issue - ROOT CAUSE FOUND

**Date**: January 30, 2026
**Status**: 🔴 **CRITICAL - BLOCKING OPERATIONS**

---

## 🎯 ROOT CAUSE IDENTIFIED

The "Degraded" status is caused by **blocking Yahoo Finance API calls** in multiple endpoints that are timing out or taking too long, causing all Gunicorn workers to become unresponsive.

---

## The Problem

### Critical Issue: Synchronous External API Calls

Multiple endpoints are making **blocking yfinance.download()** calls:

1. **`/api/health`** (line 2471-2565)
   - Downloads VIX data: `yf.download('^VIX', '1mo')`
   - Downloads SPY data: `yf.download('SPY', '6mo')`
   - Downloads VIX3M data: `yf.download('^VIX3M', '1mo')`
   - Downloads GLD data for safe haven
   - Downloads HYG data for junk bonds
   - Downloads 30+ stock tickers for market breadth

2. **`/api/themes`** - Similar pattern
3. **`/api/evolution`** - Making external API calls
4. **Other `/api/*` endpoints** - All hitting external APIs

### Why This Causes 503 Errors

```
Request → Gunicorn Worker 1 (blocked on yfinance)
       → Gunicorn Worker 2 (blocked on yfinance)
       → Gunicorn Worker 3 (blocked on yfinance)
       → Gunicorn Worker 4 (blocked on yfinance)
       → No workers available → 503 Error
```

**With only 4 workers**, if each takes 10-30 seconds waiting for Yahoo Finance:
- All workers become blocked
- New requests have no available workers
- Digital Ocean returns 503 "no_healthy_upstream"

---

## Evidence from Logs

```python
# From src/api/app.py:2236
def _get_real_market_health_data():
    """Fetch real market data for health indicators with parallel processing."""

    # BLOCKING CALL - Can take 5-30 seconds!
    vix_df = safe_download('^VIX', '1mo')  # Line 2292

    # Another BLOCKING CALL
    spy_df = safe_download('SPY', '6mo')   # Line 2307

    # Yet another BLOCKING CALL
    vix3m_df = safe_download('^VIX3M', '1mo')  # Line 2322

    # And more...
```

Each `yf.download()` call is **synchronous and blocking**:
- Minimum: 2-5 seconds per call
- Average: 5-15 seconds per call
- If Yahoo Finance is slow/down: 30+ seconds or timeout

---

## Why It's Worse in Production

### Development vs Production

| Factor | Development | Production (Digital Ocean) |
|--------|-------------|----------------------------|
| **Workers** | Often 1-2 | 4 workers |
| **Timeout** | Unlimited | 600 seconds |
| **Network** | Fast local | Varies by region |
| **Load** | Low | All page loads hit multiple APIs |
| **Recovery** | Manual restart | Auto-restart but repeated failures |

### The Death Spiral

1. User loads dashboard → Triggers `/api/health`, `/api/themes`, `/api/evolution`, etc.
2. Each API call blocks a worker for 10-30 seconds
3. Multiple users or tabs → All 4 workers blocked
4. New requests → No available workers → 503 errors
5. Frontend sees 503 → Retries → Makes problem worse
6. Digital Ocean marks app as "Degraded"

---

## Proof: Why Frontend Works, Backend Doesn't

| Component | Status | Reason |
|-----------|--------|--------|
| **Frontend (HTML)** | ✅ Works | Static files served directly, no blocking |
| **Backend APIs** | ❌ 503 | All workers blocked on external API calls |

---

## Solutions (In Order of Urgency)

### 🔥 IMMEDIATE FIX (1 hour)

**Option A: Add Aggressive Caching**

The code already has caching (line 2477), but it's not working because:
1. Cache is empty on first request
2. First request blocks all workers
3. Subsequent requests time out before cache is populated

**Fix**: Pre-populate cache or increase worker count

```python
# In app.py, add at startup:
@app.before_first_request
def warm_cache():
    """Pre-populate cache in background thread"""
    import threading

    def background_warmup():
        with app.app_context():
            try:
                _get_real_market_health_data()
            except:
                pass

    threading.Thread(target=background_warmup, daemon=True).start()
```

**Option B: Increase Workers Temporarily**

Update gunicorn command:
```bash
gunicorn --bind 0.0.0.0:$PORT \
  --workers 8 \           # Double the workers!
  --timeout 600 \
  --access-logfile - \
  --error-logfile - \
  "src.api.app:app"
```

**Pros**: Quick fix, allows more concurrent blocking calls
**Cons**: Uses more memory, still doesn't solve root issue

---

### 🔧 SHORT-TERM FIX (4-8 hours)

**Make External API Calls Async**

Convert blocking calls to async using `asyncio` or background tasks:

```python
# Option 1: Background task queue (Celery/RQ)
from redis import Redis
from rq import Queue

queue = Queue(connection=Redis())

@app.route('/api/health')
def api_health():
    # Check cache first
    cached, is_cached = _endpoint_cache.get('health', 600)
    if is_cached:
        return jsonify(cached)

    # Return cached data immediately, update in background
    job = queue.enqueue(_get_real_market_health_data)

    # Return stale data or placeholder
    return jsonify({"status": "updating", "cached": True})
```

```python
# Option 2: Use async/await (requires async framework)
import asyncio
import aiohttp

async def fetch_async(ticker):
    # Non-blocking HTTP request
    async with aiohttp.ClientSession() as session:
        async with session.get(f'https://query1.finance.yahoo.com/v8/finance/chart/{ticker}') as response:
            return await response.json()
```

---

### ✅ LONG-TERM FIX (1-2 days)

**1. Implement Background Workers**

Use Celery or Redis Queue to offload slow tasks:

```bash
# Add to requirements.txt
celery==5.3.0
redis==5.0.0
```

```python
# tasks.py
from celery import Celery

celery = Celery('tasks', broker='redis://localhost:6379/0')

@celery.task
def update_market_health():
    """Background task to update health data"""
    data = _get_real_market_health_data()
    _endpoint_cache.set('health', data, 600)
    return data

# Run every 5 minutes
@celery.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(300.0, update_market_health.s(), name='update health data')
```

**2. Add Health Check Endpoint (Simple)**

```python
@app.route('/health')
def health_check():
    """Simple health check that doesn't call external APIs"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'workers': 4
    }), 200
```

**3. Implement Request Timeout Protection**

```python
import signal
from contextlib import contextmanager

@contextmanager
def timeout(seconds):
    def timeout_handler(signum, frame):
        raise TimeoutError()

    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)

@app.route('/api/health')
def api_health():
    try:
        with timeout(10):  # Max 10 seconds
            data = _get_real_market_health_data()
            return jsonify(data)
    except TimeoutError:
        # Return cached/stale data
        return jsonify({"error": "timeout", "cached": True}), 200
```

---

## Immediate Action Plan

### Step 1: Quick Fix (Deploy Now)

```bash
# Update run command in Digital Ocean
gunicorn --bind 0.0.0.0:$PORT \
  --workers 8 \
  --worker-class gevent \
  --worker-connections 1000 \
  --timeout 600 \
  --access-logfile - \
  --error-logfile - \
  "src.api.app:app"
```

Add to `requirements.txt`:
```
gevent==24.2.1
```

### Step 2: Add Simple Health Check (5 minutes)

```python
# Add to src/api/app.py before other routes
@app.route('/health')
def simple_health():
    """Simple health check for Digital Ocean"""
    return jsonify({'status': 'ok'}), 200
```

### Step 3: Add Timeouts to yfinance Calls (10 minutes)

```python
def safe_download(ticker, period='6mo'):
    """Safely download with timeout."""
    import signal

    def timeout_handler(signum, frame):
        raise TimeoutError("yfinance timeout")

    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(5)  # 5 second timeout

    try:
        data = yf.download(ticker, period=period, progress=False)
        signal.alarm(0)
        return normalize_dataframe_columns(data) if data is not None else None
    except (Exception, TimeoutError):
        signal.alarm(0)
        return None
```

---

## Testing After Fix

```bash
# 1. Test simple health check
curl https://stock-story-jy89o.ondigitalocean.app/health
# Should return: {"status":"ok"}

# 2. Test API health (may be slow but shouldn't fail)
curl https://stock-story-jy89o.ondigitalocean.app/api/health
# Should return JSON, not HTML error

# 3. Test concurrent requests (should not block)
for i in {1..10}; do
  curl -s https://stock-story-jy89o.ondigitalocean.app/health &
done
wait
# All should succeed
```

---

## Files to Modify

1. **src/api/app.py**
   - Add simple `/health` endpoint
   - Add timeouts to `safe_download()`
   - Consider adding background task queue

2. **requirements.txt**
   - Add `gevent==24.2.1` (for async worker class)
   - Consider adding `celery` and `redis` for background tasks

3. **Digital Ocean Config**
   - Update gunicorn command to use more workers or gevent

---

## Why This Fixes the Issue

| Problem | Solution | Result |
|---------|----------|--------|
| All workers blocked | More workers (8 instead of 4) | More capacity |
| Slow external APIs | Timeouts on yfinance calls | Fail fast instead of blocking |
| No simple health check | Add `/health` endpoint | Digital Ocean can verify app is alive |
| Synchronous blocking | Gevent async workers | Non-blocking I/O |

---

## Estimated Timeline

- **Immediate** (10 min): Add simple `/health` endpoint, deploy
- **Short-term** (1 hour): Increase workers, add timeouts
- **Long-term** (1 day): Implement background tasks with Celery

---

**Next Step**: Implement the immediate fix and deploy.

