# Change Log (Auto-Updated)

<!-- AUTO-GENERATED BELOW -->

### 2026-02-05 19:37 - `75fd281`

**Frontend cleanup: remove archive files, unused code, fix CSS conflicts**

Files changed: 146

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/BUNDLE_MAPPING.txt
docs/GITHUB_SECRETS_COPY_PASTE.txt
docs/XAI_API_KEY_REQUIRED.txt
docs/archive/BEFORE_AFTER_COMPARISON.md
docs/archive/BUGS_FIXED_2026-01-29.md
docs/archive/COMPREHENSIVE_AGENTIC_BRAIN_SUMMARY.md
docs/archive/EARNINGS_COMPONENT_38_COMPLETE.md
docs/archive/EARNINGS_GUIDANCE_ANALYSIS.md
docs/archive/EVOLUTIONARY_SYSTEM_IMPLEMENTATION.md
docs/archive/FEATURES_2-9_IMPLEMENTATION_SUMMARY.md
docs/archive/INTEGRATION_PROGRESS_2026-01-29.md
docs/archive/INTEGRATION_SESSION_2_COMPLETE.md
docs/archive/PRICING_CORRECTION_SUMMARY.md
docs/archive/RAILWAY_DEPLOYMENT_GUIDE.md
docs/archive/SELF_LEARNING_SYSTEM_COMPLETE.md
docs/archive/WATCHLIST_BRAIN_INTEGRATION.md
docs/archive/WATCHLIST_IMPLEMENTATION_COMPLETE.md
docs/archive/XAI_IMPLEMENTATION_SUMMARY.md
docs/archive/XAI_OPPORTUNITIES_SUMMARY.md
docs/archive/XAI_X_INTELLIGENCE_IMPLEMENTATION.md
docs/archive/consolidated-2026-02-02/AGENTIC_BRAIN_ARCHITECTURE.md
docs/archive/consolidated-2026-02-02/AI_AB_TEST_CORRECTED_FINAL.md
docs/archive/consolidated-2026-02-02/AI_AB_TEST_FINAL_RESULTS.md
docs/archive/consolidated-2026-02-02/AI_ENHANCEMENTS_USAGE_GUIDE.md
docs/archive/consolidated-2026-02-02/AI_STRESS_TEST_ANALYSIS.md
docs/archive/consolidated-2026-02-02/BACKEND_ISSUES_REPORT.md
docs/archive/consolidated-2026-02-02/CHANGELOG.md
docs/archive/consolidated-2026-02-02/CHANGE_HISTORY.md
docs/archive/consolidated-2026-02-02/COMPLETE_AI_COMPONENT_INVENTORY.md
```
</details>

---


### 2026-02-05 19:33 - `e9247c1`

**Major code cleanup: remove unused functions and debug endpoints**

Files changed: 5

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_api_v2.py
src/data/options.py
src/data/polygon_provider.py
src/data/tastytrade_provider.py
```
</details>

---


### 2026-02-05 19:26 - `9b98147`

**Fix live Tastytrade futures quote fetching for GEX endpoint**

Files changed: 4

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_api_v2.py
src/data/options.py
src/data/tastytrade_provider.py
```
</details>

---


### 2026-02-05 18:59 - `4731f9b`

**Fix futures price fetching using SPY/QQQ reference prices**

Files changed: 3

<details>
<summary>Show files</summary>

```
CHANGES.md
src/data/options.py
src/data/tastytrade_provider.py
```
</details>

---


### 2026-02-05 18:28 - `37045ee`

**Fix futures current price estimation for GEX calculation**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
src/data/options.py
```
</details>

---


### 2026-02-05 18:24 - `9349a25`

**Remove max pain feature entirely and use GEX for OI/DTE**

Files changed: 3

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
src/data/options.py
```
</details>

---


### 2026-02-05 18:11 - `ac4b5fe`

**Fix expiration dropdown parsing for futures - handle object format {date, dte}**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
```
</details>

---


### 2026-02-05 18:03 - `476d525`

**Fix futures options buttons - use /ES, /NQ, /CL, /GC format**

Files changed: 5

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
modal_api_v2.py
src/data/options.py
src/data/tastytrade_provider.py
```
</details>

---


### 2026-02-05 17:46 - `d78d2cc`

**Update CHANGES.md**

Files changed: 1

<details>
<summary>Show files</summary>

```
CHANGES.md
```
</details>

---


### 2026-02-05 17:46 - `880406f`

**Add news endpoints and full Tastytrade futures options integration**

Files changed: 4

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_api_v2.py
src/data/options.py
src/data/tastytrade_provider.py
```
</details>

---


### 2026-02-05 16:19 - `4c28ef1`

**Fix Tastytrade provider for SDK v11 chain structure**

