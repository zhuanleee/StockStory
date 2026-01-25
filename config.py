"""
Centralized configuration for Stock Scanner Bot.

All configuration values are defined here with defaults.
Environment variables take precedence over defaults.

Usage:
    from config import config

    token = config.telegram.bot_token
    ttl = config.cache.ttl_seconds
"""
import os
from dataclasses import dataclass, field
from typing import List, Optional
from pathlib import Path


def _get_env(key: str, default: str = '') -> str:
    """Get environment variable with fallback."""
    return os.environ.get(key, default)


def _get_env_int(key: str, default: int) -> int:
    """Get environment variable as integer."""
    try:
        return int(os.environ.get(key, default))
    except (ValueError, TypeError):
        return default


def _get_env_float(key: str, default: float) -> float:
    """Get environment variable as float."""
    try:
        return float(os.environ.get(key, default))
    except (ValueError, TypeError):
        return default


def _get_env_bool(key: str, default: bool = False) -> bool:
    """Get environment variable as boolean."""
    val = os.environ.get(key, '').lower()
    if val in ('true', '1', 'yes'):
        return True
    if val in ('false', '0', 'no'):
        return False
    return default


@dataclass(frozen=True)
class TelegramConfig:
    """Telegram API configuration."""
    bot_token: str = field(default_factory=lambda: _get_env('TELEGRAM_BOT_TOKEN') or _get_env('BOT_TOKEN'))
    chat_id: str = field(default_factory=lambda: _get_env('TELEGRAM_CHAT_ID'))
    api_base: str = "https://api.telegram.org"
    message_max_length: int = 4000
    photo_caption_max_length: int = 1024
    request_timeout: int = 10
    photo_timeout: int = 30

    @property
    def api_url(self) -> str:
        """Get full API URL with bot token."""
        return f"{self.api_base}/bot{self.bot_token}"

    @property
    def is_configured(self) -> bool:
        """Check if Telegram is properly configured."""
        return bool(self.bot_token)


@dataclass(frozen=True)
class CacheConfig:
    """Cache configuration."""
    directory: Path = field(default_factory=lambda: Path('cache'))
    ttl_seconds: int = field(default_factory=lambda: _get_env_int('CACHE_TTL', 300))
    story_ttl_seconds: int = 600
    screener_ttl_seconds: int = 300
    background_refresh_interval: int = 300

    def __post_init__(self):
        """Ensure cache directory exists."""
        object.__setattr__(self, 'directory', Path(self.directory))
        self.directory.mkdir(exist_ok=True)


@dataclass(frozen=True)
class ScannerConfig:
    """Stock scanner configuration."""
    # Scoring weights
    weight_trend: float = 0.30
    weight_squeeze: float = 0.20
    weight_rs: float = 0.20
    weight_sentiment: float = 0.15
    weight_volume: float = 0.15

    # Alert thresholds
    min_composite_score: int = field(default_factory=lambda: _get_env_int('MIN_COMPOSITE_SCORE', 70))
    min_rs: int = field(default_factory=lambda: _get_env_int('MIN_RS', 5))
    volume_spike_threshold: float = field(default_factory=lambda: _get_env_float('VOLUME_SPIKE', 2.0))

    # Processing
    max_workers: int = field(default_factory=lambda: _get_env_int('MAX_WORKERS', 50))
    spy_period: str = '3mo'

    # RS calculation weights
    rs_weight_5d: float = 0.5
    rs_weight_10d: float = 0.3
    rs_weight_20d: float = 0.2


@dataclass(frozen=True)
class BacktestConfig:
    """Backtesting configuration."""
    commission_pct: float = 0.0005
    slippage_pct: float = 0.001
    default_holding_days: int = 5
    stop_loss_pct: float = 0.03
    take_profit_pct: float = 0.10


@dataclass(frozen=True)
class AIConfig:
    """AI/DeepSeek configuration."""
    api_key: str = field(default_factory=lambda: _get_env('DEEPSEEK_API_KEY'))
    api_url: str = "https://api.deepseek.com/v1/chat/completions"
    model: str = "deepseek-chat"
    temperature: float = 0.3
    default_max_tokens: int = 500
    request_timeout: int = 60

    @property
    def is_configured(self) -> bool:
        """Check if AI is properly configured."""
        return bool(self.api_key)


