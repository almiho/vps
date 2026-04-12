# ROADMAP.md — Living Project Plan
*Maintained by: Infrastructure Agent*
*Last updated: 2026-04-12*

---

## Status Key

- 🟢 Complete
- 🔵 In Progress
- ⬜ Planned
- ⚠️ Blocked

---

## 🔵 Milestone 0: Foundation
*"The environment is ready to build on"*

**Goal:** OpenClaw running cleanly, Tailscale connected, core directory structure in place, documentation framework initialized.

| Step | Status | Notes |
|------|--------|-------|
| Verify OpenClaw installation and gateway status | 🟢 | RPC probe: ok, port 18789 |
| Verify Tailscale is running and devices connected | ⚠️ | Installed per Alexander; CLI not in PATH — open item |
| Define and create top-level directory structure | 🟢 | All agent, data, log, doc dirs created |
| Initialize IMPLEMENTATION.md | 🟢 | |
| Initialize DECISIONS.md | 🟢 | |
| Initialize STANDARDS.md | 🟢 | |
| Initialize ROADMAP.md | 🟢 | (this file) |
| Scaffold Infrastructure Agent folder | 🟢 | AGENT.md, status.json, detail.html, decisions.jsonl |
| Set up logging directory and format standard | 🟢 | logs/[agent]/ created for all agents |
| Initialize git repo | 🔵 | In progress |
| Update STATUS.md | 🔵 | In progress |

**Deliverable:** A documented, verified base environment. Nothing broken. Everything recorded.

---

## ⬜ Milestone 1: The Message Bus
*"Agents can talk to each other"*

**Goal:** SQLite message bus running with correct schema, WAL mode enabled, verified for concurrent access.

| Step | Status |
|------|--------|
| Create SQLite database at data/bus.db | ⬜ |
| Create full schema (messages + agent_heartbeats tables) | ⬜ |
| Enable WAL mode and verify | ⬜ |
| Write smoke test: insert → read → mark processed | ⬜ |
| Document schema in STANDARDS.md (update existing entry) | ⬜ |
| Verify concurrent read/write correctness | ⬜ |

**Deliverable:** A working, tested message bus. All future agents will use this.

---

## ⬜ Milestone 2: The Dashboard Foundation
*"There's something to look at"*

**Goal:** Dashboard SQLite DB created, Dashboard Agent generating basic HTML, served via Tailscale web server.

**Dependency:** Tailscale verified and working (open item from M0)

| Step | Status |
|------|--------|
| Create dashboard SQLite DB at data/dashboard.db with schema | ⬜ |
| Set up static file web server bound to Tailscale interface | ⬜ |
| Verify reachable from phone and desktop on Tailscale | ⬜ |
| Verify NOT reachable from public internet | ⬜ |
| Dashboard Agent generates basic index.html | ⬜ |
| Define and document CoS page structure guidelines | ⬜ |
| Create stub agent detail page template | ⬜ |

**Deliverable:** A URL on Tailscale that shows a dashboard. Empty but real.

---

## ⬜ Milestone 3: The Monitoring Agent
*"We know if something is broken"*

**Goal:** Monitoring Agent watching message bus and system components, alerting via Telegram.

| Step | Status |
|------|--------|
| Define what Monitoring Agent watches | ⬜ |
| Implement queue health checks (stuck messages, depth) | ⬜ |
| Implement system health checks (gateway, disk, etc.) | ⬜ |
| Connect alerts to Telegram | ⬜ |
| Add Monitoring Agent to dashboard | ⬜ |
| Test: break something deliberately, verify alert fires | ⬜ |

**Deliverable:** If anything breaks, Alexander gets a Telegram message.

---

## ⬜ Milestone 4: The Comms Router
*"External messages enter the system cleanly"*

**Goal:** Comms Router ingesting Gmail, normalising, writing to SQLite bus with reply_context.

| Step | Status |
|------|--------|
| Gmail API integration (read-only first) | ⬜ |
| Define and implement normalisation format | ⬜ |
| Implement domain tagging (rule-based first) | ⬜ |
| Write to SQLite bus with all required fields | ⬜ |
| Verify reply_context populated correctly for Gmail | ⬜ |
| Add WhatsApp integration | ⬜ |
| Add scanned letter OCR pipeline | ⬜ |
| Add to Monitoring Agent watchlist | ⬜ |

**Deliverable:** External messages arrive in the bus, clean and correctly structured.

---

## ⬜ Milestone 5: Chief of Staff — GTD Layer
*"The inbox is being processed"*

**Goal:** CoS reading from bus, applying GTD Layer 1, routing to domain agents, running batched micro-reviews.

| Step | Status |
|------|--------|
| OKR onboarding session with Alexander | ⬜ |
| CoS reads from message bus (unprocessed messages) | ⬜ |
| Implement 2-minute rule logic with confirmation | ⬜ |
| Implement domain routing with forward_count | ⬜ |
| Implement batched micro-review (queue + timing) | ⬜ |
| Implement decision logging and confidence tracking | ⬜ |
| Write prioritised items to Dashboard DB | ⬜ |
| Verify on dashboard | ⬜ |

**Deliverable:** Messages get processed. Alexander gets batched review sessions.

---

## ⬜ Milestone 6: First Domain Agent — School
*"The most time-sensitive domain is covered"*

**Goal:** School Agent processing school-tagged messages, generating qualified todos, maintaining detail page.

*School first: pickup reminders are safety-critical, scope is well-defined, high immediate value.*

| Step | Status |
|------|--------|
| School Agent reads from bus (domain_tag = 'school') | ⬜ |
| Qualified TODO creation with all required fields | ⬜ |
| Dynamic pickup reminders (schedule-aware) | ⬜ |
| Writes to CoS qualified todo list | ⬜ |
| Generates and maintains school.html detail page | ⬜ |
| Feeds status to Dashboard DB via CoS | ⬜ |

**Deliverable:** School messages handled automatically. Pickup reminders work. School detail page live.

---

## ⬜ Milestone 7+: Remaining Domain Agents

Build order (by value and dependency):

| # | Agent | Reason for order |
|---|-------|-----------------|
| 1 | Finance | High value; Real Estate + Tax need it first |
| 2 | Real Estate | Feeds Finance; high complexity, start early |
| 3 | Life in Denmark | Compliance deadlines, time-sensitive |
| 4 | Tax | Needs Real Estate + Finance first |
| 5 | Travel | Needs Calendar + School running |
| 6 | Calendar | Needed by Travel + CoS scheduling |
| 7 | Health | Important but less time-critical |
| 8 | Insurance | Feeds Finance, lower urgency |
| 9 | Car | Relatively standalone, lower urgency |
| 10 | Boat | Seasonal; Phase 1 first, live monitoring later |
| 11 | Friendships | Standalone, can be built any time |
| 12 | General Comms | Last — needs Comms Router fully stable |

---

## Open Questions (unresolved design items)

These must be decided before the relevant milestone:

| # | Question | Needed by |
|---|----------|-----------|
| 1 | Data ownership model (who is source of truth per data type) | M7 domain agents |
| 2 | Tanja's access and role in the system | M7 (Travel, Health, Real Estate) |
| 3 | Which calendar system to integrate with | M6 Calendar Agent |
| 4 | Agent onboarding / cold start data collection | Per agent |
| 5 | Persistent agent memory / learning layer | Design before M5 |
| 6 | Trust & privacy boundaries when adding other users | Before Tanja access |
