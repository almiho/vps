#!/usr/bin/env python3
"""
Inbox Manager — Message Router
Reads pending messages from the bus, assigns domain_tag via keyword matching.
Confidence-based routing: score ≥ 85 AND agent in ACTIVE_AGENTS → tagged.
Otherwise → needs_review (CoS bus message + pending_reviews.json updated).
No AI calls. Pure keyword scoring. Designed for scheduled execution every 15 min.
"""

import json
import os
import sqlite3
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

sys.path.insert(0, "/home/node/.openclaw/workspace/scripts")
from agent_logger import AgentLogger

# ── Paths ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR          = Path(__file__).resolve().parent
AGENT_DIR           = SCRIPT_DIR.parent
WORKSPACE           = AGENT_DIR.parent.parent
BUS_DB              = WORKSPACE / "data" / "bus.db"
DECISIONS_LOG       = AGENT_DIR / "data" / "decisions.jsonl"
STATUS_PATH         = AGENT_DIR / "dashboard" / "status.json"
PENDING_REVIEWS_PATH = AGENT_DIR / "data" / "pending_reviews.json"
DASHBOARD_PENDING   = WORKSPACE / "dashboard" / "data" / "inbox_pending.json"

log = AgentLogger("inbox-manager")

# ── Active agents (only these can receive tagged messages) ─────────────────────
ACTIVE_AGENTS = {
    'real-estate', 'finance', 'insurance', 'boat', 'car',
    'school', 'health', 'travel', 'life-in-denmark', 'tax', 'cos'
}

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

# ── High-confidence (unique) keywords per domain ──────────────────────────────
# These are strongly domain-specific — presence of any → base score 95+
UNIQUE_KEYWORDS: dict[str, list[str]] = {
    "tax":            ["steuerbescheid", "elster", "vorauszahlung", "steuerberater", "finanzamt"],
    "real-estate":    ["hausverwaltung", "wohnungseigentum", "hausgeld", "mietvertrag", "grundbuch"],
    "boat":           ["fairline", "harderwijk", "antifouling", "wolderwijd", "veluwemeer", "mar y sol"],
    "car":            ["tüv", "fahrzeugbrief", "hauptuntersuchung"],
    "school":         ["cis", "copenhagen international school", "klassenfahrt", "stundenplan", "elternabend"],
    "health":         ["krankenkasse", "impfung", "befund", "rezept"],
    "travel":         ["boarding", "expedia", "tripadvisor", "flughafen", "check-in"],
    "life-in-denmark":["cpr-nummer", "folkeregister", "borgerservice", "udlændingestyrelsen", "opholdstilladelse", "borger.dk"],
    "insurance":      ["versicherungspolice", "schadensfall", "schadensmeldung", "berufsunfähigkeit"],
    "finance":        ["kontoauszug", "lastschrift", "inkasso", "sepa", "mahnschreiben", "mahnung"],
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


# Load learned sender mappings (from user confirmations)
_FEEDBACK_PATH = AGENT_DIR / "data" / "routing_feedback.json"
def _load_learned_senders() -> dict:
    try:
        return json.loads(_FEEDBACK_PATH.read_text()).get("learned_senders", {})
    except Exception:
        return {}
LEARNED_SENDERS: dict = _load_learned_senders()

def compute_confidence_score(domain: str, hit_count: int, text: str) -> int:
    """
    Compute a 0-100 confidence score for a domain match.
    - Unique/definitive keyword present → 95+
    - Multiple keyword hits (≥3) → 90
    - Two keyword hits → 80
    - Single keyword hit → 65
    - No hits → 0
    """
    # Check unique/highly-specific keywords
    for kw in UNIQUE_KEYWORDS.get(domain, []):
        if kw in text:
            return min(95 + hit_count - 1, 99)

    if hit_count >= 3:
        return 90
    elif hit_count == 2:
        return 80
    elif hit_count == 1:
        return 65
    return 0


def resolve_domain(scores: dict[str, int], text: str) -> tuple[str | None, int, str]:
    """
    Resolve the winning domain from scores.
    Returns (domain_tag, confidence_score, reason).
    domain_tag is None when result is ambiguous or empty.
    """
    if not scores:
        return None, 0, "no keyword match"

    # Apply priority overrides (work on a copy — don't mutate caller's dict)
    scores = dict(scores)
    for winner, loser in PRIORITY_OVERRIDES:
        if winner in scores and loser in scores:
            del scores[loser]

    sorted_domains = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    if len(sorted_domains) == 1:
        domain, hit_count = sorted_domains[0]
        score = compute_confidence_score(domain, hit_count, text)
        return domain, score, f"sole match: {hit_count} keyword(s)"

    top_domain, top_hits = sorted_domains[0]
    second_domain, second_hits = sorted_domains[1]

    if top_hits > second_hits:
        score = compute_confidence_score(top_domain, top_hits, text)
        reason = f"top match: {top_hits} vs {second_hits} keyword(s)"
        return top_domain, score, reason

    # Tie at top — ambiguous
    return None, 30, f"ambiguous: tie between {top_domain} and {second_domain}"


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
        "subject, body, reply_context FROM messages WHERE status = 'pending' "
        "AND source_channel != 'internal'"  # Skip internal CoS messages to avoid loops
    )
    return [dict(r) for r in cur.fetchall()]


