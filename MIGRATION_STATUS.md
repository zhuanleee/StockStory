# GitHub Pages + Modal Migration Status

## Goal
Migrate from Digital Ocean ($35/month) to GitHub Pages + Modal ($15/month)
**Savings: $20/month = $240/year** 💰

---

## Phase 1: Core API Endpoints ⏳ IN PROGRESS

### ✅ Completed:
- [x] Created `modal_api.py` with core endpoints
- [x] Added Modal Volume for persistent storage
- [x] Updated `modal_scanner.py` to save JSON results
- [x] Added Telegram notifications after scans
- [x] Updated GitHub Actions to deploy API
- [x] Triggered deployment (running now)

### 🔄 Next Steps:
1. **Get Modal API URLs** (after deployment completes)
2. **Update dashboard** to use Modal URLs
3. **Test core endpoints**:
   - GET /health
   - GET /scan
   - GET /ticker/:ticker
   - POST /scan/trigger
4. **Enable GitHub Pages**
5. **Verify dashboard works**

### 📝 Deployment Status:
- **Scanner**: ✅ Deployed (GPU-enabled, daily 6 AM PST)
- **API**: ⏳ Deploying now...
- **Dashboard**: ⏳ Pending (update URLs)

---

## Phase 2: Additional Endpoints 📋 PLANNED

Endpoints still on Digital Ocean (to migrate later):

### High Priority:
- [ ] `/briefing` - AI briefing
- [ ] `/conviction/alerts` - High conviction alerts
- [ ] `/theme-intel/radar` - Theme radar
- [ ] `/sec/ma-radar` - M&A radar

### Medium Priority:
- [ ] `/supplychain/*` - Supply chain features
- [ ] `/contracts/*` - Government contracts
- [ ] `/patents/*` - Patent analysis
- [ ] `/earnings` - Earnings data

### Low Priority (if needed):
- [ ] `/trades/*` - Trading features
- [ ] `/evolution/*` - Parameter learning UI
- [ ] `/sec/*` - SEC filings detail views

**Note**: Many of these may be unused. Will monitor usage before migrating.

---

## Architecture Comparison

### Before (Current):
```
Digital Ocean ($20/month)
├─ Static Dashboard (HTML/JS)
├─ Flask API Server (40+ endpoints)
└─ Postgres Database

Modal ($15/month)
└─ Background Scanner (GPU)

Total: $35/month
```

### After (Target):
```
GitHub Pages (FREE)
└─ Static Dashboard (HTML/JS)

Modal ($15/month)
├─ Background Scanner (GPU, daily 6 AM)
├─ API Endpoints (core 4, then more)
└─ Modal Volume (persistent storage)

Total: $15/month (save $20/month!)
```

### Telegram (Unchanged):
```
GitHub Actions (FREE)
├─ Story Alerts (every 30 min)
├─ Earnings Alerts (daily)
└─ Price Alerts

Modal (NEW)
└─ Scan completion notifications
```

---

## Testing Checklist

### Before Switching:
- [ ] Modal API URLs retrieved
- [ ] Test GET /health → returns 200
- [ ] Test GET /scan → returns scan data
- [ ] Test GET /ticker/NVDA → returns ticker data
- [ ] Test POST /scan/trigger?mode=quick → triggers scan
- [ ] Dashboard updated with new URLs
- [ ] Dashboard works on localhost
- [ ] GitHub Pages enabled
- [ ] Dashboard works on GitHub Pages
- [ ] All core features working
- [ ] Telegram still working

### After Switching:
- [ ] Monitor for errors (1 week)
- [ ] Check user feedback
- [ ] Verify costs reduced
- [ ] Delete Digital Ocean app

---

## Rollback Plan

If something breaks:
1. Revert dashboard to use DO URLs (git revert)
2. Keep DO running until issues fixed
3. Fix Modal API issues
4. Try migration again

---

## Timeline

- **Day 1** (Today): Deploy core Modal API ✅
- **Day 2**: Update dashboard, enable GitHub Pages, test
- **Day 3**: Monitor, fix issues
- **Week 1**: Full transition, monitor stability
- **Week 2**: Add more endpoints (Phase 2) if needed
- **Week 3**: Delete Digital Ocean, full savings!

---

## Cost Breakdown

### Current (Digital Ocean + Modal):
- Digital Ocean: $20/month
- Modal: $15/month
- **Total: $35/month**

### After Migration (GitHub Pages + Modal):
- GitHub Pages: **FREE**
- Modal: $15/month
- **Total: $15/month**

### Savings:
- **$20/month**
- **$240/year**
- **$1,200 over 5 years**

---

## Next Immediate Action

**Wait for deployment to complete** (check status):
```bash
gh run list --workflow=deploy_modal.yml --limit 1
gh run view --log
```

**Then get Modal API URLs**:
```bash
modal app list
```

**Then update dashboard** (docs/index.html line 1540-1542)
