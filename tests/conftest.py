"""
Shared test fixtures and configuration.

Provides common fixtures for testing stock scanner components.
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def sample_stock_df():
    """Create sample OHLCV DataFrame for testing."""
    dates = pd.date_range(end=datetime.now(), periods=100, freq='D')
    np.random.seed(42)

    # Generate realistic price data
    close = 100 + np.cumsum(np.random.randn(100) * 2)

    return pd.DataFrame({
        'Open': close * (1 + np.random.randn(100) * 0.01),
        'High': close * (1 + abs(np.random.randn(100) * 0.02)),
        'Low': close * (1 - abs(np.random.randn(100) * 0.02)),
        'Close': close,
        'Volume': np.random.randint(1000000, 10000000, 100),
    }, index=dates)


@pytest.fixture
def sample_multiindex_df(sample_stock_df):
    """Create sample MultiIndex DataFrame (yfinance format for multiple tickers)."""
    df = sample_stock_df.copy()
    df.columns = pd.MultiIndex.from_product([df.columns, ['AAPL']])
    return df


@pytest.fixture
def sample_spy_returns():
    """Sample SPY returns for RS calculations."""
    return {
        '5d': 1.5,
        '10d': 2.8,
        '20d': 4.2,
        '1m': 4.5,
        '3m': 8.0,
    }


@pytest.fixture
def mock_yfinance(sample_stock_df):
    """Mock yfinance.download for testing."""
    with patch('yfinance.download') as mock:
        mock.return_value = sample_stock_df
        yield mock


@pytest.fixture
def mock_requests():
    """Mock requests for testing HTTP calls."""
    with patch('requests.post') as mock_post, \
         patch('requests.get') as mock_get:

        # Default successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'ok': True}

        mock_post.return_value = mock_response
        mock_get.return_value = mock_response

        yield {'post': mock_post, 'get': mock_get}


@pytest.fixture
def mock_telegram_response():
    """Mock successful Telegram API response."""
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {
        'ok': True,
        'result': {'message_id': 12345}
    }
    return response


@pytest.fixture
def mock_telegram_rate_limit():
    """Mock Telegram rate limit response."""
    response = MagicMock()
    response.status_code = 429
    response.json.return_value = {
        'ok': False,
        'description': 'Too Many Requests',
        'parameters': {'retry_after': 30}
    }
    return response


@pytest.fixture
def app_client():
    """Create Flask test client."""
    # Import app here to avoid import issues
    from app import app
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def temp_storage_dir(tmp_path):
    """Create temporary storage directory for testing."""
    storage_dir = tmp_path / "user_data"
    storage_dir.mkdir()
    return storage_dir


@pytest.fixture
def sample_watchlist():
    """Sample watchlist data."""
    return {
        'AAPL': {'added': '2024-01-15T10:00:00'},
        'MSFT': {'added': '2024-01-16T11:00:00'},
        'GOOGL': {'added': '2024-01-17T12:00:00'},
    }


@pytest.fixture
def sample_alerts():
    """Sample alerts data."""
    return {
        'AAPL': {
            'above': [150.0, 160.0],
            'below': [140.0],
        },
        'MSFT': {
            'above': [400.0],
            'below': [],
        },
    }


@pytest.fixture
def sample_portfolio():
    """Sample portfolio data."""
    return {
        'positions': {
            'AAPL': {
                'shares': 100,
                'avg_cost': 145.50,
                'added': '2024-01-10T09:30:00',
            },
        },
        'closed_trades': [
            {
                'ticker': 'MSFT',
                'shares': 50,
                'entry_price': 380.0,
                'exit_price': 395.0,
                'pnl': 750.0,
                'pnl_pct': 3.95,
                'closed': '2024-01-14T15:00:00',
            },
        ],
    }


# Configure pytest
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
