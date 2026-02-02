#!/bin/bash
# Log a Claude session summary to CHANGES.md
# Usage: ./scripts/log-session.sh "Summary of what was done"

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
CHANGES_FILE="$REPO_ROOT/CHANGES.md"
SESSION_DATE=$(date +"%Y-%m-%d %H:%M")

if [ -z "$1" ]; then
    echo "Usage: ./scripts/log-session.sh \"Summary of changes\""
    echo ""
    echo "Example:"
    echo "  ./scripts/log-session.sh \"Added new API endpoint for user auth\""
    exit 1
fi

SUMMARY="$1"

# Get uncommitted changes
UNCOMMITTED=$(git status --porcelain | head -10)
UNCOMMITTED_COUNT=$(git status --porcelain | wc -l | tr -d ' ')

ENTRY="### ${SESSION_DATE} - Session Log

**${SUMMARY}**

"

if [ "$UNCOMMITTED_COUNT" -gt 0 ]; then
    ENTRY+="<details>
<summary>Uncommitted changes (${UNCOMMITTED_COUNT})</summary>

\`\`\`
${UNCOMMITTED}
\`\`\`
</details>

"
fi

ENTRY+="---

"

# Insert after marker
if grep -q "AUTO-GENERATED BELOW" "$CHANGES_FILE"; then
    awk -v entry="$ENTRY" '
        /AUTO-GENERATED BELOW/ {
            print
            print ""
            print entry
            next
        }
        {print}
    ' "$CHANGES_FILE" > "$CHANGES_FILE.tmp"
    mv "$CHANGES_FILE.tmp" "$CHANGES_FILE"
    echo "📝 Session logged to CHANGES.md"
else
    echo "$ENTRY" >> "$CHANGES_FILE"
    echo "📝 Session appended to CHANGES.md"
fi
