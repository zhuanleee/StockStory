# Deployment Status

**Last Updated:** 2026-02-02

---

## Current Production Stack

| Component | Platform | Status | Cost |
|-----------|----------|--------|------|
| **Intelligence Jobs** | Modal.com | Active | $2-3/month |
| **Crisis Monitoring** | Modal.com | Active | Included |
| **Telegram Bot** | Modal.com | Active | Included |
| **Dashboard** | GitHub Pages | Active | Free |

**Live Links:**
- **Dashboard:** https://zhuanleee.github.io/StockStory/
- **Telegram Bot:** [@Stocks_Story_Bot](https://t.me/Stocks_Story_Bot)

---

## Active Deployments

### Modal.com (Backend Services)

**URL:** https://modal.com/apps

**Deployed Apps:**
- `modal_scanner.py` - Crisis monitoring (hourly)
- `modal_intelligence_jobs.py` - Tier 3 intelligence

**Cron Jobs:**
| Job | Schedule | Description |
|-----|----------|-------------|
| Crisis Monitor | Every hour | X/Twitter crisis detection |
| Exit Signal Detector | 6 AM PST daily | Holdings red flag check |
| Meme Stock Scanner | 2 PM PST daily | Viral momentum detection |
| Sector Rotation | Sunday 8 PM PST | Weekly sector analysis |

**Telegram Bot:**
- Webhook endpoint deployed on Modal
- Receives commands from @Stocks_Story_Bot
- Sends alerts for exits, crises, and scans

**Secrets Configured:**
- `Stock_Story` secret with all API keys:
  - `POLYGON_API_KEY`
  - `XAI_API_KEY`
  - `DEEPSEEK_API_KEY`
  - `ALPHA_VANTAGE_API_KEY`
  - `TELEGRAM_BOT_TOKEN`
  - `TELEGRAM_CHAT_ID`

### GitHub Pages (Dashboard)

**URL:** https://zhuanleee.github.io/stock_scanner_bot/

**Source:** `docs/` folder on `main` branch

**Features:**
- Static dashboard with Chart.js visualizations
- Auto-deploys on push to main
- Free hosting

---

## Cost Summary

| Service | Monthly Cost |
|---------|-------------|
| Modal.com | $2-3 |
| GitHub Pages | Free |
| **Total** | **$2-3/month** |

---

## Migration History

### 2026-02-02: Migrated to Modal + GitHub Pages
- Discontinued DigitalOcean App Platform
- Moved all backend services to Modal.com
- Dashboard now hosted on GitHub Pages
- Reduced costs from ~$5/month to $2-3/month

### Previous: DigitalOcean (Archived)
- Was deployed at: `stock-story-jy89o.ondigitalocean.app`
- Migrated away due to cost optimization
- Historical docs in `docs/archive/`

---

## Deployment Commands

### Deploy to Modal

```bash
# Deploy crisis monitoring
modal deploy modal_scanner.py

# Deploy Tier 3 intelligence jobs
modal deploy modal_intelligence_jobs.py

# Check deployed apps
modal app list

# View logs
modal app logs modal_scanner
```

### Update GitHub Pages Dashboard

```bash
# Dashboard auto-deploys on push to main
git add docs/
git commit -m "Update dashboard"
git push origin main
```

---

## Health Checks

### Modal Apps
```bash
# Check Modal app status
modal app list

# View recent logs
modal app logs modal_scanner --tail 100
```

### Dashboard
- Visit: https://zhuanleee.github.io/stock_scanner_bot/
- Should load without errors

### Telegram Bot
- Send `/status` to @Stocks_Story_Bot
- Should respond with system health

---

## Troubleshooting

### Modal Jobs Not Running
```bash
# Redeploy
modal deploy modal_scanner.py

# Check secrets
modal secret list
```

### Dashboard Not Updating
1. Check GitHub Pages settings in repo
2. Verify `docs/` folder exists
3. Check GitHub Actions for build errors

### Telegram Bot Not Responding
1. Check Modal logs for errors
2. Verify webhook is configured
3. Check `TELEGRAM_BOT_TOKEN` secret

---

**Status:** Fully Operational
**Platform:** Modal.com + GitHub Pages
