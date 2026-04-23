#!/usr/bin/env bash
set -euo pipefail

COS_ROOT="/Users/amipatil/Desktop/CoS"

# Read the prompt JSON from stdin
INPUT=$(cat)

# Extract the prompt text
PROMPT=$(echo "$INPUT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
# Prompt is at top level, not nested under transcript_message
print(data.get('prompt', ''))
" 2>/dev/null || echo "")

# Skip empty prompts
if [ -z "$PROMPT" ]; then
    exit 0
fi

# Determine log location based on cwd
CWD=$(pwd)
if [[ "$CWD" =~ $COS_ROOT/projects/[^/]+/[^/]+ ]]; then
    # We're inside a project directory — extract the project root
    PROJECT_DIR=$(echo "$CWD" | sed -E "s|($COS_ROOT/projects/[^/]+/[^/]+).*|\1|")
    LOG_DIR="$PROJECT_DIR/logs"
else
    # CoS level
    LOG_DIR="$COS_ROOT/logs"
fi

mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/prompt-history.jsonl"

# Append entry
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
python3 -c "
import json, sys
entry = {
    'ts': '$TIMESTAMP',
    'prompt': sys.stdin.read().strip()
}
print(json.dumps(entry, ensure_ascii=False))
" <<< "$PROMPT" >> "$LOG_FILE"
