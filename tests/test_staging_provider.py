import os
import subprocess
import socket
import sys
import threading
import unittest
from http.server import ThreadingHTTPServer
from unittest.mock import patch
from urllib.request import urlopen
from app.staging_api import StagingHandler
from app.api_adapter import APISession, staging_target

class StagingProviderTests(unittest.TestCase):
    def test_missing_key_stops_before_server_starts(self):
        env=dict(os.environ);env.pop('OPENAI_API_KEY',None)
        result=subprocess.run([sys.executable,'-m','app.staging_api','--provider','openai'],env=env,capture_output=True,text=True,timeout=5)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('OPENAI_API_KEY must be set',result.stderr)

    def test_openai_provider_and_metadata_cross_http(self):
        try:
            probe=socket.socket()
            probe.bind(('127.0.0.1',0))
            probe.close()
        except OSError:
            self.skipTest('This runtime does not permit localhost listener sockets')
        previous=StagingHandler.provider
        StagingHandler.provider='openai'
        server=ThreadingHTTPServer(('127.0.0.1',0),StagingHandler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        observed=[]
        def choose(session,text):
            observed.append(session.provider)
            return dict(action='lookup',intent='status',order_id='A-1002')
        def local(request,timeout):
            request.full_url=request.full_url.replace(':8010',':'+str(server.server_port))
            return urlopen(request,timeout=timeout)
        try:
            with patch('app.api_adapter.urlopen',side_effect=local),patch('app.session_eval.SupportSession.select',choose),patch.dict(os.environ,{'OPENAI_MODEL':'test-model'}):
                self.assertEqual(staging_target(),dict(provider='openai',model='test-model'))
                result=APISession('alice').turn('Where is A-1002?',fault='timeout')
                self.assertEqual(observed,['openai'])
                self.assertEqual(result['chatbot_provider'],'openai')
                self.assertEqual(result['chatbot_model'],'test-model')
                self.assertEqual(result['actual_tool'],'tool_unavailable')
        finally:
            server.shutdown();server.server_close();thread.join()
            StagingHandler.provider=previous
