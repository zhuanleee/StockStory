# Watchlist System - Quick Start Guide

## 🚀 5-Minute Setup

### 1. System is Ready

✅ Already integrated into your Flask app
✅ API available at `/api/watchlist/*`
✅ Auto-update thread running in background
✅ Data persists to `user_data/watchlist/watchlist.json`

### 2. Test It

```bash
# Start your server (if not running)
python src/api/app.py

# Or on Railway - already running!
```

### 3. Basic Operations

**Add a Stock:**
```bash
curl -X POST http://localhost:5000/api/watchlist/ \
  -H "Content-Type: application/json" \
  -d '{
    "ticker": "NVDA",
    "notes": "AI leader, watching for entry",
    "thesis": "AI infrastructure growth story",
    "priority": "high",
    "target_entry": 850.00
  }'
```

**Get All:**
```bash
curl http://localhost:5000/api/watchlist/
```

**Get One:**
```bash
curl http://localhost:5000/api/watchlist/NVDA
```

**Update:**
```bash
curl -X PATCH http://localhost:5000/api/watchlist/NVDA \
  -H "Content-Type: application/json" \
  -d '{"notes": "Updated notes", "priority": "medium"}'
```

**Delete:**
```bash
curl -X DELETE http://localhost:5000/api/watchlist/NVDA
```

---

## 💡 Common Use Cases

### Use Case 1: Add from Scan Results

After running a scan on your dashboard:

```javascript
// In your dashboard JavaScript
async function addScanResultsToWatchlist(scanResults) {
  const response = await fetch('/api/watchlist/scan', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({results: scanResults})
  });

  const data = await response.json();
  alert(`Added ${data.added} stocks, Updated ${data.updated}`);
  refreshWatchlist();
}
```

### Use Case 2: Display Watchlist on Dashboard

```javascript
async function loadWatchlist() {
  const response = await fetch('/api/watchlist/');
  const {items} = await response.json();

  // Clear existing table
  const tbody = document.querySelector('#watchlist-table tbody');
  tbody.innerHTML = '';

  // Add rows
  items.forEach(item => {
    const row = `
      <tr>
        <td>${item.ticker}</td>
        <td>$${item.current_price?.toFixed(2) || 'N/A'}</td>
        <td class="priority-${item.priority}">${item.priority}</td>
        <td>${item.overall_score || 'N/A'}/10</td>
        <td>${item.signal_quality}</td>
        <td>${item.setup_complete ? '✓' : '-'}</td>
        <td>${item.x_sentiment}</td>
        <td>${item.ai_decision}</td>
        <td>
          <button onclick="editItem('${item.ticker}')">Edit</button>
          <button onclick="deleteItem('${item.ticker}')">Delete</button>
        </td>
      </tr>
    `;
    tbody.innerHTML += row;
  });
}
```

### Use Case 3: Pre-Trade Check

```javascript
async function checkBeforeEntry(ticker) {
  // 1. Update X sentiment
  await fetch(`/api/watchlist/update/sentiment/${ticker}`, {method: 'POST'});

  // 2. Update AI analysis
  await fetch(`/api/watchlist/update/ai/${ticker}`, {method: 'POST'});

  // 3. Get updated data
  const response = await fetch(`/api/watchlist/${ticker}`);
  const {item} = await response.json();

  // 4. Check if ready
  if (!item.setup_complete) {
    alert('Setup not complete!');
    return false;
  }

  if (item.overall_score < 6) {
    alert('Overall score too low!');
    return false;
  }

  if (item.x_sentiment === 'bearish') {
    alert('X sentiment is bearish!');
    return false;
  }

  if (item.ai_decision === 'sell') {
    alert('AI says sell!');
    return false;
  }

  // All checks passed
  alert(`${ticker} looks good! Score: ${item.overall_score}/10`);
  return true;
}
```

### Use Case 4: Auto-Update High Priority

```javascript
// Run this weekly for high-priority stocks
async function updateHighPriority() {
  const response = await fetch('/api/watchlist/?priority=high');
  const {items} = await response.json();

  for (const item of items) {
    // Update sentiment
    await fetch(`/api/watchlist/update/sentiment/${item.ticker}`, {method: 'POST'});

    // Update AI
    await fetch(`/api/watchlist/update/ai/${item.ticker}`, {method: 'POST'});

    // Wait 1 second between calls
    await new Promise(resolve => setTimeout(resolve, 1000));
  }

  alert(`Updated ${items.length} high-priority stocks`);
}
```

