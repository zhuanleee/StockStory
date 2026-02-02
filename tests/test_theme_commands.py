"""
Test theme management Telegram commands
"""
import modal

app = modal.App("test-theme-commands")
image = modal.Image.debian_slim(python_version="3.11").pip_install("requests")

@app.function(
    image=image,
    secrets=[modal.Secret.from_name("Stock_Story")],
    timeout=60,
)
def send_command(command: str):
    import os
    import requests

    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '')
    chat_id = '1191814045'  # John Lee's chat ID

    url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
    response = requests.post(url, json={
        'chat_id': chat_id,
        'text': command,
    })

    result = response.json()
    print(f"Sent: {command}")
    print(f"Response: {result}")
    return result

@app.local_entrypoint()
def main():
    # Test /themestats command
    send_command.remote("/themestats")
