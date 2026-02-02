#!/bin/bash
# Comprehensive Self-Health Check for Stock Scanner Dashboard
# Tests all endpoints, checks logs, monitors performance

BASE_URL="https://stock-story-jy89o.ondigitalocean.app"
DO_TOKEN=$(cat ~/.claude/do_api_token 2>/dev/null || cat .do_api_token 2>/dev/null)
APP_ID="54145811-faf1-4374-8cdd-b72cc5a3fd27"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
PASSED=0
FAILED=0
WARNINGS=0

echo "======================================================================"
echo "STOCK SCANNER DASHBOARD - COMPREHENSIVE HEALTH CHECK"
echo "======================================================================"
echo "URL: $BASE_URL"
echo "Time: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# =============================================================================
# Function: Test Endpoint
# =============================================================================
test_endpoint() {
    local name="$1"
    local endpoint="$2"
    local expected_status="${3:-200}"
    local max_time="${4:-5}"

    printf "%-50s " "Testing $name..."

    response=$(curl -s -o /tmp/health_response.txt -w "%{http_code}:%{time_total}" --max-time "$max_time" "$BASE_URL$endpoint" 2>&1)
    status_code=$(echo "$response" | cut -d: -f1)
    response_time=$(echo "$response" | cut -d: -f2)

    if [ "$status_code" = "$expected_status" ]; then
        echo -e "${GREEN}✓ PASS${NC} (${status_code}, ${response_time}s)"
        PASSED=$((PASSED + 1))

        # Check if response is JSON
        if python3 -m json.tool < /tmp/health_response.txt > /dev/null 2>&1; then
            ok_status=$(python3 -c "import json; print(json.load(open('/tmp/health_response.txt')).get('ok', True))" 2>/dev/null)
            if [ "$ok_status" = "False" ]; then
                error=$(python3 -c "import json; print(json.load(open('/tmp/health_response.txt')).get('error', 'Unknown'))" 2>/dev/null)
                echo -e "  ${YELLOW}⚠  Warning: ok=false, error: $error${NC}"
                WARNINGS=$((WARNINGS + 1))
            fi
        fi
    else
        echo -e "${RED}✗ FAIL${NC} (Expected $expected_status, got $status_code)"
        FAILED=$((FAILED + 1))
        head -3 /tmp/health_response.txt | sed 's/^/  /'
    fi
}

# =============================================================================
# Test Suite 1: Critical Endpoints
# =============================================================================
echo ""
echo "======================================================================"
echo "PHASE 1: CRITICAL ENDPOINTS"
echo "======================================================================"

test_endpoint "Frontend (HTML)" "/" 200 3
test_endpoint "Health Check" "/health" 200 1
test_endpoint "API Health" "/api/health" 200 15
test_endpoint "Watchlist API" "/api/trades/watchlist" 200 5

# =============================================================================
# Test Suite 2: New Aggregator Routes (Just Fixed)
# =============================================================================
echo ""
echo "======================================================================"
echo "PHASE 2: AGGREGATOR ROUTES (NEWLY FIXED)"
echo "======================================================================"

test_endpoint "Themes Aggregate" "/api/themes" 200 5
test_endpoint "Evolution Aggregate" "/api/evolution" 200 5
test_endpoint "Weights" "/api/weights" 200 5
test_endpoint "Radar" "/api/radar" 200 5
test_endpoint "M&A Radar" "/api/ma-radar" 200 5
test_endpoint "Alerts" "/api/alerts" 200 5
test_endpoint "Risk" "/api/risk" 200 5

# =============================================================================
# Test Suite 3: Other API Endpoints
# =============================================================================
echo ""
echo "======================================================================"
echo "PHASE 3: OTHER API ENDPOINTS"
echo "======================================================================"

test_endpoint "Stories" "/api/stories" 200 10
test_endpoint "News" "/api/news" 200 10
test_endpoint "Sectors" "/api/sectors" 200 10
test_endpoint "Status" "/api/status" 200 5

# =============================================================================
# Test Suite 4: Concurrent Load Test
# =============================================================================
echo ""
echo "======================================================================"
echo "PHASE 4: CONCURRENT LOAD TEST"
echo "======================================================================"

echo "Testing 10 concurrent requests to /health..."
start_time=$(date +%s)
for i in {1..10}; do
    curl -s -o /dev/null "$BASE_URL/health" &
done
wait
end_time=$(date +%s)
duration=$((end_time - start_time))

if [ $duration -lt 5 ]; then
    echo -e "${GREEN}✓ PASS${NC} - All 10 requests completed in ${duration}s"
    PASSED=$((PASSED + 1))
else
    echo -e "${YELLOW}⚠  SLOW${NC} - Took ${duration}s (expected <5s)"
    WARNINGS=$((WARNINGS + 1))
fi

# =============================================================================
# Test Suite 5: Digital Ocean App Status
# =============================================================================
echo ""
echo "======================================================================"
echo "PHASE 5: DIGITAL OCEAN APP STATUS"
echo "======================================================================"

