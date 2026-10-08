import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.request import urlopen
from urllib.error import HTTPError
from unittest.mock import patch
from http.server import HTTPServer
from app import dashboard

class DashboardTests(unittest.TestCase):
    def report(self):
        return dict(provider='openai',passed=False,metrics=dict(session_count=1,turn_count=2,failed_turn_count=1,access_check_failure_count=0,error_count=0,guard_intervention_count=1),cases=[
            dict(session_id='test',turn=1,customer_id='bob',input='<script>alert(1)</script>',answer='denied',success=True,expected_tool='access_denied',actual_tool='access_denied',model_choice=dict(action='lookup'),guard_reason='explicit_order_not_accessible',accessed_order_ids=[]),
            dict(session_id='test',turn=2,input='failed-input',answer='wrong',success=False,expected_tool='ask_order_id',actual_tool='order_lookup',tool_correct=False,missing_expected=[],policy_violations=[])])

    def test_session_shows_original_choice_and_guard(self):
        page=dashboard.render_report(self.report(),True)
        self.assertIn('Model choice',page)
        self.assertIn('explicit_order_not_accessible',page)
        self.assertIn('Route check failed',page)
        self.assertNotIn('All checks passed</p></article></details>',page)
        self.assertIn('&lt;script&gt;',page)
        self.assertNotIn('<script>',page)

    def test_filters_do_not_change_overall_gate(self):
        page=dashboard.render_report(self.report(),True,'guards')
        self.assertNotIn('failed-input',page)
        self.assertIn('Overall gate: <span class="badge fail">FAIL',page)
        page=dashboard.render_report(self.report(),True,'failed')
        self.assertIn('failed-input',page)
        self.assertNotIn('&lt;script&gt;',page)

    def test_missing_reports_are_explained(self):
        self.assertIn('reports/session-latest.json',dashboard.render_report(None,True))

    def test_http_views_and_download_are_separate(self):
        with tempfile.TemporaryDirectory() as folder:
            regular=Path(folder)/'regular.json';session=Path(folder)/'session.json'
            regular.write_text(json.dumps(dict(provider='demo',passed=True,metrics={},cases=[])))
            session.write_text(json.dumps(self.report()))
            with patch.object(dashboard,'REPORT',regular),patch.object(dashboard,'SESSION_REPORT',session):
                server=HTTPServer(('127.0.0.1',0),dashboard.Handler)
                thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
                base=f'http://127.0.0.1:{server.server_port}'
                try:
                    with urlopen(base+'/sessions?filter=guards') as response:
                        self.assertIn('Guard interventions',response.read().decode())
                    with urlopen(base+'/session-report.json') as response:
                        self.assertEqual(json.load(response)['metrics']['turn_count'],2)
                    with urlopen(base+'/') as response:
                        self.assertIn('Task success',response.read().decode())
                    session.write_text('{broken')
                    with self.assertRaises(HTTPError) as error:urlopen(base+'/sessions')
                    self.assertEqual(error.exception.code,500)
                    error.exception.close()
                finally:
                    server.shutdown();thread.join();server.server_close()
