"""
Test sending notification to StockStory Group
"""
import modal

app = modal.App("test-group-notification")
image = modal.Image.debian_slim(python_version="3.11").pip_install("requests")

@app.function(
    image=image,
    secrets=[modal.Secret.from_name("Stock_Story")],
    timeout=60,
)
def test_group_send():
    import os
    import requests

    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '')
    personal_chat_id = os.environ.get('TELEGRAM_CHAT_ID', '1191814045')
    group_chat_id = '-1003774843100'

    message = "✅ *Group Notification Test*\n\n"
    message += "This message confirms the bot can send to both:\n"
    message += "• Personal chat\n"
    message += "• StockStory Group\n\n"
    message += "_All cron jobs and alerts will now go to both!_"

    url = f'https://api.telegram.org/bot{bot_token}/sendMessage'

    results = {}
    for name, chat_id in [('Personal', personal_chat_id), ('Group', group_chat_id)]:
        response = requests.post(url, json={
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'Markdown'
        })
        results[name] = response.json()
        print(f"{name} ({chat_id}): {response.status_code}")

    return results

@app.local_entrypoint()
def main():
    test_group_send.remote()
