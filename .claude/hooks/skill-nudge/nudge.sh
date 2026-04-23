#!/usr/bin/env bash
set -euo pipefail

# Read the prompt JSON from stdin
INPUT=$(cat)

# Extract the prompt text
PROMPT=$(echo "$INPUT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(data.get('prompt', '').lower())
" 2>/dev/null || echo "")

# Skip empty prompts
if [ -z "$PROMPT" ]; then
    exit 0
fi

# Pattern matching for skill nudges
# Only output a reminder if a pattern matches — stay silent otherwise

if echo "$PROMPT" | grep -qiE '\b(build|create|add feature|implement|design|redesign|new feature)\b'; then
    echo "Skill check: this looks like creative/build work. Invoke brainstorming skill before acting."
elif echo "$PROMPT" | grep -qiE '\b(fix|bug|broken|error|not working|failing|crash|exception)\b'; then
    echo "Skill check: this looks like debugging. Invoke systematic-debugging skill before acting."
elif echo "$PROMPT" | grep -qiE '\b(plan|migrate|refactor|overhaul|rewrite|restructure)\b'; then
    echo "Skill check: this looks like multi-step work. Invoke writing-plans skill before acting."
fi
