# Code Review Workflow - Stock Scanner Bot

**Systematic Code Review Process for Every Change**

---

## Overview

This workflow ensures every code change meets quality, security, and performance standards before deployment. Follow this for EVERY commit, no exceptions.

---

## The 5-Phase Review Process

### Phase 1: Pre-Code Review (Planning)
### Phase 2: Code Quality Review
### Phase 3: Security Review
### Phase 4: Testing Review
### Phase 5: Deployment Readiness

---

## Phase 1: Pre-Code Review (Planning)

**Goal:** Ensure the approach is sound before reviewing implementation

### Questions to Answer

1. **Does this change align with requirements?**
   - [ ] Re-read the original user request
   - [ ] Confirm implementation matches intent
   - [ ] Check for scope creep (doing more than asked)

2. **Is the architecture appropriate?**
   - [ ] Does this fit the existing system design?
   - [ ] Are there better approaches?
   - [ ] Will this create technical debt?

3. **What could go wrong?**
   - [ ] List potential failure modes
   - [ ] Consider edge cases
   - [ ] Think about scale (what if 10x data?)

### Output: Architecture Notes

```markdown
## Change: [Brief Description]

### Approach
- What: [What is being changed]
- Why: [Why this approach]
- How: [How it works]

### Alternatives Considered
1. [Alternative 1] - Rejected because [reason]
2. [Alternative 2] - Rejected because [reason]

### Risk Assessment
- Data integrity: Low/Medium/High
- Performance impact: Low/Medium/High
- Security implications: Low/Medium/High
- Breaking changes: Yes/No

### Testing Strategy
- Unit tests: [Describe]
- Integration tests: [Describe]
- Manual testing: [Describe]
```

---

## Phase 2: Code Quality Review

**Goal:** Ensure code is readable, maintainable, and follows best practices

### 2.1 Structure Review

Run this command to see all changes:
```bash
git diff --stat
git diff
```

**Checklist:**

- [ ] **File organization**
  - Files in correct directories
  - Imports organized (stdlib → third-party → local)
  - No circular dependencies

- [ ] **Function design**
  - Each function has single responsibility
  - Functions < 40 lines (break down if longer)
  - No deeply nested logic (max 3 levels)
  - Clear function names (verb + noun)

- [ ] **Variable naming**
  - Descriptive names (not `x`, `data`, `temp`)
  - Constants in UPPER_CASE
  - Private methods prefixed with `_`
  - Boolean variables start with `is_`, `has_`, `should_`

- [ ] **Code duplication**
  - No copy-pasted code blocks
  - Common logic extracted to functions
  - BUT: Don't abstract too early (3 uses = abstract)

### 2.2 Python-Specific Review

```bash
# Run linting
python -m flake8 src/ --max-line-length=100 --ignore=E501,W503

# Check for common issues
grep -r "print(" src/          # No print statements
grep -r "import \*" src/       # No wildcard imports
grep -r "except:" src/         # No bare except clauses
```

**Checklist:**

- [ ] **Type hints** (for public APIs)
  ```python
  def get_stock_price(ticker: str) -> Optional[float]:
      """Get current stock price."""
      pass
  ```

- [ ] **Docstrings** (for public functions)
  ```python
  def validate_ticker(ticker: str) -> str:
      """Validate and normalize ticker symbol.

      Args:
          ticker: Raw ticker input from user

      Returns:
          Normalized ticker (uppercase, trimmed)

      Raises:
          ValueError: If ticker format is invalid
      """
      pass
  ```

- [ ] **Error handling**
  - Specific exception types (not bare `except:`)
  - Logged errors include context
  - Errors don't expose sensitive data

- [ ] **Resource management**
  - Use context managers (`with` statements)
  - Close files, connections, streams
  - Clean up temp files

### 2.3 JavaScript-Specific Review

```bash
# Check for console.log
grep -r "console\\.log" docs/js/

# Check for debugger
grep -r "debugger" docs/js/
```

**Checklist:**

- [ ] **Modern syntax**
  - Use `const`/`let` (not `var`)
  - Arrow functions where appropriate
  - Template literals for strings
  - Destructuring where it improves readability

- [ ] **Async handling**
  - Use `async/await` (not callbacks)
  - Handle promise rejections
  - Use `try/catch` in async functions

- [ ] **DOM manipulation**
  - Cache DOM queries
  - Use event delegation for dynamic content
  - Clean up event listeners

### 2.4 Performance Review

**Checklist:**

