"""
Backward compatibility wrapper for bot_listener.

This file redirects imports to the new location: src/bot/bot_listener.py
"""

from src.bot.bot_listener import *

if __name__ == '__main__':
    handle_commands()
