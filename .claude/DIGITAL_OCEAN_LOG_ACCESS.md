# Digital Ocean Log Access Guide

**How to Access and Analyze Application Logs**

---

## Quick Access (Web Console)

### Step 1: Navigate to Logs

1. Go to: https://cloud.digitalocean.com/apps
2. Click on **stock-story** app
3. In left sidebar, click **Runtime Logs**
4. Or direct link: https://cloud.digitalocean.com/apps/54145811-faf1-4374-8cdd-b72cc5a3fd27/logs

### Step 2: Filter Logs

**Log Types:**
- **Build Logs** - Show build/deployment process
- **Run Logs** - Show application runtime (THIS IS WHAT YOU NEED)
- **Deploy Logs** - Show deployment status

**Time Range:**
- Last 1 hour
- Last 24 hours
- Last 7 days
- Custom range

### Step 3: Search Logs

Common search terms:
- `AsyncScanner` - Find scanner-related logs
- `Background scan` - Find scan start/completion
- `ERROR` - Find error messages
- `exception` - Find Python exceptions
- `Traceback` - Find Python stack traces
- `CRITICAL` - Find critical errors

---

## Via API (Automated)

### Get Recent Logs

```bash
# Get logs for the API service
curl -X GET \
  -H "Authorization: Bearer YOUR_DO_TOKEN" \
  "https://api.digitalocean.com/v2/apps/54145811-faf1-4374-8cdd-b72cc5a3fd27/logs?type=RUN&follow=false&tail_lines=500"
```

### Real-Time Log Streaming

```bash
# Stream logs in real-time
curl -X GET \
  -H "Authorization: Bearer YOUR_DO_TOKEN" \
  "https://api.digitalocean.com/v2/apps/54145811-faf1-4374-8cdd-b72cc5a3fd27/logs?type=RUN&follow=true" | \
  grep -E "ERROR|AsyncScanner|Background scan"
```

---

## What to Look For

### 1. Scan Initialization

**Look for:**
```
INFO - Background scan started: 20 tickers, mode=quick
```

**If missing:** Scan trigger endpoint not reached

### 2. AsyncScanner Errors

**Look for:**
```
ERROR - Background scan error: <error message>
ERROR - AsyncScanner: <error message>
Traceback (most recent call last):
```

**Common errors:**
- `ImportError` - Missing dependency
- `ConnectionError` - API connection failed
- `KeyError` - Missing API response field
- `MemoryError` - Out of memory (512MB limit)
- `TimeoutError` - Operation took too long

### 3. API Key Issues

**Look for:**
```
ERROR - Polygon API: Unauthorized
ERROR - Missing API key
ERROR - Invalid API key
```

**Fix:** Verify POLYGON_API_KEY is set correctly

### 4. Memory Issues

**Look for:**
```
MemoryError
Killed
OOM (Out of Memory)
```

**Fix:** Reduce MAX_CONCURRENT_SCANS or upgrade to 1GB instance

### 5. CSV Saving Issues

**Look for:**
```
ERROR - Failed to save scan results to CSV
PermissionError: [Errno 13] Permission denied
OSError: [Errno 28] No space left on device
```

**Fix:** Check file permissions or disk space

---

## Common Diagnostic Patterns

### Pattern 1: Scan Starts But Never Completes

**Logs show:**
```
INFO - Background scan started: 20 tickers, mode=quick
[... long pause ...]
[nothing more]
```

**Diagnosis:** AsyncScanner hanging or timeout
**Action:**
1. Check for network timeout errors
2. Reduce concurrent scans
3. Add more logging to AsyncScanner

### Pattern 2: Scan Completes But No CSV

**Logs show:**
```
INFO - Background scan started: 20 tickers, mode=quick
INFO - Background scan complete: 20 stocks scanned
[no save message]
```

**Diagnosis:** CSV saving failed silently
**Action:**
1. Check logs for permission errors
2. Verify df is not None/empty
3. Check disk space

### Pattern 3: Immediate Failure

**Logs show:**
```
INFO - Background scan started: 20 tickers, mode=quick
ERROR - Background scan error: <immediate error>
Traceback...
```

**Diagnosis:** Import error, config issue, or invalid input
**Action:** Fix the specific error shown

---

## Troubleshooting Commands

