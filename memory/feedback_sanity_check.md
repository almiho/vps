---
name: Sanity check must verify dashboard reachability
description: When Alex asks if everything is fine, always probe the dashboard HTTP endpoint — don't just read status.json
type: feedback
originSessionId: ef130c26-9460-42c7-929c-b93b5c6b7a9a
---
When asked "is everything fine?" or similar sanity-check questions, always do a live HTTP probe of the dashboard (curl http://100.67.100.125:8080/) — not just read status.json or monitoring agent output. Those can be stale if the web server died.

**Why:** In Apr 2026 the web server went down during an update. The monitoring status.json still said "dashboard reachable" (last cached check). A live curl would have caught it immediately, but the sanity check reported green.

**How to apply:** Any time Alex asks if the system is up, healthy, or running normally — include a live curl probe of the dashboard as part of the check before confirming things are OK.
