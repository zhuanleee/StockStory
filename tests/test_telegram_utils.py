"""Tests for utils/telegram_utils.py"""
import pytest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path
import io

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.telegram_utils import (
    TelegramClient,
    get_telegram_client,
    reset_telegram_client,
    send_message,
    send_photo,
)
from utils.exceptions import TelegramError, TelegramRateLimitError


class TestTelegramClient:
    """Tests for TelegramClient class."""

    @pytest.fixture
    def mock_config(self):
        """Mock config for testing."""
        with patch('utils.telegram_utils.TelegramClient._TelegramClient__init__', return_value=None):
            yield

    @pytest.fixture
    def client(self):
        """Create a test client."""
        with patch('config.config') as mock_config:
            mock_config.telegram.bot_token = 'test_token'
            mock_config.telegram.chat_id = '123456'
            mock_config.telegram.api_base = 'https://api.telegram.org'
            mock_config.telegram.message_max_length = 4000
            mock_config.telegram.photo_caption_max_length = 1024
            mock_config.telegram.request_timeout = 10
            mock_config.telegram.photo_timeout = 30

            client = TelegramClient(bot_token='test_token', default_chat_id='123456')
            client._config = mock_config
            return client

    def test_is_configured_with_token(self, client):
        """Client should be configured with token."""
        assert client.is_configured is True

    def test_not_configured_without_token(self):
        """Client should not be configured without token."""
        with patch('config.config') as mock_config:
            mock_config.telegram.bot_token = ''
            mock_config.telegram.chat_id = ''

            client = TelegramClient(bot_token='', default_chat_id='')
            assert client.is_configured is False

    def test_api_base_url(self, client):
        """API base URL should be correct."""
        assert 'test_token' in client.api_base

    def test_send_message_success(self, client, mock_telegram_response):
        """Should send message successfully."""
        with patch('requests.post', return_value=mock_telegram_response):
            result = client.send_message('123', 'Hello')
            assert result is True

    def test_send_message_truncates_long_text(self, client, mock_telegram_response):
        """Should truncate messages over max length."""
        with patch('requests.post', return_value=mock_telegram_response) as mock_post:
            long_text = 'x' * 5000
            client.send_message('123', long_text)

            # Check that text was truncated
            call_args = mock_post.call_args
            sent_text = call_args.kwargs['json']['text']
            assert len(sent_text) <= 4000
            assert 'truncated' in sent_text

    def test_send_message_rate_limit(self, client, mock_telegram_rate_limit):
        """Should raise on rate limit."""
        with patch('requests.post', return_value=mock_telegram_rate_limit):
            with pytest.raises(TelegramRateLimitError):
                client.send_message('123', 'Hello')

    def test_send_message_without_chat_id(self, client):
        """Should use default chat_id if not provided."""
        with patch('requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response

            client.send_message(text='Hello')

            call_args = mock_post.call_args
            assert call_args.kwargs['json']['chat_id'] == '123456'

    def test_send_photo_success(self, client, mock_telegram_response):
        """Should send photo successfully."""
        with patch('requests.post', return_value=mock_telegram_response):
            photo_buffer = io.BytesIO(b'fake image data')
            result = client.send_photo('123', photo_buffer, 'Caption')
            assert result is True

    def test_send_photo_with_bytes(self, client, mock_telegram_response):
        """Should handle bytes input."""
        with patch('requests.post', return_value=mock_telegram_response):
            result = client.send_photo('123', b'fake image data', 'Caption')
            assert result is True

    def test_send_message_safe_no_exception(self, client):
        """send_message_safe should not raise exceptions."""
        with patch('requests.post', side_effect=Exception('Network error')):
            result = client.send_message_safe('123', 'Hello')
            assert result is False


class TestGetTelegramClient:
    """Tests for get_telegram_client function."""

    def test_returns_client(self):
        """Should return a TelegramClient."""
        reset_telegram_client()
        with patch('config.config') as mock_config:
            mock_config.telegram.bot_token = 'test'
            mock_config.telegram.chat_id = '123'
            mock_config.telegram.api_base = 'https://api.telegram.org'

            client = get_telegram_client()
            assert isinstance(client, TelegramClient)

    def test_returns_same_instance(self):
        """Should return same instance on multiple calls."""
        reset_telegram_client()
        with patch('config.config') as mock_config:
            mock_config.telegram.bot_token = 'test'
            mock_config.telegram.chat_id = '123'
            mock_config.telegram.api_base = 'https://api.telegram.org'

            client1 = get_telegram_client()
            client2 = get_telegram_client()
            assert client1 is client2


class TestConvenienceFunctions:
    """Tests for send_message and send_photo convenience functions."""

    def test_send_message_uses_default_client(self):
        """send_message should use default client."""
        reset_telegram_client()
        with patch('utils.telegram_utils.get_telegram_client') as mock_get:
            mock_client = MagicMock()
            mock_client.send_message_safe.return_value = True
            mock_get.return_value = mock_client

            result = send_message('123', 'Hello')

            mock_client.send_message_safe.assert_called_once()
            assert result is True

    def test_send_photo_uses_default_client(self):
        """send_photo should use default client."""
        reset_telegram_client()
        with patch('utils.telegram_utils.get_telegram_client') as mock_get:
            mock_client = MagicMock()
            mock_client.send_photo_safe.return_value = True
            mock_get.return_value = mock_client

            photo = io.BytesIO(b'data')
            result = send_photo('123', photo, 'Caption')

            mock_client.send_photo_safe.assert_called_once()
            assert result is True
