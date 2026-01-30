#!/usr/bin/env python3
"""
Modal.com Scanner - AI Brain with Parallel Processing

This runs your full Comprehensive Agentic Brain on Modal's serverless platform.
Scans 500 stocks in ~5 minutes (10 concurrent GPUs) instead of 8+ hours sequential.
With GPU: ~6 seconds per stock = 500 stocks in ~5 minutes (50x batches of 10)
"""

import modal
from datetime import datetime
from pathlib import Path
import json

# Create Modal app
app = modal.App("stock-scanner-ai-brain")

# Create persistent volume for storing scan results
volume = modal.Volume.from_name("scan-results", create_if_missing=True)

# Mount path for volume
VOLUME_PATH = "/data"

# Define compute requirements per stock
# Each stock gets its own container with these resources
compute_config = {
    "cpu": 2.0,          # 2 CPUs per stock
    "memory": 4096,      # 4GB RAM per stock
    "timeout": 300,      # 5 minute timeout per stock
    "gpu": "T4",         # GPU for 10x speed boost (~$0.60/hour)
}

# Create custom image with all dependencies
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install_from_requirements("requirements.txt")
    .add_local_dir("src", remote_path="/root/src")
    .add_local_dir("config", remote_path="/root/config")
)


@app.function(
    image=image,
    **compute_config,
    secrets=[
        # Add your API keys as Modal secrets
        # Run: modal secret create stock-api-keys \
        #   POLYGON_API_KEY=xxx \
        #   XAI_API_KEY=xxx \
        #   DEEPSEEK_API_KEY=xxx ...
        modal.Secret.from_name("stock-api-keys")
    ],
)
def scan_stock_with_ai_brain(ticker: str) -> dict:
    """
    Scan one stock with full AI brain analysis.

    This runs the complete Comprehensive Agentic Brain:
    - 5 Directors (Trading, Theme, Learning, Realtime, Validation)
    - 35 Intelligence Components
    - External API calls (Polygon, Reddit, StockTwits, etc.)

    Args:
        ticker: Stock ticker symbol (e.g., "NVDA")

    Returns:
        Dict with stock data and AI analysis
    """
    import sys
    sys.path.insert(0, '/root')

    try:
        # Import your scanner
        from src.core.async_scanner import AsyncScanner
        import asyncio
        import pandas as pd

        print(f"🔍 Analyzing {ticker} with AI brain...")

        # Create scanner
        scanner = AsyncScanner(max_concurrent=1)

        # Run scan (this includes AI brain analysis)
        async def scan():
            try:
                # Scan the ticker
                result = await scanner.scan_ticker(ticker, price_data=None)
                await scanner.close()
                return result
            except Exception as e:
                print(f"❌ Error scanning {ticker}: {e}")
                await scanner.close()
                return None

        # Run async scan
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(scan())
        loop.close()

        if result:
            print(f"✅ {ticker} analyzed - Score: {result.get('story_score', 0)}")
            return result
        else:
            print(f"⚠️  {ticker} - No results")
            return {'ticker': ticker, 'error': 'Scan failed'}

    except Exception as e:
        print(f"❌ Error with {ticker}: {e}")
        import traceback
        traceback.print_exc()
        return {'ticker': ticker, 'error': str(e)}


