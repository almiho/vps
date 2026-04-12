# STANDARDS.md — Agent Build Spec
*Version: 1.0 | Created: 2026-04-12*
*Maintained by: Infrastructure Agent*
*Read this before building any agent. Changes require Alexander's approval.*

---

## 1. Agent Directory Structure

Every agent has exactly this structure under `agents/[name]/`:

```
agents/[name]/
├── AGENT.md                  # Mission, config, domain_tag, bus patterns, dashboard contract
├── config/                   # Agent-specific configuration files
├── data/
│   └── decisions.jsonl       # Append-only decision log (created on scaffold)
├── documents/                # Domain documents stored by this agent
├── scripts/                  # Scripts this agent runs
└── dashboard/
    ├── status.json           # CoS status feed (written after each run)
    └── detail.html           # Detail page content block (assembled by Dashboard Agent)
```

**Workspace-level directories:**
```
data/
  bus.db          # SQLite message bus (shared, created in M1)
  dashboard.db    # Dashboard SQLite DB (shared, created in M2)
dashboard/        # Generated HTML files served by web server
logs/[name]/      # One log directory per agent
docs/             # Project documentation
```

---

## 2. SQLite Message Bus

**Location:** `/home/node/.openclaw/workspace/data/bus.db`
**Mode:** WAL (`PRAGMA journal_mode=WAL;`)

### Schema

```sql
CREATE TABLE messages (
  id              TEXT PRIMARY KEY,         -- UUID
  timestamp       TEXT NOT NULL,            -- ISO-8601
  source_channel  TEXT NOT NULL,            -- 'gmail' | 'whatsapp' | 'scan' | 'internal'
  source_id       TEXT,                     -- original message ID from source
  source_address  TEXT,                     -- email address, phone number, or postal address
  sender_name     TEXT,
  subject         TEXT,
  body            TEXT,
  attachments     TEXT,                     -- JSON array of attachment references
  domain_tag      TEXT,                     -- routing tag ('school', 'finance', etc.) or NULL
  status          TEXT NOT NULL DEFAULT 'pending',  -- 'pending' | 'processing' | 'processed' | 'failed' | 'archived'
  forward_count   INTEGER NOT NULL DEFAULT 0,
  processed_by    TEXT NOT NULL DEFAULT '[]',       -- JSON array of agent names
  reply_context   TEXT,                     -- JSON: channel-specific reply info
  processed_at    TEXT                      -- ISO-8601
);

CREATE TABLE agent_heartbeats (
  agent           TEXT PRIMARY KEY,
  last_updated_at TEXT NOT NULL,            -- ISO-8601
  status          TEXT NOT NULL DEFAULT 'ok'  -- 'ok' | 'warning' | 'error'
);
```

### Read Pattern (domain agent)

```sql
SELECT * FROM messages
WHERE domain_tag = '[your-domain]'
AND status = 'pending'
ORDER BY timestamp ASC;
```

### Write Pattern (mark processed)

```sql
UPDATE messages SET
  status = 'processed',
  processed_at = datetime('now'),
  processed_by = json_insert(processed_by, '$[#]', '[agent-name]')
WHERE id = '[id]';
```

### Rules
- Never delete messages — mark as `archived` or `processed`
- Never write to another agent's domain_tag
- Never modify messages written by another agent
- If `forward_count >= 3`, do NOT route again — flag to CoS for human review
- Increment `forward_count` every time you route a message onward
- Never leave a message in `processing` status if you've abandoned it — mark as `failed` with reason

---

## 3. Dashboard Output Contract

Every agent must provide two outputs:

### 3a. CoS Status Feed

**Location:** `agents/[name]/dashboard/status.json`
**Written:** After every processing run

```json
{
  "agent": "[name]",
  "updated_at": "ISO-8601 timestamp",
  "health": "ok | warning | error",
  "summary": "One sentence status summary",
  "alerts": [
    {
      "priority": 1,
      "title": "Short headline",
      "body": "Detail",
      "due_at": "ISO-8601 or null",
      "action_required": true
    }
  ],
  "upcoming": [
    {
      "priority": 3,
      "title": "Upcoming item",
      "due_at": "ISO-8601 or null"
    }
  ]
}
```

### 3b. Detail Page Content

**Location:** `agents/[name]/dashboard/detail.html`
**Required sections (in order):**
1. Header — agent name, last updated, health status, one-line summary
2. Alerts & Actions — if any, highest priority first, each with title/detail/due date
3. Current Status — domain-specific snapshot
4. Upcoming — next 30 days
5. Recent Activity — last N logged events
6. Documents / Reference — (optional) links to stored documents

---

## 4. Logging Standard

**Location:** `logs/[name]/[YYYY-MM-DD].jsonl` (one file per day, append-only)

