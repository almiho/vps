#!/usr/bin/env python3
"""
Dashboard Generator — AlexI Project
"""

import sqlite3, json, os, sys
from datetime import datetime

sys.path.insert(0, "/home/node/.openclaw/workspace/scripts")
from agent_logger import AgentLogger

WORKSPACE   = "/home/node/.openclaw/workspace"
DB_PATH     = f"{WORKSPACE}/data/dashboard.db"
OUTPUT_DIR  = f"{WORKSPACE}/dashboard"
AGENTS_DIR  = f"{WORKSPACE}/agents"
LOG_DATA_DIR = f"{OUTPUT_DIR}/data/logs"
log = AgentLogger("dashboard")

AGENTS = [
    ("cos",            "Chief of Staff",  "🧠"),
    ("infrastructure", "Infrastructure",  "🔧"),
    ("monitoring",     "Mony",            "👁️"),
    ("comms-collector",   "Comms Collector",    "📨"),
    ("inbox-manager",  "Inbox Manager",   "📬"),
    ("calendar",       "Caly",            "📅"),
    ("friendships",    "Friendships",     "👥"),
    ("finance",        "Finance",         "💰"),
    ("tax",            "Tax",             "📋"),
    ("real-estate",    "Real Estate",     "🏠"),
    ("school",         "School",          "🎒"),
    ("life-in-denmark","Life in Denmark", "🇩🇰"),
    ("car",            "Car",             "🚗"),
    ("boat",           "Boat",            "⛵"),
    ("travel",         "Travel",          "✈️"),
    ("health",         "Health",          "🏥"),
    ("insurance",      "Insurance",       "🛡️"),
    ("dashboard",      "Dashboard",       "📊"),
]

# Clustered agent groups for homepage (same grouping as architecture diagram)
AGENT_CLUSTERS = [
    ("System", [
        ("cos", "Chief of Staff", "🧠"),
        ("infrastructure", "Infrastructure", "🔧"),
        ("monitoring", "Mony", "👁️"),
        ("dashboard", "Dashboard", "📊"),
    ]),
    ("Communications", [
        ("comms-collector", "Comms Collector", "📨"),
        ("inbox-manager", "Inbox Manager", "📬"),
        ("calendar", "Caly", "📅"),
    ]),
    ("Finance & Assets", [
        ("finance", "Finance", "💰"),
        ("real-estate", "Real Estate", "🏠"),
        ("tax", "Tax", "📋"),
        ("insurance", "Insurance", "🛡️"),
    ]),
    ("Family & Life", [
        ("school", "School", "🎒"),
        ("life-in-denmark", "Life in Denmark", "🇩🇰"),
        ("health", "Health", "🏥"),
        ("friendships", "Friendships", "👥"),
    ]),
    ("Vehicles & Movement", [
        ("car", "Car", "🚗"),
        ("boat", "Boat", "⛵"),
        ("travel", "Travel", "✈️"),
    ]),
]

# Cluster accent colors — must stay in sync with SVG cluster fills in render_architecture_svg()
CLUSTER_COLORS = {
    "System":             "#1a3d6e",
    "Communications":     "#0f3d48",
    "Finance & Assets":   "#3d0f6e",
    "Family & Life":      "#3d1548",
    "Vehicles & Movement":"#0f1a55",
}

