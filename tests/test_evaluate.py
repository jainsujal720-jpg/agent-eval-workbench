import unittest
from pathlib import Path

from app.evaluate import load_cases, run_evaluation


class EvaluationTests(unittest.TestCase):
    def test_sample_benchmark_passes(self):
        cases = load_cases(Path("benchmarks/support.jsonl"))
        report = run_evaluation(cases)
        self.assertTrue(report["passed"])
        self.assertEqual(report["metrics"]["task_success_rate"], 1.0)
        self.assertEqual(report["metrics"]["policy_pass_rate"], 1.0)
        self.assertEqual(report["metrics"]["tool_correctness"], 1.0)

    def test_report_includes_case_level_failure_details(self):
        report = run_evaluation([{"id": "bad", "input": "hello", "expected_contains": ["refund approved"], "expected_tool": "refund_lookup"}])
        self.assertFalse(report["passed"])
        self.assertEqual(report["cases"][0]["missing_expected"], ["refund approved"])
        self.assertFalse(report["cases"][0]["tool_correct"])

    def test_synthetic_company_scenario_passes(self):
        cases = load_cases(Path("benchmarks/support.jsonl"))
        report = run_evaluation(cases)
        self.assertEqual(report["metrics"]["case_count"], 6)
        self.assertTrue(report["passed"])
        self.assertIn("refund_policy", report["metrics"]["success_by_category"])


if __name__ == "__main__":
    unittest.main()
