#!/usr/bin/env python3
"""
Watch — Monitoring Agent
Checks system health, updates status.json, sends Telegram alerts when needed.

Intelligence standard: don't report metrics, interpret them.
Silent when healthy. Loud when it matters.
"""

import json, os, sqlite3, subprocess, sys, urllib.request, urllib.parse
from datetime import datetime, timezone

sys.path.insert(0, "/home/node/.openclaw/workspace/scripts")
from agent_logger import AgentLogger

WORKSPACE    = "/home/node/.openclaw/workspace"
STATUS_PATH  = f"{WORKSPACE}/agents/monitoring/dashboard/status.json"
log = AgentLogger("monitoring")
ALERT_LOG    = f"{WORKSPACE}/agents/monitoring/data/alerts.jsonl"
AGENTS_DIR   = f"{WORKSPACE}/agents"
PREV_STATE   = f"{WORKSPACE}/agents/monitoring/data/prev_state.json"

# Telegram delivery via OpenClaw CLI
def send_telegram_alert(title, body):
    """Send urgent alert to Alexander via Telegram.
    Non-blocking: fires in a background thread so Watch never freezes.
    Alert is always logged to disk first regardless of delivery outcome.
    """
    import threading
    msg = f"Watch Alert: {title}\n\n{body}\n\nDashboard: http://100.67.100.125:8080/monitoring.html"

    # Always log to disk immediately (fast, reliable)
    os.makedirs(os.path.dirname(ALERT_LOG), exist_ok=True)
    with open(ALERT_LOG, "a") as f:
        f.write(json.dumps({"type": "alert_fired", "title": title, "logged_at": datetime.now().isoformat()}) + "\n")

    def deliver():
        try:
            # Direct message send — no AI agent, no interpretation, just delivery
            result = subprocess.run(
                ["openclaw", "message", "send",
                 "--channel", "telegram",
                 "--target", "8731775067",
                 "--message", msg],
                capture_output=True, text=True, timeout=15
            )
            outcome = "delivered" if result.returncode == 0 else f"failed: {result.stderr[:100]}"
        except Exception as e:
            outcome = f"exception: {e}"
        with open(ALERT_LOG, "a") as f:
            f.write(json.dumps({"type": "delivery_outcome", "title": title, "outcome": outcome, "logged_at": datetime.now().isoformat()}) + "\n")

    # Fire and forget in background thread
    t = threading.Thread(target=deliver, daemon=True)
    t.start()
    return True  # Watch continues immediately

def run(cmd):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        return r.stdout.strip()
    except:
        return ""

def load_prev_state():
    try:
        with open(PREV_STATE) as f:
            return json.load(f)
    except:
        return {}

def save_state(state):
    os.makedirs(os.path.dirname(PREV_STATE), exist_ok=True)
    with open(PREV_STATE, "w") as f:
        json.dump(state, f, indent=2)

def log_alert(alert):
    os.makedirs(os.path.dirname(ALERT_LOG), exist_ok=True)
    with open(ALERT_LOG, "a") as f:
        f.write(json.dumps({**alert, "logged_at": datetime.now().isoformat()}) + "\n")

# ── Checks ────────────────────────────────────────────────────────────────

def check_gateway():
    out = run("openclaw gateway status 2>&1")
    ok = "rpc probe: ok" in out.lower()
    if ok:
        return {"name": "gateway", "ok": True, "detail": "RPC probe OK — gateway healthy"}

    # Probe failed — investigate before concluding
    proc = run("pgrep -f 'openclaw' 2>/dev/null | wc -l").strip()
    proc_count = int(proc) if proc.isdigit() else 0

    # Check if web server is still up (separate service, helps assess scope)
    try:
        import urllib.request as _ur
        with _ur.urlopen("http://100.67.100.125:8080/", timeout=3) as r:
            web_ok = r.status == 200
    except Exception:
        web_ok = False

    # Check recent scheduler log for gateway errors
    recent = run("tail -20 /home/node/.openclaw/workspace/logs/scheduler.log 2>/dev/null")
    recent_errors = [l for l in recent.splitlines() if "gateway" in l.lower() or "error" in l.lower()]

    # Build an evidence-based diagnosis
    if proc_count > 0 and web_ok:
        detail = (
            f"RPC probe failed, but {proc_count} openclaw process(es) running and web server reachable. "
            "Assessment: likely a transient connectivity blip, not a full outage. "
            "Will self-resolve — if it persists next cycle, escalate. "
            "→ If it recurs: openclaw gateway restart"
        )
        if recent_errors:
            detail += f"\nRecent log hint: {recent_errors[-1].strip()}"
    elif proc_count == 0:
        detail = (
            "RPC probe failed and no openclaw processes found — gateway appears completely stopped. "
            "Assessment: full outage, this needs immediate attention. "
            "→ Start gateway: openclaw gateway start"
        )
    elif not web_ok:
        detail = (
            "RPC probe failed and web server also unreachable. "
            "Assessment: broad connectivity failure or full service crash. "
            f"openclaw processes running: {proc_count}. "
            "→ Check: openclaw gateway status | then: openclaw gateway restart"
        )
    else:
        detail = (
            f"RPC probe failed. Process count: {proc_count}, web server: {'up' if web_ok else 'down'}. "
            "Unable to form a confident diagnosis from available signals. "
            "→ Run manually: openclaw gateway status"
        )

    return {"name": "gateway", "ok": False, "detail": detail}

