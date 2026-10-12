# AgentEval Workbench

A small, portfolio-ready benchmark and CI/CD demo for evaluating AI agent changes before release. The synthetic business is ShopCo, an online retailer with order status, returns, and refund-review support.

## Product problem

Teams can inspect agent runs, but need a repeatable way to tell whether a change to the prompt, tools, model, or code made the agent better or worse. AgentEval runs a fixed benchmark, scores task success and behavior, and can fail a CI build when release criteria are missed.

## What is included

- A deterministic sample support agent with a simulated read-only order lookup (no model key required).
- Synthetic single-turn, multi-turn, authorization, tool-failure, and stress benchmarks for support scenarios.
- A runner that reports task success, policy pass rate, route correctness, latency, access behavior, and estimated cost.
- Threshold-based release gating and machine-readable JSON output.
- Unit tests and GitHub Actions gates for release, authorization, tool-failure, and stress behavior on pushes and pull requests.
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

The dashboard is a report viewer: opening or refreshing it does not run an evaluation. A one-message report is written to `reports/latest.json`; a multi-turn conversation report is written to `reports/session-latest.json`. A case is one message, while a conversation contains several turns.

If port 8000 is already in use, stop the older dashboard with Control-C in its Terminal tab, or start this one on another port:

```bash
python3 -m app.dashboard --port 8001
```

## Interactive local upload workflow

To upload a conversation benchmark, review its expected behavior, run it against the synthetic staging chatbot, and view the report, open two Terminal tabs in the project folder.

Terminal tab 1:

```bash
python3 -m app.staging_api --provider demo
```

Terminal tab 2:

```bash
python3 -m app.dashboard --port 8001
```

Open `http://127.0.0.1:8001/benchmarks`, choose a conversation JSON or JSONL file, select **Validate and preview**, review the cases, then select **Run evaluation**. Use **Multi-turn conversations** to inspect results and **Run history** to reopen saved reports. This local workflow uses synthetic Alice/Bob fixtures and makes no model API calls. If port 8010 is occupied, stop the old staging service with Control-C before starting another one.

For the single-message benchmark, run the evaluator command first, then refresh the dashboard:

```bash
AGENTEVAL_PROVIDER=demo python3 -m app.evaluate --benchmark benchmarks/support.jsonl --output reports/latest.json
```

## Local Docker demo

The interactive synthetic demo also runs locally in Docker; Hugging Face hosting is optional and is not required. From the project folder:

```bash
docker build -t agenteval-space .
docker run --rm -p 7861:7860 agenteval-space
```

Open `http://127.0.0.1:7861`. Using host port 7861 avoids a conflict if another app already uses 7860. Press Control-C in that Terminal tab to stop the container. This demo pins the chatbot to deterministic synthetic fixtures; it does not call OpenAI or company systems.

## Change the benchmark

Each JSONL row contains an `id`, `category`, `input`, `expected_contains` list, `expected_tool` (or `null`), and `must_not_contain` list. Add cases for important user intents and known failures. The synthetic order database contains no real customer data and all simulated operations are read-only.

## CI/CD behavior

`.github/workflows/agent-evaluation.yml` runs unit tests, release, conversation authorization, tool-failure, and stress benchmarks, then uploads reports. The stress benchmark is blocking: it must meet the evaluator's release thresholds and not regress from the recorded baseline. Any failed gate makes the workflow fail. A separate CI job builds the local synthetic Docker image, starts it, and checks that its benchmark page and sample download respond. CI uses synthetic data and does not call OpenAI or AWS. To block merges in GitHub, configure branch protection for `main` to require both `evaluate-agent` and `docker-smoke` checks; a failed workflow alone does not prevent a direct push to `main`.

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

See [the hardening roadmap](docs/NEXT_STAGES.md), [company staging API configuration](docs/COMPANY_API_ADAPTER.md), [staging/upload workflow](docs/API_STAGING.md), [deployment modes](docs/DEPLOYMENT_MODES.md), the [AWS private-pilot plan](docs/AWS_PRIVATE_PILOT.md), and the [personal AWS synthetic smoke test](docs/AWS_SYNTHETIC_SMOKE_TEST.md). The local dashboard can display AWS task summaries after `python3 -m app.aws_runs` syncs them from CloudWatch; the dashboard does not connect to AWS itself. The AWS private-pilot infrastructure for a company is not provisioned; this is not a production enterprise dashboard.

## Demo and data boundaries

The Docker demo above is local and synthetic-only. It has not been deployed as a Hugging Face Space; the account's Space setup page currently requires a paid plan to select Docker or Gradio. No subscription is needed for local Docker use. Treat any public hosted demo as synthetic/public-data only: upload checks are best-effort, and browser scoping or clear-data controls do not guarantee secure erasure. Do not upload real customer/company data or credentials. The company-controlled path requires an approved private environment, staging API, secret injection, report storage, and security review before any real company data is considered. See [`docs/AWS_PRIVATE_PILOT.md`](docs/AWS_PRIVATE_PILOT.md), [`docs/DEPLOYMENT_MODES.md`](docs/DEPLOYMENT_MODES.md), and [`docs/SECURITY_AND_ERASURE.md`](docs/SECURITY_AND_ERASURE.md). Do not add a paid model key to an unrestricted public demo.
