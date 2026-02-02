# 🗑️ DEAD CODE ANALYSIS & CLEANUP REPORT
**Stock Scanner Bot - Unused Components Forensic Analysis**

**Date:** February 1, 2026
**Analysis Type:** Dead Code Detection & Removal Recommendations
**Scope:** Backend, Frontend, Configurations, Documentation
**Estimated Dead Code:** ~2,500+ lines

---

## 📊 EXECUTIVE SUMMARY

### Findings Overview

| Category | Count | Lines | Severity | Action |
|----------|-------|-------|----------|--------|
| **Duplicate Modal APIs** | 3 files | ~1,540 | 🔴 CRITICAL | DELETE |
| **Broken API File** | 1 file | 610 | 🔴 CRITICAL | DELETE |
| **Stub Endpoints** | 12 endpoints | ~150 | 🟡 MEDIUM | DOCUMENT |
| **Deprecated Functions** | 6 scrapers | ~250 | 🟠 HIGH | REMOVE |
| **Duplicate Utilities** | 7 functions | ~70 | 🟠 HIGH | CONSOLIDATE |
| **Disabled Features** | 1 feature | ~30 | 🟡 MEDIUM | FIX OR REMOVE |
| **Archived Files** | 23 files | - | 🟢 LOW | DELETE |
| **Build Artifacts** | Multiple | - | 🟢 LOW | DELETE |

**Total Cleanup Potential:** ~2,500 lines + 27 unused files

---

## 🔴 CRITICAL ISSUES (Immediate Action Required)

### 1. Duplicate Modal API Implementations

**Problem:** Four separate modal API files with 60-80% overlap

#### Files to DELETE:

##### A. `modal_api.py` (321 lines)
- **Status:** SUPERSEDED by v2
- **Reason:** Basic implementation with only 5 endpoints
- **Last Modified:** 2026-01-31
- **Used By:** Nothing (GitHub Actions uses v2)
- **Action:** ✅ SAFE TO DELETE

##### B. `modal_api_full.py` (851 lines)
- **Status:** REDUNDANT - Most complete but UNUSED
- **Reason:** Duplicates all v2 endpoints with identical implementations
- **Issues Found:**
  - Line 518: `# TODO: Implement if needed`
  - Line 649: `# TODO: Implement correlation analysis`
- **Used By:** Nothing (GitHub Actions uses v2)
- **Action:** ✅ SAFE TO DELETE

##### C. `modal_api_consolidated.py` (610 lines)
- **Status:** ⚠️ BROKEN - FATAL ERROR
- **Critical Bug:** Decorators use `@web_app.get()` (lines 68-590) but `web_app` is created later (line 610)
- **Error Type:** `NameError: name 'web_app' is not defined`
- **Would crash if deployed:** YES
- **Used By:** Nothing
- **Action:** ✅ SAFE TO DELETE

#### File to KEEP:

##### D. `modal_api_v2.py` (599 lines) ✅
- **Status:** ACTIVE - Currently deployed
- **Deployed By:** `.github/workflows/deploy_modal.yml` line 42
- **Last Deployed:** 2026-01-31 16:35:59Z (SUCCESS)
- **Endpoints:** 44 routes (6 new options routes just added)
- **Action:** ✅ KEEP (current production version)

**Cleanup Command:**
```bash
rm modal_api.py modal_api_full.py modal_api_consolidated.py
```

**Impact:** Removes 1,782 lines of duplicate/broken code

---

### 2. Broken SocketIO Integration

**File:** `src/api/app.py`
**Lines:** 58-70

**Issue:**
```python
# Line 58-70: SocketIO initialization DISABLED
# CRITICAL: SocketIO code is causing 504 timeouts
# socketio = SocketIO(app, ...)  # COMMENTED OUT
# TODO: Re-enable with proper async/non-blocking init
```

**Status:** Intentionally disabled due to performance issues
**Impact:** No real-time sync functionality
**Options:**
1. ✅ **Remove completely** if not needed
2. ⚠️ **Fix async/non-blocking issues** if needed

**Recommendation:** DELETE if real-time sync not critical (API polling works fine)

---

## 🟠 HIGH PRIORITY ISSUES

### 3. Deprecated Web Scrapers

**File:** `src/analysis/news_analyzer.py`
**Lines:** 228-470 (242 lines)

**Explicitly deprecated but still defined:**

