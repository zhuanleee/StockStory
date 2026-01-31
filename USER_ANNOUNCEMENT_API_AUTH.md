# Stock Scanner API - Important Update: Authentication Required

**Date:** February 1, 2026
**Effective Date:** February 8, 2026 (7 days)
**Action Required:** Get your free API key

---

## What's Changing?

Starting **February 8, 2026**, all Stock Scanner API requests will require an API key for authentication. This change improves security and enables us to provide better service with usage tracking and tiered access.

---

## Action Required

### Get Your Free API Key (Takes 2 minutes)

**Option 1: Self-Service (Instant)**

```bash
curl -X POST "https://your-api-url.modal.run/api-keys/generate?user_id=YOUR_EMAIL&tier=free"
```

Response:
```json
{
  "ok": true,
  "api_key": "ssk_live_abc123...",
  "tier": "free",
  "requests_per_day": 1000
}
```

**⚠️ Important:** Save your API key! It will only be shown once.

**Option 2: Email Request**

Send an email to: `support@example.com` with:
- Your name
- Email address
- Intended use case

You'll receive your API key within 24 hours.

---

## How to Use Your API Key

### In Your Dashboard

Add this to your dashboard JavaScript:

```javascript
const API_KEY = "YOUR_API_KEY_HERE"; // ⚠️ Store securely!

// Update all API calls
fetch('https://your-api-url.modal.run/scan', {
  headers: {
    'Authorization': `Bearer ${API_KEY}`
  }
})
```

### In Python

```python
import requests

API_KEY = "YOUR_API_KEY_HERE"
headers = {"Authorization": f"Bearer {API_KEY}"}

response = requests.get(
    "https://your-api-url.modal.run/scan",
    headers=headers
)
```

### In cURL

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
     https://your-api-url.modal.run/scan
```

---

## API Tiers & Limits

| Tier | Requests/Day | Cost | Who It's For |
|------|--------------|------|--------------|
| **Free** | 1,000 | $0 | Personal projects, testing |
| **Pro** | 10,000 | $49/month | Production apps, dashboards |
| **Enterprise** | 100,000 | Custom | High-volume applications |

**Rate Limit:** 10 requests/second (all tiers)

### Free Tier Benefits
- ✅ 1,000 API calls per day
- ✅ Access to all endpoints
- ✅ Real-time stock data
- ✅ Story-first scoring
- ✅ Theme intelligence
- ✅ Social sentiment analysis
- ✅ No credit card required

---

## Timeline

### February 1, 2026 (Today)
- ✅ API authentication system launched
- ✅ Grace period begins
- ✅ All requests work with or without API keys
- ✅ Warnings logged for requests without keys

### February 1-7, 2026 (Grace Period)
- Generate your API key
- Update your code
- Test your integration
- No service disruption

### February 8, 2026 (Enforcement)
- API keys become **required**
- Requests without keys will be rejected (HTTP 401)
- Free tier: 1,000 requests/day activated

---

## What You Need to Do

### Step 1: Get Your API Key (2 minutes)
```bash
curl -X POST "https://your-api-url.modal.run/api-keys/generate?user_id=YOUR_EMAIL&tier=free"
```

### Step 2: Store It Securely
- ❌ Don't commit to git
- ❌ Don't hardcode in source files
- ✅ Use environment variables
- ✅ Use secrets management

### Step 3: Update Your Code (5 minutes)

**Before:**
```javascript
fetch('https://your-api-url.modal.run/scan')
```

**After:**
```javascript
fetch('https://your-api-url.modal.run/scan', {
  headers: { 'Authorization': `Bearer ${API_KEY}` }
})
```

### Step 4: Test (1 minute)
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
     https://your-api-url.modal.run/health
```

Should return: `{"ok": true, "status": "healthy", ...}`

---

## Monitoring Your Usage

Check your API usage anytime:

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
     https://your-api-url.modal.run/api-keys/usage
```

Response:
```json
{
  "ok": true,
  "usage": {
    "daily_requests": 234,
    "requests_remaining": 766,
    "total_requests": 5432
  }
}
```

**Dashboard:** Visit `/admin/dashboard` to see real-time metrics.

---

## FAQ

**Q: Why is authentication being added?**
A: To improve security, prevent abuse, enable usage tracking, and provide tiered service levels.

**Q: Do I need to pay?**
A: No! The free tier provides 1,000 requests/day at no cost.

**Q: What happens if I exceed 1,000 requests/day?**
A: You'll receive an error. Upgrade to Pro for 10,000 requests/day.

**Q: Can I have multiple API keys?**
A: Yes! Generate separate keys for dev/staging/prod environments.

**Q: What if my key is compromised?**
A: Revoke it immediately and generate a new one:
```bash
curl -X POST "https://your-api-url.modal.run/api-keys/revoke?api_key=OLD_KEY"
```

**Q: Will my existing dashboard break?**
A: Not during the grace period (Feb 1-7). Update before Feb 8 to avoid disruption.

**Q: Is the API key encrypted?**
A: Keys are validated securely. Store them as secrets, never in plain text.

**Q: Can I test before updating production?**
A: Yes! Generate a test key and verify your integration during the grace period.

---

## Upgrade to Pro

Need more than 1,000 requests/day?

**Pro Tier Benefits:**
- ✅ 10,000 requests/day (10x more!)
- ✅ Priority support
- ✅ Usage analytics
- ✅ $49/month

**Enterprise Tier:**
- ✅ 100,000+ requests/day
- ✅ Custom rate limits
- ✅ SLA guarantees
- ✅ Dedicated support
- ✅ Custom pricing

**Contact:** support@example.com

---

## Need Help?

**Documentation:**
- API Reference: `/docs` (Swagger UI)
- Migration Guide: `API_AUTH_MIGRATION_GUIDE.md`
- Code Examples: `API_DOCUMENTATION.md`

**Support:**
- Email: support@example.com
- GitHub Issues: https://github.com/yourusername/stock_scanner_bot/issues

**Response Time:**
- Free: 24-48 hours
- Pro: 12 hours
- Enterprise: 4 hours

---

## Summary

✅ **Action Required:** Get your free API key
✅ **Timeline:** 7-day grace period (Feb 1-8)
✅ **Free Tier:** 1,000 requests/day, $0
✅ **Update Code:** Add `Authorization: Bearer` header
✅ **Test:** Verify before Feb 8

**Get started now:** https://your-api-url.modal.run/api-keys/generate

---

Thank you for being a valued user of Stock Scanner API!

We're committed to providing the best stock analysis platform possible. API authentication enables us to deliver better service, reliability, and features.

**Questions?** Reply to this email or contact support@example.com

Best regards,
Stock Scanner Team

---

**P.S.** Upgrade to Pro anytime for 10x more requests at just $49/month!
