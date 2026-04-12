# Heartbeat Tasks

## Startup Check (run every heartbeat)
Check and auto-restart if needed:

1. **Scheduler** — `pgrep -f "scheduler.py"` — if not running, start it:
   `python3 /home/node/.openclaw/workspace/scripts/scheduler.py`

2. **Web server** — check `http://100.67.100.125:8080/` — if not reachable, start it:
   `cd /home/node/.openclaw/workspace/dashboard && python3 -m http.server 8080 --bind 100.67.100.125`

If either was down and you restarted it, notify Alexander briefly.
Otherwise stay silent (HEARTBEAT_OK).
