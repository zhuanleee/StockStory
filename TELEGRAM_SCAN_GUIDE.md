# Telegram Bot - Scan Trigger Guide

**Updated:** January 31, 2026
**Feature:** ✅ Remote scan triggering via Telegram

---

## Quick Start

### Trigger a Scan from Telegram

1. **Open your Telegram bot chat**
2. **Send:** `/scan`
3. **Wait 5-10 minutes**
4. **Get notification** when scan completes!

That's it! 🎉

---

## Setup (One Time)

### Prerequisites

Your Telegram bot needs to be set up with:
1. ✅ Bot created (via @BotFather)
2. ✅ `TELEGRAM_BOT_TOKEN` configured
3. ✅ `TELEGRAM_CHAT_ID` configured
4. ✅ Modal CLI authenticated on the server running the bot

---

## Bot Commands

### Scan Commands

| Command | What It Does | Time |
|---------|--------------|------|
| `/scan` | Trigger full scan (515 stocks) | 5-10 min |
| `/top` | Show top 10 stocks | Instant |
| `/status` | Check scan status | Instant |

### Ticker Queries

| Command | What It Does |
|---------|--------------|
| `NVDA` | Get analysis for NVDA |
| `TSLA` | Get analysis for TSLA |
| Any ticker | Get detailed stock analysis |

### Info Commands

| Command | What It Does |
|---------|--------------|
| `/help` | Show all commands |

---

## How /scan Works

### Step-by-Step

**1. You send `/scan` in Telegram**

**2. Bot responds immediately:**
```
🔄 Triggering scan...

Starting full scan on Modal (515 stocks)
This will take 5-10 minutes.

You'll receive a notification when complete! ⏳
```

**3. Bot triggers Modal scan:**
```bash
python3 -m modal run modal_scanner.py --daily
```

**4. Scan runs on Modal servers (GPU):**
```
🚀 STARTING DAILY AI BRAIN SCAN
📅 Market is OPEN - Friday, January 31, 2026
📊 Universe: 515 stocks
🔄 Scanning in batches of 10...
```

**5. Scan completes (~5-10 minutes later)**

**6. You get automatic notification:**
```
🤖 Daily Scan Complete!

📊 Scanned: 515/515 stocks
⏱️  Time: 5.2 minutes

📈 Top 10 Picks:
1. NVDA - 85.3 (hot)
2. LLY - 78.5 (developing)
3. PLTR - 72.1 (developing)
...

🔗 View: https://zhuanleee.github.io
```

---

## Example Conversation

**You:**
```
/scan
```

**Bot:**
```
🔄 Triggering scan...

Starting full scan on Modal (515 stocks)
This will take 5-10 minutes.

You'll receive a notification when complete! ⏳
```

**Bot (5 minutes later):**
```
✅ Scan started successfully!

The scan is running on Modal's servers.
You'll get a notification when it completes (~5-10 min)
```

**Bot (10 minutes later - automatic from scanner):**
```
🤖 Daily Scan Complete!

📊 Scanned: 515/515 stocks
⏱️  Time: 5.2 minutes

📈 Top 10 Picks:
1. NVDA - 85.3 (hot)
2. LLY - 78.5 (developing)
...
```

**You:**
```
NVDA
```

**Bot:**
```
NVDA ANALYSIS

Score: 85/100
RS vs SPY: +12.3%
Price: $875.50

Trend:
  Above 20 SMA: Yes
  Above 50 SMA: Yes
  Above 200 SMA: Yes

Volume: 1.8x average

Theme: AI Infrastructure
```

---

## Advantages of Telegram Triggering

### 1. Mobile Access
- ✅ Trigger scans from your phone
- ✅ No need for computer
- ✅ Perfect for on-the-go trading

### 2. Simple Interface
- ✅ Just send `/scan`
- ✅ No terminal commands
- ✅ No authentication needed (bot handles it)

### 3. Notifications
- ✅ Get notified when scan completes
- ✅ See top picks immediately
- ✅ Query individual tickers

### 4. Remote Management
- ✅ Trigger from anywhere
- ✅ No VPN or SSH needed
- ✅ Works from any device

---

## Error Handling

### If Bot Says "Scan failed to start"

**Possible causes:**
1. Modal not authenticated on bot server
2. Network connection issue
3. Modal service unavailable

