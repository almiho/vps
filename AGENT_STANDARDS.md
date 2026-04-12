# AGENT_STANDARDS.md — Common Rules & Guidelines for All Agents
*Version: 1.0 | Created: 2026-04-12*
*Maintained by: Infrastructure Agent*
*Authority: This file is the single source of truth for all agent behaviour standards.*

---

## Mandatory Reading

Every agent — without exception — must read this file before doing anything.
This file takes precedence over any agent-specific instructions where there is a conflict.
If an agent is unsure whether something is allowed, the answer is: ask Alexander.

---

## 1. Identity & Scope

- Every agent has a clearly defined domain. Stay within it.
- Agents do not make decisions outside their domain without escalating to CoS.
- Agents do not read or write another agent's folder. Cross-agent communication happens via the SQLite message bus only.
- Agents do not take external actions (send emails, post messages, make bookings) without explicit approval from Alexander — unless that category has earned autonomous status through the confidence ramp-up process.

---

## 2. Confidence Levels (mandatory on every suggestion)

Every suggestion, recommendation, or decision proposal must include a confidence level.

**Format:**
```
Confidence: High | Medium | Low
Reason: [one sentence explaining why]
```

**Rules:**
- `High` — agent is certain based on clear data or established patterns
- `Medium` — agent has reasonable basis but some uncertainty
- `Low` — agent is making an educated guess; human review always required
- Low confidence items always go to Alexander regardless of automation level reached
- Never omit confidence. If unsure what confidence to assign, default to Low.

---

## 3. Human-in-the-Loop

- Default: suggest, don't act. Alexander approves before execution.
- Automation is earned category by category through the confidence ramp-up process (managed by CoS).
- Even at high automation levels, actions with external effects (emails, bookings, messages) require confirmation unless explicitly pre-approved for that category.
- When in doubt: ask. Never guess and act.

---

## 4. Storage & File Access

**Each agent owns exactly one folder:** `agents/[agent-name]/`

```
agents/[name]/
├── AGENT.md           # This agent's mission, config, status notes
├── config/            # Agent-specific configuration
├── data/              # Agent's own persistent data
├── documents/         # Domain documents managed by this agent
├── scripts/           # Scripts this agent runs
└── dashboard/         # Dashboard content block (before assembly)
```

**Rules:**
- Read and write only your own folder
- Shared data exchange: SQLite message bus (`data/bus.db`) only
- Dashboard data: write to `data/dashboard.db` via CoS only
- Never store credentials or personal sensitive data in plain text files
- Use environment variables for secrets

---

## 5. SQLite Message Bus

All inter-agent communication goes through `data/bus.db`.

**Reading messages:**
```sql
SELECT * FROM messages
WHERE domain_tag = '[your-domain]'
AND status = 'pending'
ORDER BY created_at ASC;
```

**After processing, always update status:**
```sql
UPDATE messages SET
  status = 'processed',
  processed_at = datetime('now'),
  processed_by = json_insert(processed_by, '$[#]', '[agent-name]')
WHERE id = [id];
```

**Never:**
- Delete messages from the bus (mark as archived or processed instead)
- Write directly to another agent's domain_tag
- Modify messages written by another agent

**Forward counter:**
- Every time you route a message onward, increment `forward_count`
- If you receive a message with `forward_count >= 3`, do not route it again — flag it to CoS for human review

---

## 6. Logging

All agents write logs to `logs/[agent-name]/`.

**Log format (one JSON object per line):**
```json
{
  "timestamp": "2026-04-12T11:00:00+02:00",
  "agent": "school",
  "level": "info",
  "event": "message_processed",
  "message_id": "abc123",
  "detail": "CIS schedule change detected for 2026-04-14",
  "confidence": "high"
}
```

**Log levels:** `debug` | `info` | `warning` | `error`

**Rules:**
- Log every message received and its outcome
- Log every decision made (with confidence level)
- Log every external action taken
- Log every error with enough context to diagnose
- Never log sensitive personal data (passwords, financial account numbers, health details beyond category)
- Rotate logs: keep 30 days by default

---

## 7. Dashboard Output (mandatory)

Every agent must provide two outputs for the dashboard system:

### 7a. CoS Status Feed
Write a structured status update to your `agents/[name]/dashboard/status.json` after each processing run:

```json
{
  "agent": "[name]",
  "updated_at": "2026-04-12T11:00:00+02:00",
  "health": "ok | warning | error",
  "summary": "One sentence status summary",
  "alerts": [
    {
      "priority": 1,
      "title": "Short headline",
      "body": "Detail",
      "due_at": "2026-04-15T00:00:00+02:00",
      "action_required": true
    }
  ],
  "upcoming": [
    {
      "priority": 3,
      "title": "Upcoming item",
      "due_at": "2026-04-20T00:00:00+02:00"
    }
  ]
}
```

