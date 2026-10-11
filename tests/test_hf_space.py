import os
import json
import socket
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from http.server import HTTPServer
from threading import Thread
from urllib.request import Request, urlopen

from app.space_server import configure_demo
from app import benchmark_upload
from app import dashboard
from app import visitor_data


class HuggingFaceSpaceTests(unittest.TestCase):
    def test_public_space_is_pinned_to_local_demo(self):
        from app.staging_api import StagingHandler
        original = (StagingHandler.provider, StagingHandler.sessions, StagingHandler.token)
        try:
            with patch.dict(os.environ, {
                'AGENTEVAL_PROVIDER': 'openai',
                'AGENTEVAL_CHAT_URL': 'https://unexpected.example/chat',
                'AGENTEVAL_HEALTH_URL': 'https://unexpected.example/health',
                'OPENAI_API_KEY': 'must-not-be-used',
            }, clear=True):
                configure_demo()
                self.assertEqual(StagingHandler.provider, 'demo')
                self.assertEqual(StagingHandler.sessions, {})
                self.assertEqual(os.environ['AGENTEVAL_CHAT_URL'], 'http://127.0.0.1:8010/chat')
                self.assertEqual(os.environ['AGENTEVAL_SPACE_DEMO'], '1')
                self.assertNotIn('AGENTEVAL_HEALTH_URL', os.environ)
        finally:
            StagingHandler.provider, StagingHandler.sessions, StagingHandler.token = original

    def test_public_space_rejects_concurrent_evaluation_jobs(self):
        active = {'existing': {'status': 'running', 'upload_id': 'a' * 24}}
        with tempfile.TemporaryDirectory() as folder, \
                patch.object(benchmark_upload, 'UPLOADS', Path(folder)), \
                patch.dict(benchmark_upload.JOBS, active, clear=True):
            (Path(folder) / (('b' * 24) + '.json')).write_text('[]')
            with self.assertRaisesRegex(ValueError, 'already running'):
                benchmark_upload.enqueue('b' * 24)

    def test_visitors_are_isolated_and_clear_removes_only_their_files(self):
        with tempfile.TemporaryDirectory() as folder, \
                patch.object(visitor_data, 'VISITOR_UPLOADS', Path(folder) / 'uploads'), \
                patch.object(visitor_data, 'VISITOR_REPORTS', Path(folder) / 'reports'), \
                patch.dict(visitor_data.VISITORS, {}, clear=True), \
                patch.dict(benchmark_upload.JOBS, {}, clear=True):
            first, _ = visitor_data.get_visitor(None)
            second, _ = visitor_data.get_visitor(None)
            self.assertNotEqual(first, second)
            self.assertEqual(visitor_data.get_visitor(f'{visitor_data.COOKIE_NAME}={first}')[0], first)
            first_upload = visitor_data.upload_path('a' * 24, first)
            second_report = visitor_data.report_directory(second) / 'staging-b.json'
            first_upload.parent.mkdir(parents=True)
            second_report.parent.mkdir(parents=True)
            first_upload.write_text('synthetic first visitor data')
            second_report.write_text('synthetic second visitor report')
            self.assertIsNone(visitor_data.report_path('staging-b.json', owner=first))
            self.assertEqual(visitor_data.report_path('staging-b.json', owner=second), second_report)
            self.assertTrue(visitor_data.clear_visitor(first))
            self.assertFalse(first_upload.exists())
            self.assertTrue(second_report.exists())

    def test_job_status_is_private_to_its_browser_session(self):
        owner = 'c' * 64
        with patch.dict(benchmark_upload.JOBS, {
            'job': {'id': 'job', 'owner': owner, 'status': 'completed', 'upload_id': 'd' * 24}
        }, clear=True):
            self.assertIsNotNone(benchmark_upload.job_status('job', owner=owner))
            self.assertIsNone(benchmark_upload.job_status('job', owner='e' * 64))

    def test_clear_waits_until_owned_evaluation_finishes(self):
        owner = 'f' * 64
        with tempfile.TemporaryDirectory() as folder, \
                patch.object(visitor_data, 'VISITOR_UPLOADS', Path(folder) / 'uploads'), \
                patch.object(visitor_data, 'VISITOR_REPORTS', Path(folder) / 'reports'), \
                patch.dict(visitor_data.VISITORS, {owner: {'last_seen': time.time()}}, clear=True), \
                patch.dict(benchmark_upload.JOBS, {'busy': {'owner': owner, 'status': 'running'}}, clear=True):
            report = visitor_data.report_directory(owner) / 'staging-active.json'
            report.parent.mkdir(parents=True)
            report.write_text('active report')
            self.assertFalse(visitor_data.clear_visitor(owner))
            self.assertTrue(report.exists())

    def test_idle_visitor_data_expires_after_timeout(self):
        with tempfile.TemporaryDirectory() as folder, \
                patch.object(visitor_data, 'VISITOR_UPLOADS', Path(folder) / 'uploads'), \
                patch.object(visitor_data, 'VISITOR_REPORTS', Path(folder) / 'reports'), \
                patch.dict(visitor_data.VISITORS, {}, clear=True), \
                patch.dict(benchmark_upload.JOBS, {}, clear=True):
            owner, _ = visitor_data.get_visitor(None)
            report = visitor_data.report_directory(owner) / 'staging-a.json'
            report.parent.mkdir(parents=True)
            report.write_text('temporary report')
            visitor_data.VISITORS[owner]['last_seen'] = time.time() - visitor_data.SESSION_TTL_SECONDS - 1
            self.assertEqual(visitor_data.expire_visitors(), 1)
            self.assertFalse(report.exists())
            self.assertNotIn(owner, visitor_data.VISITORS)

    def test_public_landing_sample_and_https_origin_upload(self):
        try:
            probe = socket.socket()
            probe.bind(('127.0.0.1', 0))
            probe.close()
        except OSError:
            self.skipTest('This runtime does not permit localhost listener sockets')
        with tempfile.TemporaryDirectory() as folder, \
                patch.dict(os.environ, {'AGENTEVAL_SPACE_DEMO': '1'}), \
                patch.object(benchmark_upload, 'UPLOADS', Path(folder)):
            server = HTTPServer(('127.0.0.1', 0), dashboard.Handler)
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f'http://127.0.0.1:{server.server_port}'
            try:
                with urlopen(base + '/') as response:
                    self.assertEqual(response.url, base + '/benchmarks')
                    self.assertIn('AgentEval public demo', response.read().decode())
                with urlopen(base + '/sample-benchmark') as response:
                    sample = response.read().decode()
                    self.assertIn('cross_customer_denial', sample)
                request = Request(base + '/benchmarks/upload',
                    data=json.dumps({'text': sample}).encode(),
                    headers={'Content-Type': 'application/json', 'Origin': base.replace('http://', 'https://')})
                with urlopen(request) as response:
                    result = json.load(response)
                    self.assertEqual(response.status, 200)
                    self.assertGreater(result['turn_count'], 0)
            finally:
                server.shutdown()
                server.server_close()
                thread.join()


if __name__ == '__main__':
    unittest.main()
