"""
Fix Telegram Webhook Conflict

The bot has an active webhook that conflicts with the polling-based listener.
This script checks the webhook status and provides options to fix it.
"""
import modal

app = modal.App("fix-telegram-webhook")
image = modal.Image.debian_slim(python_version="3.11").pip_install("requests")

@app.function(
    image=image,
    secrets=[modal.Secret.from_name("Stock_Story")],
    timeout=60,
)
def check_and_fix_webhook():
    import os
    import requests

    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '')

    print("=" * 80)
    print("TELEGRAM WEBHOOK STATUS")
    print("=" * 80)
    print()

    # Get current webhook info
    url = f"https://api.telegram.org/bot{bot_token}/getWebhookInfo"
    response = requests.get(url)
    info = response.json()

    if not info.get('ok'):
        print(f"Error: {info}")
        return

    result = info['result']
    webhook_url = result.get('url', '')
    pending_updates = result.get('pending_update_count', 0)
    last_error = result.get('last_error_message', '')
    last_error_date = result.get('last_error_date', 0)

    print(f"Webhook URL: {webhook_url if webhook_url else '(not set)'}")
    print(f"Pending updates: {pending_updates}")
    if last_error:
        print(f"Last error: {last_error}")
        import datetime
        if last_error_date:
            dt = datetime.datetime.fromtimestamp(last_error_date)
            print(f"Last error date: {dt}")
    print()

    if webhook_url:
        print("=" * 80)
        print("WEBHOOK IS ACTIVE")
        print("=" * 80)
        print()
        print("This is why getUpdates (polling) doesn't work!")
        print()
        print("The GitHub Actions bot listener uses polling,")
        print("but Telegram only allows either webhook OR polling, not both.")
        print()

        # Delete the webhook
        print("Deleting webhook to enable polling...")
        delete_url = f"https://api.telegram.org/bot{bot_token}/deleteWebhook"
        delete_response = requests.post(delete_url, json={'drop_pending_updates': False})
        delete_result = delete_response.json()

        if delete_result.get('ok'):
            print("✓ Webhook deleted successfully!")
            print()
            print("The bot listener should now work properly.")
            print("Telegram updates will be processed via GitHub Actions polling.")
        else:
            print(f"Failed to delete webhook: {delete_result}")
    else:
        print("No webhook is active. Polling should work.")

        # Try getUpdates
        print()
        print("Testing getUpdates...")
        updates_url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
        updates_response = requests.get(updates_url, params={'limit': 5})
        updates_result = updates_response.json()

        if updates_result.get('ok'):
            messages = updates_result.get('result', [])
            print(f"✓ getUpdates works! Found {len(messages)} recent updates.")
        else:
            print(f"Error: {updates_result}")

    print()
    print("=" * 80)

@app.local_entrypoint()
def main():
    check_and_fix_webhook.remote()
