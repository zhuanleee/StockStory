# 🎯 Stock Scanner Bot - Current State

**Last Updated:** February 2, 2026 - 12:30 UTC
**Version:** 3.1.0
**Status:** 🟢 All systems operational

---

## 📊 System Overview

### Architecture
```
Stock Scanner Bot v3.1
├── Dashboard (GitHub Pages) - FREE
│   └── Web Dashboard (docs/index.html)
│
└── Backend (Modal.com) - $2-3/month
    ├── Flask API
    ├── Telegram Bot
    ├── Crisis Monitoring (every 15 min)
    ├── Daily Scans (6 AM PST Mon-Fri)
    ├── Exit Signals (6 AM PST Mon-Fri) ← TIER 3
    ├── Meme Scanner (manual) ← TIER 3
    └── Sector Rotation (manual) ← TIER 3
```

**Total Cost:** $2-3/month (optimized from $15/month)

---

## 🚀 Live Deployments

### GitHub Pages (Dashboard)
- **URL:** https://zhuanleee.github.io/stock_scanner_bot/
- **Status:** 🟢 Active
- **Last Deploy:** Auto-deploy on push to main
- **Components:**
  - Web dashboard (7 intelligence visualizations)
  - Static hosting (free)

### Modal.com (Backend + Bot)
- **App:** stock-scanner
- **Status:** 🟢 Active (5/5 cron slots used)
- **Last Deploy:** Feb 2, 2026 08:29 UTC
- **Components:**
  - Flask API (38-component analysis)
  - Telegram bot (@Stocks_Story_Bot)
  - 26 functions deployed
  - 5 cron jobs running
  - Tier 3 features integrated

---

## 🧠 3-Layer Intelligence System

### Layer 1: X/Twitter Intelligence (Social Detection)
**Implementation:** `src/ai/xai_x_intelligence_v2.py`
- Real-time X search using xAI SDK with `x_search` tool
- Dynamic quality filters (verified accounts, engagement thresholds)
- 5-minute caching (80% fewer API calls)
- Smart model selection (reasoning vs non-reasoning)

**Features:**
- Crisis detection from verified news accounts
- Stock sentiment analysis (last 1-2 hours)
- Meme stock viral momentum detection
- Sector sentiment tracking

**Cost:** $1-2/month (optimized with caching + batch queries)

### Layer 2: Web Intelligence (News Verification)
**Implementation:** `src/ai/web_intelligence.py`
- Verifies X rumors with authoritative sources
- Searches: Reuters, Bloomberg, CNBC, AP News, WSJ
- Uses xAI SDK with `web_search` tool

**Features:**
- Crisis verification (filters false alarms)
- Company news and red flag detection
- Market event verification

**Cost:** Included in Layer 1 cost

### Layer 3: Data Intelligence (Market Data)
**Implementation:** Multiple sources
- Google Trends (retail momentum)
- Earnings transcripts (Alpha Vantage)
- SEC filings (insider trading, executive commentary)
- Government contracts (USASpending.gov)
- Patent activity (PatentsView)
- Institutional flow (Polygon options data)

**Cost:** Mostly free APIs

---

## 🛡️ Tier 3 Features (Current Status)

### ✅ Exit Signal Detection - LIVE
**File:** `src/intelligence/exit_signal_detector.py`
**Integration:** `modal_scanner.py::morning_mega_bundle` (step 9/9)
**Schedule:** Automatic - Daily 6 AM PST (Mon-Fri)
**Status:** 🟢 Running

**How It Works:**
1. Runs before market open (6 AM PST)
2. Checks all holdings (currently: NVDA, TSLA, AAPL, GOOGL, META)
3. Detects:
   - Red flags (lawsuits, fraud, investigations)
   - Negative sentiment (score < -5)
   - Sentiment reversals (bullish → bearish in 24h)
4. Web verification with `web_intelligence.py`
5. Telegram alerts for exit signals

**Quality Filters:**
- Verified accounts only
- 5,000+ followers
- 20+ engagement (likes + retweets)

**Next Run:** Tomorrow 6 AM PST

