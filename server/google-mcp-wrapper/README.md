# Google MCP Wrapper

Policy-enforcing MCP proxy for OpenClaw access to Google services (`Gmail`, `Calendar`, `Drive`).

## Phase 1 scope
- MCP proxy mode (northbound MCP to OpenClaw, southbound MCP to downstream Google MCP server)
- Read-focused allowlist policy
- Bearer token auth (`WRAPPER_API_TOKEN`) for OC -> wrapper calls
- Rate limiting and audit logging
- Internal-only Docker network (no published ports)
- Read-only `status.json` for optional OC dashboard tile

## Quick start
1. Copy env template:
   - `cp .env.example .env`
2. Set required values in `.env`:
   - `WRAPPER_API_TOKEN`
   - `DOWNSTREAM_MCP_URL`
3. Build and run:
   - `docker compose up -d --build`

## Endpoints
- `POST /mcp` - MCP proxy endpoint (requires bearer token)
- `GET /healthz` - liveness
- `GET /readyz` - readiness
- `GET /metrics` - Prometheus-style metrics
- `GET /status.json` - sanitized status summary

## Security baseline
- No public port publishing
- Non-root container user
- Read-only filesystem
- Capabilities dropped
- No Docker socket mount

## Notes
- This is the initial implementation scaffold. Tool-specific argument validation can be expanded in `src/policy.ts`.
- Keep Google OAuth credentials outside OpenClaw and available only to wrapper/downstream Google MCP components.
