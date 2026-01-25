"""Tests for utils/data_utils.py"""
import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.data_utils import (
    normalize_dataframe_columns,
    get_spy_data_cached,
    calculate_rs,
    safe_float,
    safe_get_series,
    download_stock_data,
    clear_spy_cache,
    calculate_atr,
    calculate_rsi,
)


class TestNormalizeDataframeColumns:
    """Tests for normalize_dataframe_columns function."""

    def test_flat_columns_unchanged(self, sample_stock_df):
        """Flat column DataFrame should pass through unchanged."""
        result = normalize_dataframe_columns(sample_stock_df)
        assert list(result.columns) == list(sample_stock_df.columns)
        assert 'Close' in result.columns

    def test_multiindex_flattened(self, sample_multiindex_df):
        """MultiIndex columns should be flattened."""
        result = normalize_dataframe_columns(sample_multiindex_df)
        assert not isinstance(result.columns, pd.MultiIndex)
        # After flattening, should have base column names
        assert 'Close' in result.columns or len(result.columns) > 0

    def test_none_input(self):
        """None input should return None."""
        assert normalize_dataframe_columns(None) is None

    def test_empty_df(self):
        """Empty DataFrame should be returned as-is."""
        df = pd.DataFrame()
        result = normalize_dataframe_columns(df)
        assert result.empty

    def test_preserves_data(self, sample_stock_df):
        """Should preserve data values."""
        result = normalize_dataframe_columns(sample_stock_df)
        assert len(result) == len(sample_stock_df)
        pd.testing.assert_series_equal(result['Close'], sample_stock_df['Close'])


class TestGetSpyDataCached:
    """Tests for get_spy_data_cached function."""

    def test_returns_tuple(self, mock_yfinance, sample_stock_df):
        """Should return (DataFrame, dict) tuple."""
        clear_spy_cache()
        mock_yfinance.return_value = sample_stock_df

        data, returns = get_spy_data_cached(force_refresh=True)

        assert isinstance(data, pd.DataFrame)
        assert isinstance(returns, dict)

    def test_returns_have_expected_periods(self, mock_yfinance, sample_stock_df):
        """Returns dict should have expected period keys."""
        clear_spy_cache()
        mock_yfinance.return_value = sample_stock_df

        _, returns = get_spy_data_cached(force_refresh=True)

        assert '5d' in returns
        assert '20d' in returns

    def test_cache_hit(self, mock_yfinance, sample_stock_df):
        """Second call should use cache."""
        clear_spy_cache()
        mock_yfinance.return_value = sample_stock_df

        # First call
        get_spy_data_cached(force_refresh=True)
        # Second call
        get_spy_data_cached()

        # Should only download once
        assert mock_yfinance.call_count == 1

    def test_force_refresh_bypasses_cache(self, mock_yfinance, sample_stock_df):
        """Force refresh should bypass cache."""
        clear_spy_cache()
        mock_yfinance.return_value = sample_stock_df

        # First call
        get_spy_data_cached(force_refresh=True)
        # Second call with force_refresh
        get_spy_data_cached(force_refresh=True)

        # Should download twice
        assert mock_yfinance.call_count == 2

    def test_handles_empty_data(self, mock_yfinance):
        """Should handle empty DataFrame gracefully."""
        clear_spy_cache()
        mock_yfinance.return_value = pd.DataFrame()

        data, returns = get_spy_data_cached(force_refresh=True)

        assert data is None or data.empty
        assert returns is None


class TestCalculateRS:
    """Tests for calculate_rs function."""

    def test_returns_dict(self, sample_stock_df, sample_spy_returns):
        """Should return dictionary with RS values."""
        result = calculate_rs(sample_stock_df, sample_spy_returns)

        assert isinstance(result, dict)
        assert 'rs_composite' in result
        assert 'rs_score' in result

    def test_rs_score_in_range(self, sample_stock_df, sample_spy_returns):
        """RS score should be 0-3."""
        result = calculate_rs(sample_stock_df, sample_spy_returns)

        assert 0 <= result['rs_score'] <= 3

    def test_handles_none_stock_df(self, sample_spy_returns):
        """Should return default values for None input."""
        result = calculate_rs(None, sample_spy_returns)

        assert result['rs_composite'] == 0
        assert result['rs_score'] == 0

    def test_handles_none_spy_returns(self, sample_stock_df):
        """Should fetch SPY returns if not provided."""
        # This test may make actual API call or use mock
        result = calculate_rs(sample_stock_df, None)

        assert 'rs_composite' in result
        assert 'rs_score' in result

    def test_handles_insufficient_data(self, sample_spy_returns):
        """Should handle DataFrame with too few rows."""
        short_df = pd.DataFrame({
            'Close': [100, 101, 102],
        })
        result = calculate_rs(short_df, sample_spy_returns)

        assert result['rs_composite'] == 0
        assert result['rs_score'] == 0


