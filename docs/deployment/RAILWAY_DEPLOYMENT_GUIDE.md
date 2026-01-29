# Railway Deployment Guide

## 🚀 Complete Deployment Instructions

### Prerequisites

1. **GitHub Repository**: Code pushed to `stock_scanner_bot` repo
2. **Railway Account**: Connected to GitHub
3. **API Keys**: Ready to configure

---

## Step 1: Verify Local Setup

Run the verification script:

```bash
python3 verify_deployment.py
```

Expected output: All checks should pass except environment variables (configured in Railway).

---

## Step 2: Push to GitHub

All code is already committed and pushed. Verify:

```bash
git status
git log --oneline -1
```

Latest commit should be: "Complete framework integration: earnings analysis, executive commentary, and intelligence enhancements"

---

## Step 3: Configure Railway Environment Variables

### Required Variables

In Railway dashboard → Your Project → Variables, add:

```bash
# Market Data (REQUIRED)
POLYGON_API_KEY=your_polygon_api_key_here

# Telegram (REQUIRED for notifications)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_telegram_chat_id_here

# AI Services (REQUIRED for full functionality)
DEEPSEEK_API_KEY=your_deepseek_api_key_here
XAI_API_KEY=your_xai_api_key_here

# Earnings Intelligence (REQUIRED for transcript analysis)
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_api_key_here
```

### Optional Variables

```bash
# Alternative Data Sources
FINNHUB_API_KEY=your_finnhub_key
PATENTSVIEW_API_KEY=your_patents_key
OPENAI_API_KEY=your_openai_key

# Feature Flags
USE_AI_BRAIN_RANKING=true
USE_LEARNING_SYSTEM=true
USE_GOOGLE_TRENDS=true

# Scanner Settings
MIN_MARKET_CAP=300000000
MAX_CONCURRENT_SCANS=50
```

---

## Step 4: Deploy on Railway

### Option A: Automatic Deployment (Recommended)

1. Railway auto-deploys when you push to `main` branch
2. Check deployment status in Railway dashboard
3. View logs: Click "Deployments" → "View Logs"

### Option B: Manual Deployment

1. Go to Railway dashboard
2. Click "Deploy" → "Deploy Now"
3. Wait for build to complete (~2-3 minutes)

---

## Step 5: Set Up Telegram Webhook

After deployment, your app will be available at: `https://your-app.railway.app`

### Configure Webhook

Run this command (replace with your actual URL and bot token):

```bash
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your-app.railway.app/webhook",
    "allowed_updates": ["message", "callback_query"]
  }'
```

Expected response:
```json
{
  "ok": true,
  "result": true,
  "description": "Webhook was set"
}
```

### Verify Webhook

```bash
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo"
```

Should show:
```json
{
  "url": "https://your-app.railway.app/webhook",
  "has_custom_certificate": false,
  "pending_update_count": 0
}
```

---

## Step 6: Test Deployment

### Test Health Endpoint

```bash
curl https://your-app.railway.app/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2026-01-29T18:35:00",
  "components": {
    "api": "ok",
    "learning_system": "ok",
    "data_sources": 8
  }
}
```

### Test Telegram Bot

Send a message to your Telegram bot:

```
/help
```

Expected response:
```
📱 Stock Scanner Bot Commands

📊 Scanning:
  /scan - Run full market scan
  /scan NVDA - Scan specific ticker
  /top10 - Show top 10 stocks

📈 Intelligence:
  /trends NVDA - Google Trends analysis
  /exec NVDA - Executive commentary
  /earnings NVDA - Earnings analysis
  /sympathy NVDA - Related stocks

🧠 Learning:
  /weights - Show learned component weights
  /stats - Learning system statistics

⚙️ Settings:
  /status - System status
  /help - Show this help
```

---

## Step 7: Verify All Features

### 1. Basic Scanning
```
/scan NVDA
```

Should return stock analysis with:
- Story score
- Theme identification
- Technical confirmation
- Earnings intelligence
- Executive commentary

### 2. Intelligence Features
```
/trends NVDA
/exec NVDA
/earnings NVDA
```

Should return:
- Google Trends search interest
- Executive sentiment analysis
- Earnings call insights

### 3. Learning System
```
/weights
/stats
```

Should show:
- Current component weights
- Learning confidence
- Trade history

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Railway Deployment                    │
└─────────────────────────────────────────────────────────┘
                          │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   Flask API  │  │ Telegram Bot │  │   Scanner    │
│  (gunicorn)  │  │  (webhook)   │  │   (async)    │
└──────────────┘  └──────────────┘  └──────────────┘
        │                │                │
        └────────────────┼────────────────┘
                         ▼
                ┌──────────────────┐
                │ Data Sources (10)│
                ├──────────────────┤
                │ • Polygon        │
                │ • Alpha Vantage  │
                │ • xAI (Grok)     │
                │ • DeepSeek       │
                │ • Google Trends  │
                │ • SEC Edgar      │
                │ • StockTwits     │
                │ • Reddit         │
                │ • Patents        │
                │ • Contracts      │
                └──────────────────┘
                         ▼
                ┌──────────────────┐
                │ Learning System  │
                │ (6 components)   │
                └──────────────────┘
```

---

## Monitoring & Logs

### View Logs

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login
railway login

# View logs
railway logs
```

### Common Issues

**Issue**: Deployment fails with "Module not found"
- **Fix**: Check `requirements.txt` includes all dependencies
- Run: `pip freeze > requirements.txt`