def check_web_server():
    try:
        with urllib.request.urlopen("http://100.67.100.125:8080/", timeout=5) as r:
            ok = r.status == 200
    except Exception:
        ok = False

    if ok:
        return {"name": "web_server", "ok": True, "detail": "Dashboard reachable at http://100.67.100.125:8080/"}

    # Not reachable — investigate
    proc = run("pgrep -f 'http.server' 2>/dev/null").strip()
    proc_running = bool(proc)
    recent = run("tail -5 /home/node/.openclaw/workspace/logs/webserver.log 2>/dev/null")

    if not proc_running:
        detail = (
            "Dashboard unreachable at :8080 and web server process not found — it has stopped. "
            "Assessment: process crashed or was never started. "
            "→ Restart: cd /home/node/.openclaw/workspace/dashboard && "
            "nohup python3 -m http.server 8080 --bind 100.67.100.125 &"
        )
    else:
        detail = (
            f"Dashboard unreachable at :8080, but web server process is running (PID {proc}). "
            "Assessment: process alive but not responding — may be hung or bound to wrong address. "
            "→ Kill and restart: kill " + proc + " && cd /home/node/.openclaw/workspace/dashboard && "
            "nohup python3 -m http.server 8080 --bind 100.67.100.125 &"
        )
        if recent:
            detail += f"\nLast log entry: {recent.splitlines()[-1].strip()}"

    return {"name": "web_server", "ok": False, "detail": detail}

def check_bus():
    bus = f"{WORKSPACE}/data/bus.db"
    if not os.path.exists(bus):
        return {"name": "bus", "ok": False, "detail": "bus.db missing entirely"}
    try:
        db = sqlite3.connect(bus)
        db.execute("SELECT COUNT(*) FROM messages").fetchone()
        pending = db.execute("SELECT COUNT(*) FROM messages WHERE status='pending'").fetchone()[0]
        stuck = db.execute(
            "SELECT COUNT(*) FROM messages WHERE status='processing' AND datetime(updated_at) < datetime('now','-1 hour')"
        ).fetchone()[0]
        db.close()
        if stuck > 0:
            return {"name": "bus", "ok": False, "stuck": stuck,
                    "detail": f"{stuck} message(s) stuck in 'processing' for >1hr — possible agent crash"}
        detail = f"Healthy. {pending} pending message(s) queued." if pending > 0 else "Healthy. No pending messages."
        return {"name": "bus", "ok": True, "pending": pending, "detail": detail}
    except Exception as e:
        return {"name": "bus", "ok": False, "detail": f"Cannot read bus: {e}"}

def check_disk():
    out = run("df -h /home/node/.openclaw 2>/dev/null | tail -1")
    if not out:
        return {"name": "disk", "ok": True, "detail": "Could not read disk stats"}
    parts = out.split()
    if len(parts) < 5:
        return {"name": "disk", "ok": True, "detail": "Disk stats unreadable"}
    try:
        pct = int(parts[4].rstrip('%'))
        used = parts[2]
        avail = parts[3]
    except:
        return {"name": "disk", "ok": True, "detail": "Could not parse disk stats"}

    if pct >= 90:
        return {"name": "disk", "ok": False, "pct": pct,
                "detail": f"Critical: {pct}% used ({avail} free). Immediate cleanup needed."}
    elif pct >= 80:
        return {"name": "disk", "ok": True, "warn": True, "pct": pct,
                "detail": f"Warning: {pct}% used ({avail} free). Monitor closely."}
    else:
        return {"name": "disk", "ok": True, "pct": pct,
                "detail": f"{pct}% used ({used} of total, {avail} free). Healthy."}

