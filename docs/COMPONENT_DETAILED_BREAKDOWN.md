# AI Components - Detailed Breakdown

## Component Analysis: What Each Feature Does

---

## Component #1: Trading Signal Explainer

### What It Does
Analyzes WHY a trading signal triggered by examining:
- Relative strength metrics
- Volume patterns
- Theme correlation
- Recent news catalysts
- Technical setup quality

### Inputs
```python
{
    'ticker': 'NVDA',
    'signal_type': 'momentum_breakout',
    'rs': 95,                    # Relative strength
    'volume_trend': '2.5x avg',  # Volume anomaly
    'theme': 'AI Infrastructure', # Theme membership
    'recent_news': '...',        # News context
    'price_action': {...}        # Price data
}
```

### Processing Logic
1. **Context Gathering**: Combines quantitative signals with qualitative news
2. **Pattern Recognition**: Identifies the setup type (breakout, continuation, reversal)
3. **Catalyst Identification**: Determines what's driving the move
4. **Risk Assessment**: Identifies primary failure modes
5. **Confidence Scoring**: Rates setup quality 0-1

### Outputs
```python
{
    'reasoning': "Why this setup is compelling",
    'catalyst': "What's driving this",
    'key_risk': "What could go wrong",
    'confidence': 0.85
}
```

### Decision Support
- **For Traders**: Should I take this signal?
- **For Scanners**: Which signals are highest quality?
- **For Alerts**: What details should I include?

### Data Flow
```
Scanner Results → Signal Explainer → Enhanced Signal + Reasoning
                                   ↓
                            Trader Decision Support
```

---

## Component #2: Earnings Intelligence

### What It Does
Processes earnings call transcripts to extract:
- Management sentiment (bullish/neutral/bearish)
- Guidance changes (raises, cuts, reaffirms)
- Growth catalysts mentioned
- Risks and concerns highlighted
- Competitive positioning assessment

### Inputs
```python
{
    'ticker': 'NVDA',
    'transcript': '...',          # Full or summary transcript
    'eps': 5.16,                  # Actual EPS
    'eps_estimate': 4.60,         # Consensus estimate
    'revenue': '22B',             # Revenue
    'prior_guidance': {...}       # Previous guidance
}
```

### Processing Logic
1. **Sentiment Analysis**: Analyzes management tone and word choice
2. **Guidance Extraction**: Identifies forward-looking statements
3. **Catalyst Mining**: Extracts growth drivers mentioned
4. **Risk Identification**: Finds concerns, warnings, headwinds
5. **Competitive Analysis**: Assesses market positioning claims
6. **Synthesis**: Generates overall assessment

### Outputs
```python
{
    'management_tone': 'bullish',
    'guidance_changes': ['Raising FY outlook', 'Q2 above consensus'],
    'growth_catalysts': ['AI demand', 'Data center growth', 'Supply easing'],
    'risks_concerns': ['Competition', 'Valuation', 'Supply chain'],
    'competitive_positioning': 'Market leader with 80%+ share',
    'overall_assessment': 'Exceptional results, strong visibility',
    'confidence': 0.90
}
```

### Decision Support
- **For Investors**: Should I buy/sell post-earnings?
- **For Traders**: Is this a gap-and-go or fade?
- **For Analysts**: What are the key takeaways?

### Data Flow
```
Earnings Release → Earnings Intelligence → Earnings Summary
                                        ↓
                              Portfolio Position Decisions
```

---

## Component #3: Market Health Monitor

### What It Does
Synthesizes market-wide metrics into actionable health assessment:
- Overall market condition (healthy/neutral/warning/concerning)
- Key risk signals (breadth deterioration, volatility spike, etc.)
- Positive signals (breadth expansion, low VIX, etc.)
- Recommended trading stance (offensive/neutral/defensive)

### Inputs
```python
{
    'breadth': 65,                # % stocks above 200MA
    'vix': 14.5,                  # Volatility index
    'new_highs': 150,             # 52-week highs
    'new_lows': 25,               # 52-week lows
    'advance_decline': 2.1,       # Advance/decline ratio
    'leading_sectors': [...],     # Top sectors
    'lagging_sectors': [...],     # Bottom sectors
    'market_internals': {...}     # Additional metrics
}
```

### Processing Logic
1. **Breadth Analysis**: Assesses participation (narrow vs broad)
2. **Volatility Assessment**: Evaluates fear/complacency levels
3. **Leadership Analysis**: Identifies rotation patterns
4. **Divergence Detection**: Finds price/breadth disconnects
5. **Risk Scoring**: Quantifies overall market risk
6. **Stance Recommendation**: Determines appropriate positioning

### Outputs
```python
{
    'health_rating': 'healthy',
    'concerning_signals': ['Rising VIX', 'Breadth narrowing'],
    'positive_signals': ['New highs expanding', 'Low volatility'],
    'recommended_stance': 'offensive',
    'narrative': '2-3 sentence summary',
    'risk_level': 3/10
}
```

