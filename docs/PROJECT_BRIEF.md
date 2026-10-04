# AgentEval Workbench: project brief

## User and problem

An AI product or engineering team changes an agent prompt, tools, or implementation. They need evidence that changes improve behavior without regressions. The demo uses ShopCo, a synthetic retailer.

## Product hypothesis

A stable task set run on each proposed change helps catch regressions and makes release decisions clearer.

## What the demo implements

JSONL cases exercise a reproducible support workflow with a simulated read-only order lookup. The evaluator scores expected phrases, prohibited phrases and routes, summarizes metrics by category, compares reports to a baseline, and exits nonzero when thresholds fail. A local dashboard shows metrics and case-level traces. GitHub Actions runs tests and benchmarks on pushes and pull requests, then uploads a JSON report.

## APIs and external services

- Default path: no external model API is called; the sample agent is local and deterministic.
- Optional live path: with AGENTEVAL_PROVIDER=openai, the runner makes one OpenAI-compatible Chat Completions API request per benchmark case using the official Python SDK. Authentication uses OPENAI_API_KEY; endpoint and model are configurable. Only synthetic user input and a fixed system instruction are sent. The live adapter does not execute tools.
- CI service: GitHub Actions runs hosted workflow jobs using GitHub-maintained checkout, setup-python and upload-artifact actions.

## Metrics and limits

Task success checks expected phrases; policy pass checks prohibited phrases; tool correctness checks expected routing; latency is measured locally. Cost is estimated from token usage only when rates are configured. Thresholds are illustrative. Phrase matching is not semantic grading, the live adapter has no tool calling or human review, and the synthetic benchmark is small. The dashboard is local only and no deployment is configured. Verify configured model pricing because it changes.

## Manual steps

1. Clone the repository, run README commands, and inspect reports/latest.json.
2. Push a commit or open a pull request to see CI and its uploaded report.
3. Expand the benchmark with realistic, reviewed cases and routes.
4. If using the optional live API, install the SDK and store keys in environment variables or GitHub Secrets, never in source.
5. Choose a hosting target before adding deployment.

## Suggested next iteration

Compare pull requests against a known-good baseline and flag meaningful metric regressions separately from absolute threshold failures.