| Function | Lines | Status | Still Called? |
|----------|-------|--------|---------------|
| `scrape_finviz_news()` | 228-255 | Deprecated | ✅ Yes (line 162) |
| `scrape_yahoo_news()` | 256-282 | Deprecated | ✅ Yes (line 616) |
| `scrape_google_news()` | 283-314 | Deprecated | ❌ No |
| `scrape_marketwatch_news()` | 315-349 | Deprecated | ❌ No |
| `scrape_stocktwits()` | 350-413 | Deprecated | ✅ Yes (line 694) |
| `scrape_reddit_sentiment()` | 414-470 | Deprecated | ✅ Yes (line 704) |

**Header Comment (lines 5-7):**
```python
# Web scrapers (Finviz, Google News, MarketWatch) have been deprecated
# in favor of Finnhub and Tiingo for reliability
```

**Problem:** Functions marked deprecated but still actively used

**Options:**
1. ✅ **Keep** if they still work and provide value
2. ⚠️ **Replace** with Finnhub/Tiingo equivalents
3. ❌ **Remove unused** (google_news, marketwatch)

**Recommendation:**
```bash
# Delete unused scrapers
- Remove scrape_google_news() (lines 283-314)
- Remove scrape_marketwatch_news() (lines 315-349)

# Add deprecation warnings to used ones
- Add warnings.warn() to remaining scrapers
- Plan migration to Finnhub/Tiingo
```

---

### 4. Duplicate Utility Functions

**Function:** `ensure_data_dir()`
**Defined in 7 different files:**

1. `src/intelligence/google_trends.py:37`
2. `src/intelligence/theme_discovery.py:41`
3. `src/intelligence/rotation_predictor.py:43`
4. `src/intelligence/institutional_flow.py:46`
5. `src/intelligence/x_intelligence.py:40`
6. `src/intelligence/executive_commentary.py:30`
7. `src/intelligence/theme_intelligence.py:185`

**Code Duplication:** ~70 lines total

**Solution:**
```python
# 1. Create shared utility
# File: src/utils/file_utils.py
def ensure_data_dir(subdir=None):
    """Ensure data directory exists."""
    base_dir = os.path.join(os.getcwd(), "data")
    if subdir:
        base_dir = os.path.join(base_dir, subdir)
    os.makedirs(base_dir, exist_ok=True)
    return base_dir

# 2. Update all 7 files to import
from src.utils.file_utils import ensure_data_dir
```

**Impact:** Removes ~60 lines of duplicate code, single source of truth

---

## 🟡 MEDIUM PRIORITY ISSUES

### 5. Stub/Unimplemented Endpoints

**File:** `modal_api_v2.py`
**Lines:** 521-566

**12 Trading Endpoints Return Empty Data:**

| Endpoint | Line | Returns | Status |
|----------|------|---------|--------|
| `/trades/positions` | 524 | `{"ok": True, "data": []}` | STUB |
| `/trades/watchlist` | 528 | `{"ok": True, "data": []}` | STUB |
| `/trades/activity` | 532 | `{"ok": True, "data": []}` | STUB |
| `/trades/risk` | 536 | `{"risk_level": "low", "exposure": 0}` | STUB |
| `/trades/journal` | 540 | `{"ok": True, "data": []}` | STUB |
| `/trades/daily-report` | 544 | `{"message": "No trades today"}` | STUB |
| `/trades/scan` | 548 | `{"ok": True, "data": []}` | STUB |
| `/trades/create` | 552 | `{"error": "Trading not enabled"}` | DISABLED |
| `/trades/{id}` | 556 | `{"error": "Trade not found"}` | STUB |
| `/trades/{id}/sell` | 560 | `{"error": "Trading not enabled"}` | DISABLED |
| `/sec/deals/add` | 564 | `{"error": "Not implemented"}` | STUB |
| `/evolution/correlations` | 507 | `{"message": "Not yet implemented"}` | STUB |

**Comment at Line 521:**
```python
# =============================================================================
# ROUTES - TRADES (STUBS)
# =============================================================================
```

**Assessment:** Intentionally disabled/unimplemented

**Options:**
1. ✅ **Keep as stubs** (reserve endpoints for future implementation)
2. ⚠️ **Document clearly** in API docs that these are not functional
3. ❌ **Remove** if never planning to implement

**Recommendation:** Keep stubs but add comment in code and API docs

---

### 6. TODO/FIXME Comments

**Total Found:** 17 comments

**Critical TODOs:**