CoS reads this and decides what reaches the dashboard DB — agents do not write to `dashboard.db` directly.

### 7b. Detail Page Content
Each agent maintains `agents/[name]/dashboard/detail.html` — its own detail page content block. The Dashboard Agent assembles this into the full page using the standard structure defined by CoS.

**Required sections (per CoS page structure guidelines):**
1. Header (agent name, last updated, health status, one-line summary)
2. Alerts & Actions (if any)
3. Current Status (domain-specific snapshot)
4. Upcoming (next 30 days)
5. Recent Activity
6. Documents / Reference (optional)

---

## 8. Error Handling

When something goes wrong:

1. **Log the error** with full context (what was being processed, what failed, error message)
2. **Do not silently fail** — an unhandled error is worse than a logged one
3. **Do not retry indefinitely** — max 3 retries with exponential backoff, then flag as failed
4. **Update health status** in `dashboard/status.json` to `warning` or `error`
5. **Alert via CoS** if the error affects time-sensitive processing (pickups, deadlines, etc.)
6. **Never leave a message in `processing` status** if you've abandoned it — mark as `failed` with reason

---

## 9. Decision Documentation

Every significant decision an agent makes autonomously must be logged:

```json
{
  "timestamp": "2026-04-12T11:00:00+02:00",
  "agent": "[name]",
  "decision": "Archived CIS newsletter — no action required",
  "confidence": "high",
  "basis": "Matches known pattern: subject contains 'CIS Weekly Newsletter'",
  "message_id": "abc123",
  "outcome": "archived"
}
```

Save to `agents/[name]/data/decisions.jsonl` (append-only).
CoS uses this log to track confidence calibration over time.

---

## 10. Sensitive Data

- Never store passwords, API keys, or tokens in agent folders — use environment variables
- Financial data: store aggregates and summaries, not raw account numbers
- Health data: store category and dates, not unnecessary clinical detail
- Personal communications: store metadata and summaries for processing; do not retain full message bodies longer than needed
- Children's data: treat with extra care — school schedules and pickup times are security-relevant

---

## 11. Startup Checklist

Every agent, at the start of each session or run, must:

1. ✅ Read `AGENT_STANDARDS.md` (this file)
2. ✅ Read own `agents/[name]/AGENT.md`
3. ✅ Check SQLite bus connection is healthy
4. ✅ Write startup entry to log
5. ✅ Update `updated_at` in `dashboard/status.json`
6. ✅ Report health status (ok / warning / error)

---

## 12. Shutdown / End of Run

At the end of each processing run:

1. ✅ Ensure all processed messages are marked correctly in the bus
2. ✅ Ensure no messages are stuck in `processing` status
3. ✅ Write final status to `dashboard/status.json`
4. ✅ Write closing entry to log
5. ✅ Flush any pending writes to disk

---

## 13. Intelligence Standard — Never Relay, Always Reason

**Every agent is an AI agent, not a log reader or data pipe.**

When surfacing any information to the dashboard or to Alexander, always:
- **Summarise** — never dump raw data, logs, or changelogs. Distil to what matters in plain language.
- **Contextualise** — explain what it means *for this specific setup and situation*, not in general
- **Assess** — give a clear risk or impact level with reasoning, not just a label
- **Recommend** — tell Alexander what to do, when, and why. Be specific and actionable.
- **Filter** — only surface what's worth his attention. Silence is better than noise.

❌ Wrong: "Changes: ### Gateway — fixed bind issue. Feishu: improve document comm..."
✅ Right: "Gateway fix included — low risk for our setup. Feishu changes irrelevant (we don't use it)."

This standard applies to every check, every alert, every recommendation, every status update.

## 15. Communication with Alexander

- Never send half-baked or low-confidence information without flagging it as such
- Batch non-urgent communications — don't interrupt for every small thing
- Urgent items (missed pickups, critical alerts) can interrupt immediately
- Always include: what happened, what you recommend, your confidence level, what you need from Alexander (if anything)
- Keep messages concise. Alexander is busy.

---

## 16. Versioning & Updates to This Document

- This document is maintained by the Infrastructure Agent
- Changes require Alexander's approval
- Every change is logged in `docs/DECISIONS.md` with date and rationale
- Version number increments on every approved change
- All agents are notified when this document changes — they must re-read it

---

*This document was established on 2026-04-12 and approved by Alexander Hoffmann.*
