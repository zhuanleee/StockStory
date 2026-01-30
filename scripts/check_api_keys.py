#!/usr/bin/env python3
"""
Check which API keys are configured and which are missing.
Run this to verify your setup.
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import Config

def check_api_keys():
    """Check which API keys are configured."""
    config = Config()

    print("="*70)
    print("API KEYS STATUS CHECK")
    print("="*70)
    print()

    # Financial Data APIs
    print("📊 FINANCIAL DATA APIS")
    print("-" * 70)
    print(f"  {'✅' if config.POLYGON_API_KEY else '❌'} POLYGON_API_KEY")
    print(f"  {'✅' if config.FINNHUB_API_KEY else '❌'} FINNHUB_API_KEY")
    print(f"  {'✅' if config.ALPHA_VANTAGE_API_KEY else '❌'} ALPHA_VANTAGE_API_KEY")
    print(f"  {'⚠️ ' if not config.POLYGON_API_KEY and not config.FINNHUB_API_KEY else '  '} (Need at least one for stock data)")
    print()

    # AI Services
    print("🤖 AI SERVICES")
    print("-" * 70)
    print(f"  {'✅' if config.DEEPSEEK_API_KEY else '❌'} DEEPSEEK_API_KEY (REQUIRED for AI)")
    print(f"  {'✅' if config.XAI_API_KEY else '⚪'} XAI_API_KEY (optional)")
    print(f"  {'✅' if config.OPENAI_API_KEY else '⚪'} OPENAI_API_KEY (optional)")
    print()

    # Intelligence Sources
    print("🔍 INTELLIGENCE SOURCES")
    print("-" * 70)
    print(f"  {'✅' if config.PATENTSVIEW_API_KEY else '⚪'} PATENTSVIEW_API_KEY (optional)")
    print()

    # Communication
    print("💬 COMMUNICATION")
    print("-" * 70)
    print(f"  {'✅' if config.TELEGRAM_BOT_TOKEN else '❌'} TELEGRAM_BOT_TOKEN (REQUIRED for notifications)")
    print(f"  {'✅' if config.TELEGRAM_CHAT_ID else '❌'} TELEGRAM_CHAT_ID (REQUIRED for notifications)")
    print()

    # Summary
    print("="*70)
    print("SUMMARY")
    print("="*70)

    required_keys = {
        'DEEPSEEK_API_KEY': bool(config.DEEPSEEK_API_KEY),
        'TELEGRAM_BOT_TOKEN': bool(config.TELEGRAM_BOT_TOKEN),
        'TELEGRAM_CHAT_ID': bool(config.TELEGRAM_CHAT_ID),
        'Stock Data API (any)': bool(config.POLYGON_API_KEY or config.FINNHUB_API_KEY),
    }

    missing_required = [k for k, v in required_keys.items() if not v]

    if not missing_required:
        print("✅ All required keys are configured!")
        print()
        print("Ready to run:")
        print("  - Daily scanner with AI analysis")
        print("  - Telegram notifications")
        print("  - Dashboard with real-time data")
        return True
    else:
        print("❌ Missing required keys:")
        for key in missing_required:
            print(f"  • {key}")
        print()
        print("Setup instructions:")
        print("  1. See API_KEYS_SECURE_STORAGE.md for where to get keys")
        print("  2. Add keys to .env file")
        print("  3. Add keys to Modal secret at https://modal.com/zhuanleee/secrets")
        print("  4. Run this script again to verify")
        return False

if __name__ == '__main__':
    success = check_api_keys()
    sys.exit(0 if success else 1)
