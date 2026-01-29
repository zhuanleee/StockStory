#!/usr/bin/env python3
"""
DigitalOcean Deployment Verification
====================================
Verify DigitalOcean deployment is working correctly.
"""

import requests
import sys
from typing import Optional

def test_health_endpoint(app_url: str) -> bool:
    """Test the /health endpoint."""
    print("🔍 Testing Health Endpoint...")
    print("=" * 60)

    url = f"{app_url}/health"

    try:
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            data = response.json()
            print(f"  ✓ Status: {data.get('status')}")
            print(f"  ✓ Timestamp: {data.get('timestamp')}")

            components = data.get('components', {})
            if components:
                print(f"  ✓ Components:")
                for name, status in components.items():
                    print(f"    - {name}: {status}")

            return True
        else:
            print(f"  ✗ HTTP {response.status_code}: {response.text}")
            return False

    except requests.exceptions.ConnectionError:
        print(f"  ✗ Connection error - app may still be deploying")
        return False
    except requests.exceptions.Timeout:
        print(f"  ✗ Timeout - app not responding")
        return False
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def test_dashboard(app_url: str) -> bool:
    """Test dashboard loads."""
    print("\n\n🔍 Testing Dashboard...")
    print("=" * 60)

    try:
        response = requests.get(app_url, timeout=10)

        if response.status_code == 200:
            content = response.text

            # Check for key dashboard elements
            checks = {
                'Intelligence Tab': 'data-tab="intelligence"',
                'Chart.js': 'chart.js',
                'API Base URL': 'const API_BASE',
                'X Sentiment': 'xSentimentChart',
                'Google Trends': 'trendsChart',
            }

            all_present = True
            for name, pattern in checks.items():
                if pattern in content:
                    print(f"  ✓ {name}")
                else:
                    print(f"  ✗ {name} - MISSING")
                    all_present = False

            return all_present
        else:
            print(f"  ✗ HTTP {response.status_code}")
            return False

    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def test_api_endpoint(app_url: str, endpoint: str) -> bool:
    """Test a specific API endpoint."""
    url = f"{app_url}{endpoint}"

    try:
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                return True

        return False

    except:
        return False


def test_api_endpoints(app_url: str) -> bool:
    """Test key API endpoints."""
    print("\n\n🔍 Testing API Endpoints...")
    print("=" * 60)

    endpoints = [
        '/api/scan/results',
        '/api/intelligence/summary',
        '/api/intelligence/x-sentiment',
        '/api/intelligence/google-trends',
        '/api/system/status',
    ]

    results = {}
    for endpoint in endpoints:
        result = test_api_endpoint(app_url, endpoint)
        results[endpoint] = result
        status = "✓" if result else "✗"
        print(f"  {status} {endpoint}")

    return all(results.values())


def verify_telegram_webhook(bot_token: str) -> Optional[str]:
    """Verify Telegram webhook is configured."""
    print("\n\n🔍 Verifying Telegram Webhook...")
    print("=" * 60)

    url = f"https://api.telegram.org/bot{bot_token}/getWebhookInfo"

    try:
        response = requests.get(url, timeout=10)
        data = response.json()

        if data.get('ok'):
            result = data.get('result', {})
            webhook_url = result.get('url', '')

            if webhook_url:
                print(f"  ✓ Webhook URL: {webhook_url}")
                print(f"  ✓ Pending updates: {result.get('pending_update_count', 0)}")
                print(f"  ✓ Max connections: {result.get('max_connections', 40)}")

                if 'digitalocean.app' in webhook_url:
                    print(f"  ✓ Webhook points to DigitalOcean ✅")
                    return webhook_url
                else:
                    print(f"  ⚠️  Webhook not pointing to DigitalOcean")
                    return webhook_url
            else:
                print(f"  ✗ No webhook configured")
                return None
        else:
            print(f"  ✗ Error: {data.get('description')}")
            return None

    except Exception as e:
        print(f"  ✗ Error: {e}")
        return None


def main():
    """Run all verification checks."""
    print("\n" + "=" * 60)
    print("  DIGITALOCEAN DEPLOYMENT VERIFICATION")
    print("=" * 60 + "\n")

    # Get app URL from user
    print("Enter your DigitalOcean app URL:")
    print("Example: https://stock-scanner-bot-a4b2c.ondigitalocean.app")
    app_url = input("\nApp URL: ").strip()

    # Remove trailing slash
    if app_url.endswith('/'):
        app_url = app_url[:-1]

    # Validate URL format
    if not app_url.startswith('https://'):
        print("\n❌ Invalid URL format. Must start with https://")
        return 1

    if 'ondigitalocean.app' not in app_url:
        print("\n⚠️  Warning: URL doesn't look like a DigitalOcean app URL")
        confirm = input("Continue anyway? (y/n): ").strip().lower()
        if confirm != 'y':
            return 1

    # Run tests
    results = {}

    results['health'] = test_health_endpoint(app_url)
    results['dashboard'] = test_dashboard(app_url)
    results['api'] = test_api_endpoints(app_url)

    # Telegram webhook check
    bot_token = "7626822299:AAHVNKOLIVelbBwOEO2J2aE_6D34Ml0RuuM"
    webhook_url = verify_telegram_webhook(bot_token)
    results['webhook'] = webhook_url is not None and 'digitalocean.app' in webhook_url

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
        print("  ✅ DEPLOYMENT SUCCESSFUL")
        print("=" * 60)
        print(f"\n✨ Your bot is live on DigitalOcean!")
        print(f"  • Dashboard: {app_url}")
        print(f"  • Health: {app_url}/health")
        print(f"  • Webhook: {webhook_url if webhook_url else 'Not configured'}")
        print(f"\n🤖 Test your bot:")
        print(f"  Send /help to @Stocks_Story_Bot")
        print(f"  Send /scan NVDA to test scanning")
        print(f"  Send /earnings NVDA to test intelligence")
        return 0
    else:
        print("  ⚠️  SOME CHECKS FAILED")
        print("=" * 60)

        if not results['health']:
            print("\n❌ Health check failed:")
            print("  • App may still be deploying (wait 2-3 min)")
            print("  • Check DigitalOcean logs for errors")
            print("  • Verify environment variables are set")

        if not results['dashboard']:
            print("\n❌ Dashboard check failed:")
            print("  • Static files may not be served correctly")
            print("  • Check build logs in DigitalOcean")

        if not results['api']:
            print("\n❌ API check failed:")
            print("  • Backend may not be running")
            print("  • Check runtime logs in DigitalOcean")
            print("  • Verify Python dependencies installed")

        if not results['webhook']:
            print("\n❌ Webhook check failed:")
            print("  • Run webhook configuration command:")
            print(f'    curl -X POST "https://api.telegram.org/bot{bot_token}/setWebhook" \\')
            print(f'      -d \'{{"url": "{app_url}/webhook"}}\'')

        return 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n👋 Verification cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        sys.exit(1)
