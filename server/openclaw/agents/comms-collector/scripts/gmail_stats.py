#!/usr/bin/env python3
"""
Comms Collector — Gmail inbox stats (read-only)
Fetches Gmail INBOX unread count via the Google MCP wrapper.
Updates dashboard/status.json and dashboard/detail.html.

This is display-only — no messages are collected or written to the bus.
Runs every 30 minutes via the scheduler.

Token resolution order:
  1. GOOGLE_WRAPPER_TOKEN env var
  2. /home/node/.openclaw/openclaw.json (mcp.servers.google-wrapper-local.headers.Authorization)
"""

import json
import os
import sys
import re
import datetime
import urllib.request
import urllib.error
from pathlib import Path

SCRIPT_DIR     = Path(__file__).resolve().parent
WORKSPACE_ROOT = SCRIPT_DIR.parents[2]          # scripts/ -> comms-collector/ -> agents/ -> workspace/
CONFIG_PATH    = WORKSPACE_ROOT / "agents" / "comms-collector" / "config" / "gmail.json"
STATUS_PATH    = WORKSPACE_ROOT / "agents" / "comms-collector" / "dashboard" / "status.json"
DETAIL_PATH    = WORKSPACE_ROOT / "agents" / "comms-collector" / "dashboard" / "detail.html"
OPENCLAW_JSON  = Path("/home/node/.openclaw/openclaw.json")
WRAPPER_URL    = "http://127.0.0.1:8091/mcp"
PAGE_SIZE      = 500   # fetch up to 500 per query to count accurately


def log(msg: str):
    ts = datetime.datetime.now().isoformat(timespec="seconds")
    print(f"[{ts}] gmail_stats: {msg}", flush=True)


def get_token() -> str:
    token = os.environ.get("GOOGLE_WRAPPER_TOKEN", "")
    if token:
        log("Token loaded from GOOGLE_WRAPPER_TOKEN env var")
        return token
    try:
        with open(OPENCLAW_JSON) as f:
            oc = json.load(f)
        auth = oc["mcp"]["servers"]["google-wrapper-local"]["headers"]["Authorization"]
        token = auth.removeprefix("Bearer ").strip()
        log("Token loaded from openclaw.json")
        return token
    except Exception as e:
        log(f"ERROR: could not load token from env or openclaw.json: {e}")
        sys.exit(1)


def parse_mcp_response(raw: str) -> dict:
    """Handle both plain JSON and SSE (event:/data: lines) responses."""
    raw = raw.strip()
    # SSE format: may start with "event: message" or directly with "data:"
    if raw.startswith("event:") or raw.startswith("data:"):
        for line in reversed(raw.splitlines()):
            line = line.strip()
            if line.startswith("data:"):
                json_str = line[len("data:"):].strip()
                if json_str and json_str != "[DONE]":
                    return json.loads(json_str)
        raise ValueError(f"No parseable data line in SSE: {raw[:300]}")
    return json.loads(raw)


def mcp_post(url: str, token: str, payload: dict, session_id: str = "") -> tuple[dict, dict]:
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "Accept": "application/json, text/event-stream",
    }
    if session_id:
        headers["mcp-session-id"] = session_id
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode("utf-8")
        resp_headers = {k.lower(): v for k, v in resp.headers.items()}
        return resp_headers, parse_mcp_response(raw)


def init_session(token: str) -> str:
    resp_headers, _ = mcp_post(WRAPPER_URL, token, {
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "comms-stats", "version": "1.0"},
        },
    })
    session_id = resp_headers.get("mcp-session-id", "")
    log(f"MCP session: {session_id or '(none)'}")
    return session_id