| File | Line | Comment | Priority |
|------|------|---------|----------|
| `modal_api_full.py` | 518 | `# TODO: Implement if needed` | 🔴 File should be deleted anyway |
| `modal_api_full.py` | 649 | `# TODO: Implement correlation analysis` | 🔴 File should be deleted anyway |
| `src/api/app.py` | 60 | `# TODO: Re-enable with proper async/non-blocking` | 🟠 SocketIO disabled |
| `src/analysis/sector_rotation.py` | 48 | `'HACK': 'Cybersecurity'` | 🟡 Hardcoded test data |

**Action:** Most TODOs are in files scheduled for deletion. Remaining ones are documentation.

---

## 🟢 LOW PRIORITY ISSUES

### 7. Archived Files

#### A. GitHub Workflows Archive

**Location:** `.github/workflows-archive/`
**Files:** 5 workflow files

```
bot_listener.yml
daily_scan.yml
refresh_universe.yml
dashboard.yml
story_alerts.yml
```

**Status:** Obsolete, replaced by active workflows in `.github/workflows/`
**Action:** ✅ SAFE TO DELETE

#### B. Documentation Archive

**Location:** `docs/archive/`
**Files:** 18 markdown files

```
BEFORE_AFTER_COMPARISON.md
BUGS_FIXED_2026-01-29.md
EVOLUTIONARY_SYSTEM_IMPLEMENTATION.md
RAILWAY_DEPLOYMENT_GUIDE.md
... 14 more
```

**Status:** Historical documentation
**Action:**
- ✅ DELETE if not needed for reference
- ⚠️ KEEP if historical record is valuable

#### C. Cache Directory

**Location:** `data/cache_old/`
**Status:** Old cache directory
**Action:** ✅ SAFE TO DELETE

---

### 8. Build Artifacts

**__pycache__ directories:**
```
config/__pycache__/
tests/unit/__pycache__/
tests/integration/__pycache__/
src/**/__pycache__/
```

**Action:**
```bash
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -name "*.pyc" -delete
```

---

## 📋 CLEANUP CHECKLIST

### Immediate Actions (Critical)

- [ ] **DELETE** `modal_api.py` (superseded)
- [ ] **DELETE** `modal_api_full.py` (redundant)
- [ ] **DELETE** `modal_api_consolidated.py` (broken)
- [ ] **VERIFY** no imports reference deleted files
- [ ] **TEST** that modal_api_v2.py still deploys

### High Priority

- [ ] **CREATE** `src/utils/file_utils.py` with shared `ensure_data_dir()`
- [ ] **UPDATE** 7 files to import shared function
- [ ] **DELETE** unused scrapers: `scrape_google_news()`, `scrape_marketwatch_news()`
- [ ] **ADD** deprecation warnings to remaining scrapers
- [ ] **DECIDE** on SocketIO: fix or remove completely

### Medium Priority

- [ ] **DOCUMENT** 12 stub endpoints in API documentation
- [ ] **RESOLVE** remaining TODO comments
- [ ] **ADD** feature flags for stub endpoints

### Low Priority

- [ ] **DELETE** `.github/workflows-archive/` directory
- [ ] **REVIEW** `docs/archive/` - delete or keep for history
- [ ] **DELETE** `data/cache_old/` directory
- [ ] **CLEAN** all `__pycache__` directories
- [ ] **ADD** `.gitignore` entries for `__pycache__` and `*.pyc`

---

## 🎯 ESTIMATED CLEANUP IMPACT

### Code Reduction

| Action | Files | Lines | Impact |
|--------|-------|-------|--------|
| Delete 3 modal APIs | 3 | 1,782 | Major |
| Remove deprecated scrapers | 0 | 128 | Medium |
| Consolidate ensure_data_dir | 7 | 60 | Small |
| Remove SocketIO if not needed | 1 | 30 | Small |
| **TOTAL** | **11** | **~2,000** | **Major** |

### File Reduction

| Action | Count |
|--------|-------|
| Delete duplicate modal APIs | 3 files |
| Delete archived workflows | 5 files |
| Delete documentation archive | 18 files (optional) |
| Delete cache_old | 1 directory |
| **TOTAL** | **27+ files** |

---

## 🚀 CLEANUP SCRIPT

### Safe Cleanup Commands

