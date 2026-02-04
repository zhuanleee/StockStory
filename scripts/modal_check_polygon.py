"""Check Polygon subscription via Modal (uses stored secrets)."""

import modal

app = modal.App("polygon-check")
image = modal.Image.debian_slim().pip_install("requests")

@app.function(
    image=image,
    secrets=[modal.Secret.from_name("Stock_Story")],
    timeout=60,
)
def check_polygon_subscription():
    import os
    import requests

    api_key = os.environ.get('POLYGON_API_KEY')
    if not api_key:
        return "❌ POLYGON_API_KEY not found in Modal secrets"

    base_url = "https://api.polygon.io"
    results = []
    results.append("=" * 50)
    results.append("POLYGON.IO SUBSCRIPTION CHECK")
    results.append("=" * 50)

    # Test endpoints
    tests = [
        ("Basic API", f"{base_url}/v3/reference/tickers?limit=1&apiKey={api_key}"),
        ("Equity Options", f"{base_url}/v3/reference/options/contracts?underlying_ticker=SPY&limit=1&apiKey={api_key}"),
        ("Options Snapshots", f"{base_url}/v3/snapshot/options/SPY?limit=1&apiKey={api_key}"),
        ("Options Trades", f"{base_url}/v3/trades/O:SPY250207C00600000?limit=1&apiKey={api_key}"),
        ("Indices", f"{base_url}/v3/reference/tickers?market=indices&limit=3&apiKey={api_key}"),
        ("Forex", f"{base_url}/v3/reference/tickers?market=fx&limit=3&apiKey={api_key}"),
        ("Crypto", f"{base_url}/v3/reference/tickers?market=crypto&limit=3&apiKey={api_key}"),
        ("Historical Bars", f"{base_url}/v2/aggs/ticker/SPY/range/1/day/2025-01-01/2025-01-10?apiKey={api_key}"),
        ("Options Historical", f"{base_url}/v2/aggs/ticker/O:SPY250207C00600000/range/1/day/2025-01-01/2025-01-10?apiKey={api_key}"),
    ]

    for name, url in tests:
        try:
            r = requests.get(url, timeout=10)
            data = r.json()
            if r.status_code == 200:
                count = len(data.get('results', [])) if 'results' in data else 'N/A'
                results.append(f"✅ {name}: OK (results: {count})")
            elif r.status_code == 403:
                results.append(f"❌ {name}: NOT INCLUDED (403)")
            else:
                msg = data.get('message', data.get('error', str(r.status_code)))[:50]
                results.append(f"⚠️  {name}: {r.status_code} - {msg}")
        except Exception as e:
            results.append(f"❌ {name}: {str(e)[:50]}")

    # Check for futures specifically
    results.append("\n" + "-" * 50)
    results.append("FUTURES CHECK:")
    results.append("-" * 50)

    futures_tests = [
        ("Futures Tickers", f"{base_url}/v3/reference/tickers?market=futures&limit=5&apiKey={api_key}"),
        ("ES Futures", f"{base_url}/v2/aggs/ticker/ES/range/1/day/2025-01-01/2025-01-10?apiKey={api_key}"),
        ("Futures Options (ES)", f"{base_url}/v3/reference/options/contracts?underlying_ticker=ES&limit=1&apiKey={api_key}"),
    ]

    for name, url in futures_tests:
        try:
            r = requests.get(url, timeout=10)
            data = r.json()
            if r.status_code == 200 and data.get('results'):
                results.append(f"✅ {name}: OK")
                if 'ES' in name and data.get('results'):
                    sample = data['results'][0]
                    if isinstance(sample, dict):
                        results.append(f"   Sample: {sample.get('ticker', sample.get('T', 'N/A'))}")
            elif r.status_code == 403:
                results.append(f"❌ {name}: NOT INCLUDED")
            else:
                results.append(f"⚠️  {name}: {r.status_code}")
        except Exception as e:
            results.append(f"❌ {name}: {str(e)[:50]}")

    results.append("\n" + "=" * 50)
    return "\n".join(results)


@app.local_entrypoint()
def main():
    result = check_polygon_subscription.remote()
    print(result)
