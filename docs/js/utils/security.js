/**
 * Security utilities for XSS prevention
 * @module utils/security
 */

/**
 * Escapes HTML special characters to prevent XSS attacks
 *
 * @param {string} str - The string to escape
 * @returns {string} The escaped string safe for HTML insertion
 *
 * @example
 * escapeHTML('<script>alert("xss")</script>')
 * // Returns: '&lt;script&gt;alert("xss")&lt;/script&gt;'
 */
export function escapeHTML(str) {
    if (typeof str !== 'string') return str;

    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

/**
 * Sanitizes HTML content using DOMPurify
 * Only allows safe tags and attributes
 *
 * @param {string} html - The HTML string to sanitize
 * @returns {string} Sanitized HTML safe for insertion
 *
 * @example
 * sanitizeHTML('<div onclick="alert(1)">Hello</div>')
 * // Returns: '<div>Hello</div>' (onclick removed)
 */
export function sanitizeHTML(html) {
    if (typeof html !== 'string') return '';

    // Check if DOMPurify is available
    if (typeof DOMPurify === 'undefined') {
        console.warn('DOMPurify not loaded, falling back to basic escaping');
        return escapeHTML(html);
    }

    return DOMPurify.sanitize(html, {
        ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'a', 'br', 'div', 'span', 'p', 'ul', 'ol', 'li'],
        ALLOWED_ATTR: ['href', 'class', 'style', 'target']
    });
}

/**
 * Escapes a string for use in HTML attributes
 * Handles quotes and special characters
 *
 * @param {string} str - The string to escape for attribute use
 * @returns {string} The escaped string safe for HTML attributes
 *
 * @example
 * escapeHTMLAttribute("ticker's value")
 * // Returns: "ticker&#39;s value"
 */
export function escapeHTMLAttribute(str) {
    if (typeof str !== 'string') return str;

    return str
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}
