# Stock Scanner - Market Schedule

**Updated:** January 31, 2026
**Status:** ✅ Configured to run only on market open days

---

## Scan Schedule

### Automatic Scans
**Frequency:** Daily at **6:00 AM PST** (14:00 UTC)
**Days:** **Monday - Friday only** (when market is open)
**Holidays:** **Automatically skipped**

---

## Cron Schedule

```python
schedule=modal.Cron("0 14 * * 1-5")  # Mon-Fri at 14:00 UTC (6 AM PST)
```

**Breakdown:**
- `0` - Minute (00)
- `14` - Hour (14:00 UTC = 6:00 AM PST)
- `*` - Day of month (any)
- `*` - Month (any)
- `1-5` - Day of week (Monday=1 through Friday=5)

---

## Market Holidays 2026

Scanner automatically skips these US market holidays:

| Date | Holiday |
|------|---------|
| January 1, 2026 | New Year's Day |
| January 19, 2026 | Martin Luther King Jr. Day |
| February 16, 2026 | Presidents Day |
| April 3, 2026 | Good Friday |
| May 25, 2026 | Memorial Day |
| July 3, 2026 | Independence Day (observed) |
| September 7, 2026 | Labor Day |
| November 26, 2026 | Thanksgiving |
| December 25, 2026 | Christmas |

**Total:** 9 holidays

---

## How It Works

### 1. Cron Trigger (Modal)
```
Monday-Friday at 6:00 AM PST
```

### 2. Holiday Check (Python)
```python
# Check if today is a market holiday
today_date = datetime(today.year, today.month, today.day)
if today_date in market_holidays_2026:
    print(f"📅 Market is CLOSED - {holiday_name}")
    return {'success': False, 'reason': 'market_holiday'}
```

### 3. Weekend Check (Backup)
```python
# Shouldn't happen with Mon-Fri cron, but just in case
if today.weekday() >= 5:  # Saturday or Sunday
    return {'success': False, 'reason': 'weekend'}
```

### 4. Scan Proceeds
```python
print(f"📅 Market is OPEN - {today.strftime('%A, %B %d, %Y')}")
# Continue with scan...
```

---

## Example Output

### Market Open Day (Normal Scan)
```
======================================================================
🚀 STARTING DAILY AI BRAIN SCAN
======================================================================
📅 Market is OPEN - Monday, January 31, 2026

📊 Universe: 515 stocks (S&P500 + NASDAQ 300M+)
⏰ Start time: 2026-01-31 14:00:00 UTC
🔄 Scanning 515 stocks in batches of 10 (GPU limit)...
```

### Market Holiday (Skipped)
```
======================================================================
🚀 STARTING DAILY AI BRAIN SCAN
======================================================================
📅 Today is Christmas - Market is CLOSED
⏭️  Skipping scan. Next scan: Next market open day
======================================================================
```

### Weekend (Skipped - shouldn't happen)
```
======================================================================
🚀 STARTING DAILY AI BRAIN SCAN
======================================================================
📅 Today is Saturday - Market is CLOSED
⏭️  Skipping scan. Next scan: Monday
======================================================================
```

---

## Scan Days Per Month (2026)

| Month | Trading Days | Holidays | Weekends | Total Days |
|-------|--------------|----------|----------|------------|
| January | 21 | 2 (1, 19) | 8 | 31 |
| February | 19 | 1 (16) | 8 | 28 |
| March | 21 | 0 | 10 | 31 |
| April | 21 | 1 (3) | 9 | 30 |
| May | 20 | 1 (25) | 10 | 31 |
| June | 22 | 0 | 8 | 30 |
| July | 22 | 1 (3) | 9 | 31 |
| August | 21 | 0 | 10 | 31 |
| September | 21 | 1 (7) | 9 | 30 |
| October | 23 | 0 | 9 | 31 |
| November | 19 | 1 (26) | 10 | 30 |
| December | 22 | 1 (25) | 9 | 31 |
| **Total** | **252** | **9** | **109** | **365** |

**252 trading days** = 252 scans per year

---

## Benefits

### 1. Cost Savings
- **No scans on weekends:** Saves 104 unnecessary scans/year
- **No scans on holidays:** Saves 9 unnecessary scans/year
- **Total savings:** 113 wasted scans/year

**Modal GPU cost:** ~$0.60/hour × 5 min = ~$0.05 per scan
**Annual savings:** 113 scans × $0.05 = **~$5.65/year**

### 2. Cleaner Data
- No stale data from non-trading days
- Scan results always reflect market activity
- Easier to analyze scan history

### 3. Resource Efficiency
- Modal compute credits not wasted
- API rate limits preserved for trading days
- Better GPU availability during peak hours

---

## Manual Scans

You can still trigger scans manually anytime (even weekends/holidays):

```bash
# Scan single stock
modal run modal_scanner.py --ticker NVDA

# Full scan
modal run modal_scanner.py --daily
```

**Note:** Manual scans ignore the schedule and run immediately.

---

## Updating Holidays

To update holidays for 2027, edit `modal_scanner.py`:

```python
# Line ~138
market_holidays_2026 = [
    datetime(2027, 1, 1),   # New Year's Day
    datetime(2027, 1, 18),  # MLK Day (3rd Monday of Jan)
    datetime(2027, 2, 15),  # Presidents Day (3rd Monday of Feb)
    # ... add remaining holidays
]
```

**NYSE Holiday Calendar:** https://www.nyse.com/markets/hours-calendars

---

## Verification

### Check Next Scan Time
```bash
# Check Modal cron schedule
modal app list

# Should show: "0 14 * * 1-5" (Mon-Fri at 14:00 UTC)
```

### Check Last Scan
```bash
# View Modal logs
modal app logs stock-scanner-ai-brain

# Look for "Market is OPEN" or "Market is CLOSED" message
```

### Test Holiday Logic
```python
# In modal_scanner.py, temporarily set today to a holiday
today = datetime(2026, 12, 25)  # Christmas

# Run manually
modal run modal_scanner.py --daily

# Should see: "Today is Christmas - Market is CLOSED"
```

---

## Timezone Notes

**Cron runs at:** 14:00 UTC
**Equivalent to:**
- 6:00 AM PST (Pacific Standard Time)
- 7:00 AM PDT (Pacific Daylight Time - summer)
- 9:00 AM EST (Eastern Standard Time)
- 10:00 AM EDT (Eastern Daylight Time - summer)

**Why 6 AM PST?**
- Before market open (9:30 AM EST)
- Scan completes before trading starts
- Data ready for pre-market analysis
- Telegram notification before your morning routine

---

## Summary

✅ **Scans:** Mon-Fri at 6 AM PST
✅ **Holidays:** Automatically skipped (9 US holidays)
✅ **Weekends:** Skipped by cron schedule
✅ **Manual:** Available anytime via CLI
✅ **Cost:** Saves ~$5.65/year in unnecessary scans
✅ **Data:** Always fresh from trading days only

**Next scan:** Next market open day at 6:00 AM PST

---

**Configuration:** modal_scanner.py:118 (cron schedule)
**Holiday list:** modal_scanner.py:138-147 (market_holidays_2026)
**Deployed:** January 31, 2026 (commit a217e5c)
