# Heartbeat Tasks

## Startup Check (run every heartbeat)
Run first: `bash /home/node/.openclaw/workspace/scripts/restore_ssh.sh`

Check and auto-restart if needed:

1. **Scheduler** — `pgrep -f "scheduler.py"` — if not running, start it:
   `python3 /home/node/.openclaw/workspace/scripts/scheduler.py`

2. **Web server** — check `http://100.67.100.125:8080/` — if not reachable, start it:
   `python3 /home/node/.openclaw/workspace/dashboard/server.py`

3. **HA Proxy** — `pgrep -f "ha_proxy.py"` — if not running, start it:
   `python3 /home/node/.openclaw/workspace/dashboard/ha_proxy.py`

If any was down and you restarted it, notify Alexander briefly.
Otherwise stay silent (HEARTBEAT_OK).
