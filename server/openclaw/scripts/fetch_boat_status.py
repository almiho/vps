#!/usr/bin/env python3
"""
Fetches relevant HA entities for the boat dashboard and writes to
dashboard/data/boat_status.json — run via cron every 5 minutes.
"""
import urllib.request
import json
import os
from datetime import datetime, timezone

HA_URL   = "http://100.127.241.99:8123"
HA_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiI4ZTRlYTQzODI5YWM0NDk1YjY0MjRiMGM5NDQ5NmNmZiIsImlhdCI6MTc3NjUxNTU2NCwiZXhwIjoyMDkxODc1NTY0fQ.et05AdasM_8Zk1oAiQZlx9d66nO8ayeW1BT89Wxx524"

OUT_FILE    = os.path.join(os.path.dirname(__file__), "../dashboard/data/boat_status.json")
STATUS_JSON = os.path.join(os.path.dirname(__file__), "../agents/boat/dashboard/status.json")

ENTITIES = [
    # Anwesenheit
    "person.alex",
    "person.klemens",
    "sensor.iphone_von_klemens_ssid",
    "sensor.alex_pixel_7_pro_wifi_connection",  # fallback, may not exist
    # Position / GPS
    "sensor.gps_position",
    "sensor.geschwindigkeit_uber_grund",
    "sensor.tiefe",
    "sensor.mar_y_sol_speed",
    "device_tracker.mar_y_sol",  # enthält latitude/longitude in attributes
    # Motoren
    "sensor.port_engine_hours",
    "sensor.starboard_engine_hours",
    "sensor.port_engine_voltage",
    "sensor.starboard_engine_voltage",
    "sensor.port_engine_fuel_rate",
    "sensor.starboard_engine_fuel_rate",
    "sensor.port_engine_boost",
    "sensor.starboard_engine_boost",
    # Batterien
    "sensor.service_ladung",
    "sensor.service_spannung",
    "sensor.service_leistung",
    "sensor.bugstrahl_ladung",
    "sensor.bugstrahl_spannung",
    "sensor.heckstrahl_ladung",
    "sensor.heckstrahl_spannung",
    "sensor.starter_bb_ladung",
    "sensor.starter_bb_spannung",
    "sensor.starter_stb_ladung",
    "sensor.starter_stb_spannung",
    # Strom / Energie
    "sensor.landstrom_aktuell",
    "sensor.quattro_status",
    "sensor.quattro_ac_eingang",
    "sensor.wechselstromlasten",
    "sensor.generatorstrom_aktuell",
    "sensor.ac_input_power",
    # Tanks
    "sensor.diesel_bb",
    "sensor.diesel_stb",
    "sensor.frischwasser",
    "sensor.schwarzwasser",
    # Umgebung
    "sensor.wassertemperatur",
    "sensor.h5074_ceee_temperature",
    "sensor.h5074_ceee_humidity",
    # Sicherheit
    "binary_sensor.elektro_verteilung_rauchmelder_smoke",
    "sensor.bilge_toilettenpumpe_wassersensor_temperature",
    # Wartungsintervalle
    "input_number.maschine_bb_letzter_olwechsel",
    "input_number.maschine_stb_letzter_olwechsel",
    "input_number.intervall_olwechsel",
    "input_number.maschine_bb_letzter_impellerwechsel",
    "input_number.maschine_stb_letzter_impellerwechsel",
    "input_number.intervall_impellerwechsel",
    "input_number.maschine_bb_letzter_luftfilterwechsel",
    "input_number.maschine_stb_letzter_luftfilterwechsel",
    "input_number.intervall_luftfilter",
    "input_number.maschine_bb_letzter_getriebeolwechsel",
    "input_number.maschine_stb_letzter_getriebeolwechsel",
    "input_number.intervall_getriebeolwechsel",
]

def fetch_entity(entity_id):
    url = f"{HA_URL}/api/states/{entity_id}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {HA_TOKEN}"})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            attrs = data.get("attributes", {})
            result = {
                "state": data.get("state"),
                "unit": attrs.get("unit_of_measurement", ""),
                "friendly_name": attrs.get("friendly_name", entity_id),
            }
            if "latitude" in attrs:
                result["latitude"] = attrs["latitude"]
                result["longitude"] = attrs["longitude"]
                result["gps_accuracy"] = attrs.get("gps_accuracy")
            return result
    except Exception as e:
        return {"state": "unavailable", "unit": "", "friendly_name": entity_id, "error": str(e)}

