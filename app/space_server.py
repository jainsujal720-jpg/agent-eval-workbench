"""Start the public, synthetic-only Hugging Face Space demo."""
import os
from http.server import ThreadingHTTPServer
from threading import Event, Thread

from app import dashboard
from app.staging_api import StagingHandler
from app.visitor_data import expire_visitors


def configure_demo():
    """Pin this public demo to local synthetic fixtures and the demo agent."""
    StagingHandler.provider = 'demo'
    StagingHandler.sessions = {}
    StagingHandler.token = 'local-space-demo-token'
    os.environ['AGENTEVAL_SPACE_DEMO'] = '1'
    os.environ['AGENTEVAL_CHAT_URL'] = 'http://127.0.0.1:8010/chat'
    os.environ['AGENTEVAL_STAGING_TOKEN'] = StagingHandler.token
    os.environ.pop('AGENTEVAL_HEALTH_URL', None)
    return StagingHandler


def main():
    configure_demo()
    port = int(os.getenv('PORT', '7860'))
    staging = ThreadingHTTPServer(('127.0.0.1', 8010), StagingHandler)
    thread = Thread(target=staging.serve_forever, name='synthetic-chatbot', daemon=True)
    thread.start()
    cleanup_stop=Event()
    def cleanup_loop():
        while not cleanup_stop.wait(60):
            expire_visitors()
    cleanup_thread=Thread(target=cleanup_loop,name='visitor-data-expiry',daemon=True)
    cleanup_thread.start()
    print('Starting AgentEval public demo in deterministic synthetic-only mode.', flush=True)
    try:
        dashboard.serve(host='0.0.0.0', port=port)
    finally:
        cleanup_stop.set()
        cleanup_thread.join(timeout=2)
        staging.shutdown()
        staging.server_close()
        thread.join(timeout=2)


if __name__ == '__main__':
    main()
