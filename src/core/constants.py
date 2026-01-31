"""
Centralized Constants for Stock Scanner Bot
============================================

All hardcoded values, magic numbers, and configuration constants
should be defined here to avoid duplication and improve maintainability.

Author: Stock Scanner Bot
Version: 2.0
Date: February 1, 2026
"""

# =============================================================================
# MARKET DATA FILTERING
# =============================================================================

# Market cap thresholds (in USD)
MIN_MARKET_CAP = 300_000_000  # $300M minimum market cap
MAX_MARKET_CAP = 1_000_000_000_000  # $1T maximum (filter out mega caps if needed)

# Price range
MIN_PRICE = 5.0  # Minimum stock price (avoid penny stocks)
MAX_PRICE = 500.0  # Maximum stock price (avoid extremely high prices)

# Volume requirements
MIN_VOLUME = 500_000  # Minimum daily volume (liquidity requirement)
MIN_AVG_VOLUME_20D = 1_000_000  # Minimum 20-day average volume

# Technical filters
MIN_RS_RATING = 70  # Minimum relative strength rating (0-100)
MAX_DAYS_SINCE_ATH = 90  # Maximum days since all-time high

# =============================================================================
# TRADING HOURS (Eastern Time)
# =============================================================================

MARKET_OPEN_HOUR = 9
MARKET_OPEN_MINUTE = 30
MARKET_CLOSE_HOUR = 16
MARKET_CLOSE_MINUTE = 0
PRE_MARKET_OPEN_HOUR = 4
POST_MARKET_CLOSE_HOUR = 20

# Market days
TRADING_DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']

# =============================================================================
# API RATE LIMITS
# =============================================================================

# Rate limits (requests per second)
POLYGON_RATE_LIMIT = 100.0  # Unlimited tier - conservative limit
STOCKTWITS_RATE_LIMIT = 3.0  # ~200/hour total, self-imposed limit
REDDIT_RATE_LIMIT = 1.0  # ~60/min total, self-imposed limit
SEC_RATE_LIMIT = 10.0  # SEC requests 10/second max, be nice
NEWS_RATE_LIMIT = 5.0  # ~300/hour total for news APIs
DEEPSEEK_RATE_LIMIT = 5.0  # DeepSeek API limit
XAI_RATE_LIMIT = 3.0  # X.AI API limit

# Burst allowances (token bucket)
POLYGON_BURST = 50  # Allow short bursts up to 50
STOCKTWITS_BURST = 5  # Small burst for responsive UX
REDDIT_BURST = 4  # Small burst for responsive UX
SEC_BURST = 20  # Moderate burst
NEWS_BURST = 10  # Moderate burst
DEEPSEEK_BURST = 10
XAI_BURST = 5

# =============================================================================
# CACHE TTLs (Time-To-Live in seconds)
# =============================================================================

CACHE_TTL_PRICE = 900  # 15 minutes - price data freshness
CACHE_TTL_NEWS = 1800  # 30 minutes - news updates
CACHE_TTL_SENTIMENT = 3600  # 1 hour - sentiment analysis
CACHE_TTL_SOCIAL = 3600  # 1 hour - social media data
CACHE_TTL_SEC_FILINGS = 3600  # 1 hour - SEC filings
CACHE_TTL_SECTOR = 86400  # 24 hours - sector data (changes slowly)
CACHE_TTL_THEME = 3600  # 1 hour - theme data
CACHE_TTL_OPTIONS = 900  # 15 minutes - options data
CACHE_TTL_EARNINGS = 3600  # 1 hour - earnings data
CACHE_TTL_UNIVERSE = 86400  # 24 hours - stock universe

# Cache sizes
CACHE_MAX_SIZE_MEMORY = 10000  # Maximum LRU cache entries
CACHE_MAX_SIZE_FILE = 1000  # Maximum cached files
CACHE_MAX_AGE_DAYS = 7  # Delete cache files older than 7 days

# =============================================================================
# API ENDPOINTS
# =============================================================================

