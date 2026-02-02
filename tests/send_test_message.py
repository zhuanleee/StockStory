"""
Send a test message directly to Telegram
"""
import modal

app = modal.App("send-test-message")
image = modal.Image.debian_slim(python_version="3.11").pip_install("requests")

@app.function(
    image=image,
    secrets=[modal.Secret.from_name("Stock_Story")],
    timeout=60,
)
def send_test():
    import os
    import requests

    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '')
    chat_id = '1191814045'  # John Lee's chat ID

    print(f"Bot token: {bot_token[:10]}..." if bot_token else "No bot token!")
    print(f"Chat ID: {chat_id}")

    url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
    response = requests.post(url, json={
        'chat_id': chat_id,
        'text': '🧪 *Test Message*\n\nBot is working! Reply with /status to test.',
        'parse_mode': 'Markdown'
    })

    result = response.json()
    print(f"Response: {result}")

    if result.get('ok'):
        print("✅ Message sent successfully!")
    else:
        print(f"❌ Failed: {result.get('description', 'Unknown error')}")

    return result

@app.local_entrypoint()
def main():
    send_test.remote()
