#!/usr/bin/env python3
"""
Inbox Manager — Message Router
Reads pending messages from the bus, assigns domain_tag via keyword matching.
No AI calls. Pure keyword scoring. Designed for scheduled execution every 15 min.
"""

import json
import os
import sqlite3
import sys
import uuid
from datetime import datetime
from pathlib import Path

sys.path.insert(0, "/home/node/.openclaw/workspace/scripts")
from agent_logger import AgentLogger

# ── Paths ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR    = Path(__file__).resolve().parent
AGENT_DIR     = SCRIPT_DIR.parent
WORKSPACE     = AGENT_DIR.parent.parent
BUS_DB        = WORKSPACE / "data" / "bus.db"
DECISIONS_LOG = AGENT_DIR / "data" / "decisions.jsonl"
STATUS_PATH   = AGENT_DIR / "dashboard" / "status.json"

log = AgentLogger("inbox-manager")

# ── Routing keyword table ──────────────────────────────────────────────────────
# Keys must match domain agent names exactly.
DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "tax": [
        "steuererklärung", "finanzamt", "elster", "einkommensteuer",
        "umsatzsteuer", "grundsteuer", "steuerberater", "lohnsteuer",
        "steuerbescheid", "vorauszahlung", "steueramt",
        "tax return", "tax office", "income tax", "property tax",
    ],
    "real-estate": [
        "immobilien", "miete", "vermieter", "makler", "wohnung", "mieter",
        "weg", "hausverwaltung", "mietvertrag", "nebenkosten", "betriebskosten",
        "eigentümer", "grundbuch", "kaufvertrag", "mietwohnung", "verwalter",
        "sanierung", "renovierung", "hausgeld", "wohnungseigentum",
        "real estate", "property", "landlord", "tenant", "rent", "lease",
        "property management", "house management",
    ],
    "boat": [
        "boot", "fairline", "harderwijk", "werft", "marina", "beiboot",
        "mar y sol", "motorboot", "anker", "liegeplatz", "hafen",
        "antifouling", "impeller", "steuerboard", "steuerbordfenster",
        "wolderwijd", "veluwemeer", "ijsselmeer", "ijssel",
        "boat", "motor boat", "dinghy", "harbour", "harbor", "mooring",
        "sea cock", "engine oil", "boat repair",
    ],
    "car": [
        "auto", "kfz", "fahrzeug", "werkstatt", "hauptuntersuchung",
        "kraftfahrzeug", "reifenwechsel", "autowerkstatt", "tankstelle",
        "tüv", "werkstatttermin", "fahrzeugbrief",
        "car", "vehicle", "workshop", "tyre", "tire", "repair",
        "car insurance", "roadside",
    ],
    "school": [
        "schule", "cis", "copenhagen international school", "fernschule",
        "lehrer", "unterricht", "hausaufgaben", "zeugnis", "stundenplan",
        "schulferien", "klassenfahrt", "elternabend", "prüfung",
        "school", "teacher", "homework", "grade", "semester", "exam",
        "class schedule", "school report", "parent evening",
    ],
    "health": [
        "arzt", "apotheke", "krankenkasse", "rezept", "klinik", "krankenhaus",
        "zahnarzt", "impfung", "befund", "überweisung", "behandlung",
        "diagnose", "medikament", "therapist",
        "doctor", "pharmacy", "health insurance", "hospital", "medication",
        "prescription", "dentist", "vaccination", "appointment", "patient",
    ],
    "travel": [
        "reise", "hotel", "flug", "buchung", "urlaub", "reisebüro",
        "airbnb", "booking.com", "expedia", "tripadvisor",
        "travel", "flight", "booking", "reservation", "ticket", "airline",
        "boarding", "check-in", "departure", "arrival", "passport",
        "airport", "flughafen", "luggage",
    ],
    "life-in-denmark": [
        "behörde", "skat", "cpr-nummer", "folkeregister", "kommune",
        "borgerservice", "rådhuset", "styrelsen", "statsforvaltning",
        "udlændingestyrelsen", "opholdstilladelse",
        "danish", "denmark", "copenhagen", "visa", "residence permit",
        "danish authorities", "borger.dk",
    ],
    "insurance": [
        "versicherung", "versicherungspolice", "schadensfall", "prämie",
        "haftpflicht", "hausrat", "lebensversicherung", "berufsunfähigkeit",
        "unfallversicherung", "schadensmeldung", "allianz", "axa", "zurich",
        "hanse merkur", "debeka", "ergo", "gothaer",
        "insurance", "policy", "claim", "premium", "insurer",
    ],
    "finance": [
        "bank", "rechnung", "zahlung", "überweisung", "iban", "konto",
        "lastschrift", "kontoauszug", "bankverbindung", "abbuchung",
        "mahnschreiben", "mahnung", "forderung", "inkasso", "gutschrift",
        "dkb", "sparkasse", "commerzbank", "ing", "n26", "volksbank",
        "invoice", "payment", "direct debit", "wire transfer", "bank statement",
        "paypal", "klarna", "sepa", "bank transfer", "overdue", "reminder",
        "debit", "credit note",
    ],
}

