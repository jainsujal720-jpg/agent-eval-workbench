"""Fail a candidate evaluation when it fails or regresses from its baseline."""

import argparse
import json
from pathlib import Path


HIGHER_IS_BETTER = ("task_success_rate", "policy_pass_rate", "tool_correctness")
LOWER_IS_BETTER = ("critical_failure_count", "error_count")


def compare(candidate: dict, baseline: dict) -> dict:
    """Return explicit pass/fail checks for absolute quality and regressions."""
    checks: dict[str, bool] = {
        "candidate_passed": candidate.get("passed") is True,
        "provider_matches": candidate.get("provider") == baseline.get("provider"),
    }
    current_metrics = candidate.get("metrics", {})
    baseline_metrics = baseline.get("metrics", {})

    for key in HIGHER_IS_BETTER:
        checks[f"{key}_not_regressed"] = (
            key in current_metrics and key in baseline_metrics
            and current_metrics[key] >= baseline_metrics[key]
        )
    for key in LOWER_IS_BETTER:
        checks[f"{key}_not_regressed"] = (
            key in current_metrics and key in baseline_metrics
            and current_metrics[key] <= baseline_metrics[key]
        )

    before_categories = baseline_metrics.get("success_by_category", {})
    after_categories = current_metrics.get("success_by_category", {})
    checks["category_metrics_not_regressed"] = all(
        category in after_categories and after_categories[category] >= score
        for category, score in before_categories.items()
    )

    before_cases = {row.get("id"): row for row in baseline.get("cases", [])}
    after_cases = {row.get("id"): row for row in candidate.get("cases", [])}
    checks["benchmark_cases_match"] = (
        bool(before_cases)
        and len(before_cases) == len(baseline.get("cases", []))
        and len(after_cases) == len(candidate.get("cases", []))
        and before_cases.keys() == after_cases.keys()
    )
    checks["previously_passing_cases_still_pass"] = (
        checks["benchmark_cases_match"] and all(
            after_cases[case_id].get("success") is True
            for case_id, row in before_cases.items()
            if row.get("success") is True
        )
    )

    return {
        "passed": all(checks.values()),
        "checks": checks,
        "regressions": [name for name, passed in checks.items() if not passed],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    args = parser.parse_args()
    try:
        candidate = json.loads(args.candidate.read_text())
        baseline = json.loads(args.baseline.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"passed": False, "error": type(exc).__name__}))
        return 1
    result = compare(candidate, baseline)
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
