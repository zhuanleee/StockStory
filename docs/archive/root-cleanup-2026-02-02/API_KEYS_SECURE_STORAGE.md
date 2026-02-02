# API Keys - Secure Storage Guide

## Current Key Inventory

Your stock scanner uses **15 API keys** across 5 categories:

### 1. Financial Data APIs (5 keys)
- `POLYGON_API_KEY` - Stock prices and market data
- `FINNHUB_API_KEY` - Financial data and news
- `ALPHA_VANTAGE_API_KEY` - Market data
- `TIINGO_API_KEY` - Stock data
- `FRED_API_KEY` - Economic data (Federal Reserve)

### 2. AI Services (3 keys)
- `DEEPSEEK_API_KEY` - Primary AI for analysis ✅ (GitHub Secret)
- `XAI_API_KEY` - X.AI Grok for intelligence
- `OPENAI_API_KEY` - OpenAI GPT (optional)

### 3. Intelligence Sources (1 key)
- `PATENTSVIEW_API_KEY` - Patent data

### 4. Communication (3 keys)
- `TELEGRAM_BOT_TOKEN` - Telegram bot ✅ (GitHub Secret)
- `TELEGRAM_CHAT_ID` - Your Telegram chat ✅ (GitHub Secret)
- `BOT_USERNAME` - Bot username ✅ (GitHub Secret)

### 5. Infrastructure (3 keys)
- `MODAL_TOKEN_ID` - Modal.com auth ✅ (GitHub Secret)
- `MODAL_TOKEN_SECRET` - Modal.com secret ✅ (GitHub Secret)
- `WEBHOOK_SECRET` - API webhook security

---

## Where Keys Are Currently Stored

### ✅ GitHub Secrets (6 keys - SECURE)
Location: https://github.com/zhuanleee/stock_scanner_bot/settings/secrets/actions

- `DEEPSEEK_API_KEY`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `BOT_USERNAME`
- `MODAL_TOKEN_ID`
- `MODAL_TOKEN_SECRET`

**Purpose**: Used by GitHub Actions for deployment and Telegram notifications

### ✅ Modal Secrets (1 secret bundle - SECURE)
Location: https://modal.com/zhuanleee/secrets

Secret name: `stock-api-keys`

**Contains**: All API keys needed for scanner and API runtime
- All financial data API keys
- All AI API keys
- Telegram keys
- Patent API key

**Purpose**: Used by Modal scanner and API at runtime

### ⚠️ Local .env File (NOT committed to git)
Location: `/Users/johnlee/stock_scanner_bot/.env`

**Status**: Should exist for local development, but NOT committed to git

---

## Security Checklist

