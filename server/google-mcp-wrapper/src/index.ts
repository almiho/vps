import crypto from "node:crypto";

import express from "express";
import type { Request, Response as ExpressResponse } from "express";

import { loadConfig } from "./config.js";
import { appendAudit, log } from "./logger.js";
import { getStatusSummary, recordAuthFailure, recordCall, recordDenied, recordRateLimited, recordUpstreamError, renderPrometheus } from "./metrics.js";
import { loadPolicy, validateToolName } from "./policy.js";
import { checkRateLimit } from "./rateLimit.js";
import type { JsonRpcRequest, JsonRpcResponse } from "./types.js";

const app = express();
app.use(express.json({ limit: "1mb" }));

const config = loadConfig();
const policy = loadPolicy(config.policyFilePath);

function authOk(authHeader: string | undefined): boolean {
  if (!authHeader?.startsWith("Bearer ")) {
    return false;
  }
  const provided = authHeader.slice("Bearer ".length);
  const a = Buffer.from(provided);
  const b = Buffer.from(config.wrapperApiToken);
  if (a.length !== b.length) {
    return false;
  }
  return crypto.timingSafeEqual(a, b);
}

function deny(res: ExpressResponse, id: JsonRpcRequest["id"], code: number, message: string): void {
  const response: JsonRpcResponse = {
    jsonrpc: "2.0",
    id,
    error: { code, message }
  };
  res.status(200).json(response);
}

app.get("/healthz", (_req: Request, res: ExpressResponse) => {
  res.status(200).send("ok");
});

app.get("/readyz", (_req: Request, res: ExpressResponse) => {
  res.status(200).send("ready");
});

app.get("/metrics", (_req: Request, res: ExpressResponse) => {
  res.type("text/plain").send(renderPrometheus());
});

app.get("/status.json", (_req: Request, res: ExpressResponse) => {
  const status = {
    ...getStatusSummary(),
    last_success_ts: new Date().toISOString()
  };
  res.status(200).json(status);
});

app.post("/mcp", async (req: Request, res: ExpressResponse) => {
  const started = Date.now();
  const requestId = crypto.randomUUID();
  const caller = req.ip;

  if (!authOk(req.header("authorization"))) {
    recordAuthFailure();
    appendAudit(config.auditLogPath, {
      request_id: requestId,
      caller,
      decision: "deny",
      reason: "invalid auth token"
    });
    res.status(401).json({ error: "unauthorized" });
    return;
  }

  const jsonRpc = req.body as JsonRpcRequest;
  if (!jsonRpc || jsonRpc.jsonrpc !== "2.0" || typeof jsonRpc.method !== "string") {
    res.status(400).json({ error: "invalid json-rpc payload" });
    return;
  }

  if (jsonRpc.method === "tools/call") {
    const params = (jsonRpc.params ?? {}) as Record<string, unknown>;
    const toolName = String(params.name ?? "");

    const allowed = validateToolName(policy, toolName);
    if (!allowed.allowed) {
      recordDenied();
      appendAudit(config.auditLogPath, {
        request_id: requestId,
        caller,
        tool: toolName,
        decision: "deny",
        reason: allowed.reason
      });
      deny(res, jsonRpc.id, -32001, allowed.reason ?? "denied by policy");
      return;
    }

    const quota = checkRateLimit(`global:${toolName}`, config.rateLimitPerMinute, config.rateLimitPerDay);
    if (!quota.ok) {
      recordRateLimited();
      appendAudit(config.auditLogPath, {
        request_id: requestId,
        caller,
        tool: toolName,
        decision: "deny",
        reason: quota.reason
      });
      deny(res, jsonRpc.id, -32002, `rate limit: ${quota.reason}`);
      return;
    }
  }

  let upstreamRes: globalThis.Response;
  try {
    const mcpSessionId = req.header("mcp-session-id");
    const headers: Record<string, string> = {
      "content-type": "application/json",
      accept: "application/json, text/event-stream"
    };
    if (mcpSessionId) {
      headers["mcp-session-id"] = mcpSessionId;
    }

    upstreamRes = await fetch(config.downstreamMcpUrl, {
      method: "POST",
      headers,
      body: JSON.stringify(req.body),
      signal: AbortSignal.timeout(config.requestTimeoutMs)
    });
  } catch (error) {
    recordUpstreamError();
    appendAudit(config.auditLogPath, {
      request_id: requestId,
      caller,
      decision: "error",
      reason: "downstream unreachable",
      detail: error instanceof Error ? error.message : String(error)
    });
    res.status(502).json({ error: "downstream mcp unavailable" });
    return;
  }

  const responseBody = await upstreamRes.text();
  const downstreamSessionId = upstreamRes.headers.get("mcp-session-id");
  if (downstreamSessionId) {
    res.setHeader("mcp-session-id", downstreamSessionId);
  }
  const downstreamProtocolVersion = upstreamRes.headers.get("mcp-protocol-version");
  if (downstreamProtocolVersion) {
    res.setHeader("mcp-protocol-version", downstreamProtocolVersion);
  }
  const downstreamContentType = upstreamRes.headers.get("content-type");
  if (downstreamContentType) {
    res.setHeader("content-type", downstreamContentType);
  }
  const latency = Date.now() - started;
  recordCall(latency);
  log("info", "proxy_call", {
    request_id: requestId,
    caller,
    status_code: upstreamRes.status,
    latency_ms: latency
  });

  res.status(upstreamRes.status).send(responseBody);
});

app.listen(config.port, () => {
  log("info", "wrapper_started", {
    port: config.port,
    downstream_mcp_url: config.downstreamMcpUrl
  });
});