# Base URLs
POLYGON_BASE_URL = "https://api.polygon.io"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
XAI_BASE_URL = "https://api.x.ai"
SEC_BASE_URL = "https://www.sec.gov"
FINNHUB_BASE_URL = "https://finnhub.io/api"
ALPHA_VANTAGE_BASE_URL = "https://www.alphavantage.co"
YAHOO_FINANCE_BASE_URL = "https://query1.finance.yahoo.com"
STOCKTWITS_BASE_URL = "https://api.stocktwits.com"
PATENTSVIEW_BASE_URL = "https://search.patentsview.org"
USASPENDING_BASE_URL = "https://api.usaspending.gov"

# Telegram
TELEGRAM_BASE_URL = "https://api.telegram.org"
TELEGRAM_MAX_MESSAGE_LENGTH = 4096  # Telegram message size limit

# =============================================================================
# SCORING WEIGHTS (Initial values - learned over time)
# =============================================================================

# Component weights (must sum to ~1.0)
WEIGHT_THEME_HEAT = 0.18  # Theme narrative strength
WEIGHT_CATALYST = 0.18  # Upcoming catalysts (earnings, events)
WEIGHT_SOCIAL_BUZZ = 0.12  # Social media activity
WEIGHT_NEWS_MOMENTUM = 0.10  # News flow acceleration
WEIGHT_SENTIMENT = 0.07  # Sentiment analysis
WEIGHT_ECOSYSTEM = 0.10  # Supply chain position
WEIGHT_TECHNICAL = 0.25  # Technical indicators

# Weight bounds for learning
MIN_COMPONENT_WEIGHT = 0.05  # Minimum weight (5%)
MAX_COMPONENT_WEIGHT = 0.40  # Maximum weight (40%)

# =============================================================================
# ROLE & STAGE SCORES
# =============================================================================

# Theme role scores (relative importance)
ROLE_SCORE_DRIVER = 100  # Theme driver (most important)
ROLE_SCORE_BENEFICIARY = 70  # Benefits from theme
ROLE_SCORE_PICKS_SHOVELS = 50  # Enables theme (infrastructure)
ROLE_SCORE_INDIRECT = 30  # Indirect connection

# Theme stage scores (timing)
STAGE_SCORE_EARLY = 100  # Early stage (best opportunity)
STAGE_SCORE_MIDDLE = 70  # Middle stage (momentum)
STAGE_SCORE_LATE = 30  # Late stage (fading)
STAGE_SCORE_ONGOING = 60  # Ongoing theme (stable)
STAGE_SCORE_UNKNOWN = 50  # Unknown stage (default)

# =============================================================================
# MULTIPLIERS
# =============================================================================

MULTIPLIER_EARLY_STAGE_BOOST = 1.2  # Boost for early-stage themes
MULTIPLIER_CATALYST_NEAR_7D = 1.3  # Catalyst within 7 days
MULTIPLIER_CATALYST_NEAR_14D = 1.1  # Catalyst within 14 days
MULTIPLIER_STRONG_SENTIMENT = 1.5  # Very bullish sentiment
MULTIPLIER_VOLUME_SPIKE = 1.3  # Unusual volume
MULTIPLIER_INSIDER_BUYING = 1.2  # Recent insider buying
MULTIPLIER_INSTITUTIONAL_FLOW = 1.15  # Smart money buying

# =============================================================================
# THRESHOLDS - SENTIMENT
# =============================================================================

THRESHOLD_SENTIMENT_BULLISH = 65  # Bullish if score > 65
THRESHOLD_SENTIMENT_BEARISH = 35  # Bearish if score < 35
THRESHOLD_SENTIMENT_STRONG_BULLISH = 80  # Very bullish
THRESHOLD_SENTIMENT_STRONG_BEARISH = 20  # Very bearish

# Percentage thresholds
THRESHOLD_SENTIMENT_BULLISH_PCT = 55  # >55% bullish messages
THRESHOLD_SENTIMENT_BEARISH_PCT = 45  # <45% bullish messages

# =============================================================================
# THRESHOLDS - NEWS MOMENTUM
# =============================================================================

