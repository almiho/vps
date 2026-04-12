#!/usr/bin/env python3
"""
Dashboard Generator — AlexI Project
Reads dashboard.db and agent status.json files, generates HTML dashboard.
"""

import sqlite3
import json
import os
from datetime import datetime

WORKSPACE = "/home/node/.openclaw/workspace"
DB_PATH = f"{WORKSPACE}/data/dashboard.db"
OUTPUT_DIR = f"{WORKSPACE}/dashboard"
AGENTS_DIR = f"{WORKSPACE}/agents"

AGENTS = [
    ("cos", "Chief of Staff", "🧠"),
    ("infrastructure", "Infrastructure", "🔧"),
    ("monitoring", "Monitoring", "👁️"),
    ("comms-router", "Comms Router", "📨"),
    ("comms-general", "General Comms", "📬"),
    ("calendar", "Calendar", "📅"),
    ("friendships", "Friendships", "👥"),
    ("finance", "Finance", "💰"),
    ("tax", "Tax", "📋"),
    ("real-estate", "Real Estate", "🏠"),
    ("school", "School", "🎒"),
    ("life-in-denmark", "Life in Denmark", "🇩🇰"),
    ("car", "Car", "🚗"),
    ("boat", "Boat", "⛵"),
    ("travel", "Travel", "✈️"),
    ("health", "Health", "🏥"),
    ("insurance", "Insurance", "🛡️"),
    ("dashboard", "Dashboard", "📊"),
]

def load_agent_status(agent_id):
    path = f"{AGENTS_DIR}/{agent_id}/dashboard/status.json"
    try:
        with open(path) as f:
            return json.load(f)
    except:
        return {
            "agent": agent_id,
            "health": "unknown",
            "summary": "No status available yet",
            "alerts": [],
            "upcoming": [],
            "updated_at": None
        }

def load_dashboard_items():
    try:
        db = sqlite3.connect(DB_PATH)
        db.row_factory = sqlite3.Row
        items = db.execute(
            "SELECT * FROM dashboard_items WHERE status='active' ORDER BY priority ASC, due_at ASC"
        ).fetchall()
        db.close()
        return [dict(i) for i in items]
    except:
        return []

def health_badge(health):
    colors = {"ok": "#22c55e", "warning": "#f59e0b", "error": "#ef4444", "unknown": "#94a3b8"}
    labels = {"ok": "OK", "warning": "⚠️", "error": "❌", "unknown": "?"}
    color = colors.get(health, "#94a3b8")
    label = labels.get(health, "?")
    return f'<span style="background:{color};color:white;padding:2px 8px;border-radius:12px;font-size:0.75rem;font-weight:600">{label}</span>'

def format_time(ts):
    if not ts:
        return "never"
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.strftime("%d %b %H:%M")
    except:
        return ts[:16] if ts else "never"

