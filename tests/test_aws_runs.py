import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from app import aws_runs, dashboard


class AwsRunSyncTests(TestCase):
    def test_sync_saves_only_summary_metrics_and_dashboard_renders_them(self):
        summary={
            'provider':'demo','passed':True,
            'metrics':{'session_count':8,'turn_count':18,'failed_turn_count':0,
                       'access_check_failure_count':0,'error_count':0,
                       'handled_tool_failure_count':0,'guard_intervention_count':4},
            'cases':[{'input':'private text','answer':'private answer'}],
        }
        calls=[]
        def fake_run(command,**kwargs):
            calls.append(command)
            if 'describe-log-streams' in command:
                payload={'logStreams':[{'logStreamName':'synthetic-smoke/session-eval/task-123',
                                         'lastEventTimestamp':1791741600000}]}
            else:
                payload={'events':[{'message':line} for line in json.dumps(summary,indent=2).splitlines()]}
            return SimpleNamespace(stdout=json.dumps(payload))
        with patch.object(aws_runs.subprocess,'run',side_effect=fake_run):
            with tempfile.TemporaryDirectory() as folder:
                destination=Path(folder)/'aws-runs.json'
                report=aws_runs.sync_cloudwatch_runs(output=destination)
                saved=json.loads(destination.read_text())
                contents=destination.read_text()
            self.assertEqual(len(calls),2)
            self.assertEqual(saved['runs'][0]['run_id'],'task-123')
            self.assertEqual(saved['runs'][0]['metrics']['turn_count'],18)
            self.assertEqual(saved['runs'][0]['cases'],[])
            self.assertNotIn('private text',contents)
            self.assertEqual(report['runs'][0]['passed'],True)
            page=dashboard.render_aws_runs(saved)
            self.assertIn('AWS synthetic runs',page)
            self.assertIn('18',page)
            self.assertIn('Guard interventions',page)
            self.assertIn('PASS',page)
            self.assertNotIn('private answer',page)
            self.assertIn('Case checks unavailable',page)

    def test_bad_or_empty_stream_is_marked_unavailable_without_copying_log_text(self):
        def fake_run(command,**kwargs):
            if 'describe-log-streams' in command:
                payload={'logStreams':[{'logStreamName':'synthetic-smoke/session-eval/task-bad'}]}
            else:
                payload={'events':[{'message':'PRIVATE PROMPT SHOULD NOT BE SAVED'}]}
            return SimpleNamespace(stdout=json.dumps(payload))
        with patch.object(aws_runs.subprocess,'run',side_effect=fake_run):
            with tempfile.TemporaryDirectory() as folder:
                destination=Path(folder)/'aws-runs.json'
                report=aws_runs.sync_cloudwatch_runs(output=destination)
                contents=destination.read_text()
        self.assertFalse(report['runs'][0]['summary_available'])
        self.assertNotIn('PRIVATE PROMPT',contents)

    def test_log_parser_reads_summary_then_ignores_trailing_failure_detail(self):
        summary={'provider':'demo','passed':False,'metrics':{'turn_count':18,'error_count':1}}
        parsed=aws_runs._read_summary([json.dumps(summary,indent=2),'raw failed case content'])
        self.assertEqual(parsed['metrics'],{'turn_count':18,'error_count':1})
        self.assertNotIn('raw failed case content',json.dumps(parsed))

    def test_summary_case_outcomes_keep_only_numbered_boolean_checks(self):
        summary={'provider':'demo','passed':True,'metrics':{},'cases':[
            {'case_number':2,'success':True,'tool_correct':True,'input':'customer text','answer':'private reply'}]}
        parsed=aws_runs._read_summary([json.dumps(summary)])
        self.assertEqual(parsed['cases'],[{'case_number':2,'success':True,'tool_correct':True}])
        self.assertNotIn('customer text',json.dumps(parsed))

    def test_dashboard_renders_content_free_case_outcomes(self):
        report={'region':'ap-south-1','log_group':'/agenteval/synthetic-smoke','synced_at':'now','runs':[
            {'run_id':'task-123','last_event_utc':'now','summary_available':True,'provider':'demo','passed':False,
             'metrics':{'session_count':1,'turn_count':1,'failed_turn_count':1},
             'cases':[{'case_number':1,'success':False,'tool_correct':False,'access_correct':True,
                       'tool_outcome_correct':True,'has_policy_violations':False,'has_missing_expectations':True,'has_error':False}]}]}
        page=dashboard.render_aws_runs(report)
        self.assertIn('Case 1',page)
        self.assertIn('route: issue',page)
        self.assertIn('expectations: issue',page)
        self.assertIn('FAIL',page)

    def test_sync_preserves_previous_local_runs_without_preserving_content(self):
        summary={'provider':'demo','passed':True,
                 'metrics':{'session_count':16,'turn_count':20,'failed_turn_count':0,
                            'handled_tool_failure_count':9},
                 'cases':[{'case_number':1,'success':True,'input':'do not retain'}]}
        def fake_run(command,**kwargs):
            if 'describe-log-streams' in command:
                payload={'logStreams':[{'logStreamName':'synthetic-smoke/session-eval/new-task'}]}
            else:
                payload={'events':[{'message':line} for line in json.dumps(summary).splitlines()]}
            return SimpleNamespace(stdout=json.dumps(payload))
        with patch.object(aws_runs.subprocess,'run',side_effect=fake_run):
            with tempfile.TemporaryDirectory() as folder:
                destination=Path(folder)/'aws-runs.json'
                destination.write_text(json.dumps({
                    'source':'aws-cloudwatch','region':'ap-south-1',
                    'log_group':'/agenteval/synthetic-smoke','runs':[
                        {'run_id':'old-task','last_event_utc':'old','summary_available':True,
                         'provider':'demo','passed':False,'metrics':{'turn_count':18},
                         'cases':[{'case_number':2,'success':False}],
                         'input':'must not survive'}]}))
                report=aws_runs.sync_cloudwatch_runs(output=destination)
                saved=destination.read_text()
        self.assertEqual([run['run_id'] for run in report['runs']],['new-task','old-task'])
        self.assertNotIn('must not survive',saved)
        self.assertEqual(report['runs'][1]['metrics'],{'turn_count':18})
