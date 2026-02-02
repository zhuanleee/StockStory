# Earnings & Executive Analysis System

## Overview

Complete integration of earnings call transcripts and executive commentary analysis into the stock scanner. This system provides deep insights into management sentiment, forward guidance, and executive positioning.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  EARNINGS INTELLIGENCE                       │
│                    (Component #38)                           │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
        ▼                  ▼                  ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  Transcript  │  │  Executive   │  │   Earnings   │
│   Fetcher    │  │ Commentary   │  │   Calendar   │
│ (Alpha Vantage)│  │   Tracker    │  │   (Timing)   │
└──────────────┘  └──────────────┘  └──────────────┘
        │                  │                  │
        └──────────────────┼──────────────────┘
                           ▼
                  ┌──────────────┐
                  │  AI Analysis │
                  │ (xAI Grok)   │
                  └──────────────┘
                           │
                           ▼
                  ┌──────────────┐
                  │   Scoring    │
                  │  (0-1 scale) │
                  └──────────────┘
```

## Components

### 1. Transcript Fetcher (`src/data/transcript_fetcher.py`)

Fetches earnings call transcripts from Alpha Vantage API.

**Features:**
- Automatic caching (90-day TTL)
- Latest transcript retrieval
- Quarter-specific queries
- Transcript summaries for AI analysis
- Recency checks

**Usage:**
```python
from src.data.transcript_fetcher import fetch_latest_transcript

# Get latest earnings transcript
transcript = fetch_latest_transcript('NVDA')

# Get summary for AI (first 2000 chars)
summary = get_transcript_summary('NVDA', max_length=2000)

# Check if recent earnings call exists
has_recent = has_recent_earnings_call('NVDA', days=45)
```

**API Configuration:**
- Requires `ALPHA_VANTAGE_API_KEY` environment variable
- Available in Railway deployment
- Free tier: 25 API calls/day
- Cached results avoid repeated calls

### 2. Executive Commentary Tracker (`src/intelligence/executive_commentary.py`)

Aggregates executive commentary from multiple sources.

**Data Sources:**
1. **SEC 8-K Filings** - Significant events, often contain forward guidance
2. **News Articles** - CEO/CFO quotes from financial news
3. **Press Releases** - Official company announcements
4. **Social Media** (future) - Executive Twitter/X accounts

**Features:**
- Multi-source aggregation
- Sentiment analysis (bullish/neutral/bearish)
- Guidance tone detection (raised/maintained/lowered)
- Topic extraction (growth, margins, products, etc.)
- Executive name extraction
- 12-hour cache TTL

**Usage:**
```python
from src.intelligence.executive_commentary import get_executive_commentary

# Get comprehensive commentary summary
commentary = get_executive_commentary('TSLA', days_back=30)

# Check fields
print(commentary.overall_sentiment)  # bullish/neutral/bearish
print(commentary.guidance_tone)      # raised/maintained/lowered/none
print(commentary.key_themes)         # ['growth', 'products', 'margins']
print(commentary.recent_comments)    # List[ExecutiveComment]
```

**Commentary Structure:**
```python
@dataclass
class ExecutiveComment:
    ticker: str
    executive_name: Optional[str]
    executive_title: Optional[str]  # CEO, CFO, etc.
    source: str  # sec_filing, news, press_release
    source_url: str
    date: str
    content: str
    sentiment: str  # bullish, neutral, bearish
    topics: List[str]
    confidence: float
```

### 3. AI Earnings Analyzer (Enhanced)

Uses xAI Grok to analyze earnings call transcripts.

**Analysis Output:**
- **Management Tone**: bullish/neutral/bearish
- **Guidance Changes**: List of forward guidance updates
- **Growth Catalysts**: Key growth drivers mentioned
- **Risks & Concerns**: Challenges and headwinds
- **Competitive Positioning**: Market position assessment
- **Overall Assessment**: 2-3 sentence summary
- **Confidence Score**: 0-1 reliability

**Integration:**
```python
from src.ai.ai_enhancements import analyze_earnings

analysis = analyze_earnings(
    ticker='NVDA',
    transcript=transcript_text,
    earnings_data={'eps': 5.16, 'eps_estimate': 5.01}
)

print(analysis.management_tone)      # "bullish"
print(analysis.guidance_changes)     # ["Raised FY guidance", "Increased margin targets"]
print(analysis.growth_catalysts)     # ["AI demand", "Data center growth", "New products"]
print(analysis.confidence)           # 0.85
```

### 4. Enhanced Earnings Scorer

**Component #38** in the learning system, now with AI-powered insights.

**Scoring Components:**

1. **Timing Score (40% weight)**
   - Post-earnings window (0-30 days): HIGH score
   - Far from earnings (>14 days): GOOD score
   - Near earnings (3-14 days): MODERATE score
   - Earnings imminent (0-2 days): LOW score

2. **Historical Performance (40% weight)**
   - Beat rate (% of times beat estimates)
   - Average EPS surprise
   - Historical earnings growth

3. **Forward Guidance (20% weight)** - NEW!
   - AI-analyzed management tone
   - Guidance changes from transcripts
   - Executive commentary sentiment
   - Growth catalysts vs. risks

**Enhanced Features:**
- ✅ AI transcript analysis integration
- ✅ Executive commentary signals
- ✅ Persistent caching (7-day TTL)
- ✅ Guidance tone detection
- ✅ Multi-source sentiment aggregation

**Usage:**
```python
from src.scoring.earnings_scorer import get_earnings_scorer

scorer = get_earnings_scorer()

# Get confidence score (0-1)
confidence = scorer.score('NVDA')
# Returns: 0.85 (high confidence - good earnings setup)

# Get risk level
risk = scorer.get_earnings_risk_level('NVDA')
# Returns: "very_low"

# Check if should avoid entry
avoid = scorer.should_avoid_entry('NVDA', threshold=0.3)
# Returns: False (safe to enter)

# Get full features
features = scorer.get_features('NVDA')
print(features.has_earnings_soon)      # False
print(features.days_until_earnings)    # 28
print(features.beat_rate)              # 85.0
print(features.guidance_tone)          # "bullish"
print(features.earnings_confidence)    # 0.85
```

## Integration Flow

### Scanner Integration

The earnings intelligence is automatically integrated into the async scanner:

```python
# In src/core/async_scanner.py
from src.scoring.earnings_scorer import get_earnings_scorer

earnings_scorer = get_earnings_scorer()

# For each ticker:
earnings_confidence = earnings_scorer.score(ticker)

# Used in ComponentScores for learning system
scores = ComponentScores(
    theme_score=0.75,
    technical_score=0.82,
    ai_confidence=0.90,
    x_sentiment_score=0.68,
    earnings_confidence=earnings_confidence,  # Component #38
    institutional_flow_score=0.55
)
```

### Learning System Integration

The earnings confidence score is Component #38 in the 6-component learning system:

1. **Theme Score** (26% weight)
2. **Technical Score** (22% weight)
3. **AI Confidence** (22% weight)
4. **X Sentiment** (18% weight)
5. **Earnings Confidence** (5% weight) ← NEW
6. **Institutional Flow** (7% weight)

The learning system adapts these weights based on outcome feedback.

## Caching Strategy

### Three-Layer Cache

1. **Transcript Cache** (90 days)
   - Location: `data/earnings_transcripts/transcript_cache.json`
   - Why: Transcripts don't change after earnings call

2. **Analysis Cache** (7 days)
   - Location: `data/earnings_analysis/ai_analysis_cache.json`
   - Why: AI analysis is expensive, results stable

3. **Commentary Cache** (12 hours)
   - Location: `data/executive_commentary/commentary_cache.json`
   - Why: News and filings update frequently

### Cache Management

```python
# Clear all caches
from src.data.transcript_fetcher import get_transcript_fetcher
fetcher = get_transcript_fetcher()
fetcher.clear_cache()  # Clear all transcripts

# Clear specific ticker
fetcher.clear_cache('NVDA')  # Clear NVDA only
```

## API Requirements

### Alpha Vantage API
- **Endpoint**: `EARNINGS_CALL_TRANSCRIPT`
- **Key Location**: Railway environment variable `ALPHA_VANTAGE_API_KEY`
- **Rate Limit**: 25 calls/day (free tier)
- **Documentation**: https://www.alphavantage.co/documentation/

### xAI Grok API
- **Purpose**: AI analysis of transcripts
- **Key Location**: `XAI_API_KEY` environment variable
- **Cost**: ~$0.002 per analysis (2000 tokens @ $1/million)

## Performance Considerations

### Cost Optimization
- Transcripts cached for 90 days → No repeated API calls
- AI analysis cached for 7 days → ~$0.002 per ticker per week
- For 50 active positions: ~$0.10/week AI cost

### Speed
- Cache hit: <1ms
- Transcript fetch: ~500ms
- AI analysis: ~2s (xAI 2x speedup)
- Total cold start: ~2.5s per ticker
- Warm cache: <1ms per ticker

### API Budget
- Free tier: 25 transcripts/day
- Typical usage: 5-10 new transcripts/day
- Well within free tier limits

## Examples

### Example 1: Pre-Earnings Risk Check

```python
from src.scoring.earnings_scorer import get_earnings_scorer

scorer = get_earnings_scorer()

# Check multiple positions
positions = ['NVDA', 'TSLA', 'AAPL', 'MSFT']

risky = []
for ticker in positions:
    if scorer.should_avoid_entry(ticker, threshold=0.3):
        features = scorer.get_features(ticker)
        risky.append({
            'ticker': ticker,
            'days_until': features.days_until_earnings,
            'risk': scorer.get_earnings_risk_level(ticker)
        })

print("⚠️ Positions with earnings risk:")
for r in risky:
    print(f"  {r['ticker']}: {r['days_until']} days, {r['risk']} risk")
```

Output:
```
⚠️ Positions with earnings risk:
  TSLA: 2 days, very_high risk
  AAPL: 5 days, high risk
```

### Example 2: Guidance Signal Detection

```python
from src.intelligence.executive_commentary import get_executive_commentary

# Get recent commentary
commentary = get_executive_commentary('NVDA', days_back=30)

# Check for guidance changes
if commentary.guidance_tone in ['raised', 'lowered']:
    print(f"🎯 Guidance Change Detected!")
    print(f"  Ticker: {commentary.ticker}")
    print(f"  Guidance: {commentary.guidance_tone.upper()}")
    print(f"  Sentiment: {commentary.overall_sentiment}")
    print(f"  Key Themes: {', '.join(commentary.key_themes)}")
```

Output:
```
🎯 Guidance Change Detected!
  Ticker: NVDA
  Guidance: RAISED
  Sentiment: bullish
  Key Themes: AI demand, Data center growth, Margin expansion
```

### Example 3: Post-Earnings Analysis

```python
from src.data.transcript_fetcher import fetch_latest_transcript
from src.ai.ai_enhancements import analyze_earnings
from src.intelligence.executive_commentary import get_executive_commentary

ticker = 'MSFT'

# Get transcript analysis
transcript = fetch_latest_transcript(ticker)
if transcript:
    analysis = analyze_earnings(ticker, transcript.transcript)

    print(f"📊 {ticker} Earnings Analysis:")
    print(f"  Management Tone: {analysis.management_tone}")
    print(f"  Guidance Changes: {len(analysis.guidance_changes)}")
    for change in analysis.guidance_changes[:3]:
        print(f"    • {change}")

    print(f"\n  Growth Catalysts:")
    for catalyst in analysis.growth_catalysts[:3]:
        print(f"    • {catalyst}")

# Get executive commentary
commentary = get_executive_commentary(ticker, days_back=7)
print(f"\n📰 Recent Commentary:")
print(f"  Overall Sentiment: {commentary.overall_sentiment}")
print(f"  Recent Comments: {len(commentary.recent_comments)}")
```

## Dashboard Integration

The intelligence dashboard (`docs/index.html`) now includes earnings analysis:

```javascript
// Fetch earnings intelligence
async function loadEarningsIntel(ticker) {
    const response = await fetch(`/api/earnings/analysis/${ticker}`);
    const data = await response.json();

    // Display management tone
    displayManagementTone(data.management_tone);

    // Show guidance changes
    displayGuidanceChanges(data.guidance_changes);

    // Plot sentiment timeline
    plotSentimentTimeline(data.commentary.recent_comments);
}
```

## Testing

### Test Transcript Fetcher
```bash
python src/data/transcript_fetcher.py NVDA
```

### Test Executive Commentary
```bash
python src/intelligence/executive_commentary.py TSLA
```

### Test Earnings Scorer
```bash
python src/scoring/earnings_scorer.py
```

## Future Enhancements

1. **Social Media Integration**
   - Track CEO/CFO Twitter/X accounts
   - Analyze executive LinkedIn posts
   - Monitor CNBC/Bloomberg interview transcripts

2. **Guidance Tracking History**
   - Track guidance changes over time
   - Compare actual results vs. prior guidance
   - Calculate guidance accuracy scores

3. **Peer Comparison**
   - Compare management tone across sector
   - Identify relative optimism/pessimism
   - Detect industry-wide trends

4. **Conference Call Q&A Analysis**
   - Analyze analyst questions
   - Detect evasive answers
   - Measure management confidence

5. **Automated Transcript Summaries**
   - Generate bullet-point summaries
   - Extract key quotes
   - Highlight surprises and changes

## Troubleshooting

### No Transcript Found
**Cause**: Alpha Vantage may not have transcript for this ticker
**Solution**: Check if ticker is in S&P 500, wait for next earnings call

### AI Analysis Failed
**Cause**: xAI API rate limit or error
**Solution**: Check XAI_API_KEY, verify API credits, retry after delay

### Cache Issues
**Cause**: Corrupted cache files
**Solution**:
```bash
rm -rf data/earnings_transcripts/
rm -rf data/earnings_analysis/
rm -rf data/executive_commentary/
```

### Low Confidence Scores
**Cause**: Limited data available (new IPO, small cap)
**Solution**: System returns neutral 0.5 score when data unavailable

## References

- Alpha Vantage API: https://www.alphavantage.co/documentation/
- xAI Grok API: https://x.ai/api
- SEC EDGAR: https://www.sec.gov/edgar/searchedgar/companysearch.html
- Component #38 Learning System: `src/learning/rl_models.py`

---

**Status**: ✅ COMPLETE
**Integration**: ACTIVE in async_scanner.py
**Learning**: Component #38 (5% weight)
**Data Sources**: 3 (Transcripts, Commentary, Calendar)
**Cache Strategy**: 3-tier (90d/7d/12h)
**API Cost**: ~$0.10/week for 50 tickers
