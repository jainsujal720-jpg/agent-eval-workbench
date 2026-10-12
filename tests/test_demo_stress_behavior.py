import unittest
from pathlib import Path

from app.agent import run_demo_agent
from app.evaluate import load_cases, run_evaluation


class DemoStressBehaviorTests(unittest.TestCase):
    def test_demo_agent_passes_the_approved_stress_suite(self):
        cases = load_cases(Path("benchmarks/support_stress.jsonl"))
        report = run_evaluation(cases, agent=run_demo_agent, provider="demo")
        self.assertTrue(report["passed"], report["checks"])
        self.assertEqual(report["metrics"]["critical_failure_count"], 0)
        self.assertEqual(report["metrics"]["task_success_rate"], 1.0)
        self.assertEqual(report["metrics"]["policy_pass_rate"], 1.0)
        self.assertEqual(report["metrics"]["tool_correctness"], 1.0)


if __name__ == "__main__":
    unittest.main()
