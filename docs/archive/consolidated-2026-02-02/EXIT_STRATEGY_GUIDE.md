#!/usr/bin/env python3
"""
Exit Strategy System - Complete Guide
======================================

Dynamic exit targets and alerts using all 38 components.

**Author:** Stock Scanner Bot
**Date:** 2026-01-29
**Version:** 1.0
"""

# EXIT STRATEGY SYSTEM

## 🎯 Overview

The Exit Strategy Analyzer is a sophisticated system that uses **all 38 components** of the stock scanner to determine:

1. **When to exit** a position
2. **Dynamic price targets** (bull/base/bear cases)
3. **Exit urgency level** (1-10 scale)
4. **Specific exit reasons** based on component analysis
5. **Real-time alerts** via Telegram

---

## 🧠 How It Works

### 38-Component Analysis

The system analyzes **every position** across 38 data points:

#### TECHNICAL (8 components)
1. Price momentum (MA crossovers, trend strength)
2. Volume profile (OBV, volume trends)
3. Relative strength (RS vs SPY)
4. Support/resistance levels
5. Volatility (ATR, Bollinger Bands)
6. Price patterns (breakouts, breakdowns)
7. Moving average health (20/50/200 day)
8. MACD signals

#### SENTIMENT (6 components)
9. X/Twitter sentiment
10. Reddit sentiment
11. StockTwits sentiment
12. Sentiment trend direction
13. Viral post activity
14. Social volume changes

#### THEME/CATALYST (8 components)
15. Theme strength score
16. Theme leadership position
17. Supply chain relationships
18. Catalyst freshness
19. Narrative consistency
20. Sector rotation signals
21. Related stocks performance
22. Theme concentration risk

#### AI ANALYSIS (4 components)
23. AI conviction score
24. AI risk assessment
25. AI opportunity score
26. AI pattern recognition

#### EARNINGS (4 components)
27. Earnings call transcript tone
28. Guidance direction
29. Beat/miss rate
30. Earnings surprise trend

#### INSTITUTIONAL (4 components)
31. Institutional ownership changes
32. Dark pool activity
33. Options flow (call/put ratio)
34. Smart money indicators

#### FUNDAMENTAL (4 components)
35. Revenue growth trajectory
36. Margin trends
37. Valuation metrics vs peers
38. Insider trading activity

---

## 📊 Dynamic Price Targets

The system calculates **3 price targets** for each position:

### 1. Bull Target
**Scenario:** Everything goes right
- Theme continues strong
- Earnings beat expectations
- Sentiment remains positive
- Institutional buying continues

**Typical Multiplier:** 1.5x (50% upside)
**Timeframe:** 90 days
**Confidence:** Based on component alignment

### 2. Base Target
**Scenario:** Normal conditions
- Theme remains stable
- Fundamentals solid
- Moderate momentum continues

**Typical Multiplier:** 1.2x (20% upside)
**Timeframe:** 60 days
**Confidence:** 70%

### 3. Bear Target
**Scenario:** Things weaken
- Catalyst fading
- Sentiment deteriorating
- Rotation out of theme

**Typical Multiplier:** 1.05x (5% upside)
**Timeframe:** 30 days
**Confidence:** 50%

### Active Target Selection

The system automatically selects which target is active based on:
- Overall health score (0-100)
- Component degradation rate
- Recent momentum

**Rules:**
- Health ≥ 80% → Bull target active
- Health 60-80% → Base target active
- Health < 60% → Bear target active

---

## 🚨 Exit Urgency Levels

Exit signals are categorized by urgency:

| Urgency | Level | Action Required | Timeframe |
|---------|-------|-----------------|-----------|
| **EMERGENCY** | 10 | Exit at market immediately | Now |
| **CRITICAL** | 9 | Exit today, best price | Today |
| **HIGH** | 7 | Exit within 24 hours | Today |
| **MODERATE** | 5 | Exit this week | 1-2 days |
| **LOW** | 3 | Consider exit | This week |
| **NONE** | 0 | Monitor only | Ongoing |