**Format (one JSON object per line):**

```json
{
  "timestamp": "ISO-8601",
  "agent": "[name]",
  "level": "debug | info | warning | error",
  "event": "event_type_slug",
  "message_id": "uuid or null",
  "detail": "Human-readable description",
  "confidence": "high | medium | low | null"
}
```

**Required log events:**
- Every message received and its outcome
- Every decision made (with confidence)
- Every external action taken
- Every error (with enough context to diagnose)
- Startup and shutdown

**Rules:**
- Never log: passwords, API keys, tokens, full account numbers, unnecessary clinical detail
- Rotate: keep 30 days, delete older
- Use `warning` for recoverable issues, `error` for failures requiring attention

---

## 5. Confidence Level Format

**Mandatory on every suggestion, recommendation, or decision proposal.**

```
Confidence: High | Medium | Low
Reason: [one sentence]
```

**Rules:**
- `High` — certain based on clear data or established pattern
- `Medium` — reasonable basis but some uncertainty
- `Low` — educated guess; human review always required
- Low confidence → always escalate to Alexander regardless of automation level
- Never omit confidence. When unsure, default to Low.

---

## 6. Decision Log Format

**Location:** `agents/[name]/data/decisions.jsonl` (append-only)

```json
{
  "timestamp": "ISO-8601",
  "agent": "[name]",
  "decision": "Short description of what was decided",
  "confidence": "high | medium | low",
  "basis": "One sentence explaining the evidence or pattern",
  "message_id": "uuid or null",
  "outcome": "archived | routed | acted | deferred | failed"
}
```

---

## 7. Qualified TODO Schema

When a domain agent creates a qualified TODO from a processed message, it must include:

```json
{
  "id": "uuid",
  "created_at": "ISO-8601",
  "source_message_id": "bus message id",
  "agent": "[domain-agent-name]",
  "title": "Short action title",
  "detail": "Full context",
  "project": "Project name or null",
  "context": "@context tag or null",
  "next_flag": true,
  "energy": "high | medium | low",
  "waiting_for": "person/entity or null",
  "deadline": "ISO-8601 or null",
  "okr_tag": "OKR label or null",
  "confidence": "high | medium | low",
  "confidence_reason": "One sentence",
  "reply_context": "Preserved from original bus message"
}
```

---

## 8. Error Handling

When something goes wrong, an agent must:

1. **Log the error** — full context: what was being processed, what failed, error message
2. **Never silently fail** — an unhandled error is worse than a logged one
3. **Retry with backoff** — max 3 retries, exponential backoff, then mark as `failed`
4. **Update health status** — set `health: "warning"` or `"error"` in `status.json`
5. **Alert via CoS** — if error affects time-sensitive processing
6. **Never leave `processing` messages abandoned** — always mark as `failed` with reason

---

## 9. Agent Startup Checklist

Run at the start of every session/run:

1. ✅ Read `AGENT_STANDARDS.md`
2. ✅ Read own `agents/[name]/AGENT.md`
3. ✅ Check SQLite bus connection is healthy
4. ✅ Write startup entry to log
5. ✅ Update `updated_at` in `dashboard/status.json`
6. ✅ Report health status (ok / warning / error)

---

## 10. Agent Shutdown Checklist

Run at the end of every processing run:

1. ✅ All processed messages marked correctly in bus
2. ✅ No messages stuck in `processing` status
3. ✅ Final status written to `dashboard/status.json`
4. ✅ Closing entry written to log
5. ✅ All pending writes flushed to disk

---

## 11. Agent Conformance Checklist

**No agent is considered built until all boxes are checked.**
Infrastructure Agent documents the result in `docs/IMPLEMENTATION.md`.

```
[ ] agents/[name]/AGENT.md exists and references AGENT_STANDARDS.md
[ ] agents/[name]/config/ exists
[ ] agents/[name]/data/ exists
[ ] agents/[name]/data/decisions.jsonl exists
[ ] agents/[name]/documents/ exists
[ ] agents/[name]/scripts/ exists
[ ] agents/[name]/dashboard/status.json exists and is valid JSON
[ ] agents/[name]/dashboard/detail.html exists
[ ] logs/[name]/ exists and is writable
[ ] Agent reads AGENT_STANDARDS.md on startup
[ ] Agent updates status.json on startup and shutdown
[ ] Agent correctly reads from bus with its domain_tag
[ ] Agent correctly marks messages as processed
[ ] Agent includes confidence level in all suggestions
[ ] Agent added to Monitoring Agent watchlist
```

---

## Changelog

| Version | Date | Change | Approved by |
|---------|------|--------|-------------|
| 1.0 | 2026-04-12 | Initial version, distilled from AGENT_STANDARDS.md | Alexander |