class TestSafeFloat:
    """Tests for safe_float function."""

    def test_regular_float(self):
        assert safe_float(3.14) == 3.14

    def test_integer(self):
        assert safe_float(42) == 42.0

    def test_string_number(self):
        assert safe_float("3.14") == 3.14

    def test_none_returns_none(self):
        assert safe_float(None) is None

    def test_series_returns_first(self):
        s = pd.Series([1.5, 2.5, 3.5])
        assert safe_float(s) == 1.5

    def test_invalid_string_returns_none(self):
        assert safe_float("not a number") is None

    def test_numpy_scalar(self):
        val = np.float64(3.14)
        assert safe_float(val) == pytest.approx(3.14)

    def test_empty_series_returns_none(self):
        s = pd.Series([])
        assert safe_float(s) is None


class TestSafeGetSeries:
    """Tests for safe_get_series function."""

    def test_extracts_column(self, sample_stock_df):
        """Should extract column from DataFrame."""
        result = safe_get_series(sample_stock_df, 'Close')

        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_stock_df)

    def test_returns_none_for_missing_column(self, sample_stock_df):
        """Should return None for missing column."""
        result = safe_get_series(sample_stock_df, 'NonexistentColumn')

        assert result is None

    def test_handles_none_df(self):
        """Should handle None DataFrame."""
        result = safe_get_series(None, 'Close')

        assert result is None

    def test_handles_empty_df(self):
        """Should handle empty DataFrame."""
        result = safe_get_series(pd.DataFrame(), 'Close')

        assert result is None


class TestDownloadStockData:
    """Tests for download_stock_data function."""

    def test_returns_dataframe(self, mock_yfinance, sample_stock_df):
        """Should return DataFrame for valid ticker."""
        mock_yfinance.return_value = sample_stock_df

        result = download_stock_data('AAPL')

        assert isinstance(result, pd.DataFrame)
        mock_yfinance.assert_called_once()

    def test_returns_none_on_empty(self, mock_yfinance):
        """Should return None for empty result."""
        mock_yfinance.return_value = pd.DataFrame()

        result = download_stock_data('INVALID')

        assert result is None

    def test_normalizes_columns(self, mock_yfinance, sample_multiindex_df):
        """Should normalize MultiIndex columns by default."""
        mock_yfinance.return_value = sample_multiindex_df

        result = download_stock_data('AAPL', normalize=True)

        if result is not None:
            assert not isinstance(result.columns, pd.MultiIndex)


class TestCalculateATR:
    """Tests for calculate_atr function."""

    def test_returns_series(self, sample_stock_df):
        """Should return a Series."""
        result = calculate_atr(sample_stock_df, period=14)

        assert isinstance(result, pd.Series)

    def test_correct_length(self, sample_stock_df):
        """Should have same length as input."""
        result = calculate_atr(sample_stock_df, period=14)

        assert len(result) == len(sample_stock_df)

    def test_handles_none(self):
        """Should handle None input."""
        result = calculate_atr(None)

        assert result is None

    def test_handles_insufficient_data(self):
        """Should handle insufficient data."""
        short_df = pd.DataFrame({
            'High': [100, 101],
            'Low': [99, 100],
            'Close': [99.5, 100.5],
        })
        result = calculate_atr(short_df, period=14)

        assert result is None


class TestCalculateRSI:
    """Tests for calculate_rsi function."""

    def test_returns_series(self, sample_stock_df):
        """Should return a Series."""
        result = calculate_rsi(sample_stock_df, period=14)

        assert isinstance(result, pd.Series)

    def test_values_in_range(self, sample_stock_df):
        """RSI values should be 0-100."""
        result = calculate_rsi(sample_stock_df, period=14)

        # Filter out NaN values
        valid_values = result.dropna()
        assert all(0 <= v <= 100 for v in valid_values)

    def test_handles_none(self):
        """Should handle None input."""
        result = calculate_rsi(None)

        assert result is None
