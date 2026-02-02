"""
Comprehensive API Connection Test
Tests all services that require API keys to ensure they're properly connected.
"""
import modal
import os
from datetime import datetime

app = modal.App("test-all-api-connections")

# Same image as main scanner
image = modal.Image.debian_slim(python_version="3.11").pip_install_from_requirements("requirements.txt").add_local_dir("src", remote_path="/root/src")

@app.function(
    image=image,
    secrets=[modal.Secret.from_name("Stock_Story")],
    timeout=300,
)
def test_all_apis():
    """Test all API connections."""
    import sys
    sys.path.insert(0, '/root')

    print("=" * 80)
    print("COMPREHENSIVE API CONNECTION TEST")
    print("=" * 80)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print()

    results = {}

    # =============================================================================
    # TEST 1: xAI API (X Intelligence)
    # =============================================================================
    print("=" * 80)
    print("TEST 1: xAI API Connection")
    print("=" * 80)

    xai_key = os.environ.get('XAI_API_KEY', '')
    print(f"XAI_API_KEY: {'✓ Found' if xai_key else '✗ Missing'} ({len(xai_key)} chars)")

    if xai_key:
        try:
            from src.services.ai_service import get_ai_service
            ai_service = get_ai_service()

            response = ai_service.call_xai(
                prompt="Say 'API connection successful'",
                max_tokens=50,
                temperature=0.1
            )

            if response and "successful" in response.lower():
                print("✓ xAI API: CONNECTED")
                results['xai'] = {'status': 'connected', 'response_length': len(response)}
            else:
                print(f"✗ xAI API: Response unexpected: {response}")
                results['xai'] = {'status': 'error', 'message': 'Unexpected response'}
        except Exception as e:
            print(f"✗ xAI API: FAILED - {e}")
            results['xai'] = {'status': 'failed', 'error': str(e)}
    else:
        print("✗ xAI API: API key not configured")
        results['xai'] = {'status': 'not_configured'}
    print()

    # =============================================================================
    # TEST 2: xAI SDK with X Search
    # =============================================================================
    print("=" * 80)
    print("TEST 2: xAI SDK with X Search")
    print("=" * 80)

    try:
        from xai_sdk import Client
        from xai_sdk.tools import x_search
        print("✓ xai_sdk package available")

        from src.ai.xai_x_intelligence_v2 import get_x_intelligence_v2
        x_intel = get_x_intelligence_v2()

        if x_intel and x_intel.available:
            print("✓ X Intelligence V2 initialized")

            # Quick test
            sentiments = x_intel.search_stock_sentiment(['AAPL'])
            if 'AAPL' in sentiments:
                print(f"✓ X Search: WORKING - Got sentiment for AAPL: {sentiments['AAPL'].get('sentiment', 'unknown')}")
                results['xai_sdk'] = {'status': 'connected', 'sentiment': sentiments['AAPL'].get('sentiment')}
            else:
                print("✗ X Search: No data returned")
                results['xai_sdk'] = {'status': 'no_data'}
        else:
            print("✗ X Intelligence V2 not available")
            results['xai_sdk'] = {'status': 'not_available'}
    except ImportError as e:
        print(f"✗ xai_sdk not installed: {e}")
        results['xai_sdk'] = {'status': 'not_installed', 'error': str(e)}
    except Exception as e:
        print(f"✗ X Intelligence V2 failed: {e}")
        results['xai_sdk'] = {'status': 'failed', 'error': str(e)}
    print()

    # =============================================================================
    # TEST 3: DeepSeek API
    # =============================================================================
    print("=" * 80)
    print("TEST 3: DeepSeek API Connection")
    print("=" * 80)

    deepseek_key = os.environ.get('DEEPSEEK_API_KEY', '')
    print(f"DEEPSEEK_API_KEY: {'✓ Found' if deepseek_key else '✗ Missing'} ({len(deepseek_key)} chars)")

    if deepseek_key:
        try:
            from src.services.ai_service import get_ai_service
            ai_service = get_ai_service()

            response = ai_service.call_deepseek(
                prompt="Say 'API connection successful'",
                max_tokens=50,
                temperature=0.1
            )

            if response and "successful" in response.lower():
                print("✓ DeepSeek API: CONNECTED")
                results['deepseek'] = {'status': 'connected', 'response_length': len(response)}
            else:
                print(f"✗ DeepSeek API: Response unexpected: {response}")
                results['deepseek'] = {'status': 'error', 'message': 'Unexpected response'}
        except Exception as e:
            print(f"✗ DeepSeek API: FAILED - {e}")
            results['deepseek'] = {'status': 'failed', 'error': str(e)}
    else:
        print("✗ DeepSeek API: API key not configured")
        results['deepseek'] = {'status': 'not_configured'}
    print()

    # =============================================================================
    # TEST 4: Polygon API
    # =============================================================================
    print("=" * 80)
    print("TEST 4: Polygon API Connection")
    print("=" * 80)

    polygon_key = os.environ.get('POLYGON_API_KEY', '')
    print(f"POLYGON_API_KEY: {'✓ Found' if polygon_key else '✗ Missing'} ({len(polygon_key)} chars)")

    if polygon_key:
        try:
            from src.data.polygon_provider import get_stock_data_sync

            data = get_stock_data_sync('AAPL')

            if data and 'price' in data:
                print(f"✓ Polygon API: CONNECTED - AAPL price: ${data['price']}")
                results['polygon'] = {'status': 'connected', 'sample_price': data['price']}
            else:
                print(f"✗ Polygon API: No data returned or missing price")
                results['polygon'] = {'status': 'no_data'}
        except Exception as e:
            print(f"✗ Polygon API: FAILED - {e}")
            results['polygon'] = {'status': 'failed', 'error': str(e)}
    else:
        print("✗ Polygon API: API key not configured")
        results['polygon'] = {'status': 'not_configured'}
    print()

    # =============================================================================
    # TEST 5: Telegram Bot
    # =============================================================================
    print("=" * 80)
    print("TEST 5: Telegram Bot Connection")
    print("=" * 80)

    telegram_token = os.environ.get('TELEGRAM_BOT_TOKEN', '')
    telegram_chat = os.environ.get('TELEGRAM_CHAT_ID', '')
    print(f"TELEGRAM_BOT_TOKEN: {'✓ Found' if telegram_token else '✗ Missing'} ({len(telegram_token)} chars)")
    print(f"TELEGRAM_CHAT_ID: {'✓ Found' if telegram_chat else '✗ Missing'} ({len(telegram_chat)} chars)")

    if telegram_token and telegram_chat:
        try:
            from src.notifications.notification_manager import get_notification_manager

            notif_manager = get_notification_manager()

            # Send test message
            result = notif_manager.send_test_message("API Connection Test - All systems checked ✓")

            if result.get('success'):
                print("✓ Telegram Bot: CONNECTED - Test message sent")
                results['telegram'] = {'status': 'connected', 'message_sent': True}
            else:
                print(f"✗ Telegram Bot: Failed to send - {result.get('error')}")
                results['telegram'] = {'status': 'failed', 'error': result.get('error')}
        except Exception as e:
            print(f"✗ Telegram Bot: FAILED - {e}")
            results['telegram'] = {'status': 'failed', 'error': str(e)}
    else:
        print("✗ Telegram Bot: Credentials not configured")
        results['telegram'] = {'status': 'not_configured'}
    print()

    # =============================================================================
    # TEST 6: SEC Edgar (no API key needed, but test connection)
    # =============================================================================
    print("=" * 80)
    print("TEST 6: SEC Edgar Connection")
    print("=" * 80)

    try:
        from src.data.sec_provider import get_company_filings_sync

        filings = get_company_filings_sync('AAPL', limit=1)

        if filings and len(filings) > 0:
            print(f"✓ SEC Edgar: CONNECTED - Found {len(filings)} filing(s) for AAPL")
            results['sec'] = {'status': 'connected', 'filings_count': len(filings)}
        else:
            print("✗ SEC Edgar: No filings returned")
            results['sec'] = {'status': 'no_data'}
    except Exception as e:
        print(f"✗ SEC Edgar: FAILED - {e}")
        results['sec'] = {'status': 'failed', 'error': str(e)}
    print()

    # =============================================================================
    # SUMMARY
    # =============================================================================
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)

    total = len(results)
    connected = sum(1 for r in results.values() if r.get('status') == 'connected')
    failed = sum(1 for r in results.values() if r.get('status') in ['failed', 'error', 'no_data'])
    not_configured = sum(1 for r in results.values() if r.get('status') in ['not_configured', 'not_installed', 'not_available'])

    print(f"Total APIs tested: {total}")
    print(f"✓ Connected: {connected}")
    print(f"✗ Failed: {failed}")
    print(f"⚠ Not configured: {not_configured}")
    print()

    print("Status by service:")
    for service, result in results.items():
        status = result.get('status', 'unknown')
        icon = '✓' if status == 'connected' else '✗' if status in ['failed', 'error'] else '⚠'
        print(f"  {icon} {service.upper()}: {status}")

    print("=" * 80)

    # Alert if critical services failed
    critical_services = ['xai', 'polygon', 'telegram']
    critical_failures = [s for s in critical_services if results.get(s, {}).get('status') not in ['connected']]

    if critical_failures:
        print()
        print("⚠️  WARNING: Critical services not connected:")
        for service in critical_failures:
            print(f"   - {service.upper()}: {results.get(service, {}).get('status', 'unknown')}")
        print()
    else:
        print()
        print("✅ All critical services are connected!")
        print()

    return results

@app.local_entrypoint()
def main():
    result = test_all_apis.remote()
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
