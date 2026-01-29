/**
 * Real-time sync client for Telegram integration
 * @module sync/SyncClient
 */

import { API_BASE_URL } from '../config.js';
import { toast } from '../components/Toast.js';

/**
 * SyncClient handles real-time synchronization with Telegram bot
 * Uses Socket.IO for bidirectional communication
 */
export class SyncClient {
    constructor() {
        this.socket = null;
        this.clientId = null;
        this.connected = false;
        this.eventHandlers = {};
        this.failCount = 0;
    }

    /**
     * Connects to the sync server
     *
     * @example
     * const syncClient = new SyncClient();
     * syncClient.connect();
     */
    connect() {
        try {
            // Connect to same origin (API server) with Socket.IO
            const serverUrl = API_BASE_URL.replace('/api', '');
            const isSecure = window.location.protocol === 'https:';
            console.log('Connecting to sync server:', serverUrl);

            // Check if io (Socket.IO) is available
            if (typeof io === 'undefined') {
                console.warn('Socket.IO not loaded, sync unavailable');
                this.updateSyncStatus('unavailable');
                return;
            }

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
    }

    /**
     * Handles successful connection
     * @private
     */
    onConnect() {
        console.log('Real-time sync connected');
        this.connected = true;
        this.failCount = 0;
        this.updateSyncStatus('connected');
    }

    /**
     * Handles disconnection
     * @private
     */
    onDisconnect(reason) {
        console.debug('Sync disconnected:', reason);
        this.connected = false;
        this.updateSyncStatus('disconnected');
    }

    /**
     * Handles connection errors
     * @private
     */
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

    /**
     * Handles connected event from server
     * @private
     */
    handleConnected(data) {
        this.clientId = data.client_id;
        console.log('Sync client ID:', this.clientId);
        toast.success('Real-time Telegram sync active');
    }

    /**
     * Handles sync history from server
     * @private
     */
    handleSyncHistory(data) {
        const events = data.events || [];
        console.log(`Received ${events.length} historical events`);
        events.forEach(event => this.processEvent(event, false));
    }

    /**
     * Handles incoming sync event
     * @private
     */
    handleSyncEvent(data) {
        const event = data.event;
        if (event) {
            this.processEvent(event, true);
        }
    }

    /**
     * Handles status update from server
     * @private
     */
    handleStatus(data) {
        this.updateSyncStatusDetails(data);
    }

    /**
     * Processes a sync event
     * @private
     */
    processEvent(event, notify = true) {
        const eventType = event.event_type;
        const source = event.source;
        const payload = event.payload || {};

        console.log(`Sync event: ${eventType} from ${source}`);

        // Handle different event types
        switch (eventType) {
            case 'trade_created':
                if (source === 'telegram' && notify) {
                    toast.info(`${payload.ticker} added to watchlist (Telegram)`);
                    if (typeof fetchTrades === 'function') {
                        fetchTrades();
                    }
                }
                break;

            case 'buy_executed':
                if (source === 'telegram' && notify) {
                    toast.success(`Bought ${payload.shares} ${payload.ticker} @ $${payload.price} (Telegram)`);
                    if (typeof fetchTrades === 'function') {
                        fetchTrades();
                    }
                }
                break;

            case 'sell_executed':
                if (source === 'telegram' && notify) {
                    toast.warning(`Sold ${payload.shares} ${payload.ticker} @ $${payload.price} (Telegram)`);
                    if (typeof fetchTrades === 'function') {
                        fetchTrades();
                    }
                }
                break;

            case 'exit_signal':
                if (notify) {
                    toast.warning(`Exit signal for ${payload.ticker}: ${payload.signal_type}`);
                }
                break;

            case 'journal_added':
                if (source === 'telegram' && notify) {
                    toast.info(`Journal entry added (Telegram): ${payload.entry_type}`);
                    if (typeof fetchJournal === 'function') {
                        fetchJournal();
                    }
                }
                break;

            case 'command_received':
                if (notify) {
                    toast.info(`Telegram command: /${payload.command} ${payload.args || ''}`);
                    if (typeof addSyncActivityItem === 'function') {
                        addSyncActivityItem(`Telegram: /${payload.command} ${payload.args || ''}`, 'command');
                    }
                }
                break;

            case 'scan_completed':
                if (notify) {
                    toast.info(`Scan complete: ${payload.positions_scanned} positions, ${payload.signals_count} signals`);
                }
                break;
        }

        // Add to sync activity
        if (source === 'telegram' && notify && typeof addSyncActivityItem === 'function') {
            addSyncActivityItem(this.formatEventMessage(event), eventType.replace('_', '-'));
        }

        // Acknowledge event
        if (event.ack_required) {
            this.send({ type: 'ack', event_id: event.id });
        }
    }

    /**
     * Formats event message for display
     * @private
     */
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

    /**
     * Sends a message to the server
     *
     * @param {Object} data - The message data
     *
     * @example
     * syncClient.send({ type: 'ack', event_id: '123' });
     */
    send(data) {
        if (this.socket && this.connected) {
            this.socket.emit('message', data);
        }
    }

    /**
     * Publishes an event to the server
     *
     * @param {string} eventType - The event type
     * @param {Object} payload - The event payload
     *
     * @example
     * syncClient.publish('trade_created', { ticker: 'AAPL', ... });
     */
    publish(eventType, payload) {
        if (this.socket && this.connected) {
            this.socket.emit('publish', {
                event_type: eventType,
                payload: payload
            });
        }
    }

    /**
     * Requests sync status from server
     *
     * @example
     * syncClient.requestStatus();
     */
    requestStatus() {
        if (this.socket && this.connected) {
            this.socket.emit('get_status');
        }
    }

    /**
     * Acknowledges event receipt
     *
     * @param {string} eventId - The event ID to acknowledge
     *
     * @example
     * syncClient.ack('event-123');
     */
    ack(eventId) {
        if (this.socket && this.connected) {
            this.socket.emit('ack', { event_id: eventId });
        }
    }

    /**
     * Updates the sync status indicator in the UI
     * @private
     */
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

    /**
     * Updates the sync status details in the UI
     * @private
     */
    updateSyncStatusDetails(status) {
        const el = document.getElementById('sync-details');
        if (el) {
            el.innerHTML = `
                <div>Clients: ${status.connected_clients || 0}</div>
                <div>Events: ${status.total_events || 0}</div>
            `;
        }
    }

    /**
     * Disconnects from the sync server
     *
     * @example
     * syncClient.disconnect();
     */
    disconnect() {
        if (this.socket) {
            this.socket.disconnect();
            this.connected = false;
            this.updateSyncStatus('disconnected');
        }
    }
}
