# Watchlist + Learning System Integration Plan

## The Opportunity

Your watchlist currently uses **hardcoded weights** (30% theme, 25% technical, 25% AI, 20% sentiment) to score stocks. With the 4-tier learning system, you can make these weights **adaptive and regime-aware**.

## Current Architecture Gap

```python
# Current (watchlist_manager.py:142-165)
def calculate_overall_score(self) -> int:
    # Theme/Story (30%) - HARDCODED!
    if self.story_score is not None:
        scores.append(self.story_score)
        weights.append(0.30)  # ← Fixed weight

    # Technical (25%) - HARDCODED!
    if self.technical_score is not None:
        scores.append(self.technical_score)
        weights.append(0.25)  # ← Fixed weight

    # ... etc
```

**The learning system has already learned better weights from real trades!**

---

## Proposal 1: "Learning-Aware Watchlist" (Minimal Integration)

### What It Does
Use learned component weights instead of hardcoded ones.

### Implementation (5 minutes)

**File**: `src/watchlist/watchlist_manager.py`

```python
def calculate_overall_score(self, learned_weights=None) -> int:
    """
    Calculate weighted overall score (0-10).

    Args:
        learned_weights: Optional ComponentWeights from learning system
                        If None, uses default weights
    """
    scores = []
    weights = []

    # Get weights (learned or default)
    if learned_weights:
        theme_weight = learned_weights.theme
        technical_weight = learned_weights.technical
        ai_weight = learned_weights.ai
        sentiment_weight = learned_weights.sentiment
    else:
        # Fallback to defaults
        theme_weight = 0.30
        technical_weight = 0.25
        ai_weight = 0.25
        sentiment_weight = 0.20

    # Theme/Story
    if self.story_score is not None:
        scores.append(self.story_score)
        weights.append(theme_weight)

    # Technical
    if self.technical_score is not None:
        scores.append(self.technical_score)
        weights.append(technical_weight)

    # AI Confidence
    if self.ai_confidence is not None:
        scores.append(self.ai_confidence * 10)
        weights.append(ai_weight)

    # X Sentiment
    if self.x_sentiment_score is not None:
        sentiment_score = (self.x_sentiment_score + 1) * 5
        scores.append(sentiment_score)
        weights.append(sentiment_weight)

    # ... rest of calculation
```

**Usage:**
```python
from src.learning import get_learning_brain

wm = get_watchlist_manager()
brain = get_learning_brain()

# Get item with learned weights
item = wm.get_item("NVDA")
item.overall_score = item.calculate_overall_score(
    learned_weights=brain.current_weights
)
```

**Value**: Watchlist immediately benefits from learned weights. Zero new code complexity.

---

## Proposal 2: "Regime-Aware Watchlist" (Moderate Integration)

### What It Does
Prioritize watchlist items differently based on detected market regime.

### Implementation

```python
# Add to WatchlistManager class

def get_regime_recommendations(self, max_items: int = 5) -> List[WatchlistItem]:
    """
    Get top recommendations based on current market regime.

    Uses learning system's regime detection to prioritize:
    - Bull Momentum: High growth, momentum stocks
    - Bear Defensive: Low beta, defensive plays
    - Choppy: High RS, strong themes regardless of market
    - Crisis: Cash, quality only
    - Theme Driven: Highest theme strength
    """
    from src.learning import get_learning_brain

    brain = get_learning_brain()
    regime = brain.current_regime

    # Get all items with scores
    items = [item for item in self.items.values() if item.overall_score is not None]

    # Regime-specific filtering and sorting
    if regime == MarketRegimeType.BULL_MOMENTUM:
        # Prioritize momentum and growth
        scored_items = [
            (item, item.momentum_score or 0 * 0.5 + item.overall_score * 0.5)
            for item in items
        ]

    elif regime == MarketRegimeType.BEAR_DEFENSIVE:
        # Prioritize quality and low volatility
        scored_items = [
            (item, item.rs_rating or 50 * 0.3 + item.overall_score * 0.7)
            for item in items
            if (item.pe_ratio or 100) < 30  # Quality filter
        ]

    elif regime == MarketRegimeType.CHOPPY_RANGE:
        # Strong RS regardless of market
        scored_items = [
            (item, item.rs_rating or 0 * 0.6 + item.overall_score * 0.4)
            for item in items
            if (item.rs_rating or 0) >= 80
        ]

    elif regime == MarketRegimeType.CRISIS_MODE:
        # Only highest quality, highest conviction
        scored_items = [
            (item, item.overall_score)
            for item in items
            if item.signal_quality == SignalQuality.EXCELLENT.value
            and (item.ai_confidence or 0) >= 0.8
        ]

    elif regime == MarketRegimeType.THEME_DRIVEN:
        # Strongest themes
        scored_items = [
            (item, item.theme_strength or 0 * 0.6 + item.overall_score * 0.4)
            for item in items
            if item.theme and item.theme_stage in ['emerging', 'developing']
        ]

    else:
        # Unknown regime: use overall score
        scored_items = [(item, item.overall_score) for item in items]

    # Sort by regime-specific score
    scored_items.sort(key=lambda x: x[1], reverse=True)

    return [item for item, score in scored_items[:max_items]]
```

