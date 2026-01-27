# Stock Scanner Bot

An AI-powered stock scanner with Telegram integration, featuring story-first analysis, theme detection, and self-evolving intelligence.

## Features

### Core Scanning
- **Async Scanner** - Scan 500+ stocks in ~7 minutes (17x faster than sequential)
- **Story-First Analysis** - Prioritize stocks with compelling narratives over pure technicals
- **Theme Detection** - Auto-discover and track market themes (AI, Nuclear, GLP-1, etc.)
- **Dynamic Universe** - Auto-updated S&P 500 + NASDAQ-100 ticker lists

### AI Intelligence
- **DeepSeek Integration** - AI-powered market analysis and predictions
- **Pattern Recognition** - Detect technical and narrative patterns
- **Trading Coach** - Personalized trade feedback and suggestions
- **Market Briefings** - Daily AI-generated market summaries

### Self-Learning System
- **Parameter Learning** - 124 auto-tuning parameters that adapt to market conditions
- **Theme Evolution** - Discover new themes from news clustering and correlations
- **Correlation Learning** - Detect lead-lag relationships between stocks
- **Accuracy Tracking** - Monitor and improve prediction quality over time

### Telegram Bot Commands

| Command | Description |
|---------|-------------|
| `/scan` | Run full market scan |
| `/top` | Show top-ranked stocks |
| `/ticker NVDA` | Analyze specific stock |
| `/screen volume>2 rs>80` | Custom screening |
| `/themes` | View active market themes |
| `/stories` | Detect emerging stories |
| `/news` | Latest market news |
| `/sectors` | Sector rotation analysis |
| `/health` | Market health check |
| `/earnings` | Upcoming earnings calendar |

**AI Commands:**
| Command | Description |
|---------|-------------|
| `/briefing` | AI market briefing |
| `/predict AAPL` | AI price prediction |
| `/coach` | Trading coach feedback |
| `/patterns` | Pattern detection |

**Learning Commands:**
| Command | Description |
|---------|-------------|
| `/evolution` | Learning system status |
| `/weights` | Adaptive scoring weights |
| `/accuracy` | Prediction accuracy metrics |
| `/parameters` | Parameter learning status |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Telegram Bot (app.py)                    │
│              Flask API + Webhook Handler                     │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│ Async Scanner │    │  AI Systems   │    │   Learning    │
│               │    │               │    │               │
│ async_scanner │    │ deepseek_     │    │ parameter_    │
│ scanner_auto  │    │ intelligence  │    │ learning      │
│ story_scorer  │    │ ai_learning   │    │ evolution_    │
│               │    │               │    │ engine        │
└───────────────┘    └───────────────┘    └───────────────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│    Themes     │    │   Analysis    │    │     Data      │
│               │    │               │    │               │
│ theme_registry│    │ market_health │    │ universe_     │
│ theme_learner │    │ sector_rotate │    │ manager       │
│ relationship_ │    │ news_analyzer │    │ cache_manager │
│ graph         │    │               │    │               │
└───────────────┘    └───────────────┘    └───────────────┘
```

## Quick Start

### Prerequisites
- Python 3.11+
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
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_chat_id
DEEPSEEK_API_KEY=your_deepseek_api_key  # Optional, for AI features
```

### Running Locally

```bash
# Using main entry point (recommended)
python main.py scan           # Full scan (500+ tickers)
python main.py scan --test    # Test scan (10 tickers)
python main.py dashboard      # Generate dashboard
python main.py bot            # Telegram bot listener
python main.py api            # Start Flask API
python main.py test           # Run tests

# Or use helper scripts
./scripts/run_scan.sh
./scripts/generate_dashboard.sh
./scripts/start_api.sh
```

### Running with Async Scanner

```python
from src.core.async_scanner import AsyncScanner
import asyncio

async def scan():
    scanner = AsyncScanner(max_concurrent=50)
    results = await scanner.run_scan_async(tickers)
    return results

# Run async scan
results = asyncio.run(scan())
```

## Deployment

### Render.com (Recommended)
The bot is configured for Render deployment with:
- `Procfile` - Process configuration
- `runtime.txt` - Python version
- GitHub Actions for scheduled scans

### GitHub Actions
Automated workflows in `.github/workflows/`:
- `daily_scan.yml` - Pre-market and after-hours scans
- `story_alerts.yml` - Real-time story detection
- `dashboard.yml` - Dashboard updates

## Project Structure

