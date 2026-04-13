#!/bin/bash
# sync-and-push.sh — Sync sessions and push to GitHub
# Called by SessionStart and Stop hooks.
# Runs in background so it doesn't block Claude Code startup.

DASHBOARD="$HOME/dashboard"
LOCK="$DASHBOARD/.push.lock"

# If another push is in-flight, skip to avoid races
if [ -f "$LOCK" ]; then
  # If lock is older than 2 minutes, consider it stale and remove
  if [ "$(find "$LOCK" -mmin +2 2>/dev/null)" ]; then
    rm -f "$LOCK"
  else
    exit 0
  fi
fi

touch "$LOCK"
trap 'rm -f "$LOCK"' EXIT

cd "$DASHBOARD" || exit 0

# Sync sessions from .jsonl files
python3 sync-sessions.py > /tmp/dashboard-sync.log 2>&1

# Only push if there are changes
if git diff --quiet sessions.json state.json 2>/dev/null; then
  # No changes — nothing to push
  exit 0
fi

# Commit and push quietly
git add sessions.json state.json >> /tmp/dashboard-sync.log 2>&1
git commit -m "sync: auto-update sessions $(date +%Y-%m-%dT%H:%M:%S)" >> /tmp/dashboard-sync.log 2>&1
git push origin main >> /tmp/dashboard-sync.log 2>&1 &

# Detach push so we don't block
disown
exit 0