**Usage:**
```python
wm = get_watchlist_manager()

# Get top 5 recommendations for current regime
recommendations = wm.get_regime_recommendations(max_items=5)

for item in recommendations:
    print(f"{item.ticker}: {item.overall_score}/10 - {item.signal_quality}")
```

**Value**: Watchlist automatically adapts to market conditions. Different stocks prioritized in different regimes.

---

## Proposal 3: "Auto-Curator Watchlist Brain" (Full Integration)

### What It Does
A dedicated "Watchlist Brain" that:
1. Auto-adds stocks from scans based on learned criteria
2. Auto-removes poor performers
3. Auto-prioritizes based on regime + learning
4. Suggests position sizing from Tier 3 PPO

### Architecture

```
┌────────────────────────────────────────────────┐
│         WATCHLIST BRAIN (New Class)            │
│                                                 │
│  Responsibilities:                              │
│  - Auto-curate watchlist from scans            │
│  - Regime-aware prioritization                 │
│  - Position sizing recommendations             │
│  - Entry/exit timing signals                   │
│  - Learning from watchlist → trade outcomes    │
└──────────┬─────────────────────────┬───────────┘
           │                         │
    ┌──────▼──────┐          ┌──────▼──────┐
    │  Learning   │          │  Watchlist  │
    │   System    │          │   Manager   │
    │  (4 Tiers)  │          │  (Storage)  │
    └─────────────┘          └─────────────┘
```

### Implementation

**File**: `src/watchlist/watchlist_brain.py` (NEW)

