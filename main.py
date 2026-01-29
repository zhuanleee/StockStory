#!/usr/bin/env python3
"""
Stock Scanner Bot - Main Entry Point

Usage:
    python main.py scan          # Run full stock scan
    python main.py scan --test   # Run test scan (10 tickers)
    python main.py dashboard     # Generate dashboard
    python main.py bot           # Run Telegram bot listener
    python main.py api           # Start Flask API server
    python main.py test          # Run tests

Environment Variables:
    USE_AI_BRAIN_RANKING=true    # Enable AI brain ranking (optional, slower but more accurate)
    XAI_API_KEY=<key>            # Enable X Intelligence via xAI Grok (optional, real-time sentiment)
"""

import sys
import os
import argparse
import asyncio

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()


def run_scan(test_mode=False, use_learning=True):
    """
    Run the async stock scanner.

    Args:
        test_mode: If True, scan only 10 test tickers
        use_learning: If True, integrate with learning system (default)
    """
    from src.core.async_scanner import AsyncScanner
    import logging

    logger = logging.getLogger(__name__)

    async def scan():
        scanner = AsyncScanner(max_concurrent=50)

        # Initialize learning system if enabled
        learning_brain = None
        if use_learning:
            try:
                from src.learning import get_learning_brain
                learning_brain = get_learning_brain()
                logger.info("✓ Learning system initialized")
            except Exception as e:
                logger.warning(f"Learning system not available: {e}")
                learning_brain = None

        try:
            if test_mode:
                tickers = ['NVDA', 'AMD', 'AAPL', 'MSFT', 'META', 'GOOGL', 'AMZN', 'TSLA', 'NFLX', 'CRM']
                print(f"Running TEST scan on {len(tickers)} tickers...")
            else:
                from src.data.universe_manager import get_universe_manager
                um = get_universe_manager()
                tickers = um.get_scan_universe()
                print(f"Running FULL scan on {len(tickers)} tickers...")

            results = await scanner.run_scan_async(tickers, learning_brain=learning_brain)

            if isinstance(results, tuple):
                df = results[0]
            else:
                df = results

            print(f"\nScan complete: {len(df)} stocks analyzed")

            # Display learned weights if learning is active
            if learning_brain:
                weights = learning_brain.current_weights
                print(f"\n📊 Learned Component Weights:")
                print(f"  Theme:     {weights.theme:.1%}")
                print(f"  Technical: {weights.technical:.1%}")
                print(f"  AI:        {weights.ai:.1%}")
                print(f"  Sentiment: {weights.sentiment:.1%}")
                print(f"  Earnings:  {weights.earnings:.1%}")
                print(f"  (Confidence: {weights.confidence:.1%}, Sample: {weights.sample_size} trades)")

            print("\nTop 10 by Story Score:")
            for i, row in df.head(10).iterrows():
                ticker = row.get('ticker', 'N/A')
                score = row.get('story_score', 0)
                theme = row.get('hottest_theme', '-') or '-'
                strength = row.get('story_strength', 'none')
                print(f"  {i+1:2}. {ticker:6} | Score: {score:5.1f} | {strength:10} | {theme}")

            return df
        finally:
            await scanner.close()

    return asyncio.run(scan())


def generate_dashboard():
    """Generate the static HTML dashboard."""
    from src.dashboard.dashboard import generate_dashboard as gen_dash
    print("Generating dashboard...")
    result = gen_dash()
    if result:
        print(f"Dashboard generated: docs/index.html")
    else:
        print("Dashboard generation failed")
    return result


def run_bot():
    """Run the Telegram bot listener."""
    from src.bot.bot_listener import handle_commands
    print("Running Telegram bot listener...")
    handle_commands()


def run_api():
    """Start the Flask API server."""
    from src.api.app import app
    print("Starting Flask API server on port 5000...")
    app.run(debug=True, port=5000, host='0.0.0.0')


def run_tests():
    """Run pytest test suite."""
    import subprocess
    print("Running tests...")
    result = subprocess.run(['python', '-m', 'pytest', '-v', 'tests/'], cwd=os.path.dirname(__file__))
    return result.returncode


def refresh_universe():
    """Refresh the market cap cache for scan universe."""
    from src.data.universe_manager import get_universe_manager
    from utils import format_kl_time

    print(f"Refreshing market cap cache at {format_kl_time()} MYT...")
    um = get_universe_manager()
    stats = um.refresh_market_cap_cache(min_market_cap=300_000_000)

    print(f"\nRefresh complete:")
    print(f"  Total tickers checked: {stats['total_tickers_checked']}")
    print(f"  Stocks >= $300M: {stats['tickers_above_threshold']}")
    print(f"  Cache file: {stats['cache_file']}")

    return stats


def main():
    parser = argparse.ArgumentParser(
        description='Stock Scanner Bot - Story-First Stock Analysis',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py scan              Run full scan (1400+ liquid stocks)
  python main.py scan --test       Run test scan (10 tickers)
  python main.py dashboard         Generate HTML dashboard
  python main.py bot               Listen for Telegram commands
  python main.py api               Start REST API server
  python main.py refresh-universe  Refresh market cap cache
  python main.py test              Run test suite
        """
    )

    parser.add_argument('command', choices=['scan', 'dashboard', 'bot', 'api', 'test', 'refresh-universe'],
                        help='Command to run')
    parser.add_argument('--test', action='store_true',
                        help='Run in test mode (for scan command)')

    args = parser.parse_args()

    if args.command == 'scan':
        run_scan(test_mode=args.test)
    elif args.command == 'dashboard':
        generate_dashboard()
    elif args.command == 'bot':
        run_bot()
    elif args.command == 'api':
        run_api()
    elif args.command == 'refresh-universe':
        refresh_universe()
    elif args.command == 'test':
        sys.exit(run_tests())


if __name__ == '__main__':
    main()