Files changed: 4

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_api_v2.py
requirements.txt
src/data/tastytrade_provider.py
```
</details>

---


### 2026-02-05 16:02 - `605b41d`

**Fix Tastytrade SDK session creation - use (client_secret, refresh_token)**

Files changed: 5

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_api_v2.py
requirements.txt
scripts/get_tastytrade_token.py
src/data/tastytrade_provider.py
```
</details>

---


### 2026-02-05 15:52 - `286d896`

**Update Tastytrade provider to use OAuth2 authentication**

Files changed: 3

<details>
<summary>Show files</summary>

```
CHANGES.md
requirements.txt
src/data/tastytrade_provider.py
```
</details>

---


### 2026-02-05 15:50 - `6ef4495`

**Add Tastytrade integration for 120 DTE ratio spread analysis**

Files changed: 6

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
modal_api_v2.py
requirements.txt
src/data/options.py
src/data/tastytrade_provider.py
```
</details>

---


### 2026-02-05 15:34 - `118e39b`

**Fix term structure validation to require back DTE > front DTE**

Files changed: 3

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_api_v2.py
src/data/options.py
```
</details>

---


### 2026-02-05 15:28 - `92af4fc`

**Fix ratio spread calculation bugs: RV column name, expected move DTE, term structure validation**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
src/data/options.py
```
</details>

---


### 2026-02-05 15:25 - `4e545b3`

**Fix ratio spread calculation bugs**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
src/data/options.py
```
</details>

---


### 2026-02-05 15:21 - `e7d4d78`

**Update CHANGES.md with recent GEX and Ratio Spread features**

Files changed: 1

<details>
<summary>Show files</summary>

```
CHANGES.md
```
</details>

---


### 2026-02-05 15:19 - `fa1f2f5`

**Add Ratio Spread Conditions dashboard with 6-factor scoring**

Files changed: 3

<details>
<summary>Show files</summary>

```
docs/index.html
modal_api_v2.py
src/data/options.py
```
</details>

**Backend models (options.py):**
- `calculate_realized_volatility()`: 5d/10d/20d/30d RV with direction
- `get_vrp_analysis()`: Variance Risk Premium (IV - RV) with scoring
- `get_skew_analysis()`: 25-delta put skew analysis
- `get_expected_move()`: ATM straddle expected move with 1.5x/2x levels
- `get_iv_term_structure()`: Contango/backwardation detection
- `get_ratio_spread_score()`: Combined 6-factor scoring system

**API endpoints:**
- `/options/vrp/{ticker}`
- `/options/skew/{ticker}`
- `/options/expected-move/{ticker}`
- `/options/term-structure/{ticker}`
- `/options/realized-vol/{ticker}`
- `/options/ratio-spread-score/{ticker}`

**Frontend:** Ratio Spread Conditions dashboard with verdict banner, 6-factor grid, pass/fail indicators, strike planning levels

---

### 2026-02-05 14:55 - `b743c72`

**Update GEX to industry standard formula (Spot²/100)**

Files changed: 1

<details>
<summary>Show files</summary>

```
src/data/options.py
```
</details>

- Changed GEX formula from `(Gamma × OI × Multiplier × Spot)` to `(Gamma × OI × Multiplier × Spot² / 100)` per SpotGamma convention
- This normalizes GEX to 'per 1% move' basis for cross-ticker comparison
- Updated regime thresholds with price-scaling for accuracy
- Added confidence field to regime response

---

### 2026-02-05 14:30 - `4f947de`

**Add comprehensive GEX analysis models and dashboard**

Files changed: 3

<details>
<summary>Show files</summary>

```
docs/index.html
modal_api_v2.py
src/data/options.py
```
</details>

**Backend:**
- `get_gex_regime()`: Volatility regime classifier (pinned/volatile/transitional)
- `get_gex_levels()`: S/R wall mapper (call wall, put wall, gamma flip)
- `get_gex_analysis()`: Complete GEX analysis combining regime + levels
- `get_pc_ratio_analysis()`: P/C ratio with Z-score normalization
- `get_combined_regime()`: 2x2 GEX + P/C ratio matrix

**API:** 5 new endpoints for GEX regime, levels, analysis, combined regime, P/C ratio

**Frontend:** GEX Dashboard with regime, levels, signals, position sizing

---

### 2026-02-05 00:30 - Futures Options Support

**Add futures options support (ES, NQ, CL, GC)**

Files changed: 2

<details>
<summary>Show files</summary>

```
docs/index.html
src/data/options.py
```
</details>

**New Feature:** Added support for futures options analysis:
- Added quick ticker buttons for ES, NQ, CL, GC (E-mini S&P, Nasdaq, Crude, Gold)
- Added futures contract specs with proper multipliers (ES=50x, NQ=20x, CL=1000x, GC=100x)
- Updated GEX calculation to use futures-specific multipliers
- Updated Max Pain calculation to use futures-specific multipliers
- Added "FUTURES" badge and contract info in analysis panel
- Added futures context to interpretation text
- Styled futures buttons with orange theme for visual distinction

