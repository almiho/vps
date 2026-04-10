# Personal AI Assistant — Plan

## Vision

A personal AI assistant that:
- Runs 24/7 on the VPS, proactively reaches out — does not wait to be asked
- Is reachable via **WhatsApp** (primary channel)
- Has memory — knows your preferences, context, ongoing projects
- Covers multiple life domains, built out incrementally
- Is secure by design — only you can reach it

This is not a chatbot. It is a personal assistant that works in the background,
notices things, summarises them, and takes action when you tell it to.

---

## What the videos taught us (and what we'll do differently)

The tutorial videos (Caleb's setup, mission control) show the right direction:
- Deploy OpenClaw on a VPS — ✅ already done for us (correct approach)
- Connect to a messaging app so it can reach you first — **we use WhatsApp, not Telegram**
- Install skills to give it access to your tools (calendar, email, etc.)
- Use Cron Jobs to run tasks on a schedule (morning brief, etc.)
- Build a "mission control" dashboard as a later milestone

**Where we go our own way:**
- No Hostinger GUI for management — we use `docker-compose`, version-controlled in this repo
- No public dashboard port — OpenClaw is only reachable via Tailscale
- Security first, features second
- One thing at a time — get it running and talking before adding complexity

---

## Roadmap (step by step)

### Phase 1 — Get it running and talking (current priority)

- [ ] **Deploy OpenClaw** via `docker-compose.yml` under `server/openclaw/`
  - Bind to Tailscale IP only (`100.67.100.125`) — not `0.0.0.0`
  - Store API keys in `.env` file (gitignored)
  - Use Anthropic Claude as the primary model (good reasoning, cost-effective)
- [ ] **Connect WhatsApp**
  - OpenClaw supports WhatsApp via phone number in env config
  - Test: send a message, get a response
- [ ] **Verify the assistant is reachable and responsive**
  - Basic sanity check: ask it something, confirm it replies via WhatsApp

### Phase 2 — First real use case

Keep it simple. Pick **one** use case that delivers immediate value.

**Candidate: Morning brief**
Every morning at a set time, the assistant:
1. Checks Google Calendar for the day's agenda
2. Scans Gmail inbox for anything important
3. Sends a short WhatsApp message with priorities

This is concrete, useful, and a good test of the full stack (scheduling + tools + messaging).

Steps:
- [ ] Install Google Workspace skill (GOG — Gmail + Calendar access)
- [ ] Create a Cron Job: daily at 07:30, summarise calendar + email, send via WhatsApp
- [ ] Test and tune the prompt

### Phase 3 — Add more life domains (ideas, not committed)

Each domain is a separate capability added when Phase 2 is stable.
Pick the next one based on what would be most useful at the time.

| Domain | What it could do |
|---|---|
| **News / AI updates** | Daily digest of relevant news, filtered to your interests |
| **Tasks / projects** | Track open tasks, remind you of things, follow up |
| **Finance** | Alert on unusual spending, monthly summary |
| **Health / habits** | Daily check-in, track habits you want to build |
| **relaxedon.boats** | Answer questions about boat services, customer queries |
| **Travel** | Brief on upcoming trips, packing reminders |

### Phase 4 — Mission control dashboard (later)

Once the assistant is stable and useful, consider a local dashboard:
- View scheduled jobs and their last output
- See which skills are installed
- Quick access to logs

The video approach (HTML file + Node.js server on the VPS, accessible via Tailscale)
is a solid pattern — lightweight, no database needed, private.
**Not a priority until Phase 2 is working well.**

---

## Key technical decisions

| Decision | Choice | Reason |
|---|---|---|
| Messaging | WhatsApp | Primary phone, always with you |
| AI model | Anthropic Claude | Strong reasoning, good API |
| Skills source | ClawHub / GitHub | Official community skills |
| Scheduling | OpenClaw Cron Jobs | Built-in, no extra tooling |
| Dashboard access | Tailscale only | Security — no public port |
| Config management | `.env` files (gitignored) | Simple, keeps secrets out of repo |

---

## Security reminders

- Gateway token = treat like a password. Rotate if exposed.
- API keys (Anthropic, Google) = store only in `.env`, never commit.
- OpenClaw dashboard = Tailscale only, never bind to `0.0.0.0`.
- WhatsApp token = store in `.env`, never share.
- Before adding a new skill: check what it does. Malicious skills exist on ClawHub.

---

## References

- `docs/overview.md` — infrastructure overview and current status
- `server/openclaw/` — OpenClaw deployment files (to be created in Phase 1)
- `server/system/verify.sh` — run on VPS to audit baseline security config
