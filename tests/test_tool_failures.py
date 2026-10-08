import json
import unittest
from pathlib import Path
from unittest.mock import patch
from app.session_eval import SupportSession, evaluate_sessions

class ToolFailureTests(unittest.TestCase):
    def test_demo_failure_suite(self):
        cases=[json.loads(s) for s in Path('benchmarks/support_failures.jsonl').read_text().splitlines()]
        report=evaluate_sessions(cases,'demo')
        self.assertEqual(report['metrics']['turn_count'],20)
        self.assertTrue(report['passed'],report)

    def test_denied_lookup_never_calls_order_service(self):
        with patch('app.session_eval.read_order') as read:
            result=SupportSession('alice').turn('Where is B-2001?',fault='timeout')
        read.assert_not_called()
        self.assertEqual(result['tool_outcome'],'not_called')

    def test_wrong_record_does_not_disclose_returned_status(self):
        result=SupportSession('alice').turn('Where is A-1002?',fault='wrong_order')
        self.assertEqual(result['tool_outcome'],'invalid_response')
        self.assertNotIn('processing',result['answer'])
        self.assertNotIn('B-2001',result['answer'])
        self.assertEqual(result['accessed_order_ids'],[])

    def test_retry_fetches_fresh_data(self):
        session=SupportSession('alice')
        session.turn('Where is A-1002?',fault='timeout')
        with patch('app.session_eval.read_order',return_value={'order_id':'A-1002','status':'delivered'}) as read:
            result=session.turn('Try again.')
        read.assert_called_once_with('A-1002','none')
        self.assertIn('delivered',result['answer'])

    def test_malformed_id_cannot_be_shortened_by_model(self):
        session=SupportSession('alice')
        with patch.object(session,'select',return_value=dict(action='lookup',intent='status',order_id='A-1001')):
            result=session.turn('Where is A-1001O?')
        self.assertEqual(result['actual_tool'],'ask_order_id')
        self.assertEqual(result['accessed_order_ids'],[])

    def test_unexpected_exception_is_still_an_error(self):
        case=dict(id='error',category='tool_failure',customer_id='alice',turns=[dict(input='A-1002',expected_tool='order_lookup')])
        with patch('app.session_eval.read_order',side_effect=RuntimeError('internal detail')):
            report=evaluate_sessions([case],'demo')
        self.assertFalse(report['passed'])
        self.assertEqual(report['metrics']['error_count'],1)
