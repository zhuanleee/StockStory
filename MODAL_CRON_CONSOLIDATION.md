# Modal Cron Job Consolidation

## Issue

Modal has a limit of **5 scheduled cron jobs** per app on the free/hobby tier.

Current implementation has **16 scheduled functions**, which exceeds this limit:
```
Error: Deployment failed: reached limit of 5 cron jobs
```

## Solution: Consolidate into 5 Cron Jobs

Combine related functions that run at similar times into bundled jobs.

---

## Consolidated Schedule

### 1. Daily Morning Scan (6:00 AM PST / 14:00 UTC)
**Cron**: `0 14 * * 1-5`

**Functions**:
- `daily_scan()` - Main stock scanning with AI brain

**Duration**: ~5-10 minutes
**Purpose**: Core daily analysis

---

### 2. Morning Alerts Bundle (6:45 AM PST / 14:45 UTC)
**Cron**: `45 14 * * 1-5`

**Functions** (all run sequentially in one job):
1. `automated_theme_discovery()` - Theme discovery
2. `conviction_alerts()` - High-conviction stocks > 80
3. `unusual_options_alerts()` - Unusual options flow
4. `sector_rotation_alerts()` - Sector momentum
5. `institutional_flow_alerts()` - Smart money tracking
6. `executive_commentary_alerts()` - CEO/CFO sentiment
7. `daily_executive_briefing()` - Market open briefing

**Duration**: ~15-20 minutes total
**Purpose**: All morning alerts and briefing in one batch

**Rationale**: All these alerts depend on the daily scan results and should run after it completes.

---

### 3. Afternoon Analysis (1:00 PM PST / 21:00 UTC)
**Cron**: `0 21 * * 1-5`

**Functions** (sequential):
1. `daily_correlation_analysis()` - Theme/sector correlations
2. `batch_insider_transactions_update()` - Insider data refresh (moved from 2 PM)

**Duration**: ~20-30 minutes
**Purpose**: Mid-day analysis and data pipeline

---

### 4. Weekly Reports & Updates (Sunday 6:00 PM PST / Monday 02:00 UTC)
**Cron**: `0 2 * * 1` (Mondays 02:00 UTC = Sunday 6 PM PST)

**Functions** (sequential):
1. `weekly_summary_report()` - Week's performance summary
2. `parameter_learning_health_check()` - Learning system health
3. `batch_contracts_update()` - Weekly government contracts
4. `batch_patent_data_update()` - Monthly patents (conditional: 1st Monday only)

**Duration**: ~30-45 minutes
**Purpose**: Weekly reporting and maintenance

**Conditional Logic**:
```python
# Inside weekly function
if datetime.now().day <= 7:  # First week of month
    batch_patent_data_update()
```

---

### 5. Monitoring & Pre-fetch (Every 6 hours)
**Cron**: `0 */6 * * *` (00:00, 06:00, 12:00, 18:00 UTC)

**Functions** (sequential):
1. `data_staleness_monitor()` - Check data freshness
2. `batch_google_trends_prefetch()` - Pre-fetch trends (conditional: market hours only)

**Duration**: ~10-15 minutes
**Purpose**: Continuous monitoring and data prep

**Conditional Logic**:
```python
# Inside monitoring function
hour = datetime.now().hour
if 14 <= hour < 22:  # During/near market hours
    batch_google_trends_prefetch()
```

---

## Implementation Strategy

### Option A: Bundled Functions (Recommended)
Create 5 new "bundle" functions that call the individual functions sequentially.

**Pros**:
- Keeps existing functions intact
- Easy to test individual functions
- Clear separation of concerns
- Can run functions independently for testing

**Cons**:
- Slightly more code
- Need wrapper functions

### Option B: Merge Functions
Combine function logic directly into 5 mega-functions.

**Pros**:
- Less code overall
- Simpler structure

**Cons**:
- Harder to test individual pieces
- Less modular
- Harder to maintain

**Decision**: Use Option A (Bundled Functions)

---

## Implementation Example

### Before (16 separate scheduled functions):
```python
@app.function(schedule=modal.Cron("0 15 * * 1-5"))
def conviction_alerts():
    # ...

@app.function(schedule=modal.Cron("15 15 * * 1-5"))
def unusual_options_alerts():
    # ...

@app.function(schedule=modal.Cron("30 15 * * 1-5"))
def sector_rotation_alerts():
    # ...
```

### After (1 bundled scheduled function):
```python
@app.function(schedule=modal.Cron("45 14 * * 1-5"))
def morning_alerts_bundle():
    """Run all morning alerts in sequence"""
    print("=" * 70)
    print("🚀 MORNING ALERTS BUNDLE")
    print("=" * 70)

    results = {}

    # 1. Theme discovery
    print("\n1. Running theme discovery...")
    results['themes'] = automated_theme_discovery_internal()

    # 2. Conviction alerts
    print("\n2. Running conviction alerts...")
    results['conviction'] = conviction_alerts_internal()

    # 3. Options alerts
    print("\n3. Running options alerts...")
    results['options'] = unusual_options_alerts_internal()

    # ... etc

    return results

# Keep individual functions as non-scheduled for testing
def automated_theme_discovery_internal():
    # Original function logic
    pass

def conviction_alerts_internal():
    # Original function logic
    pass
```

---

## Migration Steps

1. **Rename existing scheduled functions** to `*_internal()`
2. **Remove @app.function decorators** from internal functions
3. **Create 5 bundle functions** with cron schedules
4. **Test locally** with `modal run`
5. **Deploy** and verify in Modal dashboard
6. **Monitor** first scheduled runs

---

## Testing Commands

```bash
# Test individual functions (no schedule)
modal run modal_scanner.py::morning_alerts_bundle
modal run modal_scanner.py::afternoon_analysis
modal run modal_scanner.py::weekly_reports

# View deployed schedules
modal schedule list

# Check logs
modal app logs stock-scanner-ai-brain --follow
```

---

## Expected Results

**Before**: 16 cron jobs → Deployment fails
**After**: 5 cron jobs → Deployment succeeds

**Functionality**: 100% preserved
**Performance**: Slightly slower (sequential vs parallel) but acceptable
**Maintainability**: Improved (fewer scheduled jobs to manage)

---

## Rollout Plan

1. Implement consolidation locally
2. Test bundled functions
3. Deploy to Modal
4. Verify all 5 schedules active
5. Monitor first automated runs
6. Update documentation

---

**Status**: Ready to implement
**Estimated Time**: 1-2 hours
**Risk**: Low (functionality preserved, just reorganized)
