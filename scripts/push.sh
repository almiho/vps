#!/bin/bash
# Push workspace to server/openclaw/ on GitHub main branch
cd /home/node/.openclaw/workspace
git fetch origin main
git checkout -b push-temp origin/main
git read-tree --prefix=server/openclaw/ -u master
git commit -m "${1:-AlexI workspace sync: $(date '+%Y-%m-%d %H:%M')}"
git push origin push-temp:main
git checkout master
git branch -D push-temp
echo "✅ Pushed to github.com/almiho/vps server/openclaw/"