### 🔄 Meme Stock Scanner - DEPLOYED (Manual)
**File:** `src/intelligence/meme_stock_detector.py`
**Function:** `modal_intelligence_jobs.py::daily_meme_stock_scan`
**Schedule:** Manual trigger only
**Status:** 🟡 Available (no auto-schedule)

**How It Works:**
1. Scans 150 tickers for viral momentum
2. Batch search (50 tickers per query) - optimized
3. No verification filter (catches early signals)
4. Detects:
   - Unusual mention volume (>1000/hour)
   - Meme keywords (diamond hands, apes, moon, etc.)
   - Short squeeze signals
   - Bullish sentiment spikes
5. Meme score calculation (0-10)
6. Top 10 candidates returned

**Quality Filters:**
- No account filters (need early signals)
- High engagement threshold (100+ for viral detection)

**Manual Trigger:**
```bash
modal run modal_intelligence_jobs.py::daily_meme_stock_scan
```

**Recommended:** Run daily at 2 PM PST (afternoon momentum)

### 🔄 Sector Rotation Tracker - DEPLOYED (Manual)
**File:** `src/intelligence/sector_rotation_tracker.py`
**Function:** `modal_intelligence_jobs.py::weekly_sector_rotation_analysis`
**Schedule:** Manual trigger only
**Status:** 🟡 Available (no auto-schedule)

**How It Works:**
1. Analyzes sentiment across 10 sectors:
   - Technology, Healthcare, Finance, Energy, Consumer
   - Industrials, Materials, Utilities, RealEstate, Communications
2. Sector representatives (5 stocks per sector)
3. Calculates average sentiment per sector
4. Identifies rotation signals:
   - ROTATE_INTO (gaining momentum)
   - ROTATE_OUT (losing momentum)
   - OVERWEIGHT (strong sector)
   - UNDERWEIGHT (weak sector)
5. Telegram weekly report

**Quality Filters:**
- Verified accounts only
- 1,000+ followers
- 10+ engagement

**Manual Trigger:**
```bash
modal run modal_intelligence_jobs.py::weekly_sector_rotation_analysis
```

**Recommended:** Run weekly on Sundays at 8 PM PST

---

## ⚙️ Smart Model Selection

**File:** `src/ai/model_selector.py`

**Strategy:** Auto-switches between reasoning and non-reasoning models based on task criticality.

| Task Type | Model | Reasoning | Use Case |
|-----------|-------|-----------|----------|
| Crisis detection | `grok-4-1-fast` | ✅ Yes | Accuracy critical |
| Exit signals | `grok-4-1-fast` | ✅ Yes | Money at stake |
| Red flag analysis | `grok-4-1-fast` | ✅ Yes | Safety critical |
| Meme scanning | `grok-4-1-fast-non-reasoning` | ❌ No | Speed matters |
| Quick sentiment | `grok-4-1-fast-non-reasoning` | ❌ No | Batch processing |
| Sector rotation | `grok-4-1-fast-non-reasoning` | ❌ No | Simple averaging |

**Trade-off:** Same cost, optimized for speed vs accuracy

---

## 📅 Cron Schedule (Modal)

| Job | Cron Expression | Time (PST) | Frequency | Status |
|-----|----------------|------------|-----------|--------|
| **morning_mega_bundle** | `0 14 * * 1-5` | 6 AM | Mon-Fri | 🟢 Active |
| **afternoon_analysis_bundle** | `0 21 * * 1-5` | 1 PM | Mon-Fri | 🟢 Active |
| **weekly_reports_bundle** | `0 2 * * 1` | Sun 6 PM | Weekly | 🟢 Active |
| **monitoring_cycle_bundle** | `0 */6 * * *` | Every 6h | Daily | 🟢 Active |
| **x_intelligence_crisis_monitor** | `*/15 * * * *` | Every 15min | 24/7 | 🟢 Active |

**Total:** 5/5 cron slots (Modal free tier limit)

### Morning Bundle Details (6 AM PST)
1. daily_scan (main stock scanning)
2. automated_theme_discovery
3. conviction_alerts
4. unusual_options_alerts
5. sector_rotation_alerts
6. institutional_flow_alerts
7. executive_commentary_alerts
8. daily_executive_briefing
9. **exit_signal_check (TIER 3)** ← New!

---

## 🔧 Optimization Details

