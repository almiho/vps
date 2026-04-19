#!/usr/bin/env python3
"""
AlexI Dashboard Server — no-cache static files + routing decision API.
POST /api/route-decision  → confirm routing of a pending review message
POST /api/archive-message → archive a pending review message
"""
import http.server, os, json, sqlite3, uuid
from datetime import datetime
from pathlib import Path

WORKSPACE = Path('/home/node/.openclaw/workspace')
BUS_DB    = WORKSPACE / 'data' / 'bus.db'
FEEDBACK  = WORKSPACE / 'agents' / 'inbox-manager' / 'data' / 'routing_feedback.json'
PENDING   = WORKSPACE / 'dashboard' / 'data' / 'inbox_pending.json'

class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()

    def log_message(self, *a): pass

    def do_GET(self):
        # Serve /agents/... paths from workspace root (outside dashboard/ dir)
        if self.path.startswith('/agents/'):
            file_path = WORKSPACE / self.path.lstrip('/')
            # Strip query string
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
        # Default: serve from dashboard/ directory
        super().do_GET()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body   = json.loads(self.rfile.read(length)) if length else {}

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
        bus_id     = body.get('bus_message_id')
        domain_tag = body.get('domain_tag')
        original_from = body.get('original_from', '')

        if not bus_id or not domain_tag:
            self._json_response({'error': 'missing bus_message_id or domain_tag'}, 400)
            return

        now = datetime.now().isoformat(timespec='seconds')

        # 1. Update bus: mark CoS review message as processed
        conn = sqlite3.connect(str(BUS_DB))
        conn.execute("UPDATE messages SET status='processed', domain_tag=?, updated_at=? WHERE id=?",
                     (domain_tag, now, bus_id))

        # 2. Also tag the original message if we can find it
        original_id = body.get('original_id')
        if original_id:
            conn.execute("UPDATE messages SET status='tagged', domain_tag=?, updated_at=? WHERE id=?",
                         (domain_tag, now, original_id))
        conn.commit()
        conn.close()

        # 3. Learn: save sender → domain mapping to routing_feedback.json
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

        # 4. Remove from pending JSON
        self._remove_from_pending(bus_id)

        self._json_response({'ok': True, 'routed_to': domain_tag})

    def _handle_archive(self, body):
        """Archive a pending review message."""
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


os.chdir('/home/node/.openclaw/workspace/dashboard')
http.server.HTTPServer(('100.67.100.125', 8080), Handler).serve_forever()
