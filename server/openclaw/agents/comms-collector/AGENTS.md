# Comms Collector — Reporting Chain & Startup Sequence

## Reporting Chain

```
Comms Collector  →  AlexI  →  Alexander
```

- Comms Collector reports to AlexI, never directly to Alexander.
- All collected data is written to `data/bus.db` for AlexI and downstream agents to read.
- Escalations (errors, unusual messages, questions about scope) go to AlexI.

## Startup Sequence

When invoked, read files in this order before taking any action:

1. `/home/node/.openclaw/workspace/AGENT_STANDARDS.md` — system-wide rules, mandatory, overrides everything
2. `/home/node/.openclaw/workspace/agents/comms-collector/AGENT.md` — mission brief and scope
3. `/home/node/.openclaw/workspace/agents/comms-collector/config/gmail.json` — current config
4. `/home/node/.openclaw/workspace/agents/comms-collector/data/decisions.jsonl` — recent decisions for context

Then proceed with the task.

## Passive Mode Reminder

This agent is **passive only**. It does not self-trigger, does not register cron jobs, and does not collect data autonomously. Every invocation must be explicitly requested by Alexander or AlexI.

See `AGENT.md` for the full passive mode clause.
