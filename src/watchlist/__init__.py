"""
Watchlist Module

Enhanced watchlist system with automatic updates from scans and AI analysis.
"""

from .watchlist_manager import (
    WatchlistManager,
    WatchlistItem,
    WatchlistPriority,
    SignalQuality,
    get_watchlist_manager
)

__all__ = [
    'WatchlistManager',
    'WatchlistItem',
    'WatchlistPriority',
    'SignalQuality',
    'get_watchlist_manager'
]
