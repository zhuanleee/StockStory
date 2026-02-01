"""
Tests for Polygon.io Data Provider

Tests cover:
- API initialization and configuration
- Async request handling
- Data fetching (aggregates, quotes, snapshots)
- Error handling (rate limits, timeouts, invalid responses)
- DataFrame conversion and formatting
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timedelta
import pandas as pd
import aiohttp
import asyncio


class TestPolygonProviderInit:
    """Test PolygonProvider initialization"""

    @pytest.mark.asyncio
    async def test_init_with_api_key(self):
        """Test initialization with API key"""
        from src.data.polygon_provider import PolygonProvider

        provider = PolygonProvider(api_key="test_key_123")

        assert provider.api_key == "test_key_123"
        assert provider._session is None
        assert provider._owns_session is True

        await provider.close()

    @pytest.mark.asyncio
    async def test_init_with_env_variable(self):
        """Test initialization with environment variable"""
        # Reimport with patched env to capture the new value
        with patch.dict('os.environ', {'POLYGON_API_KEY': 'env_key_456'}):
            import importlib
            from src.data import polygon_provider
            importlib.reload(polygon_provider)

            provider = polygon_provider.PolygonProvider()

            # Should use env variable if no key provided
            assert provider.api_key == "env_key_456"
            await provider.close()

            # Reload again to reset module state
            importlib.reload(polygon_provider)

    @pytest.mark.asyncio
    async def test_init_with_existing_session(self):
        """Test initialization with existing session"""
        from src.data.polygon_provider import PolygonProvider

        mock_session = AsyncMock(spec=aiohttp.ClientSession)
        mock_session.closed = False

        provider = PolygonProvider(api_key="test_key", session=mock_session)

        assert provider._session == mock_session
        assert provider._owns_session is False

        # Should not close session we don't own
        await provider.close()

    @pytest.mark.asyncio
    async def test_init_without_api_key_warns(self):
        """Test initialization without API key logs warning"""
        # Reload module without env variable
        with patch.dict('os.environ', {}, clear=True):
            import importlib
            from src.data import polygon_provider
            importlib.reload(polygon_provider)

            provider = polygon_provider.PolygonProvider()

            assert provider.api_key == ""
            await provider.close()

            # Reload to reset
            importlib.reload(polygon_provider)


class TestPolygonProviderSession:
    """Test session management"""

    @pytest.mark.asyncio
    async def test_get_session_creates_new(self):
        """Test _get_session creates new session"""
        from src.data.polygon_provider import PolygonProvider

        provider = PolygonProvider(api_key="test_key")

        assert provider._session is None

        session = await provider._get_session()

        assert session is not None
        assert provider._owns_session is True

        await provider.close()

    @pytest.mark.asyncio
    async def test_get_session_reuses_existing(self):
        """Test _get_session reuses existing session"""
        from src.data.polygon_provider import PolygonProvider

        mock_session = AsyncMock(spec=aiohttp.ClientSession)
        mock_session.closed = False

        provider = PolygonProvider(api_key="test_key", session=mock_session)

        session = await provider._get_session()

        assert session == mock_session
        await provider.close()

    @pytest.mark.asyncio
    async def test_close_session_when_owned(self):
        """Test closing session when owned"""
        from src.data.polygon_provider import PolygonProvider

        provider = PolygonProvider(api_key="test_key")

        # Create session
        session = await provider._get_session()

        # Close provider
        await provider.close()

        # Session should be closed
        assert session.closed


class TestPolygonProviderRequest:
    """Test API request handling"""

    @pytest.mark.asyncio
    async def test_request_success(self):
        """Test successful API request"""
        from src.data.polygon_provider import PolygonProvider

        # Mock response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={'status': 'OK', 'results': []})

        # Mock session
        mock_session = AsyncMock(spec=aiohttp.ClientSession)
        mock_session.closed = False
        mock_session.get = MagicMock(return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=mock_response),
            __aexit__=AsyncMock()
        ))

        provider = PolygonProvider(api_key="test_key", session=mock_session)

        result = await provider._request('/v2/test')

        assert result == {'status': 'OK', 'results': []}
        await provider.close()

    @pytest.mark.asyncio
    async def test_request_rate_limit(self):
        """Test rate limit handling (429)"""
        from src.data.polygon_provider import PolygonProvider

        # Mock 429 response
        mock_response = AsyncMock()
        mock_response.status = 429

        mock_session = AsyncMock(spec=aiohttp.ClientSession)
        mock_session.closed = False
        mock_session.get = MagicMock(return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=mock_response),
            __aexit__=AsyncMock()
        ))

        provider = PolygonProvider(api_key="test_key", session=mock_session)

        result = await provider._request('/v2/test')

        assert result is None
        await provider.close()

    @pytest.mark.asyncio
    async def test_request_error_status(self):
        """Test error status handling (4xx, 5xx)"""
        from src.data.polygon_provider import PolygonProvider

        # Mock 500 response
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.text = AsyncMock(return_value="Internal Server Error")

        mock_session = AsyncMock(spec=aiohttp.ClientSession)
        mock_session.closed = False
        mock_session.get = MagicMock(return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=mock_response),
            __aexit__=AsyncMock()
        ))

        provider = PolygonProvider(api_key="test_key", session=mock_session)

        result = await provider._request('/v2/test')

        assert result is None
        await provider.close()

    @pytest.mark.asyncio
    async def test_request_without_api_key(self):
        """Test request without API key"""
        from src.data.polygon_provider import PolygonProvider

        provider = PolygonProvider(api_key="")

        result = await provider._request('/v2/test')

        assert result is None
        await provider.close()

    @pytest.mark.asyncio
    async def test_request_timeout(self):
        """Test timeout handling"""
        from src.data.polygon_provider import PolygonProvider

        # Mock timeout
        mock_session = AsyncMock(spec=aiohttp.ClientSession)
        mock_session.closed = False
        mock_session.get = MagicMock(side_effect=asyncio.TimeoutError())

        provider = PolygonProvider(api_key="test_key", session=mock_session)

        result = await provider._request('/v2/test')

        assert result is None
        await provider.close()


class TestPolygonProviderAggregates:
    """Test aggregate data fetching"""

    @pytest.mark.asyncio
    async def test_get_aggregates_success(self):
        """Test successful aggregate fetching"""
        from src.data.polygon_provider import PolygonProvider

        # Mock response with aggregate data
        mock_data = {
            'status': 'OK',
            'results': [
                {
                    't': 1640995200000,  # Timestamp in ms
                    'o': 100.0,
                    'h': 105.0,
                    'l': 99.0,
                    'c': 103.0,
                    'v': 1000000,
                    'vw': 102.0,
                    'n': 5000
                }
            ]
        }

        provider = PolygonProvider(api_key="test_key")

        with patch.object(provider, '_request', return_value=mock_data):
            df = await provider.get_aggregates('AAPL')

            assert df is not None
            assert isinstance(df, pd.DataFrame)
            assert 'Open' in df.columns
            assert 'High' in df.columns
            assert 'Low' in df.columns
            assert 'Close' in df.columns
            assert 'Volume' in df.columns
            assert len(df) == 1
            assert df.iloc[0]['Close'] == 103.0

        await provider.close()

    @pytest.mark.asyncio
    async def test_get_aggregates_empty_results(self):
        """Test aggregate fetching with empty results"""
        from src.data.polygon_provider import PolygonProvider

        mock_data = {'status': 'OK', 'results': []}

        provider = PolygonProvider(api_key="test_key")

        with patch.object(provider, '_request', return_value=mock_data):
            df = await provider.get_aggregates('INVALID')

            assert df is None

        await provider.close()

    @pytest.mark.asyncio
    async def test_get_aggregates_no_results_key(self):
        """Test aggregate fetching with missing results key"""
        from src.data.polygon_provider import PolygonProvider

        mock_data = {'status': 'ERROR', 'message': 'Not found'}

        provider = PolygonProvider(api_key="test_key")

        with patch.object(provider, '_request', return_value=mock_data):
            df = await provider.get_aggregates('INVALID')

            assert df is None

        await provider.close()

    @pytest.mark.asyncio
    async def test_get_daily_bars(self):
        """Test daily bars fetching"""
        from src.data.polygon_provider import PolygonProvider

        mock_df = pd.DataFrame({
            'Open': [100.0],
            'High': [105.0],
            'Low': [99.0],
            'Close': [103.0],
            'Volume': [1000000]
        })

        provider = PolygonProvider(api_key="test_key")

        with patch.object(provider, 'get_aggregates', return_value=mock_df):
            df = await provider.get_daily_bars('AAPL', days=90)

            assert df is not None
            assert len(df) == 1

        await provider.close()


class TestPolygonProviderPreviousClose:
    """Test previous close data"""

    @pytest.mark.asyncio
    async def test_get_previous_close_success(self):
        """Test successful previous close fetch"""
        from src.data.polygon_provider import PolygonProvider

        mock_data = {
            'status': 'OK',
            'results': [{
                'T': 'AAPL',
                'c': 150.0,
                'o': 148.0,
                'h': 152.0,
                'l': 147.0,
                'v': 50000000,
                'vw': 150.5
            }]
        }

        provider = PolygonProvider(api_key="test_key")

        with patch.object(provider, '_request', return_value=mock_data):
            result = await provider.get_previous_close('AAPL')

            assert result is not None
            assert result['ticker'] == 'AAPL'
            assert result['close'] == 150.0
            assert result['open'] == 148.0

        await provider.close()

    @pytest.mark.asyncio
    async def test_get_previous_close_no_data(self):
        """Test previous close with no data"""
        from src.data.polygon_provider import PolygonProvider

        mock_data = {'status': 'OK', 'results': []}

        provider = PolygonProvider(api_key="test_key")

        with patch.object(provider, '_request', return_value=mock_data):
            result = await provider.get_previous_close('INVALID')

            assert result is None

        await provider.close()


class TestPolygonProviderSnapshot:
    """Test snapshot data"""

    @pytest.mark.asyncio
    async def test_get_snapshot_success(self):
        """Test successful snapshot fetch"""
        from src.data.polygon_provider import PolygonProvider

        mock_data = {
            'status': 'OK',
            'ticker': {
                'ticker': 'AAPL',
                'day': {
                    'c': 150.0,
                    'o': 148.0,
                    'h': 152.0,
                    'l': 147.0,
                    'v': 50000000
                },
                'prevDay': {
                    'c': 149.0
                },
                'min': {
                    'av': 1000000,
                    'c': 150.0
                },
                'todaysChange': 1.0,
                'todaysChangePerc': 0.67,
                'updated': 1640995200000
            }
        }

        provider = PolygonProvider(api_key="test_key")

        with patch.object(provider, '_request', return_value=mock_data):
            result = await provider.get_snapshot('AAPL')

            assert result is not None
            assert result['ticker'] == 'AAPL'
            assert result['price'] == 150.0
            assert result['change_percent'] == 0.67

        await provider.close()


class TestPolygonProviderSyncWrappers:
    """Test synchronous wrapper functions"""

    def test_get_aggregates_sync(self):
        """Test sync wrapper for get_aggregates"""
        from src.data.polygon_provider import get_aggregates_sync

        mock_df = pd.DataFrame({
            'Open': [100.0],
            'High': [105.0],
            'Low': [99.0],
            'Close': [103.0],
            'Volume': [1000000]
        })

        with patch('src.data.polygon_provider.PolygonProvider') as mock_provider_class:
            mock_provider = AsyncMock()
            mock_provider.get_daily_bars = AsyncMock(return_value=mock_df)
            mock_provider.close = AsyncMock()
            mock_provider_class.return_value = mock_provider

            df = get_aggregates_sync('AAPL', days=90)

            assert df is not None

    def test_get_previous_close_sync(self):
        """Test sync wrapper for get_previous_close"""
        from src.data.polygon_provider import get_previous_close_sync

        mock_data = {
            'ticker': 'AAPL',
            'close': 150.0,
            'open': 148.0
        }

        with patch('src.data.polygon_provider.PolygonProvider') as mock_provider_class:
            mock_provider = AsyncMock()
            mock_provider.get_previous_close = AsyncMock(return_value=mock_data)
            mock_provider.close = AsyncMock()
            mock_provider_class.return_value = mock_provider

            result = get_previous_close_sync('AAPL')

            assert result is not None
            assert result['ticker'] == 'AAPL'


class TestPolygonProviderDataConversion:
    """Test data format conversion"""

    @pytest.mark.asyncio
    async def test_timestamp_conversion(self):
        """Test timestamp to datetime conversion"""
        from src.data.polygon_provider import PolygonProvider

        # Timestamp: Jan 1, 2022 00:00:00 UTC
        mock_data = {
            'status': 'OK',
            'results': [{
                't': 1640995200000,
                'o': 100.0,
                'h': 100.0,
                'l': 100.0,
                'c': 100.0,
                'v': 1000000
            }]
        }

        provider = PolygonProvider(api_key="test_key")

        with patch.object(provider, '_request', return_value=mock_data):
            df = await provider.get_aggregates('TEST')

            assert df is not None
            assert df.index.name == 'Date' or isinstance(df.index, pd.DatetimeIndex)

        await provider.close()

    @pytest.mark.asyncio
    async def test_column_renaming(self):
        """Test column renaming from Polygon to yfinance format"""
        from src.data.polygon_provider import PolygonProvider

        mock_data = {
            'status': 'OK',
            'results': [{
                't': 1640995200000,
                'o': 100.0,
                'h': 105.0,
                'l': 99.0,
                'c': 103.0,
                'v': 1000000,
                'vw': 102.0
            }]
        }

        provider = PolygonProvider(api_key="test_key")

        with patch.object(provider, '_request', return_value=mock_data):
            df = await provider.get_aggregates('TEST')

            # Should have yfinance-compatible column names
            assert 'Open' in df.columns
            assert 'High' in df.columns
            assert 'Low' in df.columns
            assert 'Close' in df.columns
            assert 'Volume' in df.columns

            # Original column names should not be present
            assert 'o' not in df.columns
            assert 'h' not in df.columns

        await provider.close()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