def check_agent_heartbeats():
    """Check if active agents have updated their status recently."""
    active_agents = ["infrastructure", "cos", "dashboard"]
    issues = []
    healthy = []
    now = datetime.now(timezone.utc)

    for name in active_agents:
        path = f"{AGENTS_DIR}/{name}/dashboard/status.json"
        try:
            with open(path) as f:
                s = json.load(f)
            updated = s.get("updated_at")
            if not updated:
                issues.append(f"{name}: no update timestamp")
                continue
            # Parse timestamp
            try:
                dt = datetime.fromisoformat(updated.replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                age_hours = (now - dt).total_seconds() / 3600
                # Thresholds per agent — allow more time for infrequent updaters
                thresholds = {"infrastructure": 2, "cos": 1, "dashboard": 1, "monitoring": 0.5}
                limit = thresholds.get(name, 2)
                if age_hours > limit:
                    issues.append(f"{name}: last update {age_hours:.1f}h ago — may be stale")
                else:
                    healthy.append(name)
            except:
                healthy.append(name)
        except:
            issues.append(f"{name}: status file missing or unreadable")

    if issues:
        return {"name": "heartbeats", "ok": False,
                "detail": "Stale agent(s): " + "; ".join(issues)}
    return {"name": "heartbeats", "ok": True,
            "detail": f"All {len(healthy)} active agent(s) reporting normally"}

def check_cron_jobs():
    """Check the Python scheduler daemon is running (replaced OpenClaw cron)."""
    result = subprocess.run(["pgrep", "-f", "scheduler.py"], capture_output=True, text=True)
    if result.returncode == 0:
        pid = result.stdout.strip().split()[0]
        return {"name": "cron", "ok": True,
                "detail": f"Scheduler daemon running (PID {pid}) — dashboard 15m, watch 5m, infra 1hr"}
    return {"name": "cron", "ok": False,
            "detail": "Scheduler daemon not running — dashboard and health checks have stopped.\n→ Restart: python3 /home/node/.openclaw/workspace/scripts/scheduler.py"}

# ── Main ──────────────────────────────────────────────────────────────────

def main():
    log.info("run_start", "Beginning health checks")
    now = datetime.now().isoformat()
    prev = load_prev_state()
    checks = [
        check_gateway(),
        check_web_server(),
        check_bus(),
        check_disk(),
        check_agent_heartbeats(),
        check_cron_jobs(),
    ]

    alerts = []
    warnings = []
    new_failures = []

    for c in checks:
        was_ok = prev.get(c["name"], True)
        is_ok = c.get("ok", True)
        is_warn = c.get("warn", False)

        if not is_ok:
            log.error(f"check_{c['name']}", c["detail"])
            # New failure — alert if it wasn't already failing
            if was_ok:
                new_failures.append(c)
            alerts.append({
                "priority": 1,
                "title": f"{c['name'].replace('_',' ').title()} — Problem detected",
                "body": (
                    f"{c['detail']}\n"
                    f"→ Check: openclaw gateway status" if "gateway" in c["name"]
                    else c["detail"]
                ),
                "action_required": True,
                "due_at": None
            })
        elif is_warn:
            log.warning(f"check_{c['name']}", c["detail"])
            warnings.append({
                "priority": 2,
                "title": f"{c['name'].replace('_',' ').title()} — Warning",
                "body": c["detail"],
                "action_required": False,
                "due_at": None
            })

        else:
            log.info(f"check_{c['name']}", c["detail"])

    # Send Telegram for NEW failures only (avoid spam on repeat runs)
    for failure in new_failures:
        name = failure["name"].replace("_", " ").title()
        detail = failure["detail"]
        log_alert({"type": "failure", "component": failure["name"], "detail": detail})
        log.error("alert_sent", f"Telegram alert fired: {name} — {detail[:80]}")
        send_telegram_alert(
            f"System problem: {name}",
            f"{detail}\n\nCheck dashboard: http://100.67.100.125:8080/monitoring.html"
        )

    # Save current state for next run comparison
    save_state({c["name"]: c.get("ok", True) for c in checks})

    # Health summary
    n_fail = len(alerts)
    n_warn = len(warnings)

    if n_fail > 0:
        health = "error"
        first_fail = alerts[0]["title"] if alerts else "unknown component"
        summary = f"Down: {first_fail}" + (f" (+{n_fail-1} more)" if n_fail > 1 else "") + " — alert sent"
    elif n_warn > 0:
        health = "warning"
        first_warn = warnings[0]["title"] if warnings else "unknown issue"
        summary = f"Warning: {first_warn}"
    else:
        health = "ok"
        summary = "All systems healthy. Gateway ✓ Dashboard ✓ Bus ✓ Disk ✓ Agents ✓ Scheduler ✓"

    # Upcoming — what Watch is watching for next
    upcoming = [
        {"priority": 2, "title": "Will watch Comms Collector once connected (Milestone 4) — message bus queue depth", "due_at": None},
        {"priority": 3, "title": "Will watch School Agent pickup reminders once live (Milestone 6) — time-critical", "due_at": None},
        {"priority": 3, "title": "Will add web server auto-restart if it goes down (future improvement)", "due_at": None},
    ]

    status = {
        "agent": "monitoring",
        "updated_at": now,
        "health": health,
        "summary": summary,
        "checks": {c["name"]: {"ok": c.get("ok",True), "detail": c["detail"]} for c in checks},
        "alerts": alerts + warnings,
        "upcoming": upcoming
    }

    os.makedirs(os.path.dirname(STATUS_PATH), exist_ok=True)
    with open(STATUS_PATH, "w") as f:
        json.dump(status, f, indent=2)

    log.info("run_complete", f"health={health}, failures={n_fail}, warnings={n_warn}")
    print(f"✅ Watch: health={health}, failures={n_fail}, warnings={n_warn}")
    return health

if __name__ == "__main__":
    main()
