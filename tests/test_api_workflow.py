import json
import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from http.server import ThreadingHTTPServer
from urllib.request import Request, urlopen
from app.staging_api import StagingHandler
from app.api_adapter import APISession
from app.benchmark_upload import validate
from app.session_eval import evaluate_sessions

class APIWorkflowTests(unittest.TestCase):
    def test_invalid_upload_rejected(self):
        for text in ['[]','not json','[{"id":"x"}]']:
            with self.assertRaises(ValueError): validate(text)

    def test_fault_benchmark_validates(self):
        self.assertEqual(len(validate(Path('benchmarks/support_failures.jsonl').read_text())),16)

    def test_external_http_round_trip_and_isolation(self):
        server=ThreadingHTTPServer(('127.0.0.1',0),StagingHandler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        original_urlopen=__import__('urllib.request',fromlist=['urlopen']).urlopen
        def local(request,timeout):
            request.full_url=f'http://127.0.0.1:{server.server_port}'+('/health' if request.full_url.endswith('/health') else '/chat')
            body=json.loads(request.data) if request.data else {}
            self.assertNotIn('expected_tool',body)
            self.assertNotIn('expected_contains',body)
            return original_urlopen(request,timeout=timeout)
        try:
            with patch('app.api_adapter.urlopen',side_effect=local):
                cases=validate(Path('benchmarks/support_failures.jsonl').read_text())
                report=evaluate_sessions(cases,'staging',APISession)
                self.assertTrue(report['passed'],report)
                self.assertEqual(report['metrics']['handled_tool_failure_count'],9)
                from app.dashboard import Handler
                dashboard=ThreadingHTTPServer(('127.0.0.1',0),Handler)
                worker=threading.Thread(target=dashboard.serve_forever,daemon=True);worker.start()
                def post(path,data):
                    request=Request(f'http://127.0.0.1:{dashboard.server_port}'+path,
                        data=json.dumps(data).encode(),headers={'Content-Type':'application/json'})
                    with original_urlopen(request) as response: return json.load(response)
                try:
                    with tempfile.TemporaryDirectory() as folder:
                        previous=os.getcwd()
                        try:
                            os.chdir(folder)
                            uploaded=post('/benchmarks/upload',{'text':json.dumps(cases)})
                            ran=post('/benchmarks/run',{'upload_id':uploaded['upload_id']})
                            self.assertTrue(ran['passed'])
                            saved=json.loads(Path('reports/session-latest.json').read_text())
                            self.assertEqual(saved['provider'],'staging')
                            with original_urlopen(f'http://127.0.0.1:{dashboard.server_port}/sessions') as response:
                                self.assertIn('staging',response.read().decode())
                        finally: os.chdir(previous)
                finally:
                    dashboard.shutdown();dashboard.server_close();worker.join()
                bob=APISession('bob');r=bob.turn('Where is A-1001?')
                self.assertEqual(r['actual_tool'],'access_denied')
        finally:
            server.shutdown();server.server_close();thread.join()
