# Guide: Enabling API Authentication Enforcement

**Purpose:** Safely transition from grace period to mandatory API authentication
**Estimated Time:** 30 minutes
**Risk Level:** Medium (with proper preparation, becomes low)

---

## Pre-Enforcement Checklist

Before setting `REQUIRE_API_KEYS=true`, verify:

### 1. Adoption Metrics (Target: 80%+)

```bash
python scripts/monitor_auth_adoption.py
```

**Required thresholds:**
- ✅ Adoption rate ≥ 80%
- ✅ Unauthorized requests < 100 in last 24h
- ✅ Error rate stable (< 5%)

**If not met:** Extend grace period by 3-7 days

### 2. User Communication

- ✅ Initial announcement sent (7 days ago)
- ✅ Reminder sent (3 days ago)
- ✅ Final notice sent (24 hours ago)
- ✅ Support channels monitored

### 3. System Health

Check dashboard: `/admin/dashboard`

- ✅ System uptime > 99%
- ✅ No active incidents
- ✅ Error rate < 3%
- ✅ API response times normal

### 4. Rollback Plan Ready

- ✅ Current env vars backed up
- ✅ Rollback command prepared
- ✅ Team available for 2 hours post-enforcement
- ✅ Communication templates prepared

---

## Enforcement Methods

### Option 1: Environment Variable (Recommended)

**Step 1: Set Environment Variable**

On Modal:
```bash
modal secret set REQUIRE_API_KEYS=true
```

**Step 2: Verify**
```bash
modal secret list | grep REQUIRE_API_KEYS
```

**Step 3: Redeploy**
```bash
modal deploy modal_api_v2.py
```

**Advantages:**
- ✅ Easy to toggle
- ✅ No code changes
- ✅ Fast rollback
- ✅ Environment-specific control

---

### Option 2: Code Change (Alternative)

**Step 1: Update modal_api_v2.py**

Find this line (~line 240):
```python
REQUIRE_API_KEYS = os.environ.get('REQUIRE_API_KEYS', 'false').lower() == 'true'
```

Change to:
```python
REQUIRE_API_KEYS = os.environ.get('REQUIRE_API_KEYS', 'true').lower() == 'true'
```

**Step 2: Commit and Deploy**
```bash
git add modal_api_v2.py
git commit -m "Enable API authentication enforcement"
git push
modal deploy modal_api_v2.py
```

**Advantages:**
- ✅ Default enforcement
- ✅ Explicit in code

**Disadvantages:**
- ❌ Requires code change to rollback
- ❌ Slower to revert

**Recommendation:** Use Option 1 (environment variable) for easier rollback.

---

## Step-by-Step Enforcement

### Phase 1: Final Preparation (1 hour before)

**1. Run Final Adoption Check**
```bash
python scripts/monitor_auth_adoption.py
```

**2. Verify Target Met**
- Adoption rate ≥ 80%
- Unauthorized requests < 100

**3. Send Final Warning**

Email subject: "API Authentication Required in 1 Hour"

```
Stock Scanner API users,

This is your final reminder: API authentication will be required
starting at [TIME].

If you haven't already:
1. Get your free API key: [URL]
2. Update your code: [GUIDE]

Need help? Reply to this email immediately.

- Stock Scanner Team
```

**4. Prepare Team**
- Support team on standby
- Dev team available for rollback
- Communication channels open

---

### Phase 2: Enable Enforcement (15 minutes)

**1. Enable Auth (Choose method)**

**Modal Environment Variable:**
```bash
modal secret set REQUIRE_API_KEYS=true
modal deploy modal_api_v2.py
```

**2. Verify Deployment**
```bash
modal app logs stock-scanner-api-v2 --tail 50
```

Look for: `REQUIRE_API_KEYS=true` in logs

**3. Test Enforcement**

**Test 1: Request without API key (should fail)**
```bash
curl -i https://your-api-url.modal.run/scan
```

Expected response:
```
HTTP/1.1 401 Unauthorized
{
  "ok": false,
  "error": "Missing API key",
  "message": "Include 'Authorization: Bearer <your-api-key>' header",
  "get_key": "/api-keys/request"
}
```

**Test 2: Request with valid API key (should succeed)**
```bash
curl -i -H "Authorization: Bearer YOUR_TEST_KEY" \
     https://your-api-url.modal.run/scan
```

Expected response:
```
HTTP/1.1 200 OK
{
  "ok": true,
  "scan_time": "...",
  "results": [...]
}
```

**4. Announce Enforcement**

