# Security Model

## Trust boundaries
- OpenClaw can call wrapper only with `WRAPPER_API_TOKEN`.
- Wrapper can call downstream Google MCP.
- Google credentials are not stored in OpenClaw.

## Controls
- Default deny policy with explicit allowlist.
- Name-based deny patterns for destructive operations.
- Rate limiting (minute/day) per tool.
- Audit logging for allow/deny/error decisions.
- Container hardening (`read_only`, `cap_drop: ALL`, `no-new-privileges`).

## Token lifecycle
- Generate high-entropy token (`openssl rand -base64 48`).
- Store in runtime secrets/env only.
- Rotate every 30 days or immediately after suspected exposure.
- During rotation, accept old+new token briefly, then revoke old.

## Non-goals (phase 1)
- No write/delete Google operations.
- No wrapper admin controls exposed to dashboard.