---

## 💡 Exit Reasons

The system identifies specific exit triggers:

### 1. Risk Management
- Stop loss hit
- Maximum loss threshold reached
- Position size risk exceeded

**Example:**
```
🚨 EMERGENCY: NVDA
Stop loss triggered at $850
Action: EXIT IMMEDIATELY
```

### 2. Technical Breakdown
- Price momentum < 40/100
- MA breakdown (below 50/200 day)
- Relative strength deteriorating
- Volume profile weak

**Example:**
```
⚠️ HIGH: TSLA
Price broke below 50-day MA
Volume declining, RS falling
Action: EXIT today
```

### 3. Catalyst Expired
- Catalyst freshness < 30/100
- Narrative consistency breaking
- Original story no longer driving price

**Example:**
```
⚡ MODERATE: AMD
Earnings catalyst played out
No new catalysts on horizon
Action: EXIT this week
```

### 4. Sentiment Deterioration
- X/Twitter sentiment < 35/100
- Reddit sentiment turning negative
- Social volume declining
- Viral activity gone

**Example:**
```
⚡ MODERATE: COIN
X sentiment: 28/100 (was 75)
Reddit turning bearish
Action: EXIT on next bounce
```

### 5. Theme Weakness
- Theme strength < 40/100
- Sector rotating out
- Related stocks underperforming
- Leadership position lost

**Example:**
```
⚡ MODERATE: PLTR
AI theme weakening
Sector rotation underway
Action: EXIT this week
```

### 6. Institutional Exit
- Institutional ownership declining
- Dark pool activity negative
- Smart money indicators bearish
- Options flow turning put-heavy

**Example:**
```
⚠️ HIGH: SHOP
Institutional selling detected
Dark pool: net sellers
Action: EXIT today
```

### 7. Profit Target
- Position up 50%+
- Consider taking profits
- Lock in gains

**Example:**
```
💡 LOW: SMCI
Position +67% from entry
Action: Scale out 50-70%
Alternative: Trail stop at +20%
```

### 8. Component Degradation
- Overall health < 50/100
- 3+ critical components failing
- Degradation rate accelerating

**Example:**
```
🚨 CRITICAL: RIVN
Health: 35/100 (was 80)
8 components degraded
Action: EXIT today
```

---

## 🛡️ Dynamic Risk Management

### Stop Loss Calculation

**Base Stop:** -7% from entry

**Adjusted for Volatility:**
- Low volatility (< 1%): Stop at -7%
- Medium volatility (1-3%): Stop at -8% to -9%
- High volatility (> 3%): Stop at -10% (max)

**Example:**
```
Entry: $100
Volatility: 2.5%
Stop Loss: $92 (-8%)
```

### Trailing Stop

**Rules:**
- **< 5% profit:** Use fixed stop loss
- **5-15% profit:** Trail at breakeven + 2%
- **15-30% profit:** Trail at +10%
- **> 30% profit:** Trail at +20%

**Example:**
```
Entry: $100
Current: $135 (+35%)
Trailing Stop: $120 (+20%)
```

This locks in a 20% minimum gain while letting winners run.

---

## 📱 Telegram Alerts

### Alert Triggers

Alerts sent for:
- **EMERGENCY:** Immediate notification
- **CRITICAL:** Sent once per day max
- **HIGH:** Sent once per hour max

### Alert Format

```
🚨🚨🚨 EXIT ALERT: NVDA

💰 Entry: $850.00 → Current: $812.00
📈 P/L: -4.5% (7 days)
💊 Health: 42/100

🎯 Urgency: CRITICAL
📋 Action: EXIT today at best available price
⏰ Timeframe: TODAY

🚨 Exit Signals:
  • Technical breakdown: Price below all MAs
  • Sentiment deterioration: X sentiment at 32/100

🎯 Targets:
  Stop Loss: $793.00
  Trailing: $850.00
  Target: $890.00
```

