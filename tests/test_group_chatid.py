"""
Test /chatid command from a group context
"""
import modal

app = modal.App("test-group-chatid")
image = modal.Image.debian_slim(python_version="3.11").pip_install("requests")

@app.function(
    image=image,
    secrets=[modal.Secret.from_name("Stock_Story")],
    timeout=120,
)
def test_group_message():
    import os
    import requests
    import json

    # Simulate a group message to the webhook
    webhook_url = "https://zhuanleee--stockstory-api-create-fastapi-app.modal.run/telegram/webhook"

    # Simulate a group message with /chatid
    # Using a fake group ID for testing - the bot should respond to any chat
    update = {
        "update_id": 999999998,
        "message": {
            "message_id": 12346,
            "from": {
                "id": 1191814045,
                "is_bot": False,
                "first_name": "John",
                "last_name": "Lee",
                "username": "zhuanlee"
            },
            "chat": {
                "id": -1001234567890,  # Fake supergroup ID
                "title": "StockStory Group",
                "type": "supergroup"
            },
            "date": 1234567890,
            "text": "/chatid"
        }
    }

    print(f"Sending simulated group message to webhook...")
    print(f"Payload: {json.dumps(update, indent=2)}")

    response = requests.post(webhook_url, json=update, timeout=60)

    print(f"\nStatus: {response.status_code}")
    print(f"Response: {response.text}")

    # Also test with @bot mention format
    update2 = {
        "update_id": 999999997,
        "message": {
            "message_id": 12347,
            "from": {
                "id": 1191814045,
                "is_bot": False,
                "first_name": "John",
                "last_name": "Lee",
                "username": "zhuanlee"
            },
            "chat": {
                "id": -1001234567890,
                "title": "StockStory Group",
                "type": "supergroup"
            },
            "date": 1234567890,
            "text": "/chatid@Stocks_Story_Bot",
            "entities": [
                {"offset": 0, "length": 25, "type": "bot_command"}
            ]
        }
    }

    print(f"\n\nTesting with @bot mention...")
    response2 = requests.post(webhook_url, json=update2, timeout=60)
    print(f"Status: {response2.status_code}")
    print(f"Response: {response2.text}")

    return {"test1": response.status_code, "test2": response2.status_code}

@app.local_entrypoint()
def main():
    test_group_message.remote()
