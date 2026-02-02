"""
Test if xAI X Intelligence V2 (using SDK) has real-time X/Twitter access.
"""
import modal
import os
from datetime import datetime

app = modal.App("test-xai-v2-x-access")

# Same image as main scanner
image = modal.Image.debian_slim(python_version="3.11").pip_install_from_requirements("requirements.txt").add_local_dir("src", remote_path="/root/src")

@app.function(
    image=image,
    secrets=[modal.Secret.from_name("Stock_Story")],
    timeout=180,
)
def test_v2_x_access():
    """Test if xAI V2 (SDK-based) can actually search X/Twitter in real-time."""
    import sys
    sys.path.insert(0, '/root')

    print("=" * 80)
    print("TESTING xAI X Intelligence V2 - SDK with x_search tool")
    print("=" * 80)
    print(f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print()

    # Check SDK availability
    try:
        from xai_sdk import Client
        from xai_sdk.tools import x_search
        print("✓ xai_sdk is available")
    except ImportError as e:
        print(f"✗ xai_sdk NOT available: {e}")
        return {"error": "SDK not installed"}

    # Check API key
    api_key = os.environ.get('XAI_API_KEY', '')
    if not api_key:
        print("✗ XAI_API_KEY not found in environment")
        return {"error": "No API key"}
    print(f"✓ XAI_API_KEY found ({len(api_key)} chars)")
    print()

    # Test V2 implementation
    from src.ai.xai_x_intelligence_v2 import get_x_intelligence_v2

    x_intel = get_x_intelligence_v2()
    if not x_intel or not x_intel.available:
        print("✗ X Intelligence V2 not available")
        return {"error": "V2 not initialized"}

    print("✓ X Intelligence V2 initialized")
    print()

    # Test 1: Search for crisis topics
    print("=" * 80)
    print("TEST 1: Searching X for crisis topics")
    print("=" * 80)

    crisis_topics = x_intel.search_x_for_crises()

    print(f"Found {len(crisis_topics)} crisis topics")
    if crisis_topics:
        print("\nCrisis topics detected:")
        for i, topic in enumerate(crisis_topics[:3], 1):  # Show first 3
            print(f"\n{i}. {topic.get('topic', 'Unknown')}")
            print(f"   Severity: {topic.get('severity', 'N/A')}")
            print(f"   Mentions: {topic.get('mentions', 'N/A')}")
    else:
        print("No significant crisis topics found (this is good!)")
    print()

    # Test 2: Analyze a general market topic
    print("=" * 80)
    print("TEST 2: Deep analysis of a specific topic")
    print("=" * 80)
    print("Analyzing: 'stock market'")
    print()

    analysis = x_intel.analyze_crisis_topic("stock market")

    if analysis:
        print("Analysis received:")
        print(f"  Severity: {analysis.get('severity', 'N/A')}/10")
        print(f"  Verified: {analysis.get('verified', False)}")
        print(f"  Credibility: {analysis.get('credibility', 0):.1%}")
        print(f"  Halt trading: {analysis.get('halt_trading', False)}")
        print(f"  Affected sectors: {', '.join(analysis.get('affected_sectors', []))}")
        print()
        print("Raw analysis preview:")
        raw = analysis.get('raw_analysis', '')
        print(raw[:500] + "..." if len(raw) > 500 else raw)
    else:
        print("No analysis returned")
    print()

    # Verdict
    print("=" * 80)
    print("VERDICT")
    print("=" * 80)

    if crisis_topics is not None and analysis is not None:
        print("✓ X Intelligence V2 is operational")
        print("✓ SDK-based X search appears to be working")
        print()
        print("Next steps:")
        print("  - Monitor crisis_topics structure in production")
        print("  - Verify real-time data (check if topics match current news)")
        print("  - Test Telegram notifications when severity >= 7")
    else:
        print("✗ X Intelligence V2 had errors")
        print("  Check logs above for details")

    print("=" * 80)

    return {
        "sdk_available": True,
        "v2_initialized": True,
        "crisis_topics_count": len(crisis_topics) if crisis_topics else 0,
        "analysis_received": analysis is not None,
        "sample_topics": crisis_topics[:3] if crisis_topics else [],
        "sample_analysis": {
            "severity": analysis.get("severity") if analysis else None,
            "verified": analysis.get("verified") if analysis else None,
        }
    }

@app.local_entrypoint()
def main():
    result = test_v2_x_access.remote()
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
    print(f"Result: {result}")
