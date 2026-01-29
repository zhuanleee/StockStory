/**
 * Formatting utilities for numbers, dates, and display values
 * @module utils/formatters
 */

/**
 * Safely formats a number to fixed decimal places, handling null/undefined/NaN
 *
 * @param {number|null|undefined} value - The value to format
 * @param {number} [decimals=2] - Number of decimal places (default: 2)
 * @returns {string} Formatted number string or '--' if value is invalid
 *
 * @example
 * safeFixed(123.456, 2)  // "123.46"
 * safeFixed(null, 2)     // "--"
 * safeFixed(NaN, 2)      // "--"
 */
export function safeFixed(value, decimals = 2) {
    if (value === null || value === undefined || isNaN(value)) return '--';
    return Number(value).toFixed(decimals);
}

/**
 * Formats volume numbers with K/M/B suffixes
 *
 * @param {number} volume - The volume to format
 * @returns {string} Formatted volume string
 *
 * @example
 * formatVolume(1500000)     // "1.50M"
 * formatVolume(2500000000)  // "2.50B"
 * formatVolume(500000)      // "500.00K"
 */
export function formatVolume(volume) {
    if (!volume || volume === 0) return '--';
    if (volume >= 1e9) return (volume / 1e9).toFixed(2) + 'B';
    if (volume >= 1e6) return (volume / 1e6).toFixed(2) + 'M';
    if (volume >= 1e3) return (volume / 1e3).toFixed(2) + 'K';
    return volume.toString();
}

/**
 * Formats a price with dollar sign and appropriate decimal places
 *
 * @param {number} price - The price to format
 * @param {number} [decimals=2] - Number of decimal places
 * @returns {string} Formatted price string
 *
 * @example
 * formatPrice(123.456)   // "$123.46"
 * formatPrice(null)      // "--"
 */
export function formatPrice(price, decimals = 2) {
    if (price === null || price === undefined || isNaN(price)) return '--';
    return '$' + Number(price).toFixed(decimals);
}

/**
 * Formats a percentage value with sign and color
 *
 * @param {number} value - The percentage value
 * @param {number} [decimals=2] - Number of decimal places
 * @returns {string} Formatted percentage string
 *
 * @example
 * formatPercent(5.2)     // "+5.20%"
 * formatPercent(-2.3)    // "-2.30%"
 */
export function formatPercent(value, decimals = 2) {
    if (value === null || value === undefined || isNaN(value)) return '--';
    const sign = value >= 0 ? '+' : '';
    return sign + Number(value).toFixed(decimals) + '%';
}

/**
 * Formats a date to a readable string
 *
 * @param {string|Date} date - The date to format
 * @returns {string} Formatted date string
 *
 * @example
 * formatDate('2024-01-15')  // "Jan 15, 2024"
 */
export function formatDate(date) {
    if (!date) return '--';
    const d = typeof date === 'string' ? new Date(date) : date;
    if (isNaN(d.getTime())) return '--';
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

/**
 * Formats a date to a short string (e.g., "Jan 15")
 *
 * @param {string|Date} date - The date to format
 * @returns {string} Formatted date string
 *
 * @example
 * formatDateShort('2024-01-15')  // "Jan 15"
 */
export function formatDateShort(date) {
    if (!date) return '--';
    const d = typeof date === 'string' ? new Date(date) : date;
    if (isNaN(d.getTime())) return '--';
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

/**
 * Formats a timestamp to time string
 *
 * @param {string|Date} timestamp - The timestamp to format
 * @returns {string} Formatted time string
 *
 * @example
 * formatTime(new Date())  // "2:30 PM"
 */
export function formatTime(timestamp) {
    if (!timestamp) return '--';
    const d = typeof timestamp === 'string' ? new Date(timestamp) : timestamp;
    if (isNaN(d.getTime())) return '--';
    return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
}

/**
 * Formats a large number with commas
 *
 * @param {number} num - The number to format
 * @returns {string} Formatted number string
 *
 * @example
 * formatNumber(1234567)  // "1,234,567"
 */
export function formatNumber(num) {
    if (num === null || num === undefined || isNaN(num)) return '--';
    return Number(num).toLocaleString('en-US');
}

/**
 * Truncates text to a maximum length with ellipsis
 *
 * @param {string} text - The text to truncate
 * @param {number} maxLength - Maximum length
 * @returns {string} Truncated text
 *
 * @example
 * truncate('This is a long text', 10)  // "This is a..."
 */
export function truncate(text, maxLength) {
    if (!text || text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}