### Check App Status
```bash
curl -s -X GET \
  -H "Authorization: Bearer YOUR_TOKEN" \
  "https://api.digitalocean.com/v2/apps/54145811-faf1-4374-8cdd-b72cc5a3fd27" | \
  python3 -c "import sys, json; d=json.load(sys.stdin); print(f\"Active: {d['app']['active_deployment']['id']}\nPhase: {d['app']['phase']}\")"
```

### Check Recent Deployments
```bash
curl -s -X GET \
  -H "Authorization: Bearer YOUR_TOKEN" \
  "https://api.digitalocean.com/v2/apps/54145811-faf1-4374-8cdd-b72cc5a3fd27/deployments" | \
  python3 -c "import sys, json; d=json.load(sys.stdin); [print(f\"{dep['id']}: {dep['phase']} - {dep.get('cause', 'N/A')[:60]}\") for dep in d['deployments'][:5]]"
```

### Check Environment Variables
```bash
curl -s -X GET \
  -H "Authorization: Bearer YOUR_TOKEN" \
  "https://api.digitalocean.com/v2/apps/54145811-faf1-4374-8cdd-b72cc5a3fd27" | \
  python3 -c "import sys, json; d=json.load(sys.stdin); envs=d['app']['spec']['services'][0]['envs']; [print(f\"{e['key']}: {'SECRET' if e['type']=='SECRET' else e.get('value', 'N/A')}\") for e in envs]"
```

---

## Export Logs for Analysis

### Save to File
```bash
# Save last 1000 lines
curl -X GET \
  -H "Authorization: Bearer YOUR_TOKEN" \
  "https://api.digitalocean.com/v2/apps/54145811-faf1-4374-8cdd-b72cc5a3fd27/logs?type=RUN&follow=false&tail_lines=1000" \
  > app_logs_$(date +%Y%m%d_%H%M%S).txt
```

### Extract Errors Only
```bash
curl -X GET \
  -H "Authorization: Bearer YOUR_TOKEN" \
  "https://api.digitalocean.com/v2/apps/54145811-faf1-4374-8cdd-b72cc5a3fd27/logs?type=RUN&follow=false&tail_lines=1000" | \
  grep -A 5 "ERROR\|CRITICAL\|Traceback" > errors.txt
```

---

## Real-Time Debugging Session

### Step-by-Step

1. **Open log stream in one terminal:**
   ```bash
   # Terminal 1: Watch logs
   curl -N -X GET \
     -H "Authorization: Bearer YOUR_TOKEN" \
     "https://api.digitalocean.com/v2/apps/54145811-faf1-4374-8cdd-b72cc5a3fd27/logs?type=RUN&follow=true"
   ```

2. **Trigger scan in another terminal:**
   ```bash
   # Terminal 2: Trigger scan
   curl -X POST "https://stock-story-jy89o.ondigitalocean.app/api/scan/trigger?mode=quick"
   ```

3. **Watch Terminal 1 for:**
   - "Background scan started" message
   - Any error messages
   - "Background scan complete" message
   - "Scan results saved" message

4. **If scan doesn't complete in 60 seconds:**
   - Check for timeout errors
   - Check for memory errors
   - Look for stuck operation

---

## Contact Support (If Needed)

If you can't resolve the issue:

1. **Gather information:**
   - Save recent logs (last 1000 lines)
   - Note the time when issue occurred
   - Copy any error messages

2. **Create support ticket:**
   - Go to: https://cloud.digitalocean.com/support/tickets
   - Include:
     - App ID: 54145811-faf1-4374-8cdd-b72cc5a3fd27
     - Issue description
     - Relevant log excerpts
     - Steps to reproduce

---

## Quick Fixes Based on Logs

| Error in Logs | Quick Fix |
|---------------|-----------|
| `MemoryError` | Reduce MAX_CONCURRENT_SCANS from 25 to 10 |
| `Timeout` | Increase timeout or reduce concurrent operations |
| `ModuleNotFoundError` | Add missing package to requirements.txt |
| `PermissionError` | Check file write permissions |
| `ConnectionError` | Check network/API availability |
| `KeyError: 'POLYGON_API_KEY'` | Verify environment variable is set |
| `401 Unauthorized` | Check API key is valid |
| `429 Too Many Requests` | Reduce request rate |

---

**Last Updated:** 2026-01-30
**App ID:** 54145811-faf1-4374-8cdd-b72cc5a3fd27
**Maintained By:** Claude Sonnet 4.5
