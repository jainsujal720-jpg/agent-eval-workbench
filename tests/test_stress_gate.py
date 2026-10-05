import unittest
from app.agent import AgentResult
from app.evaluate import run_evaluation


class StressGateTests(unittest.TestCase):
    def test_critical_failure_blocks_high_aggregate_score(self):
        cases = [dict(id=str(i), input='ok', expected_contains=['ok']) for i in range(19)]
        cases.append(dict(id='critical', input='bad', expected_contains=['safe'], critical=True))
        report = run_evaluation(cases, agent=lambda text: AgentResult(text, None))
        self.assertEqual(report['metrics']['task_success_rate'], .95)
        self.assertFalse(report['passed'])
        self.assertEqual(report['critical_failures'], ['critical'])

    def test_wrong_route_is_task_failure(self):
        report = run_evaluation([dict(id='route', input='x', expected_contains=['ok'], expected_tool='order_lookup')], agent=lambda _: AgentResult('ok', 'human_handoff'))
        self.assertFalse(report['cases'][0]['success'])

    def test_error_does_not_discard_remaining_cases(self):
        def agent(text):
            if text == 'bad':
                raise RuntimeError('sensitive request data')
            return AgentResult('ok', None)
        report = run_evaluation([dict(id='error', input='bad'), dict(id='next', input='ok')], agent=agent)
        self.assertEqual(len(report['cases']), 2)
        self.assertEqual(report['cases'][0]['error'], 'RuntimeError')
        self.assertTrue(report['cases'][1]['success'])
        self.assertFalse(report['passed'])

    def test_empty_benchmark_cannot_pass(self):
        self.assertFalse(run_evaluation([], agent=lambda _: AgentResult('ok', None))['passed'])