---

## 📊 Dashboard Integration Example

### HTML Structure

```html
<!-- Watchlist Section -->
<div id="watchlist-section">
  <h2>Watchlist</h2>

  <!-- Controls -->
  <div class="controls">
    <button onclick="addManually()">+ Add Stock</button>
    <button onclick="updatePrices()">↻ Update Prices</button>
    <select onchange="filterByPriority(this.value)">
      <option value="">All Priorities</option>
      <option value="high">High</option>
      <option value="medium">Medium</option>
      <option value="low">Low</option>
    </select>
    <input type="text" placeholder="Search..." oninput="searchWatchlist(this.value)">
  </div>

  <!-- Statistics -->
  <div class="stats">
    <span>Total: <strong id="total-items">0</strong></span>
    <span>Ready: <strong id="ready-items">0</strong></span>
    <span>High Priority: <strong id="high-priority">0</strong></span>
  </div>

  <!-- Table -->
  <table id="watchlist-table">
    <thead>
      <tr>
        <th>Ticker</th>
        <th>Price</th>
        <th>Change</th>
        <th>Priority</th>
        <th>Score</th>
        <th>Quality</th>
        <th>Ready</th>
        <th>X Sentiment</th>
        <th>AI</th>
        <th>Actions</th>
      </tr>
    </thead>
    <tbody>
      <!-- Populated by JavaScript -->
    </tbody>
  </table>
</div>
```

### JavaScript Functions

```javascript
// Load watchlist
async function loadWatchlist() {
  const response = await fetch('/api/watchlist/');
  const {items, statistics} = await response.json();

  // Update stats
  document.getElementById('total-items').textContent = statistics.total_items;
  document.getElementById('ready-items').textContent = statistics.ready_to_trade;
  document.getElementById('high-priority').textContent = statistics.by_priority.high;

  // Populate table
  populateTable(items);
}

// Add stock manually
async function addManually() {
  const ticker = prompt('Enter ticker:');
  if (!ticker) return;

  const response = await fetch('/api/watchlist/', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      ticker: ticker.toUpperCase(),
      priority: 'medium'
    })
  });

  if (response.ok) {
    alert(`${ticker} added to watchlist`);
    loadWatchlist();
  }
}

// Update all prices
async function updatePrices() {
  const btn = event.target;
  btn.disabled = true;
  btn.textContent = 'Updating...';

  await fetch('/api/watchlist/update/prices', {method: 'POST'});

  btn.disabled = false;
  btn.textContent = '↻ Update Prices';
  loadWatchlist();
}

// Filter by priority
async function filterByPriority(priority) {
  const url = priority ? `/api/watchlist/?priority=${priority}` : '/api/watchlist/';
  const response = await fetch(url);
  const {items} = await response.json();
  populateTable(items);
}

// Search
async function searchWatchlist(query) {
  if (!query) {
    loadWatchlist();
    return;
  }

  const response = await fetch(`/api/watchlist/?search=${query}`);
  const {items} = await response.json();
  populateTable(items);
}

// Delete item
async function deleteItem(ticker) {
  if (!confirm(`Remove ${ticker} from watchlist?`)) return;

  await fetch(`/api/watchlist/${ticker}`, {method: 'DELETE'});
  loadWatchlist();
}

// Edit item
async function editItem(ticker) {
  const notes = prompt('Enter notes:');
  if (!notes) return;

  await fetch(`/api/watchlist/${ticker}`, {
    method: 'PATCH',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({notes})
  });

  loadWatchlist();
}

// Auto-refresh every 30 seconds
setInterval(updatePrices, 30000);

// Load on page load
document.addEventListener('DOMContentLoaded', loadWatchlist);
```

---

## 🎨 Styling Example

