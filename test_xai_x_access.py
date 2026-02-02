"""
Test if xAI Grok actually has real-time X/Twitter access.
"""
import modal
import os
from datetime import datetime

app = modal.App("test-xai-x-access")
image = modal.Image.debian_slim(python_version="3.11").pip_install_from_requirements("requirements.txt").add_local_dir("src", remote_path="/root/src")

@app.function(
    image=image,
    secrets=[modal.Secret.from_name("Stock_Story")],
    timeout=120,
)
def test_x_access():
    """Test if xAI can actually search X/Twitter in real-time."""
    import sys
    sys.path.insert(0, '/root')

    from src.services.ai_service import get_ai_service

    print("=" * 80)
    print("TESTING xAI REAL-TIME X/TWITTER ACCESS")
    print("=" * 80)
    print(f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print()

    ai_service = get_ai_service()

    # Check configuration
    print("Configuration:")
    print(f"  xAI Model: {os.environ.get('XAI_MODEL', 'not set')}")
    print(f"  xAI API Key: {os.environ.get('XAI_API_KEY', 'not set')[:10]}...")
    print()

    # Test 1: Ask for current trending topics
    print("=" * 80)
    print("TEST 1: Current X/Twitter Trending Topics")
    print("=" * 80)

    prompt1 = """
What are the top 5 trending topics on X (Twitter) RIGHT NOW?

List them with:
1. Topic name
2. Approximate number of posts/tweets
3. When it started trending (e.g., "10 minutes ago", "2 hours ago")

If you can access real-time X data, provide specific current trends.
If you cannot access X data, please say "I cannot access real-time X data."
"""

    response1 = ai_service.call_xai(
        prompt=prompt1,
        system_prompt="You are Grok with real-time access to X (Twitter). Provide current trending topics.",
        max_tokens=500,
        temperature=0.2
    )

    print("xAI Response:")
    print(response1 if response1 else "No response")
    print()

    # Test 2: Ask about a very recent event (that couldn't be in training data)
    print("=" * 80)
    print("TEST 2: Very Recent Event Check")
    print("=" * 80)
    print("Asking about events from the last 24 hours...")
    print()

    prompt2 = """
Search X (Twitter) for any major news or events that happened in the LAST 24 HOURS.

Find posts from the last day and tell me:
1. What major events are people discussing?
2. Any breaking news?
3. What time today did these posts appear?

If you can access real-time X data, show me actual recent posts/events.
If you cannot, please clearly state you don't have real-time access.
"""

    response2 = ai_service.call_xai(
        prompt=prompt2,
        system_prompt="You have real-time X access. Search and analyze posts from the last 24 hours.",
        max_tokens=500,
        temperature=0.2
    )

    print("xAI Response:")
    print(response2 if response2 else "No response")
    print()

    # Test 3: Explicit capability check
    print("=" * 80)
    print("TEST 3: Direct Capability Question")
    print("=" * 80)

    prompt3 = """
Do you (Grok) have real-time access to X (Twitter) data through this API?

Answer with:
1. YES or NO
2. If YES, what's the freshness of the data (e.g., live, 5 minutes delay, 1 hour delay)?
3. If YES, can you search specific topics and see actual posts?
4. If NO, what's your knowledge cutoff date?

Be completely honest - this is important for our crisis detection system.
"""

    response3 = ai_service.call_xai(
        prompt=prompt3,
        system_prompt="Be completely honest about your capabilities.",
        max_tokens=300,
        temperature=0.1
    )

    print("xAI Response:")
    print(response3 if response3 else "No response")
    print()

    # Analysis
    print("=" * 80)
    print("ANALYSIS")
    print("=" * 80)

    # Check if responses indicate real-time access
    has_realtime_indicators = False
    no_access_indicators = False

    if response1:
        text_lower = response1.lower()
        if any(x in text_lower for x in ["trending now", "currently trending", "minutes ago", "hours ago", "real-time"]):
            has_realtime_indicators = True
        if any(x in text_lower for x in ["cannot access", "don't have access", "knowledge cutoff", "training data"]):
            no_access_indicators = True

    print(f"Real-time indicators found: {has_realtime_indicators}")
    print(f"No-access indicators found: {no_access_indicators}")
    print()

    if has_realtime_indicators and not no_access_indicators:
        print("✓ VERDICT: Grok appears to have real-time X access")
        print("  Crisis detection should work as intended.")
    elif no_access_indicators:
        print("✗ VERDICT: Grok does NOT have real-time X access via this API")
        print("  Crisis detection will NOT work - only using training data.")
        print()
        print("POSSIBLE FIXES:")
        print("  1. Check if XAI_MODEL env var is set correctly")
        print("  2. Verify xAI API key has X access permissions")
        print("  3. May need to use specific Grok model with X access")
        print("  4. Contact xAI support about enabling X search")
    else:
        print("? VERDICT: Unclear - responses are ambiguous")
        print("  Review responses above to determine capability.")

    print("=" * 80)
    return {
        'has_realtime': has_realtime_indicators,
        'no_access': no_access_indicators,
        'responses': {
            'test1': response1,
            'test2': response2,
            'test3': response3
        }
    }

@app.local_entrypoint()
def main():
    result = test_x_access.remote()
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
