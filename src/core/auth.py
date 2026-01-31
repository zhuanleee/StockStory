"""
API Authentication and Authorization
====================================

API key management, validation, and rate limiting.

Author: Stock Scanner Bot
Date: February 1, 2026
"""

import hashlib
import secrets
import time
from typing import Optional, Dict, Tuple
from datetime import datetime, timedelta
import json
from pathlib import Path

# =============================================================================
# API KEY MANAGEMENT
# =============================================================================

class APIKeyManager:
    """Manage API keys with validation, usage tracking, and rate limiting"""

    def __init__(self, keys_file: str = "/data/api_keys.json"):
        """
        Initialize API key manager.

        Args:
            keys_file: Path to JSON file storing API keys and metadata
        """
        self.keys_file = Path(keys_file)
        self.keys: Dict[str, Dict] = {}
        self.load_keys()

    def load_keys(self):
        """Load API keys from file"""
        try:
            if self.keys_file.exists():
                with open(self.keys_file, 'r') as f:
                    self.keys = json.load(f)
        except Exception as e:
            print(f"Failed to load API keys: {e}")
            self.keys = {}

    def save_keys(self):
        """Save API keys to file"""
        try:
            self.keys_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.keys_file, 'w') as f:
                json.dump(self.keys, f, indent=2)
        except Exception as e:
            print(f"Failed to save API keys: {e}")

    def generate_key(self, user_id: str, tier: str = "free", requests_per_day: int = 1000) -> str:
        """
        Generate a new API key.

        Args:
            user_id: Unique identifier for the user
            tier: API tier (free, pro, enterprise)
            requests_per_day: Daily request limit

        Returns:
            API key (format: ssk_live_<40 hex chars>)
        """
        # Generate secure random key
        random_bytes = secrets.token_bytes(32)
        key_hash = hashlib.sha256(random_bytes).hexdigest()[:40]
        api_key = f"ssk_live_{key_hash}"

        # Store key metadata
        self.keys[api_key] = {
            'user_id': user_id,
            'tier': tier,
            'created_at': datetime.now().isoformat(),
            'requests_per_day': requests_per_day,
            'total_requests': 0,
            'daily_requests': 0,
            'last_reset': datetime.now().date().isoformat(),
            'last_used': None,
            'is_active': True
        }

        self.save_keys()
        return api_key

    def validate_key(self, api_key: str) -> Tuple[bool, Optional[str]]:
        """
        Validate an API key.

        Args:
            api_key: API key to validate

        Returns:
            (is_valid, error_message)
        """
        # Check if key exists
        if api_key not in self.keys:
            return False, "Invalid API key"

        key_data = self.keys[api_key]

        # Check if key is active
        if not key_data.get('is_active', False):
            return False, "API key has been revoked"

        # Reset daily counter if needed
        today = datetime.now().date().isoformat()
        if key_data['last_reset'] != today:
            key_data['daily_requests'] = 0
            key_data['last_reset'] = today
            self.save_keys()

        # Check rate limit
        if key_data['daily_requests'] >= key_data['requests_per_day']:
            return False, f"Daily rate limit exceeded ({key_data['requests_per_day']} requests/day)"

        return True, None

    def record_usage(self, api_key: str):
        """
        Record API key usage.

        Args:
            api_key: API key that was used
        """
        if api_key in self.keys:
            self.keys[api_key]['total_requests'] += 1
            self.keys[api_key]['daily_requests'] += 1
            self.keys[api_key]['last_used'] = datetime.now().isoformat()
            self.save_keys()

    def get_key_info(self, api_key: str) -> Optional[Dict]:
        """
        Get information about an API key.

        Args:
            api_key: API key to query

        Returns:
            Key metadata or None if not found
        """
        return self.keys.get(api_key)

    def revoke_key(self, api_key: str) -> bool:
        """
        Revoke an API key.

        Args:
            api_key: API key to revoke

        Returns:
            True if revoked, False if not found
        """
        if api_key in self.keys:
            self.keys[api_key]['is_active'] = False
            self.save_keys()
            return True
        return False

    def list_keys(self, user_id: Optional[str] = None) -> Dict[str, Dict]:
        """
        List all API keys or keys for a specific user.

        Args:
            user_id: Optional user ID to filter by

        Returns:
            Dictionary of API keys and their metadata
        """
        if user_id:
            return {k: v for k, v in self.keys.items() if v.get('user_id') == user_id}
        return self.keys.copy()

    def get_usage_stats(self, api_key: str) -> Optional[Dict]:
        """
        Get usage statistics for an API key.

        Args:
            api_key: API key to query

        Returns:
            Usage stats or None if not found
        """
        if api_key not in self.keys:
            return None

        key_data = self.keys[api_key]
        requests_remaining = key_data['requests_per_day'] - key_data['daily_requests']

        return {
            'tier': key_data['tier'],
            'requests_per_day': key_data['requests_per_day'],
            'daily_requests': key_data['daily_requests'],
            'requests_remaining': requests_remaining,
            'total_requests': key_data['total_requests'],
            'last_used': key_data['last_used'],
            'is_active': key_data['is_active']
        }


