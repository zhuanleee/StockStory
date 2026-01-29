# 🚀 Self-Learning System - Quick Start Guide

Get your self-learning trading brain up and running in 5 minutes.

---

## Step 1: Test the System (2 minutes)

```bash
# Test all components
python test_learning_system.py
```

**Expected output:**
```
✅ ALL TESTS PASSED!

Components Tested:
  ✓ Tier 1: Bayesian Bandit
  ✓ Tier 2: Regime Detection
  ✓ Tier 3: PPO Agent
  ✓ Tier 4: Meta-Learner
  ✓ Full Integration
  ✓ API Endpoints
```

---

## Step 2: Simple Integration (Tier 1 + 2) - 3 minutes

**Use Case:** Start with proven, low-risk learning.

```python
from src.learning import (
    SelfLearningBrain,
    LearningConfig,
    ComponentScores,
    MarketContext
)

# Initialize with Tier 1 + 2 only
config = LearningConfig(
    use_tier1=True,  # Bayesian Bandit
    use_tier2=True,  # Regime Detection
    use_tier3=False,  # PPO (advanced)
    use_tier4=False   # Meta-learning (most advanced)
)

brain = SelfLearningBrain(config)

# Get a trading decision
scores = ComponentScores(
    theme_score=8.5,
    technical_score=7.2,
    ai_confidence=0.85,
    x_sentiment_score=0.6
)

context = MarketContext(
    spy_change_pct=2.5,
    vix_level=15.0,
    stocks_above_ma50=70.0
)

decision = brain.get_trading_decision(
    ticker="NVDA",
    component_scores=scores,
    market_context=context
)

print(f"Action: {decision.action}")
print(f"Overall Score: {decision.overall_score}/10")
print(f"Weights: {decision.weights_used.to_dict()}")
```

---

## Step 3: Learn from Trades

```python
from src.learning import TradeRecord, create_trade_id
from datetime import datetime

# When trade closes
trade = TradeRecord(
    trade_id=create_trade_id("NVDA", datetime.now()),
    decision_id=decision.decision_id,
    ticker="NVDA",
    entry_date=datetime.now(),
    entry_price=850.0,
    exit_price=875.0,  # 2.9% win!
    shares=100,
    component_scores=scores,
    market_context=context,
    weights_used=decision.weights_used
)
trade.calculate_outcome()

# Learn from it
brain.learn_from_trade(trade)

print(f"Learned from {trade.outcome.value}: {trade.pnl_pct:.2f}%")
print(f"Total trades: {brain.total_trades}")
```

---

## Step 4: Monitor Learning Progress

```python
# Get statistics
stats = brain.get_statistics()

print(f"Win Rate: {stats['performance']['win_rate']:.1%}")
print(f"Sharpe: {stats['performance']['sharpe_ratio']:.2f}")

print("Current Weights:")
for comp, weight in stats['current_weights'].items():
    print(f"  {comp}: {weight:.1%}")

# Full report
brain.print_report()
```

---

## Step 5: Use API Endpoints

**Start server:**
```bash
python src/api/app.py
```

**Get decision via API:**
```bash
curl -X POST http://localhost:5000/api/learning/decide \
  -H "Content-Type: application/json" \
  -d '{
    "ticker": "NVDA",
    "component_scores": {
      "theme_score": 8.5,
      "technical_score": 7.2,
      "ai_confidence": 0.85,
      "x_sentiment_score": 0.6
    },
    "market_context": {
      "spy_change_pct": 2.5,
      "vix_level": 15.0
    }
  }'
```

**Get statistics:**
```bash
curl http://localhost:5000/api/learning/statistics
```

**Get current weights:**
```bash
curl http://localhost:5000/api/learning/weights
```

---

## Common Use Cases

### Use Case 1: Get Optimal Component Weights

```python
brain = get_learning_brain()

# Get weights for current regime
weights = brain.current_weights

# Calculate overall score using learned weights
overall_score = (
    theme_score * weights.theme +
    technical_score * weights.technical +
    ai_confidence * 10 * weights.ai +
    x_sentiment * 10 * weights.sentiment
)
```

### Use Case 2: Detect Market Regime

```python
if brain.regime_detector:
    regime_state = brain.regime_detector.detect_regime(market_context)

    if regime_state.current_regime == MarketRegimeType.CRISIS_MODE:
        print("⚠️ Crisis detected - defensive mode")
    elif regime_state.current_regime == MarketRegimeType.BULL_MOMENTUM:
        print("🚀 Bull momentum - aggressive mode")
```

