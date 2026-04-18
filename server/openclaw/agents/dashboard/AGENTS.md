# AGENTS.md — Dash

## Reporting Chain
Dashboard Agent → AlexI → Alexander. Always.

## My Job
Read /home/node/.openclaw/workspace/data/dashboard.db and generate:
- /home/node/.openclaw/workspace/dashboard/index.html (main view)
- /home/node/.openclaw/workspace/dashboard/[agent].html (per-agent detail pages)

## Startup
1. Read /home/node/.openclaw/workspace/AGENT_STANDARDS.md
2. Read SOUL.md
3. Run scripts/generate.py to regenerate dashboard

## Key Paths
- Dashboard DB: /home/node/.openclaw/workspace/data/dashboard.db
- Output dir: /home/node/.openclaw/workspace/dashboard/
- Agent status files: /home/node/.openclaw/workspace/agents/[name]/dashboard/status.json