### Alert Cooldown

To prevent spam:
- Same ticker: Max 1 alert per hour
- Portfolio summary: Max 1 per 4 hours

---

## 🎨 Dashboard Integration

### Position Health Panel

Shows for each position:
```
┌─────────────────────────────────────┐
│ NVDA - CRITICAL EXIT                │
├─────────────────────────────────────┤
│ Entry: $850 | Current: $812         │
│ P/L: -4.5% | Health: 42/100         │
│                                     │
│ 🎯 Target: $890 (5% upside)         │
│ 🛡️ Stop: $793 (-2.3%)               │
│ ⏰ Action: EXIT today                │
│                                     │
│ Exit Signals (3):                   │
│  • Technical breakdown              │
│  • Sentiment negative               │
│  • Theme weakening                  │
│                                     │
│ [View Details] [Exit Position]      │
└─────────────────────────────────────┘
```

### Exit Analysis Modal

Detailed view shows:
- All 38 component scores
- Component health breakdown
- Degradation rate chart
- Price target scenarios
- Alternative exit strategies
- Historical performance

---

## 🔧 Usage Examples

### Via Telegram

#### Check Single Position
```
/exit NVDA

Response:
🎯 EXIT ANALYSIS: NVDA
Entry: $850.00 | Current: $875.00 | P/L: +2.9%
Health: 72/100

Target: $935.00 (bull case)
Stop: $793.00
Action: HOLD - Monitor closely
```

#### Monitor All Positions
```
/exitall

Response:
📊 PORTFOLIO EXIT MONITOR

🚨 CRITICAL (2):
• TSLA: EXIT today (-6.2%)
• COIN: EXIT today (-4.1%)

⚠️ HIGH (1):
• AMD: EXIT this week (+8.5%)

✅ HEALTHY (5):
• NVDA: Health 85/100
• MSFT: Health 78/100
...
```

#### Get Exit Targets
```
/targets NVDA

Response:
🎯 PRICE TARGETS: NVDA
Current: $875.00 (Entry: $850.00)

Bull: $1,080.00 (+23.4%)
  Timeframe: 90 days
  Confidence: 85%
  Scenario: Theme strong, earnings beat

Base: $935.00 (+6.9%)
  Timeframe: 60 days
  Confidence: 70%
  Scenario: Normal conditions

Bear: $900.00 (+2.9%)
  Timeframe: 30 days
  Confidence: 50%
  Scenario: Catalyst fades

Active: BULL (Health: 85/100)
```

### Via API

#### Analyze Exit
```bash
curl "https://your-app.com/api/exit/analyze/NVDA?entry_price=850&entry_date=2026-01-15&current_price=875"
```

**Response:**
```json
{
  "ok": true,
  "ticker": "NVDA",
  "analysis": {
    "current_pnl_pct": 2.94,
    "overall_health": 72.5,
    "should_exit": false,
    "urgency": "LOW",
    "recommended_action": "HOLD - Monitor closely",
    "targets": {
      "bull": {
        "price": 1080.0,
        "confidence": 0.85,
        "timeframe_days": 90
      },
      "base": {
        "price": 935.0,
        "confidence": 0.70,
        "timeframe_days": 60
      },
      "bear": {
        "price": 900.0,
        "confidence": 0.50,
        "timeframe_days": 30
      },
      "current": 1080.0
    },
    "risk": {
      "stop_loss": 793.0,
      "trailing_stop": 850.0
    },
    "exit_signals": []
  }
}
```

#### Monitor Portfolio
```bash
curl -X POST https://your-app.com/api/exit/monitor \
  -H "Content-Type: application/json" \
  -d '{
    "positions": [
      {
        "ticker": "NVDA",
        "entry_price": 850,
        "entry_date": "2026-01-15",
        "shares": 100
      },
      {
        "ticker": "TSLA",
        "entry_price": 245,
        "entry_date": "2026-01-10",
        "shares": 50
      }
    ]
  }'
```

