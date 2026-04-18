#!/usr/bin/env python3
"""
Caly — Calendar Agent refresh script

Fetches this week's events from Google Calendar via the local MCP server,
writes structured data to agents/calendar/data/events.json, and updates
agents/calendar/dashboard/status.json with a smart "upcoming" section.

Smart upcoming logic:
  - After 12:00 local time → show tomorrow
  - Before 12:00 local time → show today
  Content: who picks up kids, pickup time, key meetings (BoD/CLT/BO/board)

Usage: python3 refresh.py
"""

import sys, json, os, re, urllib.request
from datetime import datetime, timedelta, timezone, date

sys.path.insert(0, "/home/node/.openclaw/workspace/scripts")
from agent_logger import AgentLogger

WORKSPACE   = "/home/node/.openclaw/workspace"
AGENT_DIR   = f"{WORKSPACE}/agents/calendar"
MCP_BASE    = "http://127.0.0.1:8000/mcp"
USER_EMAIL  = "almiho@gmail.com"

# Calendars to fetch for the weekly grid
CALENDARS = [
    ("primary",                                                                          "Alex",          "#4285f4"),
    ("osdq55i3o0k7lbrvrtp2fje45k@group.calendar.google.com",                            "SKW11a",        "#33b679"),
    ("3rkjkal9lst6pberqfv1726a98@group.calendar.google.com",                             "Lukas & Jonas", "#f6bf26"),
    ("c8758d661f01b7ebff1fc5da0f7a69ca7f9e49b6c489de8f9ec08bf64f5cdfe3@group.calendar.google.com", "Ferien", "#e67c73"),
    ("tanja.berthues@gmail.com",                                                         "Tanja",         "#a142f4"),
    ("gtohs295saeu45e8qfo3rcauestltdgl@import.calendar.google.com",                      "TripIt",        "#039be5"),
]

# Keywords that flag a meeting as "important" for the upcoming section
KEY_MEETING_KEYWORDS = [
    "bod", "board of directors", "board meeting",
    "clt", "company leadership", "leadership team",
    "globalconnect", "gc all", "exec",
    " bo ", "business operations",
    "quarterly", "all hands", "allhands",
]

TANJA_EMAILS = {"tanja.berthues@gmail.com", "tb@deepeye-medical.com"}
ALEX_EMAILS  = {"almiho@gmail.com", "alehof@globalconnect.dk"}

log = AgentLogger("calendar")


# ---------------------------------------------------------------------------
# MCP helpers
# ---------------------------------------------------------------------------

def mcp_session():
    sid, _ = _mcp_post({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
        "protocolVersion": "2024-11-05", "capabilities": {},
        "clientInfo": {"name": "caly", "version": "1.0"}
    }})
    _mcp_post({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}, sid)
    return sid


