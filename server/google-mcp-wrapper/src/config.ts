import fs from "node:fs";

export type WrapperConfig = {
  port: number;
  wrapperApiToken: string;
  downstreamMcpUrl: string;
  requestTimeoutMs: number;
  rateLimitPerMinute: number;
  rateLimitPerDay: number;
  maxToolCallsPerRequest: number;
  policyFilePath: string;
  auditLogPath: string;
};

function must(name: string): string {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Missing required env var: ${name}`);
  }
  return value;
}

function intOr(name: string, fallback: number): number {
  const raw = process.env[name];
  if (!raw) {
    return fallback;
  }
  const parsed = Number.parseInt(raw, 10);
  if (Number.isNaN(parsed)) {
    throw new Error(`Invalid integer env var ${name}: ${raw}`);
  }
  return parsed;
}

export function loadConfig(): WrapperConfig {
  const config: WrapperConfig = {
    port: intOr("WRAPPER_PORT", 8091),
    wrapperApiToken: must("WRAPPER_API_TOKEN"),
    downstreamMcpUrl: must("DOWNSTREAM_MCP_URL"),
    requestTimeoutMs: intOr("REQUEST_TIMEOUT_MS", 15000),
    rateLimitPerMinute: intOr("RATE_LIMIT_PER_MINUTE", 120),
    rateLimitPerDay: intOr("RATE_LIMIT_PER_DAY", 5000),
    maxToolCallsPerRequest: intOr("MAX_TOOL_CALLS_PER_REQUEST", 1),
    policyFilePath: process.env.POLICY_FILE_PATH ?? "./policy/allowlist.json",
    auditLogPath: process.env.AUDIT_LOG_PATH ?? "./data/audit.log"
  };

  const auditDir = config.auditLogPath.split("/").slice(0, -1).join("/");
  if (auditDir) {
    fs.mkdirSync(auditDir, { recursive: true });
  }

  return config;
}
