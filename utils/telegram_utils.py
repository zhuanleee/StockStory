"""
Centralized Telegram messaging utilities.

Consolidates 4 duplicate implementations from:
- app.py:39 - send_message()
- app.py:62 - send_photo()
- scanner_automation.py:124 - send_telegram_message()
- story_alerts.py:29 - send_telegram_alert()

Features:
- Message sending with automatic truncation
- Photo sending with caption support
- Retry logic with exponential backoff
- Rate limit handling

Usage:
    from utils.telegram_utils import send_message, send_photo, TelegramClient

    # Simple usage with default client
    send_message(chat_id, "Hello!")
    send_photo(chat_id, photo_buffer, "Caption")

    # Or create custom client
    client = TelegramClient(bot_token="...", default_chat_id="...")
    client.send_message(chat_id, "Hello!")
"""
import time
from typing import Optional, BinaryIO, Union
from functools import wraps
import threading

import requests

from utils.logging_config import get_logger
from utils.exceptions import TelegramError, TelegramRateLimitError

logger = get_logger(__name__)


def retry_on_failure(max_retries: int = 3, base_delay: float = 1.0):
    """
    Decorator for retry logic on transient failures.

    Uses exponential backoff: delay * (2 ** attempt)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except TelegramRateLimitError:
                    raise  # Don't retry rate limits
                except TelegramError as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        sleep_time = base_delay * (2 ** attempt)
                        logger.warning(f"Retry {attempt + 1}/{max_retries} after {sleep_time}s: {e}")
                        time.sleep(sleep_time)
                except requests.RequestException as e:
                    last_exception = TelegramError(str(e))
                    if attempt < max_retries - 1:
                        sleep_time = base_delay * (2 ** attempt)
                        logger.warning(f"Retry {attempt + 1}/{max_retries} after {sleep_time}s: {e}")
                        time.sleep(sleep_time)
            if last_exception:
                raise last_exception
            return None
        return wrapper
    return decorator


class TelegramClient:
    """
    Thread-safe Telegram API client.

    Usage:
        client = TelegramClient()
        client.send_message(chat_id, "Hello!")
        client.send_photo(chat_id, photo_buffer, "Caption")
    """

    def __init__(
        self,
        bot_token: Optional[str] = None,
        default_chat_id: Optional[str] = None
    ):
        """
        Initialize Telegram client.

        Args:
            bot_token: Bot token (uses config if not provided)
            default_chat_id: Default chat ID for sending (uses config if not provided)
        """
        # Lazy load config
        from config import config

        self.bot_token = bot_token or config.telegram.bot_token
        self.default_chat_id = default_chat_id or config.telegram.chat_id
        self._config = config
        self._lock = threading.Lock()

        if not self.bot_token:
            logger.warning("Telegram bot token not configured")

    @property
    def api_base(self) -> str:
        """Get API base URL."""
        return f"{self._config.telegram.api_base}/bot{self.bot_token}"

    @property
    def is_configured(self) -> bool:
        """Check if Telegram is properly configured."""
        return bool(self.bot_token)

    @retry_on_failure(max_retries=3)
    def send_message(
        self,
        chat_id: Optional[str] = None,
        text: str = "",
        parse_mode: str = 'Markdown',
        disable_preview: bool = True,
        reply_to_message_id: Optional[int] = None,
    ) -> bool:
        """
        Send text message to Telegram.

        Args:
            chat_id: Target chat ID (uses default if not specified)
            text: Message text
            parse_mode: 'Markdown' or 'HTML'
            disable_preview: Disable link previews
            reply_to_message_id: Message ID to reply to

        Returns:
            True if successful, False otherwise

        Raises:
            TelegramError: On API errors
            TelegramRateLimitError: On rate limit
        """
        if not self.is_configured:
            logger.debug(f"[Telegram disabled] Message: {text[:100]}...")
            return False

        chat_id = chat_id or self.default_chat_id
        if not chat_id:
            logger.error("No chat_id specified and no default configured")
            return False

        # Truncate if too long
        max_length = self._config.telegram.message_max_length
        if len(text) > max_length:
            text = text[:max_length - 20] + "\n\n_...truncated_"

        payload = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': parse_mode,
            'disable_web_page_preview': disable_preview,
        }

        if reply_to_message_id:
            payload['reply_to_message_id'] = reply_to_message_id

        try:
            response = requests.post(
                f"{self.api_base}/sendMessage",
                json=payload,
                timeout=self._config.telegram.request_timeout
            )

            if response.status_code == 429:
                retry_after = response.json().get('parameters', {}).get('retry_after', 60)
                logger.warning(f"Telegram rate limited, retry after {retry_after}s")
                raise TelegramRateLimitError(retry_after=retry_after)

            if response.status_code != 200:
                error_msg = response.json().get('description', response.text)
                logger.error(f"Telegram API error: {response.status_code} - {error_msg}")
                raise TelegramError(error_msg, status_code=response.status_code)

            return True

        except requests.Timeout:
            logger.error("Telegram request timeout")
            raise TelegramError("Request timeout")
        except requests.RequestException as e:
            logger.error(f"Network error sending message: {e}")
            raise TelegramError(f"Network error: {e}")

    @retry_on_failure(max_retries=2)
    def send_photo(
        self,
        chat_id: Optional[str] = None,
        photo: Union[BinaryIO, bytes] = None,
        caption: str = "",
        parse_mode: str = 'Markdown',
        filename: str = 'chart.png',
    ) -> bool:
        """
        Send photo to Telegram.

        Args:
            chat_id: Target chat ID
            photo: Photo file buffer or bytes
            caption: Photo caption
            parse_mode: Caption parse mode
            filename: Filename for the photo

        Returns:
            True if successful

        Raises:
            TelegramError: On API errors
        """
        if not self.is_configured or photo is None:
            return False

        chat_id = chat_id or self.default_chat_id
        if not chat_id:
            logger.error("No chat_id specified for photo")
            return False

        # Truncate caption
        max_caption = self._config.telegram.photo_caption_max_length
        if len(caption) > max_caption:
            caption = caption[:max_caption - 3] + "..."

        # Handle bytes vs file-like object
        if isinstance(photo, bytes):
            files = {'photo': (filename, photo, 'image/png')}
        else:
            files = {'photo': (filename, photo, 'image/png')}

        try:
            response = requests.post(
                f"{self.api_base}/sendPhoto",
                files=files,
                data={
                    'chat_id': chat_id,
                    'caption': caption,
                    'parse_mode': parse_mode,
                },
                timeout=self._config.telegram.photo_timeout
            )

            if response.status_code == 429:
                retry_after = response.json().get('parameters', {}).get('retry_after', 60)
                raise TelegramRateLimitError(retry_after=retry_after)

            if response.status_code != 200:
                error_msg = response.json().get('description', response.text)
                logger.error(f"Telegram photo error: {response.status_code} - {error_msg}")
                raise TelegramError(error_msg, status_code=response.status_code)

            return True

        except requests.Timeout:
            logger.error("Telegram photo request timeout")
            raise TelegramError("Photo request timeout")
        except requests.RequestException as e:
            logger.error(f"Error sending photo: {e}")
            raise TelegramError(f"Network error: {e}")

    def send_message_safe(
        self,
        chat_id: Optional[str] = None,
        text: str = "",
        **kwargs
    ) -> bool:
        """
        Send message without raising exceptions.

        Returns False on any error instead of raising.
        """
        try:
            return self.send_message(chat_id, text, **kwargs)
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False

    def send_photo_safe(
        self,
        chat_id: Optional[str] = None,
        photo: Union[BinaryIO, bytes] = None,
        caption: str = "",
        **kwargs
    ) -> bool:
        """
        Send photo without raising exceptions.

        Returns False on any error instead of raising.
        """
        try:
            return self.send_photo(chat_id, photo, caption, **kwargs)
        except Exception as e:
            logger.error(f"Failed to send photo: {e}")
            return False


# Default client instance (lazy initialized)
_default_client: Optional[TelegramClient] = None
_client_lock = threading.Lock()


def get_telegram_client() -> TelegramClient:
    """Get or create the default Telegram client."""
    global _default_client
    with _client_lock:
        if _default_client is None:
            _default_client = TelegramClient()
        return _default_client


def reset_telegram_client():
    """Reset the default client. Useful for testing."""
    global _default_client
    with _client_lock:
        _default_client = None


# Convenience functions for backward compatibility
def send_message(
    chat_id: str,
    text: str,
    parse_mode: str = 'Markdown',
    **kwargs
) -> bool:
    """
    Send message using default client.

    This is a drop-in replacement for the old send_message function.
    """
    return get_telegram_client().send_message_safe(chat_id, text, parse_mode=parse_mode, **kwargs)


def send_photo(
    chat_id: str,
    photo: Union[BinaryIO, bytes],
    caption: str = '',
    **kwargs
) -> bool:
    """
    Send photo using default client.

    This is a drop-in replacement for the old send_photo function.
    """
    return get_telegram_client().send_photo_safe(chat_id, photo, caption, **kwargs)
