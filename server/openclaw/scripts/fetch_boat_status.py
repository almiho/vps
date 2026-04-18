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

OUT_FILE = os.path.join(os.path.dirname(__file__), "../dashboard/data/boat_status.json")

ENTITIES = [
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

    with open(OUT_FILE, "w") as f:
        json.dump(result, f, indent=2)

    print(f"[boat] wrote {len(result['entities'])} entities → {OUT_FILE}")

if __name__ == "__main__":
    main()
