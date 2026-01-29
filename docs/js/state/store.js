/**
 * Application state management with pub/sub pattern
 * @module state/store
 */

/**
 * Application state store with reactive updates
 */
export class AppStore {
    constructor() {
        this._state = {
            positions: [],
            watchlist: [],
            journalEntries: [],
            scanData: null,
            themesData: null,
            activityItems: [],
            currentTab: 'scan',
            lastUpdate: null,
            isRefreshing: false
        };
        this._listeners = new Map();
    }

    /**
     * Gets a value from the state
     *
     * @param {string} key - The state key to retrieve
     * @returns {any} The state value
     *
     * @example
     * const positions = store.getState('positions');
     */
    getState(key) {
        return this._state[key];
    }

    /**
     * Gets all state
     *
     * @returns {Object} The entire state object
     *
     * @example
     * const state = store.getAllState();
     */
    getAllState() {
        return { ...this._state };
    }

    /**
     * Sets a value in the state and notifies listeners
     *
     * @param {string} key - The state key to set
     * @param {any} value - The new value
     *
     * @example
     * store.setState('positions', newPositions);
     */
    setState(key, value) {
        const oldValue = this._state[key];
        this._state[key] = value;
        this._notify(key, value, oldValue);
    }

    /**
     * Subscribes to state changes for a specific key
     *
     * @param {string} key - The state key to watch
     * @param {Function} callback - Callback function (newValue, oldValue) => void
     * @returns {Function} Unsubscribe function
     *
     * @example
     * const unsubscribe = store.subscribe('positions', (newVal, oldVal) => {
     *     console.log('Positions updated:', newVal);
     * });
     * // Later: unsubscribe()
     */
    subscribe(key, callback) {
        if (!this._listeners.has(key)) {
            this._listeners.set(key, new Set());
        }
        this._listeners.get(key).add(callback);

        // Return unsubscribe function
        return () => this._listeners.get(key).delete(callback);
    }

    /**
     * Notifies all listeners of a state change
     * @private
     */
    _notify(key, newValue, oldValue) {
        const listeners = this._listeners.get(key);
        if (listeners) {
            listeners.forEach(cb => {
                try {
                    cb(newValue, oldValue);
                } catch (error) {
                    console.error(`Error in state listener for ${key}:`, error);
                }
            });
        }

        // Also notify wildcard listeners (key: '*')
        const wildcardListeners = this._listeners.get('*');
        if (wildcardListeners) {
            wildcardListeners.forEach(cb => {
                try {
                    cb(key, newValue, oldValue);
                } catch (error) {
                    console.error('Error in wildcard state listener:', error);
                }
            });
        }
    }

    /**
     * Batch updates multiple state values at once
     * Notifies listeners only once after all updates
     *
     * @param {Object} updates - Object with key-value pairs to update
     *
     * @example
     * store.batchUpdate({
     *     positions: newPositions,
     *     watchlist: newWatchlist,
     *     isRefreshing: false
     * });
     */
    batchUpdate(updates) {
        const changes = [];

        // Apply all updates
        Object.entries(updates).forEach(([key, value]) => {
            const oldValue = this._state[key];
            this._state[key] = value;
            changes.push({ key, value, oldValue });
        });

        // Notify listeners after all updates
        changes.forEach(({ key, value, oldValue }) => {
            this._notify(key, value, oldValue);
        });
    }

    /**
     * Updates a nested property in the state
     *
     * @param {string} key - The top-level state key
     * @param {string|number} path - The nested property path
     * @param {any} value - The new value
     *
     * @example
     * store.updateNested('positions', 0, { ...updatedPosition });
     */
    updateNested(key, path, value) {
        const oldValue = this._state[key];
        const newValue = Array.isArray(oldValue) ? [...oldValue] : { ...oldValue };

        if (typeof path === 'number') {
            newValue[path] = value;
        } else {
            const keys = path.split('.');
            let current = newValue;
            for (let i = 0; i < keys.length - 1; i++) {
                current = current[keys[i]];
            }
            current[keys[keys.length - 1]] = value;
        }

        this.setState(key, newValue);
    }

    /**
     * Resets state to initial values
     *
     * @example
     * store.reset();
     */
    reset() {
        this._state = {
            positions: [],
            watchlist: [],
            journalEntries: [],
            scanData: null,
            themesData: null,
            activityItems: [],
            currentTab: 'scan',
            lastUpdate: null,
            isRefreshing: false
        };

        // Notify all listeners
        Object.keys(this._state).forEach(key => {
            this._notify(key, this._state[key], undefined);
        });
    }

    /**
     * Computes a derived value from the state
     *
     * @param {Function} selector - Function that takes state and returns derived value
     * @returns {any} The computed value
     *
     * @example
     * const activePositions = store.compute(state =>
     *     state.positions.filter(p => p.status === 'active')
     * );
     */
    compute(selector) {
        return selector(this._state);
    }

    /**
     * Clears all listeners
     *
     * @example
     * store.clearListeners();
     */
    clearListeners() {
        this._listeners.clear();
    }
}

// Export singleton instance
export const store = new AppStore();
