# Stock Scanner Bot 📈

**AI-powered stock scanner with 38-component analysis, learning system, and Telegram bot interface.**

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Modal](https://img.shields.io/badge/Deployed-Modal-6366F1)](https://modal.com)

> **Live Dashboard:** https://zhuanleee.github.io/stock_scanner_bot/
> **Telegram Bot:** [@Stocks_Story_Bot](https://t.me/Stocks_Story_Bot)
>
> **Complete Documentation:** See [PROJECT.md](PROJECT.md) for architecture, workflows, and where we left off.

---

## 🎯 Overview

Stock Scanner Bot is a sophisticated stock analysis system that combines:
- **38 data components** across technical, sentiment, fundamental, and AI analysis
- **10 data sources** including Polygon, Alpha Vantage, xAI, DeepSeek, Google Trends
- **6-component learning system** that adapts to market conditions
- **Exit strategy analyzer** with dynamic price targets and urgency levels
- **Real-time Telegram alerts** for trades and exits
- **Interactive dashboard** with 7 intelligence visualizations

---

## ✨ Key Features

### 📊 Market Analysis
- **Real-time scanning** of 1400+ liquid stocks
- **Story-first methodology** - finds stocks with compelling narratives
- **Theme detection** - identifies emerging market themes
- **Supply chain analysis** - maps relationships between stocks

### 🧠 3-Layer Intelligence System (NEW!)
**Layer 1: X/Twitter Intelligence** (Social Detection)
- Real-time X sentiment via xAI Grok with real X search
- Crisis detection from verified news accounts
- Meme stock viral momentum tracking
- Dynamic quality filters (verified accounts, engagement thresholds)

**Layer 2: Web Intelligence** (News Verification)
- Verifies X rumors with Reuters, Bloomberg, CNBC, AP, WSJ
- Filters false alarms with authoritative sources
- Company news and red flag detection

**Layer 3: Data Intelligence** (Market Data)
- Google Trends retail momentum tracking
- Earnings call analysis with AI-powered transcript analysis
- Executive commentary aggregation from SEC filings
- Government contracts and patent activity tracking
- Institutional flow detection

### 🎯 Exit Strategy
- **38-component exit analysis** for every position
- **Dynamic price targets** (bull/base/bear cases)
- **Exit urgency levels** (0-10 scale)
- **Telegram alerts** for critical exits
- **Automated risk management** with trailing stops

### 🚨 Tier 3 Intelligence Features (NEW!)
**Daily Exit Signal Detection** (6 AM PST)
- Monitors all holdings for red flags and sentiment shifts
- Web-verified concerns with multi-source confirmation
- Automatic exit recommendations with confidence scores

**Daily Meme Stock Scanning** (2 PM PST)
- Scans 150+ tickers for viral momentum
- Catches early meme moves before explosion
- Short squeeze and retail coordination detection

**Weekly Sector Rotation** (Sunday 8 PM PST)
- Tracks sentiment across 10 market sectors
- Identifies rotation signals (into/out of sectors)
- Overweight/underweight recommendations

**Cost:** $2-3/month (60% optimized with caching + quality filters)

### 🤖 Learning System
- **Adaptive component weights** based on performance
- **Regime detection** (bull/bear/choppy markets)
- **Performance tracking** and improvement over time
- **Trade journal** with AI insights

---

## 🚀 Quick Start

### 1. Clone Repository
```bash
git clone https://github.com/zhuanleee/stock_scanner_bot.git
cd stock_scanner_bot
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment
```bash
cp .env.example .env
# Edit .env and add your API keys
```

Required API keys:
- `POLYGON_API_KEY` - Stock data (free tier available)
- `TELEGRAM_BOT_TOKEN` - Telegram bot
- `TELEGRAM_CHAT_ID` - Your Telegram chat ID
- `XAI_API_KEY` - X/Twitter sentiment analysis
- `DEEPSEEK_API_KEY` - AI analysis
- `ALPHA_VANTAGE_API_KEY` - Earnings transcripts

### 4. Run Locally
```bash
# Start Flask API and dashboard
python main.py api

# Or run a scan
python main.py scan

# View help
python main.py --help
```

### 5. Access Dashboard
Open browser: http://localhost:5000

---

## 📱 Telegram Bot

### Setup
1. Get your Chat ID:
   ```bash
   python scripts/deployment/get_chat_id.py
   ```

2. Set environment variables in `.env`:
   ```bash
   TELEGRAM_BOT_TOKEN=your_token
   TELEGRAM_CHAT_ID=your_chat_id
   ```

3. Start the bot:
   ```bash
   python main.py api
   ```

### Available Commands

#### Scanning
```
/scan              - Full market scan
/scan NVDA         - Scan specific ticker
/top10             - Top 10 stocks
```

#### Intelligence
```
/trends NVDA       - Google Trends analysis
/exec NVDA         - Executive commentary
/earnings NVDA     - Earnings analysis
/sympathy NVDA     - Related stocks (supply chain)
```

#### Trading & Watchlist
```
/watch add NVDA    - Add to watchlist
/watch list        - View watchlist
/trades            - Trade history
```

#### Exit Strategy (NEW!)
```
/exit NVDA         - Check exit signals
/exitall           - Monitor all positions
/targets NVDA      - Show price targets
```

#### Learning System
```
/weights           - Component weights
/stats             - Learning statistics
/status            - System health
```

---

## 🏗️ Architecture

```
stock_scanner_bot/
├── src/                    # Source code
│   ├── api/               # Flask API endpoints
│   ├── ai/                # AI intelligence (xAI, DeepSeek)
│   │   ├── xai_x_intelligence_v2.py   # X/Twitter intelligence
│   │   ├── web_intelligence.py        # Web news verification
│   │   └── model_selector.py          # Auto model selection
│   ├── core/              # Core scanner logic
│   ├── intelligence/      # Intelligence modules
│   │   ├── exit_signal_detector.py    # Daily exit monitoring
│   │   ├── meme_stock_detector.py     # Viral momentum detection
│   │   └── sector_rotation_tracker.py # Sector analysis
│   ├── trading/           # Exit strategy & position monitoring
│   ├── learning/          # Learning system
│   ├── scoring/           # Scoring engines
│   └── data/              # Data fetchers
├── docs/                  # Documentation
│   ├── guides/           # User guides
│   ├── deployment/       # Deployment docs
│   └── api/              # API documentation
├── tests/                 # Test suite
│   ├── unit/             # Unit tests
│   └── integration/      # Integration tests
├── scripts/               # Utility scripts
│   ├── deployment/       # Setup scripts
│   └── verification/     # Health checks
├── modal_scanner.py       # Modal cron jobs (crisis monitoring)
├── modal_intelligence_jobs.py  # Tier 3 jobs (exit/meme/sector)
├── data/                  # Data storage (gitignored)
│   ├── cache/            # API response cache
│   ├── learning/         # Learning system state
│   └── user/             # User data
└── main.py               # Entry point
```

---

## 📊 38 Components Analyzed

### Technical (8)
Price momentum, volume profile, relative strength, support/resistance, volatility, price patterns, MA health, MACD

### Sentiment (6)
X/Twitter, Reddit, StockTwits, sentiment trends, viral activity, social volume

### Theme/Catalyst (8)
Theme strength, leadership, supply chain, catalyst freshness, narrative, sector rotation, related performance, concentration

### AI Analysis (4)
AI conviction, risk assessment, opportunity score, pattern recognition

### Earnings (4)
Transcript tone, guidance direction, beat rate, surprise trend

### Institutional (4)
Ownership changes, dark pool activity, options flow, smart money indicators

### Fundamental (4)
Revenue growth, margin trends, valuation, insider trading

---

## 🎨 Dashboard

**Live Dashboard:** https://zhuanleee.github.io/stock_scanner_bot/

### Features
- **Overview** - Market summary and top picks
- **Scans** - Full scan results with filtering
- **Intelligence** - 7 data visualizations:
  - X/Twitter sentiment chart
  - Google Trends breakouts
  - Government contracts tracking
  - Patent activity analysis
  - Supply chain visualizations
  - Catalyst source distribution
  - Real-time data updates
- **Watchlist** - Position tracking with health scores
- **Trades** - Portfolio management
- **Learning** - System performance metrics
- **Exit Targets** - Dynamic exit analysis (coming soon)

---

## 🚢 Deployment

### Current Production Stack

| Component | Platform | Cost |
|-----------|----------|------|
| **Intelligence Jobs** | Modal.com | $2-3/month |
| **Dashboard** | GitHub Pages | Free |
| **Telegram Bot** | Modal.com | Included |

### Option 1: Modal (All Backend Services)

**Primary deployment platform** for all intelligence jobs and API.

1. **Install Modal CLI:**
   ```bash
   pip install modal
   modal setup
   ```

2. **Create Modal secrets:**
   ```bash
   modal secret create Stock_Story \
     POLYGON_API_KEY=your_key \
     XAI_API_KEY=your_key \
     DEEPSEEK_API_KEY=your_key \
     ALPHA_VANTAGE_API_KEY=your_key \
     TELEGRAM_BOT_TOKEN=your_token \
     TELEGRAM_CHAT_ID=your_id
   ```

3. **Deploy all services:**
   ```bash
   # Main crisis monitoring (hourly)
   modal deploy modal_scanner.py

   # Tier 3 intelligence jobs (daily/weekly)
   modal deploy modal_intelligence_jobs.py
   ```

4. **Verify deployment:**
   ```bash
   modal app list  # Should show 6 cron jobs
   ```

**Cost:** $2-3/month (with optimizations)
**Features:** Auto-scaling, serverless, cron jobs

### Option 2: GitHub Pages (Dashboard)

**Static dashboard** hosted on GitHub Pages (free).

1. **Enable GitHub Pages:**
   - Go to repo Settings → Pages
   - Source: Deploy from branch
   - Branch: `main` / `docs` folder

2. **Dashboard URL:**
   ```
   https://zhuanleee.github.io/stock_scanner_bot/
   ```

**Cost:** Free
**Features:** Static hosting, auto-deploy on push

See [Deployment Status](docs/deployment/DEPLOYMENT_STATUS.md) for current status.

---

## 📖 Documentation

### User Guides
- [Exit Strategy Guide](docs/guides/EXIT_STRATEGY_GUIDE.md) - How to use exit analysis
- [Watchlist Quick Start](docs/guides/WATCHLIST_QUICK_START.md) - Watchlist features
- [Learning System Guide](docs/guides/LEARNING_QUICK_START.md) - How learning works
- [Telegram Setup](docs/guides/TELEGRAM_SETUP_GUIDE.md) - Bot configuration

### Deployment
- [Modal Deployment](docs/deployment/MODAL_DEPLOYMENT.md)
- [Deployment Status](docs/deployment/DEPLOYMENT_STATUS.md)

### Development
- [Implementation Summary](docs/development/IMPLEMENTATION_SUMMARY.md)
- [Claude Guidelines](docs/development/CLAUDE.md)

---

## 🧪 Testing

```bash
# Run all tests
pytest

# Run specific test category
pytest tests/unit/
pytest tests/integration/

# Run with coverage
pytest --cov=src --cov-report=html
```

---

## 🛠️ Development

### Project Structure
```python
# Main entry point
python main.py api      # Start API server
python main.py scan     # Run market scan
python main.py --help   # Show all commands

# Module imports
from src.core.async_scanner import AsyncScanner
from src.intelligence.x_intelligence import XIntelligence
from src.trading.exit_analyzer import ExitAnalyzer
from src.learning.rl_models import ReinforcementLearning
```

### Adding New Features
1. Create module in appropriate `src/` subdirectory
2. Add API endpoint in `src/api/`
3. Add Telegram command in `src/bot/`
4. Update dashboard in `docs/index.html`
5. Add tests in `tests/`
6. Update documentation in `docs/`

---

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details

---

## 🙏 Acknowledgments

**Data Sources:**
- Polygon.io - Stock market data
- Alpha Vantage - Earnings transcripts
- xAI Grok - X/Twitter sentiment
- DeepSeek - AI analysis
- Google Trends - Retail momentum
- SEC Edgar - Filings and insider trading
- USASpending.gov - Government contracts
- PatentsView - Patent activity

**Technologies:**
- Python 3.11
- Flask (API)
- Chart.js (Dashboard visualizations)
- Telegram Bot API
- Modal.com (Serverless deployment)
- GitHub Pages (Dashboard hosting)

---

## 📞 Support

**Issues:** https://github.com/zhuanleee/stock_scanner_bot/issues
**Telegram Bot:** [@Stocks_Story_Bot](https://t.me/Stocks_Story_Bot)
**Dashboard:** https://zhuanleee.github.io/stock_scanner_bot/

---

## 🔄 Recent Updates

### 2026-02-02: Tier 3 Intelligence System
- ✅ **3-layer verification** (X + Web + Data intelligence)
- ✅ **Exit signal detection** (daily morning checks before market)
- ✅ **Meme stock scanner** (daily afternoon viral detection)
- ✅ **Sector rotation tracker** (weekly sentiment analysis)
- ✅ **Smart model selection** (auto-switch reasoning/non-reasoning)
- ✅ **60% cost reduction** ($5-8/mo → $2-3/mo with optimizations)
- ✅ **Caching layer** (5-min TTL, 80% fewer API calls)
- ✅ **Dynamic quality filters** (no fixed influencer lists)
- ✅ **Batch search** (50 tickers per query)

### 2026-01-29: Exit Strategy System
- ✅ 38-component exit analysis
- ✅ Dynamic price targets (bull/base/bear)
- ✅ Exit urgency levels and real-time alerts
- ✅ Automated risk management

### 2026-01-29: Dashboard Improvements
- ✅ Dashboard hosted on GitHub Pages
- ✅ Added 7 intelligence visualizations
- ✅ Forensic analysis - all features verified

### 2026-01-29: Repository Cleanup
- ✅ Organized documentation into docs/
- ✅ Moved tests to tests/ directory
- ✅ Cleaned up root directory
- ✅ Professional structure

---

**Built with ❤️ for finding the next big stock story**

**⭐ Star this repo if you find it useful!**
