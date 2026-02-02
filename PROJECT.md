# StockStory - Complete Project Documentation

**Version:** 3.1.0
**Last Updated:** 2026-02-02
**Status:** Production Ready

### Key Metrics
| Metric | Value |
|--------|-------|
| Codebase | 78 Python files, 56,729+ lines |
| Data Sources | 12 APIs integrated |
| Analysis Components | 38 (distributed across modules) |
| AI Specialists | 35 (coordinated by 5 Directors) |
| Scan Speed | 500+ stocks in ~7 minutes |
| Monthly Cost | $2-3 (Modal.com) |

---

## Quick Navigation

| Section | Description |
|---------|-------------|
| [1. Current State](#1-current-state) | What's deployed now |
| [2. Architecture](#2-architecture) | System design |
| [3. How It Works](#3-how-it-works) | Core workflows |
| [4. Deployment](#4-deployment) | How to deploy |
| [5. Development](#5-development) | How to develop |
| [6. Change History](#6-change-history) | What changed |
| [7. Where We Left Off](#7-where-we-left-off) | Resume point |

---

## 1. Current State

### Live URLs
- **Dashboard:** https://zhuanleee.github.io/StockStory/
- **Telegram:** [@Stocks_Story_Bot](https://t.me/Stocks_Story_Bot)
- **GitHub:** https://github.com/zhuanleee/StockStory

### Production Stack
| Component | Platform | Status | Cost |
|-----------|----------|--------|------|
| Dashboard | GitHub Pages | Active | Free |
| Backend API | Modal.com | Active | $2-3/mo |
| Telegram Bot | Modal.com | Active | Included |
| Intelligence Jobs | Modal.com | Active | Included |

### Cron Jobs (Modal)
| Job | Schedule | Purpose |
|-----|----------|---------|
| Morning Mega Bundle | 6 AM PST Mon-Fri | Daily scan + exit signals |
| Afternoon Bundle | 1 PM PST Mon-Fri | Theme discovery |
| Weekly Bundle | Sun 6 PM PST | Weekly reports |
| Monitoring | Every 6 hours | Health checks |
| Crisis Monitor | Every 15 min | Real-time alerts |

---

## 2. Architecture

### System Overview
```
Stock Scanner Bot v3.1
├── Frontend (GitHub Pages) - FREE
│   └── docs/index.html (Dashboard)
│
├── Backend (Modal.com) - $2-3/month
│   ├── modal_scanner.py (Main app, 5 cron jobs)
│   ├── modal_intelligence_jobs.py (Tier 3 features)
│   └── modal_api_v2.py (Flask API)
│
└── Data Sources (12 APIs)
    ├── Polygon.io (Stock data - primary)
    ├── xAI Grok (X/Twitter sentiment)
    ├── DeepSeek (AI analysis)
    ├── Alpha Vantage (Earnings transcripts)
    ├── Google Trends (Retail momentum)
    ├── SEC Edgar (Filings, insider)
    ├── USASpending (Gov contracts)
    ├── PatentsView (Patents)
    ├── Reddit API (Sentiment)
    ├── StockTwits (Sentiment)
    ├── Finnhub (News - optional)
    └── Yahoo Finance (Fallback)
```

### 38 Analysis Components

Components are distributed across modules and synthesized at runtime:

| Category | Components | Key Files |
|----------|-----------|-----------|
| **Technical (8)** | Price momentum, volume, RS, S/R, volatility, patterns, MA, MACD | `src/core/screener.py` |
| **Sentiment (6)** | X/Twitter, Reddit, StockTwits, trends, viral, social volume | `src/scoring/story_scorer.py` |
| **Theme (8)** | Theme strength, leadership, supply chain, catalyst, narrative, rotation, related, concentration | `src/intelligence/theme_intelligence.py` |
| **AI (4)** | Conviction, risk, opportunity, patterns | `src/ai/comprehensive_agentic_brain.py` |
| **Earnings (4)** | Tone, guidance, beat rate, surprise | `src/scoring/earnings_scorer.py` |
| **Institutional (4)** | Ownership, dark pool, options, smart money | `src/intelligence/institutional_flow.py` |
| **Fundamental (4)** | Revenue, margins, valuation, insider | `src/data/sec_edgar.py` |

**Core Scoring Weights** (from `story_scorer.py`):
- Theme Heat: 25%
- Catalyst Score: 20%
- News Momentum: 15%
- Sentiment: 15%
- Technical Confirmation: 25%

### 3-Layer Intelligence System
```
Layer 1: X Intelligence (Social Detection)
├── Real-time X search via xAI SDK
├── Crisis detection from verified accounts
├── Meme stock viral tracking
└── 5-minute caching (80% cost reduction)

Layer 2: Web Intelligence (News Verification)
├── Verifies X rumors with news sources
├── Reuters, Bloomberg, CNBC, AP, WSJ
└── Filters false alarms

Layer 3: Data Intelligence (Hard Data)
├── Google Trends (retail momentum)
├── Earnings transcripts (AI analysis)
├── SEC filings (insider, executive)
├── Government contracts
└── Patent activity
```

### 5-Director AI Brain Architecture
The `comprehensive_agentic_brain.py` (2,090 lines) coordinates all AI analysis:
```
Chief Intelligence Officer (CIO)
├── Market Regime Monitor (Context)
├── Sector Cycle Analyst (Context)
│
├── Theme Intelligence Director (7 specialists)
│   └── Theme detection, catalyst tracking, narrative analysis
│
├── Trading Intelligence Director (6 specialists)
│   └── Entry/exit timing, position sizing, risk management
│
├── Learning & Adaptation Director (8 specialists)
│   └── Pattern learning, regime detection, weight optimization
│
├── Realtime Intelligence Director (7 specialists)
│   └── Crisis detection, sentiment shifts, breaking news
│
└── Validation & Feedback Director (5 specialists)
    └── Signal verification, outcome tracking, quality checks

Total: 35 coordinated AI specialists
```

### Directory Structure
```
stock_scanner_bot/
├── README.md              # Quick start guide
├── PROJECT.md             # This file (complete docs)
├── main.py                # Entry point (scan, api, bot, dashboard)
├── app.py                 # Flask app
├── modal_scanner.py       # Modal cron jobs (5 jobs)
├── modal_intelligence_jobs.py  # Tier 3 jobs
│
├── src/                   # Source code (78 Python files)
│   ├── api/              # Flask endpoints
│   ├── ai/               # AI modules (9 files)
│   │   ├── xai_x_intelligence_v2.py    # X Intelligence
│   │   ├── web_intelligence.py         # News verification
│   │   ├── comprehensive_agentic_brain.py  # 5-Director AI
│   │   ├── deepseek_intelligence.py    # DeepSeek AI
│   │   └── model_selector.py           # Smart model selection
│   ├── core/             # Scanner engine (async_scanner, screener)
│   ├── intelligence/     # Intelligence modules (15 files)
│   │   ├── exit_signal_detector.py     # Daily exit checks
│   │   ├── meme_stock_detector.py      # Viral momentum
│   │   ├── sector_rotation_tracker.py  # Sector analysis
│   │   ├── theme_intelligence.py       # Theme detection
│   │   └── google_trends.py            # Retail momentum
│   ├── trading/          # Exit strategy & position monitor
│   ├── learning/         # RL system (evolution_engine, rl_models)
│   ├── scoring/          # Scoring (story_scorer, earnings_scorer)
│   ├── data/             # Data fetchers (12 API integrations)
│   ├── analysis/         # Ecosystem intelligence
│   ├── sentiment/        # Sentiment analysis
│   ├── themes/           # Theme system
│   ├── watchlist/        # Watchlist management
│   └── bot/              # Telegram bot commands
│
├── docs/                  # Documentation
│   ├── index.html        # Dashboard (GitHub Pages)
│   └── archive/          # Historical docs
│
├── tests/                 # Test suite
├── scripts/               # Utilities
└── config/                # Configuration
```

---

## 3. How It Works

### Daily Workflow
```
6:00 AM PST - Morning Mega Bundle
├── 1. Daily scan (1400+ stocks)
├── 2. Theme discovery
├── 3. Conviction alerts
├── 4. Options flow
├── 5. Sector rotation
├── 6. Institutional flow
├── 7. Executive commentary
├── 8. Daily briefing
└── 9. EXIT SIGNAL CHECK ← Tier 3

1:00 PM PST - Afternoon Bundle
├── Theme updates
└── Market analysis

Every 15 min - Crisis Monitor
└── Real-time X crisis detection
```

### Scanning Flow
```
Input: Stock Ticker (e.g., NVDA)
           │
           ▼
┌─────────────────────┐
│  Data Collection    │ ← 12 APIs in parallel (async, cached)
│  (polygon, xai,     │
│   trends, sec, etc) │
└─────────────────────┘
           │
           ▼
┌─────────────────────┐
│  38-Component       │ ← Distributed across modules
│  Analysis           │    (technical, sentiment, AI, etc.)
└─────────────────────┘
           │
           ▼
┌─────────────────────┐
│  5-Director Brain   │ ← CIO coordinates 35 specialists
│  Synthesis          │
└─────────────────────┘
           │
           ▼
┌─────────────────────┐
│  Story Scoring      │ ← Weight by learned params
│  (Learning System)  │    (Theme 25%, Catalyst 20%, etc.)
└─────────────────────┘
           │
           ▼
Output: Score (0-10), Signals, Recommendation
```

### Exit Strategy Flow
```
Position Entry
     │
     ▼
Daily Monitoring (6 AM)
├── Check 38 components
├── Analyze sentiment shift
├── Detect red flags
└── Calculate urgency
     │
     ▼
Exit Signal Generated?
├── Yes → Telegram Alert
│         ├── Action: SELL/HOLD/REDUCE
│         ├── Urgency: 0-10
│         └── Targets: Bull/Base/Bear
│
└── No → Continue monitoring
```

---

## 4. Deployment

### Modal Setup (Backend)

**Secret Name: `Stock_Story`** (critical - all apps use this)

```bash
# 1. Install Modal
pip install modal
modal setup

# 2. Create secrets (name MUST be Stock_Story)
modal secret create Stock_Story \
  POLYGON_API_KEY=xxx \
  XAI_API_KEY=xxx \
  DEEPSEEK_API_KEY=xxx \
  ALPHA_VANTAGE_API_KEY=xxx \
  TELEGRAM_BOT_TOKEN=xxx \
  TELEGRAM_CHAT_ID=xxx

# 3. Deploy
modal deploy modal_scanner.py
modal deploy modal_intelligence_jobs.py

# 4. Verify
modal app list
modal secret list  # Should show Stock_Story
```

### GitHub Pages Setup (Dashboard)
1. Go to repo Settings → Pages
2. Source: Deploy from branch
3. Branch: `main` / `docs` folder
4. URL: https://zhuanleee.github.io/stock_scanner_bot/

### Environment Variables

**Modal Secret Name: `Stock_Story`** (always use this name)

| Variable | Purpose | Required |
|----------|---------|----------|
| POLYGON_API_KEY | Stock data | Yes |
| XAI_API_KEY | X intelligence | Yes |
| DEEPSEEK_API_KEY | AI analysis | Yes |
| ALPHA_VANTAGE_API_KEY | Earnings | Yes |
| TELEGRAM_BOT_TOKEN | Bot auth | Yes |
| TELEGRAM_CHAT_ID | Your chat | Yes |

```bash
# View current secret
modal secret list

# Update secret (use --force to overwrite)
modal secret create Stock_Story --force \
  POLYGON_API_KEY=xxx \
  XAI_API_KEY=xxx \
  DEEPSEEK_API_KEY=xxx \
  ALPHA_VANTAGE_API_KEY=xxx \
  TELEGRAM_BOT_TOKEN=xxx \
  TELEGRAM_CHAT_ID=xxx
```

---

## 5. Development

### Local Development
```bash
# Clone
git clone https://github.com/zhuanleee/stock_scanner_bot.git
cd stock_scanner_bot

# Install
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your API keys

# Run
python main.py api        # Start server
python main.py scan       # Run scan
```

### Key Files to Know
| File | Purpose | Lines |
|------|---------|-------|
| `modal_scanner.py` | Main Modal app (5 cron jobs) | 2,090 |
| `modal_intelligence_jobs.py` | Tier 3 features (exit/meme/sector) | 370 |
| `src/ai/comprehensive_agentic_brain.py` | 5-Director AI system | 2,090 |
| `src/ai/xai_x_intelligence_v2.py` | X Intelligence with caching | 400+ |
| `src/ai/web_intelligence.py` | News verification layer | 200+ |
| `src/intelligence/exit_signal_detector.py` | Daily exit checks | 300+ |
| `src/intelligence/meme_stock_detector.py` | Viral momentum detection | 250+ |
| `src/intelligence/sector_rotation_tracker.py` | Sector analysis | 200+ |
| `src/core/async_scanner.py` | Main scanning engine | 1,000+ |
| `src/scoring/story_scorer.py` | Core scoring (5 weights) | 800+ |
| `src/scoring/earnings_scorer.py` | Earnings analysis | 400+ |
| `src/trading/exit_analyzer.py` | 38-component exit analysis | 1,050 |
| `src/data/polygon_provider.py` | Stock data fetcher | 600+ |

### Adding New Features
1. Create module in `src/`
2. Add API endpoint in `src/api/`
3. Add Telegram command in bot
4. Update dashboard if needed
5. Add tests
6. Deploy to Modal

### Testing
```bash
pytest                    # All tests
pytest tests/unit/        # Unit only
pytest tests/integration/ # Integration only

# Test specific Tier 3 feature
modal run modal_intelligence_jobs.py::daily_exit_signal_check
modal run modal_intelligence_jobs.py::daily_meme_stock_scan
modal run modal_intelligence_jobs.py::weekly_sector_rotation_analysis
```

---

## 6. Change History

### Version Timeline
| Version | Date | Major Changes |
|---------|------|---------------|
| 3.1.0 | 2026-02-02 | Migrated to Modal + GitHub Pages |
| 3.0.0 | 2026-02-02 | Tier 3 Intelligence (exit/meme/sector) |
| 2.0.0 | 2026-01-29 | Exit strategy, Dashboard visualizations |
| 1.5.0 | 2026-01-25 | Learning system, Watchlist |
| 1.0.0 | 2026-01-20 | Core scanner, Telegram bot |

### Cost Evolution
| Date | Stack | Monthly Cost |
|------|-------|--------------|
| 2026-02-02 | Modal + GitHub Pages | **$2-3** |
| 2026-02-02 | DO + Modal | $7-8 |
| 2026-01-29 | DigitalOcean | $5 |
| 2026-01-25 | Railway | $10 |

### Deployment History
- **2026-02-02**: Migrated from DigitalOcean to Modal + GitHub Pages
- **2026-01-29**: Migrated from Railway to DigitalOcean
- **2026-01-10**: Initial deployment on Railway

### Recent Optimizations (2026-02-02)
- **Caching**: 5-min TTL, 80% fewer API calls
- **Batch search**: 50 tickers per query (97% reduction)
- **Quality filters**: Dynamic (no fixed influencer lists)
- **Smart models**: Auto-switch reasoning/non-reasoning
- **Cost**: $5-8 → $2-3/month (60% reduction)

---

## 7. Where We Left Off

### Last Session: 2026-02-02

**What Was Done:**
1. Deployed Tier 3 Intelligence System to Modal
2. Migrated from DigitalOcean to Modal + GitHub Pages
3. Optimized X Intelligence with caching + quality filters
4. Consolidated documentation from 150+ files to 15 active files
5. Created this PROJECT.md as single source of truth
6. Forensic verified: Documentation matches actual codebase (97.5% → 100%)

**Current Status:**
- All systems operational
- Dashboard live at GitHub Pages
- Backend running on Modal (5/5 cron slots)
- Telegram bot active (@Stocks_Story_Bot)
- 78 Python files, 56,729+ lines of code
- 12 API integrations active

### Known Limitations
1. **Modal Cron Limit**: 5 jobs max (using 5/5)
   - Meme scanner and sector rotation are manual triggers
2. **Holdings List**: Currently hardcoded
   - TODO: Integrate with portfolio tracking
3. **Options Dashboard**: Backend ready, frontend pending

### Next Steps (Optional)
- [ ] Auto-integrate meme scanner into afternoon bundle
- [ ] Auto-integrate sector rotation into weekly bundle
- [ ] Dynamic holdings list from portfolio
- [ ] Options dashboard integration

### How to Continue
1. Read this PROJECT.md for context
2. Check Modal logs: `modal app logs stock-scanner`
3. Test changes locally: `python main.py api`
4. Deploy: `modal deploy modal_scanner.py`

---

## Quick Reference

### Telegram Commands
```
/scan NVDA     - Analyze stock
/top10         - Top stocks
/exit NVDA     - Exit signals
/exitall       - All positions
/watch add X   - Add to watchlist
/trends NVDA   - Google Trends
/earnings NVDA - Earnings analysis
/status        - System health
```

### Modal Commands
```bash
modal app list                    # List apps
modal app logs stock-scanner      # View logs
modal run modal_scanner.py::test  # Test function
modal deploy modal_scanner.py     # Deploy
```

### Git Workflow
```bash
git add .
git commit -m "feat: Description"
git push origin main
# Auto-deploys to GitHub Pages
# Modal needs manual deploy
```

---

## Automatic Change Logging

Changes are **automatically logged** to `CHANGES.md`:

### Git Commits (Automatic)
Every git commit is auto-logged via post-commit hook:
```bash
# Setup (run once)
./scripts/setup-hooks.sh

# Then every commit auto-updates CHANGES.md
git commit -m "feat: Add new feature"
# → CHANGES.md updated automatically
```

### Session Logging (Manual)
Log Claude session summaries:
```bash
./scripts/log-session.sh "Added exit strategy system"
```

### View Change History
```bash
# View recent changes
cat CHANGES.md

# Or in git
git log --oneline -20
```

---

**This document is the single source of truth for the project.**
**Update this file when making significant changes.**
**CHANGES.md is auto-updated on every commit.**
