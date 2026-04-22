#!/usr/bin/env python3
"""
School Agent — Message Bus Consumer

Reads domain=school tagged messages from the bus, assesses relevance
for Lukas & Jonas (Grade 3 → Grade 4 after summer), writes a comment
and confidence level, appends to messages_summary.json, and archives
the original Gmail message (removes INBOX label).

Runs every 15 min via scheduler.
"""

import json
import os
import re
import sqlite3
import sys
import urllib.request
import urllib.error
from datetime import datetime

sys.path.insert(0, "/home/node/.openclaw/workspace/scripts")
from agent_logger import AgentLogger

WORKSPACE       = "/home/node/.openclaw/workspace"
BUS_DB          = f"{WORKSPACE}/data/bus.db"
MESSAGES_FILE   = f"{WORKSPACE}/agents/school/data/messages_summary.json"
MCP_URL         = "http://localhost:3000/mcp"
ALEXI_LABEL_ID  = "Label_3379905650781172604"
MAX_MESSAGES    = 50  # keep last N in summary

log = AgentLogger("school")

# ── Grade context ─────────────────────────────────────────────────────────────
CURRENT_YEAR    = 2026
LUKAS_GRADE     = 3   # → Grade 4 after summer 2026
JONAS_GRADE     = 3   # twins

GRADE_PATTERNS = {
    "grade_3":  [r"\bgrade\s*3\b", r"\b3rd\s+grade\b", r"\bklasse\s*3\b", r"\bjahrgangsstufe\s*3\b", r"\bClass\s+3\b"],
    "grade_4":  [r"\bgrade\s*4\b", r"\b4th\s+grade\b", r"\bklasse\s*4\b", r"\bjahrgangsstufe\s*4\b", r"\bClass\s+4\b"],
    "whole_school": [r"\ball\s+students\b", r"\bwhole\s+school\b", r"\bentire\s+school\b", r"\balle\s+sch[üu]ler\b",
                     r"\bgesamte\s+schule\b", r"\bcommunity\b", r"\bliebe\s+eltern\b", r"\bdear\s+parents\b",
                     r"\bfamilies\b", r"\bcis\s+community\b"],
    "primary":  [r"\bprimary\b", r"\bGrundschule\b", r"\bgrade\s*[1-5]\b"],
    "secondary":[r"\bsecondary\s+school\b", r"\bhigh\s+school\b", r"\bOberstufe\b", r"\bMittelschule\b", r"\bgrade\s*[6-9]\b", r"\bgrade\s*1[0-2]\b"],
}

NEWS_KEYWORDS = [r"\bnewsletter\b", r"\bnews\b", r"\bcommunity\s+news\b", r"\bupdate\b", r"\bbulletin\b",
                 r"\bwoche\b", r"\bwöchentlich\b", r"\bweekly\b"]

EVENT_KEYWORDS = [r"\bevent\b", r"\bveranstaltung\b", r"\bconference\b", r"\bkonferenz\b",
                  r"\btrip\b", r"\bausflug\b", r"\bexcursion\b", r"\bconcert\b", r"\bKonzert\b",
                  r"\bsports\s+day\b", r"\bsporttag\b", r"\bworkshop\b"]

ACTION_KEYWORDS = [r"\bplease\s+(return|sign|bring|pay)\b", r"\bbitte\s+(zurück|unterschreib|mitbring|bezahl)\b",
                   r"\bpermission\b", r"\bErlaubnis\b", r"\bdeadline\b", r"\bFrist\b",
                   r"\bby\s+\w+day\b", r"\bbis\s+(montag|dienstag|mittwoch|donnerstag|freitag)\b"]


def load_messages():
    try:
        with open(MESSAGES_FILE) as f:
            return json.load(f)
    except Exception:
        return {"updated_at": datetime.now().strftime("%Y-%m-%d"), "messages": [], "note": "Processed school messages"}


