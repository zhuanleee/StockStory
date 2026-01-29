# Resource Optimization Guide

## Current Configuration

**DigitalOcean App Platform:**
- **RAM:** 512MB (Basic XXS - $5/month)
- **CPU:** 1 shared vCPU
- **Bandwidth:** 50GB/month
- **Optimized:** `MAX_CONCURRENT_SCANS=25`

---

## Memory Usage Analysis

### Baseline Memory Consumption

| Component | Memory Usage |
|-----------|--------------|
| Python + Flask | 50-80 MB |
| Dependencies (pandas, numpy, 75 packages) | 100-150 MB |
| Learning system | 20-50 MB |
| Base total | **170-280 MB** |

### Per-Scan Memory

| Concurrency | Additional RAM | Total RAM | % of 512MB |
|-------------|----------------|-----------|------------|
| 10 scans | 20-50 MB | 190-330 MB | 37-64% |
| **25 scans** | **50-125 MB** | **220-405 MB** | **43-79%** ✅ |
| 50 scans | 100-250 MB | 270-530 MB | 53-104% ⚠️ |

**Optimized setting:** `MAX_CONCURRENT_SCANS=25` keeps you safely under 512MB.

---

## Current Performance

### With 25 Concurrent Scans

**Full market scan (1400 stocks):**
- Time: ~3-4 minutes (vs ~2 minutes with 50 concurrent)
- Memory: 60-80% utilization
- Stability: ✅ No OOM risk

**Telegram response time:**
- `/scan NVDA`: <2 seconds
- `/top10`: <3 seconds
- `/scan` (full): 3-4 minutes

**Trade-off:** Slightly slower full scans, but stable and reliable.

---

## When to Upgrade to 1GB RAM

### Upgrade Triggers

Upgrade to **Basic XS (1GB RAM, $12/month)** if:

1. **Memory alerts in DigitalOcean Insights**
   - Sustained >85% memory usage
   - Frequent memory spikes

2. **OOM errors in logs**
   - "MemoryError" exceptions
   - App restarts due to memory

3. **You want faster scans**
   - Set `MAX_CONCURRENT_SCANS=50`
   - Full scan completes in ~2 minutes

4. **You add more features**
   - More intelligence modules
   - Larger cache sizes
   - Additional data sources

### How to Upgrade (Zero Downtime)

1. Go to: DigitalOcean Dashboard → Your App
2. Click: **Settings → Resources**
3. Change: **Basic XXS** → **Basic XS**
4. Confirm: Cost increases to $12/month
5. Update environment variable:
   ```bash
   MAX_CONCURRENT_SCANS=50
   ```
6. Redeploy (automatic)

---

## Optimization Tips

### Reduce Memory Usage

**1. Lower concurrency further (if needed):**
```bash
MAX_CONCURRENT_SCANS=15  # Even more conservative
```

**2. Disable unused features:**
```bash
USE_AI_BRAIN_RANKING=false  # Save ~20MB
```

**3. Reduce cache sizes:**
Edit `src/config.py`:
```python
# Reduce cache retention
TRANSCRIPT_CACHE_DAYS = 30  # Instead of 90
ANALYSIS_CACHE_DAYS = 3     # Instead of 7
```

**4. Scan in batches:**
Instead of scanning all 1400 stocks:
```bash
# Scan only S&P 500
/scan --limit 500

# Or use watchlist
/watch add NVDA AMD TSLA
/watch scan
```

### Improve Performance

**1. Use Redis for caching (advanced):**
- Add Redis service on DigitalOcean
- Offload cache from memory to Redis
- Saves ~50MB RAM

**2. Use worker processes:**
- Separate scan workers from API server
- Requires 2 services (more cost)

---

## Monitoring Memory Usage

### Via DigitalOcean Dashboard

1. Go to: Your App → **Insights**
2. View metrics:
   - **Memory %** - Should stay <85%
   - **CPU %** - Should stay <70%
   - **Bandwidth** - Track monthly usage

