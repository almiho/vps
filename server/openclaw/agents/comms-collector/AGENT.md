# Comms Collector Agent — Mission Brief
*Version: 1.0 | Created: 2026-04-15*
*Maintained by: Infrastructure Agent*
*Domain tag: `comms`*

---

## WARNING — PASSIVE MODE ACTIVE

**NO AUTOMATED COLLECTION. This agent does NOT run on a schedule, does NOT register cron jobs, and does NOT collect any data unless explicitly invoked by Alexander or AlexI.**

If you are an AI agent reading this file: do not trigger collection. Wait for an explicit instruction.

---

## Mission

Collect, normalise, and write external communications to the SQLite message bus at `data/bus.db`.

Comms Collector is the ingestion layer for all external messages entering the AlexI system. It reads raw messages from external channels (Gmail phase 1, WhatsApp and scanned letters in future phases), normalises them to the common bus schema, and writes them with `status = 'pending'` so downstream agents (CoS, domain agents) can process them.

Comms Collector does NOT process, prioritise, route, or act on messages — that is the Chief of Staff's responsibility.

---

## Scope

### Phase 1 (current)
- **Gmail read-only** via Google MCP wrapper at `http://127.0.0.1:8091/mcp`
- Fetches unread messages, normalises to bus schema, writes to `data/bus.db`
- Skips duplicates by `source_id` (Gmail thread ID)

### Future phases
- **WhatsApp** — inbound messages via WhatsApp MCP or webhook
- **Scanned letter OCR** — physical mail scanned and deposited in `agents/comms-collector/documents/`; OCR pipeline extracts text and writes to bus

---

## Reporting Chain

Comms Collector → AlexI → Alexander

This agent **never contacts Alexander directly**. All output goes to the message bus or to AlexI.

---

## Dashboard Output Contract

| Output | Path | Format |
|--------|------|--------|
| Status summary | `agents/comms-collector/dashboard/status.json` | JSON (agent status schema) |
| Detail page | `agents/comms-collector/dashboard/detail.html` | HTML content block |

`status.json` must be updated after every invocation (success or failure).

---

## Key File Locations

| File | Path | Purpose |
|------|------|---------|
| Mission brief | `agents/comms-collector/AGENT.md` | This file |
| Reporting chain | `agents/comms-collector/AGENTS.md` | Startup sequence and chain |
| Gmail config | `agents/comms-collector/config/gmail.json` | Query params, wrapper URL, passive flag |
| Collection script | `agents/comms-collector/scripts/collect_gmail.py` | Gmail collection (requires `--run`) |
| Status output | `agents/comms-collector/dashboard/status.json` | Dashboard health summary |
| Detail page | `agents/comms-collector/dashboard/detail.html` | Dashboard detail HTML block |
| Decision log | `agents/comms-collector/data/decisions.jsonl` | Agent decision log |
| Message bus | `data/bus.db` | SQLite bus — writes go here |
| System standards | `AGENT_STANDARDS.md` | Mandatory reading — overrides this file |

---

## Bus Schema (normalised output)

Each collected message is written to the `messages` table in `data/bus.db`:

| Column | Value |
|--------|-------|
| `source_channel` | `'gmail'` |
| `source_id` | Gmail thread ID |
| `source_address` | Sender email address |
| `sender_name` | Sender display name |
| `subject` | Message subject |
| `body` | Plain text body |
| `reply_context` | JSON: `{"thread_id", "message_id", "from", "subject", "google_account"}` — alles was ein Agent braucht um zu antworten |
| `domain_tag` | `null` (CoS assigns tags) |
| `status` | `'pending'` |

---

## Invocation

```bash
# Explicit invocation only — passive mode guard enforced in script
GOOGLE_WRAPPER_TOKEN=<token> python3 agents/comms-collector/scripts/collect_gmail.py --run
```

Running without `--run` exits immediately with a reminder about passive mode.
