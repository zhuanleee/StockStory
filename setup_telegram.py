#!/usr/bin/env python3
"""
Telegram Bot Setup Helper
=========================
Get your Telegram chat ID and test bot configuration.
"""

import requests
import sys
import os

TELEGRAM_BOT_TOKEN = "7626822299:AAHVNKOLIVelbBwOEO2J2aE_6D34Ml0RuuM"

def get_bot_info():
    """Get basic bot information."""
    print("🤖 Getting bot information...")
    print("=" * 60)

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe"

    try:
        response = requests.get(url)
        data = response.json()

        if data.get('ok'):
            bot_info = data.get('result', {})
            print(f"\n✅ Bot Connected Successfully!")
            print(f"  Bot Name: {bot_info.get('first_name')}")
            print(f"  Username: @{bot_info.get('username')}")
            print(f"  Bot ID: {bot_info.get('id')}")
            return True
        else:
            print(f"\n❌ Error: {data.get('description')}")
            return False

    except Exception as e:
        print(f"\n❌ Connection error: {e}")
        return False


def get_chat_id():
    """Get chat ID from recent messages."""
    print("\n\n📱 Getting your Chat ID...")
    print("=" * 60)
    print("\n⚠️  IMPORTANT: Before running this, send a message to your bot!")
    print("   Go to Telegram and send: /start")
    print("   Then press Enter to continue...")
    input()

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"

    try:
        response = requests.get(url)
        data = response.json()

        if data.get('ok'):
            updates = data.get('result', [])

            if not updates:
                print("\n❌ No messages found!")
                print("   Make sure you sent a message to the bot first.")
                return None

            # Get the most recent chat
            latest = updates[-1]
            chat_id = latest.get('message', {}).get('chat', {}).get('id')
            chat_type = latest.get('message', {}).get('chat', {}).get('type')

            if chat_id:
                print(f"\n✅ Found your Chat ID!")
                print(f"  Chat ID: {chat_id}")
                print(f"  Chat Type: {chat_type}")
                return chat_id
            else:
                print("\n❌ Could not extract chat ID from updates")
                return None

        else:
            print(f"\n❌ Error: {data.get('description')}")
            return None

    except Exception as e:
        print(f"\n❌ Error: {e}")
        return None


def test_send_message(chat_id):
    """Test sending a message to the chat."""
    print("\n\n📤 Testing message sending...")
    print("=" * 60)

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    message = """🎉 *Bot Configuration Successful!*

Your stock scanner bot is ready to deploy.

*Next Steps:*
1. Add these environment variables to Railway
2. Deploy the app
3. Configure webhook
4. Start scanning!

Type /help to see all commands."""

    payload = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'Markdown'
    }

    try:
        response = requests.post(url, json=payload)
        data = response.json()

        if data.get('ok'):
            print("\n✅ Test message sent successfully!")
            print("   Check your Telegram - you should see a message from the bot.")
            return True
        else:
            print(f"\n❌ Error sending message: {data.get('description')}")
            return False

    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


def generate_railway_vars(chat_id):
    """Generate Railway environment variables."""
    print("\n\n⚙️  Railway Environment Variables")
    print("=" * 60)
    print("\n📋 Copy these to Railway Dashboard → Variables:\n")

    print(f"TELEGRAM_BOT_TOKEN={TELEGRAM_BOT_TOKEN}")
    print(f"TELEGRAM_CHAT_ID={chat_id}")

    print("\n✅ Also add these (you should already have them):\n")
    print("POLYGON_API_KEY=your_polygon_key")
    print("DEEPSEEK_API_KEY=your_deepseek_key")
    print("XAI_API_KEY=your_xai_key")
    print("ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key")


def generate_webhook_command(railway_url=None):
    """Generate webhook setup command."""
    print("\n\n🔗 Webhook Configuration")
    print("=" * 60)

    if not railway_url:
        print("\n⚠️  After Railway deployment, run this command:")
        print("   (Replace YOUR_RAILWAY_URL with your actual Railway app URL)\n")
        railway_url = "YOUR_RAILWAY_URL.railway.app"

    webhook_cmd = f"""curl -X POST "https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook" \\
  -H "Content-Type: application/json" \\
  -d '{{"url": "https://{railway_url}/webhook"}}'"""

    print(webhook_cmd)

    print("\n\n✅ To verify webhook later:")
    verify_cmd = f'curl "https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getWebhookInfo"'
    print(verify_cmd)


def main():
    """Run Telegram setup wizard."""
    print("\n" + "=" * 60)
    print("  TELEGRAM BOT SETUP WIZARD")
    print("=" * 60 + "\n")

    # Step 1: Test bot connection
    if not get_bot_info():
        print("\n❌ Bot connection failed. Check your token and try again.")
        return 1

    # Step 2: Get chat ID
    chat_id = get_chat_id()
    if not chat_id:
        print("\n❌ Could not get chat ID. Make sure you sent /start to the bot.")
        return 1

    # Step 3: Test sending message
    if not test_send_message(chat_id):
        print("\n⚠️  Message sending failed, but you can still continue.")

    # Step 4: Generate Railway variables
    generate_railway_vars(chat_id)

    # Step 5: Generate webhook command
    generate_webhook_command()

    # Summary
    print("\n\n" + "=" * 60)
    print("  ✅ SETUP COMPLETE!")
    print("=" * 60)
    print("\n📝 Summary:")
    print(f"  • Bot Token: {TELEGRAM_BOT_TOKEN[:20]}...")
    print(f"  • Chat ID: {chat_id}")
    print(f"  • Test message: Sent ✓")

    print("\n🚀 Next Steps:")
    print("  1. Copy the environment variables above to Railway")
    print("  2. Wait for Railway to deploy (~2 min)")
    print("  3. Run the webhook configuration command")
    print("  4. Send /help to your bot to test")

    print("\n" + "=" * 60)
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n👋 Setup cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        sys.exit(1)
