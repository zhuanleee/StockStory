# DigitalOcean Migration Guide

## Why DigitalOcean?

✅ **99.95% uptime SLA** (App Platform)
✅ **More reliable** than Railway (fewer outages)
✅ **Better pricing** - $5/month for always-on service
✅ **Auto-deploy** from GitHub (same as Railway)
✅ **Service credits** if SLA is breached

---

## Migration Overview

**Time Required:** ~15 minutes
**Downtime:** ~5 minutes (during webhook switch)
**Difficulty:** Easy (GitHub already connected)

---

## Step 1: Create DigitalOcean App

### A. Via DigitalOcean Dashboard

1. Go to: https://cloud.digitalocean.com/apps
2. Click **"Create App"**
3. Select **GitHub** as source
4. Choose repository: `zhuanleee/stock_scanner_bot`
5. Branch: `main`
6. Auto-deploy: ✅ **Enabled**
7. Click **"Next"**

### B. Configure App Settings

DigitalOcean will auto-detect the `.do/app.yaml` configuration file.

**Verify these settings:**
- **Name:** `stock-scanner-bot`
- **Region:** New York (NYC) - closest to US markets
- **Instance Size:** Basic XXS ($5/month)
- **Build Command:** `pip install --upgrade pip && pip install -r requirements.txt`
- **Run Command:** `python main.py api`
- **HTTP Port:** 5000
- **Health Check:** `/health`

Click **"Next"**

---

## Step 2: Add Environment Variables

### Required Variables

Go to **Settings → App-Level Environment Variables** and add:

```bash
# FINANCIAL DATA (Required)
POLYGON_API_KEY=<your_polygon_api_key>

# TELEGRAM (Required)
TELEGRAM_BOT_TOKEN=7626822299:AAHVNKOLIVelbBwOEO2J2aE_6D34Ml0RuuM
TELEGRAM_CHAT_ID=<your_chat_id_from_get_chat_id.py>

# AI SERVICES (Required)
DEEPSEEK_API_KEY=<your_deepseek_api_key>
XAI_API_KEY=<your_xai_api_key>

# EARNINGS INTELLIGENCE (Required)
ALPHA_VANTAGE_API_KEY=<your_alpha_vantage_api_key>
```

### Optional Variables

```bash
# ENHANCED FEATURES (Optional)
FINNHUB_API_KEY=<your_finnhub_api_key>
PATENTSVIEW_API_KEY=<your_patentsview_api_key>

# FEATURE FLAGS (Already set in app.yaml, but can override)
USE_AI_BRAIN_RANKING=true
USE_LEARNING_SYSTEM=true
MAX_CONCURRENT_SCANS=50
```

**Note:** Mark all API keys as **"Secret"** (encrypted at rest)

---

## Step 3: Deploy

1. Click **"Create Resources"**
2. Wait for deployment (~3-5 minutes)
3. Monitor build logs in real-time
4. Deployment complete when status shows **"Active"**

---

## Step 4: Get Your App URL

After deployment:

1. Go to **Settings → Domains**
2. Your app URL will be: `https://stock-scanner-bot-xxxxx.ondigitalocean.app`
3. **Save this URL** - you'll need it for the webhook

Example:
```
https://stock-scanner-bot-a4b2c.ondigitalocean.app
```

---

## Step 5: Update Telegram Webhook

### Delete Old Railway Webhook

```bash
curl -X POST "https://api.telegram.org/bot7626822299:AAHVNKOLIVelbBwOEO2J2aE_6D34Ml0RuuM/deleteWebhook"
```

Expected response:
```json
{"ok":true,"result":true,"description":"Webhook was deleted"}
```

### Set New DigitalOcean Webhook

```bash
# Replace YOUR_DO_APP_URL with your actual DigitalOcean app URL
curl -X POST "https://api.telegram.org/bot7626822299:AAHVNKOLIVelbBwOEO2J2aE_6D34Ml0RuuM/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://YOUR_DO_APP_URL.ondigitalocean.app/webhook"}'
```

Expected response:
```json
{"ok":true,"result":true,"description":"Webhook was set"}
```

### Verify Webhook

```bash
curl "https://api.telegram.org/bot7626822299:AAHVNKOLIVelbBwOEO2J2aE_6D34Ml0RuuM/getWebhookInfo"
```

Should show:
```json
{
  "ok": true,
  "result": {
    "url": "https://your-app.ondigitalocean.app/webhook",
    "has_custom_certificate": false,
    "pending_update_count": 0,
    "max_connections": 40
  }
}
```

---

## Step 6: Test Your Bot

### Test Health Endpoint

```bash
curl https://YOUR_DO_APP_URL.ondigitalocean.app/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2026-01-29...",
  "components": {
    "api": "healthy",
    "database": "healthy",
    "cache": "healthy"
  }
}
```

### Test Dashboard

Open in browser:
```
https://YOUR_DO_APP_URL.ondigitalocean.app
```

Should see:
- ✅ Dashboard loads
- ✅ "Intelligence" tab visible
- ✅ All visualizations rendering

### Test Telegram Bot

Send to `@Stocks_Story_Bot`:
```
/help
/status
/scan NVDA
/earnings NVDA
/exec TSLA
/top10
```

