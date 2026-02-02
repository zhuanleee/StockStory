"""
Test if xAI web_search provides LIVE web data
"""
import modal
import os
from datetime import datetime

app = modal.App("test-web-search-live")

# Same image with xai_sdk
image = modal.Image.debian_slim(python_version="3.11").pip_install_from_requirements("requirements.txt")

@app.function(
    image=image,
    secrets=[modal.Secret.from_name("Stock_Story")],
    timeout=180,
)
def test_web_search():
    """Test if web_search provides live/real-time data."""

    print("=" * 80)
    print("TESTING xAI web_search FOR LIVE DATA")
    print("=" * 80)
    print(f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print()

    # Import inside function
    try:
        from xai_sdk import Client
        from xai_sdk.chat import user
        from xai_sdk.tools import web_search
        print("✓ xai_sdk imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import xai_sdk: {e}")
        return {"error": "SDK not available"}

    api_key = os.environ.get('XAI_API_KEY', '')
    if not api_key:
        print("✗ XAI_API_KEY not found")
        return {"error": "No API key"}

    print(f"✓ API key found ({len(api_key)} chars)")
    print()

    # Initialize client
    client = Client(api_key=api_key)

    # =============================================================================
    # TEST 1: Search Financial News for TODAY's Headlines
    # =============================================================================
    print("=" * 80)
    print("TEST 1: Search Financial News Sites for Today's Breaking News")
    print("=" * 80)
    print("Searching: Reuters, Bloomberg, CNBC")
    print()

    try:
        chat = client.chat.create(
            model="grok-4-1-fast",
            tools=[
                web_search(allowed_domains=[
                    "reuters.com",
                    "bloomberg.com",
                    "cnbc.com"
                ]),
            ],
        )

        prompt = f"""
Search Reuters, Bloomberg, and CNBC RIGHT NOW for today's top financial/market headlines.

Today is {datetime.now().strftime('%B %d, %Y')}.

Find:
1. The TOP 3 breaking news headlines from TODAY
2. When each story was published (exact time if possible)
3. Key details from each story

If you can access live web data, you'll find actual headlines from today.
If you can't access live data, please clearly state your knowledge cutoff date.

Return the headlines with timestamps.
"""

        chat.append(user(prompt))
        response = chat.sample()

        print("Response received:")
        print("-" * 80)
        print(response.content[:1000])
        if len(response.content) > 1000:
            print(f"... (truncated, total {len(response.content)} chars)")
        print("-" * 80)
        print()

        # Analyze response
        content_lower = response.content.lower()

        # Check for live indicators
        has_today_refs = any(word in content_lower for word in [
            "today", "breaking", "just now", "minutes ago", "hours ago",
            datetime.now().strftime('%B').lower(),
            str(datetime.now().year)
        ])

        has_cutoff_refs = any(phrase in content_lower for phrase in [
            "knowledge cutoff", "training data", "cannot access",
            "don't have access", "can't access"
        ])

        print("Analysis:")
        print(f"  Contains today/recent references: {has_today_refs}")
        print(f"  Contains cutoff/no-access mentions: {has_cutoff_refs}")
        print()

    except Exception as e:
        print(f"✗ Test 1 failed: {e}")
        return {"error": str(e)}

    # =============================================================================
    # TEST 2: Search for Very Specific Recent Event
    # =============================================================================
    print("=" * 80)
    print("TEST 2: Search for Stock Market Performance from LAST 24 HOURS")
    print("=" * 80)
    print("Searching: MarketWatch, CNBC")
    print()

    try:
        chat2 = client.chat.create(
            model="grok-4-1-fast",
            tools=[
                web_search(allowed_domains=[
                    "marketwatch.com",
                    "cnbc.com"
                ]),
            ],
        )

        prompt2 = """
Search MarketWatch and CNBC for the S&P 500 closing price from YESTERDAY
and TODAY's current/latest price.

What I need:
1. Yesterday's S&P 500 closing price
2. Today's latest S&P 500 price
3. The percentage change
4. What time you found this data

If you have live web access, you'll find actual current market data.
If not, tell me your knowledge cutoff date.
"""

        chat2.append(user(prompt2))
        response2 = chat2.sample()

        print("Response received:")
        print("-" * 80)
        print(response2.content[:800])
        if len(response2.content) > 800:
            print(f"... (truncated, total {len(response2.content)} chars)")
        print("-" * 80)
        print()

        # Look for actual prices (would indicate real data)
        import re
        prices = re.findall(r'\$?[\d,]+\.?\d*', response2.content)
        has_specific_data = len(prices) >= 2

        print("Analysis:")
        print(f"  Found specific numbers/prices: {has_specific_data} ({len(prices)} numbers)")
        if prices[:5]:
            print(f"  Sample numbers: {prices[:5]}")
        print()

    except Exception as e:
        print(f"✗ Test 2 failed: {e}")

    # =============================================================================
    # TEST 3: Direct Question About Capability
    # =============================================================================
    print("=" * 80)
    print("TEST 3: Ask Directly About Live Web Access")
    print("=" * 80)

    try:
        chat3 = client.chat.create(
            model="grok-4-1-fast",
            tools=[
                web_search(allowed_domains=[
                    "reuters.com",
                    "bloomberg.com"
                ]),
            ],
        )

        prompt3 = """
Do you have real-time access to search Reuters.com and Bloomberg.com RIGHT NOW?

Answer:
1. YES or NO
2. If YES, what's a current headline from Reuters.com you can see?
3. If NO, what's your knowledge cutoff date?

Be completely honest - this is important for our system.
"""

        chat3.append(user(prompt3))
        response3 = chat3.sample()

        print("Response:")
        print("-" * 80)
        print(response3.content)
        print("-" * 80)
        print()

    except Exception as e:
        print(f"✗ Test 3 failed: {e}")

    # =============================================================================
    # VERDICT
    # =============================================================================
    print("=" * 80)
    print("VERDICT")
    print("=" * 80)

    if has_today_refs and not has_cutoff_refs:
        print("✓ LIKELY HAS LIVE WEB ACCESS")
        print("  - Found references to today/recent events")
        print("  - No mention of knowledge cutoff")
        print()
        print("Recommendation: IMPLEMENT web_search for news verification!")
        verdict = "live"
    elif has_cutoff_refs:
        print("✗ DOES NOT HAVE LIVE WEB ACCESS")
        print("  - Mentions knowledge cutoff or lack of access")
        print()
        print("Recommendation: Skip web_search, stick with x_search only")
        verdict = "no_access"
    else:
        print("? UNCLEAR - Review responses above")
        print()
        print("Recommendation: Manual review needed")
        verdict = "unclear"

    print("=" * 80)

    return {
        "verdict": verdict,
        "has_today_refs": has_today_refs,
        "has_cutoff_refs": has_cutoff_refs,
        "test_completed": True
    }

@app.local_entrypoint()
def main():
    result = test_web_search.remote()
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
    print(f"Result: {result}")
