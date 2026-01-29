#!/bin/bash
# Dashboard Verification Script
# Tests if dashboard is properly deployed on DigitalOcean

APP_URL="https://stock-story-jy89o.ondigitalocean.app"

echo "=========================================="
echo "  DASHBOARD DEPLOYMENT TEST"
echo "=========================================="
echo ""

echo "⏳ Waiting for deployment to complete..."
echo "   (This may take 3-5 minutes)"
echo ""

# Wait for deployment with progress indicator
for i in {1..60}; do
    sleep 3
    echo -n "."
    if [ $((i % 20)) -eq 0 ]; then
        echo " ${i}s"
    fi
done
echo ""
echo ""

echo "🌐 Testing Dashboard Homepage..."
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$APP_URL/")
CONTENT=$(curl -s "$APP_URL/" | head -c 100)

if [ "$RESPONSE" = "200" ] && [[ "$CONTENT" == *"<!DOCTYPE"* ]]; then
    echo "  ✅ Dashboard: SERVING HTML (HTTP $RESPONSE)"
else
    echo "  ❌ Dashboard: FAILED (HTTP $RESPONSE)"
    echo "  Content preview: $CONTENT"
fi

echo ""
echo "🏥 Testing Health Endpoint..."
HEALTH_RESPONSE=$(curl -s "$APP_URL/health")
if [[ "$HEALTH_RESPONSE" == *"Stock Scanner Bot"* ]]; then
    echo "  ✅ Health: RESPONDING"
    echo "$HEALTH_RESPONSE" | python3 -m json.tool | head -10
else
    echo "  ❌ Health: FAILED"
fi

echo ""
echo "📊 Testing API Endpoints..."

# Test intelligence API
INTEL_RESPONSE=$(curl -s "$APP_URL/api/intelligence/summary" | python3 -c "import sys, json; data=json.load(sys.stdin); print('✅' if data.get('ok') else '❌')" 2>/dev/null || echo "❌")
echo "  $INTEL_RESPONSE Intelligence Summary"

# Test X sentiment
X_RESPONSE=$(curl -s "$APP_URL/api/intelligence/x-sentiment" | python3 -c "import sys, json; data=json.load(sys.stdin); print('✅' if data.get('ok') else '❌')" 2>/dev/null || echo "❌")
echo "  $X_RESPONSE X Sentiment"

# Test Google Trends
TRENDS_RESPONSE=$(curl -s "$APP_URL/api/intelligence/google-trends" | python3 -c "import sys, json; data=json.load(sys.stdin); print('✅' if data.get('ok') else '❌')" 2>/dev/null || echo "❌")
echo "  $TRENDS_RESPONSE Google Trends"

echo ""
echo "=========================================="
echo "  DASHBOARD URL"
echo "=========================================="
echo ""
echo "  🌐 Open in browser:"
echo "     $APP_URL"
echo ""
echo "  📱 Test bot commands:"
echo "     Send /help to @Stocks_Story_Bot"
echo ""
echo "=========================================="