THRESHOLD_MOMENTUM_ACCELERATING = 1.5  # News flow increasing by 50%
THRESHOLD_MOMENTUM_STABLE = 0.8  # News flow relatively stable
SCORE_MOMENTUM_ACCELERATING = 80  # Score for accelerating news
SCORE_MOMENTUM_STABLE = 50  # Score for stable news
SCORE_MOMENTUM_DECLINING = 30  # Score for declining news

# =============================================================================
# THRESHOLDS - TECHNICAL
# =============================================================================

# Moving averages
MA_SHORT_PERIOD = 20  # 20-day moving average
MA_MEDIUM_PERIOD = 50  # 50-day moving average
MA_LONG_PERIOD = 200  # 200-day moving average

# Technical scores based on trend alignment
SCORE_TECHNICAL_TREND_3 = 100  # Above all 3 MAs (best)
SCORE_TECHNICAL_TREND_2 = 70  # Above 2 MAs
SCORE_TECHNICAL_TREND_1 = 50  # Above 1 MA
SCORE_TECHNICAL_TREND_0 = 20  # Below all MAs (worst)

# Volume ratios
VOLUME_RATIO_HIGH = 2.0  # 2x average volume
VOLUME_RATIO_MEDIUM = 1.5  # 1.5x average volume
VOLUME_RATIO_LOW = 1.2  # 1.2x average volume

# RSI thresholds
RSI_OVERBOUGHT = 70  # RSI > 70 is overbought
RSI_OVERSOLD = 30  # RSI < 30 is oversold

# =============================================================================
# THRESHOLDS - SOCIAL BUZZ
# =============================================================================

# StockTwits
THRESHOLD_STOCKTWITS_HIGH = 20  # High activity
THRESHOLD_STOCKTWITS_MEDIUM = 10  # Medium activity
THRESHOLD_STOCKTWITS_LOW = 5  # Low activity
SCORE_STOCKTWITS_HIGH = 30
SCORE_STOCKTWITS_MEDIUM = 20
SCORE_STOCKTWITS_LOW = 10
SCORE_STOCKTWITS_BULLISH_BOOST = 20  # Extra points if sentiment bullish

# Reddit
THRESHOLD_REDDIT_MENTIONS_HIGH = 5  # Mentioned in 5+ posts
THRESHOLD_REDDIT_MENTIONS_MEDIUM = 2  # Mentioned in 2-4 posts
THRESHOLD_REDDIT_SCORE_HIGH = 500  # Total upvotes > 500
THRESHOLD_REDDIT_SCORE_MEDIUM = 100  # Total upvotes > 100

# Trending
THRESHOLD_TRENDING_REDDIT_MENTIONS = 3  # Trending if 3+ mentions

# =============================================================================
# SEC FILINGS
# =============================================================================

SCORE_SEC_8K = 20  # 8-K filing score
SCORE_SEC_INSIDER_BUY = 15  # Insider buying score
SCORE_SEC_INSIDER_SELL = -10  # Insider selling penalty
SCORE_SEC_MA_DEAL = 25  # M&A deal score

# =============================================================================
# SIGNAL RANKER
# =============================================================================

SIGNAL_INITIAL_TRUST = 50  # Initial trust score for new signals
SIGNAL_CONSENSUS_4PLUS = 25  # Bonus for 4+ sources agreeing
SIGNAL_CONSENSUS_2PLUS = 15  # Bonus for 2-3 sources agreeing
SIGNAL_CONSENSUS_1 = 5  # Small bonus for single source
SIGNAL_TIER1_BONUS = 20  # Bonus for tier-1 sources (reliable)
SIGNAL_TIER2_BONUS = 12  # Bonus for tier-2 sources
SIGNAL_MULTI_TICKER_3PLUS = 15  # Signal covers 3+ tickers
SIGNAL_MULTI_TICKER_1PLUS = 10  # Signal covers 1-2 tickers
SIGNAL_CATALYST_SUBSTANTIVE = 15  # Substantive catalyst mentioned
SIGNAL_CATALYST_MENTIONED = 8  # Catalyst mentioned
SIGNAL_SMART_MONEY_DIVERGENCE = 25  # Smart money disagrees with retail

