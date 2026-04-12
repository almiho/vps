#!/usr/bin/env python3
"""
AlexI (Chief of Staff) — Status Updater
Writes current status to dashboard/status.json.
Reflects real activity: sessions, cron jobs, milestones, pending items.
"""

import json, os, subprocess
from datetime import datetime

WORKSPACE   = "/home/node/.openclaw/workspace"
STATUS_PATH = f"{WORKSPACE}/agents/cos/dashboard/status.json"
STATUS_MD   = f"{WORKSPACE}/STATUS.md"

def run(cmd):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        return r.stdout.strip()
    except:
        return ""

def get_cron_jobs():
    out = run("openclaw cron list 2>/dev/null")
    jobs = []
    for line in out.split('\n'):
        if 'every' in line.lower() or 'at ' in line.lower():
            parts = line.split()
            if len(parts) >= 3:
                jobs.append(parts[1] if len(parts) > 1 else line.strip())
    return jobs

def get_milestone_status():
    """Read STATUS.md to get current milestone."""
    try:
        with open(STATUS_MD) as f:
            content = f.read()
        for line in content.split('\n'):
            if 'Where we are' in line:
                continue
            if '**Milestone' in line:
                return line.strip().lstrip('#').strip()
    except:
        pass
    return "Planning phase complete"

def get_bus_stats():
    """Check message bus for any pending items."""
    try:
        import sqlite3
        db = sqlite3.connect(f"{WORKSPACE}/data/bus.db")
        pending = db.execute("SELECT COUNT(*) FROM messages WHERE status='pending'").fetchone()[0]
        total = db.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
        db.close()
        return pending, total
    except:
        return 0, 0

def main():
    now = datetime.now().isoformat()
    milestone = get_milestone_status()
    pending_msgs, total_msgs = get_bus_stats()
    cron_jobs = get_cron_jobs()

    alerts = []

    # Flag if OKR onboarding hasn't happened yet
    okr_done = os.path.exists(f"{WORKSPACE}/agents/cos/data/okrs.json")
    if not okr_done:
        alerts.append({
            "priority": 2,
            "title": "OKR onboarding not yet done",
            "body": "CoS cannot prioritise tasks without defined OKRs.\nThis is the most critical first step before the GTD layer can work.\n→ Schedule an OKR session with Alexander when ready for Milestone 5.",
            "due_at": None,
            "action_required": False
        })

    # Flag pending messages
    if pending_msgs > 0:
        alerts.append({
            "priority": 2,
            "title": f"{pending_msgs} pending message(s) in bus",
            "body": f"{pending_msgs} of {total_msgs} messages waiting to be processed.\nNo domain agents active yet — messages will queue until Milestone 6+.\n→ No action needed now, but worth knowing.",
            "due_at": None,
            "action_required": False
        })

    upcoming = [
        {"priority": 1, "title": "Milestone 3: Monitoring Agent — system health + Telegram alerts", "due_at": None},
        {"priority": 2, "title": "Milestone 5: OKR onboarding — define goals before GTD layer activates", "due_at": None},
        {"priority": 2, "title": "Milestone 4: Comms Router — Gmail/WhatsApp → SQLite bus", "due_at": None},
        {"priority": 3, "title": "Milestone 6: School Agent — first domain agent", "due_at": None},
    ]

    # Build summary
    summary_parts = [f"Active. {milestone}."]
    if cron_jobs:
        summary_parts.append(f"{len(cron_jobs)} scheduled job(s) running.")
    if pending_msgs > 0:
        summary_parts.append(f"{pending_msgs} message(s) queued in bus.")

    status = {
        "agent": "cos",
        "updated_at": now,
        "health": "ok" if not alerts else "warning",
        "summary": " ".join(summary_parts),
        "stats": {
            "active_cron_jobs": len(cron_jobs),
            "bus_pending": pending_msgs,
            "bus_total": total_msgs,
            "okr_onboarding_done": okr_done
        },
        "alerts": alerts,
        "upcoming": upcoming
    }

    os.makedirs(os.path.dirname(STATUS_PATH), exist_ok=True)
    with open(STATUS_PATH, "w") as f:
        json.dump(status, f, indent=2)

    print(f"✅ CoS status updated — health: {status['health']}")

if __name__ == "__main__":
    main()
