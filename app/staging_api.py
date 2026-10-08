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
    provider = 'demo'

    def do_GET(self):
        if self.path != '/health': self.send_error(404); return
        if not secrets.compare_digest(self.headers.get('Authorization',''), 'Bearer '+self.token):
            self.send_error(401); return
        payload=json.dumps({'provider':self.provider,'model':os.getenv('OPENAI_MODEL','gpt-4o-mini') if self.provider=='openai' else None}).encode()
        self.send_response(200); self.send_header('Content-Type','application/json')
        self.end_headers(); self.wfile.write(payload)
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
                session = SupportSession(customer, self.provider)
                self.sessions[session_id] = session
            result = session.turn(message, data.get('fault', 'none'))
            result['session_id'] = session_id
            result['chatbot_provider'] = self.provider
            result['chatbot_model'] = os.getenv('OPENAI_MODEL','gpt-4o-mini') if self.provider=='openai' else None
            payload = json.dumps(result).encode()
        except (ValueError, KeyError, TypeError):
            self.send_error(400, 'Invalid staging request'); return
        except Exception:
            self.send_error(502, 'Chatbot execution failed; check provider configuration'); return
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers(); self.wfile.write(payload)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8010)
    parser.add_argument('--provider', choices=['demo','openai'], default='demo')
    args = parser.parse_args()
    if args.provider == 'openai':
        if not os.getenv('OPENAI_API_KEY','').strip(): parser.error('OPENAI_API_KEY must be set in this Terminal tab')
        try: import openai
        except ImportError: parser.error("Install the SDK: python3 -m pip install -e '.[openai]'")
    StagingHandler.provider = args.provider
    StagingHandler.sessions = {}
    StagingHandler.token = os.getenv('AGENTEVAL_STAGING_TOKEN', 'local-demo-token')
    with ThreadingHTTPServer(('127.0.0.1', args.port), StagingHandler) as server:
        print(f'Synthetic staging chatbot: http://127.0.0.1:{args.port}/chat', flush=True)
        print('Provider: '+args.provider+(' — model '+os.getenv('OPENAI_MODEL','gpt-4o-mini')+'; live API requests incur charges.' if args.provider=='openai' else '; no model API calls.'), flush=True)
        print('Control-C stops the service.', flush=True)
        try: server.serve_forever()
        except KeyboardInterrupt: pass
if __name__ == '__main__': main()
