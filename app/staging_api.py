"""Separate localhost chatbot service using synthetic support fixtures."""
import argparse
import json
import os
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from app.session_eval import SupportSession

class StagingHandler(BaseHTTPRequestHandler):
    sessions = {}
    token = 'local-demo-token'
    def do_POST(self):
        if self.path != '/chat': self.send_error(404); return
        if not secrets.compare_digest(self.headers.get('Authorization', ''), 'Bearer ' + self.token):
            self.send_error(401); return
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= 65536: raise ValueError('Invalid request size')
            data = json.loads(self.rfile.read(size))
            customer = data['customer_id']
            if customer not in {'alice', 'bob'}: raise ValueError('Unknown synthetic identity')
            message = data['message']
            if not isinstance(message, str) or not message.strip(): raise ValueError('Message required')
            session_id = data.get('session_id')
            if session_id:
                session = self.sessions.get(session_id)
                if session is None or session.customer_id != customer: raise ValueError('Invalid session')
            else:
                if len(self.sessions) >= 1000: raise ValueError('Restart staging service to clear sessions')
                session_id = secrets.token_urlsafe(24)
                session = SupportSession(customer, 'demo')
                self.sessions[session_id] = session
            result = session.turn(message, data.get('fault', 'none'))
            result['session_id'] = session_id
            payload = json.dumps(result).encode()
        except (ValueError, KeyError, TypeError):
            self.send_error(400, 'Invalid staging request'); return
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers(); self.wfile.write(payload)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8010)
    args = parser.parse_args()
    StagingHandler.token = os.getenv('AGENTEVAL_STAGING_TOKEN', 'local-demo-token')
    with ThreadingHTTPServer(('127.0.0.1', args.port), StagingHandler) as server:
        print(f'Synthetic staging chatbot: http://127.0.0.1:{args.port}/chat', flush=True)
        print('Demo routing; no model API calls. Control-C stops the service.', flush=True)
        try: server.serve_forever()
        except KeyboardInterrupt: pass
if __name__ == '__main__': main()
