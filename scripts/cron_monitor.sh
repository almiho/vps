#!/bin/bash
# Monitoring Agent check — runs every 5 minutes
python3 /home/node/.openclaw/workspace/agents/monitoring/scripts/monitor.py >> /home/node/.openclaw/workspace/logs/monitor.log 2>&1
