#!/bin/bash
# Test Modal deployment

echo "🧪 Testing Modal AI Brain Scanner"
echo "=================================="
echo ""

# Check if modal is installed
if ! command -v modal &> /dev/null; then
    echo "Installing modal..."
    pip3 install modal
fi

echo "Running test scan of NVDA with full AI brain..."
echo ""

# Run test
/Users/johnlee/Library/Python/3.13/bin/modal run modal_scanner.py --test

echo ""
echo "=================================="
echo "If you see NVDA analysis above, it worked! ✅"
