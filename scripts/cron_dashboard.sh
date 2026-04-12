#!/bin/bash
# Dashboard regeneration — runs every 15 minutes
# Called directly by cron, no AI agent involved
set -e
python3 /home/node/.openclaw/workspace/agents/cos/scripts/update_status.py >> /home/node/.openclaw/workspace/logs/dashboard-cron.log 2>&1
python3 /home/node/.openclaw/workspace/agents/dashboard/scripts/generate.py >> /home/node/.openclaw/workspace/logs/dashboard-cron.log 2>&1
