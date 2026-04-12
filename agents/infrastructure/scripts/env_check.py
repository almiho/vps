#!/usr/bin/env python3
"""
Infrastructure Agent — Environment Health Check

Intelligence standard (mandatory for all agents):
- Never relay raw data. Form a conclusion and explain it.
- Interpret changes in the context of OUR specific setup.
- Tell the user what to DO, not just what EXISTS.
- Admit uncertainty explicitly when facts are missing.
- Always answer: "What does this mean for me? Is it risky? What should I do?"
"""

import json, os, subprocess, urllib.request
from datetime import datetime

WORKSPACE    = "/home/node/.openclaw/workspace"
STATUS_PATH  = f"{WORKSPACE}/agents/infrastructure/dashboard/status.json"
ROADMAP_PATH = f"{WORKSPACE}/docs/ROADMAP.md"

def run(cmd):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        return r.stdout.strip()
    except:
        return ""

def check_openclaw_version():
    ver_out = run("openclaw --version 2>&1")
    current = ver_out.split()[-1] if ver_out else "unknown"
    try:
        with urllib.request.urlopen(
            "https://api.github.com/repos/openclaw/openclaw/releases/latest", timeout=5
        ) as r:
            d = json.load(r)
            return current, d.get("tag_name","").lstrip("v"), d.get("body",""), d.get("published_at","")[:10], d.get("prerelease",False)
    except:
        return current, None, "", "", False

