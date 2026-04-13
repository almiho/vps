# Google MCP Wrapper Plan

This plan sets up a dedicated `server/google-mcp-wrapper` project that is exclusively for OpenClaw access to Google services (Gmail, Calendar, Drive), enforcing least privilege, blocking destructive actions, and adding auditing/rate limits.

## Goal
- Enable useful Gmail/Calendar/Drive experiments in OpenClaw with minimal security risk.
- Keep Google credentials isolated from OpenClaw.
- Enforce policy in one place (allowlist tools, deny send/delete by default).

## Scope (Phase 1)
- Create folder: `/Users/alex/dev/vps/server/google-mcp-wrapper`
- Add architecture/concept doc in that folder
- Add minimal project scaffold (runtime, config, policy skeleton)
- Add Docker setup for wrapper container (not public)
- Add integration notes for OpenClaw MCP registration
- Explicitly out of scope: non-Google connectors/tools

## Architecture Concept
- Northbound: wrapper exposes MCP server to OpenClaw.
- Southbound (v1 decision): wrapper proxies to a downstream Google MCP server.
- Direct Google API integration is deferred to a later phase if we need tighter control than MCP proxying can provide.
- Runtime (v1 decision): Node.js with TypeScript.
- Credentials:
  - Google OAuth secrets/tokens only in wrapper container/secret store.
  - OpenClaw gets only wrapper auth token.
- Network (v1 decision):
  - OC->wrapper uses internal TCP over a private Docker network only (no published ports).
  - OC authenticates to wrapper with a dedicated bearer token (`WRAPPER_API_TOKEN`).

## Security Controls (Phase 1 baseline)
- Default deny: only explicit allowlisted tools are exposed.
- Blocklist hard stop: `send`, `delete`, `trash`, `permanent-delete` tool patterns.
- Argument constraints (examples): max results, date-window caps, folder allowlist.
- Rate limiting: per-tool + per-minute + per-day quotas.
- Audit log for every tool call (timestamp, caller, tool, decision, latency, response size).
- Container hardening: non-root user, read-only filesystem, dropped capabilities, no docker socket mount.

## Token Lifecycle (OC -> Wrapper)
- Use a dedicated bearer token (`WRAPPER_API_TOKEN`) generated as high-entropy random secret.
- Store token only in runtime secrets/env on OC and wrapper; never commit to git.
- Rotate token on a fixed cadence (recommended: every 30 days) and immediately after any suspicion of exposure.
- Support dual-token overlap during rotation to avoid downtime (old + new valid briefly, then revoke old).
- Log auth failures with source metadata and alert on repeated invalid-token attempts.

## Proposed Initial Policy
- Gmail: allow read/search metadata + message fetch (read-only), deny send/delete.
- Calendar: allow list/read events, optional create disabled by default.
- Drive: allow list/read/download in explicitly shared folders, deny delete/update.

## Observability and Monitoring
- Wrapper emits structured JSON logs for each MCP call.
- Required log fields: `ts`, `request_id`, `caller`, `tool`, `decision`, `reason`, `status_code`, `latency_ms`.
- Maintain a separate append-only audit log for policy decisions.
- Expose health endpoints:
  - `GET /healthz` (process alive)
  - `GET /readyz` (downstream MCP reachable and config loaded)
- Expose metrics endpoint (`GET /metrics`) for request volume, deny rate, rate-limit hits, upstream errors, and p95 latency.

## OC Dashboard Integration (Loose Coupling)
- Wrapper remains an independent service and codebase.
- Phase 1: OC dashboard consumes only a non-risky, read-only wrapper status summary (no control/admin operations).
- Wrapper publishes a small `status.json` summary (file or HTTP endpoint) with sanitized operational metrics only.
- Suggested `status.json` contract:

```json
{
  "service": "google-mcp-wrapper",
  "health": "ok",
  "last_success_ts": "2026-04-13T10:50:00Z",
  "calls_1h": 120,
  "denied_1h": 9,
  "rate_limited_1h": 2,
  "error_rate_1h": 0.02,
  "p95_latency_ms": 240,
  "version": "v0.1.0"
}
```

- OC dashboard adds a single tile fed by this summary only.
- No secrets shared with the dashboard.
- Raw wrapper logs/metrics stay in wrapper scope; they are not directly exposed to OC in phase 1.
- Phase 2 (later, on request): extend OC dashboard using selected raw wrapper data through an explicit, reviewed contract.

## Deliverables
- `server/google-mcp-wrapper/README.md` (design + runbook)
- `server/google-mcp-wrapper/docker-compose.yml` (internal-only service)
- `server/google-mcp-wrapper/.env.example` (no secrets committed)
- `server/google-mcp-wrapper/policy/allowlist.json` (or equivalent)
- `server/google-mcp-wrapper/docs/security-model.md`
- `server/google-mcp-wrapper/docs/openclaw-integration.md`
- `server/google-mcp-wrapper/docs/observability.md`

## Effort Estimate
- MVP (read-only + policy + rate limit + logging + docker): 1-2 days.
- Hardened MVP (tests, metrics, token refresh reliability): +2-4 days.

## Implementation Sequence
1. Create folder + scaffold files in `server/google-mcp-wrapper`.
2. Implement MCP northbound + downstream adapter abstraction.
3. Implement policy engine (allowlist/blocklist/arg validation).
4. Add rate limiter + audit logging.
5. Add Docker hardening + internal-only connectivity.
6. Register wrapper in OpenClaw and validate with safe test calls.

## MVP Test Matrix
- Allowed read path: `gmail.search` and `gmail.read` succeed through wrapper.
- Denied destructive path: representative `send/delete` operations return explicit policy deny errors.
- Rate limiting: repeated calls trigger limit response and are logged.
- Auth enforcement: invalid/missing bearer token returns `401` and is logged.
- Downstream failure handling: wrapper returns controlled `5xx`/error message when downstream MCP is unavailable.

## Acceptance Criteria
- OpenClaw can use allowed read-only tools through wrapper.
- Disallowed operations are blocked with explicit policy errors.
- Wrapper is not reachable from public network.
- Google credentials are inaccessible to OpenClaw container.
- Audit logs show all MCP calls and decisions.

## Open Decisions
- None for Phase 1 baseline.
