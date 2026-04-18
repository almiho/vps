# Agent System — Ideas & Design

A living document capturing the full concept for Alexander's personal agent ecosystem.
Last updated: 2026-04-12

---

## Table of Contents

1. [Architecture & Design Principles](#architecture)
2. [System-Wide Standards](#standards)
3. [Open Design Questions & Todos](#todos)
4. [Agent Overview](#agents)
5. [Agent Specs](#specs)
6. [Dashboard](#dashboard)
7. [Message Flow & Communications Architecture](#comms)

---

<a name="architecture"></a>
## 🏗️ Architecture & Design Principles

### What's well designed ✅
- **Domain expert model** — bounded contexts, clear ownership, specialist depth. Correct pattern.
- **Hierarchical data flow** — specialists feed generalists (Real Estate → Finance, Tax pulls from both). Clean, no duplication.
- **Channel-agnostic messaging via SQLite bus** — right level of sophistication for the scale.
- **Proactive over reactive** — agents warn before problems, not just log after. Right mindset throughout.
- **Human-in-the-loop by default** — agents suggest, Alexander approves. Automation increases progressively as confidence rises.

### Core Design Patterns

**Layered agent hierarchy:**
```
[ YOU ] ← dashboard + Telegram alerts
    ↑
[ CoS ] ← strategic view, GTD processing, cross-domain prioritisation
    ↑
[ DOMAIN AGENTS ] ← deep specialist knowledge per area
    ↑
[ COMMS ROUTER ] ← normalises all input channels
    ↑
[ INPUT SOURCES ] ← Gmail, WhatsApp, scanned letters, manual input
```

**Data flow principle:**
- Specialist agents (Real Estate, Tax, Car, Boat, School, etc.) hold deep domain detail
- They feed summaries upward — Finance Agent gets numbers, not property management detail
- CoS is the only agent with full cross-domain view
- No agent duplicates another's source of truth

**SQLite message bus (inter-agent communication):**
- Single local SQLite file, WAL mode enabled (`PRAGMA journal_mode=WAL;`)
- All inter-agent messages normalised to standard format
- Multiple agents read/write concurrently without issue at personal scale
- Fully inspectable, auditable, survives restarts
- Future-proof: migrate to PostgreSQL if ever needed — schema stays identical

Schema:
```
messages (id, timestamp, source_channel, sender, subject, body,
          domain_tag, status, forward_count, processed_by[],
          reply_context, processed_at)
```

**Routing model (hybrid):**
1. Comms Collector ingests all channels, normalises, tags by domain, writes to bus
2. Domain agents query bus for their tagged messages, process with full domain knowledge
3. CoS handles unmatched/cross-domain items directly with Alexander
4. Inbox Manager Agent handles leftover general messages no domain claimed

### Scalability Note
The CoS currently handles both GTD processing and strategic prioritisation in one agent. This is intentional at current scale. If the system grows significantly, consider splitting into a **Processing CoS** (GTD, routing, 2-min rule) and a **Strategic CoS** (OKRs, Covey, weekly review). Not needed now — revisit when scale demands it.

---

<a name="standards"></a>
## 📐 System-Wide Standards

These apply to every agent without exception.

### Confidence Levels (mandatory)
Every agent that suggests any decision must include its confidence level.
- Format: **High / Medium / Low** + one-line reason
- Agents explain briefly why confidence is high or low
- CoS uses confidence when deciding whether to act autonomously or escalate
- Low confidence → always human-in-the-loop, regardless of automation level reached
- Confidence calibration improves over time as outcomes are tracked

### Dashboard Output (mandatory)
Every agent must have a defined `dashboard_output` — a JSON file it writes to, consumed by the HTML dashboard. Format to be defined per agent during build phase, but must be planned from the start. No agent spec is complete without it.

### Human-in-the-Loop Workflow
- Agents suggest, Alexander approves — nothing executes autonomously without approval (until confidence earns it)
- Suggestions must not silently expire — CoS tracks pending approvals and follows up
- Alexander can: approve / reject / defer any suggestion
- Automation level increases per category as CoS learns patterns and confidence rises
- All decisions logged for audit and calibration

### Audit Trail
- Every message carries `processed_by[]` — ordered list of every agent that touched it
- Combined with `forward_count`, gives full visibility of message journey
- Decision and action history persists beyond individual sessions
- Enables debugging, loop detection, and confidence calibration

### Forward Counter (loop prevention)
- Every message carries `forward_count`, incremented each time it moves inbox
- If threshold reached (e.g. 3), CoS flags for human review — never routes blindly again
- Prevents loops, surfaces genuinely ambiguous items

---

<a name="todos"></a>
## 🔧 Open Design Questions & Todos

Items that need a decision before or during build.

### Priority Design Gaps

#### 0. Agent Storage Standard *(defined in INFRA_AGENT.md)*
Every agent has its own dedicated subfolder under `agents/[name]/` in the workspace. No agent touches another's folder — all cross-agent communication via SQLite bus. Full directory structure defined in `INFRA_AGENT.md`. Infrastructure Agent creates all folders during Milestone 0.

#### 1. Data Ownership Model *(define before building)*
Multiple agents hold overlapping data (e.g. Real Estate knows property costs, Finance knows cashflow, Tax needs both). Without clear data ownership, agents will drift — two agents with different numbers for the same thing.
- Need a deliberate decision per data type: who is the source of truth, who is a consumer
- Document as part of each agent's spec during build

#### 2. Tanja's Access & Role *(decide before building)*
Several agents cover Tanja (Travel, Health, Life in Denmark, Real Estate co-ownership). No decision yet on:
- Does she have her own access to the system?
- Does she have her own view / dashboard?
- Does everything route through Alexander or does she interact directly?
- Affects: privacy boundaries, dashboard scope, Travel Agent conflict detection logic

#### 3. Calendar Ownership *(add Calendar Agent — see Agent ideas)*
Travel Agent touches calendars, School Agent touches schedules, CoS does weekly planning — but nobody *owns* the calendar. Gap: who blocks Q2 time? Who prevents double-booking? Who manages scheduling across all agent recommendations?
→ Needs a dedicated Calendar Agent or explicit calendar layer within CoS.

#### 4. Structured Onboarding / Cold Start *(design per agent)*
Every agent needs initial data to be useful. Currently implicit — fed manually. A structured onboarding flow per agent ("what do I need from you to get started?") would make adoption smoother and ensure nothing critical is missing at launch.

#### 5. Persistent Agent Memory / Learning Layer *(design before building)*
Agents are currently stateless processors. A truly great assistant learns patterns over time — preferences, summary formats, past decisions and why. Need a persistent knowledge layer per agent so context isn't rebuilt from scratch every session.

#### 6. Shared Context Bus — Inter-agent Awareness *(phase 2)*
Agents are currently isolated beyond the message bus. If Travel Agent knows you're going to Stadtlohn next weekend, Car Agent should know the car may be used, Real Estate Agent should know you might check the property. A shared context layer would make the system feel genuinely intelligent rather than a collection of trackers. Build on the SQLite bus foundation.

#### 7. Trust & Privacy Boundaries *(decide before adding other users)*
All agents currently run with the same access level. Sensitive agents (Finance, Health, Tax) should have stricter data handling rules than benign ones (Car, Boat). Especially relevant when Tanja's access is resolved.

### Future Capabilities (not urgent)
- **Proactive insight generation** — "I noticed boat maintenance costs increased 40% year-on-year." Requires historical accumulation and trend analysis per agent.
- **Context threading across agents** — builds on shared context bus; agents proactively informing each other of state changes.

---

<a name="agents"></a>
## 🤖 Agent Overview

| # | Agent | Role | Feeds into |
|---|-------|------|-----------|
| 0 | **Chief of Staff (CoS)** ⭐ | GTD processing, strategic prioritisation, OKRs, Covey Q2 | You (via Telegram + dashboard) |
| 1 | **Infrastructure** | OC environment setup, best practices | — |
| 2 | **Monitoring** | System health, message queue, proactive alerts | You + CoS |
| 3 | **Comms Collector** | Ingests Gmail/WhatsApp/scans, normalises, routes | SQLite bus |
| 4 | **Inbox Manager** | Unmatched messages, inbox triage, follow-ups | CoS |
| 5 | **Calendar** | Owns scheduling, blocks Q2 time, prevents conflicts | CoS, Travel |
| 6 | **Friendships** | Relationship CRM, last contact, birthdays, follow-ups | CoS |
| 7 | **Finance** | Central financial brain, cashflow + strategy | You + CoS |
| 8 | **Tax** | Year-round doc capture, German + Danish returns | Finance |
| 9 | **Real Estate** | Property portfolio, tenants, maintenance | Finance, Tax |
| 10 | **School** | CIS + Fernschule, schedules, pickups, academic tracking | CoS, Travel |
| 11 | **Life in Denmark** | Expat compliance, CPH apartment, CPR/MitID | CoS |
| 12 | **Car** | Car maintenance, TÜV, remote management | Finance |
| 13 | **Boat** | Maintenance, logistics, future live monitoring | Finance |
| 14 | **Travel** | Trip planning, conflict detection, family calendar | CoS, Calendar |
| 15 | **Health** | Family health, appointments, vaccinations | Finance, Insurance |
| 16 | **Insurance** | All policies, coverage gaps, renewals | Finance |
| 17 | **Dashboard Agent** | Reads dashboard DB, generates HTML, serves via Tailscale | You (browser) |

---

<a name="specs"></a>
## 📋 Agent Specs

---

### Agent 0: Chief of Staff (CoS) ⭐
*Most important agent in the system — the meta-layer that holds everything together*

The CoS holds the strategic view, filters the daily chaos, and actively guides what actually matters. Not a task manager — a thinking partner that applies GTD + OKRs + Covey Q2 in concert.

**Frameworks applied together:**
- **OKRs** — define where you're going (quarterly/annual goals with measurable outcomes). Also covers long-term strategy and ensures daily work stays aligned with bigger life goals.
- **Covey Q2** — protect time for important-but-not-urgent (the work that moves the needle but never screams)
- **GTD** — process the chaos reliably so nothing falls through cracks and your head stays clear

**The full flow:**
```
All inputs (email, WhatsApp, agent alerts, manual)
          ↓
    [ SINGLE RAW INBOX ]
          ↓
    CoS: GTD Layer 1 — quick scan
    ├── Can do in 2 min? → confirm with Alexander → do / archive
    ├── Not relevant? → hold for batched review
    └── Needs more thought? → route to domain agent inbox
                              (forward_count + 1)
          ↓
    [ DOMAIN AGENT INBOXES ]
          ↓
    Domain agent analysis → QUALIFIED TODO
    (project, context, next flag, energy, waiting-for,
     deadline, OKR tag, confidence level)
          ↓
    [ SINGLE QUALIFIED TODO LIST ]
          ↓
    CoS: Strategic Layer
    ├── OKR alignment check
    ├── Long-term goal alignment
    ├── Covey quadrant classification
    ├── Priority & sequencing across ALL domains
    └── Concrete next steps proposed (with confidence)
          ↓
    [ ALEXANDER'S APPROVAL ]
          ↓
    Execution
```

**GTD Layer 1 — Raw Inbox Processing:**
- Actions with no external effect (archive, file, note) → CoS handles autonomously at high confidence
- Actions with external effect (send message, make booking) → confirm with Alexander first
- *Early phase: also confirm archiving* until confidence rises

**Batched micro-review (human-friendly):**
- CoS does NOT interrupt constantly
- Holds pending low-priority items in a review queue
- Learns habits — detects good moments (low-message periods, known free times)
- Says: *"Hey, got a few minutes? I have [N] quick items to run through."*
- Presents one by one: summary + suggestion + confidence → brief ok/reject/redirect
- Records every decision to build confidence over time
- Automation increases progressively per category as patterns solidify

**CoS Strategic Layer:**
- Only agent with full cross-domain view
- Applies Covey quadrants: classifies by urgency × importance
- Actively protects Q2 time — schedules it, defends it, flags crowding
- Challenges Q1 escalations: *"This feels urgent — was it avoidable? Is it truly important?"*
- Checks OKR alignment: *"This task serves no current OKR — worth doing?"*
- Tracks long-term goals and flags when daily drift is taking you off course
- Proposes concrete next steps with context + confidence level
- Presents to Alexander for approval before any execution

**Weekly GTD review (CoS-led):**
- Process stuck/overdue items
- Review all active projects
- Update OKR progress
- Reflect: did time allocation match stated priorities?
- Suggest OKR adjustments if reality keeps diverging

**What makes this hard (honest):**
- Only as good as the OKRs. Vague goals = vague prioritisation. OKR onboarding is the most critical first step.
- Needs to be opinionated — it should push back, not just list
- Learning loop requires consistent feedback over time — not smart on day one
- Requires Infrastructure Agent to set up raw inbox first

---

### Agent 1: Infrastructure Agent

Sets up the OC environment properly from scratch.
- Guides through full OC setup process
- Makes best-practice recommendations based on goals
- Assists with config, node pairing, skill setup
- Prerequisites other agents — should be built first

---

### Agent 2: Monitoring Agent

Continuously watches the system and all its components.
- Proactive alerting — catches issues *before* they become outages
- Covers all OC components (gateway, nodes, plugins, connectivity)
- Makes recommendations when something looks off
- **Message queue monitoring** — watches the SQLite bus: messages processing? anything stuck? queue depth growing unexpectedly? alerts if a domain agent has stopped consuming its messages
- *Open question: same agent as Infrastructure, or separate? Related but different jobs — setup vs. ongoing health*

---

### Agent 3: Comms Collector

Ingests all input channels, normalises, and routes to the SQLite bus.
- Fetches from Gmail, WhatsApp, and scanned letters
- OCR processing for scanned letters before ingestion
- Extracts: sender, subject, body, attachments
- Normalises into standard internal format
- Tags domain where confident; leaves null where uncertain
- Writes to SQLite message bus with full reply_context

**reply_context field — key design element:**
Every message carries full reply information all the way to execution. Source is never lost.
- **Gmail** → thread_id + sender email → replies in same Gmail thread
- **WhatsApp** → chat_id + phone number → sends WhatsApp reply
- **Scanned letter** → filename + sender postal address → drafts letter response

**Scanned letters — special handling:**
- OCR runs before processing; extracted text enters flow identically to email/WhatsApp
- reply_context includes postal address for responses
- Original scan preserved as attachment reference

---

### Agent 4: Inbox Manager Agent

Handles messages not claimed by any domain agent.
- General email triage, inbox zero, action suggestions
- Follow-up tracking — things awaiting a response
- Reads from SQLite bus (untagged / general messages)
- Works across all input channels via reply_context

---

### Agent 5: Calendar Agent *(to be added — design pending)*

Owns scheduling across the whole family system.
- Single source of truth for all calendar events
- Blocks and defends Q2 time (works with CoS)
- Prevents double-booking across all agent recommendations
- Manages meeting scheduling
- School-calendar-aware (links to School Agent)
- Travel-aware (links to Travel Agent)
- Surfaces free windows for proactive planning
- *Question: which calendar system to integrate with?*

---

### Agent 6: Friendships Agent

Personal relationship manager — keeps friendships alive and intentional.
- Tracks last contact date per person, nudges when too long
- Follow-up reminders with context ("last time you talked about X")
- Birthday tracking — reminders ahead of time + list of missing birthdays
- Friend categories: close friends / regular friends / business friends
- Could suggest conversation starters based on what you know about them
- *Question: data source — manual entry, phone contacts, messaging history?*

---

### Agent 7: Finance Agent

Central financial brain — the only agent with full financial picture.

**Operational:**
- Tracks income, expenses, cashflow
- Flags unusual spending or shortfalls early
- Warns of upcoming threats (bills, renewals, cash crunches)

**Strategic:**
- Tracks financial goals and progress
- Maintains projections and scenarios
- Surfaces optimisation opportunities (savings, tax, subscriptions)
- Proactive strategy recommendations

**Receives from:** Real Estate, Tax, Car, Boat, Insurance (running costs and summaries)
- *Question: data sources — bank feeds, manual, CSV, accounting tools?*
- *Question: personal finances, business, or both?*

---

### Agent 8: Tax Agent

Year-round tax companion — eliminates the annual document scramble.

**Ongoing:**
- Captures and tags tax-relevant documents as they arrive
- Tracks events that will matter at tax time
- Everything findable instantly — no year-end treasure hunt

**Annual return season:**
- Guides through required documents
- Reminds of what's missing
- Optimises for best outcome (deductions, allowances)
- Tracks deadlines

**Cross-border complexity (key requirement):**
- 🇩🇪 German taxes: real estate ownership, rental income, German obligations (ELSTER)
- 🇩🇰 Danish taxes: temporary residency while working in Denmark (TastSelv)
- Dual tax residency rules, what to declare where, avoiding double taxation
- Tracks when Danish tax relevance ends

- *Question: integrate with Steuerberater or fully self-serve?*

---

### Agent 9: Real Estate Agent

Portfolio manager for owned properties.

**Portfolio overview:**
- Tracks all properties, ownership structure (sole vs. joint with Tanja)
- Long-term investment lens — retirement planning context
- Valuations, mortgage status, equity development

**Financial layer (feeds Finance Agent):**
- Rental income per property
- Expense tracking (repairs, maintenance, insurance, property tax)
- Summarised output to Finance — Finance gets numbers, not management detail
- Feeds Tax Agent (rental income, deductible expenses, depreciation)

**Property management:**
- Tenant tracking (lease dates, rent amounts, renewals)
- Maintenance & repair task lists per property
- Document storage (contracts, insurance, inspection reports, tenant agreements)
- Recurring obligation reminders (inspections, renewals)
- Flags issues before they become expensive

- *Question: how are properties currently tracked?*
- *Question: properties all in Germany, or elsewhere too?*

---

### Agent 10: School Agent

Education coordinator for 9-year-old twins across two school systems.

**The two schools:**
- 🇩🇰 **CIS Copenhagen** — primary day school
- 🇩🇪 **Fernschule** — German distance school, keeps language & curriculum on track

**Schedule & logistics:**
- Daily schedule per child (can differ between twins)
- Monitors schedule change announcements for that specific day
- Pickup reminders dynamically adjusted to actual schedule
- Flags early pickups, special events, no-school days in advance

**Academic & wellbeing:**
- Tracks progress per child
- Teacher communications (notes, follow-ups)
- Flags concerns, makes recommendations
- Helps prepare for parent-teacher meetings

**Admin & documents:**
- Announcements, permission slips, event registrations
- Deadlines (Fernschule submissions, CIS events)
- Document storage per child

- *Note: twins = two individuals — some things overlap, some don't*
- *Question: how do CIS and Fernschule communicate? (app/email/portal) — integration point*

---

### Agent 11: Life in Denmark Agent

Expat compliance & life management for the Copenhagen chapter.

**Who it covers:**
- Alexander + twins (living in CPH)
- Tanja (Germany-based, visits occasionally) — different obligations, tracked separately

**Legal & compliance:**
- CPR numbers — status, update requirements
- MitID — validity, linked accounts, expiry *(critical — expiry locks out banking, tax, public services)*
- Residence permits / registration certificates — deadlines, renewals
- Work permit / EU freedom of movement status
- Proactive reminders well ahead of deadlines
- Flags things as situation evolves (e.g. when Danish stay winds down)

**CPH apartment (rented):**
- Lease tracking (end date, notice periods, rent reviews) *(missing notice period can cost months of rent)*
- Utility contracts, insurance
- Tenant maintenance obligations
- Move-in/move-out documentation

**Practical expat life:**
- Danish healthcare registration (sygesikringsbevis), læge registration
- Danish driving licence requirements if applicable
- TastSelv filing deadlines
- General foreign resident obligations

**Tanja's situation:**
- Visit-related considerations — *(long stays 180+ days can trigger unexpected Danish tax/registration obligations)*
- Flags anything she needs to be aware of when visiting

- *Note: this agent has a natural end date — when leaving Denmark, it transitions/archives*
- *Integrates closely with: Tax Agent (Danish residency rules), Real Estate Agent (German home base)*

---

### Agent 12: Car Agent

Keeps the car running smoothly from a distance.

**Situation:** car based in Stadtlohn, not brought to Denmark for cost reasons — managed remotely.

**Maintenance & status:**
- Proactive reminders for scheduled maintenance
- Tracks repair history and current status
- German requirements:
  - 🔴 HU (Hauptuntersuchung / TÜV) — biannual roadworthiness inspection
  - 🔴 AU (Abgasuntersuchung) — emissions check
  - Kfz-Steuer if not on direct debit
  - Insurance renewal
- Flags when unused for extended period (battery, tyres)

**Documents:** Fahrzeugschein, insurance policy, service records

- *Question: one car or more?*
- *Question: does Tanja use it regularly while Alexander is in Denmark?*

---

### Agent 13: Boat Agent

Full lifecycle manager for a 25-year-old larger boat (Harderwijk, NL). Used for weekends and summer trips.

**Maintenance (critical given age):**
- Full maintenance history per system (engines, electrical, hull, rigging)
- Proactive scheduled service reminders
- Winterization / summerization checklists
- Age-aware: surfaces things typical for boats of this vintage
- Flags overdue items before they become failures at sea

**Safety equipment (non-optional):**
- Flare expiry tracking
- Life raft service schedule
- EPIRB registration
- Other safety cert expiry

**Logistics:**
- Marina/mooring details, contracts, fees
- Registration, flag state, insurance
- Seasonal planning (launch, haul-out, winter storage)
- Crew/guest coordination

**Live monitoring (Phase 2 — future):**
- Battery bank status & charging
- Electrical system health
- Engine hours, temperature, oil pressure
- Bilge levels
- GPS track & route logging
- Remote alerts when unattended

**Documents:** purchase records, manuals, insurance, repair invoices

- *Question: what monitoring hardware is already on board? Determines Phase 2 timeline*

---

### Agent 14: Travel Agent

Proactive travel planner and conflict manager for a family spread across multiple locations.

**Regular routes:**
- CPH → Berlin — visiting friends (frequent)
- CPH → Stadtlohn — visiting Tanja's parents + car access
- CPH → Harderwijk, NL — boat trips (weekends + summer)
- Business trips — Alexander's and Tanja's (various)

**Conflict detection:**
- Tracks both Alexander's and Tanja's travel calendars
- Flags conflicts proactively (both away = kids uncovered, business trips clashing)
- School-calendar-aware — no travel on pickup days without a plan
- Tracks Tanja's CPH visits vs. Alexander's travel

**Proactive planning:**
- Suggests windows based on calendars + weather
- Reminds to book ahead for busy periods
- Boat trip planning — weather windows, route suggestions (links to Boat Agent)
- Tracks car availability in Stadtlohn

**Logistics:**
- Preferred transport per destination
- Packing list templates per trip type
- Accommodation tracking for recurring stays
- Travel documents — passports, expiry, kids' documents

- *Question: which calendar system to integrate with?*
- *Question: actively search/book transport, or plan and remind only?*

---

### Agent 15: Health Agent

Family health tracker — covers all four family members individually.

**Who it covers:** Alexander, Tanja, and the twins (each tracked separately)

**Medical records:**
- GP/doctor registrations in Denmark and Germany
- Key health history per person
- Ongoing medications or treatments

**Appointments:**
- Upcoming appointments (GP, dentist, specialists)
- Advance reminders
- Past appointment log and outcomes

**Preventive care:**
- Vaccination schedules (especially for kids — international school requirements)
- Routine checkups, dental, eye tests
- Flags overdue items

**Kids-specific:**
- Pediatrician history
- School health requirements (vaccinations, medical forms)
- Development notes if useful

**Cross-border:**
- Danish system (sygesikring, læge) vs. German system (Krankenkasse)
- Who is covered where and under what
- Links to Insurance Agent for coverage details

- *Question: Tanja's German health insurance vs. Danish coverage for Alexander?*
- *Question: kids on Danish or German coverage, or both?*

---

### Agent 16: Insurance Agent

Single overview of all insurance policies — coverage, costs, and gaps.

**Policies tracked:**
- 🏠 Real estate — each property (building, contents, liability)
- 🚗 Car — vehicle insurance, breakdown
- ⛵ Boat — hull, liability, equipment
- 🏥 Health — family coverage DK + DE
- 👨‍👩‍👧 Life / disability
- 🧳 Travel insurance
- Other liability / personal policies

**Per policy:**
- Provider, policy number, coverage summary
- Annual cost
- Renewal date + proactive reminder
- What's covered AND what's NOT (gaps)

**Proactive features:**
- Renewal reminders — no auto-renewals sneaking through
- Coverage gap analysis — flags underinsured situations
- Cost optimisation — flags expensive-for-coverage policies
- Life event alerts (new property, new trip → review coverage)

**Feeds into:** Finance Agent (annual insurance costs)

- *Question: policies currently stored where? PDFs, emails, paper?*
- *Question: broker or direct with insurers?*

---

<a name="dashboard"></a>
## 📊 Dashboard System

### Architecture Overview

Three moving parts working together:
1. **Dashboard SQLite DB** — CoS writes prioritised status data; single source of truth for the dashboard
2. **Dashboard Agent** — reads the DB, generates the HTML dashboard and all agent detail pages
3. **Tailscale-only web server** — serves the HTML; reachable only within the private Tailscale network

```
[ DOMAIN AGENTS ]
  Each writes status/alerts to their domain
        ↓
[ CoS ]
  Decides what gets surfaced and at what priority
  Writes to Dashboard SQLite DB
        ↓
[ DASHBOARD SQLITE DB ]
  Single source of truth for all dashboard content
        ↓
[ DASHBOARD AGENT ]
  Reads DB, generates HTML files
  - index.html (main overview)
  - [agent].html (per-agent detail pages)
  Follows CoS-defined page structure guidelines
        ↓
[ TAILSCALE WEB SERVER ]
  Serves static HTML
  Only reachable within Tailscale network
  No auth complexity — Tailscale membership IS the auth
        ↓
[ ANY DEVICE ON TAILSCALE ]
  Phone, tablet, desktop — same URL, always current
```

### Dashboard SQLite DB Schema

CoS is the sole writer — it decides what from each domain gets surfaced and at what priority.

```sql
-- Main status/alert feed
dashboard_items (
  id, created_at, updated_at,
  agent,           -- which domain agent this came from
  category,        -- today / upcoming / alert / info
  priority,        -- 1 (critical) to 5 (low) — set by CoS
  title,           -- short headline
  body,            -- detail text
  due_at,          -- deadline if applicable
  action_required, -- bool: needs Alexander's input?
  link,            -- link to agent detail page if relevant
  status           -- active / acknowledged / done
)

-- Per-agent last-updated timestamps (for staleness detection)
agent_heartbeats (
  agent, last_updated_at, status  -- ok / warning / error
)
```

### Dashboard Agent

Dedicated agent responsible for HTML generation only — reads DB, writes files.

**Main dashboard (index.html):**
- Today section — urgent / action-required items at top
- Upcoming section — next 7–30 days, sorted by priority
- Agent status row — all agents shown with last-updated + health indicator
- Links to each agent's detail page
- Auto-refreshes periodically (simple meta refresh or JS)
- Self-contained HTML — no external CDN dependencies, works offline within Tailscale

**Per-agent detail pages ([agent].html):**
- Each domain agent must generate its own detail page content
- Dashboard Agent assembles these into a consistent shell
- Linked from main dashboard agent status row

### CoS Page Structure Guidelines

CoS defines the standard structure all agent detail pages must follow — Dashboard Agent enforces it.

```
[ AGENT DETAIL PAGE STRUCTURE ]

1. Header
   - Agent name + last updated timestamp
   - Health status indicator (green / amber / red)
   - One-line status summary

2. Alerts & Actions (if any)
   - Items requiring attention, highest priority first
   - Each with: title, detail, due date, action button/link

3. Current Status
   - Domain-specific snapshot (e.g. Finance: cashflow summary;
     School: today's schedule; Boat: next maintenance due)

4. Upcoming (next 30 days)
   - Deadlines, events, reminders for this domain

5. Recent Activity
   - Last N actions/events logged by this agent

6. Documents / Reference (optional)
   - Links to relevant stored documents for this domain
```

### Tailscale Web Server

- Simple static file server (e.g. `python3 -m http.server` or `caddy` or `nginx`)
- Bound to Tailscale interface only — not exposed to public internet
- Tailscale membership = access control. No passwords, no certs needed internally.
- Dashboard Agent writes HTML to a watched directory; server serves it immediately
- Accessible from any device on the Tailscale network (phone, tablet, desktop) via simple URL e.g. `http://hostname.tail.net/dashboard/`
- Potential: permanent home screen on a tablet or always-on display

### Dashboard Output Standard (system-wide)
Every domain agent must provide structured data for:
1. **CoS consumption** — status, alerts, priorities (CoS decides what reaches dashboard DB)
2. **Detail page content** — their own `[agent].html` content block following CoS page structure guidelines

No agent spec is complete without both defined.

---

<a name="comms"></a>
## 📬 Message Flow & Communications Architecture

### Input Sources
Three primary channels, all normalised by Comms Collector before anything else touches them:
- 📧 **Gmail** — email threads
- 📱 **WhatsApp** — chat messages
- 📄 **Scanned letters** — physical mail, OCR-processed before entering flow

### End-to-End Flow

```
[ INPUT SOURCES ]
   📧 Gmail       📱 WhatsApp      📄 Scanned letters
        \               |                /
         \              |               /
      [ COMMS ROUTER ]
      - Fetches from each source
      - OCR for scanned letters
      - Extracts: sender, subject, body, attachments
      - Normalises to standard internal format
      - Tags domain where confident
      - Writes to SQLite message bus
              |
              ↓
    [ SQLITE MESSAGE BUS ]
    Fields: id, source_channel, source_id, source_address,
            sender_name, timestamp_received, subject, body,
            attachments[], forward_count, domain_tag, status,
            processed_by[], reply_context
              |
              ↓
      [ CoS — GTD Layer 1 ]
      Reads bus, processes, routes
              |
      ┌───────┴──────────────────┐
      ↓                          ↓
[ DOMAIN AGENT INBOXES ]    [ CoS direct ]
  (forward_count + 1)       (unmatched — discussed
                              with Alexander)
      |
      ↓
  Domain agent qualifies →
  creates QUALIFIED TODO
  (all source fields + reply_context preserved)
      |
      ↓
[ QUALIFIED TODO LIST ]
      |
      ↓
  [ CoS — Strategic Layer ]
  Prioritises, sequences, proposes action
      |
      ↓
  [ ALEXANDER APPROVES ]
      |
      ↓
  [ EXECUTION ]
  Comms Collector uses reply_context to
  respond via correct original channel
```

### reply_context — Key Design Element
Source is never lost, even after routing through multiple agents:
- **Gmail** → thread_id + sender email → reply in same thread
- **WhatsApp** → chat_id + phone number → WhatsApp reply
- **Scanned letter** → filename + postal address → draft letter response

### Routing Model
1. **Comms Collector** — ingests, normalises, tags by domain, writes to bus
2. **Domain agents** — query bus for their tagged messages, process with full domain knowledge
3. **Inbox Manager Agent** — handles untagged / general messages
4. **CoS** — handles truly ambiguous items directly with Alexander

### Why SQLite?
- Zero infrastructure — single local file
- WAL mode = safe concurrent reads/writes
- Fully inspectable with any SQLite viewer
- Survives restarts
- Right scale for personal use
- Migration path to PostgreSQL if ever needed (schema unchanged)
