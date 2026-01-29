# Digital Ocean Environment Variables Setup
**Date**: 2026-01-30
**Platform**: Digital Ocean App Platform

---

## 🔑 **REQUIRED API KEYS**

You need to add these environment variables in the Digital Ocean App Platform console.

### **HOW TO ADD ENVIRONMENT VARIABLES IN DIGITAL OCEAN**:

1. Go to Digital Ocean App Platform: https://cloud.digitalocean.com/apps
2. Select your app: **stock-scanner-bot**
3. Click **Settings** tab
4. Scroll to **Environment Variables** section
5. Click **Edit** button
6. Add each variable below (click **+ Add Variable** for each)
7. Set each as **ENCRYPTED** (Secret type)
8. Click **Save**
9. Digital Ocean will redeploy automatically

---

## 📋 **ENVIRONMENT VARIABLES TO ADD**

### **1. REQUIRED - Financial Data**

#### **POLYGON_API_KEY**
- **Value**: `3fmE3mk57qwEQhTC8c5foYy9lxE6E0Yj`
- **Type**: Encrypted/Secret
- **Purpose**: Primary stock market data provider (faster, more reliable than yfinance)
- **Required**: YES - App will fail without this

---

### **2. REQUIRED - AI Services**

#### **DEEPSEEK_API_KEY**
- **Value**: `sk-54f0388472604628b50116e666a0a5e9`
- **Type**: Encrypted/Secret
- **Purpose**: AI-powered stock analysis and ranking
- **Required**: YES - Core AI features depend on this

#### **XAI_API_KEY**
- **Value**: `xai-rpJZuAih41zVtn5WV4cAr6XRgSrP0LwCTuklT31sK3gJtf5DJXi23YhCLDX6bDz6aIUDrKZ7gGLWtqTo`
- **Type**: Encrypted/Secret
- **Purpose**: X Intelligence via xAI Grok for real-time sentiment analysis
- **Required**: YES - Enhanced AI features

---

### **3. REQUIRED - Telegram Bot**

⚠️ **MISSING IN YOUR .env FILE** - You need to add these:

#### **TELEGRAM_BOT_TOKEN**
- **Value**: `YOUR_TELEGRAM_BOT_TOKEN_HERE`
- **Type**: Encrypted/Secret
- **Purpose**: Telegram bot authentication
- **Required**: YES - Bot won't work without this
- **How to get**:
  1. Message @BotFather on Telegram
  2. Create a new bot with `/newbot`
  3. Copy the token provided

#### **TELEGRAM_CHAT_ID**
- **Value**: `YOUR_TELEGRAM_CHAT_ID_HERE`
- **Type**: Encrypted/Secret
- **Purpose**: Your personal Telegram chat ID for receiving alerts
- **Required**: YES - Determines where messages are sent
- **How to get**:
  1. Message @userinfobot on Telegram
  2. It will reply with your chat ID
  3. Copy the numeric ID

---

### **4. REQUIRED - Earnings Intelligence**

⚠️ **MISSING IN YOUR .env FILE** - You need to add this:

#### **ALPHA_VANTAGE_API_KEY**
- **Value**: `YOUR_ALPHA_VANTAGE_KEY_HERE`
- **Type**: Encrypted/Secret
- **Purpose**: Earnings data and fundamental analysis
- **Required**: YES - Earnings features won't work without this
- **How to get**:
  1. Go to https://www.alphavantage.co/support/#api-key
  2. Sign up for free API key
  3. Copy the key

---

### **5. OPTIONAL - Enhanced Features**

These are optional but recommended for full functionality:

#### **FINNHUB_API_KEY**
- **Value**: `YOUR_FINNHUB_KEY_HERE` (if you have one)
- **Type**: Encrypted/Secret
- **Purpose**: Additional market data and news
- **Required**: NO - App works without this
- **How to get**:
  1. Go to https://finnhub.io/register
  2. Sign up for free API key
  3. Copy the key

#### **PATENTSVIEW_API_KEY**
- **Value**: `YOUR_PATENTSVIEW_KEY_HERE` (if you have one)
- **Type**: Encrypted/Secret
- **Purpose**: Patent intelligence and innovation tracking
- **Required**: NO - App works without this
- **How to get**:
  1. Go to https://patentsview.org/apis/keyrequest
  2. Request API key
  3. Copy the key from email

---

## ✅ **PRE-CONFIGURED VARIABLES**

These are already set in `.do/app.yaml` - **NO ACTION NEEDED**:

### **Feature Flags** (Already configured):
- `USE_AI_BRAIN_RANKING=true`
- `USE_LEARNING_SYSTEM=true`
- `MAX_CONCURRENT_SCANS=25`
- `PYTHONUNBUFFERED=1`

---

## 🚨 **CRITICAL: MISSING KEYS**

Based on your local `.env` file, you are **MISSING** these required keys:

1. ❌ **TELEGRAM_BOT_TOKEN** - Not found in .env
2. ❌ **TELEGRAM_CHAT_ID** - Not found in .env
3. ❌ **ALPHA_VANTAGE_API_KEY** - Not found in .env

### **What Happens Without These**:
- **Without Telegram keys**: Bot commands won't work, no alerts sent
- **Without Alpha Vantage**: Earnings analysis will fail, some features broken

### **Quick Fix**:

Add these to your local `.env` file AND to Digital Ocean:

```bash
# Add to your local .env file:
TELEGRAM_BOT_TOKEN=your_token_from_botfather
TELEGRAM_CHAT_ID=your_chat_id_from_userinfobot
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key
```

---

