"""
Read recent Telegram messages sent to the bot
"""
import modal

app = modal.App("read-telegram-messages")
image = modal.Image.debian_slim(python_version="3.11").pip_install("requests")

@app.function(
    image=image,
    secrets=[modal.Secret.from_name("Stock_Story")],
    timeout=60,
)
def read_messages():
    import os
    import requests
    from datetime import datetime

    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '')

    print("=" * 80)
    print("RECENT TELEGRAM MESSAGES")
    print("=" * 80)
    print()

    # Note: With webhook active, getUpdates won't work
    # First check webhook status
    info_url = f"https://api.telegram.org/bot{bot_token}/getWebhookInfo"
    info_resp = requests.get(info_url)
    info = info_resp.json()

    if info.get('ok'):
        result = info['result']
        webhook_url = result.get('url', '')
        pending = result.get('pending_update_count', 0)
        last_error = result.get('last_error_message', '')
        last_error_date = result.get('last_error_date', 0)

        print(f"Webhook URL: {webhook_url[:50]}..." if webhook_url else "Webhook: Not set")
        print(f"Pending updates: {pending}")

        if last_error:
            print(f"\n⚠️ Last webhook error: {last_error}")
            if last_error_date:
                dt = datetime.fromtimestamp(last_error_date)
                print(f"   Error time: {dt}")

        if webhook_url:
            print("\n📌 Note: With webhook active, messages are processed in real-time.")
            print("   Check Modal logs for message processing details.")
            print()
            print("   To view Modal logs:")
            print("   modal app logs stock-scanner-api-v2")

    print()
    print("=" * 80)

@app.local_entrypoint()
def main():
    read_messages.remote()
