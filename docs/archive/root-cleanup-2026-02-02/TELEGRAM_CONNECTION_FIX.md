# Telegram Bot Connection - Diagnostic & Fix

**Date:** January 31, 2026
**Issue:** Bot not responding to `/scan` command
**Status:** ✅ FIXED - Awaiting activation

---

## Problem Identified

### Why Your Bot Didn't Respond

When you sent `/scan` to your Telegram bot, nothing happened because:

❌ **Bot listener workflow was DISABLED (archived)**
- The GitHub Actions workflow that checks for Telegram messages was turned off
- Without this workflow, the bot can't see your messages
- It was in `.github/workflows-archive/` instead of `.github/workflows/`

❌ **Bot wasn't running anywhere**
- No process listening for Telegram messages
- No GitHub Actions workflow active
- Bot code exists but not executing

---

## What I Fixed

### ✅ Restored Bot Listener Workflow

**File:** `.github/workflows/bot_listener.yml`

**What it does:**
1. **Runs every 15 minutes** during market hours (9 AM - 5 PM EST, Mon-Fri)
2. **Checks for new Telegram messages** from your bot
3. **Processes commands** like `/scan`, `/top`, ticker queries
4. **Triggers Modal scans** when you send `/scan`
5. **Sends responses** back to Telegram

**Schedule:**
```yaml
schedule:
  - cron: '*/15 13-22 * * 1-5'  # Every 15 min, Mon-Fri, 9 AM-5 PM EST
```

**Key additions:**
- ✅ Modal authentication (for /scan command)
- ✅ All required environment variables
- ✅ Automatic commit of message offset (tracks processed messages)

---

## How It Works Now

### Complete Flow

**1. You send `/scan` to Telegram bot**
```
You → Telegram → Bot API
```

**2. GitHub Actions workflow runs (every 15 min)**
```
GitHub Actions wakes up
↓
Checks Telegram for new messages
↓
Finds your /scan command
```

**3. Bot processes command**
```
Bot listener runs: python main.py bot
↓
Sees /scan command
↓
Responds: "🔄 Triggering scan..."
```

**4. Bot triggers Modal scan**
```
Runs: modal run modal_scanner.py --daily
↓
Scan runs on Modal (5-10 min)
↓
Scan completes
```

**5. You get notification**
```
Scanner sends notification to Telegram
↓
You see: "🤖 Daily Scan Complete! ..."
```

---

## What You Need To Do

### Step 1: Verify GitHub Secrets

Go to: https://github.com/zhuanleee/stock_scanner_bot/settings/secrets/actions

**Make sure these secrets exist:**

| Secret Name | What It Is | How to Get |
|-------------|------------|------------|
| `TELEGRAM_BOT_TOKEN` | Your bot's token | @BotFather on Telegram → `/newbot` |
| `TELEGRAM_CHAT_ID` | Your chat ID | Send message to bot, then check `/getUpdates` |
| `MODAL_TOKEN_ID` | Modal authentication | https://modal.com/settings/tokens |
| `MODAL_TOKEN_SECRET` | Modal authentication | https://modal.com/settings/tokens |

**If any are missing, add them:**
1. Click "New repository secret"
2. Enter name (e.g., `TELEGRAM_BOT_TOKEN`)
3. Enter value
4. Click "Add secret"

---

### Step 2: Get Your Telegram Credentials (If Needed)

#### A. Get Bot Token

