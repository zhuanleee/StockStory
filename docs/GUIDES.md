# Stock Scanner Bot - User Guides

Quick reference for all features. For complete documentation, see [PROJECT.md](/PROJECT.md).

---

## Table of Contents
1. [Telegram Bot](#1-telegram-bot)
2. [Exit Strategy](#2-exit-strategy)
3. [Watchlist](#3-watchlist)
4. [Learning System](#4-learning-system)
5. [X Intelligence](#5-x-intelligence)

---

## 1. Telegram Bot

### Setup
```bash
# 1. Get your Chat ID
python scripts/deployment/get_chat_id.py

# 2. Configure Modal secrets
modal secret create Stock_Story \
  TELEGRAM_BOT_TOKEN=your_token \
  TELEGRAM_CHAT_ID=your_chat_id \
  POLYGON_API_KEY=xxx \
  XAI_API_KEY=xxx \
  DEEPSEEK_API_KEY=xxx \
  ALPHA_VANTAGE_API_KEY=xxx

# 3. Deploy
modal deploy modal_scanner.py
```

### Commands
| Command | Description |
|---------|-------------|
| `/scan` | Full market scan |
| `/scan NVDA` | Scan specific ticker |
| `/top10` | Top 10 stocks |
| `/trends NVDA` | Google Trends |
| `/exec NVDA` | Executive commentary |
| `/earnings NVDA` | Earnings analysis |
| `/sympathy NVDA` | Related stocks |
| `/watch add NVDA` | Add to watchlist |
| `/watch list` | View watchlist |
| `/exit NVDA` | Exit signals |
| `/exitall` | All positions |
| `/targets NVDA` | Price targets |
| `/weights` | Component weights |
| `/stats` | Learning stats |
| `/status` | System health |
| `/help` | All commands |

---

## 2. Exit Strategy

### How It Works
The exit analyzer evaluates all 38 components to determine:
- **When to exit** (urgency 0-10)
- **Price targets** (bull/base/bear cases)
- **Action** (HOLD/REDUCE/SELL)

### Usage
```
/exit NVDA          # Analyze single position
/exitall            # Monitor all positions
/targets NVDA       # View price targets
```

### Exit Signals (Automated)
Runs daily at 6 AM PST (Mon-Fri):
1. Checks all holdings for red flags
2. Detects sentiment shifts
3. Sends Telegram alerts for urgent exits

### Urgency Levels
| Level | Action | Timeframe |
|-------|--------|-----------|
| 8-10 | EXIT NOW | Today |
| 6-7 | EXIT SOON | This week |
| 4-5 | MONITOR | Watch closely |
| 0-3 | HOLD | Position healthy |

---

## 3. Watchlist

### Add Stocks
```bash
# Via Telegram
/watch add NVDA

# Via API
curl -X POST http://localhost:5000/api/watchlist/ \
  -H "Content-Type: application/json" \
  -d '{"ticker": "NVDA", "priority": "high"}'
```

### View Watchlist
```bash
/watch list

# Or via API
curl http://localhost:5000/api/watchlist/
```

### Priority Levels
- **High**: Ready to trade soon
- **Medium**: Monitor closely
- **Low**: Long-term watch

### Auto-Updates
- Prices update every 30 seconds
- Health scores recalculated every 4 hours

---

## 4. Learning System

### How It Works
The system learns optimal component weights from trade outcomes:
1. **Bayesian optimization** with Thompson sampling
2. **Regime detection** (bull/bear/choppy)
3. **Performance tracking** over time
4. **Shadow mode testing** before production

### View Weights
```
/weights            # Current component weights
/stats              # Learning statistics
```

### Training Data
- Requires trade history with outcomes
- Minimum 20 trades for meaningful learning
- Updates weights after each closed trade

---

## 5. X Intelligence

### Features
- **Crisis detection**: Monitors verified news accounts
- **Stock sentiment**: Real-time X/Twitter analysis
- **Meme detection**: Viral momentum tracking
- **Sector rotation**: Weekly sector sentiment

### Quality Filters
| Feature | Verified | Followers | Engagement |
|---------|----------|-----------|------------|
| Crisis | Yes | 10K+ | 50+ |
| Holdings | Yes | 5K+ | 20+ |
| Watchlist | Yes | 1K+ | 10+ |
| Meme scan | No | Any | 100+ |

### Cost Optimization
- 5-minute caching (80% fewer calls)
- Batch search (50 tickers/query)
- ~$2-3/month total

### Manual Testing
```bash
# Test exit signals
modal run modal_intelligence_jobs.py::daily_exit_signal_check

# Test meme scanner
modal run modal_intelligence_jobs.py::daily_meme_stock_scan

# Test sector rotation
modal run modal_intelligence_jobs.py::weekly_sector_rotation_analysis
```

---

## Troubleshooting

### Bot Not Responding
1. Check Modal logs: `modal app logs stock-scanner`
2. Verify secrets: `modal secret list`
3. Redeploy: `modal deploy modal_scanner.py`

### API Errors
1. Check API key validity
2. Verify rate limits
3. Check cache status

### Dashboard Not Loading
1. Check GitHub Pages settings
2. Verify `docs/index.html` exists
3. Check browser console for errors

---

**For complete documentation, see [PROJECT.md](/PROJECT.md)**
