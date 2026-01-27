"""
Stock Scanner Bot - Source Package

A story-first stock scanning system that prioritizes narrative over technicals.
"""

__version__ = "2.0.0"
__author__ = "Stock Scanner Bot"

# Lazy imports to avoid circular dependencies
__all__ = [
    'AsyncScanner',
    'run_async_scan_sync',
    'StoryScorer',
    'calculate_story_score',
    'ThemeRegistry',
    'get_registry',
    'UniverseManager',
    'CacheManager',
    'generate_dashboard',
]

def __getattr__(name):
    """Lazy loading of submodules to avoid import issues."""
    if name == 'AsyncScanner':
        from src.core.async_scanner import AsyncScanner
        return AsyncScanner
    elif name == 'run_async_scan_sync':
        from src.core.async_scanner import run_async_scan_sync
        return run_async_scan_sync
    elif name == 'StoryScorer':
        from src.core.story_scoring import StoryScorer
        return StoryScorer
    elif name == 'calculate_story_score':
        from src.core.story_scoring import calculate_story_score
        return calculate_story_score
    elif name == 'ThemeRegistry':
        from src.themes.theme_registry import ThemeRegistry
        return ThemeRegistry
    elif name == 'get_registry':
        from src.themes.theme_registry import get_registry
        return get_registry
    elif name == 'UniverseManager':
        from src.data.universe_manager import UniverseManager
        return UniverseManager
    elif name == 'CacheManager':
        from src.data.cache_manager import CacheManager
        return CacheManager
    elif name == 'generate_dashboard':
        from src.dashboard.dashboard import generate_dashboard
        return generate_dashboard
    raise AttributeError(f"module 'src' has no attribute '{name}'")