### Use Case 3: Circuit Breaker

```python
if brain.circuit_breaker_active:
    print("🔴 Circuit breaker active - no trading")
    # Stop all trading until conditions improve
else:
    # Normal trading
    decision = brain.get_trading_decision(...)
```

---

## Advanced: All 4 Tiers

```python
# Enable all tiers for maximum learning
config = LearningConfig(
    use_tier1=True,
    use_tier2=True,
    use_tier3=True,  # PPO for position sizing
    use_tier4=True   # Meta-learning for learner selection
)

brain = SelfLearningBrain(config)

# Provide portfolio state for Tier 3+
portfolio_state = {
    'cash_pct': 80.0,
    'num_positions': 2,
    'total_exposure_pct': 20.0,
    'current_drawdown_pct': 2.5
}

decision = brain.get_trading_decision(
    ticker="NVDA",
    component_scores=scores,
    market_context=context,
    portfolio_state=portfolio_state
)

# Get learned action parameters
print(f"Position Size: {decision.position_size}%")  # Learned!
print(f"Stop Loss: {decision.stop_loss}%")  # Learned!
print(f"Take Profit: {decision.take_profit}%")  # Learned!
print(f"Learner: {decision.learner_type}")  # Which specialist
```

---

## Dashboard Integration

```javascript
// In your dashboard JavaScript

async function getDecision(ticker, scores, context) {
    const response = await fetch('/api/learning/decide', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            ticker: ticker,
            component_scores: scores,
            market_context: context
        })
    });

    const data = await response.json();

    if (data.ok) {
        console.log('Decision:', data.decision);
        console.log('Weights:', data.decision.weights);
        console.log('Regime:', data.decision.regime);
    }
}

async function submitTrade(trade) {
    await fetch('/api/learning/learn', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({trade: trade})
    });

    console.log('Brain learned from trade!');
}
```

---

## Monitoring

### Check Learning Status

```python
brain = get_learning_brain()

print(f"Learning Active: {brain.learning_active}")
print(f"Total Trades: {brain.total_trades}")
print(f"Circuit Breaker: {brain.circuit_breaker_active}")
print(f"Current Regime: {brain.current_regime.value}")
```

### View Learning Progress

```bash
# Via API
curl http://localhost:5000/api/learning/report
```

### View Performance

```bash
curl http://localhost:5000/api/learning/performance
```

---

## Safety Features

**Automatic Circuit Breaker:**
- Activates if Sharpe < -0.5
- Activates if drawdown > 15%
- Stops all trading until conditions improve

**Manual Override:**
```python
# Manually activate
brain.circuit_breaker_active = True

# Or via API
curl -X POST http://localhost:5000/api/learning/circuit-breaker \
  -H "Content-Type: application/json" \
  -d '{"active": true}'
```

**Position Limits:**
- Max position size: 20% (configurable)
- Max daily loss: 2%
- Max drawdown: 15%

---

## Troubleshooting

**Issue: "Learning not active"**
```python
# Check minimum trades
print(brain.total_trades)  # Must be >= 5

# Or adjust config
config.min_trades_before_learning = 3
```

**Issue: "Weights not changing"**
```python
# Check if enough trades
brain.bandit.get_statistics()['sample_size']

# Need ~10-20 trades per component
```

**Issue: "API not found"**
```bash
# Check if registered
grep "Learning System API" logs

# Restart server
python src/api/app.py
```

---

## Next Steps

1. **Start Simple:** Use Tier 1 + 2 only
2. **Collect Data:** Run for 20-50 trades
3. **Monitor:** Check learning progress regularly
4. **Validate:** Compare learned weights vs defaults
5. **Scale Up:** Enable Tier 3 + 4 after validation

---

## Key Files

- `src/learning/learning_brain.py` - Main orchestrator
- `src/learning/tier1_bandit.py` - Bayesian Bandit
- `src/learning/tier2_regime.py` - Regime Detection
- `src/learning/learning_api.py` - REST API
- `test_learning_system.py` - Test suite
- `SELF_LEARNING_SYSTEM_COMPLETE.md` - Full documentation

---

## Support

**Questions?**
- Read: `SELF_LEARNING_SYSTEM_COMPLETE.md`
- Test: `python test_learning_system.py`
- Check logs: Look for `✓ Learning System API registered`

**Your trading brain is ready to learn!** 🧠✨

Start with Tier 1 + 2, let it learn from your trades, and watch it improve over time.
