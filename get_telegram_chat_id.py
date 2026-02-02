"""
Get Telegram Chat ID Helper

This script helps you find your correct Telegram chat ID.

Instructions:
1. Run this script
2. Send ANY message to your bot on Telegram (e.g., "hello" or "/start")
3. The script will show you the chat ID to use

Run: modal run get_telegram_chat_id.py
"""
import modal

app = modal.App("get-telegram-chat-id")

image = modal.Image.debian_slim(python_version="3.11").pip_install("requests")

@app.function(
    image=image,
    secrets=[modal.Secret.from_name("Stock_Story")],
    timeout=120,
)
def get_chat_id():
    """Get Telegram chat ID from recent messages."""
    import os
    import requests
    import time

    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '')

    print("=" * 80)
    print("TELEGRAM CHAT ID HELPER")
    print("=" * 80)
    print()

    if not bot_token:
        print("❌ ERROR: TELEGRAM_BOT_TOKEN not found in Stock_Story secret")
        return

    print(f"✓ Bot token found: {bot_token[:10]}...{bot_token[-5:]}")
    print()

    # Test bot connection
    print("Testing bot connection...")
    try:
        url = f"https://api.telegram.org/bot{bot_token}/getMe"
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            bot_info = response.json()
            if bot_info.get('ok'):
                bot_data = bot_info.get('result', {})
                print(f"✓ Bot connected: @{bot_data.get('username', 'unknown')}")
                print(f"  Bot name: {bot_data.get('first_name', 'unknown')}")
                print()
            else:
                print(f"❌ Bot API error: {bot_info}")
                return
        else:
            print(f"❌ Bot connection failed: HTTP {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Error connecting to bot: {e}")
        return

    # Get recent updates
    print("=" * 80)
    print("INSTRUCTIONS:")
    print("=" * 80)
    print("1. Open Telegram and find your bot")
    print("2. Send ANY message to the bot (e.g., 'hello' or '/start')")
    print("3. Wait a few seconds for this script to detect it")
    print()
    print("Waiting for messages (checking for 60 seconds)...")
    print()

    found_chats = set()

    for i in range(12):  # Check 12 times over 60 seconds
        try:
            url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                updates = response.json()

                if updates.get('ok') and updates.get('result'):
                    results = updates.get('result', [])

                    for update in results:
                        message = update.get('message', {})
                        chat = message.get('chat', {})
                        chat_id = chat.get('id')
                        chat_type = chat.get('type', 'unknown')

                        if chat_id and chat_id not in found_chats:
                            found_chats.add(chat_id)

                            print(f"✓ Found chat #{len(found_chats)}:")
                            print(f"  Chat ID: {chat_id}")
                            print(f"  Type: {chat_type}")

                            if chat_type == 'private':
                                username = chat.get('username', 'none')
                                first_name = chat.get('first_name', 'none')
                                print(f"  User: {first_name} (@{username})")
                            elif chat_type in ['group', 'supergroup']:
                                title = chat.get('title', 'none')
                                print(f"  Group: {title}")

                            message_text = message.get('text', 'none')
                            print(f"  Last message: {message_text}")
                            print()

            if found_chats:
                # Found at least one chat, keep checking for more
                pass

            if i < 11:  # Don't sleep on last iteration
                time.sleep(5)

        except Exception as e:
            print(f"⚠️ Error checking updates: {e}")
            time.sleep(5)

    print("=" * 80)

    if found_chats:
        print("✅ FOUND CHAT ID(S)!")
        print("=" * 80)
        print()

        for idx, chat_id in enumerate(sorted(found_chats), 1):
            print(f"{idx}. Use this Chat ID: {chat_id}")

        print()
        print("=" * 80)
        print("NEXT STEPS:")
        print("=" * 80)
        print("1. Copy one of the Chat IDs above")
        print("2. Update your Modal secret 'Stock_Story':")
        print("   - Go to: https://modal.com/secrets")
        print("   - Edit 'Stock_Story' secret")
        print(f"   - Change TELEGRAM_CHAT_ID to: {list(found_chats)[0]}")
        print("3. Save the secret")
        print("4. Re-run the API connection test")
        print()
    else:
        print("❌ NO MESSAGES DETECTED")
        print("=" * 80)
        print()
        print("Make sure you:")
        print("1. Sent a message to your bot on Telegram")
        print("2. Waited a few seconds before the script finished")
        print()
        print("Try running this script again and send '/start' to your bot!")
        print()

    print("=" * 80)

@app.local_entrypoint()
def main():
    print()
    print("Starting Telegram Chat ID helper...")
    print("Make sure your Telegram app is open!")
    print()
    get_chat_id.remote()
