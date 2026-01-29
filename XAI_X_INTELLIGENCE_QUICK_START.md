# xAI X Intelligence - Quick Start Guide

## 🚀 5-Minute Setup

### Step 1: Get xAI API Key
```bash
# 1. Visit https://x.ai
# 2. Sign up / Login
# 3. Generate API key
# 4. Copy key
```

### Step 2: Add to Environment
```bash
# Edit .env file
echo "XAI_API_KEY=your-key-here" >> .env
```

### Step 3: Test Installation
```bash
python test_xai_x_intelligence.py
```

✅ **Done!** X Intelligence is now monitoring 24/7.

---

## 💡 Basic Usage

### Standalone Monitoring

```python
from src.ai.xai_x_intelligence import XAIXIntelligence

x = XAIXIntelligence()

# What's trending?
trends = x.get_trending_crisis_topics()
print(f"Crisis topics: {trends}")

# Market panic level?
panic = x.detect_market_panic_on_x()
print(f"Panic: {panic.panic_level}/10")

# Stock sentiment?
sent = x.monitor_specific_stocks_on_x(['NVDA', 'TSLA'])
print(f"NVDA: {sent['NVDA'].sentiment}")
```

### Integrated with CIO (Automatic)

```python
from src.ai.evolutionary_agentic_brain import (
    get_evolutionary_cio,
    analyze_opportunity_evolutionary
)

cio = get_evolutionary_cio()  # X monitoring starts automatically

# Make decision (X check happens automatically)
decision = analyze_opportunity_evolutionary(
    ticker='AAPL',
    signal_type='momentum_breakout',
    signal_data={'rs': 90, 'volume': '2x'},
    theme_data={'name': 'Tech', 'players': ['AAPL']},
    timeframe_data={...}
)

print(f"Decision: {decision.decision.value}")
print(f"X Sentiment: {decision.x_sentiment.sentiment if hasattr(decision, 'x_sentiment') else 'N/A'}")
```

---

## 📊 Monitor Status

### Check System

```python
status = cio.get_x_intelligence_status()

print(f"Active: {status['available']}")
print(f"Mode: {status['mode']}")  # normal/elevated/crisis
print(f"Emergency: {status['emergency_override']}")
print(f"Blacklisted: {status['blacklisted_sectors']}")
```

### Check Costs

```python
stats = x.get_statistics()

print(f"Searches today: {stats['daily_searches']}")
print(f"Budget left: {stats['budget_remaining']}")
print(f"Cost today: {stats['estimated_cost_today']}")
```

### Check Performance (Component #37)

```python
from src.ai.evolutionary_agentic_brain import get_component_performance

perf = get_component_performance('x_intelligence_monitor')

print(f"Accuracy: {perf.accuracy_rate:.1%}")
print(f"Trust: {perf.trust_score:.2f}")
print(f"Decisions: {perf.decisions_participated}")
```

---

## 🚨 Emergency Handling

### During Crisis

```python
# System automatically:
# 1. Detects crisis on X
# 2. Activates emergency protocol
# 3. Halts trading (if severity ≥ 9)
# 4. Blacklists affected sectors

# Check if in emergency mode
if cio.emergency_override:
    print("🚨 EMERGENCY MODE ACTIVE")
    print(f"Reason: Crisis detected")
    print(f"Blacklisted: {cio.blacklisted_sectors}")
```

### Clear Emergency

```python
# After reviewing situation
# Manual clear required (safety feature)

cio.clear_emergency_override()
print("✓ Emergency cleared - trading resumed")
```

---

## 💰 Cost Control

### Default Budget
- **150 searches/day** = ~$15/month max
- **Normal mode:** ~$8-9/month
- **With occasional crises:** ~$11/month

### Adjust Budget

```python
# In src/ai/xai_x_intelligence.py
class XAIXIntelligence:
    def __init__(self):
        self.MAX_DAILY_SEARCHES = 100  # Lower to $10/month
        # or
        self.MAX_DAILY_SEARCHES = 50   # Lower to $5/month
```