```python
"""
Watchlist Brain - Intelligent watchlist management using learning system.

This "brain" sits between the learning system and watchlist manager,
making intelligent decisions about what to watch and when to trade.
"""

from typing import List, Dict, Optional
from datetime import datetime, timedelta

from src.learning import (
    get_learning_brain,
    ComponentScores,
    MarketContext,
    MarketRegimeType
)
from src.watchlist.watchlist_manager import (
    get_watchlist_manager,
    WatchlistItem,
    WatchlistPriority,
    SignalQuality
)


class WatchlistBrain:
    """
    Intelligent watchlist curator using 4-tier learning system.
    """

    def __init__(self):
        self.learning_brain = get_learning_brain()
        self.watchlist_mgr = get_watchlist_manager()

        # Configuration
        self.auto_add_threshold = 7.0  # Add if score >= 7/10
        self.auto_remove_threshold = 3.0  # Remove if score < 3/10
        self.max_watchlist_size = 20

    # ======================================================================
    # AUTO-CURATION
    # ======================================================================

    def evaluate_for_watchlist(
        self,
        ticker: str,
        scan_data: Dict
    ) -> Optional[WatchlistItem]:
        """
        Evaluate if ticker should be added to watchlist.
        Uses learned weights and current regime.

        Returns:
            WatchlistItem if added, None if rejected
        """
        # Build component scores from scan data
        scores = ComponentScores(
            theme_score=scan_data.get('theme_score', 5),
            technical_score=scan_data.get('technical_score', 5),
            ai_confidence=scan_data.get('ai_confidence', 0.5),
            x_sentiment_score=scan_data.get('x_sentiment_score', 0)
        )

        # Get market context (you'd get this from your market data)
        context = MarketContext(
            spy_change_pct=0,  # Populate from real data
            vix_level=15,
            stocks_above_ma50=60
        )

        # Get decision from learning brain
        decision = self.learning_brain.get_trading_decision(
            ticker=ticker,
            component_scores=scores,
            market_context=context
        )

        # Decision criteria
        if decision.overall_score >= self.auto_add_threshold:
            # Add to watchlist
            item = self.watchlist_mgr.add_from_scan(ticker, scan_data)

            # Set priority based on score
            if decision.overall_score >= 8:
                item.priority = WatchlistPriority.HIGH.value
            elif decision.overall_score >= 6:
                item.priority = WatchlistPriority.MEDIUM.value
            else:
                item.priority = WatchlistPriority.LOW.value

            # Add AI reasoning as notes
            item.notes = f"Auto-added: {decision.action.upper()} signal\n"
            item.notes += f"Regime: {decision.regime.value}\n"
            item.notes += f"Learned weights used: {decision.weights_used.to_dict()}"

            self.watchlist_mgr._save_watchlist()
            return item

        return None

    def curate_watchlist(self):
        """
        Regular curation: remove weak items, adjust priorities.
        Call this daily or weekly.
        """
        all_items = self.watchlist_mgr.get_all_items()

        for item in all_items:
            # Recalculate with learned weights
            item.overall_score = item.calculate_overall_score(
                learned_weights=self.learning_brain.current_weights
            )

            # Auto-remove if weak
            if item.overall_score is not None and item.overall_score < self.auto_remove_threshold:
                print(f"Auto-removing {item.ticker} (score: {item.overall_score}/10)")
                self.watchlist_mgr.remove_item(item.ticker)
                continue

            # Update priority
            if item.overall_score >= 8:
                item.priority = WatchlistPriority.HIGH.value
            elif item.overall_score >= 6:
                item.priority = WatchlistPriority.MEDIUM.value
            else:
                item.priority = WatchlistPriority.LOW.value

        # Trim if too large (keep highest scored)
        if len(all_items) > self.max_watchlist_size:
            sorted_items = sorted(
                all_items,
                key=lambda x: x.overall_score or 0,
                reverse=True
            )

            # Remove lowest scored items
            for item in sorted_items[self.max_watchlist_size:]:
                print(f"Trimming {item.ticker} from oversized watchlist")
                self.watchlist_mgr.remove_item(item.ticker)

        self.watchlist_mgr._save_watchlist()

    # ======================================================================
    # REGIME-AWARE RECOMMENDATIONS
    # ======================================================================

    def get_top_picks(self, count: int = 5) -> List[Dict]:
        """
        Get top picks for current market regime.

        Returns list of dicts with:
        - item: WatchlistItem
        - score: Regime-adjusted score
        - reasoning: Why it's recommended
        - suggested_size: Position size from PPO (if Tier 3 enabled)
        """
        regime = self.learning_brain.current_regime
        items = self.watchlist_mgr.get_all_items()

        picks = []
        for item in items:
            # Calculate regime-adjusted score
            base_score = item.overall_score or 0

            # Regime adjustments
            adjustment = 0
            reasoning = f"Base score: {base_score}/10. "

            if regime == MarketRegimeType.BULL_MOMENTUM:
                # Favor high momentum
                if (item.momentum_score or 0) >= 8:
                    adjustment += 1
                    reasoning += "High momentum in bull market. "

            elif regime == MarketRegimeType.BEAR_DEFENSIVE:
                # Favor quality
                if (item.rs_rating or 0) >= 85:
                    adjustment += 0.5
                    reasoning += "High RS in defensive mode. "
                if (item.signal_quality == SignalQuality.EXCELLENT.value):
                    adjustment += 0.5
                    reasoning += "Excellent quality. "

            elif regime == MarketRegimeType.THEME_DRIVEN:
                # Favor strong themes
                if (item.theme_strength or 0) >= 8:
                    adjustment += 1
                    reasoning += f"Strong theme: {item.theme}. "

            adjusted_score = min(10, base_score + adjustment)

            # Get position sizing if Tier 3 enabled
            suggested_size = None
            if self.learning_brain.ppo_agent:
                # Would integrate with PPO here for position sizing
                # Simplified for now
                if adjusted_score >= 8:
                    suggested_size = "15-20%"
                elif adjusted_score >= 6:
                    suggested_size = "10-15%"
                else:
                    suggested_size = "5-10%"

            picks.append({
                'item': item,
                'score': adjusted_score,
                'reasoning': reasoning,
                'suggested_size': suggested_size,
                'regime': regime.value
            })

        # Sort by adjusted score
        picks.sort(key=lambda x: x['score'], reverse=True)

        return picks[:count]

    # ======================================================================
    # ENTRY TIMING
    # ======================================================================

    def check_ready_to_enter(self, ticker: str) -> Dict:
        """
        Check if watchlist item is ready for entry.

        Returns dict with:
        - ready: bool
        - reasons: List of reasons why/why not
        - suggested_entry: Price level
        - suggested_stop: Stop loss level
        - confidence: 0-1
        """
        item = self.watchlist_mgr.get_item(ticker)
        if not item:
            return {'ready': False, 'reasons': ['Not in watchlist']}

        reasons = []
        ready = True

        # Check 1: Setup complete
        if not item.setup_complete:
            ready = False
            reasons.append("Setup incomplete")
        else:
            reasons.append("✓ Setup complete")

        # Check 2: Signal quality
        if item.signal_quality in [SignalQuality.EXCELLENT.value, SignalQuality.GOOD.value]:
            reasons.append(f"✓ {item.signal_quality.capitalize()} quality")
        else:
            ready = False
            reasons.append(f"✗ Signal quality only {item.signal_quality}")

        # Check 3: Overall score
        if (item.overall_score or 0) >= 7:
            reasons.append(f"✓ Strong score: {item.overall_score}/10")
        else:
            ready = False
            reasons.append(f"✗ Weak score: {item.overall_score}/10")

        # Check 4: Regime alignment
        regime = self.learning_brain.current_regime
        if regime != MarketRegimeType.CRISIS_MODE:
            reasons.append(f"✓ Regime: {regime.value}")
        else:
            ready = False
            reasons.append("✗ Crisis mode - avoid new entries")

        # Check 5: Circuit breaker
        if not self.learning_brain.circuit_breaker_active:
            reasons.append("✓ Circuit breaker OK")
        else:
            ready = False
            reasons.append("✗ Circuit breaker active")

        return {
            'ready': ready,
            'reasons': reasons,
            'suggested_entry': item.target_entry or item.current_price,
            'suggested_stop': item.stop_loss,
            'confidence': item.ai_confidence or 0.5,
            'position_size': self._suggest_position_size(item)
        }

    def _suggest_position_size(self, item: WatchlistItem) -> str:
        """Suggest position size based on conviction and regime."""
        score = item.overall_score or 5
        confidence = item.ai_confidence or 0.5

        # High conviction
        if score >= 8 and confidence >= 0.8:
            return "15-20% (high conviction)"

        # Medium conviction
        elif score >= 6 and confidence >= 0.6:
            return "10-15% (normal)"

        # Low conviction
        else:
            return "5-10% (small size)"

    # ======================================================================
    # REPORTING
    # ======================================================================

    def generate_watchlist_report(self) -> str:
        """Generate human-readable watchlist report."""
        report = []
        report.append("=" * 70)
        report.append("INTELLIGENT WATCHLIST REPORT")
        report.append("=" * 70)
        report.append("")

        # Current regime
        regime = self.learning_brain.current_regime
        report.append(f"Current Market Regime: {regime.value.upper()}")
        report.append(f"Learning Active: {self.learning_brain.learning_active}")
        report.append(f"Circuit Breaker: {'🔴 ACTIVE' if self.learning_brain.circuit_breaker_active else '🟢 OK'}")
        report.append("")

        # Learned weights
        weights = self.learning_brain.current_weights
        report.append("Learned Component Weights:")
        report.append(f"  Theme:     {weights.theme:.1%}")
        report.append(f"  Technical: {weights.technical:.1%}")
        report.append(f"  AI:        {weights.ai:.1%}")
        report.append(f"  Sentiment: {weights.sentiment:.1%}")
        report.append("")

        # Top picks
        report.append("TOP 5 PICKS FOR CURRENT REGIME:")
        report.append("-" * 70)

        picks = self.get_top_picks(count=5)
        for i, pick in enumerate(picks, 1):
            item = pick['item']
            report.append(f"{i}. {item.ticker} - Score: {pick['score']:.1f}/10")
            report.append(f"   Priority: {item.priority.upper()}")
            report.append(f"   Price: ${item.current_price:.2f}" if item.current_price else "   Price: N/A")
            report.append(f"   Quality: {item.signal_quality}")
            if pick['suggested_size']:
                report.append(f"   Suggested Size: {pick['suggested_size']}")
            report.append(f"   Reasoning: {pick['reasoning']}")
            report.append("")

        # Ready to enter
        ready_items = []
        for item in self.watchlist_mgr.get_all_items():
            check = self.check_ready_to_enter(item.ticker)
            if check['ready']:
                ready_items.append((item, check))

        if ready_items:
            report.append("READY TO ENTER NOW:")
            report.append("-" * 70)
            for item, check in ready_items:
                report.append(f"✓ {item.ticker} - {item.overall_score}/10")
                report.append(f"  Entry: ${check['suggested_entry']:.2f}")
                if check['suggested_stop']:
                    report.append(f"  Stop: ${check['suggested_stop']:.2f}")
                report.append(f"  Size: {check['position_size']}")
                report.append("")

        report.append("=" * 70)
        return "\n".join(report)


# Singleton
_watchlist_brain = None

def get_watchlist_brain() -> WatchlistBrain:
    """Get singleton watchlist brain."""
    global _watchlist_brain
    if _watchlist_brain is None:
        _watchlist_brain = WatchlistBrain()
    return _watchlist_brain
```

