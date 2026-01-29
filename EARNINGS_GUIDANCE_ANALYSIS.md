# Earnings & Forward Guidance Analysis - Current Capabilities

## ✅ YES - You Have Earnings Analysis!

Your system has comprehensive earnings and forward guidance analysis capabilities.

---

## Current Features

### 1. Earnings Calendar Tracking (`src/analysis/earnings.py`)

**What It Does:**
- Tracks 200+ stocks for upcoming earnings
- Multi-source data (Polygon API + yfinance fallback)
- 14-day forward calendar
- High-impact earnings flagging

**Data Collected:**
```python
{
    'ticker': 'NVDA',
    'next_date': datetime.date(2026, 02, 15),
    'days_until': 17,
    'eps_estimate': 2.45,              # Expected EPS
    'revenue_estimate': 22000000000,    # Expected revenue
    'historical_surprise': 15.2,        # Avg surprise %
    'beat_rate': 85.0,                  # % times beat estimates
    'high_impact': True                 # Market mover flag
}
```

**Beat/Miss Tracking:**
- Records last 20 earnings results per stock
- Calculates historical surprise patterns
- Tracks price reactions to beats/misses
- Learning database: 500 recent earnings

**Key Functions:**
- `get_earnings_info(ticker)` - Full earnings data
- `get_upcoming_earnings(days_ahead=14)` - Calendar
- `check_earnings_soon(tickers, days=3)` - Risk warning
- `record_earnings_result()` - Post-earnings tracking
- `get_earnings_patterns()` - Historical analysis

### 2. Forward Guidance Analysis (`src/ai/ai_enhancements.py`)

**What It Does:**
- AI-powered earnings call transcript analysis
- Extracts forward guidance changes
- Assesses management tone (bullish/neutral/bearish)
- Identifies growth catalysts and risks

**Analysis Output:**
```python
EarningsAnalysis(
    ticker='NVDA',
    management_tone='bullish',
    guidance_changes=[
        'Raised FY2025 revenue guidance to $120B (from $115B)',
        'Increased gross margin outlook to 74-75%'
    ],
    growth_catalysts=[
        'AI demand visibility through 2026',
        'New Blackwell GPU ramp in Q2',
        'Data center growth accelerating'
    ],
    risks_concerns=[
        'Supply constraints in advanced packaging',
        'Geopolitical risks (China export controls)',
        'Increasing competition from custom silicon'
    ],
    competitive_positioning='Clear market leader in AI training...',
    overall_assessment='Strong beat with raised guidance...',
    confidence=0.85
)
```

**AI Analysis Features:**
- Management tone detection
- Guidance change extraction
- Catalyst identification
- Risk assessment
- Competitive positioning
- Overall sentiment scoring

**Usage:**
```python
from src.ai.ai_enhancements import get_ai_engine

ai = get_ai_engine()

# Analyze earnings call
analysis = ai.analyze_earnings_call(
    ticker='NVDA',
    transcript=earnings_transcript,  # From SEC or provider
    earnings_data={'eps': 2.55, 'eps_estimate': 2.45}
)

print(f"Management Tone: {analysis.management_tone}")
print(f"Guidance Changes: {analysis.guidance_changes}")
print(f"Catalysts: {analysis.growth_catalysts}")
```

### 3. Integration Points

**Watchlist Integration:**
- Earnings risk warnings for watchlist items
- Days until earnings tracking
- Historical beat rate display

**Scanner Integration:**
- Filters out stocks with earnings in next 3 days
- Flags post-earnings momentum setups
- Beat/raise catalyst scanning

**AI Brain Integration:**
- Earnings considerations in decision-making
- X Intelligence monitors earnings sentiment
- Risk advisor warns about earnings exposure

---

## What's Working Well

### Strengths

1. **Multi-Source Data**
   - Primary: Polygon API (fast, reliable)
   - Fallback: yfinance (free, good coverage)
   - Resilient architecture

2. **Historical Learning**
   - Tracks 500 recent earnings results
   - Beat/miss patterns
   - Price reaction analysis
   - Company-specific beat rates

3. **AI-Powered Analysis**
   - Uses xAI for 2x faster analysis
   - Extracts guidance changes automatically
   - Identifies hidden risks
   - Management tone assessment