def generate_index(items, agent_statuses):
    now = datetime.now().strftime("%d %b %Y %H:%M")

    # Alerts section
    alerts_html = ""
    alert_items = [i for i in items if i["category"] in ("today", "alert") and i["action_required"]]
    if alert_items:
        for item in alert_items:
            alerts_html += f"""
            <div class="item alert-item">
                <div class="item-priority p{item['priority']}">P{item['priority']}</div>
                <div class="item-content">
                    <div class="item-title">{item['title']}</div>
                    <div class="item-meta">{item.get('agent','').upper()} · {item.get('body','')}</div>
                </div>
                {"<div class='action-badge'>Action needed</div>" if item['action_required'] else ""}
            </div>"""
    else:
        alerts_html = '<div class="empty-state">✅ No urgent items right now</div>'

    # Upcoming section
    upcoming_html = ""
    upcoming_items = [i for i in items if i["category"] == "upcoming"][:8]
    if upcoming_items:
        for item in upcoming_items:
            due = f" · Due {format_time(item.get('due_at'))}" if item.get('due_at') else ""
            upcoming_html += f"""
            <div class="item">
                <div class="item-priority p{item['priority']}">P{item['priority']}</div>
                <div class="item-content">
                    <div class="item-title">{item['title']}</div>
                    <div class="item-meta">{item.get('agent','').upper()}{due}</div>
                </div>
            </div>"""
    else:
        upcoming_html = '<div class="empty-state">Nothing upcoming logged yet</div>'

    # Agent status grid
    agents_html = ""
    for agent_id, label, emoji in AGENTS:
        status = agent_statuses.get(agent_id, {})
        health = status.get("health", "unknown")
        summary = status.get("summary", "Not yet active")
        updated = format_time(status.get("updated_at"))
        agents_html += f"""
        <a href="{agent_id}.html" class="agent-card health-{health}">
            <div class="agent-emoji">{emoji}</div>
            <div class="agent-info">
                <div class="agent-name">{label} {health_badge(health)}</div>
                <div class="agent-summary">{summary}</div>
                <div class="agent-updated">Updated: {updated}</div>
            </div>
        </a>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="refresh" content="60">
<title>AlexI Dashboard</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0f172a; color: #e2e8f0; min-height: 100vh; }}
  .header {{ background: #1e293b; padding: 1rem 1.5rem; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #334155; }}
  .header h1 {{ font-size: 1.25rem; font-weight: 700; color: #f1f5f9; }}
  .header-meta {{ font-size: 0.75rem; color: #64748b; }}
  .container {{ max-width: 1200px; margin: 0 auto; padding: 1.5rem; }}
  .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin-bottom: 1.5rem; }}
  @media (max-width: 768px) {{ .grid {{ grid-template-columns: 1fr; }} }}
  .section {{ background: #1e293b; border-radius: 12px; padding: 1.25rem; }}
  .section-title {{ font-size: 0.875rem; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 1rem; }}
  .item {{ display: flex; align-items: flex-start; gap: 0.75rem; padding: 0.75rem 0; border-bottom: 1px solid #334155; }}
  .item:last-child {{ border-bottom: none; }}
  .item-priority {{ font-size: 0.7rem; font-weight: 700; padding: 2px 6px; border-radius: 6px; white-space: nowrap; }}
  .p1 {{ background: #7f1d1d; color: #fca5a5; }}
  .p2 {{ background: #7c2d12; color: #fdba74; }}
  .p3 {{ background: #713f12; color: #fde68a; }}
  .p4 {{ background: #1e3a5f; color: #93c5fd; }}
  .p5 {{ background: #1e293b; color: #94a3b8; border: 1px solid #334155; }}
  .item-content {{ flex: 1; }}
  .item-title {{ font-size: 0.9rem; font-weight: 500; color: #f1f5f9; }}
  .item-meta {{ font-size: 0.75rem; color: #64748b; margin-top: 2px; }}
  .alert-item {{ background: rgba(239,68,68,0.05); border-radius: 8px; padding: 0.75rem !important; margin-bottom: 0.5rem; border-bottom: none !important; }}
  .action-badge {{ font-size: 0.7rem; background: #ef4444; color: white; padding: 2px 8px; border-radius: 12px; white-space: nowrap; }}
  .empty-state {{ color: #475569; font-size: 0.875rem; padding: 1rem 0; text-align: center; }}
  .agents-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 0.75rem; }}
  .agent-card {{ background: #1e293b; border-radius: 10px; padding: 1rem; display: flex; gap: 0.75rem; align-items: flex-start; text-decoration: none; color: inherit; border: 1px solid #334155; transition: border-color 0.15s; }}
  .agent-card:hover {{ border-color: #475569; }}
  .health-ok {{ border-left: 3px solid #22c55e; }}
  .health-warning {{ border-left: 3px solid #f59e0b; }}
  .health-error {{ border-left: 3px solid #ef4444; }}
  .health-unknown {{ border-left: 3px solid #475569; }}
  .agent-emoji {{ font-size: 1.5rem; line-height: 1; }}
  .agent-name {{ font-size: 0.875rem; font-weight: 600; color: #f1f5f9; display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; }}
  .agent-summary {{ font-size: 0.75rem; color: #64748b; margin-top: 3px; }}
  .agent-updated {{ font-size: 0.7rem; color: #475569; margin-top: 3px; }}
</style>
</head>
<body>
<div class="header">
  <h1>🤝 AlexI Dashboard</h1>
  <div class="header-meta">Updated {now} · Auto-refreshes every 60s</div>
</div>
<div class="container">
  <div class="grid">
    <div class="section">
      <div class="section-title">🔴 Needs Attention</div>
      {alerts_html}
    </div>
    <div class="section">
      <div class="section-title">📅 Upcoming</div>
      {upcoming_html}
    </div>
  </div>
  <div class="section">
    <div class="section-title">🤖 Agent Status</div>
    <div class="agents-grid">
      {agents_html}
    </div>
  </div>
</div>
</body>
</html>"""

