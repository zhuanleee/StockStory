# Stock Scanner API Documentation

**Version:** 2.0.0
**Base URL:** `https://your-api-url.modal.run`
**Interactive Docs:** `/docs` (Swagger UI)
**Alternative Docs:** `/redoc` (ReDoc)

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Authentication](#authentication)
3. [Rate Limiting](#rate-limiting)
4. [Core Endpoints](#core-endpoints)
5. [Scanning Endpoints](#scanning-endpoints)
6. [API Key Management](#api-key-management)
7. [Admin Endpoints](#admin-endpoints)
8. [Response Format](#response-format)
9. [Error Handling](#error-handling)
10. [Code Examples](#code-examples)

---

## Getting Started

### Quick Start

```bash
# 1. Get an API key
curl https://your-api-url/api-keys/request

# 2. Generate a key (for testing)
curl -X POST "https://your-api-url/api-keys/generate?user_id=test_user&tier=free"

# 3. Use the API
curl -H "Authorization: Bearer YOUR_API_KEY" \
     https://your-api-url/scan
```

### Base URL

All API requests should be made to:
```
https://your-api-url.modal.run
```

### Content Type

All requests and responses use `application/json`.

---

## Authentication

Most endpoints require an API key.

### Header Format

```http
Authorization: Bearer YOUR_API_KEY
```

### Getting an API Key

**Option 1: Request via Email**
```bash
GET /api-keys/request
```

**Option 2: Generate Directly (Testing)**
```bash
POST /api-keys/generate?user_id=your_id&tier=free
```

### Public Endpoints (No Auth Required)

- `GET /` - API root
- `GET /health` - Health check
- `GET /api-keys/request` - Request instructions
- `GET /docs` - Interactive API docs
- `GET /redoc` - Alternative API docs

---

## Rate Limiting

### Limits by Tier

| Tier | Requests/Day | Cost | Rate Limit |
|------|--------------|------|------------|
| Free | 1,000 | $0 | 10 req/sec |
| Pro | 10,000 | $49/month | 10 req/sec |
| Enterprise | 100,000 | Custom | 10 req/sec |

### Rate Limit Headers

All responses include:

```http
X-RateLimit-Remaining: 945
X-RateLimit-Reset: 2026-02-02T00:00:00Z
```

### Rate Limit Exceeded

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

**Status Code:** `429 Too Many Requests`

---

## Core Endpoints

### GET / - API Root

Returns basic API information.

**Request:**
```bash
curl https://your-api-url/
```

**Response:**
```json
{
  "ok": true,
  "service": "stock-scanner-api-v2",
  "version": "2.0.0",
  "documentation": "/docs",
  "dashboard": "/admin/dashboard"
}
```

---

### GET /health - Health Check

Returns API and market health status.

**Request:**
```bash
curl https://your-api-url/health
```

**Response:**
```json
{
  "ok": true,
  "status": "healthy",
  "market_health": {
    "vix": 15.3,
    "spy_trend": "bullish",
    "sector_rotation": "technology_leading"
  },
  "timestamp": "2026-02-01T12:00:00Z"
}
```

---

## Scanning Endpoints

### GET /scan - Latest Scan Results

Returns the most recent stock scan results with story scores.

**Authentication:** Required

**Request:**
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
     https://your-api-url/scan
```

**Response:**
```json
{
  "ok": true,
  "scan_time": "2026-02-01T12:00:00Z",
  "total_scanned": 500,
  "results": [
    {
      "ticker": "NVDA",
      "story_score": 87.5,
      "story_strength": "STRONG_STORY",
      "price": 875.30,
      "change_pct": 2.4,
      "hottest_theme": "AI Infrastructure",
      "theme_role": "leader",
      "next_catalyst": "Earnings in 5 days",
      "social_buzz": 85,
      "sentiment": "very_bullish",
      "technical": {
        "trend": "uptrend",
        "rs_rank": 95,
        "volume_ratio": 1.8
      }
    }
  ],
  "metadata": {
    "scan_duration": 45.2,
    "filters_applied": ["min_market_cap", "min_volume", "story_score"],
    "top_themes": ["AI Infrastructure", "Cloud Computing", "Cybersecurity"]
  }
}
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `min_score` | float | 0 | Minimum story score (0-100) |
| `limit` | int | 100 | Maximum results to return |
| `theme` | string | - | Filter by theme name |

**Example with filters:**
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
     "https://your-api-url/scan?min_score=70&limit=20&theme=AI"
```

---

### POST /scan/trigger - Manual Scan Trigger

Trigger a manual stock scan.

**Authentication:** Required

**Status:** Currently disabled (Modal limitation)

**Response:**
```json
{
  "ok": false,
  "error": "Manual trigger disabled",
  "message": "Use: modal run modal_scanner.py --daily",
  "reason": "Modal SDK doesn't allow cross-app function calls"
}
```

---

## API Key Management

### POST /api-keys/generate - Generate API Key

Generate a new API key for a user.

**Authentication:** Not required (during grace period)

**Request:**
```bash
curl -X POST "https://your-api-url/api-keys/generate?user_id=john_doe&tier=free&email=john@example.com"
```

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user_id` | string | Yes | Unique user identifier |
| `tier` | string | No | API tier: free, pro, enterprise (default: free) |
| `email` | string | No | Contact email |

**Response:**
```json
{
  "ok": true,
  "api_key": "ssk_live_a1b2c3d4e5f6...",
  "tier": "free",
  "requests_per_day": 1000,
  "created_at": "2026-02-01T12:00:00Z",
  "usage": "Include in request headers as: Authorization: Bearer <api_key>"
}
```

**Important:** Store the API key securely. It will only be shown once.

---

### GET /api-keys/usage - View Usage Statistics

Get usage statistics for your API key.

**Authentication:** Required

**Request:**
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
     https://your-api-url/api-keys/usage
```

**Response:**
```json
{
  "ok": true,
  "usage": {
    "tier": "free",
    "requests_per_day": 1000,
    "daily_requests": 234,
    "requests_remaining": 766,
    "total_requests": 5432,
    "last_used": "2026-02-01T11:45:00Z",
    "is_active": true
  },
  "timestamp": "2026-02-01T12:00:00Z"
}
```

---

### POST /api-keys/revoke - Revoke API Key

Revoke an API key (makes it unusable).

**Authentication:** Not required

**Request:**
```bash
curl -X POST "https://your-api-url/api-keys/revoke?api_key=ssk_live_..."
```

**Response:**
```json
{
  "ok": true,
  "message": "API key revoked successfully",
  "api_key": "ssk_live_a1b2c3..."
}
```

---

### GET /api-keys/request - Request Instructions

Get instructions for requesting an API key.

**Authentication:** Not required

**Request:**
```bash
curl https://your-api-url/api-keys/request
```

**Response:**
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

---

## Admin Endpoints

### GET /admin/dashboard - Admin Dashboard

View the interactive admin dashboard with real-time metrics.

**Authentication:** Not required (consider adding later)

**Browser Access:**
```
https://your-api-url/admin/dashboard
```

**Features:**
- System status and uptime
- Request/error statistics
- Latency percentiles
- Status code distribution
- Top endpoints by traffic
- Recent error log
- Function performance stats
- Auto-refresh every 30 seconds

---

### GET /admin/metrics - API Metrics

Get detailed API metrics and statistics.

**Authentication:** Not required (consider adding later)

**Request:**
```bash
curl https://your-api-url/admin/metrics
```

**Response:**
```json
{
  "ok": true,
  "timestamp": "2026-02-01T12:00:00Z",
  "metrics": {
    "uptime_seconds": 86400,
    "total_requests": 15432,
    "total_errors": 234,
    "error_rate": 1.52,
    "status_codes": {
      "200": 14850,
      "400": 123,
      "401": 89,
      "429": 22,
      "500": 11
    },
    "top_endpoints": {
      "/scan": 8234,
      "/health": 2156,
      "/api-keys/usage": 1432
    },
    "error_endpoints": {
      "/scan": 5,
      "/api-keys/generate": 3
    },
    "latency_p50": 245.3,
    "latency_p95": 892.7,
    "latency_p99": 1523.1,
    "recent_errors": [
      {
        "path": "/scan",
        "error": "Timeout connecting to Polygon API",
        "timestamp": "2026-02-01T11:58:23Z"
      }
    ]
  }
}
```

---

### GET /admin/performance - Performance Stats

Get detailed performance statistics for all monitored functions.

**Authentication:** Not required (consider adding later)

**Request:**
```bash
curl https://your-api-url/admin/performance
```

**Response:**
```json
{
  "ok": true,
  "timestamp": "2026-02-01T12:00:00Z",
  "performance": {
    "calculate_story_score": {
      "count": 8234,
      "total_calls": 8234,
      "avg": 1.234,
      "min": 0.521,
      "max": 3.456,
      "p50": 1.123,
      "p95": 2.345,
      "p99": 2.987
    },
    "get_social_buzz_score": {
      "count": 8234,
      "total_calls": 8234,
      "avg": 0.987,
      "min": 0.234,
      "max": 2.145,
      "p50": 0.923,
      "p95": 1.567,
      "p99": 1.892
    }
  }
}
```

---

## Response Format

### Success Response

All successful responses include:

```json
{
  "ok": true,
  "data": { /* endpoint-specific data */ },
  "timestamp": "2026-02-01T12:00:00Z"
}
```

### Error Response

All error responses include:

```json
{
  "ok": false,
  "error": "Error category",
  "message": "Human-readable error message",
  "details": { /* optional additional context */ }
}
```

---

## Error Handling

### HTTP Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 200 | OK | Request successful |
| 400 | Bad Request | Invalid parameters |
| 401 | Unauthorized | Missing or invalid API key |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server error |
| 501 | Not Implemented | Feature not yet available |

### Common Errors

#### Missing API Key
```json
{
  "ok": false,
  "error": "Missing API key",
  "message": "Include 'Authorization: Bearer <your-api-key>' header",
  "get_key": "/api-keys/request"
}
```

#### Invalid API Key
```json
{
  "ok": false,
  "error": "Authentication failed",
  "message": "Invalid API key"
}
```

#### Daily Limit Exceeded
```json
{
  "ok": false,
  "error": "Authentication failed",
  "message": "Daily rate limit exceeded (1000 requests/day)"
}
```

#### Rate Limit Exceeded
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

---

## Code Examples

### Python

```python
import requests

API_KEY = "ssk_live_your_key_here"
BASE_URL = "https://your-api-url.modal.run"

headers = {
    "Authorization": f"Bearer {API_KEY}"
}

# Get scan results
response = requests.get(f"{BASE_URL}/scan", headers=headers)
data = response.json()

if data["ok"]:
    print(f"Found {len(data['results'])} stocks")
    for stock in data["results"][:5]:
        print(f"{stock['ticker']}: {stock['story_score']}")
else:
    print(f"Error: {data['message']}")

# Check usage
usage = requests.get(f"{BASE_URL}/api-keys/usage", headers=headers)
print(f"Requests remaining: {usage.json()['usage']['requests_remaining']}")
```

### JavaScript

```javascript
const API_KEY = "ssk_live_your_key_here";
const BASE_URL = "https://your-api-url.modal.run";

// Get scan results
async function getScanResults() {
  const response = await fetch(`${BASE_URL}/scan`, {
    headers: {
      'Authorization': `Bearer ${API_KEY}`
    }
  });

  const data = await response.json();

  if (data.ok) {
    console.log(`Found ${data.results.length} stocks`);
    data.results.slice(0, 5).forEach(stock => {
      console.log(`${stock.ticker}: ${stock.story_score}`);
    });
  } else {
    console.error(`Error: ${data.message}`);
  }

  // Check rate limits
  const remaining = response.headers.get('X-RateLimit-Remaining');
  console.log(`Rate limit remaining: ${remaining}`);
}

getScanResults();
```

### cURL

```bash
#!/bin/bash

API_KEY="ssk_live_your_key_here"
BASE_URL="https://your-api-url.modal.run"

# Get scan results
curl -H "Authorization: Bearer $API_KEY" \
     "$BASE_URL/scan" | jq '.results[0:5][] | {ticker, story_score}'

# Check usage
curl -H "Authorization: Bearer $API_KEY" \
     "$BASE_URL/api-keys/usage" | jq '.usage'

# Get top stocks with high scores
curl -H "Authorization: Bearer $API_KEY" \
     "$BASE_URL/scan?min_score=80&limit=10" | jq '.results[] | .ticker'
```

### Rate Limit Handling

```python
import time
import requests

def fetch_with_retry(url, headers, max_retries=3):
    """Fetch with automatic retry on rate limit"""
    for attempt in range(max_retries):
        response = requests.get(url, headers=headers)

        if response.status_code == 429:
            # Rate limited - wait and retry
            data = response.json()
            retry_after = data.get('rate_limit', {}).get('retry_after', 1)
            print(f"Rate limited. Waiting {retry_after}s...")
            time.sleep(retry_after)
            continue

        return response

    raise Exception("Max retries exceeded")
```

---

## Best Practices

### 1. Security

- **Never commit API keys** to version control
- **Use environment variables** for keys
- **Rotate keys** every 90 days
- **Revoke compromised keys** immediately

### 2. Performance

- **Cache responses** when appropriate
- **Batch requests** instead of many small ones
- **Monitor rate limits** to avoid throttling
- **Use compression** (responses are gzipped)

### 3. Error Handling

- **Check `ok` field** in all responses
- **Handle rate limits** with exponential backoff
- **Log errors** for debugging
- **Provide fallbacks** for non-critical data

### 4. Testing

- **Use free tier** for development
- **Test error scenarios** (invalid keys, rate limits)
- **Validate response schemas** in tests
- **Monitor latency** in production

---

## Support & Resources

### Documentation
- **Interactive API Docs:** `/docs` (Swagger UI)
- **Alternative Docs:** `/redoc` (ReDoc)
- **Admin Dashboard:** `/admin/dashboard`
- **Migration Guides:** `API_AUTH_MIGRATION_GUIDE.md`

### Support Channels
- **Email:** support@example.com
- **GitHub Issues:** https://github.com/yourusername/stock_scanner_bot/issues
- **Documentation:** https://github.com/yourusername/stock_scanner_bot

### Rate Limit Increase
Contact support@example.com to upgrade to Pro or Enterprise tier.

---

**Last Updated:** February 1, 2026
**API Version:** 2.0.0
**Status:** Production Ready
