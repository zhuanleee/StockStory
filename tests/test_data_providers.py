"""Tests for utils/data_providers.py"""
import pytest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.data_providers import (
    FinnhubProvider,
    TiingoProvider,
    AlphaVantageProvider,
    SECEdgarProvider,
    FREDProvider,
    UnifiedDataFetcher,
    check_provider_status,
    get_available_providers,
    RateLimiter,
)


class TestRateLimiter:
    """Tests for RateLimiter class."""

    def test_allows_requests_under_limit(self):
        """Should allow requests under rate limit."""
        limiter = RateLimiter(calls_per_minute=60)
        # Should not raise or sleep
        for _ in range(5):
            limiter.wait_if_needed()

    def test_tracks_calls(self):
        """Should track call timestamps."""
        limiter = RateLimiter(calls_per_minute=10)
        limiter.wait_if_needed()
        assert len(limiter.calls) == 1


class TestFinnhubProvider:
    """Tests for FinnhubProvider."""

    def test_is_configured_without_key(self):
        """Should return False when key not set."""
        with patch.dict('os.environ', {}, clear=True):
            # Force reimport to pick up env change
            from utils.data_providers import DataProviderConfig
            DataProviderConfig.FINNHUB_API_KEY = ''
            assert FinnhubProvider.is_configured() is False

    def test_get_quote_returns_none_without_key(self):
        """Should return None when not configured."""
        with patch.object(FinnhubProvider, 'is_configured', return_value=False):
            result = FinnhubProvider.get_quote('AAPL')
            assert result is None

    @patch('utils.data_providers.requests.get')
    def test_get_quote_success(self, mock_get):
        """Should return quote data on success."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'c': 150.0, 'h': 152.0, 'l': 148.0,
            'o': 149.0, 'pc': 148.5, 't': 1234567890
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        with patch.object(FinnhubProvider, 'is_configured', return_value=True):
            with patch('utils.data_providers.DataProviderConfig.FINNHUB_API_KEY', 'test_key'):
                result = FinnhubProvider.get_quote('AAPL')

        assert result is not None
        assert result['c'] == 150.0
        assert 'dp' in result  # Percent change added

    @patch('utils.data_providers.requests.get')
    def test_get_company_news_returns_list(self, mock_get):
        """Should return list of news."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {'headline': 'Test', 'summary': 'News', 'datetime': 1234567890}
        ]
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        with patch.object(FinnhubProvider, 'is_configured', return_value=True):
            with patch('utils.data_providers.DataProviderConfig.FINNHUB_API_KEY', 'test_key'):
                result = FinnhubProvider.get_company_news('AAPL')

        assert isinstance(result, list)


class TestTiingoProvider:
    """Tests for TiingoProvider."""

    def test_is_configured_without_key(self):
        """Should return False when key not set."""
        with patch('utils.data_providers.DataProviderConfig.TIINGO_API_KEY', ''):
            assert TiingoProvider.is_configured() is False

    @patch('utils.data_providers.requests.get')
    def test_get_eod_prices_returns_list(self, mock_get):
        """Should return list of price data."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {'date': '2024-01-01', 'close': 150.0, 'volume': 1000000}
        ]
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        with patch.object(TiingoProvider, 'is_configured', return_value=True):
            with patch('utils.data_providers.DataProviderConfig.TIINGO_API_KEY', 'test_key'):
                result = TiingoProvider.get_eod_prices('AAPL')

        assert isinstance(result, list)

    @patch('utils.data_providers.requests.get')
    def test_get_news_returns_list(self, mock_get):
        """Should return list of news."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {'title': 'Test News', 'description': 'Content'}
        ]
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        with patch.object(TiingoProvider, 'is_configured', return_value=True):
            with patch('utils.data_providers.DataProviderConfig.TIINGO_API_KEY', 'test_key'):
                result = TiingoProvider.get_news(['AAPL'])

        assert isinstance(result, list)


