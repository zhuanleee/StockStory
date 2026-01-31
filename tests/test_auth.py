"""
Tests for API Authentication System
"""
import pytest
import tempfile
import json
from pathlib import Path
from src.core.auth import APIKeyManager, RateLimiter, extract_api_key, validate_request


class TestAPIKeyManager:
    """Test API key generation and management"""

    @pytest.fixture
    def temp_keys_file(self):
        """Create temporary keys file"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            f.write('{}')
            return f.name

    @pytest.fixture
    def manager(self, temp_keys_file):
        """Create APIKeyManager with temp file"""
        return APIKeyManager(keys_file=temp_keys_file)

    def test_generate_key(self, manager):
        """Test API key generation"""
        key = manager.generate_key(user_id="test_user", tier="free")

        assert key.startswith("ssk_live_")
        assert len(key) == 49  # ssk_live_ (9) + 40 hex chars
        assert key in manager.keys

    def test_generate_key_with_tiers(self, manager):
        """Test key generation with different tiers"""
        free_key = manager.generate_key(user_id="user1", tier="free", requests_per_day=1000)
        pro_key = manager.generate_key(user_id="user2", tier="pro", requests_per_day=10000)

        assert manager.keys[free_key]['requests_per_day'] == 1000
        assert manager.keys[pro_key]['requests_per_day'] == 10000

    def test_validate_valid_key(self, manager):
        """Test validation of valid API key"""
        key = manager.generate_key(user_id="test_user", tier="free")
        is_valid, error = manager.validate_key(key)

        assert is_valid is True
        assert error is None

    def test_validate_invalid_key(self, manager):
        """Test validation of invalid API key"""
        is_valid, error = manager.validate_key("invalid_key")

        assert is_valid is False
        assert error == "Invalid API key"

    def test_validate_revoked_key(self, manager):
        """Test validation of revoked key"""
        key = manager.generate_key(user_id="test_user", tier="free")
        manager.revoke_key(key)

        is_valid, error = manager.validate_key(key)

        assert is_valid is False
        assert error == "API key has been revoked"

    def test_daily_limit_enforcement(self, manager):
        """Test daily rate limit enforcement"""
        key = manager.generate_key(user_id="test_user", tier="free", requests_per_day=10)

        # Use up the daily limit
        for i in range(10):
            manager.record_usage(key)

        # Next validation should fail
        is_valid, error = manager.validate_key(key)

        assert is_valid is False
        assert "Daily rate limit exceeded" in error

    def test_record_usage(self, manager):
        """Test usage recording"""
        key = manager.generate_key(user_id="test_user", tier="free")

        manager.record_usage(key)

        assert manager.keys[key]['total_requests'] == 1
        assert manager.keys[key]['daily_requests'] == 1
        assert manager.keys[key]['last_used'] is not None

    def test_get_usage_stats(self, manager):
        """Test usage statistics retrieval"""
        key = manager.generate_key(user_id="test_user", tier="free", requests_per_day=1000)
        manager.record_usage(key)

        stats = manager.get_usage_stats(key)

        assert stats['tier'] == 'free'
        assert stats['daily_requests'] == 1
        assert stats['requests_remaining'] == 999
        assert stats['total_requests'] == 1

    def test_revoke_key(self, manager):
        """Test key revocation"""
        key = manager.generate_key(user_id="test_user", tier="free")

        success = manager.revoke_key(key)

        assert success is True
        assert manager.keys[key]['is_active'] is False


class TestRateLimiter:
    """Test rate limiting with token bucket algorithm"""

    def test_rate_limit_allows_requests(self):
        """Test that rate limiter allows requests under limit"""
        limiter = RateLimiter(requests_per_second=10.0)

        is_allowed, retry_after = limiter.check_limit("test_key")

        assert is_allowed is True
        assert retry_after == 0.0

    def test_rate_limit_blocks_excessive_requests(self):
        """Test that rate limiter blocks excessive requests"""
        limiter = RateLimiter(requests_per_second=2.0)

        # Exhaust tokens
        limiter.check_limit("test_key")
        limiter.check_limit("test_key")
        limiter.check_limit("test_key")

        # Should be rate limited
        is_allowed, retry_after = limiter.check_limit("test_key")

        assert is_allowed is False
        assert retry_after > 0

    def test_rate_limit_per_key(self):
        """Test that rate limits are per-key"""
        limiter = RateLimiter(requests_per_second=1.0)

        # Exhaust tokens for key1
        limiter.check_limit("key1")
        limiter.check_limit("key1")

        # key2 should still be allowed
        is_allowed, _ = limiter.check_limit("key2")

        assert is_allowed is True


class TestHelperFunctions:
    """Test authentication helper functions"""

    def test_extract_api_key_bearer(self):
        """Test extracting API key from Bearer token"""
        key = extract_api_key("Bearer ssk_live_abc123")
        assert key == "ssk_live_abc123"

    def test_extract_api_key_apikey(self):
        """Test extracting API key from ApiKey header"""
        key = extract_api_key("ApiKey ssk_live_abc123")
        assert key == "ssk_live_abc123"

    def test_extract_api_key_raw(self):
        """Test extracting raw API key"""
        key = extract_api_key("ssk_live_abc123")
        assert key == "ssk_live_abc123"

    def test_extract_api_key_none(self):
        """Test extracting API key from None"""
        key = extract_api_key(None)
        assert key is None

    def test_validate_request_success(self, tmp_path):
        """Test successful request validation"""
        keys_file = tmp_path / "keys.json"
        manager = APIKeyManager(keys_file=str(keys_file))
        limiter = RateLimiter(requests_per_second=10.0)

        api_key = manager.generate_key(user_id="test_user", tier="free")

        is_valid, error, rate_info = validate_request(api_key, manager, limiter)

        assert is_valid is True
        assert error is None
        assert rate_info is not None
        assert 'requests_remaining' in rate_info

    def test_validate_request_invalid_key(self, tmp_path):
        """Test request validation with invalid key"""
        keys_file = tmp_path / "keys.json"
        manager = APIKeyManager(keys_file=str(keys_file))
        limiter = RateLimiter(requests_per_second=10.0)

        is_valid, error, rate_info = validate_request("invalid_key", manager, limiter)

        assert is_valid is False
        assert error == "Invalid API key"
        assert rate_info is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
