# Telegram Bot Setup Guide

## Bot Information

**Bot Username**: `@Stocks_Story_Bot`
**Bot Name**: Stocks Story

---

## Step 1: Get Your Chat ID

### A. Send a Message to Your Bot

1. Open Telegram on your phone or desktop
2. Search for: `@Stocks_Story_Bot`
3. Click "Start" or send: `/start`
4. You should see a message that the bot received your message

### B. Run the Script to Get Your Chat ID

```bash
python3 scripts/deployment/get_chat_id.py
```

This will display your Chat ID. **Save this number** - you'll need it for Modal!

Example output:
```
Chat ID: 123456789
Type: private
Name: Your Name
```

---

## Step 2: Configure Modal Secrets

### Install Modal CLI

```bash
pip install modal
modal setup
```

### Create Modal Secret

```bash
modal secret create Stock_Story \
  TELEGRAM_BOT_TOKEN=your_bot_token_here \
  TELEGRAM_CHAT_ID=your_chat_id_from_step_1 \
  POLYGON_API_KEY=your_polygon_api_key \
  DEEPSEEK_API_KEY=your_deepseek_api_key \
  XAI_API_KEY=your_xai_api_key \
  ALPHA_VANTAGE_API_KEY=your_alpha_vantage_api_key
```

### Verify Secret

```bash
modal secret list
```

---

## Step 3: Deploy to Modal

### Deploy All Services

```bash
# Deploy main scanner with Telegram bot
modal deploy modal_scanner.py

# Deploy Tier 3 intelligence jobs
modal deploy modal_intelligence_jobs.py
```

### Verify Deployment

```bash
modal app list
```

Should show your deployed apps.

---

## Step 4: Test Your Bot

### Test via Telegram

Send these commands to `@Stocks_Story_Bot`:

```
/help           - Show all commands
/status         - System status
/scan NVDA      - Scan specific ticker
/top10          - Show top 10 stocks
```

### Test Dashboard

Open in browser:
```
https://zhuanleee.github.io/stock_scanner_bot/
```

Click "Intelligence" tab - should show all visualizations.

---

## Available Commands

Once your bot is working, you can use:

### Scanning
```
/scan              - Full market scan
/scan NVDA         - Scan specific ticker
/top10             - Top 10 stocks
/watch add NVDA    - Add to watchlist
/watch list        - View watchlist
```

### Intelligence
```
/trends NVDA       - Google Trends analysis
/exec NVDA         - Executive commentary
/earnings NVDA     - Earnings analysis
/sympathy NVDA     - Related stocks (supply chain)
/rotation          - Sector rotation forecast
/institutional     - Institutional flow summary
```

### Exit Strategy
```
/exit NVDA         - Check exit signals
/exitall           - Monitor all positions
/targets NVDA      - Show price targets
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

## Troubleshooting

### Issue: "Chat not found" or no response

**Solution**: Make sure you sent `/start` to the bot first, and your `TELEGRAM_CHAT_ID` is correct in Modal secrets.

### Issue: Bot not responding

**Solution**:
1. Check Modal logs: `modal app logs modal_scanner`
2. Verify secrets are set: `modal secret list`
3. Redeploy: `modal deploy modal_scanner.py`

### Issue: "API key not configured"

**Solution**: Update Modal secret with missing key:
```bash
modal secret create Stock_Story \
  --force \
  MISSING_KEY=your_value
```

---

## What Your Bot Can Do

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
- Live at: https://zhuanleee.github.io/stock_scanner_bot/
- 7 intelligence charts
- Interactive visualizations

---

## Security Notes

- Bot token stored securely in Modal secrets (encrypted)
- No sensitive data in git repository
- Rate limiting enabled on API endpoints

---

## Cost Estimate

| Service | Monthly Cost |
|---------|-------------|
| Modal.com | $2-3 |
| GitHub Pages | Free |
| Polygon | Your plan |
| xAI | ~$0.50/week |
| DeepSeek | ~$0.25/week |
| **Total** | **~$5-6/month** |

---

## Quick Start Checklist

- [ ] Send `/start` to @Stocks_Story_Bot
- [ ] Run `python3 scripts/deployment/get_chat_id.py` to get Chat ID
- [ ] Install Modal CLI: `pip install modal && modal setup`
- [ ] Create Modal secret with all API keys
- [ ] Deploy: `modal deploy modal_scanner.py`
- [ ] Test: Send `/help` to bot
- [ ] Test: Open https://zhuanleee.github.io/stock_scanner_bot/
- [ ] Test: Send `/scan NVDA` to bot

---

## Support

**Issues**: https://github.com/zhuanleee/stock_scanner_bot/issues
**Docs**: Check `/docs` folder in repository
**Dashboard**: https://zhuanleee.github.io/stock_scanner_bot/

---

**Last Updated**: 2026-02-02
**Bot**: @Stocks_Story_Bot
**Deployment**: Modal.com + GitHub Pages
