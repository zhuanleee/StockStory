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
    schedule=modal.Cron("0 14 * * 1-5"),  # Run Mon-Fri at 6 AM PST (14:00 UTC)
    volumes={VOLUME_PATH: volume},
)
def daily_scan():
    """
    Daily scan of all S&P 500 + NASDAQ stocks with AI brain.

    Runs automatically Mon-Fri at 6 AM PST when markets are open.
    Scans in batches of 10 (GPU concurrency limit) - takes ~5 minutes for 500 stocks.
    Each stock: ~6 seconds with GPU, 10 concurrent = 50 batches for 500 stocks.
    """
    import pandas as pd
    import sys
    sys.path.insert(0, '/root')

    print("=" * 70)
    print("🚀 STARTING DAILY AI BRAIN SCAN")
    print("=" * 70)

    # Check if market is open today (skip holidays)
    today = datetime.now()

    # US Market Holidays 2026 (NYSE/NASDAQ)
    market_holidays_2026 = [
        datetime(2026, 1, 1),   # New Year's Day
        datetime(2026, 1, 19),  # MLK Day
        datetime(2026, 2, 16),  # Presidents Day
        datetime(2026, 4, 3),   # Good Friday
        datetime(2026, 5, 25),  # Memorial Day
        datetime(2026, 7, 3),   # Independence Day (observed)
        datetime(2026, 9, 7),   # Labor Day
        datetime(2026, 11, 26), # Thanksgiving
        datetime(2026, 12, 25), # Christmas
    ]

    # Check if today is a holiday
    today_date = datetime(today.year, today.month, today.day)
    if today_date in market_holidays_2026:
        holiday_name = {
            (1, 1): "New Year's Day",
            (1, 19): "Martin Luther King Jr. Day",
            (2, 16): "Presidents Day",
            (4, 3): "Good Friday",
            (5, 25): "Memorial Day",
            (7, 3): "Independence Day",
            (9, 7): "Labor Day",
            (11, 26): "Thanksgiving",
            (12, 25): "Christmas"
        }.get((today.month, today.day), "Market Holiday")

        print(f"📅 Today is {holiday_name} - Market is CLOSED")
        print("⏭️  Skipping scan. Next scan: Next market open day")
        print("=" * 70)
        return {
            'success': False,
            'reason': 'market_holiday',
            'holiday': holiday_name,
            'date': today.strftime('%Y-%m-%d')
        }

    # Check if weekend (should not happen with Mon-Fri cron, but just in case)
    if today.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
        print(f"📅 Today is {today.strftime('%A')} - Market is CLOSED")
        print("⏭️  Skipping scan. Next scan: Monday")
        print("=" * 70)
        return {
            'success': False,
            'reason': 'weekend',
            'date': today.strftime('%Y-%m-%d')
        }

    print(f"📅 Market is OPEN - {today.strftime('%A, %B %d, %Y')}")
    print()

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
        import requests

        bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
        chat_id = os.environ.get('TELEGRAM_CHAT_ID')

        if bot_token and chat_id:
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

            # Send notification directly (no cross-app imports)
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "Markdown"
            }

            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                print("📱 Telegram notification sent")
            else:
                print(f"⚠️  Telegram failed: {response.status_code}")
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


