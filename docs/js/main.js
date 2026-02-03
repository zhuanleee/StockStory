/**
 * Dashboard Main Entry Point
 * @module main
 */

// Import modules
import { API_BASE_URL } from './config.js';
import { api } from './api/client.js';
import { apiQueue, queuedFetch } from './api/queue.js';
import { store } from './state/store.js';
import { modal } from './components/Modal.js';
import { toast } from './components/Toast.js';
import { SyncClient } from './sync/SyncClient.js';
import { dom } from './utils/dom-cache.js';
import { safeFixed, formatVolume, formatPrice, formatPercent, formatDate } from './utils/formatters.js';
import { escapeHTML, sanitizeHTML, escapeHTMLAttribute } from './utils/security.js';
import {
    validateTicker,
    validatePrice,
    validateShares,
    validateText
} from './utils/validators.js';

/**
 * Initialize the dashboard application
 */
async function init() {
    console.log('Dashboard initializing...');

    // Setup state subscribers for auto-updating UI
    setupStateSubscribers();

    // Load initial data
    await refreshAll();

    // Initialize sync client (delayed to avoid blocking initial load)
    setTimeout(() => {
        try {
            const syncClient = new SyncClient();
            syncClient.connect();
            window.syncClient = syncClient; // Expose globally for backward compatibility
        } catch (e) {
            console.warn('Sync client initialization failed:', e);
        }
    }, 1000);

    console.log('Dashboard ready!');
}

/**
 * Setup state subscribers to auto-update UI when state changes
 */
function setupStateSubscribers() {
    // Auto-update positions when they change
    store.subscribe('positions', (positions) => {
        if (typeof renderPositionCards === 'function') {
            renderPositionCards(positions);
        }
        if (typeof updatePortfolioSummary === 'function') {
            updatePortfolioSummary(positions);
        }
        if (typeof renderThemeConcentration === 'function') {
            renderThemeConcentration(positions);
        }
        if (typeof updatePerformanceMetrics === 'function') {
            updatePerformanceMetrics(positions);
        }
    });

    // Auto-update watchlist when it changes
    store.subscribe('watchlist', (watchlist) => {
        if (typeof renderWatchlistCards === 'function') {
            renderWatchlistCards(watchlist);
        }
    });

    // Auto-update journal when it changes
    store.subscribe('journalEntries', (entries) => {
        if (typeof renderJournal === 'function') {
            renderJournal(entries);
        }
    });

    // Update last refresh time
    store.subscribe('lastUpdate', (timestamp) => {
        const el = document.getElementById('last-update');
        if (el && timestamp) {
            const date = new Date(timestamp);
            el.textContent = date.toLocaleTimeString('en-US', {
                hour: '2-digit',
                minute: '2-digit'
            });
        }
    });

    // Update refreshing state
    store.subscribe('isRefreshing', (isRefreshing) => {
        const el = document.getElementById('last-update');
        if (el) {
            el.textContent = isRefreshing ? 'Refreshing...' : el.textContent;
        }
    });
}

/**
 * Refresh all dashboard data
 */
async function refreshAll() {
    const el = document.getElementById('last-update');
    if (el) {
        el.textContent = 'Refreshing...';
    }

    store.setState('isRefreshing', true);

    try {
        // Fetch all data in parallel
        await Promise.allSettled([
            typeof fetchHealth === 'function' ? fetchHealth() : Promise.resolve(),
            typeof fetchScan === 'function' ? fetchScan() : Promise.resolve(),
            typeof fetchAIIntelligence === 'function' ? fetchAIIntelligence() : Promise.resolve(),
            typeof fetchConvictionAlerts === 'function' ? fetchConvictionAlerts() : Promise.resolve(),
            typeof fetchUnusualOptions === 'function' ? fetchUnusualOptions() : Promise.resolve(),
            typeof fetchSupplyChain === 'function' ? fetchSupplyChain() : Promise.resolve(),
            typeof fetchEarnings === 'function' ? fetchEarnings() : Promise.resolve(),
            typeof fetchEvolution === 'function' ? fetchEvolution() : Promise.resolve(),
            typeof fetchParameters === 'function' ? fetchParameters() : Promise.resolve(),
            typeof fetchCorrelations === 'function' ? fetchCorrelations() : Promise.resolve(),
            typeof fetchThemes === 'function' ? fetchThemes() : Promise.resolve(),
            typeof fetchMARadar === 'function' ? fetchMARadar() : Promise.resolve(),
            typeof fetchDeals === 'function' ? fetchDeals() : Promise.resolve(),
            typeof fetchContractThemes === 'function' ? fetchContractThemes() : Promise.resolve(),
            typeof fetchRecentContracts === 'function' ? fetchRecentContracts() : Promise.resolve(),
            typeof fetchPatentThemes === 'function' ? fetchPatentThemes() : Promise.resolve(),
            typeof fetchThemeRadar === 'function' ? fetchThemeRadar() : Promise.resolve(),
            typeof fetchThemeAlerts === 'function' ? fetchThemeAlerts() : Promise.resolve(),
            typeof fetchTrades === 'function' ? fetchTrades() : Promise.resolve(),
        ]);

        const now = new Date();
        if (el) {
            el.textContent = now.toLocaleTimeString('en-US', {
                hour: '2-digit',
                minute: '2-digit'
            });
        }

        store.setState('lastUpdate', now.toISOString());
    } catch (error) {
        console.error('Error refreshing data:', error);
        if (el) {
            el.textContent = 'Error refreshing';
        }
        toast.error('Failed to refresh dashboard data');
    } finally {
        store.setState('isRefreshing', false);
    }
}

// Export modules to window for backward compatibility during migration
window.api = api;
window.apiQueue = apiQueue;
window.queuedFetch = queuedFetch;
window.store = store;
window.modal = modal;
window.toast = toast;
window.dom = dom;
window.refreshAll = refreshAll;
window.API_BASE = API_BASE_URL; // For backward compatibility

// Export utility functions to window for backward compatibility
window.safeFixed = safeFixed;
window.formatVolume = formatVolume;
window.formatPrice = formatPrice;
window.formatPercent = formatPercent;
window.formatDate = formatDate;
window.escapeHTML = escapeHTML;
window.sanitizeHTML = sanitizeHTML;
window.escapeHTMLAttribute = escapeHTMLAttribute;
window.validateTicker = validateTicker;
window.validatePrice = validatePrice;
window.validateShares = validateShares;
window.validateText = validateText;

// DON'T auto-initialize - let inline JS handle initialization
// This module only provides utilities that are exported to window

// Export for module usage
export { api, apiQueue, queuedFetch, store, modal, toast, dom, refreshAll };
