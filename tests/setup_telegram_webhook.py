"""
Set up Telegram webhook to Modal API
"""
import modal

app = modal.App("setup-telegram-webhook")
image = modal.Image.debian_slim(python_version="3.11").pip_install("requests")

MODAL_API_URL = "https://zhuanleee--stock-scanner-api-v2-create-fastapi-app.modal.run"

@app.function(
    image=image,
    secrets=[modal.Secret.from_name("Stock_Story")],
    timeout=60,
)
def setup_webhook():
    import os
    import requests

    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '')
    webhook_url = f"{MODAL_API_URL}/telegram/webhook"

    print("=" * 80)
    print("SETTING UP TELEGRAM WEBHOOK")
    print("=" * 80)
    print()
    print(f"Webhook URL: {webhook_url}")
    print()

    # First, check current webhook
    info_url = f"https://api.telegram.org/bot{bot_token}/getWebhookInfo"
    info_response = requests.get(info_url)
    info = info_response.json()

    if info.get('ok'):
        current = info['result'].get('url', '')
        print(f"Current webhook: {current if current else '(none)'}")
    print()

    # Set the new webhook
    print("Setting webhook...")
    set_url = f"https://api.telegram.org/bot{bot_token}/setWebhook"
    set_response = requests.post(set_url, json={
        'url': webhook_url,
        'allowed_updates': ['message']  # Only receive message updates
    })
    set_result = set_response.json()

    if set_result.get('ok'):
        print("✓ Webhook set successfully!")
        print()
        print(f"Bot will now receive messages instantly via:")
        print(f"  {webhook_url}")
    else:
        print(f"Failed to set webhook: {set_result}")
        return

    # Verify
    print()
    print("Verifying...")
    verify_response = requests.get(info_url)
    verify_result = verify_response.json()

    if verify_result.get('ok'):
        result = verify_result['result']
        print(f"✓ Webhook URL: {result.get('url')}")
        print(f"  Pending updates: {result.get('pending_update_count', 0)}")
        if result.get('last_error_message'):
            print(f"  Last error: {result.get('last_error_message')}")

    print()
    print("=" * 80)
    print("DONE! Test by sending /help to @Stocks_Story_Bot")
    print("=" * 80)

@app.local_entrypoint()
def main():
    setup_webhook.remote()
