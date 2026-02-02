"""
Test /hedge command by calling webhook directly
"""
import modal

app = modal.App("test-hedge-webhook")
image = modal.Image.debian_slim(python_version="3.11").pip_install("requests")

@app.function(
    image=image,
    secrets=[modal.Secret.from_name("Stock_Story")],
    timeout=180,
)
def test_hedge():
    import os
    import requests
    import json

    # Call the webhook endpoint directly with a simulated Telegram update
    webhook_url = "https://zhuanleee--stockstory-api-create-fastapi-app.modal.run/telegram/webhook"

    # Simulate a Telegram update with /hedge command
    update = {
        "update_id": 999999999,
        "message": {
            "message_id": 12345,
            "from": {
                "id": 1191814045,
                "is_bot": False,
                "first_name": "John",
                "last_name": "Lee",
                "username": "zhuanlee"
            },
            "chat": {
                "id": 1191814045,
                "first_name": "John",
                "last_name": "Lee",
                "username": "zhuanlee",
                "type": "private"
            },
            "date": 1234567890,
            "text": "/hedge"
        }
    }

    print(f"Calling webhook: {webhook_url}")
    print(f"Payload: {json.dumps(update, indent=2)}")

    response = requests.post(webhook_url, json=update, timeout=120)

    print(f"\nStatus: {response.status_code}")
    print(f"Response: {response.text}")

    return response.json() if response.status_code == 200 else response.text

@app.local_entrypoint()
def main():
    result = test_hedge.remote()
    print(f"\nFinal result: {result}")
