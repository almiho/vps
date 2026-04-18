# ROADMAP.md — Living Project Plan
*Maintained by: AlexI*
*Last updated: 2026-04-12*

---

## Status Legend
- ✅ Complete
- 🔄 In progress
- ⏳ Planned
- 🔲 Blocked

---

## Milestone 0: Foundation ✅
- ✅ OpenClaw gateway verified (running on port 18789)
- ✅ Tailscale verified (VPS IP: 100.67.100.125)
- ✅ Full directory structure created (18 agent dirs)
- ✅ Git initialised + connected to github.com/almiho/vps (server/openclaw/)
- ✅ Docs framework: IMPLEMENTATION.md, DECISIONS.md, ROADMAP.md, STANDARDS.md
- ✅ STATUS.md created and maintained
- ✅ Infrastructure Agent (Infra 🔧) scaffolded and live

---

## Milestone 1: The Message Bus ✅
- ✅ data/bus.db created with full schema + WAL mode
- ✅ data/dashboard.db created
- ✅ Conformance test passed
- ✅ Schema documented in STANDARDS.md

---

## Milestone 2: Dashboard Foundation ✅
- ✅ Dashboard Agent (Dash 📊) built
- ✅ 19 HTML pages generated (index + 18 agent detail pages)
- ✅ Web server running on http://100.67.100.125:8080/ (Tailscale only)
- ✅ About section on every agent page (collapsible)
- ✅ Architecture diagram on Infra page (SVG, domain clusters)
- ✅ Live health diagram on Monitoring page (clickable nodes)
- ✅ Clustered agent grid on homepage (System / Communications / Finance & Assets / Family & Life / Vehicles & Movement)
- ✅ Python scheduler daemon running (replaces OpenClaw cron)

---

## Milestone 3: Monitoring Agent ✅
- ✅ Monitoring Agent (Watch 👁️) built
- ✅ Checks: gateway, web server, SQLite bus, disk, agent heartbeats, scheduler
- ✅ Telegram alerts via openclaw message send (direct, no AI agent, non-blocking)
- ✅ New failures only — no spam
- ✅ Full test cycle passed: kill scheduler → alert fires → restart → back to healthy
- ✅ Watch page live on dashboard

---

## Milestone 4: Comms Collector ⏳
*"External messages enter the system cleanly"*
*Prerequisite: Gmail OAuth credentials from Alexander*

- 🔄 Gmail API integration (read-only first) — scaffold complete, passive mode
- ⏳ Normalisation format implementation
- ⏳ Domain tagging (rule-based first)
- ⏳ Write to SQLite bus with full reply_context
- ⏳ WhatsApp integration
- ⏳ Scanned letter OCR pipeline

---

## Milestone 5: Chief of Staff — GTD Layer ⏳
*"The inbox is being processed"*

- ⏳ **OKR onboarding session with Alexander** ← most critical, blocks everything downstream
- ⏳ CoS reads from message bus
- ⏳ 2-minute rule logic with confirmation
- ⏳ Domain routing with forward_count
- ⏳ Batched micro-review implementation
- ⏳ Decision logging and confidence tracking
- ⏳ Write to Dashboard DB

---

## Milestone 6: School Agent ⏳
*"Most time-sensitive domain covered first"*

- ⏳ Reads school-tagged messages from bus
- ⏳ Qualified TODO creation
- ⏳ Dynamic pickup reminders (CIS + Fernschule schedule-aware)
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
9. Boat Agent (Phase 1 first, then live monitoring)
10. Friendships Agent
11. Inbox Manager Agent
