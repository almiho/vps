#!/bin/bash
# Push workspace to server/openclaw/ on GitHub main branch
# Handles nested git repos in agents/ directories

set -e
cd /home/node/.openclaw/workspace

MSG="${1:-AlexI workspace sync: $(date '+%Y-%m-%d %H:%M')}"

# Remove cached nested repo reference if present
git rm --cached agents/infrastructure 2>/dev/null || true

# Add .gitignore for nested repos
cat > .gitignore << 'GITIGNORE'
# SQLite databases
data/*.db
data/*.db-wal
data/*.db-shm
# Logs and media
logs/
media/
# Nested git repos — track files, not repos
agents/infrastructure/.git
agents/*/. git
GITIGNORE

git add -A
git diff --cached --quiet || git commit -m "$MSG (local)"

git fetch origin main
git checkout -b push-temp origin/main 2>/dev/null || (git checkout master && git branch -D push-temp 2>/dev/null; git checkout -b push-temp origin/main)

git read-tree --prefix=server/openclaw/ -u master
git commit -m "$MSG" || echo "Nothing new to push"
git push origin push-temp:main
git checkout master
git branch -D push-temp
echo "✅ Pushed to github.com/almiho/vps server/openclaw/"
