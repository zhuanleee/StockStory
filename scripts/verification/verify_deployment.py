#!/usr/bin/env python3
"""
Deployment Verification Script
===============================
Verify all components are ready for Railway deployment.
"""

import os
import sys
from pathlib import Path

# Load environment
from dotenv import load_dotenv
load_dotenv()


def check_env_vars():
    """Check critical environment variables."""
    print("🔍 Checking Environment Variables...")
    print("=" * 60)

    required = {
        'POLYGON_API_KEY': 'Market data (required)',
        'TELEGRAM_BOT_TOKEN': 'Telegram bot (required)',
        'TELEGRAM_CHAT_ID': 'Telegram notifications (required)',
    }

    optional = {
        'DEEPSEEK_API_KEY': 'AI analysis (optional)',
        'XAI_API_KEY': 'X Intelligence (optional)',
        'ALPHA_VANTAGE_API_KEY': 'Earnings transcripts (optional)',
        'FINNHUB_API_KEY': 'Alternative data (optional)',
        'PATENTSVIEW_API_KEY': 'Patent tracking (optional)',
    }

    all_good = True

    # Check required
    print("\n✅ Required:")
    for var, desc in required.items():
        value = os.environ.get(var, '')
        if value:
            masked = f"{value[:8]}..." if len(value) > 8 else "***"
            print(f"  ✓ {var:25} = {masked:15} ({desc})")
        else:
            print(f"  ✗ {var:25} = NOT SET ({desc})")
            all_good = False

    # Check optional
    print("\n⚙️  Optional:")
    for var, desc in optional.items():
        value = os.environ.get(var, '')
        if value:
            masked = f"{value[:8]}..." if len(value) > 8 else "***"
            print(f"  ✓ {var:25} = {masked:15} ({desc})")
        else:
            print(f"  - {var:25} = NOT SET ({desc})")

    return all_good


def check_files():
    """Check critical files exist."""
    print("\n\n🔍 Checking Critical Files...")
    print("=" * 60)

    files_to_check = [
        ('Procfile', 'Railway deployment'),
        ('requirements.txt', 'Python dependencies'),
        ('app.py', 'Flask app entry'),
        ('main.py', 'CLI entry'),
        ('src/api/app.py', 'API routes'),
        ('src/bot/bot_listener.py', 'Telegram bot'),
        ('src/core/async_scanner.py', 'Scanner core'),
        ('src/data/transcript_fetcher.py', 'Earnings transcripts'),
        ('src/intelligence/executive_commentary.py', 'Executive commentary'),
        ('src/scoring/earnings_scorer.py', 'Earnings scorer'),
        ('src/intelligence/x_intelligence.py', 'X Intelligence'),
        ('src/intelligence/google_trends.py', 'Google Trends'),
        ('src/intelligence/institutional_flow.py', 'Institutional flow'),
        ('src/intelligence/rotation_predictor.py', 'Sector rotation'),
        ('src/intelligence/relationship_graph.py', 'Supply chain'),
        ('src/config.py', 'Configuration'),
    ]

    all_exist = True
    for file_path, description in files_to_check:
        exists = Path(file_path).exists()
        status = "✓" if exists else "✗"
        print(f"  {status} {file_path:50} ({description})")
        if not exists:
            all_exist = False

    return all_exist


def check_imports():
    """Check critical imports work."""
    print("\n\n🔍 Checking Critical Imports...")
    print("=" * 60)

    imports_to_check = [
        ('src.api.app', 'Flask API'),
        ('src.core.async_scanner', 'Async scanner'),
        ('src.bot.bot_listener', 'Telegram bot'),
        ('src.data.transcript_fetcher', 'Transcript fetcher'),
        ('src.intelligence.executive_commentary', 'Executive commentary'),
        ('src.intelligence.x_intelligence', 'X Intelligence'),
        ('src.intelligence.google_trends', 'Google Trends'),
        ('src.config', 'Configuration'),
    ]

    all_imported = True
    for module_path, description in imports_to_check:
        try:
            __import__(module_path)
            print(f"  ✓ {module_path:50} ({description})")
        except ImportError as e:
            print(f"  ✗ {module_path:50} ({description})")
            print(f"      Error: {e}")
            all_imported = False

    return all_imported


def check_data_sources():
    """Check data source availability."""
    print("\n\n🔍 Checking Data Sources...")
    print("=" * 60)

    from src.config import config

    sources = {
        'Polygon': config.is_api_available('polygon'),
        'Alpha Vantage': config.is_api_available('alpha_vantage'),
        'Finnhub': config.is_api_available('finnhub'),
        'xAI': config.is_api_available('xai'),
        'DeepSeek': config.is_api_available('deepseek'),
        'Patents': config.is_api_available('patents'),
        'Telegram': config.is_api_available('telegram'),
    }

    print("\n📊 Available Data Sources:")
    for source, available in sources.items():
        status = "✓" if available else "✗"
        print(f"  {status} {source}")

    return True


def check_learning_system():
    """Check learning system initialization."""
    print("\n\n🔍 Checking Learning System...")
    print("=" * 60)

    try:
        from src.learning import get_learning_brain
        brain = get_learning_brain()

        print(f"  ✓ Learning brain initialized")
        print(f"  ✓ Current weights:")
        weights = brain.current_weights
        print(f"      Theme:         {weights.theme:.1%}")
        print(f"      Technical:     {weights.technical:.1%}")
        print(f"      AI:            {weights.ai:.1%}")
        print(f"      Sentiment:     {weights.sentiment:.1%}")
        print(f"      Earnings:      {weights.earnings:.1%}")
        print(f"      Institutional: {weights.institutional:.1%}")
        print(f"  ✓ Confidence: {weights.confidence:.1%}")
        print(f"  ✓ Sample size: {weights.sample_size} trades")

        return True
    except Exception as e:
        print(f"  ✗ Learning system error: {e}")
        return False


def main():
    """Run all verification checks."""
    print("\n" + "=" * 60)
    print("  STOCK SCANNER BOT - DEPLOYMENT VERIFICATION")
    print("=" * 60)

    results = {}

    # Run checks
    results['env_vars'] = check_env_vars()
    results['files'] = check_files()
    results['imports'] = check_imports()
    results['data_sources'] = check_data_sources()
    results['learning'] = check_learning_system()

    # Summary
    print("\n\n" + "=" * 60)
    print("  VERIFICATION SUMMARY")
    print("=" * 60)

    all_passed = all(results.values())

    for check, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status} - {check.replace('_', ' ').title()}")

    print("\n" + "=" * 60)

    if all_passed:
        print("  ✅ ALL CHECKS PASSED - READY FOR DEPLOYMENT")
        print("=" * 60)
        print("\n🚀 Deployment Instructions:")
        print("  1. Push to GitHub: git push origin main")
        print("  2. Railway will auto-deploy from GitHub")
        print("  3. Set environment variables in Railway dashboard")
        print("  4. Check deployment logs: railway logs")
        print("  5. Test webhook: https://your-app.railway.app/health")
        return 0
    else:
        print("  ❌ SOME CHECKS FAILED - FIX ISSUES BEFORE DEPLOYING")
        print("=" * 60)
        return 1


if __name__ == '__main__':
    sys.exit(main())
