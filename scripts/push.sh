#!/bin/bash
# Push workspace to server/openclaw/ on GitHub main branch
# Uses a temp directory completely outside the workspace to avoid pollution
set -e

WORKSPACE="/home/node/.openclaw/workspace"
MSG="${1:-AlexI workspace sync: $(date '+%Y-%m-%d %H:%M')}"

# Work in /tmp — completely outside workspace
TMPDIR=$(mktemp -d /tmp/alexi-push-XXXXXX)
trap "rm -rf $TMPDIR" EXIT

cd "$TMPDIR"
git clone git@github.com:almiho/vps.git repo
cd repo

# Clear and repopulate server/openclaw/
rm -rf server/openclaw
mkdir -p server/openclaw

# Copy project files (explicit list — no system dirs, no DBs, no logs)
for item in \
  AGENTS.md AGENT_STANDARDS.md IDENTITY.md INFRA_AGENT.md \
  IDEAS.md STATUS.md SOUL.md TOOLS.md USER.md HEARTBEAT.md \
  .gitignore docs agents dashboard scripts; do
  [ -e "$WORKSPACE/$item" ] && cp -r "$WORKSPACE/$item" "server/openclaw/"
done

git add server/openclaw/
if git diff --cached --quiet; then
  echo "Nothing new to push"
  exit 0
fi

git commit -m "$MSG"
git push origin main
echo "✅ Pushed to github.com/almiho/vps server/openclaw/"