# Domains where a higher-priority domain wins on overlap
PRIORITY_OVERRIDES: list[tuple[str, str]] = [
    # (winner, loser) — winner takes over if both have score > 0
    ("tax",     "finance"),    # Steuersachen sind nicht einfach "Finance"
    ("finance", "insurance"),  # Versicherungsrechnung → Finance beats Insurance
]


def build_match_text(row: dict) -> str:
    """Build the text corpus to match keywords against."""
    parts = [
        row.get("subject") or "",
        row.get("sender_name") or "",
        row.get("source_address") or "",
        (row.get("body") or "")[:200],
    ]
    return " ".join(parts).lower()


def score_domains(text: str) -> dict[str, int]:
    """Return per-domain keyword hit counts."""
    scores: dict[str, int] = {}
    for domain, keywords in DOMAIN_KEYWORDS.items():
        count = sum(1 for kw in keywords if kw in text)
        if count > 0:
            scores[domain] = count
    return scores


def resolve_domain(scores: dict[str, int]) -> tuple[str | None, str]:
    """
    Resolve the winning domain from scores.
    Returns (domain_tag, confidence) where confidence is 'high'|'low'|'none'.
    Returns (None, 'none') if needs_review.
    """
    if not scores:
        return None, "none"

    # Apply priority overrides
    for winner, loser in PRIORITY_OVERRIDES:
        if winner in scores and loser in scores:
            del scores[loser]

    sorted_domains = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    if len(sorted_domains) == 1:
        return sorted_domains[0][0], "high"

    top_domain, top_score = sorted_domains[0]
    second_domain, second_score = sorted_domains[1]

    if top_score > second_score:
        confidence = "high" if top_score >= 2 else "low"
        return top_domain, confidence

    # Tie at top — ambiguous
    return None, "none"


def ensure_bus_schema(conn: sqlite3.Connection):
    """Create messages table if it doesn't exist yet (matches real bus schema)."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id              TEXT PRIMARY KEY,
            created_at      TEXT NOT NULL,
            updated_at      TEXT NOT NULL,
            source_channel  TEXT,
            source_id       TEXT,
            source_address  TEXT,
            sender_name     TEXT,
            subject         TEXT,
            body            TEXT,
            attachments     TEXT DEFAULT '[]',
            forward_count   INTEGER DEFAULT 0,
            domain_tag      TEXT DEFAULT NULL,
            status          TEXT DEFAULT 'pending',
            processed_by    TEXT DEFAULT '[]',
            reply_context   TEXT DEFAULT '{}',
            processed_at    TEXT
        )
    """)
    conn.commit()


def fetch_pending(conn: sqlite3.Connection) -> list[dict]:
    conn.row_factory = sqlite3.Row
    cur = conn.execute(
        "SELECT id, source_channel, source_id, source_address, sender_name, "
        "subject, body, reply_context FROM messages WHERE status = 'pending'"
    )
    return [dict(r) for r in cur.fetchall()]


def tag_message(conn: sqlite3.Connection, msg_id: int, domain_tag: str, new_status: str):
    conn.execute(
        "UPDATE messages SET domain_tag=?, status=?, updated_at=? WHERE id=?",
        (domain_tag, new_status, datetime.now().isoformat(timespec="seconds"), msg_id),
    )
    conn.commit()


