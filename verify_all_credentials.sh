#!/bin/bash

echo "=========================================="
echo "VERIFYING ALL CREDENTIALS"
echo "=========================================="
echo ""

# Set all credentials
export TELEGRAM_BOT_TOKEN="7626822299:AAHVNKOLIVelbBwOEO2J2aE_6D34Ml0RuuM"
export TELEGRAM_CHAT_ID="1191814045"
export MODAL_TOKEN_ID="ak-XFxcOL8QkwD3StZRl4YQOL"
export MODAL_TOKEN_SECRET="as-5QPQUcQ38JoyoeTQAXOfwj"

echo "1. Testing Telegram Bot Token..."
RESPONSE=$(curl -s "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getMe")
if echo "$RESPONSE" | grep -q '"ok":true'; then
    BOT_NAME=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['result']['username'])" 2>/dev/null)
    echo "   ✅ Telegram Bot Token: VALID (@$BOT_NAME)"
else
    echo "   ❌ Telegram Bot Token: INVALID"
    exit 1
fi
echo ""

echo "2. Testing Telegram Chat ID..."
TEST_MSG="✅ Credential verification test"
SEND_RESPONSE=$(curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    -H "Content-Type: application/json" \
    -d "{\"chat_id\":\"${TELEGRAM_CHAT_ID}\",\"text\":\"${TEST_MSG}\"}")
if echo "$SEND_RESPONSE" | grep -q '"ok":true'; then
    echo "   ✅ Telegram Chat ID: VALID (1191814045)"
    echo "   📱 Check your Telegram - you should see test message"
else
    echo "   ❌ Telegram Chat ID: INVALID"
    exit 1
fi
echo ""

echo "3. Testing Modal Tokens..."
python3 -m modal token set --token-id "$MODAL_TOKEN_ID" --token-secret "$MODAL_TOKEN_SECRET" 2>&1 | tee /tmp/modal_auth.log
if grep -q "Token verified successfully" /tmp/modal_auth.log; then
    echo "   ✅ Modal Tokens: VALID"
else
    echo "   ❌ Modal Tokens: INVALID"
    exit 1
fi
echo ""

echo "=========================================="
echo "✅ ALL CREDENTIALS VERIFIED!"
echo "=========================================="
echo ""
echo "Now copy these EXACT values to GitHub Secrets:"
echo ""
echo "Secret 1: TELEGRAM_BOT_TOKEN"
echo "Value: $TELEGRAM_BOT_TOKEN"
echo ""
echo "Secret 2: TELEGRAM_CHAT_ID"
echo "Value: $TELEGRAM_CHAT_ID"
echo ""
echo "Secret 3: MODAL_TOKEN_ID"
echo "Value: $MODAL_TOKEN_ID"
echo ""
echo "Secret 4: MODAL_TOKEN_SECRET"
echo "Value: $MODAL_TOKEN_SECRET"
echo ""
