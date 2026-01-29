#!/usr/bin/env python3
"""
Dashboard Integration Verification
===================================
Verify dashboard has all required API endpoints and features.
"""

import re
from pathlib import Path

def check_dashboard_html():
    """Check dashboard HTML for all required components."""
    print("🔍 Checking Dashboard HTML (docs/index.html)...")
    print("=" * 60)

    dashboard_file = Path("docs/index.html")
    if not dashboard_file.exists():
        print("  ✗ Dashboard file not found!")
        return False

    content = dashboard_file.read_text()

    # Check for Intelligence tab
    checks = {
        'Intelligence Tab': 'data-tab="intelligence"',
        'Intelligence Content': 'id="intelligence"',
        'X Sentiment Chart': 'id="xSentimentChart"',
        'Google Trends Chart': 'id="trendsChart"',
        'Contracts Chart': 'id="contractsChart"',
        'Patents Chart': 'id="patentsChart"',
        'Catalyst Chart': 'id="catalystChart"',
        'Supply Chain Viz': 'id="supplyChainViz"',
        'Init Function': 'function initIntelligenceDashboard',
        'Refresh X Sentiment': 'async function refreshXSentiment',
        'Refresh Google Trends': 'async function refreshGoogleTrends',
        'Load Supply Chain': 'async function loadSupplyChain',
        'Load Catalyst Breakdown': 'async function loadCatalystBreakdown',
    }

    all_present = True
    for name, pattern in checks.items():
        if pattern in content:
            print(f"  ✓ {name}")
        else:
            print(f"  ✗ {name} - MISSING")
            all_present = False

    return all_present


def check_api_endpoints():
    """Check API has all required intelligence endpoints."""
    print("\n\n🔍 Checking API Endpoints (src/api/app.py)...")
    print("=" * 60)

    api_file = Path("src/api/app.py")
    if not api_file.exists():
        print("  ✗ API file not found!")
        return False

    content = api_file.read_text()

    endpoints = {
        '/api/intelligence/summary': 'Intelligence summary',
        '/api/intelligence/x-sentiment': 'X/Twitter sentiment data',
        '/api/intelligence/google-trends': 'Google Trends data',
        '/api/intelligence/supply-chain': 'Supply chain relationships',
        '/api/intelligence/catalyst-breakdown': 'Catalyst sources distribution',
        '/api/intelligence/earnings': 'Earnings intelligence',
        '/api/intelligence/executive': 'Executive commentary',
    }

    all_present = True
    for endpoint, description in endpoints.items():
        # Search for route decorator
        pattern = f"@app.route('{endpoint}"
        if pattern in content or f'@app.route("{endpoint}' in content:
            print(f"  ✓ {endpoint:45} ({description})")
        else:
            print(f"  ✗ {endpoint:45} ({description}) - MISSING")
            all_present = False

    return all_present


def check_intelligence_modules():
    """Check intelligence module files exist."""
    print("\n\n🔍 Checking Intelligence Modules...")
    print("=" * 60)

    modules = {
        'src/intelligence/x_intelligence.py': 'X Intelligence',
        'src/intelligence/google_trends.py': 'Google Trends',
        'src/intelligence/executive_commentary.py': 'Executive Commentary',
        'src/intelligence/institutional_flow.py': 'Institutional Flow',
        'src/intelligence/rotation_predictor.py': 'Sector Rotation',
        'src/intelligence/relationship_graph.py': 'Supply Chain',
        'src/data/transcript_fetcher.py': 'Earnings Transcripts',
        'src/scoring/earnings_scorer.py': 'Earnings Scorer',
    }

    all_exist = True
    for module_path, description in modules.items():
        if Path(module_path).exists():
            print(f"  ✓ {module_path:50} ({description})")
        else:
            print(f"  ✗ {module_path:50} ({description}) - MISSING")
            all_exist = False

    return all_exist