Twitter/Social:
```
🔒 API authentication is now required for Stock Scanner API.

Get your free API key: [URL]
Questions? support@example.com

#APIUpdate #StockMarket
```

Email:
```
Subject: API Authentication Now Active

API authentication is now required as announced.

✅ Have your API key? You're all set!
❌ Don't have one? Get it now: [URL]

Support: support@example.com
```

---

### Phase 3: Monitor (First 2 hours)

**1. Continuous Monitoring**
```bash
python scripts/monitor_auth_adoption.py --continuous
```

**2. Watch Key Metrics**

Check `/admin/dashboard` every 15 minutes:

| Metric | Target | Action If Exceeded |
|--------|--------|-------------------|
| **401 Error Rate** | < 10% | Investigate users |
| **Total Error Rate** | < 5% | Check system health |
| **Response Time** | < 1s p95 | Check for overload |
| **Support Tickets** | < 20/hour | Add support staff |

**3. Track Support Issues**

Common issues:
- "My API key doesn't work" → Check key validity
- "I didn't get the announcement" → Generate key immediately
- "How do I add the header?" → Send code examples
- "Can I get an extension?" → Case-by-case basis

**4. Identify Problem Users**

Check recent errors:
```bash
curl https://your-api-url.modal.run/admin/metrics | jq '.metrics.recent_errors'
```

For high-volume users without keys:
- Contact directly
- Offer immediate assistance
- Generate key for them if needed

---

### Phase 4: Stabilization (First 24 hours)

**1. Daily Check-ins**

| Time | Action |
|------|--------|
| **Hour 2** | Full metrics review, adjust if needed |
| **Hour 4** | Check support ticket volume |
| **Hour 8** | Send success update to team |
| **Hour 24** | Generate 24-hour report |

**2. Success Metrics**

After 24 hours, verify:
- ✅ 401 error rate < 5%
- ✅ Total error rate < 3%
- ✅ Support ticket volume normal
- ✅ No P0/P1 incidents
- ✅ User sentiment positive

**3. Publish Update**

Email (24h after enforcement):
```
Subject: API Authentication: 24 Hour Update

Thank you for your patience during the transition to API authentication!

Status: ✅ Successful
- XX% of users authenticated
- XX,XXX requests served successfully
- XX support tickets resolved

Need help? support@example.com

Thank you for being part of Stock Scanner!
```

---

## Rollback Plan

If critical issues arise (error rate > 20%, major outages, overwhelming support):

### Emergency Rollback (5 minutes)

**Step 1: Disable Enforcement**
```bash
modal secret set REQUIRE_API_KEYS=false
modal deploy modal_api_v2.py
```

**Step 2: Verify Rollback**
```bash
# Test without API key (should work again)
curl https://your-api-url.modal.run/scan
```

**Step 3: Announce Rollback**

Email subject: "API Authentication Grace Period Extended"

```
Due to technical issues, we've extended the grace period for
API authentication.

You can continue using the API without a key while we resolve
issues and provide additional support.

New deadline: [DATE + 7 days]

We apologize for any inconvenience.
```

**Step 4: Post-Mortem**
- Identify root cause
- Fix issues
- Communicate improvements
- Plan new enforcement date

---

## Troubleshooting

### Issue: High 401 Error Rate (>20%)

**Diagnosis:**
```bash
curl https://your-api-url.modal.run/admin/metrics | \
  jq '.metrics | {error_rate, status_codes}'
```

**Actions:**
1. Identify top error endpoints
2. Contact affected users directly
3. Offer expedited key generation
4. Consider 24h rollback if >30% error rate

---

### Issue: Performance Degradation

**Diagnosis:**
```bash
curl https://your-api-url.modal.run/admin/performance
```

**Actions:**
1. Check auth middleware overhead
2. Review rate limiter performance
3. Scale Modal instances if needed
4. Optimize hot paths

---

### Issue: Rate Limiter False Positives

**Symptoms:**
- Users report 429 errors despite low usage
- Rate limit errors spike

**Actions:**
1. Check token bucket algorithm parameters
2. Increase per-second limit if needed
3. Adjust refill rate
4. Review for bugs in rate limiting code

---

### Issue: Key Generation Failures

**Symptoms:**
- Users can't generate keys
- `/api-keys/generate` returns errors

**Actions:**
1. Check data volume write permissions
2. Verify `api_keys.json` file accessibility
3. Check Modal volume health
4. Manual key generation if needed:
```python
from src.core.auth import APIKeyManager
manager = APIKeyManager()
key = manager.generate_key(user_id="user@example.com", tier="free")
print(f"Generated key: {key}")
```

---

## Success Criteria