```bash
#!/bin/bash
# Stock Scanner Bot - Dead Code Cleanup Script
# Run from project root

echo "🗑️  Starting cleanup..."

# 1. DELETE duplicate Modal APIs
echo "Removing duplicate modal APIs..."
rm -f modal_api.py modal_api_full.py modal_api_consolidated.py
echo "✅ Removed 3 duplicate modal API files"

# 2. DELETE archived workflows
echo "Removing archived workflows..."
rm -rf .github/workflows-archive/
echo "✅ Removed archived workflows directory"

# 3. DELETE old cache
echo "Removing old cache..."
rm -rf data/cache_old/
echo "✅ Removed old cache directory"

# 4. CLEAN build artifacts
echo "Cleaning build artifacts..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -name "*.pyc" -delete
echo "✅ Cleaned __pycache__ directories and .pyc files"

# 5. OPTIONAL: Delete documentation archive
# Uncomment if you want to delete historical docs
# echo "Removing documentation archive..."
# rm -rf docs/archive/
# echo "✅ Removed documentation archive"

echo ""
echo "🎉 Cleanup complete!"
echo ""
echo "Summary:"
echo "  - Removed 3 duplicate modal API files (1,782 lines)"
echo "  - Removed archived workflows directory"
echo "  - Removed old cache directory"
echo "  - Cleaned build artifacts"
echo ""
echo "⚠️  NEXT STEPS:"
echo "  1. Test modal deployment: modal deploy modal_api_v2.py"
echo "  2. Verify GitHub Actions still work"
echo "  3. Commit changes with: git add -A && git commit -m 'Clean up dead code'"
```

---

## ⚠️ SAFETY NOTES

### Before Deleting:

1. **Verify no imports:** Check that no files import deleted modules
   ```bash
   grep -r "import modal_api" --include="*.py" .
   grep -r "from modal_api" --include="*.py" .
   ```

2. **Check GitHub Actions:** Verify `.github/workflows/deploy_modal.yml` only uses modal_api_v2.py ✅

3. **Backup first:** Create git branch for cleanup
   ```bash
   git checkout -b cleanup-dead-code
   ```

4. **Test after cleanup:**
   ```bash
   modal deploy modal_api_v2.py
   pytest tests/
   ```

### What NOT to Delete:

- ❌ `modal_api_v2.py` - CURRENTLY DEPLOYED
- ❌ `modal_scanner.py` - CURRENTLY DEPLOYED
- ❌ Active `.github/workflows/` files
- ❌ Any file with recent modifications (check git log)

---

## 📊 FRONTEND ANALYSIS

### JavaScript Functions

**Total Functions:** 79
**Potentially Low Usage:** 15 functions

Most functions are properly used. The following have low call counts but are likely event handlers:
- `addDeal()` - Called by onclick
- `addTrade()` - Called by onclick
- `executeBuy()` - Called by onclick
- `executeSell()` - Called by onclick

**Assessment:** ✅ All functions appear to be used (many are event handlers)

### CSS Classes

**Hidden Elements:** 5 instances of `display: none`
**Assessment:** Used for tab switching and responsive design ✅

---

## 🎯 CONCLUSION

### Summary

**Dead Code Found:**
- 🔴 **3 duplicate/broken modal APIs** (1,782 lines) - CRITICAL
- 🟠 **2 unused scrapers** (128 lines) - HIGH
- 🟠 **7 duplicate utility functions** (60 lines) - HIGH
- 🟡 **12 stub endpoints** (documented) - MEDIUM
- 🟢 **27 archived files** - LOW

**Total Cleanup Potential:** ~2,000 lines of code + 27 files

### Recommended Actions

**Immediate (Today):**
1. Delete 3 duplicate modal APIs
2. Clean build artifacts
3. Test deployment

**This Week:**
1. Consolidate ensure_data_dir()
2. Remove unused scrapers
3. Decide on SocketIO (fix or remove)

**This Month:**
1. Document stub endpoints
2. Review archived documentation
3. Plan scraper migration to Finnhub/Tiingo

### Risk Assessment

**Low Risk:** Deleting duplicate modal APIs, archived files, build artifacts
**Medium Risk:** Removing deprecated scrapers (verify no external dependencies)
**High Risk:** Removing SocketIO (test thoroughly if real-time sync is needed)

---

**Report Generated:** 2026-02-01
**Analysis Duration:** 60 minutes
**Files Analyzed:** 120+ Python + Frontend files
**Dead Code Identified:** ~2,000 lines + 27 files

**✅ READY FOR CLEANUP**