### Caching Layer
**File:** `src/ai/xai_x_intelligence_v2.py`
**TTL:** 5 minutes
**Impact:** 80% reduction in repeated API calls

**How It Works:**
```python
# Cache key: sentiment_{ticker}_{verified_only}_{min_followers}_{min_engagement}
cache_key = f"sentiment_NVDA_True_1000_10"
# Stores: (data, timestamp)
# Expires: After 5 minutes
```

**Cache Hit Rate:** 60-80% for repeated tickers

### Batch Search
**File:** `src/intelligence/meme_stock_detector.py`
**Batch Size:** 50 tickers per query
**Impact:** 150 queries → 3 queries (97% reduction)

**Before:**
```python
for ticker in [150 tickers]:
    search_sentiment(ticker)  # 150 API calls
```

**After:**
```python
batches = [tickers[i:i+50] for i in range(0, 150, 50)]  # 3 batches
for batch in batches:
    search_sentiment_batch(batch)  # 3 API calls
```

**Cost Reduction:** $0.88/month saved

### Quality Filters (Dynamic)
**No fixed influencer lists** - Uses algorithmic signals instead

**Filter Tiers:**
- **CRITICAL** (Holdings): Verified, 5K+ followers, 20+ engagement
- **HIGH** (Watchlist): Verified, 1K+ followers, 10+ engagement
- **LOW** (Universe scan): Verified, 50K+ followers, 100+ engagement
- **OPEN** (Meme detection): No filters (catch early signals)

---

## 📂 Repository Structure

```
stock_scanner_bot/
├── README.md                          # Main documentation
├── CHANGELOG.md                       # Version history
├── CURRENT_STATE.md                   # This file (always current)
├── CHANGE_HISTORY.md                  # All changes with before/after
├── SESSION_LOG.md                     # Detailed session logs
│
├── src/                               # Source code
│   ├── ai/                           # AI intelligence modules
│   │   ├── xai_x_intelligence_v2.py  # X Intelligence (with caching)
│   │   ├── web_intelligence.py       # Web news verification
│   │   └── model_selector.py         # Smart model selection
│   │
│   ├── intelligence/                 # Intelligence detectors
│   │   ├── exit_signal_detector.py   # Exit signals (TIER 3)
│   │   ├── meme_stock_detector.py    # Meme detection (TIER 3)
│   │   └── sector_rotation_tracker.py # Sector rotation (TIER 3)
│   │
│   ├── core/                         # Core scanner
│   ├── trading/                      # Exit strategy
│   ├── learning/                     # Learning system
│   └── data/                         # Data fetchers
│
├── modal_scanner.py                  # Main Modal app (5 cron jobs)
├── modal_intelligence_jobs.py        # Tier 3 functions (callable)
├── modal_api_v2.py                   # API for dashboard
│
├── docs/                             # Documentation
│   ├── deployment/
│   │   ├── MODAL_DEPLOYMENT.md       # Modal setup guide
│   │   └── DEPLOYMENT_SUCCESS.md     # Latest deployment report
│   └── archive/                      # Old documentation
│
├── scripts/                          # Utility scripts
│   ├── deployment/                   # Deploy scripts
│   ├── verification/                 # Health checks
│   └── maintenance/                  # Cleanup scripts
│
├── tests/                            # Test suite
│
└── .github/workflows/                # CI/CD
    ├── deploy-scanner.yml            # Deploy scanner to Modal
    └── deploy-intelligence.yml       # Deploy intelligence to Modal
```

**Root Files:** 20 (cleaned from 98)
**Archived:** 78 old markdown files

---

## 🔑 Environment Variables

### Modal Secrets (Stock_Story)
```bash
POLYGON_API_KEY=xxx          # Stock data
TELEGRAM_BOT_TOKEN=xxx       # Bot token
TELEGRAM_CHAT_ID=xxx         # Your chat ID
XAI_API_KEY=xxx              # xAI Grok
DEEPSEEK_API_KEY=xxx         # AI analysis
ALPHA_VANTAGE_API_KEY=xxx    # Earnings
```

**Note:** All secrets are stored in Modal.com under the `Stock_Story` secret.

---

## 🧪 How to Test

### Test Exit Signal Detector
```bash
modal run modal_intelligence_jobs.py::daily_exit_signal_check
```

