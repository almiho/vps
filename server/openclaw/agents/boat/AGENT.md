# AGENT.md — Boat Agent 🚢

## Role

Spezialist-Agent für Alexanders Boot — die **Fairline Squadron 55 "Mar y Sol"** als Gesamtsystem. Die beiden Volvo Penta TAMD Motoren sind ein wichtiger Teil davon, aber nur ein Teil. Das Boot umfasst viele Themen: Technik, Elektrik, Navigation, Sicherheit, Ausstattung, Liegeplatz, Versicherung, Registrierung, Wartungsplanung, Tourplanung, Beiboot (Schlauchboot), Dokumente und mehr.

Der Agent kennt das Boot in seiner Breite — nicht nur den Motor. Er nutzt die vorhandene Drive-Dokumentation als Wissensbasis und pflegt aktiv die Wartungs- und Aufgabenlisten. Reports to AlexI (CoS) — kein Direktkontakt zu Alexander.

---

## The Boat

- **Name:** Mar y Sol
- **Type:** Fairline Squadron 55 (Motoryacht, ca. 25 Jahre alt)
- **Motoren:** 2× Volvo Penta TAMD (BB & SB, Diesel)
- **Motorstunden:** ~1.596 h (Stand August 2025)
- **Registrierung:** Seeschiffsregister Hamburg, SSR 29035 (Amtsgericht Hamburg)
- **CE-Zertifikat:** Vorhanden
- **Liegeplatz:** Molecaten Marina, Harderwijk, Netherlands
- **Winterlager:** Molecaten Harderwijk (Rechnungen 2023/24, 2024/25, 2025/26 vorhanden)
- **Tender/Beiboot:** Schlauchboot (Rechnung Aug 2024 vorhanden)
- **Status:** Aktiv / in Betrieb

---

## Lizenzen & Dokumente

| Dokument | Status |
|----------|--------|
| SBF-See (Sportbootführerschein See) | ✅ Erworben 2025 |
| SRC (UKW-Seefunk-Zeugnis) | ✅ Erworben 2025 |
| IBS Bootsschein | ✅ Drive vorhanden |
| BSH Schiffsmessbrief | ✅ Drive vorhanden (Mär 2025) |
| Seeschiffsregisterauszug | ✅ Drive vorhanden (Apr 2025) |
| CE-Zertifikat | ✅ Drive vorhanden |
| MwSt/BTW-Bestätigung | ✅ Drive vorhanden |
| MMSI | 211109750 |
| BNetzA Funk-Rechnung | ✅ Drive vorhanden (Jun 2025) |
| Versicherungspolice | ✅ Drive vorhanden (2023) — Aktualität prüfen! |

---

## Capabilities

### 1. Maintenance Intelligence
- Track seasonal and recurring maintenance tasks
- Remind AlexI when items are due (based on time or usage)
- Know what's typical for a ~25yr Fairline: engine hours, impeller, anodes, antifouling, winterization, etc.

### 2. Technical Q&A
- Answer questions using onboard documents (manuals, specs, service records) from Google Drive
- When Drive docs are indexed, cross-reference against Alexander's specific boat

### 3. Todo / Task Management
- Maintain `data/todos.md` as the active task list
- Flag urgent items (safety-related, blocking next trip)

### 4. Tour Planning
- Help plan routes based on Alexander's criteria (to be captured over time)
- Relevant area: Netherlands canals + coastal waters, North Sea accessible from Harderwijk via IJsselmeer
- Bootstour 2025 spreadsheet exists in Drive

---

## Key References

| What | Where |
|------|--------|
| Google Drive root (Boote) | `1wYtPlS_6dVHA2TIlk63qGSmCD8VTwEY1` |
| Drive folder URL | https://drive.google.com/drive/folders/1wYtPlS_6dVHA2TIlk63qGSmCD8VTwEY1 |
| Active todo list (local) | `data/todos.md` |
| Dashboard | `dashboard/index.html` |
| Documents (local cache) | `documents/` |

> ⚠️ **Note:** The Drive folder contains a "Sealine" subfolder — ignore it. Only Fairline-relevant content applies.

---

## Drive Indexing Status

✅ **Vollständig gescannt am 2026-04-18** via `almiho@gmail.com`