### Decision Support
- **For Portfolio Managers**: Should I increase/decrease exposure?
- **For Traders**: Should I be aggressive or defensive?
- **For Risk Managers**: What's the current market risk level?

### Data Flow
```
Market Metrics → Market Health Monitor → Health Assessment
                                      ↓
                            Portfolio Positioning Decisions
```

---

## Component #4: Sector Rotation Analyst

### What It Does
Explains sector rotation patterns and market cycle positioning:
- Identifies current market cycle stage
- Explains WHY certain sectors are leading/lagging
- Predicts next likely rotation
- Provides sector-specific recommendations

### Inputs
```python
{
    'top_sectors': ['Technology', 'Industrials', 'Financials'],
    'lagging_sectors': ['Utilities', 'Real Estate', 'Staples'],
    'sector_performance': {...},  # 1-month returns
    'money_flow': 'Into cyclicals', # Flow direction
    'macro_context': {...}         # Economic data
}
```

### Processing Logic
1. **Cycle Identification**: Determines early/mid/late/recession stage
2. **Leadership Analysis**: Identifies which sectors lead/lag
3. **Causality Analysis**: Explains WHY rotation is occurring
4. **Macro Correlation**: Links to economic cycle
5. **Forward Projection**: Predicts next rotation
6. **Actionable Synthesis**: Generates trading implications

### Outputs
```python
{
    'market_cycle_stage': 'early',
    'leading_sectors': [...],
    'lagging_sectors': [...],
    'reasoning': 'Economic recovery drives cyclical preference...',
    'next_rotation_likely': 'Mid-cycle: Consumer Discretionary',
    'sector_recommendations': {...},
    'confidence': 0.80
}
```

### Decision Support
- **For Sector Traders**: Which sectors should I overweight?
- **For Market Timers**: Where are we in the cycle?
- **For Strategists**: What's the macro regime?

### Data Flow
```
Sector Data → Sector Rotation Analyst → Rotation Narrative
                                      ↓
                            Sector Allocation Decisions
```

---

## Component #5: Fact Verification System

### What It Does
Cross-references claims against multiple sources with AI reasoning:
- Verifies factual claims (true/false/partial/unverifiable)
- Identifies contradictions across sources
- Assesses source reliability
- Provides confidence scoring

### Inputs
```python
{
    'claim': 'NVIDIA Q4 revenue grew 265% YoY',
    'sources': [
        {'source': 'Reuters', 'headline': '...'},
        {'source': 'Bloomberg', 'headline': '...'},
        {'source': 'WSJ', 'headline': '...'}
    ],
    'context': {...}  # Additional context
}
```

### Processing Logic
1. **Claim Extraction**: Parses specific factual claims
2. **Source Matching**: Finds relevant information in each source
3. **Consistency Check**: Identifies agreement/disagreement
4. **Reasoning**: Explains verification logic
5. **Contradiction Detection**: Finds conflicting information
6. **Confidence Scoring**: Rates verification certainty

### Outputs
```python
{
    'verified': 'true',  # true/false/partial/unverifiable
    'confidence': 1.00,
    'reasoning': 'All 3 sources confirm 265% growth',
    'contradictions': [],
    'sources_checked': 3,
    'reliability_score': 0.95
}
```

### Decision Support
- **For Traders**: Can I trust this news?
- **For Risk Managers**: Is this claim verified?
- **For Content Filters**: Should I flag this as unreliable?

### Data Flow
```
News Claim → Fact Verification → Verification Result
                               ↓
                    News Reliability Filtering
```

---

## Component #6: Timeframe Synthesizer

### What It Does
Integrates multiple timeframe analysis into unified trade setup:
- Aligns daily/weekly/monthly trends
- Identifies timeframe conflicts
- Scores trade setup quality
- Recommends optimal entry timeframe

### Inputs
```python
{
    'ticker': 'NVDA',
    'daily': {
        'trend': 'bullish',
        'strength': 'strong',
        'indicators': {...}
    },
    'weekly': {
        'trend': 'bullish',
        'strength': 'moderate',
        'indicators': {...}
    },
    'monthly': {
        'trend': 'bullish',
        'strength': 'strong',
        'indicators': {...}
    }
}
```

### Processing Logic
1. **Alignment Check**: Determines if timeframes agree
2. **Conflict Resolution**: Identifies and explains divergences
3. **Trend Strength**: Assesses conviction across timeframes
4. **Entry Timing**: Determines best timeframe for entry
5. **Support/Resistance**: Identifies key levels across timeframes
6. **Quality Scoring**: Rates overall trade setup 1-10

### Outputs
```python
{
    'overall_alignment': 'aligned_bullish',
    'best_entry_timeframe': 'daily',
    'key_levels': {'support': 850, 'resistance': 950},
    'trade_quality_score': 9,
    'synthesis': 'Strong bullish alignment...',
    'conflicts': [],
    'confidence': 0.90
}
```

### Decision Support
- **For Swing Traders**: Should I enter this trade?
- **For Position Sizers**: How confident should I be?
- **For Entry Timing**: When should I pull the trigger?

