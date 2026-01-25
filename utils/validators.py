"""
Input validation and security utilities.

Addresses:
- Unvalidated webhook URLs
- No ticker input validation
- Missing webhook signature verification

Usage:
    from utils.validators import validate_ticker, validate_webhook_url

    ticker = validate_ticker(user_input)  # Raises ValidationError if invalid
    url = validate_webhook_url(webhook_url)  # Raises ValidationError if unsafe
"""
import re
import hmac
import hashlib
from typing import Optional
from urllib.parse import urlparse


class ValidationError(Exception):
    """Input validation failed."""
    def __init__(self, message: str, field: str = None):
        super().__init__(message)
        self.field = field


# Valid ticker pattern: 1-5 alphanumeric characters, optionally with dots (BRK.B)
TICKER_PATTERN = re.compile(r'^[A-Z]{1,5}(\.[A-Z])?$')

# Blocked tickers (reserved words, common mistakes)
BLOCKED_TICKERS = {
    'HELP', 'START', 'SCAN', 'NEWS', 'TEST', 'NULL', 'NONE', 'TRUE', 'FALSE',
    'MENU', 'STOP', 'EXIT', 'QUIT', 'INFO', 'LIST', 'ALL', 'GET', 'SET',
}


def validate_ticker(ticker: str) -> str:
    """
    Validate and normalize a stock ticker symbol.

    Args:
        ticker: Input ticker string

    Returns:
        Normalized uppercase ticker

    Raises:
        ValidationError: If ticker is invalid

    Examples:
        >>> validate_ticker('aapl')
        'AAPL'
        >>> validate_ticker('$NVDA')
        'NVDA'
        >>> validate_ticker('BRK.B')
        'BRK.B'
    """
    if not ticker:
        raise ValidationError("Ticker cannot be empty", field="ticker")

    # Normalize
    ticker = ticker.upper().strip()

    # Remove common prefixes users might add
    ticker = ticker.lstrip('$')

    # Check pattern
    if not TICKER_PATTERN.match(ticker):
        raise ValidationError(
            f"Invalid ticker format: '{ticker}'. "
            "Tickers must be 1-5 letters, optionally with a dot (e.g., BRK.B)",
            field="ticker"
        )

    # Check blocked list
    if ticker in BLOCKED_TICKERS:
        raise ValidationError(f"'{ticker}' is a reserved word, not a valid ticker", field="ticker")

    return ticker


def is_valid_ticker(ticker: str) -> bool:
    """
    Check if ticker is valid without raising exception.

    Args:
        ticker: Ticker to check

    Returns:
        True if valid, False otherwise
    """
    try:
        validate_ticker(ticker)
        return True
    except ValidationError:
        return False


def validate_webhook_url(url: str) -> str:
    """
    Validate a webhook URL for security.

    Args:
        url: URL to validate

    Returns:
        Validated URL

    Raises:
        ValidationError: If URL is invalid or unsafe
    """
    if not url:
        raise ValidationError("URL cannot be empty", field="url")

    try:
        parsed = urlparse(url)
    except Exception:
        raise ValidationError("Invalid URL format", field="url")

    # Must be HTTPS
    if parsed.scheme != 'https':
        raise ValidationError("Webhook URL must use HTTPS", field="url")

    # Must have a valid host
    if not parsed.netloc:
        raise ValidationError("Invalid URL host", field="url")

    hostname = parsed.hostname or ''

    # Block localhost/internal IPs
    blocked_hosts = ['localhost', '127.0.0.1', '0.0.0.0', '::1', '[::1]']
    if hostname.lower() in blocked_hosts:
        raise ValidationError("Localhost URLs are not allowed", field="url")

    # Block internal IP ranges
    if _is_internal_ip(hostname):
        raise ValidationError("Internal IP addresses are not allowed", field="url")

    return url


def _is_internal_ip(hostname: str) -> bool:
    """Check if hostname is an internal IP address."""
    parts = hostname.split('.')
    if len(parts) != 4:
        return False

    try:
        octets = [int(p) for p in parts]
    except ValueError:
        return False

    # 10.x.x.x
    if octets[0] == 10:
        return True

    # 172.16.x.x - 172.31.x.x
    if octets[0] == 172 and 16 <= octets[1] <= 31:
        return True

    # 192.168.x.x
    if octets[0] == 192 and octets[1] == 168:
        return True

    # 169.254.x.x (link-local)
    if octets[0] == 169 and octets[1] == 254:
        return True

    return False


def validate_webhook_signature(
    payload: bytes,
    signature: str,
    secret: Optional[str] = None
) -> bool:
    """
    Verify webhook signature using HMAC-SHA256.

    Args:
        payload: Raw request body
        signature: Signature from X-Telegram-Bot-Api-Secret-Token header
        secret: Webhook secret (uses config if not provided)

    Returns:
        True if signature is valid
    """
    # Lazy import to avoid circular dependency
    if secret is None:
        from config import config
        secret = config.security.webhook_secret

    if not secret:
        # No secret configured - log warning but allow
        from utils.logging_config import get_logger
        get_logger(__name__).warning("Webhook signature verification skipped - no secret configured")
        return True

    if not signature:
        from utils.logging_config import get_logger
        get_logger(__name__).warning("Missing webhook signature")
        return False

    expected = hmac.new(
        secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(signature, expected)


def sanitize_input(text: str, max_length: int = 1000) -> str:
    """
    Sanitize user input text.

    Removes control characters and limits length.

    Args:
        text: Input text
        max_length: Maximum allowed length

    Returns:
        Sanitized text
    """
    if not text:
        return ""

    # Truncate
    text = text[:max_length]

    # Remove control characters (except newlines and tabs)
    text = ''.join(
        char for char in text
        if char >= ' ' or char in '\n\t'
    )

    return text.strip()


def validate_price(price: str) -> float:
    """
    Validate a price value.

    Args:
        price: Price string

    Returns:
        Float price value

    Raises:
        ValidationError: If price is invalid
    """
    try:
        value = float(price)
    except (ValueError, TypeError):
        raise ValidationError(f"Invalid price: '{price}'", field="price")

    if value <= 0:
        raise ValidationError("Price must be positive", field="price")

    if value > 1_000_000:
        raise ValidationError("Price seems unreasonably high", field="price")

    return value


def validate_quantity(quantity: str) -> int:
    """
    Validate a quantity/shares value.

    Args:
        quantity: Quantity string

    Returns:
        Integer quantity

    Raises:
        ValidationError: If quantity is invalid
    """
    try:
        value = int(quantity)
    except (ValueError, TypeError):
        raise ValidationError(f"Invalid quantity: '{quantity}'", field="quantity")

    if value <= 0:
        raise ValidationError("Quantity must be positive", field="quantity")

    if value > 1_000_000_000:
        raise ValidationError("Quantity seems unreasonably high", field="quantity")

    return value


def validate_chat_id(chat_id: str) -> str:
    """
    Validate a Telegram chat ID.

    Args:
        chat_id: Chat ID string

    Returns:
        Validated chat ID

    Raises:
        ValidationError: If chat ID is invalid
    """
    if not chat_id:
        raise ValidationError("Chat ID cannot be empty", field="chat_id")

    # Chat IDs can be negative (for groups)
    try:
        int(chat_id)
    except (ValueError, TypeError):
        raise ValidationError(f"Invalid chat ID: '{chat_id}'", field="chat_id")

    return str(chat_id)