```css
/* Watchlist Styles */
#watchlist-table {
  width: 100%;
  border-collapse: collapse;
}

#watchlist-table th {
  background: #2c3e50;
  color: white;
  padding: 10px;
  text-align: left;
}

#watchlist-table td {
  padding: 8px;
  border-bottom: 1px solid #ddd;
}

/* Priority Colors */
.priority-high {
  color: #e74c3c;
  font-weight: bold;
}

.priority-medium {
  color: #f39c12;
}

.priority-low {
  color: #95a5a6;
}

/* Score Badge */
.score-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 3px;
  font-weight: bold;
}

.score-excellent { background: #27ae60; color: white; }
.score-good { background: #2ecc71; color: white; }
.score-fair { background: #f39c12; color: white; }
.score-poor { background: #e74c3c; color: white; }
```

---

## 📱 Mobile View

```javascript
// Responsive card view for mobile
function populateCards(items) {
  const container = document.getElementById('watchlist-cards');
  container.innerHTML = '';

  items.forEach(item => {
    const card = `
      <div class="watchlist-card">
        <div class="card-header">
          <h3>${item.ticker}</h3>
          <span class="priority-${item.priority}">${item.priority}</span>
        </div>
        <div class="card-body">
          <div class="price">$${item.current_price?.toFixed(2) || 'N/A'}</div>
          <div class="score">Score: ${item.overall_score || 'N/A'}/10</div>
          <div class="quality">${item.signal_quality}</div>
          <div class="sentiment">
            ${item.x_sentiment}
            ${item.ai_decision}
          </div>
        </div>
        <div class="card-actions">
          <button onclick="viewDetails('${item.ticker}')">Details</button>
          <button onclick="editItem('${item.ticker}')">Edit</button>
          <button onclick="deleteItem('${item.ticker}')">Delete</button>
        </div>
      </div>
    `;
    container.innerHTML += card;
  });
}
```

---

## ✅ Testing Checklist

- [ ] Server running
- [ ] API responding at `/api/watchlist/`
- [ ] Can add stock manually
- [ ] Can add from scan results
- [ ] Can edit stock (notes, priority, etc.)
- [ ] Can delete stock
- [ ] Prices auto-update
- [ ] X sentiment updates
- [ ] AI analysis updates
- [ ] Statistics display correctly
- [ ] Data persists after restart

---

## 🔧 Troubleshooting

**Issue: API not responding**
```bash
# Check if blueprint registered
grep "Watchlist API registered" logs

# If not, check import
python -c "from src.watchlist.watchlist_api import watchlist_bp; print('OK')"
```

**Issue: Data not persisting**
```bash
# Check storage directory
ls -la user_data/watchlist/

# Should see: watchlist.json

# Check permissions
chmod 755 user_data/watchlist/
```

**Issue: Auto-update not working**
```python
# Check background thread
from src.watchlist import get_watchlist_manager
wm = get_watchlist_manager()
print(f"Auto-update enabled: {wm.auto_update_enabled}")
print(f"Last update: {wm._last_update}")
```

**Issue: X sentiment fails**
```bash
# Check xAI API key
echo $XAI_API_KEY

# Test X Intelligence
python test_xai_x_intelligence.py
```

---

## 🎯 Production Deployment

### Railway Deployment

1. **Push to git:**
   ```bash
   git add .
   git commit -m "Add enhanced watchlist system"
   git push
   ```

2. **Railway auto-deploys** (no config needed)

3. **Test on Railway:**
   ```bash
   # Your Railway URL
   curl https://stock-story-jy89o.ondigitalocean.app/api/watchlist/
   ```

4. **Update dashboard** to use Railway URL

---

## 💡 Pro Tips

1. **Use Priority Effectively:**
   - High: Ready to trade soon
   - Medium: Monitor closely
   - Low: Long-term watch

2. **Update Smartly:**
   - Prices: Every 30 seconds (free)
   - X Sentiment: Before trades (costs $0.10)
   - AI Analysis: Weekly for high-priority (costs $0.15)

3. **Organize with Tags:**
   ```javascript
   tags: ["AI", "momentum", "earnings-catalyst"]
   ```

4. **Set Clear Targets:**
   ```javascript
   target_entry: 850.00,
   stop_loss: 800.00
   ```

5. **Use Search:**
   - Search by ticker, thesis, catalyst, notes

6. **Export Regularly:**
   ```bash
   # Backup watchlist
   curl http://localhost:5000/api/watchlist/export > backup.json
   ```

---

**Your watchlist system is ready to use!** 🚀

Start adding stocks and let the auto-updates keep you informed!
