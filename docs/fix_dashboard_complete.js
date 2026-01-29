// Dashboard Complete Fix Script
// This script documents all remaining fixes needed

// FIXES APPLIED SO FAR:
// 1. ✅ Added safeFixed() utility function
// 2. ✅ Added safeFetch() utility function with timeout
// 3. ✅ Fixed syncClient initialization with try-catch
// 4. ✅ Changed syncClient from const to let

// REMAINING FIXES TO APPLY:
// These should be applied manually or via sed/awk:

// Fix 1: Initialize global variables immediately
// Location: Line ~3032
// Before: let allPositions = [];
// After:  let allPositions = []; (function initGlobals() { allPositions = []; allWatchlist = []; journalEntries = []; })();

// Fix 2: Clear filters on fetchScan()
// Location: Line ~1945 (in fetchScan function)
// Add after function start:
//   document.getElementById('filter-strength').value = '';
//   document.getElementById('filter-search').value = '';

// Fix 3: Add loading state to fetchScan button
// Location: Line ~1947
// Add: const scanBtn = document.querySelector('button[onclick*="fetchScan"]');
//      if (scanBtn) { scanBtn.disabled = true; scanBtn.textContent = '⏳ Loading...'; }
// Add in finally: if (scanBtn) { scanBtn.disabled = false; scanBtn.textContent = originalText; }

// Fix 4: Replace key toFixed() calls with safeFixed()
// Priority calls (most likely to fail):
// - Line 2096: a.conviction_score.toFixed(0) → safeFixed(a.conviction_score, 0)
// - Line 2120: data.conviction_score.toFixed(0) → safeFixed(data.conviction_score, 0)
// - Line 2124-2129: All .score.toFixed(0) → safeFixed(score, 0)
// - Line 2202: theme.opportunity_score?.toFixed(0) → safeFixed(theme.opportunity_score, 0)
// - Line 2251: theme.opportunity_score.toFixed(0) → safeFixed(theme.opportunity_score, 0)

// Fix 5: Replace key fetch() calls with safeFetch()
// Priority calls (user-facing):
// - Line 1864: showTicker() modal
// - Line 1915: Health check
// - Line 1951: fetchScan()
// - Line 2078: Conviction alerts
// - Line 2115: Conviction detail

// Fix 6: Add modal timeout handling
// Location: Lines 1859-1875 (showTicker), 3441 (showTradeDetail)
// Wrap in try-catch with timeout:
//   try {
//     const data = await safeFetch(`${API_BASE}/ticker/${ticker}`, {}, 10000);
//     // ... render
//   } catch (e) {
//     openModal(ticker, `<div class="error">Failed to load: ${e.message}</div>`);
//   }

// Fix 7: Add journal filter null check
// Location: Line ~3670
// Before: const filter = document.getElementById('journal-filter').value;
// After:  const filter = document.getElementById('journal-filter')?.value || 'all';

console.log('Dashboard fix documentation loaded');
console.log('Apply these fixes manually or use search-and-replace');
