# Heartbeat Tasks

## Startup Check (run every heartbeat)
Run first: `bash /home/node/.openclaw/workspace/scripts/restore_ssh.sh`

Check and auto-restart if needed:

1. **Scheduler** — `pgrep -f "scheduler.py"` — if not running, start it:
   `/home/node/.openclaw/workspace/scripts/schedulerctl.sh start`

2. **Web server** — check `http://100.67.100.125:8080/` — if not reachable, start it:
   `/home/node/.openclaw/workspace/scripts/dashboard-webctl.sh start`

If any was down and you restarted it, notify Alexander briefly.
Otherwise stay silent (HEARTBEAT_OK).

## Important Rules
- NEVER ask Alexander a question — if context is missing or unclear, reply NO_REPLY
- NEVER relay raw command output — interpret and summarize only
- If you receive an "async command completed" event without output: NO_REPLY
- You are not a general assistant — only act on what is defined above