def generate_agent_page(agent_id, label, emoji, status):
    now = datetime.now().strftime("%d %b %Y %H:%M")
    health = status.get("health", "unknown")
    summary = status.get("summary", "Not yet active")
    updated = format_time(status.get("updated_at"))

    alerts_html = ""
    for a in status.get("alerts", []):
        due = f" · Due {format_time(a.get('due_at'))}" if a.get('due_at') else ""
        alerts_html += f"""
        <div class="item alert-item">
            <div class="item-priority p{a['priority']}">P{a['priority']}</div>
            <div class="item-content">
                <div class="item-title">{a['title']}</div>
                <div class="item-meta">{a.get('body','')}{due}</div>
            </div>
            {"<div class='action-badge'>Action needed</div>" if a.get('action_required') else ""}
        </div>"""
    if not alerts_html:
        alerts_html = '<div class="empty-state">No alerts</div>'

    upcoming_html = ""
    for u in status.get("upcoming", []):
        due = f" · {format_time(u.get('due_at'))}" if u.get('due_at') else ""
        upcoming_html += f"""
        <div class="item">
            <div class="item-priority p{u['priority']}">P{u['priority']}</div>
            <div class="item-content">
                <div class="item-title">{u['title']}{due}</div>
            </div>
        </div>"""
    if not upcoming_html:
        upcoming_html = '<div class="empty-state">Nothing upcoming</div>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{label} — AlexI</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0f172a; color: #e2e8f0; }}
  .header {{ background: #1e293b; padding: 1rem 1.5rem; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #334155; }}
  .back {{ color: #64748b; text-decoration: none; font-size: 0.875rem; }}
  .back:hover {{ color: #94a3b8; }}
  .agent-header {{ display: flex; align-items: center; gap: 0.75rem; }}
  .agent-header h1 {{ font-size: 1.1rem; font-weight: 700; }}
  .container {{ max-width: 900px; margin: 0 auto; padding: 1.5rem; display: grid; gap: 1.5rem; }}
  .section {{ background: #1e293b; border-radius: 12px; padding: 1.25rem; }}
  .section-title {{ font-size: 0.875rem; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 1rem; }}
  .status-row {{ display: flex; gap: 1rem; align-items: center; flex-wrap: wrap; }}
  .status-summary {{ color: #cbd5e1; font-size: 0.9rem; }}
  .status-updated {{ color: #475569; font-size: 0.75rem; }}
  .item {{ display: flex; align-items: flex-start; gap: 0.75rem; padding: 0.75rem 0; border-bottom: 1px solid #334155; }}
  .item:last-child {{ border-bottom: none; }}
  .item-priority {{ font-size: 0.7rem; font-weight: 700; padding: 2px 6px; border-radius: 6px; white-space: nowrap; }}
  .p1 {{ background: #7f1d1d; color: #fca5a5; }} .p2 {{ background: #7c2d12; color: #fdba74; }}
  .p3 {{ background: #713f12; color: #fde68a; }} .p4 {{ background: #1e3a5f; color: #93c5fd; }}
  .p5 {{ background: #1e293b; color: #94a3b8; border: 1px solid #334155; }}
  .item-content {{ flex: 1; }}
  .item-title {{ font-size: 0.9rem; font-weight: 500; color: #f1f5f9; }}
  .item-meta {{ font-size: 0.75rem; color: #64748b; margin-top: 2px; }}
  .alert-item {{ background: rgba(239,68,68,0.05); border-radius: 8px; padding: 0.75rem !important; margin-bottom: 0.5rem; border-bottom: none !important; }}
  .action-badge {{ font-size: 0.7rem; background: #ef4444; color: white; padding: 2px 8px; border-radius: 12px; white-space: nowrap; }}
  .empty-state {{ color: #475569; font-size: 0.875rem; padding: 1rem 0; text-align: center; }}
  .not-active {{ text-align: center; padding: 3rem; color: #475569; }}
  .not-active .emoji {{ font-size: 3rem; margin-bottom: 1rem; }}
</style>
</head>
<body>
<div class="header">
  <a href="index.html" class="back">← Dashboard</a>
  <div class="agent-header">
    <span style="font-size:1.5rem">{emoji}</span>
    <h1>{label}</h1>
    {health_badge(health)}
  </div>
  <div style="font-size:0.75rem;color:#475569">{now}</div>
</div>
<div class="container">
  <div class="section">
    <div class="section-title">Status</div>
    <div class="status-row">
      <div class="status-summary">{summary}</div>
      <div class="status-updated">Last updated: {updated}</div>
    </div>
  </div>
  <div class="section">
    <div class="section-title">🔴 Alerts & Actions</div>
    {alerts_html}
  </div>
  <div class="section">
    <div class="section-title">📅 Upcoming</div>
    {upcoming_html}
  </div>
</div>
</body>
</html>"""

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    items = load_dashboard_items()
    agent_statuses = {}
    for agent_id, _, _ in AGENTS:
        agent_statuses[agent_id] = load_agent_status(agent_id)

    # Generate main index
    index_html = generate_index(items, agent_statuses)
    with open(f"{OUTPUT_DIR}/index.html", "w") as f:
        f.write(index_html)

    # Generate per-agent pages
    for agent_id, label, emoji in AGENTS:
        page_html = generate_agent_page(agent_id, label, emoji, agent_statuses[agent_id])
        with open(f"{OUTPUT_DIR}/{agent_id}.html", "w") as f:
            f.write(page_html)

    print(f"✅ Dashboard generated at {OUTPUT_DIR}/ ({len(AGENTS)+1} pages)")

if __name__ == "__main__":
    main()
