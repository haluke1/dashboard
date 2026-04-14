#!/usr/bin/env python3
"""
snapshot.py — Take a snapshot of tabs + sessions + state and push to GitHub.

Called by:
- launchd timer (every minute)
- SessionStart / Stop hooks (via sync-and-push.sh)

Flow:
1. Fetch /tabs from local bridge (if online)
2. Write tabs.json (full categorized data, for read-only remote view)
3. Update state.json with live tab counts
4. Run sync-sessions.py to update sessions.json
5. Commit + push if anything changed
"""

import json
import subprocess
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

DASHBOARD = Path.home() / "dashboard"
BRIDGE = "http://127.0.0.1:7337"


def fetch_tabs():
    try:
        req = urllib.request.Request(BRIDGE + "/tabs", headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=8) as r:
            return json.loads(r.read())
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError, OSError):
        return None


def update_state_json(tabs_data):
    """Update live fields in state.json without clobbering manual edits."""
    path = DASHBOARD / "state.json"
    if not path.exists():
        return False
    try:
        s = json.loads(path.read_text())
    except json.JSONDecodeError:
        return False

    changed = False

    if tabs_data:
        if s.get("open_tabs") != tabs_data["total_tabs"]:
            s["open_tabs"] = tabs_data["total_tabs"]
            changed = True
        if s.get("open_tab_windows") != tabs_data["total_windows"]:
            s["open_tab_windows"] = tabs_data["total_windows"]
            changed = True

    # Always refresh updated_at
    s["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    if changed:
        path.write_text(json.dumps(s, indent=2))
    return changed


def write_tabs_json(tabs_data):
    """Write a compact tabs snapshot for the GitHub Pages (read-only) view."""
    if not tabs_data:
        return False
    path = DASHBOARD / "tabs.json"
    # Strip large per-tab arrays for the public snapshot (privacy + size)
    compact = {
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_tabs": tabs_data["total_tabs"],
        "total_windows": tabs_data["total_windows"],
        "duplicate_tabs": tabs_data["duplicate_tabs"],
        "bridge_online": True,
        "categories": [
            {
                "name": c["name"],
                "count": c["count"],
                "domain_count": len(c["domains"]),
                "top_domains": [
                    {"domain": d["domain"], "count": d["count"]}
                    for d in c["domains"][:5]  # top 5 domains per category
                ],
            }
            for c in tabs_data["categories"]
        ],
    }
    path.write_text(json.dumps(compact, indent=2))
    return True


def git_push_if_changed():
    """Commit any changes in the dashboard repo and push."""
    try:
        subprocess.run(["git", "-C", str(DASHBOARD), "add", "-A"], check=True, capture_output=True)
        # Are there staged changes?
        result = subprocess.run(
            ["git", "-C", str(DASHBOARD), "diff", "--cached", "--quiet"],
            capture_output=True,
        )
        if result.returncode == 0:
            return "no changes"
        msg = f"sync: auto-snapshot {datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}"
        subprocess.run(
            ["git", "-C", str(DASHBOARD), "commit", "-m", msg],
            check=True, capture_output=True
        )
        subprocess.run(
            ["git", "-C", str(DASHBOARD), "push", "origin", "main"],
            check=True, capture_output=True, timeout=30
        )
        return "pushed"
    except subprocess.CalledProcessError as e:
        return f"git error: {e.stderr.decode() if e.stderr else e}"
    except subprocess.TimeoutExpired:
        return "push timeout"


def main():
    tabs = fetch_tabs()
    wrote_tabs = write_tabs_json(tabs) if tabs else False
    updated_state = update_state_json(tabs)

    # Sync sessions
    try:
        subprocess.run(
            ["python3", str(DASHBOARD / "sync-sessions.py")],
            check=True, capture_output=True, timeout=15
        )
    except Exception:
        pass

    result = git_push_if_changed()
    print(f"[{datetime.now().strftime('%H:%M:%S')}] tabs={'online' if tabs else 'offline'} "
          f"wrote_tabs={wrote_tabs} state={updated_state} git={result}")


if __name__ == "__main__":
    main()