### Data Flow
```
Multi-Timeframe Data → Timeframe Synthesizer → Trade Setup Rating
                                             ↓
                                    Entry/Exit Decisions
```

---

## Component #7: TAM Estimator

### What It Does
Estimates total addressable market expansion potential:
- Projects market size growth (CAGR)
- Identifies adoption stage (early/mid/mature)
- Lists growth drivers
- Assesses competitive intensity

### Inputs
```python
{
    'theme': 'AI Infrastructure',
    'current_players': ['NVDA', 'AMD', 'AVGO'],
    'context': 'Rapid AI chip demand growth',
    'current_tam': 200B,  # If known
    'penetration': 15%    # If known
}
```

### Processing Logic
1. **Market Sizing**: Estimates current TAM
2. **Growth Projection**: Calculates expected CAGR
3. **Adoption Analysis**: Determines market maturity stage
4. **Driver Identification**: Lists key growth factors
5. **Catalyst Discovery**: Finds expansion triggers
6. **Competition Assessment**: Evaluates market intensity

### Outputs
```python
{
    'cagr_estimate': 35.0,
    'adoption_stage': 'early',
    'growth_drivers': ['AI training demand', 'Inference workloads'],
    'expansion_catalysts': ['GPT-5', 'Enterprise adoption'],
    'competitive_intensity': 'high',
    'confidence': 0.85
}
```

### Decision Support
- **For Theme Investors**: Is this theme big enough?
- **For Long-term Holders**: What's the runway?
- **For Valuation**: How big can this market get?

### Data Flow
```
Theme Data → TAM Estimator → Market Size Projection
                           ↓
                  Theme Validation & Sizing
```

---

## Component #8: Corporate Action Analyzer

### What It Does
Analyzes impact of corporate actions (splits, buybacks, M&A):
- Predicts typical market reaction
- Explains corporate reasoning
- Cites historical precedents
- Assesses expected stock impact

### Inputs
```python
{
    'ticker': 'NVDA',
    'action_type': 'stock_split',
    'details': '10-for-1 split effective June 2024',
    'stock_price': 950,
    'market_cap': '2.3T',
    'context': {...}
}
```

### Processing Logic
1. **Action Classification**: Categorizes the corporate action
2. **Motivation Analysis**: Explains why company is doing this
3. **Historical Analysis**: Reviews similar past actions
4. **Impact Projection**: Estimates stock price effect
5. **Risk Identification**: Lists potential negative outcomes
6. **Timeline Assessment**: Determines impact duration

### Outputs
```python
{
    'typical_reaction': 'bullish',
    'reasoning': 'Lower price improves retail access...',
    'historical_precedents': '5-15% gains typical post-split',
    'expected_impact': '5-15% upward movement short-term',
    'key_risks': ['Doesn\'t change fundamentals'],
    'confidence': 0.80
}
```

### Decision Support
- **For Event Traders**: Should I trade this action?
- **For Portfolio Managers**: How will this affect holdings?
- **For Analysts**: What's the implication?

### Data Flow
```
Corporate Action → Action Analyzer → Impact Assessment
                                  ↓
                        Position Adjustment Decisions
```

---

## Component Characteristics Summary

| Component | Primary Function | Speed | Decision Support |
|-----------|-----------------|-------|------------------|
| **Signal Explainer** | Why signals trigger | 1.2s | Trade execution |
| **Earnings Intelligence** | Earnings analysis | 2-3s | Post-earnings positioning |
| **Market Health** | Market regime | 1.5s | Portfolio exposure |
| **Sector Rotation** | Cycle positioning | 1.5s | Sector allocation |
| **Fact Verification** | News verification | 1.5s | Information filtering |
| **Timeframe Synthesis** | Trade setup quality | 1.3s | Entry timing |
| **TAM Estimator** | Market sizing | 2s | Theme validation |
| **Action Analyzer** | Corporate action impact | 1.5s | Event trading |

---

## Component Dependencies

### Data Inputs Required

**Signal Explainer:**
- Scanner output
- Price/volume data
- News feed
- Theme membership

**Earnings Intelligence:**
- Earnings transcripts
- Financial data
- Consensus estimates

**Market Health:**
- Breadth indicators
- VIX/volatility
- Sector performance
- Advance/decline data

**Sector Rotation:**
- Sector ETF data
- Economic indicators
- Money flow metrics

**Fact Verification:**
- News sources
- Claims database
- Source reliability scores

**Timeframe Synthesis:**
- Daily/weekly/monthly charts
- Technical indicators
- Support/resistance levels

**TAM Estimator:**
- Theme definition
- Player list
- Industry research

**Action Analyzer:**
- Corporate filings
- Action details
- Stock price data

---

## Component Interactions (Current State)

**Currently:** All components are **independent**
- Each can be called separately
- No inter-component communication
- No shared context
- No hierarchical coordination

**Problem:** Components don't collaborate
- Earnings Intelligence doesn't inform Signal Explainer
- Market Health doesn't influence Trade Setup scoring
- Sector Rotation doesn't adjust TAM estimates

**Next Step:** Design Agentic Brain Architecture →

