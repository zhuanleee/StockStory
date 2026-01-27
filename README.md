# Stock Scanner Bot

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Railway](https://img.shields.io/badge/Deploy-Railway-blueviolet)](https://railway.app)

An institutional-grade stock scanner with real-time data from **Polygon.io**, AI-powered analysis via **DeepSeek**, and **Telegram** integration. Features story-first analysis, theme detection, options flow tracking, and self-evolving intelligence.

**Telegram Bot:** [@Stocks_Story_Bot](https://t.me/Stocks_Story_Bot)

## Highlights

- **Real-time Data** - Polygon.io integration for stocks, options, news, and fundamentals
- **17x Faster Scanning** - Async pipeline scans 500+ stocks in ~7 minutes
- **Story-First Analysis** - Prioritize narratives over pure technicals
- **Options Flow** - Track unusual options activity and put/call ratios
- **Self-Learning** - 124 auto-tuning parameters that adapt to market conditions
- **AI Intelligence** - DeepSeek-powered market analysis and predictions

## Data Sources

| Source | Data | Priority |
|--------|------|----------|
| **Polygon.io** | Price, Options, News, Financials, Dividends, Splits, Technical Indicators | Primary |
| **yfinance** | Price data, Earnings estimates | Fallback |
| **StockTwits** | Social sentiment | Supplementary |
| **Reddit** | Retail sentiment (wallstreetbets, stocks, investing, options) | Supplementary |
| **SEC EDGAR** | Insider filings, 8-K events | Supplementary |

## Features

### Core Scanning
- **Async Scanner** - Parallel scanning with connection pooling and rate limiting
- **Story-First Scoring** - Weight narratives, catalysts, and themes over technicals
- **Theme Detection** - 17+ tracked themes (AI, Nuclear, GLP-1, Defense, etc.)
- **Dynamic Universe** - Auto-updated S&P 500 + NASDAQ-100 via Polygon

### Polygon.io Integration
- **Real-time Quotes** - Sub-second price data with pre/post market
- **Options Chain** - Full options data with Greeks and unusual activity detection
- **News Feed** - Market news with sentiment scoring
- **Financials** - Quarterly/annual income statements, balance sheets, cash flow
- **Corporate Actions** - Dividends, stock splits, upcoming events
- **Technical Indicators** - SMA, EMA, RSI, MACD from Polygon's API
- **Ticker Universe** - Dynamic stock lists without web scraping

### AI Intelligence
- **DeepSeek Integration** - GPT-class analysis at lower cost
- **Pattern Recognition** - Technical and narrative pattern detection
- **Trading Coach** - Personalized trade feedback
- **Market Briefings** - Daily AI-generated summaries
- **Price Predictions** - ML-based directional forecasts

### Self-Learning System
- **Parameter Learning** - Bayesian optimization of 124 parameters
- **Theme Evolution** - Auto-discover themes from news clustering
- **Correlation Learning** - Detect lead-lag relationships
- **Accuracy Tracking** - Monitor prediction quality over time

## Telegram Commands

Use [@Stocks_Story_Bot](https://t.me/Stocks_Story_Bot) on Telegram:

### Market Analysis
| Command | Description |
|---------|-------------|
| `/scan` | Run full market scan |
| `/top` | Show top-ranked stocks |
| `/ticker NVDA` | Deep-dive on specific stock |
| `/screen volume>2 rs>80` | Custom screening filters |
| `/themes` | Active market themes |
| `/stories` | Emerging story detection |
| `/news` | Latest market news |
| `/sectors` | Sector rotation analysis |
| `/health` | Market internals (breadth, put/call, VIX) |
| `/earnings` | Upcoming earnings calendar |

### AI Commands
| Command | Description |
|---------|-------------|
| `/briefing` | AI market briefing |
| `/predict AAPL` | AI price prediction |
| `/coach` | Trading coach feedback |
| `/patterns` | Pattern detection |

### Learning Commands
| Command | Description |
|---------|-------------|
| `/evolution` | Learning system status |
| `/weights` | Adaptive scoring weights |
| `/accuracy` | Prediction accuracy metrics |
| `/parameters` | Parameter learning status |

## Architecture

```
                     ┌─────────────────────────────────────────┐
                     │           Telegram Bot (Flask)          │
                     │         Webhook + REST API              │
                     └─────────────────────────────────────────┘
                                        │
         ┌──────────────────────────────┼──────────────────────────────┐
         │                              │                              │
         ▼                              ▼                              ▼
┌─────────────────┐           ┌─────────────────┐           ┌─────────────────┐
│  Async Scanner  │           │   AI Systems    │           │    Learning     │
│                 │           │                 │           │                 │
│ • AsyncScanner  │           │ • DeepSeek AI   │           │ • Parameter     │
│ • StoryScorer   │           │ • AI Learning   │           │   Learning      │
│ • RateLimiter   │           │ • Predictions   │           │ • Evolution     │
│ • CacheManager  │           │                 │           │   Engine        │
└─────────────────┘           └─────────────────┘           └─────────────────┘
         │                              │                              │
         └──────────────────────────────┼──────────────────────────────┘
                                        │
         ┌──────────────────────────────┼──────────────────────────────┐
         │                              │                              │
         ▼                              ▼                              ▼
┌─────────────────┐           ┌─────────────────┐           ┌─────────────────┐
│  Polygon.io     │           │    Analysis     │           │     Themes      │
│                 │           │                 │           │                 │
│ • Stocks/Options│           │ • Market Health │           │ • 17+ Themes    │
│ • News          │           │ • Sector Rotate │           │ • Auto-Discovery│
│ • Financials    │           │ • News Analyzer │           │ • Correlation   │
│ • Technicals    │           │ • Earnings      │           │   Graph         │
└─────────────────┘           └─────────────────┘           └─────────────────┘
```

## Quick Start

### Prerequisites
- Python 3.11+
- Polygon.io API Key (free tier works)
- Telegram Bot Token
- (Optional) DeepSeek API Key for AI features

### Installation

```bash
# Clone repository
git clone https://github.com/zhuanleee/stock_scanner_bot.git
cd stock_scanner_bot

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys
```

### Environment Variables

```env
# Required
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_chat_id
POLYGON_API_KEY=your_polygon_api_key

# Optional
DEEPSEEK_API_KEY=your_deepseek_api_key
```

### Running

```bash
# Main entry point
python main.py scan           # Full scan (500+ tickers)
python main.py scan --test    # Test scan (10 tickers)
python main.py dashboard      # Generate HTML dashboard
python main.py bot            # Telegram bot listener
python main.py api            # Start Flask API
python main.py test           # Run test suite
```

### Using Async Scanner

```python
from src.core.async_scanner import AsyncScanner
import asyncio

async def scan():
    scanner = AsyncScanner(max_concurrent=50)
    results = await scanner.run_scan_async(tickers)
    await scanner.close()
    return results

results = asyncio.run(scan())
```

## Performance

| Metric | Sequential | Async + Polygon |
|--------|------------|-----------------|
| 500 tickers | ~125 min | ~7 min |
| Per ticker | 15s | 0.25s |
| Speedup | 1x | **60x** |
| Cache hit rate | 0% | 60-80% |

## Scoring System

### Story-First Philosophy

Traditional scanners focus on technical indicators. This scanner prioritizes **stories**:

```
Story Score = Story Quality (50%) + Catalyst (35%) + Technical Confirmation (15%)
```

### Score Components

| Component | Weight | Elements |
|-----------|--------|----------|
| **Story Quality** | 50% | Theme strength, freshness, clarity, institutional interest |
| **Catalyst** | 35% | Event type, recency, magnitude |
| **Confirmation** | 15% | Trend alignment, volume, buyability |

### Theme Tiers

| Tier | Score | Examples |
|------|-------|----------|
| MEGA | 100 | AI Infrastructure, GLP-1/Obesity |
| STRONG | 80 | Nuclear, Defense, Data Centers |
| MODERATE | 60 | Cybersecurity, Reshoring, Crypto |
| EMERGING | 40 | Robotics, Space, Quantum |

### Catalyst Types

| Tier | Score | Examples |
|------|-------|---------|
| 1 | 80-100 | FDA approval, Major contract, M&A |
| 2 | 50-79 | Analyst upgrade, Insider buying |
| 3 | 30-49 | Earnings beat, Partnership |
| 4 | 0-29 | News mention, No catalyst |

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/scan` | GET | Run scan, return results |
| `/api/ticker/<symbol>` | GET | Analyze single ticker |
| `/api/stories` | GET | Emerging stories |
| `/api/news` | GET | Latest news |
| `/api/sectors` | GET | Sector analysis |
| `/api/earnings` | GET | Earnings calendar |
| `/api/options/<symbol>` | GET | Options flow data |
| `/api/briefing` | GET | AI market briefing |

## Project Structure

```
stock_scanner_bot/
├── main.py                    # Main entry point
├── app.py                     # Flask app wrapper
├── src/
│   ├── core/                  # Scanning engine
│   │   ├── async_scanner.py   # Async parallel scanning
│   │   ├── scanner_automation.py
│   │   └── screener.py
│   │
│   ├── data/                  # Data providers
│   │   ├── polygon_provider.py  # Polygon.io client
│   │   ├── universe_manager.py  # Stock universe
│   │   └── cache_manager.py
│   │
│   ├── scoring/               # Scoring systems
│   │   └── story_scorer.py
│   │
│   ├── analysis/              # Market analysis
│   │   ├── news_analyzer.py
│   │   ├── market_health.py
│   │   ├── earnings.py
│   │   └── sector_rotation.py
│   │
│   ├── themes/                # Theme management
│   │   ├── theme_registry.py
│   │   └── theme_learner.py
│   │
│   ├── learning/              # Self-learning
│   │   ├── parameter_learning.py
│   │   └── evolution_engine.py
│   │
│   ├── ai/                    # AI systems
│   │   └── deepseek_intelligence.py
│   │
│   ├── api/                   # Web API
│   │   └── app.py
│   │
│   └── bot/                   # Telegram bot
│       └── bot_listener.py
│
├── config/                    # Configuration
├── tests/                     # Test suite
├── docs/                      # GitHub Pages dashboard
└── .github/workflows/         # CI/CD
```

## Deployment

### Railway (Recommended)
- Automatic deploys from GitHub
- Environment variables via dashboard
- Configured via `Procfile`

### GitHub Actions
Automated workflows:
- `daily_scan.yml` - Pre-market and after-hours scans
- `dashboard.yml` - Dashboard updates every 30 min

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

- [Polygon.io](https://polygon.io) - Real-time market data
- [yfinance](https://github.com/ranaroussi/yfinance) - Yahoo Finance data
- [DeepSeek](https://deepseek.com) - AI capabilities
- [Telegram Bot API](https://core.telegram.org/bots/api) - Bot platform
