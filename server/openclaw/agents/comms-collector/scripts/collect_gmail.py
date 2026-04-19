#!/usr/bin/env python3
"""
Comms Collector — Gmail collection script
Phase 1: read-only Gmail via Google MCP wrapper

PASSIVE MODE: This script requires --run to do anything.
Without --run it exits immediately. This is intentional.

Usage:
    GOOGLE_WRAPPER_TOKEN=<token> python3 collect_gmail.py --run
"""

import sys

# ─── PASSIVE MODE GUARD ───────────────────────────────────────────────────────
# Alexander's explicit instruction: no automated collection whatsoever.
# Only run when explicitly invoked with --run.
if "--run" not in sys.argv:
    print("PASSIVE MODE ACTIVE — Comms Collector will not collect without --run.")
    print("To collect: GOOGLE_WRAPPER_TOKEN=<token> python3 collect_gmail.py --run")
    sys.exit(0)
# ─────────────────────────────────────────────────────────────────────────────

import json
import os
import sqlite3
import datetime
from pathlib import Path

import urllib.request
import urllib.error

# ─── Paths ────────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = SCRIPT_DIR.parents[2]  # scripts/ -> comms-collector/ -> agents/ -> workspace/
CONFIG_PATH = WORKSPACE_ROOT / "agents" / "comms-collector" / "config" / "gmail.json"
BUS_DB_PATH = WORKSPACE_ROOT / "data" / "bus.db"
STATUS_PATH = WORKSPACE_ROOT / "agents" / "comms-collector" / "dashboard" / "status.json"


def log(msg: str):
    ts = datetime.datetime.now().isoformat(timespec="seconds")
    print(f"[{ts}] {msg}", flush=True)


def load_config() -> dict:
    log(f"Loading config from {CONFIG_PATH}")
    with open(CONFIG_PATH) as f:
        config = json.load(f)
    log(f"Config loaded: email='{config.get('user_google_email')}' query='{config['query']}' max_results={config['max_results']} wrapper={config['wrapper_url']}")
    return config


def get_token() -> str:
    token = os.environ.get("GOOGLE_WRAPPER_TOKEN", "")
    if not token:
        log("ERROR: GOOGLE_WRAPPER_TOKEN env var not set")
        sys.exit(1)
    log("Bearer token loaded from GOOGLE_WRAPPER_TOKEN")
    return token


def mcp_post(url: str, token: str, payload: dict) -> tuple[dict | None, dict]:
    """POST a JSON-RPC payload to the MCP wrapper. Returns (response_headers_dict, parsed_body)."""
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "Accept": "application/json, text/event-stream",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            headers = {k.lower(): v for k, v in resp.headers.items()}
            return headers, parse_mcp_response(raw)
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8")
        log(f"HTTP error {e.code}: {raw[:500]}")
        raise


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
        raise ValueError(f"No parseable data line in SSE response: {raw[:300]}")
    return json.loads(raw)


def init_mcp_session(wrapper_url: str, token: str) -> str:
    """Initialise MCP session and return the session ID."""
    log("Initialising MCP session...")
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "comms-collector", "version": "1.0"},
        },
    }
    headers, body = mcp_post(wrapper_url, token, payload)
    session_id = headers.get("mcp-session-id", "")
    if not session_id:
        log("WARNING: No mcp-session-id in response headers — wrapper may not require it")
    else:
        log(f"MCP session initialised: {session_id}")
    return session_id