def main():
    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
    result = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "entities": {}
    }
    for entity_id in ENTITIES:
        result["entities"][entity_id] = fetch_entity(entity_id)

    # Also embed live_summary into boat_status.json for dashboard JS
    result["live_summary"] = {
        "updated_at": None,  # filled below after live calc
        "batteries_pct": None,
        "diesel_pct": None,
        "water_pct": None,
        "blackwater_pct": None,
        "shorepower": None,
        "location": None,
    }

    with open(OUT_FILE, "w") as f:
        json.dump(result, f, indent=2)

    print(f"[boat] wrote {len(result['entities'])} entities → {OUT_FILE}")

    # --- Update live tags in agents/boat/dashboard/status.json ---
    def get_state(entity_id):
        e = result["entities"].get(entity_id, {})
        s = e.get("state")
        if s in (None, "unavailable", "unknown"):
            return None
        try:
            return float(s)
        except (ValueError, TypeError):
            return s

    # Servicebatterien %
    batt = get_state("sensor.service_ladung")
    batteries_pct = round(batt) if isinstance(batt, float) else None

    # Anwesenheit: Alex oder Klemens an Bord?
    person_alex    = result["entities"].get("person.alex", {}).get("state", "")
    person_klemens = result["entities"].get("person.klemens", {}).get("state", "")
    klemens_ssid   = result["entities"].get("sensor.iphone_von_klemens_ssid", {}).get("state", "unavailable")
    someone_aboard = (
        person_alex == "home" or
        person_klemens == "home" or
        klemens_ssid not in ("unavailable", "unknown", None, "")
    )

    # Diesel: average BB + STB — grau wenn niemand an Bord und Sensoren offline
    d_bb  = get_state("sensor.diesel_bb")
    d_stb = get_state("sensor.diesel_stb")
    # Sensors are considered offline if both are unavailable/0 simultaneously
    d_bb_raw  = result["entities"].get("sensor.diesel_bb", {}).get("state", "unavailable")
    d_stb_raw = result["entities"].get("sensor.diesel_stb", {}).get("state", "unavailable")
    diesel_sensors_offline = (
        d_bb_raw in ("unavailable", "unknown", None) and
        (d_stb_raw in ("unavailable", "unknown", None) or d_stb_raw == "0")
    )
    if not someone_aboard and diesel_sensors_offline:
        diesel_pct = "offline"  # signals dashboard to show grey, no warning
    elif isinstance(d_bb, float) and isinstance(d_stb, float):
        diesel_pct = round((d_bb + d_stb) / 2)
    elif isinstance(d_bb, float):
        diesel_pct = round(d_bb)
    elif isinstance(d_stb, float):
        diesel_pct = round(d_stb)
    else:
        diesel_pct = None

    # Frischwasser %
    w = get_state("sensor.frischwasser")
    water_pct = round(w) if isinstance(w, float) else None

    # Schwarzwasser %
    bw = get_state("sensor.schwarzwasser")
    blackwater_pct = round(bw) if isinstance(bw, float) else None

    # Landstrom: landstrom_aktuell > 0.5 A
    ls = get_state("sensor.landstrom_aktuell")
    shorepower = (ls > 0.5) if isinstance(ls, float) else None

    # Location from device_tracker attributes
    tracker = result["entities"].get("device_tracker.mar_y_sol", {})
    lat = tracker.get("latitude")
    lon = tracker.get("longitude")
    location = f"{lat:.4f}, {lon:.4f}" if lat and lon else None

    # Load + update status.json
    try:
        with open(STATUS_JSON) as f:
            status = json.load(f)
    except Exception:
        status = {"agent": "boat", "health": "ok", "alerts": [], "upcoming": []}

    status["updated_at"] = datetime.now(timezone.utc).isoformat()
    if location:
        status["location"] = location
    status["live"] = {
        "updated_at": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "batteries_pct":  batteries_pct,
        "diesel_pct":     diesel_pct,
        "water_pct":      water_pct,
        "blackwater_pct": blackwater_pct,
        "shorepower":     shorepower,
    }

    with open(STATUS_JSON, "w") as f:
        json.dump(status, f, indent=2)

    # Also write live_summary back into boat_status.json for dashboard JS
    result["live_summary"] = status["live"].copy()
    if location:
        result["live_summary"]["location"] = location
    with open(OUT_FILE, "w") as f:
        json.dump(result, f, indent=2)

    print(f"[boat] updated live tags -> {STATUS_JSON}")

if __name__ == "__main__":
    main()
