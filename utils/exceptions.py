"""
Custom exceptions for StockStory.

Use these instead of bare except: blocks for proper error handling.

Usage:
    from utils.exceptions import DataFetchError, InsufficientDataError

    try:
        df = download_data(ticker)
    except DataFetchError as e:
        logger.error(f"Failed to fetch data: {e}")
"""


class StockStoryError(Exception):
    """Base exception for all StockStory errors."""
    pass


# Backwards compatibility alias
StockScannerError = StockStoryError


class DataFetchError(StockScannerError):
    """
    Failed to fetch data from external source.

    Use when yfinance, APIs, or web scraping fails.
    """
    pass


class DataValidationError(StockScannerError):
    """
    Data validation failed.

    Use when data doesn't meet expected format or constraints.
    """
    pass


class InsufficientDataError(StockScannerError):
    """
    Not enough data points for calculation.

    Use when a calculation requires N data points but fewer are available.
    """
    def __init__(self, message: str = None, required: int = None, available: int = None):
        if message is None and required is not None:
            message = f"Need {required} data points, only {available} available"
        super().__init__(message)
        self.required = required
        self.available = available


class ConfigurationError(StockScannerError):
    """
    Configuration is invalid or missing.

    Use when required environment variables or settings are missing.
    """
    pass


class APIError(StockScannerError):
    """
    External API returned an error.

    Use for DeepSeek, Telegram, or other API errors.
    """
    def __init__(self, message: str, status_code: int = None, response: str = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response

    def __str__(self):
        base = super().__str__()
        if self.status_code:
            return f"{base} (status={self.status_code})"
        return base


class RateLimitError(APIError):
    """
    Rate limit exceeded.

    Use when an API returns 429 or similar rate limit response.
    """
    def __init__(self, retry_after: int = 60, service: str = "API"):
        super().__init__(f"{service} rate limited, retry after {retry_after}s", status_code=429)
        self.retry_after = retry_after
        self.service = service


class TelegramError(APIError):
    """
    Telegram API error.

    Use for Telegram-specific errors.
    """
    pass


class TelegramRateLimitError(TelegramError, RateLimitError):
    """Telegram rate limit exceeded."""
    def __init__(self, retry_after: int = 60):
        RateLimitError.__init__(self, retry_after=retry_after, service="Telegram")