def save_messages(data):
    data["updated_at"] = datetime.now().strftime("%Y-%m-%d")
    # Keep most recent MAX_MESSAGES
    data["messages"] = data["messages"][-MAX_MESSAGES:]
    os.makedirs(os.path.dirname(MESSAGES_FILE), exist_ok=True)
    with open(MESSAGES_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def match_patterns(text, patterns):
    text_lower = text.lower()
    return any(re.search(p, text_lower, re.IGNORECASE) for p in patterns)


def assess_relevance(subject, body, sender):
    """
    Determine relevance for Lukas & Jonas (Grade 3, → 4 after summer).
    Returns: (child, topic, comment, confidence, action_required)
    """
    combined = f"{subject} {body[:2000]}"
    
    is_grade3      = match_patterns(combined, GRADE_PATTERNS["grade_3"])
    is_grade4      = match_patterns(combined, GRADE_PATTERNS["grade_4"])
    is_whole_school= match_patterns(combined, GRADE_PATTERNS["whole_school"])
    is_primary     = match_patterns(combined, GRADE_PATTERNS["primary"])
    is_secondary   = match_patterns(combined, GRADE_PATTERNS["secondary"])
    is_news        = match_patterns(combined, NEWS_KEYWORDS)
    is_event       = match_patterns(combined, EVENT_KEYWORDS)
    is_action      = match_patterns(combined, ACTION_KEYWORDS)

    # Determine child scope
    if is_grade3 and not is_grade4:
        child = "both"
        grade_note = "Grade 3 — directly relevant for Lukas & Jonas"
        confidence = 90
    elif is_grade4 and not is_grade3:
        child = "both"
        grade_note = "Grade 4 — relevant for next school year (after summer)"
        confidence = 80
    elif is_whole_school or is_news:
        child = "both"
        grade_note = "Whole school / community — general relevance"
        confidence = 85
    elif is_primary and not is_secondary:
        child = "both"
        grade_note = "Primary school — likely relevant"
        confidence = 70
    elif is_secondary and not is_primary:
        child = "unknown"
        grade_note = "Secondary only — not relevant for Lukas & Jonas (Grade 3)"
        confidence = 75
    else:
        child = "both"
        grade_note = "No explicit grade mentioned — assuming general relevance"
        confidence = 55

    # Determine topic
    if is_action:
        topic = "Action required"
        comment = f"{grade_note}. Contains action item — check for deadlines or permissions needed."
        confidence = min(confidence + 5, 95)
    elif is_event:
        topic = "Event/Trip"
        comment = f"{grade_note}. Appears to be an upcoming event or school trip."
    elif is_news:
        topic = "Newsletter/News"
        comment = f"{grade_note}. Community newsletter — skim for relevant dates or events for Grade 3/4."
    else:
        topic = "General"
        comment = f"{grade_note}."

    # Lower confidence if secondary only
    if is_secondary and not is_primary and not is_grade3:
        comment += " Likely not relevant — secondary school content."
        confidence = max(confidence - 20, 30)

    return child, topic, comment, confidence, is_action


def init_mcp_session():
    """Initialize MCP session and return session ID."""
    try:
        init_payload = json.dumps({
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2024-11-05",
                       "capabilities": {},
                       "clientInfo": {"name": "school-agent", "version": "1.0"}}
        }).encode()
        req = urllib.request.Request(MCP_URL, data=init_payload,
                                     headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            session_id = resp.headers.get("Mcp-Session-Id") or resp.headers.get("X-Session-Id")
            return session_id
    except Exception as e:
        log.warning("mcp_session_fail", str(e))
        return None


def call_mcp_tool(session_id, tool_name, arguments):
    """Call an MCP tool with an existing session."""
    try:
        payload = json.dumps({
            "jsonrpc": "2.0", "id": 2, "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments}
        }).encode()
        headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
        if session_id:
            headers["Mcp-Session-Id"] = session_id
        req = urllib.request.Request(MCP_URL, data=payload, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode()
            # Handle SSE format
            if raw.startswith("data:"):
                for line in raw.split("\n"):
                    if line.startswith("data:"):
                        data = json.loads(line[5:].strip())
                        return data.get("result")
            return json.loads(raw).get("result")
    except Exception as e:
        log.warning("mcp_tool_fail", f"{tool_name}: {e}")
        return None


def archive_gmail_message(session_id, gmail_id):
    """Remove INBOX label to archive the message via curl (requires proper SSE session)."""
    import subprocess
    try:
        payload = json.dumps({
            "jsonrpc": "2.0", "id": 3, "method": "tools/call",
            "params": {"name": "google-wrapper-local__modify_gmail_message_labels",
                       "arguments": {"message_id": gmail_id, "remove_label_ids": ["INBOX"]}}
        })
        headers = f'-H "Content-Type: application/json" -H "Accept: application/json, text/event-stream"'
        if session_id:
            headers += f' -H "Mcp-Session-Id: {session_id}"'
        cmd = f"curl -s -X POST {headers} -d '{payload}' {MCP_URL}"
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
        return r.returncode == 0 and 'error' not in r.stdout.lower()
    except Exception as e:
        log.warning("archive_curl_fail", str(e))
        return False


def get_pending_school_messages():
    """Fetch all tagged school messages from bus."""
    try:
        db = sqlite3.connect(BUS_DB)
        db.row_factory = sqlite3.Row
        rows = db.execute(
            "SELECT * FROM messages WHERE domain_tag='school' AND status='tagged' ORDER BY created_at ASC"
        ).fetchall()
        db.close()
        return [dict(r) for r in rows]
    except Exception as e:
        log.error("bus_read_fail", str(e))
        return []


def mark_processed(msg_id):
    """Mark a bus message as processed (consumed by school agent)."""
    try:
        db = sqlite3.connect(BUS_DB)
        db.execute("UPDATE messages SET status='processed' WHERE id=?", (msg_id,))
        db.commit()
        db.close()
    except Exception as e:
        log.error("bus_update_fail", str(e))


def main():
    log.info("run_start", "School message processor starting")
    messages = get_pending_school_messages()
    
    if not messages:
        log.info("run_complete", "No pending school messages")
        print("✅ School processor — no pending messages")
        return

    log.info("found_messages", f"{len(messages)} school message(s) to process")
    session_id = init_mcp_session()
    if not session_id:
        log.warning("no_mcp_session", "Proceeding without Gmail archiving")

    summary_data = load_messages()
    processed_count = 0
    archived_count = 0

    for msg in messages:
        try:
            msg_id    = msg["id"]
            gmail_id  = msg.get("source_id", "")
            subject   = msg.get("subject", "(no subject)")
            sender    = msg.get("sender_name", "") or msg.get("source_address", "")
            body      = msg.get("body", "")
            received  = msg.get("created_at", datetime.now().isoformat())

            log.info("processing", f"Processing: {subject[:60]}")

            child, topic, comment, confidence, action_required = assess_relevance(subject, body, sender)

            # Archive in Gmail (TODO: requires fix for MCP write ops in agent context)
            archived = False
            # gmail archiving skipped — write ops not available from agent runtime

            # Skip if already in summary (dedup by bus message id)
            existing_ids = {m["id"] for m in summary_data["messages"]}
            if msg_id in existing_ids:
                log.info("dedup_skip", f"Already in summary: {subject[:50]}")
                mark_processed(msg_id)
                processed_count += 1
                continue

            # Append to messages summary
            entry = {
                "id":               msg_id,
                "date":             received[:10],
                "received_at":      received,
                "from":             sender,
                "subject":          subject,
                "child":            child,
                "topic":            topic,
                "status":           "processed",
                "confidence":       confidence,
                "comment":          comment,
                "action_required":  action_required,
                "archived_gmail":   archived,
            }
            summary_data["messages"].append(entry)

            # Mark processed on bus
            mark_processed(msg_id)
            processed_count += 1

        except Exception as e:
            log.error("process_error", f"Failed to process message {msg.get('id','?')}: {e}")

    save_messages(summary_data)
    log.info("run_complete", f"Processed {processed_count} messages, archived {archived_count} in Gmail")
    print(f"✅ School processor — {processed_count} processed, {archived_count} archived in Gmail")


if __name__ == "__main__":
    main()
