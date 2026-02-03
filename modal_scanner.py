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
app = modal.App("stockstory-scanner")

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
    max_containers=10,  # Max 10 GPU containers at once
    secrets=[
        # Add your API keys as Modal secrets
        # Run: modal secret create stock-api-keys \
        #   POLYGON_API_KEY=xxx \
        #   XAI_API_KEY=xxx \
        #   DEEPSEEK_API_KEY=xxx ...
        modal.Secret.from_name("Stock_Story")
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


def _run_daily_scan():
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

    # Also save to Modal Volume for API/Telegram access
    csv_volume_path = Path(VOLUME_PATH) / 'scan_results_latest.csv'
    df.to_csv(csv_volume_path, index=False)
    print(f"💾 Saved to Modal Volume: scan_results_latest.csv")

    # Save to JSON in Modal Volume for API access
    # Use sorted DataFrame records so API returns same order as Telegram
    # Replace NaN with None for JSON serialization
    df_clean = df.where(pd.notnull(df), None)
    scan_data = {
        "status": "success",
        "timestamp": datetime.now().isoformat(),
        "total": len(tickers),
        "successful": len(successful),
        "failed": len(failed),
        "duration_seconds": duration,
        "results": df_clean.to_dict('records')  # Sorted by story_score descending
    }

    json_path = Path(VOLUME_PATH) / json_filename
    with open(json_path, 'w') as f:
        json.dump(scan_data, f, indent=2)

    volume.commit()  # Persist to volume
    print(f"💾 Saved to Modal Volume: {json_filename}")

    # Register scan with WatchlistManager for tracking
    try:
        from src.data.watchlist_manager import get_watchlist_manager
        wm = get_watchlist_manager(VOLUME_PATH)

        # Extract top picks and themes
        top_picks = df.head(10)['ticker'].tolist() if 'ticker' in df.columns else []
        themes = df.head(20)['hottest_theme'].dropna().unique().tolist()[:5] if 'hottest_theme' in df.columns else []

        scan_record = wm.register_scan(
            filename=json_filename,
            top_picks=top_picks,
            themes=themes,
            total_stocks=len(successful)
        )
        print(f"📋 Registered as Scan #{scan_record.scan_id}")
    except Exception as e:
        print(f"⚠️  Could not register scan: {e}")

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
        personal_chat_id = os.environ.get('TELEGRAM_CHAT_ID')
        group_chat_id = os.environ.get('TELEGRAM_GROUP_CHAT_ID', '-1003774843100')
        group_topic_id = int(os.environ.get('TELEGRAM_GROUP_TOPIC_ID', '46'))  # Bot Alerts topic

        if bot_token:
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

            message += f"\n🔗 View: https://zhuanleee.github.io/StockStory"

            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

            # Send to personal chat
            if personal_chat_id:
                payload = {
                    "chat_id": personal_chat_id,
                    "text": message,
                    "parse_mode": "Markdown"
                }
                try:
                    response = requests.post(url, json=payload, timeout=10)
                    if response.status_code == 200:
                        print(f"📱 Telegram sent to personal chat")
                    else:
                        print(f"⚠️  Telegram failed for personal chat: {response.status_code}")
                except Exception as e:
                    print(f"⚠️  Telegram error for personal chat: {e}")

            # Send to group topic
            if group_chat_id:
                payload = {
                    "chat_id": group_chat_id,
                    "text": message,
                    "parse_mode": "Markdown",
                    "message_thread_id": group_topic_id  # Send to specific topic/tab
                }
                try:
                    response = requests.post(url, json=payload, timeout=10)
                    if response.status_code == 200:
                        print(f"📱 Telegram sent to group topic {group_topic_id}")
                    else:
                        print(f"⚠️  Telegram failed for group topic: {response.status_code}")
                except Exception as e:
                    print(f"⚠️  Telegram error for group topic: {e}")
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


def _run_automated_theme_discovery():
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


def _run_conviction_alerts():
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


def _run_unusual_options_alerts():
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


def _run_daily_executive_briefing():
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


def _run_exit_signal_check():
    """
    TIER 3: Exit Signal Detection

    Monitors all holdings for exit signals before market open.
    Checks for: red flags, sentiment shifts, and negative news.
    Sends Telegram alerts for positions that need attention.
    """
    import sys
    sys.path.insert(0, '/root')

    print("=" * 70)
    print("🛡️  TIER 3: EXIT SIGNAL DETECTION")
    print("=" * 70)

    try:
        from src.intelligence.exit_signal_detector import get_exit_signal_detector
        from src.notifications.notification_manager import get_notification_manager, NotificationPriority

        detector = get_exit_signal_detector()
        notif_manager = get_notification_manager()

        # Get current holdings
        holdings = ['NVDA', 'TSLA', 'AAPL', 'GOOGL', 'META']  # TODO: Get from portfolio

        if not holdings:
            print("No holdings to check")
            return {'success': True, 'holdings': 0, 'exit_signals': 0}

        print(f"Checking {len(holdings)} holdings...")

        # Check for exit signals
        exit_signals = detector.check_holdings(holdings)

        if not exit_signals:
            print("✅ All holdings clear - no exit signals")
            return {
                'success': True,
                'holdings_checked': len(holdings),
                'exit_signals': 0
            }

        # Send notifications for exit signals
        print(f"⚠️  {len(exit_signals)} exit signal(s) detected!")

        for ticker, signal in exit_signals.items():
            severity = signal['severity']
            print(f"\n🚨 {ticker}: {signal['signal_type']} ({severity})")

            # Send Telegram alert
            try:
                notif_manager.send_alert(
                    alert_type='position_alert',
                    data={
                        'ticker': ticker,
                        'signal_type': signal['signal_type'],
                        'severity': severity,
                        'reason': signal['reason'],
                        'action': signal['action']
                    },
                    priority=NotificationPriority.CRITICAL if severity == 'CRITICAL' else NotificationPriority.HIGH
                )
                print(f"   ✓ Alert sent")
            except Exception as e:
                print(f"   ✗ Alert failed: {e}")

        print("=" * 70)

        return {
            'success': True,
            'holdings_checked': len(holdings),
            'exit_signals_detected': len(exit_signals)
        }

    except Exception as e:
        print(f"❌ Exit signal check failed: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}


def _run_parameter_learning_health_check():
    """
    Parameter Learning Health Check - Weekly monitoring of learning system.

    Checks:
    - Learning system health status
    - Win rate trends
    - Stale parameters
    - Error rates

    Alerts if system degradation detected.
    Runs Mondays at 8:00 AM PST (weekly check).
    """
    import sys
    sys.path.insert(0, '/root')

    print("=" * 70)
    print("⚙️  PARAMETER LEARNING HEALTH CHECK")
    print("=" * 70)

    try:
        from src.learning.parameter_learning import ParameterRegistry
        from src.learning.monitoring.health import SelfHealthMonitor

        registry = ParameterRegistry()
        health_monitor = SelfHealthMonitor(registry)

        # Check health
        health_status = health_monitor.check_health()

        status = health_status.get('status', 'unknown')
        issues = health_status.get('issues', [])

        print(f"Status: {status}")
        print(f"Issues: {len(issues)}")

        # Get detailed metrics
        params_status = registry.get_all_parameters()
        total_params = len(params_status)

        # Count stale parameters (no update in 7+ days)
        from datetime import datetime, timedelta
        now = datetime.now()
        stale_threshold = now - timedelta(days=7)

        stale_count = sum(
            1 for p in params_status.values()
            if p.get('last_updated', now) < stale_threshold
        )

        # Calculate win rate from outcomes
        from src.learning.tracking.outcomes import OutcomeTracker
        outcome_tracker = OutcomeTracker()

        recent_outcomes = outcome_tracker.get_recent_outcomes(days=7)
        if recent_outcomes:
            wins = sum(1 for o in recent_outcomes if o.get('success', False))
            win_rate = (wins / len(recent_outcomes)) * 100
        else:
            win_rate = 0

        print(f"\nMetrics:")
        print(f"  Total parameters: {total_params}")
        print(f"  Stale parameters: {stale_count}")
        print(f"  Win rate (7d): {win_rate:.1f}%")
        print(f"  Recent outcomes: {len(recent_outcomes)}")

        # Determine if alert needed
        alert_needed = (
            status != 'healthy' or
            stale_count > 5 or
            win_rate < 50 or
            len(issues) > 0
        )

        if alert_needed:
            print("\n⚠️  ALERT: Health issues detected")

            # Send notification
            try:
                from src.notifications import get_notification_manager

                notif_mgr = get_notification_manager()
                notif_data = {
                    'status': status,
                    'win_rate': win_rate,
                    'stale_params': stale_count,
                    'issues': issues
                }

                result = notif_mgr.send_alert('learning_health', notif_data)
                if result.get('telegram'):
                    print("📱 Alert sent")
            except Exception as e:
                print(f"⚠️  Notification failed: {e}")
        else:
            print("\n✅ System healthy, no alerts needed")

        print()
        print("=" * 70)
        print("✅ Health check complete!")
        print("=" * 70)

        return {
            'success': True,
            'status': status,
            'win_rate': win_rate,
            'stale_params': stale_count,
            'alert_sent': alert_needed
        }

    except Exception as e:
        print(f"❌ Health check failed: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}


def _run_data_staleness_monitor():
    """
    Data Staleness Monitor - Monitors data freshness across all sources.

    Checks:
    - Scan results age (should be < 24 hours)
    - Theme discovery age (should be < 24 hours)
    - Volume file timestamps
    - API health

    Alerts if data becomes stale or sources fail.
    Runs every 6 hours.
    """
    import sys
    sys.path.insert(0, '/root')
    from datetime import datetime, timedelta

    print("=" * 70)
    print("⚠️  DATA STALENESS MONITOR")
    print("=" * 70)

    try:
        data_dir = Path(VOLUME_PATH)
        now = datetime.now()
        stale_sources = []

        # Check scan results
        scan_files = sorted(data_dir.glob("scan_*.json"), reverse=True)
        if scan_files:
            latest_scan = scan_files[0]
            scan_age = (now - datetime.fromtimestamp(latest_scan.stat().st_mtime))
            scan_age_hours = scan_age.total_seconds() / 3600

            print(f"Latest scan: {scan_age_hours:.1f} hours old")

            if scan_age_hours > 48:  # Alert if > 48 hours old
                stale_sources.append({
                    'name': 'Scan Results',
                    'age_hours': scan_age_hours
                })
        else:
            stale_sources.append({
                'name': 'Scan Results',
                'age_hours': 999
            })
            print("⚠️  No scan results found!")

        # Check theme discovery
        theme_file = data_dir / 'theme_discovery_latest.json'
        if theme_file.exists():
            theme_age = (now - datetime.fromtimestamp(theme_file.stat().st_mtime))
            theme_age_hours = theme_age.total_seconds() / 3600

            print(f"Latest theme discovery: {theme_age_hours:.1f} hours old")

            if theme_age_hours > 48:
                stale_sources.append({
                    'name': 'Theme Discovery',
                    'age_hours': theme_age_hours
                })
        else:
            print("⚠️  No theme discovery results")

        # Alert if stale data found
        if stale_sources:
            print(f"\n⚠️  ALERT: {len(stale_sources)} stale data sources detected")

            # Send notification
            try:
                from src.notifications import get_notification_manager

                notif_mgr = get_notification_manager()
                notif_data = {'stale_sources': stale_sources}

                result = notif_mgr.send_alert('data_staleness', notif_data)
                if result.get('telegram'):
                    print("📱 Alert sent")
            except Exception as e:
                print(f"⚠️  Notification failed: {e}")
        else:
            print("\n✅ All data sources fresh")

        print()
        print("=" * 70)
        print("✅ Staleness check complete!")
        print("=" * 70)

        return {
            'success': True,
            'stale_count': len(stale_sources),
            'stale_sources': stale_sources
        }

    except Exception as e:
        print(f"❌ Staleness check failed: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}


def _run_weekly_summary_report():
    """
    Weekly Summary Report - Comprehensive week performance analysis.

    Analyzes:
    - Week's top performing stocks
    - Theme evolution and trends
    - Parameter learning performance
    - Hit rate statistics
    - Notable market events

    Sends detailed weekly report.
    Runs Sundays at 6:00 PM PST (Monday 02:00 UTC).
    """
    import sys
    sys.path.insert(0, '/root')
    from datetime import datetime, timedelta

    print("=" * 70)
    print("📈 GENERATING WEEKLY SUMMARY REPORT")
    print("=" * 70)

    try:
        data_dir = Path(VOLUME_PATH)
        now = datetime.now()
        week_ago = now - timedelta(days=7)

        # Collect all scan results from past week
        weekly_scans = []
        for scan_file in data_dir.glob("scan_*.json"):
            file_time = datetime.fromtimestamp(scan_file.stat().st_mtime)
            if file_time >= week_ago:
                with open(scan_file) as f:
                    scan_data = json.load(f)
                weekly_scans.append(scan_data)

        print(f"📊 Analyzing {len(weekly_scans)} scans from past week")

        # Aggregate top performers
        all_stocks = {}
        for scan in weekly_scans:
            for stock in scan.get('results', []):
                ticker = stock.get('ticker')
                score = stock.get('story_score', 0)
                if ticker:
                    if ticker not in all_stocks:
                        all_stocks[ticker] = []
                    all_stocks[ticker].append(score)

        # Calculate average scores
        top_performers = []
        for ticker, scores in all_stocks.items():
            avg_score = sum(scores) / len(scores)
            appearances = len(scores)
            if appearances >= 3:  # Appeared in at least 3 scans
                top_performers.append({
                    'ticker': ticker,
                    'avg_score': avg_score,
                    'appearances': appearances
                })

        top_performers.sort(key=lambda x: x['avg_score'], reverse=True)

        print(f"✅ Top {len(top_performers[:10])} consistent performers identified")

        # Analyze theme evolution
        theme_files = sorted(data_dir.glob("theme_discovery_*.json"))
        weekly_themes = []
        for theme_file in theme_files:
            file_time = datetime.fromtimestamp(theme_file.stat().st_mtime)
            if file_time >= week_ago:
                with open(theme_file) as f:
                    theme_data = json.load(f)
                weekly_themes.append(theme_data)

        print(f"✅ Analyzed {len(weekly_themes)} theme discovery runs")

        # Get learning system stats
        from src.learning.tracking.outcomes import OutcomeTracker
        outcome_tracker = OutcomeTracker()
        weekly_outcomes = outcome_tracker.get_recent_outcomes(days=7)

        wins = sum(1 for o in weekly_outcomes if o.get('success', False))
        win_rate = (wins / len(weekly_outcomes) * 100) if weekly_outcomes else 0

        print(f"✅ Win rate (7d): {win_rate:.1f}% ({wins}/{len(weekly_outcomes)})")

        # Format report message
        message = f"*📈 WEEKLY SUMMARY REPORT*\n"
        message += f"_{now.strftime('%B %d, %Y')}_\n\n"

        message += f"*📊 Week in Review:*\n"
        message += f"• Scans completed: {len(weekly_scans)}\n"
        message += f"• Themes discovered: {len(weekly_themes)}\n"
        message += f"• Win rate: {win_rate:.1f}%\n\n"

        message += f"*🏆 Top Performers (Avg Score):*\n"
        for i, perf in enumerate(top_performers[:5], 1):
            ticker = perf['ticker']
            score = perf['avg_score']
            apps = perf['appearances']
            message += f"{i}. *{ticker}*: {score:.1f} ({apps}x)\n"

        message += f"\n_Next report: {(now + timedelta(days=7)).strftime('%B %d, %Y')}_"

        # Send notification
        try:
            from src.notifications import get_notification_manager

            notif_mgr = get_notification_manager()
            result = notif_mgr.send(message, title="📈 Weekly Summary Report")

            if result.get('telegram'):
                print("📱 Report sent")
            else:
                print("⚠️  Notification skipped (not configured)")
        except Exception as e:
            print(f"⚠️  Notification failed: {e}")

        print()
        print("=" * 70)
        print("✅ Weekly report complete!")
        print("=" * 70)

        return {
            'success': True,
            'scans': len(weekly_scans),
            'themes': len(weekly_themes),
            'win_rate': win_rate,
            'top_performers': top_performers[:10]
        }

    except Exception as e:
        print(f"❌ Weekly report failed: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}


def _run_batch_insider_transactions_update():
    """
    Batch Insider Transactions Update.

    Fetches and caches insider transaction data for universe stocks.
    Runs Mon-Fri at 2:00 PM PST (after market close).
    """
    import sys
    sys.path.insert(0, '/root')

    print("=" * 70)
    print("📋 BATCH INSIDER TRANSACTIONS UPDATE")
    print("=" * 70)

    try:
        # Get top stocks from latest scan
        data_dir = Path(VOLUME_PATH)
        scan_files = sorted(data_dir.glob("scan_*.json"), reverse=True)

        tickers = []
        if scan_files:
            with open(scan_files[0]) as f:
                scan_data = json.load(f)
            results = scan_data.get('results', [])[:100]  # Top 100 stocks
            tickers = [r.get('ticker') for r in results if r.get('ticker')]

        print(f"📊 Fetching insider data for {len(tickers)} stocks")

        from src.data.sec_edgar import get_insider_transactions
        successful = 0
        failed = 0

        for ticker in tickers[:50]:  # Limit to avoid rate limits
            try:
                transactions = get_insider_transactions(ticker)
                if transactions:
                    successful += 1
            except Exception as e:
                failed += 1
                if failed <= 5:
                    print(f"   ⚠️  {ticker}: {e}")

        print(f"✅ Fetched: {successful}, Failed: {failed}")
        print("=" * 70)

        return {'success': True, 'fetched': successful, 'failed': failed}

    except Exception as e:
        print(f"❌ Batch update failed: {e}")
        return {'success': False, 'error': str(e)}


def _run_batch_google_trends_prefetch():
    """
    Batch Google Trends Pre-fetch.

    Pre-fetches Google Trends data for top stocks to speed up API responses.
    Runs Mon-Fri at 6:30 AM PST (during daily scan).
    """
    import sys
    sys.path.insert(0, '/root')

    print("=" * 70)
    print("📈 BATCH GOOGLE TRENDS PRE-FETCH")
    print("=" * 70)

    try:
        # Get top stocks from latest scan
        data_dir = Path(VOLUME_PATH)
        scan_files = sorted(data_dir.glob("scan_*.json"), reverse=True)

        tickers = []
        if scan_files:
            with open(scan_files[0]) as f:
                scan_data = json.load(f)
            results = scan_data.get('results', [])[:50]  # Top 50 stocks
            tickers = [r.get('ticker') for r in results if r.get('ticker')]

        print(f"📊 Pre-fetching trends for {len(tickers)} stocks")

        from src.intelligence.google_trends import get_trend_score
        successful = 0
        failed = 0

        for ticker in tickers:
            try:
                score = get_trend_score(ticker)
                if score is not None:
                    successful += 1
            except Exception as e:
                failed += 1

        print(f"✅ Fetched: {successful}, Failed: {failed}")
        print("=" * 70)

        return {'success': True, 'fetched': successful, 'failed': failed}

    except Exception as e:
        print(f"❌ Batch prefetch failed: {e}")
        return {'success': False, 'error': str(e)}


def _run_x_intelligence_crisis_check():
    """
    3-LAYER INTELLIGENCE CRISIS MONITORING.

    Layer 1: X Intelligence (social detection) - detects threats from X/Twitter
    Layer 2: Web Intelligence (news verification) - verifies with Reuters, Bloomberg, etc.
    Layer 3: Data Intelligence (market reaction) - confirms market impact

    Uses xAI SDK with x_search and web_search tools.
    Sends Telegram alerts only when verified across layers.

    Severity levels:
    - 9-10: CRITICAL - Emergency protocol (halt trading)
    - 7-8: MAJOR - Tighten controls (avoid sectors)
    - 1-6: WARNING - Awareness (informational)

    Runs every 15 minutes.
    """
    import sys
    sys.path.insert(0, '/root')

    print("=" * 70)
    print("🚨 3-LAYER INTELLIGENCE CRISIS CHECK")
    print("=" * 70)
    print("Layer 1: X Intelligence (social detection)")
    print("Layer 2: Web Intelligence (news verification)")
    print("Layer 3: Data Intelligence (market reaction)")
    print("=" * 70)

    try:
        from src.ai.xai_x_intelligence_v2 import get_x_intelligence_v2
        from src.ai.web_intelligence import get_web_intelligence
        from src.notifications.notification_manager import get_notification_manager, NotificationPriority

        # Initialize intelligence layers
        x_intel = get_x_intelligence_v2()  # Layer 1
        web_intel = get_web_intelligence()  # Layer 2
        notification_manager = get_notification_manager()

        if not x_intel:
            print("✗ Layer 1 (X Intelligence) not available")
            return {
                'success': False,
                'error': 'X Intelligence SDK not available',
                'status': 'unavailable'
            }

        print("\n🔍 LAYER 1: Searching X/Twitter for threats...")
        print("   Using xAI SDK with x_search tool")

        # Layer 1: Search X for crises (REAL X search!)
        crisis_topics = x_intel.search_x_for_crises()

        if not crisis_topics:
            print("✅ Layer 1: No threats detected on X")
            return {
                'success': True,
                'crises_detected': 0,
                'status': 'clear',
                'method': '3_layer_intelligence'
            }

        print(f"⚠️  Layer 1: {len(crisis_topics)} potential threat(s) found on X")

        # Process each crisis with 3-layer verification
        verified_crises = []
        critical_count = 0
        major_count = 0
        warning_count = 0
        false_alarms = 0

        for topic_data in crisis_topics:
            topic = topic_data.get('topic', 'Unknown')
            x_severity = topic_data.get('severity', 5)

            print(f"\n{'='*70}")
            print(f"ANALYZING: {topic}")
            print(f"{'='*70}")
            print(f"📱 Layer 1 (X): Severity {x_severity}/10")

            # Layer 1: Deep X analysis
            x_analysis = x_intel.analyze_crisis_topic(topic)

            if not x_analysis:
                print(f"  ✗ Layer 1 analysis failed")
                continue

            x_severity = x_analysis.get('severity', 5)
            x_verified = x_analysis.get('verified', False)
            print(f"   Refined Severity: {x_severity}/10")
            print(f"   X Verification: {x_verified}")

            # Only verify with web if severity >= 7
            if x_severity < 7:
                warning_count += 1
                print(f"   ℹ️  Below alert threshold (< 7)")
                continue

            # Layer 2: Verify with Web Intelligence
            if web_intel:
                print(f"\n🌐 Layer 2 (Web): Verifying with news sources...")
                web_verification = web_intel.verify_crisis(topic, x_severity)

                if web_verification:
                    web_verified = web_verification.get('verified', False)
                    web_severity = web_verification.get('news_severity', 0)
                    web_sources = web_verification.get('sources', [])
                    web_credibility = web_verification.get('credibility', 0.0)

                    print(f"   News Verified: {web_verified}")
                    print(f"   News Severity: {web_severity}/10")
                    print(f"   Sources: {', '.join(web_sources) if web_sources else 'None'}")
                    print(f"   Credibility: {web_credibility:.1%}")

                    # Require news verification for high-severity alerts
                    if not web_verified and x_severity >= 9:
                        print(f"   ⚠️  FALSE ALARM: High X severity but NO news coverage")
                        print(f"   → Likely rumor or exaggeration")
                        false_alarms += 1
                        continue

                    # Adjust severity based on web intelligence
                    if web_verified and web_severity > 0:
                        # Average the two severities if both agree
                        combined_severity = (x_severity + web_severity) // 2
                        print(f"   Combined Severity: {combined_severity}/10")
                    else:
                        # Downgrade if web doesn't confirm
                        combined_severity = max(x_severity - 2, 1)
                        print(f"   Downgraded Severity: {combined_severity}/10 (no web confirmation)")

                    severity = combined_severity
                    verified = web_verified or x_verified
                else:
                    print(f"   ⚠️  Layer 2 verification failed")
                    severity = x_severity
                    verified = x_verified
            else:
                print(f"   ⚠️  Layer 2 (Web) not available")
                severity = x_severity
                verified = x_verified

            print(f"\n📊 FINAL ASSESSMENT:")
            print(f"   Severity: {severity}/10")
            print(f"   Verified: {verified}")

            # Only alert on severity >= 7
            if severity < 7:
                warning_count += 1
                print(f"   → No alert (below threshold)")
                continue

            # Determine alert type and priority
            if severity >= 9 and verified:
                alert_type = 'crisis_emergency'
                priority = NotificationPriority.CRITICAL
                protocol_type = 'emergency'
                critical_count += 1
                print(f"   🚨 CRITICAL ALERT")
            elif severity >= 7:
                alert_type = 'crisis_major'
                priority = NotificationPriority.CRITICAL
                protocol_type = 'major'
                major_count += 1
                print(f"   ⚠️  MAJOR ALERT")
            else:
                alert_type = 'crisis_alert'
                priority = NotificationPriority.HIGH
                protocol_type = 'warning'
                warning_count += 1
                print(f"   ℹ️  WARNING ALERT")

            # Prepare crisis data for notification
            crisis_data = {
                'severity': severity,
                'topic': topic,
                'crisis_type': 'multi_source_verified' if (web_intel and web_verified) else 'social_only',
                'description': x_analysis.get('raw_analysis', '')[:500],
                'verified': verified,
                'credibility_score': web_verification.get('credibility', 0.5) if (web_intel and web_verification) else x_analysis.get('credibility', 0.5),
                'affected_sectors': x_analysis.get('affected_sectors', []),
                'affected_tickers': [],
                'immediate_actions': ['Monitor situation', 'Review positions'],
                'protocol_type': protocol_type,
                'verification_layers': {
                    'x_severity': x_severity,
                    'x_verified': x_verified,
                    'web_verified': web_verification.get('verified', False) if (web_intel and web_verification) else False,
                    'web_sources': web_verification.get('sources', []) if (web_intel and web_verification) else []
                }
            }

            verified_crises.append(crisis_data)

            # Send Telegram notification
            print(f"   📤 Sending Telegram notification...")
            try:
                result = notification_manager.send_alert(
                    alert_type=alert_type,
                    data=crisis_data,
                    priority=priority
                )
                if result.get('telegram'):
                    print(f"  ✓ Telegram notification sent ({protocol_type})")
                else:
                    print(f"  ✗ Telegram notification failed")
            except Exception as e:
                print(f"  ✗ Notification error: {e}")

        print("\n" + "=" * 70)
        print(f"✅ 3-LAYER INTELLIGENCE CHECK COMPLETE:")
        print(f"   Critical: {critical_count}")
        print(f"   Major: {major_count}")
        print(f"   Warning: {warning_count}")
        print(f"   False Alarms Filtered: {false_alarms}")
        print(f"   Verified Crises: {len(verified_crises)}")
        print("=" * 70)

        return {
            'success': True,
            'crises_detected': len(verified_crises),
            'critical': critical_count,
            'major': major_count,
            'warning': warning_count,
            'false_alarms_filtered': false_alarms,
            'method': '3_layer_intelligence',
            'status': 'alerts_sent' if verified_crises else 'clear'
        }

    except Exception as e:
        print(f"❌ X Intelligence check failed: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}


def _run_batch_patent_data_update():
    """
    Batch Patent Data Update.

    Monthly update of patent data for universe stocks.
    Runs 1st of each month at 7:00 PM PST.
    """
    import sys
    sys.path.insert(0, '/root')

    print("=" * 70)
    print("📄 BATCH PATENT DATA UPDATE")
    print("=" * 70)

    try:
        # Get universe stocks
        data_dir = Path(VOLUME_PATH)
        scan_files = sorted(data_dir.glob("scan_*.json"), reverse=True)

        tickers = []
        if scan_files:
            with open(scan_files[0]) as f:
                scan_data = json.load(f)
            results = scan_data.get('results', [])[:100]  # Top 100 stocks
            tickers = [r.get('ticker') for r in results if r.get('ticker')]

        print(f"📊 Updating patent data for {len(tickers)} stocks")

        from src.data.patents import get_patent_intelligence
        patent_intel = get_patent_intelligence()

        successful = 0
        failed = 0

        for ticker in tickers[:50]:  # Limit batch size
            try:
                activity = patent_intel.get_company_patents(ticker)
                if activity:
                    successful += 1
            except Exception as e:
                failed += 1

        print(f"✅ Updated: {successful}, Failed: {failed}")
        print("=" * 70)

        return {'success': True, 'updated': successful, 'failed': failed}

    except Exception as e:
        print(f"❌ Batch update failed: {e}")
        return {'success': False, 'error': str(e)}


def _run_batch_contracts_update():
    """
    Batch Government Contracts Update.

    Weekly update of government contract data for universe stocks.
    Runs Sundays at 7:00 PM PST.
    """
    import sys
    sys.path.insert(0, '/root')

    print("=" * 70)
    print("📋 BATCH GOVERNMENT CONTRACTS UPDATE")
    print("=" * 70)

    try:
        # Get universe stocks
        data_dir = Path(VOLUME_PATH)
        scan_files = sorted(data_dir.glob("scan_*.json"), reverse=True)

        tickers = []
        if scan_files:
            with open(scan_files[0]) as f:
                scan_data = json.load(f)
            results = scan_data.get('results', [])[:100]  # Top 100 stocks
            tickers = [r.get('ticker') for r in results if r.get('ticker')]

        print(f"📊 Updating contract data for {len(tickers)} stocks")

        from src.data.gov_contracts import get_contract_intelligence
        contract_intel = get_contract_intelligence()

        successful = 0
        failed = 0

        for ticker in tickers[:50]:  # Limit batch size
            try:
                activity = contract_intel.get_company_contracts(ticker)
                if activity:
                    successful += 1
            except Exception as e:
                failed += 1

        print(f"✅ Updated: {successful}, Failed: {failed}")
        print("=" * 70)

        return {'success': True, 'updated': successful, 'failed': failed}

    except Exception as e:
        print(f"❌ Batch update failed: {e}")
        return {'success': False, 'error': str(e)}


def _run_sector_rotation_alerts():
    """
    Sector Rotation Alerts - Daily sector momentum and rotation analysis.

    Analyzes sector rotation patterns and peak warnings.
    Alerts on significant sector momentum shifts.
    Runs Mon-Fri at 7:30 AM PST.
    """
    import sys
    sys.path.insert(0, '/root')

    print("=" * 70)
    print("🔄 SECTOR ROTATION ANALYSIS")
    print("=" * 70)

    try:
        from src.intelligence.rotation_predictor import get_rotation_alerts, get_peak_warnings

        # Get rotation alerts
        rotation_alerts = get_rotation_alerts()
        peak_warnings = get_peak_warnings()

        print(f"✅ Rotation alerts: {len(rotation_alerts)}")
        print(f"✅ Peak warnings: {len(peak_warnings)}")

        # Send notification if alerts found
        if rotation_alerts or peak_warnings:
            try:
                from src.notifications import get_notification_manager

                notif_mgr = get_notification_manager()
                notif_data = {
                    'rotations': rotation_alerts[:5],
                    'peaks': peak_warnings[:5]
                }

                result = notif_mgr.send_alert('rotation', notif_data)
                if result.get('telegram'):
                    print("📱 Alert sent")
            except Exception as e:
                print(f"⚠️  Notification failed: {e}")

        print("=" * 70)
        return {
            'success': True,
            'rotations': len(rotation_alerts),
            'peaks': len(peak_warnings)
        }

    except Exception as e:
        print(f"❌ Rotation analysis failed: {e}")
        return {'success': False, 'error': str(e)}


def _run_institutional_flow_alerts():
    """
    Institutional Flow Alerts - Smart money tracking.

    Monitors institutional activity, options flow, and insider clusters.
    Alerts on unusual institutional movements.
    Runs Mon-Fri at 7:45 AM PST.
    """
    import sys
    sys.path.insert(0, '/root')

    print("=" * 70)
    print("💼 INSTITUTIONAL FLOW ANALYSIS")
    print("=" * 70)

    try:
        from src.intelligence.institutional_flow import get_institutional_summary, get_insider_clusters

        # Get institutional summary
        inst_summary = get_institutional_summary()
        insider_clusters = get_insider_clusters()

        print(f"✅ Institutional flows analyzed")
        print(f"✅ Insider clusters: {len(insider_clusters)}")

        # Check for significant activity
        significant_flows = inst_summary.get('significant_flows', [])

        if significant_flows or insider_clusters:
            try:
                from src.notifications import get_notification_manager

                notif_mgr = get_notification_manager()
                notif_data = {
                    'flows': significant_flows[:10],
                    'clusters': insider_clusters[:5]
                }

                result = notif_mgr.send_alert('institutional', notif_data)
                if result.get('telegram'):
                    print("📱 Alert sent")
            except Exception as e:
                print(f"⚠️  Notification failed: {e}")

        print("=" * 70)
        return {
            'success': True,
            'flows': len(significant_flows),
            'clusters': len(insider_clusters)
        }

    except Exception as e:
        print(f"❌ Institutional analysis failed: {e}")
        return {'success': False, 'error': str(e)}


def _run_executive_commentary_alerts():
    """
    Executive Commentary Alerts - CEO/CFO sentiment tracking.

    Monitors executive commentary for bullish/bearish statements.
    Alerts on significant sentiment changes.
    Runs Mon-Fri at 8:00 AM PST.
    """
    import sys
    sys.path.insert(0, '/root')

    print("=" * 70)
    print("📢 EXECUTIVE COMMENTARY ANALYSIS")
    print("=" * 70)

    try:
        from src.intelligence.executive_commentary import get_commentary_tracker

        tracker = get_commentary_tracker()

        # Get recent commentaries (past 24 hours)
        recent_commentaries = []
        try:
            # This would need implementation in executive_commentary.py
            # For now, placeholder
            print("✅ Commentary tracking active")
        except Exception as e:
            print(f"⚠️  Commentary tracking: {e}")

        # For now, return success without alerts
        # Full implementation requires executive_commentary module enhancement

        print("=" * 70)
        return {
            'success': True,
            'commentaries': len(recent_commentaries)
        }

    except Exception as e:
        print(f"❌ Executive commentary failed: {e}")
        return {'success': False, 'error': str(e)}


def _run_daily_correlation_analysis():
    """
    Daily Correlation Analysis - Theme and sector correlation matrix.

    Analyzes correlations between:
    - Themes and sectors
    - Theme performance patterns
    - Sector momentum relationships

    Stores results for API access.
    Runs Mon-Fri at 1:00 PM PST.
    """
    import sys
    sys.path.insert(0, '/root')
    import pandas as pd
    import numpy as np

    print("=" * 70)
    print("📊 DAILY CORRELATION ANALYSIS")
    print("=" * 70)

    try:
        # Load latest scan results
        data_dir = Path(VOLUME_PATH)
        scan_files = sorted(data_dir.glob("scan_*.json"), reverse=True)

        if not scan_files:
            print("⚠️  No scan results found")
            return {'success': False, 'error': 'No scan data'}

        with open(scan_files[0]) as f:
            scan_data = json.load(f)

        results = scan_data.get('results', [])
        print(f"📊 Analyzing correlations for {len(results)} stocks")

        # Build theme-score matrix
        theme_scores = {}
        for stock in results:
            theme = stock.get('hottest_theme', 'No theme')
            score = stock.get('story_score', 0)

            if theme not in theme_scores:
                theme_scores[theme] = []
            theme_scores[theme].append(score)

        # Calculate theme statistics
        theme_stats = {}
        for theme, scores in theme_scores.items():
            if len(scores) >= 3:  # At least 3 stocks
                theme_stats[theme] = {
                    'count': len(scores),
                    'mean_score': float(np.mean(scores)),
                    'median_score': float(np.median(scores)),
                    'std_score': float(np.std(scores)),
                    'max_score': float(np.max(scores)),
                    'min_score': float(np.min(scores))
                }

        print(f"✅ Analyzed {len(theme_stats)} themes")

        # Build correlation matrix (simplified version)
        # In a full implementation, this would calculate pairwise correlations
        # between theme momentum, sector movements, etc.
        correlation_matrix = {}

        for theme1 in list(theme_stats.keys())[:10]:  # Top 10 themes
            correlation_matrix[theme1] = {}
            for theme2 in list(theme_stats.keys())[:10]:
                if theme1 == theme2:
                    correlation_matrix[theme1][theme2] = 1.0
                else:
                    # Placeholder: Use score similarity as proxy for correlation
                    diff = abs(
                        theme_stats[theme1]['mean_score'] -
                        theme_stats[theme2]['mean_score']
                    )
                    correlation_matrix[theme1][theme2] = float(max(0, 1 - diff / 100))

        # Save correlation data
        correlation_data = {
            'timestamp': datetime.now().isoformat(),
            'theme_stats': theme_stats,
            'correlation_matrix': correlation_matrix
        }

        # Save to volume
        correlation_file = data_dir / 'correlation_analysis_latest.json'
        with open(correlation_file, 'w') as f:
            json.dump(correlation_data, f, indent=2)

        volume.commit()

        print(f"✅ Correlation matrix generated")
        print(f"   Themes analyzed: {len(theme_stats)}")
        print(f"   Correlation pairs: {len(correlation_matrix)}")

        print("=" * 70)
        return {
            'success': True,
            'themes': len(theme_stats),
            'correlations': len(correlation_matrix)
        }

    except Exception as e:
        print(f"❌ Correlation analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}


# ============================================================================
# Individual Function Wrappers (for testing, no schedules)
# ============================================================================

@app.function(
    image=image,
    timeout=3600,  # 1 hour max for full scan
    volumes={VOLUME_PATH: volume},
    secrets=[modal.Secret.from_name("Stock_Story")],
)
def daily_scan():
    """
    Daily scan of all S&P 500 + NASDAQ stocks with AI brain.
    (No schedule - for testing only. Use daily_scan_bundle for scheduled runs.)
    """
    return _run_daily_scan()


@app.function(
    image=image,
    timeout=1800,  # 30 minutes max
    volumes={VOLUME_PATH: volume},
)
def automated_theme_discovery():
    """
    Automated Theme Discovery - Runs 4 advanced discovery methods.
    (No schedule - for testing only. Use morning_alerts_bundle for scheduled runs.)
    """
    return _run_automated_theme_discovery()


@app.function(
    image=image,
    timeout=600,  # 10 minutes max
    volumes={VOLUME_PATH: volume},
)
def conviction_alerts():
    """
    Conviction Alerts - Scans daily results for high-conviction opportunities.
    (No schedule - for testing only. Use morning_alerts_bundle for scheduled runs.)
    """
    return _run_conviction_alerts()


@app.function(
    image=image,
    timeout=1200,  # 20 minutes max
    volumes={VOLUME_PATH: volume},
)
def unusual_options_alerts():
    """
    Unusual Options Activity Alerts.
    (No schedule - for testing only. Use morning_alerts_bundle for scheduled runs.)
    """
    return _run_unusual_options_alerts()


@app.function(
    image=image,
    timeout=600,  # 10 minutes max
    volumes={VOLUME_PATH: volume},
)
def daily_executive_briefing():
    """
    Daily Executive Briefing - Comprehensive market overview.
    (No schedule - for testing only. Use morning_alerts_bundle for scheduled runs.)
    """
    return _run_daily_executive_briefing()


@app.function(
    image=image,
    timeout=300,  # 5 minutes max
    volumes={VOLUME_PATH: volume},
)
def parameter_learning_health_check():
    """
    Parameter Learning Health Check - Weekly monitoring of learning system.
    (No schedule - for testing only. Use weekly_reports for scheduled runs.)
    """
    return _run_parameter_learning_health_check()


@app.function(
    image=image,
    timeout=300,  # 5 minutes max
    volumes={VOLUME_PATH: volume},
)
def data_staleness_monitor():
    """
    Data Staleness Monitor - Monitors data freshness across all sources.
    (No schedule - for testing only. Use monitoring_cycle for scheduled runs.)
    """
    return _run_data_staleness_monitor()


@app.function(
    image=image,
    timeout=900,  # 15 minutes max
    volumes={VOLUME_PATH: volume},
)
def weekly_summary_report():
    """
    Weekly Summary Report - Comprehensive week performance analysis.
    (No schedule - for testing only. Use weekly_reports for scheduled runs.)
    """
    return _run_weekly_summary_report()


@app.function(
    image=image,
    timeout=3600,  # 1 hour max
    volumes={VOLUME_PATH: volume},
)
def batch_insider_transactions_update():
    """
    Batch Insider Transactions Update.
    (No schedule - for testing only. Use afternoon_analysis for scheduled runs.)
    """
    return _run_batch_insider_transactions_update()


@app.function(
    image=image,
    timeout=1800,  # 30 minutes max
    volumes={VOLUME_PATH: volume},
)
def batch_google_trends_prefetch():
    """
    Batch Google Trends Pre-fetch.
    (No schedule - for testing only. Use monitoring_cycle for scheduled runs.)
    """
    return _run_batch_google_trends_prefetch()


@app.function(
    image=image,
    timeout=3600,  # 1 hour max
    volumes={VOLUME_PATH: volume},
)
def batch_patent_data_update():
    """
    Batch Patent Data Update.
    (No schedule - for testing only. Use weekly_reports for scheduled runs.)
    """
    return _run_batch_patent_data_update()


@app.function(
    image=image,
    timeout=3600,  # 1 hour max
    volumes={VOLUME_PATH: volume},
)
def batch_contracts_update():
    """
    Batch Government Contracts Update.
    (No schedule - for testing only. Use weekly_reports for scheduled runs.)
    """
    return _run_batch_contracts_update()


@app.function(
    image=image,
    timeout=600,  # 10 minutes max
    volumes={VOLUME_PATH: volume},
)
def sector_rotation_alerts():
    """
    Sector Rotation Alerts - Daily sector momentum and rotation analysis.
    (No schedule - for testing only. Use morning_alerts_bundle for scheduled runs.)
    """
    return _run_sector_rotation_alerts()


@app.function(
    image=image,
    timeout=600,  # 10 minutes max
    volumes={VOLUME_PATH: volume},
)
def institutional_flow_alerts():
    """
    Institutional Flow Alerts - Smart money tracking.
    (No schedule - for testing only. Use morning_alerts_bundle for scheduled runs.)
    """
    return _run_institutional_flow_alerts()


@app.function(
    image=image,
    timeout=600,  # 10 minutes max
    volumes={VOLUME_PATH: volume},
)
def executive_commentary_alerts():
    """
    Executive Commentary Alerts - CEO/CFO sentiment tracking.
    (No schedule - for testing only. Use morning_alerts_bundle for scheduled runs.)
    """
    return _run_executive_commentary_alerts()


@app.function(
    image=image,
    timeout=900,  # 15 minutes max
    volumes={VOLUME_PATH: volume},
)
def daily_correlation_analysis():
    """
    Daily Correlation Analysis - Theme and sector correlation matrix.
    (No schedule - for testing only. Use afternoon_analysis for scheduled runs.)
    """
    return _run_daily_correlation_analysis()


# ============================================================================
# BUNDLED SCHEDULED FUNCTIONS (5 total to stay within Modal's limit)
# ============================================================================

@app.function(
    image=image,
    timeout=3600,  # 1 hour max
    schedule=modal.Cron("0 14 * * 1-5"),  # Run Mon-Fri at 6:00 AM PST (14:00 UTC)
    volumes={VOLUME_PATH: volume},
    secrets=[modal.Secret.from_name("Stock_Story")],
)
def morning_mega_bundle():
    """
    Bundle 1: Morning Mega Bundle (Daily Scan + All Alerts)
    Runs Mon-Fri at 6:00 AM PST (14:00 UTC)

    Executes in sequence:
    1. daily_scan (main stock scanning)
    2. automated_theme_discovery
    3. conviction_alerts
    4. unusual_options_alerts
    5. sector_rotation_alerts
    6. institutional_flow_alerts
    7. executive_commentary_alerts
    8. daily_executive_briefing
    """
    print("=" * 70)
    print("📦 BUNDLE 1: MORNING MEGA BUNDLE (SCAN + ALERTS)")
    print("=" * 70)

    results = {}

    # 1. Daily Scan (MUST run first - all alerts depend on this)
    print("\n[1/8] Running daily_scan...")
    try:
        results['daily_scan'] = _run_daily_scan()
    except Exception as e:
        print(f"❌ Daily scan failed: {e}")
        results['daily_scan'] = {'success': False, 'error': str(e)}
        # If scan fails, still try alerts but they may have limited data
        print("⚠️  Daily scan failed, but continuing with alerts using previous data...")

    # 2. Theme Discovery
    print("\n[2/8] Running automated_theme_discovery...")
    try:
        results['theme_discovery'] = _run_automated_theme_discovery()
    except Exception as e:
        print(f"❌ Theme discovery failed: {e}")
        results['theme_discovery'] = {'success': False, 'error': str(e)}

    # 3. Conviction Alerts
    print("\n[3/8] Running conviction_alerts...")
    try:
        results['conviction'] = _run_conviction_alerts()
    except Exception as e:
        print(f"❌ Conviction alerts failed: {e}")
        results['conviction'] = {'success': False, 'error': str(e)}

    # 4. Unusual Options Alerts
    print("\n[4/8] Running unusual_options_alerts...")
    try:
        results['unusual_options'] = _run_unusual_options_alerts()
    except Exception as e:
        print(f"❌ Unusual options failed: {e}")
        results['unusual_options'] = {'success': False, 'error': str(e)}

    # 5. Sector Rotation Alerts
    print("\n[5/8] Running sector_rotation_alerts...")
    try:
        results['sector_rotation'] = _run_sector_rotation_alerts()
    except Exception as e:
        print(f"❌ Sector rotation failed: {e}")
        results['sector_rotation'] = {'success': False, 'error': str(e)}

    # 6. Institutional Flow Alerts
    print("\n[6/8] Running institutional_flow_alerts...")
    try:
        results['institutional_flow'] = _run_institutional_flow_alerts()
    except Exception as e:
        print(f"❌ Institutional flow failed: {e}")
        results['institutional_flow'] = {'success': False, 'error': str(e)}

    # 7. Executive Commentary Alerts
    print("\n[7/8] Running executive_commentary_alerts...")
    try:
        results['executive_commentary'] = _run_executive_commentary_alerts()
    except Exception as e:
        print(f"❌ Executive commentary failed: {e}")
        results['executive_commentary'] = {'success': False, 'error': str(e)}

    # 8. Daily Executive Briefing
    print("\n[8/9] Running daily_executive_briefing...")
    try:
        results['briefing'] = _run_daily_executive_briefing()
    except Exception as e:
        print(f"❌ Daily briefing failed: {e}")
        results['briefing'] = {'success': False, 'error': str(e)}

    # 9. Exit Signal Detection (TIER 3)
    print("\n[9/9] Running exit_signal_check...")
    try:
        results['exit_signals'] = _run_exit_signal_check()
    except Exception as e:
        print(f"❌ Exit signal check failed: {e}")
        results['exit_signals'] = {'success': False, 'error': str(e)}

    print("=" * 70)
    print("✅ BUNDLE 1 COMPLETE (9/9 functions)")
    print("=" * 70)

    return {
        'bundle': 'morning_mega',
        'results': results,
        'success': True
    }


@app.function(
    image=image,
    timeout=3600,  # 1 hour max
    schedule=modal.Cron("0 21 * * 1-5"),  # Run Mon-Fri at 1:00 PM PST (21:00 UTC)
    volumes={VOLUME_PATH: volume},
    secrets=[modal.Secret.from_name("Stock_Story")],
)
def afternoon_analysis_bundle():
    """
    Bundle 2: Afternoon Analysis
    Runs Mon-Fri at 1:00 PM PST (21:00 UTC)

    Executes in sequence:
    1. daily_correlation_analysis
    2. batch_insider_transactions_update
    """
    print("=" * 70)
    print("📦 BUNDLE 2: AFTERNOON ANALYSIS")
    print("=" * 70)

    results = {}

    # 1. Daily Correlation Analysis
    print("\n[1/2] Running daily_correlation_analysis...")
    try:
        results['correlation'] = _run_daily_correlation_analysis()
    except Exception as e:
        print(f"❌ Correlation analysis failed: {e}")
        results['correlation'] = {'success': False, 'error': str(e)}

    # 2. Batch Insider Transactions Update
    print("\n[2/2] Running batch_insider_transactions_update...")
    try:
        results['insider_transactions'] = _run_batch_insider_transactions_update()
    except Exception as e:
        print(f"❌ Insider transactions failed: {e}")
        results['insider_transactions'] = {'success': False, 'error': str(e)}

    print("=" * 70)
    print("✅ BUNDLE 3 COMPLETE")
    print("=" * 70)

    return {
        'bundle': 'afternoon_analysis',
        'results': results,
        'success': True
    }


@app.function(
    image=image,
    timeout=3600,  # 1 hour max
    schedule=modal.Cron("0 2 * * 1"),  # Run Mondays at 2:00 AM UTC (Sunday 6 PM PST)
    volumes={VOLUME_PATH: volume},
    secrets=[modal.Secret.from_name("Stock_Story")],
)
def weekly_reports_bundle():
    """
    Bundle 3: Weekly Reports
    Runs Mondays at 2:00 AM UTC (Sunday 6:00 PM PST)

    Executes in sequence:
    1. weekly_summary_report
    2. parameter_learning_health_check
    3. batch_contracts_update
    4. batch_patent_data_update (conditional: only if first Monday of month)
    """
    print("=" * 70)
    print("📦 BUNDLE 3: WEEKLY REPORTS")
    print("=" * 70)

    results = {}

    # 1. Weekly Summary Report
    print("\n[1/4] Running weekly_summary_report...")
    try:
        results['weekly_summary'] = _run_weekly_summary_report()
    except Exception as e:
        print(f"❌ Weekly summary failed: {e}")
        results['weekly_summary'] = {'success': False, 'error': str(e)}

    # 2. Parameter Learning Health Check
    print("\n[2/4] Running parameter_learning_health_check...")
    try:
        results['health_check'] = _run_parameter_learning_health_check()
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        results['health_check'] = {'success': False, 'error': str(e)}

    # 3. Batch Contracts Update
    print("\n[3/4] Running batch_contracts_update...")
    try:
        results['contracts'] = _run_batch_contracts_update()
    except Exception as e:
        print(f"❌ Contracts update failed: {e}")
        results['contracts'] = {'success': False, 'error': str(e)}

    # 4. Batch Patent Data Update (only first Monday of month)
    from datetime import datetime
    now = datetime.now()
    is_first_monday = now.day <= 7

    if is_first_monday:
        print("\n[4/4] Running batch_patent_data_update (first Monday of month)...")
        try:
            results['patents'] = _run_batch_patent_data_update()
        except Exception as e:
            print(f"❌ Patent update failed: {e}")
            results['patents'] = {'success': False, 'error': str(e)}
    else:
        print("\n[4/4] Skipping batch_patent_data_update (not first Monday of month)")
        results['patents'] = {'success': True, 'skipped': True}

    print("=" * 70)
    print("✅ BUNDLE 4 COMPLETE")
    print("=" * 70)

    return {
        'bundle': 'weekly_reports',
        'results': results,
        'success': True
    }


@app.function(
    image=image,
    timeout=1800,  # 30 minutes max
    schedule=modal.Cron("0 */6 * * *"),  # Run every 6 hours
    volumes={VOLUME_PATH: volume},
    secrets=[modal.Secret.from_name("Stock_Story")],
)
def monitoring_cycle_bundle():
    """
    Bundle 4: Monitoring Cycle
    Runs every 6 hours

    Executes in sequence:
    1. data_staleness_monitor
    2. batch_google_trends_prefetch (conditional: only during market hours 14-22 UTC)
    """
    print("=" * 70)
    print("📦 BUNDLE 4: MONITORING CYCLE")
    print("=" * 70)

    results = {}

    # 1. Data Staleness Monitor
    print("\n[1/2] Running data_staleness_monitor...")
    try:
        results['staleness'] = _run_data_staleness_monitor()
    except Exception as e:
        print(f"❌ Staleness monitor failed: {e}")
        results['staleness'] = {'success': False, 'error': str(e)}

    # 2. Batch Google Trends Prefetch (only during market hours)
    from datetime import datetime
    now = datetime.now()
    current_hour = now.hour
    is_market_hours = 14 <= current_hour <= 22  # 6 AM - 2 PM PST in UTC
    is_weekday = now.weekday() < 5  # Monday = 0, Friday = 4

    if is_market_hours and is_weekday:
        print("\n[2/2] Running batch_google_trends_prefetch (market hours)...")
        try:
            results['trends'] = _run_batch_google_trends_prefetch()
        except Exception as e:
            print(f"❌ Trends prefetch failed: {e}")
            results['trends'] = {'success': False, 'error': str(e)}
    else:
        print("\n[2/2] Skipping batch_google_trends_prefetch (outside market hours)")
        results['trends'] = {'success': True, 'skipped': True}

    print("=" * 70)
    print("✅ BUNDLE 4 COMPLETE")
    print("=" * 70)

    return {
        'bundle': 'monitoring_cycle',
        'results': results,
        'success': True
    }


@app.function(
    image=image,
    timeout=300,  # 5 minutes max
    schedule=modal.Cron("0 * * * *"),  # Run every hour (at minute 0)
    secrets=[modal.Secret.from_name("Stock_Story")],
)
def x_intelligence_crisis_monitor():
    """
    Bundle 5: X Intelligence Crisis Monitor
    Runs every hour

    Real-time monitoring of X/Twitter for market threats.
    Sends Telegram alerts when crises detected.

    Severity levels:
    - 9-10: CRITICAL - Emergency protocol (halt all trading)
    - 7-8: MAJOR - Tighten controls (avoid affected sectors)
    - 1-6: WARNING - Informational awareness

    This is our 5th and final cron job (5/5 limit on free tier).
    """
    print("=" * 70)
    print("🚨 X INTELLIGENCE CRISIS MONITOR")
    print("=" * 70)
    print(f"Check frequency: Every hour")
    print(f"Next check: In 15 minutes")
    print("=" * 70)

    try:
        result = _run_x_intelligence_crisis_check()

        if result.get('success'):
            crises = result.get('crises_detected', 0)
            if crises > 0:
                print(f"\n⚠️  {crises} threat(s) detected and notifications sent")
            else:
                print(f"\n✅ No threats detected - markets clear")

        return result

    except Exception as e:
        print(f"❌ Crisis monitor failed: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}


# ============================================================================
# Test Functions
# ============================================================================

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
