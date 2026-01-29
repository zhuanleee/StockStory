"""
Centralized Configuration
========================
Single source of truth for all configuration values.

Environment variables override defaults.
"""

import os
from pathlib import Path
from typing import Optional


class Config:
    """Application configuration."""

    # =============================================================================
    # PATHS
    # =============================================================================

    PROJECT_ROOT = Path(__file__).parent.parent
    DATA_DIR = PROJECT_ROOT / "data"
    CACHE_DIR = PROJECT_ROOT / "cache"
    DOCS_DIR = PROJECT_ROOT / "docs"

    # =============================================================================
    # API KEYS
    # =============================================================================

    # Financial Data
    POLYGON_API_KEY = os.environ.get('POLYGON_API_KEY', '')
    FINNHUB_API_KEY = os.environ.get('FINNHUB_API_KEY', '')
    ALPHA_VANTAGE_API_KEY = os.environ.get('ALPHA_VANTAGE_API_KEY', '')

    # AI Services
    DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
    XAI_API_KEY = os.environ.get('XAI_API_KEY', '')
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')

    # Intelligence Sources
    PATENTSVIEW_API_KEY = os.environ.get('PATENTSVIEW_API_KEY', '')

    # Communication
    TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
    TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '')

    # =============================================================================
    # FEATURE FLAGS
    # =============================================================================

    USE_AI_BRAIN_RANKING = os.environ.get('USE_AI_BRAIN_RANKING', '').lower() in ['true', '1', 'yes']
    USE_LEARNING_SYSTEM = os.environ.get('USE_LEARNING_SYSTEM', 'true').lower() in ['true', '1', 'yes']
    USE_X_INTELLIGENCE = bool(XAI_API_KEY)  # Auto-enable if API key present
    USE_GOOGLE_TRENDS = os.environ.get('USE_GOOGLE_TRENDS', 'true').lower() in ['true', '1', 'yes']

    # =============================================================================
    # SCANNER SETTINGS
    # =============================================================================

    # Universe
    MIN_MARKET_CAP = int(os.environ.get('MIN_MARKET_CAP', '300000000'))  # $300M
    MAX_CONCURRENT_SCANS = int(os.environ.get('MAX_CONCURRENT_SCANS', '50'))

    # Scoring Thresholds
    STORY_SCORE_HOT_THRESHOLD = float(os.environ.get('STORY_SCORE_HOT_THRESHOLD', '70.0'))
    STORY_SCORE_DEVELOPING_THRESHOLD = float(os.environ.get('STORY_SCORE_DEVELOPING_THRESHOLD', '50.0'))

    # =============================================================================
    # CACHE SETTINGS
    # =============================================================================

    # Cache TTLs (seconds)
    CACHE_TTL_PRICE = 300  # 5 minutes
    CACHE_TTL_NEWS = 900  # 15 minutes
    CACHE_TTL_SOCIAL = 900  # 15 minutes
    CACHE_TTL_SEC = 3600  # 1 hour
    CACHE_TTL_SECTOR = 86400  # 24 hours
    CACHE_TTL_TRENDS = 3600  # 1 hour
    CACHE_TTL_X_SENTIMENT = 900  # 15 minutes
    CACHE_TTL_CONTRACTS = 43200  # 12 hours
    CACHE_TTL_PATENTS = 86400  # 24 hours

    # =============================================================================
    # LEARNING SYSTEM SETTINGS
    # =============================================================================

    # Bayesian Bandit
    BANDIT_ALPHA_PRIOR = float(os.environ.get('BANDIT_ALPHA_PRIOR', '1.0'))
    BANDIT_BETA_PRIOR = float(os.environ.get('BANDIT_BETA_PRIOR', '1.0'))

    # Regime Detection
    REGIME_N_STATES = int(os.environ.get('REGIME_N_STATES', '4'))  # bull, bear, choppy, crisis

    # PPO
    PPO_LEARNING_RATE = float(os.environ.get('PPO_LEARNING_RATE', '0.0003'))
    PPO_GAMMA = float(os.environ.get('PPO_GAMMA', '0.99'))
    PPO_EPISODES_PER_UPDATE = int(os.environ.get('PPO_EPISODES_PER_UPDATE', '10'))

    # Meta-Learning
    META_LEARNING_RATE = float(os.environ.get('META_LEARNING_RATE', '0.001'))
    META_ADAPTATION_STEPS = int(os.environ.get('META_ADAPTATION_STEPS', '5'))

    # =============================================================================
    # TRADING SETTINGS
    # =============================================================================

    # Position Sizing
    DEFAULT_POSITION_SIZE = float(os.environ.get('DEFAULT_POSITION_SIZE', '0.02'))  # 2% of portfolio
    MAX_POSITION_SIZE = float(os.environ.get('MAX_POSITION_SIZE', '0.10'))  # 10% max

    # Risk Management
    DEFAULT_STOP_LOSS_PCT = float(os.environ.get('DEFAULT_STOP_LOSS_PCT', '0.08'))  # 8%
    DEFAULT_TAKE_PROFIT_PCT = float(os.environ.get('DEFAULT_TAKE_PROFIT_PCT', '0.20'))  # 20%

    # =============================================================================
    # RATE LIMITS
    # =============================================================================

    # API Rate Limits (requests per minute)
    RATE_LIMIT_STOCKTWITS = 200
    RATE_LIMIT_REDDIT = 60
    RATE_LIMIT_SEC = 600  # 10/second
    RATE_LIMIT_POLYGON = 6000  # Unlimited tier
    RATE_LIMIT_XAI = 60
    RATE_LIMIT_GOOGLE_TRENDS = 10  # Conservative to avoid bans

    # =============================================================================
    # LOGGING SETTINGS
    # =============================================================================

    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    # =============================================================================
    # HELPER METHODS
    # =============================================================================

    @classmethod
    def is_api_available(cls, api_name: str) -> bool:
        """Check if API credentials are configured."""
        api_keys = {
            'polygon': cls.POLYGON_API_KEY,
            'finnhub': cls.FINNHUB_API_KEY,
            'alpha_vantage': cls.ALPHA_VANTAGE_API_KEY,
            'deepseek': cls.DEEPSEEK_API_KEY,
            'xai': cls.XAI_API_KEY,
            'openai': cls.OPENAI_API_KEY,
            'patents': cls.PATENTSVIEW_API_KEY,
            'telegram': cls.TELEGRAM_BOT_TOKEN,
        }
        return bool(api_keys.get(api_name.lower(), ''))

    @classmethod
    def get_required_apis(cls) -> dict:
        """Get status of all APIs."""
        return {
            'polygon': cls.is_api_available('polygon'),
            'finnhub': cls.is_api_available('finnhub'),
            'alpha_vantage': cls.is_api_available('alpha_vantage'),
            'deepseek': cls.is_api_available('deepseek'),
            'xai': cls.is_api_available('xai'),
            'openai': cls.is_api_available('openai'),
            'patents': cls.is_api_available('patents'),
            'telegram': cls.is_api_available('telegram'),
        }

    @classmethod
    def validate_config(cls) -> dict:
        """Validate configuration and return issues."""
        issues = []
        warnings = []

        # Check critical APIs
        if not cls.POLYGON_API_KEY:
            warnings.append("POLYGON_API_KEY not set - price data may be limited")

        if not cls.DEEPSEEK_API_KEY:
            warnings.append("DEEPSEEK_API_KEY not set - AI analysis disabled")

        # Check feature configurations
        if cls.USE_AI_BRAIN_RANKING and not cls.DEEPSEEK_API_KEY:
            issues.append("USE_AI_BRAIN_RANKING=true but DEEPSEEK_API_KEY not set")

        if cls.USE_X_INTELLIGENCE and not cls.XAI_API_KEY:
            issues.append("X Intelligence requires XAI_API_KEY")

        # Check paths
        if not cls.DATA_DIR.exists():
            warnings.append(f"Data directory does not exist: {cls.DATA_DIR}")

        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings
        }


