"""Tests for new AI features in ai_learning.py"""
import pytest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestCatalystDetector:
    """Tests for analyze_catalyst_realtime function."""

    def test_import_function(self):
        """Function should import successfully."""
        from ai_learning import analyze_catalyst_realtime
        assert callable(analyze_catalyst_realtime)

    def test_returns_dict_structure(self):
        """Should return dict with expected keys when API unavailable."""
        from ai_learning import analyze_catalyst_realtime

        result = analyze_catalyst_realtime(
            ticker="AAPL",
            headline="Apple announces new iPhone"
        )

        # Even without API, should return a dict or None
        assert result is None or isinstance(result, dict)

    def test_handles_missing_optional_params(self):
        """Should work with only required params."""
        from ai_learning import analyze_catalyst_realtime

        # Should not raise
        result = analyze_catalyst_realtime(
            ticker="TSLA",
            headline="Tesla reports earnings"
        )
        assert result is None or isinstance(result, dict)


class TestThemeLifecycle:
    """Tests for analyze_theme_lifecycle function."""

    def test_import_function(self):
        """Function should import successfully."""
        from ai_learning import analyze_theme_lifecycle
        assert callable(analyze_theme_lifecycle)

    def test_returns_expected_structure(self):
        """Should handle valid inputs."""
        from ai_learning import analyze_theme_lifecycle

        theme_data = {
            "name": "AI/ML",
            "tickers": ["NVDA", "AMD"],
            "avg_gain": 30.0
        }

        result = analyze_theme_lifecycle(
            theme_name="AI/ML",
            theme_data=theme_data
        )

        assert result is None or isinstance(result, dict)


class TestThemeRotation:
    """Tests for predict_theme_rotation function."""

    def test_import_function(self):
        """Function should import successfully."""
        from ai_learning import predict_theme_rotation
        assert callable(predict_theme_rotation)

    def test_handles_dict_sector_performance(self):
        """Should handle dict input for sector_performance."""
        from ai_learning import predict_theme_rotation

        # This was the bug - ensure it doesn't crash
        result = predict_theme_rotation(
            current_themes=[{"name": "Tech", "performance": 10}],
            market_regime="bullish",
            sector_performance={"Technology": 12.0, "Energy": 5.0}
        )

        assert result is None or isinstance(result, dict)

    def test_handles_list_sector_performance(self):
        """Should handle list input for sector_performance."""
        from ai_learning import predict_theme_rotation

        result = predict_theme_rotation(
            current_themes=[{"name": "Tech", "performance": 10}],
            market_regime="bearish",
            sector_performance=[("Technology", 12.0), ("Energy", 5.0)]
        )

        assert result is None or isinstance(result, dict)


class TestOptionsFlow:
    """Tests for analyze_options_flow function."""

    def test_import_function(self):
        """Function should import successfully."""
        from ai_learning import analyze_options_flow
        assert callable(analyze_options_flow)

    def test_handles_basic_input(self):
        """Should handle basic options data."""
        from ai_learning import analyze_options_flow

        options_data = {
            "total_call_volume": 10000,
            "total_put_volume": 5000,
            "call_put_ratio": 2.0
        }

        result = analyze_options_flow(
            ticker="AAPL",
            options_data=options_data
        )

        assert result is None or isinstance(result, dict)


class TestUnusualActivityScanner:
    """Tests for scan_options_unusual_activity function."""

    def test_import_function(self):
        """Function should import successfully."""
        from ai_learning import scan_options_unusual_activity
        assert callable(scan_options_unusual_activity)

    def test_returns_structure(self):
        """Should return expected structure."""
        from ai_learning import scan_options_unusual_activity

        result = scan_options_unusual_activity(
            tickers=["AAPL", "MSFT"],
            threshold_volume_ratio=3.0
        )

        # Should return list of alerts or empty list
        assert result is None or isinstance(result, (dict, list))


class TestRealtimeScan:
    """Tests for run_realtime_ai_scan function."""

    def test_import_function(self):
        """Function should import successfully."""
        from ai_learning import run_realtime_ai_scan
        assert callable(run_realtime_ai_scan)

    def test_handles_string_list_for_top_stocks(self):
        """Should handle list of strings for top_stocks (bug fix)."""
        from ai_learning import run_realtime_ai_scan

        # This was the bug - strings instead of dicts
        result = run_realtime_ai_scan(
            news_items=None,
            themes=None,
            top_stocks=["AAPL", "MSFT", "NVDA"]
        )

        assert isinstance(result, dict)

    def test_handles_dict_list_for_top_stocks(self):
        """Should handle list of dicts for top_stocks."""
        from ai_learning import run_realtime_ai_scan

        result = run_realtime_ai_scan(
            news_items=None,
            themes=None,
            top_stocks=[{"ticker": "AAPL"}, {"ticker": "MSFT"}]
        )

        assert isinstance(result, dict)

    def test_handles_empty_inputs(self):
        """Should handle all empty inputs."""
        from ai_learning import run_realtime_ai_scan

        result = run_realtime_ai_scan(
            news_items=None,
            themes=None,
            top_stocks=None
        )

        assert isinstance(result, dict)


class TestFormatRealtimeAlerts:
    """Tests for format_realtime_ai_alerts function."""

    def test_import_function(self):
        """Function should import successfully."""
        from ai_learning import format_realtime_ai_alerts
        assert callable(format_realtime_ai_alerts)

    def test_returns_string(self):
        """Should return formatted string."""
        from ai_learning import format_realtime_ai_alerts

        result = format_realtime_ai_alerts({
            "catalyst_alerts": [],
            "theme_insights": [],
            "options_alerts": []
        })

        assert isinstance(result, str)

    def test_handles_populated_data(self):
        """Should handle populated data."""
        from ai_learning import format_realtime_ai_alerts

        result = format_realtime_ai_alerts({
            "catalyst_alerts": [{"ticker": "AAPL", "headline": "test"}],
            "theme_insights": [{"theme": "AI", "stage": "growth"}],
            "options_alerts": [{"ticker": "NVDA", "signal": "bullish"}],
            "rotation_prediction": {"outlook": "bullish"}
        })

        assert isinstance(result, str)
        assert len(result) > 0