# About section content per agent
AGENT_ABOUT = {
    "cos": {
        "mission": "Chief of Staff — the single point of contact between Alexander and the entire agent ecosystem.",
        "role": "AlexI doesn't just aggregate data from agents — it adds a strategic interpretation layer on top. It decides what reaches Alexander, when, and in what form. It orchestrates delegation, tracks cross-domain priorities, and ensures the whole system stays aligned with Alexander's goals.",
        "why_important": "Without CoS, Alexander would need to manage 17 separate agents directly. CoS filters, prioritises, and presents a single coherent view. It also holds the OKR framework that gives every todo in the system a strategic purpose.",
        "connects_to": "Receives summaries from all agents. Writes to the dashboard DB. Manages OKRs that inform every domain agent's priorities.",
        "not_overlap": "CoS never stores domain data — it doesn't know tenant names or school schedules. It only knows priorities, status summaries, and strategic context. All detail lives in the specialist agents."
    },
    "infrastructure": {
        "mission": "Builder and standards enforcer for the entire technical foundation.",
        "role": "Sets up, configures, and maintains everything the other agents run on. Defines standards all agents must follow. Scaffolds new agents ensuring consistency. Monitors environment health and flags technical issues proactively.",
        "why_important": "Every other agent depends on the infrastructure Infra builds. If the message bus breaks, all agents go silent. If standards aren't enforced, agents become inconsistent and hard to maintain.",
        "connects_to": "Feeds status to CoS. Scaffolds all other agents. Manages the SQLite message bus schema and dashboard DB.",
        "not_overlap": "Infra has no opinion on finances, school schedules, or boat maintenance. It only cares that the technical plumbing works."
    },
    "monitoring": {
        "mission": "Mony — silent watchdog. Watches everything, speaks only when something is wrong.",
        "role": "Continuously checks system health across all components. Sends Telegram alerts for new failures. Tracks whether agents are alive and processing. Detects degradation before it becomes outage.",
        "why_important": "A system this complex needs a dedicated health layer. Without Watch, problems could go unnoticed for hours. Watch catches issues proactively so Alexander never has to wonder if things are working.",
        "connects_to": "Reads status.json from all active agents. Checks gateway, bus, disk, cron jobs. Sends Telegram alerts directly. Reports to CoS.",
        "not_overlap": "Watch never modifies anything — it only reads and alerts. All fixes are done by Infra or the relevant domain agent."
    },
    "comms-collector": {
        "mission": "Single ingestion point for all external messages — Gmail, WhatsApp, scanned letters.",
        "role": "Reads all incoming channels, normalises messages to a standard internal format, tags by domain, and writes to the SQLite message bus. Preserves full reply context so any agent can respond via the original channel.",
        "why_important": "Without a single normalised ingestion point, every agent would need its own Gmail/WhatsApp connection. Comms Collector means channels are wired once, and all agents speak a channel-agnostic language.",
        "connects_to": "Writes to the SQLite message bus. All domain agents read from the bus. reply_context preserved end-to-end for responding via original channel.",
        "not_overlap": "Router does not process content — it only normalises and routes. No decisions about importance or action. That's CoS and domain agents."
    },
    "inbox-manager": {
        "mission": "Pure router — reads every pending message from the bus and decides which domain agent owns it. Nothing else.",
        "role": "Keyword-matches on subject, sender and first 200 chars of body. Clear match → domain_tag set, status='tagged'. Ambiguous → status='needs_review' + CoS review message written to bus. Logs every decision to decisions.jsonl.",
        "why_important": "Without a router, every domain agent would have to scan all pending messages. Inbox Manager gives each specialist a clean, pre-filtered queue and prevents duplication across agents.",
        "connects_to": "Reads pending messages from the bus (bus.db). Writes domain_tag and status back. Writes needs_review notifications to CoS (domain_tag='cos') on the bus.",
        "not_overlap": "Inbox Manager never analyses content, sets priorities, or suggests actions. It only routes. All downstream intelligence lives in the domain agents and CoS."
    },
    "calendar": {
        "mission": "Caly — the single source of truth for time. Passive calendar layer that shows what's happening and answers questions about schedule.",
        "role": "Fetches and displays events from Google Calendar. Shows the current week at a glance. Answers scheduling questions on request. Does not push notifications or modify events.",
        "why_important": "Travel Agent, School Agent, and CoS all need to reason about time. Without a calendar layer that owns scheduling, conflicts happen and Q2 work never gets protected.",
        "connects_to": "Used by CoS (weekly planning), Travel Agent (conflict detection), School Agent (pickup reminders). Reads from Google Calendar via local MCP.",
        "not_overlap": "Caly doesn't know why you're going to Stadtlohn — just that the slot is taken. Context lives in Travel Agent. Caly is read-only: it never creates or modifies events."
    },
    "friendships": {
        "mission": "Personal relationship CRM — keeps friendships alive and intentional.",
        "role": "Tracks last contact per person, nudges when relationships drift, reminds of birthdays (and flags missing birthdays), maintains friend categories, suggests conversation starters.",
        "why_important": "Most people let friendships drift not from lack of care but from lack of system. Friendships Agent provides the system so the care can actually show.",
        "connects_to": "Reads from comms history (future). Feeds reminders to CoS.",
        "not_overlap": "Tracks relationships, not tasks. No overlap with Calendar (just because someone's in your calendar doesn't mean the relationship is tracked here)."
    },
    "finance": {
        "mission": "Central financial brain — the only agent with the full financial picture.",
        "role": "Tracks cashflow, flags shortfalls, maintains long-term projections and goals, surfaces optimisation opportunities. Receives financial summaries from Real Estate, Tax, Car, Boat, Insurance.",
        "why_important": "Financial health affects everything. Finance Agent is the one place where all money flows are visible together — not just one property or one insurance policy.",
        "connects_to": "Receives summaries from Real Estate, Tax, Insurance, Car, Boat. Reports to CoS.",
        "not_overlap": "Finance sees numbers and trends, not details. It doesn't know which tenant is late — Real Estate does. Finance just knows rental income is down."
    },
    "tax": {
        "mission": "Year-round tax companion — eliminates the annual document scramble.",
        "role": "Captures and tags tax-relevant documents throughout the year, tracks German and Danish filing obligations, guides through annual returns, tracks deadlines.",
        "why_important": "Cross-border tax (Germany + Denmark) with real estate, rental income, and temporary residency is complex. Missing a deadline or document is expensive. Tax Agent makes it manageable.",
        "connects_to": "Receives data from Real Estate (rental income, expenses). Feeds summaries to Finance. Integrates with Life in Denmark Agent (residency status).",
        "not_overlap": "Tax handles tax obligations only. Rental management (tenants, repairs) stays in Real Estate."
    },
    "real-estate": {
        "mission": "Full portfolio manager for owned properties — financial and operational.",
        "role": "Tracks all properties, ownership structure, valuations, mortgages. Manages tenants, leases, maintenance. Stores documents. Feeds financial summaries to Finance Agent and tax data to Tax Agent.",
        "why_important": "Multiple properties, some co-owned, most rented — this is a business in itself. Real Estate Agent is the dedicated manager so nothing slips through.",
        "connects_to": "Feeds to Finance Agent (income/expenses), Tax Agent (rental data). Receives from Comms Collector (tenant emails).",
        "not_overlap": "Provides numbers to Finance but keeps all detail. Finance doesn't need to know about the boiler repair — just that expenses were higher this month."
    },
    "school": {
        "mission": "Education coordinator for the twins across two school systems.",
        "role": "Tracks CIS Copenhagen and Fernschule schedules, monitors day-specific changes, fires dynamic pickup reminders, tracks academic progress and teacher communications.",
        "why_important": "Pickup reminders are safety-critical. Two school systems with different schedules, deadlines, and communication channels is genuinely complex to track manually.",
        "connects_to": "Reads from Comms Collector (school emails/announcements). Feeds schedule data to Calendar and Travel Agent. Reports to CoS.",
        "not_overlap": "School tracks education and schedules. Health Agent handles vaccinations and medical forms separately."
    },
    "life-in-denmark": {
        "mission": "Expat compliance guardian for the Copenhagen chapter.",
        "role": "Tracks CPR numbers, MitID validity, residence permits, the CPH apartment lease, and all Danish obligations for Alexander and the twins. Flags anything Tanja needs to know when visiting.",
        "why_important": "MitID expiry locks out banking, tax, and public services. Missing a lease notice period costs months of rent. These are easy to forget and expensive to miss.",
        "connects_to": "Cross-references with Tax Agent (Danish residency rules) and Real Estate (German home base). Reports to CoS.",
        "not_overlap": "Covers Danish compliance only. German obligations (property, car, tax) are handled by their respective agents."
    },
    "car": {
        "mission": "Remote car manager — keeps the car roadworthy from a distance.",
        "role": "Tracks maintenance history, TÜV/AU deadlines, insurance renewal, and flags when the car has been unused long enough to need attention (battery, tyres).",
        "why_important": "Car sits in Stadtlohn while Alexander is in Copenhagen. No one is checking on it. Without Car Agent, TÜV deadlines get missed and a flat battery is discovered the day you need to drive.",
        "connects_to": "Feeds running costs to Finance Agent. Informs Travel Agent when car is available.",
        "not_overlap": "Handles the car only. Travel Agent knows the car is in Stadtlohn — Car Agent knows if it's actually ready to drive."
    },
    "boat": {
        "mission": "Full lifecycle manager for a 25-year-old boat.",
        "role": "Tracks maintenance history per system, safety equipment expiry, seasonal planning, marina logistics. Future phase: live monitoring (battery, bilge, engine hours).",
        "why_important": "A 25-year-old boat needs consistent maintenance attention. Safety equipment expiry (flares, life raft) is non-negotiable. Age-related failures at sea are serious.",
        "connects_to": "Feeds costs to Finance Agent. Informs Travel Agent of boat availability and weather windows.",
        "not_overlap": "Boat handles everything boat-specific. Insurance Agent handles the hull/liability policy separately."
    },
    "travel": {
        "mission": "Proactive travel planner and family conflict detector.",
        "role": "Plans trips across regular routes (CPH↔Berlin, Stadtlohn, Harderwijk), detects calendar conflicts (both parents away = kids uncovered), suggests optimal travel windows.",
        "why_important": "With family split across countries, a boat in the Netherlands, and business trips for two people — travel coordination is a real job. One missed conflict means kids without a parent.",
        "connects_to": "Uses Calendar Agent for conflict detection. Cross-references School Agent (no travel on pickup days). Checks Car Agent (car available?), Boat Agent (boat ready?).",
        "not_overlap": "Travel plans the logistics. Car/Boat Agents report readiness. School Agent owns the schedule that constrains travel."
    },
    "health": {
        "mission": "Family health tracker — all four family members, both countries.",
        "role": "Tracks GP registrations, upcoming appointments, vaccination schedules, health history. Flags overdue checkups and school health requirements.",
        "why_important": "With a family across two healthcare systems (Danish + German), it's easy to lose track of who is registered where, whose vaccinations are current, and when checkups are due.",
        "connects_to": "Links to Insurance Agent (what's covered where). Informs School Agent (vaccination requirements). Reports to CoS.",
        "not_overlap": "Health tracks health. Insurance Agent holds the policy details. There's no overlap — Health asks 'is this covered?' and Insurance Agent answers."
    },
    "insurance": {
        "mission": "Single overview of all policies — what's covered, what's not, what's expiring.",
        "role": "Tracks all insurance policies (property, car, boat, health, life, travel), flags renewals, identifies coverage gaps, surfaces cost optimisation opportunities.",
        "why_important": "Multiple properties, a boat, a car, a family across two countries — the insurance picture is complex. Coverage gaps are only discovered when you need to make a claim.",
        "connects_to": "Feeds annual costs to Finance Agent. Informs Health Agent (coverage details). Alerts CoS on renewals.",
        "not_overlap": "Insurance holds policies. Real Estate, Car, Boat hold the assets. Insurance Agent doesn't manage the boat — it just makes sure it's covered."
    },
    "dashboard": {
        "mission": "Silent renderer — reads data, writes HTML, stays out of the way.",
        "role": "Reads the dashboard DB and all agent status.json files, generates the HTML dashboard and per-agent pages every 15 minutes. No decision-making — pure presentation.",
        "why_important": "All the intelligence in the world is useless if you can't see it. Dashboard Agent is the final mile that turns data into a readable interface accessible on any device.",
        "connects_to": "Reads from dashboard.db (CoS writes) and all agents' status.json files. Writes to /workspace/dashboard/. Served by the web server on Tailscale.",
        "not_overlap": "Dashboard only reads and renders. It never writes to the bus or modifies any agent's data."
    }
}

CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0f172a; color: #e2e8f0; min-height: 100vh; }
.header { background: #1e293b; padding: 1rem 1.5rem; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #334155; }
.header h1 { font-size: 1.25rem; font-weight: 700; color: #f1f5f9; }
.header-meta { font-size: 0.75rem; color: #64748b; }
.container { max-width: 1200px; margin: 0 auto; padding: 1.5rem; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin-bottom: 1.5rem; }
@media (max-width: 768px) { .grid { grid-template-columns: 1fr; } }
.section { background: #1e293b; border-radius: 12px; padding: 1.25rem; margin-bottom: 1.5rem; }
.section-title { font-size: 0.875rem; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 1rem; }
.item { display: flex; align-items: flex-start; gap: 0.75rem; padding: 0.75rem 0; border-bottom: 1px solid #334155; }
.item:last-child { border-bottom: none; }
.item-priority { font-size: 0.7rem; font-weight: 700; padding: 2px 6px; border-radius: 6px; white-space: nowrap; flex-shrink: 0; margin-top: 2px; }
.p1 { background: #7f1d1d; color: #fca5a5; }
.p2 { background: #7c2d12; color: #fdba74; }
.p3 { background: #713f12; color: #fde68a; }
.p4 { background: #1e3a5f; color: #93c5fd; }
.p5 { background: #1e293b; color: #94a3b8; border: 1px solid #334155; }
.item-content { flex: 1; min-width: 0; }
.item-title { font-size: 0.9rem; font-weight: 600; color: #f1f5f9; }
.item-body { margin-top: 6px; }
.item-body-line { font-size: 0.78rem; color: #94a3b8; line-height: 1.7; display: block; }
.item-body-line.muted { color: #64748b; }
.item-body-line.section-head { color: #cbd5e1; font-weight: 600; margin-top: 4px; }
.item-meta { font-size: 0.75rem; color: #64748b; margin-top: 3px; }
.alert-item { background: rgba(239,68,68,0.05); border-radius: 8px; padding: 0.75rem !important; margin-bottom: 0.5rem; border-bottom: none !important; }
.action-badge { font-size: 0.7rem; background: #ef4444; color: white; padding: 2px 8px; border-radius: 12px; white-space: nowrap; flex-shrink: 0; }
.empty-state { color: #475569; font-size: 0.875rem; padding: 1rem 0; text-align: center; }

/* Cluster grouping on homepage */
.cluster-section { margin-bottom: 1.25rem; }
.cluster-section:last-child { margin-bottom: 0; }
.cluster-label { font-size: 0.72rem; font-weight: 600; color: #475569; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 0.6rem; padding-left: 2px; border-bottom: 1px solid #1e293b; padding-bottom: 0.4rem; }
.agents-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 0.75rem; }
.agent-card { background: #1e293b; border-radius: 10px; padding: 1rem; display: flex; gap: 0.75rem; align-items: flex-start; text-decoration: none; color: inherit; border: 1px solid #334155; transition: border-color 0.15s; }
.agent-card:hover { border-color: #475569; }
.health-ok { border-left: 3px solid #22c55e; }
.health-warning { border-left: 3px solid #f59e0b; }
.health-error { border-left: 3px solid #ef4444; }
.health-unknown { border-left: 3px solid #475569; }
.agent-emoji { font-size: 1.5rem; line-height: 1; flex-shrink: 0; }
.agent-info { flex: 1; min-width: 0; }
.agent-name { font-size: 0.875rem; font-weight: 600; color: #f1f5f9; display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; }
.agent-summary { font-size: 0.75rem; color: #64748b; margin-top: 3px; }
.agent-updated { font-size: 0.7rem; color: #475569; margin-top: 3px; }
.back { color: #64748b; text-decoration: none; font-size: 0.875rem; }
.back:hover { color: #94a3b8; }
.status-row { display: flex; gap: 1rem; align-items: center; flex-wrap: wrap; }
.status-summary { color: #cbd5e1; font-size: 0.9rem; }
.status-updated { color: #475569; font-size: 0.75rem; }
/* About section */
.about-toggle { width: 100%; background: none; border: 1px solid #334155; border-radius: 8px; padding: 0.6rem 1rem; color: #64748b; font-size: 0.8rem; cursor: pointer; text-align: left; display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; }
.about-toggle:hover { border-color: #475569; color: #94a3b8; }
.about-content { display: none; background: #1e293b; border-radius: 12px; padding: 1.25rem; margin-bottom: 1.5rem; }
.about-content.open { display: block; }
.about-row { margin-bottom: 1rem; }
.about-row:last-child { margin-bottom: 0; }
.about-label { font-size: 0.72rem; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.25rem; }
.about-text { font-size: 0.85rem; color: #cbd5e1; line-height: 1.6; }
.about-connects { font-size: 0.8rem; color: #94a3b8; font-style: italic; }
.okr-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-top: 0.75rem; }
@media (max-width: 768px) { .okr-grid { grid-template-columns: 1fr; } }
.okr-card { background: #0f172a; border: 1px solid #334155; border-radius: 10px; padding: 1rem; }
.okr-card-header { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem; }
.okr-icon { font-size: 1.2rem; }
.okr-title { font-size: 0.9rem; font-weight: 700; color: #c7d2fe; }
.okr-idea { font-size: 0.78rem; color: #94a3b8; line-height: 1.5; margin-bottom: 0.75rem; font-style: italic; }
.okr-kr-group { font-size: 0.72rem; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; margin-top: 0.6rem; margin-bottom: 0.2rem; }
.okr-kr-item { font-size: 0.8rem; color: #cbd5e1; line-height: 1.5; padding-left: 0.25rem; }
/* Log section */
details.log-section > summary { cursor:pointer; color:#64748b; font-size:0.8rem; padding:0.4rem 0; user-select:none; list-style:none; }
details.log-section > summary::before { content:'▶ '; font-size:0.7rem; }
details.log-section[open] > summary::before { content:'▼ '; }
details.log-section > summary:hover { color:#94a3b8; }
.log-reload-btn { background:none; border:1px solid #334155; border-radius:6px; color:#64748b; padding:3px 10px; font-size:0.75rem; cursor:pointer; line-height:1; }
.log-reload-btn:hover { border-color:#475569; color:#94a3b8; }
.log-filter-bar { display:flex; flex-wrap:wrap; gap:0.75rem; margin:0.6rem 0 0.4rem; }
.log-filter-group { display:flex; align-items:center; gap:0.3rem; }
.log-filter-label { font-size:0.7rem; color:#475569; text-transform:uppercase; letter-spacing:0.05em; margin-right:2px; }
.log-filter-btn { background:none; border:1px solid #334155; border-radius:4px; color:#64748b; padding:2px 8px; font-size:0.72rem; cursor:pointer; }
.log-filter-btn:hover { border-color:#475569; color:#94a3b8; }
.log-filter-btn.active { background:#1e3a5f; border-color:#3b82f6; color:#93c5fd; }
.log-container { margin-top:0.25rem; font-family:'SF Mono',Menlo,monospace; }
.log-row { display:grid; grid-template-columns:150px 90px 68px 130px 1fr; gap:6px; padding:3px 6px; border-bottom:1px solid #0f172a; font-size:0.74rem; align-items:start; }
.log-row:hover { background:#162032; }
.log-ts { color:#475569; white-space:nowrap; }
.log-agent { color:#a78bfa; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.log-level { font-weight:700; }
.log-lvl-debug { color:#475569; }
.log-lvl-info { color:#64748b; }
.log-lvl-warning { color:#f59e0b; }
.log-lvl-error { color:#ef4444; }
.log-lvl-critical { color:#fca5a5; background:#450a0a; padding:0 3px; border-radius:3px; }
.log-event { color:#7dd3fc; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.log-msg { color:#94a3b8; }
.log-empty { color:#475569; font-size:0.8rem; padding:0.5rem 0; }
"""

ABOUT_JS = """
function toggleAbout() {
  const content = document.getElementById('about-content');
  const arrow = document.getElementById('about-arrow');
  content.classList.toggle('open');
  arrow.textContent = content.classList.contains('open') ? '▲' : '▼';
}
"""

def read_agent_logs(agent_id, n=20):
    """Read last n log entries for an agent."""
    return AgentLogger.read_recent(agent_id, n)

def write_log_json(agent_id, entries):
    """Write log entries as JSON array to dashboard/data/logs/[agent].json."""
    os.makedirs(LOG_DATA_DIR, exist_ok=True)
    with open(f"{LOG_DATA_DIR}/{agent_id}.json", "w") as f:
        json.dump(entries, f)

def render_log_section(agent_id, entries, combined=False):
    """
    Render a collapsible log section with agent/level filters and a reload button.
    combined=True: shows all active agents merged, with agent filter buttons.
    """
    fetch_url = "/data/logs/_combined.json" if combined else f"/data/logs/{agent_id}.json"
    fn_suffix = "combined" if combined else agent_id.replace("-", "_")
    container_id = f"log-{fn_suffix}"
    title = "📋 Combined System Log" if combined else "📋 Recent Log"

    # Collect unique agents for filter buttons (combined only)
    agents_in_log = []
    if combined:
        seen = []
        for e in entries:
            a = e.get("agent", "")
            if a and a not in seen:
                seen.append(a)
        agents_in_log = seen

    entries_json = json.dumps(entries)

    # Agent filter buttons HTML
    agent_filter_html = ""
    if combined and agents_in_log:
        btns = '<button class="log-filter-btn active" onclick="logFilterAgent_{fn_suffix}(this,\'all\')">All</button>'.format(fn_suffix=fn_suffix)
        for a in agents_in_log:
            btns += f'<button class="log-filter-btn" onclick="logFilterAgent_{fn_suffix}(this,\'{a}\')">{a}</button>'
        agent_filter_html = f'<div class="log-filter-group"><span class="log-filter-label">Agent:</span>{btns}</div>'

    return f"""
<div class="section" style="margin-top:1.5rem">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.25rem">
    <div class="section-title" style="margin:0">{title}</div>
    <button class="log-reload-btn" onclick="logReload_{fn_suffix}()">↻ Reload</button>
  </div>
  <details class="log-section">
    <summary>{len(entries)} entries — click to expand</summary>
    <div class="log-filter-bar">
      <div class="log-filter-group">
        <span class="log-filter-label">Level:</span>
        <button class="log-filter-btn active" onclick="logFilterLevel_{fn_suffix}(this,'all')">All</button>
        <button class="log-filter-btn" onclick="logFilterLevel_{fn_suffix}(this,'warning')">Warning+</button>
        <button class="log-filter-btn" onclick="logFilterLevel_{fn_suffix}(this,'error')">Error+</button>
      </div>
      {agent_filter_html}
    </div>
    <div id="{container_id}" class="log-container"></div>
  </details>
</div>
<script>
(function() {{
  var LEVEL_ORDER = {{debug:0,info:1,warning:2,error:3,critical:4}};
  var state_{fn_suffix} = {{data:[], levelMin:-1, agent:'all'}};

  function renderRows_{fn_suffix}() {{
    var s = state_{fn_suffix};
    var el = document.getElementById('{container_id}');
    var rows = s.data.slice().reverse().filter(function(e) {{
      var lvlOk = s.levelMin < 0 || (LEVEL_ORDER[e.level||'info']||0) >= s.levelMin;
      var agOk = s.agent === 'all' || e.agent === s.agent;
      return lvlOk && agOk;
    }});
    if (!rows.length) {{ el.innerHTML = '<div class="log-empty">No entries match the current filter.</div>'; return; }}
    var html = '';
    for (var i = 0; i < rows.length; i++) {{
      var e = rows[i];
      var ts = (e.timestamp||'').slice(0,19).replace('T',' ');
      var lvl = e.level||'info';
      html += '<div class="log-row">'
        + '<span class="log-ts">'+ts+'</span>'
        + '<span class="log-agent">'+(e.agent||'')+'</span>'
        + '<span class="log-level log-lvl-'+lvl+'">'+lvl.toUpperCase()+'</span>'
        + '<span class="log-event">'+(e.event||'')+'</span>'
        + '<span class="log-msg">'+(e.message||'')+'</span>'
        + '</div>';
    }}
    el.innerHTML = html;
  }}

  function setActive(btn) {{
    var group = btn.parentElement;
    group.querySelectorAll('.log-filter-btn').forEach(function(b){{b.classList.remove('active');}});
    btn.classList.add('active');
  }}

  window.logFilterLevel_{fn_suffix} = function(btn, level) {{
    setActive(btn);
    var map = {{all:-1, warning:2, error:3}};
    state_{fn_suffix}.levelMin = map[level] !== undefined ? map[level] : -1;
    renderRows_{fn_suffix}();
  }};

  window.logFilterAgent_{fn_suffix} = function(btn, agent) {{
    setActive(btn);
    state_{fn_suffix}.agent = agent;
    renderRows_{fn_suffix}();
  }};

  window.logReload_{fn_suffix} = function() {{
    fetch('{fetch_url}?t='+Date.now())
      .then(function(r){{return r.json();}})
      .then(function(d){{ state_{fn_suffix}.data = d; renderRows_{fn_suffix}(); }})
      .catch(function(){{}});
  }};

  state_{fn_suffix}.data = {entries_json};
  renderRows_{fn_suffix}();
}})();
</script>"""

def load_agent_status(agent_id):
    try:
        with open(f"{AGENTS_DIR}/{agent_id}/dashboard/status.json") as f:
            return json.load(f)
    except:
        return {"agent": agent_id, "health": "unknown", "summary": "Not yet active", "alerts": [], "upcoming": [], "updated_at": None}

def load_dashboard_items():
    try:
        db = sqlite3.connect(DB_PATH)
        db.row_factory = sqlite3.Row
        items = db.execute("SELECT * FROM dashboard_items WHERE status='active' ORDER BY priority ASC, due_at ASC").fetchall()
        db.close()
        return [dict(i) for i in items]
    except:
        return []

def health_badge(health):
    colors = {"ok": "#22c55e", "warning": "#f59e0b", "error": "#ef4444", "unknown": "#94a3b8"}
    labels = {"ok": "OK", "warning": "⚠️ Warning", "error": "❌ Error", "unknown": "—"}
    return f'<span style="background:{colors.get(health,"#94a3b8")};color:white;padding:2px 8px;border-radius:12px;font-size:0.72rem;font-weight:600">{labels.get(health,"?")}</span>'

def format_time(ts):
    if not ts: return "never"
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.strftime("%d %b %H:%M")
    except:
        return ts[:16] if ts else "never"

def render_body(body_text):
    if not body_text: return ""
    lines = body_text.strip().split("\n")
    html = '<div class="item-body">'
    for line in lines:
        line = line.strip()
        if not line:
            html += '<span class="item-body-line" style="margin-top:4px"> </span>'
        elif any(line.startswith(e) for e in ["✅","❌","🟡","⚠️","🔴","—"*2]):
            html += f'<span class="item-body-line section-head">{line}</span>'
        elif line.startswith("  •") or line.startswith("•"):
            html += f'<span class="item-body-line" style="padding-left:1rem">{line.lstrip()}</span>'
        elif line.startswith("→"):
            html += f'<span class="item-body-line muted" style="padding-left:0.5rem">{line}</span>'
        else:
            html += f'<span class="item-body-line">{line}</span>'
    html += '</div>'
    return html

def render_alert_item(a, show_agent=False):
    p = a.get('priority', 3)
    agent_label = f'<span class="item-meta">{a.get("agent","").upper()}</span>' if show_agent else ""
    action = "<div class='action-badge'>Action needed</div>" if a.get('action_required') else ""
    return f"""
    <div class="item alert-item">
        <div class="item-priority p{p}">P{p}</div>
        <div class="item-content">
            <div class="item-title">{a['title']}</div>
            {agent_label}
            {render_body(a.get('body',''))}
        </div>
        {action}
    </div>"""

def render_okr_section():
    """Parse OKRs.md and render a collapsible OKR overview for the CoS page."""
    okr_path = f"{WORKSPACE}/OKRs.md"
    if not os.path.exists(okr_path):
        return ""

    with open(okr_path) as f:
        lines = f.readlines()

    objectives = []
    current_obj = None
    current_kr_group = None

    for line in lines:
        line = line.rstrip()
        # Top-level objective: ## 1) Title
        if line.startswith("## ") and ")" in line:
            if current_obj:
                objectives.append(current_obj)
            current_obj = {"title": line[3:].strip(), "idea": "", "krs": []}
            current_kr_group = None
        # Idea line
        elif current_obj and line.startswith("**Idea:**"):
            current_obj["idea"] = line.replace("**Idea:**", "").strip()
        # KR group heading
        elif current_obj and line.startswith("**") and line.endswith("**") and "Idea" not in line and "Key Results" not in line and "Measure" not in line:
            current_kr_group = line.strip("*").strip()
        # KR bullet
        elif current_obj and line.strip().startswith("- ") and "Measure:" not in line and current_kr_group:
            current_obj["krs"].append({"group": current_kr_group, "text": line.strip()[2:]})

    if current_obj:
        objectives.append(current_obj)

    # Render
    cards_html = ""
    icons = ["👨‍👩‍👧", "💪", "💶", "💼", "👥"]
    for i, obj in enumerate(objectives):
        icon = icons[i] if i < len(icons) else "🎯"
        # Group KRs by group name
        groups = {}
        for kr in obj["krs"]:
            groups.setdefault(kr["group"], []).append(kr["text"])
        krs_html = ""
        for grp, items in groups.items():
            krs_html += f'<div class="okr-kr-group">{grp}</div>'
            for item in items:
                krs_html += f'<div class="okr-kr-item">• {item}</div>'
        cards_html += f"""
<div class="okr-card">
  <div class="okr-card-header">
    <span class="okr-icon">{icon}</span>
    <span class="okr-title">{obj["title"]}</span>
  </div>
  {f'<div class="okr-idea">{obj["idea"]}</div>' if obj["idea"] else ""}
  <div class="okr-krs">{krs_html}</div>
</div>"""

    return f"""
<button class="about-toggle" onclick="toggleOkrs()" style="margin-bottom:0.5rem">
  🎯 Personal OKRs &nbsp;<span id="okr-arrow">▶</span>
</button>
<div id="okr-content" style="display:none">
  <div class="okr-grid">{cards_html}</div>
</div>
<script>
function toggleOkrs() {{
  var el = document.getElementById('okr-content');
  var arrow = document.getElementById('okr-arrow');
  if (el.style.display === 'none') {{ el.style.display = 'block'; arrow.textContent = '▼'; }}
  else {{ el.style.display = 'none'; arrow.textContent = '▶'; }}
}}
</script>"""


def render_about_section(agent_id):
    about = AGENT_ABOUT.get(agent_id)
    if not about:
        return ""
    return f"""
<button class="about-toggle" onclick="toggleAbout()">
  ℹ️ About this agent &nbsp;<span id="about-arrow">▼</span>
</button>
<div class="about-content" id="about-content">
  <div class="about-row">
    <div class="about-label">Mission</div>
    <div class="about-text">{about['mission']}</div>
  </div>
  <div class="about-row">
    <div class="about-label">Role in the system</div>
    <div class="about-text">{about['role']}</div>
  </div>
  <div class="about-row">
    <div class="about-label">Why it matters</div>
    <div class="about-text">{about['why_important']}</div>
  </div>
  <div class="about-row">
    <div class="about-label">Connects to</div>
    <div class="about-connects">{about['connects_to']}</div>
  </div>
  <div class="about-row">
    <div class="about-label">Does NOT overlap with</div>
    <div class="about-connects">{about['not_overlap']}</div>
  </div>
</div>"""

def render_architecture_svg(agent_statuses=None):
    """
    SVG architecture diagram with domain clusters.
    live=True: nodes coloured by health, clickable.
    """
    live = agent_statuses is not None

    def node_bg(aid):
        if not live: return "#1e293b"
        h = agent_statuses.get(aid, {}).get("health", "unknown")
        return {"ok": "#14532d", "warning": "#f59e0b", "error": "#450a0a", "unknown": "#1e293b"}.get(h, "#1e293b")

    def node_stroke(aid):
        if not live: return "#334155"
        h = agent_statuses.get(aid, {}).get("health", "unknown")
        return {"ok": "#22c55e", "warning": "#d97706", "error": "#ef4444", "unknown": "#475569"}.get(h, "#475569")

    def node_text(aid):
        if not live: return "#94a3b8"
        h = agent_statuses.get(aid, {}).get("health", "unknown")
        return {"ok": "#86efac", "warning": "#1c1917", "error": "#fca5a5", "unknown": "#64748b"}.get(h, "#64748b")

    W, H = 860, 530
    NW, NH = 108, 32
    PAD = 10

    clusters = [
        ("System", "#1a3d6e", [
            ("infrastructure", "🔧 Infra"),
            ("monitoring",     "👁 Watch"),
            ("dashboard",      "📊 Dash"),
        ]),
        ("Communications", "#0f3d48", [
            ("comms-collector",   "📨 Router"),
            ("inbox-manager",  "📬 Comms"),
        ]),
        ("Finance & Assets", "#3d0f6e", [
            ("finance",        "💰 Finance"),
            ("real-estate",    "🏠 Real Estate"),
            ("tax",            "📋 Tax"),
            ("insurance",      "🛡 Insurance"),
        ]),
        ("Family & Life", "#3d1548", [
            ("school",         "🎒 School"),
            ("life-in-denmark","🇩🇰 Denmark"),
            ("health",         "🏥 Health"),
            ("friendships",    "👥 Friends"),
            ("calendar",       "📅 Calendar"),
        ]),
        ("Vehicles & Movement", "#0f1a55", [
            ("car",    "🚗 Car"),
            ("boat",   "⛵ Boat"),
            ("travel", "✈ Travel"),
        ]),
    ]

    svg = []
    svg.append(f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" style="width:100%;max-width:{W}px;font-family:system-ui,sans-serif;background:#0f172a;border-radius:12px">')
    svg.append('<defs><marker id="arr" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto"><path d="M0,0 L0,6 L6,3 z" fill="#334155"/></marker></defs>')

    title = "Live System Health" if live else "System Architecture"
    svg.append(f'<text x="{W//2}" y="20" text-anchor="middle" fill="#64748b" font-size="12">{title}</text>')

    positions = {}

    # CoS at top center
    cos_y = 32
    cos_x = W // 2 - NW // 2
    positions["cos"] = (W // 2, cos_y + NH // 2)
    svg.append(f'<rect x="{cos_x}" y="{cos_y}" width="{NW}" height="{NH}" rx="6" fill="#312e81" stroke="#6366f1" stroke-width="2"/>')
    svg.append(f'<text x="{W//2}" y="{cos_y+NH//2+4}" text-anchor="middle" fill="#c7d2fe" font-size="11" font-weight="bold">🧠 CoS / AlexI</text>')

    # Row 1: System cluster (y=90)
    row1_y = 90
    sys_agents = clusters[0][2]
    sys_total = len(sys_agents) * NW + (len(sys_agents)-1) * PAD
    sys_x = W//2 - sys_total//2
    svg.append(f'<rect x="{sys_x-8}" y="{row1_y-14}" width="{sys_total+16}" height="{NH+22}" rx="8" fill="none" stroke="{clusters[0][1]}" stroke-width="1.5" stroke-opacity="0.7"/>')
    svg.append(f'<text x="{sys_x}" y="{row1_y-4}" fill="#64748b" font-size="9">System</text>')
    for i, (aid, lbl) in enumerate(sys_agents):
        x = sys_x + i*(NW+PAD)
        positions[aid] = (x+NW//2, row1_y+NH//2)

    # Row 2: Comms (left) + Finance&Assets (right), y=170
    row2_y = 175
    comms_agents = clusters[1][2]
    comms_total = len(comms_agents)*NW + (len(comms_agents)-1)*PAD
    comms_x = 18
    svg.append(f'<rect x="{comms_x-8}" y="{row2_y-14}" width="{comms_total+16}" height="{NH+22}" rx="8" fill="none" stroke="{clusters[1][1]}" stroke-width="1.5" stroke-opacity="0.7"/>')
    svg.append(f'<text x="{comms_x}" y="{row2_y-4}" fill="#64748b" font-size="9">Communications</text>')
    for i, (aid, lbl) in enumerate(comms_agents):
        x = comms_x + i*(NW+PAD)
        positions[aid] = (x+NW//2, row2_y+NH//2)

    fin_agents = clusters[2][2]
    fin_total = len(fin_agents)*NW + (len(fin_agents)-1)*PAD
    fin_x = W - fin_total - 18
    svg.append(f'<rect x="{fin_x-8}" y="{row2_y-14}" width="{fin_total+16}" height="{NH+22}" rx="8" fill="none" stroke="{clusters[2][1]}" stroke-width="1.5" stroke-opacity="0.7"/>')
    svg.append(f'<text x="{fin_x}" y="{row2_y-4}" fill="#64748b" font-size="9">Finance & Assets</text>')
    for i, (aid, lbl) in enumerate(fin_agents):
        x = fin_x + i*(NW+PAD)
        positions[aid] = (x+NW//2, row2_y+NH//2)

    # SQLite bus between rows 2 and 3 — clearly labelled separator
    bus_y = 255
    svg.append(f'<rect x="30" y="{bus_y}" width="{W-60}" height="5" rx="3" fill="#1d4ed8" opacity="0.8"/>')
    svg.append(f'<text x="{W//2}" y="{bus_y+16}" text-anchor="middle" fill="#93c5fd" font-size="9">⇄  SQLite Message Bus  —  shared communication channel for all agents  ⇄</text>')

    # Row 3: Family & Life (y=290)
    row3_y = 290
    fam_agents = clusters[3][2]
    fam_total = len(fam_agents)*NW + (len(fam_agents)-1)*PAD
    fam_x = W//2 - fam_total//2
    svg.append(f'<rect x="{fam_x-8}" y="{row3_y-14}" width="{fam_total+16}" height="{NH+22}" rx="8" fill="none" stroke="{clusters[3][1]}" stroke-width="1.5" stroke-opacity="0.7"/>')
    svg.append(f'<text x="{fam_x}" y="{row3_y-4}" fill="#64748b" font-size="9">Family & Life</text>')
    for i, (aid, lbl) in enumerate(fam_agents):
        x = fam_x + i*(NW+PAD)
        positions[aid] = (x+NW//2, row3_y+NH//2)

    # Row 4: Vehicles & Movement (y=375)
    row4_y = 375
    veh_agents = clusters[4][2]
    veh_total = len(veh_agents)*NW + (len(veh_agents)-1)*PAD
    veh_x = W//2 - veh_total//2
    svg.append(f'<rect x="{veh_x-8}" y="{row4_y-14}" width="{veh_total+16}" height="{NH+22}" rx="8" fill="none" stroke="{clusters[4][1]}" stroke-width="1.5" stroke-opacity="0.7"/>')
    svg.append(f'<text x="{veh_x}" y="{row4_y-4}" fill="#64748b" font-size="9">Vehicles & Movement</text>')
    for i, (aid, lbl) in enumerate(veh_agents):
        x = veh_x + i*(NW+PAD)
        positions[aid] = (x+NW//2, row4_y+NH//2)

    # Dashed arrows from CoS to key agents
    cx0, cy0 = positions["cos"]
    for aid in ["infrastructure", "monitoring", "comms-collector", "finance", "school"]:
        if aid in positions:
            ax, ay = positions[aid]
            svg.append(f'<line x1="{cx0}" y1="{cy0+NH//2}" x2="{ax}" y2="{ay-NH//2}" stroke="#334155" stroke-width="1" stroke-dasharray="4,3" marker-end="url(#arr)"/>')

    # Draw all agent nodes
    all_agents = [a for cl in clusters for a in cl[2]]
    for aid, lbl in all_agents:
        if aid not in positions: continue
        px, py = positions[aid]
        x, y = px-NW//2, py-NH//2
        link_open = f'<a href="{aid}.html">' if live else ""
        link_close = "</a>" if live else ""
        bg = node_bg(aid)
        stroke = node_stroke(aid)
        tc = node_text(aid)
        svg.append(link_open)
        svg.append(f'<rect x="{x}" y="{y}" width="{NW}" height="{NH}" rx="5" fill="{bg}" stroke="{stroke}" stroke-width="{1.5 if live else 1}"/>')
        if live:
            h = agent_statuses.get(aid, {}).get("health", "unknown")
            dc = {"ok": "#22c55e", "warning": "#f59e0b", "error": "#ef4444", "unknown": "#475569"}.get(h, "#475569")
            svg.append(f'<circle cx="{x+NW-6}" cy="{y+7}" r="3.5" fill="{dc}"/>')
        svg.append(f'<text x="{px}" y="{py+4}" text-anchor="middle" fill="{tc}" font-size="10">{lbl}</text>')
        svg.append(link_close)

    # Legend for live mode
    if live:
        lx, ly = 20, H-22
        for color, label in [("#22c55e","Healthy"),("#f59e0b","Warning"),("#ef4444","Error"),("#475569","Unknown")]:
            svg.append(f'<circle cx="{lx+5}" cy="{ly+5}" r="4" fill="{color}"/>')
            svg.append(f'<text x="{lx+13}" y="{ly+9}" fill="#64748b" font-size="10">{label}</text>')
            lx += 85

    svg.append("</svg>")
    return "\n".join(svg)

def render_calendar_week():
    """Render a weekly calendar grid from agents/calendar/data/events.json."""
    events_path = f"{AGENTS_DIR}/calendar/data/events.json"
    try:
        with open(events_path) as f:
            data = json.load(f)
    except Exception:
        return '<div class="section"><div class="section-title">📅 This Week</div><div class="empty-state">No calendar data yet — run agents/calendar/scripts/refresh.py</div></div>'

    events    = data.get("events", [])
    week_start = data.get("week_start", "")
    generated  = data.get("generated_at", "")[:16].replace("T", " ")

    # Build day buckets
    from datetime import date, timedelta
    try:
        mon = date.fromisoformat(week_start)
    except Exception:
        mon = date.today() - __import__("datetime").timedelta(days=date.today().weekday())

    days = [mon + timedelta(days=i) for i in range(7)]
    day_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    today_str  = date.today().isoformat()

    buckets = {d.isoformat(): [] for d in days}
    for e in events:
        day = e.get("start", "")[:10]
        if day in buckets:
            buckets[day].append(e)

    # Calendar legend
    calendars = data.get("calendars", [])
    legend_html = '<div style="display:flex;flex-wrap:wrap;gap:0.5rem;margin-bottom:1rem">'
    for cal in calendars:
        legend_html += f'<span style="font-size:0.72rem;background:{cal["color"]}22;border:1px solid {cal["color"]}55;color:{cal["color"]};padding:2px 8px;border-radius:10px">{cal["name"]}</span>'
    legend_html += '</div>'

    # Grid
    cols_html = ""
    for i, d in enumerate(days):
        d_str   = d.isoformat()
        is_today = d_str == today_str
        day_events = buckets[d_str]

        # Day header
        hdr_bg    = "#1a3d6e" if is_today else "#1e293b"
        hdr_color = "#93c5fd" if is_today else "#94a3b8"
        today_dot = ' <span style="display:inline-block;width:6px;height:6px;border-radius:50%;background:#3b82f6;vertical-align:middle;margin-left:2px"></span>' if is_today else ""
        hdr = (f'<div style="background:{hdr_bg};border-radius:6px 6px 0 0;padding:6px 8px;text-align:center">'
               f'<div style="font-size:0.7rem;font-weight:700;color:{hdr_color};text-transform:uppercase">{day_labels[i]}{today_dot}</div>'
               f'<div style="font-size:0.75rem;color:#64748b">{d.strftime("%d %b")}</div>'
               f'</div>')

        # Events in this day
        items_html = ""
        if day_events:
            for ev in day_events:
                color = ev.get("calendar_color", "#64748b")
                start = ev.get("start", "")
                time_label = start[11:16] if "T" in start else "All day"
                title = ev.get("title", "—")
                link  = ev.get("link", "")
                link_open  = f'<a href="{link}" target="_blank" style="text-decoration:none;color:inherit">' if link else ""
                link_close = "</a>" if link else ""
                items_html += (
                    f'<div style="background:{color}18;border-left:2px solid {color};border-radius:0 4px 4px 0;'
                    f'padding:4px 6px;margin-bottom:4px;overflow:hidden">'
                    f'{link_open}'
                    f'<div style="font-size:0.65rem;color:{color};font-weight:600">{time_label}</div>'
                    f'<div style="font-size:0.72rem;color:#cbd5e1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{title}</div>'
                    f'{link_close}</div>'
                )
        else:
            items_html = '<div style="font-size:0.7rem;color:#334155;text-align:center;padding:8px 0">—</div>'

        cols_html += (
            f'<div style="min-width:0;flex:1">'
            f'{hdr}'
            f'<div style="background:#0f172a;border-radius:0 0 6px 6px;padding:6px;min-height:80px">{items_html}</div>'
            f'</div>'
        )

    grid_html = f'<div style="display:flex;gap:6px;overflow-x:auto">{cols_html}</div>'
    footer    = f'<div style="font-size:0.7rem;color:#475569;margin-top:0.75rem;text-align:right">Fetched {generated} UTC</div>'

    gc_connected = data.get("globalconnect_connected", False)
    if gc_connected:
        gc_section = ""  # future: render second grid
    else:
        gc_section = (
            f'<div class="section" style="margin-top:1rem">'
            f'<div class="section-title">💼 GlobalConnect Calendar</div>'
            f'<div style="background:#1e293b;border-radius:8px;padding:1rem;display:flex;align-items:center;gap:0.75rem">'
            f'<span style="font-size:1.25rem">🔗</span>'
            f'<div>'
            f'<div style="font-size:0.875rem;font-weight:600;color:#f1f5f9">Not connected</div>'
            f'<div style="font-size:0.78rem;color:#64748b;margin-top:3px">'
            f'alehof@globalconnect.dk needs OAuth authorization.<br>'
            f'Ask Caly to connect it: "Connect my GlobalConnect calendar"'
            f'</div>'
            f'</div>'
            f'</div>'
            f'</div>'
        )

    return (f'<div class="section">'
            f'<div class="section-title">📅 This Week — {mon.strftime("%d %b")} to {(mon + timedelta(days=6)).strftime("%d %b")}</div>'
            f'{legend_html}{grid_html}{footer}'
            f'</div>'
            f'{gc_section}')


def render_inbox_manager_section(status: dict) -> str:
    """Custom section for Inbox Manager: routing stats, recent decisions, needs_review queue."""
    stats = status.get("stats", {})
    decisions = status.get("recent_decisions", [])
    review_queue = status.get("needs_review_queue", [])

    # Stats row
    stats_html = (
        f'<div style="display:flex;gap:2rem;flex-wrap:wrap;margin-bottom:1rem">'
        f'<div><div style="font-size:1.5rem;font-weight:700;color:#f1f5f9">{stats.get("total_tagged_alltime",0)}</div>'
        f'<div style="font-size:0.72rem;color:#64748b;text-transform:uppercase">Total Tagged</div></div>'
        f'<div><div style="font-size:1.5rem;font-weight:700;color:#f59e0b">{stats.get("last_run_needs_review",0)}</div>'
        f'<div style="font-size:0.72rem;color:#64748b;text-transform:uppercase">Needs Review</div></div>'
        f'<div><div style="font-size:1.5rem;font-weight:700;color:#22c55e">{stats.get("last_run_tagged",0)}</div>'
        f'<div style="font-size:0.72rem;color:#64748b;text-transform:uppercase">Last Run Tagged</div></div>'
        f'<div><div style="font-size:0.85rem;color:#94a3b8">{(stats.get("last_run_at") or "never")[:16]}</div>'
        f'<div style="font-size:0.72rem;color:#64748b;text-transform:uppercase">Last Run</div></div>'
        f'</div>'
    )

    # Domain color map
    domain_colors = {
        "finance":        ("#1e3a5f", "#93c5fd"),
        "real-estate":    ("#14532d", "#86efac"),
        "tax":            ("#3b0764", "#d8b4fe"),
        "boat":           ("#0f3d48", "#67e8f9"),
        "car":            ("#1c1917", "#d6d3d1"),
        "school":         ("#422006", "#fcd34d"),
        "health":         ("#450a0a", "#fca5a5"),
        "travel":         ("#1e3a5f", "#7dd3fc"),
        "life-in-denmark":("#052e16", "#4ade80"),
        "insurance":      ("#2d1b69", "#c4b5fd"),
        "cos":            ("#1e293b", "#94a3b8"),
    }

    def domain_badge(domain):
        bg, fg = domain_colors.get(domain, ("#1e293b", "#94a3b8"))
        return f'<span style="background:{bg};color:{fg};padding:2px 8px;border-radius:10px;font-size:0.7rem;font-weight:600;white-space:nowrap">{domain}</span>'

    def conf_badge(conf):
        colors = {"high": "#22c55e", "low": "#f59e0b", "none": "#ef4444"}
        color = colors.get(conf, "#64748b")
        return f'<span style="color:{color};font-size:0.7rem;font-weight:600">{conf.upper()}</span>'

    # Recent decisions table
    if decisions:
        rows = ""
        for d in reversed(decisions[-15:]):
            ts = (d.get("timestamp") or "")[:16]
            subj = (d.get("subject") or "(no subject)")[:50]
            dom = d.get("domain") or "—"
            conf = d.get("confidence") or "none"
            action = d.get("action") or ""
            badge = domain_badge(dom) if action == "tagged" else '<span style="color:#f59e0b;font-size:0.7rem;font-weight:600">REVIEW</span>'
            rows += (f'<div class="item" style="padding:0.5rem 0">'
                     f'<div style="flex:1;min-width:0">'
                     f'<div class="item-title" style="font-size:0.82rem">{subj}</div>'
                     f'<div class="item-meta">{ts}</div></div>'
                     f'<div style="display:flex;gap:0.5rem;align-items:center">{badge} {conf_badge(conf)}</div>'
                     f'</div>')
        decisions_html = f'<div class="section"><div class="section-title">🔀 Recent Routing Decisions</div>{rows}</div>'
    else:
        decisions_html = '<div class="section"><div class="section-title">🔀 Recent Routing Decisions</div><div class="empty-state">No decisions yet</div></div>'

    # Needs review queue
    if review_queue:
        qrows = ""
        for item in review_queue:
            subj = (item.get("subject") or "").replace("Inbox Review: ", "")[:60]
            ts = (item.get("created_at") or "")[:16]
            try:
                body = json.loads(item.get("body") or "{}")
                opts = ", ".join(body.get("routing_options", [])) or "none"
                reason = body.get("reason", "")
            except Exception:
                opts = "—"
                reason = ""
            qrows += (f'<div class="item alert-item">'
                      f'<span class="action-badge">REVIEW</span>'
                      f'<div class="item-content">'
                      f'<div class="item-title">{subj}</div>'
                      f'<span class="item-body-line">Options: {opts} · {reason}</span>'
                      f'<div class="item-meta">{ts}</div></div></div>')
        review_html = f'<div class="section"><div class="section-title">⚠️ Needs Review Queue</div>{qrows}</div>'
    else:
        review_html = '<div class="section"><div class="section-title">⚠️ Needs Review Queue</div><div class="empty-state">Queue empty ✓</div></div>'

    return (
        f'<div class="section"><div class="section-title">📊 Routing Stats</div>{stats_html}</div>'
        + review_html
        + decisions_html
    )


def generate_index(items, agent_statuses):
    now = datetime.now().strftime("%d %b %Y %H:%M")
    alert_items = [i for i in items if i["category"] in ("today","alert") and i["action_required"]]

    # Promote action_required alerts from agent status.json files into the panel
    for agent_id, s in agent_statuses.items():
        if s.get("health") in ("error", "warning"):
            for a in s.get("alerts", []):
                if a.get("action_required"):
                    alert_items.append({**a, "agent": agent_id, "category": "alert"})
            # Also promote health=error agents that have no explicit action_required alert
            if s.get("health") == "error" and not any(a.get("action_required") for a in s.get("alerts", [])):
                alert_items.append({
                    "priority": 1,
                    "title": f"{agent_id.title()} — {s.get('summary', 'Error detected')}",
                    "body": f"Agent health: {s.get('health')}. See {agent_id}.html for details.",
                    "agent": agent_id,
                    "action_required": True,
                    "category": "alert",
                    "due_at": None,
                })

    alert_items.sort(key=lambda i: i.get("priority", 3))
    alerts_html = "".join(render_alert_item(i, show_agent=True) for i in alert_items) if alert_items else '<div class="empty-state">✅ No urgent items right now</div>'
    upcoming_items = [i for i in items if i["category"] == "upcoming"]
    # Also pull upcoming from agent status.json files
    for agent_id, s in agent_statuses.items():
        for u in s.get("upcoming", []):
            if u.get("title"):
                upcoming_items.append({**u, "agent": agent_id})
    upcoming_items.sort(key=lambda i: (i.get("priority", 3), i.get("due_at") or ""))
    upcoming_items = upcoming_items[:8]
    upcoming_html = ""
    for item in upcoming_items:
        due = f" · {format_time(item.get('due_at'))}" if item.get('due_at') else ""
        agent_label = item.get("agent","").upper()
        meta = f"{agent_label}{due}" if agent_label else due.lstrip(" · ")
        meta_html = f'<div class="item-meta">{meta}</div>' if meta else ""
        upcoming_html += f'<div class="item"><div class="item-priority p{item["priority"]}">P{item["priority"]}</div><div class="item-content"><div class="item-title">{item["title"]}</div>{meta_html}</div></div>'
    if not upcoming_html:
        upcoming_html = '<div class="empty-state">Nothing upcoming logged yet</div>'

    # Build clustered agent grid
    clusters_html = ""
    for cluster_name, cluster_agents in AGENT_CLUSTERS:
        cluster_color = CLUSTER_COLORS.get(cluster_name, "#334155")
        cards = ""
        for agent_id, label, emoji in cluster_agents:
            s = agent_statuses.get(agent_id, {})
            health = s.get("health","unknown")
            cards += (f'<a href="{agent_id}.html" class="agent-card health-{health}" style="border-right:3px solid {cluster_color}">'
                     f'<div class="agent-emoji">{emoji}</div>'
                     f'<div class="agent-info">'
                     f'<div class="agent-name">{label} {health_badge(health)}</div>'
                     f'<div class="agent-summary">{s.get("summary","Not yet active")}</div>'
                     f'<div class="agent-updated">Updated: {format_time(s.get("updated_at"))}</div>'
                     f'</div></a>')
        clusters_html += (f'<div class="cluster-section">'
                         f'<div class="cluster-label">{cluster_name}</div>'
                         f'<div class="agents-grid">{cards}</div>'
                         f'</div>')

    return ('<!DOCTYPE html>\n'
            '<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">\n'
            f'<meta http-equiv="refresh" content="900"><title>AlexI Dashboard</title><style>{CSS}</style></head>\n'
            '<body>\n'
            f'<div class="header"><h1>\U0001f91d AlexI Dashboard</h1><div class="header-meta">Updated {now} \xb7 Auto-refreshes every 15 min</div></div>\n'
            f'<div class="container">\n'
            f'  <div class="grid">\n'
            f'    <div class="section"><div class="section-title">\U0001f534 Needs Attention</div>{alerts_html}</div>\n'
            f'    <div class="section"><div class="section-title">\U0001f4c5 Upcoming</div>{upcoming_html}</div>\n'
            f'  </div>\n'
            f'  <div class="section"><div class="section-title">\U0001f916 Agent Status</div>{clusters_html}</div>\n'
            '</div></body></html>')

def generate_agent_page(agent_id, label, emoji, status, agent_statuses=None, agent_logs=None):
    now = datetime.now().strftime("%d %b %Y %H:%M")
    health = status.get("health","unknown")
    summary = status.get("summary","Not yet active")
    updated = format_time(status.get("updated_at"))

    alerts_html = "".join(render_alert_item(a) for a in status.get("alerts",[]))
    if not alerts_html: alerts_html = '<div class="empty-state">No alerts</div>'

    upcoming_html = ""
    for u in status.get("upcoming",[]):
        due = f" · {format_time(u.get('due_at'))}" if u.get('due_at') else ""
        upcoming_html += f'<div class="item"><div class="item-priority p{u["priority"]}">P{u["priority"]}</div><div class="item-content"><div class="item-title">{u["title"]}{due}</div></div></div>'
    if not upcoming_html: upcoming_html = '<div class="empty-state">Nothing upcoming</div>'

    about_html = render_about_section(agent_id)

    # Extra sections for specific agents
    extra_html = ""
    if agent_id == "cos":
        okr_html = render_okr_section()
        if okr_html:
            extra_html = f'<div class="section"><div class="section-title">🎯 Goals & OKRs</div>{okr_html}</div>'
    elif agent_id == "infrastructure":
        extra_html = f'<div class="section"><div class="section-title">🗺️ System Architecture</div>{render_architecture_svg()}</div>'
    elif agent_id == "calendar":
        extra_html = render_calendar_week()
    elif agent_id == "inbox-manager":
        extra_html = render_inbox_manager_section(status)
    elif agent_id == "monitoring" and agent_statuses:
        combined_entries = agent_logs.get("_combined", []) if agent_logs else []
        combined_log_html = render_log_section("monitoring", combined_entries, combined=True)
        extra_html = (f'<div class="section"><div class="section-title">🟢 Live System Health</div>{render_architecture_svg(agent_statuses)}</div>'
                      + combined_log_html)

    # Per-agent log section (at bottom of every page)
    agent_log_entries = (agent_logs or {}).get(agent_id, [])
    log_html = render_log_section(agent_id, agent_log_entries)

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{label} — AlexI</title><style>{CSS}</style><script>{ABOUT_JS}</script></head>
<body>
<div class="header">
  <a href="index.html" class="back">← Dashboard</a>
  <div style="display:flex;align-items:center;gap:0.75rem"><span style="font-size:1.5rem">{emoji}</span><span style="font-size:1.1rem;font-weight:700">{label}</span>{health_badge(health)}</div>
  <div style="font-size:0.75rem;color:#475569">{now}</div>
</div>
<div class="container" style="max-width:900px">
  {about_html}
  <div class="section"><div class="section-title">Status</div>
    <div class="status-row"><div class="status-summary">{summary}</div><div class="status-updated">Last updated: {updated}</div></div>
  </div>
  {extra_html}
  <div class="section"><div class="section-title">🔴 Alerts & Actions</div>{alerts_html}</div>
  <div class="section"><div class="section-title">📅 Upcoming</div>{upcoming_html}</div>
  {log_html}
</div></body></html>"""

def main():
    log.info("run_start", "Beginning dashboard generation")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(LOG_DATA_DIR, exist_ok=True)
    items = load_dashboard_items()
    agent_statuses = {aid: load_agent_status(aid) for aid, _, _ in AGENTS}

    # Read logs for all agents and write per-agent JSON files
    ACTIVE_AGENTS = ["cos", "infrastructure", "monitoring", "dashboard"]
    agent_logs = {}
    for agent_id, _, _ in AGENTS:
        entries = read_agent_logs(agent_id, n=50)
        agent_logs[agent_id] = entries
        write_log_json(agent_id, entries)

    # Combined log for monitoring page (last 30 entries across active agents, newest first)
    combined = AgentLogger.read_combined(ACTIVE_AGENTS, n=30)
    agent_logs["_combined"] = combined
    with open(f"{LOG_DATA_DIR}/_combined.json", "w") as f:
        json.dump(combined, f)

    with open(f"{OUTPUT_DIR}/index.html", "w") as f:
        f.write(generate_index(items, agent_statuses))

    HANDCRAFTED_PAGES = {"boat", "tax"}  # these have custom dashboards — do not overwrite

    for agent_id, label, emoji in AGENTS:
        if agent_id in HANDCRAFTED_PAGES:
            continue  # skip — handcrafted dashboard exists
        with open(f"{OUTPUT_DIR}/{agent_id}.html", "w") as f:
            f.write(generate_agent_page(agent_id, label, emoji, agent_statuses[agent_id], agent_statuses, agent_logs))

    # Update dashboard agent's own status.json
    _status = {
        "agent": "dashboard",
        "updated_at": datetime.now().isoformat(),
        "health": "ok",
        "summary": f"Generated {len(AGENTS)+1} pages. Runs every 15 minutes.",
        "alerts": [],
        "upcoming": []
    }
    _spath = f"{AGENTS_DIR}/dashboard/dashboard/status.json"
    os.makedirs(os.path.dirname(_spath), exist_ok=True)
    with open(_spath, "w") as _f:
        json.dump(_status, _f, indent=2)

    log.info("run_complete", f"Generated {len(AGENTS)+1} pages")
    print(f"✅ Dashboard generated — {len(AGENTS)+1} pages")

if __name__ == "__main__":
    main()