---


### 2026-02-05 00:15 - GEX Consistency Fix

**Fix GEX data consistency between Market Sentiment and Options Analysis**

Files changed: 1

<details>
<summary>Show files</summary>

```
docs/index.html
```
</details>

**Fix:** GEX values differed between hero zone and Options Analysis panel when viewing SPY:
- Removed fallback to `sentiment.gex` (stale/unfiltered) - now only uses real GEX endpoint
- Added expiration sync between Market Sentiment and Options Analysis for SPY
- Added `isSyncingExpiry` flag to prevent infinite recursion
- Both sections now show identical values when same ticker/expiration selected

---


### 2026-02-05 00:05 - `2f62916`

**Fix Market Sentiment to use same data as Options Analysis**

Files changed: 1

<details>
<summary>Show files</summary>

```
docs/index.html
```
</details>

**Fix:** Market Sentiment hero now uses identical data sources as Options Analysis:
- P/C Ratio: OI-based (putOI/callOI) instead of volume-based
- GEX: Real GEX from `/options/gex` endpoint instead of simplified proxy
- Consistent thresholds and labels

---


### 2026-02-04 23:55 - `c1629f4`

**Fix Options tab - guard missing element references**

Files changed: 1

<details>
<summary>Show files</summary>

```
docs/index.html
```
</details>

**Fix:** spy-oi-label element was removed in new layout but JS still tried to access it, causing error that blocked GEX and sentiment gauge updates.

---


### 2026-02-04 23:50 - `35f875f`

**Improve Options tab UI and usability**

Files changed: 1

<details>
<summary>Show files</summary>

```
docs/index.html
```
</details>

**Changes:**
- Quick ticker shortcuts (SPY, QQQ, NVDA, TSLA, AAPL, AMD, META)
- Visual sentiment gauge with animated needle
- Consolidated hero zone (2-column layout)
- Auto-load SPY data on tab open
- Mobile responsive layouts

---


### 2026-02-04 23:35 - `472b068`

**Replace Trading tab with Options as main tab**

Files changed: 1

<details>
<summary>Show files</summary>

```
docs/index.html
```
</details>

---


### 2026-02-04 23:25 - `884c2a3`

**Add CHANGELOG.md to docs with v3.2.0 updates**

Files changed: 1

<details>
<summary>Show files</summary>

```
docs/CHANGELOG.md
```
</details>

---


### 2026-02-04 23:20 - `fa5ad17`

**Simplify dashboard: restructure SEC Intel and Health tabs**

Files changed: 1

<details>
<summary>Show files</summary>

```
docs/index.html
```
</details>

---


### 2026-02-04 22:45 - `eb750ac`

**Fix scan file loading to exclude non-date-formatted files**

Files changed: 1

<details>
<summary>Show files</summary>

```
modal_api_v2.py
```
</details>

---


### 2026-02-04 22:30 - `07be44d`

**Fix null pointer errors in agentic_brain.py and rename test script**

Files changed: 2

<details>
<summary>Show files</summary>

```
src/ai/agentic_brain.py
tests/telegram_diagnostic.py
```
</details>

---


### 2026-02-04 22:15 - `8ed0353`

**Fix IV Rank to use actual IV from Polygon options**

Files changed: 1

<details>
<summary>Show files</summary>

```
src/analysis/options_flow.py
```
</details>

---


### 2026-02-04 18:06 - `a49338f`

**Add real GEX calculation with proper gamma values**

Files changed: 4

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
modal_api_v2.py
src/data/options.py
```
</details>

---


### 2026-02-04 17:53 - `33e29f6`

**Add clickable GEX and Max Pain charts with toggle**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
```
</details>

---


### 2026-02-04 17:22 - `0d12d12`

**Merge Options Analysis and Max Pain into unified panel**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
```
</details>

---


### 2026-02-04 17:10 - `57c02d7`

**Fix max pain to auto-select nearest expiration when none provided**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
src/data/options.py
```
</details>

---


### 2026-02-04 17:02 - `cf6f083`

**Fix Quick Analysis max pain accuracy - fetch from dedicated endpoint**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
```
</details>

---


### 2026-02-04 16:28 - `7d0a686`

**Add quick options analysis with P/C, GEX, IV Rank**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
```
</details>

---


### 2026-02-04 16:08 - `2cfc600`

**Activate X/Social sentiment with real X search**

Files changed: 4

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
modal_api_v2.py
src/ai/xai_x_intelligence_v2.py
```
</details>

---


### 2026-02-04 16:04 - `d1956cb`

**Replace mock data with real data in Health tab**

Files changed: 3

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
modal_api_v2.py
```
</details>