def call_tool(wrapper_url: str, token: str, session_id: str, tool_name: str, arguments: dict) -> dict:
    """Call an MCP tool and return the result."""
    log(f"Calling tool: {tool_name} with args: {arguments}")
    headers_map = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "Accept": "application/json, text/event-stream",
    }
    if session_id:
        headers_map["mcp-session-id"] = session_id

    payload = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments},
    }
    body_bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(wrapper_url, data=body_bytes, headers=headers_map, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8")
            return parse_mcp_response(raw)
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8")
        log(f"HTTP error {e.code} calling {tool_name}: {raw[:500]}")
        raise


def extract_tool_result(response: dict) -> list | dict | str | None:
    """Dig out the actual result content from a JSON-RPC tools/call response."""
    result = response.get("result", {})
    # MCP wraps content in result.content array
    content = result.get("content", [])
    if isinstance(content, list) and content:
        # Usually first item is {"type": "text", "text": "..."}
        first = content[0]
        if isinstance(first, dict) and "text" in first:
            try:
                return json.loads(first["text"])
            except (json.JSONDecodeError, TypeError):
                return first["text"]
    return result


def search_messages(wrapper_url: str, token: str, session_id: str, query: str, max_results: int, email: str) -> list:
    """Search Gmail for messages matching query."""
    log(f"Searching Gmail: query='{query}' max_results={max_results}")
    response = call_tool(wrapper_url, token, session_id, "search_gmail_messages", {
        "user_google_email": email,
        "query": query,
        "page_size": max_results,
    })
    result = extract_tool_result(response)
    if isinstance(result, list):
        log(f"Found {len(result)} messages")
        return result
    elif isinstance(result, dict) and "messages" in result:
        msgs = result["messages"]
        log(f"Found {len(msgs)} messages")
        return msgs
    elif isinstance(result, str):
        # Parse text response — extract Message IDs
        import re
        ids = re.findall(r'Message ID:\s*([a-f0-9]+)', result)
        thread_ids = re.findall(r'Thread ID:\s*([a-f0-9]+)', result)
        if ids:
            msgs = [{"id": mid, "threadId": tid} for mid, tid in zip(ids, thread_ids or ids)]
            log(f"Parsed {len(msgs)} message IDs from text response")
            return msgs
        log(f"Unexpected search result shape: {type(result)} — {str(result)[:200]}")
        return []
    else:
        log(f"Unexpected search result shape: {type(result)} — {str(result)[:200]}")
        return []


def fetch_message_content(wrapper_url: str, token: str, session_id: str, message_id: str, email: str) -> dict:
    """Fetch full content of a single Gmail message."""
    log(f"Fetching message content: {message_id}")
    response = call_tool(wrapper_url, token, session_id, "get_gmail_message_content", {
        "user_google_email": email,
        "message_id": message_id,
    })
    result = extract_tool_result(response)
    if isinstance(result, dict):
        return result
    if isinstance(result, str):
        # Wrapper returned plain text — parse subject/from/body from text
        import re
        parsed = {}
        m = re.search(r'Subject:\s*(.+)', result)
        if m: parsed['subject'] = m.group(1).strip()
        m = re.search(r'From:\s*(.+)', result)
        if m: parsed['from'] = m.group(1).strip()
        # Body is everything after '--- BODY ---'
        body_match = re.split(r'---\s*BODY\s*---', result, maxsplit=1)
        if len(body_match) > 1:
            parsed['body'] = body_match[1].strip()[:2000]
        parsed['id'] = message_id
        return parsed
    log(f"Unexpected content shape for {message_id}: {type(result)}")
    return {}


def normalise_message(msg_summary: dict, msg_content: dict, google_account: str = "") -> dict:
    """Normalise a Gmail message to the SQLite bus schema."""
    thread_id = msg_summary.get("threadId") or msg_content.get("threadId") or ""
    message_id = msg_summary.get("id") or msg_content.get("id") or ""

    # Extract headers
    headers = {}
    for h in msg_content.get("payload", {}).get("headers", []):
        headers[h.get("name", "").lower()] = h.get("value", "")

    from_raw = headers.get("from", "") or msg_content.get("from", "")
    subject = headers.get("subject", "") or msg_content.get("subject", "No subject")

    # Parse "Name <email>" or plain email
    sender_name, source_address = parse_from(from_raw)

    # Extract plain text body
    body = extract_body(msg_content)

    reply_context = json.dumps({
        "thread_id": thread_id,
        "message_id": message_id,
        "from": from_raw,
        "subject": subject,
        "google_account": google_account,  # needed for sending replies via MCP
    })

    return {
        "source_channel": "gmail",
        "source_id": thread_id,
        "source_address": source_address,
        "sender_name": sender_name,
        "subject": subject,
        "body": body,
        "reply_context": reply_context,
        "domain_tag": None,
        "status": "pending",
    }


def parse_from(from_raw: str) -> tuple[str, str]:
    """Parse 'Display Name <email@example.com>' into (name, email)."""
    from_raw = from_raw.strip()
    if "<" in from_raw and ">" in from_raw:
        name = from_raw[:from_raw.index("<")].strip().strip('"')
        email = from_raw[from_raw.index("<") + 1:from_raw.index(">")].strip()
        return name, email
    return "", from_raw


def extract_body(msg_content: dict) -> str:
    """Extract plain text body from message content, trying multiple locations."""
    # Direct body field
    if "body" in msg_content and isinstance(msg_content["body"], str):
        return msg_content["body"]

    # Nested payload parts
    payload = msg_content.get("payload", {})
    body_data = payload.get("body", {}).get("data", "")
    if body_data:
        return decode_base64url(body_data)

    # Multi-part — prefer text/plain
    for part in payload.get("parts", []):
        if part.get("mimeType") == "text/plain":
            data = part.get("body", {}).get("data", "")
            if data:
                return decode_base64url(data)

    # Fallback: snippet
    return msg_content.get("snippet", "")


def decode_base64url(data: str) -> str:
    import base64
    # Gmail uses URL-safe base64 without padding
    padded = data.replace("-", "+").replace("_", "/")
    padded += "=" * (4 - len(padded) % 4) if len(padded) % 4 else ""
    try:
        return base64.b64decode(padded).decode("utf-8", errors="replace")
    except Exception:
        return data


ALEXI_LABEL_ID = "Label_3379905650781172604"


def apply_alexi_label(wrapper_url: str, token: str, session_id: str, message_id: str, email: str) -> bool:
    """Apply the 'AlexI' Gmail label to a message to mark it as picked up."""
    try:
        call_tool(wrapper_url, token, session_id, "modify_gmail_message_labels", {
            "user_google_email": email,
            "message_id": message_id,
            "add_label_ids": [ALEXI_LABEL_ID],
        })
        log(f"Applied AlexI label to message {message_id}")
        return True
    except Exception as e:
        log(f"WARNING: Could not apply AlexI label to {message_id}: {e}")
        return False


def write_to_bus(db_path: Path, record: dict) -> bool:
    """Write a normalised message to bus.db. Returns True if inserted, False if skipped (duplicate)."""
    conn = sqlite3.connect(str(db_path))
    try:
        cursor = conn.cursor()
        # Check for existing source_id
        cursor.execute("SELECT id FROM messages WHERE source_id = ?", (record["source_id"],))
        if cursor.fetchone():
            log(f"Skipping duplicate source_id: {record['source_id']}")
            return False

        import uuid as _uuid
        now = datetime.datetime.now().isoformat(timespec="seconds")
        record.setdefault('id', str(_uuid.uuid4()))
        record.setdefault('created_at', now)
        record.setdefault('updated_at', now)
        cursor.execute("""
            INSERT INTO messages
                (id, created_at, updated_at, source_channel, source_id, source_address,
                 sender_name, subject, body, reply_context, domain_tag, status)
            VALUES
                (:id, :created_at, :updated_at, :source_channel, :source_id, :source_address,
                 :sender_name, :subject, :body, :reply_context, :domain_tag, :status)
        """, record)
        conn.commit()
        log(f"Inserted message: source_id={record['source_id']} from={record['source_address']}")
        return True
    finally:
        conn.close()


def update_status(collected: int, inserted: int, skipped: int, error: str | None = None):
    health = "ok" if not error else "error"
    summary = (
        f"Last run: collected {collected} messages, {inserted} new, {skipped} skipped."
        if not error
        else f"Error during collection: {error}"
    )
    status = {
        "agent": "comms-collector",
        "updated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "health": health,
        "summary": summary,
        "alerts": [{"priority": 1, "title": error, "body": error, "due_at": None, "action_required": True}] if error else [],
        "upcoming": [],
    }
    with open(STATUS_PATH, "w") as f:
        json.dump(status, f, indent=2)
    log(f"Status updated: health={health}")


def main():
    log("=== Comms Collector — Gmail collection starting ===")

    config = load_config()
    token = get_token()

    wrapper_url = config["wrapper_url"]
    query = config["query"]
    max_results = config["max_results"]
    email = config.get("user_google_email", "almiho@gmail.com")

    # Init MCP session
    session_id = init_mcp_session(wrapper_url, token)

    # Search Gmail
    messages = search_messages(wrapper_url, token, session_id, query, max_results, email)

    if not messages:
        log("No messages found matching query.")
        update_status(0, 0, 0)
        return

    inserted = 0
    skipped = 0

    for msg_summary in messages:
        msg_id = msg_summary.get("id") or msg_summary.get("message_id") or ""
        if not msg_id:
            log(f"WARNING: message summary has no id field: {msg_summary}")
            skipped += 1
            continue

        try:
            msg_content = fetch_message_content(wrapper_url, token, session_id, msg_id, email)
        except Exception as e:
            log(f"ERROR fetching content for {msg_id}: {e}")
            skipped += 1
            continue

        record = normalise_message(msg_summary, msg_content, google_account=email)

        if not record["source_id"]:
            log(f"WARNING: no thread_id for message {msg_id}, using message_id as source_id")
            record["source_id"] = msg_id

        try:
            was_inserted = write_to_bus(BUS_DB_PATH, record)
            if was_inserted:
                inserted += 1
                # Mark as picked up in Gmail with AlexI label
                apply_alexi_label(wrapper_url, token, session_id, msg_id, email)
            else:
                skipped += 1
        except Exception as e:
            log(f"ERROR writing to bus for {msg_id}: {e}")
            skipped += 1

    log(f"=== Collection complete: {len(messages)} found, {inserted} inserted, {skipped} skipped ===")
    update_status(len(messages), inserted, skipped)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"FATAL: {e}")
        update_status(0, 0, 0, error=str(e))
        sys.exit(1)
