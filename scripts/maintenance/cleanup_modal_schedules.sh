#!/bin/bash
set -e

echo "=============================================="
echo "Modal Schedule Cleanup Script"
echo "=============================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if modal is installed
if ! command -v modal &> /dev/null; then
    echo -e "${YELLOW}Modal CLI not found. Installing...${NC}"
    pip3 install modal
    echo -e "${GREEN}✓ Modal CLI installed${NC}"
fi

echo ""
echo "Step 1: Checking Modal authentication..."
echo "==========================================="

# Check if already authenticated
if python3 -m modal app list &> /dev/null; then
    echo -e "${GREEN}✓ Already authenticated${NC}"
else
    echo -e "${YELLOW}Not authenticated. Please login...${NC}"
    echo ""
    echo "This will open a browser window for authentication."
    echo "Press Enter to continue..."
    read

    python3 -m modal token set

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Authentication successful${NC}"
    else
        echo -e "${RED}✗ Authentication failed${NC}"
        exit 1
    fi
fi

echo ""
echo "Step 2: Checking current deployments..."
echo "==========================================="
python3 -m modal app list
echo ""

echo ""
echo "Step 3: Stopping old deployments..."
echo "==========================================="
echo "Stopping old apps (stock-scanner-ai-brain, stock-scanner-api-v2)..."
python3 -m modal app stop stock-scanner-ai-brain 2>&1 || echo "App may not exist or already stopped"
python3 -m modal app stop stock-scanner-api-v2 2>&1 || echo "App may not exist or already stopped"

echo "Note: New apps are named 'stockstory-api' and 'stockstory-scanner'"

echo -e "${GREEN}✓ Apps stopped${NC}"

echo ""
echo "Waiting 10 seconds for cleanup..."
sleep 10

echo ""
echo "Step 4: Deploying fresh versions..."
echo "==========================================="

echo "Deploying API (no schedules)..."
python3 -m modal deploy modal_api_v2.py

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ API deployed successfully${NC}"
else
    echo -e "${RED}✗ API deployment failed${NC}"
    exit 1
fi

echo ""
echo "Deploying Scanner (4 schedules)..."
python3 -m modal deploy modal_scanner.py

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Scanner deployed successfully${NC}"
else
    echo -e "${RED}✗ Scanner deployment failed${NC}"
    echo ""
    echo "If you see 'reached limit of 5 cron jobs', there are still phantom schedules."
    echo ""
    echo "Next steps:"
    echo "1. Go to https://modal.com and login"
    echo "2. Navigate to 'Schedules' section"
    echo "3. Delete all old schedules manually"
    echo "4. Run this script again"
    echo ""
    echo "Or upgrade to Team plan: https://modal.com/settings/zhuanleee/plans"
    exit 1
fi

echo ""
echo "=============================================="
echo -e "${GREEN}✓ DEPLOYMENT SUCCESSFUL!${NC}"
echo "=============================================="
echo ""
echo "Your 4 automated schedules are now active:"
echo "  1. morning_mega_bundle (Mon-Fri 6:00 AM PST)"
echo "  2. afternoon_analysis_bundle (Mon-Fri 1:00 PM PST)"
echo "  3. weekly_reports_bundle (Sunday 6:00 PM PST)"
echo "  4. monitoring_cycle_bundle (Every 6 hours)"
echo ""
echo "First run: Tomorrow morning at 6:00 AM PST"
echo ""
echo "To test manually:"
echo "  python3 -m modal run modal_scanner.py::conviction_alerts"
echo ""
echo "To monitor logs:"
echo "  python3 -m modal app logs stockstory-scanner --follow"
echo ""