**Solution:**
- Check Modal authentication: `modal token set`
- Try again in a few minutes
- Or run manually: `modal run modal_scanner.py --daily`

### If Bot Says "Scan timed out"

**Meaning:** Scan is taking longer than 10 minutes

**Solution:**
- Check Modal dashboard for scan status
- Scan might still be running successfully
- Wait for automatic notification

### If Bot Says "Error triggering scan"

**Meaning:** Unexpected error occurred

**Solution:**
- Check bot logs
- Verify Modal is accessible
- Run scan manually as fallback

---

## Bot Setup (For Reference)

If you need to set up the Telegram bot:

### 1. Create Bot

Talk to @BotFather on Telegram:
```
/newbot
Name: Stock Scanner Bot
Username: your_scanner_bot
```

Get your `BOT_TOKEN`

### 2. Get Chat ID

Send a message to your bot, then visit:
```
https://api.telegram.org/bot<BOT_TOKEN>/getUpdates
```

Look for `"chat":{"id":123456789}`

### 3. Configure Environment

Add to your environment (GitHub Secrets or server):
```bash
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

### 4. Start Bot Listener

```bash
python3 src/bot/bot_listener.py
```

Or set up as GitHub Actions workflow (already configured).

---

## Bot Listener Details

**File:** `src/bot/bot_listener.py`

**How it works:**
1. Polls Telegram API every few seconds
2. Checks for new messages
3. Processes commands
4. Sends responses

**Runs on:**
- Local machine (manual: `python3 src/bot/bot_listener.py`)
- GitHub Actions (automatic - check workflows)
- Server (systemd service or cron)

---

## Comparison: Telegram vs Terminal

| Method | Pros | Cons |
|--------|------|------|
| **Telegram** | • Mobile access<br>• No terminal needed<br>• Automatic notifications<br>• Simple `/scan` command | • Requires bot setup<br>• Depends on bot server |
| **Terminal** | • Direct control<br>• No intermediary<br>• See real-time output | • Requires computer<br>• Need Modal auth<br>• Terminal access |

**Recommendation:** Use Telegram for convenience, terminal for debugging.

---

## Other Telegram Commands

While you're at it, try these:

```
/top           → See top 10 stocks
/status        → Check scan status
NVDA           → Analyze NVDA
TSLA           → Analyze TSLA
/help          → Show all commands
```

---

## Troubleshooting

### Bot Not Responding

**Check:**
1. Is bot listener running?
   ```bash
   ps aux | grep bot_listener
   ```

2. Are environment variables set?
   ```bash
   echo $TELEGRAM_BOT_TOKEN
   echo $TELEGRAM_CHAT_ID
   ```

3. Is network accessible?
   ```bash
   curl https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getMe
   ```

### Scan Not Starting

**Check:**
1. Is Modal authenticated?
   ```bash
   modal token set
   ```

2. Can bot access Modal?
   ```bash
   python3 -m modal app list
   ```

3. Is scan file accessible?
   ```bash
   ls modal_scanner.py
   ```

---

## Advanced: Scheduled Bot Polling

To keep the bot listening continuously, set up a cron job or systemd service:

**Cron (every 5 minutes):**
```cron
*/5 * * * * cd /path/to/stock_scanner_bot && python3 src/bot/bot_listener.py
```

**Systemd Service:**
```ini
[Unit]
Description=Stock Scanner Telegram Bot
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/stock_scanner_bot
ExecStart=/usr/bin/python3 src/bot/bot_listener.py
Restart=always

[Install]
WantedBy=multi-user.target
```

---

## Summary

✅ **Easiest way to trigger scans:** Send `/scan` in Telegram
✅ **Works from mobile:** No computer needed
✅ **Automatic notifications:** Know when scan completes
✅ **Additional features:** Ticker queries, top stocks, status

**To trigger a scan right now:**
1. Open Telegram
2. Find your Stock Scanner bot
3. Send: `/scan`
4. Wait for notification!

---

## Next Steps

1. **Test it now:** Send `/scan` to your bot
2. **Bookmark your bot** for quick access
3. **Set up notifications** on your phone
4. **Try other commands** like `/top` and ticker queries

Your bot is ready to use! 🚀

---

**Documentation:** This guide
**Bot file:** `src/bot/bot_listener.py`
**Deployed:** January 31, 2026 (commit 1c91f7c)
