# Dashboard Enhancements Plan

## Current Dashboard Tabs
1. Overview - Market summary, top stocks
2. Scan Results - Latest scan data
3. Watchlist - Tracked stocks
4. Learning - Learning system metrics (added earlier)
5. Themes - Theme performance
6. Theme Radar - Theme detection
7. SEC Intel - SEC filings
8. Trades - Trade history
9. Analytics - Performance analytics

---

## Proposed Enhancements

### 1. New "Intelligence" Tab ⭐
**Purpose**: Visualize all new integrated intelligence sources

**Components**:
- **Government Contracts Timeline**
  - Recent contracts by company
  - Contract value over time
  - Top defense/infrastructure plays
  - Filter by theme (defense, space, cloud, etc.)

- **Patent Activity Chart**
  - Recent patent filings by company
  - Innovation heatmap by sector
  - Patent velocity trends
  - Company comparison

- **Supply Chain Visualization**
  - Theme → Leaders → Suppliers → Infrastructure
  - Interactive network graph
  - Role-based scoring explanation

- **Catalyst Sources Summary**
  - Breakdown: News vs Contracts vs Patents
  - Catalyst type distribution
  - Recency heatmap

---

### 2. Enhanced "Learning" Tab
**Current** (from earlier session):
- Component weights chart
- Learning progress
- Trade outcomes
- Regime detection
- Thompson sampling
- PPO training metrics

**Enhancements**:
- ✅ Already has 6 Chart.js visualizations
- Add: Component weight evolution over time (line chart)
- Add: Win rate by component (bar chart)
- Add: Earnings intelligence contribution (new Component #38)
- Add: Trade outcome distribution by market regime

---

### 3. Enhanced "Scan Results" Tab
**Current**: Table of scan results

**Enhancements**:
- Add column: Supply chain role (leader/supplier/etc.)
- Add column: Government contract indicator (🏛️ if recent contract)
- Add column: Patent activity indicator (📜 if recent patents)
- Add column: AI brain confidence (if USE_AI_BRAIN_RANKING enabled)
- Add filter: By supply chain role
- Add filter: By catalyst type

---

### 4. Enhanced "Analytics" Tab
**Enhancements**:
- AI brain decision accuracy over time
- Component performance breakdown
- Supply chain role performance (do leaders outperform suppliers?)
- Catalyst type performance (which catalysts lead to wins?)
- Learning curve visualization (improvement over time)

---

## Implementation Priority

### Phase 1: Intelligence Tab (High Impact)
**Estimated Time**: 2-3 hours
**Components**:
1. Government contracts timeline (Chart.js timeline)
2. Patent activity chart (Chart.js bar)
3. Supply chain visualization (D3.js or simple HTML)

### Phase 2: Enhanced Learning Tab
**Estimated Time**: 1-2 hours
**Components**:
1. Component weight evolution (already have framework)
2. Win rate by component
3. Earnings contribution chart

### Phase 3: Scan Results Enhancements
**Estimated Time**: 1-2 hours
**Components**:
1. New table columns
2. Filter controls
3. Icons/indicators

### Phase 4: Analytics Enhancements
**Estimated Time**: 2-3 hours
**Components**:
1. AI brain accuracy tracking
2. Component performance breakdown
3. Role-based performance analysis

---

## API Endpoints Needed

### For Intelligence Tab
```javascript
// Government contracts
GET /api/gov-contracts/recent
GET /api/gov-contracts/by-company/{ticker}
GET /api/gov-contracts/by-theme/{theme_id}

// Patents
GET /api/patents/recent
GET /api/patents/by-company/{ticker}
GET /api/patents/trends

// Supply chain
GET /api/themes/supply-chain/{theme_id}
```

### For Learning Tab (already exist)
```javascript
GET /api/learning/stats
GET /api/learning/weights-history
GET /api/learning/outcomes
```

### For Scan Results (enhancement)
```javascript
GET /api/scan/latest  // Enhanced with new fields
```

---

## Technical Stack

**Frontend**:
- Chart.js 4.4.0 (already loaded)
- HTML/CSS/JavaScript (no framework needed)
- Fetch API for data loading

**Backend** (Flask):
- Need to expose new API endpoints
- JSON responses
- CORS enabled

**Data Sources**:
- Government contracts: src/data/gov_contracts.py
- Patents: src/data/patents.py
- Supply chain: SUPPLY_CHAIN_MAP in story_scoring.py
- Learning: src/learning/ modules

---

## MVP for This Session

**Goal**: Quick wins that demonstrate value

**Scope**:
1. Add "Intelligence" tab to dashboard
2. Add government contracts timeline chart
3. Add patent activity chart
4. Add supply chain role indicators to scan results
5. Document new features

**Out of Scope** (for future sessions):
- Full D3.js network graphs
- Real-time updates
- Advanced filtering
- Mobile responsive design tweaks

---

## Success Metrics

**User Can**:
- ✅ See which companies have recent government contracts
- ✅ See which companies have patent filing activity
- ✅ Understand supply chain roles (leader vs supplier)
- ✅ Visualize learning system performance
- ✅ Track catalyst source distribution

**System Shows**:
- ✅ All integrated intelligence sources
- ✅ Clear value of each component
- ✅ Learning system improvements over time
- ✅ AI brain decision patterns

---

**Next Steps**:
1. Create Intelligence tab HTML
2. Add Chart.js visualizations
3. Connect to existing API endpoints (or create stubs)
4. Test with sample data
5. Document usage

---

**Status**: READY TO IMPLEMENT
**Estimated Total Time**: 6-8 hours (MVP: 2-3 hours)
**Dependencies**: None (all data modules already integrated)