if [ -n "$DO_TOKEN" ]; then
    app_data=$(curl -s -H "Authorization: Bearer $DO_TOKEN" \
        "https://api.digitalocean.com/v2/apps/$APP_ID")

    phase=$(echo "$app_data" | python3 -c "import sys, json; print(json.load(sys.stdin)['app']['active_deployment']['phase'])" 2>/dev/null)
    workers=$(echo "$app_data" | python3 -c "import sys, json; print(json.load(sys.stdin)['app']['spec']['services'][0]['run_command'])" 2>/dev/null | grep -oE "workers [0-9]+" | grep -oE "[0-9]+")
    instance=$(echo "$app_data" | python3 -c "import sys, json; print(json.load(sys.stdin)['app']['spec']['services'][0]['instance_size_slug'])" 2>/dev/null)

    echo "Deployment Phase: $phase"
    echo "Workers: $workers"
    echo "Instance Size: $instance"

    if [ "$phase" = "ACTIVE" ]; then
        echo -e "${GREEN}✓ App is ACTIVE${NC}"
        PASSED=$((PASSED + 1))
    else
        echo -e "${RED}✗ App is $phase (not ACTIVE)${NC}"
        FAILED=$((FAILED + 1))
    fi

    if [ "$workers" -ge 8 ]; then
        echo -e "${GREEN}✓ Using $workers workers (recommended: 8)${NC}"
    else
        echo -e "${YELLOW}⚠  Using only $workers workers (recommended: 8)${NC}"
        echo "  Update run command to: --workers 8 --worker-class gevent"
        WARNINGS=$((WARNINGS + 1))
    fi

    if [[ "$instance" == *"1gb"* ]] || [[ "$instance" == *"2gb"* ]]; then
        echo -e "${GREEN}✓ Instance has adequate RAM${NC}"
    else
        echo -e "${YELLOW}⚠  Instance may be undersized: $instance${NC}"
        echo "  Recommended: apps-s-1vcpu-1gb or larger"
        WARNINGS=$((WARNINGS + 1))
    fi
else
    echo -e "${YELLOW}⚠  Digital Ocean API token not found${NC}"
    echo "  Cannot check app status"
    WARNINGS=$((WARNINGS + 1))
fi

# =============================================================================
# Test Suite 6: Runtime Logs Analysis
# =============================================================================
echo ""
echo "======================================================================"
echo "PHASE 6: RUNTIME LOGS ANALYSIS"
echo "======================================================================"

if [ -n "$DO_TOKEN" ]; then
    deployment_id=$(echo "$app_data" | python3 -c "import sys, json; print(json.load(sys.stdin)['app']['active_deployment']['id'])" 2>/dev/null)

    log_url=$(curl -s -H "Authorization: Bearer $DO_TOKEN" \
        "https://api.digitalocean.com/v2/apps/$APP_ID/deployments/$deployment_id/logs?type=RUN&follow=false&tail_lines=100" \
        | python3 -c "import sys, json; print(json.load(sys.stdin)['url'])" 2>/dev/null)

    logs=$(curl -s "$log_url" | tail -100)

    # Count errors and warnings
    error_count=$(echo "$logs" | grep -c "ERROR" || echo "0")
    warning_count=$(echo "$logs" | grep -c "WARNING" || echo "0")
    critical_count=$(echo "$logs" | grep -c "CRITICAL" || echo "0")

    echo "Errors (last 100 lines): $error_count"
    echo "Warnings (last 100 lines): $warning_count"
    echo "Critical (last 100 lines): $critical_count"

    if [ "$error_count" -eq 0 ] && [ "$critical_count" -eq 0 ]; then
        echo -e "${GREEN}✓ No errors in recent logs${NC}"
        PASSED=$((PASSED + 1))
    else
        echo -e "${YELLOW}⚠  Found $error_count errors, $critical_count critical${NC}"
        echo ""
        echo "Recent errors:"
        echo "$logs" | grep -E "ERROR|CRITICAL" | tail -5 | sed 's/^/  /'
        WARNINGS=$((WARNINGS + 1))
    fi

    # Check for specific issues
    if echo "$logs" | grep -q "No module named 'torch'"; then
        echo -e "${YELLOW}⚠  PyTorch not installed (Learning features disabled)${NC}"
        WARNINGS=$((WARNINGS + 1))
    fi

    if echo "$logs" | grep -q "SocketIO disabled"; then
        echo -e "${BLUE}ℹ  SocketIO disabled (real-time sync unavailable)${NC}"
    fi
else
    echo -e "${YELLOW}⚠  Cannot check logs (no API token)${NC}"
    WARNINGS=$((WARNINGS + 1))
fi

# =============================================================================
# Summary
# =============================================================================
echo ""
echo "======================================================================"
echo "HEALTH CHECK SUMMARY"
echo "======================================================================"
echo ""

total=$((PASSED + FAILED + WARNINGS))
pass_rate=0
if [ $total -gt 0 ]; then
    pass_rate=$((PASSED * 100 / total))
fi

echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo -e "${YELLOW}Warnings: $WARNINGS${NC}"
echo "Pass Rate: ${pass_rate}%"
echo ""

if [ $FAILED -eq 0 ]; then
    if [ $WARNINGS -eq 0 ]; then
        echo -e "${GREEN}🎉 PERFECT HEALTH - All systems operational!${NC}"
        exit 0
    else
        echo -e "${YELLOW}✓ HEALTHY - Minor issues detected${NC}"
        echo ""
        echo "Recommended actions:"
        echo "  1. Update run command to use 8 workers + gevent"
        echo "  2. Consider upgrading instance size to 1GB RAM"
        echo "  3. Optionally add PyTorch for Learning features"
        exit 0
    fi
else
    echo -e "${RED}⚠  ISSUES DETECTED - $FAILED critical failures${NC}"
    echo ""
    echo "Review failed tests above and take action"
    exit 1
fi