---


### 2026-02-04 15:48 - `14b8ce7`

**Add SEC/institutional scoring module for Market Health**

Files changed: 3

<details>
<summary>Show files</summary>

```
CHANGES.md
src/scoring/__init__.py
src/scoring/sec_scoring.py
```
</details>

---


### 2026-02-04 15:40 - `ce54540`

**Fix SVG gauge rendering - use stroke-dashoffset**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
```
</details>

---


### 2026-02-04 15:35 - `c9dee0d`

**Add comprehensive Market Health visualization tab**

Files changed: 3

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
modal_api_v2.py
```
</details>

---


### 2026-02-04 15:13 - `dbce3e3`

**Add info tooltips to SPY Key Levels card**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
```
</details>

---


### 2026-02-04 15:10 - `f7911cc`

**Disable X Crisis Monitor cron schedule**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_scanner.py
```
</details>

---


### 2026-02-04 15:09 - `e0b6fd8`

**Add SPY volume profile key levels to dashboard**

Files changed: 4

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
modal_api_v2.py
src/data/options.py
```
</details>

---


### 2026-02-04 14:53 - `bd5727e`

**Add info tooltips to Market Options Sentiment metrics**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
```
</details>

---


### 2026-02-04 14:49 - `b584b32`

**Add global expiration selector for Market Options Sentiment**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
```
</details>

---


### 2026-02-04 14:43 - `d50e85a`

**Add expiration date selector for SPY Max Pain in Market Sentiment**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
```
</details>

---


### 2026-02-04 14:42 - `ae49367`

**Add SPY Max Pain to Market Options Sentiment section**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
```
</details>

---


### 2026-02-04 14:36 - `afc5af1`

**Fix max pain bar highlight with tolerance for fractional strikes**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
```
</details>

---


### 2026-02-04 14:34 - `7ca1bb0`

**Fix chart bars using pixel heights instead of percentages**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
```
</details>

---


### 2026-02-04 14:26 - `352256c`

**Add debug logging to chart render function**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
```
</details>

---


### 2026-02-04 14:23 - `218d254`

**Fix chart: replace canvas with div-based bar chart, remove orphan code**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
```
</details>

---


### 2026-02-04 14:21 - `2baaf7b`

**Fix chart rendering - variable name bug and add debugging**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
```
</details>

---


### 2026-02-04 14:16 - `ea56cfa`

**Fix max pain chart - filter strikes around current price**

Files changed: 3

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
src/data/options.py
```
</details>

---


### 2026-02-04 14:11 - `6b9973c`

**Add pain by strike chart to Max Pain analysis**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
```
</details>

---


### 2026-02-04 14:04 - `d1fa743`

**Fix max pain current price to use real-time snapshot**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
src/data/options.py
```
</details>

---


### 2026-02-04 13:58 - `bd00333`

**Redesign options flow UI with visual sentiment gauge**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
```
</details>

---


### 2026-02-04 13:55 - `4e8b148`

**Fix expirations endpoint to fetch all available dates**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
src/data/options.py
```
</details>

---


### 2026-02-04 13:53 - `ec170c2`

**Add expiration date support to Max Pain analysis**

Files changed: 4

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
modal_api_v2.py
src/data/options.py
```
</details>

---


### 2026-02-04 13:40 - `9415a65`

**Add Max Pain theory to Options tab**

Files changed: 4

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
modal_api_v2.py
src/data/options.py
```
</details>

---


### 2026-02-04 13:33 - `1fce3a8`

**Restructure all dashboard tabs with 4-tier visual hierarchy**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
```
</details>

---


### 2026-02-04 13:17 - `0295754`

**Restructure dashboard with 4-tier visual hierarchy**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
```
</details>

---


### 2026-02-04 13:01 - `d9ed275`

**Add utils mount to Modal image for Theme Registry**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_scanner.py
```
</details>

---


### 2026-02-04 00:15 - `9c4e8b8`

**Fix X Intelligence to use same pattern as working xai_x_intelligence_v2**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
src/intelligence/x_intelligence.py
```
</details>

---


### 2026-02-04 00:07 - `8f3fc8f`

**Remove Reddit, update X Intelligence to use xai_sdk with x_search**

Files changed: 3

<details>
<summary>Show files</summary>

```
CHANGES.md
src/core/async_scanner.py
src/intelligence/x_intelligence.py
```
</details>

---


### 2026-02-04 00:02 - `13f9ed4`

**Add social buzz to scoring formula and integrate X Intelligence**

Files changed: 4

<details>
<summary>Show files</summary>

```
CHANGES.md
src/core/async_scanner.py
src/core/story_scoring.py
src/scoring/story_scorer.py
```
</details>

---


### 2026-02-03 23:37 - `165411c`

**Add technical filters for stock universe scanning**

Files changed: 4

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_api_v2.py
modal_scanner.py
src/data/universe_manager.py
```
</details>