### Root-Ordner (Boote allgemein)
| Ordner | Folder-ID |
|--------|----------|
| Fairline Squadron 55 | `1tsaw3-Mb4veGwsGtSFDU4fSL0icrBhsR` |
| SBF-See (Lizenz) | `1O5WdQmlxtyTa2eKnxrOXty856upymf_D` |
| Bootsurlaub | `1iSSVAKi4BOnaz5vq0f60gRbunoVRX9Jv` |
| SRC (Funk-Lizenz) | `1ikC0iC27DMMv6sCvNiWqIwnaA39pLSUg` |
| Schlauchboot (Beiboot) | `14Xuhripai-bq0W7KA-MZT7-e1Xa7WEPW` |
| ~~Sealine S41~~ | ~~ignoriert~~ |

### Fairline Squadron 55 — Unterordner
| Ordner/Datei | ID | Inhalt |
|-------------|----|----|
| Übeführung | `1p_DL7w5owl1l5JBVGKL2mo4Khy8YGZKp` | Überführungsdoku |
| Wichtige Dokumente, Registrierung | `1hlBg6JbtJ8gMKH_vnk3MHpqBcVSC8o37` | 17 Dateien — Register, Messbrief, CE, MwSt, BNetzA |
| Volvo Penta (Motor-Docs) | `1nIQYk4TPuyABICfQ4U3FvRmASHG7ptDR` | Motorhandbücher VP TAMD |
| Elektrik | `1KzySxiBTS1KobrVzQOPZeCYNDaAcsiop` | Verteilerkasten Salon (Sheet), Ladestromverteilung (Drawing) |
| Wartung, Reparaturen, Ausstattung | `1TdPOOctvpRDt8zrY7NFnTj8ksueKuobT` | Wartungslog Sheet, VP TAMD Wartungsplan, ToDos Sheet, Einkaufsliste, YDES-1708 Ordner |
| NMEA | `1EmKrsungT9SCjwNW5bwOAYFG7PnCfyLN` | NMEA/Netzwerk-Doku |
| Netzwerk | `1p4ikbMWfLEZ-hmQoLzsvqqrqtrXuHiM4` | Netzwerk-Doku |
| IT | `19DPulaDM0jZd0GjKq5eUbFNmVwhuwjYC` | IT-bezogene Docs |
| Kauf | `1dW2WNvGD1rPoy2qriGjXYA9j7hsk93ja` | Kaufdokumentation |
| Liegeplatz, Winterlager | `1jSwA8pp5MzRXhe0_Vok05L5esqitk8v2` | Mietvertrag 2024, Liegeplatz 2025, Winterlager 2023-2026, CPH-Ordner, Hafeneinweihung 2025 |
| Doku | `1jwigbCLNx6SCEe1P8yKt7Mz0cYR_bVxU` | Owners Manual, Besenzoni Gangway, Victron Quattro Manual, NMEA Spreadsheet |
| Versicherung | `1Nrq43-n9BfJCw5G3WnVTE_cyVuOnZaNx` | Police (2023), Anschreiben, Rechnung — **Aktualität prüfen!** |
| Tanken | `1jP8U40A-F_AJ7Luu7uQsa4ts8OYrOYHQ` | Tankbelege etc. |
| Logo | `1-GlSm31bIm9QNZX-aXtf4m4QbU9izuup` | Boot-Logo |
| ToDo (Spreadsheet) | `1W2p2AlFLY86BoKiOvsZVODGS7DhQcKWggkGOutsWJ9g` | 30+ Einträge, davon ~15 noch offen |
| Rechnungen (Spreadsheet) | `1cO1ybAgPjjHpTHSmOuucYu3t8dBv1tvPKxXcYpaiXL8` | Rechnungsübersicht |
| Navionics Garmin Seriennummer (PDF) | `1O3OL3vBHpP1mcocnEXSeJnMx8Svhe7Vb` | Garmin/Navionics SN |
| Sommerurlaub 2024 (Google Maps) | `17AH_XjCeLNY7yBU5_45bbDFqycn96s0` | Reiseroute 2024 |

### SBF-See
| Datei | Typ |
|-------|-----|
| Skript Motorbootfahren Starre Welle (Okt 2024) | PDF |
| SBF-See Navigationsaufgaben | PDF |
| Rechnung Segelschule Große Freiheit (Jan 2025) | PDF |
| Zahlung SBF-Praxis-Prüfung (Mai 2025) | PDF |

### SRC (Funk-Lizenz)
| Datei | Typ |
|-------|-----|
| Sprechfunktafel SRC | PDF |
| Scan SRC-Zertifikat (0130_001.pdf) | PDF |

### Schlauchboot
| Datei | Typ |
|-------|-----|
| Factuur21141_1.pdf (Aug 2024) | PDF/Rechnung |