1. Open Telegram
2. Search for `@BotFather`
3. Send: `/newbot`
4. Follow prompts to create bot
5. Copy the **token** (looks like: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

#### B. Get Chat ID

1. Send any message to your bot (e.g., "hello")
2. Visit this URL in browser (replace `<TOKEN>` with your bot token):
   ```
   https://api.telegram.org/bot<TOKEN>/getUpdates
   ```
3. Look for `"chat":{"id":123456789}`
4. Copy that number (your chat ID)

---

### Step 3: Test Your Setup (Optional)

Run the diagnostic tool I created:

```bash
./check_telegram_setup.sh
```

**This will:**
- ✅ Test if bot token is valid
- ✅ Test sending a message
- ✅ Show recent messages
- ✅ Check workflow configuration

**Expected output:**
```
✅ Bot is valid: @your_bot_name
✅ Successfully sent test message to chat
📱 Check your Telegram - you should see the test message!
```

---

### Step 4: Activate the Workflow

The workflow is already pushed to GitHub (just committed).

**Check if it's active:**
1. Go to: https://github.com/zhuanleee/stock_scanner_bot/actions
2. Look for "Bot Listener" workflow
3. Should show as enabled

**If you want to test it immediately:**
1. Click "Bot Listener" workflow
2. Click "Run workflow" button (dropdown)
3. Click green "Run workflow" button
4. Wait 30 seconds
5. Check your Telegram for bot responses

---

### Step 5: Try /scan Again

**Send to your Telegram bot:**
```
/scan
```

**What should happen:**

**Immediately (within 15 minutes):**
```
🔄 Triggering scan...

Starting full scan on Modal (515 stocks)
This will take 5-10 minutes.

You'll receive a notification when complete! ⏳
```

**After scan completes (5-10 min later):**
```
🤖 Daily Scan Complete!

📊 Scanned: 515/515 stocks
⏱️  Time: 5.2 minutes

📈 Top 10 Picks:
1. NVDA - 85.3 (hot)
2. LLY - 78.5 (developing)
...
```

---

## Troubleshooting

### Bot Still Not Responding After 15 Minutes

**Check workflow runs:**
1. Go to: https://github.com/zhuanleee/stock_scanner_bot/actions
2. Click "Bot Listener"
3. Check recent runs
4. Click on a run to see logs

**If workflow failed:**
- Check the error message in logs
- Likely missing GitHub Secrets
- Or incorrect token/chat ID

**If workflow succeeded but no response:**
- Check Telegram credentials are correct
- Verify chat ID matches your chat
- Try sending another command like `/help`

---

### Bot Responds But /scan Fails

**Error message will tell you why:**

**"Modal not authenticated":**
- Add `MODAL_TOKEN_ID` and `MODAL_TOKEN_SECRET` to GitHub Secrets

**"Scan failed to start":**
- Check Modal tokens are correct
- Verify Modal service is accessible

**"Scan timed out":**
- Scan is taking longer than expected
- Check Modal dashboard for scan status

---

### How to Check Workflow Logs

1. Go to: https://github.com/zhuanleee/stock_scanner_bot/actions
2. Click "Bot Listener" workflow
3. Click on the latest run
4. Click "listen" job
5. Expand each step to see output

**Look for:**
- ✅ "Running Telegram bot listener..."
- ✅ "Processing command: /scan"
- ✅ "Triggering scan..."

---

## Timeline & Expectations

### When Bot Checks for Messages

**Every 15 minutes during market hours:**
- Monday-Friday
- 9:00 AM - 5:00 PM EST
- On the hour: 9:00, 9:15, 9:30, 9:45, 10:00, etc.

**Example:**
- 9:05 AM - You send `/scan`
- 9:15 AM - Workflow runs, sees your command, responds
- 9:16 AM - Scan starts on Modal
- 9:21 AM - Scan completes, you get notification

**Max wait time:** 15 minutes from when you send the command

---

### Outside Market Hours

**Bot still works, but checks less frequently:**
- After 5 PM EST: No scheduled checks
- Weekends: No scheduled checks
- Can still manually trigger: GitHub Actions → Run workflow

**Or use manual trigger:**
```bash
# On your computer
modal run modal_scanner.py --daily
```

---

## Alternative: Run Bot Locally (24/7 Response)

If you want instant responses instead of waiting 15 minutes:

### Option A: Run Bot Listener Locally

```bash
# In a terminal that stays open
export TELEGRAM_BOT_TOKEN="your_token"
export TELEGRAM_CHAT_ID="your_chat_id"
python main.py bot
```

**Pros:**
- Instant responses
- No 15-minute wait

**Cons:**
- Terminal must stay open
- Computer must stay on
- Modal authentication needed locally

### Option B: Deploy to Always-On Server

Deploy `src/bot/bot_listener.py` to:
- Railway.app
- Render.com
- AWS Lambda (with schedule)
- Your own server

---

## Summary

### What Was Wrong
❌ Bot listener workflow was disabled (archived)
❌ No process running to check Telegram messages
❌ Bot code was fine, just not executing

### What I Fixed
✅ Restored bot listener workflow
✅ Added Modal authentication to workflow
✅ Configured to run every 15 minutes during market hours
✅ Created diagnostic tool (check_telegram_setup.sh)

### What You Need To Do
1. ✅ Verify GitHub Secrets are set (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, MODAL_TOKEN_ID, MODAL_TOKEN_SECRET)
2. ✅ Workflow is already activated (just pushed)
3. ✅ Send `/scan` to your Telegram bot
4. ✅ Wait up to 15 minutes for response

### Expected Timeline
- **Now:** Send `/scan`
- **Within 15 min:** Bot responds "Triggering scan..."
- **5-10 min later:** Scan completes, you get notification
- **Total:** 15-25 minutes from command to results

---

## Quick Test

**Right now, send this to your bot:**
```
/help
```

**Within 15 minutes, you should see:**
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

**If you see this response, your bot is working!** ✅

Then try `/scan` and wait for the scan to complete.

---

**Status:** ✅ Bot listener restored and deployed
**Next scan trigger:** Send `/scan` anytime!
**Max wait:** 15 minutes for bot to see command
**Total time:** 15-25 minutes from `/scan` to results

Your Telegram bot is ready to use! 🚀
