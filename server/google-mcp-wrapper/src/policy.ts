import fs from "node:fs";

import type { Policy } from "./types.js";

export function loadPolicy(path: string): Policy {
  const raw = fs.readFileSync(path, "utf8");
  return JSON.parse(raw) as Policy;
}

export function validateToolName(policy: Policy, toolName: string): { allowed: boolean; reason?: string } {
  if (!policy.allowedTools.includes(toolName)) {
    return { allowed: false, reason: `Tool not allowlisted: ${toolName}` };
  }

  const denied = policy.deniedNamePatterns.some((pattern) => {
    const re = new RegExp(pattern, "i");
    return re.test(toolName);
  });

  if (denied) {
    return { allowed: false, reason: `Tool denied by pattern: ${toolName}` };
  }

  return { allowed: true };
}
