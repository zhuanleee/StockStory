# Modal Deployment Guide

**Complete guide to deploying Tier 3 Intelligence Jobs on Modal**

---

## Overview

Modal hosts the scheduled intelligence jobs (cron jobs) for:
- **3-Layer Crisis Monitoring** (hourly)
- **Exit Signal Detection** (daily 6 AM PST)
- **Meme Stock Scanning** (daily 2 PM PST)
- **Sector Rotation Analysis** (weekly Sunday 8 PM PST)

**Why Modal?**
- Serverless auto-scaling
- Built-in cron scheduling
- Pay-per-use pricing ($2-3/month)
- 5 cron jobs on free tier

---

## Prerequisites

1. **Modal Account**
   - Sign up at https://modal.com
   - Free tier includes 5 cron jobs

2. **API Keys Required**
   - `XAI_API_KEY` - xAI Grok for X/Twitter intelligence
   - `TELEGRAM_BOT_TOKEN` - For alerts
   - `TELEGRAM_CHAT_ID` - Your Telegram chat ID

3. **Python Environment**
   ```bash
   pip install modal
   ```

---

## Step 1: Modal Setup

### Install Modal CLI

```bash
pip install modal
```

### Authenticate

```bash
modal setup
```

This will:
1. Open browser for authentication
2. Create `~/.modal.toml` with credentials
3. Verify connection to Modal servers

---

## Step 2: Create Secrets

Modal stores sensitive data in **secrets** (encrypted environment variables).

### Create Stock_Story Secret

```bash
modal secret create Stock_Story \
  XAI_API_KEY="xai-your-key-here" \
  TELEGRAM_BOT_TOKEN="1234567890:ABC-DEF..." \
  TELEGRAM_CHAT_ID="1191814045"
```

### Verify Secret

```bash
modal secret list
```

Should show:
```
Stock_Story (3 keys)
```

---

## Step 3: Deploy Crisis Monitoring

**File:** `modal_scanner.py`

This deploys:
- Hourly crisis monitoring (3-layer verification)
- X + Web + Data intelligence

### Deploy

```bash
cd /path/to/stock_scanner_bot
modal deploy modal_scanner.py
```

### Expected Output

```
✓ Initialized. View run at https://modal.com/...
✓ Created objects.
├── 🔨 Created mount /root
├── 🔨 Created image stock-scanner-img
├── 🔨 Created health_check
├── 🔨 Created run_x_intelligence_check (cron: 0 */1 * * *)
└── 🔨 Created test_x_intelligence
✓ App deployed! 🎉

View at: https://modal.com/apps/ap-xxx
```

---

## Step 4: Deploy Tier 3 Intelligence

**File:** `modal_intelligence_jobs.py`

This deploys:
- Exit signal detection (daily 6 AM PST)
- Meme stock scanning (daily 2 PM PST)
- Sector rotation (weekly Sunday 8 PM PST)

### Deploy

```bash
modal deploy modal_intelligence_jobs.py
```

### Expected Output

```
✓ Initialized. View run at https://modal.com/...
✓ Created objects.
├── 🔨 Created daily_exit_signal_check (cron: 0 14 * * *)
├── 🔨 Created daily_meme_stock_scan (cron: 0 22 * * *)
└── 🔨 Created weekly_sector_rotation_analysis (cron: 0 4 * * 1)
✓ App deployed! 🎉
```

---

## Step 5: Verify Deployment

### List Apps

```bash
modal app list
```

Should show:
```
stock-scanner
├── health_check
├── run_x_intelligence_check (cron: hourly)
├── daily_exit_signal_check (cron: daily 6 AM PST)
├── daily_meme_stock_scan (cron: daily 2 PM PST)
└── weekly_sector_rotation_analysis (cron: weekly)
```

### Check Logs

```bash
# View recent logs
modal app logs stock-scanner

# Stream live logs
modal app logs stock-scanner --follow
```

---

## Step 6: Test Jobs Manually

Before waiting for cron schedule, test each job manually:

### Test Exit Signal Detection

```bash
modal run modal_intelligence_jobs.py::daily_exit_signal_check
```

