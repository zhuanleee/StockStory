"""
Trigger /chatid in a group by simulating webhook call
First, let's try to find the group from Modal logs
"""
import modal

app = modal.App("send-chatid-group")
image = modal.Image.debian_slim(python_version="3.11").pip_install("requests")

@app.function(
    image=image,
    secrets=[modal.Secret.from_name("Stock_Story")],
    timeout=60,
)
def try_common_group_ids():
    import os
    import requests

    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '')

    # Try common supergroup ID patterns
    # Supergroups start with -100
    # Let's try to get chat info for potential StockStory group IDs

    print("Searching for StockStory Group...")

    # Try getChat for potential group IDs
    # If the user recently added the bot, we might find it

    # Common test - try to send a test message and see what groups exist
    # We can use getChatAdministrators if we know the chat_id

    # Let's try some approaches:
    # 1. Check if there's a TELEGRAM_GROUP_CHAT_ID env var
    group_id = os.environ.get('TELEGRAM_GROUP_CHAT_ID', '')
    if group_id:
        print(f"Found TELEGRAM_GROUP_CHAT_ID: {group_id}")

    # 2. Try to get info for the personal chat to confirm API works
    personal_id = 1191814045
    url = f'https://api.telegram.org/bot{bot_token}/getChat'
    response = requests.post(url, json={'chat_id': personal_id})
    print(f"\nPersonal chat check: {response.json()}")

    # Since we don't know the group ID, let's send a message to the personal chat
    # asking to forward the group chat ID
    url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
    response = requests.post(url, json={
        'chat_id': personal_id,
        'text': '🔍 Please send /chatid in the StockStory Group and share the chat ID here.',
        'parse_mode': 'Markdown'
    })
    print(f"\nSent reminder: {response.json()}")

    return "Check Telegram for instructions"

@app.local_entrypoint()
def main():
    try_common_group_ids.remote()
