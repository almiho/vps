#!/usr/bin/env python3
"""
Shared structured logger for all AlexI agents.

Usage:
    import sys; sys.path.insert(0, "/home/node/.openclaw/workspace/scripts")
    from agent_logger import AgentLogger

    log = AgentLogger("cos")
    log.info("run_start", "Beginning status update")
    log.warning("disk_high", "Disk at 82%", detail="82% used, 4.2G free")
    log.error("gateway_down", "RPC probe failed")

Log format (JSONL, one entry per line):
    {"timestamp": "2026-04-14T09:00:00", "agent": "cos", "level": "info",
     "event": "run_start", "message": "Beginning status update"}

Files: logs/[agent]/agent.log  (rolling, max 500 lines)
"""

import json, os
from datetime import datetime

WORKSPACE = "/home/node/.openclaw/workspace"
MAX_LINES = 500


class AgentLogger:
    LEVELS = ("debug", "info", "warning", "error", "critical")

    def __init__(self, agent_name: str):
        self.agent = agent_name
        self.path = f"{WORKSPACE}/logs/{agent_name}/agent.log"
        os.makedirs(os.path.dirname(self.path), exist_ok=True)

    def _write(self, level: str, event: str, message: str, **kwargs):
        entry = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "agent": self.agent,
            "level": level,
            "event": event,
            "message": message,
        }
        if kwargs:
            entry.update(kwargs)
        try:
            with open(self.path, "a") as f:
                f.write(json.dumps(entry) + "\n")
            self._rotate()
        except Exception:
            pass  # Never crash the agent just because logging failed

    def _rotate(self):
        """Keep only the last MAX_LINES entries."""
        try:
            with open(self.path) as f:
                lines = f.readlines()
            if len(lines) > MAX_LINES:
                with open(self.path, "w") as f:
                    f.writelines(lines[-MAX_LINES:])
        except Exception:
            pass

    def debug(self, event: str, message: str, **kw):
        self._write("debug", event, message, **kw)

    def info(self, event: str, message: str, **kw):
        self._write("info", event, message, **kw)

    def warning(self, event: str, message: str, **kw):
        self._write("warning", event, message, **kw)

    def error(self, event: str, message: str, **kw):
        self._write("error", event, message, **kw)

    def critical(self, event: str, message: str, **kw):
        self._write("critical", event, message, **kw)

    @staticmethod
    def read_recent(agent_name: str, n: int = 50) -> list:
        """Read the last n log entries for an agent, newest last."""
        path = f"{WORKSPACE}/logs/{agent_name}/agent.log"
        try:
            with open(path) as f:
                lines = f.readlines()
            entries = []
            for line in lines[-n:]:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except Exception:
                    pass
            return entries
        except Exception:
            return []

    @staticmethod
    def read_combined(agent_names: list, n: int = 30) -> list:
        """
        Read the last n log entries across multiple agents, merged by timestamp.
        Returns a list sorted newest-first.
        """
        all_entries = []
        for name in agent_names:
            all_entries.extend(AgentLogger.read_recent(name, n))
        all_entries.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
        return all_entries[:n]
