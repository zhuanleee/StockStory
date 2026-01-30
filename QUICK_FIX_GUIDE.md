# Quick Fix Guide - Stock Scanner Dashboard
**Last Updated:** 2026-01-31

---

## 🔴 Current Status: BROKEN

**Why:**
1. Wrong API URL in config.js → 404 errors
2. No scan data in Modal Volume → Empty dashboard
3. Broken Telegram notifications → Import error

---

## ✅ Fixes Applied (Local)

1. **docs/js/config.js** - Fixed API URL to point to Modal
2. **modal_scanner.py** - Fixed Telegram (removed cross-app import)

---

## 🚀 Deploy Now (5 commands)

```bash
cd /Users/johnlee/stock_scanner_bot

# 1. Check what changed
git diff docs/js/config.js modal_scanner.py

# 2. Add files
git add docs/js/config.js modal_scanner.py FORENSIC_ANALYSIS_COMPLETE.md FIXES_APPLIED.md EXECUTIVE_SUMMARY.md QUICK_FIX_GUIDE.md

# 3. Commit
git commit -m "Fix critical dashboard issues: API URL + Telegram integration

- Fix config.js API URL (GitHub Pages /api → Modal API)
- Fix Telegram integration (remove cross-app import, use direct HTTP)
- Add forensic analysis and fix documentation"

# 4. Push
git push origin main

# 5. Monitor
echo "Watch: https://github.com/zhuanleee/stock_scanner_bot/actions"
```

---

## ⏱️ After Deployment (Wait 5 min, then run)

```bash
# Trigger first scan (requires Modal CLI auth)
modal run modal_scanner.py --daily

# OR wait for cron (next 6 AM PST)
```

---

## ✅ Verify Working

```bash
# 1. Check API has data
curl -s https://zhuanleee--stock-scanner-api-v2-create-fastapi-app.modal.run/scan | jq '.results | length'

# 2. Check dashboard config
curl -s https://zhuanleee.github.io/stock_scanner_bot/js/config.js | grep Modal

# 3. Open dashboard
open https://zhuanleee.github.io/stock_scanner_bot/
```

---

## 📋 Checklist

- [ ] Commit and push fixes (5 min)
- [ ] Wait for GitHub Actions (2 min)
- [ ] Verify deployment (2 min)
- [ ] Run first scan (10 min)
- [ ] Verify dashboard shows data (1 min)
- [ ] Check Telegram notification (instant)

**Total Time:** ~20 minutes

---

## 🆘 If Something Goes Wrong

**Rollback:**
```bash
git revert HEAD
git push origin main
```

**Debug:**
```bash
# Check logs
open https://github.com/zhuanleee/stock_scanner_bot/actions

# Test API
curl https://zhuanleee--stock-scanner-api-v2-create-fastapi-app.modal.run/health

# Check browser console
open https://zhuanleee.github.io/stock_scanner_bot/
# Open DevTools (F12) → Console
```

---

## 📚 Full Documentation

- **FORENSIC_ANALYSIS_COMPLETE.md** - Complete technical analysis (19 KB)
- **FIXES_APPLIED.md** - Detailed deployment guide (8 KB)
- **EXECUTIVE_SUMMARY.md** - High-level overview (10 KB)
- **QUICK_FIX_GUIDE.md** - This document (2 KB)

---

**Status:** ✅ READY FOR DEPLOYMENT
**Risk:** 🟢 LOW
**ETA:** 20 minutes to fully working dashboard

---
