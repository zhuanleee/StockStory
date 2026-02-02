"""
Find StockStory Group chat ID
"""
import modal

app = modal.App("find-stockstory-group")
image = modal.Image.debian_slim(python_version="3.11").pip_install("requests")

@app.function(
    image=image,
    secrets=[modal.Secret.from_name("Stock_Story")],
    timeout=60,
)
def find_group():
    import os
    import requests

    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '')

    # Try common group chat ID formats
    # Groups usually have negative IDs
    # Supergroups start with -100

    # Let's check the bot's info first
    url = f'https://api.telegram.org/bot{bot_token}/getMe'
    response = requests.get(url)
    bot_info = response.json()
    print(f"Bot Info: {bot_info}")

    # Try to get chat info for known IDs
    # John Lee's personal chat
    personal_chat_id = 1191814045

    # Try some potential group IDs (you may need to send /chatid in the group first)
    potential_ids = [
        personal_chat_id,  # Personal
    ]

    print("\n=== Checking Known Chats ===")
    for chat_id in potential_ids:
        url = f'https://api.telegram.org/bot{bot_token}/getChat'
        response = requests.post(url, json={'chat_id': chat_id})
        data = response.json()
        if data.get('ok'):
            chat = data.get('result', {})
            print(f"\nChat ID: {chat_id}")
            print(f"  Type: {chat.get('type')}")
            print(f"  Title: {chat.get('title') or chat.get('first_name')}")
        else:
            print(f"\nChat ID {chat_id}: {data.get('description', 'Not found')}")

    return bot_info

@app.local_entrypoint()
def main():
    find_group.remote()