Should receive instant responses.

---

## Step 7: Monitor Deployment

### View Logs

1. Go to DigitalOcean Dashboard → Your App
2. Click **"Runtime Logs"**
3. Monitor for errors

### Check Metrics

1. Go to **"Insights"** tab
2. View:
   - CPU usage
   - Memory usage
   - Request rate
   - Response time

### Set Up Alerts

1. Go to **"Settings" → "Alerts"**
2. Add alert rules:
   - High CPU usage (>80%)
   - High memory usage (>90%)
   - Failed health checks

---

## Step 8: Clean Up Railway (Optional)

Once DigitalOcean is working:

1. Go to Railway Dashboard
2. Select your project: `stock_scanner_bot`
3. Click **Settings → Danger Zone**
4. Click **"Delete Project"**

This stops Railway charges.

---

## Troubleshooting

### Issue: Build fails with "requirements.txt not found"

**Solution:** DigitalOcean auto-detected wrong root directory.

Fix:
1. Go to **Settings → App Spec**
2. Add `source_dir: /`
3. Redeploy

### Issue: Health check failing

**Solution:** Increase health check timeout.

Fix:
1. Go to **Settings → App Spec**
2. Update health_check settings:
   ```yaml
   health_check:
     initial_delay_seconds: 120
     timeout_seconds: 20
   ```
3. Save and redeploy

### Issue: "Module not found" errors in logs

**Solution:** Missing dependencies.

Fix:
1. Check `requirements.txt` includes all dependencies
2. Add missing packages
3. Commit and push (auto-deploys)

### Issue: Telegram bot not responding

**Solution:** Webhook not configured correctly.

Fix:
1. Verify webhook URL in Step 5
2. Check app logs for webhook errors
3. Ensure `/webhook` endpoint is accessible:
   ```bash
   curl https://YOUR_APP_URL.ondigitalocean.app/webhook
   ```

### Issue: Out of memory errors

**Solution:** Upgrade instance size.

Fix:
1. Go to **Settings → Resources**
2. Upgrade to **Basic XS** ($12/month, 1GB RAM)
3. Redeploy

---

## Cost Comparison

### Railway (Your Current Setup)
- **Free tier:** 500 hours/month = ~20 days
- **After free tier:** $20-30/month
- **No SLA**

### DigitalOcean App Platform (New Setup)
- **Cost:** $5/month (Basic XXS, 512MB RAM)
- **SLA:** 99.95% uptime
- **Service credits:** If SLA breached
- **No hourly limits**

**Savings:** $15-25/month

---

## Performance Comparison

| Metric | Railway | DigitalOcean |
|--------|---------|--------------|
| Uptime SLA | None | 99.95% |
| Instance RAM | 512MB | 512MB |
| Cold starts | No | No (always-on) |
| Deploy time | 2-3 min | 3-5 min |
| Global CDN | Yes | Yes |
| Service credits | No | Yes |

---

## DigitalOcean Advantages

✅ **Formal SLA** - 99.95% uptime guarantee
✅ **Service Credits** - Compensation for downtime
✅ **Better Reliability** - Fewer incidents than Railway
✅ **Lower Cost** - $5/month vs $20-30/month
✅ **Same Auto-Deploy** - GitHub integration
✅ **Better Monitoring** - Built-in metrics and alerts
✅ **Scaling** - Easy upgrade to larger instances
✅ **No Hourly Limits** - True always-on service

---

## Post-Migration Checklist

- [ ] DigitalOcean app created and deployed
- [ ] All environment variables added
- [ ] App URL obtained
- [ ] Old Railway webhook deleted
- [ ] New DigitalOcean webhook configured
- [ ] Webhook verified with getWebhookInfo
- [ ] Health endpoint returning 200 OK
- [ ] Dashboard loading in browser
- [ ] Telegram bot responding to commands
- [ ] Logs show no errors
- [ ] Alerts configured
- [ ] Railway project deleted (optional)

---

## Quick Reference

**App URL Structure:**
```
https://stock-scanner-bot-[random].ondigitalocean.app
```

**Webhook URL:**
```
https://your-app.ondigitalocean.app/webhook
```

**Health Check URL:**
```
https://your-app.ondigitalocean.app/health
```

**Dashboard URL:**
```
https://your-app.ondigitalocean.app
```

---

## Support

**DigitalOcean Docs:** https://docs.digitalocean.com/products/app-platform/
**Telegram Bot API:** https://core.telegram.org/bots/api
**Your Bot:** @Stocks_Story_Bot
**Status Page:** https://status.digitalocean.com

---

## Summary

Migration steps:
1. ✅ Create app on DigitalOcean (5 min)
2. ✅ Add environment variables (3 min)
3. ✅ Deploy and get URL (5 min)
4. ✅ Update Telegram webhook (2 min)
5. ✅ Test everything (5 min)

**Total time:** ~20 minutes
**Result:** More reliable bot at lower cost with 99.95% SLA

---

**Last Updated:** 2026-01-29
**Bot:** @Stocks_Story_Bot
**Status:** Ready for DigitalOcean migration ✅
