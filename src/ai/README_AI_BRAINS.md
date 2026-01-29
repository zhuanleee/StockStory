# AI Brain Architecture

## Active Implementations

### 1. comprehensive_agentic_brain.py (1200 lines)
**Status**: ACTIVE (Base system)
**Purpose**: Hierarchical intelligence system with 5 specialized directors

**Architecture**:
- ChiefIntelligenceOfficer (orchestrator)
- ThemeIntelligenceDirector (theme analysis)
- TradingIntelligenceDirector (entry/exit logic)
- LearningAdaptationDirector (continuous learning)
- RealtimeIntelligenceDirector (market monitoring)
- ValidationFeedbackDirector (outcome tracking)

**Usage**:
```python
from src.ai.comprehensive_agentic_brain import ChiefIntelligenceOfficer

cio = ChiefIntelligenceOfficer()
decision = cio.analyze_opportunity(...)
```

**Used By**: evolutionary_agentic_brain.py (extends this)

---

### 2. evolutionary_agentic_brain.py (1500 lines) ⭐
**Status**: ACTIVE (Production system)
**Purpose**: Self-improving brain with automatic performance tracking

**Key Features**:
- Extends comprehensive_agentic_brain
- Automatic component performance tracking
- Trust score evolution based on accuracy
- Weight optimization (high performers get more weight)
- Decision history and outcome recording
- Zero manual work - everything automatic

**Architecture**:
```
EvolutionaryChiefIntelligenceOfficer
  └─ extends ChiefIntelligenceOfficer
      └─ ComponentPerformance tracking (37 components)
      └─ Auto-learning from outcomes
      └─ Weight evolution
```

**Usage** (RECOMMENDED):
```python
from src.ai.evolutionary_agentic_brain import get_evolutionary_cio, record_trade_outcome

# Get decision
cio = get_evolutionary_cio()
decision = cio.analyze_opportunity(ticker='NVDA', signal_type='story_scan', signal_data={...})

# Later, record outcome (system automatically learns)
record_trade_outcome(
    decision_id=decision.decision_id,
    actual_outcome='win',
    actual_pnl=0.15  # +15%
)
```

**Integration Points**:
- ✅ async_scanner.py (optional AI ranking via USE_AI_BRAIN_RANKING env var)
- ✅ watchlist_manager.py (decision support)
- Future: trade_manager.py (auto-learning from closes)

---

## Archived Implementations

### agentic_brain.py.archived (800 lines)
**Status**: ARCHIVED
**Reason**: Basic version, only used in tests, superseded by comprehensive + evolutionary

**Migration**:
- Old tests using agentic_brain → use evolutionary_agentic_brain
- All production code → use get_evolutionary_cio()

---

## Decision Tree: Which Brain to Use?

```
Do you need AI decision support?
├─ YES: Use evolutionary_agentic_brain.py
│   ├─ get_evolutionary_cio() for decisions
│   └─ record_trade_outcome() for learning
│
└─ NO: Don't need AI brain, use rule-based scoring
```

**Key Point**: Always use `evolutionary_agentic_brain.py` for production. It automatically uses comprehensive_agentic_brain underneath while adding self-improvement.

---

## Component Tracking (37 Components)

The evolutionary brain tracks performance for:
1. Theme Intelligence Director
2. Trading Intelligence Director
3. Learning Adaptation Director
4. Realtime Intelligence Director
5. Validation Feedback Director
6-37. Individual specialists under each director

Each component has:
- Accuracy rate (predictions_correct / total_predictions)
- Trust score (0-1, evolves based on accuracy)
- Weight multiplier (0.5-2.0, high performers get >1.0)
- Performance history (last 100 decisions)

---

## Performance Data Storage

**Location**: `~/.claude/agentic_brain/`
- `component_performance.json` - Trust scores, accuracy, weights
- `decision_history.json` - All decisions made
- `evolution_log.json` - Weight evolution over time

**Persistence**: Automatically saved after each outcome recording

---

## Integration Checklist

- [x] Scanner integration (USE_AI_BRAIN_RANKING=true)
- [x] Watchlist integration
- [ ] Trade manager integration (auto-record outcomes)
- [ ] Dashboard visualization (component performance charts)
- [ ] Outcome webhook (for manual trade recording)

---

## Migration Guide

### From agentic_brain.py (old)
```python
# OLD
from src.ai.agentic_brain import get_brain
brain = get_brain()
decision = brain.analyze(...)

# NEW (recommended)
from src.ai.evolutionary_agentic_brain import get_evolutionary_cio
cio = get_evolutionary_cio()
decision = cio.analyze_opportunity(...)
```

### From comprehensive_agentic_brain.py
```python
# OLD (works but doesn't learn)
from src.ai.comprehensive_agentic_brain import ChiefIntelligenceOfficer
cio = ChiefIntelligenceOfficer()
decision = cio.analyze_opportunity(...)

# NEW (adds auto-learning)
from src.ai.evolutionary_agentic_brain import get_evolutionary_cio
cio = get_evolutionary_cio()
decision = cio.analyze_opportunity(...)
# Plus: record_trade_outcome() to enable learning
```

---

## Future Enhancements

1. **Regime-Specific Weights**: Different weights per market regime (bull/bear/choppy)
2. **Meta-Learning**: Learn which components work best for which setups
3. **Ensemble Decisions**: Multiple brains voting with confidence weighting
4. **Explainability Dashboard**: Visual component performance over time
5. **Auto-Tuning**: Automated A/B testing of weight configurations

---

**Last Updated**: 2026-01-29
**Maintained By**: Learning System Team
**Documentation**: See LEARNING_QUICK_START.md for user guide
