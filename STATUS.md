# Project Status
Last updated: 2026-04-12 ~22:45

## Where we are
**Milestone 3 — Complete** ✅

## What was just done (evening session 2026-04-12)
- Recovered from OpenClaw update that took down the web server
- Moved SSH private key out of git, scrubbed from history, rotated key
- Added memory auto-sync: .claude memory files → workspace/memory/ every 15 min, auto-committed to git
- Full git cleanup: clean history, master tracking origin/main, everything pushed

## Agent build priority — confirmed by Alexander

### Next: Milestone 4 — School Agent 🏫
Alexander feels behind on what's happening at school. Deadline-driven.
- German lesson tracking and prep status
- School calendar / upcoming tests and deadlines
- Registration status (both kids in Denmark)
- Health insurance confirmation

### Then: Milestone 5 — Tax Agent 💶
Tax deadline approaching. Cross-border complexity (Germany + Denmark).
- Deadline tracking
- Document checklist
- Status of filings

### Then: Milestone 6 — Travel Agent ✈️
Multiple trips with approaching booking deadlines.
- Upcoming trip list with booking status
- Booking deadline alerts (target: 30 days before departure)
- Summer boat trip planning

### Supporting infrastructure
Each domain agent will likely need:
- A data file or lightweight DB for its domain
- A status.json for the dashboard
- Possibly a cron script for time-sensitive alerts

### Later milestones (order TBD)
- Comms Collector (Gmail/WhatsApp → bus) — needs OAuth discussion
- Finance Agent — cross-border visibility, contingency planning
- Friendships tracker — monthly contact log for key relationships
- Remaining domain agents (health, insurance, real estate, etc.)

## Active cron jobs
- watch-monitor: every 5 min (system health)
- dashboard-regenerate: every 15 min
- cos-status-update: every 15 min
- infra-env-check: every 1 hr
- sync-memory: every 15 min (memory → git)

## Live URLs (Tailscale only)
- Dashboard: http://100.67.100.125:8080/
- Monitoring: http://100.67.100.125:8080/monitoring.html
