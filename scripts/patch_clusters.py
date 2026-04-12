#!/usr/bin/env python3
import re

path = "/home/node/.openclaw/workspace/agents/dashboard/scripts/generate.py"
with open(path) as f:
    content = f.read()

# 1. Add cluster CSS after .agents-grid
cluster_css = """
/* Cluster grouping on homepage */
.cluster-section { margin-bottom: 1.25rem; }
.cluster-section:last-child { margin-bottom: 0; }
.cluster-label { font-size: 0.72rem; font-weight: 600; color: #475569; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 0.6rem; padding-left: 2px; border-bottom: 1px solid #1e293b; padding-bottom: 0.4rem; }
"""
content = content.replace(".agents-grid {", cluster_css + ".agents-grid {", 1)

# 2. Add AGENT_CLUSTERS definition after AGENTS list
clusters_def = '''
# Clustered agent groups for homepage (same grouping as architecture diagram)
AGENT_CLUSTERS = [
    ("System", [
        ("cos", "Chief of Staff", "\U0001f9e0"),
        ("infrastructure", "Infrastructure", "\U0001f527"),
        ("monitoring", "Monitoring", "\U0001f441\ufe0f"),
        ("dashboard", "Dashboard", "\U0001f4ca"),
    ]),
    ("Communications", [
        ("comms-collector", "Comms Collector", "\U0001f4e8"),
        ("inbox-manager", "Inbox Manager", "\U0001f4ec"),
        ("calendar", "Calendar", "\U0001f4c5"),
    ]),
    ("Finance & Assets", [
        ("finance", "Finance", "\U0001f4b0"),
        ("real-estate", "Real Estate", "\U0001f3e0"),
        ("tax", "Tax", "\U0001f4cb"),
        ("insurance", "Insurance", "\U0001f6e1\ufe0f"),
    ]),
    ("Family & Life", [
        ("school", "School", "\U0001f392"),
        ("life-in-denmark", "Life in Denmark", "\U0001f1e9\U0001f1f0"),
        ("health", "Health", "\U0001f3e5"),
        ("friendships", "Friendships", "\U0001f465"),
    ]),
    ("Vehicles & Movement", [
        ("car", "Car", "\U0001f697"),
        ("boat", "Boat", "\u26f5"),
        ("travel", "Travel", "\u2708\ufe0f"),
    ]),
]
'''

# Insert after AGENTS list closes
content = content.replace(
    "]\n\n# About section content per agent",
    "]\n" + clusters_def + "\n# About section content per agent",
    1
)

# 3. Replace the agents_html loop in generate_index with clustered version
old = '''    agents_html = ""
    for agent_id, label, emoji in AGENTS:
        s = agent_statuses.get(agent_id, {})
        health = s.get("health","unknown")
        agents_html += f\'<a href="{agent_id}.html" class="agent-card health-{health}"><div class="agent-emoji">{emoji}</div><div class="agent-info"><div class="agent-name">{label} {health_badge(health)}</div><div class="agent-summary">{s.get("summary","Not yet active")}</div><div class="agent-updated">Updated: {format_time(s.get("updated_at"))}</div></div></a>\'

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<meta http-equiv="refresh" content="900"><title>AlexI Dashboard</title><style>{CSS}</style></head>
<body>
<div class="header"><h1>\U0001f91d AlexI Dashboard</h1><div class="header-meta">Updated {now} \xb7 Auto-refreshes every 15 min</div></div>
<div class="container">
  <div class="grid">
    <div class="section"><div class="section-title">\U0001f534 Needs Attention</div>{alerts_html}</div>
    <div class="section"><div class="section-title">\U0001f4c5 Upcoming</div>{upcoming_html}</div>
  </div>
  <div class="section"><div class="section-title">\U0001f916 Agent Status</div><div class="agents-grid">{agents_html}</div></div>
</div></body></html>"""'''

idx = content.find('    agents_html = ""\n    for agent_id, label, emoji in AGENTS:')
if idx < 0:
    print("Could not find agents_html loop")
else:
    # Find the end of the return statement
    end_marker = '</div></body></html>"""'
    end_idx = content.find(end_marker, idx) + len(end_marker)
    
    new_block = '''    # Build clustered agent grid
    clusters_html = ""
    for cluster_name, cluster_agents in AGENT_CLUSTERS:
        cards = ""
        for agent_id, label, emoji in cluster_agents:
            s = agent_statuses.get(agent_id, {})
            health = s.get("health","unknown")
            cards += (f\'<a href="{agent_id}.html" class="agent-card health-{health}">\'
                     f\'<div class="agent-emoji">{emoji}</div>\'
                     f\'<div class="agent-info">\'
                     f\'<div class="agent-name">{label} {health_badge(health)}</div>\'
                     f\'<div class="agent-summary">{s.get("summary","Not yet active")}</div>\'
                     f\'<div class="agent-updated">Updated: {format_time(s.get("updated_at"))}</div>\'
                     f\'</div></a>\')
        clusters_html += (f\'<div class="cluster-section">\'
                         f\'<div class="cluster-label">{cluster_name}</div>\'
                         f\'<div class="agents-grid">{cards}</div>\'
                         f\'</div>\')

    return (\'<!DOCTYPE html>\\n\'
            \'<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">\\n\'
            f\'<meta http-equiv="refresh" content="900"><title>AlexI Dashboard</title><style>{CSS}</style></head>\\n\'
            \'<body>\\n\'
            f\'<div class="header"><h1>\\U0001f91d AlexI Dashboard</h1><div class="header-meta">Updated {now} \\xb7 Auto-refreshes every 15 min</div></div>\\n\'
            f\'<div class="container">\\n\'
            f\'  <div class="grid">\\n\'
            f\'    <div class="section"><div class="section-title">\\U0001f534 Needs Attention</div>{alerts_html}</div>\\n\'
            f\'    <div class="section"><div class="section-title">\\U0001f4c5 Upcoming</div>{upcoming_html}</div>\\n\'
            f\'  </div>\\n\'
            f\'  <div class="section"><div class="section-title">\\U0001f916 Agent Status</div>{clusters_html}</div>\\n\'
            \'</div></body></html>\')'''

    content = content[:idx] + new_block + content[end_idx:]
    print("Replaced agents section")

with open(path, 'w') as f:
    f.write(content)
print("Saved")
