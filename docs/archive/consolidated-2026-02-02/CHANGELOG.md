# Changelog

All notable changes to Stock Scanner Bot are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Pending
- Options integration dashboard components

---

## [3.1.0] - 2026-02-02

### Changed - Deployment Migration 🚀
**DigitalOcean → Modal + GitHub Pages**

**Why Migrated:**
- Simplified architecture (all backend on Modal)
- Cost reduction ($5/mo → $0/mo for dashboard)
- Better integration with existing Modal jobs
- Free static hosting via GitHub Pages

**New Stack:**
| Component | Platform | Cost |
|-----------|----------|------|
| Intelligence Jobs | Modal.com | $2-3/month |
| Crisis Monitoring | Modal.com | Included |
| Telegram Bot | Modal.com | Included |
| Dashboard | GitHub Pages | Free |

**Live URLs:**
- **Dashboard:** https://zhuanleee.github.io/stock_scanner_bot/
- **Telegram:** [@Stocks_Story_Bot](https://t.me/Stocks_Story_Bot)

### Documentation Updated
- Updated README.md with new deployment stack
- Updated all guides to remove DigitalOcean references
- Created DEPLOYMENT_STATUS.md with current production state
- Updated TELEGRAM_SETUP_GUIDE.md for Modal deployment

---

## [3.0.0] - 2026-02-02

### Added - Tier 3 Intelligence System 🧠
**3-Layer Verification System:**
- Layer 1: X Intelligence (social detection with real X search)
- Layer 2: Web Intelligence (news verification from Reuters, Bloomberg, CNBC, AP, WSJ)
- Layer 3: Data Intelligence (market data and fundamentals)

**Exit Signal Detection (Daily 6 AM PST):**
- Monitors all holdings for red flags (lawsuits, fraud, investigations)
- Detects sentiment reversals (bullish → bearish in 24h)
- Web-verified concerns with multi-source confirmation
- Automatic exit recommendations with confidence scores
- Telegram alerts for critical exits

**Meme Stock Scanner (Daily 2 PM PST):**
- Scans 150+ tickers for viral momentum
- Detects unusual mention volume spikes
- Identifies short squeeze signals and retail coordination
- Meme keyword detection (diamond hands, apes, moon, etc.)
- Early entry alerts before explosion

**Sector Rotation Tracker (Weekly Sunday 8 PM PST):**
- Tracks sentiment across 10 market sectors
- Identifies rotation signals (ROTATE_INTO, ROTATE_OUT)
- Overweight/underweight recommendations
- Weekly sector strength reports via Telegram

**Smart Model Selection:**
- Auto-switches between reasoning and non-reasoning models
- Reasoning for critical decisions (crisis, exits, red flags)
- Non-reasoning for speed (meme scanning, batch processing)
- Same cost, optimized for speed vs accuracy trade-off

### Optimized
**Cost Reduction (60%):** $5-8/month → $2-3/month
- 5-minute caching layer (80% fewer repeated API calls)
- Dynamic quality filters (no fixed influencer lists)
- Batch search (50 tickers per query for meme scanner)
- Tiered search strategy by feature importance

**Quality Improvements:**
- Verified account filtering for accuracy-critical features
- Engagement thresholds (10-100+ likes/retweets)
- Follower count requirements (1K-5K+ for quality)
- Prompt-based filtering (works with xAI SDK constraints)

### Changed
- `xai_x_intelligence_v2.py`: Added caching, quality filters, batch search
- `exit_signal_detector.py`: Uses verified accounts (5K+ followers, 20+ engagement)
- `meme_stock_detector.py`: Batch search optimization (150 tickers → 3 queries)
- `sector_rotation_tracker.py`: Quality filters (1K+ followers, 10+ engagement)

### Files Added
- `src/ai/web_intelligence.py` - Web news verification layer
- `src/ai/model_selector.py` - Smart model selection
- `src/intelligence/exit_signal_detector.py` - Daily exit monitoring
- `src/intelligence/meme_stock_detector.py` - Viral momentum detection
- `src/intelligence/sector_rotation_tracker.py` - Sector sentiment tracking
- `modal_intelligence_jobs.py` - Tier 3 Modal cron jobs

---

## [2.0.0] - 2026-01-29

### Added - Exit Strategy System 🎯
**38-Component Exit Analysis:**
- Dynamic price targets (bull/base/bear cases)
- Exit urgency levels (0-10 scale)
- Real-time Telegram alerts for critical exits
- Automated risk management with trailing stops

**Exit Analyzer Features:**
- Comprehensive position health scoring
- Multi-factor exit signal detection
- Trade journal with AI insights
- Performance tracking and improvement

### Added - Dashboard Intelligence Visualizations 📊
**7 New Intelligence Cards:**
- X/Twitter sentiment chart (real-time)
- Google Trends breakouts
- Government contracts tracking
- Patent activity analysis
- Supply chain visualizations
- Catalyst source distribution
- Real-time data updates

### Fixed
- Dashboard serving issues (forensic analysis complete)
- All 38 components verified working
- API endpoint routing
- Static file serving

### Changed
- Migrated from Railway to DigitalOcean App Platform
- Reduced deployment cost ($10/mo → $5/mo)
- *(Note: DigitalOcean deprecated in v3.1.0, now using Modal + GitHub Pages)*

---

## [1.5.0] - 2026-01-25

### Added - Learning System 🤖
**6-Component Adaptive Learning:**
- Reinforcement learning for component weights
- Regime detection (bull/bear/choppy markets)
- Performance tracking and improvement
- Trade journal with AI insights

**Learning Dashboard:**
- Real-time weight visualization
- Performance metrics over time
- Regime detection display
- Trade history analysis

### Added - Watchlist System 📋
- Add/remove stocks to watchlist
- Periodic health checks (every 4 hours)
- Position tracking with scores
- Telegram alerts for watchlist changes

---

## [1.0.0] - 2026-01-20

### Added - Core Scanner 🔍
**38-Component Analysis:**
- Technical indicators (8 components)
- Sentiment analysis (6 components)
- Theme/catalyst detection (8 components)
- AI analysis (4 components)
- Earnings analysis (4 components)
- Institutional flow (4 components)
- Fundamentals (4 components)

**Data Sources (10):**
- Polygon.io - Real-time stock data
- Alpha Vantage - Earnings transcripts
- xAI Grok - X/Twitter sentiment
- DeepSeek - AI analysis
- Google Trends - Retail momentum
- SEC Edgar - Filings and insider trading
- USASpending.gov - Government contracts
- PatentsView - Patent activity
- Reddit API - Social sentiment
- StockTwits API - Trading sentiment

### Added - Telegram Bot Interface 📱
**Commands:**
- `/scan` - Full market scan
- `/top10` - Top 10 stocks
- `/trends` - Google Trends analysis
- `/exec` - Executive commentary
- `/earnings` - Earnings analysis
- `/sympathy` - Related stocks (supply chain)

### Added - Web Dashboard 🌐
**Features:**
- Live dashboard (now at https://zhuanleee.github.io/stock_scanner_bot/)
- Overview, Scans, Intelligence, Watchlist, Trades, Learning tabs
- Real-time updates
- Interactive charts with Chart.js

### Added - Infrastructure 🏗️
- Flask API backend
- Modal.com serverless deployment
- Telegram webhook integration
- Data caching layer
- Error handling and logging

---

## [0.1.0] - 2026-01-10

### Added - Initial Prototype
- Basic stock scanner
- Polygon data integration
- Simple scoring algorithm
- Command-line interface

---

## Deployment History

### Current Stack (2026-02-02)
**Modal.com + GitHub Pages**

| Component | Platform | Status | Cost |
|-----------|----------|--------|------|
| Intelligence Jobs | Modal.com | ✅ Active | $2-3/month |
| Telegram Bot | Modal.com | ✅ Active | Included |
| Dashboard | GitHub Pages | ✅ Active | Free |

**Live URLs:**
- Dashboard: https://zhuanleee.github.io/stock_scanner_bot/
- Telegram: @Stocks_Story_Bot

### DigitalOcean (Deprecated)
- **2026-01-29 to 2026-02-02**: Dashboard + API hosting
- **Migrated to**: GitHub Pages (dashboard) + Modal (backend)
- **Reason**: Consolidate all backend on Modal, free dashboard hosting

### Railway (Deprecated)
- **2026-01-10 to 2026-01-29**: Initial deployment
- **Migrated to**: DigitalOcean
- **Reason**: Cost ($10/mo) and reliability issues

---

## Cost Evolution

| Date | Platform | Features | Monthly Cost |
|------|----------|----------|--------------|
| 2026-02-02 | Modal + GitHub Pages | Full + Tier 3 | **$2-3** |
| 2026-02-02 | DO + Modal | Full + Tier 3 | $7-8 |
| 2026-01-29 | DigitalOcean | Full system | $5 |
| 2026-01-25 | Railway | Learning added | $10 |
| 2026-01-20 | Railway | Core scanner | $10 |
| 2026-01-10 | Local | Prototype | $0 |

**Current Total**: $2-3/month (Modal only, GitHub Pages is free)

---

## Breaking Changes

### v3.1.0
- **Deployment platform changed** from DigitalOcean to Modal + GitHub Pages
- Dashboard now at https://zhuanleee.github.io/stock_scanner_bot/
- All backend services consolidated on Modal

### v3.0.0
- **Modal deployment required** for Tier 3 features
- New environment variables needed: `XAI_API_KEY` in Modal secrets
- Cron jobs changed (added 3 new jobs)

### v2.0.0
- **Deployment platform changed** from Railway to DigitalOcean
- New webhook URL required for Telegram
- Environment variables need to be re-set in DigitalOcean

### v1.5.0
- **New data directory structure** for learning system
- Persistent volume required for learning state

---

## Feature Comparison

| Feature | v1.0 | v1.5 | v2.0 | v3.0 |
|---------|------|------|------|------|
| Core Scanner | ✅ | ✅ | ✅ | ✅ |
| 38 Components | ✅ | ✅ | ✅ | ✅ |
| Telegram Bot | ✅ | ✅ | ✅ | ✅ |
| Dashboard | ✅ | ✅ | ✅ | ✅ |
| Learning System | ❌ | ✅ | ✅ | ✅ |
| Watchlist | ❌ | ✅ | ✅ | ✅ |
| Exit Strategy | ❌ | ❌ | ✅ | ✅ |
| Intelligence Viz | ❌ | ❌ | ✅ | ✅ |
| 3-Layer Verification | ❌ | ❌ | ❌ | ✅ |
| Exit Signals | ❌ | ❌ | ❌ | ✅ |
| Meme Detection | ❌ | ❌ | ❌ | ✅ |
| Sector Rotation | ❌ | ❌ | ❌ | ✅ |
| Smart Models | ❌ | ❌ | ❌ | ✅ |

---

## Known Issues

### v3.0.0
- Modal deployment requires manual user action (CLI not in sandbox)
- Options dashboard integration pending

### v2.0.0
- Options chain data available but UI pending

---

## Roadmap

### v3.1.0 (Planned)
- [ ] Options dashboard integration
- [ ] Options flow alerts
- [ ] Max pain calculator
- [ ] Greeks visualization

### v4.0.0 (Future)
- [ ] Multi-timeframe analysis
- [ ] Strategy backtesting
- [ ] Portfolio optimization
- [ ] Risk/reward calculator

---

**For detailed deployment instructions, see:**
- [Deployment Status](docs/deployment/DEPLOYMENT_STATUS.md)
- [Modal Deployment](docs/deployment/MODAL_DEPLOYMENT.md)
- [Telegram Setup](docs/guides/TELEGRAM_SETUP_GUIDE.md)
- [Quick Start Guide](README.md)
