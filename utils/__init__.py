"""
Utility modules for Stock Scanner Bot.

This package provides centralized utilities to eliminate code duplication:
- logging_config: Structured logging setup
- exceptions: Custom exception types
- data_utils: Data fetching and processing
- validators: Input validation
- telegram_utils: Telegram API client
"""
from .logging_config import get_logger, setup_logging
from .exceptions import (
    StockScannerError,
    DataFetchError,
    DataValidationError,
    InsufficientDataError,
    ConfigurationError,
    APIError,
    RateLimitError,
    TelegramError,
)
from .data_utils import (
    normalize_dataframe_columns,
    get_spy_data_cached,
    calculate_rs,
    safe_float,
    safe_get_series,
    download_stock_data,
    clear_spy_cache,
)
from .validators import (
    validate_ticker,
    validate_webhook_url,
    validate_webhook_signature,
    sanitize_input,
    validate_price,
    ValidationError,
)
from .telegram_utils import (
    TelegramClient,
    get_telegram_client,
    send_message,
    send_photo,
)

__all__ = [
    # Logging
    'get_logger',
    'setup_logging',
    # Exceptions
    'StockScannerError',
    'DataFetchError',
    'DataValidationError',
    'InsufficientDataError',
    'ConfigurationError',
    'APIError',
    'RateLimitError',
    'TelegramError',
    'ValidationError',
    # Data utilities
    'normalize_dataframe_columns',
    'get_spy_data_cached',
    'calculate_rs',
    'safe_float',
    'safe_get_series',
    'download_stock_data',
    'clear_spy_cache',
    # Validators
    'validate_ticker',
    'validate_webhook_url',
    'validate_webhook_signature',
    'sanitize_input',
    'validate_price',
    # Telegram
    'TelegramClient',
    'get_telegram_client',
    'send_message',
    'send_photo',
]