**Expected output:**
```
======================================================================
🛡️  TIER 3: EXIT SIGNAL DETECTION
======================================================================
Checking 5 holdings for negative sentiment & red flags...
======================================================================

✅ All holdings clear - no exit signals

EXIT SIGNAL SUMMARY:
  Holdings checked: 5
  Exit signals: 0
  Critical: 0
  High: 0
  Medium: 0
======================================================================
```

### Test Meme Stock Scanner

```bash
modal run modal_intelligence_jobs.py::daily_meme_stock_scan
```

**Expected output:**
```
======================================================================
🚀 TIER 3: MEME STOCK DETECTION
======================================================================
Scanning for viral momentum on X/Twitter...
======================================================================
Scanning 150 tickers...

🎯 Found 3 stocks with viral momentum!

🔥 TSLA:
   Meme Score: 7.5/10
   Mentions/hr: 1200
   Sentiment: bullish (8)
   🚨 HIGH VIRAL POTENTIAL - Early entry opportunity!
   ✓ Alert sent
...
```

### Test Sector Rotation

```bash
modal run modal_intelligence_jobs.py::weekly_sector_rotation_analysis
```

**Expected output:**
```
======================================================================
📊 TIER 3: SECTOR ROTATION ANALYSIS
======================================================================
Analyzing sector sentiment for rotation signals...
======================================================================

SECTOR ROTATION SIGNALS:
======================================================================

🟢 STRONGEST SECTORS (Overweight):
   Technology: 6.5 (STRONG_POSITIVE) - OVERWEIGHT
   Healthcare: 4.2 (POSITIVE) - HOLD
   Energy: 3.8 (POSITIVE) - HOLD

🔴 WEAKEST SECTORS (Underweight):
   Finance: -2.1 (NEGATIVE) - UNDERWEIGHT
   RealEstate: -3.5 (NEGATIVE) - ROTATE_OUT
   Utilities: -1.5 (NEGATIVE) - HOLD

✓ Weekly report sent
======================================================================
```

### Test Crisis Monitoring

```bash
modal run modal_scanner.py::run_x_intelligence_check
```

**Expected output:**
```
======================================================================
🚨 X INTELLIGENCE CRISIS CHECK
======================================================================
Checking X/Twitter for market-moving crises...
======================================================================

Layer 1: X Intelligence (Social Detection)
✓ Searching X for crisis topics...
✓ Found 0 high-severity topics

Layer 2: Web Intelligence (News Verification)
(Skipped - no crises detected)

Layer 3: Data Intelligence (Market Data)
(Skipped - no crises detected)

✅ ALL CLEAR - No market-moving crises detected
======================================================================
```

---

## Cron Schedule Reference

| Job | Schedule | Time (PST) | Frequency |
|-----|----------|------------|-----------|
| Crisis monitoring | `0 */1 * * *` | Every hour | 24x/day |
| Exit signals | `0 14 * * *` | 6 AM | Daily |
| Meme scanner | `0 22 * * *` | 2 PM | Daily |
| Sector rotation | `0 4 * * 1` | Sun 8 PM | Weekly |

**Cron format:** `minute hour day_of_month month day_of_week`

**UTC Conversion:**
- PST = UTC - 8 hours
- 6 AM PST = 14:00 UTC
- 2 PM PST = 22:00 UTC
- 8 PM PST = 04:00 UTC (next day)

---

## Monitoring & Debugging

### View Dashboard

1. Go to https://modal.com
2. Click on "stock-scanner" app
3. View:
   - Job execution history
   - Logs for each run
   - Error rates
   - Execution times
   - Cost tracking

### Check Job Status

```bash
# List all jobs with status
modal app list

# View specific job logs
modal run modal_intelligence_jobs.py::daily_exit_signal_check --detach
modal logs <run-id>
```

### Debug Failed Jobs

If a job fails:

1. **Check logs:**
   ```bash
   modal app logs stock-scanner | grep ERROR
   ```

2. **Common issues:**
   - Missing secrets (check `modal secret list`)
   - API rate limits (check xAI usage)
   - Network timeouts (increase timeout in code)
   - Import errors (check dependencies in `modal_scanner.py`)

