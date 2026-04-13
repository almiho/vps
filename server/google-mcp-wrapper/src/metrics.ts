type Metrics = {
  totalCalls: number;
  deniedCalls: number;
  rateLimitedCalls: number;
  authFailures: number;
  upstreamErrors: number;
  latencies: number[];
};

const metrics: Metrics = {
  totalCalls: 0,
  deniedCalls: 0,
  rateLimitedCalls: 0,
  authFailures: 0,
  upstreamErrors: 0,
  latencies: []
};

export function recordCall(latencyMs: number): void {
  metrics.totalCalls += 1;
  metrics.latencies.push(latencyMs);
  if (metrics.latencies.length > 5000) {
    metrics.latencies.shift();
  }
}

export function recordDenied(): void {
  metrics.deniedCalls += 1;
}

export function recordRateLimited(): void {
  metrics.rateLimitedCalls += 1;
}

export function recordAuthFailure(): void {
  metrics.authFailures += 1;
}

export function recordUpstreamError(): void {
  metrics.upstreamErrors += 1;
}

function p95(): number {
  if (metrics.latencies.length === 0) {
    return 0;
  }
  const sorted = [...metrics.latencies].sort((a, b) => a - b);
  const idx = Math.floor(0.95 * (sorted.length - 1));
  return sorted[idx] ?? 0;
}

export function getStatusSummary() {
  return {
    service: "google-mcp-wrapper",
    health: "ok",
    calls_1h: metrics.totalCalls,
    denied_1h: metrics.deniedCalls,
    rate_limited_1h: metrics.rateLimitedCalls,
    error_rate_1h: metrics.totalCalls === 0 ? 0 : metrics.upstreamErrors / metrics.totalCalls,
    p95_latency_ms: p95(),
    version: process.env.npm_package_version ?? "0.1.0"
  };
}

export function renderPrometheus(): string {
  return [
    `wrapper_calls_total ${metrics.totalCalls}`,
    `wrapper_denied_total ${metrics.deniedCalls}`,
    `wrapper_rate_limited_total ${metrics.rateLimitedCalls}`,
    `wrapper_auth_failures_total ${metrics.authFailures}`,
    `wrapper_upstream_errors_total ${metrics.upstreamErrors}`,
    `wrapper_latency_p95_ms ${p95()}`
  ].join("\n");
}