---


### 2026-02-03 23:16 - `e1d0638`

**Fix JSON serialization with robust NaN/numpy type handling**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_scanner.py
```
</details>

---


### 2026-02-03 22:56 - `e19ab66`

**Fix NaN values in JSON serialization for scan results**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_scanner.py
```
</details>

---


### 2026-02-03 22:42 - `84c8b65`

**Fix: Dashboard and Telegram now show same sorted results**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_scanner.py
```
</details>

---


### 2026-02-03 22:40 - `460e46c`

**Fix Google Trends rate limiting with throttling and backoff**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
src/intelligence/google_trends.py
```
</details>

---


### 2026-02-03 22:18 - `cd43064`

**Add secrets to daily_scan for manual testing**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_scanner.py
```
</details>

---


### 2026-02-03 22:11 - `6074c09`

**Fix: Add secrets to all scheduled bundle functions**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_scanner.py
```
</details>

---


### 2026-02-03 21:58 - `98ecf43`

**Fix risk_reward calculation in agentic stock analysis**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_api_v2.py
```
</details>

---


### 2026-02-03 21:56 - `c0cb2a5`

**Integrate Agentic Brain AI system into dashboard**

Files changed: 3

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
modal_api_v2.py
```
</details>

---


### 2026-02-03 21:39 - `1e669a4`

**Remove Quick Actions from dashboard and fix Daily Digest bug**

Files changed: 3

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
modal_api_v2.py
```
</details>

---


### 2026-02-03 21:22 - `8800c00`

**Optimize dashboard loading with staged data fetching**

Files changed: 3

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
docs/js/main.js
```
</details>

---


### 2026-02-03 21:18 - `2352d15`

**Fix missing fetchAIIntelligence and fetchUnusualOptions in module's refreshAll**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/js/main.js
```
</details>

---


### 2026-02-03 21:15 - `20a0fd5`

**Add fetchUnusualOptions to dashboard data loading**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
```
</details>

---


### 2026-02-03 21:09 - `4f6654e`

**Fix wrong API URL in config.js that was breaking dashboard data loading**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/js/config.js
```
</details>

---


### 2026-02-03 21:04 - `a0701d0`

**Fix dashboard data loading with improved error handling and logging**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
```
</details>

---


### 2026-02-03 20:51 - `4a16ded`

**Fix Hot Themes on dashboard to render theme pills and stocks**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
```
</details>

---


### 2026-02-03 20:46 - `c12728b`

**Fix High Conviction alerts to handle API response structure**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
```
</details>

---


### 2026-02-03 20:41 - `03f07a2`

**Fix dashboard to load High Conviction and Hot Themes data**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
```
</details>

---


### 2026-02-03 20:34 - `8dfd8fa`

**Restructure dashboard from 10 flat tabs to 4 main categories**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
```
</details>

---


### 2026-02-03 19:25 - `3441efc`

**Fix AI reasoning modal close button leaving overlay blocking dashboard**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
```
</details>

---


### 2026-02-03 19:21 - `d73b6ff`

**Fix confirmations/conflicts to only compare directional signals**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_api_v2.py
```
</details>

---


### 2026-02-03 19:15 - `a06e717`

**Add AI Intelligence Hub with unified market analysis**

Files changed: 3

<details>
<summary>Show files</summary>

```
.gitignore
docs/index.html
modal_api_v2.py
```
</details>

---


### 2026-02-03 18:38 - `3d85e9c`

**Add debug providers endpoint and fix CPI YoY calculation**

Files changed: 2

<details>
<summary>Show files</summary>

```
modal_api_v2.py
utils/data_providers.py
```
</details>

---


### 2026-02-03 18:15 - `2e15383`

**Add FRED Economic Dashboard with comprehensive indicators**

Files changed: 4

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
modal_api_v2.py
utils/data_providers.py
```
</details>

---


### 2026-02-03 18:06 - `63cdaeb`

**Fix themes tab API and JS for proper data rendering**

Files changed: 3

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
modal_api_v2.py
```
</details>

---


### 2026-02-03 18:03 - `c59dd49`

**Fix correlations endpoint to return flat pair format for dashboard**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_api_v2.py
```
</details>

---


### 2026-02-03 17:54 - `681efb7`

**Fix tooltip clipping by using JS-based tooltips appended to body**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
```
</details>

---


### 2026-02-03 17:51 - `a113c3a`

**Improve tooltip readability with better contrast and styling**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
```
</details>

---


### 2026-02-03 17:47 - `ad5c3bf`

**Fix Analytics tab API response structures for dashboard compatibility**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_api_v2.py
```
</details>

