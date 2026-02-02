# API Authentication Migration Guide

**Date:** February 1, 2026
**Status:** Grace Period Active
**Enforcement Date:** TBD (7+ days from deployment)

---

## Overview

The Stock Scanner API now supports API key authentication with rate limiting. This guide explains how to migrate to the new authentication system.

## Current Status

**Grace Period Active:** API keys are optional but recommended. The system will log warnings for requests without API keys but will still process them.

**Enforcement:** Set `REQUIRE_API_KEYS=true` environment variable to enforce authentication (planned after 7-day grace period).

---

## Quick Start

### 1. Get an API Key

Visit the API key request endpoint:

```bash
GET https://your-api-url/api-keys/request
```

Response:
```json
{
  "ok": true,
  "message": "API Key Request Instructions",
  "instructions": [
    "1. Email your request to: support@stockscanner.example.com",
    "2. Include: your name, email, intended use case",
    "3. You'll receive an API key within 24 hours"
  ],
  "tiers": {
    "free": {"requests_per_day": 1000, "price": "$0"},
    "pro": {"requests_per_day": 10000, "price": "$49/month"},
    "enterprise": {"requests_per_day": 100000, "price": "Contact us"}
  }
}
```

### 2. Generate API Key (Development/Testing)

For immediate testing, generate a key directly:

```bash
POST https://your-api-url/api-keys/generate?user_id=your_user_id&tier=free
```

Response:
```json
{
  "ok": true,
  "api_key": "ssk_live_abc123...",
  "tier": "free",
  "requests_per_day": 1000,
  "created_at": "2026-02-01T12:00:00",
  "usage": "Include in request headers as: Authorization: Bearer <api_key>"
}
```

**Important:** Store this API key securely! It will only be shown once.

### 3. Use the API Key

Include the API key in all requests:

```bash
curl -H "Authorization: Bearer ssk_live_abc123..." \
     https://your-api-url/scan
```

Or in JavaScript:

```javascript
const response = await fetch('https://your-api-url/scan', {
  headers: {
    'Authorization': 'Bearer ssk_live_abc123...'
  }
});
```

---

## API Key Tiers

| Tier | Requests/Day | Price | Use Case |
|------|--------------|-------|----------|
| **Free** | 1,000 | $0 | Personal projects, testing |
| **Pro** | 10,000 | $49/month | Production apps, dashboards |
| **Enterprise** | 100,000 | Contact us | High-volume applications |

---

## Rate Limiting

### Per-Request Rate Limit
- **10 requests/second** per API key (token bucket algorithm)
- Exceeding this returns HTTP 429 with `Retry-After` header

### Daily Rate Limit
- Varies by tier (see table above)
- Resets daily at midnight UTC
- Exceeding returns HTTP 401 with error message

### Rate Limit Headers

All responses include rate limit information:

```
X-RateLimit-Remaining: 9543
X-RateLimit-Reset: 2026-02-02T00:00:00
```

---

## API Endpoints

### Authentication Required

All endpoints require API keys **except**:
- `GET /` - Root/info
- `GET /health` - Health check
- `GET /api-keys/request` - Request instructions
- `GET /api-keys/generate` - Generate key (during grace period)

### Management Endpoints

#### Get Usage Statistics

```bash
GET /api-keys/usage
Authorization: Bearer <your-api-key>
```

Response:
```json
{
  "ok": true,
  "usage": {
    "tier": "free",
    "requests_per_day": 1000,
    "daily_requests": 234,
    "requests_remaining": 766,
    "total_requests": 5432,
    "last_used": "2026-02-01T12:34:56",
    "is_active": true
  }
}
```

#### Revoke an API Key

```bash
POST /api-keys/revoke?api_key=ssk_live_abc123...
```

Response:
```json
{
  "ok": true,
  "message": "API key revoked successfully"
}
```

---

## Migration Timeline

### Week 1 (Current)
- ✅ API authentication system deployed
- ✅ Grace period active (API keys optional)
- ✅ Warnings logged for requests without keys
- ✅ Migration guide published

### Week 2
- Send email notifications to users
- Update dashboard documentation
- Monitor adoption rate

### Week 3+
- Set `REQUIRE_API_KEYS=true` to enforce authentication
- All requests require valid API keys
- Grace period ends

---

## Code Examples

### Python

```python
import requests

API_KEY = "ssk_live_abc123..."
BASE_URL = "https://your-api-url"

headers = {
    "Authorization": f"Bearer {API_KEY}"
}

# Get scan results
response = requests.get(f"{BASE_URL}/scan", headers=headers)
print(response.json())

# Check usage
usage = requests.get(f"{BASE_URL}/api-keys/usage", headers=headers)
print(f"Requests remaining: {usage.json()['usage']['requests_remaining']}")
```

