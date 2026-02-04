"""Test futures options contracts via Polygon."""

import modal

app = modal.App("test-futures")
image = modal.Image.debian_slim().pip_install("requests")

@app.function(
    image=image,
    secrets=[modal.Secret.from_name("Stock_Story")],
    timeout=60,
)
def check_futures_contracts():
    import os
    import requests

    api_key = os.environ.get('POLYGON_API_KEY')
    base_url = "https://api.polygon.io"

    results = []
    results.append("=" * 60)
    results.append("FUTURES OPTIONS CONTRACTS CHECK")
    results.append("=" * 60)

    # Check what ES contracts exist
    tickers_to_test = ['ES', 'NQ', '/ES', '/NQ', 'ESH25', 'ESH26', 'NQH26']

    for ticker in tickers_to_test:
        results.append(f"\n--- Testing: {ticker} ---")
        try:
            # Get options contracts
            r = requests.get(
                f"{base_url}/v3/reference/options/contracts",
                params={
                    'underlying_ticker': ticker,
                    'limit': 5,
                    'apiKey': api_key
                },
                timeout=10
            )
            data = r.json()

            if r.status_code == 200 and data.get('results'):
                results.append(f"  ✅ Found {len(data['results'])} contracts")
                for c in data['results'][:3]:
                    results.append(f"     - {c.get('ticker')}: strike=${c.get('strike_price')}, exp={c.get('expiration_date')}")
            else:
                results.append(f"  ❌ No contracts found")
        except Exception as e:
            results.append(f"  ❌ Error: {str(e)[:50]}")

    # Also check tickers endpoint for futures
    results.append("\n--- Checking Futures Tickers ---")
    try:
        r = requests.get(
            f"{base_url}/v3/reference/tickers",
            params={
                'search': 'ES',
                'market': 'indices',
                'limit': 10,
                'apiKey': api_key
            },
            timeout=10
        )
        data = r.json()
        if r.status_code == 200 and data.get('results'):
            for t in data['results'][:5]:
                results.append(f"  - {t.get('ticker')}: {t.get('name')}")
    except Exception as e:
        results.append(f"  ❌ Error: {str(e)[:50]}")

    # Check for actual futures
    results.append("\n--- Checking Futures Market ---")
    try:
        r = requests.get(
            f"{base_url}/v3/reference/tickers",
            params={
                'search': 'SP 500',
                'limit': 10,
                'apiKey': api_key
            },
            timeout=10
        )
        data = r.json()
        if r.status_code == 200 and data.get('results'):
            for t in data['results'][:5]:
                results.append(f"  - {t.get('ticker')}: {t.get('name')} (market={t.get('market')})")
    except Exception as e:
        results.append(f"  ❌ Error: {str(e)[:50]}")

    return "\n".join(results)


@app.local_entrypoint()
def main():
    result = check_futures_contracts.remote()
    print(result)
