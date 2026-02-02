#!/bin/bash
# Setup git hooks for automatic change logging
# Run this once: ./scripts/setup-hooks.sh

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)

if [ -z "$REPO_ROOT" ]; then
    echo "❌ Error: Not in a git repository"
    exit 1
fi

HOOKS_DIR="$REPO_ROOT/.git/hooks"
SOURCE_DIR="$REPO_ROOT/scripts/hooks"

echo "🔧 Setting up git hooks..."

# Create hooks directory if needed
mkdir -p "$HOOKS_DIR"

# Copy post-commit hook
if [ -f "$SOURCE_DIR/post-commit" ]; then
    cp "$SOURCE_DIR/post-commit" "$HOOKS_DIR/post-commit"
    chmod +x "$HOOKS_DIR/post-commit"
    echo "✅ post-commit hook installed"
else
    echo "❌ post-commit hook not found in $SOURCE_DIR"
    exit 1
fi

echo ""
echo "🎉 Git hooks installed successfully!"
echo ""
echo "From now on, every commit will automatically update CHANGES.md"
echo ""
echo "To test, make a commit and check CHANGES.md"
