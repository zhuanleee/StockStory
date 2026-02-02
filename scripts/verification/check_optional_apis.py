"""
Check optional API keys in Stock_Story secret
"""
import modal
import os

app = modal.App("check-optional-apis")
image = modal.Image.debian_slim(python_version="3.11")

@app.function(
    image=image,
    secrets=[modal.Secret.from_name("Stock_Story")],
    timeout=30,
)
def check_optional_apis():
    """Check if optional API keys are configured."""

    print("=" * 80)
    print("OPTIONAL API KEYS CHECK")
    print("=" * 80)
    print()

    optional_apis = {
        'ALPHA_VANTAGE_API_KEY': 'Earnings transcripts',
        'FINNHUB_API_KEY': 'Alternative stock data',
        'PATENTSVIEW_API_KEY': 'Patent tracking',
    }

    configured = []
    missing = []

    for key, description in optional_apis.items():
        value = os.environ.get(key, '')

        if value:
            print(f"✓ {key:25} ({len(value)} chars) - {description}")
            configured.append(key)
        else:
            print(f"✗ {key:25} NOT SET - {description}")
            missing.append(key)

    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Configured: {len(configured)}/3")
    print(f"Missing: {len(missing)}/3")
    print()

    if missing:
        print("⚠️  MISSING OPTIONAL APIs:")
        for key in missing:
            print(f"   - {key}: {optional_apis[key]}")
        print()
        print("IMPACT:")
        print("   - System will work without these")
        print("   - Some features may be limited:")
        if 'ALPHA_VANTAGE_API_KEY' in missing:
            print("     • No earnings call transcripts")
        if 'FINNHUB_API_KEY' in missing:
            print("     • Limited alternative data sources")
        if 'PATENTSVIEW_API_KEY' in missing:
            print("     • No patent tracking")
        print()
        print("Current primary data source: Polygon API (✓ Connected)")
    else:
        print("✅ All optional APIs are configured!")

    print("=" * 80)

    return {
        'configured': configured,
        'missing': missing,
        'total': len(optional_apis)
    }

@app.local_entrypoint()
def main():
    result = check_optional_apis.remote()
    print()
    print(f"Result: {result}")
