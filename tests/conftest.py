"""Pytest configuration and fixtures."""
import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def sample_ticker():
    """Sample ticker for testing."""
    return 'NVDA'


@pytest.fixture
def sample_price():
    """Sample price for testing."""
    return 500.0


@pytest.fixture
def sample_shares():
    """Sample shares for testing."""
    return 10


@pytest.fixture
def mock_patent_data():
    """Mock patent data for testing."""
    return {
        'patents': [
            {
                'patent_id': '12345678',
                'patent_title': 'GPU Computing Method',
                'patent_date': '2024-06-15',
                'cpc_current': [{'cpc_class_id': 'G06'}],
            },
        ],
        'total_patent_count': 1,
    }