@app.function(
    image=image,
    timeout=3600,  # 1 hour max for full scan
    schedule=modal.Cron("0 14 * * *"),  # Run daily at 6 AM PST (14:00 UTC)
    volumes={VOLUME_PATH: volume},
)
def daily_scan():
    """
    Daily scan of all S&P 500 + NASDAQ stocks with AI brain.

    Runs automatically every day at 6 AM PST.
    Scans in batches of 10 (GPU concurrency limit) - takes ~5 minutes for 500 stocks.
    Each stock: ~6 seconds with GPU, 10 concurrent = 50 batches for 500 stocks.
    """
    import pandas as pd
    import sys
    sys.path.insert(0, '/root')

    print("=" * 70)
    print("🚀 STARTING DAILY AI BRAIN SCAN")
    print("=" * 70)

    # Get stock universe
    try:
        from src.data.universe_manager import get_universe_manager
        um = get_universe_manager()
        tickers = um.get_scan_universe(use_polygon_full=False, min_market_cap=300_000_000)
        print(f"📊 Universe: {len(tickers)} stocks (S&P500 + NASDAQ 300M+)")
    except Exception as e:
        print(f"⚠️  Using fallback ticker list: {e}")
        # Fallback to quick scan list
        tickers = [
            'NVDA', 'AMD', 'AVGO', 'TSM', 'MSFT', 'GOOGL', 'META', 'AAPL',
            'TSLA', 'VST', 'CEG', 'PLTR', 'CRWD', 'NET', 'LLY', 'NVO',
            'LMT', 'JPM', 'XOM', 'SPY',
        ]
        print(f"📊 Using {len(tickers)} fallback stocks")

    start_time = datetime.now()
    print(f"⏰ Start time: {start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print()

    # Run stocks in parallel (batched by GPU concurrency limit)
    print(f"🔄 Scanning {len(tickers)} stocks in batches of 10 (GPU limit)...")
    print("   (Each stock gets: 2 CPU + 4GB RAM + T4 GPU)")
    print(f"   Expected time: ~{(len(tickers) / 10 * 6):.0f} seconds")
    print()

    # Map function runs in parallel, respecting GPU concurrency limit
    # Modal automatically batches: 10 concurrent GPU containers at a time
    results = list(scan_stock_with_ai_brain.map(tickers))

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    print()
    print("=" * 70)
    print(f"✅ SCAN COMPLETE in {duration:.1f} seconds ({duration/60:.1f} minutes)")
    print("=" * 70)

    # Filter successful results
    successful = [r for r in results if r and 'error' not in r]
    failed = [r for r in results if r and 'error' in r]

    print(f"✅ Successful: {len(successful)}/{len(tickers)} stocks")
    if failed:
        print(f"❌ Failed: {len(failed)} stocks")
        for f in failed[:5]:  # Show first 5 failures
            print(f"   - {f.get('ticker', 'Unknown')}: {f.get('error', 'Unknown error')}")

    if not successful:
        print("❌ No successful scans - check logs above")
        return

    # Create DataFrame
    df = pd.DataFrame(successful)

    # Sort by story score
    if 'story_score' in df.columns:
        df = df.sort_values('story_score', ascending=False)

    # Save results to CSV and JSON
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    csv_filename = f'scan_{timestamp}.csv'
    json_filename = f'scan_{timestamp}.json'

    print(f"\n💾 Saving results to {csv_filename}...")
    df.to_csv(csv_filename, index=False)

    # Save to JSON in Modal Volume for API access
    scan_data = {
        "status": "success",
        "timestamp": datetime.now().isoformat(),
        "total": len(tickers),
        "successful": len(successful),
        "failed": len(failed),
        "duration_seconds": duration,
        "results": successful
    }

    json_path = Path(VOLUME_PATH) / json_filename
    with open(json_path, 'w') as f:
        json.dump(scan_data, f, indent=2)

    volume.commit()  # Persist to volume
    print(f"💾 Saved to Modal Volume: {json_filename}")

    # Print top 10
    print(f"\n📈 Top 10 Stocks by Story Score:")
    print("-" * 70)
    for i, row in df.head(10).iterrows():
        ticker = row.get('ticker', 'Unknown')
        score = row.get('story_score', 0)
        strength = row.get('story_strength', 'unknown')
        theme = row.get('hottest_theme', 'No theme')
        print(f"{i+1:2d}. {ticker:6s} - Score: {score:5.1f} - {strength:12s} - {theme}")

    print()
    print("=" * 70)
    print("🎉 Daily scan complete! Results saved to CSV.")
    print(f"📊 Total stocks analyzed: {len(successful)}")
    print(f"⏱️  Total time: {duration:.1f} seconds")
    print(f"⚡ Average time per stock: {duration/len(tickers):.2f} seconds")
    print("=" * 70)

    # Send Telegram notification with top picks
    try:
        import os
        telegram_enabled = os.environ.get('TELEGRAM_BOT_TOKEN') and os.environ.get('TELEGRAM_CHAT_ID')

        if telegram_enabled:
            top_picks = df.head(10)
            message = f"🤖 *Daily Scan Complete!*\n\n"
            message += f"📊 Scanned: {len(successful)}/{len(tickers)} stocks\n"
            message += f"⏱️  Time: {duration/60:.1f} minutes\n\n"
            message += f"📈 *Top 10 Picks:*\n"

            for i, row in top_picks.iterrows():
                ticker = row.get('ticker', 'Unknown')
                score = row.get('story_score', 0)
                strength = row.get('story_strength', 'unknown')
                message += f"{i+1}. `{ticker}` - {score:.1f} ({strength})\n"

            message += f"\n🔗 View: https://zhuanleee.github.io/stock_scanner_bot"

            # Send notification
            from modal_api import send_telegram_notification
            send_telegram_notification.remote(message)
            print("📱 Telegram notification sent")
        else:
            print("⚠️  Telegram not configured - skipping notification")
    except Exception as e:
        print(f"⚠️  Telegram notification failed: {e}")

    return {
        'success': True,
        'total': len(tickers),
        'successful': len(successful),
        'failed': len(failed),
        'duration_seconds': duration,
        'csv_file': csv_filename,
    }


@app.function(image=image)
def test_single_stock():
    """Test scanning a single stock (NVDA) to verify setup."""
    print("🧪 Testing AI brain with NVDA...")
    result = scan_stock_with_ai_brain.remote("NVDA")
    print(f"\n✅ Test complete!")
    print(f"Result: {result}")
    return result


@app.local_entrypoint()
def main(
    ticker: str = None,
    test: bool = False,
    daily: bool = False,
):
    """
    Run scanner from command line.

    Examples:
        modal run modal_scanner.py --test          # Test with NVDA
        modal run modal_scanner.py --ticker AAPL   # Scan single stock
        modal run modal_scanner.py --daily         # Run full daily scan
    """
    if test:
        print("🧪 Running test scan...")
        test_single_stock.remote()
    elif ticker:
        print(f"🔍 Scanning {ticker}...")
        result = scan_stock_with_ai_brain.remote(ticker)
        print(f"\n✅ Result: {result}")
    elif daily:
        print("🚀 Running daily scan...")
        result = daily_scan.remote()
        print(f"\n✅ Scan complete: {result}")
    else:
        print("Usage:")
        print("  modal run modal_scanner.py --test")
        print("  modal run modal_scanner.py --ticker NVDA")
        print("  modal run modal_scanner.py --daily")
