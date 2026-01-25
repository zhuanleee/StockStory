"""Tests for utils/validators.py"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.validators import (
    validate_ticker,
    is_valid_ticker,
    validate_webhook_url,
    validate_webhook_signature,
    sanitize_input,
    validate_price,
    validate_quantity,
    validate_chat_id,
    ValidationError,
)


class TestValidateTicker:
    """Tests for validate_ticker function."""

    def test_valid_simple_tickers(self):
        """Standard tickers should pass."""
        assert validate_ticker('AAPL') == 'AAPL'
        assert validate_ticker('MSFT') == 'MSFT'
        assert validate_ticker('A') == 'A'
        assert validate_ticker('GOOGL') == 'GOOGL'

    def test_lowercase_normalized(self):
        """Lowercase should be normalized to uppercase."""
        assert validate_ticker('aapl') == 'AAPL'
        assert validate_ticker('msft') == 'MSFT'

    def test_dollar_sign_removed(self):
        """Dollar sign prefix should be removed."""
        assert validate_ticker('$AAPL') == 'AAPL'
        assert validate_ticker('$nvda') == 'NVDA'

    def test_ticker_with_dot(self):
        """Tickers with dots should pass."""
        assert validate_ticker('BRK.B') == 'BRK.B'
        assert validate_ticker('BRK.A') == 'BRK.A'

    def test_whitespace_stripped(self):
        """Whitespace should be stripped."""
        assert validate_ticker('  AAPL  ') == 'AAPL'
        assert validate_ticker('\tMSFT\n') == 'MSFT'

    def test_too_long_rejected(self):
        """Tickers longer than 5 chars should be rejected."""
        with pytest.raises(ValidationError, match='Invalid ticker format'):
            validate_ticker('TOOLONG')

    def test_numbers_rejected(self):
        """Tickers with numbers should be rejected."""
        with pytest.raises(ValidationError, match='Invalid ticker format'):
            validate_ticker('AAP1')

    def test_empty_rejected(self):
        """Empty string should be rejected."""
        with pytest.raises(ValidationError, match='cannot be empty'):
            validate_ticker('')

    def test_blocked_words_rejected(self):
        """Reserved words should be rejected."""
        with pytest.raises(ValidationError, match='reserved word'):
            validate_ticker('HELP')
        with pytest.raises(ValidationError, match='reserved word'):
            validate_ticker('TEST')
        with pytest.raises(ValidationError, match='reserved word'):
            validate_ticker('NULL')


class TestIsValidTicker:
    """Tests for is_valid_ticker function."""

    def test_valid_returns_true(self):
        assert is_valid_ticker('AAPL') is True
        assert is_valid_ticker('msft') is True

    def test_invalid_returns_false(self):
        assert is_valid_ticker('TOOLONG') is False
        assert is_valid_ticker('') is False
        assert is_valid_ticker('HELP') is False


class TestValidateWebhookUrl:
    """Tests for validate_webhook_url function."""

    def test_valid_https_url(self):
        """Valid HTTPS URLs should pass."""
        url = validate_webhook_url('https://example.com/webhook')
        assert url == 'https://example.com/webhook'

    def test_https_with_port(self):
        """HTTPS with port should pass."""
        url = validate_webhook_url('https://example.com:8443/webhook')
        assert 'example.com' in url

    def test_http_rejected(self):
        """HTTP URLs should be rejected."""
        with pytest.raises(ValidationError, match='HTTPS'):
            validate_webhook_url('http://example.com/webhook')

    def test_empty_rejected(self):
        """Empty URL should be rejected."""
        with pytest.raises(ValidationError, match='cannot be empty'):
            validate_webhook_url('')

    def test_localhost_rejected(self):
        """Localhost should be rejected."""
        with pytest.raises(ValidationError, match='Localhost'):
            validate_webhook_url('https://localhost/webhook')

    def test_127_0_0_1_rejected(self):
        """127.0.0.1 should be rejected."""
        with pytest.raises(ValidationError, match='Localhost'):
            validate_webhook_url('https://127.0.0.1/webhook')

    def test_internal_ip_10_rejected(self):
        """10.x.x.x IPs should be rejected."""
        with pytest.raises(ValidationError, match='Internal IP'):
            validate_webhook_url('https://10.0.0.1/webhook')

    def test_internal_ip_172_rejected(self):
        """172.16-31.x.x IPs should be rejected."""
        with pytest.raises(ValidationError, match='Internal IP'):
            validate_webhook_url('https://172.16.0.1/webhook')

    def test_internal_ip_192_rejected(self):
        """192.168.x.x IPs should be rejected."""
        with pytest.raises(ValidationError, match='Internal IP'):
            validate_webhook_url('https://192.168.1.1/webhook')


class TestValidateWebhookSignature:
    """Tests for validate_webhook_signature function."""

    def test_valid_signature(self):
        """Valid signature should return True."""
        payload = b'test payload'
        secret = 'test_secret'

        import hmac
        import hashlib
        signature = hmac.new(
            secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()

        result = validate_webhook_signature(payload, signature, secret)
        assert result is True

    def test_invalid_signature(self):
        """Invalid signature should return False."""
        payload = b'test payload'
        secret = 'test_secret'
        wrong_signature = 'invalid_signature'

        result = validate_webhook_signature(payload, wrong_signature, secret)
        assert result is False

    def test_empty_signature_rejected(self):
        """Empty signature should return False."""
        result = validate_webhook_signature(b'payload', '', 'secret')
        assert result is False

    def test_no_secret_allows_all(self):
        """No secret configured should allow (with warning)."""
        result = validate_webhook_signature(b'payload', 'any', None)
        # When no secret, it should pass (but log warning)
        assert result is True


class TestSanitizeInput:
    """Tests for sanitize_input function."""

    def test_basic_text_unchanged(self):
        """Normal text should be unchanged."""
        assert sanitize_input('Hello World') == 'Hello World'

    def test_truncates_long_text(self):
        """Long text should be truncated."""
        long_text = 'a' * 2000
        result = sanitize_input(long_text, max_length=100)
        assert len(result) == 100

    def test_removes_control_chars(self):
        """Control characters should be removed."""
        text = 'Hello\x00World\x1f'
        result = sanitize_input(text)
        assert '\x00' not in result
        assert '\x1f' not in result

    def test_preserves_newlines(self):
        """Newlines should be preserved."""
        text = 'Hello\nWorld'
        result = sanitize_input(text)
        assert '\n' in result

    def test_preserves_tabs(self):
        """Tabs should be preserved."""
        text = 'Hello\tWorld'
        result = sanitize_input(text)
        assert '\t' in result

    def test_strips_whitespace(self):
        """Leading/trailing whitespace should be stripped."""
        result = sanitize_input('  hello  ')
        assert result == 'hello'

    def test_empty_string(self):
        """Empty string should return empty."""
        assert sanitize_input('') == ''

    def test_none_returns_empty(self):
        """None should return empty string."""
        assert sanitize_input(None) == ''


class TestValidatePrice:
    """Tests for validate_price function."""

    def test_valid_price(self):
        """Valid price strings should work."""
        assert validate_price('100.50') == 100.50
        assert validate_price('0.01') == 0.01
        assert validate_price('1000') == 1000.0

    def test_invalid_format(self):
        """Invalid format should raise."""
        with pytest.raises(ValidationError, match='Invalid price'):
            validate_price('not a price')

    def test_negative_rejected(self):
        """Negative prices should be rejected."""
        with pytest.raises(ValidationError, match='must be positive'):
            validate_price('-10')

    def test_zero_rejected(self):
        """Zero should be rejected."""
        with pytest.raises(ValidationError, match='must be positive'):
            validate_price('0')

    def test_unreasonably_high_rejected(self):
        """Very high prices should be rejected."""
        with pytest.raises(ValidationError, match='unreasonably high'):
            validate_price('999999999')


class TestValidateQuantity:
    """Tests for validate_quantity function."""

    def test_valid_quantity(self):
        """Valid quantities should work."""
        assert validate_quantity('100') == 100
        assert validate_quantity('1') == 1

    def test_invalid_format(self):
        """Invalid format should raise."""
        with pytest.raises(ValidationError, match='Invalid quantity'):
            validate_quantity('not a number')

    def test_negative_rejected(self):
        """Negative quantities should be rejected."""
        with pytest.raises(ValidationError, match='must be positive'):
            validate_quantity('-10')

    def test_zero_rejected(self):
        """Zero should be rejected."""
        with pytest.raises(ValidationError, match='must be positive'):
            validate_quantity('0')

    def test_float_converts_to_int(self):
        """Float strings should truncate to int."""
        # This should raise or truncate depending on implementation
        with pytest.raises(ValidationError):
            validate_quantity('10.5')


class TestValidateChatId:
    """Tests for validate_chat_id function."""

    def test_valid_positive_id(self):
        """Positive chat IDs should work."""
        assert validate_chat_id('123456789') == '123456789'

    def test_valid_negative_id(self):
        """Negative chat IDs (groups) should work."""
        assert validate_chat_id('-123456789') == '-123456789'

    def test_empty_rejected(self):
        """Empty string should be rejected."""
        with pytest.raises(ValidationError, match='cannot be empty'):
            validate_chat_id('')

    def test_invalid_format(self):
        """Invalid format should be rejected."""
        with pytest.raises(ValidationError, match='Invalid chat ID'):
            validate_chat_id('not_a_number')