def _mcp_post(payload, sid=None):
    data = json.dumps(payload).encode()
    hdrs = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
    if sid:
        hdrs["Mcp-Session-Id"] = sid
    req = urllib.request.Request(MCP_BASE, data=data, headers=hdrs, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.headers.get("Mcp-Session-Id"), r.read().decode()


def call_tool(sid, name, arguments):
    _, body = _mcp_post({
        "jsonrpc": "2.0", "id": 2, "method": "tools/call",
        "params": {"name": name, "arguments": arguments}
    }, sid)
    for line in body.splitlines():
        if line.startswith("data: "):
            d = json.loads(line[6:])
            content = d.get("result", {}).get("content", [])
            if content:
                return content[0].get("text", "")
    return ""


# ---------------------------------------------------------------------------
# Event text parser
# ---------------------------------------------------------------------------

_EVENT_HEADER = re.compile(
    r'^- "(.+?)"\s*\(Starts:\s*([\d\-T:+Z]+),\s*Ends:\s*([\d\-T:+Z]+)\)',
    re.MULTILINE
)
_ID_LINK = re.compile(r'ID:\s*(\S+?)(?:\s*\|)?\s*(?:Link:\s*(\S+))?$', re.MULTILINE)
_ORGANIZER = re.compile(r'([\w.@+-]+):\s*(?:accepted|needsAction|declined)\s*\(organizer\)', re.IGNORECASE)


def parse_events_text(text, calendar_id, calendar_name, calendar_color):
    events = []
    headers = list(_EVENT_HEADER.finditer(text))
    for i, m in enumerate(headers):
        title = m.group(1)
        start = m.group(2)
        end   = m.group(3)
        block_start = m.start()
        block_end   = headers[i + 1].start() if i + 1 < len(headers) else len(text)
        block = text[block_start:block_end]

        id_match  = _ID_LINK.search(block)
        org_match = _ORGANIZER.search(block)
        event_id  = id_match.group(1) if id_match else None
        link      = id_match.group(2) if id_match else None
        organizer = org_match.group(1).lower() if org_match else ""

        events.append({
            "id":             event_id,
            "calendar_id":    calendar_id,
            "calendar_name":  calendar_name,
            "calendar_color": calendar_color,
            "title":          title,
            "start":          start,
            "end":            end,
            "all_day":        "T" not in start,
            "link":           link,
            "organizer":      organizer,
        })
    return events


# ---------------------------------------------------------------------------
# Smart upcoming logic
# ---------------------------------------------------------------------------

def pickup_owner(event):
    """Return 'Tanja', 'Alex', or None based on event title + organizer."""
    title = event.get("title", "")
    organizer = event.get("organizer", "")

    # "TB - Kids abholen" pattern → Tanja
    if re.search(r'\bTB\b', title, re.IGNORECASE):
        return "Tanja"
    # Organizer is Tanja → Tanja
    if organizer in TANJA_EMAILS:
        return "Tanja"
    # Organizer is Alex → Alex
    if organizer in ALEX_EMAILS:
        return "Alex"
    return None


def is_key_meeting(event):
    """Return True if the event title suggests a high-importance meeting."""
    title = event.get("title", "").lower()
    return any(kw in title for kw in KEY_MEETING_KEYWORDS)


def is_pickup(event):
    return "abholen" in event.get("title", "").lower()


def fmt_time(iso):
    """Extract HH:MM from ISO timestamp."""
    if "T" in iso:
        return iso[11:16]
    return ""


def build_upcoming(all_events):
    """
    Build upcoming items for status.json.
    Target day: tomorrow if now >= 12:00, today otherwise.
    """
    now = datetime.now()
    if now.hour >= 12:
        target = (now.date() + timedelta(days=1))
        day_label = "tomorrow"
    else:
        target = now.date()
        day_label = "today"

    target_str = target.isoformat()
    day_events = [e for e in all_events if e["start"][:10] == target_str]
    day_events.sort(key=lambda e: e["start"])

    upcoming = []

    # --- Pickup ---
    pickup_events = [e for e in day_events if is_pickup(e)]
    if pickup_events:
        pe = pickup_events[0]
        owner = pickup_owner(pe)
        t = fmt_time(pe["start"])
        if owner:
            upcoming.append({
                "priority": 1,
                "title": f"🚌 Kids pickup — {owner} at {t} ({day_label})",
                "due_at": pe["start"],
            })
        else:
            upcoming.append({
                "priority": 1,
                "title": f"🚌 Kids pickup at {t} ({day_label}) — owner unclear",
                "due_at": pe["start"],
            })
    else:
        upcoming.append({
            "priority": 3,
            "title": f"🚌 No kids pickup event found for {day_label}",
            "due_at": None,
        })

    # --- Key meetings ---
    key = [e for e in day_events if is_key_meeting(e) and not is_pickup(e)]
    for e in key:
        t = fmt_time(e["start"])
        upcoming.append({
            "priority": 1,
            "title": f"📌 {e['title']} at {t} ({day_label})",
            "due_at": e["start"],
        })

    # --- GlobalConnect not connected ---
    upcoming.append({
        "priority": 3,
        "title": "⚠️ GlobalConnect calendar not connected — alehof@globalconnect.dk needs OAuth",
        "due_at": None,
    })

    if not key and not pickup_events:
        upcoming.append({
            "priority": 4,
            "title": f"📅 No key events found for {day_label} ({target_str})",
            "due_at": None,
        })

    return upcoming, day_label, target_str


# ---------------------------------------------------------------------------
# Week helpers
# ---------------------------------------------------------------------------

def current_week_bounds():
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    return monday, sunday


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    log.info("refresh_start", "Caly refresh starting")
    monday, sunday = current_week_bounds()
    time_min = f"{monday.isoformat()}T00:00:00Z"
    time_max = f"{(sunday + timedelta(days=1)).isoformat()}T00:00:00Z"

    log.info("week_range", f"Fetching {monday} → {sunday}")

    try:
        sid = mcp_session()
    except Exception as e:
        log.error("mcp_connect_failed", str(e))
        _write_status("error", f"Cannot reach Calendar MCP: {e}", mcp_ok=False, upcoming=[])
        sys.exit(1)

    all_events = []
    fetch_errors = []

    for cal_id, cal_name, cal_color in CALENDARS:
        try:
            text = call_tool(sid, "get_events", {
                "user_google_email": USER_EMAIL,
                "calendar_id":       cal_id,
                "time_min":          time_min,
                "time_max":          time_max,
                "max_results":       50,
                "detailed":          True,
            })
            if "error" in text.lower() and "retrieved" not in text.lower():
                log.warning("calendar_fetch_error", f"{cal_name}: {text[:120]}")
                fetch_errors.append(cal_name)
            else:
                events = parse_events_text(text, cal_id, cal_name, cal_color)
                all_events.extend(events)
                log.info("calendar_fetched", f"{cal_name}: {len(events)} events")
        except Exception as e:
            log.error("calendar_fetch_exception", f"{cal_name}: {e}")
            fetch_errors.append(cal_name)

    # Sort by start time
    all_events.sort(key=lambda e: e["start"])

    # Write events.json
    os.makedirs(f"{AGENT_DIR}/data", exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "week_start":   monday.isoformat(),
        "week_end":     sunday.isoformat(),
        "globalconnect_connected": False,
        "calendars": [
            {"id": cid, "name": cname, "color": ccolor}
            for cid, cname, ccolor in CALENDARS
        ],
        "events": all_events,
    }
    with open(f"{AGENT_DIR}/data/events.json", "w") as f:
        json.dump(payload, f, indent=2)

    # Build smart upcoming
    upcoming, day_label, target_str = build_upcoming(all_events)

    # Build status
    n = len(all_events)
    today_str = date.today().isoformat()
    n_today = len([e for e in all_events if e["start"][:10] == today_str])

    if fetch_errors:
        health  = "warning"
        summary = f"{n} events this week ({n_today} today) — fetch errors: {', '.join(fetch_errors)}"
    else:
        health  = "ok"
        summary = f"{n} events this week, {n_today} today · showing {day_label} in Upcoming"

    _write_status(health, summary, mcp_ok=True, upcoming=upcoming)
    log.info("refresh_done", summary)
    print(f"✅ Caly refresh complete — {summary}")


def _write_status(health, summary, mcp_ok, upcoming):
    status = {
        "agent":      "calendar",
        "updated_at": datetime.now().isoformat(),
        "health":     health,
        "summary":    summary,
        "alerts":     [],
        "upcoming":   upcoming,
        "checks": {
            "google_calendar_mcp": {
                "ok":    mcp_ok,
                "detail": "Connected" if mcp_ok else "Unreachable"
            },
            "globalconnect_calendar": {
                "ok":    False,
                "detail": "Not connected — alehof@globalconnect.dk needs OAuth authorization"
            }
        }
    }
    path = f"{AGENT_DIR}/dashboard/status.json"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(status, f, indent=2)


if __name__ == "__main__":
    main()
