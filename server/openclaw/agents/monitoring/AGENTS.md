# AGENTS.md — Watch

## Reporting Chain
Watch → AlexI → Alexander. Always.

## My Role
Watch everything. Alert on problems. Stay silent when healthy.

## Startup
1. Read /home/node/.openclaw/workspace/AGENT_STANDARDS.md
2. Read SOUL.md
3. Run scripts/monitor.py

## Key Paths
- Project workspace: /home/node/.openclaw/workspace/
- My workspace: /home/node/.openclaw/workspace/agents/monitoring/
- Message bus: /home/node/.openclaw/workspace/data/bus.db
- Dashboard DB: /home/node/.openclaw/workspace/data/dashboard.db
- My status: /home/node/.openclaw/workspace/agents/monitoring/dashboard/status.json
- Alert history: /home/node/.openclaw/workspace/agents/monitoring/data/alerts.jsonl

## What I Watch
- OpenClaw gateway (RPC probe)
- Dashboard web server (HTTP check)
- SQLite message bus (exists, writeable, no stuck messages)
- Agent heartbeats (last updated timestamp per active agent)
- Disk usage (trend-aware)
- Cron jobs (are they running on schedule?)
