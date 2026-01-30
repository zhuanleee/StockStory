# Telegram Bot - Instant Test (No Waiting)

**Problem:** Bot not responding to `/scan`
**Status:** Workflow is running, but you need to test it NOW

---

## The Issue

The bot workflow runs **every 15 minutes** during market hours. You might be:
- ⏰ Waiting for the next scheduled run
- ⚠️ Missing Telegram credentials in GitHub Secrets
- ❌ Using wrong chat ID or bot token

---

## Solution 1: Manually Trigger Workflow (INSTANT TEST)

Instead of waiting 15 minutes, trigger the workflow RIGHT NOW:

### Step-by-Step:

**1. Go to GitHub Actions:**
```
https://github.com/zhuanleee/stock_scanner_bot/actions
```

**2. Click "Bot Listener"** in the left sidebar

**3. Click "Run workflow"** button (top right, dropdown)

**4. Click green "Run workflow"** button

**5. Wait 30 seconds**

**6. Check your Telegram** for bot response

---

## Solution 2: Check GitHub Secrets

The workflow is running successfully, but might not have your Telegram credentials.

### Check Secrets:

**Go to:**
```
https://github.com/zhuanleee/stock_scanner_bot/settings/secrets/actions
```

**You should see these secrets:**
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `MODAL_TOKEN_ID`
- `MODAL_TOKEN_SECRET`

**If `TELEGRAM_BOT_TOKEN` or `TELEGRAM_CHAT_ID` are missing:**

1. Click "New repository secret"
2. Add each one

**To get your credentials:**

### Get Bot Token:
1. Open Telegram
2. Search for `@BotFather`
3. Send: `/mybots`
4. Select your bot
5. Click "API Token"
6. Copy the token

### Get Chat ID:
1. Send any message to your bot
2. Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
3. Look for: `"chat":{"id":123456789}`
4. That number is your Chat ID

---

## Solution 3: Test Locally (Verify Credentials)

Run this script to test if your credentials work:

```bash
# Set your credentials
export TELEGRAM_BOT_TOKEN="your_token_here"
export TELEGRAM_CHAT_ID="your_chat_id_here"

# Run test
python3 test_telegram_now.py
```

**Expected output:**
```
✅ Token set: 123456789:ABCDE...
✅ Chat ID set: 987654321
✅ Bot connected: @your_bot_name
✅ Message sent successfully!
📱 Check your Telegram - you should see the test message
```

**If you see this, your credentials are correct!**

Then add them to GitHub Secrets.

---

## Solution 4: Send Test Command

After setting up secrets or manually triggering workflow:

**Send to your Telegram bot:**
```
/help
```

**You should see (within 1 minute if manually triggered):**
```
BOT COMMANDS

Send any ticker (e.g., NVDA) for analysis

Scan Commands:
/scan - Trigger full scan (515 stocks)
/top - Show top 10 stocks
/status - Check scan status

Info:
/help - Show this help
```

**If you see this, your bot is working!** ✅

---

## Debugging Checklist

### ✅ Is the workflow running?
Go to: https://github.com/zhuanleee/stock_scanner_bot/actions
- Should see "Bot Listener" runs
- Recent runs should show ✅ success

### ✅ Are credentials set?
Go to: https://github.com/zhuanleee/stock_scanner_bot/settings/secrets/actions
- `TELEGRAM_BOT_TOKEN` exists
- `TELEGRAM_CHAT_ID` exists

### ✅ Are credentials correct?
Run: `python3 test_telegram_now.py`
- Should send test message to your Telegram

### ✅ Is bot receiving messages?
Check: `https://api.telegram.org/bot<TOKEN>/getUpdates`
- Should show your recent messages to the bot

---

## Most Likely Issue

**You sent `/scan` but the workflow hasn't run yet.**

The workflow runs every 15 minutes:
- 9:00, 9:15, 9:30, 9:45, 10:00, etc. (EST)

**If you sent `/scan` at 9:07:**
- Workflow runs at 9:15 (8 min wait)
- Bot sees your message
- Responds with "Triggering scan..."

**To avoid waiting:**
Manually trigger the workflow (Solution 1 above)

---

## Next Scheduled Run

The workflow runs during market hours (9 AM - 5 PM EST, Mon-Fri):

**Current time:** Check https://time.is/EST

**Next run:** Next 15-minute mark
- Example: If it's 10:37 AM EST, next run is 10:45 AM EST

**To see exact schedule:**
Workflow runs at: `:00, :15, :30, :45` of each hour during 9 AM - 5 PM EST

---

## Quick Action (Do This Now)

### Option A: Manual Trigger (Fastest)

1. **Go to:** https://github.com/zhuanleee/stock_scanner_bot/actions
2. **Click:** "Bot Listener"
3. **Click:** "Run workflow" dropdown
4. **Click:** Green "Run workflow" button
5. **Wait:** 30 seconds
6. **Check:** Your Telegram

### Option B: Test Credentials

```bash
export TELEGRAM_BOT_TOKEN="your_token"
export TELEGRAM_CHAT_ID="your_chat_id"
python3 test_telegram_now.py
```

If this sends you a message on Telegram, your credentials work!
Then add them to GitHub Secrets.

---

## Expected Timeline

### If credentials are set correctly:

**Manual trigger:**
- 0:00 - You trigger workflow on GitHub
- 0:30 - Workflow completes
- 0:30 - Bot processes your `/scan` message
- 0:30 - You get "Triggering scan..." response
- 5:30 - Scan completes
- 5:30 - You get "Scan complete!" notification

**Scheduled run:**
- 0:00 - You send `/scan`
- 0:00-15:00 - Wait for next scheduled run
- 15:00 - Workflow runs, sees your message
- 15:00 - You get "Triggering scan..." response
- 20:00 - Scan completes
- 20:00 - You get "Scan complete!" notification

---

## Summary

**Most likely reason bot isn't responding:**
1. ⏰ You're between scheduled runs (workflow runs every 15 min)
2. ⚠️ Telegram credentials not in GitHub Secrets
3. ❌ Credentials are incorrect

**Quick fix:**
1. Manually trigger workflow (instant test)
2. Or wait for next 15-min mark
3. Verify credentials are in GitHub Secrets

**Test right now:**
```
https://github.com/zhuanleee/stock_scanner_bot/actions
→ Bot Listener → Run workflow
```

Then send `/help` to your bot and wait 30 seconds!

---

**Files Created:**
- `test_telegram_now.py` - Local credential tester
- `TELEGRAM_INSTANT_TEST.md` - This guide
- `TELEGRAM_CONNECTION_FIX.md` - Complete diagnostic

**Your bot IS working** - you just need to either manually trigger it or wait for the next scheduled run! ✅