@app.function(
    image=image,
    timeout=1800,  # 30 minutes max
    schedule=modal.Cron("30 14 * * 1-5"),  # Run Mon-Fri at 6:30 AM PST (30 min after daily scan)
    volumes={VOLUME_PATH: volume},
)
def automated_theme_discovery():
    """
    Automated Theme Discovery - Runs 4 advanced discovery methods:
    1. Supply Chain Analysis (finds suppliers of theme leaders, identifies lagging plays)
    2. Patent Clustering (groups companies by patent similarity)
    3. Contract Analysis (discovers themes from government contracts)
    4. News Co-occurrence (reveals market narrative from co-mentioned stocks)

    Runs automatically Mon-Fri at 6:30 AM PST, 30 minutes after daily scan completes.
    Results are saved to Modal volume and accessible via /theme-intel/alerts API.
    """
    import sys
    sys.path.insert(0, '/root')

    print("=" * 70)
    print("🔍 STARTING AUTOMATED THEME DISCOVERY")
    print("=" * 70)

    today = datetime.now()
    print(f"📅 {today.strftime('%A, %B %d, %Y %H:%M UTC')}")
    print()

    try:
        from src.intelligence.theme_discovery_engine import get_theme_discovery_engine

        engine = get_theme_discovery_engine()

        # 1. Discover emerging themes from high story-score stocks
        print("🔍 Method 1: Discovering emerging themes from story scores...")
        emerging_themes = engine.discover_emerging_themes(min_story_score=60)
        print(f"   ✅ Found {len(emerging_themes)} emerging themes")

        # 2. Analyze known supply chains for lagging opportunities
        print("\n🔗 Method 2: Analyzing supply chains for lagging plays...")
        supply_chain_themes = []

        # Known themes to analyze (from SUPPLY_CHAIN_MAP)
        known_themes = [
            'ai_infrastructure', 'ev_battery', 'defense_tech', 'energy_transition',
            'cybersecurity', 'biotech_innovation', 'fintech_payments', 'cloud_computing'
        ]

        for theme_id in known_themes:
            try:
                theme = engine.analyze_supply_chain(theme_id)
                if theme and theme.laggard_count > 0:
                    supply_chain_themes.append(theme)
                    print(f"   ✅ {theme_id}: {theme.laggard_count} lagging opportunities")
            except Exception as e:
                print(f"   ⚠️  {theme_id}: {e}")

        print(f"   ✅ Analyzed {len(known_themes)} supply chains, found {len(supply_chain_themes)} with opportunities")

        # 3. Validate themes with patent data
        print("\n📄 Method 3: Validating themes with patent clustering...")
        patent_validated = 0

        all_themes = emerging_themes + supply_chain_themes
        for theme in all_themes:
            try:
                # Get tickers from theme
                tickers = []
                if hasattr(theme, 'leaders'):
                    tickers.extend([n.ticker for n in theme.leaders if hasattr(n, 'ticker')])
                if hasattr(theme, 'suppliers'):
                    tickers.extend([n.ticker for n in theme.suppliers if hasattr(n, 'ticker')])

                if tickers:
                    # Validate with patents
                    patent_score = engine._validate_with_patents(tickers[:5], [theme.name])
                    if patent_score > 30:  # Threshold for patent relevance
                        patent_validated += 1
                        # Store patent score in theme metadata
                        if not hasattr(theme, 'metadata'):
                            theme.metadata = {}
                        theme.metadata['patent_validation_score'] = patent_score
            except Exception as e:
                print(f"   ⚠️  Patent validation error: {e}")

        print(f"   ✅ Patent-validated {patent_validated}/{len(all_themes)} themes")

        # 4. Validate themes with government contract data
        print("\n📋 Method 4: Validating themes with contract analysis...")
        contract_validated = 0

        for theme in all_themes:
            try:
                # Get tickers from theme
                tickers = []
                if hasattr(theme, 'leaders'):
                    tickers.extend([n.ticker for n in theme.leaders if hasattr(n, 'ticker')])
                if hasattr(theme, 'suppliers'):
                    tickers.extend([n.ticker for n in theme.suppliers if hasattr(n, 'ticker')])

                if tickers:
                    # Validate with contracts
                    contract_score = engine._validate_with_contracts(tickers[:5])
                    if contract_score > 20:  # Threshold for contract relevance
                        contract_validated += 1
                        # Store contract score in theme metadata
                        if not hasattr(theme, 'metadata'):
                            theme.metadata = {}
                        theme.metadata['contract_validation_score'] = contract_score
            except Exception as e:
                print(f"   ⚠️  Contract validation error: {e}")

        print(f"   ✅ Contract-validated {contract_validated}/{len(all_themes)} themes")

        # Save results to Modal volume
        print("\n💾 Saving theme discovery results...")

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        results_filename = f'theme_discovery_{timestamp}.json'

        # Convert themes to dict format for JSON serialization
        theme_data = []
        for theme in all_themes:
            try:
                theme_dict = {
                    'name': theme.name,
                    'discovery_method': theme.discovery_method,
                    'confidence_score': theme.confidence_score,
                    'laggard_count': theme.laggard_count,
                    'timestamp': theme.timestamp.isoformat() if hasattr(theme.timestamp, 'isoformat') else str(theme.timestamp),
                }

                # Add leaders
                if hasattr(theme, 'leaders') and theme.leaders:
                    theme_dict['leaders'] = [
                        {'ticker': n.ticker, 'opportunity_score': n.opportunity_score}
                        for n in theme.leaders[:5] if hasattr(n, 'ticker')
                    ]

                # Add laggards
                if hasattr(theme, 'laggards') and theme.laggards:
                    theme_dict['laggards'] = [
                        {'ticker': n.ticker, 'opportunity_score': n.opportunity_score}
                        for n in theme.laggards[:10] if hasattr(n, 'ticker')
                    ]

                # Add suppliers
                if hasattr(theme, 'suppliers') and theme.suppliers:
                    theme_dict['suppliers'] = [
                        {'ticker': n.ticker, 'opportunity_score': n.opportunity_score}
                        for n in theme.suppliers[:5] if hasattr(n, 'ticker')
                    ]

                # Add validation scores
                if hasattr(theme, 'metadata') and theme.metadata:
                    theme_dict['patent_validation'] = theme.metadata.get('patent_validation_score', 0)
                    theme_dict['contract_validation'] = theme.metadata.get('contract_validation_score', 0)

                theme_data.append(theme_dict)
            except Exception as e:
                print(f"   ⚠️  Error serializing theme {theme.name}: {e}")

        # Create summary data structure
        summary = {
            'status': 'success',
            'timestamp': datetime.now().isoformat(),
            'discovery_methods': {
                'emerging_themes': len(emerging_themes),
                'supply_chain_analysis': len(supply_chain_themes),
                'patent_validated': patent_validated,
                'contract_validated': contract_validated
            },
            'total_themes': len(all_themes),
            'themes': theme_data
        }

        # Save to volume
        json_path = Path(VOLUME_PATH) / results_filename
        with open(json_path, 'w') as f:
            json.dump(summary, f, indent=2)

        # Also save as 'latest' for easy API access
        latest_path = Path(VOLUME_PATH) / 'theme_discovery_latest.json'
        with open(latest_path, 'w') as f:
            json.dump(summary, f, indent=2)

        volume.commit()

        print(f"   ✅ Saved to Modal Volume: {results_filename}")
        print(f"   ✅ Saved as latest: theme_discovery_latest.json")

        # Print summary
        print()
        print("=" * 70)
        print("📊 THEME DISCOVERY SUMMARY")
        print("=" * 70)
        print(f"Total themes discovered: {len(all_themes)}")
        print(f"  • Emerging themes: {len(emerging_themes)}")
        print(f"  • Supply chain opportunities: {len(supply_chain_themes)}")
        print(f"  • Patent-validated: {patent_validated}")
        print(f"  • Contract-validated: {contract_validated}")

        if theme_data:
            print(f"\n🎯 Top 5 Opportunities:")
            print("-" * 70)
            # Sort by confidence score
            sorted_themes = sorted(theme_data, key=lambda x: x.get('confidence_score', 0), reverse=True)
            for i, theme in enumerate(sorted_themes[:5], 1):
                name = theme.get('name', 'Unknown')
                confidence = theme.get('confidence_score', 0)
                laggards = theme.get('laggard_count', 0)
                method = theme.get('discovery_method', 'unknown')
                print(f"{i}. {name} (confidence: {confidence:.1f}, {laggards} laggards, method: {method})")

        print()
        print("=" * 70)
        print("✅ Theme discovery complete!")
        print("=" * 70)

        # Send Telegram notification with top themes
        try:
            from src.notifications import get_notification_manager

            notif_mgr = get_notification_manager()

            # Prepare notification data
            top_themes = sorted(theme_data, key=lambda x: x.get('confidence_score', 0), reverse=True)[:5]

            notif_data = {
                'themes': [
                    {
                        'name': theme.get('name', 'Unknown'),
                        'confidence': theme.get('confidence_score', 0),
                        'laggards': theme.get('laggard_count', 0),
                        'method': theme.get('discovery_method', 'unknown')
                    }
                    for theme in top_themes
                ],
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M UTC')
            }

            result = notif_mgr.send_alert('theme_discovery', notif_data)
            if result.get('telegram'):
                print("📱 Telegram notification sent")
            else:
                print("⚠️  Telegram notification skipped (not configured)")
        except Exception as e:
            print(f"⚠️  Notification failed: {e}")

        return {
            'success': True,
            'total_themes': len(all_themes),
            'emerging_themes': len(emerging_themes),
            'supply_chain_themes': len(supply_chain_themes),
            'patent_validated': patent_validated,
            'contract_validated': contract_validated,
            'results_file': results_filename
        }

    except Exception as e:
        print(f"❌ Theme discovery failed: {e}")
        import traceback
        traceback.print_exc()

        return {
            'success': False,
            'error': str(e)
        }


