/**
 * Authentication utilities
 * @module utils/auth
 */

/**
 * Retrieves CSRF token from meta tag or cookie
 *
 * @returns {string|null} The CSRF token or null if not found
 *
 * @example
 * const token = getCSRFToken();
 * headers['X-CSRF-Token'] = token;
 */
export function getCSRFToken() {
    // First, try to get from meta tag
    const meta = document.querySelector('meta[name="csrf-token"]');
    if (meta) return meta.content;

    // Fallback to cookie
    const cookie = document.cookie
        .split('; ')
        .find(row => row.startsWith('csrf_token='));
    if (cookie) return cookie.split('=')[1];

    return null;
}

/**
 * Retrieves authentication Bearer token from localStorage
 *
 * @returns {string|null} The auth token or null if not found
 *
 * @example
 * const token = getAuthToken();
 * headers['Authorization'] = `Bearer ${token}`;
 */
export function getAuthToken() {
    return localStorage.getItem('auth_token');
}

/**
 * Sets authentication token in localStorage
 *
 * @param {string} token - The token to store
 *
 * @example
 * setAuthToken('abc123xyz');
 */
export function setAuthToken(token) {
    if (token) {
        localStorage.setItem('auth_token', token);
    } else {
        localStorage.removeItem('auth_token');
    }
}

/**
 * Clears authentication token from localStorage
 *
 * @example
 * clearAuthToken();
 */
export function clearAuthToken() {
    localStorage.removeItem('auth_token');
}

/**
 * Checks if user is authenticated (has valid token)
 *
 * @returns {boolean} True if authenticated, false otherwise
 *
 * @example
 * if (isAuthenticated()) {
 *     // Load user data
 * }
 */
export function isAuthenticated() {
    const token = getAuthToken();
    return token !== null && token !== '';
}