**Issue**: Telegram webhook not working
- **Fix**: Verify webhook URL is correct
- Check: `https://api.telegram.org/bot<TOKEN>/getWebhookInfo`

**Issue**: "API key not configured"
- **Fix**: Add missing API key to Railway environment variables
- Restart deployment after adding

**Issue**: Scanner timeout
- **Fix**: Increase `MAX_CONCURRENT_SCANS` environment variable
- Default is 50, try 30 for slower systems

---

## Performance Optimization

### Railway Free Tier Limits
- 512 MB RAM
- 1 vCPU
- 500 hours/month

### Optimize for Free Tier

1. **Reduce Concurrent Scans**
   ```bash
   MAX_CONCURRENT_SCANS=30
   ```

2. **Enable Caching**
   - Transcripts: 90 days
   - Analysis: 7 days
   - Commentary: 12 hours

3. **Limit Universe**
   ```bash
   MIN_MARKET_CAP=500000000  # Focus on larger caps
   ```

---

## Cost Breakdown

### Free Tier (Typical Usage)
- **Railway**: Free (500 hrs/month)
- **Polygon**: Free (unlimited tier)
- **xAI**: ~$0.10/week (50 tickers)
- **DeepSeek**: ~$0.05/week (analysis)
- **Alpha Vantage**: Free (25 calls/day)
- **Total**: ~$0.60/month

### Paid Tier (Heavy Usage)
- **Railway**: $5/month (Hobby plan)
- **Polygon**: $0 (unlimited tier)
- **xAI**: ~$1/week (500 tickers)
- **DeepSeek**: ~$0.50/week
- **Alpha Vantage**: Free tier sufficient
- **Total**: ~$11/month

---

## Data Sources Status

After deployment, check data sources:

```bash
curl https://your-app.railway.app/api/system/status
```

Expected response:
```json
{
  "status": "operational",
  "data_sources": {
    "polygon": "✓ configured",
    "alpha_vantage": "✓ configured",
    "xai": "✓ configured",
    "deepseek": "✓ configured",
    "google_trends": "✓ available (no key needed)",
    "sec_edgar": "✓ available (no key needed)",
    "stocktwits": "✓ available (no key needed)",
    "reddit": "✓ available (no key needed)",
    "patents": "- not configured (optional)",
    "telegram": "✓ configured"
  },
  "features": {
    "ai_brain_ranking": "enabled",
    "learning_system": "enabled",
    "x_intelligence": "enabled",
    "google_trends": "enabled",
    "earnings_analysis": "enabled",
    "executive_commentary": "enabled",
    "sector_rotation": "enabled",
    "institutional_flow": "enabled"
  },
  "learning_system": {
    "component_count": 6,
    "weights": {
      "theme": 0.26,
      "technical": 0.22,
      "ai": 0.22,
      "sentiment": 0.18,
      "earnings": 0.05,
      "institutional": 0.07
    },
    "confidence": 0.50,
    "sample_size": 0
  }
}
```

---

## Troubleshooting

### Logs Show "Import Error"
```bash
# Check if module is in requirements.txt
grep "module_name" requirements.txt

# If missing, add it locally and push
pip freeze | grep module_name >> requirements.txt
git add requirements.txt
git commit -m "Add missing dependency"
git push
```

### Telegram Not Responding
```bash
# Check webhook
curl https://api.telegram.org/bot<TOKEN>/getWebhookInfo

# Reset webhook
curl -X POST https://api.telegram.org/bot<TOKEN>/setWebhook \
  -d "url=https://your-app.railway.app/webhook"

# Check Railway logs
railway logs | grep telegram
```

### Slow Scans
```bash
# Reduce concurrent scans in Railway variables
MAX_CONCURRENT_SCANS=20

# Or limit universe
MIN_MARKET_CAP=1000000000  # $1B+ only
```

---

## Security Checklist

- [ ] API keys stored in Railway environment variables (NOT in code)
- [ ] `.env` file in `.gitignore`
- [ ] Telegram webhook uses HTTPS
- [ ] Railway app has unique domain
- [ ] Database credentials (if used) are secure
- [ ] Rate limiting enabled on API endpoints

---

## Next Steps After Deployment

1. **Test All Features**: Run `/help` in Telegram, test each command
2. **Monitor Logs**: Watch Railway logs for errors
3. **Check Costs**: Monitor xAI and DeepSeek usage
4. **Optimize Performance**: Adjust `MAX_CONCURRENT_SCANS` based on response time
5. **Add Watchlist**: Use `/watch add NVDA` to start tracking stocks
6. **Review Learning**: Check `/stats` daily to see learning progress

---

## Support

**Issues**: https://github.com/your-username/stock_scanner_bot/issues
**Docs**: Check `/docs` folder in repository
**Logs**: `railway logs` command

---

## Quick Reference

```bash
# Deployment
git push origin main                    # Auto-deploys on Railway

# Logs
railway logs                            # View deployment logs
railway logs --tail                     # Follow logs

# Status
curl https://your-app.railway.app/health           # Health check
curl https://your-app.railway.app/api/system/status # Full status

# Telegram
/help                                   # Show all commands
/status                                 # System status
/scan                                   # Run market scan
```

---

**Status**: ✅ DEPLOYMENT READY
**Version**: 2.0 (Complete Integration)
**Last Updated**: 2026-01-29
