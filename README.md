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
# Start the bot
python app.py

# Or run a scan directly
python scanner_automation.py
```

### Running with Async Scanner

```python
from scanner_automation import run_scan_with_async

# Run async scan (17x faster)
results, price_data = run_scan_with_async()
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
├── app.py                 # Main Flask app + Telegram bot
├── async_scanner.py       # High-performance async scanning
├── scanner_automation.py  # Core scanning orchestration
├── story_scorer.py        # Story-first scoring system
├── theme_registry.py      # Theme tracking and management
├── theme_learner.py       # AI theme discovery
├── deepseek_intelligence.py  # DeepSeek AI integration
├── evolution_engine.py    # Self-learning system
├── parameter_learning.py  # Auto-tuning parameters
├── cache_manager.py       # Caching infrastructure
├── config.py              # Configuration management
├── utils/                 # Utility modules
├── tests/                 # Test suite
└── docs/                  # Dashboard HTML
```

## Key Concepts

### Story-First Analysis
Traditional scanners focus on technical indicators. This scanner prioritizes **stories**:
- What theme is the stock part of?
- Is there an upcoming catalyst?
- Is news momentum accelerating?
- What's the social sentiment?

Technical analysis confirms, but story drives alpha.

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
