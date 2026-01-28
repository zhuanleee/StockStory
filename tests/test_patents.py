"""Tests for patent tracking module."""
import pytest
from unittest.mock import patch, MagicMock


class TestPatentTracker:
    """Tests for patent_tracker module."""

    def test_get_company_names_known_ticker(self):
        """Test company name lookup for known tickers."""
        from src.patents.patent_tracker import get_company_names

        names = get_company_names('NVDA')
        assert 'NVIDIA Corporation' in names

        names = get_company_names('AAPL')
        assert 'Apple Inc' in names

    def test_get_company_names_unknown_ticker(self):
        """Test company name lookup for unknown tickers."""
        from src.patents.patent_tracker import get_company_names

        names = get_company_names('UNKNOWN123')
        assert 'UNKNOWN123' in names

    @patch('src.patents.patent_tracker.requests.get')
    def test_search_patents_by_assignee(self, mock_get):
        """Test patent search API call."""
        from src.patents.patent_tracker import search_patents_by_assignee

        mock_response = MagicMock()
        mock_response.json.return_value = {
            'patents': [
                {'patent_id': '123', 'patent_title': 'Test Patent'}
            ],
            'total_patent_count': 1
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = search_patents_by_assignee('NVIDIA', years_back=1)

        assert result['success'] is True
        assert result['total_patents'] == 1
        assert len(result['patents']) == 1

    @patch('src.patents.patent_tracker.requests.get')
    def test_search_patents_api_error(self, mock_get):
        """Test patent search handles API errors."""
        from src.patents.patent_tracker import search_patents_by_assignee
        import requests

        mock_get.side_effect = requests.exceptions.RequestException('API Error')

        result = search_patents_by_assignee('NVIDIA', years_back=1)

        assert result['success'] is False
        assert 'error' in result

    def test_analyze_patent_portfolio_empty(self):
        """Test portfolio analysis with no patents."""
        from src.patents.patent_tracker import analyze_patent_portfolio

        result = analyze_patent_portfolio([], years_back=3)

        assert result['total_patents'] == 0
        assert result['innovation_score'] == 0
        assert result['trend'] == 'none'

    def test_analyze_patent_portfolio_with_data(self):
        """Test portfolio analysis with patent data."""
        from src.patents.patent_tracker import analyze_patent_portfolio

        patents = [
            {'patent_id': '1', 'patent_date': '2024-06-01', 'cpc_current': [{'cpc_class_id': 'G06'}]},
            {'patent_id': '2', 'patent_date': '2024-07-01', 'cpc_current': [{'cpc_class_id': 'H01'}]},
            {'patent_id': '3', 'patent_date': '2025-01-01', 'cpc_current': [{'cpc_class_id': 'G06'}]},
        ]

        result = analyze_patent_portfolio(patents, years_back=3)

        assert result['patents_per_year'] > 0
        assert len(result['top_categories']) > 0
        assert result['innovation_score'] >= 0

    def test_get_innovation_signal(self):
        """Test innovation signal generation."""
        from src.patents.patent_tracker import get_innovation_signal

        # Mock the get_patent_stats to avoid API call
        with patch('src.patents.patent_tracker.get_patent_stats') as mock_stats:
            mock_stats.return_value = {
                'total_patents': 50,
                'innovation_score': 75,
                'trend': 'accelerating',
                'recent_patent_count': 5,
                'top_categories': [{'section': 'G', 'count': 30, 'description': 'Physics'}],
            }

            result = get_innovation_signal('NVDA')

            assert result['ticker'] == 'NVDA'
            assert result['signal'] in ['strong_innovator', 'active_innovator', 'moderate_innovator', 'some_patents', 'no_patents']
            assert result['signal_score'] >= 0


class TestPatentReportFormatting:
    """Tests for patent report formatting."""

    def test_format_patent_report_no_patents(self):
        """Test formatting when no patents found."""
        from src.patents.patent_tracker import format_patent_report

        with patch('src.patents.patent_tracker.get_patent_stats') as mock_stats:
            mock_stats.return_value = {'total_patents': 0, 'company_names': ['Test Corp']}

            result = format_patent_report('TEST')

            assert 'No patents found' in result

    def test_format_patent_report_with_patents(self):
        """Test formatting with patent data."""
        from src.patents.patent_tracker import format_patent_report

        with patch('src.patents.patent_tracker.get_patent_stats') as mock_stats:
            mock_stats.return_value = {
                'total_patents': 100,
                'patents_per_year': 33.3,
                'innovation_score': 85,
                'trend': 'accelerating',
                'company_names': ['NVIDIA Corporation'],
                'top_categories': [
                    {'section': 'G', 'count': 50, 'description': 'Physics/Computing'},
                ],
                'recent_patents': [
                    {'id': '123', 'title': 'AI Patent', 'date': '2024-12-01'},
                ],
            }

            result = format_patent_report('NVDA')

            assert 'NVDA' in result
            assert '100' in result
            assert 'Innovation Score' in result