def write_review_message(conn: sqlite3.Connection, original: dict, routing_options: list[str], reason: str):
    """Write a needs_review notification to CoS on the bus."""
    review_source_id = f"review_{original['id']}"

    # Check idempotency — don't double-write
    existing = conn.execute(
        "SELECT id FROM messages WHERE source_id = ?", (review_source_id,)
    ).fetchone()
    if existing:
        return

    body_payload = json.dumps({
        "original_id":      original["id"],
        "original_source_id": original.get("source_id"),
        "original_subject": original.get("subject"),
        "original_sender":  original.get("source_address"),
        "routing_options":  routing_options,
        "reason":           reason,
    })

    now = datetime.now().isoformat(timespec="seconds")
    conn.execute(
        """INSERT INTO messages
           (id, created_at, updated_at, source_channel, source_id, domain_tag, subject, body, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            str(uuid.uuid4()),
            now,
            now,
            "internal",
            review_source_id,
            "cos",
            f"Inbox Review: {original.get('subject', '(no subject)')}",
            body_payload,
            "pending",
        ),
    )
    conn.commit()


def append_decision(decision: dict):
    DECISIONS_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(DECISIONS_LOG, "a") as f:
        f.write(json.dumps(decision) + "\n")


def load_recent_decisions(n: int = 20) -> list[dict]:
    if not DECISIONS_LOG.exists():
        return []
    lines = DECISIONS_LOG.read_text().strip().splitlines()
    entries = []
    for line in lines:
        try:
            entries.append(json.loads(line))
        except Exception:
            pass
    return entries[-n:]


def load_needs_review_queue(conn: sqlite3.Connection) -> list[dict]:
    """Return pending CoS review messages from the bus."""
    conn.row_factory = sqlite3.Row
    cur = conn.execute(
        "SELECT id, source_id, subject, body, created_at FROM messages "
        "WHERE domain_tag='cos' AND source_channel='internal' AND status='pending' "
        "ORDER BY created_at DESC LIMIT 20"
    )
    rows = []
    for r in cur.fetchall():
        rows.append(dict(r))
    return rows


def write_status(tagged: int, needs_review: int, skipped: int, error: str | None, conn: sqlite3.Connection):
    try:
        total = conn.execute("SELECT COUNT(*) FROM messages WHERE status='tagged'").fetchone()[0]
        review_queue = load_needs_review_queue(conn)
    except Exception:
        total = 0
        review_queue = []

    health = "ok" if not error else "error"
    if needs_review > 0 and not error:
        health = "warning"

    recent_decisions = load_recent_decisions(20)

    summary = (
        f"Last run: {tagged} tagged, {needs_review} needs review, {skipped} skipped."
        if not error
        else f"Error: {error}"
    )

    alerts = []
    if review_queue:
        alerts.append({
            "priority": 2,
            "title": f"{len(review_queue)} message(s) need routing review",
            "body": "Cannot determine domain automatically. CoS must classify.",
            "due_at": None,
            "action_required": True,
        })
    if error:
        alerts.append({
            "priority": 1,
            "title": "Router error",
            "body": error,
            "due_at": None,
            "action_required": True,
        })

    status = {
        "agent":      "inbox-manager",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "health":     health,
        "summary":    summary,
        "alerts":     alerts,
        "upcoming":   [],
        "stats": {
            "total_tagged_alltime": total,
            "last_run_tagged":      tagged,
            "last_run_needs_review": needs_review,
            "last_run_skipped":     skipped,
            "last_run_at":          datetime.now().isoformat(timespec="seconds"),
        },
        "recent_decisions": recent_decisions,
        "needs_review_queue": review_queue,
    }

    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(STATUS_PATH, "w") as f:
        json.dump(status, f, indent=2)


def main():
    log.info("run_start", "Inbox Manager routing run starting")

    if not BUS_DB.exists():
        log.info("no_bus", "Bus DB not found — nothing to route yet")
        write_status(0, 0, 0, None, sqlite3.connect(":memory:"))
        return

    conn = sqlite3.connect(str(BUS_DB))
    try:
        ensure_bus_schema(conn)
        pending = fetch_pending(conn)

        if not pending:
            log.info("no_pending", f"No pending messages")
            write_status(0, 0, 0, None, conn)
            print("0 pending messages — nothing to route")
            return

        log.info("pending_found", f"Found {len(pending)} pending messages")

        tagged = 0
        needs_review = 0
        skipped = 0

        for msg in pending:
            msg_id  = msg["id"]
            subject = msg.get("subject", "") or ""
            text    = build_match_text(msg)
            scores  = score_domains(text)

            domain, confidence = resolve_domain(dict(scores))  # pass copy — resolve mutates

            ts = datetime.now().isoformat(timespec="seconds")

            if domain:
                tag_message(conn, msg_id, domain, "tagged")
                decision = {
                    "timestamp":   ts,
                    "message_id":  msg_id,
                    "source_id":   msg.get("source_id"),
                    "subject":     subject[:80],
                    "domain":      domain,
                    "confidence":  confidence,
                    "scores":      scores,
                    "action":      "tagged",
                }
                append_decision(decision)
                log.info("tagged", f"msg={msg_id} → {domain} ({confidence})", detail=subject[:60])
                tagged += 1
            else:
                # needs_review — tag + write CoS message
                tag_message(conn, msg_id, "cos", "needs_review")
                routing_options = sorted(scores.keys()) if scores else []
                reason = "equal top scores" if scores else "no keyword match"
                write_review_message(conn, msg, routing_options, reason)

                decision = {
                    "timestamp":   ts,
                    "message_id":  msg_id,
                    "source_id":   msg.get("source_id"),
                    "subject":     subject[:80],
                    "domain":      None,
                    "confidence":  "none",
                    "scores":      scores,
                    "action":      "needs_review",
                    "reason":      reason,
                }
                append_decision(decision)
                log.warning("needs_review", f"msg={msg_id} — {reason}", detail=subject[:60])
                needs_review += 1

        log.info("run_complete", f"Done: {tagged} tagged, {needs_review} needs_review, {skipped} skipped")
        write_status(tagged, needs_review, skipped, None, conn)
        print(f"{tagged} tagged, {needs_review} needs_review, {skipped} skipped")

    except Exception as e:
        log.error("run_error", str(e))
        try:
            write_status(0, 0, 0, str(e), conn)
        except Exception:
            pass
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
