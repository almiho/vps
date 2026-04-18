# AGENT.md — Inbox Manager 📬

## Role

**Pure router.** Reads `pending` messages from the bus and decides: which domain agent is responsible. Nothing else. No priority scoring, no action suggestions, no analysis. Those are jobs for the domain agents.

Reports to AlexI (CoS). Never contacts Alexander directly.

---

## What It Does

1. Query `data/bus.db` for `status = 'pending'`
2. For each message: run keyword matching on subject + sender_name + source_address + body[:200]
3. Clear match → set `domain_tag`, update `status = 'tagged'`
4. No match / ambiguous → set `status = 'needs_review'` + write a CoS message on the bus
5. Log every decision to `data/decisions.jsonl`

**Idempotent.** Messages with `status != 'pending'` are always skipped.

---

## Routing Table

| Domain Tag | Routes When... |
|------------|----------------|
| `real-estate` | Immobilien, Miete, Mietvertrag, Hausverwaltung, WEG, Vermieter, Makler, property, tenant, rent |
| `finance` | Bank, Rechnung, Zahlung, IBAN, Lastschrift, Kontoauszug, invoice, payment, DKB, Sparkasse, PayPal, Inkasso |
| `insurance` | Versicherung, Police, Schadensfall, Prämie, insurance, claim — **only if finance doesn't also match** |
| `boat` | Boot, Fairline, Harderwijk, Werft, Marina, Beiboot, Mar y Sol, Motorboot, hafen, IJsselmeer |
| `car` | Auto, KFZ, Werkstatt, TÜV, Fahrzeug, car, vehicle, Reparatur, Hauptuntersuchung |
| `school` | Schule, CIS, Copenhagen International School, Fernschule, Lehrer, teacher, Hausaufgaben, Zeugnis |
| `health` | Arzt, Apotheke, Krankenkasse, Rezept, doctor, pharmacy, hospital, medication |
| `travel` | Reise, Hotel, Flug, Buchung, Airbnb, flight, booking, airline, airport |
| `life-in-denmark` | Behörde, Skat, CPR, Folkeregister, Kommune, Borgerservice, Danish authorities |
| `tax` | Steuererklärung, Finanzamt, ELSTER, Einkommensteuer, tax return, tax office |
| `cos` | Fallback for unclear / multi-domain / no match → `needs_review` path |

### Conflict Rules

- `finance` beats `insurance` when both match (finance is the broader catch)
- `tax` beats `finance` when Finanzamt/ELSTER/Steuererklärung keywords match
- Tie (two domains equal non-zero score) → `needs_review`
- Zero matches → `needs_review`

---

## Bus Schema

```sql
CREATE TABLE IF NOT EXISTS messages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source_channel  TEXT,
    source_id       TEXT UNIQUE,
    source_address  TEXT,
    sender_name     TEXT,
    subject         TEXT,
    body            TEXT,
    reply_context   TEXT,
    domain_tag      TEXT DEFAULT NULL,
    status          TEXT DEFAULT 'pending',
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP
)
```

### Status Values

| Status | Meaning |
|--------|---------|
| `pending` | New, unprocessed |
| `tagged` | Domain assigned by Inbox Manager |
| `needs_review` | No clear domain — CoS review message written |
| `processing` | A domain agent is working on it |
| `done` | Handled |

### needs_review CoS Message Format

```json
{
  "source_channel": "internal",
  "source_id": "review_{original_message_id}",
  "domain_tag": "cos",
  "subject": "Inbox Review: {original subject}",
  "body": {
    "original_id": 123,
    "original_source_id": "...",
    "original_subject": "...",
    "original_sender": "...",
    "routing_options": ["real-estate", "finance"],
    "reason": "equal keyword score"
  },
  "status": "pending"
}
```

---

## Files

| File | Purpose |
|------|---------|
| `scripts/route_messages.py` | Main routing script (scheduled) |
| `data/decisions.jsonl` | Append-only decision log |
| `dashboard/status.json` | Status + recent stats for dashboard |

---

## Scheduling

- Runs every **15 minutes** via `scripts/scheduler.py` (key: `inbox_manager`)
- No `--run` guard needed — designed to be safe to run on schedule
- Exits cleanly with count if no pending messages

---

## Notes

- **No AI in this script** — pure keyword matching. Cheap, fast, deterministic.
- **No Telegram** — unclear messages → CoS on bus, CoS decides whether to surface to Alexander
- Created: 2026-04-18
