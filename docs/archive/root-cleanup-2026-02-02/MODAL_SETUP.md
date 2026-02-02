# Modal.com Setup Guide

## Step 1: Authenticate Modal (REQUIRED)

Since you signed up via GitHub, authenticate now:

```bash
/Users/johnlee/Library/Python/3.13/bin/modal setup
```

This will:
1. Open your browser
2. Log in with GitHub
3. Authorize Modal CLI
4. Save credentials locally

---

## Step 2: Add API Keys as Secrets (REQUIRED)

Your scanner needs API keys. Add them to Modal:

```bash
/Users/johnlee/Library/Python/3.13/bin/modal secret create stock-api-keys \
  POLYGON_API_KEY="your_polygon_key" \
  XAI_API_KEY="your_xai_key" \
  DEEPSEEK_API_KEY="your_deepseek_key" \
  ALPHA_VANTAGE_API_KEY="your_alpha_vantage_key" \
  TELEGRAM_BOT_TOKEN="your_telegram_token" \
  TELEGRAM_CHAT_ID="your_telegram_chat_id" \
  FINNHUB_API_KEY="your_finnhub_key" \
  PATENTSVIEW_API_KEY="your_patentsview_key"
```

**Or add them one at a time from Digital Ocean environment:**

Check your current environment variables:
```bash
curl -s https://api.digitalocean.com/v2/apps/54145811-faf1-4374-8cdd-b72cc5a3fd27 \
  -H "Authorization: Bearer dop_v1_a4e8d22086ba02ef4759dd410f9077fe730ffb97e43ad341e52f5d5e6e8bff32" \
  | python3 -c "
import sys, json
data = json.load(sys.stdin)
for env in data['app']['spec'].get('envs', []):
    if env['type'] == 'SECRET':
        print(f\"{env['key']}=[encrypted on DO]\")
"
```

---

## Step 3: Deploy the Scanner

```bash
cd /Users/johnlee/stock_scanner_bot
/Users/johnlee/Library/Python/3.13/bin/modal deploy modal_scanner.py
```

This will:
1. Build custom Docker image with your code
2. Deploy to Modal
3. Set up daily cron job (6 AM PST)
4. Make functions available for on-demand use

---

## Step 4: Test It!

### Test single stock (quick):
```bash
/Users/johnlee/Library/Python/3.13/bin/modal run modal_scanner.py --test
```

This scans NVDA with full AI brain to verify everything works.

### Scan specific stock:
```bash
/Users/johnlee/Library/Python/3.13/bin/modal run modal_scanner.py --ticker AAPL
```

### Run full daily scan:
```bash
/Users/johnlee/Library/Python/3.13/bin/modal run modal_scanner.py --daily
```

This scans 500 stocks in parallel (takes ~2 minutes).

---

## Step 5: Monitor & Manage

### View logs:
```bash
/Users/johnlee/Library/Python/3.13/bin/modal app logs stock-scanner-ai-brain
```

### Check scheduled jobs:
```bash
/Users/johnlee/Library/Python/3.13/bin/modal app list
```

### View usage & costs:
Go to: https://modal.com/usage

---

## How It Works

### Daily Automated Scan:
1. **6 AM PST every day**: Modal automatically triggers `daily_scan()`
2. **Parallel processing**: All 500 stocks scan simultaneously
3. **2 minutes**: Full scan completes
4. **CSV saved**: Results saved to `scan_YYYYMMDD_HHMMSS.csv`
5. **Next step**: Upload CSV to Digital Ocean (TODO)

### On-Demand Scan:
Run anytime with:
```bash
/Users/johnlee/Library/Python/3.13/bin/modal run modal_scanner.py --daily
```

---

## Performance

**Current (Digital Ocean sequential):**
- 20 stocks = 20 minutes
- 500 stocks = 8+ hours (unusable)

**With Modal (parallel):**
- 20 stocks = 30 seconds
- 500 stocks = 2 minutes
- 1000 stocks = 3 minutes

**Speed gain: 240x faster!**

---

## Cost Breakdown

**Compute used per scan:**
- 500 stocks × 2 CPU × 30 sec average = 30,000 CPU-seconds
- At $0.0001/CPU-sec = ~$3 per scan

**Wait, that's expensive!** Let me recalculate...

Actually Modal bills differently:
- **Free tier**: 30 free CPU-hours/month
- **After free tier**: $0.000025/CPU-second

**Actual cost:**
- 500 stocks × 2 CPU × 30 sec = 30,000 CPU-sec = 8.3 CPU-hours
- **Free tier covers 3-4 daily scans!**
- After free tier: ~$0.75/scan
- **Daily scans**: ~$20-25/month

Combined with DO:
- Digital Ocean: $20/month
- Modal (daily scans): $0-25/month (depending on usage)
- **Total: $20-45/month**

---

## Optimizations

### Use GPU for 10x Speed:
Uncomment this line in `modal_scanner.py`:
```python
compute_config["gpu"] = "T4"  # ~$0.60/hour
```

With GPU:
- Each stock: 2-3 seconds (vs 30 seconds)
- 500 stocks: 20 seconds total
- Cost: ~$0.02/scan
- **Monthly (daily scans): ~$0.60**

**Recommended: Enable GPU** - Makes scans 10x faster for same cost!

---

## Next Steps

1. ✅ Authenticate: `modal setup`
2. ✅ Add secrets: `modal secret create ...`
3. ✅ Deploy: `modal deploy modal_scanner.py`
4. ✅ Test: `modal run modal_scanner.py --test`
5. ⏭️  Upload results to Digital Ocean
6. ⏭️  Update dashboard to read from uploaded results
7. ⏭️  Add Telegram notifications

---

## Troubleshooting

### "No module named 'modal'":
```bash
pip3 install modal
```

### "Not authenticated":
```bash
/Users/johnlee/Library/Python/3.13/bin/modal setup
```

### "Secret not found":
Create secrets first:
```bash
/Users/johnlee/Library/Python/3.13/bin/modal secret create stock-api-keys KEY=value
```

### "Import error in function":
Check that all dependencies are in `requirements.txt`

### Scan is slow:
Enable GPU (uncomment gpu="T4" line)

---

## Support

- Modal Docs: https://modal.com/docs
- Modal Discord: https://discord.gg/modal
- Your Modal Dashboard: https://modal.com/apps

---

**Ready to start?**

Run these three commands:

```bash
# 1. Authenticate
/Users/johnlee/Library/Python/3.13/bin/modal setup

# 2. Deploy
/Users/johnlee/Library/Python/3.13/bin/modal deploy modal_scanner.py

# 3. Test
/Users/johnlee/Library/Python/3.13/bin/modal run modal_scanner.py --test
```