---


### 2026-02-03 17:35 - `a352b96`

**Fix SEC Intel tab API connections and data rendering**

Files changed: 3

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
modal_api_v2.py
```
</details>

---


### 2026-02-03 17:28 - `1020070`

**Fix nested response structure in contracts/patents themes endpoints**

Files changed: 3

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
modal_api_v2.py
```
</details>

---


### 2026-02-03 17:25 - `5de66fd`

**Fix SEC Intel API response structure to match dashboard JS**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_api_v2.py
```
</details>

---


### 2026-02-03 17:16 - `eb21f71`

**Bot only reads and replies in Bot Alerts topic**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_api_v2.py
```
</details>

---


### 2026-02-03 17:12 - `16f7cf8`

**Send bot messages to group topic instead of main chat**

Files changed: 6

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_scanner.py
src/notifications/notification_manager.py
tests/check_cron_status.py
tests/test_group_notification.py
tests/trigger_crisis_monitor.py
```
</details>

---


### 2026-02-03 16:46 - `1f90a23`

**Change tooltips from underlined text to info icons**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
```
</details>

---


### 2026-02-03 16:40 - `1e7431d`

**Add tooltips to Options, Analytics, and SEC Intel tabs**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
```
</details>

---


### 2026-02-03 16:27 - `2d4113b`

**Watchlist updates now reflect instantly**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
```
</details>

---


### 2026-02-03 16:17 - `a9ce0bb`

**Header refresh button now only refreshes current tab**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
```
</details>

---


### 2026-02-03 16:15 - `7d04c87`

**Optimize dashboard performance with lazy loading**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
```
</details>

---


### 2026-02-03 16:11 - `e238d70`

**Fix watchlist persistence with volume.commit()**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_api_v2.py
```
</details>

---


### 2026-02-03 16:04 - `671bc5d`

**Add expandable scan rows with individual stock add/remove**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
```
</details>

---


### 2026-02-03 15:55 - `7444765`

**Add dedicated Watchlist tab to dashboard**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
```
</details>

---


### 2026-02-03 15:48 - `c72a163`

**Add unified watchlist and scan management system**

Files changed: 12

<details>
<summary>Show files</summary>

```
CHANGES.md
assets/stockstory_icon.png
assets/stockstory_icon.svg
assets/stockstory_logo.png
assets/stockstory_logo.svg
assets/stockstory_minimal.png
assets/stockstory_minimal.svg
docs/index.html
modal_api_v2.py
modal_scanner.py
src/data/__init__.py
src/data/watchlist_manager.py
```
</details>

---


### 2026-02-03 04:17 - `49f5b09`

**feat: Add group chat support for all notifications**

Files changed: 3

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_scanner.py
src/notifications/notification_manager.py
```
</details>

---


### 2026-02-03 04:12 - `e9a6c3a`

**fix: Use correct variable name in /chatid command**

Files changed: 7

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_api_v2.py
tests/check_bot_chats.py
tests/check_group_admin.py
tests/find_stockstory_group.py
tests/send_chatid_to_group.py
tests/test_group_chatid.py
```
</details>

---


### 2026-02-03 04:02 - `7cd157c`

**feat: Add /chatid command to get chat ID for group alerts**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_api_v2.py
```
</details>

---


### 2026-02-03 03:56 - `c1e725f`

**fix: Always calculate market fear level even if other fetches fail**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
src/analysis/options_flow.py
```
</details>

---


### 2026-02-03 03:54 - `64dcca3`

**feat: Add GEX and Max Pain to /hedge command**

Files changed: 4

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_api_v2.py
tests/test_hedge_command.py
tests/test_hedge_webhook.py
```
</details>

---


### 2026-02-03 03:48 - `6aab1d5`

**fix: Revert VIX to yfinance (Polygon VIX is EOD only)**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
src/analysis/options_flow.py
```
</details>

---


### 2026-02-03 03:44 - `ef29448`

**feat: Get VIX from Polygon Indices API**

Files changed: 3

<details>
<summary>Show files</summary>

```
CHANGES.md
src/analysis/options_flow.py
src/data/polygon_provider.py
```
</details>

---


### 2026-02-03 03:41 - `03f8484`

**feat: Use Polygon for SPY/QQQ prices in Grok analysis**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
src/analysis/options_flow.py
```
</details>

---


### 2026-02-03 03:40 - `c4d3337`

**feat: Feed Polygon live options data to Grok for put analysis**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
src/analysis/options_flow.py
```
</details>

---


### 2026-02-03 03:37 - `a90bf88`

**feat: Integrate Grok 4.1 Fast Reasoning for put protection analysis**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
src/analysis/options_flow.py
```
</details>

---


### 2026-02-03 03:32 - `892ad66`

**feat: Add options sentiment and put protection to crisis alerts**

