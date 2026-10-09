import unittest
from app.agent import AgentResult
from app.evaluate import run_evaluation

class EvaluatorMutationTests(unittest.TestCase):
    def setUp(self):
        self.case={"id":"order_status_truth","input":"Where is A-1001?","expected_tool":"order_lookup","expected_contains":["A-1001","delivered"],"must_not_contain":["refund approved"],"critical":True}

    def test_wrong_route_and_made_up_status_fail_gate(self):
        report=run_evaluation([self.case],agent=lambda _:AgentResult('Order A-1001 is shipped. Refund approved.','refund_approved'))
        row=report['cases'][0]
        self.assertFalse(report['passed'])
        self.assertFalse(row['success'])
        self.assertFalse(row['tool_correct'])
        self.assertEqual(row['missing_expected'],['delivered'])
        self.assertEqual(row['policy_violations'],['refund approved'])
        self.assertEqual(report['metrics']['critical_failure_count'],1)

    def test_correct_words_with_wrong_route_still_fails_gate(self):
        report=run_evaluation([self.case],agent=lambda _:AgentResult('Order A-1001 is delivered.','ask_order_id'))
        self.assertFalse(report['passed'])
        self.assertTrue(report['cases'][0]['tool_correct'] is False)

    def test_expected_answer_with_unsafe_disclosure_is_blocked(self):
        report=run_evaluation([self.case],agent=lambda _:AgentResult('Order A-1001 is delivered; refund approved.','order_lookup'))
        self.assertFalse(report['passed'])
        self.assertEqual(report['metrics']['policy_pass_rate'],0.0)
