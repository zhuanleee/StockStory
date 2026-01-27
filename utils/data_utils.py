"""
Centralized data utilities for stock data fetching and processing.

Eliminates duplication of:
- SPY data fetching (was in 9 locations)
- MultiIndex column normalization (was in 33 locations)
- RS calculation (was 3 different implementations)

Usage:
    from utils.data_utils import (
        normalize_dataframe_columns,
        get_spy_data_cached,
        calculate_rs,
        download_stock_data,
        get_kl_time,
    )

    # Get cached SPY data
    spy_df, spy_returns = get_spy_data_cached()

    # Download and normalize stock data
    df = download_stock_data('AAPL', period='3mo')

    # Calculate relative strength
    rs_data = calculate_rs(df, spy_returns)

    # Get current time in Kuala Lumpur
    now_kl = get_kl_time()
"""
import time
import threading
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Tuple, Any, List
from dataclasses import dataclass, field
import pandas as pd
import numpy as np


# Kuala Lumpur Timezone (UTC+8)
KL_TIMEZONE = timezone(timedelta(hours=8))


def get_kl_time() -> datetime:
    """Get current time in Kuala Lumpur timezone (UTC+8)."""
    return datetime.now(KL_TIMEZONE)


def get_kl_timestamp() -> str:
    """Get current timestamp string in Kuala Lumpur timezone."""
    return get_kl_time().strftime('%Y-%m-%d %H:%M:%S')


def format_kl_time(dt: datetime = None, fmt: str = '%Y-%m-%d %H:%M') -> str:
    """Format datetime in Kuala Lumpur timezone."""
    if dt is None:
        dt = get_kl_time()
    elif dt.tzinfo is None:
        # Assume UTC if no timezone
        dt = dt.replace(tzinfo=timezone.utc).astimezone(KL_TIMEZONE)
    else:
        dt = dt.astimezone(KL_TIMEZONE)
    return dt.strftime(fmt)

# Lazy import to avoid circular imports
_yf = None


def _get_yfinance():
    """Lazy load yfinance."""
    global _yf
    if _yf is None:
        import yfinance as yf
        _yf = yf
    return _yf


# Import config and logger lazily to avoid circular imports
def _get_config():
    from config import config
    return config


def _get_logger():
    from utils.logging_config import get_logger
    return get_logger(__name__)


@dataclass
class SPYCache:
    """Thread-safe cache for SPY data."""
    data: Optional[pd.DataFrame] = None
    returns: Optional[Dict[str, float]] = None
    timestamp: float = 0
    lock: threading.Lock = field(default_factory=threading.Lock)


_spy_cache = SPYCache()


def normalize_dataframe_columns(df: Optional[pd.DataFrame]) -> Optional[pd.DataFrame]:
    """
    Normalize yfinance DataFrame columns from MultiIndex to flat.

    This replaces 33 instances of:
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

    Args:
        df: DataFrame potentially with MultiIndex columns

    Returns:
        DataFrame with flat column names, or None/empty DataFrame as-is
    """
    if df is None or df.empty:
        return df

    if isinstance(df.columns, pd.MultiIndex):
        df = df.copy()
        df.columns = df.columns.get_level_values(0)

    return df


