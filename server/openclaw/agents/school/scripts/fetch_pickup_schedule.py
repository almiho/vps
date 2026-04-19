#!/usr/bin/env python3
"""
fetch_pickup_schedule.py — School Agent
Reads 'Kids abholen' events from Google Calendar for the next 7 days
and writes pickup_schedule to agents/school/data/responsibilities.json

Naming convention:
  "Kids abholen"       → Alexander
  "TB - Kids abholen"  → Tanja

Run daily via scheduler (e.g. 07:00 on weekdays).
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, "/home/node/.openclaw/workspace/scripts")
from agent_logger import AgentLogger

try:
    from googleapiclient.discovery import build
    from google.oauth2.credentials import Credentials
except ImportError:
    print("ERROR: google-api-python-client not installed")
    sys.exit(1)

log = AgentLogger("school")

WORKSPACE     = "/home/node/.openclaw/workspace"
RESP_PATH     = f"{WORKSPACE}/agents/school/data/responsibilities.json"
TOKEN_PATH    = f"{WORKSPACE}/config/google_token.json"
CALENDAR_ID   = "almiho@gmail.com"
PICKUP_KEYWORD = "kids abholen"
DROPOFF_TIME  = "08:00"

def get_calendar_service():
    if not os.path.exists(TOKEN_PATH):
        log.warning("Google token not found, skipping pickup fetch")
        return None
    creds = Credentials.from_authorized_user_file(TOKEN_PATH)
    return build("calendar", "v3", credentials=creds, cache_discovery=False)

def isodate(dt):
    return dt.strftime("%Y-%m-%d")

def fetch_pickup_events(service, days=8):
    now = datetime.now(timezone.utc)
    time_min = now.isoformat()
    time_max = (now + timedelta(days=days)).isoformat()

    result = service.events().list(
        calendarId=CALENDAR_ID,
        timeMin=time_min,
        timeMax=time_max,
        maxResults=50,
        singleEvents=True,
        orderBy="startTime"
    ).execute()

    return result.get("items", [])

def parse_person(title):
    t = title.strip().lower()
    if t.startswith("tb"):
        return "Tanja"
    return "Alexander"

def parse_time(event):
    start = event.get("start", {})
    dt_str = start.get("dateTime")
    if not dt_str:
        return None
    dt = datetime.fromisoformat(dt_str)
    return dt.strftime("%H:%M")

def main():
    service = get_calendar_service()
    if not service:
        return

    events = fetch_pickup_events(service)

    pickup_schedule = {}
    for ev in events:
        title = ev.get("summary", "")
        if PICKUP_KEYWORD not in title.lower():
            continue
        date_key = ev["start"].get("date") or ev["start"].get("dateTime", "")[:10]
        t = parse_time(ev)
        person = parse_person(title)
        pickup_schedule[date_key] = {"person": person, "time": t or "—"}
        log.info(f"Pickup: {date_key} → {person} at {t}")

    # Load existing, update, write back
    data = {}
    if os.path.exists(RESP_PATH):
        with open(RESP_PATH) as f:
            data = json.load(f)

    data["updated_at"] = isodate(datetime.now())
    data["dropoff"] = {"person": data.get("dropoff", {}).get("person", "Alexander"), "time": DROPOFF_TIME}
    data["pickup_schedule"] = pickup_schedule
    data["note"] = "Auto-updated from Google Calendar. TB- prefix = Tanja, no prefix = Alexander."

    with open(RESP_PATH, "w") as f:
        json.dump(data, f, indent=2)

    log.info(f"Pickup schedule updated: {len(pickup_schedule)} days")
    print(f"✅ Pickup schedule updated: {len(pickup_schedule)} entries")

if __name__ == "__main__":
    main()