### JavaScript/React

```javascript
const API_KEY = "ssk_live_abc123...";
const BASE_URL = "https://your-api-url";

async function fetchScanResults() {
  const response = await fetch(`${BASE_URL}/scan`, {
    headers: {
      'Authorization': `Bearer ${API_KEY}`
    }
  });

  // Check rate limit headers
  const remaining = response.headers.get('X-RateLimit-Remaining');
  const resetAt = response.headers.get('X-RateLimit-Reset');

  console.log(`Rate limit: ${remaining} requests remaining`);
  console.log(`Resets at: ${resetAt}`);

  return await response.json();
}
```

### cURL

```bash
# Store API key in environment variable
export API_KEY="ssk_live_abc123..."

# Make authenticated request
curl -H "Authorization: Bearer $API_KEY" \
     https://your-api-url/scan

# Check usage
curl -H "Authorization: Bearer $API_KEY" \
     https://your-api-url/api-keys/usage
```

---

## Error Handling

### 401 Unauthorized

**Missing API Key:**
```json
{
  "ok": false,
  "error": "Missing API key",
  "message": "Include 'Authorization: Bearer <your-api-key>' header",
  "get_key": "/api-keys/request"
}
```

**Invalid API Key:**
```json
{
  "ok": false,
  "error": "Authentication failed",
  "message": "Invalid API key"
}
```

**Daily Limit Exceeded:**
```json
{
  "ok": false,
  "error": "Authentication failed",
  "message": "Daily rate limit exceeded (1000 requests/day)"
}
```

### 429 Too Many Requests

**Per-Second Rate Limit:**
```json
{
  "ok": false,
  "error": "Authentication failed",
  "message": "Rate limit exceeded. Retry after 0.34 seconds",
  "rate_limit": {
    "retry_after": 0.34
  }
}
```

**Handling in Code:**

```javascript
async function fetchWithRetry(url, maxRetries = 3) {
  for (let i = 0; i < maxRetries; i++) {
    const response = await fetch(url, {
      headers: { 'Authorization': `Bearer ${API_KEY}` }
    });

    if (response.status === 429) {
      // Rate limited - wait and retry
      const retryAfter = parseFloat(response.headers.get('Retry-After') || '1');
      await new Promise(resolve => setTimeout(resolve, retryAfter * 1000));
      continue;
    }

    return response;
  }

  throw new Error('Max retries exceeded');
}
```

---

## Best Practices

### Security

1. **Never commit API keys to git**
   - Use environment variables
   - Add `.env` to `.gitignore`

2. **Store keys securely**
   - Use environment variables or secrets management
   - Never hardcode in source files

3. **Rotate keys periodically**
   - Generate new keys every 90 days
   - Revoke old keys after migration

### Performance

1. **Implement exponential backoff**
   - Handle 429 responses gracefully
   - Wait before retrying

2. **Cache responses**
   - Reduce API calls
   - Respect cache headers

3. **Monitor usage**
   - Check `/api-keys/usage` regularly
   - Upgrade tier before hitting limits

### Error Handling

1. **Check rate limit headers**
   - `X-RateLimit-Remaining`
   - `X-RateLimit-Reset`

2. **Handle 401/429 gracefully**
   - Show user-friendly error messages
   - Implement retry logic

3. **Log authentication errors**
   - Track failed requests
   - Alert on repeated failures

---

## FAQ

**Q: Do I need an API key right now?**
A: Not immediately. The grace period allows requests without keys. However, we recommend getting one now to avoid disruption.

**Q: How long is the grace period?**
A: Minimum 7 days, but we'll notify users before enforcement begins.

**Q: What happens if I exceed my rate limit?**
A: You'll receive a 401 error and must wait until the next day (midnight UTC) or upgrade your tier.

**Q: Can I have multiple API keys?**
A: Yes! Generate multiple keys for different apps or environments (dev/staging/prod).

**Q: How do I upgrade my tier?**
A: Email support@stockscanner.example.com to discuss Pro or Enterprise plans.

**Q: What if my key is compromised?**
A: Immediately revoke it via `/api-keys/revoke` and generate a new one.

**Q: Are API keys required for the dashboard?**
A: If you're hosting your own dashboard, yes. The dashboard should include the API key in its requests.

---

## Support

**Questions?** Email: support@stockscanner.example.com

**Issues?** GitHub: https://github.com/yourusername/stock_scanner_bot/issues

**Documentation:** https://your-docs-url.com/api-authentication

---

**Last Updated:** February 1, 2026
**Version:** 1.0
**Status:** Active (Grace Period)