class TestAlphaVantageProvider:
    """Tests for AlphaVantageProvider."""

    def test_is_configured_without_key(self):
        """Should return False when key not set."""
        with patch('utils.data_providers.DataProviderConfig.ALPHA_VANTAGE_API_KEY', ''):
            assert AlphaVantageProvider.is_configured() is False

    @patch('utils.data_providers.requests.get')
    def test_get_company_overview(self, mock_get):
        """Should return company fundamentals."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'Symbol': 'AAPL',
            'Name': 'Apple Inc',
            'MarketCapitalization': '3000000000000'
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        with patch.object(AlphaVantageProvider, 'is_configured', return_value=True):
            with patch('utils.data_providers.DataProviderConfig.ALPHA_VANTAGE_API_KEY', 'test'):
                result = AlphaVantageProvider.get_company_overview('AAPL')

        assert result is not None
        assert result['Symbol'] == 'AAPL'


class TestSECEdgarProvider:
    """Tests for SECEdgarProvider."""

    @patch('utils.data_providers.requests.get')
    def test_get_company_cik(self, mock_get):
        """Should return CIK for ticker."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            '0': {'cik_str': 320193, 'ticker': 'AAPL', 'title': 'Apple Inc'}
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = SECEdgarProvider.get_company_cik('AAPL')

        assert result == '0000320193'

    @patch('utils.data_providers.requests.get')
    def test_get_company_cik_not_found(self, mock_get):
        """Should return None for unknown ticker."""
        mock_response = MagicMock()
        mock_response.json.return_value = {}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = SECEdgarProvider.get_company_cik('INVALID')

        assert result is None


class TestFREDProvider:
    """Tests for FREDProvider."""

    def test_is_configured_without_key(self):
        """Should return False when key not set."""
        with patch('utils.data_providers.DataProviderConfig.FRED_API_KEY', ''):
            assert FREDProvider.is_configured() is False

    def test_series_ids_defined(self):
        """Should have common economic series defined."""
        assert 'fed_funds_rate' in FREDProvider.SERIES
        assert 'unemployment' in FREDProvider.SERIES
        assert 'treasury_10y' in FREDProvider.SERIES
        assert 'vix' in FREDProvider.SERIES

    @patch('utils.data_providers.requests.get')
    def test_get_series_returns_list(self, mock_get):
        """Should return list of observations."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'observations': [
                {'date': '2024-01-01', 'value': '5.25'}
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        with patch.object(FREDProvider, 'is_configured', return_value=True):
            with patch('utils.data_providers.DataProviderConfig.FRED_API_KEY', 'test'):
                result = FREDProvider.get_series('FEDFUNDS')

        assert isinstance(result, list)


class TestUnifiedDataFetcher:
    """Tests for UnifiedDataFetcher."""

    def test_get_quote_fallback_to_yfinance(self):
        """Should fall back to yfinance when providers not configured."""
        with patch.object(FinnhubProvider, 'is_configured', return_value=False):
            with patch.object(TiingoProvider, 'is_configured', return_value=False):
                with patch('yfinance.Ticker') as mock_ticker:
                    mock_info = MagicMock()
                    mock_info.last_price = 150.0
                    mock_info.day_high = 152.0
                    mock_info.day_low = 148.0
                    mock_info.open = 149.0
                    mock_info.previous_close = 148.5
                    mock_info.last_volume = 1000000
                    mock_ticker.return_value.fast_info = mock_info

                    result = UnifiedDataFetcher.get_quote('AAPL')

        assert result is not None
        assert result['price'] == 150.0
        assert result['source'] == 'yfinance'

    def test_get_news_returns_list(self):
        """Should return list of news."""
        with patch.object(FinnhubProvider, 'is_configured', return_value=False):
            with patch.object(TiingoProvider, 'is_configured', return_value=False):
                result = UnifiedDataFetcher.get_news('AAPL')

        assert isinstance(result, list)

    def test_get_insider_activity_returns_list(self):
        """Should return list of insider trades."""
        with patch.object(FinnhubProvider, 'is_configured', return_value=False):
            with patch.object(SECEdgarProvider, 'get_insider_transactions', return_value=[]):
                result = UnifiedDataFetcher.get_insider_activity('AAPL')

        assert isinstance(result, list)


class TestProviderStatus:
    """Tests for provider status functions."""

    def test_check_provider_status_returns_dict(self):
        """Should return dict with all providers."""
        status = check_provider_status()

        assert isinstance(status, dict)
        assert 'finnhub' in status
        assert 'tiingo' in status
        assert 'alpha_vantage' in status
        assert 'fred' in status
        assert 'sec_edgar' in status

    def test_sec_edgar_always_available(self):
        """SEC EDGAR should always be available (no key needed)."""
        status = check_provider_status()
        assert status['sec_edgar'] is True

    def test_get_available_providers_returns_list(self):
        """Should return list of available providers."""
        providers = get_available_providers()
        assert isinstance(providers, list)
        assert 'sec_edgar' in providers  # Always available
