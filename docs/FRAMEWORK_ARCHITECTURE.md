# Stock Scanner Bot - Complete Framework & Workflow Documentation

**Version:** 2.0
**Last Updated:** 2026-01-29
**Project:** Institutional-Grade Story-First Stock Scanner

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Core Philosophy](#core-philosophy)
3. [Architecture Layers](#architecture-layers)
4. [Complete Data Flow](#complete-data-flow)
5. [Scanning Workflow](#scanning-workflow)
6. [Intelligence Framework](#intelligence-framework)
7. [Scoring System](#scoring-system)
8. [Learning System](#learning-system)
9. [Hard Data Framework](#hard-data-framework)
10. [Automation Workflows](#automation-workflows)
11. [Integration Points](#integration-points)
12. [Operational Procedures](#operational-procedures)
13. [Decision Trees](#decision-trees)
14. [Performance Optimization](#performance-optimization)

---

## 1. System Overview

### 1.1 Mission Statement
Identify high-conviction stock opportunities by prioritizing narratives and hard data over pure technicals, using self-learning AI to adapt to market conditions.

### 1.2 Key Metrics
- **Codebase:** 78 Python files, 56,729 lines
- **Scan Speed:** 500+ stocks in ~7 minutes (60x speedup)
- **Data Sources:** 10+ APIs (Polygon, SEC, USPTO, USAspending, etc.)
- **Learning Parameters:** 85+ auto-tuning parameters
- **Themes Tracked:** 17+ market themes
- **Cache Hit Rate:** 60-80%

### 1.3 Technology Stack
```
Language:        Python 3.11+
Async Runtime:   asyncio, aiohttp
Data Provider:   Polygon.io (primary), yfinance (fallback)
AI Engine:       DeepSeek API, xAI Grok
Bot Platform:    Telegram Bot API
Web Framework:   Flask (REST API)
CI/CD:           GitHub Actions
Deployment:      Modal.com (Backend/Bot), GitHub Pages (Dashboard)
```

---

## 2. Core Philosophy

### 2.1 Story-First Principle
```
Traditional Scanner:  Technicals (80%) + Story (20%)
This Scanner:         Story (85%) + Confirmation (15%)
```

**Why Stories Matter:**
- Narratives drive institutional capital allocation
- Technical setups without stories fade quickly
- Stories create multi-month momentum
- Retail follows institutional narratives with lag

### 2.2 Hard Data > Sentiment
```
Priority Order:
1. Hard Data (leads 1-12 months)
   - Patents (6-12 months)
   - Government Contracts (1-3 months)
   - Insider Buying (0-1 month)

2. Smart Money (confirms 0-1 month)
   - Options Flow
   - Institutional 13F

3. Sentiment (validates or warns)
   - Positive = Confirmation
   - Euphoric = WARNING (too late)

4. Technical (timing)
   - Entry/exit timing only
```

### 2.3 Learning-First Design
- **NO hardcoded parameters** (except theme names/keywords)
- **ALL weights learned** from outcomes
- **Bayesian optimization** with Thompson sampling
- **Shadow mode testing** before production
- **Continuous validation** and rollback capability

---

## 3. Architecture Layers

### 3.1 System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER INTERFACES                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │   Telegram   │  │    Web API   │  │   Dashboard  │              │
│  │     Bot      │  │   (Flask)    │  │  (GitHub Pg) │              │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘              │
└─────────┼──────────────────┼──────────────────┼─────────────────────┘
          │                  │                  │
┌─────────┼──────────────────┼──────────────────┼─────────────────────┐
│         │         ORCHESTRATION LAYER         │                      │
│         ▼                  ▼                  ▼                      │
│  ┌─────────────────────────────────────────────────────┐            │
│  │           Async Scanner (Core Engine)                │            │
│  │  • AsyncScanner: Parallel execution                  │            │
│  │  • RateLimiter: Per-API token bucket                 │            │
│  │  • CacheManager: TTL + LRU + prefetch                │            │
│  │  • DataFetcher: Multi-source concurrent fetch        │            │
│  └─────────────────────────────────────────────────────┘            │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
┌───────────────────────────────┼─────────────────────────────────────┐
│         INTELLIGENCE LAYER    │                                      │
│  ┌────────────┬───────────────┼──────────────┬──────────────┐       │
│  ▼            ▼               ▼              ▼              ▼       │
│ ┌──────┐  ┌──────┐  ┌──────────────┐  ┌─────────┐  ┌──────────┐   │
│ │Theme │  │Story │  │ Hard Data    │  │Options  │  │Ecosystem │   │
│ │Intel │  │Scorer│  │   Scanner    │  │  Flow   │  │  Intel   │   │
│ │Hub   │  │      │  │              │  │         │  │          │   │
│ └──────┘  └──────┘  └──────────────┘  └─────────┘  └──────────┘   │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
┌───────────────────────────────┼─────────────────────────────────────┐
│           DATA LAYER          │                                      │
│  ┌────────────┬───────────────┼──────────────┬──────────────┐       │
│  ▼            ▼               ▼              ▼              ▼       │
│ ┌─────┐  ┌────────┐  ┌─────────┐  ┌────────┐  ┌───────────┐       │
│ │Poly-│  │Patents │  │Gov      │  │SEC     │  │Google     │       │
│ │gon  │  │View    │  │Contracts│  │EDGAR   │  │Trends     │       │
│ │.io  │  │(USPTO) │  │(USA$)   │  │(SEC)   │  │           │       │
│ └─────┘  └────────┘  └─────────┘  └────────┘  └───────────┘       │
│                                                                      │
│ ┌─────────┐  ┌──────────┐  ┌────────┐  ┌─────────┐                │
│ │StockTwit│  │ Reddit   │  │X/Twtr  │  │ yfinance│                │
│ │         │  │          │  │        │  │(fallback)│               │
│ └─────────┘  └──────────┘  └────────┘  └─────────┘                │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│                      LEARNING LAYER                                   │
│  ┌─────────────────────────────────────────────────────────┐         │
│  │         Evolution Engine (Self-Learning)                 │         │
│  │  • ParameterLearning: Bayesian optimization             │         │
│  │  • OutcomeTracker: Attribution & feedback               │         │
│  │  • ThompsonSampling: Exploration/exploitation           │         │
│  │  • ABTesting: Controlled experiments                    │         │
│  │  • ShadowMode: Safe testing before production           │         │
│  │  • ValidationMonitor: Continuous performance check      │         │
│  └─────────────────────────────────────────────────────────┘         │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│                     STORAGE LAYER                                     │
│  ┌───────────┐  ┌────────────┐  ┌──────────────┐  ┌──────────┐     │
│  │File Cache │  │JSON State  │  │CSV Results   │  │Learning  │     │
│  │(TTL-based)│  │(Themes,    │  │(Scan output) │  │  Data    │     │
│  │           │  │ Scanner)   │  │              │  │          │     │
│  └───────────┘  └────────────┘  └──────────────┘  └──────────┘     │
└──────────────────────────────────────────────────────────────────────┘
```

### 3.2 Module Breakdown

#### Core Modules (`/src/core`)
- **async_scanner.py** (42KB) - Main scanning engine
- **story_scoring.py** (22KB) - Story-first scoring logic
- **scanner_automation.py** (82KB) - Automated scanning workflows
- **screener.py** (13KB) - Custom screening filters

#### Intelligence Modules (`/src/intelligence`)
- **theme_intelligence.py** (33KB) - Multi-signal theme detection
- **theme_discovery_engine.py** (41KB) - Auto-discover emerging themes
- **hard_data_scanner.py** (25KB) - Conviction scoring from hard data
- **institutional_flow.py** (23KB) - Smart money tracking
- **rotation_predictor.py** (24KB) - Theme rotation forecasting

#### Data Modules (`/src/data`)
- **polygon_provider.py** (66KB) - Polygon.io integration
- **cache_manager.py** (23KB) - Multi-tier caching
- **universe_manager.py** (36KB) - Stock universe management
- **patents.py** (20KB) - USPTO patent tracking
- **gov_contracts.py** (23KB) - Federal contract tracking
- **sec_edgar.py** (16KB) - SEC filings integration
- **google_trends.py** (17KB) - Trend velocity tracking

#### Scoring Modules (`/src/scoring`)
- **story_scorer.py** (59KB) - Main scoring engine
- **signal_ranker.py** (22KB) - Multi-signal ranking
- **param_helper.py** (14KB) - Parameter utilities

#### Analysis Modules (`/src/analysis`)
- **news_analyzer.py** (42KB) - Multi-source news aggregation
- **ecosystem_intelligence.py** (36KB) - Supply chain mapping
- **market_health.py** (31KB) - Market breadth analysis
- **earnings.py** (14KB) - Earnings calendar
- **sector_rotation.py** (15KB) - Sector analysis

#### Learning Modules (`/src/learning`)
- **parameter_learning.py** (75KB) - Bayesian optimization
- **evolution_engine.py** (70KB) - Self-learning coordinator
- **self_learning.py** (44KB) - Continuous improvement

#### Trading Modules (`/src/trading`)
- **trade_manager.py** (12KB) - Trade CRUD
- **exit_scanner.py** (21KB) - Exit signal detection
- **scaling_engine.py** (20KB) - Position sizing
- **risk_advisor.py** (20KB) - Risk management

#### API Module (`/src/api`)
- **app.py** (245KB) - Comprehensive Flask REST API

---

## 4. Complete Data Flow

### 4.1 End-to-End Data Pipeline

```
┌─────────────────────────────────────────────────────────────────────┐
│  STAGE 1: DATA INGESTION (Async Parallel)                           │
└─────────────────────────────────────────────────────────────────────┘
        │
        ├─► Polygon.io (Primary)
        │   ├─► Price/Volume (15min cache)
        │   ├─► Options Chain (30min cache)
        │   ├─► News Feed (30min cache)
        │   └─► Financials (24hr cache)
        │
        ├─► Hard Data Sources
        │   ├─► Patents (PatentsView, 24hr cache)
        │   ├─► Gov Contracts (USAspending, 12hr cache)
        │   └─► SEC Filings (EDGAR, 1hr cache)
        │
        ├─► Social Sentiment
        │   ├─► Google Trends (1hr cache)
        │   ├─► StockTwits (1hr cache)
        │   ├─► Reddit (1hr cache)
        │   └─► X/Twitter (1hr cache)
        │
        └─► Fallback: yfinance (if Polygon fails)

                        ↓

┌─────────────────────────────────────────────────────────────────────┐
│  STAGE 2: DATA NORMALIZATION & ENRICHMENT                           │
└─────────────────────────────────────────────────────────────────────┘
        │
        ├─► Parse & Clean
        │   ├─► Remove duplicates
        │   ├─► Handle missing data
        │   ├─► Normalize timestamps
        │   └─► Validate data quality
        │
        ├─► Calculate Derived Metrics
        │   ├─► Technical indicators (SMA, RS, Volume)
        │   ├─► Relative strength vs SPY
        │   ├─► Volatility measures
        │   └─► Trend alignment
        │
        └─► Enrich with Context
            ├─► Sector/Industry mapping
            ├─► Market cap tier
            ├─► Theme membership
            └─► Supply chain position

                        ↓

┌─────────────────────────────────────────────────────────────────────┐
│  STAGE 3: INTELLIGENCE PROCESSING (Multi-Signal)                    │
└─────────────────────────────────────────────────────────────────────┘
        │
        ├─► Theme Intelligence Hub
        │   ├─► Leading: Google Trends (1-3 days ahead)
        │   ├─► Confirming: Social sentiment
        │   ├─► Lagging: News volume (institutional awareness)
        │   ├─► Hard Data: Patents, contracts
        │   └─► Lifecycle: EMERGING → PEAK → DECLINING
        │
        ├─► Hard Data Scanner (Conviction)
        │   ├─► Insider Activity (25% weight)
        │   ├─► Options Flow (25% weight)
        │   ├─► Patents (12% weight)
        │   ├─► Gov Contracts (13% weight)
        │   ├─► Sentiment Validation (10% weight)
        │   └─► Technical Timing (15% weight)
        │
        ├─► News Analyzer
        │   ├─► Catalyst detection (FDA, M&A, Earnings)
        │   ├─► Sentiment scoring
        │   ├─► Event classification
        │   └─► Fact checking
        │
        ├─► Ecosystem Intelligence
        │   ├─► Supply chain mapping
        │   ├─► Wave propagation tracking
        │   ├─► Leader identification
        │   └─► Laggard detection (alpha opportunity)
        │
        └─► Options Flow Analysis
            ├─► Unusual activity detection
            ├─► Put/Call ratio
            ├─► Premium flow (calls vs puts)
            └─► Institutional positioning

                        ↓

┌─────────────────────────────────────────────────────────────────────┐
│  STAGE 4: STORY-FIRST SCORING                                       │
└─────────────────────────────────────────────────────────────────────┘
        │
        ├─► Story Quality Score (50% of total)
        │   ├─► Theme Strength (MEGA=100, STRONG=80, etc.)
        │   ├─► Theme Freshness (newer = better)
        │   ├─► Narrative Clarity (AI-scored)
        │   ├─► Institutional Interest (13F, news)
        │   └─► Supply Chain Position (leader vs laggard)
        │
        ├─► Catalyst Score (35% of total)
        │   ├─► Event Type (FDA=100, Contract=95, Upgrade=70)
        │   ├─► Recency (decay over time)
        │   ├─► Magnitude (deal size, % impact)
        │   └─► Confirmation (multiple sources)
        │
        └─► Technical Confirmation (15% of total)
            ├─► Trend Alignment (above SMAs)
            ├─► Volume Surge (>1.5x avg)
            ├─► Relative Strength (RS > 80)
            ├─► Buyability (not extended)
            └─► Squeeze Detection (BB inside KC)

                        ↓

┌─────────────────────────────────────────────────────────────────────┐
│  STAGE 5: LEARNING & OPTIMIZATION                                   │
└─────────────────────────────────────────────────────────────────────┘
        │
        ├─► Parameter Learning
        │   ├─► Bayesian optimization of 85+ parameters
        │   ├─► Thompson sampling for exploration
        │   ├─► Outcome attribution
        │   └─► Gradual rollout with validation
        │
        ├─► Theme Evolution
        │   ├─► Auto-discover new themes from news
        │   ├─► Learn member stocks from correlation
        │   ├─► Update lifecycle stages
        │   └─► Retire dead themes
        │
        ├─► Correlation Learning
        │   ├─► Lead-lag relationship detection
        │   ├─► Ecosystem graph updates
        │   └─► Supplier chain learning
        │
        └─► Accuracy Tracking
            ├─► Track prediction quality
            ├─► Monitor false positives/negatives
            ├─► A/B test parameter changes
            └─► Rollback if performance degrades

                        ↓

┌─────────────────────────────────────────────────────────────────────┐
│  STAGE 6: OUTPUT & DISTRIBUTION                                     │
└─────────────────────────────────────────────────────────────────────┘
        │
        ├─► REST API (Flask)
        │   ├─► /api/scan - Full scan results
        │   ├─► /api/ticker/<symbol> - Deep dive
        │   ├─► /api/stories - Emerging stories
        │   ├─► /api/themes - Active themes
        │   ├─► /api/conviction - Hard data scores
        │   └─► /api/briefing - AI market summary
        │
        ├─► Telegram Bot
        │   ├─► Real-time alerts (high conviction)
        │   ├─► Command interface (/scan, /ticker, /themes)
        │   ├─► Story detection (every 30 min)
        │   └─► Daily briefings
        │
        ├─► Dashboard (GitHub Pages)
        │   ├─► Static HTML generation
        │   ├─► Top opportunities table
        │   ├─► Theme heatmap
        │   ├─► Market pulse indicators
        │   └─► Auto-refresh every 6 hours
        │
        └─► CSV Export
            ├─► Daily scan results (scan_YYYYMMDD.csv)
            ├─► Retained for 30 days
            └─► Used for backtesting/learning
```

### 4.2 Cache Strategy

```
┌──────────────────────────────────────────────────────────┐
│                MULTI-TIER CACHE ARCHITECTURE              │
└──────────────────────────────────────────────────────────┘

Level 1: In-Memory LRU Cache (500 entries max)
├─► Price Data: 15 minutes TTL
├─► Options Data: 30 minutes TTL
├─► News: 30 minutes TTL
└─► Social: 1 hour TTL

Level 2: File-Based Cache (Persistent)
├─► Sector Analysis: 24 hours TTL
├─► Financials: 24 hours TTL
├─► Patents: 24 hours TTL
├─► Gov Contracts: 12 hours TTL
└─► Theme Memberships: 7 days TTL

Level 3: State Files (JSON)
├─► Scanner State: Persistent
├─► Theme History: Persistent
├─► Learned Parameters: Persistent
└─► Cluster History: Persistent

Background Prefetch:
├─► Prefetch hot stocks during off-hours
├─► Refresh expiring cache entries
└─► Warm up cache before market open
```

---

## 5. Scanning Workflow

### 5.1 Full Scan Process

```
START SCAN
    │
    ├─► Initialize AsyncScanner
    │   ├─► max_concurrent = 50
    │   ├─► Setup rate limiters (per-API)
    │   ├─► Initialize connection pool
    │   └─► Load universe (S&P 500 + NASDAQ 100)
    │
    ├─► Pre-Scan Preparation
    │   ├─► Refresh market cap cache (if stale)
    │   ├─► Load learned parameters
    │   ├─► Initialize scoring weights
    │   └─► Setup result collectors
    │
    ├─► PARALLEL EXECUTION (50 stocks at a time)
    │   │
    │   └─► For each ticker:
    │       │
    │       ├─► PHASE 1: Data Collection (parallel)
    │       │   ├─► Polygon: Price, volume, options
    │       │   ├─► Polygon: News feed
    │       │   ├─► Social: StockTwits, Reddit, X
    │       │   ├─► Hard Data: Patents, contracts, SEC
    │       │   └─► Google Trends: Search volume
    │       │
    │       ├─► PHASE 2: Technical Analysis
    │       │   ├─► Calculate SMAs (20, 50, 200)
    │       │   ├─► Relative strength vs SPY
    │       │   ├─► Volume ratio (vs 20-day avg)
    │       │   ├─► Squeeze detection
    │       │   └─► Distance from 52-week high
    │       │
    │       ├─► PHASE 3: Intelligence Processing
    │       │   ├─► Theme matching & scoring
    │       │   ├─► Catalyst detection & classification
    │       │   ├─► News sentiment analysis
    │       │   ├─► Ecosystem position identification
    │       │   └─► Options flow analysis
    │       │
    │       ├─► PHASE 4: Story Scoring
    │       │   ├─► Story Quality (50%)
    │       │   ├─► Catalyst Strength (35%)
    │       │   ├─► Technical Confirmation (15%)
    │       │   └─► Calculate final score (0-100)
    │       │
    │       └─► PHASE 5: Conviction Analysis
    │           ├─► Hard data scanner (if enabled)
    │           ├─► 6-signal conviction score
    │           └─► Risk warnings & recommendations
    │
    ├─► Post-Processing
    │   ├─► Sort by story_score (descending)
    │   ├─► Filter out low scores (<30)
    │   ├─► Deduplicate results
    │   └─► Format for output
    │
    ├─► Learning Update
    │   ├─► Track which stocks moved significantly
    │   ├─► Attribute to parameter values
    │   ├─► Update Bayesian priors
    │   └─► Save learned parameters
    │
    └─► Output Generation
        ├─► CSV export (scan_YYYYMMDD.csv)
        ├─► Update dashboard data
        ├─► Send Telegram alerts (high conviction)
        └─► Cache results for API queries

END SCAN

Performance Metrics:
├─► Total Time: ~7 minutes for 500+ stocks
├─► Per-Ticker: ~0.25 seconds average
├─► Cache Hit Rate: 60-80%
└─► API Calls: ~2000-3000 per full scan
```

### 5.2 Test Scan Process

```
TEST SCAN (10 tickers)
    │
    ├─► Hardcoded tickers: NVDA, AMD, AAPL, MSFT, META,
    │                       GOOGL, AMZN, TSLA, NFLX, CRM
    │
    ├─► Same process as Full Scan
    │   └─► But limited to 10 stocks
    │
    └─► Typical completion: 30-60 seconds
```

### 5.3 Single Ticker Analysis

```
TICKER DEEP DIVE (e.g., /ticker NVDA)
    │
    ├─► Check cache (5-minute TTL)
    │   └─► Return cached if fresh
    │
    ├─► Full data collection
    │   ├─► All data sources (same as scan)
    │   ├─► Extended time series (6 months)
    │   └─► Detailed options chain
    │
    ├─► Enhanced analysis
    │   ├─► Historical theme membership
    │   ├─► Ecosystem relationships
    │   ├─► Insider transaction history
    │   ├─► Institutional ownership changes
    │   └─► Patent activity trends
    │
    ├─► AI-Powered Insights (DeepSeek)
    │   ├─► Pattern recognition
    │   ├─► Price prediction
    │   ├─► Risk assessment
    │   └─► Trade recommendations
    │
    └─► Format response
        ├─► Story summary
        ├─► Conviction breakdown
        ├─► Factor contributions
        ├─► Warnings & risks
        └─► Entry/exit levels
```

---

## 6. Intelligence Framework

### 6.1 Theme Intelligence Multi-Signal System

```
┌────────────────────────────────────────────────────────────┐
│         THEME INTELLIGENCE HUB (Multi-Signal Fusion)        │
└────────────────────────────────────────────────────────────┘

Signal Layers (Time-Offset):

┌─────────────────────────────────────────────────────────────┐
│  LEADING INDICATORS (1-3 days ahead)                         │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Google Trends                                       │   │
│  │  • Search volume velocity                           │   │
│  │  • Regional interest                                │   │
│  │  • Related queries                                  │   │
│  │  • Weight: 40% (highest for theme discovery)       │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↓ 1-3 days later
┌─────────────────────────────────────────────────────────────┐
│  CONFIRMING INDICATORS (real-time)                           │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Social Sentiment                                    │   │
│  │  • StockTwits mentions & sentiment                  │   │
│  │  • Reddit discussion volume                         │   │
│  │  • X/Twitter buzz                                   │   │
│  │  • Weight: 30%                                      │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↓ few days later
┌─────────────────────────────────────────────────────────────┐
│  LAGGING INDICATORS (institutional awareness)                │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  News & SEC                                          │   │
│  │  • Mainstream news coverage                         │   │
│  │  • SEC filings (8-K, 13D, DEFM14A)                 │   │
│  │  • Analyst reports                                  │   │
│  │  • Weight: 20% (confirms trend is mature)          │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Hard Data Validation                                │   │
│  │  • Patent activity                                   │   │
│  │  • Government contracts                              │   │
│  │  • Insider buying                                    │   │
│  │  • Weight: 10% (long-term validation)              │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘

Theme Lifecycle States:
├─► DEAD: No signals, no movement
├─► EMERGING: Google Trends + Social starting
├─► ACCELERATING: All signals increasing
├─► PEAK: News volume maxed, euphoria warning
└─► DECLINING: Trend velocity negative, fade signal
```

### 6.2 Theme Membership Learning

```
THEME MEMBERSHIP (Learned, NOT Hardcoded)

Initial Seeds (Minimal Hardcoding):
├─► Theme Name: "AI Infrastructure"
├─► Keywords: ["AI", "artificial intelligence", "GPU", "neural"]
└─► Seed Members: [NVDA, AMD] (just 2-3 to start)

Learning Process:
    │
    ├─► Correlation Analysis
    │   ├─► Calculate 20-day rolling correlation
    │   ├─► Identify stocks moving with seed members
    │   └─► Threshold: r > 0.6 for membership
    │
    ├─► News Co-Mention
    │   ├─► Stocks frequently mentioned with seed members
    │   ├─► Shares theme keywords in news
    │   └─► Threshold: 60%+ keyword overlap
    │
    ├─► Supply Chain Analysis (AI-powered)
    │   ├─► Ask DeepSeek: "Who supplies NVDA?"
    │   ├─► Identify suppliers, customers, competitors
    │   └─► Assign roles: DRIVER, BENEFICIARY, PICKS_SHOVELS
    │
    ├─► Pattern Recognition
    │   ├─► Stocks that move 1-3 days after theme leaders
    │   ├─► "Laggard" detection (alpha opportunity)
    │   └─► Wave propagation tracking
    │
    └─► Confidence Scoring
        ├─► Multiple sources = higher confidence
        ├─► Long correlation history = higher confidence
        ├─► Store: ticker, role, confidence, source, date_added

Result: Self-expanding theme membership
├─► AI Infrastructure: NVDA, AMD, SMCI, ARM, AVGO, MRVL, etc.
├─► Each with role (DRIVER vs BENEFICIARY)
└─► Continuously updated as market evolves
```

### 6.3 Ecosystem Intelligence

```
ECOSYSTEM MAPPING & WAVE PROPAGATION

Supply Chain Hierarchy:
    │
    ├─► LEADERS (move first)
    │   ├─► Large cap, high visibility
    │   ├─► Catalyst originates here
    │   └─► Example: NVDA in AI theme
    │
    ├─► DIRECT BENEFICIARIES (move 1-3 days later)
    │   ├─► Customers, partners
    │   ├─► Directly impacted by leader success
    │   └─► Example: SMCI, DELL when NVDA reports
    │
    ├─► SUPPLIERS (move 3-7 days later) ← ALPHA HERE
    │   ├─► Provide components to leaders
    │   ├─► Market slower to recognize impact
    │   └─► Example: MRVL, ANET, ARM
    │
    └─► PERIPHERAL (move last, if at all)
        ├─► Loosely related
        ├─► May not move significantly
        └─► Lower conviction plays

Wave Propagation Tracking:
    │
    ├─► Event: NVDA beats earnings, guides up
    │
    ├─► Day 0-1: NVDA surges
    │
    ├─► Day 1-3: Direct beneficiaries rally
    │   └─► SMCI, DELL, WDAY, MSFT
    │
    ├─► Day 3-7: Suppliers catch up ← OPPORTUNITY WINDOW
    │   └─► MRVL, ANET, ARM, AVGO
    │
    └─► Day 7+: Peripheral stocks move (or don't)

Intelligence Engine:
├─► Track which stocks moved after leader event
├─► Calculate lag time (days)
├─► Learn lead-lag relationships
├─► Build ecosystem graph (directed edges)
└─► Alert: "NVDA up 10% → Watch MRVL in 3-5 days"
```

---

## 7. Scoring System

### 7.1 Story-First Scoring Formula

```
FINAL SCORE = Story Quality × 0.50
            + Catalyst Strength × 0.35
            + Technical Confirmation × 0.15

Range: 0-100 (higher = better setup)
```

### 7.2 Story Quality Component (50% weight)

```python
Story Quality Score = (
    Theme Heat × 0.40 +          # How hot is the theme?
    Freshness × 0.25 +            # How recent is the story?
    Clarity × 0.20 +              # How clear is the narrative?
    Institutional Interest × 0.15 # Are big players involved?
)

Theme Heat (0-100):
├─► MEGA themes (AI, GLP-1): 100
├─► STRONG themes (Nuclear, Defense): 80
├─► MODERATE themes (Cybersecurity): 60
├─► EMERGING themes (Robotics): 40
├─► WEAK themes: 20
└─► NO theme: 0

Freshness (0-100):
├─► New story (<7 days): 100
├─► Recent story (7-30 days): 80
├─► Ongoing story (30-90 days): 60
├─► Old story (>90 days): 30
└─► No recent catalysts: 0

Clarity (0-100):
├─► AI-scored narrative coherence
├─► Clear value proposition: 80-100
├─► Somewhat clear: 50-70
└─► Vague/confused: 0-40

Institutional Interest (0-100):
├─► 13F filings showing accumulation: +30
├─► Analyst upgrades: +20
├─► News coverage from WSJ/Bloomberg: +20
├─► Insider buying: +20
└─► Options flow (smart money): +10
```

### 7.3 Catalyst Strength Component (35% weight)

```python
Catalyst Score = (
    Event Type × 0.50 +           # What happened?
    Recency × 0.25 +              # How recent?
    Magnitude × 0.25              # How significant?
)

Event Type Scores:
├─► Tier 1 (80-100): FDA approval, Major contract (>$1B),
│                     M&A announcement, Breakthrough tech
├─► Tier 2 (50-79):  Analyst upgrade (2+ notch), Partnership,
│                     Insider buying (>$1M), Earnings beat
├─► Tier 3 (30-49):  Contract win (<$1B), New product launch,
│                     Positive news, Patent grant
└─► Tier 4 (0-29):   Minor news, No catalyst

Recency Decay:
├─► 0-3 days: 100% (full score)
├─► 3-7 days: 90%
├─► 7-14 days: 75%
├─► 14-30 days: 50%
└─► >30 days: 25%

Magnitude:
├─► Massive (transformative): 100
├─► Significant (material impact): 70
├─► Moderate (notable): 50
└─► Small (incremental): 30
```

### 7.4 Technical Confirmation Component (15% weight)

```python
Technical Score = (
    Trend Alignment × 0.35 +      # With the trend
    Volume × 0.25 +                # Unusual volume
    Relative Strength × 0.25 +     # Outperforming market
    Buyability × 0.15              # Not extended
)

Trend Alignment (0-100):
├─► Above 20, 50, 200 SMA: 100
├─► Above 20, 50 SMA: 75
├─► Above 20 SMA only: 50
└─► Below all SMAs: 0

Volume (0-100):
├─► >3x average: 100
├─► 2-3x average: 80
├─► 1.5-2x average: 60
├─► 1-1.5x average: 40
└─► <1x average: 0

Relative Strength (0-100):
├─► RS > 90: 100
├─► RS 80-90: 80
├─► RS 70-80: 60
├─► RS 60-70: 40
└─► RS < 60: 20

Buyability (0-100):
├─► Tight consolidation (squeeze): 100
├─► Pullback to SMA: 80
├─► Breaking out: 70
├─► Extended (>15% above 20 SMA): 30
└─► Parabolic (>30% above 20 SMA): 0
```

### 7.5 Score Interpretation

```
Score Ranges & Actions:

90-100: EXCEPTIONAL SETUP
├─► Strong story + Fresh catalyst + Perfect technical
├─► Action: Add to watchlist, prepare to enter
└─► Historical accuracy: 70%+ win rate

75-89: STRONG SETUP
├─► Good story + Recent catalyst + Buyable
├─► Action: Watch closely, enter on pullback
└─► Historical accuracy: 60%+ win rate

60-74: DECENT SETUP
├─► Moderate story + Some catalyst + OK technical
├─► Action: Monitor, wait for improvement
└─► Historical accuracy: 50%+ win rate

40-59: WEAK SETUP
├─► Weak story OR poor technical
├─► Action: Pass, not worth the risk
└─► Historical accuracy: <40% win rate

0-39: AVOID
├─► No story + No catalyst + Bad technical
├─► Action: Stay away
└─► Historical accuracy: <30% win rate
```

---

## 8. Learning System

### 8.1 Parameter Learning Architecture

```
┌──────────────────────────────────────────────────────────┐
│        85+ SELF-TUNING PARAMETERS (All Learned)          │
└──────────────────────────────────────────────────────────┘

Parameter Categories:

1. SCORING WEIGHTS (20 parameters)
├─► story_quality_weight: 0.50 (learned, not fixed)
├─► catalyst_weight: 0.35
├─► technical_weight: 0.15
├─► theme_heat_weight: 0.40
├─► freshness_weight: 0.25
└─► ... (all optimized from outcomes)

2. THEME DETECTION (15 parameters)
├─► correlation_threshold: 0.6
├─► news_overlap_threshold: 0.6
├─► trend_velocity_threshold: 0.3
├─► social_buzz_threshold: 50
└─► ... (dynamic based on accuracy)

3. CATALYST SCORING (12 parameters)
├─► fda_approval_score: 100
├─► major_contract_score: 95
├─► upgrade_score: 70
├─► recency_decay_rate: 0.9 per week
└─► ...

4. TECHNICAL INDICATORS (10 parameters)
├─► sma_periods: [20, 50, 200]
├─► volume_threshold: 1.5x
├─► rs_threshold: 80
└─► ...

5. CACHE TTLs (8 parameters)
├─► price_cache_ttl: 900 sec (15 min)
├─► news_cache_ttl: 1800 sec (30 min)
└─► ... (optimized for freshness vs load)

6. RISK THRESHOLDS (10 parameters)
├─► extended_threshold: 1.15 (15% above SMA)
├─► euphoria_sentiment: 0.7
├─► euphoria_news_volume: 20
└─► ...

7. ECOSYSTEM PARAMETERS (10 parameters)
├─► lag_window: 3-7 days
├─► correlation_window: 20 days
└─► ...
```

### 8.2 Learning Process Flow

```
CONTINUOUS LEARNING CYCLE

┌─────────────────────────────────────────────────────┐
│  PHASE 1: OUTCOME TRACKING                          │
└─────────────────────────────────────────────────────┘
    │
    ├─► For each stock scored:
    │   ├─► Record: score, parameters used, timestamp
    │   ├─► Track price movement (1d, 3d, 7d, 14d, 30d)
    │   └─► Store: actual_move, predicted_direction
    │
    └─► For each theme detected:
        ├─► Record: heat score, lifecycle stage
        ├─► Track: stocks in theme, correlation strength
        └─► Monitor: theme performance vs market

┌─────────────────────────────────────────────────────┐
│  PHASE 2: ATTRIBUTION                               │
└─────────────────────────────────────────────────────┘
    │
    ├─► Which parameter values led to winners?
    │   ├─► Example: story_weight=0.50 → 70% accuracy
    │   ├─► Example: story_weight=0.40 → 55% accuracy
    │   └─► Conclusion: Keep 0.50, penalize 0.40
    │
    └─► Which combinations work best?
        ├─► High story + High catalyst = 75% win rate
        ├─► High story + Low catalyst = 55% win rate
        └─► Update Bayesian priors

┌─────────────────────────────────────────────────────┐
│  PHASE 3: BAYESIAN OPTIMIZATION                     │
└─────────────────────────────────────────────────────┘
    │
    ├─► For each parameter:
    │   ├─► Maintain probability distribution
    │   ├─► Update based on outcomes (Bayes rule)
    │   └─► Narrow distribution around optimal value
    │
    ├─► Thompson Sampling:
    │   ├─► Exploration (20%): Try new values
    │   ├─► Exploitation (80%): Use known good values
    │   └─► Balance discovery vs performance
    │
    └─► Multi-Armed Bandit:
        ├─► Each parameter set = "arm"
        ├─► Pull arms based on expected reward
        └─► Learn reward distribution over time

┌─────────────────────────────────────────────────────┐
│  PHASE 4: VALIDATION                                │
└─────────────────────────────────────────────────────┘
    │
    ├─► Shadow Mode Testing:
    │   ├─► Run new parameters alongside production
    │   ├─► Compare results (no impact to users)
    │   └─► Only promote if superior
    │
    ├─► A/B Testing:
    │   ├─► Split traffic 90/10 (control/test)
    │   ├─► Monitor metrics (accuracy, win rate)
    │   └─► Gradual rollout if test wins
    │
    └─► Rollback Capability:
        ├─► Keep last 5 parameter snapshots
        ├─► Auto-rollback if accuracy drops >5%
        └─► Alert: "Parameters rolled back"

┌─────────────────────────────────────────────────────┐
│  PHASE 5: DEPLOYMENT                                │
└─────────────────────────────────────────────────────┘
    │
    ├─► Gradual Rollout:
    │   ├─► Day 1: 10% of stocks
    │   ├─► Day 2: 25% of stocks
    │   ├─► Day 3: 50% of stocks
    │   ├─► Day 4: 75% of stocks
    │   └─► Day 5: 100% (if no issues)
    │
    ├─► Audit Trail:
    │   ├─► Log every parameter change
    │   ├─► Store: old_value, new_value, reason, timestamp
    │   └─► Enable forensic analysis
    │
    └─► Performance Monitoring:
        ├─► Track accuracy continuously
        ├─► Alert if drops below baseline
        └─► Auto-revert if critical threshold breached

CYCLE REPEATS DAILY
```

### 8.3 Theme Evolution Learning

```
THEME LIFECYCLE LEARNING

Discovery:
├─► Cluster news headlines (NLP)
├─► Find emerging keyword clusters
├─► Example: "Small modular reactor" suddenly trending
└─► Create new theme candidate

Validation:
├─► Check Google Trends (is it real?)
├─► Check social mentions (building momentum?)
├─► Identify seed stocks (which tickers mentioned?)
└─► Promote to active theme if validated

Growth Tracking:
├─► Monitor signal strength over time
├─► Detect inflection points (EMERGING → ACCELERATING)
├─► Identify peak (euphoria warning)
└─► Fade detection (DECLINING)

Member Learning:
├─► Auto-expand membership via correlation
├─► Learn supply chain relationships
├─► Classify roles (DRIVER, BENEFICIARY, etc.)
└─► Continuously update as market evolves

Retirement:
├─► Dead themes (no signals for 90+ days)
├─► Archive for historical analysis
└─► Free resources for new themes
```

---

## 9. Hard Data Framework

### 9.1 Multi-Signal Conviction System

```
HARD DATA CONVICTION SCORING

┌────────────────────────────────────────────────────────┐
│  6-SIGNAL ARCHITECTURE (Weighted Combination)          │
└────────────────────────────────────────────────────────┘

Signal 1: INSIDER ACTIVITY (25% weight) ← HIGHEST
├─► Source: SEC Form 4 filings
├─► What: Director/officer buy/sell transactions
├─► Why: Management knows internal prospects
├─► Scoring:
│   ├─► >$500K buying, 2+ transactions: 80-100 (strong bullish)
│   ├─► >$200K buying: 60-80 (bullish)
│   ├─► >$1M selling, 3+ transactions: 0-30 (bearish)
│   └─► Net buying: 50-80 (slightly bullish)
├─► Leading Time: 0-3 months
└─► Cache: 1 hour

Signal 2: OPTIONS FLOW (25% weight) ← HIGHEST
├─► Source: Polygon.io options chain
├─► What: Unusual call/put activity, premium flow
├─► Why: Smart money positioning ahead of moves
├─► Scoring:
│   ├─► P/C < 0.5, call premium >$1M: 80-100 (strong bullish)
│   ├─► P/C < 0.7, call premium >$500K: 65-85 (bullish)
│   ├─► P/C > 1.5, put premium >$1M: 0-30 (bearish)
│   └─► P/C < 0.8: 55-70 (slightly bullish)
├─► Leading Time: 0-4 weeks
└─► Cache: 30 minutes

Signal 3: PATENTS (12% weight)
├─► Source: USPTO PatentsView API
├─► What: Patent filings by company
├─► Why: R&D investment signal, 6-12 months ahead
├─► Scoring:
│   ├─► YoY > 50% + hot theme: 80-100 (strong bullish)
│   ├─► YoY > 30%: 65-85 (bullish)
│   ├─► YoY > 10%: 50-70 (slightly bullish)
│   └─► YoY < -20%: 20-40 (bearish)
├─► Leading Time: 6-12 months
└─► Cache: 24 hours

Signal 4: GOV CONTRACTS (13% weight)
├─► Source: USAspending.gov API
├─► What: Federal contract awards
├─► Why: Revenue visibility 1-3 months ahead
├─► Scoring:
│   ├─► >$1B + YoY > 20%: 80-100 (strong bullish)
│   ├─► >$500M or YoY > 30%: 65-85 (bullish)
│   ├─► >$100M: 50-70 (slightly bullish)
│   └─► Minimal contracts: 40-50 (neutral)
├─► Leading Time: 1-3 months
└─► Cache: 12 hours

Signal 5: SENTIMENT (10% weight) ← VALIDATION ONLY
├─► Source: News, social, analyst reports
├─► What: Market sentiment about the stock
├─► Why: Validation, BUT warns if too high
├─► Scoring:
│   ├─► Positive + NOT euphoric: 60-80 (confirming)
│   ├─► Slightly positive: 55-65 (slightly bullish)
│   ├─► EUPHORIC (>0.7 + 20+ articles): 40 (WARNING)
│   └─► Negative: 30-50 (bearish)
├─► Leading Time: Lagging (warns if late)
└─► Cache: 30 minutes

Signal 6: TECHNICAL (15% weight) ← TIMING ONLY
├─► Source: yfinance, calculated indicators
├─► What: Setup quality for entry
├─► Why: Entry timing, NOT conviction driver
├─► Scoring:
│   ├─► Above SMAs + Squeeze + High RS: 75-100 (buyable)
│   ├─► Above SMAs + High RS: 60-75 (watchable)
│   ├─► Extended >15% above SMA: 35-50 (warning)
│   └─► Below SMAs: 20-40 (not ready)
├─► Leading Time: N/A (timing tool)
└─► Cache: 15 minutes

┌────────────────────────────────────────────────────────┐
│  CONVICTION SCORE CALCULATION                          │
└────────────────────────────────────────────────────────┘

conviction_score = (
    insider_score × 0.25 +
    options_score × 0.25 +
    patent_score × 0.12 +
    contract_score × 0.13 +
    sentiment_score × 0.10 +
    technical_score × 0.15
)

Range: 0-100

Recommendations:
├─► 75-100 + 3+ bullish signals: STRONG BUY
├─► 65-74 + 2+ bullish signals: BUY
├─► 55-64: WATCH
├─► 35-54: HOLD
└─► 0-34: AVOID

Warning Adjustments:
├─► 2+ warnings: Downgrade recommendation
│   ├─► STRONG BUY → BUY
│   └─► BUY → WATCH
└─► Warnings: extended, euphoric, bearish signals
```

### 9.2 Hard Data Workflow

```
CONVICTION ANALYSIS WORKFLOW

Input: Ticker symbol (e.g., "NVDA")
    │
    ├─► Check cache (5-minute TTL)
    │   └─► Return if fresh
    │
    ├─► PARALLEL SIGNAL FETCH (6 workers)
    │   │
    │   ├─► Worker 1: Insider Activity
    │   │   ├─► Query SEC EDGAR for Form 4
    │   │   ├─► Parse buy/sell transactions
    │   │   ├─► Calculate net activity
    │   │   └─► Score: 0-100
    │   │
    │   ├─► Worker 2: Options Flow
    │   │   ├─► Get options chain from Polygon
    │   │   ├─► Calculate P/C ratio
    │   │   ├─► Identify unusual activity
    │   │   └─► Score: 0-100
    │   │
    │   ├─► Worker 3: Patents
    │   │   ├─► Query PatentsView API
    │   │   ├─► Calculate YoY change
    │   │   ├─► Check theme alignment
    │   │   └─► Score: 0-100
    │   │
    │   ├─► Worker 4: Gov Contracts
    │   │   ├─► Query USAspending API
    │   │   ├─► Sum contract values
    │   │   ├─► Calculate MoM change
    │   │   └─► Score: 0-100
    │   │
    │   ├─► Worker 5: Sentiment
    │   │   ├─► Get news sentiment
    │   │   ├─► Check for euphoria
    │   │   ├─► Social sentiment
    │   │   └─► Score: 0-100
    │   │
    │   └─► Worker 6: Technical
    │       ├─► Calculate SMAs
    │       ├─► Detect squeeze
    │       ├─► Check if extended
    │       └─► Score: 0-100
    │
    ├─► AGGREGATE SIGNALS
    │   ├─► Apply weights (25%, 25%, 12%, 13%, 10%, 15%)
    │   ├─► Calculate weighted average
    │   ├─► Count bullish/bearish signals
    │   ├─► Collect warnings
    │   └─► Generate reasoning
    │
    ├─► DETERMINE RECOMMENDATION
    │   ├─► Score + Signal count → Base recommendation
    │   ├─► Apply warning adjustments
    │   └─► Final: STRONG BUY | BUY | WATCH | HOLD | AVOID
    │
    ├─► CACHE RESULT (5 minutes)
    │
    └─► Return ConvictionResult
        ├─► conviction_score: 78.5
        ├─► recommendation: "BUY"
        ├─► bullish_signals: 3
        ├─► bearish_signals: 0
        ├─► warnings: []
        ├─► reasoning: [
        │       "Insider: strong_bullish",
        │       "Options: bullish",
        │       "Patents: slightly_bullish"
        │   ]
        └─► signals: { full breakdown }

Typical Execution Time: 5-10 seconds (parallel)
Cache Hit Performance: <50ms
```

---

## 10. Automation Workflows

### 10.1 GitHub Actions Workflows

```
┌──────────────────────────────────────────────────────────┐
│  WORKFLOW 1: Daily Stock Scanner                         │
│  File: .github/workflows/daily_scan.yml                  │
└──────────────────────────────────────────────────────────┘

Trigger: Cron schedule
├─► 6:30 AM ET (11:30 UTC): Pre-market scan
└─► 4:30 PM ET (21:30 UTC): After-hours scan

Manual: workflow_dispatch (on-demand)

Steps:
1. Checkout repository
2. Setup Python 3.11
3. Install dependencies (yfinance, pandas, numpy, etc.)
4. Run scanner
   ├─► Command: python scanner_automation.py
   ├─► Env: TELEGRAM_BOT_TOKEN, CHAT_ID, DEEPSEEK_API_KEY
   └─► Output: scan_YYYYMMDD.csv
5. Generate dashboard
   ├─► Command: python dashboard.py
   └─► Output: docs/index.html
6. Upload artifacts (CSV, 30-day retention)
7. Commit dashboard to repo
   └─► Auto-push to GitHub Pages

Runtime: ~10-15 minutes
Cost: Free (GitHub Actions)

┌──────────────────────────────────────────────────────────┐
│  WORKFLOW 2: Dashboard Updates                           │
│  File: .github/workflows/dashboard.yml                   │
└──────────────────────────────────────────────────────────┘

Trigger:
├─► Cron: Every 6 hours during market days (Mon-Fri)
├─► Push: Changes to dashboard.py
└─► Manual: workflow_dispatch

Steps:
1. Checkout code
2. Setup Python 3.11
3. Cache pip packages (faster runs)
4. Install minimal dependencies (pandas, yfinance, requests)
5. Generate dashboard
   ├─► Env: BOT_USERNAME, DEEPSEEK_API_KEY
   └─► Output: docs/index.html
6. Commit and push
   └─► Only if changes detected

Runtime: ~3-5 minutes
Cost: Free

┌──────────────────────────────────────────────────────────┐
│  WORKFLOW 3: Story Alerts (Real-Time)                    │
│  File: .github/workflows/story_alerts.yml                │
└──────────────────────────────────────────────────────────┘

Trigger: Cron every 30 minutes during market hours
├─► 9:30 AM - 4:00 PM ET (14:00-21:00 UTC)
└─► Monday-Friday only

Manual: workflow_dispatch

Jobs:

Job 1: Story Detection (every 30 min)
├─► Steps:
│   1. Checkout code
│   2. Setup Python 3.11
│   3. Cache pip + previous state
│   4. Install dependencies
│   5. Run story detection
│      ├─► Command: python story_alerts.py stories
│      ├─► Detects: New themes heating up
│      ├─► Detects: Breaking catalysts
│      └─► Sends: Telegram alerts
│   6. Check price alerts
│      └─► Command: python story_alerts.py prices
│   7. Save state for next run
│      └─► Cache: story_state.json
└─► Runtime: ~2-3 minutes

Job 2: Earnings Alerts (daily, 9 AM ET)
├─► Conditional: Only at 9 AM ET
├─► Steps:
│   1. Checkout code
│   2. Setup Python 3.11
│   3. Install dependencies
│   4. Check earnings calendar
│      ├─► Command: python story_alerts.py earnings
│      └─► Sends: Today's earnings preview
└─► Runtime: ~1 minute

Total Executions: ~16 per day (30 min × 6.5 hours)
Cost: Free

┌──────────────────────────────────────────────────────────┐
│  WORKFLOW 4: Bot Listener                                │
│  File: .github/workflows/bot_listener.yml                │
└──────────────────────────────────────────────────────────┘

Trigger: Manual or on-demand
Purpose: Long-running Telegram bot listener
Note: Typically runs on Railway, not GitHub Actions

┌──────────────────────────────────────────────────────────┐
│  WORKFLOW 5: Universe Refresh                            │
│  File: .github/workflows/refresh_universe.yml            │
└──────────────────────────────────────────────────────────┘

Trigger: Cron (weekly, Sunday nights)
Purpose: Update S&P 500 + NASDAQ 100 universe
Steps:
1. Fetch latest constituents from Polygon
2. Filter by market cap ($300M minimum)
3. Save to cache file
4. Commit updated universe

Runtime: ~5 minutes
```

### 10.2 Railway Deployment

```
┌──────────────────────────────────────────────────────────┐
│  RAILWAY CONTINUOUS DEPLOYMENT                           │
└──────────────────────────────────────────────────────────┘

Procfile Configuration:
├─► web: python -m src.api.app
├─► bot: python main.py bot
└─► Auto-detects Flask app and starts on port 5000

Deployment Flow:
1. Push to GitHub main branch
2. Railway detects commit
3. Build environment
   ├─► Install Python 3.11
   ├─► pip install -r requirements.txt
   └─► ~2-3 minutes build time
4. Deploy services
   ├─► Web: Flask API (public URL)
   ├─► Bot: Telegram listener (background)
   └─► Health checks enabled
5. Auto-restart on failure

Environment Variables (Railway Dashboard):
├─► TELEGRAM_BOT_TOKEN
├─► TELEGRAM_CHAT_ID
├─► POLYGON_API_KEY
├─► DEEPSEEK_API_KEY
├─► PATENTSVIEW_API_KEY (optional)
└─► PORT (auto-set by Railway)

Cost: ~$5-10/month (starter plan)
Uptime: 99.9%
```

---

## 11. Integration Points

### 11.1 API Endpoints (Flask)

```
BASE URL: https://zhuanleee.github.io/stock_scanner_bot
(Dashboard - static. For API endpoints, use Modal functions or local server)
or LOCAL: http://localhost:5000

┌──────────────────────────────────────────────────────────┐
│  SCANNING ENDPOINTS                                       │
└──────────────────────────────────────────────────────────┘

GET /api/scan
├─► Full market scan (500+ stocks)
├─► Query params: ?test=true (10 stocks only)
├─► Returns: Array of scored stocks
├─► Cache: 5 minutes
└─► Response time: 30s (test) / 7min (full)

GET /api/top
├─► Top 20 stocks by story score
├─► No params
├─► Cache: 5 minutes
└─► Response time: <1s (cached)

GET /api/ticker/<symbol>
├─► Deep dive on single stock
├─► Example: /api/ticker/NVDA
├─► Returns: Full analysis + conviction
├─► Cache: 5 minutes
└─► Response time: 5-10s

POST /api/screen
├─► Custom screening filters
├─► Body: { "volume": ">2", "rs": ">80", "sector": "Technology" }
├─► Returns: Filtered results
└─► Response time: <2s

┌──────────────────────────────────────────────────────────┐
│  INTELLIGENCE ENDPOINTS                                   │
└──────────────────────────────────────────────────────────┘

GET /api/themes
├─► Active market themes
├─► Returns: Theme heat, lifecycle, members
├─► Cache: 1 hour
└─► Response time: <1s

GET /api/stories
├─► Emerging story detection
├─► Returns: New narratives, catalysts
├─► Cache: 30 minutes
└─► Response time: <2s

GET /api/conviction/<symbol>
├─► Hard data conviction analysis
├─► Example: /api/conviction/PLTR
├─► Returns: 6-signal breakdown
├─► Cache: 5 minutes
└─► Response time: 5-10s

GET /api/ecosystem/<symbol>
├─► Supply chain relationships
├─► Returns: Suppliers, customers, wave propagation
├─► Cache: 24 hours
└─► Response time: <2s

GET /api/opportunities
├─► High-conviction setups
├─► Query: ?min_score=70
├─► Returns: Filtered by conviction
└─► Response time: 10-15s

┌──────────────────────────────────────────────────────────┐
│  MARKET ANALYSIS ENDPOINTS                                │
└──────────────────────────────────────────────────────────┘

GET /api/health
├─► Market internals
├─► Returns: Breadth, VIX, put/call
├─► Cache: 15 minutes
└─► Response time: <2s

GET /api/sectors
├─► Sector rotation analysis
├─► Returns: Sector strength, rotation signals
├─► Cache: 1 hour
└─► Response time: <2s

GET /api/earnings
├─► Earnings calendar
├─► Query: ?days=7 (next 7 days)
├─► Cache: 12 hours
└─► Response time: <1s

GET /api/news
├─► Latest market news
├─► Query: ?ticker=NVDA (optional)
├─► Cache: 30 minutes
└─► Response time: <2s

┌──────────────────────────────────────────────────────────┐
│  AI ENDPOINTS                                             │
└──────────────────────────────────────────────────────────┘

GET /api/briefing
├─► AI-generated market briefing
├─► Returns: Summary, key themes, risks
├─► Cache: 1 hour
└─► Response time: 10-15s (DeepSeek call)

POST /api/predict
├─► AI price prediction
├─► Body: { "ticker": "AAPL", "horizon": "7d" }
├─► Returns: Direction, confidence, reasoning
└─► Response time: 5-10s

POST /api/coach
├─► Trading coach feedback
├─► Body: { "trade": { entry, exit, reasoning } }
├─► Returns: Feedback, score, suggestions
└─► Response time: 5-10s

┌──────────────────────────────────────────────────────────┐
│  TRADING ENDPOINTS                                        │
└──────────────────────────────────────────────────────────┘

GET /api/trades
├─► Active trades
├─► Returns: Open positions
└─► Response time: <1s

POST /api/trades
├─► Create new trade
├─► Body: { ticker, entry, size, stop, target }
└─► Returns: Trade ID

GET /api/exits/<ticker>
├─► Exit signal detection
├─► Returns: Exit reasons, recommended action
└─► Response time: <2s

┌──────────────────────────────────────────────────────────┐
│  ADMIN ENDPOINTS                                          │
└──────────────────────────────────────────────────────────┘

POST /api/refresh-universe
├─► Refresh stock universe
├─► Auth: Required
└─► Response time: 30-60s

POST /api/clear-cache
├─► Clear all caches
├─► Auth: Required
└─► Response time: <1s

GET /api/status
├─► System health
├─► Returns: Cache status, API health, uptime
└─► Response time: <1s
```

### 11.2 Telegram Bot Commands

```
┌──────────────────────────────────────────────────────────┐
│  TELEGRAM BOT: @Stocks_Story_Bot                         │
└──────────────────────────────────────────────────────────┘

Market Analysis Commands:

/scan
├─► Run full market scan
├─► Returns: Top 10 stocks
└─► Response time: 30s

/top
├─► Show top-ranked stocks
├─► Returns: Top 20 by score
└─► Response time: <5s

/ticker <SYMBOL>
├─► Deep dive on stock
├─► Example: /ticker NVDA
├─► Returns: Story, conviction, factors
└─► Response time: 10s

/screen <filters>
├─► Custom screening
├─► Example: /screen volume>2 rs>80
├─► Returns: Filtered stocks
└─► Response time: <5s

/themes
├─► Active market themes
├─► Returns: Heat map, lifecycle
└─► Response time: <5s

/stories
├─► Emerging story detection
├─► Returns: New narratives
└─► Response time: <5s

/news [ticker]
├─► Latest market news
├─► Optional: Filter by ticker
└─► Response time: <5s

/sectors
├─► Sector rotation analysis
└─► Response time: <5s

/health
├─► Market internals
├─► Returns: Breadth, fear/greed
└─► Response time: <5s

/earnings
├─► Earnings calendar
└─► Response time: <5s

AI Commands:

/briefing
├─► AI market briefing
├─► Returns: Daily summary
└─► Response time: 15s

/predict <SYMBOL>
├─► AI price prediction
├─► Example: /predict AAPL
└─► Response time: 10s

/coach
├─► Trading coach feedback
└─► Response time: 10s

/patterns
├─► Pattern detection
└─► Response time: 10s

Learning Commands:

/evolution
├─► Learning system status
└─► Response time: <5s

/weights
├─► Current scoring weights
└─► Response time: <5s

/accuracy
├─► Prediction accuracy metrics
└─► Response time: <5s

/parameters
├─► Parameter learning status
└─► Response time: <5s

Automated Alerts:

• High conviction setups (score >75)
• Theme heating alerts
• Breaking catalysts (FDA, M&A, etc.)
• Earnings previews (daily)
• Price alerts (user-configured)
```

---

## 12. Operational Procedures

### 12.1 Daily Operations

```
AUTOMATED DAILY WORKFLOW (No Manual Intervention)

Pre-Market (6:30 AM ET):
├─► GitHub Action: Daily scan triggers
├─► Scanner runs full scan (500+ stocks)
├─► Results posted to Telegram
├─► Dashboard updated
└─► CSV saved to artifacts

Market Hours (9:30 AM - 4:00 PM ET):
├─► Story alerts every 30 minutes
├─► Theme heating detection
├─► Breaking catalyst alerts
└─► Telegram notifications

After Hours (4:30 PM ET):
├─► GitHub Action: Evening scan triggers
├─► Full scan with day's data
├─► Performance analysis
├─► Learning update (parameters)
└─► Dashboard refresh

End of Day:
├─► Save scan results (CSV)
├─► Update theme history
├─► Commit learning data
└─► Generate nightly report
```

### 12.2 Weekly Maintenance

```
WEEKLY TASKS (Mostly Automated)

Sunday Night:
├─► Refresh stock universe
│   ├─► Update S&P 500 constituents
│   ├─► Update NASDAQ 100 constituents
│   └─► Filter by market cap ($300M min)
├─► Clear stale cache entries
├─► Archive old scan CSVs (>30 days)
└─► Backup learning data

Monday Morning:
├─► Review weekend news
├─► Check for new themes
└─► Validate universe updates
```

### 12.3 Error Handling

```
ERROR RECOVERY PROCEDURES

API Failures:
├─► Polygon.io down:
│   └─► Auto-fallback to yfinance
├─► SEC EDGAR rate limit:
│   └─► Exponential backoff + retry
├─► DeepSeek timeout:
│   └─► Skip AI features, continue scan
└─► Rate limit exceeded:
    └─► Queue requests, throttle

Data Quality Issues:
├─► Missing price data:
│   └─► Try fallback source, or skip ticker
├─► Corrupt cache:
│   └─► Delete entry, fetch fresh
└─► Invalid data:
    └─► Log warning, use default value

System Failures:
├─► GitHub Action timeout:
│   └─► Manual retrigger via workflow_dispatch
├─► Railway crash:
│   └─► Auto-restart (built-in)
├─► Cache corruption:
│   └─► Clear all caches endpoint
└─► Learning parameter corruption:
    └─► Rollback to last known good snapshot

Monitoring:
├─► Telegram bot health ping (every hour)
├─► API endpoint health check (every 5 min)
├─► GitHub Actions failure notifications
└─► Railway deployment status emails
```

---

## 13. Decision Trees

### 13.1 Theme Classification Decision Tree

```
THEME LIFECYCLE CLASSIFICATION

Input: Theme signals over time
    │
    ├─► Check Google Trends velocity
    │   │
    │   ├─► Velocity > 0.5 AND increasing
    │   │   └─► Candidate: EMERGING or ACCELERATING
    │   │
    │   └─► Velocity < -0.3
    │       └─► Candidate: DECLINING
    │
    ├─► Check Social Buzz
    │   │
    │   ├─► Mentions > 100/day AND increasing
    │   │   └─► Supports: ACCELERATING
    │   │
    │   ├─► Mentions > 500/day AND flat
    │   │   └─► Candidate: PEAK (warning)
    │   │
    │   └─► Mentions < 10/day
    │       └─► Candidate: DEAD
    │
    ├─► Check News Volume
    │   │
    │   ├─► Articles > 50/day
    │   │   └─► Candidate: PEAK (institutions aware)
    │   │
    │   ├─► Articles 10-50/day
    │   │   └─► Supports: ACCELERATING
    │   │
    │   └─► Articles < 5/day
    │       └─► Supports: EMERGING or DEAD
    │
    └─► FINAL CLASSIFICATION
        │
        ├─► All signals low → DEAD
        ├─► Trends up, social up, news low → EMERGING ← BEST TIME
        ├─► All signals up → ACCELERATING ← GOOD TIME
        ├─► News high, trends flat → PEAK ← WARNING
        └─► All signals down → DECLINING ← FADE

Output: Theme stage, confidence, recommendation
```

### 13.2 Conviction Recommendation Decision Tree

```
CONVICTION-BASED RECOMMENDATION

Input: 6 signal scores + warnings
    │
    ├─► Calculate conviction_score (weighted)
    │   │
    │   └─► Range: 0-100
    │
    ├─► Count bullish signals (score > 60)
    │   └─► bullish_count
    │
    ├─► Count bearish signals (score < 40)
    │   └─► bearish_count
    │
    ├─► Collect warnings
    │   ├─► extended (price >15% above SMA)
    │   ├─► euphoric (sentiment too high)
    │   └─► bearish signals
    │
    └─► DECISION LOGIC
        │
        ├─► conviction >= 75 AND bullish >= 3 AND warnings == 0
        │   └─► STRONG BUY
        │
        ├─► conviction >= 75 AND bullish >= 3 AND warnings > 0
        │   └─► BUY (downgraded from STRONG BUY)
        │
        ├─► conviction >= 65 AND bullish >= 2 AND warnings <= 1
        │   └─► BUY
        │
        ├─► conviction >= 65 AND bullish >= 2 AND warnings > 1
        │   └─► WATCH (downgraded from BUY)
        │
        ├─► conviction >= 55
        │   └─► WATCH
        │
        ├─► conviction >= 35 AND conviction < 55
        │   └─► HOLD
        │
        └─► conviction < 35 OR bearish >= 3
            └─► AVOID

Output: Recommendation + reasoning
```

### 13.3 Scan/Skip Decision Tree

```
SHOULD WE SCAN THIS TICKER?

Input: Ticker symbol
    │
    ├─► Check market cap
    │   │
    │   ├─► < $300M
    │   │   └─► SKIP (too small, illiquid)
    │   │
    │   └─► >= $300M
    │       └─► CONTINUE
    │
    ├─► Check average volume
    │   │
    │   ├─► < 100K shares/day
    │   │   └─► SKIP (too illiquid)
    │   │
    │   └─► >= 100K
    │       └─► CONTINUE
    │
    ├─► Check if in universe
    │   │
    │   ├─► In S&P 500 OR NASDAQ 100
    │   │   └─► SCAN (priority)
    │   │
    │   └─► Not in universe
    │       └─► Check theme membership
    │           │
    │           ├─► Member of hot theme
    │           │   └─► SCAN
    │           │
    │           └─► Not a member
    │               └─► SKIP
    │
    └─► Check cache
        │
        ├─► Cached AND fresh (<5 min)
        │   └─► SKIP FETCH (use cache)
        │
        └─► No cache OR stale
            └─► SCAN (fetch fresh data)

Output: SCAN or SKIP
```

---

## 14. Performance Optimization

### 14.1 Speed Optimizations

```
PERFORMANCE STRATEGIES

1. Async Everything
   ├─► aiohttp for HTTP requests
   ├─► asyncio.gather for parallel ops
   ├─► Connection pooling (shared session)
   └─► Result: 60x speedup vs sequential

2. Smart Caching
   ├─► Multi-tier (memory + file)
   ├─► TTL-based expiration
   ├─► Background prefetch
   ├─► LRU eviction (500 max entries)
   └─► Result: 60-80% cache hit rate

3. Rate Limiting
   ├─► Token bucket per API
   ├─► Respects provider limits
   ├─► Backoff on 429 errors
   └─► Result: No rate limit bans

4. Batch Processing
   ├─► Scan 50 stocks concurrently
   ├─► Group API calls
   └─► Result: Optimal throughput

5. Data Minimization
   ├─► Fetch only needed fields
   ├─► Limit time series to 6 months
   ├─► Truncate long text
   └─► Result: Less bandwidth, faster parse

6. Strategic Prefetch
   ├─► Warm cache before market open
   ├─► Prefetch universe stocks off-hours
   └─► Result: Faster real-time queries
```

### 14.2 Cost Optimizations

```
COST REDUCTION STRATEGIES

1. API Call Minimization
   ├─► Aggressive caching
   ├─► Fallback to free sources
   ├─► Batch calls where possible
   └─► Polygon.io: ~2000 calls/scan (within free tier)

2. Computation Offloading
   ├─► GitHub Actions (free for public repos)
   ├─► Railway (low-cost hosting)
   └─► Avoid expensive cloud functions

3. Storage Optimization
   ├─► File-based cache (no DB costs)
   ├─► CSV exports (simple, cheap)
   ├─► GitHub repo as storage (free)
   └─► Periodic cleanup (30-day retention)

4. AI Cost Management
   ├─► DeepSeek (10x cheaper than GPT-4)
   ├─► Cache AI responses
   ├─► Use AI sparingly (validation, not discovery)
   └─► Estimated: <$5/month for AI

Total Monthly Cost: ~$10-15
├─► Railway: $5-10
├─► DeepSeek AI: <$5
└─► Everything else: FREE
```

### 14.3 Reliability Improvements

```
RELIABILITY STRATEGIES

1. Graceful Degradation
   ├─► Primary source fails → Fallback source
   ├─► AI fails → Skip AI features, continue
   ├─► Cache fails → Fetch live (slower)
   └─► Never fully crash

2. Retry Logic
   ├─► Exponential backoff (1s, 2s, 4s, 8s)
   ├─► Max 3 retries per request
   ├─► Circuit breaker pattern
   └─► Fail fast after threshold

3. Data Validation
   ├─► Type checking on all inputs
   ├─► Range validation (prices, scores)
   ├─► Handle missing data gracefully
   └─► Log anomalies, don't crash

4. Monitoring
   ├─► Health check endpoints
   ├─► Telegram bot heartbeat
   ├─► GitHub Actions notifications
   └─► Railway status dashboard

5. Rollback Capability
   ├─► Version all parameter changes
   ├─► Keep last 5 snapshots
   ├─► Auto-rollback on accuracy drop
   └─► Manual rollback via API
```

---

## Appendix A: Data Source Details

```
┌──────────────────────────────────────────────────────────┐
│  PRIMARY DATA SOURCES                                     │
└──────────────────────────────────────────────────────────┘

1. Polygon.io (Primary)
   ├─► Price/Volume: Real-time quotes
   ├─► Options: Full chain with Greeks
   ├─► News: Curated feed
   ├─► Financials: Income, balance sheet, cash flow
   ├─► Technicals: Pre-calculated indicators
   ├─► Rate Limit: Unlimited tier
   └─► Cost: $199/month (Unlimited plan)

2. USPTO PatentsView
   ├─► Patent filings by company
   ├─► Rate Limit: 45 req/min
   ├─► Requires: Free API key
   └─► Cost: FREE

3. USAspending.gov
   ├─► Federal contract awards
   ├─► Rate Limit: Unspecified (generous)
   ├─► Requires: No API key
   └─► Cost: FREE

4. SEC EDGAR
   ├─► Form 4, 8-K, 13D, DEFM14A
   ├─► Rate Limit: 10 req/sec
   ├─► Requires: User-Agent header
   └─► Cost: FREE

5. Google Trends (pytrends)
   ├─► Search volume trends
   ├─► Rate Limit: ~30 req/hour (unofficial)
   ├─► Requires: No API key
   └─► Cost: FREE

6. StockTwits
   ├─► Social sentiment
   ├─► Rate Limit: 200 req/hour
   ├─► Requires: No API key (public)
   └─► Cost: FREE

7. Reddit API
   ├─► Subreddit mentions (WSB, stocks, etc.)
   ├─► Rate Limit: 60 req/min
   ├─► Requires: No API key (public endpoint)
   └─► Cost: FREE

8. X/Twitter (via xAI)
   ├─► Real-time tweets
   ├─► Using xAI web_search tool
   ├─► Experimental
   └─► Cost: xAI API costs

9. yfinance (Fallback)
   ├─► Price data
   ├─► Earnings estimates
   ├─► Rate Limit: ~2000 req/hour
   └─► Cost: FREE

10. DeepSeek (AI)
    ├─► Pattern recognition
    ├─► Sentiment analysis
    ├─► Ecosystem mapping
    ├─► Rate Limit: ~60 req/min
    └─► Cost: ~$0.001 per 1K tokens
```

---

## Appendix B: File Structure

```
stock_scanner_bot/
├── main.py                    # Entry point (scan, bot, api, test)
├── app.py                     # Flask app wrapper
├── requirements.txt           # Python dependencies
├── runtime.txt                # Python version (3.11)
├── Procfile                   # Railway deployment config
├── .env                       # Local environment variables (gitignored)
├── .env.example               # Example env vars
├── README.md                  # Public documentation
├── CLAUDE.md                  # AI coding guidelines
├── .gitignore                 # Git ignore rules
│
├── .github/
│   └── workflows/
│       ├── daily_scan.yml     # Pre/post market scans
│       ├── dashboard.yml      # Dashboard updates
│       ├── story_alerts.yml   # Real-time alerts
│       ├── bot_listener.yml   # Bot deployment
│       └── refresh_universe.yml # Universe updates
│
├── src/
│   ├── core/                  # Scanning engine
│   │   ├── async_scanner.py   # Main async scanner
│   │   ├── story_scoring.py   # Story-first scoring
│   │   ├── scanner_automation.py
│   │   └── screener.py
│   │
│   ├── intelligence/          # Intelligence systems
│   │   ├── theme_intelligence.py
│   │   ├── theme_discovery_engine.py
│   │   ├── hard_data_scanner.py
│   │   ├── institutional_flow.py
│   │   ├── rotation_predictor.py
│   │   └── theme_discovery.py
│   │
│   ├── data/                  # Data providers
│   │   ├── polygon_provider.py
│   │   ├── universe_manager.py
│   │   ├── cache_manager.py
│   │   ├── patents.py
│   │   ├── gov_contracts.py
│   │   ├── sec_edgar.py
│   │   ├── google_trends.py
│   │   ├── alt_sources.py
│   │   └── storage.py
│   │
│   ├── scoring/               # Scoring systems
│   │   ├── story_scorer.py
│   │   ├── signal_ranker.py
│   │   └── param_helper.py
│   │
│   ├── analysis/              # Market analysis
│   │   ├── news_analyzer.py
│   │   ├── ecosystem_intelligence.py
│   │   ├── market_health.py
│   │   ├── earnings.py
│   │   ├── sector_rotation.py
│   │   ├── backtest.py
│   │   ├── multi_timeframe.py
│   │   ├── tam_estimator.py
│   │   ├── corporate_actions.py
│   │   ├── fact_checker.py
│   │   └── relationship_graph.py
│   │
│   ├── themes/                # Theme management
│   │   ├── theme_registry.py
│   │   ├── theme_learner.py
│   │   └── fast_stories.py
│   │
│   ├── learning/              # Self-learning
│   │   ├── parameter_learning.py
│   │   ├── evolution_engine.py
│   │   └── self_learning.py
│   │
│   ├── trading/               # Trade management
│   │   ├── models.py
│   │   ├── trade_manager.py
│   │   ├── exit_scanner.py
│   │   ├── scaling_engine.py
│   │   ├── risk_advisor.py
│   │   ├── scan_integration.py
│   │   └── telegram_commands.py
│   │
│   ├── api/                   # REST API
│   │   └── app.py             # Flask API (245KB)
│   │
│   ├── bot/                   # Telegram bot
│   │   ├── bot_listener.py
│   │   └── story_alerts.py
│   │
│   ├── dashboard/             # Web dashboard
│   │   ├── dashboard.py
│   │   └── charts.py
│   │
│   ├── sync/                  # Dashboard sync
│   │   ├── sync_hub.py
│   │   ├── socketio_server.py
│   │   └── websocket_server.py
│   │
│   ├── ai/                    # AI systems
│   │   ├── deepseek_intelligence.py
│   │   ├── ai_learning.py
│   │   └── ai_ecosystem_generator.py
│   │
│   ├── sentiment/             # Sentiment analysis
│   │   └── deepseek_sentiment.py
│   │
│   └── services/              # Service layer
│       └── ai_service.py
│
├── config/                    # Configuration files
├── docs/                      # GitHub Pages dashboard
│   └── index.html
│
├── tests/                     # Test suite
│
├── data/                      # Generated data
│   ├── patents/
│   ├── gov_contracts/
│   └── ...
│
├── cache/                     # File cache
├── cache_data/                # Legacy cache
├── learning_data/             # Learned parameters
├── theme_data/                # Theme membership
├── universe_data/             # Stock universe
├── evolution_data/            # Evolution engine
├── parameter_data/            # Parameter snapshots
├── ai_data/                   # AI learning
├── user_data/                 # User preferences
│
├── utils/                     # Utility functions
│
├── scripts/                   # Standalone scripts
│
└── *.json                     # State files
    ├── scanner_state.json     # Scanner state
    ├── theme_history.json     # Theme lifecycle
    ├── learned_stories.json   # Story patterns
    ├── cluster_history.json   # Theme clusters
    ├── sector_state.json      # Sector data
    ├── weekly_stats.json      # Performance stats
    └── telegram_offset.json   # Bot offset
```

---

## Appendix C: Key Learnings & Insights

### Design Decisions That Worked:

1. **Story-First Philosophy**
   - Narratives drive 3-6 month moves
   - Technicals alone mean-revert quickly
   - Institutions allocate based on themes

2. **Hard Data > Sentiment**
   - Patents/contracts lead by months
   - Sentiment confirms but warns if too late
   - Insider buying is highest conviction signal

3. **Learning-First Architecture**
   - No hardcoded parameters (except names)
   - Bayesian optimization beats manual tuning
   - Shadow mode prevents bad deployments

4. **Async Everything**
   - 60x speedup enables real-time analysis
   - Connection pooling essential
   - Rate limiting prevents bans

5. **Multi-Signal Fusion**
   - Single signal = noise
   - 3+ confirming signals = conviction
   - Time-offset signals (leading vs lagging)

6. **Ecosystem Intelligence**
   - Leaders move first, suppliers lag 3-7 days
   - Supply chain analysis finds alpha
   - Wave propagation tracking works

### Lessons Learned:

1. **Theme Membership MUST Be Learned**
   - Hardcoded lists go stale quickly
   - Correlation + news co-mention works best
   - Roles matter (DRIVER vs BENEFICIARY)

2. **Euphoria Is a WARNING Sign**
   - High sentiment + high news = late
   - Best time: Trends up, news low
   - FOMO trades underperform

3. **Technical Timing Matters**
   - Great story + extended = wait
   - Pullback to SMA = better entry
   - Squeeze = highest probability setup

4. **Cache Aggressively**
   - 60-80% hit rate saves API costs
   - TTLs matter (price 15min, news 30min)
   - Prefetch during off-hours

5. **Error Handling Is Critical**
   - APIs fail constantly
   - Fallbacks prevent downtime
   - Graceful degradation > full crash

---

**END OF FRAMEWORK DOCUMENTATION**

This document captures the complete architecture, workflows, and operational procedures of the Stock Scanner Bot system as of 2026-01-29.

For questions or updates, refer to:
- README.md (public overview)
- CLAUDE.md (coding guidelines)
- Source code in /src/ (implementation details)
