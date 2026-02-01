# Modal Schedule Cleanup Guide

## Step-by-Step Instructions

### Step 1: Install Modal CLI

```bash
pip install modal
```

If you already have it installed, upgrade to latest:
```bash
pip install --upgrade modal
```

---

### Step 2: Login to Modal

```bash
modal token set
```

This will:
1. Open a browser window
2. Ask you to authorize the CLI
3. Save your credentials locally

If you already have a token, it will use that.

---

### Step 3: Check Current Apps

```bash
modal app list
```

**Expected output:**
```
stock-scanner-api-v2 (deployed)
stock-scanner-ai-brain (deployed)
```

**Look for:**
- Multiple versions of the same app
- Old/duplicate deployments
- Apps you don't recognize

---

### Step 4: Check Current Schedules

```bash
modal schedule list
```

**This is the key command!** It will show all scheduled functions.

**Expected output:**
```
App                          Function                    Schedule
---------------------------  --------------------------  ---------------
stock-scanner-ai-brain       morning_mega_bundle         0 14 * * 1-5
stock-scanner-ai-brain       afternoon_analysis_bundle   0 21 * * 1-5
stock-scanner-ai-brain       weekly_reports_bundle       0 2 * * 1
stock-scanner-ai-brain       monitoring_cycle_bundle     0 */6 * * *
```

**Look for:**
- Old function names (daily_scan_bundle, conviction_alerts with schedules, etc.)
- Duplicate schedules
- More than 4 schedules
- Schedules from old deployments

---

### Step 5: Stop Old Deployments

```bash
# Stop both apps
modal app stop stock-scanner-ai-brain
modal app stop stock-scanner-api-v2
```

**What this does:**
- Stops running functions
- Should remove associated schedules
- Clears the workspace

**Wait 10 seconds**, then check schedules again:
```bash
modal schedule list
```

If schedules are still there, they're phantom schedules that need manual deletion.

---

### Step 6: Delete Individual Schedules (If Needed)

If schedules persist after stopping apps, Modal CLI doesn't have a direct delete command. You have two options:

**Option A: Web Dashboard**
1. Go to: https://modal.com
2. Login to your workspace
3. Click on "Schedules" in sidebar
4. Delete old schedules manually

**Option B: Contact Support**
If you can't delete via dashboard:
```
Email: support@modal.com
Subject: Cannot delete old schedules

Hi Modal team,

I'm trying to deploy my app but hitting the 5 cron limit due to phantom schedules.
I've run `modal app stop` but schedules persist.

Workspace: zhuanleee
Apps: stock-scanner-ai-brain, stock-scanner-api-v2

Can you please manually clear all schedules for these apps?

Thanks!
```

---

### Step 7: Fresh Deployment

Once schedules are cleared:

```bash
# Deploy API first (no schedules)
modal deploy modal_api_v2.py

# Deploy scanner with 4 schedules
modal deploy modal_scanner.py
```

**Watch the output carefully:**
- Should say "Created 4 schedules"
- Should NOT say "reached limit of 5 cron jobs"
- Should succeed

---

### Step 8: Verify Deployment

```bash
# Check schedules again
modal schedule list

# Should show exactly 4 schedules:
# 1. morning_mega_bundle
# 2. afternoon_analysis_bundle
# 3. weekly_reports_bundle
# 4. monitoring_cycle_bundle

# Check app status
modal app list

# Both apps should show as deployed
```

---

## Troubleshooting

### Problem: "modal: command not found"

**Solution:**
```bash
# Make sure Modal is installed
pip install modal

# If using virtual environment, activate it first
source venv/bin/activate  # or your venv path
pip install modal
```

---

### Problem: "No token found"

**Solution:**
```bash
modal token set
```

Follow the browser authentication flow.

---

### Problem: Schedules still there after `modal app stop`

**Solution:**
1. Try redeploying with same app name (should replace old deployment)
2. Use web dashboard to delete manually
3. Contact Modal support (they're usually very responsive)

---

### Problem: Still seeing 6 or 7 schedules

**Possible causes:**
1. Old schedules not deleted
2. Another app in workspace has schedules
3. Modal counting issue

**Solution:**
```bash
# List ALL apps in workspace
modal app list

# Check if there are other apps with schedules
# Delete or stop any you don't need

# If still stuck, contact support
```

---

### Problem: Deployment succeeds but functions don't run

**Solution:**
```bash
# Test individual function manually
modal run modal_scanner.py::morning_mega_bundle

# Check logs
modal app logs stock-scanner-ai-brain --follow

# Verify environment variables are set
modal secret list
# Should show: stock-api-keys
```

---

## Expected Timeline

- **Step 1-2**: 2 minutes (install + login)
- **Step 3-4**: 1 minute (check current state)
- **Step 5**: 1 minute (stop apps)
- **Step 6**: 5-10 minutes (manual cleanup if needed)
- **Step 7-8**: 3-5 minutes (redeploy + verify)

**Total**: 15-20 minutes

---

## Success Criteria

✅ `modal schedule list` shows exactly 4 schedules
✅ All 4 schedules are for stock-scanner-ai-brain app
✅ No duplicate or old schedules
✅ Deployment completes without errors
✅ Can see apps in `modal app list`

---

## After Successful Deployment

### Test Individual Functions

```bash
# Test morning bundle (will take 15-20 min)
modal run modal_scanner.py::morning_mega_bundle

# Test afternoon bundle (will take 20-30 min)
modal run modal_scanner.py::afternoon_analysis_bundle

# Test individual alert (quick test)
modal run modal_scanner.py::conviction_alerts
```

### Monitor First Scheduled Run

The first automated run will be tomorrow (Monday) at 6:00 AM PST.

**To monitor it:**
```bash
# Watch logs live
modal app logs stock-scanner-ai-brain --follow

# Or check in dashboard
https://modal.com/apps/stock-scanner-ai-brain
```

### Configure Telegram (If Not Already)

For notifications to work, make sure these are set in Modal secrets:
```bash
modal secret create stock-api-keys \
  TELEGRAM_BOT_TOKEN=your_bot_token \
  TELEGRAM_CHAT_ID=your_chat_id \
  POLYGON_API_KEY=... \
  XAI_API_KEY=... \
  DEEPSEEK_API_KEY=... \
  # ... other API keys
```

---

## Need Help?

If you run into issues during cleanup, let me know:
- What command you ran
- What error message you got
- Output of `modal schedule list`

I can help troubleshoot!
