import json
import os
import tempfile
import time
import socket
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

def requires_local_sockets(test):
    def wrapped(self,*args,**kwargs):
        try:
            probe=socket.socket()
            probe.bind(('127.0.0.1',0))
            probe.close()
        except OSError:
            self.skipTest('This runtime does not permit localhost listener sockets')
        return test(self,*args,**kwargs)
    return wrapped

class APIWorkflowTests(unittest.TestCase):
    def test_invalid_upload_rejected(self):
        for text in ['[]','not json','[{"id":"x"}]']:
            with self.assertRaises(ValueError): validate(text)

    def test_fault_benchmark_validates(self):
        self.assertEqual(len(validate(Path('benchmarks/support_failures.jsonl').read_text())),16)

    @requires_local_sockets
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
                            request=Request(f'http://127.0.0.1:{dashboard.server_port}/benchmarks/run',data=json.dumps({'upload_id':uploaded['upload_id']}).encode(),headers={'Content-Type':'application/json'})
                            with original_urlopen(request) as response: started=json.load(response)
                            self.assertIn('job_id',started)
                            deadline=time.time()+15
                            while True:
                                with original_urlopen(f'http://127.0.0.1:{dashboard.server_port}/benchmarks/jobs/{started["job_id"]}') as response: ran=json.load(response)
                                if ran['status'] in {'completed','failed'}: break
                                self.assertLess(time.time(),deadline,'Evaluation job did not finish')
                                time.sleep(.02)
                            self.assertEqual(ran['status'],'completed',ran)
                            self.assertTrue(ran['result']['passed'])
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

class ConfigurableCompanyAdapterTests(unittest.TestCase):
    def test_custom_request_auth_and_response_contract(self):
        from app.api_adapter import APISession
        class Response:
            def __enter__(self): return self
            def __exit__(self,*args): return False
            def read(self): return json.dumps({'reply':{'text':'Order A-1002 is shipped.'},'routing':{'tool':'order_lookup'},'context':{'id':'company-session-2'},'trace':{'orders':['A-1002']}}).encode()
        captured={}
        def fake_urlopen(request,timeout):
            captured['url']=request.full_url;captured['body']=json.loads(request.data);captured['auth']=request.get_header('X-test-token');captured['timeout']=timeout
            return Response()
        env={'AGENTEVAL_CHAT_URL':'https://company.example/support','AGENTEVAL_CUSTOMER_FIELD':'account','AGENTEVAL_MESSAGE_FIELD':'query','AGENTEVAL_SESSION_FIELD':'conversation','AGENTEVAL_FAULT_FIELD':'','AGENTEVAL_AUTH_TOKEN':'test-secret','AGENTEVAL_AUTH_HEADER':'X-Test-Token','AGENTEVAL_AUTH_SCHEME':'','AGENTEVAL_RESPONSE_ANSWER_FIELD':'reply.text','AGENTEVAL_RESPONSE_ROUTE_FIELD':'routing.tool','AGENTEVAL_RESPONSE_SESSION_FIELD':'context.id','AGENTEVAL_RESPONSE_ACCESSED_FIELD':'trace.orders'}
        with patch.dict(os.environ,env,clear=True),patch('app.api_adapter.urlopen',side_effect=fake_urlopen):
            client=APISession('alice');result=client.turn('Where is A-1002?')
        self.assertEqual(captured['body'],{'account':'alice','query':'Where is A-1002?','conversation':None})
        self.assertEqual(captured['auth'],'test-secret')
        self.assertEqual(result['actual_tool'],'order_lookup')
        self.assertEqual(result['accessed_order_ids'],['A-1002'])
        self.assertEqual(client.session_id,'company-session-2')
        self.assertEqual(captured['timeout'],120)

    def test_company_api_requires_https(self):
        from app.api_adapter import APISession
        with patch.dict(os.environ,{'AGENTEVAL_CHAT_URL':'http://company.example/chat'},clear=True):
            with self.assertRaisesRegex(ValueError,'HTTPS'): APISession('alice').turn('Hello')

    def test_job_status_tracks_background_progress_and_completion(self):
        from app.benchmark_upload import enqueue, job_status
        case={'id':'one','customer_id':'alice','category':'status','turns':[{'input':'status','expected_tool':'order_lookup','expected_contains':[],'expected_accessed_order_ids':[]} ]}
        previous=os.getcwd()
        try:
            with tempfile.TemporaryDirectory() as folder:
                upload_dir=Path(folder)/'benchmarks/uploads';upload_dir.mkdir(parents=True);upload_id='a'*24
                (upload_dir/(upload_id+'.json')).write_text(json.dumps([case]))
                os.chdir(folder)
                def fake_evaluate(cases,provider,session_factory,progress_callback=None):
                    if progress_callback: progress_callback(1,1)
                    return {'passed':True,'metrics':{'session_count':1,'turn_count':1,'failed_turn_count':0},'cases':[]}
                with patch('app.benchmark_upload.UPLOADS',Path('benchmarks/uploads')),patch('app.benchmark_upload.staging_target',return_value={'provider':'demo'}),patch('app.benchmark_upload.evaluate_sessions',side_effect=fake_evaluate):
                    job=enqueue(upload_id)
                    deadline=time.time()+3
                    while job_status(job)['status'] not in {'completed','failed'} and time.time()<deadline: time.sleep(.01)
                    status=job_status(job)
                    self.assertEqual(status['status'],'completed',status)
                    self.assertEqual(status['completed_turns'],1)
                    self.assertEqual(status['total_turns'],1)
                    self.assertEqual(status['result']['chatbot_provider'],'demo')
        finally: os.chdir(previous)
