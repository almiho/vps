#!/usr/bin/env python3
"""
AlexI Dashboard Server — no-cache static files + routing decision API.

Binds only to the explicitly configured addresses, by default:
- 127.0.0.1
- 100.67.100.125 (Tailscale)

Never bind to 0.0.0.0.
"""

import http.server
import json
import os
import signal
import sqlite3
import threading
import time
from datetime import datetime
from pathlib import Path

WORKSPACE = Path('/home/node/.openclaw/workspace')
BUS_DB = WORKSPACE / 'data' / 'bus.db'
FEEDBACK = WORKSPACE / 'agents' / 'inbox-manager' / 'data' / 'routing_feedback.json'
PENDING = WORKSPACE / 'dashboard' / 'data' / 'inbox_pending.json'
PORT = int(os.environ.get('DASHBOARD_PORT', '8080'))
BIND_ADDRS = [
    addr.strip()
    for addr in os.environ.get('DASHBOARD_BIND_ADDRS', '127.0.0.1,100.67.100.125').split(',')
    if addr.strip()
]


class ReusableThreadingHTTPServer(http.server.ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True


class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()

    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path == '/__healthz':
            self._json_response({'ok': True, 'bind_addrs': BIND_ADDRS, 'port': PORT})
            return

        # Serve /agents/... paths from workspace root (outside dashboard/ dir)
        if self.path.startswith('/agents/'):
            file_path = WORKSPACE / self.path.lstrip('/')
            file_path = Path(str(file_path).split('?')[0])
            if file_path.exists() and file_path.is_file():
                content = file_path.read_bytes()
                self.send_response(200)
                if str(file_path).endswith('.json'):
                    self.send_header('Content-Type', 'application/json')
                else:
                    self.send_header('Content-Type', 'text/plain')
                self.end_headers()
                self.wfile.write(content)
            else:
                self.send_response(404)
                self.end_headers()
            return

        super().do_GET()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body = json.loads(self.rfile.read(length)) if length else {}

        if self.path == '/api/route-decision':
            self._handle_route_decision(body)
        elif self.path == '/api/archive-message':
            self._handle_archive(body)
        else:
            self.send_response(404)
            self.end_headers()

    def _json_response(self, data, status=200):
        payload = json.dumps(data).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(payload)

    def _handle_route_decision(self, body):
        """Confirm routing: set domain_tag + status='tagged' on bus message, learn the sender."""
        bus_id = body.get('bus_message_id')
        domain_tag = body.get('domain_tag')
        original_from = body.get('original_from', '')

        if not bus_id or not domain_tag:
            self._json_response({'error': 'missing bus_message_id or domain_tag'}, 400)
            return

        now = datetime.now().isoformat(timespec='seconds')

        conn = sqlite3.connect(str(BUS_DB))
        conn.execute(
            "UPDATE messages SET status='processed', domain_tag=?, updated_at=? WHERE id=?",
            (domain_tag, now, bus_id),
        )

        original_id = body.get('original_id')
        if original_id:
            conn.execute(
                "UPDATE messages SET status='tagged', domain_tag=?, updated_at=? WHERE id=?",
                (domain_tag, now, original_id),
            )
        conn.commit()
        conn.close()

        if original_from:
            feedback = {}
            if FEEDBACK.exists():
                try:
                    feedback = json.loads(FEEDBACK.read_text())
                except Exception:
                    feedback = {}
            domain = original_from.split('@')[-1].split('.')[0] if '@' in original_from else original_from
            feedback.setdefault('learned_senders', {})[original_from] = {
                'domain_tag': domain_tag,
                'learned_at': now,
                'domain_hint': domain,
            }
            feedback['updated_at'] = now
            FEEDBACK.write_text(json.dumps(feedback, indent=2))

        self._remove_from_pending(bus_id)
        self._json_response({'ok': True, 'routed_to': domain_tag})

    def _handle_archive(self, body):
        bus_id = body.get('bus_message_id')
        if not bus_id:
            self._json_response({'error': 'missing bus_message_id'}, 400)
            return

        now = datetime.now().isoformat(timespec='seconds')
        conn = sqlite3.connect(str(BUS_DB))
        conn.execute("UPDATE messages SET status='archived', updated_at=? WHERE id=?", (now, bus_id))
        conn.commit()
        conn.close()
        self._remove_from_pending(bus_id)
        self._json_response({'ok': True})

    def _remove_from_pending(self, bus_id):
        try:
            data = json.loads(PENDING.read_text())
            data['pending'] = [p for p in data.get('pending', []) if p.get('bus_message_id') != bus_id]
            data['updated_at'] = datetime.now().isoformat(timespec='seconds')
            PENDING.write_text(json.dumps(data, indent=2))
        except Exception:
            pass


def serve_forever(bind_addr: str, port: int, servers: list):
    httpd = ReusableThreadingHTTPServer((bind_addr, port), Handler)
    servers.append(httpd)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd, thread


def main():
    os.chdir('/home/node/.openclaw/workspace/dashboard')

    servers = []
    threads = []
    started = []
    failures = []

    for bind_addr in BIND_ADDRS:
        try:
            httpd, thread = serve_forever(bind_addr, PORT, servers)
            threads.append(thread)
            started.append(bind_addr)
            print(f"Dashboard server listening on http://{bind_addr}:{PORT}/", flush=True)
        except Exception as e:
            failures.append((bind_addr, str(e)))
            print(f"Dashboard server failed on {bind_addr}:{PORT} -> {e}", flush=True)

    if not started:
        raise SystemExit(f"Dashboard server could not bind to any address: {failures}")

    stop_event = threading.Event()

    def shutdown(*_args):
        for server in servers:
            try:
                server.shutdown()
                server.server_close()
            except Exception:
                pass
        stop_event.set()

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    try:
        while not stop_event.is_set():
            time.sleep(0.5)
    finally:
        shutdown()


if __name__ == '__main__':
    main()
