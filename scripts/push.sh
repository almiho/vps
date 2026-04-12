#!/bin/bash
# Push workspace to server/openclaw/ on GitHub main branch
set -e

WORKSPACE="/home/node/.openclaw/workspace"
MSG="${1:-AlexI workspace sync: $(date '+%Y-%m-%d %H:%M')}"

TMPDIR=$(mktemp -d /tmp/alexi-push-XXXXXX)
trap "rm -rf $TMPDIR" EXIT

cd "$TMPDIR"
git clone git@github.com:almiho/vps.git repo
cd repo

rm -rf server/openclaw
mkdir -p server/openclaw

# Copy files — strip all nested .git directories
for item in \
  AGENTS.md AGENT_STANDARDS.md IDENTITY.md INFRA_AGENT.md \
  IDEAS.md STATUS.md SOUL.md TOOLS.md USER.md HEARTBEAT.md \
  .gitignore docs agents dashboard scripts; do
  src="$WORKSPACE/$item"
  if [ -e "$src" ]; then
    cp -r "$src" "server/openclaw/"
    # Remove any nested .git dirs in the copy
    find "server/openclaw/$item" -name ".git" -type d -exec rm -rf {} + 2>/dev/null || true
  fi
done

git add server/openclaw/
if git diff --cached --quiet; then
  echo "Nothing new to push"
  exit 0
fi

git commit -m "$MSG"
git push origin main
echo "✅ Pushed to github.com/almiho/vps server/openclaw/"