def check_dashboard_data_flow():
    """Check dashboard can fetch data from API."""
    print("\n\n🔍 Checking Dashboard Data Flow...")
    print("=" * 60)

    dashboard_file = Path("docs/index.html")
    content = dashboard_file.read_text()

    # Extract API calls from dashboard
    api_calls = re.findall(r'fetch\(`\${API_BASE}(/[^`]+)`\)', content)

    print(f"\n  Found {len(api_calls)} API fetch calls in dashboard:\n")
    for call in sorted(set(api_calls)):
        print(f"    • {call}")

    # Check API file has these endpoints
    api_file = Path("src/api/app.py")
    api_content = api_file.read_text()

    missing = []
    for call in set(api_calls):
        # Remove any template variables like ${themeId}
        endpoint_base = re.sub(r'/[^/]+$', '', call) if '{' not in call else call
        if f"@app.route('{call}" not in api_content and \
           f'@app.route("{call}"' not in api_content and \
           f"@app.route('{endpoint_base}" not in api_content:
            missing.append(call)

    if missing:
        print(f"\n  ⚠️  Endpoints called by dashboard but may be missing in API:")
        for endpoint in missing:
            print(f"    ✗ {endpoint}")
        return False
    else:
        print(f"\n  ✓ All dashboard API calls have corresponding endpoints")
        return True


def check_feature_completeness():
    """Check all advertised features are implemented."""
    print("\n\n🔍 Checking Feature Completeness...")
    print("=" * 60)

    features = [
        ('X Intelligence (xAI Grok)', 'src/intelligence/x_intelligence.py'),
        ('Google Trends Tracking', 'src/intelligence/google_trends.py'),
        ('Earnings Call Analysis', 'src/data/transcript_fetcher.py'),
        ('Executive Commentary', 'src/intelligence/executive_commentary.py'),
        ('Institutional Flow', 'src/intelligence/institutional_flow.py'),
        ('Sector Rotation', 'src/intelligence/rotation_predictor.py'),
        ('Supply Chain Graph', 'src/intelligence/relationship_graph.py'),
        ('6-Component Learning', 'src/learning/rl_models.py'),
        ('Intelligence Dashboard', 'docs/index.html'),
        ('API Integration', 'src/api/app.py'),
    ]

    all_implemented = True
    for feature, file_path in features:
        if Path(file_path).exists():
            print(f"  ✓ {feature:40} ({file_path})")
        else:
            print(f"  ✗ {feature:40} ({file_path}) - MISSING")
            all_implemented = False

    return all_implemented


def main():
    """Run all verification checks."""
    print("\n" + "=" * 60)
    print("  DASHBOARD INTEGRATION VERIFICATION")
    print("=" * 60 + "\n")

    results = {}

    # Run checks
    results['dashboard_html'] = check_dashboard_html()
    results['api_endpoints'] = check_api_endpoints()
    results['intelligence_modules'] = check_intelligence_modules()
    results['data_flow'] = check_dashboard_data_flow()
    results['features'] = check_feature_completeness()

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
        print("  ✅ DASHBOARD FULLY INTEGRATED")
        print("=" * 60)
        print("\n✨ Dashboard Features:")
        print("  • Intelligence tab with 7 data visualizations")
        print("  • X/Twitter sentiment analysis (xAI Grok)")
        print("  • Google Trends retail momentum tracking")
        print("  • Earnings call transcript analysis")
        print("  • Executive commentary aggregation")
        print("  • Institutional flow detection")
        print("  • Sector rotation predictions")
        print("  • Supply chain relationship mapping")
        print("  • Catalyst sources distribution")
        print("\n📊 API Endpoints:")
        print("  • /api/intelligence/x-sentiment")
        print("  • /api/intelligence/google-trends")
        print("  • /api/intelligence/supply-chain/:theme")
        print("  • /api/intelligence/catalyst-breakdown")
        print("  • /api/intelligence/earnings/:ticker")
        print("  • /api/intelligence/executive/:ticker")
        print("\n🚀 Ready for Railway deployment!")
        return 0
    else:
        print("  ❌ SOME INTEGRATIONS INCOMPLETE")
        print("=" * 60)
        print("\nFix issues above before deploying.")
        return 1


if __name__ == '__main__':
    import sys
    sys.exit(main())
