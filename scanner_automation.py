"""
Backward compatibility wrapper for scanner_automation.

This file redirects imports to the new location: src/core/scanner_automation.py
"""

# Re-export everything from new location
from src.core.scanner_automation import *

# Allow running as main
if __name__ == '__main__':
    main()
