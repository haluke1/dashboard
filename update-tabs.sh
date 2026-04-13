#!/bin/bash
# Auto-update tab count in state.json
# Usage: ./update-tabs.sh

cd "$(dirname "$0")"

# Count Chrome tabs across all windows
read TABS WINDOWS <<< $(osascript <<'EOF'
tell application "Google Chrome"
  set windowCount to count of windows
  set tabTotal to 0
  repeat with i from 1 to windowCount
    set tabTotal to tabTotal + (count of tabs of window i)
  end repeat
  return tabTotal & " " & windowCount
end tell
EOF
)

if [ -z "$TABS" ]; then
  echo "Could not count tabs. Is Chrome running?"
  exit 1
fi

# Update state.json using python for safe JSON editing
python3 <<PYEOF
import json
from datetime import datetime, timezone

with open("state.json") as f:
    s = json.load(f)

s["open_tabs"] = $TABS
s["open_tab_windows"] = $WINDOWS
s["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

with open("state.json", "w") as f:
    json.dump(s, f, indent=2)

print(f"Updated: {$TABS} tabs across {$WINDOWS} windows")
PYEOF
