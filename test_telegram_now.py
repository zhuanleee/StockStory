#!/usr/bin/env python3
"""
Quick Telegram test - checks if bot can communicate
"""
import os
import requests
import sys

# Try to get credentials from environment
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '')

print("=" * 60)
print("TELEGRAM BOT QUICK TEST")
print("=" * 60)
print()

# Check 1: Credentials
print("1. Checking credentials...")
if not BOT_TOKEN:
    print("   ❌ TELEGRAM_BOT_TOKEN not set")
    print()
    print("   To test, run:")
    print("   export TELEGRAM_BOT_TOKEN='your_token'")
    print("   export TELEGRAM_CHAT_ID='your_chat_id'")
    print("   python3 test_telegram_now.py")
    sys.exit(1)
else:
    print(f"   ✅ Token set: {BOT_TOKEN[:15]}...")

if not CHAT_ID:
    print("   ❌ TELEGRAM_CHAT_ID not set")
    sys.exit(1)
else:
    print(f"   ✅ Chat ID set: {CHAT_ID}")

print()

# Check 2: Test bot connection
print("2. Testing bot connection...")
try:
    response = requests.get(
        f"https://api.telegram.org/bot{BOT_TOKEN}/getMe",
        timeout=10
    )
    if response.status_code == 200:
        data = response.json()
        if data.get('ok'):
            bot_info = data['result']
            print(f"   ✅ Bot connected: @{bot_info['username']}")
            print(f"      Name: {bot_info['first_name']}")
        else:
            print(f"   ❌ Bot API error: {data}")
            sys.exit(1)
    else:
        print(f"   ❌ HTTP error: {response.status_code}")
        sys.exit(1)
except Exception as e:
    print(f"   ❌ Connection failed: {e}")
    sys.exit(1)

print()

# Check 3: Send test message
print("3. Sending test message...")
try:
    test_msg = "🧪 Test from diagnostic script\n\nIf you see this, your bot is working!"
    response = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={'chat_id': CHAT_ID, 'text': test_msg},
        timeout=10
    )
    if response.status_code == 200:
        data = response.json()
        if data.get('ok'):
            print("   ✅ Message sent successfully!")
            print("   📱 Check your Telegram - you should see the test message")
        else:
            print(f"   ❌ Send failed: {data}")
    else:
        print(f"   ❌ HTTP error: {response.status_code}")
        print(f"   Response: {response.text}")
except Exception as e:
    print(f"   ❌ Send failed: {e}")

print()

# Check 4: Check for recent messages
print("4. Checking for your messages...")
try:
    response = requests.get(
        f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?limit=10",
        timeout=10
    )
    if response.status_code == 200:
        data = response.json()
        if data.get('ok'):
            updates = data.get('result', [])
            print(f"   Found {len(updates)} recent messages:")
            print()
            for update in updates[-5:]:  # Show last 5
                if 'message' in update:
                    msg = update['message']
                    text = msg.get('text', '')
                    from_user = msg.get('from', {}).get('username', 'unknown')
                    date = msg.get('date', 0)
                    print(f"      • {from_user}: {text}")

            if updates:
                print()
                print(f"   ℹ️  Latest update ID: {updates[-1]['update_id']}")
        else:
            print(f"   ❌ Error: {data}")
    else:
        print(f"   ❌ HTTP error: {response.status_code}")
except Exception as e:
    print(f"   ❌ Check failed: {e}")

print()
print("=" * 60)
print("TEST COMPLETE")
print("=" * 60)
print()
print("If you saw ✅ for all checks, your Telegram bot is configured correctly!")
print()
print("The workflow runs every 15 minutes during market hours.")
print("To test the /scan command RIGHT NOW:")
print()
print("1. Go to: https://github.com/zhuanleee/stock_scanner_bot/actions")
print("2. Click 'Bot Listener' workflow")
print("3. Click 'Run workflow' dropdown")
print("4. Click green 'Run workflow' button")
print("5. Wait 30 seconds")
print("6. Check your Telegram")
print()
