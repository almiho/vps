#!/usr/bin/env python3
"""
Infrastructure Agent — Environment Health Check
Runs periodically, updates status.json with structured, readable assessments.
Intelligence standard: never relay raw data — summarise, contextualise, recommend.
"""

import json, os, subprocess, urllib.request
from datetime import datetime

WORKSPACE   = "/home/node/.openclaw/workspace"
STATUS_PATH = f"{WORKSPACE}/agents/infrastructure/dashboard/status.json"
ROADMAP_PATH= f"{WORKSPACE}/docs/ROADMAP.md"

def run(cmd):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        return r.stdout.strip()
    except:
        return ""

def check_openclaw_version():
    current = run("openclaw --version 2>&1").split()[-1] if run("openclaw --version 2>&1") else "?"
    try:
        with urllib.request.urlopen(
            "https://api.github.com/repos/openclaw/openclaw/releases/latest", timeout=5
        ) as r:
            d = json.load(r)
            return current, d.get("tag_name","").lstrip("v"), d.get("body",""), d.get("published_at","")[:10], d.get("prerelease",False)
    except:
        return current, None, "", "", False

def analyse_release(notes):
    """Return structured analysis: relevant list, irrelevant list, risk level."""
    n = notes.lower()
    rel, irr = [], []
    for kw, label, reason in [
        ("memory",   "Memory/wiki",        "could improve AlexI's long-term memory"),
        ("telegram", "Telegram",           "our primary channel — worth testing after update"),
        ("gateway",  "Gateway",            "core infra — review release notes carefully"),
        ("agent",    "Agent runtime",      "affects how all our agents run"),
        ("cron",     "Cron scheduler",     "we rely on cron for automation"),
        ("embed",    "New embed tags",     "potentially useful for our HTML dashboard"),
        ("whatsapp", "WhatsApp",           "planned for Milestone 4"),
        ("chatgpt",  "ChatGPT import",     "could migrate existing conversations to AlexI"),
    ]:
        if kw in n:
            rel.append({"label": label, "reason": reason})
    for kw, label in [("feishu","Feishu"),("video","Video generation"),("discord","Discord")]:
        if kw in n:
            irr.append(label)
    has_core_changes = any(kw in n for kw in ["gateway","agent runtime","agent turn","breaking"])
    risk = "MEDIUM" if has_core_changes else "LOW"
    risk_note = "Review gateway/agent changes before updating" if risk == "MEDIUM" else "Safe to update at next maintenance window — no urgency"
    return rel, irr, risk, risk_note

def check_gateway():
    return "ok" in run("openclaw gateway status 2>&1 | grep 'RPC probe'").lower()

def check_disk():
    r = run("df -h /home/node/.openclaw 2>/dev/null | tail -1")
    if r:
        parts = r.split()
        if len(parts) >= 5:
            try: return int(parts[4].rstrip('%'))
            except: pass
    return None

def check_web_server():
    try:
        with urllib.request.urlopen("http://100.67.100.125:8080/", timeout=3) as r:
            return r.status == 200
    except:
        return False

def check_bus():
    return os.path.exists(f"{WORKSPACE}/data/bus.db")

def load_roadmap_milestones():
    upcoming, priority = [], 1
    try:
        with open(ROADMAP_PATH) as f:
            for line in f:
                if line.startswith('## Milestone') and '⏳' in line:
                    title = line.replace('## ','').replace('⏳','').strip().strip('*"')
                    upcoming.append({"priority": min(priority,4), "title": title, "due_at": None})
                    priority += 1
    except: pass
    return upcoming[:6]

def build_alert(priority, title, lines, action_required=False, due_at=None):
    """Build a structured alert with a body that renders as clean bullet lines."""
    return {
        "priority": priority,
        "title": title,
        "body": "\n".join(lines),
        "due_at": due_at,
        "action_required": action_required
    }

def main():
    now = datetime.now().isoformat()
    alerts, health = [], "ok"

    # 1. OpenClaw version
    current, latest, notes, date, prerelease = check_openclaw_version()
    if latest and current and latest != current and not prerelease:
        rel, irr, risk, risk_note = analyse_release(notes)
        lines = [f"🟡 Risk: {risk} — {risk_note}"]
        if rel:
            lines.append("")
            lines.append("✅ Relevant to our setup:")
            for item in rel:
                lines.append(f"  • {item['label']} — {item['reason']}")
        if irr:
            lines.append("")
            lines.append(f"❌ Not relevant for us: {', '.join(irr)}")
        alerts.append(build_alert(2,
            f"OpenClaw {current} → {latest}  (released {date})",
            lines
        ))
        health = "warning"

    # 2. Gateway
    if not check_gateway():
        alerts.append(build_alert(1, "Gateway not responding", [
            "⚠️ RPC probe failed — gateway may be down",
            "→ Run: openclaw gateway status",
            "→ If down: openclaw gateway start"
        ], action_required=True))
        health = "error"

    # 3. Web server
    if not check_web_server():
        alerts.append(build_alert(1, "Dashboard web server not reachable", [
            "⚠️ http://100.67.100.125:8080/ not responding",
            "→ Restart: cd /home/node/.openclaw/workspace/dashboard",
            "→ Run: nohup python3 -m http.server 8080 --bind 100.67.100.125 &"
        ], action_required=True))
        if health != "error": health = "warning"

    # 4. Disk
    disk = check_disk()
    if disk and disk > 80:
        alerts.append(build_alert(2 if disk <= 90 else 1,
            f"Disk usage: {disk}%",
            [
                f"{'⚠️ High' if disk <= 90 else '🔴 Critical'} disk usage at {disk}%",
                "→ Check logs: du -sh /home/node/.openclaw/workspace/logs/",
                "→ Consider pruning old logs or rotating databases"
            ], action_required=disk > 90))
        if health == "ok": health = "warning"

    # 5. Message bus
    if not check_bus():
        alerts.append(build_alert(1, "SQLite message bus missing", [
            "🔴 data/bus.db not found",
            "→ Re-run Milestone 1 setup"
        ], action_required=True))
        health = "error"

    # Summary
    n_action = len([a for a in alerts if a.get("action_required")])
    if health == "ok":
        summary = "All systems healthy. Milestones 0–2 complete."
    elif health == "warning":
        summary = f"{len(alerts)} item(s) to review — no immediate action required."
    else:
        summary = f"⚠️ {n_action} issue(s) need immediate attention."

    status = {
        "agent": "infrastructure",
        "updated_at": now,
        "health": health,
        "summary": summary,
        "alerts": alerts,
        "upcoming": load_roadmap_milestones()
    }

    with open(STATUS_PATH, "w") as f:
        json.dump(status, f, indent=2)

    print(f"✅ Infra env check — health: {health}, alerts: {len(alerts)}")

if __name__ == "__main__":
    main()