3. **Test locally:**
   ```bash
   # Run without Modal (won't use secrets)
   python -c "from modal_intelligence_jobs import daily_exit_signal_check; daily_exit_signal_check()"
   ```

---

## Cost Management

### Monitor Usage

```bash
# View Modal usage dashboard
modal app show stock-scanner
```

### Cost Breakdown

| Component | Monthly Cost | Notes |
|-----------|-------------|-------|
| Crisis monitoring | $0.50 | 24 runs/day × $0.0007 |
| Exit signals | $0.30 | 30 runs/month × $0.01 |
| Meme scanner | $0.90 | 30 runs/month × $0.03 |
| Sector rotation | $0.04 | 4 runs/month × $0.01 |
| **Total** | **$1.74** | Without optimizations |
| **With cache** | **$0.70** | 60% reduction |
| **With batch** | **$0.02** | Meme scan optimized |
| **Final Total** | **$2-3** | All optimizations |

### Optimization Tips

1. **Caching**: 5-minute TTL reduces repeated calls by 80%
2. **Batch queries**: 50 tickers per query (vs 150 individual calls)
3. **Quality filters**: Less data processed = faster = cheaper
4. **Schedule timing**: Avoid market hours overlap

---

## Troubleshooting

### Issue: "Secret not found"

**Solution:**
```bash
modal secret list  # Check if Stock_Story exists
modal secret create Stock_Story XAI_API_KEY=xxx ...
```

### Issue: "xai_sdk not found"

**Solution:** Check `modal_scanner.py` image definition includes `xai-sdk`:
```python
image = (
    modal.Image.debian_slim()
    .pip_install("xai-sdk", ...)
)
```

### Issue: Telegram alerts not sending

**Solution:**
1. Check `TELEGRAM_CHAT_ID` is numeric (not @username)
   ```bash
   python scripts/deployment/get_chat_id.py
   ```
2. Verify bot token:
   ```bash
   curl https://api.telegram.org/bot<TOKEN>/getMe
   ```

### Issue: Job times out

**Solution:** Increase timeout in job decorator:
```python
@app.function(
    timeout=900,  # 15 minutes (was 600)
    ...
)
```

---

## Updating Deployment

### Update Code

1. **Make changes** to `modal_scanner.py` or `modal_intelligence_jobs.py`
2. **Commit and push** to GitHub
3. **Re-deploy:**
   ```bash
   modal deploy modal_scanner.py
   modal deploy modal_intelligence_jobs.py
   ```

### Update Secrets

```bash
# Update existing secret
modal secret create Stock_Story \
  XAI_API_KEY="new-key" \
  --force  # Overwrite existing
```

---

## Stopping/Removing Jobs

### Stop App (Pause Cron Jobs)

```bash
modal app stop stock-scanner
```

### Resume App

```bash
# Jobs auto-resume on next deploy
modal deploy modal_scanner.py
```

### Delete App Completely

```bash
modal app delete stock-scanner
```

**Warning:** This removes all jobs and logs. Cannot be undone.

---

## Best Practices

### 1. Version Control
- Always commit changes before deploying
- Tag releases: `git tag v3.0.0 && git push --tags`

### 2. Testing
- Test manually before relying on cron
- Monitor first 24 hours after deployment

### 3. Monitoring
- Check Modal dashboard daily first week
- Set up alerts for job failures (Modal UI)

### 4. Cost Control
- Review usage weekly: https://modal.com/billing
- Adjust cron frequency if costs exceed budget

### 5. Security
- Never commit secrets to Git
- Rotate API keys quarterly
- Use Modal secrets for all sensitive data

---

## Next Steps

1. ✅ Deploy Modal jobs
2. ✅ Test each job manually
3. ✅ Monitor logs for 24 hours
4. ✅ Verify Telegram alerts received
5. ⏳ Wait for first cron execution
6. ✅ Check cost usage after 1 week

---

## Support

**Modal Documentation:** https://modal.com/docs
**Stock Scanner Issues:** https://github.com/zhuanleee/stock_scanner_bot/issues
**Modal Support:** support@modal.com

---

**Deployment complete! 🚀**

Your Tier 3 Intelligence System is now running on autopilot.
