#!/bin/bash
# Stock Scanner Bot - Safe Dead Code Cleanup Script
# Run from project root: bash cleanup_dead_code.sh

set -e  # Exit on error

echo "🗑️  Stock Scanner Bot - Dead Code Cleanup"
echo "=========================================="
echo ""

# Safety check - verify we're in the right directory
if [ ! -f "modal_api_v2.py" ]; then
    echo "❌ Error: Not in project root directory"
    echo "Please run from /Users/johnlee/stock_scanner_bot/"
    exit 1
fi

echo "📋 This script will:"
echo "  1. Delete 3 duplicate modal API files (1,782 lines)"
echo "  2. Remove archived workflows directory"
echo "  3. Remove old cache directory"
echo "  4. Clean build artifacts (__pycache__, *.pyc)"
echo ""
echo "⚠️  Files to be deleted:"
echo "  - modal_api.py"
echo "  - modal_api_full.py"
echo "  - modal_api_consolidated.py"
echo "  - .github/workflows-archive/"
echo "  - data/cache_old/"
echo "  - All __pycache__ directories"
echo ""

read -p "Continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

echo ""
echo "Starting cleanup..."
echo ""

# 1. Verify no imports reference files to be deleted
echo "🔍 Step 1: Checking for imports..."
IMPORTS_FOUND=0

if grep -r "import modal_api[^_]" --include="*.py" . 2>/dev/null | grep -v modal_api_v2; then
    echo "⚠️  Warning: Found imports of modal_api (not v2)"
    IMPORTS_FOUND=1
fi

if grep -r "from modal_api[^_]" --include="*.py" . 2>/dev/null | grep -v modal_api_v2; then
    echo "⚠️  Warning: Found from imports of modal_api (not v2)"
    IMPORTS_FOUND=1
fi

if [ $IMPORTS_FOUND -eq 1 ]; then
    echo ""
    read -p "Imports found. Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Cancelled."
        exit 0
    fi
else
    echo "✅ No problematic imports found"
fi

# 2. DELETE duplicate Modal APIs
echo ""
echo "🗑️  Step 2: Removing duplicate modal APIs..."
rm -f modal_api.py && echo "  ✅ Deleted modal_api.py"
rm -f modal_api_full.py && echo "  ✅ Deleted modal_api_full.py"
rm -f modal_api_consolidated.py && echo "  ✅ Deleted modal_api_consolidated.py"

# 3. DELETE archived workflows
echo ""
echo "🗑️  Step 3: Removing archived workflows..."
if [ -d ".github/workflows-archive" ]; then
    rm -rf .github/workflows-archive/
    echo "  ✅ Deleted .github/workflows-archive/"
else
    echo "  ℹ️  Directory .github/workflows-archive/ not found (already deleted?)"
fi

# 4. DELETE old cache
echo ""
echo "🗑️  Step 4: Removing old cache..."
if [ -d "data/cache_old" ]; then
    rm -rf data/cache_old/
    echo "  ✅ Deleted data/cache_old/"
else
    echo "  ℹ️  Directory data/cache_old/ not found (already deleted?)"
fi

# 5. CLEAN build artifacts
echo ""
echo "🧹 Step 5: Cleaning build artifacts..."
PYCACHE_COUNT=$(find . -type d -name "__pycache__" 2>/dev/null | wc -l | tr -d ' ')
PYC_COUNT=$(find . -name "*.pyc" 2>/dev/null | wc -l | tr -d ' ')

find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true

echo "  ✅ Cleaned $PYCACHE_COUNT __pycache__ directories"
echo "  ✅ Deleted $PYC_COUNT .pyc files"

# 6. Summary
echo ""
echo "🎉 Cleanup complete!"
echo ""
echo "Summary:"
echo "  ✅ Removed 3 duplicate modal API files (~1,782 lines)"
echo "  ✅ Removed archived workflows directory"
echo "  ✅ Removed old cache directory (if existed)"
echo "  ✅ Cleaned $PYCACHE_COUNT __pycache__ directories and $PYC_COUNT .pyc files"
echo ""
echo "📊 Disk space saved: ~3-5 MB"
echo ""
echo "⚠️  NEXT STEPS:"
echo "  1. Test modal deployment:"
echo "     modal deploy modal_api_v2.py"
echo ""
echo "  2. Verify GitHub Actions:"
echo "     gh run list --workflow=deploy_modal.yml --limit 3"
echo ""
echo "  3. Commit changes:"
echo "     git add -A"
echo "     git commit -m 'Clean up dead code: remove 3 duplicate modal APIs and archived files'"
echo "     git push origin main"
echo ""
echo "✅ Cleanup script completed successfully!"