- [ ] **Database queries**
  - No N+1 queries (use joins or batch loads)
  - Appropriate indexes on queried fields
  - Limit results (pagination)
  - Use `select_related` / `prefetch_related` (Django)

- [ ] **API calls**
  - Batch requests where possible
  - Cache responses appropriately
  - Set reasonable timeouts
  - Handle rate limits

- [ ] **Algorithms**
  - Time complexity acceptable (O(n²) flag for review)
  - Space complexity reasonable
  - Consider sorting/hashing for lookups

- [ ] **Resource usage**
  - No memory leaks
  - Large files streamed (not loaded into memory)
  - Background tasks don't block requests

---

## Phase 3: Security Review

**Goal:** Prevent security vulnerabilities

### 3.1 Input Validation

Find all user input:
```bash
# Python
grep -r "request\\.json\\|request\\.args\\|request\\.form" src/

# JavaScript
grep -r "request\\.query\\|request\\.body\\|request\\.params" src/
```

**For each input, verify:**

- [ ] **Type validation**
  ```python
  # BAD
  shares = request.json['shares']

  # GOOD
  shares = int(request.json.get('shares', 0))
  if shares <= 0 or shares > 1000000:
      raise ValueError("Invalid shares count")
  ```

- [ ] **Range validation**
  - Numbers within expected range
  - Strings within max length
  - Arrays within max size

- [ ] **Format validation**
  - Email format
  - Phone format
  - Ticker symbol format
  - Date format

- [ ] **Sanitization**
  - HTML escaped before rendering
  - SQL parameters bound (not concatenated)
  - Shell commands avoided or properly escaped

### 3.2 Authentication & Authorization

**Checklist:**

- [ ] **Authentication required?**
  - Public endpoints clearly documented
  - Protected endpoints check auth token
  - Token validation is correct

- [ ] **Authorization checked?**
  - User can only access their data
  - Admin actions require admin role
  - Cross-user access prevented

- [ ] **Session security**
  - Sessions expire appropriately
  - Sensitive actions require re-authentication
  - Logout clears session completely

### 3.3 Data Protection

**Checklist:**

- [ ] **Secrets management**
  ```bash
  # Check for hardcoded secrets
  grep -ri "password\\|secret\\|api_key\\|token" src/ --exclude-dir=tests
  ```
  - No API keys in code
  - No passwords in code
  - Use environment variables
  - Secrets not logged

- [ ] **Sensitive data**
  - PII encrypted at rest
  - Sensitive fields not logged
  - Error messages don't leak data
  - Passwords hashed (never plain text)

### 3.4 OWASP Top 10 Check

- [ ] **SQL Injection**
  - Use parameterized queries
  - No string concatenation in SQL

- [ ] **XSS (Cross-Site Scripting)**
  - Escape user input before rendering
  - Use CSP headers
  - Sanitize HTML

- [ ] **CSRF (Cross-Site Request Forgery)**
  - CSRF tokens on state-changing operations
  - Check referer header
  - SameSite cookie attribute

- [ ] **Insecure Deserialization**
  - Validate data before deserializing
  - Don't use pickle with untrusted data
  - Use JSON schema validation

- [ ] **Using Components with Known Vulnerabilities**
  ```bash
  # Check for outdated dependencies
  pip list --outdated
  npm audit
  ```

---

## Phase 4: Testing Review

**Goal:** Ensure changes are thoroughly tested

### 4.1 Test Coverage Review

```bash
# Run tests with coverage
pytest --cov=src --cov-report=term-missing tests/

# Target: 80%+ coverage for new code
```

**Checklist:**

- [ ] **Unit tests exist**
  - Each function has at least one test
  - Happy path tested
  - Error cases tested
  - Edge cases tested

- [ ] **Test quality**
  - Tests are independent (can run in any order)
  - Tests are deterministic (same result every time)
  - Tests are fast (< 100ms each for unit tests)
  - Test names describe what they test

### 4.2 Test Scenarios

**For each changed function:**

- [ ] **Happy path**
  ```python
  def test_validate_ticker_valid():
      """Test validation with valid ticker."""
      assert validate_ticker("AAPL") == "AAPL"
      assert validate_ticker("  googl  ") == "GOOGL"
  ```

- [ ] **Edge cases**
  ```python
  def test_validate_ticker_edge_cases():
      """Test validation with edge case inputs."""
      assert validate_ticker("A") == "A"       # Min length
      assert validate_ticker("ABCDE") == "ABCDE"  # Max length
  ```

