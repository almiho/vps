#!/bin/bash
# Infrastructure environment check — runs every hour
# Called directly by cron, no AI agent involved
set -e
python3 /home/node/.openclaw/workspace/agents/infrastructure/scripts/env_check.py >> /home/node/.openclaw/workspace/logs/infra-check.log 2>&1
python3 /home/node/.openclaw/workspace/agents/dashboard/scripts/generate.py >> /home/node/.openclaw/workspace/logs/dashboard-cron.log 2>&1
