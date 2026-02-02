# 🔴 URGENT: Credential Rotation Guide

**Status:** CRITICAL - Credentials exposed in Git
**Date:** February 1, 2026
**Priority:** P0 - Do immediately

---

## 🚨 EXPOSED CREDENTIALS

The following credentials were found exposed in `.env` file committed to Git:

```
POLYGON_API_KEY=3fmE3mk57qwEQhTC8c5foYy9lxE6E0Yj
DEEPSEEK_API_KEY=sk-54f0388472604628b50116e666a0a5e9
TELEGRAM_BOT_TOKEN=7***************:AAF***
TELEGRAM_CHAT_ID=5**********
```

---

## 📋 ROTATION CHECKLIST

### Step 1: Rotate Polygon API Key (5 min)

1. **Login to Polygon.io:**
   - Go to: https://polygon.io/dashboard
   - Navigate to: API Keys

2. **Create New Key:**
   - Click "Create New Key"
   - Name: `stock-scanner-production-v2`
   - Copy the new key

3. **Update Modal Secret:**
   ```bash
   modal secret create stock-api-keys \
       POLYGON_API_KEY=<NEW_KEY> \
       DEEPSEEK_API_KEY=<CURRENT_DEEPSEEK_KEY> \
       TELEGRAM_BOT_TOKEN=<CURRENT_TELEGRAM_TOKEN> \
       TELEGRAM_CHAT_ID=<CURRENT_TELEGRAM_CHAT_ID>
   ```

4. **Delete Old Key:**
   - In Polygon.io dashboard, delete old key `3fmE3mk...`
   - Verify new key works: `curl "https://api.polygon.io/v2/aggs/ticker/AAPL/range/1/day/2023-01-01/2023-01-10?apiKey=<NEW_KEY>"`

---

### Step 2: Rotate DeepSeek API Key (5 min)

1. **Login to DeepSeek:**
   - Go to: https://platform.deepseek.com/
   - Navigate to: API Keys

2. **Create New Key:**
   - Click "Create new secret key"
   - Name: `stock-scanner-prod`
   - Copy the new key

3. **Update Modal Secret:**
   ```bash
   modal secret create stock-api-keys \
       POLYGON_API_KEY=<NEW_POLYGON_KEY> \
       DEEPSEEK_API_KEY=<NEW_DEEPSEEK_KEY> \
       TELEGRAM_BOT_TOKEN=<CURRENT_TELEGRAM_TOKEN> \
       TELEGRAM_CHAT_ID=<CURRENT_TELEGRAM_CHAT_ID>
   ```

4. **Delete Old Key:**
   - In DeepSeek dashboard, revoke old key `sk-54f03...`
   - Test new key: `curl https://api.deepseek.com/v1/chat/completions -H "Authorization: Bearer <NEW_KEY>"`

---

### Step 3: Rotate Telegram Bot Token (5 min)

1. **Contact BotFather:**
   - Open Telegram and search for `@BotFather`
   - Send: `/mybots`
   - Select your bot
   - Choose: "API Token"
   - Click: "Revoke current token"
   - Copy the new token

2. **Update Modal Secret:**
   ```bash
   modal secret create stock-api-keys \
       POLYGON_API_KEY=<NEW_POLYGON_KEY> \
       DEEPSEEK_API_KEY=<NEW_DEEPSEEK_KEY> \
       TELEGRAM_BOT_TOKEN=<NEW_TELEGRAM_TOKEN> \
       TELEGRAM_CHAT_ID=<CURRENT_TELEGRAM_CHAT_ID>
   ```

3. **Update GitHub Secret:**
   ```bash
   # Go to: https://github.com/zhuanleee/stock_scanner_bot/settings/secrets/actions
   # Click: Update secret TELEGRAM_BOT_TOKEN
   # Paste new token
   ```

---

### Step 4: Clean Git History (10 min)

⚠️ **WARNING:** This rewrites Git history. Coordinate with team if shared repo.

1. **Backup Repository:**
   ```bash
   cd /Users/johnlee/stock_scanner_bot
   git clone . ../stock_scanner_bot_backup
   ```

2. **Remove .env from History:**
   ```bash
   git filter-branch --force --index-filter \
     "git rm --cached --ignore-unmatch .env" \
     --prune-empty --tag-name-filter cat -- --all
   ```

3. **Force Push:**
   ```bash
   git push origin --force --all
   git push origin --force --tags
   ```

4. **Clean Local Repo:**
   ```bash
   rm -rf .git/refs/original/
   git reflog expire --expire=now --all
   git gc --prune=now --aggressive
   ```

