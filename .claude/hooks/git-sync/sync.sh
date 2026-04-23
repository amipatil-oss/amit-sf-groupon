#!/usr/bin/env bash
# CoS git auto-sync — tracked files only, bidirectional
# Runs via launchd every 4 hours
# Skips if a Claude Code session is actively working (lock file)

set -euo pipefail

REPO_DIR="/Users/amipatil/Desktop/CoS"
LOG_FILE="$REPO_DIR/.claude/hooks/git-sync/.sync.log"
LOCK_FILE="$REPO_DIR/.claude/hooks/git-sync/.sync.lock"

log() { echo "$(date -u '+%Y-%m-%dT%H:%M:%SZ') $*" >> "$LOG_FILE"; }

cd "$REPO_DIR"

# Skip if lock file exists and is less than 10 minutes old
if [ -f "$LOCK_FILE" ]; then
    lock_age=$(( $(date +%s) - $(stat -f %m "$LOCK_FILE") ))
    if [ "$lock_age" -lt 600 ]; then
        log "SKIP: lock file active (${lock_age}s old), Claude session in progress"
        exit 0
    fi
    log "WARN: stale lock file (${lock_age}s old), removing"
    rm -f "$LOCK_FILE"
fi

# Skip if git index is locked (another git operation in progress)
if [ -f "$REPO_DIR/.git/index.lock" ]; then
    log "SKIP: git index.lock exists, another git operation in progress"
    exit 0
fi

# Ensure we're on main branch
BRANCH=$(git branch --show-current)
if [ "$BRANCH" != "main" ]; then
    log "SKIP: on branch '$BRANCH', not 'main'"
    exit 0
fi

# Pull remote changes (rebase to keep history clean)
if git pull --rebase 2>>"$LOG_FILE"; then
    log "PULL: success"
else
    log "PULL: failed — possible conflict, aborting rebase"
    git rebase --abort 2>/dev/null || true
    exit 1
fi

# Stage only tracked files that changed
git add -u

# Commit if there are staged changes
if ! git diff --cached --quiet; then
    git commit -m "auto-sync: $(date -u '+%Y-%m-%d %H:%M UTC')"
    log "COMMIT: changes committed"
else
    log "COMMIT: nothing to commit"
fi

# Push
if git push 2>>"$LOG_FILE"; then
    log "PUSH: success"
else
    log "PUSH: failed"
    exit 1
fi

log "SYNC: complete"
