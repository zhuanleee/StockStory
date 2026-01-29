/**
 * API Client with caching and request deduplication
 * @module api/client
 */

import { API_BASE_URL, TIMEOUTS } from '../config.js';
import { getAuthToken, getCSRFToken, clearAuthToken } from '../utils/auth.js';

/**
 * API Client class with caching and request deduplication
 */
export class APIClient {
    constructor(baseURL = API_BASE_URL) {
        this.baseURL = baseURL;
        this.pendingRequests = new Map(); // For deduplication
        this.cache = new Map(); // For caching
        this.cacheTTL = 60000; // 1 minute default TTL
    }

    /**
     * Performs a GET request
     *
     * @param {string} endpoint - The API endpoint (without base URL)
     * @param {Object} [options={}] - Additional fetch options
     * @returns {Promise<Object>} The response data
     *
     * @example
     * const data = await api.get('scan/top-picks');
     */
    async get(endpoint, options = {}) {
        return this._request('GET', endpoint, null, options);
    }

    /**
     * Performs a POST request
     *
     * @param {string} endpoint - The API endpoint
     * @param {Object} body - The request body
     * @param {Object} [options={}] - Additional fetch options
     * @returns {Promise<Object>} The response data
     *
     * @example
     * const result = await api.post('trades/create', { ticker: 'AAPL', ... });
     */
    async post(endpoint, body, options = {}) {
        return this._request('POST', endpoint, body, options);
    }

    /**
     * Performs a PUT request
     *
     * @param {string} endpoint - The API endpoint
     * @param {Object} body - The request body
     * @param {Object} [options={}] - Additional fetch options
     * @returns {Promise<Object>} The response data
     */
    async put(endpoint, body, options = {}) {
        return this._request('PUT', endpoint, body, options);
    }

    /**
     * Performs a DELETE request
     *
     * @param {string} endpoint - The API endpoint
     * @param {Object} [options={}] - Additional fetch options
     * @returns {Promise<Object>} The response data
     *
     * @example
     * await api.delete('trades/123');
     */
    async delete(endpoint, options = {}) {
        return this._request('DELETE', endpoint, null, options);
    }

    /**
     * Internal method to handle all requests
     * @private
     */
    async _request(method, endpoint, body, options) {
        const cacheKey = `${method}:${endpoint}:${JSON.stringify(body || {})}`;

        // Return cached response if available and fresh (GET only)
        if (method === 'GET') {
            const cached = this._getFromCache(cacheKey);
            if (cached) {
                console.debug(`Cache HIT: ${cacheKey}`);
                return cached;
            }
        }

        // Return existing promise if request in flight (deduplication)
        if (this.pendingRequests.has(cacheKey)) {
            console.debug(`Deduplication: ${cacheKey}`);
            return this.pendingRequests.get(cacheKey);
        }

        const promise = this._makeRequest(method, endpoint, body, options)
            .finally(() => this.pendingRequests.delete(cacheKey));

        this.pendingRequests.set(cacheKey, promise);

        const result = await promise;

        // Cache GET responses
        if (method === 'GET' && result) {
            this._addToCache(cacheKey, result);
        }

        // Invalidate cache for mutations
        if (['POST', 'PUT', 'DELETE'].includes(method)) {
            this.invalidateCache(endpoint.split('/')[0]); // Invalidate related cache
        }

        return result;
    }

    /**
     * Makes the actual HTTP request
     * @private
     */
    async _makeRequest(method, endpoint, body, options) {
        const timeout = options.timeout || TIMEOUTS.NORMAL;
        const url = `${this.baseURL}/${endpoint}`;
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), timeout);

        try {
            const headers = { 'Content-Type': 'application/json' };

            // Add authentication token if available
            const token = getAuthToken();
            if (token) {
                headers['Authorization'] = `Bearer ${token}`;
            }

            // Add CSRF token for mutation requests
            if (['POST', 'PUT', 'DELETE'].includes(method)) {
                const csrfToken = getCSRFToken();
                if (csrfToken) {
                    headers['X-CSRF-Token'] = csrfToken;
                }
            }

            const response = await fetch(url, {
                method,
                headers: { ...headers, ...options.headers },
                body: body ? JSON.stringify(body) : undefined,
                signal: controller.signal,
                ...options
            });

            clearTimeout(timeoutId);

            // Handle 401 Unauthorized
            if (response.status === 401) {
                clearAuthToken();
                console.warn('Unauthorized - token cleared');
                throw new Error('Unauthorized - please login');
            }

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            return await response.json();
        } catch (error) {
            clearTimeout(timeoutId);
            if (error.name === 'AbortError') {
                throw new Error('Request timed out');
            }
            this._handleError(endpoint, error);
            throw error;
        }
    }

    /**
     * Gets data from cache if fresh
     * @private
     */
    _getFromCache(key) {
        const cached = this.cache.get(key);
        if (cached && Date.now() - cached.timestamp < this.cacheTTL) {
            return cached.data;
        }
        return null;
    }

    /**
     * Adds data to cache
     * @private
     */
    _addToCache(key, data) {
        this.cache.set(key, { data, timestamp: Date.now() });
    }

    /**
     * Invalidates cache entries matching a pattern
     *
     * @param {string} pattern - The pattern to match (e.g., 'trades', 'scan')
     *
     * @example
     * api.invalidateCache('trades'); // Clears all trade-related cache
     */
    invalidateCache(pattern) {
        for (const key of this.cache.keys()) {
            if (key.includes(pattern)) {
                this.cache.delete(key);
            }
        }
    }

    /**
     * Clears all cache
     *
     * @example
     * api.clearCache();
     */
    clearCache() {
        this.cache.clear();
    }

    /**
     * Handles errors from API requests
     * @private
     */
    _handleError(endpoint, error) {
        console.error(`API Error [${endpoint}]:`, error);
        // Could send to error tracking service here (e.g., Sentry)
    }

    /**
     * Sets cache TTL (time-to-live)
     *
     * @param {number} ttl - TTL in milliseconds
     *
     * @example
     * api.setCacheTTL(120000); // 2 minutes
     */
    setCacheTTL(ttl) {
        this.cacheTTL = ttl;
    }
}

// Export singleton instance
export const api = new APIClient();
