# Archived Workflows

These workflows were used before migrating to Modal.com on January 30, 2026.

## Why Archived?

After migrating to Modal, these workflows became redundant:

### Old Architecture (GitHub Actions)
- `daily_scan.yml` - Ran scanner on GitHub Actions runners
- `bot_listener.yml` - Listened for bot commands
- `dashboard.yml` - Updated dashboard data
- `refresh_universe.yml` - Refreshed stock universe cache
- `story_alerts.yml` - Detected story-worthy stocks

**Problems:**
- Cost: GitHub Actions compute time
- Limited compute: No GPU support
- Complex: Multiple workflows to maintain
- Slow: Sequential processing

### New Architecture (Modal)
- `deploy_modal.yml` - Single deployment workflow
- `modal_scanner.py` - Runs daily on Modal with GPU
- `modal_api_v2.py` - Serves all API endpoints

**Benefits:**
- Cost: $0/month (free tier)
- Fast: T4 GPU acceleration
- Simple: One workflow, two Modal functions
- Scalable: Auto-scaling serverless

## What Replaced Each Workflow

| Old Workflow | Replaced By | Notes |
|--------------|-------------|-------|
| `daily_scan.yml` | Modal scanner cron | Runs at 6 AM PST with GPU |
| `bot_listener.yml` | Modal scanner | Sends Telegram notifications |
| `dashboard.yml` | GitHub Pages + Modal API | Auto-updates on push |
| `refresh_universe.yml` | Modal scanner | Refreshes during scan |
| `story_alerts.yml` | Modal scanner | Included in daily scan |

## Cost Savings

**Before:**
- GitHub Actions: ~$5-10/month (estimate)
- Digital Ocean: $20/month
- **Total: ~$25-30/month**

**After:**
- GitHub Actions: $0 (only deployment)
- Modal: $0 (free tier)
- GitHub Pages: $0 (public repo)
- **Total: $0/month**

**Annual savings: ~$300-360**

## If You Need to Restore

If you need to revert to GitHub Actions for any reason:

1. Move workflows back:
   ```bash
   mv .github/workflows-archive/*.yml .github/workflows/
   ```

2. Restore GitHub Secrets:
   ```bash
   gh secret set DEEPSEEK_API_KEY
   gh secret set TELEGRAM_BOT_TOKEN
   gh secret set TELEGRAM_CHAT_ID
   gh secret set POLYGON_API_KEY
   ```

3. Disable Modal cron schedule in `modal_scanner.py`

---

**Archived:** January 31, 2026
**Reason:** Migration to Modal completed
**Safe to delete:** After 6 months (July 2026) if no issues
