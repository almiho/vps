# DECISIONS.md — Decision Log
*Maintained by: AlexI (Infrastructure Agent)*
*Format: date | decision | options considered | rationale | approved by*

---

## 2026-04-12

### D001 — Workspace root location
- **Decision:** All project files under `/home/node/.openclaw/workspace/`
- **Options:** Custom path vs. default OpenClaw workspace
- **Rationale:** Default workspace is already configured, all tools point here
- **Approved by:** Alexander

### D002 — SQLite message bus location
- **Decision:** Single shared `data/bus.db` at workspace root
- **Options:** Per-agent databases vs. single shared bus
- **Rationale:** Single bus enables cross-agent communication; per-agent DBs would require additional routing layer
- **Approved by:** Alexander

### D003 — Existing agent starter files
- **Decision:** Leave OpenClaw starter files (SOUL.md, AGENTS.md etc.) in place in agents/infrastructure/, add project files alongside
- **Options:** Replace / leave as-is / reconcile
- **Rationale:** Starter files are the agent's own identity files, separate from project files. No conflict.
- **Approved by:** Alexander (via AlexI recommendation)

### D004 — Git initialisation
- **Decision:** Initialise git in workspace root, commit as work progresses, no remote yet
- **Options:** No git / local only / with remote
- **Rationale:** Version control is essential for a project of this complexity. Remote to be added as a next infrastructure step.
- **Approved by:** Alexander

### D005 — Agent communication model
- **Decision:** AlexI acts as Chief of Staff — all agent interactions go through AlexI, who consolidates and presents one answer to Alexander
- **Options:** Direct agent-to-Alexander messaging / CoS model
- **Rationale:** Reduces cognitive load, avoids context switching, enables intelligent filtering
- **Approved by:** Alexander

### D006 — AlexI identity
- **Decision:** Main agent named "AlexI" — combination of Alex + AI, representing the partnership
- **Approved by:** Alexander (named by Alexander on 2026-04-12)

### D007 — Tailscale dashboard access
- **Decision:** Dashboard served on Tailscale IP 100.67.100.125 — reachable from any device on the Tailscale network
- **Options:** Public internet / SSH tunnel / Tailscale
- **Rationale:** Tailscale provides private access without auth complexity; already running on VPS
- **Approved by:** Alexander (via AlexI recommendation)
