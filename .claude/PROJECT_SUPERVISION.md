# Stock Scanner Bot - Project Supervision Protocol

**Expert-Level Code Engineering Supervision System**

---

## Table of Contents

1. [Pre-Development Checklist](#pre-development-checklist)
2. [Development Standards](#development-standards)
3. [Code Review Workflow](#code-review-workflow)
4. [Testing Protocol](#testing-protocol)
5. [Deployment Checklist](#deployment-checklist)
6. [Incident Response](#incident-response)
7. [Architecture Principles](#architecture-principles)

---

## Pre-Development Checklist

**MANDATORY: Complete BEFORE writing any code**

### Phase 1: Requirements Analysis
- [ ] Understand the user's actual problem (not just stated request)
- [ ] Identify potential edge cases
- [ ] Check for similar existing functionality in codebase
- [ ] Assess impact on existing systems
- [ ] Estimate complexity (Simple / Medium / Complex)

### Phase 2: Planning Decision
- [ ] **Simple task** (< 20 lines, single file) → Proceed directly
- [ ] **Medium task** (20-100 lines, 2-3 files) → Create brief implementation notes
- [ ] **Complex task** (> 100 lines, multiple files, architecture changes) → **MANDATORY: Use Plan Mode**

### Phase 3: Risk Assessment
- [ ] Will this change affect critical paths? (auth, payments, data integrity)
- [ ] Does this touch multiple modules/services?
- [ ] Are there database/API schema changes?
- [ ] Will this impact existing users/data?
- [ ] **If ANY risk flagged → Use Plan Mode**

---

## Development Standards

### Code Quality Rules

#### 1. Security (P0 - CRITICAL)
- [ ] **NO SQL injection vulnerabilities** - Use parameterized queries
- [ ] **NO XSS vulnerabilities** - Escape all user input, sanitize HTML
- [ ] **NO command injection** - Never pass user input to shell commands
- [ ] **Validate ALL user input** - Type, range, format, length
- [ ] **Authentication/Authorization** - Verify user permissions
- [ ] **Secrets management** - Never commit API keys, use environment variables
- [ ] **CSRF protection** - Include tokens for state-changing operations

#### 2. Error Handling (P0 - CRITICAL)
- [ ] **Wrap external API calls** in try-catch with timeout
- [ ] **Database operations** must have error handling
- [ ] **File operations** must check permissions and handle errors
- [ ] **Log errors** with context (don't fail silently)
- [ ] **Graceful degradation** - System continues functioning on partial failures

#### 3. Code Structure (P1 - HIGH)
- [ ] **Functions < 40 lines** - Break down complex logic
- [ ] **Single Responsibility** - Each function does ONE thing
- [ ] **DRY principle** - Don't repeat yourself (but avoid premature abstraction)
- [ ] **Meaningful names** - Variables/functions describe their purpose
- [ ] **Comments for "why"** - Not "what" (code should be self-documenting)

#### 4. Performance (P1 - HIGH)
- [ ] **No N+1 queries** - Use batch operations
- [ ] **Pagination** for large datasets
- [ ] **Caching** for expensive operations
- [ ] **Async operations** for I/O-bound tasks
- [ ] **Resource cleanup** - Close connections, files, streams

#### 5. Testing (P1 - HIGH)
- [ ] **Unit tests** for business logic
- [ ] **Integration tests** for API endpoints
- [ ] **Manual testing** of critical paths
- [ ] **Edge case testing** (null, empty, max values, special characters)

---

## Code Review Workflow

### Self-Review Checklist (Before Committing)

#### Step 1: Code Inspection
```bash
# Run this before every commit
git diff --staged
```

- [ ] Read EVERY line of changed code
- [ ] Check for debugging code (console.log, print, breakpoints)
- [ ] Verify no commented-out code (delete it)
- [ ] Check for TODO/FIXME comments (address or ticket them)
- [ ] Look for hardcoded values (extract to config)

#### Step 2: Security Review
- [ ] Search for user input handling: `grep -r "request\." src/`
- [ ] Check database queries: `grep -r "execute\|query" src/`
- [ ] Find external API calls: `grep -r "requests\|fetch\|curl" src/`
- [ ] Review each for proper validation and error handling

#### Step 3: Impact Analysis
- [ ] List all files changed: `git diff --name-only`
- [ ] For each file, answer:
  - What functionality does this affect?
  - Could this break existing features?
  - Are there dependencies to update?

#### Step 4: Testing Verification
```bash
# Run before commit
pytest tests/                    # Unit tests
python -m flake8 src/           # Linting
python -m mypy src/             # Type checking (if using)
```

- [ ] All tests pass
- [ ] No new linting errors
- [ ] Manual testing completed

#### Step 5: Documentation Check
- [ ] Update README if user-facing changes
- [ ] Update API docs if endpoints changed
- [ ] Add/update docstrings for new functions
- [ ] Update environment variable docs if new vars added

---

## Testing Protocol

### Level 1: Unit Testing (Required for ALL business logic)

```python
# Example: test_scanner.py
def test_validate_ticker():
    """Test ticker validation handles all edge cases."""
    # Valid cases
    assert validate_ticker("AAPL") == "AAPL"
    assert validate_ticker("  tsla  ") == "TSLA"

    # Invalid cases
    with pytest.raises(ValueError):
        validate_ticker("")           # Empty
    with pytest.raises(ValueError):
        validate_ticker("TOOLONG")    # Too long
    with pytest.raises(ValueError):
        validate_ticker("123")        # Numbers only
    with pytest.raises(ValueError):
        validate_ticker("A@PL")       # Special chars
```

**Required Coverage:**
- [ ] Happy path (expected input)
- [ ] Edge cases (empty, null, max/min values)
- [ ] Error cases (invalid input)
- [ ] Boundary conditions

### Level 2: Integration Testing (Required for API changes)

```python
# Example: test_api.py
def test_scan_trigger_endpoint():
    """Test /api/scan/trigger endpoint end-to-end."""
    response = client.post('/api/scan/trigger?mode=quick')

    assert response.status_code == 202
    assert response.json['status'] == 'started'
    assert response.json['universe_size'] > 0

    # Verify scan actually runs (check for results after delay)
    time.sleep(30)
    scan_results = client.get('/api/scan')
    assert scan_results.json['total'] > 0
```

**Test Scenarios:**
- [ ] Endpoint returns correct status codes
- [ ] Response format matches specification
- [ ] Database changes persist correctly
- [ ] External API integration works
- [ ] Error responses are properly formatted

### Level 3: Manual Testing (Required ALWAYS)

**Pre-Deployment Manual Test Checklist:**

1. **Local Testing:**
   ```bash
   # Start local server
   python main.py

   # Test in browser
   open http://localhost:5000
   ```
   - [ ] Dashboard loads without errors
   - [ ] Changed functionality works as expected
   - [ ] No console errors (check browser DevTools)
   - [ ] Test with different browsers if UI changes

2. **Staging Testing** (if available):
   - [ ] Deploy to staging environment
   - [ ] Test with production-like data
   - [ ] Performance testing under load
   - [ ] Test error scenarios

3. **Critical Path Testing:**
   - [ ] User authentication/login
   - [ ] Core scanning functionality
   - [ ] Data persistence (trades, watchlist)
   - [ ] External API integrations
   - [ ] Telegram bot commands

### Level 4: Performance Testing (For complex features)

```python
# Example: test_performance.py
def test_scan_performance():
    """Scan should complete within acceptable time."""
    start_time = time.time()

    result = scanner.run_scan(['AAPL', 'GOOGL', 'MSFT'] * 10)  # 30 stocks

    elapsed = time.time() - start_time
    assert elapsed < 60, f"Scan took {elapsed}s, expected < 60s"
    assert len(result) == 30
```

**Performance Benchmarks:**
- API endpoints: < 2 seconds for simple queries
- Scan 20 stocks: < 60 seconds
- Dashboard load: < 3 seconds
- Database queries: < 500ms

---

## Deployment Checklist

### Pre-Deployment (MANDATORY)

#### 1. Code Verification
- [ ] All tests passing locally
- [ ] Code reviewed (self-review checklist completed)
- [ ] No debugging code (print statements, console.logs)
- [ ] No TODOs in critical code paths
- [ ] All merge conflicts resolved

#### 2. Environment Verification
- [ ] Environment variables documented in `.do/app.yaml`
- [ ] Secrets not committed to git
- [ ] Database migrations ready (if applicable)
- [ ] Dependencies updated in `requirements.txt` or `package.json`

#### 3. Risk Mitigation
- [ ] Backup strategy in place (can rollback?)
- [ ] Identify critical functionality that could break
- [ ] Have rollback plan ready (revert commit SHA noted)
- [ ] Schedule deployment during low-traffic period if high-risk

#### 4. Communication
- [ ] User notified if downtime expected
- [ ] Team aware of deployment
- [ ] Monitoring alerts configured

### Deployment Steps

```bash
# 1. Final local test
pytest tests/
python -m flake8 src/

# 2. Commit with descriptive message
git add <files>
git commit -m "feat: Add XYZ feature

- Detailed change 1
- Detailed change 2
- Fixes issue #123

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"

# 3. Push to trigger auto-deploy
git push origin main

# 4. Monitor deployment
# Modal: modal app logs modal_scanner
# GitHub Pages: Auto-deploys on push
```

### Post-Deployment (MANDATORY)

#### Immediate Verification (< 5 minutes)
- [ ] Modal apps running: `modal app list`
- [ ] Dashboard loads: Visit https://zhuanleee.github.io/stock_scanner_bot/
- [ ] No errors in browser console

#### Functional Verification (< 15 minutes)
- [ ] Test changed functionality in production
- [ ] Check critical paths still work:
  - [ ] Scan trigger
  - [ ] Ticker lookup
  - [ ] Trade operations
  - [ ] Telegram bot responses
- [ ] Monitor error rates in logs

#### Extended Monitoring (24 hours)
- [ ] Check application logs for errors
- [ ] Monitor response times
- [ ] Verify background jobs running
- [ ] Check database performance
- [ ] Review user feedback

### Rollback Procedure (If Issues Detected)

```bash
# Option 1: Revert last commit
git revert HEAD
git push origin main

# Option 2: Force rollback to specific commit
git reset --hard <previous-good-commit-sha>
git push -f origin main

# Option 3: Redeploy Modal apps
modal deploy modal_scanner.py
modal deploy modal_intelligence_jobs.py
```

**Rollback Criteria (Immediate rollback if ANY true):**
- [ ] App completely down (health check failing)
- [ ] Critical functionality broken (auth, payment, data loss)
- [ ] Security vulnerability introduced
- [ ] Performance degradation > 50%
- [ ] Error rate > 5%

---

## Incident Response

### Severity Levels

#### P0 - CRITICAL (Act immediately)
**Examples:** App completely down, data loss, security breach, payment failure

**Response:**
1. **Alert** - Notify user immediately
2. **Assess** - Identify root cause (check logs, deployment history)
3. **Mitigate** - Rollback if recent deployment caused it
4. **Fix** - Apply hotfix with expedited testing
5. **Verify** - Confirm resolution
6. **Post-mortem** - Document incident and prevention measures

#### P1 - HIGH (Act within 1 hour)
**Examples:** Major feature broken, significant performance degradation, API failures

**Response:**
1. **Assess** - Understand impact and scope
2. **Communicate** - Inform affected users
3. **Plan** - Design fix with proper testing
4. **Implement** - Follow standard deployment process
5. **Monitor** - Watch for recurrence

#### P2 - MEDIUM (Act within 24 hours)
**Examples:** Minor feature broken, UI bugs, non-critical errors

**Response:**
1. **Document** - Create issue/ticket
2. **Plan** - Schedule fix in next sprint
3. **Implement** - Standard workflow

#### P3 - LOW (Act within 1 week)
**Examples:** Cosmetic issues, nice-to-have features, optimization

**Response:**
1. **Backlog** - Add to enhancement list
2. **Prioritize** - Include in planning

### Incident Log Template

```markdown
## Incident: [Brief Description]

**Date:** 2026-01-30
**Severity:** P0 / P1 / P2 / P3
**Status:** Investigating / Mitigated / Resolved

### Timeline
- 14:00 - Issue first detected
- 14:05 - Root cause identified
- 14:10 - Mitigation deployed
- 14:15 - Resolution verified

### Root Cause
[Detailed explanation of what caused the issue]

### Impact
- Affected users: X
- Duration: X minutes
- Data loss: Yes/No

### Resolution
[What was done to fix it]

### Prevention
[What will be done to prevent recurrence]
- [ ] Add monitoring
- [ ] Add tests
- [ ] Update documentation
- [ ] Code review process update
```

---

## Architecture Principles

### 1. Fail-Safe Design
**Principle:** System should gracefully degrade, not crash

```python
# BAD - Will crash entire app if API fails
def get_stock_price(ticker):
    response = requests.get(f"https://api.example.com/{ticker}")
    return response.json()['price']

# GOOD - Graceful degradation
def get_stock_price(ticker):
    try:
        response = requests.get(
            f"https://api.example.com/{ticker}",
            timeout=5
        )
        response.raise_for_status()
        return response.json().get('price')
    except requests.exceptions.Timeout:
        logger.error(f"Timeout fetching price for {ticker}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching price for {ticker}: {e}")
        return None
    except (KeyError, ValueError) as e:
        logger.error(f"Invalid response for {ticker}: {e}")
        return None
```

### 2. Idempotency
**Principle:** Same operation repeated = same result (no side effects)

```python
# BAD - Running twice creates duplicate records
def create_trade(ticker, shares):
    trade = Trade(ticker=ticker, shares=shares)
    db.session.add(trade)
    db.session.commit()

# GOOD - Idempotent with unique constraint
def create_trade(ticker, shares, idempotency_key):
    existing = Trade.query.filter_by(idempotency_key=idempotency_key).first()
    if existing:
        return existing

    trade = Trade(ticker=ticker, shares=shares, idempotency_key=idempotency_key)
    db.session.add(trade)
    db.session.commit()
    return trade
```

### 3. Defense in Depth
**Principle:** Multiple layers of validation/security

```python
# Layer 1: Client-side validation (UX)
# JavaScript validates before sending request

# Layer 2: API validation (Security)
@app.route('/api/trade', methods=['POST'])
def create_trade():
    # Validate authentication
    if not is_authenticated():
        return jsonify({'error': 'Unauthorized'}), 401

    # Validate input format
    ticker = request.json.get('ticker', '').strip().upper()
    if not ticker or len(ticker) > 5:
        return jsonify({'error': 'Invalid ticker'}), 400

    # Layer 3: Business logic validation
    if not is_valid_ticker(ticker):
        return jsonify({'error': 'Ticker not found'}), 404

    # Layer 4: Database constraints
    # ticker field has CHECK constraint in schema
```

### 4. Observability
**Principle:** System behavior should be visible and debuggable

```python
# Add structured logging
logger.info("Scan started", extra={
    'mode': mode,
    'universe_size': len(tickers),
    'user_id': user.id,
    'timestamp': datetime.now().isoformat()
})

# Add metrics
metrics.increment('scan.started')
metrics.timing('scan.duration', elapsed_time)
metrics.gauge('scan.stocks_found', len(results))

# Add health checks
@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'database': check_database_connection(),
        'redis': check_redis_connection(),
        'external_apis': check_external_apis(),
        'version': get_version(),
        'uptime': get_uptime()
    })
```

### 5. Configuration over Code
**Principle:** Behavior controlled by config, not code changes

```python
# BAD - Requires code change to adjust
def scan_stocks():
    max_concurrent = 25  # Hardcoded
    timeout = 30

# GOOD - Controlled by environment
def scan_stocks():
    max_concurrent = int(os.getenv('MAX_CONCURRENT_SCANS', '25'))
    timeout = int(os.getenv('SCAN_TIMEOUT', '30'))
```

---

## Quick Reference

### Before ANY Code Change
1. ✅ Understand the requirement
2. ✅ Check if complex → Use Plan Mode
3. ✅ Assess security risks
4. ✅ Read existing code first

### Before Committing
1. ✅ Run tests
2. ✅ Self-review checklist
3. ✅ Security review
4. ✅ Manual testing

### Before Deploying
1. ✅ Pre-deployment checklist
2. ✅ Rollback plan ready
3. ✅ Monitor after deploy
4. ✅ Verify in production

### If Something Breaks
1. ✅ Assess severity (P0-P3)
2. ✅ Rollback if P0
3. ✅ Document incident
4. ✅ Fix with proper testing
5. ✅ Add prevention measures

---

**Last Updated:** 2026-01-30
**Maintained By:** Claude Sonnet 4.5
**Review Frequency:** Quarterly or after major incidents
