"""
Market Analysis

News analysis, market health, sector rotation, and backtesting.
"""

# Lazy imports to avoid circular dependencies
__all__ = [
    'get_market_health',
    'get_market_health_lite',
    'calculate_fear_greed_index',
    'calculate_market_breadth',
]


def __getattr__(name):
    """Lazy load modules to avoid circular imports."""
    if name in ('get_market_health', 'get_market_health_lite',
                'calculate_fear_greed_index', 'calculate_market_breadth'):
        from src.analysis import market_health
        return getattr(market_health, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
