#!/usr/bin/env python3
"""
Infrastructure Agent — Environment Health Check
Runs periodically, updates status.json with intelligent assessments.
"""

import json
import os
import subprocess
import urllib.request
from datetime import datetime

WORKSPACE = "/home/node/.openclaw/workspace"
STATUS_PATH = f"{WORKSPACE}/agents/infrastructure/dashboard/status.json"
ROADMAP_PATH = f"{WORKSPACE}/docs/ROADMAP.md"

def run(cmd):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        return r.stdout.strip()
    except:
        return ""

def analyse_release(notes):
    """Reason about release notes for THIS specific setup. No raw dumps."""
    n = notes.lower()
    relevant, irrelevant = [], []
    checks = [
        ("memory",    "Memory/wiki enhancements",   True,  "Could improve AlexI's long-term memory"),
        ("telegram",  "Telegram changes",            True,  "Our primary channel — worth reviewing"),
        ("gateway",   "Gateway changes",             True,  "Core infra — review carefully before updating"),
        ("agent",     "Agent runtime changes",       True,  "Affects how all our agents run"),
        ("cron",      "Cron scheduler changes",      True,  "We rely on cron for dashboard + env checks"),
        ("embed",     "New embed/output tags",       True,  "Potentially useful for our HTML dashboard"),
        ("whatsapp",  "WhatsApp changes",            True,  "Planned for Milestone 4 — good to know"),
        ("chatgpt",   "ChatGPT import",              True,  "Could help migrate existing conversations to AlexI"),
        ("feishu",    "Feishu",                      False, "not used"),
        ("video",     "Video generation",            False, "not used"),
        ("discord",   "Discord",                    False, "not our primary channel"),
    ]
    for kw, label, is_rel, context in checks:
        if kw in n:
            (relevant if is_rel else irrelevant).append(f"{label} ({context})")
    parts = []
    if relevant:
        parts.append("Relevant to our setup: " + "; ".join(relevant))
    if irrelevant:
        parts.append("Not relevant for us: " + ", ".join(irrelevant))
    if not parts:
        parts.append("No changes directly affecting our current setup")
    return ". ".join(parts)

def check_openclaw_version():
    current = run("openclaw --version 2>&1 | grep -oP '\\d{4}\\.\\d+\\.\\d+'")
    try:
        with urllib.request.urlopen(
            "https://api.github.com/repos/openclaw/openclaw/releases/latest",
            timeout=5
        ) as r:
            data = json.load(r)
            latest = data.get("tag_name","").lstrip("v")
            notes = data.get("body","")
            date = data.get("published_at","")[:10]
            prerelease = data.get("prerelease", False)
            return current, latest, notes, date, prerelease
    except:
        return current, None, "", "", False

def check_gateway():
    result = run("openclaw gateway status 2>&1 | grep 'RPC probe'")
    return "ok" in result.lower()

def check_disk():
    result = run("df -h /home/node/.openclaw 2>/dev/null | tail -1")
    if result:
        parts = result.split()
        if len(parts) >= 5:
            pct = int(parts[4].rstrip('%'))
            return pct
    return None

def check_web_server():
    try:
        with urllib.request.urlopen("http://100.67.100.125:8080/", timeout=3) as r:
            return r.status == 200
    except:
        return False

def check_bus():
    bus = f"{WORKSPACE}/data/bus.db"
    return os.path.exists(bus)

def load_roadmap_milestones():
    """Extract pending milestones from ROADMAP.md"""
    upcoming = []
    priority = 1
    try:
        with open(ROADMAP_PATH) as f:
            content = f.read()
        for line in content.split('\n'):
            if line.startswith('## Milestone') and '⏳' in line:
                title = line.replace('## ', '').replace('⏳', '').strip()
                # Remove the emoji markers
                title = title.replace('*"', '').replace('"*', '').strip()
                upcoming.append({"priority": min(priority, 4), "title": title, "due_at": None})
                priority += 1
    except:
        pass
    return upcoming[:6]

def main():
    now = datetime.now().isoformat()
    alerts = []
    health = "ok"

    # 1. OpenClaw version check
    current, latest, notes, date, prerelease = check_openclaw_version()
    if latest and current and latest != current and not prerelease:
        analysis = analyse_release(notes)
        # Assess risk based on what's changing
        n = notes.lower()
        has_gateway = "gateway" in n
        has_agent_runtime = "agent runtime" in n or "agent turn" in n
        risk = "MEDIUM — review gateway/agent changes before updating" if (has_gateway or has_agent_runtime) else "LOW — safe to update at next maintenance window"
        alerts.append({
            "priority": 2,
            "title": f"OpenClaw update available: {current} → {latest} (released {date})",
            "body": f"Risk: {risk}. {analysis}.",
            "due_at": None,
            "action_required": False
        })
        health = "warning"

    # 2. Gateway check
    if not check_gateway():
        alerts.append({
            "priority": 1,
            "title": "OpenClaw gateway not responding",
            "body": "RPC probe failed. Gateway may be down. Check with: openclaw gateway status",
            "due_at": None,
            "action_required": True
        })
        health = "error"

    # 3. Web server check
    if not check_web_server():
        alerts.append({
            "priority": 1,
            "title": "Dashboard web server not responding",
            "body": "http://100.67.100.125:8080/ is not reachable. Restart with: cd /home/node/.openclaw/workspace/dashboard && nohup python3 -m http.server 8080 --bind 100.67.100.125 &",
            "due_at": None,
            "action_required": True
        })
        if health != "error":
            health = "warning"

    # 4. Disk usage
    disk_pct = check_disk()
    if disk_pct and disk_pct > 80:
        alerts.append({
            "priority": 2,
            "title": f"Disk usage high: {disk_pct}%",
            "body": "Consider cleaning logs or old data before it becomes critical.",
            "due_at": None,
            "action_required": disk_pct > 90
        })
        if health == "ok":
            health = "warning"

    # 5. Message bus check
    if not check_bus():
        alerts.append({
            "priority": 1,
            "title": "SQLite message bus missing",
            "body": "data/bus.db not found. Run Milestone 1 setup.",
            "due_at": None,
            "action_required": True
        })
        health = "error"

    # Summary
    if health == "ok":
        summary = "All systems healthy. Milestones 0-2 complete."
    elif health == "warning":
        summary = f"Systems OK with {len(alerts)} item(s) needing attention."
    else:
        summary = f"⚠️ {len([a for a in alerts if a['action_required']])} issue(s) require immediate attention."

    # Load roadmap upcoming items
    upcoming = load_roadmap_milestones()

    status = {
        "agent": "infrastructure",
        "updated_at": now,
        "health": health,
        "summary": summary,
        "alerts": alerts,
        "upcoming": upcoming
    }

    with open(STATUS_PATH, "w") as f:
        json.dump(status, f, indent=2)

    print(f"✅ Infra env check complete — health: {health}, alerts: {len(alerts)}")

if __name__ == "__main__":
    main()
