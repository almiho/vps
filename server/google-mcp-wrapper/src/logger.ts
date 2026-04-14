import fs from "node:fs";

export type LogLevel = "info" | "warn" | "error";

export function log(level: LogLevel, message: string, fields: Record<string, unknown> = {}): void {
  const entry = {
    ts: new Date().toISOString(),
    level,
    message,
    ...fields
  };
  process.stdout.write(`${JSON.stringify(entry)}\n`);
}

export function appendAudit(auditLogPath: string, fields: Record<string, unknown>): void {
  const entry = {
    ts: new Date().toISOString(),
    ...fields
  };
  fs.appendFileSync(auditLogPath, `${JSON.stringify(entry)}\n`, { encoding: "utf8" });
}