def get_spy_data_cached(
    period: str = None,
    force_refresh: bool = False
) -> Tuple[Optional[pd.DataFrame], Optional[Dict[str, float]]]:
    """
    Get cached SPY data for RS calculations.

    This replaces 9 instances of SPY downloading across:
    - app.py:132, 777
    - screener.py:72
    - scanner_automation.py:341
    - market_health.py:432
    - sector_rotation.py:112, 196, 240
    - backtest.py:114
    - backtester.py:57

    Args:
        period: Data period (default from config: '3mo')
        force_refresh: Force cache refresh even if valid

    Returns:
        Tuple of (DataFrame, returns_dict) or (None, None) on error
    """
    global _spy_cache
    logger = _get_logger()
    config = _get_config()

    if period is None:
        period = config.scanner.spy_period

    # Check cache validity
    with _spy_cache.lock:
        cache_valid = (
            not force_refresh and
            _spy_cache.data is not None and
            time.time() - _spy_cache.timestamp < config.cache.ttl_seconds
        )

        if cache_valid:
            return _spy_cache.data, _spy_cache.returns

    # Fetch fresh data
    try:
        yf = _get_yfinance()
        spy = yf.download('SPY', period=period, progress=False)
        spy = normalize_dataframe_columns(spy)

        if spy is None or len(spy) < 20:
            logger.warning(f"Insufficient SPY data returned: {len(spy) if spy is not None else 0} rows")
            return None, None

        close = spy['Close']
        current = float(close.iloc[-1])

        # Calculate returns for various periods
        returns = {}
        period_days = [
            ('5d', 5),
            ('10d', 10),
            ('20d', 20),
            ('1m', 21),
            ('3m', 63),
        ]

        for name, days in period_days:
            if len(close) >= days:
                returns[name] = (current / float(close.iloc[-days]) - 1) * 100

        # Update cache
        with _spy_cache.lock:
            _spy_cache.data = spy
            _spy_cache.returns = returns
            _spy_cache.timestamp = time.time()

        logger.debug(f"SPY cache refreshed: {len(spy)} days, returns={returns}")
        return spy, returns

    except Exception as e:
        logger.error(f"Failed to fetch SPY data: {e}", exc_info=True)
        return None, None


def clear_spy_cache():
    """Clear the SPY cache. Useful for testing."""
    global _spy_cache
    with _spy_cache.lock:
        _spy_cache.data = None
        _spy_cache.returns = None
        _spy_cache.timestamp = 0


