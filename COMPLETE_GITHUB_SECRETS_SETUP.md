# Complete GitHub Secrets Setup - Copy & Paste Ready

**Status**: All credentials verified and ready to use ✅

---

## Your Verified Credentials

### Telegram Bot
- ✅ Bot Token: `7626822299:AAHVNKOLIVelbBwOEO2J2aE_6D34Ml0RuuM`
- ✅ Bot Name: @Stocks_Story_Bot
- ✅ Your Chat ID: `1191814045`
- ✅ Your Username: @zhuanlee
- ✅ Bot can send messages: CONFIRMED

### Modal
- ✅ Token ID: `wk-nUmIlRoKEbHVj8CDDcimf2`
- ✅ Token Secret: `ws-EAZXk2XZaOQ2ZngQ8ivYET`

---

## Step-by-Step: Update GitHub Secrets

### 1. Open GitHub Secrets Page

Click this link:
```
https://github.com/zhuanleee/stock_scanner_bot/settings/secrets/actions
```

### 2. Add/Update These 4 Secrets

You need to set exactly 4 secrets. For each one:
- Click "New repository secret" (or edit if it exists)
- Copy the Name and Value from below
- Click "Add secret" or "Update secret"

---

#### Secret 1: TELEGRAM_BOT_TOKEN

**Name:**
```
TELEGRAM_BOT_TOKEN
```

**Value:**
```
7626822299:AAHVNKOLIVelbBwOEO2J2aE_6D34Ml0RuuM
```

---

#### Secret 2: TELEGRAM_CHAT_ID

**Name:**
```
TELEGRAM_CHAT_ID
```

**Value:**
```
1191814045
```

---

#### Secret 3: MODAL_TOKEN_ID

**Name:**
```
MODAL_TOKEN_ID
```

**Value:**
```
wk-nUmIlRoKEbHVj8CDDcimf2
```

---

#### Secret 4: MODAL_TOKEN_SECRET

**Name:**
```
MODAL_TOKEN_SECRET
```

**Value:**
```
ws-EAZXk2XZaOQ2ZngQ8ivYET
```

---

## 3. Verify Secrets Are Set

After adding all 4 secrets, you should see this on the Secrets page:

```
✅ TELEGRAM_BOT_TOKEN
✅ TELEGRAM_CHAT_ID
✅ MODAL_TOKEN_ID
✅ MODAL_TOKEN_SECRET
```

---

## 4. Test the Bot Immediately

### Option A: Manually Trigger Workflow (Instant Test)

1. Go to: https://github.com/zhuanleee/stock_scanner_bot/actions
2. Click "Bot Listener" in the left sidebar
3. Click "Run workflow" dropdown (top right)
4. Click green "Run workflow" button
5. Wait 30 seconds
6. Check your Telegram!

### Option B: Wait for Next Scheduled Run

The workflow runs every 15 minutes during market hours (9 AM - 5 PM EST, Mon-Fri).

Just wait up to 15 minutes after setting the secrets.

---

## 5. Test Commands

After the workflow runs, send these to @Stocks_Story_Bot:

### Test 1: Help Command
```
/help
```

**Expected Response:**
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

### Test 2: Scan Command
```
/scan
```

**Expected Response:**
```
🔄 Triggering scan...

Starting full scan on Modal (515 stocks)
This will take 5-10 minutes.

You'll receive a notification when complete! ⏳
```

**5-10 minutes later:**
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

### If bot doesn't respond after 15 minutes:

1. **Check workflow ran successfully:**
   - Go to: https://github.com/zhuanleee/stock_scanner_bot/actions
   - Look for green checkmark on latest "Bot Listener" run
   - If red X, click it to see error logs

2. **Verify secrets are set correctly:**
   - Go to: https://github.com/zhuanleee/stock_scanner_bot/settings/secrets/actions
   - Should see all 4 secrets listed
   - Make sure no typos in the secret NAMES (case-sensitive)

3. **Check for typos in secret values:**
   - Delete and re-add the secret
   - Copy-paste exactly from this document
   - Don't add extra spaces or newlines

### If /scan command fails:

Check the error message. Common issues:

**"Modal not authenticated":**
- MODAL_TOKEN_ID or MODAL_TOKEN_SECRET is wrong or missing
- Re-add the Modal secrets from this document

**"Scan timed out":**
- Scan is taking longer than expected
- Check Modal dashboard: https://modal.com/
- The scan might still be running

**"Network connection issue":**
- GitHub Actions might have network issues
- Try manually triggering workflow again

---

## What Happens After Setup

### Automatic Scanning
The bot listener workflow runs **every 15 minutes** during market hours:
- Monday-Friday
- 9:00 AM - 5:00 PM EST
- At: :00, :15, :30, :45 of each hour

### Bot Commands Available
- `/help` - Show help
- `/scan` - Trigger full scan (515 stocks, 5-10 min)
- `/top` - Show top 10 stocks
- `/status` - Check scan status
- Send any ticker (e.g., `NVDA`) - Get analysis

### Notifications
You'll receive Telegram notifications when:
- Daily scan completes
- You trigger manual scan via `/scan`
- New hot stocks are found

---

## Summary Checklist

Before testing, make sure:

- [ ] Added TELEGRAM_BOT_TOKEN to GitHub Secrets
- [ ] Added TELEGRAM_CHAT_ID to GitHub Secrets
- [ ] Added MODAL_TOKEN_ID to GitHub Secrets
- [ ] Added MODAL_TOKEN_SECRET to GitHub Secrets
- [ ] Manually triggered workflow OR waited for next scheduled run
- [ ] Sent /help to @Stocks_Story_Bot
- [ ] Received response from bot ✅

---

## Quick Copy-Paste Reference

**For GitHub Secrets page** (https://github.com/zhuanleee/stock_scanner_bot/settings/secrets/actions):

```
Secret 1:
Name: TELEGRAM_BOT_TOKEN
Value: 7626822299:AAHVNKOLIVelbBwOEO2J2aE_6D34Ml0RuuM

Secret 2:
Name: TELEGRAM_CHAT_ID
Value: 1191814045

Secret 3:
Name: MODAL_TOKEN_ID
Value: wk-nUmIlRoKEbHVj8CDDcimf2

Secret 4:
Name: MODAL_TOKEN_SECRET
Value: ws-EAZXk2XZaOQ2ZngQ8ivYET
```

---

**Status**: ✅ All credentials verified and ready to use!

Once you add these 4 secrets to GitHub, your Telegram bot will be fully operational! 🚀
