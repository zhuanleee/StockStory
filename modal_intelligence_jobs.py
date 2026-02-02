"""
Intelligence Jobs for Modal - Tier 3 Features

New intelligence features that run on schedules:
- Exit Signal Detection (daily, morning)
- Meme Stock Detection (daily, afternoon)
- Sector Rotation (weekly)
- Earnings Reactions (as needed)

These are bundled with existing cron jobs to stay within 5-job limit.
"""

import modal
from modal_scanner import image, app


# ============================================================================
# EXIT SIGNAL DETECTION (Daily Morning - 6 AM PST / 14:00 UTC)
# ============================================================================

@app.function(
    image=image,
    timeout=600,  # 10 minutes
    secrets=[modal.Secret.from_name("Stock_Story")],
)
def daily_exit_signal_check():
    """
    TIER 3: Exit Signal Detection

    Checks all holdings for exit signals before market open.
    Sends Telegram alerts for positions that should be exited.

    Run time: Daily at 6 AM PST (before market opens)
    Cost: ~$0.01/day = $0.27/month
    """
    import sys
    sys.path.insert(0, '/root')

    print("=" * 70)
    print("🛡️  TIER 3: EXIT SIGNAL DETECTION")
    print("=" * 70)
    print("Checking holdings for negative sentiment & red flags...")
    print("=" * 70)

    try:
        from src.intelligence.exit_signal_detector import get_exit_signal_detector
        from src.notifications.notification_manager import get_notification_manager, NotificationPriority

        detector = get_exit_signal_detector()
        notif_manager = get_notification_manager()

        # Get current holdings (you'll need to implement get_holdings)
        # For now, use a sample watchlist
        holdings = _get_current_holdings()

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
                'exit_signals': 0,
                'status': 'all_clear'
            }

        # Send notifications for exit signals
        print(f"⚠️  {len(exit_signals)} exit signal(s) detected!")

        for ticker, signal in exit_signals.items():
            severity = signal['severity']
            action = signal['action']

            print(f"\n🚨 {ticker}:")
            print(f"   Signal: {signal['signal_type']}")
            print(f"   Severity: {severity}")
            print(f"   Action: {action}")
            print(f"   Reason: {signal['reason']}")

            # Send Telegram alert
            alert_type = 'position_warning' if severity == 'MEDIUM' else 'position_alert'
            priority = NotificationPriority.CRITICAL if severity == 'CRITICAL' else NotificationPriority.HIGH

            try:
                notif_manager.send_alert(
                    alert_type=alert_type,
                    data={
                        'ticker': ticker,
                        'signal_type': signal['signal_type'],
                        'severity': severity,
                        'reason': signal['reason'],
                        'action': action,
                        'sentiment_score': signal.get('sentiment_score', 0),
                        'confidence': signal.get('confidence', 0),
                        'web_verified': signal.get('web_verified', False)
                    },
                    priority=priority
                )
                print(f"   ✓ Alert sent")
            except Exception as e:
                print(f"   ✗ Alert failed: {e}")

        # Get summary
        summary = detector.get_summary(exit_signals)

        print("\n" + "=" * 70)
        print("EXIT SIGNAL SUMMARY:")
        print(f"  Holdings checked: {summary['total_holdings_checked']}")
        print(f"  Exit signals: {summary['exit_signals_detected']}")
        print(f"  Critical: {summary['critical']}")
        print(f"  High: {summary['high']}")
        print(f"  Medium: {summary['medium']}")
        if summary['tickers_to_exit']:
            print(f"  IMMEDIATE EXIT: {', '.join(summary['tickers_to_exit'])}")
        if summary['tickers_to_reduce']:
            print(f"  Consider exit: {', '.join(summary['tickers_to_reduce'])}")
        print("=" * 70)

        return {
            'success': True,
            'holdings_checked': len(holdings),
            'exit_signals_detected': len(exit_signals),
            'critical': summary['critical'],
            'high': summary['high'],
            'medium': summary['medium'],
            'tickers_to_exit': summary['tickers_to_exit']
        }

    except Exception as e:
        print(f"❌ Exit signal check failed: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}


# ============================================================================
# MEME STOCK DETECTION (Daily Afternoon - 2 PM PST / 22:00 UTC)
# ============================================================================

@app.function(
    image=image,
    timeout=900,  # 15 minutes
    secrets=[modal.Secret.from_name("Stock_Story")],
)
def daily_meme_stock_scan():
    """
    TIER 3: Meme Stock Detection

    Scans universe for stocks showing viral momentum on X.
    Sends alerts for early entry opportunities.

    Run time: Daily at 2 PM PST (catch afternoon momentum)
    Cost: ~$0.03/day = $0.90/month
    """
    import sys
    sys.path.insert(0, '/root')

    print("=" * 70)
    print("🚀 TIER 3: MEME STOCK DETECTION")
    print("=" * 70)
    print("Scanning for viral momentum on X/Twitter...")
    print("=" * 70)

    try:
        from src.intelligence.meme_stock_detector import get_meme_stock_detector
        from src.notifications.notification_manager import get_notification_manager, NotificationPriority

        detector = get_meme_stock_detector()
        notif_manager = get_notification_manager()

        # Get scan universe (top liquid stocks)
        universe = _get_scan_universe()

        print(f"Scanning {len(universe)} tickers...")

        # Scan for meme stocks
        candidates = detector.scan_universe(universe, top_n=10)

        if not candidates:
            print("✅ No unusual viral activity detected")
            return {
                'success': True,
                'tickers_scanned': len(universe),
                'meme_stocks_found': 0,
                'status': 'normal_activity'
            }

        print(f"🎯 Found {len(candidates)} stocks with viral momentum!")

        # Send alerts for top candidates
        for candidate in candidates[:5]:  # Alert on top 5
            ticker = candidate['ticker']
            score = candidate['meme_score']

            print(f"\n🔥 {ticker}:")
            print(f"   Meme Score: {score}/10")
            print(f"   Mentions/hr: {candidate['mentions_per_hour']}")
            print(f"   Sentiment: {candidate['sentiment']} ({candidate['sentiment_score']})")

            if score >= 7.0:  # High viral potential
                print(f"   🚨 HIGH VIRAL POTENTIAL - Early entry opportunity!")

                try:
                    notif_manager.send_alert(
                        alert_type='opportunity',
                        data={
                            'ticker': ticker,
                            'opportunity_type': 'MEME_STOCK',
                            'meme_score': score,
                            'mentions_per_hour': candidate['mentions_per_hour'],
                            'sentiment': candidate['sentiment'],
                            'sentiment_score': candidate['sentiment_score'],
                            'has_meme_keywords': candidate['has_meme_keywords'],
                            'recommendation': 'WATCH' if score < 8 else 'STRONG_BUY'
                        },
                        priority=NotificationPriority.HIGH if score >= 8 else NotificationPriority.NORMAL
                    )
                    print(f"   ✓ Alert sent")
                except Exception as e:
                    print(f"   ✗ Alert failed: {e}")

        print("\n" + "=" * 70)
        print("MEME STOCK SCAN SUMMARY:")
        print(f"  Tickers scanned: {len(universe)}")
        print(f"  Viral candidates: {len(candidates)}")
        print(f"  Top 3: {', '.join([c['ticker'] for c in candidates[:3]])}")
        print("=" * 70)

        return {
            'success': True,
            'tickers_scanned': len(universe),
            'meme_stocks_found': len(candidates),
            'top_candidates': [c['ticker'] for c in candidates[:5]],
            'highest_score': candidates[0]['meme_score'] if candidates else 0
        }

    except Exception as e:
        print(f"❌ Meme stock scan failed: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}


# ============================================================================
# SECTOR ROTATION (Weekly - Sunday 8 PM PST / Monday 04:00 UTC)
# ============================================================================

@app.function(
    image=image,
    timeout=300,  # 5 minutes
    secrets=[modal.Secret.from_name("Stock_Story")],
)
def weekly_sector_rotation_analysis():
    """
    TIER 3: Sector Rotation Analysis

    Analyzes sentiment across all sectors to detect rotation.
    Sends weekly sector strength report.

    Run time: Weekly on Sunday evening
    Cost: ~$0.01/week = $0.04/month
    """
    import sys
    sys.path.insert(0, '/root')

    print("=" * 70)
    print("📊 TIER 3: SECTOR ROTATION ANALYSIS")
    print("=" * 70)
    print("Analyzing sector sentiment for rotation signals...")
    print("=" * 70)

    try:
        from src.intelligence.sector_rotation_tracker import get_sector_rotation_tracker
        from src.notifications.notification_manager import get_notification_manager, NotificationPriority

        tracker = get_sector_rotation_tracker()
        notif_manager = get_notification_manager()

        # Analyze all sectors
        sector_analysis = tracker.analyze_sectors()

        if not sector_analysis:
            print("✗ Sector analysis failed")
            return {'success': False, 'error': 'No sector data'}

        # Get top and bottom sectors
        top_sectors = tracker.get_top_sectors(sector_analysis, n=3)
        bottom_sectors = tracker.get_bottom_sectors(sector_analysis, n=3)

        print("\n" + "=" * 70)
        print("SECTOR ROTATION SIGNALS:")
        print("=" * 70)

        print("\n🟢 STRONGEST SECTORS (Overweight):")
        for sector in top_sectors:
            data = sector_analysis[sector]
            print(f"   {sector}: {data['avg_sentiment']:.1f} ({data['momentum']}) - {data['rotation_signal']}")

        print("\n🔴 WEAKEST SECTORS (Underweight):")
        for sector in bottom_sectors:
            data = sector_analysis[sector]
            print(f"   {sector}: {data['avg_sentiment']:.1f} ({data['momentum']}) - {data['rotation_signal']}")

        # Send weekly report
        try:
            notif_manager.send_alert(
                alert_type='weekly_report',
                data={
                    'report_type': 'SECTOR_ROTATION',
                    'top_sectors': top_sectors,
                    'bottom_sectors': bottom_sectors,
                    'sector_data': sector_analysis
                },
                priority=NotificationPriority.LOW
            )
            print("\n✓ Weekly report sent")
        except Exception as e:
            print(f"\n✗ Report failed: {e}")

        print("=" * 70)

        return {
            'success': True,
            'sectors_analyzed': len(sector_analysis),
            'top_sectors': top_sectors,
            'bottom_sectors': bottom_sectors
        }

    except Exception as e:
        print(f"❌ Sector rotation analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _get_current_holdings() -> list:
    """Get current holdings (implement based on your portfolio tracking)."""
    # TODO: Implement actual holdings retrieval
    # For now, return sample watchlist
    return ['NVDA', 'TSLA', 'AAPL', 'GOOGL', 'META']


def _get_scan_universe() -> list:
    """Get universe for meme stock scanning."""
    # Return top 150 liquid stocks
    return [
        # Tech
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'AVGO', 'ORCL', 'CSCO',
        # Finance
        'JPM', 'BAC', 'WFC', 'GS', 'MS', 'C', 'BLK', 'SCHW', 'AXP', 'USB',
        # Healthcare
        'JNJ', 'UNH', 'LLY', 'ABBV', 'MRK', 'PFE', 'TMO', 'ABT', 'DHR', 'BMY',
        # Consumer
        'HD', 'MCD', 'NKE', 'SBUX', 'TGT', 'LOW', 'TJX', 'CMG', 'MAR', 'BKNG',
        # Energy
        'XOM', 'CVX', 'COP', 'SLB', 'EOG', 'MPC', 'PSX', 'VLO', 'OXY', 'HAL',
        # Add 100 more liquid stocks
        # ... (you can expand this list)
    ][:150]