Files changed: 4

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_api_v2.py
src/analysis/options_flow.py
src/notifications/notification_manager.py
```
</details>

---


### 2026-02-03 03:23 - `af999a5`

**feat: Add SPY and QQQ prices to health monitor**

Files changed: 3

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
modal_api_v2.py
```
</details>

---


### 2026-02-03 03:21 - `ca17519`

**fix: Add comma formatting for large dollar amounts**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
```
</details>

---


### 2026-02-03 03:15 - `5550ead`

**fix: Use month abbreviation for expiration dates (Feb 7 instead of 2/7)**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
```
</details>

---


### 2026-02-03 03:13 - `86cfd56`

**feat: Add expiration date to Whale Trades, Unusual Activity, and Smart Money Flow**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
```
</details>

---


### 2026-02-03 03:07 - `e0b1eba`

**fix: Fix vol/OI ratio display in Unusual Activity**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
```
</details>

---


### 2026-02-03 03:03 - `998a4e4`

**fix: Fix put/call ratio display in Options Chain Lookup**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
```
</details>

---


### 2026-02-03 03:00 - `37bd848`

**feat: Add real 0DTE volume from Polygon options data**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_api_v2.py
```
</details>

---


### 2026-02-03 02:56 - `08716de`

**fix: Fix GEX calculation and display formatting**

Files changed: 3

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
modal_api_v2.py
```
</details>

---


### 2026-02-03 02:55 - `3938685`

**fix: Increase Polygon options limit to 250 for full chain data**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
src/data/polygon_provider.py
```
</details>

---


### 2026-02-03 02:49 - `56dc6f3`

**fix: Call correct functions when switching to Options tab**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
```
</details>

---


### 2026-02-03 02:45 - `48fd195`

**fix: Lower whale trades threshold to $50K for more data**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
```
</details>

---


### 2026-02-03 02:43 - `27605ae`

**feat: Enable Polygon.io for real-time options data**

Files changed: 4

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_api_v2.py
src/analysis/options_flow.py
src/data/polygon_provider.py
```
</details>

---


### 2026-02-03 02:37 - `fc40f30`

**fix: Fix JavaScript to handle API response field names**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
```
</details>

---


### 2026-02-03 02:32 - `ef8afb0`

**feat: Enhanced options flow with dashboard UI and Telegram commands**

Files changed: 4

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
modal_api_v2.py
src/analysis/options_flow.py
```
</details>

---


### 2026-02-03 02:09 - `096d458`

**docs: Update CHANGES.md with latest entries**

Files changed: 1

<details>
<summary>Show files</summary>

```
CHANGES.md
```
</details>

---


### 2026-02-03 02:02 - `56ac910`

**fix: Add raw_data to health endpoint for dashboard market pulse**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_api_v2.py
```
</details>

---


### 2026-02-03 01:56 - `b27d5e5`

**fix: Update API response format to match dashboard expectations**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_api_v2.py
```
</details>

---


### 2026-02-03 01:53 - `b16bf53`

**fix: Auto-load data when switching tabs**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
```
</details>

---


### 2026-02-03 01:52 - `5475bce`

**fix: Update API_BASE to use stockstory-api endpoint**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
```
</details>

---


### 2026-02-03 01:46 - `c161f59`

**feat: Add theme management to dashboard**

Files changed: 3

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
modal_api_v2.py
```
</details>

---


### 2026-02-03 01:37 - `c126191`

**feat: Implement hybrid dynamic theme system with AI discovery**

Files changed: 6

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_api_v2.py
src/themes/fast_stories.py
src/themes/theme_manager.py
tests/test_theme_commands.py
tests/test_theme_manager.py
```
</details>

---


### 2026-02-02 21:37 - `247a19f`

**fix: Telegram bot volume access and themes display**

Files changed: 5

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_api_v2.py
modal_scanner.py
static/stockstory_logo.svg
tests/send_test_message.py
```
</details>

---


### 2026-02-02 20:43 - `9a959fa`

**fix: Add volume.reload() to sync scan results**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_api_v2.py
```
</details>

---


### 2026-02-02 20:39 - `8fd18e5`

**fix: Update /themes command to use correct function**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_api_v2.py
```
</details>

---


### 2026-02-02 20:31 - `5b3d8ab`

**fix: Use max_containers instead of deprecated concurrency_limit**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_scanner.py
```
</details>

---


### 2026-02-02 20:30 - `dabc579`

**fix: Save scan results CSV to Modal volume for API access**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_scanner.py
```
</details>

---


### 2026-02-02 20:20 - `309410f`

**perf: Limit GPU concurrency to 10 containers max**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_scanner.py
```
</details>

---


### 2026-02-02 20:16 - `d8122a7`

**fix: Correct /news command import error**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_api_v2.py
```
</details>