### Monitor Usage

```python
stats = x.get_statistics()

if stats['daily_searches'] > 100:
    print("⚠️ High usage today")

if stats['budget_remaining'] < 20:
    print("⚠️ Budget running low")
```

---

## 🎯 Common Scenarios

### Scenario 1: Before Entering Trade

```python
# Check X sentiment before buying
sentiment = x.monitor_specific_stocks_on_x(['AAPL'])

if sentiment['AAPL'].has_red_flags:
    print(f"🚩 RED FLAGS: {sentiment['AAPL'].red_flags}")
    print("❌ Skip trade")
elif sentiment['AAPL'].sentiment == 'bullish':
    print(f"✓ Bullish sentiment: {sentiment['AAPL'].catalysts}")
    print("✓ Proceed with trade")
```

### Scenario 2: Check Market Conditions

```python
# Before market open
panic = x.detect_market_panic_on_x()

if panic.panic_level >= 8:
    print("⚠️ HIGH PANIC - Stay in cash")
elif panic.panic_level <= 3:
    print("✓ Low fear - Look for opportunities")
```

### Scenario 3: Monitor During Day

```python
# Check periodically
trending = x.get_trending_crisis_topics()

if trending:
    print(f"⚠️ Potential crises: {trending}")
    # System will auto-analyze and alert if serious
```

---

## 🔧 Troubleshooting

### Problem: No alerts

**Check:**
```python
# 1. API key configured?
import os
print(os.getenv('XAI_API_KEY'))  # Should not be None

# 2. Budget remaining?
print(x.get_statistics()['budget_remaining'])  # Should be > 0

# 3. Markets calm?
print(x.get_trending_crisis_topics())  # Empty list = calm
```

### Problem: Too many false alarms

**Solution:**
```python
# Increase credibility threshold
# Edit src/ai/xai_x_intelligence.py
# In _analyze_topic_with_xai:

if alert.credibility_score < 0.75:  # Raise from 0.7
    return None  # Skip low-credibility
```

### Problem: High costs

**Solution:**
```python
# 1. Lower daily limit
x.MAX_DAILY_SEARCHES = 50

# 2. Increase cache TTL
cache = XAnalysisCache(ttl_hours=48)  # Longer cache

# 3. Check for unnecessary calls
stats = x.get_statistics()
print(f"Searches: {stats['daily_searches']}")  # Should be < 150
```

---

## 📈 Interpretation Guide

### Panic Levels

| Level | Meaning | Action |
|-------|---------|--------|
| 1-2 | Extreme greed | Caution, consider taking profits |
| 3-4 | Moderate optimism | Normal conditions |
| 5-6 | Neutral | Wait and see |
| 7-8 | Fear rising | Defensive positioning |
| 9-10 | Extreme panic | Cash is king |

### Sentiment Scores

| Score | Meaning | Interpretation |
|-------|---------|----------------|
| +0.7 to +1.0 | Very bullish | Strong positive sentiment |
| +0.3 to +0.7 | Bullish | Positive lean |
| -0.3 to +0.3 | Neutral | Mixed/unclear |
| -0.7 to -0.3 | Bearish | Negative lean |
| -1.0 to -0.7 | Very bearish | Strong negative sentiment |

### Crisis Severity

| Level | Description | Response |
|-------|-------------|----------|
| 1-3 | Minor | Monitor only |
| 4-6 | Moderate | Increase alertness |
| 7-8 | Major | Tighten controls |
| 9-10 | Critical | Emergency protocol |

---

## 📚 Key Files

**Source Code:**
- `src/ai/xai_x_intelligence.py` - Main system
- `src/ai/evolutionary_agentic_brain.py` - Integration

**Tests:**
- `test_xai_x_intelligence.py` - Test suite

