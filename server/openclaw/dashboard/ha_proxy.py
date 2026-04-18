#!/usr/bin/env python3
"""
Lightweight HA proxy — serves /ha/states/<entity_id> with CORS headers.
Runs on port 8081, bind to Tailscale IP.
"""
import http.server
import urllib.request
import json
import os

HA_URL   = "http://100.127.241.99:8123"
HA_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiI4ZTRlYTQzODI5YWM0NDk1YjY0MjRiMGM5NDQ5NmNmZiIsImlhdCI6MTc3NjUxNTU2NCwiZXhwIjoyMDkxODc1NTY0fQ.et05AdasM_8Zk1oAiQZlx9d66nO8ayeW1BT89Wxx524"
BIND_IP  = "100.67.100.125"
PORT     = 8081

class ProxyHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # suppress access logs

    def do_GET(self):
        if not self.path.startswith("/ha/states/"):
            self.send_response(404)
            self.end_headers()
            return

        entity_id = self.path[len("/ha/states/"):]
        url = f"{HA_URL}/api/states/{entity_id}"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {HA_TOKEN}"})
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = resp.read()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(data)
        except Exception as e:
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

if __name__ == "__main__":
    server = http.server.HTTPServer((BIND_IP, PORT), ProxyHandler)
    print(f"HA Proxy running on http://{BIND_IP}:{PORT}")
    server.serve_forever()
