/**
 * DOM Element Caching Utility
 * Reduces repeated querySelector calls by caching element references
 * @module utils/dom-cache
 */

/**
 * DOMCache class for caching DOM element references
 */
export class DOMCache {
    constructor() {
        this.cache = new Map();
    }

    /**
     * Gets an element by ID (cached)
     *
     * @param {string} id - The element ID
     * @returns {HTMLElement|null} The cached element or null if not found
     *
     * @example
     * const container = dom.get('scan-table-body');
     */
    get(id) {
        if (!this.cache.has(id)) {
            const element = document.getElementById(id);
            if (element) {
                this.cache.set(id, element);
            }
        }
        return this.cache.get(id) || null;
    }

    /**
     * Queries an element by selector (cached)
     *
     * @param {string} selector - The CSS selector
     * @returns {HTMLElement|null} The cached element or null if not found
     *
     * @example
     * const header = dom.query('.dashboard-header');
     */
    query(selector) {
        if (!this.cache.has(selector)) {
            const element = document.querySelector(selector);
            if (element) {
                this.cache.set(selector, element);
            }
        }
        return this.cache.get(selector) || null;
    }

    /**
     * Queries all elements by selector (cached)
     *
     * @param {string} selector - The CSS selector
     * @returns {NodeList|Array} The cached NodeList or empty array
     *
     * @example
     * const tabs = dom.queryAll('.nav-tab');
     */
    queryAll(selector) {
        if (!this.cache.has(selector)) {
            const elements = document.querySelectorAll(selector);
            if (elements.length > 0) {
                this.cache.set(selector, elements);
            }
        }
        return this.cache.get(selector) || [];
    }

    /**
     * Sets an element in the cache manually
     *
     * @param {string} key - The cache key
     * @param {HTMLElement|NodeList} element - The element to cache
     *
     * @example
     * dom.set('custom-key', myElement);
     */
    set(key, element) {
        this.cache.set(key, element);
    }

    /**
     * Checks if an element is cached
     *
     * @param {string} key - The cache key
     * @returns {boolean} True if element is cached
     *
     * @example
     * if (dom.has('scan-table-body')) {
     *     // Element is cached
     * }
     */
    has(key) {
        return this.cache.has(key);
    }

    /**
     * Clears the entire cache
     *
     * @example
     * dom.clear();
     */
    clear() {
        this.cache.clear();
    }

    /**
     * Invalidates (removes) a specific cache entry
     *
     * @param {string} key - The cache key to invalidate
     *
     * @example
     * dom.invalidate('scan-table-body');
     */
    invalidate(key) {
        this.cache.delete(key);
    }

    /**
     * Invalidates multiple cache entries by pattern
     *
     * @param {string|RegExp} pattern - Pattern to match keys against
     *
     * @example
     * dom.invalidatePattern('scan-'); // Invalidates all scan-* keys
     * dom.invalidatePattern(/^scan-/); // Using regex
     */
    invalidatePattern(pattern) {
        const regex = typeof pattern === 'string'
            ? new RegExp(pattern)
            : pattern;

        for (const key of this.cache.keys()) {
            if (regex.test(key)) {
                this.cache.delete(key);
            }
        }
    }

    /**
     * Gets cache size
     *
     * @returns {number} Number of cached elements
     *
     * @example
     * console.log(`Cache size: ${dom.size()}`);
     */
    size() {
        return this.cache.size;
    }

    /**
     * Gets all cache keys
     *
     * @returns {Array<string>} Array of all cache keys
     *
     * @example
     * const keys = dom.keys();
     */
    keys() {
        return Array.from(this.cache.keys());
    }

    /**
     * Refreshes cache for a specific key
     * Forces re-query of the element
     *
     * @param {string} key - The cache key to refresh
     * @returns {HTMLElement|NodeList|null} The refreshed element
     *
     * @example
     * dom.refresh('scan-table-body');
     */
    refresh(key) {
        this.cache.delete(key);

        // Try to get by ID first
        let element = document.getElementById(key);
        if (element) {
            this.cache.set(key, element);
            return element;
        }

        // Otherwise query as selector
        element = document.querySelector(key);
        if (element) {
            this.cache.set(key, element);
            return element;
        }

        // Try queryAll
        const elements = document.querySelectorAll(key);
        if (elements.length > 0) {
            this.cache.set(key, elements);
            return elements;
        }

        return null;
    }

    /**
     * Creates a DocumentFragment for efficient DOM manipulation
     *
     * @returns {DocumentFragment} A new DocumentFragment
     *
     * @example
     * const fragment = dom.createFragment();
     * fragment.appendChild(element1);
     * fragment.appendChild(element2);
     * container.appendChild(fragment);
     */
    createFragment() {
        return document.createDocumentFragment();
    }

    /**
     * Replaces all children of an element efficiently
     * Uses replaceChildren for better performance than innerHTML
     *
     * @param {string|HTMLElement} target - Target element or ID
     * @param {DocumentFragment|HTMLElement|Array<HTMLElement>} content - New content
     *
     * @example
     * const fragment = dom.createFragment();
     * // ... add children to fragment
     * dom.replaceChildren('container-id', fragment);
     */
    replaceChildren(target, content) {
        const element = typeof target === 'string' ? this.get(target) : target;
        if (!element) return;

        if (Array.isArray(content)) {
            element.replaceChildren(...content);
        } else {
            element.replaceChildren(content);
        }
    }

    /**
     * Batch queries multiple elements
     * More efficient than calling get() multiple times
     *
     * @param {Array<string>} ids - Array of element IDs
     * @returns {Object} Object with id -> element mappings
     *
     * @example
     * const elements = dom.batchGet(['scan-table', 'modal', 'toast']);
     * elements['scan-table'].innerHTML = '...';
     */
    batchGet(ids) {
        const result = {};
        ids.forEach(id => {
            result[id] = this.get(id);
        });
        return result;
    }

    /**
     * Checks if element exists in DOM (not cached)
     *
     * @param {string} selector - Element selector or ID
     * @returns {boolean} True if element exists
     *
     * @example
     * if (dom.exists('scan-table-body')) {
     *     // Element exists in DOM
     * }
     */
    exists(selector) {
        return !!(document.getElementById(selector) || document.querySelector(selector));
    }
}

// Export singleton instance
export const dom = new DOMCache();