**Documentation:**
- `docs/XAI_X_INTELLIGENCE_SYSTEM.md` - Full docs
- `XAI_X_INTELLIGENCE_IMPLEMENTATION.md` - Implementation summary
- `XAI_X_INTELLIGENCE_QUICK_START.md` - This guide

**Data:**
- `~/.claude/agentic_brain/component_performance.json` - Component #37 tracking
- `~/.claude/agentic_brain/decision_history.json` - Decision log
- `~/.claude/agentic_brain/evolution_log.json` - Evolution events

---

## 🎓 Learning Path

**Day 1: Setup**
- Install xAI API key
- Run test suite
- Understand basic concepts

**Week 1: Monitoring**
- Check status daily
- Review alerts
- Monitor costs

**Month 1: Optimization**
- Tune credibility thresholds
- Adjust budget if needed
- Review component performance

**Month 3: Mastery**
- Understand crisis patterns
- Optimize response protocols
- Customize for your strategy

---

## 💡 Pro Tips

### Tip 1: Check Before Market Open
```python
# Every morning routine
panic = x.detect_market_panic_on_x()
trends = x.get_trending_crisis_topics()

if panic.panic_level > 7 or trends:
    print("⚠️ Elevated risk today")
```

### Tip 2: Verify Major Alerts
```python
# For severity ≥ 9, double-check
if alert.severity >= 9:
    # Check mainstream news
    # Verify with multiple sources
    # Don't rely on single alert
```

### Tip 3: Monitor Costs Weekly
```python
# Every Friday
stats = x.get_statistics()
weekly_cost = stats['cost_today'] * 7  # Estimate weekly

if weekly_cost > 5:  # $5/week = $20/month
    print("⚠️ On track to exceed budget")
```

### Tip 4: Trust the System
```python
# System blocked your trade?
if decision.decision.value == 'pass':
    if 'X Intelligence' in decision.reasoning:
        # Trust it - there's a reason
        print("✓ Trade blocked by X Intelligence")
        print(f"Reason: {decision.reasoning}")
```

---

## 🎯 Success Metrics

### Track These Weekly

```python
# Component #37 performance
perf = get_component_performance('x_intelligence_monitor')

print(f"Accuracy: {perf.accuracy_rate:.1%}")  # Target: >75%
print(f"Trust: {perf.trust_score:.2f}")       # Target: >0.6
print(f"Decisions: {perf.decisions_participated}")

# Cost efficiency
stats = x.get_statistics()
print(f"Weekly cost: ${stats['cost_today'] * 7:.2f}")  # Target: <$3
```

### Monthly Review

1. **How many crises detected?**
2. **How many were accurate?**
3. **Did we avoid losses?**
4. **What was the ROI?**
5. **Any false positives to tune?**

---

## 🆘 Support

### Get Help

1. **Run diagnostics:**
   ```bash
   python test_xai_x_intelligence.py
   ```

2. **Check logs:**
   ```bash
   tail -f ~/.claude/agentic_brain/evolution_log.json
   ```

3. **Review performance:**
   ```python
   from src.ai.evolutionary_agentic_brain import get_accountability_dashboard
   print(get_accountability_dashboard())
   ```

---

## 📞 Quick Reference Commands

```python
# Import
from src.ai.xai_x_intelligence import XAIXIntelligence
from src.ai.evolutionary_agentic_brain import get_evolutionary_cio

# Initialize
x = XAIXIntelligence()
cio = get_evolutionary_cio()

# Monitor
x.get_trending_crisis_topics()
x.detect_market_panic_on_x()
x.monitor_specific_stocks_on_x(['TICKER'])

# Status
cio.get_x_intelligence_status()
x.get_statistics()

# Emergency
cio.clear_emergency_override()
```

---

**Status: ✅ READY TO USE**

**Remember:** This system is your early warning radar. Trust it, monitor it, but always verify critical alerts manually.

**Cost:** ~$11/month
**Value:** Priceless (one avoided crisis = 1,000%+ ROI)
**Status:** Component #37 actively learning

🚀 **Happy Trading with X Intelligence!**
