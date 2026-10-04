"""Run a benchmark and enforce CI release thresholds."""

import argparse
import json
import os
import statistics
import time
from pathlib import Path

from app import config
from app.agent import selected_agent


def load_cases(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def evaluate_case(case: dict, agent) -> dict:
    started = time.perf_counter()
    result = agent(case["input"])
    latency_ms = round((time.perf_counter() - started) * 1000, 2)
    answer = result.answer.lower()
    missing = [phrase for phrase in case.get("expected_contains", []) if phrase.lower() not in answer]
    prohibited = [phrase for phrase in case.get("must_not_contain", []) if phrase.lower() in answer]
    expected_tool = case.get("expected_tool")
    return {
        "id": case["id"], "success": not missing and not prohibited,
        "missing_expected": missing, "policy_violations": prohibited,
        "tool_correct": expected_tool is None or result.tool == expected_tool,
        "expected_tool": expected_tool, "actual_tool": result.tool,
        "category": case.get("category", "uncategorized"),
        "answer": result.answer, "latency_ms": latency_ms,
        "input_tokens": result.input_tokens, "output_tokens": result.output_tokens,
    }


def run_evaluation(cases: list[dict], agent=None, provider="demo") -> dict:
    if agent is None:
        agent, provider = selected_agent()
    rows = [evaluate_case(case, agent) for case in cases]
    n = max(len(rows), 1)
    mean_latency = round(statistics.mean(r["latency_ms"] for r in rows), 2) if rows else 0
    input_rate = float(os.getenv("AGENTEVAL_INPUT_USD_PER_1K", "0"))
    output_rate = float(os.getenv("AGENTEVAL_OUTPUT_USD_PER_1K", "0"))
    estimated_cost = sum(r["input_tokens"] * input_rate + r["output_tokens"] * output_rate for r in rows) / 1000
    categories = sorted({r["category"] for r in rows})
    by_category = {
        category: round(sum(r["success"] for r in rows if r["category"] == category) /
                        max(sum(1 for r in rows if r["category"] == category), 1), 4)
        for category in categories
    }
    metrics = {
        "case_count": len(rows),
        "task_success_rate": round(sum(r["success"] for r in rows) / n, 4),
        "policy_pass_rate": round(1 - sum(bool(r["policy_violations"]) for r in rows) / n, 4),
        "tool_correctness": round(sum(r["tool_correct"] for r in rows) / n, 4),
        "mean_latency_ms": mean_latency,
        "estimated_cost_usd": round(estimated_cost, 8), "success_by_category": by_category,
    }
    checks = {
        "task_success_rate": metrics["task_success_rate"] >= config.MIN_TASK_SUCCESS_RATE,
        "policy_pass_rate": metrics["policy_pass_rate"] >= config.MIN_POLICY_PASS_RATE,
        "tool_correctness": metrics["tool_correctness"] >= config.MIN_TOOL_CORRECTNESS,
        "mean_latency_ms": metrics["mean_latency_ms"] <= config.MAX_MEAN_LATENCY_MS,
    }
    return {"passed": all(checks.values()), "provider": provider, "metrics": metrics, "thresholds": {
        "min_task_success_rate": config.MIN_TASK_SUCCESS_RATE,
        "min_policy_pass_rate": config.MIN_POLICY_PASS_RATE,
        "min_tool_correctness": config.MIN_TOOL_CORRECTNESS,
        "max_mean_latency_ms": config.MAX_MEAN_LATENCY_MS,
    }, "checks": checks, "cases": rows}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", type=Path, default=Path("benchmarks/support.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("reports/latest.json"))
    parser.add_argument("--baseline", type=Path, help="Compare with an earlier JSON evaluation report")
    parser.add_argument("--save-baseline", type=Path, help="Save passing or failing report as a baseline snapshot")
    args = parser.parse_args()
    agent, provider = selected_agent()
    report = run_evaluation(load_cases(args.benchmark), agent=agent, provider=provider)
    if args.baseline and args.baseline.exists():
        baseline = json.loads(args.baseline.read_text())
        before, after = baseline["metrics"], report["metrics"]
        report["baseline_comparison"] = {
            "baseline_provider": baseline.get("provider", "unknown"),
            "task_success_rate_delta": round(after["task_success_rate"] - before["task_success_rate"], 4),
            "policy_pass_rate_delta": round(after["policy_pass_rate"] - before["policy_pass_rate"], 4),
            "tool_correctness_delta": round(after["tool_correctness"] - before["tool_correctness"], 4),
            "mean_latency_ms_delta": round(after["mean_latency_ms"] - before["mean_latency_ms"], 2),
            "estimated_cost_usd_delta": round(after["estimated_cost_usd"] - before["estimated_cost_usd"], 8),
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    if args.save_baseline:
        args.save_baseline.parent.mkdir(parents=True, exist_ok=True)
        args.save_baseline.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"passed": report["passed"], "metrics": report["metrics"], "checks": report["checks"]}, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
