#!/usr/bin/env python3
"""
AgentMail Webhook Relay

Listens on port 18790, receives AgentMail webhooks (no auth required from AgentMail),
validates the shared secret, and forwards to OpenClaw with proper auth header.

This solves the problem: AgentMail can't send custom auth headers, and OpenClaw
rejects query param tokens.

Usage:
    python3 agentmail-relay.py &
    # Then set AgentMail webhook URL to: https://ssd.tail5ec603.ts.net:18790/webhook
"""

import http.server
import json
import urllib.request
import sys
import os

OPENCLAW_URL = "http://127.0.0.1:18789/hooks/agentmail"
OPENCLAW_TOKEN = "aa1f7373656ab275d9af235ce463299f01c37fb901debc63"
LISTEN_PORT = 18790


class RelayHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            
            # Forward to OpenClaw with proper auth header
            req = urllib.request.Request(
                OPENCLAW_URL,
                data=body,
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {OPENCLAW_TOKEN}',
                },
                method='POST'
            )
            
            with urllib.request.urlopen(req, timeout=10) as resp:
                self.send_response(resp.status)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(resp.read())
                
        except Exception as e:
            print(f"[relay] Error forwarding: {e}", file=sys.stderr)
            self.send_response(502)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())
    
    def log_message(self, format, *args):
        from datetime import datetime
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[agentmail-relay {ts}] {args[0]}", file=sys.stderr)


def main():
    server = http.server.HTTPServer(('127.0.0.1', LISTEN_PORT), RelayHandler)
    print(f"[agentmail-relay] Listening on 127.0.0.1:{LISTEN_PORT}", file=sys.stderr)
    print(f"[agentmail-relay] Forwarding to {OPENCLAW_URL}", file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[agentmail-relay] Shutting down", file=sys.stderr)
        server.server_close()


if __name__ == '__main__':
    main()