### Test Meme Scanner
```bash
modal run modal_intelligence_jobs.py::daily_meme_stock_scan
```

### Test Sector Rotation
```bash
modal run modal_intelligence_jobs.py::weekly_sector_rotation_analysis
```

### Test Single Stock Analysis
```bash
modal run modal_scanner.py::test_single_stock --ticker NVDA
```

### View Live Logs
```bash
modal app logs stock-scanner --follow
```

---

## 📊 Performance Metrics

### API Call Reduction
- **Before:** ~500 calls/day
- **After:** ~100 calls/day (80% reduction)
- **Method:** 5-minute caching + batch queries

### Cost Reduction
- **Before:** $5-8/month (xAI intelligence)
- **After:** $1-3/month (60% reduction)
- **Method:** Caching + batching + quality filters

### Response Time
- **Cached queries:** <100ms
- **Uncached queries:** 1-2s
- **Batch queries:** 2-3s (50 tickers)

---

## 🎯 Known Limitations

### Modal Free Tier
- **Cron limit:** 5 jobs (currently using 5/5)
- **Solution:** Bundled jobs to stay within limit
- **Impact:** Meme + sector rotation are manual triggers

### Quality Filters
- **Trade-off:** Better signal quality but may miss some early signals
- **Mitigation:** Meme detection uses open search (no filters)

### Holdings List
- **Current:** Hardcoded list (NVDA, TSLA, AAPL, GOOGL, META)
- **TODO:** Integrate with actual portfolio tracking
- **File:** `modal_scanner.py::_run_exit_signal_check()` line ~922

---

## 🔄 Next Improvements (Optional)

### 1. Auto-integrate Meme + Sector
**Benefit:** Full automation (no manual triggers)
**Cost:** None (already within cron limits)
**Implementation:**
- Add `_run_meme_stock_scan()` to `afternoon_analysis_bundle`
- Add `_run_sector_rotation()` to `weekly_reports_bundle`

### 2. Dynamic Holdings List
**Benefit:** Real portfolio tracking
**Implementation:**
- Create portfolio tracking service
- Store holdings in Modal volume
- Query from exit signal detector

### 3. Options Dashboard Integration
**Benefit:** Visualize options flow in dashboard
**Status:** Backend ready, frontend pending
**See:** [Polygon Options Plan](/Users/johnlee/.claude/plans/transient-painting-stallman.md)

---

## 📞 Quick Commands

### Deploy
```bash
# Deploy scanner
gh workflow run deploy-scanner.yml

# Deploy intelligence
gh workflow run deploy-intelligence.yml
```

### Monitor
```bash
# App status
modal app list

# Live logs
modal app logs stock-scanner --follow

# Check recent errors
modal app logs stock-scanner | grep ERROR
```

### Test
```bash
# Test exit signals
modal run modal_intelligence_jobs.py::daily_exit_signal_check

# Test meme scanner
modal run modal_intelligence_jobs.py::daily_meme_stock_scan

# Test sector rotation
modal run modal_intelligence_jobs.py::weekly_sector_rotation_analysis
```

---

## 📝 Important Notes

### When Modal Deployment Fails
**Error:** "reached limit of 5 cron jobs"
**Cause:** Too many `schedule=modal.Cron()` decorators
**Solution:** Remove schedule decorators from new functions, integrate into existing bundles

### When Adding New Intelligence Features
1. Create function in `modal_intelligence_jobs.py` **WITHOUT** cron schedule
2. Add helper function to `modal_scanner.py` (e.g., `_run_new_feature()`)
3. Call from existing bundle (morning/afternoon/weekly)
4. Redeploy both files

### Cache Invalidation
**TTL:** 5 minutes (automatic)
**Manual clear:** Restart Modal app (cache is in-memory)

---

## 🔗 Links

- **Dashboard:** https://zhuanleee.github.io/stock_scanner_bot/
- **GitHub:** https://github.com/zhuanleee/stock_scanner_bot
- **Telegram Bot:** [@Stocks_Story_Bot](https://t.me/Stocks_Story_Bot)
- **Modal Dashboard:** https://modal.com/apps

---

**Last verified working:** February 2, 2026 12:30 UTC
**Next scheduled update:** After next feature change