---

### Step 5: Prevent Future Exposure (5 min)

1. **Update .gitignore:**
   ```bash
   echo ".env" >> .gitignore
   echo ".env.local" >> .gitignore
   echo ".env.*.local" >> .gitignore
   git add .gitignore
   git commit -m "Add .env to .gitignore"
   git push
   ```

2. **Delete Local .env:**
   ```bash
   rm .env
   ```

3. **Create .env.example:**
   ```bash
   cat > .env.example << 'EOF'
# Financial Data APIs
POLYGON_API_KEY=your_polygon_key_here
FINNHUB_API_KEY=
ALPHA_VANTAGE_API_KEY=
TIINGO_API_KEY=
FRED_API_KEY=

# AI Services
DEEPSEEK_API_KEY=your_deepseek_key_here
XAI_API_KEY=
OPENAI_API_KEY=

# Intelligence
PATENTSVIEW_API_KEY=

# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
BOT_USERNAME=

# Feature Flags
USE_AI_BRAIN_RANKING=false
USE_LEARNING_SYSTEM=true
DEBUG=false
EOF
   git add .env.example
   git commit -m "Add .env.example template"
   git push
   ```

---

### Step 6: Verify New Setup (5 min)

1. **Test Modal Deployment:**
   ```bash
   modal deploy modal_api_v2.py
   ```

2. **Test API with New Keys:**
   ```bash
   curl "https://zhuanleee--stock-scanner-api-v2-create-fastapi-app.modal.run/health"
   ```

3. **Test Telegram Bot:**
   - Send `/help` to your bot
   - Verify it responds

4. **Check Modal Logs:**
   ```bash
   modal app logs stock-scanner-api-v2 --lines 50
   ```

---

## 🔒 SECURITY BEST PRACTICES GOING FORWARD

### 1. Never Commit Secrets

✅ **Do:**
- Use environment variables
- Use Modal Secrets
- Use GitHub Secrets
- Use .env.example templates

❌ **Don't:**
- Commit .env files
- Hardcode API keys
- Share keys in chat/email
- Store keys in code comments

### 2. Use Different Keys per Environment

```
Development:   POLYGON_API_KEY=dev_key_xxx
Staging:       POLYGON_API_KEY=staging_key_xxx
Production:    POLYGON_API_KEY=prod_key_xxx
```

### 3. Rotate Keys Regularly

- Schedule: Every 90 days
- Set calendar reminders
- Document rotation in changelog

### 4. Monitor Key Usage

- Check Polygon.io usage dashboard weekly
- Set up billing alerts
- Review access logs monthly

### 5. Principle of Least Privilege

- Use read-only keys where possible
- Limit key scope to necessary endpoints
- Use separate keys for different services

---

## 📊 POST-ROTATION VERIFICATION

After completing all steps, verify:

- [ ] New Polygon key works in production
- [ ] New DeepSeek key works in production
- [ ] New Telegram bot token works
- [ ] Old keys are deleted/revoked
- [ ] .env file removed from Git history
- [ ] .gitignore updated
- [ ] .env.example created
- [ ] Modal secrets updated
- [ ] GitHub secrets updated
- [ ] No API errors in logs
- [ ] All deployments successful

---

## 🆘 TROUBLESHOOTING

### "Modal secret not found"

```bash
# List secrets
modal secret list

# Create if missing
modal secret create stock-api-keys \
    POLYGON_API_KEY=xxx \
    DEEPSEEK_API_KEY=xxx \
    TELEGRAM_BOT_TOKEN=xxx \
    TELEGRAM_CHAT_ID=xxx
```

### "API returns 401 Unauthorized"

- Verify key is correct (no extra spaces)
- Check key has correct permissions
- Ensure key is active (not expired)
- Try regenerating key

### "Telegram bot not responding"

- Verify token with: `curl https://api.telegram.org/bot<TOKEN>/getMe`
- Check chat ID is correct
- Ensure bot is not blocked

### "Git filter-branch failed"

- Ensure you have backup
- Try BFG Repo-Cleaner instead: https://rtyley.github.io/bfg-repo-cleaner/
- Contact Git support if needed

---

## 📝 AUDIT LOG

| Date | Action | Who | Keys Rotated |
|------|--------|-----|--------------|
| 2026-02-01 | Initial rotation | System | Polygon, DeepSeek, Telegram |
| | Next rotation due | - | 2026-05-01 |

---

**Completed:** [ ] (Check when done)
**Verified by:** _______________
**Date:** _______________

**PRIORITY:** 🔴 CRITICAL - Complete within 24 hours
