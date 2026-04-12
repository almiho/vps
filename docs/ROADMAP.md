# ROADMAP.md — Living Project Plan
*Maintained by: AlexI (Infrastructure Agent)*
*Last updated: 2026-04-12*

---

## Status Legend
- ✅ Complete
- 🔄 In progress
- ⏳ Planned
- 🔲 Blocked

---

## Milestone 0: Foundation 🔄
*"The environment is ready to build on"*

- ✅ Verify OpenClaw gateway health
- ✅ Verify Tailscale status (running on VPS: 100.67.100.125)
- ✅ Create full directory structure
- ✅ Initialise git repository
- ✅ Initialise docs framework (IMPLEMENTATION.md, DECISIONS.md, ROADMAP.md, STANDARDS.md)
- 🔄 Scaffold infrastructure agent folder (status.json, detail.html, decisions.jsonl)
- ⏳ Verify conformance checklist
- ⏳ Update STATUS.md

**Next infrastructure steps (post M0):**
- ⏳ Set up git remote (GitHub/GitLab)

---

## Milestone 1: The Message Bus ✅
*"Agents can talk to each other"*

- ✅ Create SQLite database at data/bus.db
- ✅ Create full schema (messages + agent_heartbeats tables)
- ✅ Enable WAL mode
- ✅ Conformance test passed (insert → read → mark processed → clean)
- ✅ Document schema in docs/STANDARDS.md
- ✅ Create data/dashboard.db with dashboard_items schema
- ✅ Infrastructure agent heartbeat registered

---

## Milestone 2: Dashboard Foundation ⏳
*"There's something to look at"*

- ⏳ Create dashboard SQLite DB at data/dashboard.db
- ⏳ Set up static file web server on Tailscale interface (100.67.100.125)
- ⏳ Verify reachable from phone + desktop on Tailscale
- ⏳ Verify NOT reachable from public internet
- ⏳ Dashboard Agent generates basic index.html
- ⏳ Define CoS page structure guidelines
- ⏳ Create stub agent detail page template

---

## Milestone 3: Monitoring Agent ⏳
*"We know if something is broken"*

- ⏳ Define monitoring scope (gateway, SQLite bus, agent heartbeats, disk)
- ⏳ Implement queue health checks
- ⏳ Implement system health checks
- ⏳ Connect alerts to Telegram
- ⏳ Add to dashboard
- ⏳ Test: break something, verify alert fires

---

## Milestone 4: Comms Collector ⏳
*"External messages enter the system cleanly"*

- ⏳ Gmail API integration (read-only first)
- ⏳ Normalisation format implementation
- ⏳ Domain tagging (rule-based first)
- ⏳ Write to SQLite bus with full reply_context
- ⏳ WhatsApp integration
- ⏳ Scanned letter OCR pipeline

---

## Milestone 5: Chief of Staff — GTD Layer ⏳
*"The inbox is being processed"*

- ⏳ **OKR onboarding session with Alexander** ← most critical step
- ⏳ CoS reads from message bus
- ⏳ 2-minute rule logic with confirmation
- ⏳ Domain routing with forward_count
- ⏳ Batched micro-review implementation
- ⏳ Decision logging and confidence tracking
- ⏳ Write to Dashboard DB

---

## Milestone 6: School Agent ⏳
*"Most time-sensitive domain covered"*

- ⏳ Reads school-tagged messages from bus
- ⏳ Qualified TODO creation
- ⏳ Dynamic pickup reminders
- ⏳ school.html detail page
- ⏳ Dashboard status feed

---

## Milestone 7+: Remaining Domain Agents ⏳
*Build order (value + dependency):*

1. Finance Agent
2. Real Estate Agent
3. Life in Denmark Agent
4. Tax Agent
5. Travel Agent + Calendar Agent
6. Health Agent
7. Insurance Agent
8. Car Agent
9. Boat Agent (Phase 1, then live monitoring)
10. Friendships Agent
11. Inbox Manager Agent