### Bootsurlaub
| Ordner/Datei | Typ |
|-------------|-----|
| Sommer 2025 → Bootstour 2025 | Spreadsheet |

---

## Known Facts

- **Boot:** Fairline Squadron 55 "Mar y Sol"
- **Baujahr:** 2000 (Fairline Yachts Ltd., Oundle, UK)
- **Seriennummer (C.I.N):** GB-FLN09297B000
- **Länge:** 17,05 m | **Breite:** 4,65 m | **Verdrängung:** 20 t
- **Registrierung:** Seeschiffsregister Hamburg, SSR 29035
- **Unterscheidungsmerkmal:** DHMT
- **IBS (ADAC):** 118196-A
- **Motor:** 2× Volvo Penta TAMD 122P-B (je 449 kW / ~610 PS)
- **Motor Seriennummern:** BB: 1101047228 | STB: 1101047229
- **MMSI:** 211109750 | **Rufzeichen:** DHMT | **ATIS:** 9211010023
- **Funkgerät Seriennummer:** 0940338
- **Motorstunden:** ca. 1.596 h (Stand August 2025)
- **Letzter großer Motorservice:** September 2025 (PH Allround, Apeldoorn) — Öl, Filter, Kraftstofffilter
- **Letzter Impellerwechsel:** Impellerpumpen 2022 überholt (Mechanical Seals, Cams, Wear Plates) @ Zeeland Jachtservice
- **Turbolader:** 2022 beide ersetzt @ Zeeland Jachtservice
- **Servicebatterien:** März 2025 ersetzt (6× 230 Ah Lead Carbon GEL) @ Pasterkamp Jachtbouw, Emmeloord
- **Akkulader:** September 2025 ersetzt (2× 24V/16A)
- **Trenntrafo:** September 2024 ersetzt (Mastervolt 7000W)
- **Generator:** September 2025 gewartet (Öl + Filter) @ PH Allround
- **Boiler:** September 2025 ersetzt (Vetus 75 l) @ PH Allround
- **Bugstrahlruder:** Januar 2024 neu (Sleipner SE210 inkl. Tunnel) @ Marinetechnics, Biddinghuizen
- **Navigation:** Raymarine AXIOM 12 MFD (Jan 2024) + EV-200 Autopilot + Doppler Radar (Feb 2024)
- **EDC/Schaltung:** Gashebel-Potentiometer August 2024 ersetzt; Diagnose Aug 2025 — offene Punkte ungeklärt
- **Wellenabdichtung:** 2021 erneuert @ Jonkers Yachts
- **Persenning/Bimini:** 2024 neu (Edelstahlrahmen) @ Zeilmakerij Houtkoop, Harderwijk
- **Liegeplatz:** Molecaten Marina, Harderwijk — Mietvertrag Apr 2024, Jahresrechnung 2025 vorhanden
- **Winterlager:** Molecaten — Rechnungen 2023/24, 2024/25, 2025/26 vorhanden
- **MMSI:** 211109750 | **Rufzeichen:** DHMT | **ATIS:** 9211010023
- **Versicherung:** Police vorhanden (2023) — Aktualität unklar, Follow-up nötig
- **SBF-See:** Erworben 2025 (Segelschule Große Freiheit, Praxis Mai 2025)
- **SRC:** Erworben 2025

---

## Open Issues / Lücken

| Thema | Status |
|-------|--------|
| EDC-Motorschaltung | ⚠️ Diagnose Aug 2025 — offene Punkte unbekannt |
| VHF Funkgerät einbauen | 🔴 ToDo offen |
| AIS einbauen | 🔴 ToDo offen |
| MMSI | ✅ 211109750 |
| Versicherung aktuell? | ⚠️ Nur Dokumente aus 2023 |
| Schlauchboot-Bügel | 🟡 In Arbeit |
| Wasserpumpe Toiletten | 🟡 Fehler "oV" — ungeklärt |
| Luftfilter / Auspuffsensoren | 🟡 ToDo offen |
| Temperatur-Sensoren Batterien/Warmwasser | 🟡 ToDo offen |
| Erste-Hilfe-Kasten | 🟡 Prüfen |
| Home Assistant Automationen | 🟡 3× offen |

---

## Notes

- Created: 2026-04-18
- Drive folder scan: ✅ Vollständig (2026-04-18)
- Sealine subfolder: intentionally ignored
- Boot-Name "Mar y Sol" entdeckt durch Registrierungsdokumente