4. **Risk Management**
   - Warns before earnings
   - Historical surprise data
   - Beat rate statistics
   - Price reaction patterns

---

## Integration Gap: Not Connected to Learning System ⚠️

### Current State

**Earnings data is collected but NOT used by the learning system:**

```python
# Learning system (Tier 1-4) trains on:
✅ Theme scores
✅ Technical scores
✅ AI confidence
✅ Sentiment scores

# But NOT on:
❌ Earnings proximity
❌ Historical beat rates
❌ Forward guidance strength
❌ Management tone
```

### The Opportunity

Earnings could be a **powerful component** in the learning system!

**What could be learned:**
- Does trading near earnings help or hurt?
- Do high beat-rate stocks perform better?
- Does bullish guidance predict wins?
- What's the optimal earnings timing?

---

## Suggested Enhancement: "Earnings Intelligence Component"

### Proposal: Add Earnings as Component #38

Make earnings data a learnable component in your 4-tier system.

### What It Would Include

**Earnings Features (for scoring):**
```python
@dataclass
class EarningsFeatures:
    """Earnings intelligence for learning."""

    # Timing
    has_earnings_soon: bool          # Within 3 days
    days_until_earnings: Optional[int]

    # Historical Performance
    beat_rate: float                 # 0-100%
    avg_surprise: float              # Average EPS surprise %

    # Forward Guidance
    guidance_tone: str               # bullish/neutral/bearish
    guidance_strength: float         # 0-1 confidence
    guidance_raised: bool            # Recently raised?

    # Composite Score
    earnings_confidence: float       # 0-1 overall score
```

**How Learning Would Work:**

```python
# Tier 1: Learn earnings importance
weights = {
    'theme': 0.30,
    'technical': 0.25,
    'ai': 0.25,
    'sentiment': 0.20,
    'earnings': 0.10  # ← NEW: Learned weight for earnings
}

# Tier 2: Regime-specific earnings strategies
if regime == MarketRegimeType.BULL_MOMENTUM:
    # In bull markets, strong earnings guidance matters more
    earnings_weight = 0.15
elif regime == MarketRegimeType.CHOPPY_RANGE:
    # In choppy markets, avoid earnings uncertainty
    earnings_weight = -0.10  # Negative = avoid earnings stocks
```

**Scoring Logic:**
```python
def calculate_earnings_score(ticker: str) -> float:
    """Calculate 0-1 earnings confidence score."""

    info = get_earnings_info(ticker)

    # Factor 1: Earnings timing (prefer post-earnings or far from earnings)
    days_until = info.get('days_until')
    if days_until is None:
        timing_score = 0.7  # Unknown = neutral
    elif days_until < 0:
        timing_score = 1.0  # Post-earnings = good
    elif days_until > 14:
        timing_score = 0.8  # Far from earnings = good
    elif days_until <= 3:
        timing_score = 0.2  # Earnings very soon = risky
    else:
        timing_score = 0.5  # Moderate risk

    # Factor 2: Historical performance
    beat_rate = info.get('beat_rate', 50) / 100.0  # Normalize to 0-1
    avg_surprise = info.get('historical_surprise', 0)
    surprise_score = min(1.0, max(0.0, (avg_surprise + 20) / 40))  # -20% to +20% → 0 to 1

    performance_score = (beat_rate * 0.6 + surprise_score * 0.4)

    # Factor 3: Forward guidance (if available)
    guidance_score = 0.5  # Default neutral

    # Try to get recent earnings analysis
    from src.ai.ai_enhancements import get_ai_engine
    ai = get_ai_engine()
    # Check if we have recent analysis cached
    # ... (implementation details)

    # Composite score
    earnings_confidence = (
        timing_score * 0.4 +
        performance_score * 0.4 +
        guidance_score * 0.2
    )

    return earnings_confidence
```

### Implementation Steps

**1. Create Earnings Scorer (30 minutes)**

```python
# File: src/scoring/earnings_scorer.py

class EarningsScorer:
    """Score stocks based on earnings intelligence."""

    def score(self, ticker: str) -> float:
        """Return 0-1 confidence score."""
        # Implementation above
        pass

    def get_features(self, ticker: str) -> EarningsFeatures:
        """Get all earnings features."""
        pass
```

