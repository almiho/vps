# Observability

## Logs
Wrapper emits JSON logs to stdout with fields:
- `ts`, `level`, `message`
- `request_id`, `caller`, `status_code`, `latency_ms`

## Audit log
Append-only log at `AUDIT_LOG_PATH` (default `./data/audit.log`) for policy and auth decisions.

## Health
- `GET /healthz` -> process liveness
- `GET /readyz` -> config/downstream readiness (phase 1 returns static ready, can be expanded)

## Metrics
`GET /metrics` exposes:
- `wrapper_calls_total`
- `wrapper_denied_total`
- `wrapper_rate_limited_total`
- `wrapper_auth_failures_total`
- `wrapper_upstream_errors_total`
- `wrapper_latency_p95_ms`

## Status summary contract
`GET /status.json` returns sanitized summary for optional OC dashboard tile.
