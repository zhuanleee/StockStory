"""
Set up Telegram Bot Menu and Commands
"""
import modal

app = modal.App("setup-telegram-menu")
image = modal.Image.debian_slim(python_version="3.11").pip_install("requests")

@app.function(
    image=image,
    secrets=[modal.Secret.from_name("Stock_Story")],
    timeout=60,
)
def setup_menu():
    import os
    import requests

    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '')

    print("=" * 80)
    print("SETTING UP TELEGRAM BOT MENU")
    print("=" * 80)
    print()

    # Define bot commands
    commands = [
        {"command": "start", "description": "🚀 Start the bot"},
        {"command": "help", "description": "❓ Show all commands"},
        {"command": "top", "description": "🏆 Top 10 stocks by score"},
        {"command": "movers", "description": "📊 Today's biggest movers"},
        {"command": "themes", "description": "🔥 Hot market themes"},
        {"command": "earnings", "description": "📅 Upcoming earnings"},
        {"command": "chart", "description": "📈 Price chart (e.g., /chart NVDA)"},
        {"command": "news", "description": "📰 Stock news (e.g., /news AAPL)"},
        {"command": "insider", "description": "👔 Insider trades (e.g., /insider MSFT)"},
        {"command": "sec", "description": "📋 SEC filings (e.g., /sec TSLA)"},
        {"command": "watchlist", "description": "👁 View your watchlist"},
        {"command": "watch", "description": "➕ Add to watchlist (e.g., /watch AMD)"},
        {"command": "unwatch", "description": "➖ Remove from watchlist"},
        {"command": "status", "description": "🟢 System status"},
    ]

    # Set commands
    url = f"https://api.telegram.org/bot{bot_token}/setMyCommands"
    response = requests.post(url, json={"commands": commands})
    result = response.json()

    if result.get('ok'):
        print("✅ Bot commands set successfully!")
        print()
        print("Commands registered:")
        for cmd in commands:
            print(f"  /{cmd['command']} - {cmd['description']}")
    else:
        print(f"❌ Failed to set commands: {result}")
        return

    print()

    # Set menu button to show commands
    menu_url = f"https://api.telegram.org/bot{bot_token}/setChatMenuButton"
    menu_response = requests.post(menu_url, json={
        "menu_button": {
            "type": "commands"
        }
    })
    menu_result = menu_response.json()

    if menu_result.get('ok'):
        print("✅ Menu button configured!")
    else:
        print(f"⚠️ Menu button config: {menu_result}")

    print()

    # Set bot description
    desc_url = f"https://api.telegram.org/bot{bot_token}/setMyDescription"
    desc_response = requests.post(desc_url, json={
        "description": "📈 StockStory - Story-first stock analysis with AI-powered insights. Send any ticker (NVDA, AAPL) for instant analysis!"
    })

    short_desc_url = f"https://api.telegram.org/bot{bot_token}/setMyShortDescription"
    requests.post(short_desc_url, json={
        "short_description": "StockStory - AI-powered stock analysis"
    })

    print("✅ Bot description updated!")
    print()
    print("=" * 80)
    print("DONE! Open @Stocks_Story_Bot and tap the menu button (☰) to see commands")
    print("=" * 80)

@app.local_entrypoint()
def main():
    setup_menu.remote()
