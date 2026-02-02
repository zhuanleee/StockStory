"""
Check what chats the bot is in and get their IDs
"""
import modal

app = modal.App("check-bot-chats")
image = modal.Image.debian_slim(python_version="3.11").pip_install("requests")

@app.function(
    image=image,
    secrets=[modal.Secret.from_name("Stock_Story")],
    timeout=60,
)
def check_chats():
    import os
    import requests

    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '')

    # Get recent updates to find chat IDs
    url = f'https://api.telegram.org/bot{bot_token}/getUpdates'
    response = requests.get(url)
    data = response.json()

    print("=== Recent Updates ===")

    chats_seen = {}

    if data.get('ok') and data.get('result'):
        for update in data['result']:
            message = update.get('message') or update.get('my_chat_member', {}).get('chat')
            if message:
                chat = message.get('chat', message)
                chat_id = chat.get('id')
                chat_type = chat.get('type')
                chat_title = chat.get('title') or chat.get('first_name', 'Unknown')

                if chat_id not in chats_seen:
                    chats_seen[chat_id] = {
                        'id': chat_id,
                        'type': chat_type,
                        'title': chat_title
                    }

    print("\n=== Chats Found ===")
    for chat_id, info in chats_seen.items():
        print(f"Chat ID: {info['id']}")
        print(f"  Type: {info['type']}")
        print(f"  Title: {info['title']}")
        print()

    return chats_seen

@app.local_entrypoint()
def main():
    result = check_chats.remote()
    print(f"\nTotal chats found: {len(result)}")
