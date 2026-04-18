#!/usr/bin/env python3
"""
Memory sync — copies Claude auto-memory files into the git-tracked workspace/memory/
so they survive a VPS rebuild. Runs every 15 minutes via scheduler.py.

Source:  /home/node/.claude/projects/-home-node--openclaw-workspace/memory/
Target:  /home/node/.openclaw/workspace/memory/
"""

import os
import shutil
import subprocess
from datetime import datetime

SRC = "/home/node/.claude/projects/-home-node--openclaw-workspace/memory"
DST = "/home/node/.openclaw/workspace/memory"
WORKSPACE = "/home/node/.openclaw/workspace"


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] sync_memory: {msg}", flush=True)


def git(args, **kwargs):
    return subprocess.run(
        ["git", "-C", WORKSPACE] + args,
        capture_output=True, text=True, **kwargs
    )


def main():
    if not os.path.isdir(SRC):
        log(f"Source directory not found: {SRC} — skipping")
        return

    os.makedirs(DST, exist_ok=True)

    # Copy every file from source to destination
    copied = []
    for fname in os.listdir(SRC):
        src_path = os.path.join(SRC, fname)
        dst_path = os.path.join(DST, fname)
        if not os.path.isfile(src_path):
            continue
        shutil.copy2(src_path, dst_path)
        copied.append(fname)

    if not copied:
        log("No files to sync")
        return

    log(f"Synced: {', '.join(copied)}")

    # Check if git sees any changes in memory/
    status = git(["status", "--porcelain", "memory/"])
    if not status.stdout.strip():
        log("No git changes — already up to date")
        return

    # Stage and commit
    git(["add", "memory/"])
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    commit = git(["commit", "-m", f"Auto-sync memory files [{ts}]"])
    if commit.returncode != 0:
        log(f"Commit failed: {commit.stderr.strip()}")
        return

    log(f"Committed: {commit.stdout.strip()[:80]}")

    # Push
    push = git(["push"])
    if push.returncode == 0:
        log("Pushed to GitHub")
    else:
        log(f"Push failed (will retry next cycle): {push.stderr.strip()[:100]}")


if __name__ == "__main__":
    main()