def search_messages_count(token: str, session_id: str, email: str, query: str) -> tuple[int, bool]:
    """
    Count messages matching query. Returns (count, has_more).
    Uses pagination to count beyond PAGE_SIZE if needed, up to 2 pages total
    (enough to distinguish "47" from "500+").
    """
    total = 0
    page_token = None

    for page in range(2):   # At most 2 pages = up to 1000 messages counted
        args: dict = {
            "user_google_email": email,
            "query": query,
            "page_size": PAGE_SIZE,
        }
        if page_token:
            args["page_token"] = page_token

        _, body = mcp_post(WRAPPER_URL, token, {
            "jsonrpc": "2.0", "id": 10 + page, "method": "tools/call",
            "params": {"name": "search_gmail_messages", "arguments": args},
        }, session_id)

        result = body.get("result", {})
        content = result.get("content", [])
        text = content[0].get("text", "") if content else ""

        if result.get("isError"):
            log(f"Search error: {text[:200]}")
            break

        # Count messages from the text block "Found N messages matching..."
        # The text lists each message under "📧 MESSAGES:", count "N. Message ID:" lines
        msg_ids = re.findall(r"\d+\. Message ID:", text)
        count_this_page = len(msg_ids)
        total += count_this_page
        log(f"  page {page+1}: {count_this_page} messages (running total: {total})")

        # Check for pagination token
        token_match = re.search(r"page_token='([^']+)'", text)
        if token_match and count_this_page == PAGE_SIZE:
            page_token = token_match.group(1)
            # More pages exist — stop counting and flag as "N+"
            log(f"  pagination token found, more messages exist beyond {total}")
            return total, True
        else:
            break

    return total, False


def write_status(unread: int, unread_more: bool, error: str | None = None):
    now = datetime.datetime.now().isoformat(timespec="seconds")
    unread_display = f"{unread}+" if unread_more else str(unread)
    if error:
        status = {
            "agent": "comms-collector",
            "updated_at": now,
            "health": "warning",
            "summary": f"Gmail stats unavailable: {error}",
            "gmail_inbox_unread": None,
            "gmail_inbox_unread_display": None,
            "gmail_stats_updated_at": now,
            "alerts": [],
            "upcoming": [],
        }
    else:
        status = {
            "agent": "comms-collector",
            "updated_at": now,
            "health": "ok",
            "summary": f"Passive mode. Gmail inbox: {unread_display} unread.",
            "gmail_inbox_unread": unread,
            "gmail_inbox_unread_more": unread_more,
            "gmail_inbox_unread_display": unread_display,
            "gmail_stats_updated_at": now,
            "alerts": [],
            "upcoming": [],
        }
    with open(STATUS_PATH, "w") as f:
        json.dump(status, f, indent=2)
    log(f"status.json written: unread={unread_display}")