# Signal weight distribution
SIGNAL_WEIGHT_SOURCE_TRUST = 0.25  # Weight for source reliability
SIGNAL_WEIGHT_SIGNAL_STRENGTH = 0.30  # Weight for signal strength
SIGNAL_WEIGHT_TIMING = 0.25  # Weight for timeliness
SIGNAL_WEIGHT_NOVELTY = 0.20  # Weight for new information

# =============================================================================
# CATALYST WINDOWS (days)
# =============================================================================

CATALYST_WINDOW_EARNINGS = 14  # Earnings within 14 days
CATALYST_WINDOW_FDA = 30  # FDA decision within 30 days
CATALYST_WINDOW_PRODUCT_LAUNCH = 30  # Product launch within 30 days
CATALYST_WINDOW_CONFERENCE = 7  # Conference within 7 days
CATALYST_WINDOW_MERGER = 90  # Merger closing within 90 days
CATALYST_WINDOW_IPO = 30  # IPO within 30 days

# Catalyst impact scores
CATALYST_IMPACT_VERY_HIGH = 100
CATALYST_IMPACT_HIGH = 75
CATALYST_IMPACT_MEDIUM = 50
CATALYST_IMPACT_LOW = 25

# =============================================================================
# KEYWORD WEIGHTS
# =============================================================================

# Bullish keywords
KEYWORD_BULLISH_STRONG = 3  # "breakout", "explosive", "surging"
KEYWORD_BULLISH_MEDIUM = 2  # "bullish", "strong", "upgrade"
KEYWORD_BULLISH_WEAK = 1  # "positive", "up", "gain"

# Bearish keywords
KEYWORD_BEARISH_STRONG = 3  # "crash", "plunge", "collapse"
KEYWORD_BEARISH_MEDIUM = 2  # "bearish", "weak", "downgrade"
KEYWORD_BEARISH_WEAK = 1  # "negative", "down", "loss"

# =============================================================================
# LEARNING SYSTEM
# =============================================================================

MIN_TRADES_BEFORE_LEARNING = 20  # Minimum trades before enabling learning
MAX_POSITION_SIZE = 25.0  # Maximum position size (%)
MAX_DRAWDOWN = 15.0  # Maximum drawdown before circuit breaker (%)
LEARNING_ACTIVE = True  # Enable learning system

# Outcome thresholds
OUTCOME_WIN_THRESHOLD = 2.0  # >2% gain = win
OUTCOME_LOSS_THRESHOLD = -2.0  # <-2% loss = loss
OUTCOME_WIN_RATE_MIN = 40  # Minimum 40% win rate
OUTCOME_PROMOTION_THRESHOLD = 3  # 3 consecutive wins = promote strategy

# Parameter learning
PARAM_LEARNING_MIN_SAMPLES = 50  # Minimum samples before optimizing
PARAM_LEARNING_CONFIDENCE_MIN = 0.7  # Minimum confidence (70%)
PARAM_LEARNING_AB_TEST_DURATION = 14  # A/B test duration (days)

# =============================================================================
# FEATURE FLAGS
# =============================================================================

USE_AI_BRAIN_RANKING = False  # Too slow for batch scanning (10-30s per stock)
USE_GOOGLE_TRENDS = True  # Enable Google Trends integration
USE_LEARNING_SYSTEM = True  # Enable parameter learning
USE_OPTIONS_ANALYSIS = True  # Enable options flow analysis
USE_SEC_INTELLIGENCE = True  # Enable SEC filings analysis
USE_SOCIAL_SENTIMENT = True  # Enable social media sentiment
DEBUG = False  # Debug mode (verbose logging)

# =============================================================================
# CORS & SECURITY
# =============================================================================

# Allowed origins for CORS
ALLOWED_ORIGINS = [
    "https://zhuanleee.github.io",  # Production dashboard
    "http://localhost:5000",  # Local development
    "http://127.0.0.1:5000"  # Local development (IP)
]

