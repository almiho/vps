# STANDARDS.md — Agent Build Specification
*Maintained by: AlexI (Infrastructure Agent)*
*Version: 1.0 | Created: 2026-04-12*
*Read AGENT_STANDARDS.md for the full system-wide rules. This document is the build-time reference.*

---

## 1. Agent Directory Template

Every agent gets this structure under `agents/[name]/`:

```
agents/[name]/
├── AGENT.md               # Mission, scope, domain_tag, dashboard contract
├── config/                # Agent-specific configuration
├── data/
│   └── decisions.jsonl    # Append-only decision log
├── documents/             # Domain documents
├── scripts/               # Agent scripts
└── dashboard/
    ├── status.json        # Written after each run; read by CoS
    └── detail.html        # Agent's detail page content block
```

---

## 2. SQLite Message Bus

**Location:** `data/bus.db`
**WAL mode:** always enabled

### Schema
```sql
CREATE TABLE messages (
  id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  source_channel TEXT,        -- gmail / whatsapp / scan / internal
  source_id TEXT,             -- thread_id / chat_id / filename
  source_address TEXT,        -- email / phone / postal address
  sender_name TEXT,
  subject TEXT,
  body TEXT,
  attachments TEXT,           -- JSON array
  forward_count INTEGER DEFAULT 0,
  domain_tag TEXT,            -- school / finance / real-estate / etc.
  status TEXT DEFAULT 'pending', -- pending / processing / processed / archived / failed
  processed_by TEXT,          -- JSON array of agent names
  reply_context TEXT,         -- JSON: everything needed to reply
  processed_at TEXT
);

CREATE TABLE agent_heartbeats (
  agent TEXT PRIMARY KEY,
  last_updated_at TEXT NOT NULL,
  status TEXT DEFAULT 'ok'    -- ok / warning / error
);
```

### Read pattern
```sql
SELECT * FROM messages
WHERE domain_tag = '[your-domain]' AND status = 'pending'
ORDER BY created_at ASC;
```

### Update after processing
```sql
UPDATE messages SET
  status = 'processed',
  processed_at = datetime('now'),
  processed_by = json_insert(processed_by, '$[#]', '[agent-name]')
WHERE id = '[id]';
```

---

## 3. Dashboard DB

**Location:** `data/dashboard.db`

```sql
CREATE TABLE dashboard_items (
  id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  agent TEXT NOT NULL,
  category TEXT NOT NULL,     -- today / upcoming / alert / info
  priority INTEGER NOT NULL,  -- 1 (critical) to 5 (low)
  title TEXT NOT NULL,
  body TEXT,
  due_at TEXT,
  action_required INTEGER DEFAULT 0,
  link TEXT,
  status TEXT DEFAULT 'active' -- active / acknowledged / done
);
```

Only CoS writes to this table. Domain agents write to their own `dashboard/status.json`.

---

## 4. Confidence Level Format

Every suggestion or recommendation must include:

```
Confidence: High | Medium | Low
Reason: [one sentence]
```

Never omit. Default to Low if unsure.

---

## 5. Dashboard status.json Format

```json
{
  "agent": "[name]",
  "updated_at": "ISO8601",
  "health": "ok | warning | error",
  "summary": "One sentence status",
  "alerts": [
    {
      "priority": 1,
      "title": "Headline",
      "body": "Detail",
      "due_at": "ISO8601 or null",
      "action_required": true
    }
  ],
  "upcoming": [
    {
      "priority": 3,
      "title": "Item",
      "due_at": "ISO8601"
    }
  ]
}
```

---

## 6. Log Format

One JSON object per line in `logs/[agent]/[agent]-YYYY-MM-DD.log`:

```json
{
  "timestamp": "ISO8601",
  "agent": "[name]",
  "level": "debug|info|warning|error",
  "event": "[event_name]",
  "detail": "[human readable]",
  "confidence": "high|medium|low|null"
}
```

Retention: 30 days.

---

## 7. Decision Log Entry Format

Append to `agents/[name]/data/decisions.jsonl`:

```json
{
  "timestamp": "ISO8601",
  "agent": "[name]",
  "decision": "[what was decided]",
  "confidence": "high|medium|low",
  "basis": "[why]",
  "message_id": "[if applicable]",
  "outcome": "[result]"
}
```

---

## 8. Conformance Checklist

Before any agent goes live, all boxes must be checked:

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
