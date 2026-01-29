/**
 * Input validation utilities
 * @module utils/validators
 */

/**
 * Validates ticker symbol format
 * Allows 1-5 uppercase letters or numbers
 *
 * @param {string} ticker - The ticker symbol to validate
 * @returns {string} The cleaned and validated ticker symbol
 * @throws {Error} If ticker format is invalid
 *
 * @example
 * validateTicker('AAPL')  // Returns: 'AAPL'
 * validateTicker('aapl')  // Returns: 'AAPL' (auto-uppercase)
 * validateTicker('TOOLONG')  // Throws: Error
 */
export function validateTicker(ticker) {
    const cleaned = ticker.trim().toUpperCase();

    if (!/^[A-Z0-9]{1,5}$/.test(cleaned)) {
        throw new Error('Invalid ticker format. Use 1-5 uppercase letters/numbers.');
    }

    return cleaned;
}

/**
 * Validates price input
 * Must be a positive number, maximum $999,999
 *
 * @param {string|number} priceStr - The price to validate
 * @returns {number} The validated price as a number
 * @throws {Error} If price is invalid
 *
 * @example
 * validatePrice('123.45')  // Returns: 123.45
 * validatePrice('-100')    // Throws: Error
 * validatePrice('abc')     // Throws: Error
 */
export function validatePrice(priceStr) {
    const price = parseFloat(priceStr);

    if (isNaN(price)) {
        throw new Error('Price must be a number');
    }

    if (price <= 0) {
        throw new Error('Price must be positive');
    }

    if (price > 999999) {
        throw new Error('Price too high (max $999,999)');
    }

    return price;
}

/**
 * Validates shares quantity
 * Must be a positive integer, maximum 1,000,000
 *
 * @param {string|number} sharesStr - The shares quantity to validate
 * @returns {number} The validated shares as an integer
 * @throws {Error} If shares quantity is invalid
 *
 * @example
 * validateShares('100')    // Returns: 100
 * validateShares('0')      // Throws: Error
 * validateShares('-50')    // Throws: Error
 */
export function validateShares(sharesStr) {
    const shares = parseInt(sharesStr, 10);

    if (isNaN(shares)) {
        throw new Error('Shares must be a number');
    }

    if (shares <= 0) {
        throw new Error('Shares must be positive');
    }

    if (shares > 1000000) {
        throw new Error('Shares too high (max 1,000,000)');
    }

    return shares;
}

/**
 * Validates text input with length constraints
 * Used for thesis, journal entries, notes, etc.
 *
 * @param {string} text - The text to validate
 * @param {number} [minLength=10] - Minimum allowed length
 * @param {number} [maxLength=1000] - Maximum allowed length
 * @returns {string} The cleaned and validated text
 * @throws {Error} If text length is invalid
 *
 * @example
 * validateText('This is a valid thesis', 10, 1000)  // Returns: 'This is a valid thesis'
 * validateText('Short', 10, 1000)  // Throws: Error (too short)
 */
export function validateText(text, minLength = 10, maxLength = 1000) {
    const cleaned = text.trim();

    if (cleaned.length < minLength) {
        throw new Error(`Text must be at least ${minLength} characters`);
    }

    if (cleaned.length > maxLength) {
        throw new Error(`Text too long (max ${maxLength} characters)`);
    }

    return cleaned;
}

/**
 * Validates a deal price specifically
 * Similar to validatePrice but with different messaging
 *
 * @param {string|number} priceStr - The deal price to validate
 * @returns {number} The validated deal price
 * @throws {Error} If deal price is invalid
 *
 * @example
 * validateDealPrice('142.50')  // Returns: 142.5
 */
export function validateDealPrice(priceStr) {
    const price = parseFloat(priceStr);

    if (isNaN(price) || !priceStr) {
        throw new Error('Please enter a valid deal price');
    }

    if (price <= 0) {
        throw new Error('Deal price must be positive');
    }

    if (price > 999999) {
        throw new Error('Deal price too high (max $999,999)');
    }

    return price;
}

/**
 * Validates a company/ticker name
 * Allows letters, numbers, spaces, and some special characters
 *
 * @param {string} name - The company/ticker name to validate
 * @returns {string} The cleaned and validated name
 * @throws {Error} If name is invalid
 *
 * @example
 * validateCompanyName('Apple Inc.')  // Returns: 'Apple Inc.'
 * validateCompanyName('')  // Throws: Error
 */
export function validateCompanyName(name) {
    const cleaned = name.trim();

    if (cleaned.length === 0) {
        throw new Error('Company name cannot be empty');
    }

    if (cleaned.length > 100) {
        throw new Error('Company name too long (max 100 characters)');
    }

    // Allow letters, numbers, spaces, periods, commas, ampersands
    if (!/^[a-zA-Z0-9\s.,&'-]+$/.test(cleaned)) {
        throw new Error('Company name contains invalid characters');
    }

    return cleaned;
}