- [ ] **Error cases**
  ```python
  def test_validate_ticker_invalid():
      """Test validation rejects invalid input."""
      with pytest.raises(ValueError):
          validate_ticker("")
      with pytest.raises(ValueError):
          validate_ticker("TOOLONG")
      with pytest.raises(ValueError):
          validate_ticker("@#$%")
  ```

- [ ] **Boundary conditions**
  ```python
  def test_validate_price_boundaries():
      """Test price validation at boundaries."""
      assert validate_price("0.01") == 0.01   # Min
      assert validate_price("999999") == 999999  # Max
      with pytest.raises(ValueError):
          validate_price("0")                  # Below min
      with pytest.raises(ValueError):
          validate_price("1000000")            # Above max
  ```

### 4.3 Integration Testing

**For API changes:**

- [ ] **Endpoint testing**
  ```python
  def test_scan_trigger_endpoint():
      """Test scan trigger returns correct response."""
      response = client.post('/api/scan/trigger?mode=quick')

      assert response.status_code == 202
      assert response.json['status'] == 'started'
      assert 'universe_size' in response.json
  ```

- [ ] **Database integration**
  - Data persists correctly
  - Transactions commit/rollback properly
  - Constraints enforced

- [ ] **External API integration**
  - Mocked in unit tests
  - Real calls in integration tests
  - Error handling tested

### 4.4 Manual Testing Checklist

**Must be completed before deployment:**

1. **Local testing**
   ```bash
   python main.py  # Start server
   # Test in browser
   ```
   - [ ] Changed functionality works
   - [ ] No JavaScript console errors
   - [ ] No Python exceptions in logs
   - [ ] Visual rendering correct (if UI change)

2. **Regression testing**
   - [ ] Related features still work
   - [ ] Critical paths unaffected
   - [ ] Performance not degraded

3. **Cross-browser testing** (if UI changes)
   - [ ] Chrome
   - [ ] Safari
   - [ ] Firefox
   - [ ] Mobile browsers

---

## Phase 5: Deployment Readiness

**Goal:** Ensure change is ready for production

### 5.1 Documentation Review

**Checklist:**

- [ ] **Code documentation**
  - Public functions have docstrings
  - Complex logic has explanatory comments
  - TODOs addressed or ticketed

- [ ] **API documentation**
  - New endpoints documented
  - Request/response examples
  - Error codes documented

- [ ] **User documentation**
  - README updated if user-facing changes
  - CHANGELOG entry added
  - Migration guide if breaking changes

- [ ] **Configuration documentation**
  - New environment variables documented in `.do/app.yaml`
  - Default values specified
  - Required vs optional clearly marked

### 5.2 Deployment Impact

**Checklist:**

- [ ] **Breaking changes?**
  - API contract changes?
  - Database schema changes?
  - Configuration changes?
  - If yes → Migration plan required

- [ ] **Database migrations**
  ```bash
  # Check for new migrations
  python manage.py makemigrations --dry-run

  # If migrations exist:
  # - Review migration file
  # - Test on copy of production data
  # - Plan for rollback
  ```

- [ ] **Dependencies updated?**
  - `requirements.txt` updated
  - `package.json` updated
  - No conflicting versions
  - Security vulnerabilities checked

- [ ] **Environment variables**
  - New vars added to `.do/app.yaml`
  - Secrets configured in Digital Ocean
  - Required vars will be present on deploy

### 5.3 Rollback Plan

**Every deployment needs a rollback plan:**

```markdown
## Rollback Plan

### Quick Rollback (< 2 minutes)
```bash
git revert HEAD
git push origin main
```

### Full Rollback (< 5 minutes)
```bash
git reset --hard <previous-commit-sha>
git push -f origin main
```

### Database Rollback (if migrations)
```bash
python manage.py migrate <app> <previous_migration>
```

### Verification After Rollback
- [ ] Health check returns 200
- [ ] Dashboard loads
- [ ] Critical paths work
```

**Document:**
- [ ] Last known good commit SHA
- [ ] How to verify rollback success
- [ ] Expected downtime

### 5.4 Monitoring Plan

**What to watch after deployment:**

- [ ] **Health metrics**
  - App status (ACTIVE)
  - Health endpoint (200 OK)
  - Error rate (< 1%)
  - Response time (< 2s p95)

- [ ] **Functional metrics**
  - Feature usage
  - Success/failure rates
  - User feedback

- [ ] **Resource metrics**
  - CPU usage
  - Memory usage
  - Database connections
  - API rate limits

**Monitoring duration:**
- First 5 minutes: Active monitoring
- First hour: Check every 15 minutes
- First 24 hours: Check periodically
- After 24 hours: Normal monitoring