## 📝 **STEP-BY-STEP DIGITAL OCEAN SETUP**

### **Step 1: Access Environment Variables**
```
1. Go to: https://cloud.digitalocean.com/apps
2. Click on: stock-scanner-bot
3. Click: Settings tab
4. Scroll to: App-Level Environment Variables
5. Click: Edit
```

### **Step 2: Add Each Variable**

For each variable below, click **+ Add Variable**:

| Variable Name | Value | Type |
|---------------|-------|------|
| `POLYGON_API_KEY` | `3fmE3mk57qwEQhTC8c5foYy9lxE6E0Yj` | Encrypted |
| `DEEPSEEK_API_KEY` | `sk-54f0388472604628b50116e666a0a5e9` | Encrypted |
| `XAI_API_KEY` | `xai-rpJZuAih41zVtn5WV4cAr6XRgSrP0LwCTuklT31sK3gJtf5DJXi23YhCLDX6bDz6aIUDrKZ7gGLWtqTo` | Encrypted |
| `TELEGRAM_BOT_TOKEN` | *YOUR_TOKEN_HERE* | Encrypted |
| `TELEGRAM_CHAT_ID` | *YOUR_CHAT_ID_HERE* | Encrypted |
| `ALPHA_VANTAGE_API_KEY` | *YOUR_KEY_HERE* | Encrypted |
| `FINNHUB_API_KEY` | *OPTIONAL* | Encrypted |
| `PATENTSVIEW_API_KEY` | *OPTIONAL* | Encrypted |

### **Step 3: Save and Deploy**
```
1. Click: Save
2. Digital Ocean will ask: "This will redeploy your app. Continue?"
3. Click: Save (confirms redeployment)
4. Wait: 4-6 minutes for deployment
5. Check: Health endpoint after deployment
```

---

## 🔍 **VERIFICATION**

After adding environment variables and deployment completes:

### **Check Health Endpoint**:
```bash
curl https://stock-story-jy89o.ondigitalocean.app/health
```

**Expected Response**:
```json
{
  "status": "healthy",
  "timestamp": "2026-01-30T...",
  "version": "1.0"
}
```

### **Check API Keys Are Loaded**:

The app will log during startup if keys are missing:
- ✅ "Polygon API initialized" = POLYGON_API_KEY working
- ✅ "DeepSeek AI initialized" = DEEPSEEK_API_KEY working
- ✅ "xAI initialized" = XAI_API_KEY working
- ✅ "Telegram bot initialized" = TELEGRAM_BOT_TOKEN working
- ⚠️ "Alpha Vantage not configured" = ALPHA_VANTAGE_API_KEY missing

---

## 🔐 **SECURITY NOTES**

### **API Key Security**:
1. ✅ Never commit API keys to git (already protected by .gitignore)
2. ✅ Use "Encrypted" type in Digital Ocean for all secrets
3. ✅ Rotate API keys quarterly for security
4. ✅ Monitor API usage in each service's dashboard
5. ✅ Set up billing alerts to prevent unexpected charges

### **Key Rotation Checklist**:
When rotating keys (recommended every 3 months):
1. Generate new key in service dashboard
2. Update Digital Ocean environment variable
3. Update local .env file
4. Test in production
5. Revoke old key

---

## 🆘 **TROUBLESHOOTING**

### **Problem: "ModuleNotFoundError: No module named 'app'"**
**Solution**: ✅ Already fixed in latest deployment with correct gunicorn config

### **Problem: "Polygon API key invalid"**
**Solution**:
1. Verify key is exactly: `3fmE3mk57qwEQhTC8c5foYy9lxE6E0Yj`
2. No extra spaces or line breaks
3. Type is "Encrypted" in Digital Ocean

### **Problem: "Telegram bot not responding"**
**Solution**:
1. Verify TELEGRAM_BOT_TOKEN is set
2. Verify TELEGRAM_CHAT_ID is set
3. Test bot with `/start` command in Telegram
4. Check deployment logs for "Telegram bot initialized"

### **Problem: "Earnings data not loading"**
**Solution**:
1. Add ALPHA_VANTAGE_API_KEY to Digital Ocean
2. Get free key from https://www.alphavantage.co/support/#api-key
3. Redeploy app

---

## 📊 **CURRENT STATUS**

### **Keys You Have** (in local .env):
- ✅ POLYGON_API_KEY
- ✅ DEEPSEEK_API_KEY
- ✅ XAI_API_KEY

### **Keys You Need to Get**:
- ❌ TELEGRAM_BOT_TOKEN
- ❌ TELEGRAM_CHAT_ID
- ❌ ALPHA_VANTAGE_API_KEY
- ⚪ FINNHUB_API_KEY (optional)
- ⚪ PATENTSVIEW_API_KEY (optional)

### **Estimated Setup Time**:
- **If you have all keys**: 5 minutes
- **If you need to get keys**: 15-20 minutes
- **Deployment after setup**: 4-6 minutes

---

## ✅ **QUICK CHECKLIST**

Before deploying, ensure:
- [ ] All 6 required API keys obtained
- [ ] Each key added to Digital Ocean (Encrypted type)
- [ ] Keys tested locally first (optional but recommended)
- [ ] Digital Ocean redeployment triggered
- [ ] Health check passes after deployment
- [ ] Telegram bot responds to `/start` command
- [ ] Dashboard loads without errors

---

**Status**: Review this document and add the missing API keys to Digital Ocean
**Priority**: HIGH - App won't work fully without Telegram and Alpha Vantage keys
**Next Step**: Get missing API keys, then add all keys to Digital Ocean environment variables
