---
title: AgentEval Workbench
emoji: 🧪
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
---

# AgentEval Workbench

A small, portfolio-ready benchmark and CI/CD demo for evaluating AI agent changes before release. The synthetic business is ShopCo, an online retailer with order status, returns, and refund-review support.

## Product problem

Teams can inspect agent runs, but need a repeatable way to tell whether a change to the prompt, tools, model, or code made the agent better or worse. AgentEval runs a fixed benchmark, scores task success and behavior, and can fail a CI build when release criteria are missed.

## What is included

- A deterministic sample support agent with a simulated read-only order lookup (no model key required).
- Synthetic single-turn, multi-turn, authorization, tool-failure, and stress benchmarks for support scenarios.
- A runner that reports task success, policy pass rate, route correctness, latency, access behavior, and estimated cost.
- Threshold-based release gating and machine-readable JSON output.
- Unit tests and GitHub Actions gates for release, authorization, and tool-failure behavior on pushes and pull requests.
- Optional OpenAI-compatible model API adapter, disabled unless explicitly configured.
- Benchmark upload, background evaluation jobs, report history, and a browser dashboard.

## Run locally

Requires Python 3.11+.

```bash
cd agent-eval-workbench
python3 -m app.evaluate --benchmark benchmarks/support.jsonl --output reports/latest.json --save-baseline reports/baseline.json
python -m unittest discover -s tests -v
```

No package installation is needed for the default demo; it uses only the Python standard library. To use pytest, install the development extra with `pip install -e '.[dev]'` when package downloads are available.

The evaluator exits with code `1` when a release threshold fails. That is what causes CI to block a merge/release.

## Optional real model API

By default, the project calls **no external API**. To exercise a real OpenAI-compatible chat completions endpoint, install the optional SDK and set `AGENTEVAL_PROVIDER=openai`, `OPENAI_API_KEY`, and optionally `OPENAI_BASE_URL` and `OPENAI_MODEL`. The live adapter uses function calling to select among three local simulated routes: read-only order lookup, ask for an order ID, or recommend human handoff. The order fixture is synthetic; handoff does not contact anyone. No company systems are called or modified.

```bash
pip install -e '.[openai]'
export AGENTEVAL_PROVIDER=openai
export OPENAI_API_KEY='your-key'
export OPENAI_MODEL='your-model'
python -m app.evaluate --benchmark benchmarks/support.jsonl --output reports/latest.json
```

The adapter sends each case's system policy and user input to the chat completions endpoint. If the model selects a function, the app runs the allow-listed function against local synthetic data and formats the final answer in code. The current flow uses one model request per case. Put the API key in a local environment variable; do not commit it. Configure AGENTEVAL_INPUT_USD_PER_1K and AGENTEVAL_OUTPUT_USD_PER_1K for cost estimates. These are estimates from token usage and configured rates, not provider billing records.

Compare a candidate run with an existing report:

```bash
python3 -m app.evaluate --baseline reports/baseline.json --output reports/candidate.json
```

Open the local dashboard after an evaluation:

```bash
python3 -m app.dashboard
```

Then visit `http://127.0.0.1:8000`.

## Change the benchmark

Each JSONL row contains an `id`, `category`, `input`, `expected_contains` list, `expected_tool` (or `null`), and `must_not_contain` list. Add cases for important user intents and known failures. The synthetic order database contains no real customer data and all simulated operations are read-only.

## CI/CD behavior

`.github/workflows/agent-evaluation.yml` runs unit tests, release, conversation authorization, and tool-failure benchmarks, then uploads reports. Pull requests receive a pass/fail check. The stress benchmark is retained as a known baseline and its expected demo-agent failures do not fail the release gate.

## Product metrics in this prototype

- **Task success rate:** expected key facts appear in the response.
- **Policy pass rate:** prohibited content is absent.
- **Tool correctness:** the expected action/route was selected.
- **Latency:** wall-clock duration for each case.
- **Estimated cost:** token usage multiplied by configured per-token rates (provider adapter only).

These are sample metrics, not universal release standards. Thresholds live in `app/config.py` and should be chosen based on user impact and risk.

## Project brief

See [`docs/PROJECT_BRIEF.md`](docs/PROJECT_BRIEF.md) for product framing, API behavior, CI/CD flow, limitations, and a manual run checklist.

## Workbench improvements and deployment roadmap

See [the hardening roadmap](docs/NEXT_STAGES.md), [company staging API configuration](docs/COMPANY_API_ADAPTER.md), [staging/upload workflow](docs/API_STAGING.md), [the two deployment modes](docs/DEPLOYMENT_MODES.md), the [AWS private-pilot plan](docs/AWS_PRIVATE_PILOT.md), and the [personal AWS synthetic smoke test](docs/AWS_SYNTHETIC_SMOKE_TEST.md). The local dashboard can display AWS task summaries after `python -m app.aws_runs` syncs them from CloudWatch; the dashboard does not connect to AWS itself. The public Hugging Face Space is synthetic-only. The selected private-pilot design runs the session evaluator as a one-shot ECS Fargate task inside the company's AWS network and calls its approved HTTPS staging API. AWS infrastructure for the company pilot is not provisioned yet; this is not a production enterprise dashboard.

## Public interactive demo

This repository includes a Docker Space setup for a public, deterministic demo using synthetic data. It makes no model API calls and does not connect to company systems. Uploads/reports are scoped by a browser session cookie, with a clear-data action and 30-minute idle cleanup. A best-effort detector rejects some credential-shaped uploads; it does not make sensitive uploads safe and it does not guarantee secure erasure. Do not put real customer/company data or credentials in the public Space. For the company-controlled path, run `python3 -m app.session_eval --target company-api` inside the planned private AWS task; by default it writes a summary-only report. The AWS task, networking, and secret integration still need to be implemented and reviewed. See [`docs/AWS_PRIVATE_PILOT.md`](docs/AWS_PRIVATE_PILOT.md), [`docs/DEPLOYMENT_MODES.md`](docs/DEPLOYMENT_MODES.md), and [`docs/SECURITY_AND_ERASURE.md`](docs/SECURITY_AND_ERASURE.md). Do not add a paid model key to an unrestricted public Space.
