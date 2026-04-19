#!/usr/bin/env python3
"""
AlexI Scheduler — lightweight background daemon
Runs maintenance scripts on schedule. No AI involvement.
Pure Python, no external dependencies.
"""

import subprocess, time, os, sys, signal
from datetime import datetime

LOG = "/home/node/.openclaw/workspace/logs/scheduler.log"
WORKSPACE = "/home/node/.openclaw/workspace"

WEBSERVER_PID_FILE = f"{WORKSPACE}/logs/webserver.pid"
WEBSERVER_LOG      = f"{WORKSPACE}/logs/webserver.log"
WEBSERVER_BIND     = "100.67.100.125"
WEBSERVER_PORT     = 8080
WEBSERVER_DIR      = f"{WORKSPACE}/dashboard"

import subprocess as _sp
# Restore SSH keys on startup (wiped by container updates)
_sp.run(["bash", "/home/node/.openclaw/workspace/scripts/restore_ssh.sh"], capture_output=True)

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a") as f:
            f.write(line + "\n")
    except:
        pass

def run_script(script, label):
    try:
        r = subprocess.run(
            ["python3", script],
            capture_output=True, text=True, timeout=60
        )
        if r.returncode == 0:
            log(f"OK: {label} — {r.stdout.strip()[:100]}")
        else:
            log(f"ERROR: {label} — {r.stderr.strip()[:200]}")
    except Exception as e:
        log(f"EXCEPTION: {label} — {e}")

SCRIPTS = {
    "dashboard":    (15 * 60, f"{WORKSPACE}/agents/dashboard/scripts/generate.py",                  "Dashboard regeneration"),
    "cos_status":   (15 * 60, f"{WORKSPACE}/agents/cos/scripts/update_status.py",                   "CoS status update"),
    "monitor":      ( 5 * 60, f"{WORKSPACE}/agents/monitoring/scripts/monitor.py",                  "Watch health check"),
    "infra_check":  (60 * 60, f"{WORKSPACE}/agents/infrastructure/scripts/env_check.py",            "Infra env check"),
    "sync_memory":  (15 * 60, f"{WORKSPACE}/scripts/sync_memory.py",                                "Memory sync to git"),
    "gmail_stats":  (30 * 60, f"{WORKSPACE}/agents/comms-collector/scripts/gmail_stats.py",         "Gmail inbox stats"),
    "boat_status":  (60 * 60, f"{WORKSPACE}/scripts/fetch_boat_status.py",                            "Boat HA status fetch"),
    "inbox_manager": (15 * 60, f"{WORKSPACE}/agents/inbox-manager/scripts/route_messages.py",         "Inbox message routing"),
    "school_pickup":  (24 * 60 * 60, f"{WORKSPACE}/agents/school/scripts/fetch_pickup_schedule.py",   "School pickup schedule fetch"),
}

def webserver_alive():
    """Return True if the webserver is actually responding on the port."""
    try:
        import urllib.request as _ur
        with _ur.urlopen(f"http://{WEBSERVER_BIND}:{WEBSERVER_PORT}/", timeout=3) as r:
            return r.status == 200
    except Exception:
        return False

def start_webserver():
    """Start the dashboard HTTP server using server.py (no-cache, single instance)."""
    # Kill anything already on the port first, then wait for port to free
    try:
        subprocess.run(["pkill", "-f", "server.py"], capture_output=True)
        subprocess.run(["pkill", "-f", f"http.server {WEBSERVER_PORT}"], capture_output=True)
        import time as _t
        for _ in range(5):  # Wait up to 5s for port to free
            _t.sleep(1)
            if not webserver_alive():
                break  # Port is free, proceed
    except Exception:
        pass
    log_fh = open(WEBSERVER_LOG, "a")
    proc = subprocess.Popen(
        ["python3", f"{WORKSPACE}/dashboard/server.py"],
        stdout=log_fh,
        stderr=log_fh,
        start_new_session=True,
    )
    with open(WEBSERVER_PID_FILE, "w") as f:
        f.write(str(proc.pid))
    log(f"Webserver started — PID {proc.pid} on {WEBSERVER_BIND}:{WEBSERVER_PORT}")

_last_webserver_start = 0

def ensure_webserver():
    """Restart webserver only if it is truly not responding, with cooldown."""
    global _last_webserver_start
    if webserver_alive():
        return
    # Cooldown: don't restart more than once every 60 seconds
    now = time.time()
    if now - _last_webserver_start < 60:
        return
    log("Webserver not responding — restarting")
    _last_webserver_start = now
    start_webserver()

def main():
    log("AlexI Scheduler starting")
    last_run = {k: 0 for k in SCRIPTS}

    ensure_webserver()

    # Run everything once at startup
    for key, (interval, script, label) in SCRIPTS.items():
        log(f"Startup run: {label}")
        run_script(script, label)
        last_run[key] = time.time()

    while True:
        ensure_webserver()
        now = time.time()
        for key, (interval, script, label) in SCRIPTS.items():
            if now - last_run[key] >= interval:
                run_script(script, label)
                last_run[key] = now
        time.sleep(30)  # Check every 30 seconds

if __name__ == "__main__":
    main()
