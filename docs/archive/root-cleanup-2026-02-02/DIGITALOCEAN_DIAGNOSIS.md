# Digital Ocean App Platform Diagnosis

**Date**: January 30, 2026
**App**: stock-story (stock-scanner-bot)
**Status**: 🟡 **DEGRADED**
**Live URL**: https://stock-story-jy89o.ondigitalocean.app

---

## Issue Summary

The app shows **"Degraded"** status on Digital Ocean. Investigation reveals:

- ✅ Frontend (HTML) loads successfully (200 OK)
- ❌ Backend API endpoints return 503 errors
- ⚠️ Gunicorn workers are running but not handling API requests properly

---

## Current Status

### Deployment Info

| Item | Status |
|------|--------|
| **Deployment ID** | `08f26825-b2a2-4b2b-8347-0ad2d51269de` |
| **Phase** | ACTIVE |
| **Build Status** | SUCCESS (6/6 steps) |
| **Region** | Singapore (sgp) |
| **Instance** | apps-s-1vcpu-0.5gb (1 instance) |
| **Workers** | 4 Gunicorn workers running |

### Service Health

- **Frontend**: ✅ Working - Static HTML serving correctly
- **Backend API**: ❌ Failing - All `/api/*` endpoints return 503
- **Socket.io**: ❌ Disabled/Not working
- **Learning System**: ⚠️ Missing torch module

---

## Error Details

### API Endpoint Failures

All backend API endpoints are returning Digital Ocean error pages:

```
upstream_reset_before_response_started{connection_termination} (503 UC)
App Platform failed to forward this request to the application.
```

**Affected Endpoints**:
- `/api/health` - 503 UC
- `/api/themes` - 503 error
- `/api/evolution` - 503 error
- `/api/trades/watchlist` - 503 error
- `/socket.io/*` - 503 error
- All other `/api/*` endpoints

### Console Errors (From Browser)

```
Failed to load resource: the server responded with a status of 504
Themes fetch failed: SyntaxError: Unexpected token '<', "<!DOCTYPE"... is not valid JSON
Evolution fetch failed: SyntaxError: Unexpected token '<', "<!DOCTYPE"... is not valid JSON
```

---

## Runtime Logs Analysis

### What's Working ✅

```
[INFO] Starting gunicorn 24.1.1
[INFO] Listening at: http://0.0.0.0:8080 (1)
[INFO] Using worker: sync
[INFO] Booting worker with pid: 14
[INFO] Booting worker with pid: 15
[INFO] Booting worker with pid: 16
[INFO] Booting worker with pid: 17
[INFO] ✓ Watchlist API registered
```

### Warnings ⚠️

```
[WARNING] SocketIO disabled - running without real-time sync
[WARNING] Learning System API not available: No module named 'torch'
```

---

## Root Cause Analysis

### Probable Cause: Flask Routes Not Configured

The issue appears to be that:

1. **Gunicorn is running** - Workers started successfully
2. **Frontend static files work** - HTML is served correctly
3. **API routes are failing** - Flask app may not have routes registered properly

### Possible Reasons:

1. **Missing Route Registration** - `/api/*` routes not registered in Flask app
2. **Import Error in API Module** - API blueprint failing to import
3. **Database Connection Failure** - API routes trying to connect to missing database
4. **Missing Dependencies** - Some Python packages not installed
5. **Port/Path Mismatch** - API routes expecting different base path

---

## Diagnostic Commands Used

```bash
# List apps
curl -H "Authorization: Bearer $TOKEN" \
  https://api.digitalocean.com/v2/apps

# Get app details
curl -H "Authorization: Bearer $TOKEN" \
  https://api.digitalocean.com/v2/apps/54145811-faf1-4374-8cdd-b72cc5a3fd27

# Get runtime logs
curl -H "Authorization: Bearer $TOKEN" \
  "https://api.digitalocean.com/v2/apps/54145811-faf1-4374-8cdd-b72cc5a3fd27/deployments/08f26825-b2a2-4b2b-8347-0ad2d51269de/logs?type=RUN&follow=false&tail_lines=100"
```

---

## Recommended Fixes

### 1. Check API Route Registration

Verify that `src/api/app.py` properly registers all API blueprints:

```python
from flask import Flask
app = Flask(__name__)

# Ensure these are uncommented and working:
from src.api.routes import health, themes, evolution, trades
app.register_blueprint(health_bp)
app.register_blueprint(themes_bp)
# ... etc
```

### 2. Add Health Check Endpoint

Digital Ocean needs a working health check. Add to `src/api/app.py`:

```python
@app.route('/health', methods=['GET'])
def health_check():
    return {'status': 'healthy'}, 200
```

### 3. Check for Missing Imports

Look for any import errors in the API modules that might prevent routes from registering.

### 4. Add Torch Dependency (Optional)

If Learning System is needed, add to `requirements.txt`:
```
torch>=2.0.0
```

### 5. Enable Debug Logging

Update gunicorn command to get more verbose logs:
```bash
gunicorn --bind 0.0.0.0:$PORT \
  --workers 4 \
  --timeout 600 \
  --log-level debug \
  --access-logfile - \
  --error-logfile - \
  "src.api.app:app"
```

---

## Immediate Action Items

1. **Check `src/api/app.py`** - Verify all routes are registered
2. **Add simple health check** - `/health` endpoint that just returns 200
3. **Check requirements.txt** - Ensure all dependencies are listed
4. **Review recent code changes** - See if any recent commits broke API routes
5. **Test locally** - Run `gunicorn` command locally to reproduce issue

---

## Testing After Fix

Once fixed, verify with:

```bash
# Test health endpoint
curl https://stock-story-jy89o.ondigitalocean.app/api/health

# Test themes endpoint
curl https://stock-story-jy89o.ondigitalocean.app/api/themes

# Should return JSON, not HTML error pages
```

---

## Files to Investigate

1. **src/api/app.py** - Main Flask app, route registration
2. **src/api/routes/*.py** - Individual API route files
3. **requirements.txt** - Python dependencies
4. **src/api/__init__.py** - Module initialization

---

## Digital Ocean Resources

- **App Dashboard**: https://cloud.digitalocean.com/apps/54145811-faf1-4374-8cdd-b72cc5a3fd27
- **Runtime Logs**: Click "Runtime Logs" in dashboard
- **Build Logs**: Click "Deployments" → Latest deployment
- **API Token**: Stored in `.do_api_token` (gitignored)

---

## Next Steps

1. ✅ API token saved to `.do_api_token`
2. ⏭️ Investigate `src/api/app.py` for route registration issues
3. ⏭️ Add basic health check endpoint
4. ⏭️ Test API endpoints locally
5. ⏭️ Deploy fix and verify

---

**Status**: Awaiting code investigation and fix deployment