```
stock_scanner_bot/
├── main.py                       # Main entry point
├── src/                          # Source code (organized by module)
│   ├── core/                     # Core scanning engine
│   │   ├── async_scanner.py      # Async parallel scanning
│   │   ├── scanner_automation.py # Scan orchestration
│   │   ├── screener.py           # Technical filters
│   │   └── story_scoring.py      # Story-first scoring
│   │
│   ├── scoring/                  # Scoring systems
│   │   ├── story_scorer.py       # Legacy story scorer
│   │   ├── signal_ranker.py      # Signal ranking
│   │   └── param_helper.py       # Parameter helpers
│   │
│   ├── themes/                   # Theme management
│   │   ├── theme_registry.py     # Theme database (17 themes)
│   │   ├── theme_learner.py      # Auto-discover themes
│   │   └── fast_stories.py       # Quick story detection
│   │
│   ├── learning/                 # Self-learning system
│   │   ├── parameter_learning.py # Bayesian optimization
│   │   ├── self_learning.py      # Outcome tracking
│   │   └── evolution_engine.py   # Adaptive scoring
│   │
│   ├── ai/                       # AI intelligence
│   │   ├── deepseek_intelligence.py
│   │   ├── ai_learning.py
│   │   └── ai_ecosystem_generator.py
│   │
│   ├── data/                     # Data management
│   │   ├── universe_manager.py   # Stock universe (515 tickers)
│   │   ├── cache_manager.py      # File-based caching
│   │   └── storage.py            # Persistence
│   │
│   ├── analysis/                 # Market analysis
│   │   ├── news_analyzer.py      # News processing
│   │   ├── market_health.py      # Market internals
│   │   └── sector_rotation.py    # Sector analysis
│   │
│   ├── api/                      # Web API
│   │   └── app.py                # Flask application
│   │
│   ├── bot/                      # Telegram bot
│   │   ├── bot_listener.py       # Command handler
│   │   └── story_alerts.py       # Alert generation
│   │
│   └── dashboard/                # Dashboard
│       ├── dashboard.py          # HTML generator
│       └── charts.py             # Chart generation
│
├── config/                       # Configuration
│   └── config.py
├── scripts/                      # Helper scripts
├── tests/                        # Test suite
├── utils/                        # Utilities
├── docs/                         # Dashboard output (GitHub Pages)
└── .github/workflows/            # GitHub Actions
```

**Note:** Backward-compatible wrapper files exist in the root directory for legacy imports.

## Key Concepts

### Story-First Scoring System

```
Story Score = Story Quality (50%) + Catalyst (35%) + Technical Confirmation (15%)
```

Traditional scanners focus on technical indicators. This scanner prioritizes **stories**:
- What theme is the stock part of?
- Is there an upcoming catalyst?
- Is news momentum accelerating?
- What's the social sentiment?

Technical analysis confirms, but **story drives alpha**.

#### Score Components

| Component | Weight | Elements |
|-----------|--------|----------|
| **Story Quality** | 50% | Theme strength (40%), freshness (20%), clarity (20%), institutional (20%) |
| **Catalyst** | 35% | Catalyst type score × recency multiplier |
| **Confirmation** | 15% | Trend, volume, buyability |

#### Theme Tiers

| Tier | Score | Themes |
|------|-------|--------|
| MEGA | 100 | AI, GLP-1/Obesity Drugs |
| STRONG | 80 | Nuclear, Defense, Data Centers |
| MODERATE | 60 | Cybersecurity, Reshoring, Crypto |
| WEAK | 30 | EV, Cannabis, SPACs |

#### Catalyst Types

| Tier | Score | Types |
|------|-------|-------|
| 1 | 80-100 | FDA approval, Major contract, Acquisition target |
| 2 | 50-79 | Analyst upgrade, Insider buying, Partnership |
| 3 | 30-49 | Earnings beat, SEC 8-K, Social buzz |
| 4 | 0-29 | News mention, No catalyst |

#### Story Strength Labels

| Score | Label | Action |
|-------|-------|--------|
| 75+ | Hot | Strong narrative, ready to trade |
| 55-74 | Developing | Building momentum, watch closely |
| 40-54 | Watchlist | Story exists, needs confirmation |
| 25-39 | Waiting | Weak/old story |
| <25 | None | No story, avoid |

### Theme Detection
Themes are market narratives that drive stock movements:
- **AI Infrastructure** - NVDA, AMD, SMCI, etc.
- **Nuclear Renaissance** - CEG, VST, CCJ, etc.
- **GLP-1/Obesity** - LLY, NVO, VKTX, etc.

The system auto-discovers themes through:
1. News clustering (TF-IDF + DBSCAN)
2. Correlation analysis
3. AI classification (DeepSeek)

### Adaptive Learning
The system continuously improves through:
- **Parameter Learning** - 124 parameters auto-tune based on signal accuracy
- **Weight Optimization** - Scoring weights adapt to market regime
- **Theme Evolution** - New themes discovered, old ones retired

## Performance

| Metric | Sequential | Async |
|--------|------------|-------|
| 500 tickers | ~125 min | ~7 min |
| Per ticker | 15s | 0.9s |
| Speedup | 1x | **17x** |

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/scan` | Run scan, return results |
| `GET /api/ticker/<symbol>` | Analyze single ticker |
| `GET /api/stories` | Get emerging stories |
| `GET /api/news` | Latest news |
| `GET /api/sectors` | Sector analysis |
| `GET /api/earnings` | Earnings calendar |
| `GET /api/briefing` | AI market briefing |

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `pytest`
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Acknowledgments

- [yfinance](https://github.com/ranaroussi/yfinance) - Yahoo Finance data
- [DeepSeek](https://deepseek.com) - AI capabilities
- [Telegram Bot API](https://core.telegram.org/bots/api) - Bot platform