---

## API Integration

**File**: `src/watchlist/watchlist_api.py` (ADD ENDPOINT)

```python
# Add to existing API

@watchlist_bp.route('/brain/top-picks', methods=['GET'])
def get_brain_top_picks():
    """Get intelligent recommendations from watchlist brain."""
    try:
        from src.watchlist.watchlist_brain import get_watchlist_brain

        brain = get_watchlist_brain()
        picks = brain.get_top_picks(count=5)

        # Serialize
        result = []
        for pick in picks:
            item = pick['item']
            result.append({
                'ticker': item.ticker,
                'score': pick['score'],
                'reasoning': pick['reasoning'],
                'regime': pick['regime'],
                'current_price': item.current_price,
                'signal_quality': item.signal_quality,
                'suggested_size': pick['suggested_size']
            })

        return jsonify({'ok': True, 'picks': result})

    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@watchlist_bp.route('/brain/report', methods=['GET'])
def get_brain_report():
    """Get full watchlist brain report."""
    try:
        from src.watchlist.watchlist_brain import get_watchlist_brain

        brain = get_watchlist_brain()
        report = brain.generate_watchlist_report()

        return jsonify({'ok': True, 'report': report})

    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500
```

---

## Dashboard Integration

Add to watchlist tab in `docs/index.html`:

```javascript
async function refreshWatchlistBrain() {
    try {
        const res = await fetch(`${API_BASE}/watchlist/brain/top-picks`);
        const data = await res.json();

        if (data.ok) {
            const picks = data.picks;

            // Display top picks with regime-aware scoring
            const picksHtml = picks.map((pick, i) => `
                <div class="watchlist-pick" style="margin-bottom: 12px; padding: 12px; background: var(--card-bg); border-radius: 8px;">
                    <div style="display: flex; justify-content: space-between;">
                        <div>
                            <strong style="font-size: 1.1rem;">${i+1}. ${pick.ticker}</strong>
                            <span style="margin-left: 8px; color: var(--text-muted);">${pick.signal_quality}</span>
                        </div>
                        <div style="font-size: 1.1rem; font-weight: 700; color: var(--green);">
                            ${pick.score.toFixed(1)}/10
                        </div>
                    </div>
                    <div style="font-size: 0.875rem; color: var(--text-muted); margin-top: 4px;">
                        ${pick.reasoning}
                    </div>
                    <div style="margin-top: 8px; font-size: 0.875rem;">
                        <span>Price: $${pick.current_price?.toFixed(2) || 'N/A'}</span>
                        ${pick.suggested_size ? `<span style="margin-left: 16px;">Size: ${pick.suggested_size}</span>` : ''}
                    </div>
                </div>
            `).join('');

            document.getElementById('brain-top-picks').innerHTML = picksHtml;
        }
    } catch (error) {
        console.error('Error fetching brain picks:', error);
    }
}
```

---

## Value Proposition

### Minimal Integration (Proposal 1)
**Effort**: 5 minutes
**Value**: Watchlist scoring improves as system learns
**Risk**: Zero

### Moderate Integration (Proposal 2)
**Effort**: 30 minutes
**Value**: Regime-aware stock prioritization
**Risk**: Low

### Full Integration (Proposal 3)
**Effort**: 2-3 hours
**Value**: Fully autonomous watchlist curation
**Risk**: Moderate (needs testing)

---

## Recommendation

**Start with Proposal 1** today (5 minutes):
- Replace hardcoded weights with learned weights
- Immediate benefit, zero risk

**Add Proposal 2** this week (30 minutes):
- Regime-aware recommendations
- Significant value add

**Consider Proposal 3** after validation (2-3 hours):
- Full "Watchlist Brain" for autonomous curation
- Most powerful, but needs careful testing

---

## Testing Plan

```bash
# Test Proposal 1
python3 -c "
from src.watchlist.watchlist_manager import get_watchlist_manager
from src.learning import get_learning_brain

wm = get_watchlist_manager()
brain = get_learning_brain()

# Add test item
wm.add_item('NVDA', notes='Test integration')

# Score with learned weights
item = wm.get_item('NVDA')
item.technical_score = 8
item.ai_confidence = 0.85
item.story_score = 7
item.x_sentiment_score = 0.6

score = item.calculate_overall_score(learned_weights=brain.current_weights)
print(f'Score with learned weights: {score}/10')
"
```

---

**Question for you:** Which proposal interests you most? I can implement any of them right now.