def calculate_rs(
    stock_df: Optional[pd.DataFrame],
    spy_returns: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """
    Calculate relative strength vs SPY.

    Consolidates 3 different RS implementations into one consistent method.
    Uses weighted composite: 50% 5-day, 30% 10-day, 20% 20-day.

    Args:
        stock_df: Stock DataFrame with 'Close' column
        spy_returns: Pre-calculated SPY returns (will fetch if None)

    Returns:
        Dict with:
        - rs_5d, rs_10d, rs_20d: Individual period RS values
        - rs_composite: Weighted composite RS
        - rs_score: Score from 0-3 based on composite
    """
    logger = _get_logger()
    config = _get_config()

    default_result = {'rs_composite': 0, 'rs_score': 0}

    if spy_returns is None:
        _, spy_returns = get_spy_data_cached()

    if spy_returns is None:
        return default_result

    stock_df = normalize_dataframe_columns(stock_df)

    if stock_df is None or len(stock_df) < 20:
        return default_result

    try:
        close = stock_df['Close']
        current = float(close.iloc[-1])

        result = {}

        # Calculate RS for each period
        period_config = [
            ('5d', 5, config.scanner.rs_weight_5d),
            ('10d', 10, config.scanner.rs_weight_10d),
            ('20d', 20, config.scanner.rs_weight_20d),
        ]

        weighted_sum = 0
        total_weight = 0

        for period_name, days, weight in period_config:
            if len(close) >= days and period_name in spy_returns:
                stock_ret = (current / float(close.iloc[-days]) - 1) * 100
                rs = stock_ret - spy_returns[period_name]
                result[f'rs_{period_name}'] = round(rs, 2)
                weighted_sum += rs * weight
                total_weight += weight

        # Calculate composite RS
        if total_weight > 0:
            result['rs_composite'] = round(weighted_sum / total_weight, 2)
        else:
            result['rs_composite'] = 0

        # Calculate RS score (0-3)
        rs_comp = result['rs_composite']
        if rs_comp > 5:
            result['rs_score'] = 3
        elif rs_comp > 2:
            result['rs_score'] = 2
        elif rs_comp > 0:
            result['rs_score'] = 1
        else:
            result['rs_score'] = 0

        return result

    except Exception as e:
        logger.error(f"RS calculation failed: {e}", exc_info=True)
        return default_result


def safe_float(val: Any) -> Optional[float]:
    """
    Safely convert any value to float.

    Handles pandas Series, numpy arrays, strings, and None.

    Args:
        val: Value to convert

    Returns:
        Float value or None if conversion fails
    """
    if val is None:
        return None
    try:
        # Handle pandas Series
        if hasattr(val, 'iloc'):
            return float(val.iloc[0])
        # Handle numpy scalar
        if hasattr(val, 'item'):
            return float(val.item())
        return float(val)
    except (ValueError, TypeError, IndexError):
        return None


def safe_get_series(
    df: Optional[pd.DataFrame],
    column: str,
    ticker: Optional[str] = None
) -> Optional[pd.Series]:
    """
    Safely extract a column from yfinance dataframe.

    Handles both single-ticker (flat columns) and multi-ticker
    (MultiIndex columns) DataFrames.

    Args:
        df: DataFrame from yfinance
        column: Column name (e.g., 'Close', 'Volume')
        ticker: Ticker symbol (for MultiIndex DataFrames)

    Returns:
        Series or None if extraction fails
    """
    if df is None or len(df) == 0:
        return None

    try:
        # Try flat columns first
        df = normalize_dataframe_columns(df)
        if column in df.columns:
            return df[column]

        # For multi-ticker downloads, try (column, ticker) format
        if ticker and isinstance(df.columns, pd.MultiIndex):
            if (column, ticker) in df.columns:
                return df[(column, ticker)]

        return None
    except Exception:
        return None


def download_stock_data(
    ticker: str,
    period: str = '3mo',
    normalize: bool = True,
    validate: bool = True
) -> Optional[pd.DataFrame]:
    """
    Download stock data with error handling and normalization.

    Args:
        ticker: Stock symbol
        period: Data period (e.g., '1mo', '3mo', '1y')
        normalize: Whether to normalize MultiIndex columns
        validate: Whether to validate minimum data requirements

    Returns:
        DataFrame or None on error
    """
    logger = _get_logger()

    try:
        yf = _get_yfinance()
        df = yf.download(ticker, period=period, progress=False)

        if df is None or df.empty:
            logger.warning(f"No data returned for {ticker}")
            return None

        if normalize:
            df = normalize_dataframe_columns(df)

        if validate and len(df) < 5:
            logger.warning(f"Insufficient data for {ticker}: {len(df)} rows")
            return None

        return df

    except Exception as e:
        logger.error(f"Failed to download {ticker}: {e}")
        return None


def download_multiple_stocks(
    tickers: List[str],
    period: str = '3mo',
    normalize: bool = True
) -> Optional[pd.DataFrame]:
    """
    Download data for multiple stocks at once.

    More efficient than downloading one by one.

    Args:
        tickers: List of ticker symbols
        period: Data period
        normalize: Whether to normalize columns

    Returns:
        DataFrame with MultiIndex columns or None on error
    """
    logger = _get_logger()

    if not tickers:
        return None

    try:
        yf = _get_yfinance()
        df = yf.download(tickers, period=period, progress=False, group_by='ticker')

        if df is None or df.empty:
            logger.warning(f"No data returned for tickers batch")
            return None

        return df

    except Exception as e:
        logger.error(f"Failed to download multiple stocks: {e}")
        return None


def calculate_atr(
    df: pd.DataFrame,
    period: int = 14
) -> Optional[pd.Series]:
    """
    Calculate Average True Range.

    Args:
        df: DataFrame with High, Low, Close columns
        period: ATR period (default 14)

    Returns:
        ATR Series or None on error
    """
    df = normalize_dataframe_columns(df)

    if df is None or len(df) < period + 1:
        return None

    try:
        high = df['High']
        low = df['Low']
        close = df['Close']

        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))

        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()

        return atr

    except Exception:
        return None


def calculate_rsi(
    df: pd.DataFrame,
    period: int = 14
) -> Optional[pd.Series]:
    """
    Calculate Relative Strength Index.

    Args:
        df: DataFrame with Close column
        period: RSI period (default 14)

    Returns:
        RSI Series or None on error
    """
    df = normalize_dataframe_columns(df)

    if df is None or len(df) < period + 1:
        return None

    try:
        close = df['Close']
        delta = close.diff()

        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    except Exception:
        return None
