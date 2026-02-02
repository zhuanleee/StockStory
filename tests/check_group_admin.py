"""
Check StockStory Group - bot is now admin with privacy off
"""
import modal

app = modal.App("check-group-admin")
image = modal.Image.debian_slim(python_version="3.11").pip_install("requests")

@app.function(
    image=image,
    secrets=[modal.Secret.from_name("Stock_Story")],
    timeout=60,
)
def check_group():
    import os
    import requests

    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '')

    # Check bot info again
    url = f'https://api.telegram.org/bot{bot_token}/getMe'
    response = requests.get(url)
    bot_info = response.json()
    print(f"Bot Info: {bot_info}")

    # Get updates - with webhook, we need to temporarily remove it to get updates
    # Or check recent webhook info

    # Try getWebhookInfo to see recent activity
    url = f'https://api.telegram.org/bot{bot_token}/getWebhookInfo'
    response = requests.get(url)
    webhook_info = response.json()
    print(f"\nWebhook Info: {webhook_info}")

    # Get updates (may be empty if webhook is set)
    url = f'https://api.telegram.org/bot{bot_token}/getUpdates'
    response = requests.get(url)
    updates = response.json()
    print(f"\nUpdates: {updates}")

    # If there's pending_update_count in webhook info, there might be unprocessed updates
    if webhook_info.get('ok'):
        info = webhook_info.get('result', {})
        print(f"\nPending updates: {info.get('pending_update_count', 0)}")
        print(f"Last error: {info.get('last_error_message', 'None')}")
        print(f"Last error date: {info.get('last_error_date', 'None')}")

    return webhook_info

@app.local_entrypoint()
def main():
    check_group.remote()