---

## Review Completion Checklist

Before marking review as "APPROVED":

### Code Quality
- [ ] Phase 1: Planning reviewed
- [ ] Phase 2: Code quality verified
- [ ] All code quality issues addressed
- [ ] Performance acceptable

### Security
- [ ] Phase 3: Security review complete
- [ ] All inputs validated
- [ ] No security vulnerabilities
- [ ] Secrets properly managed

### Testing
- [ ] Phase 4: Testing complete
- [ ] All tests passing
- [ ] Coverage > 80% for new code
- [ ] Manual testing done

### Deployment
- [ ] Phase 5: Deployment ready
- [ ] Documentation updated
- [ ] Rollback plan documented
- [ ] Monitoring plan in place

### Final Approval
- [ ] All checklists completed
- [ ] No blockers remaining
- [ ] Ready for production

**Sign-off:**
- Reviewer: [Name]
- Date: [YYYY-MM-DD]
- Commit SHA: [abc123]
- Status: APPROVED / CHANGES REQUESTED / BLOCKED

---

## Common Issues and Solutions

### Issue: Tests fail locally but passed before

**Investigation:**
```bash
# Check what changed
git diff main..HEAD --name-only

# Run specific test
pytest tests/test_specific.py -v

# Check for flaky tests
pytest tests/ --count=10
```

**Solutions:**
- Database state not reset between tests
- Time-dependent tests (use freezegun)
- External API dependency (use mocks)
- File system state (clean up in teardown)

### Issue: Code too complex

**Indicators:**
- Functions > 40 lines
- Nested ifs > 3 levels
- Cyclomatic complexity > 10

**Solutions:**
```python
# BAD - Complex nested logic
def process_trade(trade):
    if trade.ticker:
        if trade.shares > 0:
            if trade.price:
                if is_market_open():
                    execute_trade(trade)
                else:
                    queue_trade(trade)
            else:
                raise ValueError("No price")
        else:
            raise ValueError("Invalid shares")
    else:
        raise ValueError("No ticker")

# GOOD - Early returns, extracted validation
def process_trade(trade):
    _validate_trade(trade)

    if is_market_open():
        execute_trade(trade)
    else:
        queue_trade(trade)

def _validate_trade(trade):
    if not trade.ticker:
        raise ValueError("Ticker required")
    if trade.shares <= 0:
        raise ValueError("Shares must be positive")
    if not trade.price:
        raise ValueError("Price required")
```

### Issue: Test coverage low

**Strategies:**
1. Start with critical paths
2. Focus on business logic (not getters/setters)
3. Test error handling
4. Use parametrized tests for multiple cases

```python
@pytest.mark.parametrize("ticker,expected", [
    ("AAPL", "AAPL"),
    ("  googl  ", "GOOGL"),
    ("tsla", "TSLA"),
])
def test_validate_ticker_various_formats(ticker, expected):
    """Test ticker validation with various formats."""
    assert validate_ticker(ticker) == expected
```

---

## Templates

### Code Review Comment Template

```markdown
**Issue:** [Brief description]
**Severity:** Critical / High / Medium / Low
**Location:** `file.py:123`

**Current code:**
```python
[problematic code]
```

**Issue:**
[Explanation of the problem]

**Suggested fix:**
```python
[corrected code]
```

**References:**
- [Link to documentation]
- [Link to similar issue]
```

### Review Summary Template

```markdown
## Code Review Summary

**Commit:** abc123def
**Reviewer:** Claude Sonnet 4.5
**Date:** 2026-01-30
**Status:** ✅ APPROVED / ⚠️ CHANGES REQUESTED / ❌ BLOCKED

### Summary
[Brief overview of changes]

### Strengths
- [What was done well]
- [Good practices followed]

### Issues Found
1. [Critical issue] - BLOCKER
2. [High priority issue] - Must fix before merge
3. [Medium priority issue] - Should fix
4. [Low priority issue] - Nice to have

### Testing
- Unit tests: ✅ Passing
- Integration tests: ✅ Passing
- Manual testing: ✅ Completed
- Coverage: 85% (target: 80%)

### Recommendations
- [Suggestion for improvement]
- [Future enhancement]

### Approval Conditions
- [ ] Fix critical issues
- [ ] Address high priority issues
- [ ] Update documentation
- [ ] Add missing tests

**Overall Assessment:** [Summary paragraph]
```

---

**Last Updated:** 2026-01-30
**Review Frequency:** Use for every commit
**Maintained By:** Claude Sonnet 4.5