@dataclass(frozen=True)
class DataProviderConfig:
    """
    Data provider API configuration.

    Free tier limits:
    - Finnhub: 60 calls/min
    - Tiingo: 1000 calls/day
    - Alpha Vantage: 25 calls/day
    - FRED: Unlimited
    - SEC EDGAR: Unlimited (no key needed)
    """
    # API Keys
    finnhub_api_key: str = field(default_factory=lambda: _get_env('FINNHUB_API_KEY'))
    tiingo_api_key: str = field(default_factory=lambda: _get_env('TIINGO_API_KEY'))
    alpha_vantage_api_key: str = field(default_factory=lambda: _get_env('ALPHA_VANTAGE_API_KEY'))
    fred_api_key: str = field(default_factory=lambda: _get_env('FRED_API_KEY'))

    # Rate limits (per minute)
    finnhub_rate_limit: int = 60
    tiingo_rate_limit: int = 50
    alpha_vantage_rate_limit: int = 5

    # Timeouts
    request_timeout: int = 10

    @property
    def finnhub_configured(self) -> bool:
        return bool(self.finnhub_api_key)

    @property
    def tiingo_configured(self) -> bool:
        return bool(self.tiingo_api_key)

    @property
    def alpha_vantage_configured(self) -> bool:
        return bool(self.alpha_vantage_api_key)

    @property
    def fred_configured(self) -> bool:
        return bool(self.fred_api_key)

    @property
    def any_configured(self) -> bool:
        """Check if any premium data provider is configured."""
        return any([
            self.finnhub_configured,
            self.tiingo_configured,
            self.alpha_vantage_configured,
            self.fred_configured
        ])


@dataclass(frozen=True)
class SecurityConfig:
    """Security configuration."""
    webhook_secret: str = field(default_factory=lambda: _get_env('WEBHOOK_SECRET'))
    allowed_cors_origins: List[str] = field(default_factory=lambda: [
        origin.strip()
        for origin in _get_env('ALLOWED_CORS_ORIGINS', '').split(',')
        if origin.strip()
    ] or ['*'])  # Default to * if not configured
    rate_limit_requests: int = 100
    rate_limit_window: int = 60


@dataclass(frozen=True)
class StorageConfig:
    """Data storage configuration."""
    user_data_dir: Path = field(default_factory=lambda: Path('user_data'))
    max_watchlist_size: int = 20
    max_alerts_per_user: int = 50
    max_closed_trades: int = 100

    def __post_init__(self):
        """Ensure storage directory exists."""
        object.__setattr__(self, 'user_data_dir', Path(self.user_data_dir))
        self.user_data_dir.mkdir(exist_ok=True)


@dataclass
class Config:
    """Main configuration container."""
    telegram: TelegramConfig = field(default_factory=TelegramConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    scanner: ScannerConfig = field(default_factory=ScannerConfig)
    backtest: BacktestConfig = field(default_factory=BacktestConfig)
    ai: AIConfig = field(default_factory=AIConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    data_providers: DataProviderConfig = field(default_factory=DataProviderConfig)

    # Server settings
    debug: bool = field(default_factory=lambda: _get_env_bool('DEBUG', False))
    port: int = field(default_factory=lambda: _get_env_int('PORT', 5000))

    def validate(self) -> List[str]:
        """
        Validate configuration and return list of warnings.

        Returns:
            List of warning messages (empty if all OK)
        """
        warnings = []

        if not self.telegram.is_configured:
            warnings.append("TELEGRAM_BOT_TOKEN not set - Telegram features disabled")

        if not self.telegram.chat_id:
            warnings.append("TELEGRAM_CHAT_ID not set - automated alerts disabled")

        if not self.ai.is_configured:
            warnings.append("DEEPSEEK_API_KEY not set - AI features disabled")

        if not self.security.webhook_secret:
            warnings.append("WEBHOOK_SECRET not set - webhook signature verification disabled")

        if self.security.allowed_cors_origins == ['*']:
            warnings.append("CORS allows all origins - consider restricting in production")

        return warnings


# Global configuration instance
config = Config()


def print_config_status():
    """Print configuration status for debugging."""
    warnings = config.validate()
    if warnings:
        print("Configuration warnings:")
        for w in warnings:
            print(f"  - {w}")
    else:
        print("Configuration OK")


if __name__ == '__main__':
    print_config_status()
