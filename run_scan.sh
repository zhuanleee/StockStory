#!/bin/bash

echo "=========================================="
echo "Stock Scanner - Manual Scan Trigger"
echo "=========================================="
echo ""

# Check if Modal is installed
if ! python3 -c "import modal" 2>/dev/null; then
    echo "❌ Modal not installed"
    echo "Installing Modal..."
    pip install modal
fi

# Check if Modal is authenticated
if [ ! -d ~/.modal ]; then
    echo "⚠️  Modal not authenticated"
    echo ""
    echo "Please authenticate Modal:"
    echo "1. Go to https://modal.com/settings/tokens"
    echo "2. Create a new token"
    echo "3. Run: python3 -m modal token set"
    echo "4. Then run this script again"
    exit 1
fi

echo "✅ Modal authenticated"
echo ""

# Ask what type of scan
echo "Choose scan type:"
echo "1) Quick test (single stock - NVDA)"
echo "2) Full scan (515 stocks - 5-10 minutes)"
echo ""
read -p "Enter choice (1 or 2): " choice

case $choice in
    1)
        echo ""
        echo "Running quick test scan..."
        python3 -m modal run modal_scanner.py --ticker NVDA
        ;;
    2)
        echo ""
        echo "Running full scan (this will take 5-10 minutes)..."
        echo "Starting scan..."
        python3 -m modal run modal_scanner.py --daily
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "=========================================="
echo "Scan complete!"
echo ""
echo "View results at:"
echo "https://zhuanleee.github.io/stock_scanner_bot/"
echo ""
echo "Don't forget to click the '↻ Refresh' button!"
echo "=========================================="
