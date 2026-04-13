#!/usr/bin/env python3
"""
sync-sessions.py — Scan all Claude Code session .jsonl files and build sessions.json

Reads the live .jsonl session files (which are updated during active sessions)
and extracts status, context, and metadata for the dashboard.

Called by:
- SessionStart hook (when a new Claude session begins)
- SessionEnd hook (when a session ends)
- Stop hook (after every response)
- Manual: python3 ~/dashboard/sync-sessions.py
"""

import json
import glob
import os
from datetime import datetime, timezone
from pathlib import Path

DASHBOARD_DIR = Path(__file__).parent
PROJECTS_DIR = Path.home() / ".claude" / "projects"
OUTPUT = DASHBOARD_DIR / "sessions.json"

ACTIVE_THRESHOLD_MIN = 5       # Modified in last 5 min = active
RECENT_THRESHOLD_HOURS = 24    # Modified in last day = recent


def parse_jsonl_session(path: Path):
    """Parse a .jsonl session file and extract summary info."""
    try:
        stat = path.stat()
    except OSError:
        return None

    mtime = stat.st_mtime
    size = stat.st_size

    session_id = path.stem  # filename without .jsonl
    first_prompt = None
    cwd = None
    git_branch = None
    permission_mode = None
    message_count = 0
    last_user_msg = None
    last_assistant_snippet = None

    try:
        with open(path, "r") as f:
            for line_num, line in enumerate(f):
                if not line.strip():
                    continue
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue

                t = d.get("type")
                if t == "permission-mode":
                    permission_mode = d.get("permissionMode")

                if "cwd" in d and d["cwd"]:
                    cwd = d["cwd"]
                if "gitBranch" in d and d["gitBranch"]:
                    git_branch = d["gitBranch"]

                if t == "user":
                    message_count += 1
                    msg = d.get("message", {})
                    content = msg.get("content", "")
                    if isinstance(content, list):
                        text_parts = [p.get("text", "") for p in content if isinstance(p, dict) and p.get("type") == "text"]
                        content = " ".join(text_parts)
                    if isinstance(content, str) and content.strip():
                        clean = content.strip()
                        if first_prompt is None:
                            first_prompt = clean
                        last_user_msg = clean

                elif t == "assistant":
                    message_count += 1
                    msg = d.get("message", {})
                    content = msg.get("content", "")
                    if isinstance(content, list):
                        text_parts = [p.get("text", "") for p in content if isinstance(p, dict) and p.get("type") == "text"]
                        content = " ".join(text_parts)
                    if isinstance(content, str) and content.strip():
                        last_assistant_snippet = content.strip()
    except OSError:
        return None

    now = datetime.now().timestamp()
    age_seconds = now - mtime
    age_min = age_seconds / 60

    if age_min < ACTIVE_THRESHOLD_MIN:
        status = "active"
    elif age_min < RECENT_THRESHOLD_HOURS * 60:
        status = "recent"
    else:
        status = "archived"

    def truncate(s, n):
        if s is None:
            return None
        s = " ".join(s.split())  # collapse whitespace
        return s[:n] + "…" if len(s) > n else s

    return {
        "id": session_id[:8],
        "full_id": session_id,
        "status": status,
        "project": cwd or "(unknown)",
        "git_branch": git_branch,
        "permission_mode": permission_mode,
        "first_prompt": truncate(first_prompt, 180),
        "last_user_msg": truncate(last_user_msg, 180),
        "last_assistant_snippet": truncate(last_assistant_snippet, 180),
        "message_count": message_count,
        "file_size_kb": round(size / 1024),
        "modified_ts": mtime,
        "modified_iso": datetime.fromtimestamp(mtime).isoformat(),
        "minutes_since_active": round(age_min, 1),
    }


def main():
    all_sessions = []
    for jsonl_path in glob.glob(str(PROJECTS_DIR / "*" / "*.jsonl")):
        info = parse_jsonl_session(Path(jsonl_path))
        if info:
            all_sessions.append(info)

    # Sort by most recent first
    all_sessions.sort(key=lambda s: s["modified_ts"], reverse=True)

    active = [s for s in all_sessions if s["status"] == "active"]
    recent = [s for s in all_sessions if s["status"] == "recent"][:25]
    archived_count = sum(1 for s in all_sessions if s["status"] == "archived")

    output = {
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "counts": {
            "active": len(active),
            "recent": len([s for s in all_sessions if s["status"] == "recent"]),
            "archived": archived_count,
            "total": len(all_sessions),
        },
        "active": active,
        "recent": recent,
    }

    OUTPUT.write_text(json.dumps(output, indent=2))
    print(f"✓ {output['counts']['active']} active, {output['counts']['recent']} recent, {archived_count} archived → {OUTPUT}")


if __name__ == "__main__":
    main()
