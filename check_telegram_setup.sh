#!/bin/bash

echo "=========================================="
echo "TELEGRAM BOT SETUP CHECKER"
echo "=========================================="
echo ""

# Check 1: Environment variables
echo "1. Checking environment variables..."
if [ ! -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo "   ✅ TELEGRAM_BOT_TOKEN is set"
    BOT_TOKEN="$TELEGRAM_BOT_TOKEN"
else
    echo "   ⚠️  TELEGRAM_BOT_TOKEN not set in environment"
    read -p "   Enter your Telegram Bot Token: " BOT_TOKEN
fi

if [ ! -z "$TELEGRAM_CHAT_ID" ]; then
    echo "   ✅ TELEGRAM_CHAT_ID is set: $TELEGRAM_CHAT_ID"
    CHAT_ID="$TELEGRAM_CHAT_ID"
else
    echo "   ⚠️  TELEGRAM_CHAT_ID not set in environment"
    read -p "   Enter your Telegram Chat ID: " CHAT_ID
fi

echo ""

# Check 2: Test bot connection
echo "2. Testing bot connection..."
if [ ! -z "$BOT_TOKEN" ]; then
    RESPONSE=$(curl -s "https://api.telegram.org/bot${BOT_TOKEN}/getMe")

    if echo "$RESPONSE" | grep -q '"ok":true'; then
        BOT_USERNAME=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['result']['username'])" 2>/dev/null)
        BOT_NAME=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['result']['first_name'])" 2>/dev/null)
        echo "   ✅ Bot is valid: @$BOT_USERNAME ($BOT_NAME)"
    else
        echo "   ❌ Bot token is invalid"
        echo "   Response: $RESPONSE"
    fi
else
    echo "   ⚠️  Skipping (no token provided)"
fi

echo ""

# Check 3: Test sending message
echo "3. Testing message sending..."
if [ ! -z "$BOT_TOKEN" ] && [ ! -z "$CHAT_ID" ]; then
    TEST_MSG="✅ Telegram bot test from setup checker"
    SEND_RESPONSE=$(curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
        -H "Content-Type: application/json" \
        -d "{\"chat_id\":\"${CHAT_ID}\",\"text\":\"${TEST_MSG}\"}")

    if echo "$SEND_RESPONSE" | grep -q '"ok":true'; then
        echo "   ✅ Successfully sent test message to chat"
        echo "   📱 Check your Telegram - you should see the test message!"
    else
        echo "   ❌ Failed to send message"
        echo "   Response: $SEND_RESPONSE"
    fi
else
    echo "   ⚠️  Skipping (missing token or chat ID)"
fi

echo ""

# Check 4: Check for pending messages
echo "4. Checking for recent Telegram messages..."
if [ ! -z "$BOT_TOKEN" ]; then
    UPDATES=$(curl -s "https://api.telegram.org/bot${BOT_TOKEN}/getUpdates?limit=5")

    UPDATE_COUNT=$(echo "$UPDATES" | python3 -c "import sys, json; print(len(json.load(sys.stdin).get('result', [])))" 2>/dev/null)

    if [ "$UPDATE_COUNT" -gt 0 ]; then
        echo "   ✅ Found $UPDATE_COUNT recent messages"
        echo ""
        echo "   Recent messages:"
        echo "$UPDATES" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for msg in data.get('result', [])[-5:]:
    if 'message' in msg:
        text = msg['message'].get('text', '')
        user = msg['message'].get('from', {}).get('username', 'unknown')
        print(f'      • {user}: {text}')
" 2>/dev/null
    else
        echo "   ⚠️  No recent messages found"
    fi
else
    echo "   ⚠️  Skipping (no token)"
fi

echo ""

# Check 5: GitHub Secrets (can't check directly, but provide instructions)
echo "5. GitHub Secrets configuration..."
echo "   ℹ️  To check GitHub Secrets, visit:"
echo "   https://github.com/zhuanleee/stock_scanner_bot/settings/secrets/actions"
echo ""
echo "   Required secrets:"
echo "   • TELEGRAM_BOT_TOKEN (your bot token)"
echo "   • TELEGRAM_CHAT_ID (your chat ID)"
echo "   • MODAL_TOKEN_ID (for /scan command)"
echo "   • MODAL_TOKEN_SECRET (for /scan command)"

echo ""

# Check 6: Bot listener workflow
echo "6. Checking bot listener workflow..."
if [ -f ".github/workflows/bot_listener.yml" ]; then
    echo "   ✅ Workflow file exists"

    # Check if it's enabled (not in archive)
    if grep -q "schedule:" ".github/workflows/bot_listener.yml"; then
        echo "   ✅ Workflow has schedule configured"
    else
        echo "   ⚠️  Workflow missing schedule"
    fi
else
    echo "   ❌ Workflow file not found"
    echo "   File should be at: .github/workflows/bot_listener.yml"
fi

echo ""

# Check 7: Modal authentication
echo "7. Checking Modal authentication..."
if [ -d "$HOME/.modal" ]; then
    echo "   ✅ Modal config exists"
else
    echo "   ⚠️  Modal not authenticated locally"
    echo "   Run: modal token set"
fi

echo ""
echo "=========================================="
echo "SUMMARY"
echo "=========================================="
echo ""

if [ ! -z "$BOT_TOKEN" ] && [ ! -z "$CHAT_ID" ]; then
    echo "✅ Bot credentials are configured"
    echo ""
    echo "Next steps:"
    echo "1. Make sure GitHub Secrets are set:"
    echo "   https://github.com/zhuanleee/stock_scanner_bot/settings/secrets/actions"
    echo ""
    echo "2. Push the bot_listener.yml workflow:"
    echo "   git add .github/workflows/bot_listener.yml"
    echo "   git commit -m 'Restore bot listener workflow'"
    echo "   git push"
    echo ""
    echo "3. Manually trigger the workflow to test:"
    echo "   https://github.com/zhuanleee/stock_scanner_bot/actions"
    echo ""
    echo "4. Send /scan to your bot and wait 15 minutes for workflow to run"
    echo ""
    echo "Your bot: @$BOT_USERNAME"
    echo "Test it: Open Telegram and send /scan"
else
    echo "❌ Bot credentials missing"
    echo ""
    echo "To set up:"
    echo "1. Create a bot via @BotFather on Telegram"
    echo "2. Get your bot token"
    echo "3. Send a message to your bot"
    echo "4. Get your chat ID from:"
    echo "   https://api.telegram.org/bot<TOKEN>/getUpdates"
    echo "5. Add to GitHub Secrets"
fi

echo ""
echo "=========================================="