**Response:**
```json
{
  "ok": true,
  "total_positions": 2,
  "critical_positions": 1,
  "analyses": [
    {
      "ticker": "TSLA",
      "current_pnl_pct": -6.2,
      "overall_health": 38.0,
      "should_exit": true,
      "urgency": "CRITICAL",
      "recommended_action": "EXIT today",
      "targets": {
        "current": 250.0,
        "stop_loss": 228.0
      },
      "top_signals": [
        {
          "reason": "Technical breakdown",
          "urgency": "HIGH"
        },
        {
          "reason": "Theme weakening",
          "urgency": "MODERATE"
        }
      ]
    },
    {
      "ticker": "NVDA",
      "current_pnl_pct": 2.9,
      "overall_health": 72.0,
      "should_exit": false,
      "urgency": "NONE"
    }
  ]
}
```

---

## 🎓 Best Practices

### 1. Check Daily
- Run exit analysis every morning
- Review overnight changes
- Adjust stops accordingly

### 2. Act on Urgency
- **EMERGENCY/CRITICAL:** Exit immediately, don't hesitate
- **HIGH:** Exit same day, don't wait for perfect price
- **MODERATE:** Exit within 1-2 days, can wait for bounce
- **LOW:** Monitor, no rush

### 3. Use Trailing Stops
- Once position profitable, always use trailing stop
- Never let a winner turn into a loser
- Lock in gains systematically

### 4. Trust the System
- If 3+ components failing → Exit
- If overall health < 50 → Exit
- Don't fight the analysis

### 5. Scale Out
- Don't need to exit 100% at once
- Scale out 50-70% on signals
- Keep 30-50% as runner with trailing stop

### 6. Learn from Exits
- Review exit decisions weekly
- What worked? What didn't?
- System learns from your feedback

---

## 📈 Performance Optimization

### Component Weights

The system uses weighted scoring:

**High Weight (exits):**
- Price momentum: 8%
- Relative strength: 7%
- Theme strength: 6%
- Catalyst freshness: 6%
- Institutional ownership: 5%

**Medium Weight:**
- Sentiment: 21% combined
- AI analysis: 12% combined
- Earnings: 11% combined

**Lower Weight:**
- Fundamental: 9% combined
- Supporting indicators: 15% combined

### Degradation Detection

Tracks how fast position quality is deteriorating:

**Degradation Rate:**
- **> +2.0/day:** Improving rapidly ✅
- **+0.5 to +2.0:** Improving gradually ✅
- **-0.5 to +0.5:** Stable ⚠️
- **-2.0 to -0.5:** Degrading slowly 🚨
- **< -2.0/day:** Degrading rapidly 🚨🚨

---

## 🔮 Future Enhancements

**Planned Features:**
1. Machine learning exit timing optimization
2. Backtesting exit strategies
3. Win rate tracking by exit reason
4. Optimal exit time prediction
5. Correlation with market regime
6. Sector-specific exit rules
7. Volatility-adjusted targets
8. Options overlay strategies

---

## 📞 Support

**Questions?**
- Check `/help exit` in Telegram
- View dashboard "Exit Analysis" tab
- Review `DASHBOARD_FORENSIC_REPORT.md`

**Found a bug?**
- Report via GitHub issues
- Include ticker, entry date, error message

---

## ✅ Summary

The Exit Strategy Analyzer provides:

✅ **38-component analysis** of every position
✅ **Dynamic price targets** (bull/base/bear)
✅ **Real-time exit signals** with urgency levels
✅ **Telegram alerts** for critical exits
✅ **Dashboard integration** for visual monitoring
✅ **Automated risk management** with trailing stops
✅ **Learning system** that improves over time

**Result:** Never miss an exit, maximize profits, minimize losses.

---

**Last Updated:** 2026-01-29
**Version:** 1.0
**Status:** Production Ready ✅
