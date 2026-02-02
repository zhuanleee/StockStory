"""
Quick Telegram Check - Shows all past messages
"""
import modal

app = modal.App("quick-telegram-check")
image = modal.Image.debian_slim(python_version="3.11").pip_install("requests")

@app.function(
    image=image,
    secrets=[modal.Secret.from_name("Stock_Story")],
    timeout=60,
)
def check_telegram():
    import os
    import requests

    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '')
    current_chat_id = os.environ.get('TELEGRAM_CHAT_ID', '')

    print("=" * 80)
    print("TELEGRAM BOT STATUS CHECK")
    print("=" * 80)
    print()
    print(f"Bot Token: {bot_token[:10]}...{bot_token[-5:]}")
    print(f"Current Chat ID in config: {current_chat_id}")
    print()

    # Get bot info
    url = f"https://api.telegram.org/bot{bot_token}/getMe"
    response = requests.get(url)
    bot_info = response.json()

    if bot_info.get('ok'):
        bot = bot_info['result']
        print(f"✓ Bot: @{bot['username']} ({bot['first_name']})")
    print()

    # Get ALL updates (including old ones)
    print("Checking ALL message history...")
    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    response = requests.get(url)
    updates = response.json()

    if not updates.get('ok'):
        print(f"❌ Error: {updates}")
        return

    messages = updates.get('result', [])
    print(f"Found {len(messages)} total messages/updates in history")
    print()

    if messages:
        print("=" * 80)
        print("ALL CHAT IDs FROM MESSAGE HISTORY:")
        print("=" * 80)

        chats = {}
        for msg in messages:
            if 'message' in msg:
                chat = msg['message'].get('chat', {})
                chat_id = chat.get('id')
                if chat_id:
                    if chat_id not in chats:
                        chats[chat_id] = {
                            'type': chat.get('type'),
                            'title': chat.get('title', chat.get('first_name', 'Unknown')),
                            'username': chat.get('username', 'none'),
                            'count': 0
                        }
                    chats[chat_id]['count'] += 1

        if chats:
            for chat_id, info in chats.items():
                print()
                print(f"Chat ID: {chat_id}")
                print(f"  Type: {info['type']}")
                print(f"  Name: {info['title']}")
                if info['username'] != 'none':
                    print(f"  Username: @{info['username']}")
                print(f"  Messages: {info['count']}")

                if str(chat_id) == str(current_chat_id):
                    print(f"  ✓ THIS IS YOUR CURRENT CONFIGURED CHAT")
        else:
            print("No chats found in message history")

        print()
        print("=" * 80)
        print("WHAT TO DO:")
        print("=" * 80)
        print()
        print("If you see your chat ID above, copy it and update Modal secret:")
        print("1. Go to: https://modal.com/secrets")
        print("2. Edit 'Stock_Story' secret")
        print("3. Update TELEGRAM_CHAT_ID to the Chat ID shown above")
        print()

        if not chats:
            print("❌ NO CHAT IDs FOUND!")
            print()
            print("This means:")
            print("1. You've never sent a message to this bot, OR")
            print("2. The bot history was cleared")
            print()
            print("TO FIX:")
            print("1. Open Telegram")
            print("2. Search for @Stocks_Story_Bot")
            print("3. Send /start")
            print("4. Run this script again")

    else:
        print("❌ No messages found")
        print()
        print("TO GET CHAT ID:")
        print("1. Open Telegram app")
        print("2. Search: @Stocks_Story_Bot")
        print("3. Click 'START' or send any message")
        print("4. Run this script again")

    print("=" * 80)

@app.local_entrypoint()
def main():
    check_telegram.remote()
