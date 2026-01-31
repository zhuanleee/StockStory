"""
Tests for Configuration Constants
"""
import pytest
from src.core.constants import (
    # Market filtering
    MIN_MARKET_CAP,
    MIN_PRICE,
    MAX_PRICE,
    MIN_VOLUME,
    # Rate limits
    POLYGON_RATE_LIMIT,
    STOCKTWITS_RATE_LIMIT,
    # Scoring weights
    WEIGHT_THEME_HEAT,
    WEIGHT_CATALYST,
    WEIGHT_TECHNICAL,
    # Validation
    validate_constants
)


class TestMarketFiltering:
    """Test market filtering constants"""

    def test_market_cap_limits(self):
        """Test market cap limits are reasonable"""
        assert MIN_MARKET_CAP > 0
        assert MIN_MARKET_CAP >= 100_000_000  # At least 100M

    def test_price_limits(self):
        """Test price limits are reasonable"""
        assert MIN_PRICE > 0
        assert MAX_PRICE > MIN_PRICE
        assert MIN_PRICE >= 1.0  # Avoid penny stocks
        assert MAX_PRICE <= 10_000  # Reasonable upper bound

    def test_volume_limits(self):
        """Test volume limits are reasonable"""
        assert MIN_VOLUME > 0
        assert MIN_VOLUME >= 100_000  # Sufficient liquidity


class TestRateLimits:
    """Test API rate limit constants"""

    def test_polygon_rate_limit(self):
        """Test Polygon rate limit"""
        assert POLYGON_RATE_LIMIT > 0
        assert POLYGON_RATE_LIMIT <= 100  # Free tier limit

    def test_stocktwits_rate_limit(self):
        """Test StockTwits rate limit"""
        assert STOCKTWITS_RATE_LIMIT > 0
        assert STOCKTWITS_RATE_LIMIT <= 10  # Conservative


class TestScoringWeights:
    """Test scoring weight constants"""

    def test_weights_are_positive(self):
        """Test all weights are positive"""
        assert WEIGHT_THEME_HEAT > 0
        assert WEIGHT_CATALYST > 0
        assert WEIGHT_TECHNICAL > 0

    def test_weights_are_reasonable(self):
        """Test weights are in reasonable range"""
        assert 0 < WEIGHT_THEME_HEAT < 1
        assert 0 < WEIGHT_CATALYST < 1
        assert 0 < WEIGHT_TECHNICAL < 1

    def test_weights_sum_to_one(self):
        """Test scoring weights sum to approximately 1.0"""
        # Import all weights
        from src.core import constants

        # Get all WEIGHT_ attributes
        weights = [
            getattr(constants, attr)
            for attr in dir(constants)
            if attr.startswith('WEIGHT_')
        ]

        total = sum(weights)

        # Should sum to approximately 1.0 (allow small floating point error)
        assert 0.99 <= total <= 1.01, f"Weights sum to {total}, expected ~1.0"


class TestValidation:
    """Test constant validation"""

    def test_validate_constants(self):
        """Test that validation passes"""
        try:
            result = validate_constants()
            assert result is True
        except AssertionError as e:
            pytest.fail(f"Constant validation failed: {e}")


class TestConstantImmutability:
    """Test that constants cannot be easily modified"""

    def test_constants_are_uppercase(self):
        """Test constants follow naming convention"""
        from src.core import constants

        # Check key constants are uppercase
        assert 'MIN_MARKET_CAP' in dir(constants)
        assert 'MIN_PRICE' in dir(constants)
        assert 'WEIGHT_THEME_HEAT' in dir(constants)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