# Create config instance
config = Config()


# =============================================================================
# CONFIGURATION HELPER FUNCTIONS
# =============================================================================

def get_config() -> Config:
    """Get global configuration instance."""
    return config


def is_feature_enabled(feature_name: str) -> bool:
    """Check if a feature is enabled."""
    features = {
        'ai_brain': config.USE_AI_BRAIN_RANKING,
        'learning': config.USE_LEARNING_SYSTEM,
        'x_intelligence': config.USE_X_INTELLIGENCE,
        'google_trends': config.USE_GOOGLE_TRENDS,
    }
    return features.get(feature_name.lower(), False)


def print_config_status():
    """Print configuration status (for debugging)."""
    validation = config.validate_config()

    print("Configuration Status:")
    print(f"  Valid: {validation['valid']}")

    if validation['issues']:
        print("\n  Issues:")
        for issue in validation['issues']:
            print(f"    ❌ {issue}")

    if validation['warnings']:
        print("\n  Warnings:")
        for warning in validation['warnings']:
            print(f"    ⚠️  {warning}")

    print("\n  APIs:")
    for api, available in config.get_required_apis().items():
        status = "✅" if available else "❌"
        print(f"    {status} {api}")

    print("\n  Features:")
    print(f"    AI Brain Ranking: {config.USE_AI_BRAIN_RANKING}")
    print(f"    Learning System: {config.USE_LEARNING_SYSTEM}")
    print(f"    X Intelligence: {config.USE_X_INTELLIGENCE}")
    print(f"    Google Trends: {config.USE_GOOGLE_TRENDS}")


if __name__ == '__main__':
    print_config_status()