# Security
MAX_REQUEST_SIZE = 10_000_000  # 10 MB max request size
REQUEST_TIMEOUT = 30  # Request timeout (seconds)
RATE_LIMIT_PER_IP = 100  # Requests per minute per IP
RATE_LIMIT_PER_USER = 1000  # Requests per hour per API key

# =============================================================================
# MODAL DEPLOYMENT
# =============================================================================

MODAL_GPU_TYPE = "T4"  # NVIDIA T4 Tensor Core
MODAL_CPU_COUNT = 2  # CPU cores per container
MODAL_MEMORY_GB = 4  # RAM per container
MODAL_TIMEOUT = 3600  # 1 hour max execution
MODAL_CONCURRENCY = 10  # Parallel GPU containers
MODAL_KEEP_WARM = 1  # Keep 1 container warm

# =============================================================================
# FILE PATHS
# =============================================================================

DATA_DIR = "data"
CACHE_DIR = "cache_data"
LOG_DIR = "logs"
USER_DATA_DIR = "user_data"
BACKUP_DIR = "backups"

# =============================================================================
# LOGGING
# =============================================================================

LOG_LEVEL_PRODUCTION = "INFO"
LOG_LEVEL_DEVELOPMENT = "DEBUG"
LOG_MAX_SIZE_MB = 100  # Rotate logs at 100 MB
LOG_BACKUP_COUNT = 5  # Keep 5 old log files

# =============================================================================
# MARKET HOLIDAYS 2026 (US Stock Market)
# =============================================================================
# Note: Should ideally fetch from NYSE calendar API
# Hardcoded as fallback

from datetime import datetime

MARKET_HOLIDAYS_2026 = [
    datetime(2026, 1, 1),   # New Year's Day
    datetime(2026, 1, 19),  # Martin Luther King Jr. Day
    datetime(2026, 2, 16),  # Presidents' Day
    datetime(2026, 4, 3),   # Good Friday
    datetime(2026, 5, 25),  # Memorial Day
    datetime(2026, 7, 3),   # Independence Day (observed)
    datetime(2026, 9, 7),   # Labor Day
    datetime(2026, 11, 26), # Thanksgiving
    datetime(2026, 12, 25)  # Christmas
]

# =============================================================================
# VALIDATION
# =============================================================================

def validate_constants():
    """Validate that constants are properly configured"""
    # Ensure weights sum to ~1.0
    total_weight = (
        WEIGHT_THEME_HEAT +
        WEIGHT_CATALYST +
        WEIGHT_SOCIAL_BUZZ +
        WEIGHT_NEWS_MOMENTUM +
        WEIGHT_SENTIMENT +
        WEIGHT_ECOSYSTEM +
        WEIGHT_TECHNICAL
    )
    assert 0.99 <= total_weight <= 1.01, f"Weights must sum to 1.0, got {total_weight}"

    # Ensure signal weights sum to 1.0
    signal_weight_sum = (
        SIGNAL_WEIGHT_SOURCE_TRUST +
        SIGNAL_WEIGHT_SIGNAL_STRENGTH +
        SIGNAL_WEIGHT_TIMING +
        SIGNAL_WEIGHT_NOVELTY
    )
    assert 0.99 <= signal_weight_sum <= 1.01, f"Signal weights must sum to 1.0, got {signal_weight_sum}"

    # Ensure rate limits are positive
    assert POLYGON_RATE_LIMIT > 0, "Polygon rate limit must be positive"
    assert STOCKTWITS_RATE_LIMIT > 0, "StockTwits rate limit must be positive"

    # Ensure cache TTLs are reasonable
    assert CACHE_TTL_PRICE >= 60, "Price cache TTL should be at least 1 minute"
    assert CACHE_TTL_SECTOR <= 86400 * 7, "Sector cache TTL should be at most 1 week"

    return True

# Auto-validate on import
if __name__ != "__main__":
    try:
        validate_constants()
    except AssertionError as e:
        import logging
        logging.error(f"Constants validation failed: {e}")
        raise