def write_detail_html(unread: int, unread_more: bool, stats_ts: str, error: str | None = None):
    unread_display = f"{unread:,}+" if unread_more else f"{unread:,}"
    if error:
        stats_html = f"""
<section id="comms-gmail-stats">
  <h3>Gmail Inbox</h3>
  <p class="stats-error">Stats unavailable: {error}</p>
  <p class="stats-note">Last attempted: {stats_ts}</p>
</section>"""
    else:
        unread_class = "stats-warn" if unread > 0 else "stats-ok"
        stats_html = f"""
<section id="comms-gmail-stats">
  <h3>Gmail Inbox</h3>
  <table class="stats-table">
    <tr><th>Unread</th><td class="{unread_class}">{unread_display}</td></tr>
  </table>
  <p class="stats-note">Last checked: {stats_ts}</p>
</section>"""

    html = f"""<!-- Comms Collector Agent — Detail Page Content Block -->
<!-- Assembled by Dashboard Agent into full page shell -->

<section id="comms-header">
  <h2>Comms Collector Agent</h2>
  <p class="last-updated">Last updated: <span id="comms-updated">{stats_ts}</span></p>
  <p class="health-status health-ok">&#9679; OK</p>
  <p class="summary">Passive mode. Gmail inbox: {unread_display} unread.</p>
</section>
{stats_html}
<section id="comms-passive-notice">
  <h3>&#9888; Passive Mode Active</h3>
  <p>This agent collects <strong>only when explicitly invoked</strong> by Alexander or AlexI. There is no automated collection, no cron schedule, and no background polling. This is by design — Alexander's explicit instruction on 2026-04-15.</p>
  <p>To invoke: <code>GOOGLE_WRAPPER_TOKEN=&lt;token&gt; python3 agents/comms-collector/scripts/collect_gmail.py --run</code></p>
</section>

<section id="comms-alerts">
  <h3>Alerts &amp; Actions</h3>
  <p class="no-alerts">No current alerts.</p>
</section>

<section id="comms-status">
  <h3>Current Status</h3>
  <ul>
    <li><strong>Mode:</strong> Passive — no automated collection</li>
    <li><strong>Phase 1 — Gmail:</strong> Connected. Google MCP wrapper running at http://127.0.0.1:8091/mcp</li>
    <li><strong>Phase 2 — WhatsApp:</strong> Planned (future milestone)</li>
    <li><strong>Phase 3 — Scanned letter OCR:</strong> Planned (future milestone)</li>
    <li><strong>Message bus:</strong> Writes to <code>data/bus.db</code>, table <code>messages</code></li>
    <li><strong>Duplicate guard:</strong> Skips by <code>source_id</code> (Gmail thread ID)</li>
  </ul>
</section>

<section id="comms-what-it-does">
  <h3>What Happens When Invoked</h3>
  <ol>
    <li>Initialises MCP session with the Google Workspace wrapper (port 8091)</li>
    <li>Calls <code>search_gmail_messages</code> with query <code>is:unread</code> (up to 50 results)</li>
    <li>For each message found, fetches full content via <code>get_gmail_message_content</code></li>
    <li>Normalises each message to the bus schema: source channel, sender, subject, body, reply context</li>
    <li>Writes new messages to <code>data/bus.db</code> with <code>status = 'pending'</code></li>
    <li>Skips messages already present (deduplication by thread ID)</li>
    <li>Updates <code>agents/comms-collector/dashboard/status.json</code> with run results</li>
  </ol>
  <p>The Comms Collector does <strong>not</strong> process, prioritise, route, or reply to messages. That is the Chief of Staff's responsibility (Milestone 5).</p>
</section>

<section id="comms-reporting-chain">
  <h3>Reporting Chain</h3>
  <p>Comms Collector &rarr; AlexI &rarr; Alexander</p>
  <p>This agent never contacts Alexander directly.</p>
</section>

<section id="comms-activity">
  <h3>Recent Activity</h3>
  <ul>
    <li>2026-04-15 &mdash; Agent scaffolded. Gmail read-only via MCP wrapper. Passive mode enforced per Alexander's instruction.</li>
    <li>{stats_ts[:10]} &mdash; Gmail inbox stats: {unread_display} unread.</li>
  </ul>
</section>

<section id="comms-docs">
  <h3>Reference Documents</h3>
  <ul>
    <li><a href="#">AGENT_STANDARDS.md</a> &mdash; System-wide rules</li>
    <li><a href="#">agents/comms-collector/AGENT.md</a> &mdash; Full mission brief</li>
    <li><a href="#">agents/comms-collector/config/gmail.json</a> &mdash; Gmail config</li>
    <li><a href="#">agents/comms-collector/scripts/collect_gmail.py</a> &mdash; Collection script</li>
    <li><a href="#">agents/comms-collector/scripts/gmail_stats.py</a> &mdash; Stats script (this)</li>
    <li><a href="#">docs/ROADMAP.md</a> &mdash; Milestone plan</li>
  </ul>
</section>
"""
    with open(DETAIL_PATH, "w") as f:
        f.write(html)
    log("detail.html written with live stats")


def main():
    log("=== Gmail stats run starting ===")
    token = get_token()
    now_str = datetime.datetime.now().isoformat(timespec="seconds")

    try:
        with open(CONFIG_PATH) as f:
            config = json.load(f)
        email = config.get("user_google_email", "almiho@gmail.com")
        log(f"Using account: {email}")

        session_id = init_session(token)

        log("Counting unread inbox messages...")
        unread, unread_more = search_messages_count(token, session_id, email, "in:inbox is:unread")
        log(f"Result: unread={unread} more={unread_more}")

        write_status(unread, unread_more)
        write_detail_html(unread, unread_more, now_str)
        log("=== Gmail stats run complete ===")

    except Exception as e:
        log(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        write_status(0, False, error=str(e))
        write_detail_html(0, False, now_str, error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
