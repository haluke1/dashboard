# Haluk Command Center

Live dashboard for tracking focus, inbox, tabs, projects, and AEQ progression.

**Live URL:** https://haluke1.github.io/dashboard/

## How It Works

- `index.html` — the dashboard UI (static, no build step)
- `state.json` — the single source of truth for all metrics
- Any Claude Code session can update `state.json` and push to GitHub
- GitHub Pages serves it; changes go live in ~30 seconds

## Updating from a Claude Code Session

Any session can say: "update the dashboard" and I will:
1. Edit `~/dashboard/state.json`
2. Commit + push to GitHub
3. Tell you the changes are live

## What to Update

| Field | When |
|---|---|
| `today_focus` | Every morning — ONE thing |
| `inbox_count` | After every triage |
| `days_since_last_triage` | Reset to 0 after triage |
| `open_tabs` | After tab purges |
| `current_projects` | When projects change status |
| `recent_shipped` | After every shipped artifact |
| `aeq_score` | Weekly |

## File Structure

```
dashboard/
├── index.html        # UI — pure HTML/CSS/JS, no build
├── state.json        # Data — edit this to change dashboard
├── update-tabs.sh    # Script to auto-update tab count
└── README.md         # This file
```