# =============================================================================
# RATE LIMITING
# =============================================================================

class RateLimiter:
    """Token bucket rate limiter for API requests"""

    def __init__(self, requests_per_second: float = 10.0):
        """
        Initialize rate limiter.

        Args:
            requests_per_second: Maximum requests per second
        """
        self.rate = requests_per_second
        self.buckets: Dict[str, Dict] = {}  # key -> {tokens, last_update}

    def check_limit(self, key: str) -> Tuple[bool, float]:
        """
        Check if request is allowed under rate limit.

        Args:
            key: Unique identifier (e.g., API key or IP)

        Returns:
            (is_allowed, retry_after_seconds)
        """
        now = time.time()

        # Initialize bucket if needed
        if key not in self.buckets:
            self.buckets[key] = {
                'tokens': self.rate,
                'last_update': now
            }

        bucket = self.buckets[key]

        # Add tokens based on time elapsed
        time_elapsed = now - bucket['last_update']
        bucket['tokens'] = min(self.rate, bucket['tokens'] + time_elapsed * self.rate)
        bucket['last_update'] = now

        # Check if we have tokens available
        if bucket['tokens'] >= 1.0:
            bucket['tokens'] -= 1.0
            return True, 0.0
        else:
            # Calculate retry after time
            tokens_needed = 1.0 - bucket['tokens']
            retry_after = tokens_needed / self.rate
            return False, retry_after


# =============================================================================
# AUTHENTICATION HELPERS
# =============================================================================

def extract_api_key(authorization: str) -> Optional[str]:
    """
    Extract API key from Authorization header.

    Supports:
    - Bearer <key>
    - ApiKey <key>
    - <key> (raw key)

    Args:
        authorization: Authorization header value

    Returns:
        API key or None if not found
    """
    if not authorization:
        return None

    # Remove bearer/apikey prefix if present
    parts = authorization.split()
    if len(parts) == 2 and parts[0].lower() in ['bearer', 'apikey']:
        return parts[1]
    elif len(parts) == 1:
        return parts[0]

    return None


def validate_request(api_key: str, key_manager: APIKeyManager, rate_limiter: RateLimiter) -> Tuple[bool, Optional[str], Optional[Dict]]:
    """
    Validate API request with authentication and rate limiting.

    Args:
        api_key: API key from request
        key_manager: APIKeyManager instance
        rate_limiter: RateLimiter instance

    Returns:
        (is_valid, error_message, rate_limit_info)
    """
    # Validate API key
    is_valid, error = key_manager.validate_key(api_key)
    if not is_valid:
        return False, error, None

    # Check rate limit
    is_allowed, retry_after = rate_limiter.check_limit(api_key)
    if not is_allowed:
        return False, f"Rate limit exceeded. Retry after {retry_after:.2f} seconds", {
            'retry_after': retry_after
        }

    # Record usage
    key_manager.record_usage(api_key)

    # Get usage stats
    usage_stats = key_manager.get_usage_stats(api_key)

    return True, None, {
        'requests_remaining': usage_stats['requests_remaining'],
        'reset_at': datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    }
