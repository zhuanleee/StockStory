#!/bin/bash

echo "=========================================="
echo "TELEGRAM BOT - LOCAL TEST"
echo "=========================================="
echo ""

# Set your credentials
export TELEGRAM_BOT_TOKEN="7626822299:AAHVNKOLIVelbBwOEO2J2aE_6D34Ml0RuuM"
export TELEGRAM_CHAT_ID="1191814045"

echo "✅ Credentials set:"
echo "   Bot: @Stocks_Story_Bot"
echo "   Chat ID: 1191814045"
echo ""

echo "🔍 Running bot listener locally..."
echo "   This will check for your /scan and /help messages"
echo ""

# Run the bot listener
cd "$(dirname "$0")"
python3 main.py bot

echo ""
echo "=========================================="
echo "If you see responses above, the bot is working!"
echo "Now update GitHub Secrets with these same values."
echo "=========================================="
