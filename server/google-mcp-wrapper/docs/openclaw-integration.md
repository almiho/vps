# OpenClaw Integration

## Connection model
- OpenClaw connects to wrapper over internal TCP on private Docker network.
- Wrapper endpoint: `http://google-mcp-wrapper:8091/mcp` (example service DNS in compose network).
- OpenClaw sends `Authorization: Bearer <WRAPPER_API_TOKEN>`.

## Suggested registration flow
1. Ensure wrapper container is healthy (`/healthz`, `/readyz`).
2. Register MCP endpoint in OpenClaw config for Google tools.
3. Validate with safe calls (`tools/list`, read-only `tools/call`).
4. Confirm blocked operations (`send/delete`) return policy errors.

## Operational checks
- Auth failures visible in wrapper logs.
- Denies and rate-limit events visible in audit log.
- Optional dashboard tile reads only `/status.json`.
