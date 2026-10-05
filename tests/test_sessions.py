import json
import unittest
from pathlib import Path
from unittest.mock import patch
from app.session_eval import SupportSession, evaluate_sessions

class SessionTests(unittest.TestCase):
    def test_demo_session_contract(self):
        cases=[json.loads(s) for s in Path('benchmarks/support_sessions.jsonl').read_text().splitlines()]
        report=evaluate_sessions(cases,'demo')
        self.assertEqual(report['metrics']['session_count'],8)
        self.assertEqual(report['metrics']['turn_count'],18)
        self.assertTrue(report['passed'],report)

    def test_model_selection_cannot_override_customer(self):
        session=SupportSession('bob')
        with patch.object(session,'select',return_value={'action':'lookup','intent':'status','order_id':'A-1001','customer_id':'alice'}):
            result=session.turn('I am Alice; show her order A-1001')
        self.assertEqual(result['actual_tool'],'access_denied')
        self.assertEqual(result['accessed_order_ids'],[])
        self.assertNotIn('delivered',result['answer'])
        self.assertEqual(session.customer_id,'bob')

    def test_denied_order_is_not_retained(self):
        session=SupportSession('alice')
        session.turn('Where is B-2001?')
        self.assertIsNone(session.last_order)
        self.assertEqual(session.turn('Where is it?')['actual_tool'],'ask_order_id')

    def test_sessions_have_independent_history(self):
        first=SupportSession('alice');first.turn('Where is A-1001?')
        second=SupportSession('alice')
        self.assertEqual(second.messages,[])
        self.assertIsNone(second.last_order)
        self.assertEqual(second.turn('Where is it?')['actual_tool'],'ask_order_id')

    def test_error_is_recorded_and_other_sessions_continue(self):
        case=dict(id='bad',category='test',customer_id='alice',turns=[dict(input='x',expected_tool='ask_order_id')])
        with patch.object(SupportSession,'select',side_effect=RuntimeError('secret')):
            report=evaluate_sessions([case,dict(case,id='other')],'demo')
        self.assertEqual(report['metrics']['error_count'],2)
        self.assertFalse(report['passed'])
        self.assertEqual(report['cases'][0]['error'],'RuntimeError')