**2. Integrate with Learning System (15 minutes)**

```python
# In learning_brain.py

@dataclass
class ComponentScores:
    theme_score: float
    technical_score: float
    ai_confidence: float
    x_sentiment_score: float
    earnings_confidence: float  # ← NEW

# In component weights
@dataclass
class ComponentWeights:
    theme: float = 0.30
    technical: float = 0.25
    ai: float = 0.23
    sentiment: float = 0.17
    earnings: float = 0.05  # ← NEW: Start small
```

**3. Update Scoring Logic (10 minutes)**

```python
# In decision calculation
overall_score = (
    scores.theme_score * weights.theme +
    scores.technical_score * weights.technical +
    scores.ai_confidence * 10 * weights.ai +
    scores.x_sentiment_score * 10 * weights.sentiment +
    scores.earnings_confidence * 10 * weights.earnings  # ← NEW
)
```

**4. Test & Validate (15 minutes)**

```python
# test_earnings_component.py
def test_earnings_learning():
    brain = get_learning_brain()

    # Stock with earnings tomorrow
    score1 = brain.score_ticker('NVDA')  # Should be lower risk score

    # Stock with earnings in 2 weeks
    score2 = brain.score_ticker('AAPL')  # Should be higher

    # Stock that consistently beats
    score3 = brain.score_ticker('MSFT')  # Should be higher
```

### Expected Results

**After 20-30 trades, learning system discovers:**

1. **Earnings Timing Patterns**
   - "Avoid trades 3 days before earnings"
   - "Post-earnings momentum is profitable"
   - "Far-from-earnings stocks are safer"

2. **Beat Rate Correlation**
   - "Stocks with 80%+ beat rate outperform"
   - "Guidance raises are strong buy signals"
   - "Consistent beaters deserve higher weight"

3. **Regime-Specific Strategies**
   - Bull market: Strong guidance matters more
   - Bear market: Avoid all earnings uncertainty
   - Choppy: Only trade post-earnings setups

4. **Automatic Weight Adjustment**
   ```
   Initial weights: earnings = 5%

   After learning:
   - Bull regime: earnings = 12% (learned it matters)
   - Bear regime: earnings = 2% (learned to avoid)
   - Crisis: earnings = -5% (learned to heavily avoid)
   ```

---

## Summary

### What You Have Today ✅

1. **Comprehensive Earnings Tracking**
   - 200+ stocks monitored
   - EPS/revenue estimates
   - Historical beat rates
   - Price reaction patterns

2. **AI Forward Guidance Analysis**
   - Transcript parsing
   - Guidance change extraction
   - Management tone assessment
   - Catalyst/risk identification

3. **Risk Integration**
   - Earnings warnings in watchlist
   - Scanner filters near earnings
   - Historical data for context

### What's Missing ❌

1. **Learning System Integration**
   - Earnings not a learnable component
   - No adaptive earnings strategies
   - Missing regime-specific handling

### Quick Win ⚡

**Add earnings as Component #38 (1 hour implementation):**
- Create `EarningsScorer` class
- Add to `ComponentScores` dataclass
- Start at 5% weight
- Let system learn optimal strategy

**Value:**
- Avoid earnings disasters
- Capitalize on post-earnings momentum
- Learn which companies to trust
- Regime-aware earnings strategies

---

## Recommendation

**Option A: Use What You Have (Today)**
- Earnings data is already collected
- AI analysis available on demand
- Manual review of earnings calendar
- Scanner avoids near-earnings stocks

**Option B: Add Earnings Learning (1 hour)**
- Make earnings a learnable component
- System discovers optimal strategies
- Automated earnings intelligence
- Higher win rate, lower risk

**My suggestion:** Start with Option A, add Option B after you validate the learning system with 50+ trades.

---

**Status:** ✅ Earnings analysis exists, ⚠️ not integrated with learning system

**Files:**
- `src/analysis/earnings.py` - Earnings calendar & tracking
- `src/ai/ai_enhancements.py` - AI guidance analysis
- Integration: Manual (not automatic)

**Next Step:** Decide if you want to add earnings as Component #38 in the learning system.
