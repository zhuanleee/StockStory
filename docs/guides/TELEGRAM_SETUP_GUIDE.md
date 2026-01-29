# Telegram Bot Setup Guide

## ✅ Your Bot Information

**Bot Token**: `7626822299:AAHVNKOLIVelbBwOEO2J2aE_6D34Ml0RuuM`
**Bot Username**: `@Stocks_Story_Bot`
**Bot Name**: Stocks Story
**Bot ID**: 7626822299

---

## 📱 Step 1: Get Your Chat ID

### A. Send a Message to Your Bot

1. Open Telegram on your phone or desktop
2. Search for: `@Stocks_Story_Bot`
3. Click "Start" or send: `/start`
4. You should see a message that the bot received your message

### B. Run the Script to Get Your Chat ID

```bash
python3 get_chat_id.py
```

This will display your Chat ID. **Save this number** - you'll need it for Railway!

Example output:
```
Chat ID: 123456789
Type: private
Name: Your Name
```

---

## ⚙️ Step 2: Configure Railway Environment Variables

### Go to Railway Dashboard

1. Open: https://railway.app/dashboard
2. Select your project: `stock_scanner_bot`
3. Click on "Variables" tab
4. Add the following variables:

```bash
# TELEGRAM (Required)
TELEGRAM_BOT_TOKEN=7626822299:AAHVNKOLIVelbBwOEO2J2aE_6D34Ml0RuuM
TELEGRAM_CHAT_ID=YOUR_CHAT_ID_FROM_STEP_1

# DATA SOURCES (Required)
POLYGON_API_KEY=your_polygon_api_key_here

# AI SERVICES (Required for full functionality)
DEEPSEEK_API_KEY=your_deepseek_api_key_here
XAI_API_KEY=your_xai_api_key_here

# EARNINGS INTELLIGENCE (Required for earnings analysis)
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_api_key_here

# OPTIONAL (Enhance features)
FINNHUB_API_KEY=your_finnhub_key_here
PATENTSVIEW_API_KEY=your_patents_key_here
USE_AI_BRAIN_RANKING=true
USE_LEARNING_SYSTEM=true
MAX_CONCURRENT_SCANS=50
```

### Save and Deploy

Railway will automatically redeploy when you add/change variables.

---

## 🔗 Step 3: Configure Webhook (After Railway Deployment)

### Wait for Deployment

1. Go to Railway Dashboard → Deployments
2. Wait until status shows "Deployed" (~2-3 minutes)
3. Note your Railway app URL (e.g., `your-app-name.railway.app`)

### Set Webhook

Run this command (replace `YOUR_RAILWAY_URL` with your actual Railway URL):

```bash
curl -X POST "https://api.telegram.org/bot7626822299:AAHVNKOLIVelbBwOEO2J2aE_6D34Ml0RuuM/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://YOUR_RAILWAY_URL.railway.app/webhook"}'
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
    "url": "https://your-app.railway.app/webhook",
    "has_custom_certificate": false,
    "pending_update_count": 0
  }
}
```

---

## ✅ Step 4: Test Your Bot

### Test via Telegram

Send these commands to `@Stocks_Story_Bot`:

```
/help           - Show all commands
/status         - System status
/scan NVDA      - Scan specific ticker
/top10          - Show top 10 stocks
```

### Test Health Endpoint

```bash
curl https://YOUR_RAILWAY_URL.railway.app/health
```

Expected:
```json
{
  "status": "healthy",
  "timestamp": "2026-01-29...",
  "components": {...}
}
```

### Test Dashboard

Open in browser:
```
https://YOUR_RAILWAY_URL.railway.app
```

Click "Intelligence" tab - should show all visualizations.

---

## 🎯 Available Commands

Once your bot is working, you can use:

### Scanning
```
/scan              - Full market scan
/scan NVDA         - Scan specific ticker
/top10             - Top 10 stocks
/watch add NVDA    - Add to watchlist
/watch list        - View watchlist
```

### Intelligence (NEW)
```
/trends NVDA       - Google Trends analysis
/exec NVDA         - Executive commentary
/earnings NVDA     - Earnings analysis
/sympathy NVDA     - Related stocks (supply chain)
/rotation          - Sector rotation forecast
/institutional     - Institutional flow summary
```

### Learning System
```
/weights           - Show learned component weights
/stats             - Learning system statistics
/trades            - Trade history
```

### System
```
/status            - System health check
/health            - Detailed health status
/help              - Show all commands
```

---

## 🐛 Troubleshooting

### Issue: "Chat not found" or no response

**Solution**: Make sure you sent `/start` to the bot first, and your `TELEGRAM_CHAT_ID` is correct.

### Issue: Webhook not working

**Solution**:
1. Check Railway deployment logs for errors
2. Verify webhook URL is correct
3. Delete and recreate webhook:
```bash
curl -X POST "https://api.telegram.org/bot7626822299:AAHVNKOLIVelbBwOEO2J2aE_6D34Ml0RuuM/deleteWebhook"
# Then set it again
```

### Issue: "API key not configured"

**Solution**: Add missing environment variable in Railway dashboard and redeploy.

### Issue: Bot responds slowly

**Solution**:
- Reduce `MAX_CONCURRENT_SCANS` to 30
- Check Railway logs for performance issues
- Ensure all API keys are valid

---

## 📊 What Your Bot Can Do

### Real-time Stock Analysis
- Scans 1400+ liquid stocks
- 10 data sources integrated
- 6-component AI learning system
- Story-first methodology

### Intelligence Features
- X/Twitter sentiment (xAI Grok)
- Google Trends breakouts
- Earnings call analysis
- Executive commentary tracking
- Government contracts
- Patent activity
- Sector rotation predictions
- Institutional flow tracking

### Dashboard
- Live visualizations
- 7 intelligence charts
- Real-time updates
- Interactive supply chain maps

---

## 🔒 Security Notes

- ✅ Bot token is stored securely in Railway environment variables
- ✅ Webhook uses HTTPS
- ✅ No sensitive data in git repository
- ✅ Rate limiting enabled on API endpoints

---

## 📈 Cost Estimate

**Free Tier** (Recommended):
- Railway: Free (500 hrs/month)
- Polygon: Free (your unlimited tier)
- Alpha Vantage: Free (25 calls/day)
- xAI: ~$0.10/week
- DeepSeek: ~$0.05/week

**Total: ~$0.60/month**

---

## 🚀 Quick Start Checklist

- [ ] Send `/start` to @Stocks_Story_Bot
- [ ] Run `python3 get_chat_id.py` to get Chat ID
- [ ] Add all environment variables to Railway
- [ ] Wait for Railway deployment (2-3 min)
- [ ] Configure webhook with Railway URL
- [ ] Test: Send `/help` to bot
- [ ] Test: Open Railway dashboard URL
- [ ] Test: Send `/scan NVDA` to bot

---

## 📞 Support

**Issues**: https://github.com/zhuanleee/stock_scanner_bot/issues
**Docs**: Check `/docs` folder in repository
**Verification**: Run `python3 verify_deployment.py`

---

**Last Updated**: 2026-01-29
**Bot**: @Stocks_Story_Bot
**Status**: Ready for deployment ✅
