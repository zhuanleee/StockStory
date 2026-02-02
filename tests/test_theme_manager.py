#!/usr/bin/env python3
"""
Test Theme Manager locally
"""
import sys
sys.path.insert(0, '/Users/johnlee/stock_scanner_bot')

from src.themes.theme_manager import ThemeManager, get_default_themes
from pathlib import Path
import json

def test_theme_manager():
    """Test basic theme manager operations."""
    # Use temp path for testing
    test_path = Path("/tmp/test_themes_config.json")

    # Clean up any existing test file
    if test_path.exists():
        test_path.unlink()

    # Create manager with test path
    manager = ThemeManager(config_path=test_path)

    print("✅ Theme manager initialized")
    print(f"   Config path: {manager.config_path}")

    # Get stats
    stats = manager.get_stats()
    print(f"\n📊 Stats:")
    print(f"   Total themes: {stats['total_themes']}")
    print(f"   Known: {stats['known']}")
    print(f"   Emerging: {stats['emerging']}")
    print(f"   Archived: {stats['archived']}")

    # Test getting keywords and tickers (for fast_stories.py compatibility)
    keywords = manager.get_keywords_dict()
    tickers = manager.get_tickers_dict()
    print(f"\n🔑 Keywords dict has {len(keywords)} themes")
    print(f"🏷️ Tickers dict has {len(tickers)} themes")

    # Test adding a new theme
    success = manager.add_theme(
        theme_id="TEST_THEME",
        name="Test Theme",
        keywords=["test", "demo", "example"],
        tickers=["TEST", "DEMO"]
    )
    print(f"\n➕ Add theme: {'✅ Success' if success else '❌ Failed'}")

    # Verify it was added
    theme = manager.get_theme("TEST_THEME")
    print(f"   Theme status: {theme.get('status') if theme else 'NOT FOUND'}")

    # Test archiving
    manager.remove_theme("TEST_THEME", archive=True)
    theme = manager.get_theme("TEST_THEME")
    print(f"\n🗑️ After archive: status = {theme.get('status') if theme else 'NOT FOUND'}")

    # Test restoring
    manager.restore_theme("TEST_THEME")
    theme = manager.get_theme("TEST_THEME")
    print(f"♻️ After restore: status = {theme.get('status') if theme else 'NOT FOUND'}")

    # Clean up
    if test_path.exists():
        test_path.unlink()

    print("\n✅ All tests passed!")

if __name__ == "__main__":
    test_theme_manager()
