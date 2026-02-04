#!/usr/bin/env python3
"""Check Polygon.io subscription tier and available data."""

import os
import requests

def check_subscription():
    api_key = os.environ.get('POLYGON_API_KEY')

    if not api_key:
        print("❌ POLYGON_API_KEY not set")
        print("\nRun with: POLYGON_API_KEY=your_key python scripts/check_polygon_subscription.py")
        return

    base_url = "https://api.polygon.io"
    headers = {"Authorization": f"Bearer {api_key}"}

    print("=" * 60)
    print("POLYGON.IO SUBSCRIPTION CHECK")
    print("=" * 60)

    # 1. Check basic API access
    print("\n📊 Testing API Access...")
    try:
        r = requests.get(f"{base_url}/v3/reference/tickers?limit=1&apiKey={api_key}", timeout=10)
        if r.status_code == 200:
            print("   ✅ Basic API: OK")
        else:
            print(f"   ❌ Basic API: {r.status_code} - {r.text[:100]}")
    except Exception as e:
        print(f"   ❌ Basic API: {e}")

    # 2. Check equity options access
    print("\n📈 Testing Equity Options...")
    try:
        r = requests.get(f"{base_url}/v3/reference/options/contracts?underlying_ticker=SPY&limit=1&apiKey={api_key}", timeout=10)
        data = r.json()
        if r.status_code == 200 and data.get('results'):
            print("   ✅ Equity Options: OK")
            print(f"      Sample: {data['results'][0].get('ticker', 'N/A')}")
        elif r.status_code == 403:
            print("   ❌ Equity Options: Not included in subscription")
        else:
            print(f"   ⚠️  Equity Options: {r.status_code}")
    except Exception as e:
        print(f"   ❌ Equity Options: {e}")

    # 3. Check futures access
    print("\n📉 Testing Futures...")
    try:
        r = requests.get(f"{base_url}/v3/reference/tickers?market=indices&type=INDEX&limit=5&apiKey={api_key}", timeout=10)
        data = r.json()
        if r.status_code == 200:
            print("   ✅ Indices: OK")
        else:
            print(f"   ⚠️  Indices: {r.status_code}")
    except Exception as e:
        print(f"   ❌ Indices: {e}")

    # Try futures market
    try:
        r = requests.get(f"{base_url}/v3/reference/tickers?market=fx&limit=3&apiKey={api_key}", timeout=10)
        data = r.json()
        if r.status_code == 200 and data.get('results'):
            print("   ✅ Forex: OK")
        else:
            print(f"   ⚠️  Forex: {r.status_code}")
    except Exception as e:
        print(f"   ❌ Forex: {e}")

    # Try crypto
    try:
        r = requests.get(f"{base_url}/v3/reference/tickers?market=crypto&limit=3&apiKey={api_key}", timeout=10)
        data = r.json()
        if r.status_code == 200 and data.get('results'):
            print("   ✅ Crypto: OK")
        else:
            print(f"   ⚠️  Crypto: {r.status_code}")
    except Exception as e:
        print(f"   ❌ Crypto: {e}")

    # 4. Check options snapshots (real-time)
    print("\n⚡ Testing Real-time Options Data...")
    try:
        r = requests.get(f"{base_url}/v3/snapshot/options/SPY?limit=1&apiKey={api_key}", timeout=10)
        data = r.json()
        if r.status_code == 200 and data.get('results'):
            print("   ✅ Options Snapshots: OK (real-time)")
        elif r.status_code == 403:
            print("   ❌ Options Snapshots: Not included (need Options add-on)")
        else:
            print(f"   ⚠️  Options Snapshots: {r.status_code}")
    except Exception as e:
        print(f"   ❌ Options Snapshots: {e}")

    # 5. Check options trades (real-time trades)
    print("\n💹 Testing Options Trades...")
    try:
        r = requests.get(f"{base_url}/v3/trades/O:SPY250207C00600000?limit=1&apiKey={api_key}", timeout=10)
        data = r.json()
        if r.status_code == 200:
            print("   ✅ Options Trades: OK")
        elif r.status_code == 403:
            print("   ❌ Options Trades: Not included")
        else:
            print(f"   ⚠️  Options Trades: {r.status_code}")
    except Exception as e:
        print(f"   ❌ Options Trades: {e}")

    # 6. Check aggregates (historical bars)
    print("\n📊 Testing Historical Data...")
    try:
        r = requests.get(f"{base_url}/v2/aggs/ticker/SPY/range/1/day/2025-01-01/2025-01-10?apiKey={api_key}", timeout=10)
        data = r.json()
        if r.status_code == 200 and data.get('results'):
            print("   ✅ Historical Bars: OK")
        else:
            print(f"   ⚠️  Historical Bars: {r.status_code}")
    except Exception as e:
        print(f"   ❌ Historical Bars: {e}")

    # 7. Check options aggregates
    print("\n📈 Testing Options Historical...")
    try:
        r = requests.get(f"{base_url}/v2/aggs/ticker/O:SPY250207C00600000/range/1/day/2025-01-01/2025-01-10?apiKey={api_key}", timeout=10)
        data = r.json()
        if r.status_code == 200:
            print("   ✅ Options Historical: OK")
        elif r.status_code == 403:
            print("   ❌ Options Historical: Not included")
        else:
            print(f"   ⚠️  Options Historical: {r.status_code}")
    except Exception as e:
        print(f"   ❌ Options Historical: {e}")

    print("\n" + "=" * 60)
    print("SUBSCRIPTION TIER ESTIMATE:")
    print("=" * 60)
    print("""
Based on the tests above:
- Stocks Starter ($29/mo): Basic stocks only
- Stocks Developer ($79/mo): + Real-time stocks
- Stocks Advanced ($199/mo): + Options contracts reference
- Options ($199/mo add-on): + Real-time options, snapshots, trades
- Business ($499/mo+): Full access including futures

Futures options require Business tier or specific add-on.
    """)

if __name__ == "__main__":
    check_subscription()
