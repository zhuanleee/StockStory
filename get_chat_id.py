#!/usr/bin/env python3
"""
Quick script to get Telegram Chat ID
"""

import requests

TELEGRAM_BOT_TOKEN = "7626822299:AAHVNKOLIVelbBwOEO2J2aE_6D34Ml0RuuM"

print("=" * 60)
print("  TELEGRAM BOT INFORMATION")
print("=" * 60)

# Get bot info
url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe"
response = requests.get(url)
data = response.json()

if data.get('ok'):
    bot_info = data.get('result', {})
    print(f"\n✅ Bot: @{bot_info.get('username')}")
    print(f"   Name: {bot_info.get('first_name')}")
    print(f"   ID: {bot_info.get('id')}")
else:
    print(f"\n❌ Error: {data.get('description')}")
    exit(1)

# Get updates
print("\n" + "=" * 60)
print("  CHECKING FOR MESSAGES")
print("=" * 60)

url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
response = requests.get(url)
data = response.json()

if data.get('ok'):
    updates = data.get('result', [])

    if not updates:
        print("\n⚠️  No messages found!")
        print("\n📱 TO GET YOUR CHAT ID:")
        print("   1. Open Telegram")
        print("   2. Search for: @Stocks_Story_Bot")
        print("   3. Send: /start")
        print("   4. Run this script again: python3 get_chat_id.py")
    else:
        print(f"\n✅ Found {len(updates)} message(s)\n")

        # Show all unique chat IDs
        chat_ids = set()
        for update in updates:
            message = update.get('message', {})
            chat = message.get('chat', {})
            chat_id = chat.get('id')
            chat_type = chat.get('type')
            username = chat.get('username', 'N/A')
            first_name = chat.get('first_name', 'N/A')

            if chat_id:
                chat_ids.add(chat_id)
                print(f"  Chat ID: {chat_id}")
                print(f"  Type: {chat_type}")
                print(f"  Name: {first_name}")
                print(f"  Username: @{username}")
                print()

        if chat_ids:
            # Use the most recent one
            latest_chat_id = list(chat_ids)[-1]

            print("=" * 60)
            print("  RAILWAY ENVIRONMENT VARIABLES")
            print("=" * 60)
            print("\n📋 Copy these to Railway Dashboard → Variables:\n")
            print(f"TELEGRAM_BOT_TOKEN={TELEGRAM_BOT_TOKEN}")
            print(f"TELEGRAM_CHAT_ID={latest_chat_id}")

            print("\n" + "=" * 60)
            print("  WEBHOOK CONFIGURATION")
            print("=" * 60)
            print("\n⚠️  After Railway deployment, run this:\n")
            print(f'curl -X POST "https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook" \\')
            print('  -H "Content-Type: application/json" \\')
            print('  -d \'{"url": "https://YOUR_RAILWAY_URL.railway.app/webhook"}\'')

            print("\n✅ Replace YOUR_RAILWAY_URL with your actual Railway app URL")

            print("\n" + "=" * 60)
            print("  NEXT STEPS")
            print("=" * 60)
            print("\n1. Add environment variables to Railway (see above)")
            print("2. Wait for Railway to deploy (~2-3 minutes)")
            print("3. Run webhook configuration command (see above)")
            print("4. Test: Send /help to @Stocks_Story_Bot")
            print()

else:
    print(f"\n❌ Error: {data.get('description')}")
