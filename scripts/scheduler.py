#!/usr/bin/env python3
"""
AlexI Scheduler — lightweight background daemon
Runs maintenance scripts on schedule. No AI involvement.
Pure Python, no external dependencies.
"""

import subprocess, time, os, sys
from datetime import datetime

LOG = "/home/node/.openclaw/workspace/logs/scheduler.log"
WORKSPACE = "/home/node/.openclaw/workspace"

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
    "dashboard":   (15 * 60, f"{WORKSPACE}/agents/dashboard/scripts/generate.py",         "Dashboard regeneration"),
    "cos_status":  (15 * 60, f"{WORKSPACE}/agents/cos/scripts/update_status.py",           "CoS status update"),
    "monitor":     ( 5 * 60, f"{WORKSPACE}/agents/monitoring/scripts/monitor.py",          "Watch health check"),
    "infra_check": (60 * 60, f"{WORKSPACE}/agents/infrastructure/scripts/env_check.py",    "Infra env check"),
}

def main():
    log("AlexI Scheduler starting")
    last_run = {k: 0 for k in SCRIPTS}

    # Run everything once at startup
    for key, (interval, script, label) in SCRIPTS.items():
        log(f"Startup run: {label}")
        run_script(script, label)
        last_run[key] = time.time()

    while True:
        now = time.time()
        for key, (interval, script, label) in SCRIPTS.items():
            if now - last_run[key] >= interval:
                run_script(script, label)
                last_run[key] = now
        time.sleep(30)  # Check every 30 seconds

if __name__ == "__main__":
    main()
