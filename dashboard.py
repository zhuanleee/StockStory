"""
Backward compatibility wrapper for dashboard.

This file redirects imports to the new location: src/dashboard/dashboard.py
"""

# Re-export everything from new location
from src.dashboard.dashboard import *

# Allow running as main
if __name__ == '__main__':
    generate_dashboard()