@app.function(
    image=image,
    timeout=600,  # 10 minutes max
    schedule=modal.Cron("0 15 * * 1-5"),  # Run Mon-Fri at 7:00 AM PST (15:00 UTC)
    volumes={VOLUME_PATH: volume},
)
def conviction_alerts():
    """
    Conviction Alerts - Scans daily results for high-conviction opportunities.

    Alerts when stocks exceed conviction threshold (score > 80).
    Runs Mon-Fri at 7:00 AM PST, 1 hour after daily scan completes.
    Sends Telegram notification with top high-conviction stocks.
    """
    import sys
    sys.path.insert(0, '/root')

    print("=" * 70)
    print("🎯 SCANNING FOR HIGH-CONVICTION OPPORTUNITIES")
    print("=" * 70)

    try:
        # Load latest scan results
        data_dir = Path(VOLUME_PATH)
        scan_files = sorted(data_dir.glob("scan_*.json"), reverse=True)

        if not scan_files:
            print("⚠️  No scan results found")
            return {'success': False, 'error': 'No scan results'}

        with open(scan_files[0]) as f:
            scan_data = json.load(f)

        results = scan_data.get('results', [])
        print(f"📊 Analyzing {len(results)} stocks from latest scan")

        # Filter high-conviction stocks (score > 80)
        high_conviction = [
            stock for stock in results
            if stock.get('story_score', 0) > 80
        ]

        # Sort by score
        high_conviction.sort(key=lambda x: x.get('story_score', 0), reverse=True)

        print(f"✅ Found {len(high_conviction)} high-conviction opportunities (score > 80)")

        if not high_conviction:
            print("📊 No high-conviction alerts today")
            return {'success': True, 'count': 0}

        # Print top 10
        print(f"\n🎯 Top High-Conviction Stocks:")
        print("-" * 70)
        for stock in high_conviction[:10]:
            ticker = stock.get('ticker', 'Unknown')
            score = stock.get('story_score', 0)
            theme = stock.get('hottest_theme', 'No theme')
            print(f"• {ticker}: {score:.1f} - {theme}")

        # Send Telegram notification
        try:
            from src.notifications import get_notification_manager

            notif_mgr = get_notification_manager()

            # Prepare notification data
            notif_data = {
                'stocks': [
                    {
                        'ticker': stock.get('ticker', 'Unknown'),
                        'score': stock.get('story_score', 0),
                        'theme': stock.get('hottest_theme', 'No theme'),
                        'strength': stock.get('story_strength', 'unknown')
                    }
                    for stock in high_conviction[:10]
                ]
            }

            result = notif_mgr.send_alert('conviction', notif_data)
            if result.get('telegram'):
                print("📱 Telegram notification sent")
            else:
                print("⚠️  Telegram notification skipped (not configured)")
        except Exception as e:
            print(f"⚠️  Notification failed: {e}")

        print()
        print("=" * 70)
        print("✅ Conviction alerts complete!")
        print("=" * 70)

        return {
            'success': True,
            'count': len(high_conviction),
            'top_ticker': high_conviction[0].get('ticker') if high_conviction else None,
            'top_score': high_conviction[0].get('story_score', 0) if high_conviction else 0
        }

    except Exception as e:
        print(f"❌ Conviction alerts failed: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}


@app.function(
    image=image,
    timeout=1200,  # 20 minutes max
    schedule=modal.Cron("15 15 * * 1-5"),  # Run Mon-Fri at 7:15 AM PST (15:15 UTC)
    volumes={VOLUME_PATH: volume},
)
def unusual_options_alerts():
    """
    Unusual Options Activity Alerts.

    Scans universe for unusual options flow and alerts on significant activity.
    Runs Mon-Fri at 7:15 AM PST, after conviction alerts.
    """
    import sys
    sys.path.insert(0, '/root')

    print("=" * 70)
    print("🔥 SCANNING FOR UNUSUAL OPTIONS ACTIVITY")
    print("=" * 70)

    try:
        from src.data.universe_manager import get_universe_manager
        from src.data.options import get_unusual_activity

        # Get watchlist tickers (top stocks from latest scan)
        data_dir = Path(VOLUME_PATH)
        scan_files = sorted(data_dir.glob("scan_*.json"), reverse=True)

        tickers_to_check = []
        if scan_files:
            with open(scan_files[0]) as f:
                scan_data = json.load(f)
            # Check top 50 stocks from scan
            results = scan_data.get('results', [])[:50]
            tickers_to_check = [r.get('ticker') for r in results if r.get('ticker')]
        else:
            # Fallback to common tickers
            tickers_to_check = ['SPY', 'QQQ', 'NVDA', 'TSLA', 'AAPL', 'MSFT', 'AMD', 'META']

        print(f"📊 Checking {len(tickers_to_check)} tickers for unusual options activity")

        unusual_activities = []

        for ticker in tickers_to_check[:30]:  # Limit to 30 to avoid rate limits
            try:
                activity = get_unusual_activity(ticker, threshold=2.0)
                if activity and activity.get('unusual_contracts'):
                    unusual_activities.append({
                        'ticker': ticker,
                        'volume': activity.get('total_volume', 0),
                        'sentiment': activity.get('sentiment', 'neutral'),
                        'unusual_count': len(activity.get('unusual_contracts', []))
                    })
            except Exception as e:
                print(f"   ⚠️  {ticker}: {e}")

        unusual_activities.sort(key=lambda x: x.get('volume', 0), reverse=True)

        print(f"✅ Found {len(unusual_activities)} tickers with unusual options activity")

        if unusual_activities:
            print(f"\n🔥 Top Unusual Activity:")
            print("-" * 70)
            for activity in unusual_activities[:10]:
                ticker = activity.get('ticker')
                volume = activity.get('volume', 0)
                sentiment = activity.get('sentiment')
                print(f"• {ticker}: {volume:,} volume - {sentiment}")

        # Send notification if activity found
        if unusual_activities:
            try:
                from src.notifications import get_notification_manager

                notif_mgr = get_notification_manager()
                notif_data = {'activities': unusual_activities[:10]}

                result = notif_mgr.send_alert('unusual_options', notif_data)
                if result.get('telegram'):
                    print("📱 Telegram notification sent")
            except Exception as e:
                print(f"⚠️  Notification failed: {e}")

        print()
        print("=" * 70)
        print("✅ Unusual options scan complete!")
        print("=" * 70)

        return {
            'success': True,
            'count': len(unusual_activities),
            'activities': unusual_activities[:10]
        }

    except Exception as e:
        print(f"❌ Unusual options scan failed: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}


@app.function(
    image=image,
    timeout=600,  # 10 minutes max
    schedule=modal.Cron("45 14 * * 1-5"),  # Run Mon-Fri at 9:45 AM ET / 6:45 AM PST (14:45 UTC)
    volumes={VOLUME_PATH: volume},
)
def daily_executive_briefing():
    """
    Daily Executive Briefing - Comprehensive market overview at market open.

    Generates and sends briefing with:
    - Market overview and sentiment
    - Top themes and opportunities
    - Key alerts (conviction, rotation, unusual activity)
    - Executive commentary highlights

    Runs Mon-Fri at 9:30 AM ET (market open).
    """
    import sys
    sys.path.insert(0, '/root')

    print("=" * 70)
    print("📊 GENERATING DAILY EXECUTIVE BRIEFING")
    print("=" * 70)

    try:
        # Generate briefing
        from src.intelligence.executive_commentary import generate_executive_briefing

        briefing = generate_executive_briefing()

        print(f"✅ Briefing generated")
        print(f"   Sections: {len(briefing.get('sections', []))}")

        # Format briefing message
        message = "*📊 DAILY MARKET BRIEFING*\n"
        message += f"_{datetime.now().strftime('%A, %B %d, %Y')}_\n\n"

        # Add market overview
        if 'market_overview' in briefing:
            overview = briefing['market_overview']
            message += f"*Market Overview:*\n"
            message += f"{overview.get('summary', 'No overview available')}\n\n"

        # Add top themes
        data_dir = Path(VOLUME_PATH)
        theme_file = data_dir / 'theme_discovery_latest.json'
        if theme_file.exists():
            with open(theme_file) as f:
                theme_data = json.load(f)
            themes = theme_data.get('themes', [])[:3]
            if themes:
                message += f"*🔍 Top Themes:*\n"
                for theme in themes:
                    name = theme.get('name', 'Unknown')
                    confidence = theme.get('confidence_score', 0)
                    message += f"• {name} ({confidence:.0f}%)\n"
                message += "\n"

        # Add conviction alerts
        scan_files = sorted(data_dir.glob("scan_*.json"), reverse=True)
        if scan_files:
            with open(scan_files[0]) as f:
                scan_data = json.load(f)
            high_conviction = [
                s for s in scan_data.get('results', [])
                if s.get('story_score', 0) > 80
            ][:3]
            if high_conviction:
                message += f"*🎯 High Conviction:*\n"
                for stock in high_conviction:
                    ticker = stock.get('ticker')
                    score = stock.get('story_score', 0)
                    message += f"• {ticker}: {score:.0f}\n"
                message += "\n"

        message += f"\n🔗 [View Dashboard](https://zhuanleee.github.io/stock_scanner_bot)"

        # Send notification
        try:
            from src.notifications import get_notification_manager

            notif_mgr = get_notification_manager()
            result = notif_mgr.send(message, title="📊 Daily Market Briefing")

            if result.get('telegram'):
                print("📱 Telegram briefing sent")
            else:
                print("⚠️  Telegram notification skipped (not configured)")
        except Exception as e:
            print(f"⚠️  Notification failed: {e}")

        print()
        print("=" * 70)
        print("✅ Daily briefing complete!")
        print("=" * 70)

        return {
            'success': True,
            'briefing': briefing
        }

    except Exception as e:
        print(f"❌ Daily briefing failed: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}


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
    themes: bool = False,
):
    """
    Run scanner from command line.

    Examples:
        modal run modal_scanner.py --test          # Test with NVDA
        modal run modal_scanner.py --ticker AAPL   # Scan single stock
        modal run modal_scanner.py --daily         # Run full daily scan
        modal run modal_scanner.py --themes        # Run theme discovery
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
    elif themes:
        print("🔍 Running automated theme discovery...")
        result = automated_theme_discovery.remote()
        print(f"\n✅ Theme discovery complete: {result}")
    else:
        print("Usage:")
        print("  modal run modal_scanner.py --test")
        print("  modal run modal_scanner.py --ticker NVDA")
        print("  modal run modal_scanner.py --daily")
        print("  modal run modal_scanner.py --themes")