def analyse_release(notes):
    """
    For each relevant change: form a conclusion for OUR setup.
    Answer: will this help us, hurt us, or need action? Be specific. Admit gaps.
    """
    n = notes.lower()
    findings = []

    if "memory" in n or "memory-wiki" in n:
        if "chatgpt import" in n or "imported insights" in n or "memory palace" in n:
            findings.append({
                "label": "Memory/wiki — ChatGPT import + Memory Palace tab",
                "verdict": "✅ Worth exploring after update",
                "lines": [
                    "Adds ability to import ChatGPT conversation history into AlexI's memory.",
                    "New 'Memory Palace' tab gives better visibility into what AlexI remembers.",
                    "My assessment: this directly improves AlexI's continuity — relevant to us.",
                    "No breaking changes expected to existing memory files.",
                    "→ Action: after updating, check the new Memory Palace tab in the control panel."
                ]
            })
        else:
            findings.append({
                "label": "Memory/wiki changes (details unclear in release notes)",
                "verdict": "⚠️ Monitor after update",
                "lines": [
                    "Memory system was modified but the changelog is vague on specifics.",
                    "I cannot confirm whether this helps or changes existing behaviour.",
                    "→ Action: after updating, verify MEMORY.md is intact and AlexI responds normally.",
                    "→ If memory feels off, check: /home/node/.openclaw/workspace/MEMORY.md"
                ]
            })

    if "telegram" in n:
        findings.append({
            "label": "Telegram changes",
            "verdict": "⚠️ Test immediately after updating",
            "lines": [
                "Telegram is our only active channel — any breakage here stops all communication.",
                "Release notes don't specify what changed (I don't have more detail than this).",
                "Risk if it breaks: you lose Telegram access to AlexI until fixed.",
                "→ Action: immediately after updating, send a test message via Telegram.",
                "→ If it fails: openclaw channels status — then openclaw gateway restart."
            ]
        })

    if "gateway" in n:
        findings.append({
            "label": "Gateway changes",
            "verdict": "🔴 Higher risk — update during a quiet moment",
            "lines": [
                "The gateway handles ALL traffic: Telegram, agent sessions, cron jobs.",
                "If it breaks, everything stops — agents, dashboard, Telegram alerts.",
                "Specific change details not in release summary — I can't tell you exactly what shifted.",
                "My assessment: treat as medium risk. Update when you have 5 min to test, not mid-day.",
                "→ Immediately after: openclaw gateway status — expect 'RPC probe: ok'.",
                "→ If it fails: openclaw gateway restart"
            ]
        })

    if "agent" in n and any(kw in n for kw in ["runtime","turn","session","acp"]):
        findings.append({
            "label": "Agent runtime/session changes",
            "verdict": "⚠️ Test active agents after updating",
            "lines": [
                "Changes to agent sessions affect how Infra and all future agents run.",
                "Most likely improvement (not breaking) but I cannot confirm without more detail.",
                "→ Action: after updating, send a test message to the infrastructure agent.",
                "→ If sessions feel broken, clear session cache: rm ~/.openclaw/agents/*/sessions/*.jsonl"
            ]
        })

    if "cron" in n:
        findings.append({
            "label": "Cron scheduler changes",
            "verdict": "⚠️ Verify jobs still running after update",
            "lines": [
                "We have 2 active cron jobs: dashboard regeneration (15 min) and env check (1 hr).",
                "Cron changes could affect job scheduling or delivery.",
                "→ Action: after updating, run: openclaw cron list",
                "→ Check both jobs are enabled and next run times look correct."
            ]
        })

    if "embed" in n:
        findings.append({
            "label": "New [embed ...] output tag",
            "verdict": "✅ Low priority — note for future",
            "lines": [
                "New capability for rendering rich content inline in agent responses.",
                "Not relevant to our current setup (we use our own HTML dashboard).",
                "Could be useful later when building richer agent interactions.",
                "→ No action needed now."
            ]
        })

    if "whatsapp" in n:
        findings.append({
            "label": "WhatsApp changes",
            "verdict": "✅ Relevant for Milestone 4",
            "lines": [
                "WhatsApp integration is planned for our Comms Router (Milestone 4).",
                "Worth noting what changed now so we can plan accordingly.",
                "I don't have the specific details of what changed (not in release notes summary).",
                "→ Action: review full WhatsApp changelog when we reach Milestone 4."
            ]
        })

    irr = []
    for kw, label in [("feishu","Feishu"),("video_generate","Video generation"),("discord","Discord")]:
        if kw in n:
            irr.append(label)

    has_critical = any(kw in n for kw in ["gateway","breaking change","agent turn","acp"])
    risk = "MEDIUM" if has_critical else "LOW"
    risk_note = "Contains changes to core infrastructure (gateway/agent runtime) — read notes carefully and test thoroughly" if risk == "MEDIUM" else "No core infrastructure changes detected — relatively safe to update, but always test Telegram channel immediately after"

    return findings, irr, risk, risk_note

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
        findings, irr, risk, risk_note = analyse_release(notes)

        body_lines = [
            f"{'🔴' if risk == 'MEDIUM' else '🟡'} Risk: {risk} — {risk_note}",
            ""
        ]

        for f in findings:
            body_lines.append(f"{'—'*40}")
            body_lines.append(f"{f['verdict']}  |  {f['label']}")
            for line in f['lines']:
                body_lines.append(f"  {line}")
            body_lines.append("")

        if irr:
            body_lines.append(f"❌ Not relevant for us: {', '.join(irr)}")

        alerts.append(build_alert(2,
            f"OpenClaw {current} → {latest}  (released {date})",
            body_lines
        ))
        health = "warning"

    # 2. Gateway
    if not check_gateway():
        alerts.append(build_alert(1, "Gateway not responding", [
            "⚠️ RPC probe failed — gateway may be down.",
            "All agent communication and Telegram routing is affected.",
            "→ Check status: openclaw gateway status",
            "→ If down: openclaw gateway start"
        ], action_required=True))
        health = "error"

    # 3. Web server
    if not check_web_server():
        alerts.append(build_alert(1, "Dashboard web server not reachable", [
            "⚠️ http://100.67.100.125:8080/ is not responding.",
            "The dashboard is inaccessible from Tailscale devices.",
            "→ Restart: cd /home/node/.openclaw/workspace/dashboard",
            "→ Run: nohup python3 -m http.server 8080 --bind 100.67.100.125 &"
        ], action_required=True))
        if health != "error": health = "warning"

    # 4. Disk
    disk = check_disk()
    if disk and disk > 80:
        critical = disk > 90
        alerts.append(build_alert(1 if critical else 2,
            f"Disk usage: {disk}% {'— Critical' if critical else '— Getting high'}",
            [
                f"{'🔴 Critical' if critical else '⚠️ High'} disk usage at {disk}%.",
                f"{'Immediate action needed' if critical else 'Monitor and clean up soon'} to avoid storage issues.",
                "→ Check logs: du -sh /home/node/.openclaw/workspace/logs/",
                "→ Consider: rm /home/node/.openclaw/workspace/logs/*/*.log (keep last 7 days)"
            ], action_required=critical))
        if health == "ok": health = "warning"

    # 5. Bus
    if not check_bus():
        alerts.append(build_alert(1, "SQLite message bus missing", [
            "🔴 data/bus.db not found — this is critical.",
            "Agent communication is broken without the message bus.",
            "→ Re-run Milestone 1 setup immediately."
        ], action_required=True))
        health = "error"

    # Summary — always name the actual issue, never use vague counts
    n_action = len([a for a in alerts if a.get("action_required")])
    if health == "ok":
        summary = "All systems healthy. Milestones 0–2 complete."
    elif health == "warning":
        # Name the first alert, not just a count
        first = alerts[0]["title"] if alerts else "unknown issue"
        summary = f"Review needed: {first}" + (f" (+{len(alerts)-1} more)" if len(alerts) > 1 else "")
    else:
        # Name the critical issue directly
        critical = [a for a in alerts if a.get("action_required")]
        first = critical[0]["title"] if critical else alerts[0]["title"]
        summary = f"Action needed: {first}" + (f" (+{n_action-1} more)" if n_action > 1 else "")

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