3. Set alerts:
   - Alert when memory >85% for 5 minutes
   - Alert when CPU >80% for 5 minutes

### Via API Logs

Check for memory warnings:
```bash
# In DigitalOcean Runtime Logs
grep -i "memory" logs.txt
grep -i "oom" logs.txt
```

### Via Health Endpoint

```bash
curl https://your-app.ondigitalocean.app/health
```

Check response includes memory stats.

---

## Cost Comparison

| Tier | RAM | CPU | Monthly Cost | Best For |
|------|-----|-----|--------------|----------|
| **Basic XXS** | 512MB | 1 shared | $5 | Light usage, optimized |
| **Basic XS** | 1GB | 1 shared | $12 | Production, full features |
| **Basic S** | 2GB | 1 dedicated | $25 | Heavy usage, multiple bots |

**Recommendation:** Start with **Basic XXS** ($5), upgrade to **Basic XS** ($12) if needed.

---

## Bandwidth Usage

### Estimated Monthly Usage

| Activity | Monthly Data |
|----------|--------------|
| Telegram messages | ~10 MB |
| Dashboard views | ~1 GB |
| API calls | ~500 MB |
| **Total** | **~1.5 GB** |

**50GB allowance = 3% usage**

You have plenty of bandwidth headroom. No optimization needed.

---

## CPU Usage

### Current Usage

**1 shared vCPU is sufficient** because:
- ✅ Most operations are I/O-bound (waiting for APIs)
- ✅ Minimal CPU-intensive operations
- ✅ Pandas operations are brief

**Expected CPU usage:** 20-40% average, 60-80% during full scans

### When to Upgrade CPU

Only upgrade to dedicated CPU if:
- Sustained CPU >90% for long periods
- Adding heavy ML models
- Real-time video processing (not applicable)

**For your bot:** 1 shared vCPU is fine even at 1GB RAM.

---

## Current Configuration Summary

**Optimized for 512MB RAM:**
```yaml
instance_size_slug: basic-xxs  # 512MB RAM, 1 shared vCPU
MAX_CONCURRENT_SCANS: 25        # Safe memory usage
Expected memory: 60-80%          # Comfortable headroom
Expected CPU: 30-50%             # Plenty of headroom
Expected bandwidth: 3%           # Plenty of headroom
```

**Performance:**
- ✅ Full scan: 3-4 minutes
- ✅ Single ticker: <2 seconds
- ✅ Dashboard: <3 seconds
- ✅ Stable, no OOM risk

**Cost:** $5/month

---

## Decision Matrix

### Stay on 512MB if:
- ✅ 3-4 minute full scans are acceptable
- ✅ You mostly scan individual tickers
- ✅ Budget is priority
- ✅ Memory usage stays <80%

### Upgrade to 1GB if:
- ✅ You want 2-minute full scans
- ✅ You scan frequently (10+ times/day)
- ✅ You want maximum reliability
- ✅ $7/month extra is acceptable

---

## Quick Commands

**Monitor memory:**
```bash
# Check current usage
curl https://your-app.ondigitalocean.app/api/system/status
```

**Adjust concurrency:**
```bash
# In DigitalOcean environment variables
MAX_CONCURRENT_SCANS=15  # More conservative
MAX_CONCURRENT_SCANS=30  # More aggressive
MAX_CONCURRENT_SCANS=50  # Requires 1GB RAM
```

**Force garbage collection (if memory high):**
```python
# Added to health check endpoint
import gc
gc.collect()
```

---

## Conclusion

**512MB RAM with MAX_CONCURRENT_SCANS=25 is a good starting point:**
- ✅ Sufficient for stable operation
- ✅ Lowest cost ($5/month)
- ✅ Easy to upgrade if needed

**Monitor for 1 week, then decide:**
- Memory stays <75%? → Stay on 512MB ✅
- Memory >85% frequently? → Upgrade to 1GB 📈

---

**Last Updated:** 2026-01-29
**Configuration:** Basic XXS (512MB), optimized for reliability
