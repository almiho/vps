# DECISIONS.md — Decision Log
*Maintained by: Infrastructure Agent*
*Every significant decision recorded here.*

---

## Format

```
### [DATE] — [SHORT TITLE]
- **Decision:** What was decided
- **Options considered:** What alternatives were evaluated
- **Rationale:** Why this option was chosen
- **Approved by:** Alexander / Infrastructure Agent / Both
- **Conditions / caveats:** Any limitations or follow-up required
```

---

## Log

---

### 2026-04-12 — Workspace Root Location

- **Decision:** All workspace files live under `/home/node/.openclaw/workspace/`
- **Options considered:** (1) Use workspace root as-is; (2) Create a subdirectory like `project/`
- **Rationale:** Alexander confirmed this is the correct root. Agent is already running from here.
- **Approved by:** Alexander
- **Conditions / caveats:** None

---

### 2026-04-12 — Existing Agent Files Preservation

- **Decision:** Preserve existing starter files in `agents/infrastructure/` (AGENTS.md, SOUL.md, HEARTBEAT.md, etc.) and add standard template files alongside them
- **Options considered:** (1) Preserve and add; (2) Replace with pure template; (3) Move starters to a subfolder
- **Rationale:** Alexander explicitly instructed to leave starters as-is. They serve the OpenClaw agent framework (session startup, heartbeat, identity). Standard template files are additive.
- **Approved by:** Alexander
- **Conditions / caveats:** Both sets of files coexist; no conflict expected

---

### 2026-04-12 — Git Repository Initialisation

- **Decision:** Initialise git repo at workspace root `/home/node/.openclaw/workspace/`. No remote for now.
- **Options considered:** (1) Git at workspace root; (2) Git at a subdirectory; (3) No git yet
- **Rationale:** Alexander confirmed: initialise git, commit as you go, no remote yet. Workspace root is the correct scope — captures all agent files, docs, and infrastructure.
- **Approved by:** Alexander
- **Conditions / caveats:** Remote to be added later if/when needed. No secrets or credentials to be committed (environment variables only per AGENT_STANDARDS.md §10).

---

### 2026-04-12 — Shared data/ Directory at Workspace Root

- **Decision:** Single `data/` directory at workspace root for shared databases (`bus.db`, `dashboard.db`). Per-agent data in `agents/[name]/data/`.
- **Options considered:** (1) All DBs at root `data/`; (2) All DBs in agent folders; (3) Split as above
- **Rationale:** Alexander confirmed: one shared `data/` at root for the bus and dashboard DB. Agent-specific data stays in the agent's own folder. Matches INFRA_AGENT.md directory spec.
- **Approved by:** Alexander
- **Conditions / caveats:** None

---

### 2026-04-12 — Tailscale Verification Deferred

- **Decision:** Proceed with Milestone 0 without Tailscale verification. Flagged as open item.
- **Options considered:** (1) Block M0 until Tailscale confirmed; (2) Proceed and flag; (3) Skip Tailscale entirely
- **Rationale:** `tailscale` not in PATH and no socket found at `/var/run/tailscale/`. Alexander confirmed it's installed. This is likely a PATH issue in the container environment. Non-blocking for M0 — Tailscale is required for M2 (dashboard web server) but not for directory/doc setup.
- **Approved by:** Infrastructure Agent (minor decision — flagged to Alexander)
- **Conditions / caveats:** Must be resolved before Milestone 2. Alexander to confirm Tailscale CLI path or verify via `sudo tailscale status`.