---


### 2026-02-02 20:07 - `49108d0`

**fix: Update GitHub workflows for StockStory rename**

Files changed: 4

<details>
<summary>Show files</summary>

```
.github/workflows/deploy.yml
.github/workflows/manual-deploy.yml
.github/workflows/test-crisis-monitor.yml
CHANGES.md
```
</details>

---


### 2026-02-02 19:42 - `52e277f`

**refactor: Complete StockStory rebranding**

Files changed: 13

<details>
<summary>Show files</summary>

```
.env.example
CHANGES.md
PROJECT.md
README.md
docs/deployment/DEPLOYMENT_STATUS.md
docs/index.html
main.py
modal_api_v2.py
scripts/maintenance/cleanup_modal_schedules.sh
scripts/run_scan.sh
src/notifications/notification_manager.py
utils/__init__.py
utils/exceptions.py
```
</details>

---


### 2026-02-02 19:37 - `53eb300`

**refactor: Rename project to StockStory**

Files changed: 8

<details>
<summary>Show files</summary>

```
CHANGES.md
main.py
modal_api_v2.py
modal_scanner.py
src/__init__.py
src/api/app.py
tests/setup_telegram_menu.py
tests/setup_telegram_webhook.py
```
</details>

---


### 2026-02-02 19:30 - `1c4e219`

**docs: Update CHANGES.md**

Files changed: 1

<details>
<summary>Show files</summary>

```
CHANGES.md
```
</details>

---


### 2026-02-02 19:30 - `8adb657`

**chore: Add Telegram message reader utility**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
tests/read_telegram_messages.py
```
</details>

---


### 2026-02-02 19:27 - `0f760d1`

**feat: Add Telegram menu button and inline keyboards**

Files changed: 3

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_api_v2.py
tests/setup_telegram_menu.py
```
</details>

---


### 2026-02-02 19:20 - `6db7447`

**feat: 6-month candlestick chart with 10/20/50/200 SMAs**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_api_v2.py
```
</details>

---


### 2026-02-02 19:15 - `8215f97`

**feat: Replace line chart with candlestick chart**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_api_v2.py
```
</details>

---


### 2026-02-02 19:11 - `5cad92c`

**fix: Add Markdown fallback for Telegram replies**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_api_v2.py
```
</details>

---


### 2026-02-02 18:58 - `3e328da`

**feat: Add detailed logging to Telegram webhook**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_api_v2.py
```
</details>

---


### 2026-02-02 18:50 - `d5b2b07`

**fix: Correct import for calculate_story_score in Telegram bot**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_api_v2.py
```
</details>

---


### 2026-02-02 18:47 - `7a7546f`

**feat: Enhanced Telegram bot with rich analysis and charts**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_api_v2.py
```
</details>

---


### 2026-02-02 18:40 - `743626b`

**fix: Fix Telegram bot webhook conflict and add instant messaging**

Files changed: 5

<details>
<summary>Show files</summary>

```
.github/workflows/bot_listener.yml
CHANGES.md
modal_api_v2.py
tests/fix_telegram_webhook.py
tests/setup_telegram_webhook.py
```
</details>

---


### 2026-02-02 18:28 - `a4ef6fe`

**fix: Correct import errors in Modal API endpoints**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_api_v2.py
```
</details>

---


### 2026-02-02 18:11 - `95fd20d`

**perf: Optimize web scraping with parallel fetching and fix broken sources**

Files changed: 5

<details>
<summary>Show files</summary>

```
CHANGES.md
src/analysis/news_analyzer.py
src/data/alt_sources.py
src/scoring/story_scorer.py
src/themes/fast_stories.py
```
</details>

---


### 2026-02-02 17:54 - `48a7385`

**fix: Add missing except block in evolutionary_agentic_brain.py**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
src/ai/evolutionary_agentic_brain.py
```
</details>

---


### 2026-02-02 17:53 - `9532c1a`

**chore: Update CHANGES.md with latest entry**

Files changed: 1

<details>
<summary>Show files</summary>

```
CHANGES.md
```
</details>

---


### 2026-02-02 17:39 - `bd0d648`

**fix: modal_api_v2.py use correct secret name (Stock_Story)**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_api_v2.py
```
</details>

---


### 2026-02-02 17:36 - `e6d4ed1`

**docs: Add Modal secret name (Stock_Story) to PROJECT.md**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
PROJECT.md
```
</details>

---


### 2026-02-02 17:18 - `e94964e`

**fix: Post-commit hook now stacks entries correctly**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
scripts/hooks/post-commit
```
</details>

---


### 2026-02-02 17:17 - `e1f043d`

**chore: Update CHANGES.md with latest entry**

Files changed: 1

<details>
<summary>Show files</summary>

```
CHANGES.md
```
</details>

---

