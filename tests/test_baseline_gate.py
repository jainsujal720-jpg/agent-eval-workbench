import unittest

from app.baseline_gate import compare


def report(*, passed, score=0.4, policy=0.9, tools=0.5, critical=6,
           errors=0, category=0.0, successes=("ok",)):
    return {
        "provider": "demo",
        "passed": passed,
        "metrics": {
            "task_success_rate": score,
            "policy_pass_rate": policy,
            "tool_correctness": tools,
            "critical_failure_count": critical,
            "error_count": errors,
            "success_by_category": {"ambiguity": category},
        },
        "cases": [{"id": name, "success": True} for name in successes],
    }


class BaselineGateTests(unittest.TestCase):
    def test_failed_candidate_never_passes_even_when_unchanged(self):
        baseline = report(passed=False)
        result = compare(report(passed=False), baseline)
        self.assertFalse(result["passed"])
        self.assertIn("candidate_passed", result["regressions"])

    def test_passing_candidate_with_improved_metrics_passes(self):
        baseline = report(passed=False)
        candidate = report(passed=True, score=0.85, policy=1.0, tools=0.95,
                           critical=0, category=0.5)
        self.assertTrue(compare(candidate, baseline)["passed"])

    def test_metric_regression_blocks_candidate(self):
        baseline = report(passed=False)
        candidate = report(passed=True, score=0.39, policy=1.0, tools=0.8,
                           critical=0, category=0.0)
        result = compare(candidate, baseline)
        self.assertFalse(result["passed"])
        self.assertIn("task_success_rate_not_regressed", result["regressions"])

    def test_previously_passing_case_cannot_regress(self):
        baseline = report(passed=False, successes=("was-good",))
        candidate = report(passed=True, score=0.9, policy=1.0, tools=0.9,
                           critical=0, category=0.2, successes=("was-good", "new"))
        candidate["cases"][0]["success"] = False
        result = compare(candidate, baseline)
        self.assertFalse(result["passed"])
        self.assertFalse(result["checks"]["previously_passing_cases_still_pass"])

    def test_changed_benchmark_blocks_comparison(self):
        baseline = report(passed=False)
        candidate = report(passed=True, score=0.9, policy=1.0, tools=0.9,
                           critical=0, category=0.2, successes=("different",))
        result = compare(candidate, baseline)
        self.assertFalse(result["passed"])
        self.assertFalse(result["checks"]["benchmark_cases_match"])


if __name__ == "__main__":
    unittest.main()