- ✅ GitHub Secrets configured for CI/CD
- ✅ Modal Secrets configured for runtime
- ✅ .env in .gitignore (keys won't be committed)
- ✅ Repository is public (keys are in secrets, not code)
- ⚠️ Need to verify all keys are in Modal secret
- ⚠️ Need to create .env.example template

---

## How to Securely Store Your Keys

### Option 1: Password Manager (RECOMMENDED)
Store all keys in a password manager with 2FA:

**Recommended managers:**
- 1Password
- Bitwarden
- LastPass
- Dashlane

**Structure:**
```
Stock Scanner Bot/
├── Financial APIs/
│   ├── Polygon API Key: sk_xxxxx
│   ├── Finnhub API Key: xxxxx
│   ├── Alpha Vantage Key: xxxxx
│   ├── Tiingo API Key: xxxxx
│   └── FRED API Key: xxxxx
├── AI Services/
│   ├── DeepSeek API Key: sk_xxxxx
│   ├── XAI API Key: xxxxx
│   └── OpenAI API Key: sk_xxxxx
├── Intelligence/
│   └── PatentsView API Key: xxxxx
├── Communication/
│   ├── Telegram Bot Token: xxxxx:xxxxx
│   ├── Telegram Chat ID: -xxxxx
│   └── Bot Username: @xxxxx
└── Infrastructure/
    ├── Modal Token ID: xxxxx
    ├── Modal Token Secret: xxxxx
    └── Webhook Secret: xxxxx
```

### Option 2: Encrypted File (Advanced)
```bash
# Create encrypted file
gpg --symmetric --cipher-algo AES256 api_keys.txt

# This creates api_keys.txt.gpg (encrypted)
# Store the passphrase in your password manager

# To decrypt when needed:
gpg api_keys.txt.gpg
```

### Option 3: macOS Keychain (Mac only)
```bash
# Store a key
security add-generic-password -a "$USER" -s "POLYGON_API_KEY" -w "your-key-here"

# Retrieve a key
security find-generic-password -a "$USER" -s "POLYGON_API_KEY" -w
```

---

## Setting Up Keys for the First Time

### 1. Create Local .env File
```bash
cd /Users/johnlee/stock_scanner_bot
cp .env.example .env
```

Then edit `.env` and fill in your keys.

### 2. Add Keys to GitHub Secrets
```bash
# One-time setup for each key
gh secret set POLYGON_API_KEY --body "your-key-here"
gh secret set FINNHUB_API_KEY --body "your-key-here"
gh secret set ALPHA_VANTAGE_API_KEY --body "your-key-here"
# ... etc
```

Or via GitHub web UI:
1. Go to https://github.com/zhuanleee/stock_scanner_bot/settings/secrets/actions
2. Click "New repository secret"
3. Add name and value
4. Click "Add secret"

### 3. Add Keys to Modal Secret
Via Modal web UI:
1. Go to https://modal.com/zhuanleee/secrets
2. Click "Create secret"
3. Name it `stock-api-keys`
4. Add all keys as key-value pairs
5. Save

Or via Modal CLI:
```bash
modal secret create stock-api-keys \
  POLYGON_API_KEY="your-key" \
  FINNHUB_API_KEY="your-key" \
  DEEPSEEK_API_KEY="your-key" \
  XAI_API_KEY="your-key" \
  TELEGRAM_BOT_TOKEN="your-token" \
  TELEGRAM_CHAT_ID="your-chat-id"
```

---

## .env.example Template

I'll create a `.env.example` file in your repo with all required keys (no actual values).

---

## Getting API Keys (Where to Sign Up)

### Financial Data APIs

**Polygon.io** (RECOMMENDED - Best for stock data)
- URL: https://polygon.io/
- Free tier: 5 calls/min
- Paid: $29/month for unlimited

**Finnhub**
- URL: https://finnhub.io/
- Free tier: 60 calls/min
- Good for news and earnings

**Alpha Vantage**
- URL: https://www.alphavantage.co/
- Free tier: 25 calls/day
- Limited but free

**Tiingo**
- URL: https://www.tiingo.com/
- Free tier: 1,000 calls/day

**FRED (Federal Reserve Economic Data)**
- URL: https://fred.stlouisfed.org/docs/api/api_key.html
- Free, unlimited
- Required for economic data

### AI Services

**DeepSeek** (PRIMARY - REQUIRED)
- URL: https://platform.deepseek.com/
- Very affordable ($0.14 per 1M tokens)
- Best for financial analysis

**X.AI (Grok)**
- URL: https://x.ai/api
- Premium ($20/month for X Premium+ includes API access)
- Optional, for X/Twitter intelligence

**OpenAI**
- URL: https://platform.openai.com/
- Optional fallback
- More expensive than DeepSeek

### Intelligence Sources

**PatentsView**
- URL: https://patentsview.org/apis/purpose
- Free, requires registration
- For patent intelligence

### Communication

**Telegram Bot**
- Create bot: https://t.me/BotFather
- Send `/newbot` to BotFather
- Get token and chat ID

---

## Security Best Practices

### ✅ DO:
- Store keys in password manager with 2FA
- Use environment variables for local development
- Use GitHub Secrets for CI/CD
- Use Modal Secrets for runtime
- Rotate keys every 6-12 months
- Use different keys for dev/staging/production
- Monitor API usage for unusual activity

### ❌ DON'T:
- Commit .env file to git
- Share keys in Slack/email/Discord
- Store keys in plaintext files
- Use same key across multiple projects
- Share your screen while keys are visible
- Store keys in browser bookmarks/notes

---

## Key Rotation Schedule

Rotate keys regularly to maintain security:

| Key Type | Rotation Frequency | Last Rotated |
|----------|-------------------|--------------|
| Financial APIs | Every 12 months | - |
| AI APIs | Every 6 months | - |
| Telegram Bot | When compromised | Jan 2026 |
| Modal Tokens | Every 12 months | Jan 2026 |
| Webhook Secret | Every 6 months | - |

---

## Emergency: Key Compromised

If a key is compromised:

1. **Immediately revoke** the key at the provider
2. **Generate new key** from provider
3. **Update all locations**:
   - Local .env
   - GitHub Secrets
   - Modal Secrets
   - Password manager
4. **Check logs** for unauthorized usage
5. **Monitor billing** for unexpected charges

---

## Checking Which Keys Are Set

Run this command to see which keys are configured:

```bash
cd /Users/johnlee/stock_scanner_bot
python3 src/config.py
```

Output shows:
```
Configuration Status:
  Valid: True

  APIs:
    ✅ polygon
    ✅ finnhub
    ❌ alpha_vantage
    ✅ deepseek
    ✅ xai
    ❌ openai
    ❌ patents
    ✅ telegram
```

---

## Quick Reference: Where Each Key Is Used

| Key | Local Dev | GitHub Actions | Modal Runtime |
|-----|-----------|----------------|---------------|
| POLYGON_API_KEY | .env | - | Modal Secret |
| FINNHUB_API_KEY | .env | - | Modal Secret |
| ALPHA_VANTAGE_API_KEY | .env | - | Modal Secret |
| TIINGO_API_KEY | .env | - | Modal Secret |
| FRED_API_KEY | .env | - | Modal Secret |
| DEEPSEEK_API_KEY | .env | GitHub Secret | Modal Secret |
| XAI_API_KEY | .env | - | Modal Secret |
| OPENAI_API_KEY | .env | - | Modal Secret |
| PATENTSVIEW_API_KEY | .env | - | Modal Secret |
| TELEGRAM_BOT_TOKEN | .env | GitHub Secret | Modal Secret |
| TELEGRAM_CHAT_ID | .env | GitHub Secret | Modal Secret |
| BOT_USERNAME | - | GitHub Secret | - |
| MODAL_TOKEN_ID | - | GitHub Secret | - |
| MODAL_TOKEN_SECRET | - | GitHub Secret | - |
| WEBHOOK_SECRET | .env | - | Modal Secret |

---

## Next Steps

1. ✅ Review this document
2. ⬜ Copy all keys to password manager
3. ⬜ Verify Modal secret has all required keys
4. ⬜ Create local .env file from .env.example
5. ⬜ Test local development with keys
6. ⬜ Set up key rotation calendar reminders
7. ⬜ Document where you got each key (in password manager notes)

---

**Security Status**: 6/15 keys in GitHub Secrets ✅
**Next Action**: Verify Modal secret has all 15 keys