Consider enforcement successful when:

### After 2 Hours
- ✅ 401 error rate < 10%
- ✅ No P0 incidents
- ✅ Support ticket volume manageable

### After 24 Hours
- ✅ 401 error rate < 5%
- ✅ Total error rate < 3%
- ✅ Less than 50 support tickets
- ✅ System performance normal

### After 7 Days
- ✅ 401 error rate < 2%
- ✅ Support tickets back to baseline
- ✅ User sentiment positive
- ✅ Revenue tracking active (if Pro users)

---

## Post-Enforcement Tasks

### Week 1
1. Monitor metrics daily
2. Respond to support tickets promptly
3. Identify and contact high-volume users
4. Generate weekly adoption report

### Week 2-4
5. Analyze usage patterns by tier
6. Identify upgrade candidates (free → pro)
7. Optimize rate limiting based on data
8. Plan Pro tier marketing campaign

### Month 2+
9. Review API key rotation policy
10. Implement key expiration (optional)
11. Add key usage analytics to dashboard
12. Launch Pro tier revenue tracking

---

## Communication Templates

### Email: 24h Before Enforcement

```
Subject: Final Reminder: API Keys Required Tomorrow

This is your final reminder that API authentication will be
required starting tomorrow at [TIME].

⏰ Deadline: [DATE TIME]

Action Required:
1. Get your free API key: [URL]
2. Update your code: [GUIDE]
3. Test your integration

Need help? Reply NOW - we're here to assist!

After the deadline, requests without API keys will be rejected.

Thank you,
Stock Scanner Team
```

---

### Email: Enforcement Active

```
Subject: API Authentication Now Active

API authentication is now active. All requests require an API key.

✅ Have your key? Great! No action needed.
❌ Don't have one? Get it now: [URL]

Need immediate help?
- Email: support@example.com
- We're responding within 1 hour

Thank you for your understanding!
```

---

### Social Media: Enforcement

```
🔒 API authentication is now required

Get your free API key (1,000 requests/day):
👉 [URL]

Questions? support@example.com

#StockScanner #APIUpdate
```

---

## Monitoring Commands Reference

```bash
# Check adoption rate
python scripts/monitor_auth_adoption.py

# Continuous monitoring
python scripts/monitor_auth_adoption.py --continuous

# View live dashboard
open https://your-api-url.modal.run/admin/dashboard

# Get metrics JSON
curl https://your-api-url.modal.run/admin/metrics

# Check recent errors
curl https://your-api-url.modal.run/admin/metrics | \
  jq '.metrics.recent_errors'

# View Modal logs
modal app logs stock-scanner-api-v2 --follow

# Check system health
curl https://your-api-url.modal.run/health
```

---

## Decision Tree

```
Is adoption rate ≥ 80%?
├─ YES: Is unauthorized request count < 100?
│   ├─ YES: ✅ Proceed with enforcement
│   └─ NO: Extend grace period 3-7 days
└─ NO: Extend grace period 3-7 days

After enforcement, is 401 error rate < 10%?
├─ YES: ✅ Continue monitoring
└─ NO: Is error rate > 20%?
    ├─ YES: 🚨 Consider rollback
    └─ NO: Monitor closely, assist users
```

---

## Enforcement Checklist

Copy and use this checklist:

### Pre-Enforcement
- [ ] Adoption rate ≥ 80%
- [ ] Unauthorized requests < 100
- [ ] Final announcement sent (24h before)
- [ ] Team briefed and available
- [ ] Rollback plan reviewed
- [ ] Monitoring tools ready

### Enforcement
- [ ] Environment variable set (`REQUIRE_API_KEYS=true`)
- [ ] Application deployed
- [ ] Enforcement verified (test without key fails)
- [ ] Authenticated requests verified (test with key succeeds)
- [ ] Announcement posted
- [ ] Monitoring started

### Post-Enforcement (First 2 Hours)
- [ ] Monitor dashboard every 15 min
- [ ] 401 error rate < 10%
- [ ] Support tickets triaged
- [ ] Critical issues escalated
- [ ] Team check-in at hour 2

### Post-Enforcement (First 24 Hours)
- [ ] Metrics reviewed hourly
- [ ] Support ticket volume normal
- [ ] 24-hour report generated
- [ ] Success update posted
- [ ] Team debriefed

---

**Document Status:** Ready for execution
**Estimated Total Time:** 30 minutes + 2 hours monitoring
**Recommended Timing:** Tuesday or Wednesday, 10 AM-12 PM (avoid Mondays, Fridays, weekends)

**Good luck with the enforcement! 🚀**