def tag_message(conn: sqlite3.Connection, msg_id: str, domain_tag: str, new_status: str):
    conn.execute(
        "UPDATE messages SET domain_tag=?, status=?, updated_at=? WHERE id=?",
        (domain_tag, new_status, datetime.now().isoformat(timespec="seconds"), msg_id),
    )
    conn.commit()


def write_review_message(
    conn: sqlite3.Connection,
    original: dict,
    score: int,
    reason: str,
    best_guess_tag: str | None,
):
    """Write a needs_review notification to CoS on the bus."""
    message_id = original["id"]
    review_source_id = f"review_{message_id}"

    # Idempotency — don't double-write for same original message
    existing = conn.execute(
        "SELECT id FROM messages WHERE source_id = ?", (review_source_id,)
    ).fetchone()
    if existing:
        return

    body = original.get("body") or ""
    subject = original.get("subject") or "(no subject)"
    sender = original.get("source_address") or original.get("sender_name") or ""

    body_payload = json.dumps({
        "original_id":      message_id,
        "original_subject": subject,
        "original_from":    sender,
        "snippet":          body[:200],
        "proposed_tag":     best_guess_tag,
        "confidence":       score,
        "reason":           reason,
        "routing_options":  sorted(ACTIVE_AGENTS),
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
            f"Inbox Review: {subject}",
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


def write_pending_json(review_queue: list[dict]):
    """Write pending review data to both dashboard and agent data files."""
    pending_items = []
    for row in review_queue:
        try:
            body_data = json.loads(row.get("body") or "{}")
        except Exception:
            body_data = {}
        pending_items.append({
            "bus_message_id":  row["id"],
            "source_id":       row.get("source_id"),
            "subject":         row.get("subject"),
            "created_at":      row.get("created_at"),
            "original_id":     body_data.get("original_id"),
            "original_from":   body_data.get("original_from"),
            "snippet":         body_data.get("snippet"),
            "proposed_tag":    body_data.get("proposed_tag"),
            "confidence":      body_data.get("confidence"),
            "reason":          body_data.get("reason"),
            "routing_options": body_data.get("routing_options", []),
        })

    payload = {
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "pending":    pending_items,
    }

    # Write to dashboard data dir
    DASHBOARD_PENDING.parent.mkdir(parents=True, exist_ok=True)
    with open(DASHBOARD_PENDING, "w") as f:
        json.dump(payload, f, indent=2)

    # Write to agent data dir
    PENDING_REVIEWS_PATH.parent.mkdir(parents=True, exist_ok=True)
    agent_payload = {
        "updated_at": payload["updated_at"],
        "pending":    pending_items,
        "note":       "Messages waiting for routing confirmation from Alexander",
    }
    with open(PENDING_REVIEWS_PATH, "w") as f:
        json.dump(agent_payload, f, indent=2)


def write_status(tagged: int, needs_review: int, skipped: int, error: str | None, conn: sqlite3.Connection):
    try:
        total = conn.execute("SELECT COUNT(*) FROM messages WHERE status='tagged'").fetchone()[0]
        review_queue = load_needs_review_queue(conn)
    except Exception:
        total = 0
        review_queue = []

    # Write pending JSON files
    write_pending_json(review_queue)

    health = "ok" if not error else "error"
    if review_queue and not error:
        # Check oldest pending item — escalate to error after 4 hours
        from datetime import datetime as _dt
        oldest_str = min((r.get('created_at','') for r in review_queue), default='')
        try:
            oldest_age_h = (_dt.now() - _dt.fromisoformat(oldest_str)).total_seconds() / 3600
        except Exception:
            oldest_age_h = 0
        health = "error" if oldest_age_h > 4 else "warning"

    recent_decisions = load_recent_decisions(20)
    pending_count = len(review_queue)

    summary = (
        f"Pure router — Keyword-Routing aktiv · {pending_count} Entscheidung{'en' if pending_count != 1 else ''} ausstehend"
        if pending_count > 0
        else "Pure router — Keyword-Routing aktiv · 0 Entscheidungen ausstehend"
    )
    if error:
        summary = f"Error: {error}"
    elif not error and tagged == 0 and needs_review == 0:
        summary = f"Last run: 0 tagged, 0 needs review, 0 skipped."
    elif not error:
        summary = f"Last run: {tagged} tagged, {needs_review} needs review, {skipped} skipped."

    alerts = []
    if review_queue:
        alerts.append({
            "priority": 2,
            "title": f"{pending_count} message(s) need routing review",
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
        "agent":           "inbox-manager",
        "updated_at":      datetime.now().isoformat(timespec="seconds"),
        "health":          health,
        "summary":         summary,
        "pending_reviews": pending_count,
        "alerts":          alerts,
        "upcoming":        [],
        "stats": {
            "total_tagged_alltime":   total,
            "last_run_tagged":        tagged,
            "last_run_needs_review":  needs_review,
            "last_run_skipped":       skipped,
            "last_run_at":            datetime.now().isoformat(timespec="seconds"),
        },
        "recent_decisions":   recent_decisions,
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
            log.info("no_pending", "No pending messages")
            write_status(0, 0, 0, None, conn)
            print("0 pending messages — nothing to route")
            return

        log.info("pending_found", f"Found {len(pending)} pending messages")

        tagged       = 0
        needs_review = 0
        skipped      = 0

        for msg in pending:
            msg_id  = msg["id"]
            subject = msg.get("subject", "") or ""
            body    = msg.get("body", "") or ""
            text    = build_match_text(msg)
            scores  = score_domains(text)

            domain, score, reason = resolve_domain(dict(scores), text)

            ts = datetime.now().isoformat(timespec="seconds")

            # Determine best_guess_tag even when domain is None (for review message)
            best_guess_tag = domain
            if best_guess_tag is None and scores:
                best_guess_tag = max(scores, key=lambda d: scores[d])

            # Route: score ≥ 85 AND agent is active → tagged
            if domain and score >= 85 and domain in ACTIVE_AGENTS:
                tag_message(conn, msg_id, domain, "tagged")
                decision = {
                    "timestamp":        ts,
                    "message_id":       msg_id,
                    "source_id":        msg.get("source_id"),
                    "subject":          subject[:80],
                    "domain":           domain,
                    "confidence":       "high",
                    "confidence_score": score,
                    "reason":           reason,
                    "scores":           scores,
                    "action":           "tagged",
                }
                append_decision(decision)
                log.info("tagged", f"msg={msg_id} → {domain} (score={score})", detail=subject[:60])
                tagged += 1
            else:
                # Needs review — inactive agent, low confidence, or ambiguous
                if domain and domain not in ACTIVE_AGENTS:
                    reason = f"{reason} (agent '{domain}' not active)"
                elif domain and score < 85:
                    reason = f"{reason} (score {score} < 85 threshold)"

                tag_message(conn, msg_id, "cos", "needs_review")
                write_review_message(conn, msg, score, reason, best_guess_tag)

                decision = {
                    "timestamp":        ts,
                    "message_id":       msg_id,
                    "source_id":        msg.get("source_id"),
                    "subject":          subject[:80],
                    "domain":           None,
                    "confidence":       "none",
                    "confidence_score": score,
                    "reason":           reason,
                    "scores":           scores,
                    "action":           "needs_review",
                    "proposed_tag":     best_guess_tag,
                }
                append_decision(decision)
                log.warning("needs_review", f"msg={msg_id} — score={score} — {reason}", detail=subject[:60])
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
