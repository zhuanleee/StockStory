const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? 'http://localhost:5000/api'
    : 'https://zhuanleee--stockstory-api-create-fastapi-app.modal.run';

// Add loading spinner CSS
const style = document.createElement('style');
style.textContent = `
    .loading-spinner {
        display: inline-block;
        width: 12px;
        height: 12px;
        border: 2px solid var(--text-muted);
        border-top-color: var(--green);
        border-radius: 50%;
        animation: spin 0.8s linear infinite;
    }
    @keyframes spin {
        to { transform: rotate(360deg); }
    }
    .is-loading .card { opacity: 0.7; }
`;
document.head.appendChild(style);

// =============================================================================
// FETCH WITH RETRY - Exponential backoff for resilient API calls
// =============================================================================
async function fetchWithRetry(url, options = {}, maxRetries = 3) {
    let lastError;
    for (let i = 0; i < maxRetries; i++) {
        try {
            const res = await fetch(url, options);
            if (!res.ok && res.status >= 500) {
                throw new Error(`Server error: ${res.status}`);
            }
            return res;
        } catch (error) {
            lastError = error;
            if (i < maxRetries - 1) {
                const delay = Math.pow(2, i) * 1000; // 1s, 2s, 4s
                console.log(`Retry ${i + 1}/${maxRetries} for ${url} in ${delay}ms`);
                await new Promise(r => setTimeout(r, delay));
            }
        }
    }
    throw lastError;
}

// =============================================================================
// TIMEZONE UTILITY - Uses user's local timezone
// =============================================================================
const userTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
const userLocale = navigator.language || 'en-US';

function formatLocalTime(date = new Date()) {
    return date.toLocaleTimeString(userLocale, {
        hour: '2-digit',
        minute: '2-digit'
    });
}

// =============================================================================
// DEBUG HELPER - Test API connection
// =============================================================================
window.testConnection = async function() {
    console.log('🧪 Testing API Connection...');
    console.log('📍 Current hostname:', window.location.hostname);
    console.log('📡 API_BASE:', API_BASE);
    console.log('');

    try {
        // Test 1: Health endpoint
        console.log('Test 1: Health endpoint');
        const healthUrl = `${API_BASE}/health`;
        console.log('  URL:', healthUrl);
        const healthRes = await fetch(healthUrl);
        console.log('  Status:', healthRes.status);
        const healthData = await healthRes.json();
        console.log('  Response:', healthData);
        console.log('');

        // Test 2: Scan endpoint
        console.log('Test 2: Scan endpoint');
        const scanUrl = `${API_BASE}/scan`;
        console.log('  URL:', scanUrl);
        const scanRes = await fetch(scanUrl);
        console.log('  Status:', scanRes.status);
        const scanData = await scanRes.json();
        console.log('  Response:', scanData);
        console.log('');

        console.log('✅ Connection test complete!');
        console.log('💡 To manually refresh: refreshAll()');
        console.log('💡 To test scan fetch: fetchScan()');

        return { health: healthData, scan: scanData };
    } catch (e) {
        console.error('❌ Connection test failed:', e);
        return { error: e.message };
    }
};

// Log API configuration on page load
console.log('🚀 Stock Scanner Dashboard loaded');
console.log('📡 API_BASE:', API_BASE);
console.log('💡 Run testConnection() to verify API');

// =============================================================================
// SOCKET.IO SYNC CLIENT
// =============================================================================

class SyncClient {
    constructor() {
        this.socket = null;
        this.clientId = null;
        this.connected = false;
        this.eventHandlers = {};
    }

    connect() {
        // SocketIO is disabled on the backend
        // Real-time sync is not available in this deployment
        console.debug('Real-time sync disabled - SocketIO not available on backend');
        this.updateSyncStatus('unavailable');
        return;

        /* Disabled - SocketIO not enabled on backend
        try {
            // Connect to same origin (API server) with Socket.IO
            const serverUrl = API_BASE.replace('/api', '');
            const isSecure = window.location.protocol === 'https:';
            console.log('Connecting to sync server:', serverUrl);

            this.socket = io(serverUrl, {
                transports: ['polling'],  // Polling only - WebSocket upgrade fails on Railway
                secure: isSecure,
                reconnection: true,
                reconnectionAttempts: 3,
                reconnectionDelay: 3000,
                reconnectionDelayMax: 10000,
                timeout: 10000,
            });

            // Connection events
            this.socket.on('connect', () => this.onConnect());
            this.socket.on('disconnect', (reason) => this.onDisconnect(reason));
            this.socket.on('connect_error', (error) => this.onError(error));

            // Sync events
            this.socket.on('connected', (data) => this.handleConnected(data));
            this.socket.on('sync_history', (data) => this.handleSyncHistory(data));
            this.socket.on('sync_event', (data) => this.handleSyncEvent(data));
            this.socket.on('status', (data) => this.handleStatus(data));
            this.socket.on('heartbeat_ack', () => {});
            this.socket.on('error', (data) => console.debug('Sync error:', data));

        } catch (e) {
            console.debug('Sync server unavailable');
            this.updateSyncStatus('unavailable');
        }
        */
    }

    onConnect() {
        console.log('Real-time sync connected');
        this.connected = true;
        this.failCount = 0;
        this.updateSyncStatus('connected');
    }

    onDisconnect(reason) {
        console.debug('Sync disconnected:', reason);
        this.connected = false;
        this.updateSyncStatus('disconnected');
    }

    onError(error) {
        this.failCount = (this.failCount || 0) + 1;
        if (this.failCount <= 2) {
            console.debug('Sync connection attempt', this.failCount);
        }
        if (this.failCount >= 3) {
            // Give up quietly - sync is optional
            this.updateSyncStatus('unavailable');
            if (this.socket) {
                this.socket.disconnect();
            }
            return;
        }
        this.updateSyncStatus('error');
    }

    handleConnected(data) {
        this.clientId = data.client_id;
        console.log('Sync client ID:', this.clientId);
        this.showNotification('Sync Connected', 'Real-time Telegram sync active', 'success');
    }

    handleSyncHistory(data) {
        const events = data.events || [];
        console.log(`Received ${events.length} historical events`);
        events.forEach(event => this.processEvent(event, false));
    }

    handleSyncEvent(data) {
        const event = data.event;
        if (event) {
            this.processEvent(event, true);
        }
    }

    handleStatus(data) {
        this.updateSyncStatusDetails(data);
    }

    processEvent(event, notify = true) {
        const eventType = event.event_type;
        const source = event.source;
        const payload = event.payload || {};

        console.log(`Sync event: ${eventType} from ${source}`);

        // Handle different event types
        switch (eventType) {
            case 'trade_created':
                if (source === 'telegram' && notify) {
                    this.showNotification('Trade Added (Telegram)', `${payload.ticker} added to watchlist`, 'info');
                    fetchTrades();
                }
                break;

            case 'buy_executed':
                if (source === 'telegram' && notify) {
                    this.showNotification('Buy Executed (Telegram)', `${payload.shares} ${payload.ticker} @ $${payload.price}`, 'success');
                    fetchTrades();
                }
                break;

            case 'sell_executed':
                if (source === 'telegram' && notify) {
                    this.showNotification('Sell Executed (Telegram)', `${payload.shares} ${payload.ticker} @ $${payload.price}`, 'warning');
                    fetchTrades();
                }
                break;

            case 'exit_signal':
                if (notify) {
                    this.showNotification('Exit Signal', `${payload.ticker}: ${payload.signal_type}`, 'danger');
                }
                break;

            case 'journal_added':
                if (source === 'telegram' && notify) {
                    this.showNotification('Journal Entry (Telegram)', `${payload.entry_type}: ${(payload.content || '').slice(0, 50)}...`, 'info');
                    fetchJournal();
                }
                break;

            case 'command_received':
                if (notify) {
                    this.showNotification('Telegram Command', `/${payload.command} ${payload.args || ''}`, 'info');
                    addSyncActivityItem(`Telegram: /${payload.command} ${payload.args || ''}`, 'command');
                }
                break;

            case 'scan_completed':
                if (notify) {
                    this.showNotification('Scan Complete', `${payload.positions_scanned} positions, ${payload.signals_count} signals`, 'info');
                }
                break;
        }

        // Add to sync activity
        if (source === 'telegram' && notify) {
            addSyncActivityItem(this.formatEventMessage(event), eventType.replace('_', '-'));
        }

        // Acknowledge event
        if (event.ack_required) {
            this.send({ type: 'ack', event_id: event.id });
        }
    }

    formatEventMessage(event) {
        const p = event.payload;
        const formatters = {
            'trade_created': () => `Added ${p.ticker} to watchlist`,
            'buy_executed': () => `Bought ${p.shares} ${p.ticker} @ $${p.price}`,
            'sell_executed': () => `Sold ${p.shares} ${p.ticker} @ $${p.price}`,
            'exit_signal': () => `Exit signal for ${p.ticker}: ${p.signal_type}`,
            'journal_added': () => `Journal: ${p.entry_type} - ${p.content?.slice(0, 30)}...`,
            'command_received': () => `Command: /${p.command}`,
            'scan_completed': () => `Scan: ${p.positions_scanned} positions`,
        };
        const formatter = formatters[event.event_type];
        return formatter ? formatter() : event.event_type;
    }

    send(data) {
        if (this.socket && this.connected) {
            this.socket.emit('message', data);
        }
    }

    // Publish event to server
    publish(eventType, payload) {
        if (this.socket && this.connected) {
            this.socket.emit('publish', {
                event_type: eventType,
                payload: payload
            });
        }
    }

    // Request sync status
    requestStatus() {
        if (this.socket && this.connected) {
            this.socket.emit('get_status');
        }
    }

    // Acknowledge event receipt
    ack(eventId) {
        if (this.socket && this.connected) {
            this.socket.emit('ack', { event_id: eventId });
        }
    }

    updateSyncStatus(status) {
        const indicator = document.getElementById('sync-status-indicator');
        const text = document.getElementById('sync-status-text');

        if (!indicator || !text) return;

        const statusConfig = {
            'connected': { color: 'var(--green)', text: 'SYNCED', icon: '●' },
            'disconnected': { color: 'var(--yellow)', text: 'OFFLINE', icon: '○' },
            'error': { color: 'var(--red)', text: 'ERROR', icon: '✕' },
            'unavailable': { color: 'var(--text-muted)', text: 'N/A', icon: '○' },
        };

        const config = statusConfig[status] || statusConfig.disconnected;
        indicator.style.color = config.color;
        indicator.textContent = config.icon;
        text.textContent = config.text;
        text.style.color = config.color;
    }

    updateSyncStatusDetails(status) {
        const el = document.getElementById('sync-details');
        if (el) {
            el.innerHTML = `
                <div>Clients: ${status.connected_clients || 0}</div>
                <div>Events: ${status.total_events || 0}</div>
            `;
        }
    }

    showNotification(title, message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `sync-notification sync-notification-${type}`;
        notification.innerHTML = `
            <div class="sync-notification-title">${title}</div>
            <div class="sync-notification-message">${message}</div>
        `;

        // Add to container
        let container = document.getElementById('sync-notifications');
        if (!container) {
            container = document.createElement('div');
            container.id = 'sync-notifications';
            container.style.cssText = 'position: fixed; top: 70px; right: 20px; z-index: 9999; display: flex; flex-direction: column; gap: 8px;';
            document.body.appendChild(container);
        }
        container.appendChild(notification);

        // Auto-remove after 5 seconds
        setTimeout(() => {
            notification.style.opacity = '0';
            notification.style.transform = 'translateX(100%)';
            setTimeout(() => notification.remove(), 300);
        }, 5000);
    }
}

// Global sync client
const syncClient = new SyncClient();

// Sync activity helper
function addSyncActivityItem(message, type = 'sync') {
    const activityItems = window.activityItems || [];
    activityItems.unshift({
        message: `[SYNC] ${message}`,
        type: type,
        timestamp: new Date().toISOString()
    });
    window.activityItems = activityItems;
    if (typeof renderActivityFeed === 'function') {
        renderActivityFeed();
    }
}

// Category to sub-tabs mapping
const categorySubTabs = {
    dashboard: null,  // No sub-tabs
    health: null,     // No sub-tabs - Market Health visualization
    research: ['themes', 'sec'],
    trading: ['scanner', 'trades', 'watchlist', 'options'],
    analytics: null   // No sub-tabs
};

// Current active state
let currentCategory = 'dashboard';
let currentSubTab = null;

// Main category tab switching
document.querySelectorAll('.main-tab').forEach(tab => {
    tab.addEventListener('click', () => {
        const categoryId = tab.dataset.category;
        switchCategory(categoryId);
    });
});

// Sub-tab switching
document.querySelectorAll('.sub-tab').forEach(tab => {
    tab.addEventListener('click', () => {
        const tabId = tab.dataset.tab;
        switchSubTab(tabId);
    });
});

// Accordion toggle for collapsible sections
function toggleAccordion(element) {
    element.classList.toggle('open');
}

// Populate hero top picks (called from fetchScan)
function updateHeroTopPicks(stocks) {
    const container = document.getElementById('hero-top-picks');
    if (!container || !stocks || stocks.length === 0) return;

    const top3 = stocks.slice(0, 3);
    container.innerHTML = top3.map(stock => {
        const score = stock.story_score || stock.composite_score || 0;
        const scoreClass = score >= 70 ? '' : 'developing';
        const theme = stock.hottest_theme || stock.theme || 'Analyzing...';
        const catalyst = stock.next_catalyst || stock.catalyst?.description || 'Click for details';

        return `
            <div class="hero-stock-card" onclick="showTickerDetail('${stock.ticker}')">
                <div class="hero-stock-header">
                    <span class="hero-stock-ticker">${stock.ticker}</span>
                    <span class="hero-stock-score ${scoreClass}">${Math.round(score)}</span>
                </div>
                <div class="hero-stock-theme">${theme}</div>
                <div class="hero-stock-catalyst">${catalyst.substring(0, 50)}${catalyst.length > 50 ? '...' : ''}</div>
            </div>
        `;
    }).join('');
}

function switchCategory(categoryId) {
    // Update main tabs
    document.querySelectorAll('.main-tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.sub-tabs').forEach(s => s.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

    // Activate main category
    const mainTab = document.querySelector(`[data-category="${categoryId}"]`);
    if (mainTab) mainTab.classList.add('active');

    currentCategory = categoryId;

    // Show sub-tabs if category has them
    const subTabs = document.getElementById(`sub-tabs-${categoryId}`);
    if (subTabs) {
        subTabs.classList.add('active');
        // Activate first sub-tab
        const firstSubTab = subTabs.querySelector('.sub-tab');
        if (firstSubTab) {
            // Reset sub-tab active states for this category
            subTabs.querySelectorAll('.sub-tab').forEach(t => t.classList.remove('active'));
            firstSubTab.classList.add('active');
            switchSubTab(firstSubTab.dataset.tab, false);
        }
    } else {
        // No sub-tabs, show category content directly
        const content = document.getElementById(categoryId);
        if (content) content.classList.add('active');
        currentSubTab = null;
        loadTabData(categoryId);
    }
}

function switchSubTab(tabId, updateActive = true) {
    // Hide all tab content
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

    // Update sub-tab active state if requested
    if (updateActive) {
        document.querySelectorAll('.sub-tab').forEach(t => t.classList.remove('active'));
        const subTab = document.querySelector(`[data-tab="${tabId}"]`);
        if (subTab) subTab.classList.add('active');
    }

    // Show tab content
    const content = document.getElementById(tabId);
    if (content) content.classList.add('active');

    currentSubTab = tabId;
    loadTabData(tabId);
}

function loadTabData(tabId) {
    // Check cache - skip if data loaded recently
    const lastLoaded = tabLoadedAt[tabId] || 0;
    const isCached = (Date.now() - lastLoaded) < CACHE_TTL;

    if (isCached) {
        console.log(`Tab ${tabId} cached, skipping fetch`);
        return;
    }

    console.log(`Loading data for tab: ${tabId}`);

    // Load data based on tab - using Promise.all for parallel fetching
    if (tabId === 'dashboard') {
        Promise.all([
            fetchHealth(),
            fetchScan(),
            fetchAIIntelligence(),
            fetchConvictionAlerts(),
            fetchThemes(),  // For Hot Themes section
            fetchUnusualOptions()
        ]).catch(err => console.error('Dashboard load error:', err));
    } else if (tabId === 'health') {
        fetchMarketHealth();
    } else if (tabId === 'themes') {
        Promise.all([
            fetchThemes(),
            fetchThemeRadar(),
            loadThemeConfig()
        ]).catch(err => console.error('Themes load error:', err));
    } else if (tabId === 'sec') {
        Promise.all([
            fetchMARadar(),
            fetchDeals()
        ]).catch(err => console.error('SEC load error:', err));
    } else if (tabId === 'scanner') {
        fetchScan();
    } else if (tabId === 'trades') {
        fetchTrades();
    } else if (tabId === 'watchlist') {
        refreshWatchlistTab();
    } else if (tabId === 'options') {
        Promise.all([
            loadMarketSentiment(),
            loadWhaleTrades(),
            loadUnusualActivity()
        ]).then(() => {
            // Auto-load SPY options analysis after market data loads
            quickAnalyzeTicker('SPY');
        }).catch(err => console.error('Options load error:', err));
    } else if (tabId === 'analytics') {
        Promise.all([
            fetchEvolution(),
            fetchParameters(),
            fetchCorrelations(),
            fetchEconomicDashboard()
        ]).catch(err => console.error('Analytics load error:', err));
    }

    tabLoadedAt[tabId] = Date.now();
}

// Legacy switchTab function for backwards compatibility
function switchTab(tabId) {
    // Map old tab names to new navigation
    if (tabId === 'overview' || tabId === 'intelligence') {
        switchCategory('dashboard');
    } else if (tabId === 'themeradar') {
        switchCategory('research');
        switchSubTab('themes');
    } else if (tabId === 'scan' || tabId === 'scanner') {
        switchCategory('dashboard');
    } else if (['themes', 'sec'].includes(tabId)) {
        switchCategory('research');
        switchSubTab(tabId);
    } else if (tabId === 'options') {
        switchCategory('options');
    } else if (tabId === 'analytics') {
        switchCategory('analytics');
    } else if (tabId === 'health') {
        switchCategory('health');
    }
}

// Modal
function openModal(title, content) {
    document.getElementById('modal-title').textContent = title;
    document.getElementById('modal-body').innerHTML = content;
    document.getElementById('modal-overlay').classList.add('active');
}

function closeModal(e) {
    if (!e || e.target === document.getElementById('modal-overlay')) {
        document.getElementById('modal-overlay').classList.remove('active');
    }
}

document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });

// Skeleton loading helpers
function getSkeletonHTML(type = 'default') {
    const skeletons = {
        default: `
            <div class="skeleton-row" style="padding: 20px;">
                <span class="skeleton skeleton-text-lg" style="width: 60%;"></span>
                <span class="skeleton skeleton-text" style="width: 90%;"></span>
                <span class="skeleton skeleton-text" style="width: 75%;"></span>
            </div>`,
        card: `
            <div style="display: grid; gap: 16px; padding: 20px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span class="skeleton skeleton-text-lg" style="width: 100px;"></span>
                    <span class="skeleton skeleton-stat"></span>
                </div>
                <div class="skeleton skeleton-card"></div>
                <div class="skeleton-row">
                    <span class="skeleton skeleton-text" style="width: 80%;"></span>
                    <span class="skeleton skeleton-text-sm" style="width: 60%;"></span>
                </div>
            </div>`,
        table: `
            <div style="padding: 16px;">
                ${[1,2,3,4,5].map(() => `
                    <div class="skeleton-table-row">
                        <span class="skeleton skeleton-text-sm" style="width: 60px;"></span>
                        <span class="skeleton skeleton-text" style="width: 100px;"></span>
                        <span class="skeleton skeleton-text-sm" style="width: 80px;"></span>
                        <span class="skeleton skeleton-text-sm" style="width: 60px;"></span>
                    </div>
                `).join('')}
            </div>`,
        text: `<span class="skeleton skeleton-text" style="display: inline-block;"></span>`
    };
    return skeletons[type] || skeletons.default;
}

// Show ticker details
async function showTicker(ticker) {
    openModal(ticker, getSkeletonHTML('card'));
    try {
        // Fetch both stock data and options overview in parallel
        const [stockRes, optionsRes] = await Promise.all([
            fetch(`${API_BASE}/ticker/${ticker}`),
            fetch(`${API_BASE}/options/overview/${ticker}`)
        ]);

        const data = await stockRes.json();
        const optionsData = await optionsRes.json();

        if (data.ok && data.stock) {
            const s = data.stock;
            let content = `
                <div style="display: grid; gap: 16px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <div style="font-size: 1.5rem; font-weight: 700;">${s.ticker}</div>
                            <div style="color: var(--text-muted);">${s.sector || 'N/A'}</div>
                        </div>
                        <div style="text-align: right;">
                            <div style="font-size: 1.25rem; font-weight: 600;">Score: ${(s.story_score || 0).toFixed(1)}</div>
                            <div style="color: var(--text-muted);">${s.story_strength || 'N/A'}</div>
                        </div>
                    </div>
                    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px;">
                        <div style="background: var(--bg-hover); padding: 12px; border-radius: 8px;">
                            <div style="font-size: 0.75rem; color: var(--text-muted);">Change</div>
                            <div style="font-weight: 600; color: ${(s.change_pct || 0) >= 0 ? 'var(--green)' : 'var(--red)'};">${(s.change_pct || 0) >= 0 ? '+' : ''}${(s.change_pct || 0).toFixed(2)}%</div>
                        </div>
                        <div style="background: var(--bg-hover); padding: 12px; border-radius: 8px;">
                            <div style="font-size: 0.75rem; color: var(--text-muted);">Volume</div>
                            <div style="font-weight: 600;">${formatVolume(s.volume || 0)}</div>
                        </div>
                        <div style="background: var(--bg-hover); padding: 12px; border-radius: 8px;">
                            <div style="font-size: 0.75rem; color: var(--text-muted);">RS Rating</div>
                            <div style="font-weight: 600;">${(s.rs_rating || 0).toFixed(0)}</div>
                        </div>
                    </div>
                    ${s.hottest_theme ? `<div style="padding: 8px 12px; background: var(--blue-bg); border-radius: 8px; font-size: 0.875rem;"><strong>Theme:</strong> ${s.hottest_theme}</div>` : ''}
                    ${s.catalyst ? `<div style="padding: 8px 12px; background: var(--yellow-bg); border-radius: 8px; font-size: 0.875rem;"><strong>Catalyst:</strong> ${s.catalyst}</div>` : ''}
            `;

            // Add options overview if available
            if (optionsData.ok && optionsData.data && !optionsData.data.error) {
                const opts = optionsData.data;
                const flow = opts.flow || {};
                const unusual = opts.unusual_activity || {};

                if (flow.sentiment || flow.put_call_ratio) {
                    const sentiment = flow.sentiment || 'neutral';
                    const sentimentColor = sentiment === 'bullish' ? 'var(--green)' :
                                           sentiment === 'bearish' ? 'var(--red)' :
                                           'var(--text-muted)';

                    content += `
                        <div style="padding: 12px; background: var(--bg-hover); border-radius: 8px; border-left: 3px solid ${sentimentColor};">
                            <div style="font-size: 0.75rem; color: var(--text-muted); margin-bottom: 8px;">📊 OPTIONS FLOW</div>
                            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px;">
                                <div>
                                    <div style="font-size: 0.7rem; color: var(--text-muted);">Sentiment</div>
                                    <div style="font-weight: 600; color: ${sentimentColor}; text-transform: uppercase;">${sentiment}</div>
                                </div>
                                <div>
                                    <div style="font-size: 0.7rem; color: var(--text-muted);">P/C Ratio</div>
                                    <div style="font-weight: 600;">${flow.put_call_ratio?.toFixed(2) || '--'}</div>
                                </div>
                                <div>
                                    <div style="font-size: 0.7rem; color: var(--text-muted);">Call Vol</div>
                                    <div style="font-weight: 600; color: var(--green);">${formatVolume(flow.total_call_volume || 0)}</div>
                                </div>
                            </div>
                            ${unusual.unusual_activity ?
                                `<div style="margin-top: 8px; padding: 6px 10px; background: rgba(255, 193, 7, 0.1); border-radius: 4px; font-size: 0.75rem; color: var(--yellow);">
                                    ⚠️ Unusual activity detected (${unusual.unusual_contracts?.length || 0} contracts)
                                </div>` :
                                ''
                            }
                        </div>
                    `;
                }
            }

            content += `</div>`;
            document.getElementById('modal-body').innerHTML = content;
        }
    } catch (e) {
        document.getElementById('modal-body').innerHTML = '<div style="color: var(--red);">Failed to load data</div>';
    }
}

function formatVolume(vol) {
    if (vol >= 1e9) return (vol / 1e9).toFixed(1) + 'B';
    if (vol >= 1e6) return (vol / 1e6).toFixed(1) + 'M';
    if (vol >= 1e3) return (vol / 1e3).toFixed(1) + 'K';
    return vol.toString();
}

// Fetch functions
async function fetchHealth() {
    console.log('🔄 fetchHealth() called');
    try {
        const res = await fetchWithRetry(`${API_BASE}/health`);
        const data = await res.json();
        console.log('📦 Health API response:', data);

        // Check for success - API may return ok:true or status:success
        if (data.ok || data.status === 'success' || res.ok) {
            const fg = data.fear_greed || {};
            const breadth = data.breadth || {};
            const raw = data.raw_data || {};

            // Market pulse - SPY and QQQ prices with daily change
            const spyPrice = raw.spy_price || 0;
            const spyChange = raw.spy_change || 0;
            const qqqPrice = raw.qqq_price || 0;
            const qqqChange = raw.qqq_change || 0;

            const spyPriceEl = document.getElementById('spy-price');
            const spyChangeEl = document.getElementById('spy-change');
            const qqqPriceEl = document.getElementById('qqq-price');
            const qqqChangeEl = document.getElementById('qqq-change');
            const vixEl = document.getElementById('vix-value');

            if (spyPriceEl) spyPriceEl.textContent = '$' + spyPrice.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2});
            if (spyChangeEl) {
                spyChangeEl.textContent = (spyChange >= 0 ? '+' : '') + spyChange.toFixed(2) + '%';
                spyChangeEl.style.color = spyChange >= 0 ? 'var(--green)' : 'var(--red)';
            }
            if (qqqPriceEl) qqqPriceEl.textContent = '$' + qqqPrice.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2});
            if (qqqChangeEl) {
                qqqChangeEl.textContent = (qqqChange >= 0 ? '+' : '') + qqqChange.toFixed(2) + '%';
                qqqChangeEl.style.color = qqqChange >= 0 ? 'var(--green)' : 'var(--red)';
            }
            if (vixEl) vixEl.textContent = (raw.vix || 0).toFixed(1);

            // Fear & Greed
            const fgScore = fg.score !== undefined ? fg.score : (data.overall_score || 50);
            const fgValueEl = document.getElementById('fg-value');
            const fearGreedEl = document.getElementById('fear-greed');
            const fgLabelEl = document.getElementById('fg-label');
            const gaugeNeedleEl = document.getElementById('gauge-needle');

            if (fgValueEl) fgValueEl.textContent = fgScore.toFixed(0);
            if (fearGreedEl) fearGreedEl.textContent = fgScore.toFixed(0);
            const fgLabel = fg.label || (fgScore <= 25 ? 'Extreme Fear' : fgScore <= 45 ? 'Fear' : fgScore <= 55 ? 'Neutral' : fgScore <= 75 ? 'Greed' : 'Extreme Greed');
            if (fgLabelEl) fgLabelEl.textContent = fgLabel;
            const rotation = (fgScore - 50) * 1.8; // -90 to 90 degrees
            if (gaugeNeedleEl) gaugeNeedleEl.style.setProperty('--rotation', rotation + 'deg');

            // Health metrics from breadth
            const breadthScoreEl = document.getElementById('breadth-score');
            const advDecEl = document.getElementById('adv-dec');
            const hiLoEl = document.getElementById('hi-lo');
            const putCallEl = document.getElementById('put-call');

            if (breadthScoreEl) breadthScoreEl.textContent = (breadth.breadth_score || 0).toFixed(0) + '%';
            if (advDecEl) advDecEl.textContent = (breadth.advance_decline_ratio || 0).toFixed(2);
            if (hiLoEl) hiLoEl.textContent = `${breadth.new_highs || 0} / ${breadth.new_lows || 0}`;
            if (putCallEl) putCallEl.textContent = (raw.vix_term_ratio || 0).toFixed(2);

            console.log('✅ fetchHealth completed successfully');
        } else {
            console.warn('⚠️ fetchHealth: API returned non-ok status', data);
        }
    } catch (e) {
        console.error('fetchHealth error:', e);
        // Show error state in UI
        const el = document.getElementById('fear-greed-score');
        if (el) el.textContent = 'Error';
        const fgValueEl = document.getElementById('fg-value');
        if (fgValueEl) fgValueEl.textContent = '--';
        const fgLabelEl = document.getElementById('fg-label');
        if (fgLabelEl) fgLabelEl.textContent = 'Error loading data';
    }
}

async function fetchScan() {
    console.log('🔄 fetchScan() called');
    console.log('📡 API_BASE:', API_BASE);

    try {
        const url = `${API_BASE}/scan`;
        console.log('📍 Fetching:', url);

        const res = await fetchWithRetry(url);
        console.log('✅ Response status:', res.status, res.statusText);

        const data = await res.json();
        console.log('📦 Response data:', data);

        // Fix: API returns 'results' not 'stocks'
        const stocks = data.results || data.stocks || [];
        console.log('📊 Stocks array length:', stocks.length);

        // Fix: Check for data.status === 'success' OR data.ok OR just having stocks
        // API returns {status: 'success', results: [...]} not {ok: true}
        if (stocks.length > 0) {
            console.log('✅ Rendering', stocks.length, 'stocks');
            renderTopPicks(stocks);
            renderScanTable(stocks);
            updateHeroTopPicks(stocks);  // Update hero zone top 3

            // Update stats - Dashboard tab
            const hotCount = stocks.filter(s => s.story_strength === 'hot').length;
            const devCount = stocks.filter(s => s.story_strength === 'developing').length;
            const watchCount = stocks.filter(s => s.story_strength === 'watchlist').length;

            document.getElementById('stat-scanned').textContent = stocks.length;
            document.getElementById('stat-hot').textContent = hotCount;
            document.getElementById('stat-developing').textContent = devCount;
            document.getElementById('stat-watchlist').textContent = watchCount;

            // Update stats - Scanner tab
            const scannerTotal = document.getElementById('scanner-stat-total');
            const scannerHot = document.getElementById('scanner-stat-hot');
            const scannerDev = document.getElementById('scanner-stat-developing');
            const scannerWatch = document.getElementById('scanner-stat-watchlist');
            const scannerTime = document.getElementById('scanner-last-scan');

            if (scannerTotal) scannerTotal.textContent = stocks.length;
            if (scannerHot) scannerHot.textContent = hotCount;
            if (scannerDev) scannerDev.textContent = devCount;
            if (scannerWatch) scannerWatch.textContent = watchCount;
            if (scannerTime) scannerTime.textContent = formatLocalTime();
        } else {
            // Show empty state when no data - still update stats to show 0
            console.log('⚠️ No scan data available:', data.message || 'Scanner has not run yet');
            console.log('   data.ok:', data.ok);
            console.log('   data.status:', data.status);
            console.log('   stocks.length:', stocks.length);
            document.getElementById('stat-scanned').textContent = '0';
            document.getElementById('stat-hot').textContent = '0';
            document.getElementById('stat-developing').textContent = '0';
            document.getElementById('stat-watchlist').textContent = '0';

            // Also update scanner tab
            const scannerTotal = document.getElementById('scanner-stat-total');
            if (scannerTotal) scannerTotal.textContent = '0';
            const scannerHot = document.getElementById('scanner-stat-hot');
            if (scannerHot) scannerHot.textContent = '0';
            const scannerDev = document.getElementById('scanner-stat-developing');
            if (scannerDev) scannerDev.textContent = '0';
            const scannerWatch = document.getElementById('scanner-stat-watchlist');
            if (scannerWatch) scannerWatch.textContent = '0';

            renderTopPicks([]);
        }
    } catch (e) {
        console.error('fetchScan error:', e);
        console.error('   Error details:', e.message, e.stack);
        // Show error state in UI
        const statScanned = document.getElementById('stat-scanned');
        if (statScanned) statScanned.textContent = 'Error';
        const statHot = document.getElementById('stat-hot');
        if (statHot) statHot.textContent = '--';
        const statDev = document.getElementById('stat-developing');
        if (statDev) statDev.textContent = '--';
        const statWatch = document.getElementById('stat-watchlist');
        if (statWatch) statWatch.textContent = '--';
    }
}

async function triggerScan(mode = 'indices', evt = null) {
    // Safety: Check if toast is loaded
    const safeToast = window.toast || { error: console.error, success: console.log };

    // Fix: Get button reference safely - use passed event or find button
    const btn = evt?.target || document.querySelector(`button[onclick*="triggerScan('${mode}')"]`) || null;
    if (!btn) {
        safeToast.error('Button reference not found');
        return;
    }

    const originalText = btn.textContent;
    const modeLabel = mode === 'full' ? 'Full Universe' : mode === 'indices' ? 'S&P+NASDAQ' : 'Quick';
    btn.textContent = `⏳ Scanning ${modeLabel}...`;
    btn.disabled = true;

    try {
        const res = await fetch(`${API_BASE}/scan/trigger?mode=${mode}`, { method: 'POST' });
        const data = await res.json();

        if (data.ok && data.status === 'started') {
            // Scan started in background (202 Accepted)
            btn.textContent = `⏳ Scanning ${data.universe_size} stocks...`;
            safeToast.success(`Scan started! Processing ${data.universe_size} stocks in background.`, 5000);

            // Poll for results every 10 seconds
            let pollCount = 0;
            const maxPolls = 30; // 5 minutes max
            const pollInterval = setInterval(async () => {
                pollCount++;
                try {
                    await fetchScan();
                    // If we got new data, stop polling
                    clearInterval(pollInterval);
                    btn.textContent = '✅ Scan complete!';
                    safeToast.success('Scan results updated!');
                    setTimeout(() => {
                        btn.textContent = originalText;
                        btn.disabled = false;
                    }, 2000);
                } catch (e) {
                    // Continue polling
                    if (pollCount >= maxPolls) {
                        clearInterval(pollInterval);
                        btn.textContent = '⏰ Timed out';
                        setTimeout(() => {
                            btn.textContent = originalText;
                            btn.disabled = false;
                        }, 2000);
                    }
                }
            }, 10000); // Poll every 10 seconds

            // Re-enable button after 5 seconds (allow manual refresh)
            setTimeout(() => {
                btn.disabled = false;
            }, 5000);

        } else if (data.ok && data.scanned !== undefined) {
            // Legacy response (scan completed immediately)
            btn.textContent = `✅ ${data.scanned} stocks!`;
            await fetchScan();
            setTimeout(() => {
                btn.textContent = originalText;
                btn.disabled = false;
            }, 2000);
        } else {
            const errorMsg = data.error || 'Scan failed';
            btn.textContent = '❌ ' + errorMsg.substring(0, 20);
            safeToast.error('Scan failed: ' + errorMsg);
            setTimeout(() => {
                btn.textContent = originalText;
                btn.disabled = false;
            }, 3000);
        }
    } catch (e) {
        console.error('Trigger scan failed:', e);
        btn.textContent = '❌ Error';
        safeToast.error('Scan error: ' + (e.message || 'Network issue'));
        setTimeout(() => {
            btn.textContent = originalText;
            btn.disabled = false;
        }, 3000);
    }
}

function renderTopPicks(stocks) {
    const top = stocks.slice(0, 10);
    if (top.length === 0) {
        document.getElementById('top-picks').innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">📊</div>
                <div style="margin-bottom: 8px;">No scan data available</div>
                <div style="font-size: 0.75rem; color: var(--text-muted);">Run /scan on Telegram or wait for scheduled scan</div>
            </div>`;
        return;
    }

    document.getElementById('top-picks').innerHTML = top.map((s, i) => {
        const rankClass = i === 0 ? 'gold' : i === 1 ? 'silver' : i === 2 ? 'bronze' : '';
        return `
            <div class="top-pick" onclick="showTicker('${s.ticker}')">
                <div class="pick-rank ${rankClass}">${i + 1}</div>
                <div class="pick-info">
                    <div class="pick-ticker">${s.ticker}</div>
                    <div class="pick-name">${s.story_strength || 'N/A'}</div>
                </div>
                <div class="pick-score">
                    <div class="pick-score-value">${(s.story_score || 0).toFixed(0)}</div>
                    <div class="pick-score-label">score</div>
                </div>
                ${s.hottest_theme ? `<div class="pick-theme">${s.hottest_theme}</div>` : ''}
            </div>
        `;
    }).join('');
}

function renderScanTable(stocks) {
    window.scanData = stocks;

    // Populate theme filter dropdown
    populateThemeFilter(stocks);

    filterTable();
}

function populateThemeFilter(stocks) {
    const themeFilter = document.getElementById('filter-theme');
    if (!themeFilter || !stocks || stocks.length === 0) return;

    // Extract unique themes from scan data
    const themes = [...new Set(stocks.map(s => s.hottest_theme).filter(t => t && t !== '-'))].sort();

    // Keep "All Themes" option and add discovered themes
    themeFilter.innerHTML = '<option value="">All Themes</option>' +
        themes.map(theme => `<option value="${theme}">${theme}</option>`).join('');
}

// Pagination state
const ITEMS_PER_PAGE = 25;
let currentPage = 1;
let filteredData = [];

function filterTable() {
    const strength = document.getElementById('filter-strength').value;
    const theme = document.getElementById('filter-theme').value;

    filteredData = window.scanData || [];
    if (strength) filteredData = filteredData.filter(s => s.story_strength === strength);
    if (theme) filteredData = filteredData.filter(s => s.hottest_theme === theme);

    currentPage = 1;
    renderPaginatedTable();
}

function renderPaginatedTable() {
    const startIdx = 0;
    const endIdx = currentPage * ITEMS_PER_PAGE;
    const pageData = filteredData.slice(startIdx, endIdx);
    const hasMore = endIdx < filteredData.length;

    let html = pageData.map((s, i) => `
        <tr>
            <td>${i + 1}</td>
            <td class="ticker-cell" onclick="showTicker('${s.ticker}')">${s.ticker}</td>
            <td>
                <span class="score-bar"><span class="score-bar-fill" style="width: ${Math.min(s.story_score || 0, 100)}%"></span></span>
                ${(s.story_score || 0).toFixed(0)}
            </td>
            <td>${s.story_strength || '-'}</td>
            <td>${s.hottest_theme || '-'}</td>
            <td style="color: ${(s.change_pct || 0) >= 0 ? 'var(--green)' : 'var(--red)'};">${(s.change_pct || 0) >= 0 ? '+' : ''}${(s.change_pct || 0).toFixed(2)}%</td>
            <td>${formatVolume(s.volume || 0)}</td>
            <td>${(s.rs_rating || 0).toFixed(0)}</td>
        </tr>
    `).join('');

    // Add "Load More" row if there's more data
    if (hasMore) {
        html += `
            <tr id="load-more-row">
                <td colspan="8" style="text-align: center; padding: 16px;">
                    <button class="btn btn-ghost" onclick="loadMoreResults()" style="min-height: 40px;">
                        Load More (${filteredData.length - endIdx} remaining)
                    </button>
                    <span style="color: var(--text-muted); font-size: 0.75rem; margin-left: 12px;">
                        Showing ${endIdx} of ${filteredData.length}
                    </span>
                </td>
            </tr>
        `;
    }

    document.getElementById('scan-table-body').innerHTML = html;
}

function loadMoreResults() {
    currentPage++;
    renderPaginatedTable();
}

async function fetchConvictionAlerts() {
    try {
        document.getElementById('conviction-alerts-container').innerHTML = '<div style="color: var(--text-muted); font-size: 0.8125rem;">Scanning signals...</div>';
        const res = await fetch(`${API_BASE}/conviction/alerts?min_score=60`);
        const data = await res.json();

        // Handle both data.alerts and data.data response structures
        const alerts = data.alerts || data.data || [];

        if (data.ok && alerts.length > 0) {
            const strengthEmoji = {
                'hot': '🔥',
                'developing': '🟡',
                'watchlist': '⚪'
            };

            let html = '';
            alerts.slice(0, 5).forEach(a => {
                const score = a.conviction_score || a.score || 0;
                const emoji = strengthEmoji[a.strength] || '⚪';
                const label = a.recommendation || a.strength || 'N/A';
                const detail = a.bullish_signals ? `${a.bullish_signals} bullish` : (a.theme || '');

                html += `<div class="sidebar-item" style="cursor: pointer; padding: 8px 0; border-bottom: 1px solid var(--border);" onclick="showConvictionDetail('${a.ticker}')">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-weight: 600;">${a.ticker}</span>
                        <span style="font-size: 0.875rem;">${emoji} ${score.toFixed(0)}</span>
                    </div>
                    <div style="font-size: 0.7rem; color: var(--text-muted); margin-top: 2px;">
                        ${detail} ${detail ? '•' : ''} ${label}
                    </div>
                </div>`;
            });
            document.getElementById('conviction-alerts-container').innerHTML = html;
        } else {
            document.getElementById('conviction-alerts-container').innerHTML = '<div style="color: var(--text-muted); font-size: 0.8125rem;">No high-conviction setups. Signals need to align.</div>';
        }
    } catch (e) {
        console.warn('Conviction alerts fetch failed:', e);
        document.getElementById('conviction-alerts-container').innerHTML = '<div style="color: var(--text-muted); font-size: 0.8125rem;">Could not load conviction data</div>';
    }
}

async function showConvictionDetail(ticker) {
    try {
        const res = await fetch(`${API_BASE}/conviction/${ticker}`);
        const data = await res.json();

        if (data.ok) {
            const recEmoji = {'STRONG BUY': '🟢🟢', 'BUY': '🟢', 'WATCH': '🟡', 'HOLD': '⚪', 'AVOID': '🔴'};
            let msg = `🎯 ${ticker} CONVICTION: ${data.conviction_score.toFixed(0)}/100\n`;
            msg += `Recommendation: ${data.recommendation} ${recEmoji[data.recommendation] || ''}\n\n`;

            msg += `Signals:\n`;
            if (data.signals.insider) msg += `• Insider: ${data.signals.insider.score.toFixed(0)} (${data.signals.insider.signal})\n`;
            if (data.signals.options) msg += `• Options: ${data.signals.options.score.toFixed(0)} (${data.signals.options.signal})\n`;
            if (data.signals.patents) msg += `• Patents: ${data.signals.patents.score.toFixed(0)} (${data.signals.patents.signal})\n`;
            if (data.signals.contracts) msg += `• Contracts: ${data.signals.contracts.score.toFixed(0)} (${data.signals.contracts.signal})\n`;
            if (data.signals.sentiment) msg += `• Sentiment: ${data.signals.sentiment.score.toFixed(0)} (${data.signals.sentiment.signal})\n`;
            if (data.signals.technical) msg += `• Technical: ${data.signals.technical.score.toFixed(0)} (${data.signals.technical.signal})\n`;

            if (data.warnings && data.warnings.length > 0) {
                msg += `\nWarnings: ${data.warnings.join(', ')}`;
            }

            alert(msg);
        }
    } catch (e) {
        console.warn('Conviction detail fetch failed:', e);
    }
}

// Supply Chain Discovery Functions
async function fetchSupplyChain() {
    try {
        document.getElementById('supplychain-container').innerHTML = '<div style="color: var(--text-muted); font-size: 0.8125rem;">🤖 AI analyzing market data...</div>';

        // Try AI-driven discovery first
        let data = null;
        try {
            const aiRes = await fetch(`${API_BASE}/supplychain/ai-discover`);
            data = await aiRes.json();
        } catch (e) {
            console.warn('AI discovery failed, trying static:', e);
        }

        // Fallback to static themes if AI fails
        if (!data || !data.ok || !data.opportunities || data.opportunities.length === 0) {
            const staticRes = await fetch(`${API_BASE}/supplychain/themes`);
            data = await staticRes.json();
            data.isStatic = true;
        }

        if (data.ok) {
            let html = '';

            // AI-driven opportunities
            if (data.opportunities && data.opportunities.length > 0) {
                const themeGroups = {};
                for (const opp of data.opportunities) {
                    const theme = opp.theme || 'Unknown';
                    if (!themeGroups[theme]) themeGroups[theme] = [];
                    themeGroups[theme].push(opp);
                }

                for (const [theme, opps] of Object.entries(themeGroups).slice(0, 4)) {
                    const topOpp = opps[0];
                    const confEmoji = topOpp.confidence > 75 ? '🔥' : topOpp.confidence > 50 ? '🌱' : '👀';

                    html += `<div class="sidebar-item" style="cursor: pointer; padding: 8px 0; border-bottom: 1px solid var(--border);" onclick="showAIOpportunity('${encodeURIComponent(JSON.stringify(opps.slice(0, 5)))}')">
                        <div>
                            <span style="font-weight: 600;">${confEmoji} ${theme}</span>
                            <div style="font-size: 0.7rem; color: var(--text-muted);">${opps.length} opportunities</div>
                            <div style="font-size: 0.7rem; color: var(--green);">Top: ${opps.slice(0, 2).map(o => o.ticker).join(', ')}</div>
                        </div>
                    </div>`;
                }

                html += `<div style="font-size: 0.7rem; color: var(--blue); margin-top: 8px;">🤖 AI-analyzed • ${data.opportunities.length} total</div>`;
            }
            // Static theme mapping
            else if (data.themes && data.themes.length > 0) {
                const stageEmoji = {'emerging': '🌱', 'accelerating': '🚀', 'mainstream': '🌊', 'late': '🍂'};

                for (const theme of data.themes.slice(0, 5)) {
                    const emoji = stageEmoji[theme.lifecycle_stage] || '⚪';
                    html += `<div class="sidebar-item" style="cursor: pointer; padding: 8px 0; border-bottom: 1px solid var(--border);" onclick="showSupplyChainDetail('${theme.theme_id}')">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <span style="font-weight: 600;">${emoji} ${theme.theme_name}</span>
                                <div style="font-size: 0.7rem; color: var(--text-muted);">${theme.laggard_count} lagging plays</div>
                            </div>
                            <span style="color: var(--green); font-size: 0.8rem;">${theme.opportunity_score?.toFixed(0) || '--'}</span>
                        </div>
                    </div>`;
                }

                html += `<div style="font-size: 0.7rem; color: var(--text-muted); margin-top: 8px;">Total: ${data.total_opportunities} opportunities</div>`;
            } else {
                html = '<div style="color: var(--text-muted); font-size: 0.8125rem;">No lagging plays found.</div>';
            }

            document.getElementById('supplychain-container').innerHTML = html;
        } else {
            document.getElementById('supplychain-container').innerHTML = '<div style="color: var(--text-muted); font-size: 0.8125rem;">No lagging plays found. Run a scan first.</div>';
        }
    } catch (e) {
        console.warn('Supply chain fetch failed:', e);
        document.getElementById('supplychain-container').innerHTML = '<div style="color: var(--text-muted); font-size: 0.8125rem;">Could not load supply chain data</div>';
    }
}

function showAIOpportunity(encodedData) {
    try {
        const opps = JSON.parse(decodeURIComponent(encodedData));
        let msg = '🤖 AI SUPPLY CHAIN OPPORTUNITIES\n\n';

        for (const opp of opps) {
            msg += `• ${opp.ticker} (${opp.role || opp.source})\n`;
            if (opp.connection) msg += `  Connection: ${opp.connection}\n`;
            if (opp.catalyst) msg += `  Catalyst: ${opp.catalyst}\n`;
            if (opp.thesis) msg += `  Thesis: ${opp.thesis}\n`;
            if (opp.opportunity_score) msg += `  Score: ${opp.opportunity_score}/100\n`;
            msg += '\n';
        }

        alert(msg);
    } catch (e) {
        console.warn('Failed to parse AI opportunity:', e);
    }
}

async function showSupplyChainDetail(themeId) {
    try {
        const res = await fetch(`${API_BASE}/supplychain/${themeId}`);
        const data = await res.json();

        if (data.ok && data.theme) {
            const theme = data.theme;
            let msg = `🔗 SUPPLY CHAIN: ${theme.theme_name}\n`;
            msg += `Stage: ${theme.lifecycle_stage.toUpperCase()}\n`;
            msg += `Opportunity: ${theme.opportunity_score.toFixed(0)}/100\n\n`;

            msg += `Lagging Plays (${theme.laggard_count} stocks):\n`;

            // Show suppliers that haven't moved
            const allNodes = [...(theme.suppliers || []), ...(theme.equipment || []), ...(theme.materials || []), ...(theme.beneficiaries || []), ...(theme.infrastructure || [])];
            const laggards = allNodes.filter(n => !n.has_moved).sort((a, b) => b.opportunity_score - a.opportunity_score).slice(0, 8);

            for (const node of laggards) {
                const perf = node.price_performance_30d >= 0 ? '+' + node.price_performance_30d.toFixed(1) : node.price_performance_30d.toFixed(1);
                msg += `• ${node.ticker} (${node.role}): Story ${node.story_score.toFixed(0)}, 30d: ${perf}%\n`;
            }

            msg += `\nValidation:\n`;
            msg += `• Patents: ${theme.patent_validation.toFixed(0)}/100\n`;
            msg += `• Contracts: ${theme.contract_validation.toFixed(0)}/100\n`;
            msg += `• Insider: ${theme.insider_validation.toFixed(0)}/100\n`;
            msg += `\n${theme.estimated_runway}`;

            alert(msg);
        }
    } catch (e) {
        console.warn('Supply chain detail fetch failed:', e);
    }
}

async function fetchEarnings() {
    try {
        const res = await fetch(`${API_BASE}/earnings`);
        const data = await res.json();
        if (data.ok && data.earnings) {
            const upcoming = data.earnings.slice(0, 5);
            if (upcoming.length === 0) {
                document.getElementById('earnings-sidebar').innerHTML = '<div style="color: var(--text-muted); font-size: 0.8125rem;">No upcoming earnings</div>';
                return;
            }
            document.getElementById('earnings-sidebar').innerHTML = upcoming.map(e => `
                <div class="sidebar-item" style="cursor: pointer;" onclick="showTicker('${e.ticker}')">
                    <span style="font-weight: 600;">${e.ticker}</span>
                    <span style="font-size: 0.75rem; color: ${e.days_until === 0 ? 'var(--red)' : e.days_until === 1 ? 'var(--yellow)' : 'var(--text-muted)'};">
                        ${e.days_until === 0 ? 'TODAY' : e.days_until === 1 ? 'Tomorrow' : e.days_until + 'd'}
                    </span>
                </div>
            `).join('');

            // Show alert if earnings today
            const today = data.earnings.filter(e => e.days_until === 0);
            if (today.length > 0) {
                document.getElementById('alerts-container').innerHTML = `
                    <div class="alert warning">
                        <span class="alert-icon">⚠️</span>
                        <span><strong>${today.length} stock(s)</strong> report earnings today: ${today.map(e => e.ticker).join(', ')}</span>
                    </div>
                `;
            }
        }
    } catch (e) { console.warn('Earnings fetch failed:', e); }
}

async function fetchEvolution() {
    try {
        const statusRes = await fetch(`${API_BASE}/evolution/status`);
        const status = await statusRes.json();
        if (status.ok) {
            document.getElementById('evo-cycles').textContent = status.learning_cycles || 0;
            document.getElementById('evo-accuracy').textContent = ((status.overall_accuracy || 0) * 100).toFixed(1) + '%';
            document.getElementById('evo-calibration').textContent = ((status.calibration_score || 0) * 100).toFixed(1) + '%';
            document.getElementById('evo-last').textContent = status.last_evolution || 'Never';
        }

        const weightsRes = await fetch(`${API_BASE}/evolution/weights`);
        const weights = await weightsRes.json();
        if (weights.ok && weights.weights) {
            const w = weights.weights;
            document.getElementById('weights-container').innerHTML = Object.entries(w).slice(0, 6).map(([k, v]) => `
                <div class="sidebar-item">
                    <span class="sidebar-label">${k.replace(/_/g, ' ')}</span>
                    <span class="sidebar-value">${(v * 100).toFixed(0)}%</span>
                </div>
            `).join('');
        }
    } catch (e) { console.warn('Evolution fetch failed:', e); }
}

async function fetchParameters() {
    try {
        const res = await fetch(`${API_BASE}/parameters/status`);
        const data = await res.json();
        if (data.ok) {
            const p = data.parameters || {};
            document.getElementById('param-total').textContent = p.total || 0;
            document.getElementById('param-learned').textContent = p.learned || 0;
            document.getElementById('param-progress').textContent = ((p.learning_progress || 0) * 100).toFixed(0) + '%';
            document.getElementById('param-confidence').textContent = ((p.avg_confidence || 0) * 100).toFixed(0) + '%';
        }
    } catch (e) { console.warn('Parameters fetch failed:', e); }
}

async function fetchCorrelations() {
    try {
        const res = await fetch(`${API_BASE}/evolution/correlations`);
        const data = await res.json();
        if (data.ok && data.correlations) {
            const corrs = Object.entries(data.correlations).slice(0, 5);
            if (corrs.length === 0) {
                document.getElementById('correlations-container').innerHTML = '<div style="color: var(--text-muted); font-size: 0.8125rem;">No correlations discovered yet</div>';
                return;
            }
            document.getElementById('correlations-container').innerHTML = corrs.map(([pair, value]) => `
                <div class="sidebar-item">
                    <span class="sidebar-label">${pair}</span>
                    <span class="sidebar-value" style="color: ${value >= 0.5 ? 'var(--green)' : value <= -0.5 ? 'var(--red)' : 'var(--text)'};">${(value * 100).toFixed(0)}%</span>
                </div>
            `).join('');
        }
    } catch (e) { console.warn('Correlations fetch failed:', e); }
}

async function fetchThemes() {
    try {
        const res = await fetch(`${API_BASE}/themes/list`);
        const data = await res.json();

        // Handle both data.themes and data.data structures
        const themesArray = data.themes || data.data || [];

        if (data.ok) {
            // Convert array to object if needed
            if (Array.isArray(themesArray)) {
                window.themesData = {};
                themesArray.forEach(theme => {
                    if (theme.name) {
                        window.themesData[theme.name] = theme;
                    }
                });
            } else {
                window.themesData = themesArray;
            }

            // Render themes to DOM
            renderThemes();
        }
    } catch (e) {
        console.warn('Themes fetch failed:', e);
        renderThemes(); // Show empty state
    }
}

function renderThemes() {
    const themes = window.themesData || {};
    const themeNames = Object.keys(themes);

    // Render theme pills for Themes tab
    const allThemesContainer = document.getElementById('all-themes');
    // Render theme pills for Dashboard Hot Themes
    const dashboardThemePills = document.getElementById('theme-pills');

    if (themeNames.length === 0) {
        if (allThemesContainer) {
            allThemesContainer.innerHTML = '<div style="color: var(--text-muted); font-size: 0.875rem; padding: 16px;">No themes available. Themes will appear here after a scan is completed.</div>';
        }
        if (dashboardThemePills) {
            dashboardThemePills.innerHTML = '<div style="color: var(--text-muted); font-size: 0.875rem;">No themes available</div>';
        }
        const themeCards = document.getElementById('theme-cards');
        if (themeCards) themeCards.innerHTML = '';
        return;
    }

    const themePillsHtml = themeNames.map(name => `
        <span class="theme-pill" onclick="selectTheme('${name}')">${name}</span>
    `).join('');

    // Populate both containers
    if (allThemesContainer) allThemesContainer.innerHTML = themePillsHtml;
    if (dashboardThemePills) dashboardThemePills.innerHTML = themePillsHtml;

    // Render theme cards for Themes tab
    const themeCardsContainer = document.getElementById('theme-cards');
    if (themeCardsContainer) {
        themeCardsContainer.innerHTML = themeNames.map(name => {
            const theme = themes[name];
            const tickerCount = theme.tickers ? theme.tickers.length : (theme.count || 0);
            return `
                <div class="card card-glass" style="cursor: pointer;" onclick="selectTheme('${name}')">
                    <div class="card-body">
                        <div style="font-weight: var(--font-semibold); font-size: var(--text-lg); margin-bottom: 8px; color: var(--text);">${name}</div>
                        <div style="color: var(--text-muted); font-size: var(--text-sm);">${tickerCount} stocks</div>
                    </div>
                </div>
            `;
        }).join('');
    }

    // Auto-select first theme to populate dashboard stocks grid
    if (themeNames.length > 0) {
        selectTheme(themeNames[0]);
    }
}

function selectTheme(themeName) {
    // Highlight selected pill
    document.querySelectorAll('.theme-pill').forEach(pill => {
        pill.classList.toggle('active', pill.textContent.includes(themeName));
    });

    // Show theme stocks
    const themes = window.themesData || {};
    const theme = themes[themeName];
    if (theme && theme.tickers) {
        document.getElementById('theme-stocks-grid').innerHTML = theme.tickers.slice(0, 12).map(ticker => `
            <div class="theme-stock" onclick="showTicker('${ticker}')">
                <div class="theme-stock-ticker">${ticker}</div>
            </div>
        `).join('');
    }
}

async function fetchBriefing() {
    document.getElementById('briefing-container').innerHTML = '<div style="color: var(--text-muted);">Generating AI briefing...</div>';
    try {
        const res = await fetch(`${API_BASE}/briefing`);
        const data = await res.json();
        if (data.ok && data.briefing) {
            document.getElementById('briefing-container').innerHTML = `
                <div style="white-space: pre-wrap; line-height: 1.7; font-size: 0.875rem;">${data.briefing}</div>
            `;
        }
    } catch (e) {
        document.getElementById('briefing-container').innerHTML = '<div style="color: var(--red);">Failed to generate briefing</div>';
    }
}

// =============================================================================
// AI INTELLIGENCE HUB
// =============================================================================

async function fetchAIIntelligence() {
    console.log('🔄 fetchAIIntelligence() called');
    // Show loading states
    document.getElementById('regime-label').textContent = 'Analyzing...';
    document.getElementById('regime-reasoning').textContent = 'AI is processing market data...';
    document.getElementById('ai-synthesis-container').innerHTML = '<div style="color: var(--text-muted);">🧠 Generating AI intelligence... This may take 10-20 seconds.</div>';
    document.getElementById('signal-matrix-container').innerHTML = '<div style="color: var(--text-muted);">Loading signals...</div>';

    try {
        // Fetch signal matrix first (faster)
        const matrixRes = await fetch(`${API_BASE}/ai/matrix`);
        const matrixData = await matrixRes.json();
        console.log('📦 Matrix API response:', matrixData);
        if (matrixData.ok || matrixData.status === 'success' || matrixData.signals) {
            renderSignalMatrix(matrixData);
        } else {
            console.warn('⚠️ Signal matrix: unexpected response', matrixData);
        }

        // Fetch full intelligence
        const res = await fetch(`${API_BASE}/ai/intelligence`);
        const data = await res.json();
        console.log('📦 Intelligence API response:', data);

        // Check for success - API may return ok:true or have analysis directly
        if ((data.ok || data.status === 'success') && data.analysis) {
            renderAIIntelligence(data.analysis);
        } else if (data.analysis) {
            // Some APIs return analysis without ok flag
            renderAIIntelligence(data.analysis);
        } else {
            console.warn('⚠️ AI Intelligence: unexpected response', data);
            document.getElementById('ai-synthesis-container').innerHTML = `<div style="color: var(--red);">Error: ${data.error || 'Failed to generate intelligence'}</div>`;
        }
    } catch (e) {
        console.error('❌ AI Intelligence error:', e);
        document.getElementById('ai-synthesis-container').innerHTML = '<div style="color: var(--red);">Failed to connect to AI service</div>';
    }
}

function renderSignalMatrix(data) {
    const signals = data.signals || {};
    const container = document.getElementById('signal-matrix-container');

    let html = '<div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px;">';

    for (const [key, signal] of Object.entries(signals)) {
        const color = signal.signal === 'BULLISH' ? 'var(--green)' :
                      signal.signal === 'BEARISH' ? 'var(--red)' : 'var(--text-muted)';
        const emoji = signal.signal === 'BULLISH' ? '🟢' :
                      signal.signal === 'BEARISH' ? '🔴' : '🟡';

        html += `
            <div style="padding: 10px; background: var(--bg-hover); border-radius: 6px; border-left: 3px solid ${color};">
                <div style="font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase;">${key.replace(/_/g, ' ')}</div>
                <div style="display: flex; align-items: center; gap: 6px; margin-top: 4px;">
                    <span>${emoji}</span>
                    <span style="font-weight: 600; color: ${color};">${signal.signal}</span>
                    <span style="font-size: 0.75rem; color: var(--text-muted);">${signal.value || ''}</span>
                </div>
            </div>
        `;
    }
    html += '</div>';

    // Add interpretation
    if (data.interpretation && data.interpretation.overall_signal) {
        const interp = data.interpretation;
        html += `
            <div style="margin-top: 12px; padding: 10px; background: rgba(99, 102, 241, 0.1); border-radius: 6px;">
                <div style="font-weight: 600; color: var(--primary);">AI Interpretation: ${interp.overall_signal}</div>
                <div style="font-size: 0.8rem; color: var(--text-muted); margin-top: 4px;">${interp.key_insight || ''}</div>
            </div>
        `;
    }

    container.innerHTML = html;

    // Render confirmations and conflicts
    renderConfirmationsConflicts(data);
}

function renderConfirmationsConflicts(data) {
    const container = document.getElementById('confirmations-container');
    let html = '';

    // Confirmations
    if (data.confirmations && data.confirmations.length > 0) {
        html += '<div style="margin-bottom: 12px;"><div style="font-size: 0.75rem; color: var(--green); font-weight: 600; margin-bottom: 6px;">✅ CONFIRMATIONS</div>';
        for (const conf of data.confirmations) {
            html += `
                <div style="padding: 8px; background: rgba(34, 197, 94, 0.1); border-radius: 4px; margin-bottom: 4px; font-size: 0.8rem;">
                    <span style="color: var(--green);">${conf.signals.join(' ↔ ')}</span>
                    <span style="color: var(--text-muted);"> → ${conf.direction}</span>
                </div>
            `;
        }
        html += '</div>';
    }

    // Conflicts
    if (data.conflicts && data.conflicts.length > 0) {
        html += '<div><div style="font-size: 0.75rem; color: var(--yellow); font-weight: 600; margin-bottom: 6px;">⚠️ CONFLICTS</div>';
        for (const conf of data.conflicts) {
            html += `
                <div style="padding: 8px; background: rgba(234, 179, 8, 0.1); border-radius: 4px; margin-bottom: 4px; font-size: 0.8rem;">
                    <span style="color: var(--yellow);">${conf.note}</span>
                </div>
            `;
        }
        html += '</div>';
    }

    if (!html) {
        html = '<div style="color: var(--text-muted); font-size: 0.8rem;">No strong confirmations or conflicts detected</div>';
    }

    container.innerHTML = html;
}

function renderAIIntelligence(analysis) {
    // Regime
    if (analysis.regime) {
        const regime = analysis.regime;
        const emoji = regime.label === 'RISK-ON' ? '🚀' :
                      regime.label === 'RISK-OFF' ? '🛡️' :
                      regime.label === 'ROTATION' ? '🔄' : '📊';
        document.getElementById('regime-emoji').textContent = emoji;
        document.getElementById('regime-label').textContent = regime.label || 'ANALYZING';
        document.getElementById('regime-reasoning').textContent = regime.reasoning || '';
        document.getElementById('regime-confidence').textContent = `${regime.confidence || 0}%`;
    }

    // AI Synthesis
    let synthesisHtml = '';
    if (analysis.macro_theme_connection) {
        const macro = analysis.macro_theme_connection;
        synthesisHtml += `
            <div style="margin-bottom: 16px;">
                <div style="font-size: 0.75rem; color: var(--primary); font-weight: 600; margin-bottom: 6px;">MACRO → THEME CONNECTION</div>
                <div style="padding: 12px; background: var(--bg-hover); border-radius: 6px;">
                    <div style="display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 8px;">
                        ${(macro.supporting_themes || []).map(t => `<span style="padding: 4px 8px; background: rgba(99, 102, 241, 0.2); border-radius: 4px; font-size: 0.75rem;">${t}</span>`).join('')}
                    </div>
                    <div style="font-size: 0.85rem; color: var(--text);">${macro.reasoning || ''}</div>
                </div>
            </div>
        `;
    }
    document.getElementById('ai-synthesis-container').innerHTML = synthesisHtml || '<div style="color: var(--text-muted);">No synthesis available</div>';

    // Conviction Picks
    if (analysis.top_conviction_picks && analysis.top_conviction_picks.length > 0) {
        let picksHtml = '';
        for (const pick of analysis.top_conviction_picks) {
            picksHtml += `
                <div style="padding: 12px; background: var(--bg-hover); border-radius: 6px; margin-bottom: 8px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-weight: 700; font-size: 1.1rem; color: var(--primary);">${pick.ticker}</span>
                        <button class="btn btn-ghost" style="padding: 2px 8px; font-size: 0.7rem;" onclick="fetchAIReasoning('${pick.ticker}')">📊 Detail</button>
                    </div>
                    <div style="font-size: 0.85rem; margin-top: 6px; color: var(--text);">${pick.reasoning || ''}</div>
                    <div style="font-size: 0.75rem; margin-top: 4px; color: var(--red);">⚠️ Risk: ${pick.risk || 'N/A'}</div>
                </div>
            `;
        }
        document.getElementById('conviction-picks-container').innerHTML = picksHtml;
    }

    // Trade Ideas
    if (analysis.trade_ideas && analysis.trade_ideas.length > 0) {
        let ideasHtml = '';
        for (const idea of analysis.trade_ideas) {
            ideasHtml += `
                <div style="padding: 12px; background: var(--bg-hover); border-radius: 6px; margin-bottom: 8px;">
                    <div style="font-weight: 600; color: var(--green);">💡 ${idea.idea}</div>
                    <div style="font-size: 0.85rem; margin-top: 6px; color: var(--text);">${idea.rationale || ''}</div>
                    <div style="font-size: 0.75rem; margin-top: 4px; color: var(--yellow);">❌ Invalidation: ${idea.invalidation || 'N/A'}</div>
                </div>
            `;
        }
        document.getElementById('trade-ideas-container').innerHTML = ideasHtml;
    }

    // Key Risks
    if (analysis.key_risks && analysis.key_risks.length > 0) {
        let risksHtml = '<ul style="margin: 0; padding-left: 20px;">';
        for (const risk of analysis.key_risks) {
            risksHtml += `<li style="margin-bottom: 6px; color: var(--text);">${risk}</li>`;
        }
        risksHtml += '</ul>';
        document.getElementById('key-risks-container').innerHTML = risksHtml;
    }

    // Market Narrative
    if (analysis.summary) {
        document.getElementById('market-narrative').textContent = analysis.summary;
    }
}

async function fetchAIDigest() {
    document.getElementById('daily-digest-container').innerHTML = '<div style="color: var(--text-muted);">📰 Generating daily digest...</div>';

    try {
        const res = await fetch(`${API_BASE}/ai/digest`);
        const data = await res.json();

        if (data.ok && data.digest) {
            const d = data.digest;
            let html = `
                <div style="margin-bottom: 12px;">
                    <div style="font-size: 1.1rem; font-weight: 700; color: var(--text);">${d.headline || 'Market Update'}</div>
                    <div style="font-size: 0.8rem; color: var(--text-muted); margin-top: 4px;">${data.date || ''}</div>
                </div>
                <div style="padding: 10px; background: var(--bg-hover); border-radius: 6px; margin-bottom: 12px;">
                    <span style="font-weight: 600;">Stance:</span> ${d.market_stance || 'N/A'}
                </div>
            `;

            if (d.top_3_ideas && d.top_3_ideas.length > 0) {
                html += '<div style="font-size: 0.75rem; color: var(--primary); font-weight: 600; margin-bottom: 6px;">TOP IDEAS</div>';
                for (const idea of d.top_3_ideas) {
                    const actionColor = idea.action === 'BUY' ? 'var(--green)' :
                                        idea.action === 'AVOID' ? 'var(--red)' : 'var(--yellow)';
                    html += `
                        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px;">
                            <span style="font-weight: 600;">${idea.ticker}</span>
                            <span style="padding: 2px 6px; background: ${actionColor}20; color: ${actionColor}; border-radius: 4px; font-size: 0.7rem;">${idea.action}</span>
                            <span style="font-size: 0.8rem; color: var(--text-muted);">${idea.reason}</span>
                        </div>
                    `;
                }
            }

            if (d.one_liner) {
                html += `
                    <div style="margin-top: 12px; padding: 10px; background: rgba(99, 102, 241, 0.1); border-radius: 6px; border-left: 3px solid var(--primary);">
                        <div style="font-size: 0.85rem; font-style: italic;">"${d.one_liner}"</div>
                    </div>
                `;
            }

            document.getElementById('daily-digest-container').innerHTML = html;
        }
    } catch (e) {
        document.getElementById('daily-digest-container').innerHTML = '<div style="color: var(--red);">Failed to generate digest</div>';
    }
}

function closeAIReasoningModal() {
    const modal = document.getElementById('ai-reasoning-modal');
    if (modal) modal.remove();
}

async function fetchAIReasoning(ticker) {
    try {
        const res = await fetch(`${API_BASE}/ai/reasoning/${ticker}`);
        const data = await res.json();

        if (data.ok && data.analysis) {
            const a = data.analysis;
            let html = `
                <div id="ai-reasoning-modal">
                    <div onclick="closeAIReasoningModal()" style="position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); z-index: 9999;"></div>
                    <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px; padding: 24px; max-width: 500px; width: 90%; max-height: 80vh; overflow-y: auto; z-index: 10000; box-shadow: 0 20px 60px rgba(0,0,0,0.5);">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                            <span style="font-size: 1.5rem; font-weight: 700;">${ticker}</span>
                            <button onclick="closeAIReasoningModal()" style="background: none; border: none; color: var(--text-muted); cursor: pointer; font-size: 1.5rem;">&times;</button>
                        </div>
                        <div style="margin-bottom: 12px;">
                            <div style="font-size: 0.75rem; color: var(--primary); font-weight: 600;">THESIS</div>
                            <div style="font-size: 0.9rem; margin-top: 4px;">${a.thesis || 'N/A'}</div>
                        </div>
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 12px;">
                            <div>
                                <div style="font-size: 0.75rem; color: var(--green); font-weight: 600;">BULL CASE</div>
                                <ul style="margin: 4px 0 0 16px; padding: 0; font-size: 0.8rem;">
                                    ${(a.bull_case || []).map(b => `<li>${b}</li>`).join('')}
                                </ul>
                            </div>
                            <div>
                                <div style="font-size: 0.75rem; color: var(--red); font-weight: 600;">BEAR CASE</div>
                                <ul style="margin: 4px 0 0 16px; padding: 0; font-size: 0.8rem;">
                                    ${(a.bear_case || []).map(b => `<li>${b}</li>`).join('')}
                                </ul>
                            </div>
                        </div>
                        <div style="padding: 10px; background: var(--bg-hover); border-radius: 6px;">
                            <span style="font-weight: 600;">Conviction:</span> ${a.conviction_level || 'N/A'}
                            <span style="margin-left: 12px; font-weight: 600;">Timeline:</span> ${a.catalyst_timeline || 'N/A'}
                        </div>
                        <div style="margin-top: 12px; padding: 10px; background: rgba(99, 102, 241, 0.1); border-radius: 6px;">
                            <div style="font-size: 0.85rem;">${a.suggested_action || ''}</div>
                        </div>
                    </div>
                </div>
            `;
            // Remove existing modal if any
            closeAIReasoningModal();
            document.body.insertAdjacentHTML('beforeend', html);
        }
    } catch (e) {
        console.error('AI Reasoning error:', e);
    }
}

// =============================================================================
// AGENTIC BRAIN - Hierarchical AI Intelligence System
// =============================================================================

async function fetchAgenticStatus() {
    console.log('🧠 fetchAgenticStatus() called');
    const container = document.getElementById('agentic-status-container');
    if (!container) return;

    container.innerHTML = '<div style="color: var(--text-muted);">🧠 Loading AI brain status...</div>';

    try {
        const res = await fetch(`${API_BASE}/ai/agentic/status`);
        const data = await res.json();
        console.log('📦 Agentic status response:', data);

        if (data.ok) {
            renderAgenticStatus(data);
        } else {
            container.innerHTML = `<div style="color: var(--red);">Error: ${data.error || 'Failed to load'}</div>`;
        }
    } catch (e) {
        console.error('Agentic status error:', e);
        container.innerHTML = '<div style="color: var(--red);">Failed to connect to AI brain</div>';
    }
}

function renderAgenticStatus(data) {
    const container = document.getElementById('agentic-status-container');
    if (!container) return;

    const stance = data.market_stance || {};
    const health = data.market_health || {};
    const directors = data.directors || {};

    let html = `
        <!-- Market Stance -->
        <div style="text-align: center; padding: 12px; background: var(--bg-hover); border-radius: 8px; margin-bottom: 12px;">
            <div style="font-size: 2rem;">${stance.emoji || '⚖️'}</div>
            <div style="font-size: 1.1rem; font-weight: 700; color: ${stance.stance === 'OFFENSIVE' ? 'var(--green)' : stance.stance === 'DEFENSIVE' ? 'var(--red)' : 'var(--yellow)'};">${stance.stance || 'NEUTRAL'}</div>
            <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 4px;">${stance.description || ''}</div>
            <div style="font-size: 0.7rem; color: var(--text-muted); margin-top: 2px;">Confidence: ${stance.confidence || 0}%</div>
        </div>

        <!-- Directors Grid -->
        <div style="font-size: 0.7rem; color: var(--primary); font-weight: 600; margin-bottom: 6px;">5 DIRECTORS (35 SPECIALISTS)</div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 6px; margin-bottom: 12px;">
    `;

    const directorOrder = ['theme_intelligence', 'trading_intelligence', 'learning_adaptation', 'realtime_intelligence', 'validation_feedback'];
    const directorLabels = {
        'theme_intelligence': 'Theme',
        'trading_intelligence': 'Trading',
        'learning_adaptation': 'Learning',
        'realtime_intelligence': 'Realtime',
        'validation_feedback': 'Validation'
    };

    for (const key of directorOrder) {
        const d = directors[key] || {};
        html += `
            <div style="padding: 6px; background: var(--bg-hover); border-radius: 4px; font-size: 0.75rem;">
                <span>${d.emoji || '📊'}</span>
                <span style="font-weight: 600;">${directorLabels[key]}</span>
                <span style="color: var(--text-muted);">(${d.specialists || 0})</span>
            </div>
        `;
    }

    html += `</div>`;

    // Emerging Themes
    if (data.emerging_themes && data.emerging_themes.length > 0) {
        html += `<div style="font-size: 0.7rem; color: var(--green); font-weight: 600; margin-bottom: 4px;">🔥 HOT THEMES</div>`;
        html += `<div style="display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 8px;">`;
        for (const t of data.emerging_themes.slice(0, 3)) {
            html += `<span style="padding: 2px 6px; background: rgba(34, 197, 94, 0.2); border-radius: 4px; font-size: 0.7rem;">${t.name}</span>`;
        }
        html += `</div>`;
    }

    // Fading Themes
    if (data.fading_themes && data.fading_themes.length > 0) {
        html += `<div style="font-size: 0.7rem; color: var(--red); font-weight: 600; margin-bottom: 4px;">📉 FADING</div>`;
        html += `<div style="display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 8px;">`;
        for (const t of data.fading_themes.slice(0, 3)) {
            html += `<span style="padding: 2px 6px; background: rgba(239, 68, 68, 0.2); border-radius: 4px; font-size: 0.7rem;">${t.name}</span>`;
        }
        html += `</div>`;
    }

    // Alerts
    if (data.alerts && data.alerts.length > 0) {
        html += `<div style="font-size: 0.7rem; color: var(--yellow); font-weight: 600; margin-bottom: 4px;">⚠️ ALERTS</div>`;
        for (const alert of data.alerts.slice(0, 2)) {
            const msg = alert.message || alert;
            html += `<div style="font-size: 0.7rem; color: var(--text-muted); margin-bottom: 2px;">• ${typeof msg === 'string' ? msg.substring(0, 50) : 'Alert'}...</div>`;
        }
    }

    container.innerHTML = html;
}

async function fetchAgenticPicks() {
    console.log('🧠 fetchAgenticPicks() called');
    try {
        const res = await fetch(`${API_BASE}/ai/agentic/picks`);
        const data = await res.json();
        console.log('📦 Agentic picks response:', data);

        if (data.ok && data.picks) {
            renderAgenticPicks(data.picks);
        }
    } catch (e) {
        console.error('Agentic picks error:', e);
    }
}

function renderAgenticPicks(picks) {
    const container = document.getElementById('conviction-picks-container');
    if (!container || !picks || picks.length === 0) return;

    let html = '';
    for (const pick of picks) {
        const scores = pick.director_scores || {};
        const avgScore = ((scores.theme || 0) + (scores.trading || 0) + (scores.learning || 0) + (scores.realtime || 0) + (scores.validation || 0)) / 5;

        const decisionColor = pick.decision === 'strong_buy' || pick.decision === 'buy' ? 'var(--green)' :
                              pick.decision === 'sell' || pick.decision === 'strong_sell' ? 'var(--red)' : 'var(--yellow)';

        html += `
            <div style="padding: 12px; background: var(--bg-hover); border-radius: 8px; margin-bottom: 10px; cursor: pointer;" onclick="showAgenticDeepDive('${pick.ticker}')">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <div>
                        <span style="font-weight: 700; font-size: 1.1rem; color: var(--primary);">${pick.ticker}</span>
                        ${pick.theme ? `<span style="margin-left: 8px; padding: 2px 6px; background: rgba(99, 102, 241, 0.2); border-radius: 4px; font-size: 0.7rem;">${pick.theme}</span>` : ''}
                    </div>
                    <div style="text-align: right;">
                        <div style="font-weight: 600; color: ${decisionColor}; text-transform: uppercase; font-size: 0.8rem;">${(pick.decision || 'hold').replace('_', ' ')}</div>
                        <div style="font-size: 0.7rem; color: var(--text-muted);">${pick.confidence || 0}% conf</div>
                    </div>
                </div>

                <!-- Director Scores Bar -->
                <div style="display: flex; gap: 4px; margin-bottom: 8px;">
                    <div style="flex: 1; height: 4px; background: rgba(139, 92, 246, ${(scores.theme || 0) / 10}); border-radius: 2px;" title="Theme: ${scores.theme || 0}"></div>
                    <div style="flex: 1; height: 4px; background: rgba(59, 130, 246, ${(scores.trading || 0) / 10}); border-radius: 2px;" title="Trading: ${scores.trading || 0}"></div>
                    <div style="flex: 1; height: 4px; background: rgba(16, 185, 129, ${(scores.learning || 0) / 10}); border-radius: 2px;" title="Learning: ${scores.learning || 0}"></div>
                    <div style="flex: 1; height: 4px; background: rgba(245, 158, 11, ${(scores.realtime || 0) / 10}); border-radius: 2px;" title="Realtime: ${scores.realtime || 0}"></div>
                    <div style="flex: 1; height: 4px; background: rgba(34, 197, 94, ${(scores.validation || 0) / 10}); border-radius: 2px;" title="Validation: ${scores.validation || 0}"></div>
                </div>

                <!-- Trade Plan -->
                ${pick.trade_plan && pick.trade_plan.entry ? `
                <div style="display: flex; gap: 12px; font-size: 0.75rem; color: var(--text-muted);">
                    <span>Entry: $${pick.trade_plan.entry?.toFixed(2) || 'N/A'}</span>
                    <span style="color: var(--red);">Stop: $${pick.trade_plan.stop?.toFixed(2) || 'N/A'}</span>
                    ${pick.trade_plan.targets && pick.trade_plan.targets[0] ? `<span style="color: var(--green);">Target: $${pick.trade_plan.targets[0]?.toFixed(2)}</span>` : ''}
                </div>
                ` : ''}

                <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 6px;">${pick.reasoning || ''}</div>
            </div>
        `;
    }

    container.innerHTML = html;
}

function closeAgenticModal() {
    const modal = document.getElementById('agentic-deep-dive-modal');
    if (modal) modal.remove();
}

async function showAgenticDeepDive(ticker) {
    console.log('🧠 showAgenticDeepDive() called for', ticker);

    // Show loading modal
    let loadingHtml = `
        <div id="agentic-deep-dive-modal">
            <div onclick="closeAgenticModal()" style="position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.7); z-index: 9999;"></div>
            <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: var(--bg-card); border: 1px solid rgba(139, 92, 246, 0.3); border-radius: 16px; padding: 24px; max-width: 600px; width: 95%; max-height: 85vh; overflow-y: auto; z-index: 10000; box-shadow: 0 25px 80px rgba(139, 92, 246, 0.3);">
                <div style="text-align: center; padding: 40px;">
                    <div style="font-size: 2rem; margin-bottom: 12px;">🧠</div>
                    <div style="font-size: 1.2rem; font-weight: 600;">${ticker}</div>
                    <div style="color: var(--text-muted); margin-top: 8px;">Analyzing with 35 AI specialists...</div>
                    <div style="margin-top: 16px; display: flex; justify-content: center; gap: 4px;">
                        <div style="width: 8px; height: 8px; background: var(--primary); border-radius: 50%; animation: pulse 1s infinite;"></div>
                        <div style="width: 8px; height: 8px; background: var(--primary); border-radius: 50%; animation: pulse 1s infinite 0.2s;"></div>
                        <div style="width: 8px; height: 8px; background: var(--primary); border-radius: 50%; animation: pulse 1s infinite 0.4s;"></div>
                    </div>
                </div>
            </div>
        </div>
    `;
    closeAgenticModal();
    document.body.insertAdjacentHTML('beforeend', loadingHtml);

    try {
        const res = await fetch(`${API_BASE}/ai/agentic/${ticker}`);
        const data = await res.json();
        console.log('📦 Agentic deep dive response:', data);

        if (data.ok) {
            renderAgenticDeepDive(data);
        } else {
            closeAgenticModal();
            alert(`Analysis failed: ${data.error || 'Unknown error'}`);
        }
    } catch (e) {
        console.error('Agentic deep dive error:', e);
        closeAgenticModal();
        alert('Failed to analyze stock');
    }
}

function renderAgenticDeepDive(data) {
    const decision = data.decision || {};
    const trade = data.trade_plan || {};
    const scores = data.director_scores || {};
    const analysis = data.analysis || {};
    const scan = data.scan_data || {};

    const decisionColor = decision.action === 'strong_buy' || decision.action === 'buy' ? 'var(--green)' :
                          decision.action === 'sell' || decision.action === 'strong_sell' ? 'var(--red)' : 'var(--yellow)';

    let html = `
        <div id="agentic-deep-dive-modal">
            <div onclick="closeAgenticModal()" style="position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.7); z-index: 9999;"></div>
            <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: var(--bg-card); border: 1px solid rgba(139, 92, 246, 0.3); border-radius: 16px; padding: 24px; max-width: 600px; width: 95%; max-height: 85vh; overflow-y: auto; z-index: 10000; box-shadow: 0 25px 80px rgba(139, 92, 246, 0.3);">

                <!-- Header -->
                <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 20px;">
                    <div>
                        <div style="display: flex; align-items: center; gap: 12px;">
                            <span style="font-size: 1.75rem; font-weight: 700;">${data.ticker}</span>
                            <span style="padding: 4px 10px; background: ${decisionColor}20; color: ${decisionColor}; border-radius: 6px; font-weight: 600; text-transform: uppercase;">${(decision.action || 'hold').replace('_', ' ')}</span>
                        </div>
                        <div style="color: var(--text-muted); font-size: 0.85rem; margin-top: 4px;">${data.company || ''}</div>
                        <div style="color: var(--text-muted); font-size: 0.75rem;">${data.sector || ''} • ${data.industry || ''}</div>
                    </div>
                    <button onclick="closeAgenticModal()" style="background: none; border: none; color: var(--text-muted); cursor: pointer; font-size: 1.5rem; padding: 0;">&times;</button>
                </div>

                <!-- Decision Summary -->
                <div style="padding: 16px; background: linear-gradient(135deg, var(--bg-hover) 0%, ${decisionColor}10 100%); border-radius: 12px; margin-bottom: 20px; border-left: 4px solid ${decisionColor};">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                        <div>
                            <div style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">Confidence</div>
                            <div style="font-size: 1.5rem; font-weight: 700; color: ${decisionColor};">${decision.confidence?.toFixed(0) || 0}%</div>
                        </div>
                        <div style="text-align: right;">
                            <div style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">Position Size</div>
                            <div style="font-size: 1.1rem; font-weight: 600;">${decision.position_size || 'None'}</div>
                        </div>
                    </div>
                    <div style="font-size: 0.9rem; color: var(--text);">${decision.reasoning || 'No reasoning provided'}</div>
                </div>

                <!-- Director Scores -->
                <div style="margin-bottom: 20px;">
                    <div style="font-size: 0.8rem; color: var(--primary); font-weight: 600; margin-bottom: 10px;">🧠 DIRECTOR ASSESSMENTS</div>
                    <div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 8px;">
                        <div style="text-align: center; padding: 10px; background: var(--bg-hover); border-radius: 8px;">
                            <div style="font-size: 1.25rem; font-weight: 700; color: #8b5cf6;">${scores.theme || 0}</div>
                            <div style="font-size: 0.65rem; color: var(--text-muted);">Theme</div>
                        </div>
                        <div style="text-align: center; padding: 10px; background: var(--bg-hover); border-radius: 8px;">
                            <div style="font-size: 1.25rem; font-weight: 700; color: #3b82f6;">${scores.trading || 0}</div>
                            <div style="font-size: 0.65rem; color: var(--text-muted);">Trading</div>
                        </div>
                        <div style="text-align: center; padding: 10px; background: var(--bg-hover); border-radius: 8px;">
                            <div style="font-size: 1.25rem; font-weight: 700; color: #10b981;">${scores.learning || 0}</div>
                            <div style="font-size: 0.65rem; color: var(--text-muted);">Learning</div>
                        </div>
                        <div style="text-align: center; padding: 10px; background: var(--bg-hover); border-radius: 8px;">
                            <div style="font-size: 1.25rem; font-weight: 700; color: #f59e0b;">${scores.realtime || 0}</div>
                            <div style="font-size: 0.65rem; color: var(--text-muted);">Realtime</div>
                        </div>
                        <div style="text-align: center; padding: 10px; background: var(--bg-hover); border-radius: 8px;">
                            <div style="font-size: 1.25rem; font-weight: 700; color: #22c55e;">${scores.validation || 0}</div>
                            <div style="font-size: 0.65rem; color: var(--text-muted);">Validation</div>
                        </div>
                    </div>
                </div>

                <!-- Trade Plan -->
                <div style="margin-bottom: 20px;">
                    <div style="font-size: 0.8rem; color: var(--primary); font-weight: 600; margin-bottom: 10px;">📊 TRADE PLAN</div>
                    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px;">
                        <div style="padding: 12px; background: var(--bg-hover); border-radius: 8px; text-align: center;">
                            <div style="font-size: 0.65rem; color: var(--text-muted); text-transform: uppercase;">Entry</div>
                            <div style="font-size: 1rem; font-weight: 600;">$${trade.entry_price?.toFixed(2) || 'N/A'}</div>
                        </div>
                        <div style="padding: 12px; background: rgba(239, 68, 68, 0.1); border-radius: 8px; text-align: center;">
                            <div style="font-size: 0.65rem; color: var(--red); text-transform: uppercase;">Stop Loss</div>
                            <div style="font-size: 1rem; font-weight: 600; color: var(--red);">$${trade.stop_loss?.toFixed(2) || 'N/A'}</div>
                        </div>
                        <div style="padding: 12px; background: rgba(34, 197, 94, 0.1); border-radius: 8px; text-align: center;">
                            <div style="font-size: 0.65rem; color: var(--green); text-transform: uppercase;">Target 1</div>
                            <div style="font-size: 1rem; font-weight: 600; color: var(--green);">$${trade.targets && trade.targets[0] ? trade.targets[0].toFixed(2) : 'N/A'}</div>
                        </div>
                        <div style="padding: 12px; background: rgba(34, 197, 94, 0.1); border-radius: 8px; text-align: center;">
                            <div style="font-size: 0.65rem; color: var(--green); text-transform: uppercase;">R:R</div>
                            <div style="font-size: 1rem; font-weight: 600; color: var(--green);">${trade.risk_reward?.toFixed(1) || 'N/A'}</div>
                        </div>
                    </div>
                </div>

                <!-- Strengths & Risks -->
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 20px;">
                    <div>
                        <div style="font-size: 0.8rem; color: var(--green); font-weight: 600; margin-bottom: 8px;">💪 KEY STRENGTHS</div>
                        <ul style="margin: 0; padding-left: 16px; font-size: 0.8rem; color: var(--text);">
                            ${(analysis.key_strengths || ['None identified']).map(s => `<li style="margin-bottom: 4px;">${s}</li>`).join('')}
                        </ul>
                    </div>
                    <div>
                        <div style="font-size: 0.8rem; color: var(--red); font-weight: 600; margin-bottom: 8px;">⚠️ RISKS</div>
                        <ul style="margin: 0; padding-left: 16px; font-size: 0.8rem; color: var(--text);">
                            ${(analysis.risks || ['None identified']).map(r => `<li style="margin-bottom: 4px;">${r}</li>`).join('')}
                        </ul>
                    </div>
                </div>

                <!-- Context -->
                <div style="padding: 12px; background: var(--bg-hover); border-radius: 8px; font-size: 0.8rem;">
                    <div style="color: var(--text-muted); margin-bottom: 4px;"><strong>Market Context:</strong> ${analysis.market_context || 'N/A'}</div>
                    <div style="color: var(--text-muted);"><strong>Sector Context:</strong> ${analysis.sector_context || 'N/A'}</div>
                </div>

            </div>
        </div>
    `;

    closeAgenticModal();
    document.body.insertAdjacentHTML('beforeend', html);
}

// Intelligence data is now loaded as part of Dashboard tab

// Economic Dashboard (FRED)
async function fetchEconomicDashboard() {
    try {
        const res = await fetch(`${API_BASE}/economic/dashboard`);
        const data = await res.json();

        if (!data.ok) {
            document.getElementById('econ-score').textContent = '--';
            document.getElementById('econ-label').textContent = data.error || 'Not configured';
            return;
        }

        // Overall score
        const score = data.overall_score || 50;
        const label = data.overall_label || 'Neutral';
        const color = data.overall_color || '#eab308';

        document.getElementById('econ-score').textContent = score;
        document.getElementById('econ-score').style.color = color;
        document.getElementById('econ-label').textContent = label;
        document.getElementById('econ-label').style.color = color;

        // Alerts
        const alertsContainer = document.getElementById('econ-alerts');
        if (data.alerts && data.alerts.length > 0) {
            alertsContainer.innerHTML = data.alerts.map(a => `
                <div style="padding: 8px 12px; background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 6px; margin-bottom: 8px; font-size: 0.8rem;">
                    <span style="color: #ef4444;">⚠️ ${a.message}</span>
                </div>
            `).join('');
        } else {
            alertsContainer.innerHTML = '';
        }

        // Yield curve
        const yc = data.yield_curve || {};
        document.getElementById('econ-yield-curve').textContent = yc.display || '--';
        document.getElementById('econ-yield-curve').style.color = yc.inverted ? '#ef4444' : (yc.spread > 0.5 ? '#22c55e' : '#eab308');
        document.getElementById('econ-yield-status').textContent = yc.emoji || '🟡';

        // Individual indicators
        const indicators = data.indicators || {};

        // Fed Rate
        if (indicators.fed_funds_rate) {
            document.getElementById('econ-fed-rate').textContent = indicators.fed_funds_rate.display;
        }

        // 10Y Treasury
        if (indicators.treasury_10y) {
            document.getElementById('econ-10y').textContent = indicators.treasury_10y.display;
        }

        // 2Y Treasury
        if (indicators.treasury_2y) {
            document.getElementById('econ-2y').textContent = indicators.treasury_2y.display;
        }

        // Unemployment
        if (indicators.unemployment) {
            document.getElementById('econ-unemployment').textContent = indicators.unemployment.display;
            document.getElementById('econ-unemployment-status').textContent = indicators.unemployment.emoji;
        }

        // Initial Claims
        if (indicators.initial_claims) {
            document.getElementById('econ-claims').textContent = indicators.initial_claims.display;
            document.getElementById('econ-claims-status').textContent = indicators.initial_claims.emoji;
        }

        // CPI
        if (indicators.cpi_yoy) {
            document.getElementById('econ-cpi').textContent = indicators.cpi_yoy.display;
            document.getElementById('econ-cpi-status').textContent = indicators.cpi_yoy.emoji;
        }

        // High Yield Spread
        if (indicators.high_yield_spread) {
            document.getElementById('econ-hy-spread').textContent = indicators.high_yield_spread.display;
            document.getElementById('econ-hy-status').textContent = indicators.high_yield_spread.emoji;
        }

        // Consumer Sentiment
        if (indicators.consumer_sentiment) {
            document.getElementById('econ-sentiment').textContent = indicators.consumer_sentiment.display;
            document.getElementById('econ-sentiment-status').textContent = indicators.consumer_sentiment.emoji;
        }

        // M2 Money Supply
        if (indicators.m2_money) {
            document.getElementById('econ-m2').textContent = indicators.m2_money.display;
        }

        // Timestamp
        if (data.timestamp) {
            const ts = new Date(data.timestamp);
            document.getElementById('econ-timestamp').textContent = ts.toLocaleString();
        }

    } catch (e) {
        console.warn('Economic dashboard fetch failed:', e);
        document.getElementById('econ-label').textContent = 'Failed to load';
    }
}

// SEC EDGAR Functions
async function fetchMARadar() {
    try {
        const res = await fetch(`${API_BASE}/sec/ma-radar`);
        const data = await res.json();

        if (data.ok && data.radar) {
            // Update SEC stats bar
            const secMaCount = document.getElementById('sec-ma-count');
            if (secMaCount) secMaCount.textContent = data.radar.length;

            let html = '';
            if (data.radar.length === 0) {
                html = '<div style="color: var(--text-muted);">No M&A activity detected</div>';
            } else {
                data.radar.slice(0, 8).forEach(item => {
                    // Extract ticker from company name or use provided ticker
                    let ticker = item.ticker;
                    if (!ticker || ticker === '?') {
                        // Try to extract from company name: "COMPANY NAME (TICK) (CIK...)"
                        const match = item.company?.match(/\(([A-Z]{1,5})\)/);
                        ticker = match ? match[1] : 'N/A';
                    }
                    // Use score if available, otherwise mark all as HIGH (DEFM14A = definitive merger proxy)
                    const score = item.score || (item.form === 'DEFM14A' ? 75 : 50);
                    const color = score >= 50 ? 'var(--yellow)' : 'var(--green)';
                    const formBadge = item.form || 'SEC';
                    html += `<div class="sidebar-item" style="cursor: pointer;" onclick="lookupMACheckFor('${ticker}')">
                        <span class="sidebar-label">${ticker}</span>
                        <span class="sidebar-value" style="color: ${color};">${formBadge}</span>
                    </div>`;
                });
            }
            document.getElementById('ma-radar-container').innerHTML = html;
        }
    } catch (e) { console.warn('M&A radar fetch failed:', e); }
}

async function fetchDeals() {
    try {
        const res = await fetch(`${API_BASE}/sec/deals`);
        const data = await res.json();

        if (data.ok) {
            // Update SEC stats bar for 8-K count (estimate from deals data)
            const sec8kCount = document.getElementById('sec-8k-count');
            if (sec8kCount && data.deals) sec8kCount.textContent = data.deals.length;

            // Update deals container with SEC EDGAR merger filings
            let html = '';
            if (!data.deals || data.deals.length === 0) {
                html = '<div style="color: var(--text-muted);">No pending mergers found</div>';
                document.getElementById('deals-container').innerHTML = html;
                document.getElementById('deals-table-body').innerHTML = '<tr><td colspan="4" style="text-align: center; color: var(--text-muted);">No pending merger filings found</td></tr>';
                if (sec8kCount) sec8kCount.textContent = '0';
                return;
            }

            // Summary in sidebar - extract ticker from company name
            data.deals.slice(0, 8).forEach(deal => {
                let ticker = deal.ticker;
                if (!ticker || ticker === '?') {
                    const match = deal.company?.match(/\(([A-Z]{1,5})\)/);
                    ticker = match ? match[1] : 'N/A';
                }
                const formColor = deal.form === 'DEFM14A' ? 'var(--yellow)' : 'var(--green)';
                html += `<div class="sidebar-item" style="cursor: pointer;" onclick="lookupMACheckFor('${ticker}')">
                    <span class="sidebar-label">${ticker}</span>
                    <span class="sidebar-value" style="color: ${formColor};">${deal.form || 'SEC'}</span>
                </div>`;
            });
            document.getElementById('deals-container').innerHTML = html;

            // Table with SEC filing details
            let tableHtml = '';
            data.deals.forEach(deal => {
                let ticker = deal.ticker;
                if (!ticker || ticker === '?') {
                    const match = deal.company?.match(/\(([A-Z]{1,5})\)/);
                    ticker = match ? match[1] : 'N/A';
                }
                // Extract just company name (before ticker)
                const companyName = deal.company?.split('(')[0]?.trim() || deal.company || 'Unknown';
                const filedDate = deal.filed_date || 'N/A';
                const formBadge = deal.form === 'DEFM14A' ? '🟡 DEFM14A' : '🔵 ' + (deal.form || 'Filing');
                tableHtml += `<tr style="cursor: pointer;" onclick="lookupMACheckFor('${ticker}')">
                    <td><strong>${ticker}</strong></td>
                    <td>${companyName.substring(0, 40)}${companyName.length > 40 ? '...' : ''}</td>
                    <td>${formBadge}</td>
                    <td>${filedDate}</td>
                </tr>`;
            });
            document.getElementById('deals-table-body').innerHTML = tableHtml;
        }
    } catch (e) { console.warn('Deals fetch failed:', e); }
}

async function lookupSECFilings() {
    const ticker = document.getElementById('sec-ticker-input').value.trim().toUpperCase();
    if (!ticker) { alert('Enter a ticker'); return; }

    document.getElementById('sec-lookup-result').innerHTML = '<div style="color: var(--text-muted);">Loading...</div>';

    try {
        const res = await fetch(`${API_BASE}/sec/filings/${ticker}`);
        const data = await res.json();

        if (data.ok && data.filings) {
            let html = `<div style="margin-bottom: 8px; font-weight: 600;">${ticker} - ${data.count} filings</div>`;
            data.filings.slice(0, 10).forEach(f => {
                const emoji = f.form_type.includes('8-K') ? '⚡' : f.form_type.includes('DEFM') ? '🔔' : f.form_type === '4' ? '👤' : '📄';
                html += `<div style="margin-bottom: 6px;">
                    ${emoji} <strong>${f.form_type}</strong> - ${f.filed_date}
                    <a href="${f.url}" target="_blank" style="color: var(--blue); margin-left: 8px;">View</a>
                </div>`;
            });
            document.getElementById('filings-feed').innerHTML = html;
            document.getElementById('sec-lookup-result').innerHTML = `<div style="color: var(--green);">Found ${data.count} filings</div>`;
        } else {
            document.getElementById('sec-lookup-result').innerHTML = '<div style="color: var(--red);">No filings found</div>';
        }
    } catch (e) {
        document.getElementById('sec-lookup-result').innerHTML = '<div style="color: var(--red);">Error fetching filings</div>';
    }
}

async function lookupMACheck() {
    const ticker = document.getElementById('sec-ticker-input').value.trim().toUpperCase();
    if (!ticker) { alert('Enter a ticker'); return; }
    lookupMACheckFor(ticker);
}

async function lookupMACheckFor(ticker) {
    document.getElementById('sec-lookup-result').innerHTML = '<div style="color: var(--text-muted);">Analyzing M&A activity...</div>';

    try {
        const res = await fetch(`${API_BASE}/sec/ma-check/${ticker}`);
        const data = await res.json();

        if (data.ok) {
            const color = data.ma_score >= 50 ? 'var(--red)' : data.ma_score >= 25 ? 'var(--yellow)' : 'var(--green)';
            const level = data.ma_score >= 50 ? 'HIGH' : data.ma_score >= 25 ? 'MEDIUM' : 'LOW';
            let html = `<div style="margin-bottom: 8px;">
                <strong>${ticker}</strong> M&A Probability: <span style="color: ${color}; font-weight: 600;">${level} (${data.ma_score}/100)</span>
            </div>`;
            if (data.signals && data.signals.length > 0) {
                html += '<div style="margin-top: 8px;">';
                data.signals.forEach(s => {
                    html += `<div style="margin-bottom: 4px;">• ${s}</div>`;
                });
                html += '</div>';
            } else {
                html += '<div style="color: var(--text-muted);">No M&A signals detected</div>';
            }
            document.getElementById('sec-lookup-result').innerHTML = html;
        }
    } catch (e) {
        document.getElementById('sec-lookup-result').innerHTML = '<div style="color: var(--red);">Error checking M&A</div>';
    }
}

async function lookupInsider() {
    const ticker = document.getElementById('sec-ticker-input').value.trim().toUpperCase();
    if (!ticker) { alert('Enter a ticker'); return; }

    document.getElementById('sec-lookup-result').innerHTML = '<div style="color: var(--text-muted);">Loading insider data...</div>';

    try {
        const res = await fetch(`${API_BASE}/sec/insider/${ticker}`);
        const data = await res.json();

        if (data.ok) {
            let html = `<div style="margin-bottom: 8px;"><strong>${ticker}</strong> - ${data.count} Form 4 filings (90 days)</div>`;
            if (data.transactions && data.transactions.length > 0) {
                data.transactions.slice(0, 5).forEach(t => {
                    html += `<div style="margin-bottom: 4px;">👤 ${t.date} - <a href="${t.url}" target="_blank" style="color: var(--blue);">View</a></div>`;
                });
            } else {
                html += '<div style="color: var(--text-muted);">No recent insider transactions</div>';
            }
            document.getElementById('sec-lookup-result').innerHTML = html;
        }
    } catch (e) {
        document.getElementById('sec-lookup-result').innerHTML = '<div style="color: var(--red);">Error fetching insider data</div>';
    }
}

function showAddDealModal() {
    const target = prompt('Target ticker (e.g., VMW):');
    if (!target) return;
    const acquirer = prompt('Acquirer ticker (e.g., AVGO):');
    if (!acquirer) return;
    const price = prompt('Deal price (e.g., 142.50):');
    if (!price) return;

    addDeal(target, acquirer, parseFloat(price));
}

async function addDeal(target, acquirer, dealPrice) {
    try {
        const res = await fetch(`${API_BASE}/sec/deals/add`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ target, acquirer, deal_price: dealPrice })
        });
        const data = await res.json();

        if (data.ok) {
            alert(data.message);
            fetchDeals();
        } else {
            alert('Error: ' + data.error);
        }
    } catch (e) {
        alert('Failed to add deal');
    }
}

// Government Contracts Functions
async function fetchContractThemes() {
    try {
        document.getElementById('contract-themes-container').innerHTML = '<div style="color: var(--text-muted);">Loading...</div>';
        const res = await fetch(`${API_BASE}/contracts/themes`);
        const data = await res.json();

        if (data.ok && data.themes) {
            let html = '';
            const sortedThemes = Object.entries(data.themes)
                .filter(([_, info]) => info.total_value > 0)
                .sort((a, b) => b[1].total_value - a[1].total_value)
                .slice(0, 8);

            sortedThemes.forEach(([theme, info]) => {
                const trendEmoji = info.trend === 'increasing' ? '📈' : info.trend === 'decreasing' ? '📉' : '➡️';
                const trendColor = info.trend === 'increasing' ? 'var(--green)' : info.trend === 'decreasing' ? 'var(--red)' : 'var(--text-muted)';
                const valueB = (info.total_value / 1e9).toFixed(1);

                html += `<div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid var(--border);">
                    <div>
                        <div style="font-weight: 500;">${theme.replace(/_/g, ' ').toUpperCase()}</div>
                        <div style="font-size: 0.75rem; color: var(--text-muted);">${info.contract_count || 0} contracts</div>
                    </div>
                    <div style="text-align: right;">
                        <div style="font-weight: 600;">$${valueB}B</div>
                        <div style="font-size: 0.75rem; color: ${trendColor};">${trendEmoji} ${info.mom_change > 0 ? '+' : ''}${(info.mom_change || 0).toFixed(0)}% MoM</div>
                    </div>
                </div>`;
            });

            document.getElementById('contract-themes-container').innerHTML = html || '<div style="color: var(--text-muted);">No contract data</div>';
        } else {
            document.getElementById('contract-themes-container').innerHTML = '<div style="color: var(--text-muted);">Contracts API not configured</div>';
        }
    } catch (e) {
        console.warn('Contract themes fetch failed:', e);
        document.getElementById('contract-themes-container').innerHTML = '<div style="color: var(--text-muted);">Could not load contract data</div>';
    }
}

async function fetchRecentContracts() {
    try {
        document.getElementById('recent-contracts-container').innerHTML = '<div style="color: var(--text-muted);">Loading...</div>';
        const res = await fetch(`${API_BASE}/contracts/recent`);
        const data = await res.json();

        if (data.ok && data.contracts) {
            let html = '';
            data.contracts.slice(0, 6).forEach(c => {
                const valueM = (c.amount / 1e6).toFixed(1);
                html += `<div style="padding: 8px 0; border-bottom: 1px solid var(--border);">
                    <div style="font-weight: 500; font-size: 0.8125rem;">${c.recipient || 'Unknown'}</div>
                    <div style="display: flex; justify-content: space-between; margin-top: 4px;">
                        <span style="font-size: 0.75rem; color: var(--text-muted);">${c.agency || 'Federal'}</span>
                        <span style="font-weight: 600; color: var(--green);">$${valueM}M</span>
                    </div>
                </div>`;
            });
            document.getElementById('recent-contracts-container').innerHTML = html || '<div style="color: var(--text-muted);">No recent contracts</div>';
        } else {
            document.getElementById('recent-contracts-container').innerHTML = '<div style="color: var(--text-muted);">No data</div>';
        }
    } catch (e) {
        console.warn('Recent contracts fetch failed:', e);
        document.getElementById('recent-contracts-container').innerHTML = '<div style="color: var(--text-muted);">Could not load contracts</div>';
    }
}

async function lookupCompanyContracts() {
    const ticker = document.getElementById('contract-ticker-input').value.trim().toUpperCase();
    if (!ticker) { alert('Enter a ticker'); return; }

    document.getElementById('contract-lookup-result').innerHTML = '<div style="color: var(--text-muted);">Searching contracts...</div>';

    try {
        const res = await fetch(`${API_BASE}/contracts/company/${ticker}`);
        const data = await res.json();

        if (data.ok && data.activity) {
            const a = data.activity;
            const valueB = (a.total_value / 1e9).toFixed(2);
            const signalPct = Math.round((a.signal_strength || 0) * 100);

            let html = `
                <div style="background: var(--bg-hover); border-radius: 8px; padding: 12px; margin-bottom: 12px;">
                    <div style="font-size: 1.25rem; font-weight: 700; color: var(--green);">$${valueB}B</div>
                    <div style="font-size: 0.75rem; color: var(--text-muted);">Total Contract Value</div>
                    <div style="margin-top: 8px; font-size: 0.875rem;">${a.contract_count || 0} contracts • Signal: ${signalPct}%</div>
                </div>`;

            if (a.top_agencies && a.top_agencies.length > 0) {
                html += '<div style="margin-bottom: 8px;"><strong>Top Agencies:</strong></div>';
                a.top_agencies.slice(0, 3).forEach(agency => {
                    html += `<div style="font-size: 0.75rem; color: var(--text-muted); margin-bottom: 4px;">• ${agency}</div>`;
                });
            }

            document.getElementById('contract-lookup-result').innerHTML = html;
        } else {
            document.getElementById('contract-lookup-result').innerHTML = `<div style="color: var(--text-muted);">No contract data for ${ticker}</div>`;
        }
    } catch (e) {
        document.getElementById('contract-lookup-result').innerHTML = '<div style="color: var(--red);">Error fetching contracts</div>';
    }
}

// Patent Intelligence Functions
async function fetchPatentThemes() {
    try {
        document.getElementById('patent-themes-container').innerHTML = '<div style="color: var(--text-muted);">Loading...</div>';
        const res = await fetch(`${API_BASE}/patents/themes`);
        const data = await res.json();

        if (data.ok && data.themes) {
            let html = '';
            const sortedThemes = Object.entries(data.themes)
                .sort((a, b) => b[1].patent_count - a[1].patent_count)
                .slice(0, 8);

            sortedThemes.forEach(([theme, info]) => {
                const trendEmoji = info.trend === 'increasing' ? '📈' : info.trend === 'decreasing' ? '📉' : '➡️';
                const trendColor = info.trend === 'increasing' ? 'var(--green)' : info.trend === 'decreasing' ? 'var(--red)' : 'var(--text-muted)';
                const signalPct = Math.round((info.signal_strength || 0) * 100);

                html += `<div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid var(--border);">
                    <div>
                        <div style="font-weight: 500;">${theme.replace(/_/g, ' ').toUpperCase()}</div>
                        <div style="font-size: 0.75rem; color: var(--text-muted);">${info.patent_count} patents</div>
                    </div>
                    <div style="text-align: right;">
                        <div style="color: ${trendColor};">${trendEmoji} ${info.yoy_change > 0 ? '+' : ''}${(info.yoy_change || 0).toFixed(0)}% YoY</div>
                        <div style="font-size: 0.75rem; color: var(--text-muted);">Signal: ${signalPct}%</div>
                    </div>
                </div>`;
            });

            document.getElementById('patent-themes-container').innerHTML = html || '<div style="color: var(--text-muted);">No patent data</div>';
        } else {
            document.getElementById('patent-themes-container').innerHTML = '<div style="color: var(--text-muted);">Patent API not configured</div>';
        }
    } catch (e) {
        console.warn('Patent themes fetch failed:', e);
        document.getElementById('patent-themes-container').innerHTML = '<div style="color: var(--text-muted);">Could not load patent data</div>';
    }
}

async function lookupCompanyPatents() {
    const ticker = document.getElementById('patent-ticker-input').value.trim().toUpperCase();
    if (!ticker) { alert('Enter a ticker'); return; }

    document.getElementById('patent-lookup-result').innerHTML = '<div style="color: var(--text-muted);">Searching patents...</div>';

    try {
        const res = await fetch(`${API_BASE}/patents/company/${ticker}`);
        const data = await res.json();

        if (data.ok && data.activity) {
            const a = data.activity;
            const trendEmoji = a.trend === 'increasing' ? '📈' : a.trend === 'decreasing' ? '📉' : '➡️';
            const trendColor = a.trend === 'increasing' ? 'var(--green)' : a.trend === 'decreasing' ? 'var(--red)' : 'var(--text-muted)';

            let html = `
                <div style="background: var(--bg-hover); border-radius: 8px; padding: 12px; margin-bottom: 12px;">
                    <div style="font-size: 1.5rem; font-weight: 700; color: var(--text);">${a.patent_count}</div>
                    <div style="font-size: 0.75rem; color: var(--text-muted);">Patents (3 years)</div>
                    <div style="margin-top: 8px; color: ${trendColor};">${trendEmoji} ${a.yoy_change > 0 ? '+' : ''}${(a.yoy_change || 0).toFixed(0)}% YoY</div>
                </div>`;

            if (a.top_keywords && a.top_keywords.length > 0) {
                html += '<div style="margin-bottom: 8px;"><strong>Top Keywords:</strong></div>';
                html += '<div style="display: flex; flex-wrap: wrap; gap: 4px;">';
                a.top_keywords.slice(0, 6).forEach(kw => {
                    html += `<span style="background: var(--bg); padding: 2px 8px; border-radius: 4px; font-size: 0.7rem;">${kw}</span>`;
                });
                html += '</div>';
            }

            if (a.recent_patents && a.recent_patents.length > 0) {
                html += '<div style="margin-top: 12px;"><strong>Recent Patents:</strong></div>';
                a.recent_patents.slice(0, 3).forEach(p => {
                    html += `<div style="margin-top: 6px; font-size: 0.75rem; color: var(--text-muted);">• ${p.title || p.patent_id}</div>`;
                });
            }

            document.getElementById('patent-lookup-result').innerHTML = html;
        } else {
            document.getElementById('patent-lookup-result').innerHTML = `<div style="color: var(--text-muted);">No patent data for ${ticker}</div>`;
        }
    } catch (e) {
        document.getElementById('patent-lookup-result').innerHTML = '<div style="color: var(--red);">Error fetching patents</div>';
    }
}

// Theme Intelligence Hub Functions
async function fetchThemeRadar() {
    try {
        const res = await fetch(`${API_BASE}/theme-intel/radar`);
        const data = await res.json();

        if (data.ok && data.radar) {
            const lifecycleEmoji = {
                'emerging': '🌱',
                'accelerating': '🚀',
                'peak': '🔥',
                'declining': '📉',
                'dead': '💀'
            };
            const lifecycleColor = {
                'emerging': 'var(--blue)',
                'accelerating': 'var(--green)',
                'peak': 'var(--yellow)',
                'declining': 'var(--red)',
                'dead': 'var(--text-muted)'
            };

            let html = '';
            data.radar.forEach(theme => {
                const emoji = lifecycleEmoji[theme.lifecycle] || '⚪';
                const color = lifecycleColor[theme.lifecycle] || 'var(--text-muted)';
                const trendArrow = theme.trend > 0 ? '↑' : theme.trend < 0 ? '↓' : '→';
                const trendColor = theme.trend > 0 ? 'var(--green)' : theme.trend < 0 ? 'var(--red)' : 'var(--text-muted)';

                html += `<div style="background: var(--bg-hover); border-radius: 8px; padding: 12px; border-left: 3px solid ${color};">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                        <span style="font-weight: 600;">${emoji} ${theme.theme_name}</span>
                        <span style="color: ${trendColor};">${trendArrow}</span>
                    </div>
                    <div style="font-size: 1.25rem; font-weight: 700; color: ${color};">${theme.score.toFixed(0)}</div>
                    <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 4px;">${theme.lifecycle.toUpperCase()}</div>
                    <div style="font-size: 0.7rem; color: var(--text-muted); margin-top: 4px;">${theme.tickers.slice(0, 4).join(', ')}</div>
                </div>`;
            });

            document.getElementById('theme-radar-grid').innerHTML = html || '<div style="color: var(--text-muted);">No theme data available</div>';

            // Update lifecycle counts if summary available
            const lifecycleCounts = { emerging: 0, accelerating: 0, peak: 0, declining: 0, dead: 0 };
            data.radar.forEach(t => {
                if (lifecycleCounts[t.lifecycle] !== undefined) {
                    lifecycleCounts[t.lifecycle]++;
                }
            });
            document.getElementById('emerging-count').textContent = lifecycleCounts.emerging;
            document.getElementById('accelerating-count').textContent = lifecycleCounts.accelerating;
            document.getElementById('peak-count').textContent = lifecycleCounts.peak;
            document.getElementById('declining-count').textContent = lifecycleCounts.declining;
            document.getElementById('dead-count').textContent = lifecycleCounts.dead;

            // Update table
            let tableHtml = '';
            data.radar.forEach(theme => {
                const emoji = lifecycleEmoji[theme.lifecycle] || '⚪';
                const color = lifecycleColor[theme.lifecycle] || 'var(--text-muted)';
                const trendStr = theme.trend > 0 ? `+${theme.trend.toFixed(1)}` : theme.trend.toFixed(1);
                const trendColor = theme.trend > 0 ? 'var(--green)' : theme.trend < 0 ? 'var(--red)' : 'var(--text-muted)';

                tableHtml += `<tr>
                    <td><strong>${theme.theme_name}</strong></td>
                    <td>${emoji} <span style="color: ${color};">${theme.lifecycle}</span></td>
                    <td>${theme.score.toFixed(0)}</td>
                    <td style="color: ${trendColor};">${trendStr}</td>
                    <td style="font-size: 0.75rem;">${theme.tickers.slice(0, 5).join(', ')}</td>
                </tr>`;
            });
            document.getElementById('themes-detail-body').innerHTML = tableHtml || '<tr><td colspan="5" style="text-align: center; color: var(--text-muted);">No data</td></tr>';
        }
    } catch (e) {
        console.warn('Theme radar fetch failed:', e);
        document.getElementById('theme-radar-grid').innerHTML = '<div style="color: var(--red);">Failed to load theme radar</div>';
    }
}

async function fetchThemeAlerts() {
    try {
        const res = await fetch(`${API_BASE}/theme-intel/alerts`);
        const data = await res.json();

        if (data.ok) {
            let html = '';
            if (!data.alerts || data.alerts.length === 0) {
                html = '<div style="color: var(--text-muted);">No alerts in last 24h</div>';
            } else {
                data.alerts.slice(0, 10).forEach(alert => {
                    const typeEmoji = {
                        'breakout': '💥',
                        'acceleration': '🚀',
                        'rotation_in': '📈',
                        'rotation_out': '📉'
                    }[alert.alert_type] || '⚪';
                    const severityColor = {
                        'high': 'var(--red)',
                        'medium': 'var(--yellow)',
                        'low': 'var(--green)'
                    }[alert.severity] || 'var(--text-muted)';

                    html += `<div style="padding: 8px 0; border-bottom: 1px solid var(--border);">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span>${typeEmoji} <strong>${alert.theme_name}</strong></span>
                            <span style="font-size: 0.75rem; padding: 2px 6px; background: ${severityColor}20; color: ${severityColor}; border-radius: 4px;">${alert.severity.toUpperCase()}</span>
                        </div>
                        <div style="font-size: 0.8125rem; color: var(--text-muted); margin-top: 4px;">${alert.message}</div>
                    </div>`;
                });
            }
            document.getElementById('theme-alerts-container').innerHTML = html;
        }
    } catch (e) {
        console.warn('Theme alerts fetch failed:', e);
    }
}

async function runThemeAnalysis() {
    document.getElementById('theme-radar-grid').innerHTML = '<div style="color: var(--text-muted);">Running full analysis... This may take 1-2 minutes.</div>';

    try {
        const res = await fetch(`${API_BASE}/theme-intel/run-analysis`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ quick: true })
        });
        const data = await res.json();

        if (data.ok) {
            alert(`Analysis complete! Found ${data.alerts_count} alerts.`);
            fetchThemeRadar();
            fetchThemeAlerts();
        } else {
            alert('Analysis failed: ' + data.error);
        }
    } catch (e) {
        alert('Failed to run analysis');
    }
}

async function lookupTickerTheme() {
    const ticker = document.getElementById('ticker-theme-input').value.trim().toUpperCase();
    if (!ticker) { alert('Enter a ticker'); return; }

    document.getElementById('ticker-theme-result').innerHTML = '<div style="color: var(--text-muted);">Loading...</div>';

    try {
        const res = await fetch(`${API_BASE}/theme-intel/ticker/${ticker}`);
        const data = await res.json();

        if (data.ok) {
            const boostColor = data.boost > 0 ? 'var(--green)' : data.boost < 0 ? 'var(--red)' : 'var(--text-muted)';
            const boostSign = data.boost > 0 ? '+' : '';

            let html = `<div style="margin-bottom: 12px;">
                <strong>${ticker}</strong> Theme Boost: <span style="color: ${boostColor}; font-weight: 700; font-size: 1.25rem;">${boostSign}${data.boost} pts</span>
            </div>`;

            if (data.themes && data.themes.length > 0) {
                html += '<div style="margin-top: 12px;">';
                data.themes.forEach(theme => {
                    const lifecycleEmoji = {
                        'emerging': '🌱',
                        'accelerating': '🚀',
                        'peak': '🔥',
                        'declining': '📉',
                        'dead': '💀'
                    }[theme.lifecycle] || '⚪';
                    const themeBoostColor = theme.boost > 0 ? 'var(--green)' : theme.boost < 0 ? 'var(--red)' : 'var(--text-muted)';

                    html += `<div style="padding: 8px; background: var(--bg-hover); border-radius: 6px; margin-bottom: 8px;">
                        <div style="display: flex; justify-content: space-between;">
                            <span>${lifecycleEmoji} ${theme.theme_name}</span>
                            <span style="color: ${themeBoostColor};">${theme.boost > 0 ? '+' : ''}${theme.boost}</span>
                        </div>
                        <div style="font-size: 0.75rem; color: var(--text-muted);">Score: ${theme.score.toFixed(0)} | ${theme.lifecycle}</div>
                    </div>`;
                });
                html += '</div>';
            } else {
                html += `<div style="color: var(--text-muted);">${data.reason}</div>`;
            }

            document.getElementById('ticker-theme-result').innerHTML = html;
        } else {
            document.getElementById('ticker-theme-result').innerHTML = `<div style="color: var(--red);">Error: ${data.error}</div>`;
        }
    } catch (e) {
        document.getElementById('ticker-theme-result').innerHTML = '<div style="color: var(--red);">Failed to lookup ticker</div>';
    }
}

// =============================================================================
// THEME CONFIG MANAGEMENT FUNCTIONS
// =============================================================================

async function loadThemeConfig() {
    try {
        const res = await fetch(`${API_BASE}/themes/config`);
        const data = await res.json();

        if (data.ok) {
            // Update stats
            const stats = data.stats || {};
            document.getElementById('stat-total').textContent = stats.total_themes || 0;
            document.getElementById('stat-known').textContent = stats.known || 0;
            document.getElementById('stat-emerging').textContent = stats.emerging || 0;
            document.getElementById('stat-archived').textContent = stats.archived || 0;

            // Render theme table
            const tbody = document.getElementById('theme-config-body');
            const themes = data.themes || {};

            if (Object.keys(themes).length === 0) {
                tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--text-muted);">No themes configured</td></tr>';
                return;
            }

            let html = '';
            Object.entries(themes).forEach(([id, theme]) => {
                const statusColor = theme.status === 'known' ? 'var(--green)' :
                                   theme.status === 'emerging' ? 'var(--yellow)' : 'var(--text-muted)';
                const statusBadge = `<span style="background: ${statusColor}20; color: ${statusColor}; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem;">${theme.status}</span>`;

                html += `<tr data-theme-id="${id}">
                    <td style="font-weight: 600;">${theme.name || id}</td>
                    <td>${statusBadge}</td>
                    <td style="font-size: 0.75rem; color: var(--text-muted);">${(theme.keywords || []).slice(0, 5).join(', ')}${theme.keywords?.length > 5 ? '...' : ''}</td>
                    <td style="font-size: 0.75rem;"><code>${(theme.tickers || []).join(', ')}</code></td>
                    <td>
                        <div style="display: flex; gap: 4px;">
                            ${theme.status === 'archived'
                                ? `<button class="btn btn-ghost" style="padding: 2px 8px; font-size: 0.7rem;" onclick="restoreTheme('${id}')">Restore</button>`
                                : `<button class="btn btn-ghost" style="padding: 2px 8px; font-size: 0.7rem; color: var(--red);" onclick="archiveTheme('${id}')">Archive</button>`
                            }
                        </div>
                    </td>
                </tr>`;
            });
            tbody.innerHTML = html;
        } else {
            document.getElementById('theme-config-body').innerHTML =
                `<tr><td colspan="5" style="text-align: center; color: var(--red);">Error: ${data.error}</td></tr>`;
        }
    } catch (e) {
        document.getElementById('theme-config-body').innerHTML =
            '<tr><td colspan="5" style="text-align: center; color: var(--red);">Failed to load theme config</td></tr>';
    }
}

async function addNewTheme() {
    const themeId = document.getElementById('new-theme-id').value.trim();
    const keywords = document.getElementById('new-theme-keywords').value.trim();
    const tickers = document.getElementById('new-theme-tickers').value.trim();

    if (!themeId) { alert('Theme ID is required'); return; }
    if (!keywords) { alert('Keywords are required'); return; }

    try {
        const res = await fetch(`${API_BASE}/themes/add`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                theme_id: themeId,
                keywords: keywords.split(',').map(k => k.trim().toLowerCase()),
                tickers: tickers ? tickers.split(',').map(t => t.trim().toUpperCase()) : []
            })
        });
        const data = await res.json();

        if (data.ok) {
            alert('Theme added successfully!');
            document.getElementById('new-theme-id').value = '';
            document.getElementById('new-theme-keywords').value = '';
            document.getElementById('new-theme-tickers').value = '';
            loadThemeConfig();
        } else {
            alert('Error: ' + data.error);
        }
    } catch (e) {
        alert('Failed to add theme');
    }
}

async function archiveTheme(themeId) {
    if (!confirm(`Archive theme "${themeId}"?`)) return;

    try {
        const res = await fetch(`${API_BASE}/themes/remove`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ theme_id: themeId })
        });
        const data = await res.json();

        if (data.ok) {
            loadThemeConfig();
        } else {
            alert('Error: ' + data.error);
        }
    } catch (e) {
        alert('Failed to archive theme');
    }
}

async function restoreTheme(themeId) {
    try {
        const res = await fetch(`${API_BASE}/themes/restore`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ theme_id: themeId })
        });
        const data = await res.json();

        if (data.ok) {
            loadThemeConfig();
        } else {
            alert('Error: ' + data.error);
        }
    } catch (e) {
        alert('Failed to restore theme');
    }
}

async function runAIDiscovery() {
    const card = document.getElementById('ai-discovery-card');
    const results = document.getElementById('ai-discovery-results');

    card.style.display = 'block';
    results.innerHTML = '<div style="color: var(--text-muted);">Running AI discovery... this may take 30 seconds...</div>';

    try {
        const res = await fetch(`${API_BASE}/themes/discover`, { method: 'POST' });
        const data = await res.json();

        if (data.ok && data.discovered && data.discovered.length > 0) {
            let html = '<div style="display: grid; gap: 12px;">';
            data.discovered.forEach(theme => {
                html += `<div style="background: var(--bg-hover); padding: 12px; border-radius: 8px; border-left: 3px solid var(--yellow);">
                    <div style="font-weight: 600; margin-bottom: 8px;">${theme.name || theme.id}</div>
                    <div style="font-size: 0.75rem; color: var(--text-muted); margin-bottom: 4px;">
                        <strong>Keywords:</strong> ${(theme.keywords || []).join(', ')}
                    </div>
                    <div style="font-size: 0.75rem; color: var(--text-muted); margin-bottom: 4px;">
                        <strong>Tickers:</strong> ${(theme.suggested_tickers || []).join(', ')}
                    </div>
                    <div style="font-size: 0.75rem; color: var(--text-muted); margin-bottom: 8px;">
                        <strong>Catalyst:</strong> ${theme.catalyst || 'N/A'}
                    </div>
                    <button class="btn btn-primary" style="padding: 4px 12px; font-size: 0.75rem;"
                        onclick="addDiscoveredTheme('${theme.id}', '${(theme.keywords || []).join(',')}', '${(theme.suggested_tickers || []).join(',')}')">
                        Add Theme
                    </button>
                </div>`;
            });
            html += '</div>';
            html += `<div style="margin-top: 12px; font-size: 0.75rem; color: var(--text-muted);">Analyzed ${data.headline_count} headlines</div>`;
            results.innerHTML = html;
        } else if (data.ok) {
            results.innerHTML = '<div style="color: var(--text-muted);">No new themes discovered. Current themes cover the news well!</div>';
        } else {
            results.innerHTML = `<div style="color: var(--red);">Error: ${data.error}</div>`;
        }
    } catch (e) {
        results.innerHTML = '<div style="color: var(--red);">Failed to run AI discovery</div>';
    }
}

async function addDiscoveredTheme(themeId, keywords, tickers) {
    try {
        const res = await fetch(`${API_BASE}/themes/add`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                theme_id: themeId,
                keywords: keywords.split(',').filter(k => k),
                tickers: tickers.split(',').filter(t => t)
            })
        });
        const data = await res.json();

        if (data.ok) {
            alert('Theme added!');
            loadThemeConfig();
        } else {
            alert('Error: ' + data.error);
        }
    } catch (e) {
        alert('Failed to add theme');
    }
}

// =============================================================================
// TRADE MANAGEMENT FUNCTIONS
// =============================================================================

// Store positions globally for filtering
let allPositions = [];
let allWatchlist = [];
let journalEntries = [];

async function fetchTrades() {
    try {
        // Fetch positions
        const posRes = await fetch(`${API_BASE}/trades/positions`);
        const posData = await posRes.json();

        if (posData.ok) {
            allPositions = posData.positions || [];
            document.getElementById('trade-positions-count').textContent = posData.count || 0;
            renderPositionCards(allPositions);
            updatePortfolioSummary(allPositions);
            renderThemeConcentration(allPositions);
            updatePerformanceMetrics(allPositions);
        }

        // Fetch watchlist from new endpoint
        const watchRes = await fetch(`${API_BASE}/watchlist`);
        const watchData = await watchRes.json();

        if (watchData.ok) {
            allWatchlist = watchData.watchlist || [];
            document.getElementById('trade-watchlist-count').textContent = watchData.count || 0;
            renderWatchlistCards(allWatchlist);
        }

        // Fetch starred scans
        const scansRes = await fetch(`${API_BASE}/scans?starred_only=true`);
        const scansData = await scansRes.json();
        if (scansData.ok) {
            renderStarredScans(scansData.scans || []);
        }

        // Fetch risk
        const riskRes = await fetch(`${API_BASE}/trades/risk`);
        const riskData = await riskRes.json();

        if (riskData.ok) {
            const riskColors = {
                'critical': 'var(--red)',
                'high': 'var(--red)',
                'elevated': 'var(--yellow)',
                'moderate': 'var(--green)',
                'low': 'var(--text-muted)',
                'none': 'var(--green)'
            };
            const riskLevel = riskData.overall_risk || 'none';
            document.getElementById('trade-risk-level').textContent = riskLevel.toUpperCase();
            document.getElementById('trade-risk-level').style.color = riskColors[riskLevel] || 'var(--text)';
            document.getElementById('trade-high-risk').textContent = riskData.high_risk_count || 0;

            // Show risk alerts
            renderTradeAlerts(riskData.high_risk_trades || []);
        }

        // Fetch journal
        fetchJournal();

        // Fetch activity
        fetchActivityFeed();

    } catch (e) {
        console.warn('Trades fetch failed:', e);
    }
}

function renderPositionCards(positions) {
    const container = document.getElementById('position-cards-container');
    if (!positions || positions.length === 0) {
        container.innerHTML = '<div style="text-align: center; color: var(--text-muted); padding: 40px;">No open positions. Click "+ Add Trade" to start tracking.</div>';
        return;
    }

    const riskColors = {
        'critical': '#ef4444',
        'high': '#f97316',
        'elevated': '#eab308',
        'moderate': '#22c55e',
        'low': '#6b7280',
        'none': '#10b981'
    };

    container.innerHTML = positions.map(pos => {
        const pnlPct = pos.pnl_pct || 0;
        const pnlValue = pos.pnl_value || 0;
        const pnlColor = pnlPct >= 0 ? 'var(--green)' : 'var(--red)';
        const riskLevel = pos.current_risk_level || 'none';
        const riskColor = riskColors[riskLevel] || riskColors.none;
        const storyScore = pos.story_score || 0;
        const exitConf = pos.composite_exit_confidence || 0;
        const daysHeld = pos.days_held || 0;
        const theme = pos.theme || 'No Theme';

        // Calculate profit target progress (assuming 20% target for visual)
        const profitTarget = 20;
        const progressPct = Math.min(100, Math.max(0, (pnlPct / profitTarget) * 100));
        const progressColor = pnlPct >= profitTarget ? 'var(--green)' : pnlPct >= 0 ? 'var(--blue)' : 'var(--red)';

        return `<div style="background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px; padding: 16px; margin-bottom: 12px; border-left: 4px solid ${riskColor};">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
                <div style="cursor: pointer;" onclick="showTradeDetail('${pos.id}')">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span style="font-size: 1.25rem; font-weight: 700;">${pos.ticker}</span>
                        <span style="font-size: 0.7rem; padding: 2px 6px; background: ${riskColor}20; color: ${riskColor}; border-radius: 4px;">${riskLevel.toUpperCase()}</span>
                    </div>
                    <div style="font-size: 0.75rem; color: var(--text-muted);">${theme} • ${daysHeld}d held</div>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 1.5rem; font-weight: 700; color: ${pnlColor};">${pnlPct >= 0 ? '+' : ''}${pnlPct.toFixed(1)}%</div>
                    <div style="font-size: 0.8rem; color: ${pnlColor};">$${pnlValue >= 0 ? '+' : ''}${pnlValue.toLocaleString(undefined, {maximumFractionDigits: 0})}</div>
                </div>
            </div>

            <!-- Story Score Bar -->
            <div style="margin-bottom: 8px;">
                <div style="display: flex; justify-content: space-between; font-size: 0.7rem; color: var(--text-muted); margin-bottom: 4px;">
                    <span>Story Score</span>
                    <span>${storyScore.toFixed(0)}/100</span>
                </div>
                <div style="height: 4px; background: var(--bg-hover); border-radius: 2px; overflow: hidden;">
                    <div style="height: 100%; width: ${storyScore}%; background: linear-gradient(90deg, var(--blue), var(--purple));"></div>
                </div>
            </div>

            <!-- Profit Target Progress -->
            <div style="margin-bottom: 12px;">
                <div style="display: flex; justify-content: space-between; font-size: 0.7rem; color: var(--text-muted); margin-bottom: 4px;">
                    <span>Profit Target</span>
                    <span>${pnlPct.toFixed(1)}% / ${profitTarget}%</span>
                </div>
                <div style="height: 4px; background: var(--bg-hover); border-radius: 2px; overflow: hidden;">
                    <div style="height: 100%; width: ${progressPct}%; background: ${progressColor}; transition: width 0.3s;"></div>
                </div>
            </div>

            <!-- Position Details -->
            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-bottom: 12px; font-size: 0.75rem;">
                <div style="background: var(--bg-hover); padding: 8px; border-radius: 6px; text-align: center;">
                    <div style="color: var(--text-muted);">Shares</div>
                    <div style="font-weight: 600;">${pos.total_shares}</div>
                </div>
                <div style="background: var(--bg-hover); padding: 8px; border-radius: 6px; text-align: center;">
                    <div style="color: var(--text-muted);">Avg Cost</div>
                    <div style="font-weight: 600;">$${(pos.average_cost || 0).toFixed(2)}</div>
                </div>
                <div style="background: var(--bg-hover); padding: 8px; border-radius: 6px; text-align: center;">
                    <div style="color: var(--text-muted);">Current</div>
                    <div style="font-weight: 600;">$${(pos.current_price || 0).toFixed(2)}</div>
                </div>
                <div style="background: var(--bg-hover); padding: 8px; border-radius: 6px; text-align: center;">
                    <div style="color: var(--text-muted);">Exit Conf</div>
                    <div style="font-weight: 600; color: ${exitConf > 60 ? 'var(--yellow)' : 'var(--text)'};">${exitConf.toFixed(0)}%</div>
                </div>
            </div>

            <!-- Action Buttons -->
            <div style="display: flex; gap: 8px;">
                <button class="btn btn-primary" style="flex: 1; padding: 8px; font-size: 0.75rem;" onclick="showBuyModalFor('${pos.id}', '${pos.ticker}')">📈 Scale In</button>
                <button class="btn btn-ghost" style="flex: 1; padding: 8px; font-size: 0.75rem;" onclick="showSellModalFor('${pos.id}', '${pos.ticker}', ${pos.total_shares})">📉 Scale Out</button>
                <button class="btn btn-ghost" style="padding: 8px; font-size: 0.75rem;" onclick="scanSinglePosition('${pos.id}')">🔍</button>
            </div>
        </div>`;
    }).join('');
}

async function scanSinglePosition(tradeId) {
    try {
        const res = await fetch(`${API_BASE}/trades/scan`);
        const data = await res.json();
        if (data.ok) {
            const position = (data.positions || []).find(p => p.id === tradeId);
            if (position) {
                let msg = `Scan Results for ${position.ticker}:\n\n`;
                if (position.exit_signals && position.exit_signals.length > 0) {
                    msg += 'Exit Signals:\n';
                    position.exit_signals.forEach(s => {
                        msg += `- ${s.signal_type}: ${s.reason} (${s.confidence}%)\n`;
                    });
                } else {
                    msg += 'No exit signals detected.\n';
                }
                if (position.scale_in?.should_scale) {
                    msg += `\nScale In: +${position.scale_in.size_pct}%`;
                }
                if (position.scale_out?.should_scale) {
                    msg += `\nScale Out: -${position.scale_out.size_pct}%`;
                }
                alert(msg);
            }
        }
    } catch (e) {
        alert('Scan failed');
    }
}

function renderWatchlistCards(watchlist) {
    const container = document.getElementById('watchlist-cards-container');
    if (!watchlist || watchlist.length === 0) {
        container.innerHTML = '<div style="text-align: center; color: var(--text-muted); padding: 20px;">Watchlist empty. Use /watch TICKER in Telegram to add stocks.</div>';
        return;
    }

    container.innerHTML = `<div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 12px;">
        ${watchlist.map(item => {
            const changePct = item.change_pct;
            const hasChange = changePct !== null && changePct !== undefined;
            const pnlColor = hasChange ? (changePct >= 0 ? 'var(--green)' : 'var(--red)') : 'var(--text-muted)';
            const themes = item.themes || [];
            const theme = themes.length > 0 ? themes[0] : 'No Theme';
            const sourceScan = item.source_scan;
            const entryPrice = item.entry_price;
            const currentPrice = item.current_price;

            return `<div style="background: var(--bg-hover); border: 1px solid var(--border); border-radius: 10px; padding: 14px; border-left: 3px solid ${pnlColor};">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                    <div>
                        <div style="font-size: 1.1rem; font-weight: 700;">${item.ticker}</div>
                        <div style="font-size: 0.7rem; color: var(--text-muted);">${theme}</div>
                    </div>
                    ${hasChange ? `<span style="font-size: 0.9rem; font-weight: 600; color: ${pnlColor};">${changePct >= 0 ? '+' : ''}${changePct.toFixed(1)}%</span>` : ''}
                </div>
                <div style="font-size: 0.75rem; color: var(--text-muted); margin-bottom: 8px;">
                    ${entryPrice ? `Entry: $${entryPrice.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}` : ''}
                    ${currentPrice ? ` → $${currentPrice.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}` : ''}
                </div>
                ${sourceScan ? `<div style="font-size: 0.65rem; color: var(--text-muted);">From Scan #${sourceScan.id}</div>` : ''}
                ${item.notes ? `<div style="font-size: 0.7rem; color: var(--text-secondary); margin-top: 6px; font-style: italic;">${item.notes}</div>` : ''}
                <div style="display: flex; gap: 6px; margin-top: 10px;">
                    <button class="btn btn-ghost" style="flex: 1; padding: 6px; font-size: 0.7rem;" onclick="viewStockDetail('${item.ticker}')">View</button>
                    <button class="btn btn-ghost" style="padding: 6px; font-size: 0.7rem;" onclick="removeFromWatchlist('${item.ticker}')">✕</button>
                </div>
            </div>`;
        }).join('')}
    </div>`;
}

function renderStarredScans(scans) {
    // Find or create starred scans container
    let container = document.getElementById('starred-scans-container');
    if (!container) return;

    if (!scans || scans.length === 0) {
        container.innerHTML = '<div style="color: var(--text-muted); font-size: 0.8rem;">No starred scans. Use /star in Telegram to keep important scans.</div>';
        return;
    }

    container.innerHTML = scans.slice(0, 5).map(scan => {
        const date = scan.date ? new Date(scan.date).toLocaleDateString('en-US', {month: 'short', day: 'numeric'}) : 'Unknown';
        const topPicks = scan.top_picks ? scan.top_picks.slice(0, 3).join(', ') : '';
        return `<div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid var(--border-subtle);">
            <div>
                <span style="color: var(--yellow);">⭐</span>
                <span style="font-weight: 600; margin-left: 4px;">#${scan.scan_id}</span>
                <span style="color: var(--text-muted); font-size: 0.75rem; margin-left: 8px;">${date}</span>
            </div>
            <div style="font-size: 0.7rem; color: var(--text-muted);">${topPicks}</div>
        </div>`;
    }).join('');
}

async function removeFromWatchlist(ticker) {
    if (!confirm(`Remove ${ticker} from watchlist?`)) return;
    try {
        const res = await fetch(`${API_BASE}/watchlist/${ticker}`, { method: 'DELETE' });
        const data = await res.json();
        if (data.ok) {
            refreshWatchlistTable(); // Instant refresh
        }
    } catch (e) {
        console.error('Remove failed:', e);
    }
}

function viewStockDetail(ticker) {
    // Switch to scanner tab and show ticker detail
    document.querySelector('[data-tab="scanner"]')?.click();
    setTimeout(() => {
        const tickerInput = document.getElementById('ticker-detail-input');
        if (tickerInput) {
            tickerInput.value = ticker;
            tickerInput.dispatchEvent(new Event('change'));
        }
    }, 100);
}

// ============ WATCHLIST TAB FUNCTIONS ============
let wlCurrentFilter = 'recent';

async function refreshWatchlistTab() {
    try {
        // Fetch watchlist
        const wlRes = await fetch(`${API_BASE}/watchlist`);
        const wlData = await wlRes.json();

        if (wlData.ok) {
            const watchlist = wlData.watchlist || [];
            document.getElementById('wl-stat-count').textContent = watchlist.length;
            renderWatchlistTable(watchlist);

            // Calculate avg performance
            const withPerf = watchlist.filter(w => w.change_pct !== null && w.change_pct !== undefined);
            if (withPerf.length > 0) {
                const avgPerf = withPerf.reduce((sum, w) => sum + w.change_pct, 0) / withPerf.length;
                const avgEl = document.getElementById('wl-stat-avg-perf');
                avgEl.textContent = `${avgPerf >= 0 ? '+' : ''}${avgPerf.toFixed(1)}%`;
                avgEl.style.color = avgPerf >= 0 ? 'var(--green)' : 'var(--red)';
            }
        }

        // Fetch scans
        const scansRes = await fetch(`${API_BASE}/scans`);
        const scansData = await scansRes.json();
        if (scansData.ok) {
            document.getElementById('wl-stat-total-scans').textContent = scansData.count || 0;
        }

        // Fetch starred scans
        const starredRes = await fetch(`${API_BASE}/scans?starred_only=true`);
        const starredData = await starredRes.json();
        if (starredData.ok) {
            const starred = starredData.scans || [];
            document.getElementById('wl-stat-starred').textContent = starred.length;
            renderWlStarredQuick(starred);
        }

        // Load scans based on filter
        filterScans(wlCurrentFilter);

    } catch (e) {
        console.error('Watchlist tab refresh failed:', e);
    }
}

function renderWatchlistTable(watchlist) {
    const container = document.getElementById('wl-table-container');
    if (!watchlist || watchlist.length === 0) {
        container.innerHTML = '<div style="text-align: center; color: var(--text-muted); padding: 40px;">Watchlist empty. Add stocks using the form above or /watch in Telegram.</div>';
        return;
    }

    container.innerHTML = `
        <table style="width: 100%; border-collapse: collapse; font-size: 0.85rem;">
            <thead>
                <tr style="border-bottom: 1px solid var(--border); color: var(--text-muted); font-size: 0.75rem;">
                    <th style="text-align: left; padding: 10px 8px;">Ticker</th>
                    <th style="text-align: left; padding: 10px 8px;">Entry</th>
                    <th style="text-align: left; padding: 10px 8px;">Current</th>
                    <th style="text-align: right; padding: 10px 8px;">P&L</th>
                    <th style="text-align: left; padding: 10px 8px;">Source</th>
                    <th style="text-align: left; padding: 10px 8px;">Notes</th>
                    <th style="text-align: center; padding: 10px 8px;">Actions</th>
                </tr>
            </thead>
            <tbody>
                ${watchlist.map(item => {
                    const changePct = item.change_pct;
                    const hasChange = changePct !== null && changePct !== undefined;
                    const pnlColor = hasChange ? (changePct >= 0 ? 'var(--green)' : 'var(--red)') : 'var(--text-muted)';
                    const entryPrice = item.entry_price;
                    const currentPrice = item.current_price;
                    const sourceScan = item.source_scan;
                    const addedDate = item.added_date ? new Date(item.added_date).toLocaleDateString('en-US', {month: 'short', day: 'numeric'}) : '';

                    return `<tr style="border-bottom: 1px solid var(--border-subtle);">
                        <td style="padding: 12px 8px;">
                            <div style="font-weight: 600; font-size: 1rem;">${item.ticker}</div>
                            <div style="font-size: 0.7rem; color: var(--text-muted);">${addedDate}</div>
                        </td>
                        <td style="padding: 12px 8px; color: var(--text-secondary);">
                            ${entryPrice ? '$' + entryPrice.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2}) : '--'}
                        </td>
                        <td style="padding: 12px 8px; font-weight: 500;">
                            ${currentPrice ? '$' + currentPrice.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2}) : '--'}
                        </td>
                        <td style="padding: 12px 8px; text-align: right; font-weight: 600; color: ${pnlColor};">
                            ${hasChange ? (changePct >= 0 ? '+' : '') + changePct.toFixed(1) + '%' : '--'}
                        </td>
                        <td style="padding: 12px 8px; font-size: 0.75rem; color: var(--text-muted);">
                            ${sourceScan ? '#' + sourceScan.id : '--'}
                        </td>
                        <td style="padding: 12px 8px; font-size: 0.75rem; color: var(--text-muted); max-width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${item.notes || ''}">
                            ${item.notes || '--'}
                        </td>
                        <td style="padding: 12px 8px; text-align: center;">
                            <button class="btn btn-ghost" style="padding: 4px 8px; font-size: 0.7rem; margin-right: 4px;" onclick="loadStockHistoryFor('${item.ticker}')">📜</button>
                            <button class="btn btn-ghost" style="padding: 4px 8px; font-size: 0.7rem;" onclick="removeFromWatchlist('${item.ticker}')">✕</button>
                        </td>
                    </tr>`;
                }).join('')}
            </tbody>
        </table>
    `;
}

function renderWlStarredQuick(scans) {
    const container = document.getElementById('wl-starred-quick');
    if (!scans || scans.length === 0) {
        container.innerHTML = '<div style="color: var(--text-muted); font-size: 0.8rem;">No starred scans yet.</div>';
        return;
    }

    container.innerHTML = scans.slice(0, 5).map(scan => {
        const date = scan.date ? new Date(scan.date).toLocaleDateString('en-US', {month: 'short', day: 'numeric'}) : '';
        const topPicks = scan.top_picks ? scan.top_picks.slice(0, 3).join(', ') : '';
        return `<div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid var(--border-subtle); cursor: pointer;" onclick="viewScanDetail(${scan.scan_id})">
            <div>
                <span style="color: var(--yellow);">⭐</span>
                <span style="font-weight: 600; margin-left: 4px;">#${scan.scan_id}</span>
                <span style="color: var(--text-muted); font-size: 0.7rem; margin-left: 6px;">${date}</span>
            </div>
            <div style="font-size: 0.7rem; color: var(--text-muted);">${topPicks}</div>
        </div>`;
    }).join('');
}

async function filterScans(filter) {
    wlCurrentFilter = filter;
    // Update filter button styles
    document.querySelectorAll('.wl-scan-filter').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.filter === filter);
        btn.style.background = btn.dataset.filter === filter ? 'var(--blue)' : '';
        btn.style.color = btn.dataset.filter === filter ? 'white' : '';
    });

    const container = document.getElementById('wl-scans-container');
    container.innerHTML = '<div style="text-align: center; color: var(--text-muted); padding: 20px;">Loading...</div>';

    try {
        let url = `${API_BASE}/scans`;
        if (filter === 'starred') url += '?starred_only=true';
        else if (filter === 'archived') url += '?archived=true';

        const res = await fetch(url);
        const data = await res.json();

        if (data.ok) {
            renderScansTable(data.scans || []);
        }
    } catch (e) {
        container.innerHTML = '<div style="color: var(--red); padding: 20px;">Failed to load scans</div>';
    }
}

// Store expanded scan data
let expandedScanData = {};

function renderScansTable(scans) {
    const container = document.getElementById('wl-scans-container');
    if (!scans || scans.length === 0) {
        container.innerHTML = '<div style="text-align: center; color: var(--text-muted); padding: 40px;">No scans found.</div>';
        return;
    }

    container.innerHTML = `
        <div style="font-size: 0.75rem; color: var(--text-muted); margin-bottom: 12px;">Click on a scan to expand and add stocks to watchlist</div>
        <div id="scans-accordion">
            ${scans.map(scan => {
                const date = scan.date ? new Date(scan.date).toLocaleDateString('en-US', {month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'}) : '';
                const topPicks = scan.top_picks ? scan.top_picks.slice(0, 4).join(', ') : '';
                const themes = scan.themes ? scan.themes.slice(0, 2).join(', ') : '';
                const starred = scan.starred;
                const archived = scan.archived;

                return `
                    <div class="scan-accordion-item" style="border: 1px solid var(--border); border-radius: 8px; margin-bottom: 8px; overflow: hidden;">
                        <div class="scan-accordion-header" onclick="toggleScanExpand(${scan.scan_id})" style="display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; background: var(--bg-hover); cursor: pointer; transition: background 0.2s;">
                            <div style="display: flex; align-items: center; gap: 12px;">
                                <span id="scan-arrow-${scan.scan_id}" style="color: var(--text-muted); transition: transform 0.2s;">▶</span>
                                <div>
                                    <span style="font-weight: 600;">#${scan.scan_id}</span>
                                    ${starred ? '<span style="color: var(--yellow); margin-left: 4px;">⭐</span>' : ''}
                                    ${archived ? '<span style="color: var(--text-muted); margin-left: 4px;">📁</span>' : ''}
                                    <span style="color: var(--text-muted); font-size: 0.8rem; margin-left: 12px;">${date}</span>
                                </div>
                            </div>
                            <div style="display: flex; align-items: center; gap: 16px;">
                                <span style="font-size: 0.8rem; color: var(--text-muted);">${scan.total_stocks || 0} stocks</span>
                                <div onclick="event.stopPropagation();">
                                    ${!starred ? `<button class="btn btn-ghost" style="padding: 4px 8px; font-size: 0.7rem;" onclick="starScan(${scan.scan_id})">⭐ Star</button>` : `<button class="btn btn-ghost" style="padding: 4px 8px; font-size: 0.7rem;" onclick="unstarScan(${scan.scan_id})">★ Unstar</button>`}
                                </div>
                            </div>
                        </div>
                        <div id="scan-expand-${scan.scan_id}" style="display: none; padding: 16px; background: var(--bg-card); border-top: 1px solid var(--border-subtle);">
                            <div style="text-align: center; color: var(--text-muted); padding: 20px;">Loading stocks...</div>
                        </div>
                    </div>
                `;
            }).join('')}
        </div>
    `;
}

async function toggleScanExpand(scanId) {
    const expandDiv = document.getElementById(`scan-expand-${scanId}`);
    const arrow = document.getElementById(`scan-arrow-${scanId}`);

    if (expandDiv.style.display === 'none') {
        // Expand
        expandDiv.style.display = 'block';
        arrow.style.transform = 'rotate(90deg)';

        // Load scan data if not cached
        if (!expandedScanData[scanId]) {
            try {
                const res = await fetch(`${API_BASE}/scans/${scanId}`);
                const data = await res.json();
                if (data.ok) {
                    expandedScanData[scanId] = data;
                    renderExpandedScan(scanId, data);
                }
            } catch (e) {
                expandDiv.innerHTML = '<div style="color: var(--red); padding: 20px;">Failed to load scan</div>';
            }
        } else {
            renderExpandedScan(scanId, expandedScanData[scanId]);
        }
    } else {
        // Collapse
        expandDiv.style.display = 'none';
        arrow.style.transform = 'rotate(0deg)';
    }
}

async function renderExpandedScan(scanId, data) {
    const expandDiv = document.getElementById(`scan-expand-${scanId}`);
    const scan = data.scan;
    const results = data.data?.results || [];

    // Get current watchlist to check which stocks are already added
    let watchlistTickers = [];
    try {
        const wlRes = await fetch(`${API_BASE}/watchlist`);
        const wlData = await wlRes.json();
        if (wlData.ok) {
            watchlistTickers = (wlData.watchlist || []).map(w => w.ticker);
        }
    } catch (e) {}

    if (results.length === 0) {
        expandDiv.innerHTML = '<div style="color: var(--text-muted); padding: 20px; text-align: center;">No stocks in this scan</div>';
        return;
    }

    expandDiv.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
            <div>
                <span style="font-weight: 600;">${results.length} stocks</span>
                ${scan.themes && scan.themes.length > 0 ? `<span style="color: var(--text-muted); font-size: 0.8rem; margin-left: 12px;">Themes: ${scan.themes.join(', ')}</span>` : ''}
            </div>
            <button class="btn btn-primary" style="padding: 6px 12px; font-size: 0.75rem;" onclick="addAllToWatchlist(${scanId})">+ Add All Top 10</button>
        </div>
        <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 10px; max-height: 400px; overflow-y: auto;">
            ${results.slice(0, 50).map((stock, idx) => {
                const ticker = stock.ticker;
                const score = stock.story_score || stock.composite_score || 0;
                const price = stock.price;
                const theme = stock.hottest_theme || stock.theme || '';
                const inWatchlist = watchlistTickers.includes(ticker);

                return `
                    <div id="scan-stock-${scanId}-${ticker}" style="background: var(--bg-hover); border: 1px solid var(--border-subtle); border-radius: 8px; padding: 12px; display: flex; flex-direction: column; justify-content: space-between;">
                        <div>
                            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 6px;">
                                <div>
                                    <span style="font-weight: 700; font-size: 1rem;">${ticker}</span>
                                    <span style="color: var(--text-muted); font-size: 0.7rem; margin-left: 6px;">#${idx + 1}</span>
                                </div>
                                <span style="color: var(--blue); font-size: 0.8rem; font-weight: 500;">${score.toFixed(0)}</span>
                            </div>
                            ${price ? `<div style="font-size: 0.8rem; color: var(--text-secondary);">$${price.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</div>` : ''}
                            ${theme ? `<div style="font-size: 0.7rem; color: var(--text-muted); margin-top: 4px;">${theme}</div>` : ''}
                        </div>
                        <div style="margin-top: 10px;">
                            ${inWatchlist
                                ? `<button class="btn btn-ghost" style="width: 100%; padding: 6px; font-size: 0.7rem; color: var(--green);" onclick="removeFromWatchlistInScan(${scanId}, '${ticker}')">✓ In Watchlist</button>`
                                : `<button class="btn btn-primary" style="width: 100%; padding: 6px; font-size: 0.7rem;" onclick="addToWatchlistFromScan(${scanId}, '${ticker}', ${price || 0})">+ Add to Watchlist</button>`
                            }
                        </div>
                    </div>
                `;
            }).join('')}
        </div>
        ${results.length > 50 ? `<div style="text-align: center; color: var(--text-muted); font-size: 0.8rem; margin-top: 12px;">Showing 50 of ${results.length} stocks</div>` : ''}
    `;
}

async function addToWatchlistFromScan(scanId, ticker, price) {
    try {
        const res = await fetch(`${API_BASE}/watchlist/add?ticker=${ticker}&notes=From%20Scan%20%23${scanId}`, { method: 'POST' });
        const data = await res.json();
        if (data.ok) {
            // Update button to show "In Watchlist"
            const stockDiv = document.getElementById(`scan-stock-${scanId}-${ticker}`);
            if (stockDiv) {
                const btn = stockDiv.querySelector('button');
                btn.className = 'btn btn-ghost';
                btn.style.color = 'var(--green)';
                btn.textContent = '✓ In Watchlist';
                btn.onclick = () => removeFromWatchlistInScan(scanId, ticker);
            }
            // Refresh watchlist table to show new stock
            refreshWatchlistTable();
        }
    } catch (e) {
        alert('Failed to add to watchlist');
    }
}

// Quick refresh just the watchlist table (not full tab)
async function refreshWatchlistTable() {
    try {
        const wlRes = await fetch(`${API_BASE}/watchlist`);
        const wlData = await wlRes.json();
        if (wlData.ok) {
            const watchlist = wlData.watchlist || [];
            document.getElementById('wl-stat-count').textContent = watchlist.length;
            renderWatchlistTable(watchlist);

            // Update avg performance
            const withPerf = watchlist.filter(w => w.change_pct !== null && w.change_pct !== undefined);
            if (withPerf.length > 0) {
                const avgPerf = withPerf.reduce((sum, w) => sum + w.change_pct, 0) / withPerf.length;
                const avgEl = document.getElementById('wl-stat-avg-perf');
                avgEl.textContent = `${avgPerf >= 0 ? '+' : ''}${avgPerf.toFixed(1)}%`;
                avgEl.style.color = avgPerf >= 0 ? 'var(--green)' : 'var(--red)';
            }
        }
    } catch (e) {
        console.error('Failed to refresh watchlist table:', e);
    }
}

async function removeFromWatchlistInScan(scanId, ticker) {
    try {
        const res = await fetch(`${API_BASE}/watchlist/${ticker}`, { method: 'DELETE' });
        const data = await res.json();
        if (data.ok) {
            // Update button to show "Add to Watchlist"
            const stockDiv = document.getElementById(`scan-stock-${scanId}-${ticker}`);
            if (stockDiv) {
                const btn = stockDiv.querySelector('button');
                btn.className = 'btn btn-primary';
                btn.style.color = '';
                btn.textContent = '+ Add to Watchlist';
                btn.onclick = () => addToWatchlistFromScan(scanId, ticker, 0);
            }
            // Refresh watchlist table
            refreshWatchlistTable();
        }
    } catch (e) {
        alert('Failed to remove from watchlist');
    }
}

async function addAllToWatchlist(scanId) {
    const data = expandedScanData[scanId];
    if (!data || !data.data?.results) return;

    const results = data.data.results.slice(0, 10);
    let added = 0;

    for (const stock of results) {
        try {
            const res = await fetch(`${API_BASE}/watchlist/add?ticker=${stock.ticker}&notes=From%20Scan%20%23${scanId}`, { method: 'POST' });
            const resData = await res.json();
            if (resData.ok) added++;
        } catch (e) {}
    }

    alert(`Added ${added} stocks to watchlist`);
    // Refresh the expanded view
    renderExpandedScan(scanId, data);
    // Update count
    refreshWatchlistTab();
}

async function loadStockHistory() {
    const ticker = document.getElementById('wl-history-ticker').value.trim().toUpperCase();
    if (!ticker) return;
    loadStockHistoryFor(ticker);
}

async function loadStockHistoryFor(ticker) {
    const container = document.getElementById('wl-history-container');
    container.innerHTML = '<div style="text-align: center; color: var(--text-muted);">Loading...</div>';
    document.getElementById('wl-history-ticker').value = ticker;

    try {
        const res = await fetch(`${API_BASE}/history/${ticker}`);
        const data = await res.json();

        if (data.ok && data.history && data.history.length > 0) {
            container.innerHTML = `
                <div style="font-weight: 600; margin-bottom: 12px;">${ticker} appeared in ${data.count} scans</div>
                ${data.history.slice(0, 8).map(h => {
                    const date = h.date ? new Date(h.date).toLocaleDateString('en-US', {month: 'short', day: 'numeric'}) : '';
                    const score = h.stock_data?.story_score || h.stock_data?.composite_score || 0;
                    const price = h.stock_data?.price;
                    return `<div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid var(--border-subtle);">
                        <div>
                            ${h.starred ? '<span style="color: var(--yellow);">⭐</span>' : ''}
                            <span style="font-weight: 500;">#${h.scan_id}</span>
                            <span style="color: var(--text-muted); font-size: 0.75rem; margin-left: 6px;">${date}</span>
                        </div>
                        <div style="font-size: 0.8rem;">
                            ${score ? `<span style="color: var(--blue);">Score: ${score.toFixed(0)}</span>` : ''}
                            ${price ? `<span style="color: var(--text-muted); margin-left: 8px;">$${price.toFixed(2)}</span>` : ''}
                        </div>
                    </div>`;
                }).join('')}
            `;
        } else {
            container.innerHTML = `<div style="color: var(--text-muted); text-align: center;">${ticker} not found in any scans</div>`;
        }
    } catch (e) {
        container.innerHTML = '<div style="color: var(--red);">Failed to load history</div>';
    }
}

async function addToWatchlistFromDashboard() {
    const ticker = document.getElementById('wl-add-ticker').value.trim().toUpperCase();
    const notes = document.getElementById('wl-add-notes').value.trim();
    if (!ticker) return alert('Enter a ticker symbol');

    try {
        const res = await fetch(`${API_BASE}/watchlist/add?ticker=${ticker}&notes=${encodeURIComponent(notes)}`, { method: 'POST' });
        const data = await res.json();
        if (data.ok) {
            document.getElementById('wl-add-ticker').value = '';
            document.getElementById('wl-add-notes').value = '';
            refreshWatchlistTab();
        } else {
            alert('Failed to add: ' + (data.error || 'Unknown error'));
        }
    } catch (e) {
        alert('Failed to add to watchlist');
    }
}

async function starScan(scanId) {
    try {
        const res = await fetch(`${API_BASE}/scans/${scanId}/star`, { method: 'POST' });
        const data = await res.json();
        if (data.ok) {
            refreshWatchlistTab();
        }
    } catch (e) {
        alert('Failed to star scan');
    }
}

async function unstarScan(scanId) {
    try {
        const res = await fetch(`${API_BASE}/scans/${scanId}/unstar`, { method: 'POST' });
        const data = await res.json();
        if (data.ok) {
            refreshWatchlistTab();
        }
    } catch (e) {
        alert('Failed to unstar scan');
    }
}

async function starLatestScan() {
    try {
        const scansRes = await fetch(`${API_BASE}/scans?limit=1`);
        const scansData = await scansRes.json();
        if (scansData.ok && scansData.scans && scansData.scans.length > 0) {
            const latestId = scansData.scans[0].scan_id;
            await starScan(latestId);
        } else {
            alert('No scans available to star');
        }
    } catch (e) {
        alert('Failed to star latest scan');
    }
}

async function cleanupOldScans() {
    if (!confirm('Archive all unstarred scans older than 7 days?')) return;
    try {
        // This would call a cleanup endpoint - for now just refresh
        alert('Use /cleanup command in Telegram to archive old scans');
    } catch (e) {
        alert('Cleanup failed');
    }
}

function exportWatchlist() {
    // Export watchlist as CSV
    const table = document.querySelector('#wl-table-container table');
    if (!table) return alert('No watchlist data to export');

    let csv = 'Ticker,Entry,Current,P&L,Source,Notes\\n';
    table.querySelectorAll('tbody tr').forEach(row => {
        const cells = row.querySelectorAll('td');
        const ticker = cells[0]?.textContent?.trim().split('\\n')[0] || '';
        const entry = cells[1]?.textContent?.trim() || '';
        const current = cells[2]?.textContent?.trim() || '';
        const pnl = cells[3]?.textContent?.trim() || '';
        const source = cells[4]?.textContent?.trim() || '';
        const notes = cells[5]?.textContent?.trim() || '';
        csv += `${ticker},${entry},${current},${pnl},${source},"${notes}"\\n`;
    });

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'watchlist_' + new Date().toISOString().split('T')[0] + '.csv';
    a.click();
}

function viewScanDetail(scanId) {
    // Show scan detail in modal
    showModal('Scan #' + scanId, '<div style="text-align: center; padding: 20px;">Loading scan details...</div>');
    fetch(`${API_BASE}/scans/${scanId}`)
        .then(res => res.json())
        .then(data => {
            if (data.ok) {
                const scan = data.scan;
                const results = data.data?.results || [];
                const date = scan.date ? new Date(scan.date).toLocaleString() : '';

                let html = `
                    <div style="margin-bottom: 16px;">
                        <div style="font-size: 0.9rem; color: var(--text-muted);">${date}</div>
                        <div style="margin-top: 8px;">
                            ${scan.starred ? '<span style="background: var(--yellow-bg); color: var(--yellow); padding: 2px 8px; border-radius: 4px; font-size: 0.75rem;">⭐ Starred</span>' : ''}
                            ${scan.archived ? '<span style="background: var(--bg-hover); color: var(--text-muted); padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; margin-left: 8px;">📁 Archived</span>' : ''}
                        </div>
                    </div>
                    <div style="margin-bottom: 16px;">
                        <div style="font-weight: 600; margin-bottom: 8px;">Top Picks</div>
                        <div style="display: flex; flex-wrap: wrap; gap: 6px;">
                            ${(scan.top_picks || []).map(t => `<span style="background: var(--blue-bg); color: var(--blue); padding: 4px 10px; border-radius: 4px; font-size: 0.8rem;">${t}</span>`).join('')}
                        </div>
                    </div>
                    ${scan.themes && scan.themes.length > 0 ? `
                    <div style="margin-bottom: 16px;">
                        <div style="font-weight: 600; margin-bottom: 8px;">Themes</div>
                        <div style="color: var(--text-secondary); font-size: 0.85rem;">${scan.themes.join(', ')}</div>
                    </div>` : ''}
                    <div>
                        <div style="font-weight: 600; margin-bottom: 8px;">Results (${results.length} stocks)</div>
                        <div style="max-height: 300px; overflow-y: auto;">
                            ${results.slice(0, 20).map((r, i) => `
                                <div style="display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid var(--border-subtle);">
                                    <div>
                                        <span style="color: var(--text-muted); font-size: 0.75rem;">${i + 1}.</span>
                                        <span style="font-weight: 600; margin-left: 4px;">${r.ticker}</span>
                                    </div>
                                    <div style="font-size: 0.85rem;">
                                        <span style="color: var(--blue);">Score: ${(r.story_score || r.composite_score || 0).toFixed(0)}</span>
                                        ${r.price ? `<span style="color: var(--text-muted); margin-left: 12px;">$${r.price.toFixed(2)}</span>` : ''}
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                `;
                document.getElementById('modal-body').innerHTML = html;
            }
        })
        .catch(e => {
            document.getElementById('modal-body').innerHTML = '<div style="color: var(--red);">Failed to load scan details</div>';
        });
}

// Load watchlist tab when switched to
document.addEventListener('DOMContentLoaded', () => {
    const watchlistTab = document.querySelector('[data-tab="watchlist"]');
    if (watchlistTab) {
        watchlistTab.addEventListener('click', () => {
            setTimeout(refreshWatchlistTab, 100);
        });
    }
});

function renderTradeAlerts(highRiskTrades) {
    const container = document.getElementById('trade-alerts-container');
    if (!highRiskTrades || highRiskTrades.length === 0) {
        container.innerHTML = '';
        return;
    }

    container.innerHTML = highRiskTrades.map(trade => `
        <div class="alert ${trade.risk_level === 'critical' ? 'alert-danger' : 'alert-warning'}" style="margin-bottom: 12px;">
            <span class="alert-icon">${trade.risk_level === 'critical' ? '🔴' : '⚠️'}</span>
            <span><strong>${trade.ticker}</strong>: ${trade.risk_level.toUpperCase()} risk (${trade.confidence.toFixed(0)}%) - ${trade.urgency}</span>
        </div>
    `).join('');
}

function updatePortfolioSummary(positions) {
    let totalInvested = 0;
    let currentValue = 0;

    positions.forEach(pos => {
        totalInvested += (pos.average_cost || 0) * (pos.total_shares || 0);
        currentValue += (pos.current_price || pos.average_cost || 0) * (pos.total_shares || 0);
    });

    const totalPnl = currentValue - totalInvested;
    const pnlPct = totalInvested > 0 ? (totalPnl / totalInvested) * 100 : 0;

    document.getElementById('portfolio-invested').textContent = '$' + totalInvested.toLocaleString(undefined, {maximumFractionDigits: 0});
    document.getElementById('portfolio-value').textContent = '$' + currentValue.toLocaleString(undefined, {maximumFractionDigits: 0});

    const pnlEl = document.getElementById('portfolio-pnl');
    pnlEl.textContent = `${totalPnl >= 0 ? '+' : ''}$${totalPnl.toLocaleString(undefined, {maximumFractionDigits: 0})} (${pnlPct >= 0 ? '+' : ''}${pnlPct.toFixed(1)}%)`;
    pnlEl.style.color = totalPnl >= 0 ? 'var(--green)' : 'var(--red)';
}

async function scanAllPositions() {
    document.getElementById('scale-opportunities').innerHTML = '<div style="color: var(--text-muted);">Scanning positions...</div>';

    try {
        const res = await fetch(`${API_BASE}/trades/scan`);
        const data = await res.json();

        if (data.ok) {
            // Update scale opportunities
            let scaleHtml = '';
            const positions = data.positions || [];

            const scaleIns = positions.filter(p => p.scale_in?.should_scale);
            const scaleOuts = positions.filter(p => p.scale_out?.should_scale);

            if (scaleIns.length > 0) {
                scaleHtml += '<div style="margin-bottom: 12px;"><strong style="color: var(--green);">📈 Scale In:</strong></div>';
                scaleIns.forEach(p => {
                    scaleHtml += `<div class="sidebar-item">
                        <span class="sidebar-label">${p.ticker}</span>
                        <span class="sidebar-value" style="color: var(--green);">+${p.scale_in.size_pct.toFixed(0)}%</span>
                    </div>`;
                });
            }

            if (scaleOuts.length > 0) {
                scaleHtml += '<div style="margin-bottom: 12px; margin-top: 16px;"><strong style="color: var(--yellow);">📉 Scale Out:</strong></div>';
                scaleOuts.forEach(p => {
                    scaleHtml += `<div class="sidebar-item">
                        <span class="sidebar-label">${p.ticker}</span>
                        <span class="sidebar-value" style="color: var(--yellow);">-${p.scale_out.size_pct.toFixed(0)}%</span>
                    </div>`;
                });
            }

            if (!scaleHtml) {
                scaleHtml = '<div style="color: var(--text-muted); font-size: 0.8125rem;">No scaling opportunities detected</div>';
            }

            document.getElementById('scale-opportunities').innerHTML = scaleHtml;

            // Refresh positions table with updated risk levels
            fetchTrades();
        }
    } catch (e) {
        console.warn('Scan failed:', e);
        document.getElementById('scale-opportunities').innerHTML = '<div style="color: var(--red);">Scan failed</div>';
    }
}

function showAddTradeModal() {
    const ticker = prompt('Ticker symbol:');
    if (!ticker) return;

    const thesis = prompt('Investment thesis (why this trade?):');
    const theme = prompt('Theme (e.g., AI Infrastructure):') || '';
    const strategy = prompt('Strategy (conservative/aggressive/core_trade/momentum):') || 'conservative';

    addTrade(ticker.toUpperCase(), thesis, theme, strategy);
}

async function addTrade(ticker, thesis, theme, strategy) {
    try {
        const res = await fetch(`${API_BASE}/trades/create`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ticker, thesis, theme, strategy })
        });
        const data = await res.json();

        if (data.ok) {
            alert(`Added ${ticker} to watchlist`);
            fetchTrades();
        } else {
            alert('Error: ' + data.error);
        }
    } catch (e) {
        alert('Failed to add trade');
    }
}

function showBuyModal() {
    const ticker = prompt('Ticker symbol:');
    if (!ticker) return;

    showBuyModalFor(null, ticker.toUpperCase());
}

function showBuyModalFor(tradeId, ticker) {
    const shares = prompt(`Shares to buy for ${ticker}:`);
    if (!shares) return;

    const price = prompt(`Price per share for ${ticker}:`);
    if (!price) return;

    const reason = prompt('Reason for buy:') || 'Manual entry';

    executeBuy(tradeId, ticker, parseInt(shares), parseFloat(price), reason);
}

async function executeBuy(tradeId, ticker, shares, price, reason) {
    try {
        let url = `${API_BASE}/trades/${tradeId}/buy`;

        // If no tradeId, first create the trade
        if (!tradeId) {
            const createRes = await fetch(`${API_BASE}/trades/create`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ticker, thesis: reason })
            });
            const createData = await createRes.json();
            if (!createData.ok) {
                alert('Error creating trade: ' + createData.error);
                return;
            }
            tradeId = createData.trade.id;
            url = `${API_BASE}/trades/${tradeId}/buy`;
        }

        const res = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ shares, price, reason })
        });
        const data = await res.json();

        if (data.ok) {
            alert(data.message);
            fetchTrades();
        } else {
            alert('Error: ' + data.error);
        }
    } catch (e) {
        alert('Failed to execute buy');
    }
}

function showSellModal() {
    const ticker = prompt('Ticker symbol to sell:');
    if (!ticker) return;

    // Find trade by ticker
    alert('Please use the Sell button on a specific position');
}

function showSellModalFor(tradeId, ticker, maxShares) {
    const shares = prompt(`Shares to sell for ${ticker} (max: ${maxShares}):`);
    if (!shares) return;

    const price = prompt(`Price per share for ${ticker}:`);
    if (!price) return;

    const reason = prompt('Reason for sell:') || 'Manual exit';

    executeSell(tradeId, parseInt(shares), parseFloat(price), reason);
}

async function executeSell(tradeId, shares, price, reason) {
    try {
        const res = await fetch(`${API_BASE}/trades/${tradeId}/sell`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ shares, price, reason })
        });
        const data = await res.json();

        if (data.ok) {
            alert(data.message);
            fetchTrades();
        } else {
            alert('Error: ' + data.error);
        }
    } catch (e) {
        alert('Failed to execute sell');
    }
}

async function deleteTrade(tradeId) {
    if (!confirm('Remove this trade from watchlist?')) return;

    try {
        const res = await fetch(`${API_BASE}/trades/${tradeId}`, {
            method: 'DELETE'
        });
        const data = await res.json();

        if (data.ok) {
            fetchTrades();
        } else {
            alert('Error: ' + data.error);
        }
    } catch (e) {
        alert('Failed to delete trade');
    }
}

async function showTradeDetail(tradeId) {
    openModal('Trade Details', '<div style="text-align: center; padding: 20px;">Loading...</div>');

    try {
        const res = await fetch(`${API_BASE}/trades/${tradeId}`);
        const data = await res.json();

        if (data.ok && data.trade) {
            const t = data.trade;
            const pnlPct = t.unrealized_pnl_pct || ((t.current_price - t.average_cost) / t.average_cost * 100) || 0;
            const pnlColor = pnlPct >= 0 ? 'var(--green)' : 'var(--red)';

            const content = `
                <div style="display: grid; gap: 16px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <div style="font-size: 1.5rem; font-weight: 700;">${t.ticker}</div>
                            <div style="color: var(--text-muted);">${t.theme || 'No theme'}</div>
                        </div>
                        <div style="text-align: right;">
                            <div style="font-size: 1.25rem; font-weight: 600; color: ${pnlColor};">${pnlPct >= 0 ? '+' : ''}${pnlPct.toFixed(1)}%</div>
                            <div style="color: var(--text-muted);">${t.status}</div>
                        </div>
                    </div>

                    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px;">
                        <div style="background: var(--bg-hover); padding: 12px; border-radius: 8px;">
                            <div style="font-size: 0.75rem; color: var(--text-muted);">Shares</div>
                            <div style="font-weight: 600;">${t.total_shares}</div>
                        </div>
                        <div style="background: var(--bg-hover); padding: 12px; border-radius: 8px;">
                            <div style="font-size: 0.75rem; color: var(--text-muted);">Avg Cost</div>
                            <div style="font-weight: 600;">$${(t.average_cost || 0).toFixed(2)}</div>
                        </div>
                        <div style="background: var(--bg-hover); padding: 12px; border-radius: 8px;">
                            <div style="font-size: 0.75rem; color: var(--text-muted);">Current</div>
                            <div style="font-weight: 600;">$${(t.current_price || 0).toFixed(2)}</div>
                        </div>
                        <div style="background: var(--bg-hover); padding: 12px; border-radius: 8px;">
                            <div style="font-size: 0.75rem; color: var(--text-muted);">Days Held</div>
                            <div style="font-weight: 600;">${t.days_held}</div>
                        </div>
                    </div>

                    ${t.thesis ? `<div style="padding: 12px; background: var(--bg-hover); border-radius: 8px;">
                        <div style="font-size: 0.75rem; color: var(--text-muted); margin-bottom: 4px;">Thesis</div>
                        <div style="font-size: 0.875rem;">${t.thesis}</div>
                    </div>` : ''}

                    <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px;">
                        <div style="background: var(--bg-hover); padding: 12px; border-radius: 8px;">
                            <div style="font-size: 0.75rem; color: var(--text-muted);">Risk Level</div>
                            <div style="font-weight: 600;">${(t.current_risk_level || 'none').toUpperCase()}</div>
                        </div>
                        <div style="background: var(--bg-hover); padding: 12px; border-radius: 8px;">
                            <div style="font-size: 0.75rem; color: var(--text-muted);">Exit Confidence</div>
                            <div style="font-weight: 600;">${(t.composite_exit_confidence || 0).toFixed(0)}%</div>
                        </div>
                    </div>

                    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px;">
                        <div style="background: var(--bg-hover); padding: 12px; border-radius: 8px;">
                            <div style="font-size: 0.75rem; color: var(--text-muted);">Strategy</div>
                            <div style="font-weight: 600; text-transform: capitalize;">${t.scaling_plan?.strategy || 'conservative'}</div>
                        </div>
                        <div style="background: var(--bg-hover); padding: 12px; border-radius: 8px;">
                            <div style="font-size: 0.75rem; color: var(--text-muted);">Scale-ins</div>
                            <div style="font-weight: 600;">${t.scale_ins_used || 0}/${t.scaling_plan?.max_scale_ins || 3}</div>
                        </div>
                        <div style="background: var(--bg-hover); padding: 12px; border-radius: 8px;">
                            <div style="font-size: 0.75rem; color: var(--text-muted);">Scale-outs</div>
                            <div style="font-weight: 600;">${t.scale_outs_used || 0}</div>
                        </div>
                    </div>

                    <div style="display: flex; gap: 8px; margin-top: 8px;">
                        <button class="btn btn-primary" onclick="showBuyModalFor('${t.id}', '${t.ticker}')" style="flex: 1;">Add Shares</button>
                        <button class="btn btn-ghost" onclick="showSellModalFor('${t.id}', '${t.ticker}', ${t.total_shares})" style="flex: 1;">Sell Shares</button>
                    </div>
                </div>
            `;
            document.getElementById('modal-body').innerHTML = content;

            // Update options flow sidebar
            showOptionsFlowForTicker(t.ticker);
        }
    } catch (e) {
        document.getElementById('modal-body').innerHTML = '<div style="color: var(--red);">Failed to load trade details</div>';
    }
}

async function fetchDailyReport() {
    openModal('Daily Report', '<div style="text-align: center; padding: 20px;">Generating report...</div>');

    try {
        const res = await fetch(`${API_BASE}/trades/daily-report`);
        const data = await res.json();

        if (data.ok && data.report) {
            document.getElementById('modal-body').innerHTML = `
                <div style="white-space: pre-wrap; line-height: 1.7; font-size: 0.875rem; font-family: monospace;">${data.report}</div>
            `;
        } else {
            document.getElementById('modal-body').innerHTML = '<div style="color: var(--red);">Failed to generate report</div>';
        }
    } catch (e) {
        document.getElementById('modal-body').innerHTML = '<div style="color: var(--red);">Failed to generate report</div>';
    }
}

// =============================================================================
// AI ADVISOR FUNCTIONS
// =============================================================================

async function refreshAIAdvisor() {
    document.getElementById('ai-insight').innerHTML = '<span style="color: var(--text-muted);">Analyzing positions...</span>';

    try {
        // Get risk assessment for AI insights
        const riskRes = await fetch(`${API_BASE}/trades/risk`);
        const riskData = await riskRes.json();

        // Get scan data for market context
        const scanRes = await fetch(`${API_BASE}/trades/scan`);
        const scanData = await scanRes.json();

        if (riskData.ok && scanData.ok) {
            const positions = scanData.positions || [];
            const highRisk = riskData.high_risk_trades || [];

            // Determine priority action
            let priorityAction = 'HOLD';
            let priorityColor = 'var(--text)';
            if (highRisk.length > 0) {
                const critical = highRisk.filter(t => t.risk_level === 'critical');
                if (critical.length > 0) {
                    priorityAction = `EXIT ${critical[0].ticker}`;
                    priorityColor = 'var(--red)';
                } else {
                    priorityAction = `REVIEW ${highRisk[0].ticker}`;
                    priorityColor = 'var(--yellow)';
                }
            } else {
                const scaleIns = positions.filter(p => p.scale_in?.should_scale);
                if (scaleIns.length > 0) {
                    priorityAction = `SCALE IN ${scaleIns[0].ticker}`;
                    priorityColor = 'var(--green)';
                }
            }

            // Determine market regime based on positions
            let regime = 'NEUTRAL';
            let regimeColor = 'var(--text-muted)';
            const avgPnl = positions.length > 0 ? positions.reduce((sum, p) => sum + (p.pnl_pct || 0), 0) / positions.length : 0;
            if (avgPnl > 5) {
                regime = 'BULLISH';
                regimeColor = 'var(--green)';
            } else if (avgPnl < -5) {
                regime = 'BEARISH';
                regimeColor = 'var(--red)';
            }

            // Determine overall stance
            let stance = 'NEUTRAL';
            let stanceColor = 'var(--text-muted)';
            const riskLevel = riskData.overall_risk || 'none';
            if (riskLevel === 'critical' || riskLevel === 'high') {
                stance = 'DEFENSIVE';
                stanceColor = 'var(--red)';
            } else if (riskLevel === 'elevated') {
                stance = 'CAUTIOUS';
                stanceColor = 'var(--yellow)';
            } else if (positions.length > 0 && avgPnl > 0) {
                stance = 'AGGRESSIVE';
                stanceColor = 'var(--green)';
            }

            document.getElementById('ai-priority-action').innerHTML = `<span style="color: ${priorityColor};">${priorityAction}</span>`;
            document.getElementById('ai-market-regime').innerHTML = `<span style="color: ${regimeColor};">${regime}</span>`;
            document.getElementById('ai-stance').innerHTML = `<span style="color: ${stanceColor};">${stance}</span>`;

            // Generate insight
            let insight = '';
            if (positions.length === 0) {
                insight = 'No open positions. Consider scanning for high-conviction setups with strong story scores.';
            } else if (highRisk.length > 0) {
                insight = `${highRisk.length} position(s) require attention. ${highRisk[0].ticker} shows ${highRisk[0].risk_level} risk level (${highRisk[0].confidence}% confidence). Consider reducing exposure.`;
            } else {
                const winners = positions.filter(p => (p.pnl_pct || 0) > 0);
                const losers = positions.filter(p => (p.pnl_pct || 0) < 0);
                insight = `Portfolio is ${winners.length > losers.length ? 'performing well' : 'mixed'}. ${winners.length} winners, ${losers.length} losers. `;
                if (avgPnl > 10) {
                    insight += 'Consider taking partial profits on extended positions.';
                } else if (avgPnl < -5) {
                    insight += 'Review stop levels and thesis integrity for underperformers.';
                } else {
                    insight += 'Continue monitoring story developments and technical levels.';
                }
            }
            document.getElementById('ai-insight').innerHTML = insight;
        }
    } catch (e) {
        console.warn('AI Advisor refresh failed:', e);
        document.getElementById('ai-insight').innerHTML = '<span style="color: var(--red);">Failed to load AI insights</span>';
    }
}

// =============================================================================
// JOURNAL FUNCTIONS
// =============================================================================

async function fetchJournal() {
    try {
        const res = await fetch(`${API_BASE}/trades/journal`);
        const data = await res.json();

        if (data.ok) {
            journalEntries = data.entries || [];
            renderJournal(journalEntries);
        } else {
            // Journal endpoint might not exist yet, show empty state
            journalEntries = [];
            renderJournal([]);
        }
    } catch (e) {
        console.warn('Journal fetch failed:', e);
        journalEntries = [];
        renderJournal([]);
    }
}

function filterJournal() {
    const filter = document.getElementById('journal-filter').value;
    if (filter === 'all') {
        renderJournal(journalEntries);
    } else {
        renderJournal(journalEntries.filter(e => e.entry_type === filter));
    }
}

function renderJournal(entries) {
    const container = document.getElementById('journal-container');

    if (!entries || entries.length === 0) {
        container.innerHTML = `<div style="text-align: center; padding: 30px;">
            <div style="font-size: 2rem; margin-bottom: 8px;">📓</div>
            <div style="color: var(--text-muted);">No journal entries yet.</div>
            <div style="color: var(--text-muted); font-size: 0.8rem; margin-top: 4px;">Document your trades, lessons, and insights.</div>
        </div>`;
        return;
    }

    const typeIcons = {
        'trade': '💹',
        'note': '📝',
        'lesson': '💡',
        'mistake': '⚠️'
    };
    const typeColors = {
        'trade': 'var(--blue)',
        'note': 'var(--text-muted)',
        'lesson': 'var(--green)',
        'mistake': 'var(--red)'
    };

    container.innerHTML = entries.map(entry => {
        const icon = typeIcons[entry.entry_type] || '📝';
        const color = typeColors[entry.entry_type] || 'var(--text-muted)';
        const date = new Date(entry.timestamp).toLocaleDateString('en-US', {month: 'short', day: 'numeric'});
        const time = new Date(entry.timestamp).toLocaleTimeString('en-US', {hour: '2-digit', minute: '2-digit'});

        return `<div style="padding: 12px; background: var(--bg-hover); border-radius: 8px; margin-bottom: 10px; border-left: 3px solid ${color};">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 6px;">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="font-size: 1.1rem;">${icon}</span>
                    ${entry.ticker ? `<span style="font-weight: 600;">${entry.ticker}</span>` : ''}
                    <span style="font-size: 0.7rem; padding: 2px 6px; background: ${color}20; color: ${color}; border-radius: 4px; text-transform: capitalize;">${entry.entry_type}</span>
                </div>
                <span style="font-size: 0.7rem; color: var(--text-muted);">${date} ${time}</span>
            </div>
            <div style="font-size: 0.85rem; line-height: 1.5;">${entry.content}</div>
            ${entry.tags && entry.tags.length > 0 ? `<div style="margin-top: 8px; display: flex; gap: 4px; flex-wrap: wrap;">
                ${entry.tags.map(tag => `<span style="font-size: 0.65rem; padding: 2px 6px; background: var(--bg-card); border-radius: 4px; color: var(--text-muted);">#${tag}</span>`).join('')}
            </div>` : ''}
        </div>`;
    }).join('');
}

function showAddJournalEntry() {
    const entryType = prompt('Entry type (trade/note/lesson/mistake):', 'note') || 'note';
    const validTypes = ['trade', 'note', 'lesson', 'mistake'];
    if (!validTypes.includes(entryType.toLowerCase())) {
        alert('Invalid type. Use: trade, note, lesson, or mistake');
        return;
    }

    const ticker = prompt('Ticker (optional, press Enter to skip):') || '';
    const content = prompt('Entry content:');
    if (!content) return;

    const tagsStr = prompt('Tags (comma-separated, optional):') || '';
    const tags = tagsStr ? tagsStr.split(',').map(t => t.trim()).filter(t => t) : [];

    addJournalEntry(entryType.toLowerCase(), content, ticker.toUpperCase() || null, tags);
}

async function addJournalEntry(entryType, content, ticker = null, tags = []) {
    try {
        const res = await fetch(`${API_BASE}/trades/journal`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ entry_type: entryType, content, ticker, tags })
        });
        const data = await res.json();

        if (data.ok) {
            fetchJournal();
            // Also add to activity feed
            addActivityItem(`Added ${entryType} journal entry${ticker ? ` for ${ticker}` : ''}`);
        } else {
            alert('Failed to add entry: ' + (data.error || 'Unknown error'));
        }
    } catch (e) {
        alert('Failed to add journal entry');
    }
}

// =============================================================================
// MARKET HEALTH TAB
// =============================================================================

async function fetchMarketHealth() {
    try {
        // Show loading state
        document.getElementById('health-gauge-score').textContent = '...';
        document.getElementById('health-gauge-label').textContent = 'Analyzing...';

        const res = await fetch(`${API_BASE}/market-health/ai-analysis`);
        const data = await res.json();

        if (!data.ok) {
            console.error('Market health fetch failed:', data.error);
            document.getElementById('health-gauge-label').textContent = 'Error loading';
            return;
        }

        const health = data.data.health_data;
        const ai = data.data.ai_analysis;

        // Update Composite Score Gauge
        updateHealthGauge(health.composite_score, health.verdict);

        // Update AI Synthesis
        updateAISynthesis(ai, health);

        // Update Component Scores
        updateComponentScores(health.components);

        // Update Volume Profile Chart
        updateVolumeProfileChart(health.components.volume_profile);

        // Update Options Gauges
        updateOptionsGauges(health.components.options);

        // Update FRED Data
        updateFREDSparklines(health.components.fred);

        // Update Sentiment Donuts (News + X/Social)
        updateSentimentDonuts(health.components.sentiment, health.components.x_sentiment);

        // Update Radar Chart
        updateRadarChart(health.components);

        // Update Catalysts & Actions
        updateCatalysts(health.catalysts);
        updateActionItems(health.action_items);

        // Update Divergences
        updateDivergences(health.divergences);

        // Update score trend with real history data from API
        updateScoreTrend(health.history || [], health.composite_score);

    } catch (e) {
        console.error('Market health error:', e);
        document.getElementById('health-gauge-label').textContent = 'Error';
    }
}

function updateHealthGauge(score, verdict) {
    const scoreEl = document.getElementById('health-gauge-score');
    const labelEl = document.getElementById('health-gauge-label');
    const arcEl = document.getElementById('health-gauge-arc');

    scoreEl.textContent = score;
    labelEl.textContent = verdict;

    // Semi-circle arc length for radius 80 = π * 80 = 251.2
    // stroke-dashoffset controls how much is hidden
    // At 0%: dashoffset = 251.2 (fully hidden)
    // At 100%: dashoffset = 0 (fully visible)
    const arcLength = 251.2;
    const dashOffset = arcLength * (1 - score / 100);
    arcEl.setAttribute('stroke-dashoffset', dashOffset);

    // Set color based on score
    let color = 'var(--yellow)';
    if (score >= 70) color = 'var(--green)';
    else if (score >= 55) color = '#86efac';
    else if (score <= 30) color = 'var(--red)';
    else if (score <= 45) color = 'var(--orange)';

    arcEl.setAttribute('stroke', color);
    scoreEl.style.fill = color;
}

function updateAISynthesis(ai, health) {
    const insightEl = document.getElementById('health-ai-insight');
    const obsEl = document.getElementById('health-observations');
    const riskBadge = document.getElementById('health-risk-badge');

    insightEl.textContent = ai.key_insight || 'Analysis not available';

    // Risk badge
    const riskColors = {
        'low': { bg: 'rgba(34,197,94,0.2)', text: 'var(--green)' },
        'medium': { bg: 'rgba(245,158,11,0.2)', text: 'var(--orange)' },
        'high': { bg: 'rgba(239,68,68,0.2)', text: 'var(--red)' }
    };
    const riskStyle = riskColors[ai.risk_level] || riskColors.medium;
    riskBadge.textContent = `${ai.risk_level?.toUpperCase() || 'MEDIUM'} RISK`;
    riskBadge.style.background = riskStyle.bg;
    riskBadge.style.color = riskStyle.text;

    // Observations
    if (ai.top_3_observations && ai.top_3_observations.length > 0) {
        obsEl.innerHTML = ai.top_3_observations.map(obs =>
            `<div style="margin-bottom: 4px;">• ${obs}</div>`
        ).join('');
    }
}

function updateComponentScores(components) {
    const updates = [
        { id: 'health-tech-score', bar: 'health-tech-bar', key: 'volume_profile', color: 'var(--blue)' },
        { id: 'health-options-score', bar: 'health-options-bar', key: 'options', color: 'var(--green)' },
        { id: 'health-macro-score', bar: 'health-macro-bar', key: 'fred', color: 'var(--yellow)' },
        { id: 'health-sentiment-score', bar: 'health-sentiment-bar', key: 'sentiment', color: 'var(--purple)' },
        { id: 'health-inst-score', bar: 'health-inst-bar', key: 'institutional', color: 'var(--cyan)' },
    ];

    updates.forEach(({ id, bar, key, color }) => {
        const score = components[key]?.score || 50;
        document.getElementById(id).textContent = score;
        const barEl = document.getElementById(bar);
        if (barEl) {
            barEl.innerHTML = `<div style="height: 100%; width: ${score}%; background: ${color}; border-radius: 2px; transition: width 0.5s;"></div>`;
        }
    });

    // Risk score (inverse of average - lower composite = higher risk)
    const avgScore = Object.values(components).reduce((sum, c) => sum + (c.score || 50), 0) / Object.keys(components).length;
    const riskScore = Math.round(100 - avgScore);
    document.getElementById('health-risk-score').textContent = riskScore;
    document.getElementById('health-risk-bar').innerHTML = `<div style="height: 100%; width: ${riskScore}%; background: var(--orange); border-radius: 2px;"></div>`;
}

function updateVolumeProfileChart(vp) {
    const container = document.getElementById('health-volume-profile');
    if (!vp || vp.error) {
        container.innerHTML = '<div style="color: var(--text-muted); text-align: center; padding-top: 70px;">Volume profile unavailable</div>';
        return;
    }

    // Update position badge
    const positionEl = document.getElementById('health-vp-position');
    const positionLabels = {
        'above_vah': { text: 'Above VAH', color: 'var(--green)' },
        'below_val': { text: 'Below VAL', color: 'var(--red)' },
        'at_poc': { text: 'At POC', color: '#a855f7' },
        'above_poc': { text: 'Above POC', color: '#86efac' },
        'below_poc': { text: 'Below POC', color: 'var(--orange)' },
        'in_range': { text: 'In Range', color: 'var(--text-muted)' }
    };
    const pos = positionLabels[vp.position] || positionLabels.in_range;
    positionEl.textContent = pos.text;
    positionEl.style.background = pos.color;
    positionEl.style.color = 'white';

    // Update values
    document.getElementById('health-vp-val').textContent = `$${vp.val?.toFixed(2) || '--'}`;
    document.getElementById('health-vp-poc').textContent = `$${vp.poc?.toFixed(2) || '--'}`;
    document.getElementById('health-vp-vah').textContent = `$${vp.vah?.toFixed(2) || '--'}`;
    document.getElementById('health-vp-current').textContent = `$${vp.current_price?.toFixed(2) || '--'}`;

    // Build horizontal bar chart using real volume_by_price data
    const poc = vp.poc || 0;
    const vah = vp.vah || 0;
    const val = vp.val || 0;
    const current = vp.current_price || 0;
    const volumeByPrice = vp.volume_by_price || [];

    let html = '<div style="display: flex; flex-direction: column; gap: 2px; height: 100%;">';

    // Use real volume data if available, otherwise show placeholder
    if (volumeByPrice.length === 0) {
        html += '<div style="color: var(--text-muted); text-align: center; padding-top: 60px;">Volume data loading...</div>';
    } else {
        // Show up to 12 price levels (reverse to show high prices at top)
        const levels = volumeByPrice.slice(-12).reverse();
        const priceStep = levels.length > 1 ? Math.abs(levels[0].price - levels[1].price) : 1;

        levels.forEach(level => {
            const price = level.price;
            const volumePct = level.pct || 0;  // Real percentage from API
            const isVAH = Math.abs(price - vah) < priceStep * 0.6;
            const isPOC = Math.abs(price - poc) < priceStep * 0.6;
            const isVAL = Math.abs(price - val) < priceStep * 0.6;
            const isCurrent = Math.abs(price - current) < priceStep * 0.6;
            const inValueArea = price >= val && price <= vah;

            let barColor = 'rgba(100,116,139,0.3)';
            if (isPOC) barColor = '#a855f7';
            else if (isVAH) barColor = 'var(--green)';
            else if (isVAL) barColor = 'var(--red)';
            else if (inValueArea) barColor = 'rgba(139,92,246,0.4)';

            html += `<div style="display: flex; align-items: center; gap: 4px; flex: 1;">
                <div style="width: 45px; font-size: 0.6rem; color: var(--text-muted); text-align: right;">$${price.toFixed(0)}</div>
                <div style="flex: 1; height: 100%; background: rgba(100,116,139,0.1); border-radius: 2px; position: relative;">
                    <div style="height: 100%; width: ${volumePct}%; background: ${barColor}; border-radius: 2px;"></div>
                    ${isCurrent ? `<div style="position: absolute; right: 4px; top: 50%; transform: translateY(-50%); width: 8px; height: 8px; background: white; border: 2px solid ${pos.color}; border-radius: 50%;"></div>` : ''}
                </div>
                <div style="width: 30px; font-size: 0.55rem; color: var(--text-muted);">
                    ${isPOC ? 'POC' : isVAH ? 'VAH' : isVAL ? 'VAL' : isCurrent ? '●' : ''}
                </div>
            </div>`;
        });
    }

    html += '</div>';
    container.innerHTML = html;
}

function updateOptionsGauges(options) {
    if (!options || options.error) return;

    // P/C Ratio
    const pcRatio = options.put_call_ratio || 1;
    document.getElementById('health-pc-value').textContent = pcRatio.toFixed(2);
    const pcAngle = Math.min(1, Math.max(0, (1.5 - pcRatio) / 1)); // 0.5-1.5 range
    updateMiniGauge('health-pc-arc', pcAngle, pcRatio < 0.8 ? 'var(--green)' : pcRatio > 1.2 ? 'var(--red)' : 'var(--yellow)');

    // Sentiment
    const sentiment = options.sentiment || 'neutral';
    document.getElementById('health-iv-value').textContent = sentiment.charAt(0).toUpperCase() + sentiment.slice(1);
    const sentAngle = sentiment === 'bullish' ? 0.8 : sentiment === 'bearish' ? 0.2 : 0.5;
    updateMiniGauge('health-iv-arc', sentAngle, sentiment === 'bullish' ? 'var(--green)' : sentiment === 'bearish' ? 'var(--red)' : 'var(--yellow)');

    // Volume bars
    const callVol = options.call_volume || 0;
    const putVol = options.put_volume || 0;
    const totalVol = callVol + putVol || 1;
    const callPct = (callVol / totalVol) * 100;

    document.getElementById('health-call-bar').style.width = `${callPct}%`;
    document.getElementById('health-put-bar').style.width = `${100 - callPct}%`;
    document.getElementById('health-call-vol').textContent = formatVolume(callVol);
    document.getElementById('health-put-vol').textContent = formatVolume(putVol);
}

function updateMiniGauge(id, pct, color) {
    const arc = document.getElementById(id);
    if (!arc) return;

    // Semi-circle arc length for radius 40 = π * 40 = 125.6
    // pct is 0-1, so dashoffset = arcLength * (1 - pct)
    const arcLength = 125.6;
    const dashOffset = arcLength * (1 - pct);
    arc.setAttribute('stroke-dashoffset', dashOffset);
    arc.setAttribute('stroke', color);
}

function updateFREDSparklines(fred) {
    if (!fred || fred.error) return;

    const data = fred.data || {};

    // Update values
    document.getElementById('health-fred-rate').textContent = `${data.fed_funds_rate?.value?.toFixed(2) || '--'}%`;
    document.getElementById('health-fred-cpi').textContent = `${data.cpi_yoy?.value?.toFixed(1) || '--'}%`;
    document.getElementById('health-fred-unemp').textContent = `${data.unemployment?.value?.toFixed(1) || '--'}%`;
    document.getElementById('health-fred-vix').textContent = data.vix?.value?.toFixed(1) || '--';
    document.getElementById('health-fred-yield').textContent = `${data.yield_curve?.toFixed(2) || '--'}%`;

    // Yield curve marker position
    const yieldCurve = data.yield_curve || 0;
    const yieldPct = Math.min(100, Math.max(0, (yieldCurve + 1) / 2 * 100)); // -1 to +1 maps to 0-100%
    document.getElementById('health-yield-marker').style.left = `${yieldPct}%`;

    // Show current value indicator (real data, no mock sparklines)
    // Historical sparklines require time-series data not currently available from FRED API
    ['rate', 'cpi', 'unemp', 'vix'].forEach(key => {
        const sparkEl = document.getElementById(`health-fred-${key}-spark`);
        if (sparkEl) {
            // Show a single bar representing current value relative to typical range
            const ranges = { rate: [0, 8], cpi: [0, 10], unemp: [3, 10], vix: [10, 40] };
            const values = {
                rate: data.fed_funds_rate?.value || 0,
                cpi: data.cpi_yoy?.value || 0,
                unemp: data.unemployment?.value || 0,
                vix: data.vix?.value || 0
            };
            const [min, max] = ranges[key];
            const val = values[key];
            const pct = Math.min(100, Math.max(0, ((val - min) / (max - min)) * 100));

            // Color based on value (green=good, red=concerning)
            let color = 'var(--blue)';
            if (key === 'vix') {
                color = val < 15 ? 'var(--green)' : val > 25 ? 'var(--red)' : 'var(--yellow)';
            } else if (key === 'cpi') {
                color = val <= 2.5 ? 'var(--green)' : val > 5 ? 'var(--red)' : 'var(--yellow)';
            } else if (key === 'unemp') {
                color = val < 4 ? 'var(--green)' : val > 5.5 ? 'var(--red)' : 'var(--yellow)';
            }

            sparkEl.innerHTML = `<div style="width: 100%; height: 100%; background: rgba(100,116,139,0.2); border-radius: 2px; position: relative;">
                <div style="position: absolute; bottom: 0; left: 0; width: 100%; height: ${pct}%; background: ${color}; opacity: 0.6; border-radius: 2px;"></div>
            </div>`;
        }
    });
}

function updateSentimentDonuts(sentiment, xSentiment) {
    // News sentiment
    if (!sentiment || sentiment.error) {
        document.getElementById('health-news-pct').textContent = '--%';
    } else {
        const newsScore = sentiment.score || 50;
        const newsDonut = document.getElementById('health-news-donut');
        const newsOffset = 251.2 * (1 - newsScore / 100);
        newsDonut.setAttribute('stroke-dashoffset', newsOffset);
        newsDonut.setAttribute('stroke', newsScore > 60 ? 'var(--green)' : newsScore < 40 ? 'var(--red)' : 'var(--yellow)');

        document.getElementById('health-news-pct').textContent = `${newsScore}%`;
        document.getElementById('health-news-label').textContent = sentiment.label || 'Neutral';
        document.getElementById('health-news-label').style.color = newsScore > 60 ? 'var(--green)' : newsScore < 40 ? 'var(--red)' : 'var(--yellow)';
    }

    // X/Social sentiment (real-time from X search)
    const xDonut = document.getElementById('health-x-donut');
    if (!xSentiment || !xSentiment.available) {
        // X Intelligence not available
        xDonut.setAttribute('stroke-dashoffset', '251.2');
        xDonut.setAttribute('stroke', 'rgba(100,116,139,0.3)');
        document.getElementById('health-x-pct').textContent = 'N/A';
        document.getElementById('health-x-label').textContent = xSentiment?.error ? 'Unavailable' : 'Not Configured';
        document.getElementById('health-x-label').style.color = 'var(--text-muted)';
    } else {
        // Display real X sentiment
        const xScore = xSentiment.score || 50;
        const xOffset = 251.2 * (1 - xScore / 100);
        xDonut.setAttribute('stroke-dashoffset', xOffset);
        xDonut.setAttribute('stroke', xScore > 60 ? 'var(--green)' : xScore < 40 ? 'var(--red)' : 'var(--yellow)');

        document.getElementById('health-x-pct').textContent = `${xScore}%`;

        // Label based on sentiment
        const xLabel = xSentiment.sentiment === 'bullish' ? 'Bullish' :
                       xSentiment.sentiment === 'bearish' ? 'Bearish' : 'Neutral';
        document.getElementById('health-x-label').textContent = xLabel;
        document.getElementById('health-x-label').style.color = xScore > 60 ? 'var(--green)' : xScore < 40 ? 'var(--red)' : 'var(--yellow)';

        // Show volume indicator if elevated
        if (xSentiment.volume === 'elevated' || xSentiment.volume === 'spiking') {
            document.getElementById('health-x-label').textContent = `${xLabel} 🔥`;
        }
    }
}

function updateRadarChart(components) {
    const radar = document.getElementById('health-radar-data');
    if (!radar) return;

    // Get scores (0-100)
    const tech = (components.volume_profile?.score || 50) / 100;
    const options = (components.options?.score || 50) / 100;
    const sentiment = (components.sentiment?.score || 50) / 100;
    const inst = (components.institutional?.score || 50) / 100;
    const macro = (components.fred?.score || 50) / 100;

    // Calculate points (5 axes)
    // Technical: top (100, 20)
    // Options: top-right (170, 65)
    // Sentiment: bottom-right (155, 145)
    // Institutional: bottom-left (45, 145)
    // Macro: top-left (30, 65)

    const center = 100;
    const maxRadius = 80;

    const points = [
        { x: center, y: center - maxRadius * tech },
        { x: center + maxRadius * 0.875 * options, y: center - maxRadius * 0.44 * options },
        { x: center + maxRadius * 0.69 * sentiment, y: center + maxRadius * 0.56 * sentiment },
        { x: center - maxRadius * 0.69 * inst, y: center + maxRadius * 0.56 * inst },
        { x: center - maxRadius * 0.875 * macro, y: center - maxRadius * 0.44 * macro }
    ];

    const pointsStr = points.map(p => `${p.x.toFixed(0)},${p.y.toFixed(0)}`).join(' ');
    radar.setAttribute('points', pointsStr);
}

function updateCatalysts(catalysts) {
    const container = document.getElementById('health-catalyst-events');
    if (!catalysts || catalysts.length === 0) {
        container.innerHTML = '<div style="text-align: center; color: var(--text-muted);">No upcoming catalysts</div>';
        return;
    }

    const impactColors = {
        'high': 'var(--red)',
        'medium': 'var(--orange)',
        'low': 'var(--green)'
    };

    container.innerHTML = catalysts.slice(0, 4).map(cat => `
        <div style="text-align: center; flex: 1;">
            <div style="width: 12px; height: 12px; background: ${impactColors[cat.impact] || 'var(--yellow)'}; border-radius: 50%; margin: 0 auto 8px; border: 2px solid var(--bg-card);"></div>
            <div style="font-size: 0.7rem; font-weight: 600;">${cat.event}</div>
            <div style="font-size: 0.6rem; color: var(--text-muted);">${cat.days_away}d away</div>
        </div>
    `).join('');
}

function updateActionItems(items) {
    const container = document.getElementById('health-action-items');
    if (!items || items.length === 0) {
        container.innerHTML = '<div style="color: var(--text-muted);">No specific actions recommended</div>';
        return;
    }

    container.innerHTML = items.slice(0, 4).map(item =>
        `<div style="margin-bottom: 6px; padding-left: 12px; border-left: 2px solid var(--blue);">${item}</div>`
    ).join('');
}

function updateDivergences(divergences) {
    const alertEl = document.getElementById('health-divergence-alert');
    const textEl = document.getElementById('health-divergence-text');

    if (!divergences || divergences.length === 0) {
        alertEl.style.display = 'none';
        return;
    }

    alertEl.style.display = 'block';
    textEl.innerHTML = divergences.map(d => `<div>• ${d}</div>`).join('');
}

function updateScoreTrend(history, currentScore) {
    const container = document.getElementById('health-trend-chart');

    // Use real historical data from API - no mock data
    // history format: [{date: '2025-02-03', day: 'Mon', score: 52}, ...]

    if (!history || history.length === 0) {
        // No historical data yet - show current score only
        const today = new Date().toLocaleDateString('en-US', { weekday: 'short' });
        container.innerHTML = `
            <div style="display: flex; align-items: flex-end; gap: 4px; width: 100%; height: 100%;">
                <div style="flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: flex-end; height: 100%;">
                    <div style="width: 100%; height: 60px; background: var(--yellow); border-radius: 4px 4px 0 0;"></div>
                    <div style="font-size: 0.55rem; color: var(--text-muted); margin-top: 4px;">${today}</div>
                </div>
                <div style="flex: 5; display: flex; align-items: center; justify-content: center; color: var(--text-muted); font-size: 0.75rem;">
                    Building history... (refreshes every hour)
                </div>
            </div>
        `;
        return;
    }

    const scores = history.map(h => h.score);
    const maxScore = Math.max(...scores);
    const minScore = Math.min(...scores);
    const range = maxScore - minScore || 1;

    let html = '<div style="display: flex; align-items: flex-end; gap: 4px; width: 100%; height: 100%;">';
    history.forEach((entry, i) => {
        const height = ((entry.score - minScore) / range) * 60 + 20; // 20-80px height
        const color = entry.score >= 60 ? 'var(--green)' : entry.score <= 40 ? 'var(--red)' : 'var(--yellow)';
        const isLatest = i === history.length - 1;

        html += `
            <div style="flex: 1; display: flex; flex-direction: column; align-items: center;" title="${entry.date}: ${entry.score}">
                <div style="font-size: 0.5rem; color: ${color}; margin-bottom: 2px;">${entry.score}</div>
                <div style="width: 100%; height: ${height}px; background: ${color}; border-radius: 4px 4px 0 0; opacity: ${isLatest ? 1 : 0.6};"></div>
                <div style="font-size: 0.55rem; color: var(--text-muted); margin-top: 4px;">${entry.day}</div>
            </div>
        `;
    });
    html += '</div>';

    container.innerHTML = html;
}

// =============================================================================
// THEME CONCENTRATION
// =============================================================================

function renderThemeConcentration(positions) {
    const container = document.getElementById('theme-concentration-chart');

    if (!positions || positions.length === 0) {
        container.innerHTML = '<div style="color: var(--text-muted); font-size: 0.75rem;">No positions to analyze</div>';
        return;
    }

    // Group by theme
    const themeValues = {};
    let totalValue = 0;

    positions.forEach(pos => {
        const theme = pos.theme || 'No Theme';
        const value = (pos.current_price || pos.average_cost || 0) * (pos.total_shares || 0);
        themeValues[theme] = (themeValues[theme] || 0) + value;
        totalValue += value;
    });

    if (totalValue === 0) {
        container.innerHTML = '<div style="color: var(--text-muted); font-size: 0.75rem;">No position values</div>';
        return;
    }

    // Sort by value
    const sortedThemes = Object.entries(themeValues).sort((a, b) => b[1] - a[1]);

    // Theme colors
    const themeColors = [
        'var(--blue)', 'var(--purple)', 'var(--green)', 'var(--yellow)',
        'var(--red)', 'var(--cyan)', 'var(--pink)', 'var(--text-muted)'
    ];

    container.innerHTML = sortedThemes.map(([theme, value], i) => {
        const pct = (value / totalValue * 100).toFixed(1);
        const color = themeColors[i % themeColors.length];

        return `<div style="margin-bottom: 8px;">
            <div style="display: flex; justify-content: space-between; font-size: 0.7rem; margin-bottom: 2px;">
                <span style="color: ${color};">${theme}</span>
                <span>${pct}%</span>
            </div>
            <div style="height: 6px; background: var(--bg-hover); border-radius: 3px; overflow: hidden;">
                <div style="height: 100%; width: ${pct}%; background: ${color}; transition: width 0.3s;"></div>
            </div>
        </div>`;
    }).join('');
}

// =============================================================================
// PERFORMANCE METRICS
// =============================================================================

function updatePerformanceMetrics(positions) {
    // Calculate from positions
    const wins = positions.filter(p => (p.pnl_pct || 0) > 0);
    const losses = positions.filter(p => (p.pnl_pct || 0) < 0);

    const avgWin = wins.length > 0 ? wins.reduce((sum, p) => sum + (p.pnl_pct || 0), 0) / wins.length : 0;
    const avgLoss = losses.length > 0 ? losses.reduce((sum, p) => sum + Math.abs(p.pnl_pct || 0), 0) / losses.length : 0;

    const totalWins = wins.reduce((sum, p) => sum + (p.pnl_value || 0), 0);
    const totalLosses = Math.abs(losses.reduce((sum, p) => sum + (p.pnl_value || 0), 0));
    const profitFactor = totalLosses > 0 ? (totalWins / totalLosses).toFixed(2) : (totalWins > 0 ? '∞' : '--');

    const allPnl = positions.map(p => p.pnl_pct || 0);
    const bestTrade = allPnl.length > 0 ? Math.max(...allPnl) : 0;
    const worstTrade = allPnl.length > 0 ? Math.min(...allPnl) : 0;

    const avgHoldTime = positions.length > 0 ? Math.round(positions.reduce((sum, p) => sum + (p.days_held || 0), 0) / positions.length) : 0;

    document.getElementById('perf-avg-win').textContent = avgWin > 0 ? `+${avgWin.toFixed(1)}%` : '--';
    document.getElementById('perf-avg-loss').textContent = avgLoss > 0 ? `-${avgLoss.toFixed(1)}%` : '--';
    document.getElementById('perf-profit-factor').textContent = profitFactor;
    document.getElementById('perf-best').textContent = bestTrade > 0 ? `+${bestTrade.toFixed(1)}%` : '--';
    document.getElementById('perf-worst').textContent = worstTrade < 0 ? `${worstTrade.toFixed(1)}%` : '--';
    document.getElementById('perf-hold-time').textContent = avgHoldTime > 0 ? `${avgHoldTime}d` : '--';
}

// =============================================================================
// ACTIVITY FEED
// =============================================================================

let activityItems = [];

async function fetchActivityFeed() {
    try {
        const res = await fetch(`${API_BASE}/trades/activity`);
        const data = await res.json();

        if (data.ok) {
            activityItems = data.activities || [];
            renderActivityFeed();
        } else {
            // Activity endpoint might not exist, use local tracking
            renderActivityFeed();
        }
    } catch (e) {
        // Fallback to showing recent local activity
        renderActivityFeed();
    }
}

function renderActivityFeed() {
    const container = document.getElementById('recent-activity');

    if (activityItems.length === 0) {
        container.innerHTML = '<div style="color: var(--text-muted); font-size: 0.8rem;">No recent activity</div>';
        return;
    }

    container.innerHTML = activityItems.slice(0, 10).map(item => {
        const time = item.timestamp ? new Date(item.timestamp).toLocaleTimeString('en-US', {hour: '2-digit', minute: '2-digit'}) : 'now';
        const typeEmoji = {
            'buy': '📈',
            'sell': '📉',
            'create': '➕',
            'delete': '🗑️',
            'scan': '🔍',
            'journal': '📓'
        }[item.type] || '•';

        return `<div style="padding: 6px 0; border-bottom: 1px solid var(--border); font-size: 0.8rem;">
            <span>${typeEmoji}</span>
            <span>${item.message}</span>
            <span style="color: var(--text-muted); font-size: 0.7rem; float: right;">${time}</span>
        </div>`;
    }).join('');
}

function addActivityItem(message, type = 'general') {
    activityItems.unshift({
        message,
        type,
        timestamp: new Date().toISOString()
    });
    renderActivityFeed();
}

// =============================================================================
// OPTIONS FEATURES (POLYGON)
// =============================================================================

async function fetchUnusualOptions() {
    try {
        const res = await fetch(`${API_BASE}/options/scan/unusual?limit=10`);
        const data = await res.json();

        if (!data.ok || !data.data || data.data.length === 0) {
            document.getElementById('unusual-options-container').innerHTML =
                '<div style="color: var(--text-muted); font-size: 0.8125rem;">No unusual activity detected</div>';
            return;
        }

        let html = '';
        data.data.slice(0, 5).forEach(item => {
            const signals = item.signals || [];
            const sentiment = signals.find(s => s.type === 'BEARISH_FLOW' || s.type === 'BULLISH_FLOW');
            const sentimentColor = sentiment ?
                (sentiment.type === 'BULLISH_FLOW' ? 'var(--green)' : 'var(--red)') :
                'var(--text-muted)';

            html += `
                <div class="sidebar-item" style="cursor: pointer;" onclick="showOptionsDetail('${item.ticker}')">
                    <div>
                        <div style="font-weight: 600;">${item.ticker}</div>
                        <div style="font-size: 0.7rem; color: ${sentimentColor};">
                            ${item.unusual_contracts} unusual contracts
                        </div>
                    </div>
                    <div style="text-align: right; font-size: 0.75rem; color: var(--text-muted);">
                        ${sentiment ? sentiment.strength : 'moderate'}
                    </div>
                </div>
            `;
        });

        document.getElementById('unusual-options-container').innerHTML = html;
    } catch (e) {
        console.error('Failed to fetch unusual options:', e);
        document.getElementById('unusual-options-container').innerHTML =
            '<div style="color: var(--red); font-size: 0.8125rem;">Failed to load</div>';
    }
}

// Volume Profile - SPY Key Levels
async function fetchVolumeProfile() {
    const container = document.getElementById('volume-profile-container');
    try {
        const res = await fetch(`${API_BASE}/volume-profile/SPY?days=30`);
        const data = await res.json();

        if (!data.ok || data.data.error) {
            container.innerHTML = '<div style="color: var(--text-muted); font-size: 0.8125rem;">Failed to load volume profile</div>';
            return;
        }

        const vp = data.data;
        const current = vp.current_price || 0;
        const poc = vp.poc || 0;
        const vah = vp.vah || 0;
        const val = vp.val || 0;

        // Determine position relative to value area
        let positionColor = 'var(--text-muted)';
        let positionLabel = 'In Range';
        if (current > vah) {
            positionColor = 'var(--green)';
            positionLabel = 'Above VAH';
        } else if (current < val) {
            positionColor = 'var(--red)';
            positionLabel = 'Below VAL';
        } else if (Math.abs(current - poc) < (vah - val) * 0.1) {
            positionColor = 'var(--blue)';
            positionLabel = 'At POC';
        }

        // Build visual range bar
        const rangeSize = vah - val;
        const extendedHigh = vah + rangeSize * 0.3;
        const extendedLow = val - rangeSize * 0.3;
        const totalRange = extendedHigh - extendedLow;

        const pocPct = ((poc - extendedLow) / totalRange) * 100;
        const vahPct = ((vah - extendedLow) / totalRange) * 100;
        const valPct = ((val - extendedLow) / totalRange) * 100;
        const currentPct = Math.min(100, Math.max(0, ((current - extendedLow) / totalRange) * 100));

        let html = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <div style="font-size: 0.85rem; font-weight: 600;">SPY $${current.toFixed(2)}</div>
                <div style="font-size: 0.7rem; color: ${positionColor}; font-weight: 500;">${positionLabel}</div>
            </div>

            <!-- Visual Price Range -->
            <div style="position: relative; height: 32px; background: linear-gradient(90deg, rgba(239,68,68,0.15) 0%, rgba(100,116,139,0.1) 50%, rgba(34,197,94,0.15) 100%); border-radius: 4px; margin-bottom: 8px;">
                <!-- Value Area (70% volume zone) -->
                <div style="position: absolute; left: ${valPct}%; right: ${100-vahPct}%; top: 0; bottom: 0; background: rgba(139, 92, 246, 0.25); border-left: 2px solid rgba(139, 92, 246, 0.6); border-right: 2px solid rgba(139, 92, 246, 0.6);"></div>

                <!-- POC Line -->
                <div style="position: absolute; left: ${pocPct}%; top: 0; bottom: 0; width: 2px; background: #a855f7;" title="POC: $${poc.toFixed(2)}"></div>

                <!-- Current Price Marker -->
                <div style="position: absolute; left: ${currentPct}%; top: 50%; transform: translate(-50%, -50%); width: 12px; height: 12px; background: ${positionColor}; border: 2px solid white; border-radius: 50%; box-shadow: 0 1px 3px rgba(0,0,0,0.3);" title="Current: $${current.toFixed(2)}"></div>
            </div>

            <!-- Key Levels -->
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 4px; font-size: 0.7rem;">
                <div style="text-align: left;">
                    <div style="color: var(--text-muted);">VAL <span class="info-icon" data-tooltip="Value Area Low: Lower bound of the 70% volume zone. Strong support - price below VAL indicates weakness and may rally back."></span></div>
                    <div style="font-weight: 600; color: var(--red);">$${val.toFixed(2)}</div>
                </div>
                <div style="text-align: center;">
                    <div style="color: var(--text-muted);">POC <span class="info-icon" data-tooltip="Point of Control: Price with highest trading volume - the 'fair value' where most activity occurred. Strongest support/resistance level."></span></div>
                    <div style="font-weight: 600; color: #a855f7;">$${poc.toFixed(2)}</div>
                </div>
                <div style="text-align: right;">
                    <div style="color: var(--text-muted);">VAH <span class="info-icon" data-tooltip="Value Area High: Upper bound of the 70% volume zone. Strong resistance - price above VAH indicates strength but may pull back."></span></div>
                    <div style="font-weight: 600; color: var(--green);">$${vah.toFixed(2)}</div>
                </div>
            </div>

            <!-- Analysis -->
            <div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid var(--border); font-size: 0.7rem; color: var(--text-muted);">
                ${vp.analysis || 'Volume profile analysis'}
            </div>
        `;

        container.innerHTML = html;
    } catch (e) {
        console.error('Failed to fetch volume profile:', e);
        container.innerHTML = '<div style="color: var(--red); font-size: 0.8125rem;">Failed to load</div>';
    }
}

function showOptionsDetail(ticker) {
    // Switch to Options tab
    showTab('options');

    // Load options chain for ticker
    document.getElementById('options-ticker-input').value = ticker;
    loadOptionsChain();

    // Also load technical indicators
    document.getElementById('technical-ticker-input').value = ticker;
    loadTechnicalIndicators();
}

// Options flow for Trades tab
let currentFlowTicker = null;

async function showOptionsFlowForTicker(ticker) {
    if (!ticker) {
        document.getElementById('options-flow-container').innerHTML =
            '<div style="color: var(--text-muted); font-size: 0.8125rem;">Select a position to view options flow</div>';
        currentFlowTicker = null;
        return;
    }

    currentFlowTicker = ticker;

    try {
        const res = await fetch(`${API_BASE}/options/flow/${ticker}`);
        const data = await res.json();

        if (!data.ok || data.data.error) {
            document.getElementById('options-flow-container').innerHTML =
                '<div style="color: var(--text-muted); font-size: 0.8125rem;">No options data available</div>';
            return;
        }

        const flow = data.data;
        const sentiment = flow.sentiment || 'neutral';
        const sentimentColor = sentiment === 'bullish' ? 'var(--green)' :
                              sentiment === 'bearish' ? 'var(--red)' :
                              'var(--text-muted)';

        // Calculate percentages for visual bars
        const callVol = flow.total_call_volume || 0;
        const putVol = flow.total_put_volume || 0;
        const totalVol = callVol + putVol;
        const callPct = totalVol > 0 ? (callVol / totalVol * 100) : 50;
        const putPct = totalVol > 0 ? (putVol / totalVol * 100) : 50;

        const callOI = flow.total_call_oi || 0;
        const putOI = flow.total_put_oi || 0;
        const totalOI = callOI + putOI;
        const callOIPct = totalOI > 0 ? (callOI / totalOI * 100) : 50;

        // Sentiment score for gauge (0-100)
        const sentScore = flow.sentiment_score ?? (sentiment === 'bullish' ? 75 : sentiment === 'bearish' ? 25 : 50);
        const gaugeRotation = (sentScore / 100) * 180 - 90; // -90 to 90 degrees

        const html = `
            <!-- Sentiment Hero Section -->
            <div style="text-align: center; padding: 16px 12px; background: linear-gradient(135deg, ${sentiment === 'bullish' ? 'rgba(34, 197, 94, 0.1)' : sentiment === 'bearish' ? 'rgba(239, 68, 68, 0.1)' : 'rgba(100, 116, 139, 0.1)'}, transparent); border-radius: 12px; margin-bottom: 16px;">
                <!-- Sentiment Gauge -->
                <div style="position: relative; width: 100px; height: 55px; margin: 0 auto 8px;">
                    <svg viewBox="0 0 100 55" style="width: 100%; height: 100%;">
                        <!-- Background arc -->
                        <path d="M 10 50 A 40 40 0 0 1 90 50" fill="none" stroke="var(--border)" stroke-width="8" stroke-linecap="round"/>
                        <!-- Colored arc based on sentiment -->
                        <path d="M 10 50 A 40 40 0 0 1 90 50" fill="none" stroke="url(#sentimentGradient)" stroke-width="8" stroke-linecap="round" stroke-dasharray="${sentScore * 1.26} 126"/>
                        <defs>
                            <linearGradient id="sentimentGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                                <stop offset="0%" style="stop-color: var(--red)"/>
                                <stop offset="50%" style="stop-color: var(--yellow)"/>
                                <stop offset="100%" style="stop-color: var(--green)"/>
                            </linearGradient>
                        </defs>
                        <!-- Needle -->
                        <line x1="50" y1="50" x2="50" y2="20" stroke="${sentimentColor}" stroke-width="2" stroke-linecap="round" transform="rotate(${gaugeRotation}, 50, 50)"/>
                        <circle cx="50" cy="50" r="4" fill="${sentimentColor}"/>
                    </svg>
                </div>
                <div style="font-size: 1.5rem; font-weight: 700; color: ${sentimentColor}; text-transform: uppercase; letter-spacing: 1px;">
                    ${sentiment}
                </div>
                <div style="font-size: 0.7rem; color: var(--text-muted); margin-top: 2px;">Score: ${sentScore}/100</div>
            </div>

            <!-- P/C Ratio with Visual Bar -->
            <div style="margin-bottom: 16px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                    <span style="font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px;">P/C Ratio</span>
                    <span style="font-size: 1.1rem; font-weight: 700; color: ${(flow.put_call_ratio || 0) > 1 ? 'var(--red)' : 'var(--green)'};">${flow.put_call_ratio?.toFixed(2) || '--'}</span>
                </div>
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="font-size: 0.65rem; color: var(--green); width: 35px;">Calls</span>
                    <div style="flex: 1; height: 8px; background: var(--bg-hover); border-radius: 4px; overflow: hidden; display: flex;">
                        <div style="width: ${callPct}%; background: linear-gradient(90deg, var(--green), #4ade80); transition: width 0.3s;"></div>
                        <div style="width: ${putPct}%; background: linear-gradient(90deg, #f87171, var(--red)); transition: width 0.3s;"></div>
                    </div>
                    <span style="font-size: 0.65rem; color: var(--red); width: 35px; text-align: right;">Puts</span>
                </div>
            </div>

            <!-- Volume Comparison -->
            <div style="margin-bottom: 16px;">
                <div style="font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px;">Volume</div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
                    <div style="background: rgba(34, 197, 94, 0.1); border: 1px solid rgba(34, 197, 94, 0.2); border-radius: 8px; padding: 10px; text-align: center;">
                        <div style="font-size: 0.65rem; color: var(--green); margin-bottom: 2px;">CALLS</div>
                        <div style="font-size: 1rem; font-weight: 700; color: var(--green);">${formatVolume(callVol)}</div>
                        <div style="font-size: 0.6rem; color: var(--text-muted);">${callPct.toFixed(0)}%</div>
                    </div>
                    <div style="background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.2); border-radius: 8px; padding: 10px; text-align: center;">
                        <div style="font-size: 0.65rem; color: var(--red); margin-bottom: 2px;">PUTS</div>
                        <div style="font-size: 1rem; font-weight: 700; color: var(--red);">${formatVolume(putVol)}</div>
                        <div style="font-size: 0.6rem; color: var(--text-muted);">${putPct.toFixed(0)}%</div>
                    </div>
                </div>
            </div>

            <!-- Open Interest -->
            <div style="margin-bottom: 12px;">
                <div style="font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px;">Open Interest</div>
                <div style="display: flex; align-items: center; gap: 6px; margin-bottom: 4px;">
                    <div style="flex: 1; height: 6px; background: var(--bg-hover); border-radius: 3px; overflow: hidden;">
                        <div style="width: ${callOIPct}%; height: 100%; background: var(--green); border-radius: 3px;"></div>
                    </div>
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 0.7rem;">
                    <span style="color: var(--green);">C: ${formatVolume(callOI)}</span>
                    <span style="color: var(--red);">P: ${formatVolume(putOI)}</span>
                </div>
            </div>

            ${flow.has_unusual_activity ?
                `<div style="margin-top: 12px; padding: 10px; background: linear-gradient(135deg, rgba(251, 191, 36, 0.15), rgba(251, 191, 36, 0.05)); border: 1px solid rgba(251, 191, 36, 0.3); border-radius: 8px; display: flex; align-items: center; gap: 8px;">
                    <span style="font-size: 1.2rem;">⚠️</span>
                    <div>
                        <div style="font-size: 0.75rem; font-weight: 600; color: var(--yellow);">Unusual Activity</div>
                        <div style="font-size: 0.65rem; color: var(--text-muted);">Large volume detected</div>
                    </div>
                </div>` :
                ''}
        `;

        document.getElementById('options-flow-container').innerHTML = html;
    } catch (e) {
        console.error('Failed to fetch options flow:', e);
        document.getElementById('options-flow-container').innerHTML =
            '<div style="color: var(--red); font-size: 0.8125rem;">Failed to load</div>';
    }
}

async function refreshOptionsFlow() {
    if (currentFlowTicker) {
        await showOptionsFlowForTicker(currentFlowTicker);
    }
}

// Options chain loader
async function loadOptionsChain() {
    const ticker = document.getElementById('options-ticker-input').value.trim().toUpperCase();
    if (!ticker) {
        alert('Please enter a ticker symbol');
        return;
    }

    try {
        // Show loading state
        document.getElementById('calls-table-body').innerHTML =
            '<tr><td colspan="7" style="text-align: center; padding: 40px; color: var(--text-muted);">Loading...</td></tr>';
        document.getElementById('puts-table-body').innerHTML =
            '<tr><td colspan="7" style="text-align: center; padding: 40px; color: var(--text-muted);">Loading...</td></tr>';

        // Fetch options chain
        const res = await fetch(`${API_BASE}/options/chain/${ticker}`);
        const data = await res.json();

        if (!data.ok || data.data.error) {
            throw new Error(data.data?.error || 'Failed to load options chain');
        }

        const chain = data.data;

        // Show summary grid
        document.getElementById('options-summary').style.display = 'grid';
        document.getElementById('options-tables').style.display = 'grid';

        // Populate summary
        const summary = chain.summary || {};
        const sentiment = summary.sentiment || 'neutral';
        const sentimentColor = sentiment === 'bullish' ? 'var(--green)' :
                              sentiment === 'bearish' ? 'var(--red)' :
                              'var(--text-muted)';

        document.getElementById('opt-sentiment').textContent = sentiment.toUpperCase();
        document.getElementById('opt-sentiment').style.color = sentimentColor;
        document.getElementById('opt-pc-ratio').textContent = (summary.put_call_volume_ratio || summary.put_call_ratio || 0).toFixed(2);
        document.getElementById('opt-call-vol').textContent = (summary.total_call_volume || 0).toLocaleString();
        document.getElementById('opt-put-vol').textContent = (summary.total_put_volume || 0).toLocaleString();

        // Render calls table
        const calls = chain.calls || [];
        if (calls.length === 0) {
            document.getElementById('calls-table-body').innerHTML =
                '<tr><td colspan="7" style="text-align: center; padding: 40px; color: var(--text-muted);">No call contracts available</td></tr>';
        } else {
            document.getElementById('calls-table-body').innerHTML = calls.slice(0, 50).map(c => {
                const deltaColor = (c.delta || 0) >= 0.5 ? 'var(--green)' : 'var(--text-muted)';
                return `
                    <tr style="border-bottom: 1px solid var(--border);">
                        <td style="padding: 8px; font-weight: 600;">$${c.strike || '--'}</td>
                        <td style="padding: 8px; text-align: right;">$${(c.bid || 0).toFixed(2)}</td>
                        <td style="padding: 8px; text-align: right;">$${(c.ask || 0).toFixed(2)}</td>
                        <td style="padding: 8px; text-align: right;">${(c.volume || 0).toLocaleString()}</td>
                        <td style="padding: 8px; text-align: right;">${(c.open_interest || 0).toLocaleString()}</td>
                        <td style="padding: 8px; text-align: right;">${c.implied_volatility ? (c.implied_volatility * 100).toFixed(1) + '%' : '--'}</td>
                        <td style="padding: 8px; text-align: right; color: ${deltaColor}; font-weight: 600;">${c.delta ? c.delta.toFixed(3) : '--'}</td>
                    </tr>
                `;
            }).join('');
        }

        // Render puts table
        const puts = chain.puts || [];
        if (puts.length === 0) {
            document.getElementById('puts-table-body').innerHTML =
                '<tr><td colspan="7" style="text-align: center; padding: 40px; color: var(--text-muted);">No put contracts available</td></tr>';
        } else {
            document.getElementById('puts-table-body').innerHTML = puts.slice(0, 50).map(p => {
                const deltaColor = (p.delta || 0) <= -0.5 ? 'var(--red)' : 'var(--text-muted)';
                return `
                    <tr style="border-bottom: 1px solid var(--border);">
                        <td style="padding: 8px; font-weight: 600;">$${p.strike || '--'}</td>
                        <td style="padding: 8px; text-align: right;">$${(p.bid || 0).toFixed(2)}</td>
                        <td style="padding: 8px; text-align: right;">$${(p.ask || 0).toFixed(2)}</td>
                        <td style="padding: 8px; text-align: right;">${(p.volume || 0).toLocaleString()}</td>
                        <td style="padding: 8px; text-align: right;">${(p.open_interest || 0).toLocaleString()}</td>
                        <td style="padding: 8px; text-align: right;">${p.implied_volatility ? (p.implied_volatility * 100).toFixed(1) + '%' : '--'}</td>
                        <td style="padding: 8px; text-align: right; color: ${deltaColor}; font-weight: 600;">${p.delta ? p.delta.toFixed(3) : '--'}</td>
                    </tr>
                `;
            }).join('');
        }

    } catch (e) {
        console.error('Failed to load options chain:', e);
        alert('Failed to load options chain: ' + e.message);
        document.getElementById('calls-table-body').innerHTML =
            '<tr><td colspan="7" style="text-align: center; padding: 40px; color: var(--red);">Failed to load</td></tr>';
        document.getElementById('puts-table-body').innerHTML =
            '<tr><td colspan="7" style="text-align: center; padding: 40px; color: var(--red);">Failed to load</td></tr>';
    }
}

// Unified Options Analysis (P/C, GEX, IV + Chart)
let optionsAnalysisTicker = '';
let optionsChartData = { gexByStrike: [], currentPrice: 0 };
let isSyncingExpiry = false; // Prevent infinite sync loops

// Futures contract specs (for display)
const FUTURES_SPECS = {
    '/ES': { name: 'E-mini S&P 500', multiplier: 50 },
    '/NQ': { name: 'E-mini Nasdaq 100', multiplier: 20 },
    '/CL': { name: 'Crude Oil', multiplier: 1000 },
    '/GC': { name: 'Gold', multiplier: 100 },
    '/SI': { name: 'Silver', multiplier: 5000 },
    '/RTY': { name: 'E-mini Russell 2000', multiplier: 50 },
    '/YM': { name: 'E-mini Dow', multiplier: 5 },
    '/MES': { name: 'Micro E-mini S&P', multiplier: 5 },
    '/MNQ': { name: 'Micro E-mini Nasdaq', multiplier: 2 },
};

function isFuturesTicker(ticker) {
    return ticker.startsWith('/') || ticker.toUpperCase() in FUTURES_SPECS;
}

function getFuturesInfo(ticker) {
    const upper = ticker.toUpperCase();
    // Check with and without slash
    if (upper in FUTURES_SPECS) {
        return { isFutures: true, ...FUTURES_SPECS[upper] };
    }
    if (('/' + upper) in FUTURES_SPECS) {
        return { isFutures: true, ...FUTURES_SPECS['/' + upper] };
    }
    if (upper.startsWith('/')) {
        return { isFutures: true, name: upper.slice(1) + ' Futures', multiplier: 50 };
    }
    return { isFutures: false, name: null, multiplier: 100 };
}

// Quick ticker analysis - sets input and triggers analysis
function quickAnalyzeTicker(ticker) {
    document.getElementById('options-ticker-input').value = ticker;
    // Highlight active ticker button
    document.querySelectorAll('.ticker-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.textContent === ticker) btn.classList.add('active');
    });
    loadOptionsAnalysis();
}

// Update sentiment gauge needle position
function updateSentimentGauge(pcRatio, vix) {
    // Calculate sentiment: P/C > 1 = bearish, P/C < 0.7 = bullish
    // VIX > 25 = fear, VIX < 15 = complacent
    let sentiment = 50; // neutral

    if (pcRatio && !isNaN(pcRatio)) {
        if (pcRatio < 0.6) sentiment += 30;
        else if (pcRatio < 0.8) sentiment += 15;
        else if (pcRatio > 1.2) sentiment -= 30;
        else if (pcRatio > 1.0) sentiment -= 15;
    }

    if (vix && !isNaN(vix)) {
        if (vix < 15) sentiment += 10;
        else if (vix > 30) sentiment -= 20;
        else if (vix > 25) sentiment -= 10;
    }

    // Clamp between 0-100
    sentiment = Math.max(0, Math.min(100, sentiment));

    // Convert to rotation angle (-90 to 90 degrees)
    const angle = (sentiment / 100) * 180 - 90;

    const needle = document.getElementById('sentiment-needle');
    if (needle) {
        needle.setAttribute('transform', `rotate(${angle}, 90, 85)`);
    }

    // Update label
    const label = document.getElementById('sentiment-label');
    const desc = document.getElementById('sentiment-description');
    if (label && desc) {
        if (sentiment >= 70) {
            label.textContent = 'BULLISH';
            label.style.color = 'var(--green)';
            desc.textContent = 'Call heavy, low fear';
        } else if (sentiment >= 55) {
            label.textContent = 'LEAN BULLISH';
            label.style.color = 'var(--green-light)';
            desc.textContent = 'Slightly bullish positioning';
        } else if (sentiment <= 30) {
            label.textContent = 'BEARISH';
            label.style.color = 'var(--red)';
            desc.textContent = 'Put heavy, high fear';
        } else if (sentiment <= 45) {
            label.textContent = 'LEAN BEARISH';
            label.style.color = 'var(--red-light)';
            desc.textContent = 'Slightly bearish positioning';
        } else {
            label.textContent = 'NEUTRAL';
            label.style.color = 'var(--yellow)';
            desc.textContent = 'Balanced positioning';
        }
    }
}

async function loadOptionsAnalysis() {
    const ticker = document.getElementById('options-ticker-input').value.trim().toUpperCase();
    if (!ticker) {
        alert('Please enter a ticker symbol');
        return;
    }

    optionsAnalysisTicker = ticker;

    const container = document.getElementById('options-analysis-container');
    container.style.display = 'block';

    // Show ticker with futures badge if applicable
    const futuresInfo = getFuturesInfo(ticker);
    const tickerEl = document.getElementById('oa-ticker');
    if (futuresInfo.isFutures) {
        tickerEl.innerHTML = `${ticker} <span style="font-size: 0.65rem; padding: 2px 6px; background: var(--orange); color: white; border-radius: 4px; margin-left: 4px;">FUTURES</span>
            <span style="font-size: 0.65rem; color: var(--text-muted); margin-left: 4px;">${futuresInfo.name} (${futuresInfo.multiplier}x)</span>`;
    } else {
        tickerEl.textContent = ticker;
    }
    document.getElementById('oa-interpretation').textContent = 'Loading analysis...';

    // Load expirations first
    const expirySelect = document.getElementById('oa-expiry-select');
    expirySelect.innerHTML = '<option value="">Loading...</option>';

    try {
        // Use query param for futures (path doesn't work with /)
        const expUrl = ticker.startsWith('/')
            ? `${API_BASE}/options/expirations?ticker=${encodeURIComponent(ticker)}`
            : `${API_BASE}/options/expirations/${ticker}`;
        const expRes = await fetch(expUrl);
        const expData = await expRes.json();

        if (expData.ok && expData.data && expData.data.expirations) {
            const expirations = expData.data.expirations;
            expirySelect.innerHTML = formatExpirationOptions(expirations, 0);

            // Load data for nearest expiration
            await loadOptionsForExpiry();
        } else {
            expirySelect.innerHTML = '<option value="">No expirations</option>';
            throw new Error('Could not load expirations');
        }
    } catch (e) {
        console.error('Failed to load options analysis:', e);
        document.getElementById('oa-interpretation').textContent = 'Error: ' + e.message;
        document.getElementById('oa-sentiment').textContent = 'ERROR';
        document.getElementById('oa-sentiment').style.background = 'rgba(239,68,68,0.2)';
        document.getElementById('oa-sentiment').style.color = 'var(--red)';
    }
}

// Quick-select expiration by approximate days out
function selectExpiryByDays(targetDays) {
    // Check if a ticker is loaded
    if (!optionsAnalysisTicker) {
        if (window.toast) {
            window.toast.warning('Please analyze a ticker first');
        } else {
            alert('Please analyze a ticker first');
        }
        return;
    }

    const expirySelect = document.getElementById('oa-expiry-select');

    // Get all options including those inside optgroups
    const options = Array.from(expirySelect.querySelectorAll('option')).filter(o => o.value);

    if (options.length === 0) {
        if (window.toast) {
            window.toast.warning('No expirations available');
        } else {
            alert('No expirations available');
        }
        return;
    }

    const today = new Date();
    today.setHours(0, 0, 0, 0);

    let bestOption = options[0];
    let bestDiff = Infinity;

    options.forEach(opt => {
        const expDate = new Date(opt.value + 'T00:00:00');
        const daysOut = Math.round((expDate - today) / (1000 * 60 * 60 * 24));
        const diff = Math.abs(daysOut - targetDays);

        if (diff < bestDiff) {
            bestDiff = diff;
            bestOption = opt;
        }
    });

    expirySelect.value = bestOption.value;
    loadOptionsForExpiry();

    // Visual feedback - briefly highlight the selected button
    const buttons = document.querySelectorAll('[onclick^="selectExpiryByDays"]');
    buttons.forEach(btn => btn.style.background = '');
    event.target.style.background = 'var(--blue-bg)';
    setTimeout(() => { event.target.style.background = ''; }, 500);
}

async function loadOptionsForExpiry() {
    const ticker = optionsAnalysisTicker;
    const expiry = document.getElementById('oa-expiry-select').value;

    if (!ticker) return;

    // Sync expirations when viewing SPY - ensures consistency between hero zone and analysis panel
    if (ticker === 'SPY' && expiry && !isSyncingExpiry) {
        const marketExpirySelect = document.getElementById('market-sentiment-expiry');
        if (marketExpirySelect && marketExpirySelect.value !== expiry) {
            // Check if this expiry exists in market sentiment dropdown
            const options = Array.from(marketExpirySelect.options).map(o => o.value);
            if (options.includes(expiry)) {
                isSyncingExpiry = true;
                marketExpirySelect.value = expiry;
                loadMarketSentimentForExpiry().finally(() => { isSyncingExpiry = false; });
            }
        }
    }

    try {
        // Build URLs - use query params for futures (path doesn't work with /)
        const isFutures = ticker.startsWith('/');
        const tickerParam = encodeURIComponent(ticker);
        const expiryParam = expiry ? `${isFutures ? '&' : '?'}expiration=${expiry}` : '';

        const sentimentUrl = isFutures ? `${API_BASE}/options/sentiment?ticker=${tickerParam}` : `${API_BASE}/options/sentiment/${ticker}`;
        const flowUrl = isFutures ? `${API_BASE}/options/flow?ticker=${tickerParam}` : `${API_BASE}/options/flow/${ticker}`;
        const gexUrl = isFutures ? `${API_BASE}/options/gex?ticker=${tickerParam}${expiryParam}` : `${API_BASE}/options/gex/${ticker}${expiry ? '?expiration=' + expiry : ''}`;

        // Fetch all data in parallel (GEX endpoint now provides OI and DTE data)
        const [sentimentRes, flowRes, gexRes] = await Promise.all([
            fetch(sentimentUrl),
            fetch(flowUrl),
            fetch(gexUrl)
        ]);

        const sentimentData = await sentimentRes.json();
        const flowData = await flowRes.json();
        const gexData = await gexRes.json();

        const sentiment = sentimentData.data || {};
        const flow = flowData.data || {};
        const gex = gexData.data || {};

        // P/C Ratio (calculate from GEX endpoint OI data)
        const callOI = gex.total_call_oi || 0;
        const putOI = gex.total_put_oi || 0;
        const pcRatio = callOI > 0 ? (putOI / callOI) : (flow.put_call_ratio || 0);
        document.getElementById('oa-pc-ratio').textContent = pcRatio.toFixed(2);
        let pcLabel = 'Neutral';
        let pcColor = 'var(--text)';
        if (pcRatio < 0.7) { pcLabel = 'Bullish'; pcColor = 'var(--green)'; }
        else if (pcRatio > 1.0) { pcLabel = 'Bearish'; pcColor = 'var(--red)'; }
        document.getElementById('oa-pc-label').textContent = pcLabel;
        document.getElementById('oa-pc-label').style.color = pcColor;
        document.getElementById('oa-pc-ratio').style.color = pcColor;

        // GEX (from dedicated GEX endpoint with real gamma calculations - no fallback to ensure consistency)
        let gexValue = gex.total_gex || 0;
        if (typeof gexValue === 'object') gexValue = gexValue.total || 0;
        let gexDisplay = Math.abs(gexValue) >= 1e9 ? `$${(gexValue / 1e9).toFixed(1)}B` :
                         Math.abs(gexValue) >= 1e6 ? `$${(gexValue / 1e6).toFixed(1)}M` :
                         `$${(gexValue / 1e3).toFixed(0)}K`;
        document.getElementById('oa-gex').textContent = gexDisplay;
        const gexLabel = gexValue > 0 ? 'Stabilizing' : gexValue < 0 ? 'Volatile' : 'Neutral';
        const gexColor = gexValue > 0 ? 'var(--green)' : gexValue < 0 ? 'var(--red)' : 'var(--text)';
        document.getElementById('oa-gex-label').textContent = gexLabel;
        document.getElementById('oa-gex-label').style.color = gexColor;
        document.getElementById('oa-gex').style.color = gexColor;

        // IV Rank
        const ivRank = sentiment.iv_rank || 0;
        document.getElementById('oa-iv-rank').textContent = `${ivRank.toFixed(0)}%`;
        let ivLabel = 'Normal', ivColor = 'var(--text)';
        if (ivRank > 50) { ivLabel = 'High (Sell)'; ivColor = 'var(--orange)'; }
        else if (ivRank < 20) { ivLabel = 'Low (Buy)'; ivColor = 'var(--green)'; }
        document.getElementById('oa-iv-label').textContent = ivLabel;
        document.getElementById('oa-iv-label').style.color = ivColor;

        // Current Price (from GEX endpoint)
        const currentPrice = gex.current_price || flow.current_price || sentiment.current_price || 0;
        document.getElementById('oa-current-price').textContent = currentPrice > 0 ? `$${currentPrice.toFixed(2)}` : '--';

        // DTE (from GEX endpoint)
        const dte = gex.days_to_expiry || 0;
        const dteText = dte === 0 ? '0DTE' : dte === 1 ? '1 day' : `${dte} days`;
        document.getElementById('oa-dte').textContent = dteText;
        document.getElementById('oa-dte').style.color = dte <= 2 ? 'var(--red)' : dte <= 5 ? 'var(--yellow)' : 'var(--text-muted)';

        // Call/Put OI (from GEX endpoint)
        document.getElementById('oa-call-oi').textContent = callOI.toLocaleString();
        document.getElementById('oa-put-oi').textContent = putOI.toLocaleString();

        // Expiry display (from GEX endpoint)
        if (gex.expiration) {
            const expDate = new Date(gex.expiration + 'T00:00:00');
            document.getElementById('oa-expiry-display').textContent = expDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        }

        // Overall Sentiment Badge
        const overallSentiment = pcRatio < 0.7 && gexValue > 0 ? 'bullish' :
                                pcRatio > 1.0 && gexValue < 0 ? 'bearish' : 'neutral';
        const sentBadge = document.getElementById('oa-sentiment');
        sentBadge.textContent = overallSentiment.toUpperCase();
        sentBadge.style.background = overallSentiment === 'bullish' ? 'rgba(34,197,94,0.2)' :
                                     overallSentiment === 'bearish' ? 'rgba(239,68,68,0.2)' : 'rgba(100,116,139,0.2)';
        sentBadge.style.color = overallSentiment === 'bullish' ? 'var(--green)' :
                                overallSentiment === 'bearish' ? 'var(--red)' : 'var(--text-muted)';

        // Interpretation (GEX-focused)
        let interpretation = '';
        if (pcRatio < 0.7 && gexValue > 0) {
            interpretation = `📈 Bullish: Low P/C (${pcRatio.toFixed(2)}) + Positive GEX dampens selloffs.`;
        } else if (pcRatio > 1.0 && gexValue < 0) {
            interpretation = `📉 Bearish: High P/C (${pcRatio.toFixed(2)}) + Negative GEX amplifies moves.`;
        } else if (gexValue < 0) {
            interpretation = `⚠️ Volatile: Negative GEX (${gexDisplay}) = larger swings.`;
        } else {
            interpretation = `⚖️ Neutral: P/C ${pcRatio.toFixed(2)}, GEX ${gexDisplay}.`;
        }
        if (ivRank > 50) interpretation += ` High IV (${ivRank.toFixed(0)}%) favors selling.`;
        else if (ivRank < 20) interpretation += ` Low IV (${ivRank.toFixed(0)}%) = cheap options.`;

        // Add futures context if applicable
        const futuresInfo = getFuturesInfo(ticker);
        if (futuresInfo.isFutures) {
            interpretation = `🔶 ${futuresInfo.name} Options (${futuresInfo.multiplier}x). ` + interpretation;
        }

        document.getElementById('oa-interpretation').textContent = interpretation;

        // Store chart data
        optionsChartData.currentPrice = currentPrice;

        // Store GEX data
        optionsChartData.gexByStrike = (gex.gex_by_strike || []).map(s => ({
            strike: s.strike,
            callGex: s.call_gex || 0,
            putGex: s.put_gex || 0,
            netGex: s.net_gex || 0
        }));

        console.log('✅ Options analysis loaded for', ticker, gex.expiration);

        // Load GEX Dashboard after options analysis
        loadGexDashboard();

        // Load Ratio Spread Conditions after options analysis
        loadRatioSpreadScore();

        // Load Options Visualization chart after other data loads
        loadOptionsViz(ticker);

    } catch (e) {
        console.error('Options analysis error:', e);
        document.getElementById('oa-interpretation').textContent = 'Error: ' + e.message;
    }
}

// GEX Price Ladder - Visual representation of key GEX levels
function renderGexPriceLadder(levelsData, currentPrice) {
    if (!levelsData || !currentPrice) {
        return '<div style="text-align: center; color: var(--text-muted); padding: 20px;">No price ladder data available</div>';
    }

    const callWall = levelsData.call_wall;
    const putWall = levelsData.put_wall;
    const callWallGex = levelsData.call_wall_gex_millions || 0;
    const putWallGex = levelsData.put_wall_gex_millions || 0;
    const gammaFlip = levelsData.gamma_flip;
    const magnetZones = levelsData.magnet_zones || [];
    const accelZones = levelsData.acceleration_zones || [];

    // Calculate distance percentages
    const calcDist = (price) => {
        if (!price || !currentPrice) return '';
        const dist = ((price - currentPrice) / currentPrice * 100).toFixed(1);
        return dist > 0 ? `+${dist}%` : `${dist}%`;
    };

    // Calculate bar width (max 100%)
    const maxGex = Math.max(Math.abs(callWallGex), Math.abs(putWallGex), 1);
    const calcBarWidth = (gex) => Math.min(Math.abs(gex) / maxGex * 100, 100);

    // Build levels array for sorting
    const levels = [];

    if (callWall) {
        levels.push({
            type: 'call_wall',
            label: 'CALL WALL',
            price: callWall,
            gex: callWallGex,
            color: 'var(--red)',
            icon: 'resistance'
        });
    }

    if (gammaFlip && gammaFlip !== callWall && gammaFlip !== putWall) {
        levels.push({
            type: 'gamma_flip',
            label: 'GAMMA FLIP',
            price: gammaFlip,
            gex: 0,
            color: 'var(--orange)',
            icon: 'flip'
        });
    }

    // Add magnet zones
    magnetZones.forEach((zone, idx) => {
        if (zone !== callWall && zone !== putWall && zone !== gammaFlip) {
            levels.push({
                type: 'magnet',
                label: `MAGNET ${idx + 1}`,
                price: zone,
                gex: null,
                color: 'var(--blue)',
                icon: 'magnet'
            });
        }
    });

    // Add acceleration zones
    accelZones.forEach((zone, idx) => {
        if (zone !== callWall && zone !== putWall && zone !== gammaFlip) {
            levels.push({
                type: 'accel',
                label: `ACCEL ${idx + 1}`,
                price: zone,
                gex: null,
                color: 'var(--purple)',
                icon: 'accel'
            });
        }
    });

    if (putWall) {
        levels.push({
            type: 'put_wall',
            label: 'PUT WALL',
            price: putWall,
            gex: putWallGex,
            color: 'var(--green)',
            icon: 'support'
        });
    }

    // Sort levels by price descending (highest at top)
    levels.sort((a, b) => b.price - a.price);

    // Find where current price fits
    let currentInserted = false;
    const sortedWithCurrent = [];

    for (const level of levels) {
        if (!currentInserted && level.price < currentPrice) {
            sortedWithCurrent.push({ type: 'current', price: currentPrice });
            currentInserted = true;
        }
        sortedWithCurrent.push(level);
    }
    if (!currentInserted) {
        sortedWithCurrent.push({ type: 'current', price: currentPrice });
    }

    // Build HTML
    let html = `
        <div style="background: var(--bg-hover); border-radius: 8px; padding: 16px;">
            <div style="font-size: 0.75rem; font-weight: 600; color: var(--orange); margin-bottom: 12px; display: flex; align-items: center; gap: 6px;">
                <span>GEX PRICE LADDER</span>
                <span class="info-icon" data-tooltip="Visual price ladder showing key GEX levels. Call Wall = resistance (red), Put Wall = support (green), Gamma Flip = volatility transition zone.">i</span>
            </div>
            <div style="display: flex; flex-direction: column; gap: 0;">
    `;

    sortedWithCurrent.forEach((level, idx) => {
        const isFirst = idx === 0;
        const isLast = idx === sortedWithCurrent.length - 1;

        if (level.type === 'current') {
            // Current price marker
            html += `
                <div style="display: flex; align-items: center; padding: 10px 0; position: relative;">
                    <div style="width: 120px; text-align: right; padding-right: 12px;">
                        <span style="font-size: 0.7rem; font-weight: 600; color: var(--text);">CURRENT</span>
                    </div>
                    <div style="flex: 0 0 20px; display: flex; justify-content: center; position: relative;">
                        <div style="width: 12px; height: 12px; background: var(--text); border-radius: 50%; border: 2px solid var(--bg); z-index: 2;"></div>
                        ${!isFirst ? '<div style="position: absolute; top: -10px; left: 50%; transform: translateX(-50%); width: 2px; height: 10px; background: var(--border);"></div>' : ''}
                        ${!isLast ? '<div style="position: absolute; bottom: -10px; left: 50%; transform: translateX(-50%); width: 2px; height: 10px; background: var(--border);"></div>' : ''}
                    </div>
                    <div style="flex: 1; padding-left: 12px; display: flex; align-items: center; gap: 12px;">
                        <span style="font-size: 1.1rem; font-weight: 700; color: var(--text);">$${currentPrice.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</span>
                        <span style="font-size: 0.75rem; padding: 2px 8px; background: rgba(255,255,255,0.1); border-radius: 4px; color: var(--text-muted);">NOW</span>
                    </div>
                </div>
            `;
        } else {
            // Level row
            const dist = calcDist(level.price);
            const barWidth = level.gex !== null ? calcBarWidth(level.gex) : 0;
            const barColor = level.gex >= 0 ? 'var(--green)' : 'var(--red)';
            const gexText = level.gex !== null ? `${level.gex >= 0 ? '+' : ''}${level.gex.toFixed(1)}M GEX` : '';

            // Determine connector lines
            const showTopLine = !isFirst;
            const showBottomLine = !isLast;

            html += `
                <div style="display: flex; align-items: center; padding: 8px 0; position: relative;">
                    <div style="width: 120px; text-align: right; padding-right: 12px;">
                        <span style="font-size: 0.65rem; font-weight: 600; color: ${level.color}; letter-spacing: 0.5px;">${level.label}</span>
                    </div>
                    <div style="flex: 0 0 20px; display: flex; justify-content: center; position: relative;">
                        <div style="width: 8px; height: 8px; background: ${level.color}; border-radius: 2px;"></div>
                        ${showTopLine ? '<div style="position: absolute; top: -8px; left: 50%; transform: translateX(-50%); width: 2px; height: 8px; background: var(--border);"></div>' : ''}
                        ${showBottomLine ? '<div style="position: absolute; bottom: -8px; left: 50%; transform: translateX(-50%); width: 2px; height: 8px; background: var(--border);"></div>' : ''}
                    </div>
                    <div style="flex: 1; padding-left: 12px;">
                        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
                            <span style="font-size: 0.95rem; font-weight: 600; color: ${level.color};">$${level.price.toLocaleString(undefined, {minimumFractionDigits: 0, maximumFractionDigits: 0})}</span>
                            <span style="font-size: 0.7rem; color: var(--text-muted);">${dist}</span>
                        </div>
                        ${level.gex !== null ? `
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <div style="flex: 1; max-width: 150px; height: 6px; background: var(--bg); border-radius: 3px; overflow: hidden;">
                                <div style="width: ${barWidth}%; height: 100%; background: ${barColor}; border-radius: 3px;"></div>
                            </div>
                            <span style="font-size: 0.65rem; color: var(--text-muted);">${gexText}</span>
                        </div>
                        ` : ''}
                    </div>
                </div>
            `;
        }
    });

    html += `
            </div>
        </div>
    `;

    return html;
}

// GEX Key Levels Table - Detailed view of all key GEX strikes
function renderGexLevelsTable(keyLevels, currentPrice) {
    if (!keyLevels || !Array.isArray(keyLevels) || keyLevels.length === 0 || !currentPrice) {
        return '<div style="text-align: center; color: var(--text-muted); padding: 12px; font-size: 0.7rem;">No key levels data available</div>';
    }

    // Sort levels by absolute distance from current price (nearest first)
    const sortedLevels = [...keyLevels].sort((a, b) => {
        const distA = Math.abs(a.distance_pct || ((a.strike - currentPrice) / currentPrice * 100));
        const distB = Math.abs(b.distance_pct || ((b.strike - currentPrice) / currentPrice * 100));
        return distA - distB;
    });

    // Limit to 10 levels
    const displayLevels = sortedLevels.slice(0, 10);

    // Build table HTML with compact styling
    let html = `
        <table style="width: 100%; border-collapse: collapse; font-size: 0.7rem;">
            <thead>
                <tr style="background: var(--bg); border-bottom: 1px solid var(--border);">
                    <th style="padding: 6px 8px; text-align: left; font-weight: 600; color: var(--text-muted);">Strike</th>
                    <th style="padding: 6px 8px; text-align: right; font-weight: 600; color: var(--text-muted);">GEX ($M)</th>
                    <th style="padding: 6px 8px; text-align: center; font-weight: 600; color: var(--text-muted);">Type</th>
                    <th style="padding: 6px 8px; text-align: center; font-weight: 600; color: var(--text-muted);">Role</th>
                    <th style="padding: 6px 8px; text-align: right; font-weight: 600; color: var(--text-muted);">Distance</th>
                    <th style="padding: 6px 8px; text-align: right; font-weight: 600; color: var(--text-muted);">Call OI</th>
                    <th style="padding: 6px 8px; text-align: right; font-weight: 600; color: var(--text-muted);">Put OI</th>
                </tr>
            </thead>
            <tbody>
    `;

    displayLevels.forEach((level, idx) => {
        const strike = level.strike || 0;
        const netGex = level.net_gex || 0;
        const gexMillions = level.gex_millions !== undefined ? level.gex_millions : (netGex / 1000000);
        const type = (level.type || 'unknown').toLowerCase();
        const role = (level.role || 'neutral').toLowerCase();
        const distancePct = level.distance_pct !== undefined ? level.distance_pct : ((strike - currentPrice) / currentPrice * 100);
        const callOi = level.call_oi || 0;
        const putOi = level.put_oi || 0;

        // GEX color: positive = green, negative = red
        const gexColor = gexMillions >= 0 ? 'var(--green)' : 'var(--red)';
        const gexSign = gexMillions >= 0 ? '+' : '';

        // Type badge: magnet = blue, acceleration = orange/yellow
        let typeBadgeBg, typeBadgeColor, typeLabel;
        if (type === 'magnet' || type === 'high_gamma') {
            typeBadgeBg = 'var(--blue-bg)';
            typeBadgeColor = 'var(--blue)';
            typeLabel = 'Magnet';
        } else if (type === 'acceleration' || type === 'accel' || type === 'low_gamma') {
            typeBadgeBg = 'var(--yellow-bg)';
            typeBadgeColor = 'var(--yellow)';
            typeLabel = 'Accel';
        } else {
            typeBadgeBg = 'var(--bg)';
            typeBadgeColor = 'var(--text-muted)';
            typeLabel = type.charAt(0).toUpperCase() + type.slice(1);
        }

        // Role color: support = green, resistance = red
        let roleColor;
        if (role === 'support') {
            roleColor = 'var(--green)';
        } else if (role === 'resistance') {
            roleColor = 'var(--red)';
        } else {
            roleColor = 'var(--text-muted)';
        }
        const roleLabel = role.charAt(0).toUpperCase() + role.slice(1);

        // Distance formatting
        const distSign = distancePct >= 0 ? '+' : '';
        const distColor = distancePct >= 0 ? 'var(--text-muted)' : 'var(--text-muted)';

        // Alternating row background
        const rowBg = idx % 2 === 0 ? 'var(--bg-hover)' : 'transparent';

        html += `
            <tr style="background: ${rowBg}; border-bottom: 1px solid var(--border);">
                <td style="padding: 6px 8px; font-weight: 600; color: var(--text);">$${strike.toLocaleString()}</td>
                <td style="padding: 6px 8px; text-align: right; font-weight: 600; color: ${gexColor};">${gexSign}${gexMillions.toFixed(1)}M</td>
                <td style="padding: 6px 8px; text-align: center;">
                    <span style="padding: 2px 6px; border-radius: 4px; background: ${typeBadgeBg}; color: ${typeBadgeColor}; font-weight: 500; font-size: 0.65rem;">${typeLabel}</span>
                </td>
                <td style="padding: 6px 8px; text-align: center; color: ${roleColor}; font-weight: 500;">${roleLabel}</td>
                <td style="padding: 6px 8px; text-align: right; color: ${distColor};">${distSign}${distancePct.toFixed(1)}%</td>
                <td style="padding: 6px 8px; text-align: right; color: var(--text-muted);">${callOi.toLocaleString()}</td>
                <td style="padding: 6px 8px; text-align: right; color: var(--text-muted);">${putOi.toLocaleString()}</td>
            </tr>
        `;
    });

    html += `
            </tbody>
        </table>
    `;

    return html;
}

// Toggle GEX Levels Table visibility
function toggleGexLevelsTable() {
    const tableBody = document.getElementById('gex-levels-table-body');
    const toggleIcon = document.getElementById('gex-levels-toggle-icon');
    const header = document.getElementById('gex-levels-table-header');

    if (tableBody.style.display === 'none') {
        tableBody.style.display = 'block';
        toggleIcon.style.transform = 'rotate(90deg)';
        header.style.borderRadius = '6px 6px 0 0';
    } else {
        tableBody.style.display = 'none';
        toggleIcon.style.transform = 'rotate(0deg)';
        header.style.borderRadius = '6px';
    }
}

// GEX Dashboard - Advanced gamma exposure analysis
async function loadGexDashboard() {
    const ticker = optionsAnalysisTicker;
    if (!ticker) return;

    const expiry = document.getElementById('oa-expiry-select').value;
    const container = document.getElementById('gex-dashboard-container');
    container.style.display = 'block';
    document.getElementById('gex-ticker').textContent = ticker;

    // Reset all fields
    const resetFields = ['gex-regime-badge', 'gex-regime-confidence', 'gex-regime-strategy',
        'gex-regime-recommendation', 'combined-regime-badge', 'combined-risk-level',
        'combined-position-size', 'combined-recommendation', 'gex-call-wall', 'gex-put-wall',
        'gex-gamma-flip', 'gex-pc-zscore', 'gex-pc-sentiment', 'gex-magnet-zones',
        'gex-accel-zones', 'gex-signal-badge', 'gex-signal-note', 'gex-interpretation'];
    resetFields.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.textContent = 'Loading...';
    });

    try {
        // Fetch all GEX data in parallel
        // Use query params for futures (path params don't work with /)
        const isFutures = ticker.startsWith('/');
        const expiryParam = expiry ? `&expiration=${expiry}` : '';
        const [regimeRes, levelsRes, combinedRes] = await Promise.all([
            fetch(isFutures
                ? `${API_BASE}/options/gex-regime?ticker=${encodeURIComponent(ticker)}${expiryParam}`
                : `${API_BASE}/options/gex-regime/${ticker}${expiry ? '?expiration=' + expiry : ''}`),
            fetch(isFutures
                ? `${API_BASE}/options/gex-levels?ticker=${encodeURIComponent(ticker)}${expiryParam}`
                : `${API_BASE}/options/gex-levels/${ticker}${expiry ? '?expiration=' + expiry : ''}`),
            fetch(isFutures
                ? `${API_BASE}/options/combined-regime?ticker=${encodeURIComponent(ticker)}${expiryParam}`
                : `${API_BASE}/options/combined-regime/${ticker}${expiry ? '?expiration=' + expiry : ''}`)
        ]);

        const regimeData = await regimeRes.json();
        const levelsData = await levelsRes.json();
        const combinedData = await combinedRes.json();

        // Update Volatility Regime
        if (regimeData.ok && regimeData.data) {
            const r = regimeData.data;
            const regimeBadge = document.getElementById('gex-regime-badge');
            regimeBadge.textContent = (r.regime || '--').toUpperCase();

            // Color based on regime
            if (r.regime === 'pinned') {
                regimeBadge.style.background = 'rgba(34, 197, 94, 0.2)';
                regimeBadge.style.color = 'var(--green)';
            } else if (r.regime === 'volatile') {
                regimeBadge.style.background = 'rgba(239, 68, 68, 0.2)';
                regimeBadge.style.color = 'var(--red)';
            } else {
                regimeBadge.style.background = 'rgba(251, 191, 36, 0.2)';
                regimeBadge.style.color = 'var(--orange)';
            }

            document.getElementById('gex-regime-confidence').textContent =
                r.confidence ? `${(r.confidence * 100).toFixed(0)}%` : '--';
            document.getElementById('gex-regime-strategy').textContent =
                r.strategy_bias === 'mean_revert' ? 'Mean Revert' :
                r.strategy_bias === 'trend_follow' ? 'Trend Follow' : r.strategy_bias || '--';
            document.getElementById('gex-regime-recommendation').textContent =
                r.recommendation || '--';
        }

        // Update Combined Regime
        if (combinedData.ok && combinedData.data) {
            const c = combinedData.data;
            const combinedBadge = document.getElementById('combined-regime-badge');
            combinedBadge.textContent = (c.combined_regime || '--').toUpperCase().replace('_', ' ');

            // Color based on regime
            const regimeColors = {
                'opportunity': { bg: 'rgba(34, 197, 94, 0.2)', color: 'var(--green)' },
                'melt_up': { bg: 'rgba(59, 130, 246, 0.2)', color: 'var(--blue)' },
                'high_risk': { bg: 'rgba(251, 191, 36, 0.2)', color: 'var(--orange)' },
                'danger': { bg: 'rgba(239, 68, 68, 0.2)', color: 'var(--red)' }
            };
            const colors = regimeColors[c.combined_regime] || { bg: 'var(--bg)', color: 'var(--text-muted)' };
            combinedBadge.style.background = colors.bg;
            combinedBadge.style.color = colors.color;

            // Risk level with color
            const riskEl = document.getElementById('combined-risk-level');
            riskEl.textContent = c.risk_level || '--';
            if (c.risk_level === 'low') riskEl.style.color = 'var(--green)';
            else if (c.risk_level === 'medium') riskEl.style.color = 'var(--orange)';
            else if (c.risk_level === 'high' || c.risk_level === 'extreme') riskEl.style.color = 'var(--red)';
            else riskEl.style.color = 'var(--text)';

            document.getElementById('combined-position-size').textContent =
                c.position_sizing ? `${(c.position_sizing * 100).toFixed(0)}%` : '--';
            document.getElementById('combined-recommendation').textContent =
                c.recommendation || '--';

            // P/C Z-score from combined data (flat fields: pc_zscore, pc_sentiment)
            const zscore = c.pc_zscore;
            const zscoreEl = document.getElementById('gex-pc-zscore');
            zscoreEl.textContent = zscore !== undefined ? zscore.toFixed(2) : '--';
            if (zscore > 1) zscoreEl.style.color = 'var(--red)';
            else if (zscore < -1) zscoreEl.style.color = 'var(--green)';
            else zscoreEl.style.color = 'var(--text)';

            const sentiment = c.pc_sentiment;
            const sentimentEl = document.getElementById('gex-pc-sentiment');
            sentimentEl.textContent = sentiment || '--';
            if (sentiment === 'fear' || (sentiment && sentiment.includes('fear'))) {
                sentimentEl.style.color = 'var(--red)';
            } else if (sentiment === 'complacency' || (sentiment && sentiment.includes('complacency'))) {
                sentimentEl.style.color = 'var(--green)';
            } else {
                sentimentEl.style.color = 'var(--text-muted)';
            }
        }

        // Update GEX Levels
        if (levelsData.ok && levelsData.data) {
            const l = levelsData.data;
            const currentPrice = l.current_price || 0;

            // Call Wall
            const callWall = l.call_wall;
            document.getElementById('gex-call-wall').textContent =
                callWall ? `$${callWall.toFixed(2)}` : '--';
            if (callWall && currentPrice) {
                const dist = ((callWall - currentPrice) / currentPrice * 100).toFixed(1);
                document.getElementById('gex-call-wall-dist').textContent = `${dist > 0 ? '+' : ''}${dist}% from price`;
            }

            // Put Wall
            const putWall = l.put_wall;
            document.getElementById('gex-put-wall').textContent =
                putWall ? `$${putWall.toFixed(2)}` : '--';
            if (putWall && currentPrice) {
                const dist = ((putWall - currentPrice) / currentPrice * 100).toFixed(1);
                document.getElementById('gex-put-wall-dist').textContent = `${dist > 0 ? '+' : ''}${dist}% from price`;
            }

            // Gamma Flip
            const gammaFlip = l.gamma_flip;
            document.getElementById('gex-gamma-flip').textContent =
                gammaFlip ? `$${gammaFlip.toFixed(2)}` : '--';

            // Magnet zones
            const magnets = l.magnet_zones || [];
            document.getElementById('gex-magnet-zones').textContent =
                magnets.length > 0 ? magnets.map(z => `$${z.toFixed(0)}`).join(', ') : 'None';

            // Acceleration zones
            const accels = l.acceleration_zones || [];
            document.getElementById('gex-accel-zones').textContent =
                accels.length > 0 ? accels.map(z => `$${z.toFixed(0)}`).join(', ') : 'None';

            // Trading signal derived from GEX levels
            const signalBadge = document.getElementById('gex-signal-badge');
            let signal = 'neutral';
            let signalNote = l.interpretation || '--';

            // Derive signal from price position relative to walls
            if (callWall && putWall && currentPrice) {
                const distToCall = ((callWall - currentPrice) / currentPrice) * 100;
                const distToPut = ((currentPrice - putWall) / currentPrice) * 100;

                if (distToPut < 2) {
                    signal = 'bullish';
                    signalNote = `Price near put wall support at $${putWall.toFixed(0)}`;
                } else if (distToCall < 2) {
                    signal = 'bearish';
                    signalNote = `Price near call wall resistance at $${callWall.toFixed(0)}`;
                } else if (distToCall < distToPut) {
                    signal = 'bearish';
                    signalNote = `Closer to call wall resistance ($${callWall.toFixed(0)})`;
                } else {
                    signal = 'bullish';
                    signalNote = `Closer to put wall support ($${putWall.toFixed(0)})`;
                }
            }

            signalBadge.textContent = signal.toUpperCase();
            if (signal === 'bullish') {
                signalBadge.style.background = 'rgba(34, 197, 94, 0.2)';
                signalBadge.style.color = 'var(--green)';
            } else if (signal === 'bearish') {
                signalBadge.style.background = 'rgba(239, 68, 68, 0.2)';
                signalBadge.style.color = 'var(--red)';
            } else {
                signalBadge.style.background = 'var(--bg)';
                signalBadge.style.color = 'var(--text-muted)';
            }

            document.getElementById('gex-signal-note').textContent = signalNote;

            // Render GEX Price Ladder
            const priceLadderContainer = document.getElementById('gex-price-ladder-container');
            if (priceLadderContainer) {
                priceLadderContainer.innerHTML = renderGexPriceLadder(l, currentPrice);
            }

            // Render GEX Key Levels Table
            const keyLevels = l.key_levels || [];
            const levelsTableContainer = document.getElementById('gex-levels-table-container');
            const levelsTableBody = document.getElementById('gex-levels-table-body');
            const levelsCount = document.getElementById('gex-levels-count');

            if (levelsTableContainer && levelsTableBody) {
                if (keyLevels.length > 0) {
                    levelsTableContainer.style.display = 'block';
                    levelsTableBody.innerHTML = renderGexLevelsTable(keyLevels, currentPrice);
                    if (levelsCount) {
                        levelsCount.textContent = `${Math.min(keyLevels.length, 10)} levels`;
                    }
                } else {
                    levelsTableContainer.style.display = 'none';
                }
            }
        }

        // Build interpretation
        let interpretation = [];
        if (regimeData.ok && regimeData.data) {
            const r = regimeData.data;
            interpretation.push(`Regime: ${r.regime} (${r.strategy_bias === 'mean_revert' ? 'fade moves' : 'ride trends'}).`);
        }
        if (combinedData.ok && combinedData.data) {
            const c = combinedData.data;
            interpretation.push(`Combined: ${c.combined_regime?.replace('_', ' ')} - ${c.recommendation || ''}`);
        }
        if (levelsData.ok && levelsData.data) {
            const l = levelsData.data;
            if (l.call_wall && l.put_wall) {
                interpretation.push(`Range: $${l.put_wall.toFixed(0)} support to $${l.call_wall.toFixed(0)} resistance.`);
            }
        }

        document.getElementById('gex-interpretation').textContent =
            interpretation.length > 0 ? interpretation.join(' ') : 'GEX analysis loaded.';

        console.log('✅ GEX Dashboard loaded for', ticker);

    } catch (e) {
        console.error('GEX Dashboard error:', e);
        document.getElementById('gex-interpretation').textContent = 'Error loading GEX data: ' + e.message;
    }
}

// Ratio Spread Conditions Dashboard (V2 with Tastytrade support)
async function loadRatioSpreadScore() {
    const ticker = optionsAnalysisTicker;
    if (!ticker) return;

    // Get target DTE from selector (default 120)
    const targetDTE = document.getElementById('ratio-dte-select')?.value || '120';
    const container = document.getElementById('ratio-spread-container');
    container.style.display = 'block';
    document.getElementById('ratio-ticker').textContent = `${ticker} @ ${targetDTE} DTE`;

    // Reset fields
    document.getElementById('ratio-total-score').textContent = '-';
    document.getElementById('ratio-verdict').textContent = 'Loading...';
    document.getElementById('ratio-recommendation').textContent = 'Analyzing conditions...';
    document.getElementById('ratio-data-source').textContent = '...';

    try {
        // Use V2 endpoint with target_dte parameter
        // Use query params for futures (path params don't work with /)
        const isFutures = ticker.startsWith('/');
        const response = await fetch(isFutures
            ? `${API_BASE}/options/ratio-spread-score-v2?ticker=${encodeURIComponent(ticker)}&target_dte=${targetDTE}`
            : `${API_BASE}/options/ratio-spread-score-v2/${ticker}?target_dte=${targetDTE}`);
        const data = await response.json();

        if (!data.ok || !data.data) {
            throw new Error(data.error || 'Failed to load ratio spread score');
        }

        const d = data.data;
        const scores = d.scores || {};

        // Update total score and verdict
        document.getElementById('ratio-total-score').textContent = d.total_score;

        const verdictEl = document.getElementById('ratio-verdict');
        const bannerEl = document.getElementById('ratio-verdict-banner');
        verdictEl.textContent = d.verdict;

        // Color verdict banner based on score
        const verdictColors = {
            'HIGH_CONVICTION': { bg: 'rgba(34, 197, 94, 0.15)', border: 'var(--green)', text: 'var(--green)' },
            'FAVORABLE': { bg: 'rgba(59, 130, 246, 0.15)', border: 'var(--blue)', text: 'var(--blue)' },
            'NEUTRAL': { bg: 'rgba(251, 191, 36, 0.15)', border: 'var(--orange)', text: 'var(--orange)' },
            'UNFAVORABLE': { bg: 'rgba(239, 68, 68, 0.1)', border: 'var(--red)', text: 'var(--red)' },
            'AVOID': { bg: 'rgba(239, 68, 68, 0.2)', border: 'var(--red)', text: 'var(--red)' }
        };
        const colors = verdictColors[d.verdict] || verdictColors['NEUTRAL'];
        bannerEl.style.background = colors.bg;
        bannerEl.style.borderLeft = `4px solid ${colors.border}`;
        verdictEl.style.color = colors.text;

        document.getElementById('ratio-recommendation').textContent = d.recommendation;
        document.getElementById('ratio-risk-level').textContent = d.risk_level;
        document.getElementById('ratio-position-size').textContent = d.position_size;

        // Risk level color
        const riskEl = document.getElementById('ratio-risk-level');
        if (d.risk_level === 'low') riskEl.style.color = 'var(--green)';
        else if (d.risk_level === 'moderate') riskEl.style.color = 'var(--blue)';
        else if (d.risk_level === 'elevated') riskEl.style.color = 'var(--orange)';
        else riskEl.style.color = 'var(--red)';

        // Data source display
        const dataSourceEl = document.getElementById('ratio-data-source');
        const dataSource = d.data_source || 'polygon';
        dataSourceEl.textContent = dataSource === 'tastytrade' ? 'Tastytrade' : 'Polygon';
        dataSourceEl.style.color = dataSource === 'tastytrade' ? 'var(--green)' : 'var(--yellow)';

        // Update individual factor cards
        const updateFactorCard = (id, scoreData, valueFormatter) => {
            const card = document.getElementById(`ratio-${id}-card`);
            const checkEl = document.getElementById(`ratio-${id}-check`);
            const valueEl = document.getElementById(`ratio-${id}-value`);
            const labelEl = document.getElementById(`ratio-${id}-label`);

            if (scoreData.error) {
                checkEl.textContent = '❌';
                valueEl.textContent = 'Error';
                labelEl.textContent = scoreData.error;
                card.style.borderLeftColor = 'var(--red)';
                return;
            }

            checkEl.textContent = scoreData.pass ? '✅' : '⬜';
            valueEl.textContent = valueFormatter(scoreData);
            labelEl.textContent = scoreData.label || '';
            card.style.borderLeftColor = scoreData.pass ? 'var(--green)' : 'var(--border)';
        };

        // VRP
        if (scores.vrp) {
            updateFactorCard('vrp', scores.vrp, s => s.value !== undefined ? `${s.value > 0 ? '+' : ''}${s.value.toFixed(1)}%` : '--');
        }

        // Skew (show DTE if available from Tastytrade)
        if (scores.skew) {
            updateFactorCard('skew', scores.skew, s => {
                const skewPct = s.value ? `${((s.value - 1) * 100).toFixed(1)}%` : '--';
                return s.dte ? `${skewPct} (${s.dte}d)` : skewPct;
            });
        }

        // Term Structure (show DTE comparison if available)
        if (scores.term_structure) {
            updateFactorCard('term', scores.term_structure, s => {
                if (s.front_dte && s.back_dte) {
                    return `${s.front_dte}d vs ${s.back_dte}d`;
                }
                return s.signal || '--';
            });
        }

        // GEX
        if (scores.gex) {
            updateFactorCard('gex', scores.gex, s => s.signal ? s.signal.toUpperCase() : '--');
        }

        // RV Direction
        if (scores.rv_direction) {
            updateFactorCard('rv', scores.rv_direction, s => s.signal || '--');
        }

        // Expected Move (show DTE in the value)
        if (scores.expected_move) {
            updateFactorCard('em', scores.expected_move, s => {
                const label = s.label || '--';
                return s.dte ? `${label} (${s.dte}d)` : label;
            });
        }

        // Detail values from full data
        if (d.vrp_data) {
            document.getElementById('ratio-iv-30d').textContent = `${d.vrp_data.iv_30d_pct}%`;
            document.getElementById('ratio-rv-20d').textContent = d.vrp_data.rv_20d_pct ? `${d.vrp_data.rv_20d_pct}%` : '--';
        }

        if (d.skew_data) {
            document.getElementById('ratio-atm-iv').textContent = `${d.skew_data.atm_iv_pct}%`;
            document.getElementById('ratio-25d-iv').textContent = d.skew_data.otm_25d_iv_pct ? `${d.skew_data.otm_25d_iv_pct}%` : '--';
        }

        if (d.em_data) {
            document.getElementById('ratio-em-lower').textContent = `$${d.em_data.lower_expected}`;
            document.getElementById('ratio-em-1-5x').textContent = `$${d.em_data.lower_1_5x_em}`;
            document.getElementById('ratio-em-2x').textContent = `$${d.em_data.lower_2x_em}`;
            document.getElementById('ratio-dte').textContent = d.em_data.dte ? `${d.em_data.dte}d` : '--';
        }

        // Passing factors
        const factors = d.passing_factors || [];
        document.getElementById('ratio-passing-factors').textContent =
            factors.length > 0 ? factors.join(' • ') : 'No factors passing - unfavorable conditions';

        console.log('✅ Ratio Spread Score loaded for', ticker, '- Score:', d.total_score);

    } catch (e) {
        console.error('Ratio Spread Score error:', e);
        document.getElementById('ratio-verdict').textContent = 'ERROR';
        document.getElementById('ratio-recommendation').textContent = 'Error: ' + e.message;
    }
}

// ============================================================================
// OPTIONS VISUALIZATION (ApexCharts)
// ============================================================================

// Global state for options visualization charts
let optionsVizChart = null;
let priceChart = null;
let priceSeries = null;
let priceLines = {}; // Store price line references for updates
let optionsVizData = {
    gexByStrike: [],
    callOI: [],
    putOI: [],
    strikes: [],
    currentPrice: 0,
    callWall: 0,
    putWall: 0,
    gammaFlip: 0,
    maxPain: 0,
    expectedMove: { upper: 0, lower: 0 },
    totalGex: 0,
    pcRatio: 0,
    candles: [] // Candle data for price chart
};

/**
 * loadOptionsViz - Main function to fetch all options visualization data
 * @param {string} ticker - The ticker symbol to load data for
 */
async function loadOptionsViz(ticker) {
    if (!ticker) {
        ticker = optionsAnalysisTicker;
    }
    if (!ticker) {
        console.warn('loadOptionsViz: No ticker provided');
        return;
    }

    const container = document.getElementById('options-viz-container');
    const priceChartContainer = document.getElementById('price-chart-container');
    const gexChartContainer = document.getElementById('gex-chart-container');

    // Show container
    container.style.display = 'block';

    // Update ticker label
    const tickerLabel = document.getElementById('viz-ticker-label');
    if (tickerLabel) {
        tickerLabel.textContent = `- ${ticker}`;
    }

    // Show loading state in both chart containers
    if (priceChartContainer) {
        priceChartContainer.innerHTML = '<div style="display: flex; align-items: center; justify-content: center; height: 100%; color: var(--text-muted);"><span class="loading-spinner" style="margin-right: 8px;"></span>Loading price data...</div>';
    }
    if (gexChartContainer) {
        gexChartContainer.innerHTML = '<div style="display: flex; align-items: center; justify-content: center; height: 100%; color: var(--text-muted);"><span class="loading-spinner" style="margin-right: 8px;"></span>Loading GEX data...</div>';
    }

    try {
        const isFutures = ticker.startsWith('/');
        const tickerParam = encodeURIComponent(ticker);
        const expiry = document.getElementById('oa-expiry-select')?.value || '';
        const days = 30; // Default to 30 days of candle data

        // Build URLs for all data sources
        const gexLevelsUrl = isFutures
            ? `${API_BASE}/options/gex-levels?ticker=${tickerParam}${expiry ? '&expiration=' + expiry : ''}`
            : `${API_BASE}/options/gex-levels/${ticker}${expiry ? '?expiration=' + expiry : ''}`;

        const gexUrl = isFutures
            ? `${API_BASE}/options/gex?ticker=${tickerParam}${expiry ? '&expiration=' + expiry : ''}`
            : `${API_BASE}/options/gex/${ticker}${expiry ? '?expiration=' + expiry : ''}`;

        const maxPainUrl = isFutures
            ? `${API_BASE}/options/max-pain?ticker=${tickerParam}${expiry ? '&expiration=' + expiry : ''}`
            : `${API_BASE}/options/max-pain/${ticker}${expiry ? '?expiration=' + expiry : ''}`;

        const candlesUrl = `${API_BASE}/market/candles?ticker=${tickerParam}&days=${days}`;

        // Fetch all data in parallel (including candles)
        const [gexLevelsRes, gexRes, maxPainRes, candlesRes] = await Promise.all([
            fetch(gexLevelsUrl),
            fetch(gexUrl),
            fetch(maxPainUrl),
            fetch(candlesUrl).catch(e => {
                console.warn('Failed to fetch candle data:', e);
                return null;
            })
        ]);

        const gexLevelsData = await gexLevelsRes.json();
        const gexData = await gexRes.json();
        const maxPainData = await maxPainRes.json();

        // Parse candle data if available
        if (candlesRes && candlesRes.ok) {
            try {
                const candlesData = await candlesRes.json();
                console.log('Candles API response:', candlesData);
                // Convert candle data to Lightweight Charts format
                // API returns: {ok: true, data: {ticker, candles: [...]}}
                let candles = [];
                if (candlesData && candlesData.data && Array.isArray(candlesData.data.candles)) {
                    candles = candlesData.data.candles;
                } else if (candlesData && Array.isArray(candlesData.candles)) {
                    candles = candlesData.candles;
                } else if (Array.isArray(candlesData)) {
                    candles = candlesData;
                }
                console.log('Parsed candles array:', candles.length, 'items');
                optionsVizData.candles = candles.map(c => ({
                    time: c.time || c.date || c.t,
                    open: c.open || c.o,
                    high: c.high || c.h,
                    low: c.low || c.l,
                    close: c.close || c.c
                })).filter(c => c.time && c.open && c.high && c.low && c.close);
            } catch (parseErr) {
                console.error('Error parsing candle data:', parseErr);
                optionsVizData.candles = [];
            }
        } else {
            console.warn('Candles response not ok:', candlesRes?.status);
            optionsVizData.candles = [];
        }

        // Extract GEX levels
        const levels = gexLevelsData.data || {};
        optionsVizData.currentPrice = levels.current_price || gexData.data?.current_price || 0;
        optionsVizData.callWall = levels.call_wall || 0;
        optionsVizData.putWall = levels.put_wall || 0;
        optionsVizData.gammaFlip = levels.gamma_flip || 0;

        // Extract GEX by strike data
        const gex = gexData.data || {};
        optionsVizData.gexByStrike = (gex.gex_by_strike || []).map(s => ({
            strike: s.strike,
            callGex: s.call_gex || 0,
            putGex: s.put_gex || 0,
            netGex: s.net_gex || 0,
            callOI: s.call_oi || 0,
            putOI: s.put_oi || 0
        }));

        optionsVizData.totalGex = gex.total_gex || 0;
        const totalCallOI = gex.total_call_oi || 0;
        const totalPutOI = gex.total_put_oi || 0;
        optionsVizData.pcRatio = totalCallOI > 0 ? (totalPutOI / totalCallOI) : 0;

        // Extract max pain
        const maxPain = maxPainData.data || {};
        optionsVizData.maxPain = maxPain.max_pain || maxPain.maxPain || 0;

        // Calculate expected move if available
        if (levels.expected_move) {
            optionsVizData.expectedMove = {
                upper: levels.expected_move.upper || optionsVizData.currentPrice * 1.02,
                lower: levels.expected_move.lower || optionsVizData.currentPrice * 0.98
            };
        } else {
            // Default to +/- 2% if no expected move data
            optionsVizData.expectedMove = {
                upper: optionsVizData.currentPrice * 1.02,
                lower: optionsVizData.currentPrice * 0.98
            };
        }

        // Extract strikes and OI data
        optionsVizData.strikes = optionsVizData.gexByStrike.map(s => s.strike);
        optionsVizData.callOI = optionsVizData.gexByStrike.map(s => s.callOI);
        optionsVizData.putOI = optionsVizData.gexByStrike.map(s => s.putOI);

        // Update info bar
        updateVizInfoBar();

        // Render both charts
        renderPriceChart();
        renderVizGexChart();

        console.log('Options Viz loaded for', ticker, optionsVizData);

    } catch (e) {
        console.error('loadOptionsViz error:', e);
        const errorMsg = `<div style="display: flex; align-items: center; justify-content: center; height: 100%; color: var(--red);">Error loading options data: ${e.message}</div>`;
        if (priceChartContainer) priceChartContainer.innerHTML = errorMsg;
        if (gexChartContainer) gexChartContainer.innerHTML = errorMsg;
    }
}

/**
 * updateVizInfoBar - Update the info bar below the chart
 */
function updateVizInfoBar() {
    const currentPriceEl = document.getElementById('viz-current-price');
    const totalGexEl = document.getElementById('viz-total-gex');
    const pcRatioEl = document.getElementById('viz-pc-ratio');
    const maxPainEl = document.getElementById('viz-max-pain');
    const callWallEl = document.getElementById('viz-call-wall');
    const putWallEl = document.getElementById('viz-put-wall');

    if (currentPriceEl) {
        currentPriceEl.textContent = optionsVizData.currentPrice > 0
            ? `$${optionsVizData.currentPrice.toFixed(2)}`
            : '--';
    }

    if (totalGexEl) {
        const gex = optionsVizData.totalGex;
        const gexDisplay = Math.abs(gex) >= 1e9 ? `$${(gex / 1e9).toFixed(1)}B` :
                          Math.abs(gex) >= 1e6 ? `$${(gex / 1e6).toFixed(1)}M` :
                          Math.abs(gex) >= 1e3 ? `$${(gex / 1e3).toFixed(0)}K` :
                          `$${gex.toFixed(0)}`;
        totalGexEl.textContent = gexDisplay;
        totalGexEl.style.color = gex > 0 ? 'var(--green)' : gex < 0 ? 'var(--red)' : 'var(--text)';
    }

    if (pcRatioEl) {
        pcRatioEl.textContent = optionsVizData.pcRatio > 0
            ? optionsVizData.pcRatio.toFixed(2)
            : '--';
        const ratio = optionsVizData.pcRatio;
        pcRatioEl.style.color = ratio < 0.7 ? 'var(--green)' : ratio > 1.0 ? 'var(--red)' : 'var(--text)';
    }

    if (maxPainEl) {
        maxPainEl.textContent = optionsVizData.maxPain > 0
            ? `$${optionsVizData.maxPain.toFixed(0)}`
            : '--';
    }

    // Update Call Wall and Put Wall values
    if (callWallEl) {
        callWallEl.textContent = optionsVizData.callWall > 0
            ? `$${optionsVizData.callWall.toFixed(0)}`
            : '--';
        callWallEl.style.color = 'var(--red)';
    }

    if (putWallEl) {
        putWallEl.textContent = optionsVizData.putWall > 0
            ? `$${optionsVizData.putWall.toFixed(0)}`
            : '--';
        putWallEl.style.color = 'var(--green)';
    }
}

/**
 * renderPriceChart - Render the Lightweight Charts candlestick chart with level lines
 */
function renderPriceChart() {
    const container = document.getElementById('price-chart-container');

    if (!container) {
        console.warn('renderPriceChart: price-chart-container not found');
        return;
    }

    // Clear existing chart
    if (priceChart) {
        priceChart.remove();
        priceChart = null;
        priceSeries = null;
        priceLines = {};
    }

    // Check if candle data is available
    if (!optionsVizData.candles || optionsVizData.candles.length === 0) {
        container.innerHTML = '<div style="display: flex; align-items: center; justify-content: center; height: 100%; color: var(--text-muted);">No price data available</div>';
        return;
    }

    // Clear container before creating new chart
    container.innerHTML = '';

    // Create chart with dark theme
    priceChart = LightweightCharts.createChart(container, {
        layout: {
            background: { type: 'solid', color: 'transparent' },
            textColor: '#9ca3af',
        },
        grid: {
            vertLines: { color: 'rgba(255,255,255,0.05)' },
            horzLines: { color: 'rgba(255,255,255,0.05)' },
        },
        crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
        rightPriceScale: { borderColor: 'rgba(255,255,255,0.1)' },
        timeScale: { borderColor: 'rgba(255,255,255,0.1)', timeVisible: true },
        width: container.clientWidth,
        height: container.clientHeight || 300,
    });

    // Add candlestick series
    priceSeries = priceChart.addCandlestickSeries({
        upColor: '#22c55e',
        downColor: '#ef4444',
        borderUpColor: '#22c55e',
        borderDownColor: '#ef4444',
        wickUpColor: '#22c55e',
        wickDownColor: '#ef4444',
    });

    // Set candle data
    priceSeries.setData(optionsVizData.candles);

    // Add price lines for levels
    updatePriceChartLevels();

    // Fit content
    priceChart.timeScale().fitContent();

    // Handle resize
    const resizeObserver = new ResizeObserver(entries => {
        if (priceChart && container.clientWidth > 0) {
            priceChart.applyOptions({
                width: container.clientWidth,
                height: container.clientHeight || 300
            });
        }
    });
    resizeObserver.observe(container);
}

/**
 * updatePriceChartLevels - Add/remove level lines based on checkbox states
 */
function updatePriceChartLevels() {
    if (!priceSeries) return;

    // Remove existing lines
    Object.values(priceLines).forEach(line => {
        if (line) {
            try {
                priceSeries.removePriceLine(line);
            } catch (e) {
                // Line may already be removed
            }
        }
    });
    priceLines = {};

    // Call Wall (red)
    if (document.getElementById('viz-toggle-callwall')?.checked && optionsVizData.callWall > 0) {
        priceLines.callWall = priceSeries.createPriceLine({
            price: optionsVizData.callWall,
            color: '#ef4444',
            lineWidth: 2,
            lineStyle: LightweightCharts.LineStyle.Dashed,
            axisLabelVisible: true,
            title: 'Call Wall',
        });
    }

    // Put Wall (green)
    if (document.getElementById('viz-toggle-putwall')?.checked && optionsVizData.putWall > 0) {
        priceLines.putWall = priceSeries.createPriceLine({
            price: optionsVizData.putWall,
            color: '#22c55e',
            lineWidth: 2,
            lineStyle: LightweightCharts.LineStyle.Dashed,
            axisLabelVisible: true,
            title: 'Put Wall',
        });
    }

    // Gamma Flip (orange)
    if (document.getElementById('viz-toggle-gammaflip')?.checked && optionsVizData.gammaFlip > 0) {
        priceLines.gammaFlip = priceSeries.createPriceLine({
            price: optionsVizData.gammaFlip,
            color: '#f97316',
            lineWidth: 2,
            lineStyle: LightweightCharts.LineStyle.Dotted,
            axisLabelVisible: true,
            title: 'Gamma Flip',
        });
    }

    // Max Pain (purple)
    if (document.getElementById('viz-toggle-maxpain')?.checked && optionsVizData.maxPain > 0) {
        priceLines.maxPain = priceSeries.createPriceLine({
            price: optionsVizData.maxPain,
            color: '#a855f7',
            lineWidth: 2,
            lineStyle: LightweightCharts.LineStyle.Dotted,
            axisLabelVisible: true,
            title: 'Max Pain',
        });
    }
}

/**
 * renderVizGexChart - Render the ApexCharts GEX by strike bar chart for options visualization
 */
function renderVizGexChart() {
    const chartDiv = document.getElementById('gex-chart-container');

    if (!chartDiv) {
        console.warn('renderVizGexChart: gex-chart-container not found');
        return;
    }

    // Check if GEX chart should be shown
    const showGexChart = document.getElementById('viz-toggle-gex')?.checked ?? true;

    if (!showGexChart) {
        chartDiv.style.display = 'none';
        return;
    }

    chartDiv.style.display = 'block';

    if (!optionsVizData.gexByStrike || optionsVizData.gexByStrike.length === 0) {
        chartDiv.innerHTML = '<div style="display: flex; align-items: center; justify-content: center; height: 100%; color: var(--text-muted);">No GEX data available for visualization</div>';
        return;
    }

    // Filter data to reasonable range around current price (+/- 10-15%)
    let data = optionsVizData.gexByStrike.slice();
    const currentPrice = optionsVizData.currentPrice;

    if (currentPrice > 0 && data.length > 15) {
        const minRange = currentPrice * 0.88;
        const maxRange = currentPrice * 1.12;
        const filtered = data.filter(d => d.strike >= minRange && d.strike <= maxRange);
        if (filtered.length >= 5) {
            data = filtered;
        }
    }

    // Limit to 30 strikes centered on current price for readability
    if (data.length > 30) {
        const centerIdx = data.findIndex(d => d.strike >= currentPrice) || Math.floor(data.length / 2);
        const start = Math.max(0, centerIdx - 15);
        const end = Math.min(data.length, centerIdx + 15);
        data = data.slice(start, end);
    }

    if (data.length === 0) {
        chartDiv.innerHTML = '<div style="display: flex; align-items: center; justify-content: center; height: 100%; color: var(--text-muted);">No data in visible range</div>';
        return;
    }

    // Read checkbox states
    const showLevels = document.getElementById('viz-toggle-levels')?.checked ?? true;
    const showOI = document.getElementById('viz-toggle-oi')?.checked ?? false;
    const showMaxPain = document.getElementById('viz-toggle-maxpain')?.checked ?? true;
    const showEM = document.getElementById('viz-toggle-em')?.checked ?? false;

    // Prepare series data
    const strikes = data.map(d => d.strike);
    const netGexData = data.map(d => (d.netGex / 1e6)); // Convert to millions
    const callOIData = data.map(d => d.callOI);
    const putOIData = data.map(d => -d.putOI); // Negative for visual differentiation

    // Build series array
    const series = [];

    series.push({
        name: 'Net GEX (M)',
        type: 'bar',
        data: netGexData
    });

    if (showOI) {
        series.push({
            name: 'Call OI',
            type: 'bar',
            data: callOIData
        });
        series.push({
            name: 'Put OI',
            type: 'bar',
            data: putOIData
        });
    }

    // Build annotations for key levels
    const xAxisAnnotations = [];

    if (showLevels) {
        // Current Price - white solid line (thicker)
        if (currentPrice > 0) {
            xAxisAnnotations.push({
                x: currentPrice,
                borderColor: '#ffffff',
                borderWidth: 3,
                label: {
                    text: `Price: $${currentPrice.toFixed(0)}`,
                    style: {
                        color: '#ffffff',
                        background: 'rgba(0,0,0,0.7)',
                        fontSize: '11px',
                        fontWeight: 600
                    },
                    position: 'top',
                    offsetY: 0
                }
            });
        }

        // Call Wall - red dashed line
        if (optionsVizData.callWall > 0 && strikes.includes(optionsVizData.callWall) ||
            (optionsVizData.callWall >= Math.min(...strikes) && optionsVizData.callWall <= Math.max(...strikes))) {
            xAxisAnnotations.push({
                x: optionsVizData.callWall,
                borderColor: '#ef4444',
                borderWidth: 2,
                strokeDashArray: 5,
                label: {
                    text: `Call Wall: $${optionsVizData.callWall.toFixed(0)}`,
                    style: {
                        color: '#ef4444',
                        background: 'rgba(239,68,68,0.15)',
                        fontSize: '10px'
                    },
                    position: 'top',
                    offsetY: 20
                }
            });
        }

        // Put Wall - green dashed line
        if (optionsVizData.putWall > 0 &&
            (optionsVizData.putWall >= Math.min(...strikes) && optionsVizData.putWall <= Math.max(...strikes))) {
            xAxisAnnotations.push({
                x: optionsVizData.putWall,
                borderColor: '#22c55e',
                borderWidth: 2,
                strokeDashArray: 5,
                label: {
                    text: `Put Wall: $${optionsVizData.putWall.toFixed(0)}`,
                    style: {
                        color: '#22c55e',
                        background: 'rgba(34,197,94,0.15)',
                        fontSize: '10px'
                    },
                    position: 'top',
                    offsetY: 40
                }
            });
        }

        // Gamma Flip - orange dashed line
        if (optionsVizData.gammaFlip > 0 &&
            (optionsVizData.gammaFlip >= Math.min(...strikes) && optionsVizData.gammaFlip <= Math.max(...strikes))) {
            xAxisAnnotations.push({
                x: optionsVizData.gammaFlip,
                borderColor: '#f97316',
                borderWidth: 2,
                strokeDashArray: 3,
                label: {
                    text: `Gamma Flip: $${optionsVizData.gammaFlip.toFixed(0)}`,
                    style: {
                        color: '#f97316',
                        background: 'rgba(249,115,22,0.15)',
                        fontSize: '10px'
                    },
                    position: 'top',
                    offsetY: 60
                }
            });
        }
    }

    // Max Pain - purple dotted line
    if (showMaxPain && optionsVizData.maxPain > 0 &&
        (optionsVizData.maxPain >= Math.min(...strikes) && optionsVizData.maxPain <= Math.max(...strikes))) {
        xAxisAnnotations.push({
            x: optionsVizData.maxPain,
            borderColor: '#a855f7',
            borderWidth: 2,
            strokeDashArray: 2,
            label: {
                text: `Max Pain: $${optionsVizData.maxPain.toFixed(0)}`,
                style: {
                    color: '#a855f7',
                    background: 'rgba(168,85,247,0.15)',
                    fontSize: '10px'
                },
                position: 'bottom',
                offsetY: -10
            }
        });
    }

    // Expected Move - shaded area
    const shadeAnnotations = [];
    if (showEM && optionsVizData.expectedMove.upper > 0 && optionsVizData.expectedMove.lower > 0) {
        shadeAnnotations.push({
            x: optionsVizData.expectedMove.lower,
            x2: optionsVizData.expectedMove.upper,
            fillColor: 'rgba(59, 130, 246, 0.15)',
            borderColor: 'transparent',
            label: {
                text: 'Expected Move',
                style: {
                    color: '#3b82f6',
                    background: 'transparent',
                    fontSize: '10px'
                },
                position: 'top',
                offsetY: 80
            }
        });
    }

    // Determine colors for GEX bars (green for positive, red for negative)
    const barColors = netGexData.map(val => val >= 0 ? '#22c55e' : '#ef4444');

    // Build chart options
    const options = {
        chart: {
            type: 'bar',
            height: 300,
            background: 'transparent',
            toolbar: {
                show: true,
                tools: {
                    download: true,
                    selection: false,
                    zoom: true,
                    zoomin: true,
                    zoomout: true,
                    pan: false,
                    reset: true
                }
            },
            animations: {
                enabled: true,
                easing: 'easeinout',
                speed: 400
            }
        },
        theme: {
            mode: 'dark'
        },
        series: series,
        colors: !showOI ? barColors : ['#22c55e', '#3b82f6', '#ef4444'],
        plotOptions: {
            bar: {
                horizontal: false,
                columnWidth: '70%',
                borderRadius: 2,
                distributed: !showOI,
                dataLabels: {
                    position: 'top'
                }
            }
        },
        dataLabels: {
            enabled: false
        },
        stroke: {
            show: true,
            width: 1,
            colors: ['transparent']
        },
        xaxis: {
            categories: strikes.map(s => `$${s}`),
            labels: {
                rotate: -45,
                rotateAlways: strikes.length > 15,
                style: {
                    colors: 'var(--text-muted)',
                    fontSize: '10px'
                },
                formatter: function(val) {
                    return val;
                }
            },
            axisBorder: {
                show: true,
                color: 'var(--border)'
            },
            axisTicks: {
                show: true,
                color: 'var(--border)'
            },
            title: {
                text: 'Strike Price',
                style: {
                    color: 'var(--text-muted)',
                    fontSize: '11px'
                }
            }
        },
        yaxis: {
            title: {
                text: 'GEX (Millions)',
                style: {
                    color: 'var(--text-muted)',
                    fontSize: '11px'
                }
            },
            labels: {
                style: {
                    colors: 'var(--text-muted)',
                    fontSize: '10px'
                },
                formatter: function(val) {
                    return val.toFixed(1) + 'M';
                }
            },
            axisBorder: {
                show: true,
                color: 'var(--border)'
            }
        },
        fill: {
            opacity: 0.85,
            type: 'solid'
        },
        tooltip: {
            theme: 'dark',
            shared: true,
            intersect: false,
            y: {
                formatter: function(val, { seriesIndex, dataPointIndex, w }) {
                    const seriesName = w.config.series[seriesIndex]?.name || '';
                    if (seriesName.includes('GEX')) {
                        return `$${(val * 1e6).toLocaleString()} (${val.toFixed(2)}M)`;
                    } else if (seriesName.includes('OI')) {
                        return Math.abs(val).toLocaleString() + ' contracts';
                    }
                    return val;
                }
            },
            x: {
                formatter: function(val) {
                    return `Strike: ${val}`;
                }
            }
        },
        legend: {
            show: series.length > 1,
            position: 'top',
            horizontalAlign: 'right',
            labels: {
                colors: 'var(--text-muted)'
            }
        },
        grid: {
            borderColor: 'var(--border)',
            strokeDashArray: 3,
            xaxis: {
                lines: {
                    show: false
                }
            },
            yaxis: {
                lines: {
                    show: true
                }
            }
        },
        annotations: {
            xaxis: [...xAxisAnnotations, ...shadeAnnotations]
        }
    };

    // Destroy existing chart if present
    if (optionsVizChart) {
        optionsVizChart.destroy();
        optionsVizChart = null;
    }

    // Create new chart
    optionsVizChart = new ApexCharts(chartDiv, options);
    optionsVizChart.render();
}

/**
 * updateOptionsViz - Called when checkboxes change to update both charts
 */
function updateOptionsViz() {
    // Update price chart level lines (doesn't require re-render)
    updatePriceChartLevels();

    // Re-render the GEX chart with new options
    if (optionsVizData.gexByStrike && optionsVizData.gexByStrike.length > 0) {
        renderVizGexChart();
    }
}

/**
 * refreshOptionsViz - Refresh button handler
 */
function refreshOptionsViz() {
    const ticker = optionsAnalysisTicker;
    if (!ticker) {
        if (window.toast) {
            window.toast.warning('Please analyze a ticker first');
        }
        return;
    }
    loadOptionsViz(ticker);
}

// Market Options Sentiment loader
async function loadMarketSentiment() {
    try {
        // Fetch VIX and SPY expirations in parallel
        const [sentimentRes, expirationsRes] = await Promise.all([
            fetch(`${API_BASE}/options/market-sentiment`),
            fetch(`${API_BASE}/options/expirations/SPY`)
        ]);

        const data = await sentimentRes.json();
        const expData = await expirationsRes.json();

        // VIX (not expiration specific)
        if (data.ok && data.data) {
            const sentiment = data.data;
            const vix = sentiment.vix || 0;
            const vixEl = document.getElementById('vix-level');
            vixEl.textContent = vix.toFixed(1);
            vixEl.style.color = vix > 25 ? 'var(--red)' : vix < 15 ? 'var(--green)' : 'var(--text)';
            document.getElementById('vix-label').textContent = vix > 25 ? 'High Fear' : vix < 15 ? 'Low Fear' : 'Normal';
        }

        // Populate expiration dropdown with grouped options
        const expirySelect = document.getElementById('market-sentiment-expiry');
        if (expData.ok && expData.data && expData.data.expirations) {
            const expirations = expData.data.expirations;
            expirySelect.innerHTML = formatExpirationOptions(expirations, 0);

            // Load sentiment data for nearest expiration
            await loadMarketSentimentForExpiry();
        } else {
            expirySelect.innerHTML = '<option value="">N/A</option>';
        }
    } catch (e) {
        console.error('Failed to load market sentiment:', e);
    }
}

// Helper function to format expiration options with grouping
function formatExpirationOptions(expirations, selectedIndex = 0) {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];

    // Group expirations by timeframe
    const groups = {
        thisWeek: [],
        nextWeek: [],
        thisMonth: [],
        nextMonth: [],
        quarterly: [],
        leaps: []
    };

    expirations.forEach((exp, i) => {
        // Handle both string format and object format {date, dte, strike_count}
        const expDate = typeof exp === 'string' ? exp : exp.date;
        const d = new Date(expDate + 'T00:00:00');
        const daysOut = typeof exp === 'object' && exp.dte !== undefined ? exp.dte : Math.round((d - today) / (1000 * 60 * 60 * 24));
        const isMonthly = d.getDate() >= 15 && d.getDate() <= 21 && d.getDay() === 5;
        const isQuarterly = [2, 5, 8, 11].includes(d.getMonth()) && isMonthly;

        const label = daysOut <= 0 ? `${months[d.getMonth()]} ${d.getDate()} (0DTE)` :
                     daysOut === 1 ? `${months[d.getMonth()]} ${d.getDate()} (1d)` :
                     `${months[d.getMonth()]} ${d.getDate()} (${daysOut}d)`;

        const option = { value: expDate, label, daysOut, isSelected: i === selectedIndex };

        if (daysOut <= 7) groups.thisWeek.push(option);
        else if (daysOut <= 14) groups.nextWeek.push(option);
        else if (daysOut <= 30) groups.thisMonth.push(option);
        else if (daysOut <= 60) groups.nextMonth.push(option);
        else if (daysOut <= 180 || isQuarterly) groups.quarterly.push(option);
        else groups.leaps.push(option);
    });

    let html = '';

    // This Week
    if (groups.thisWeek.length > 0) {
        html += '<optgroup label="📅 This Week">';
        html += groups.thisWeek.map(o => `<option value="${o.value}" ${o.isSelected ? 'selected' : ''}>${o.label}</option>`).join('');
        html += '</optgroup>';
    }

    // Next Week
    if (groups.nextWeek.length > 0) {
        html += '<optgroup label="📆 Next Week">';
        html += groups.nextWeek.map(o => `<option value="${o.value}" ${o.isSelected ? 'selected' : ''}>${o.label}</option>`).join('');
        html += '</optgroup>';
    }

    // This Month
    if (groups.thisMonth.length > 0) {
        html += '<optgroup label="🗓️ This Month">';
        html += groups.thisMonth.map(o => `<option value="${o.value}" ${o.isSelected ? 'selected' : ''}>${o.label}</option>`).join('');
        html += '</optgroup>';
    }

    // Next Month
    if (groups.nextMonth.length > 0) {
        html += '<optgroup label="📋 Next Month">';
        html += groups.nextMonth.map(o => `<option value="${o.value}" ${o.isSelected ? 'selected' : ''}>${o.label}</option>`).join('');
        html += '</optgroup>';
    }

    // Quarterly / Monthlies (60-180 days)
    if (groups.quarterly.length > 0) {
        html += '<optgroup label="📊 Quarterly">';
        html += groups.quarterly.slice(0, 8).map(o => `<option value="${o.value}" ${o.isSelected ? 'selected' : ''}>${o.label}</option>`).join('');
        html += '</optgroup>';
    }

    // LEAPS (180+ days)
    if (groups.leaps.length > 0) {
        html += '<optgroup label="🔮 LEAPS">';
        html += groups.leaps.slice(0, 6).map(o => `<option value="${o.value}" ${o.isSelected ? 'selected' : ''}>${o.label}</option>`).join('');
        html += '</optgroup>';
    }

    return html;
}

// Load all sentiment data for selected expiration
async function loadMarketSentimentForExpiry() {
    const expiry = document.getElementById('market-sentiment-expiry').value;
    if (!expiry) return;

    // Sync to Options Analysis if SPY is selected there
    if (optionsAnalysisTicker === 'SPY' && !isSyncingExpiry) {
        const oaExpirySelect = document.getElementById('oa-expiry-select');
        if (oaExpirySelect && oaExpirySelect.value !== expiry) {
            const options = Array.from(oaExpirySelect.options).map(o => o.value);
            if (options.includes(expiry)) {
                isSyncingExpiry = true;
                oaExpirySelect.value = expiry;
                loadOptionsForExpiry().finally(() => { isSyncingExpiry = false; });
            }
        }
    }

    // Set loading states
    document.getElementById('spy-pc-ratio').textContent = '...';
    document.getElementById('market-gex').textContent = '...';
    document.getElementById('spy-call-put-oi').textContent = '...';

    try {
        // Fetch GEX data (provides OI and gamma exposure)
        const gexRes = await fetch(`${API_BASE}/options/gex/SPY?expiration=${expiry}`);
        const gexData = await gexRes.json();
        const gex = gexData.data || {};

        // P/C Ratio (same calculation as Options Analysis - OI based from GEX endpoint)
        const callOI = gex.total_call_oi || 0;
        const putOI = gex.total_put_oi || 0;
        const pcRatio = callOI > 0 ? (putOI / callOI) : 0;
        const pcEl = document.getElementById('spy-pc-ratio');
        pcEl.textContent = pcRatio.toFixed(2);
        pcEl.style.color = pcRatio > 1.0 ? 'var(--red)' : pcRatio < 0.7 ? 'var(--green)' : 'var(--text)';
        document.getElementById('spy-pc-label').textContent = pcRatio > 1.0 ? 'Bearish' : pcRatio < 0.7 ? 'Bullish' : 'Neutral';

        // Call/Put OI display
        const oiEl = document.getElementById('spy-call-put-oi');
        if (oiEl) {
            oiEl.innerHTML = `<span style="color: var(--green);">${(callOI/1000).toFixed(0)}K</span>/<span style="color: var(--red);">${(putOI/1000).toFixed(0)}K</span>`;
        }

        // GEX (real GEX from dedicated endpoint - same as Options Analysis)
        let gexValue = gex.total_gex || 0;
        if (typeof gexValue === 'object') gexValue = gexValue.total || 0;
        const gexEl = document.getElementById('market-gex');
        if (Math.abs(gexValue) >= 1e9) {
            gexEl.textContent = '$' + (gexValue / 1e9).toFixed(1) + 'B';
        } else if (Math.abs(gexValue) >= 1e6) {
            gexEl.textContent = '$' + (gexValue / 1e6).toFixed(1) + 'M';
        } else {
            gexEl.textContent = '$' + (gexValue / 1e3).toFixed(0) + 'K';
        }
        gexEl.style.color = gexValue > 0 ? 'var(--green)' : 'var(--red)';
        document.getElementById('gex-label').textContent = gexValue > 0 ? 'Stabilizing' : 'Volatile';

        // Update sentiment gauge
        const vixText = document.getElementById('vix-level').textContent;
        const vix = parseFloat(vixText) || 0;
        updateSentimentGauge(pcRatio, vix);

    } catch (e) {
        console.error('Failed to load sentiment for expiry:', e);
    }
}

// Whale Trades loader
async function loadWhaleTrades() {
    const container = document.getElementById('whale-trades-container');
    container.innerHTML = '<div style="padding: 20px; text-align: center; color: var(--text-muted);">Loading whale trades...</div>';

    try {
        const res = await fetch(`${API_BASE}/options/whales?min_premium=50000`);
        const data = await res.json();

        if (data.ok && (data.whales || data.data) && (data.whales || data.data).length > 0) {
            const trades = data.whales || data.data;
            let html = '<table style="width: 100%; border-collapse: collapse; font-size: 0.8rem;">';
            html += '<thead><tr style="background: var(--bg-hover); border-bottom: 1px solid var(--border);">';
            html += '<th style="padding: 8px; text-align: left;">Ticker</th>';
            html += '<th style="padding: 8px; text-align: left;">Type</th>';
            html += '<th style="padding: 8px; text-align: right;">Strike</th>';
            html += '<th style="padding: 8px; text-align: center;">Expiry</th>';
            html += '<th style="padding: 8px; text-align: right;">Premium</th>';
            html += '<th style="padding: 8px; text-align: center;">Side</th>';
            html += '</tr></thead><tbody>';

            trades.slice(0, 15).forEach(t => {
                const typeEmoji = t.type === 'C' || t.type === 'call' ? '📈' : '📉';
                const sideColor = t.side?.toLowerCase() === 'buy' ? 'var(--green)' : 'var(--red)';
                const premium = (t.premium || 0) / 1000;
                // Format expiration date as Mon DD
                let expiry = '--';
                if (t.expiration) {
                    const d = new Date(t.expiration + 'T00:00:00');
                    const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
                    expiry = months[d.getMonth()] + ' ' + d.getDate();
                }

                html += `<tr style="border-bottom: 1px solid var(--border);">
                    <td style="padding: 8px; font-weight: 600;">${t.ticker || '--'}</td>
                    <td style="padding: 8px;">${typeEmoji} ${(t.type || 'C').toUpperCase()}</td>
                    <td style="padding: 8px; text-align: right;">$${(t.strike || 0).toLocaleString()}</td>
                    <td style="padding: 8px; text-align: center; color: var(--text-muted); font-size: 0.75rem;">${expiry}</td>
                    <td style="padding: 8px; text-align: right; font-weight: 600;">$${premium.toLocaleString(undefined, {maximumFractionDigits: 0})}K</td>
                    <td style="padding: 8px; text-align: center; color: ${sideColor}; font-weight: 600;">${(t.side || 'BUY').toUpperCase()}</td>
                </tr>`;
            });

            html += '</tbody></table>';
            container.innerHTML = html;
        } else {
            container.innerHTML = '<div style="padding: 20px; text-align: center; color: var(--text-muted);">No whale trades found</div>';
        }
    } catch (e) {
        console.error('Failed to load whale trades:', e);
        container.innerHTML = '<div style="padding: 20px; text-align: center; color: var(--red);">Failed to load whale trades</div>';
    }
}

// Unusual Activity loader
async function loadUnusualActivity() {
    const container = document.getElementById('unusual-activity-container');
    container.innerHTML = '<div style="padding: 20px; text-align: center; color: var(--text-muted);">Scanning unusual activity...</div>';

    try {
        const tickers = 'NVDA,AAPL,TSLA,META,AMZN,GOOGL,MSFT,AMD,SPY,QQQ';
        const res = await fetch(`${API_BASE}/options/feed?tickers=${tickers}`);
        const data = await res.json();

        if (data.ok && (data.feed || data.data) && (data.feed || data.data).length > 0) {
            const items = data.feed || data.data;
            let html = '<div style="padding: 8px 0;">';

            items.slice(0, 12).forEach(item => {
                const typeEmoji = item.type === 'C' || item.type === 'call' ? '📈' : '📉';
                const volOi = item.vol_oi_ratio || item.volume_oi_ratio || 0;
                const premium = (item.premium || 0) / 1000;
                const unusualBadge = volOi > 3 ? '<span style="background: var(--yellow); color: #000; padding: 2px 6px; border-radius: 4px; font-size: 0.65rem; margin-left: 8px;">HOT</span>' : '';
                // Format expiration date as Mon DD
                let expiry = '';
                if (item.expiration) {
                    const d = new Date(item.expiration + 'T00:00:00');
                    const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
                    expiry = months[d.getMonth()] + ' ' + d.getDate();
                }

                html += `<div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 12px; border-bottom: 1px solid var(--border);">
                    <div>
                        <span style="font-weight: 600;">${item.ticker || '--'}</span>
                        <span style="color: var(--text-muted); margin-left: 8px;">${typeEmoji} $${(item.strike || 0).toLocaleString()}</span>
                        ${expiry ? `<span style="color: var(--text-muted); margin-left: 6px; font-size: 0.75rem;">(${expiry})</span>` : ''}
                        ${unusualBadge}
                    </div>
                    <div style="text-align: right;">
                        <div style="font-weight: 600;">$${premium.toLocaleString(undefined, {maximumFractionDigits: 0})}K</div>
                        <div style="font-size: 0.7rem; color: var(--text-muted);">Vol/OI: ${volOi.toFixed(1)}x</div>
                    </div>
                </div>`;
            });

            html += '</div>';
            container.innerHTML = html;
        } else {
            container.innerHTML = '<div style="padding: 20px; text-align: center; color: var(--text-muted);">No unusual activity detected</div>';
        }
    } catch (e) {
        console.error('Failed to load unusual activity:', e);
        container.innerHTML = '<div style="padding: 20px; text-align: center; color: var(--red);">Failed to scan</div>';
    }
}

// Options Screener
async function runOptionsScreener() {
    const container = document.getElementById('screener-results');
    container.innerHTML = '<div style="padding: 20px; text-align: center; color: var(--text-muted);">Running screener...</div>';

    try {
        const minPremium = (document.getElementById('screener-min-premium').value || 50) * 1000;
        const minIv = document.getElementById('screener-min-iv').value || 0;
        const sentiment = document.getElementById('screener-sentiment').value;
        const tickers = document.getElementById('screener-tickers').value.trim().toUpperCase() || 'NVDA,AAPL,TSLA,META,AMD';

        let url = `${API_BASE}/options/screener?tickers=${tickers}&min_premium=${minPremium}&min_iv_rank=${minIv}`;
        if (sentiment) url += `&sentiment=${sentiment}`;

        const res = await fetch(url);
        const data = await res.json();

        if (data.ok && (data.results || data.data) && (data.results || data.data).length > 0) {
            const results = data.results || data.data;
            let html = '<table style="width: 100%; border-collapse: collapse; font-size: 0.8rem; margin-top: 12px;">';
            html += '<thead><tr style="background: var(--bg-hover); border-bottom: 1px solid var(--border);">';
            html += '<th style="padding: 10px; text-align: left;">Ticker</th>';
            html += '<th style="padding: 10px; text-align: left;">Type</th>';
            html += '<th style="padding: 10px; text-align: right;">Strike</th>';
            html += '<th style="padding: 10px; text-align: right;">Premium</th>';
            html += '<th style="padding: 10px; text-align: right;">IV Rank</th>';
            html += '<th style="padding: 10px; text-align: center;">Sentiment</th>';
            html += '</tr></thead><tbody>';

            results.slice(0, 20).forEach(r => {
                const typeEmoji = r.type === 'C' ? '📈' : '📉';
                const sentColor = r.sentiment === 'bullish' ? 'var(--green)' : r.sentiment === 'bearish' ? 'var(--red)' : 'var(--text-muted)';
                const premium = (r.premium || 0) / 1000;
                const ivRank = r.iv_rank || 0;

                html += `<tr style="border-bottom: 1px solid var(--border);">
                    <td style="padding: 10px; font-weight: 600;">${r.ticker || '--'}</td>
                    <td style="padding: 10px;">${typeEmoji} ${(r.type || 'C').toUpperCase()}</td>
                    <td style="padding: 10px; text-align: right;">$${(r.strike || 0).toLocaleString()}</td>
                    <td style="padding: 10px; text-align: right; font-weight: 600;">$${premium.toLocaleString(undefined, {maximumFractionDigits: 0})}K</td>
                    <td style="padding: 10px; text-align: right;">${ivRank.toFixed(0)}%</td>
                    <td style="padding: 10px; text-align: center; color: ${sentColor}; font-weight: 600; text-transform: uppercase;">${r.sentiment || 'neutral'}</td>
                </tr>`;
            });

            html += '</tbody></table>';
            container.innerHTML = html;
        } else {
            container.innerHTML = '<div style="padding: 20px; text-align: center; color: var(--text-muted);">No results match your filters</div>';
        }
    } catch (e) {
        console.error('Failed to run screener:', e);
        container.innerHTML = '<div style="padding: 20px; text-align: center; color: var(--red);">Screener failed: ' + e.message + '</div>';
    }
}

// Smart Money Flow analyzer
async function loadSmartMoneyFlow() {
    const ticker = document.getElementById('flow-ticker-input').value.trim().toUpperCase();
    if (!ticker) {
        alert('Please enter a ticker symbol');
        return;
    }

    const container = document.getElementById('smart-money-flow-container');
    container.innerHTML = '<div style="padding: 20px; text-align: center; color: var(--text-muted);">Analyzing flow...</div>';

    try {
        const res = await fetch(`${API_BASE}/options/smart-money/${ticker}`);
        const data = await res.json();

        if (data.ok && data.data) {
            const flow = data.data;
            const netFlow = flow.net_flow || 0;
            const callFlow = flow.call_flow || 0;
            const putFlow = flow.put_flow || 0;
            const instRatio = flow.institutional_ratio || 0;

            const flowColor = netFlow > 0 ? 'var(--green)' : netFlow < 0 ? 'var(--red)' : 'var(--text-muted)';
            const flowLabel = netFlow > 0 ? 'NET INFLOW' : netFlow < 0 ? 'NET OUTFLOW' : 'NEUTRAL';

            let html = `
                <div class="grid grid-4" style="margin-bottom: 16px;">
                    <div style="text-align: center; padding: 12px; background: var(--bg-hover); border-radius: 8px;">
                        <div style="font-size: 0.7rem; color: var(--text-muted); margin-bottom: 4px;">NET FLOW</div>
                        <div style="font-size: 1.25rem; font-weight: 700; color: ${flowColor};">$${Math.abs(netFlow / 1e6).toFixed(1)}M</div>
                        <div style="font-size: 0.65rem; color: ${flowColor};">${flowLabel}</div>
                    </div>
                    <div style="text-align: center; padding: 12px; background: var(--bg-hover); border-radius: 8px;">
                        <div style="font-size: 0.7rem; color: var(--text-muted); margin-bottom: 4px;">CALL FLOW</div>
                        <div style="font-size: 1.25rem; font-weight: 700; color: var(--green);">$${(callFlow / 1e6).toFixed(1)}M</div>
                    </div>
                    <div style="text-align: center; padding: 12px; background: var(--bg-hover); border-radius: 8px;">
                        <div style="font-size: 0.7rem; color: var(--text-muted); margin-bottom: 4px;">PUT FLOW</div>
                        <div style="font-size: 1.25rem; font-weight: 700; color: var(--red);">$${(putFlow / 1e6).toFixed(1)}M</div>
                    </div>
                    <div style="text-align: center; padding: 12px; background: var(--bg-hover); border-radius: 8px;">
                        <div style="font-size: 0.7rem; color: var(--text-muted); margin-bottom: 4px;">INSTITUTIONAL</div>
                        <div style="font-size: 1.25rem; font-weight: 700;">${(instRatio * 100).toFixed(0)}%</div>
                    </div>
                </div>
            `;

            // Notable trades
            const notable = flow.notable_trades || [];
            if (notable.length > 0) {
                html += '<div style="font-size: 0.85rem; font-weight: 600; margin-bottom: 8px;">Notable Trades</div>';
                html += '<div style="max-height: 200px; overflow-y: auto;">';
                notable.slice(0, 8).forEach(t => {
                    const signalEmoji = t.signal?.includes('sweep') ? '🔥' : t.signal?.includes('block') ? '🟦' : '•';
                    const premium = (t.premium || 0) / 1000;
                    // Format expiration date as Mon DD
                    let expiry = '';
                    if (t.expiration) {
                        const d = new Date(t.expiration + 'T00:00:00');
                        const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
                        expiry = months[d.getMonth()] + ' ' + d.getDate();
                    }

                    html += `<div style="display: flex; justify-content: space-between; padding: 8px 12px; border-bottom: 1px solid var(--border);">
                        <span>${signalEmoji} $${(t.strike || 0).toLocaleString()} ${t.type || 'C'}${expiry ? ` <span style="color: var(--text-muted); font-size: 0.75rem;">(${expiry})</span>` : ''}</span>
                        <span style="font-weight: 600;">$${premium.toLocaleString(undefined, {maximumFractionDigits: 0})}K <span style="color: var(--text-muted); font-weight: normal; font-size: 0.75rem;">${t.signal || ''}</span></span>
                    </div>`;
                });
                html += '</div>';
            }

            container.innerHTML = html;
        } else {
            container.innerHTML = '<div style="padding: 20px; text-align: center; color: var(--text-muted);">No flow data for ' + ticker + '</div>';
        }
    } catch (e) {
        console.error('Failed to load smart money flow:', e);
        container.innerHTML = '<div style="padding: 20px; text-align: center; color: var(--red);">Failed to analyze flow</div>';
    }
}

// Technical indicators loader
async function loadTechnicalIndicators() {
    const ticker = document.getElementById('technical-ticker-input').value.trim().toUpperCase();
    if (!ticker) {
        alert('Please enter a ticker symbol');
        return;
    }

    try {
        // Show loading state
        document.getElementById('technical-indicators-container').innerHTML =
            '<div style="color: var(--text-muted); font-size: 0.8125rem;">Loading...</div>';

        // Fetch technical indicators
        const res = await fetch(`${API_BASE}/options/technical/${ticker}`);
        const data = await res.json();

        if (!data.ok || data.data.error) {
            throw new Error(data.data?.error || 'Failed to load technical indicators');
        }

        const tech = data.data;

        // Determine trend color
        const trendColors = {
            'bullish': 'var(--green)',
            'bearish': 'var(--red)',
            'neutral': 'var(--text-muted)',
            'sideways': 'var(--text-muted)'
        };
        const trendColor = trendColors[tech.trend?.toLowerCase()] || 'var(--text-muted)';

        // RSI color coding
        let rsiColor = 'var(--text)';
        if (tech.rsi >= 70) rsiColor = 'var(--red)';
        else if (tech.rsi <= 30) rsiColor = 'var(--green)';

        // Build HTML
        let html = `
            <div style="margin-bottom: 12px;">
                <div style="font-size: 0.75rem; color: var(--text-muted); margin-bottom: 4px;">TREND</div>
                <div style="font-size: 1.1rem; font-weight: 700; color: ${trendColor}; text-transform: uppercase;">
                    ${tech.trend || 'N/A'}
                </div>
                <div style="font-size: 0.7rem; color: var(--text-muted);">Price: $${tech.price?.toFixed(2) || '--'}</div>
            </div>
            <div class="sidebar-item">
                <span class="sidebar-label">SMA 20</span>
                <span class="sidebar-value">${tech.sma_20 ? '$' + tech.sma_20.toFixed(2) : '--'}</span>
            </div>
            <div class="sidebar-item">
                <span class="sidebar-label">SMA 50</span>
                <span class="sidebar-value">${tech.sma_50 ? '$' + tech.sma_50.toFixed(2) : '--'}</span>
            </div>
            <div class="sidebar-item">
                <span class="sidebar-label">SMA 200</span>
                <span class="sidebar-value">${tech.sma_200 ? '$' + tech.sma_200.toFixed(2) : '--'}</span>
            </div>
            <div class="sidebar-item">
                <span class="sidebar-label">RSI (14)</span>
                <span class="sidebar-value" style="color: ${rsiColor}; font-weight: 600;">${tech.rsi?.toFixed(1) || '--'}</span>
            </div>
            <div class="sidebar-item">
                <span class="sidebar-label">MACD</span>
                <span class="sidebar-value">${tech.macd?.toFixed(2) || '--'}</span>
            </div>
            <div class="sidebar-item">
                <span class="sidebar-label">Signal</span>
                <span class="sidebar-value">${tech.macd_signal?.toFixed(2) || '--'}</span>
            </div>
        `;

        // Add signals if available
        if (tech.signals && tech.signals.length > 0) {
            html += `
                <div style="margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--border);">
                    <div style="font-size: 0.75rem; color: var(--text-muted); margin-bottom: 8px;">ACTIVE SIGNALS</div>
                    ${tech.signals.map(signal => `
                        <div style="font-size: 0.75rem; padding: 4px 8px; background: var(--bg-hover); border-radius: 4px; margin-bottom: 4px;">
                            ${signal}
                        </div>
                    `).join('')}
                </div>
            `;
        }

        document.getElementById('technical-indicators-container').innerHTML = html;

    } catch (e) {
        console.error('Failed to load technical indicators:', e);
        document.getElementById('technical-indicators-container').innerHTML =
            '<div style="color: var(--red); font-size: 0.8125rem;">Failed to load: ' + e.message + '</div>';
    }
}

// Simple cache to avoid refetching
const tabLoadedAt = {};
const CACHE_TTL = 60000; // 1 minute

async function refreshAll() {
    console.log('🔄 refreshAll() called - loading dashboard data');

    // Show loading state in header
    const lastUpdateEl = document.getElementById('last-update');
    if (lastUpdateEl) {
        lastUpdateEl.innerHTML = '<span class="loading-spinner"></span> Loading...';
    }

    // Add loading class to body for global styling
    document.body.classList.add('is-loading');

    try {
        // Stage 1: Load fast data first (user sees results quickly)
        await Promise.all([
            fetchHealth(),
            fetchScan(),
            fetchThemes(),
            fetchConvictionAlerts(),
        ]);

        // Update time after fast data loads
        if (lastUpdateEl) lastUpdateEl.textContent = formatLocalTime();

        tabLoadedAt['dashboard'] = Date.now();

        // Stage 2: Load slower AI data in background (don't block UI)
        Promise.all([
            fetchAIIntelligence(),
            fetchUnusualOptions(),
            fetchVolumeProfile(),
            fetchAgenticStatus(),
            fetchAgenticPicks(),
        ]).catch(e => console.warn('Background AI fetch error:', e));
    } finally {
        document.body.classList.remove('is-loading');
    }
}

// Refresh only the current active tab
async function refreshCurrentTab() {
    // Determine current active tab
    let activeTab = currentSubTab || currentCategory || 'dashboard';
    console.log(`🔄 Refreshing current tab: ${activeTab}`);

    // Clear cache for this tab to force refresh
    delete tabLoadedAt[activeTab];

    document.getElementById('last-update').textContent = 'Refreshing...';

    await loadTabDataForce(activeTab);

    document.getElementById('last-update').textContent = formatLocalTime();
}

async function loadTabDataForce(tabId) {
    switch(tabId) {
        case 'dashboard':
            await Promise.all([fetchHealth(), fetchScan(), fetchAIIntelligence(), fetchConvictionAlerts(), fetchThemes(), fetchUnusualOptions(), fetchVolumeProfile(), fetchAgenticStatus(), fetchAgenticPicks()]);
            break;
        case 'health':
            await fetchMarketHealth();
            break;
        case 'scanner':
            await fetchScan();
            break;
        case 'themes':
            await Promise.all([fetchThemes(), fetchThemeRadar(), loadThemeConfig()]);
            break;
        case 'sec':
            await Promise.all([fetchMARadar(), fetchDeals()]);
            break;
        case 'trades':
            await fetchTrades();
            break;
        case 'watchlist':
            await refreshWatchlistTab();
            break;
        case 'analytics':
            await Promise.all([fetchEvolution(), fetchParameters(), fetchCorrelations(), fetchEconomicDashboard()]);
            break;
        case 'options':
            await Promise.all([loadMarketSentiment(), loadWhaleTrades(), loadUnusualActivity()]);
            break;
    }
    tabLoadedAt[tabId] = Date.now();
}

// Tooltip system - escapes overflow:hidden containers
function initTooltips() {
    let tooltipEl = document.createElement('div');
    tooltipEl.className = 'tooltip-popup';
    document.body.appendChild(tooltipEl);

    document.addEventListener('mouseover', (e) => {
        const icon = e.target.closest('.info-icon[data-tooltip]');
        if (!icon) return;

        const text = icon.getAttribute('data-tooltip');
        if (!text) return;

        tooltipEl.textContent = text;
        tooltipEl.classList.add('visible');

        const rect = icon.getBoundingClientRect();
        const tooltipRect = tooltipEl.getBoundingClientRect();

        let left = rect.left + rect.width / 2 - tooltipRect.width / 2;
        let top = rect.top - tooltipRect.height - 10;

        // Keep within viewport
        if (left < 10) left = 10;
        if (left + tooltipRect.width > window.innerWidth - 10) {
            left = window.innerWidth - tooltipRect.width - 10;
        }
        if (top < 10) {
            top = rect.bottom + 10; // Show below if no room above
        }

        tooltipEl.style.left = left + 'px';
        tooltipEl.style.top = top + 'px';
    });

    document.addEventListener('mouseout', (e) => {
        const icon = e.target.closest('.info-icon[data-tooltip]');
        if (icon) {
            tooltipEl.classList.remove('visible');
        }
    });
}

// Init
document.addEventListener('DOMContentLoaded', () => {
    initTooltips();
    refreshAll();

    // Auto-refresh unusual options every 5 minutes
    setInterval(fetchUnusualOptions, 300000);

    // Initialize sync client
    setTimeout(() => {
        syncClient.connect();
    }, 1000);
});

// Also refresh AI advisor after trades are loaded
setTimeout(() => {
    if (typeof refreshAIAdvisor === 'function') {
        refreshAIAdvisor();
    }
}, 2000);
