# AgentEval Workbench

A small, portfolio-ready benchmark and CI/CD demo for evaluating AI agent changes before release. The synthetic business is ShopCo, an online retailer with order status, returns, and refund-review support.

## Product problem

Teams can inspect agent runs, but need a repeatable way to tell whether a change to the prompt, tools, model, or code made the agent better or worse. AgentEval runs a fixed benchmark, scores task success and behavior, and can fail a CI build when release criteria are missed.

## What is included

- A deterministic sample support agent with a simulated read-only order lookup (no model key required).
- A six-case realistic synthetic benchmark covering refund policy, missing information, order status, and security handoff.
- A runner that reports success rate, policy pass rate, tool correctness, latency, and estimated cost.
- Threshold-based release gating and machine-readable JSON output.
- Unit tests and a GitHub Actions workflow triggered on pushes and pull requests.
- Optional OpenAI-compatible model API adapter, disabled unless explicitly configured.
- Baseline metric comparison and a local browser dashboard.

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

By default, the project calls **no external API**. To exercise a real OpenAI-compatible chat completions endpoint, install the optional SDK and set `AGENTEVAL_PROVIDER=openai`, `OPENAI_API_KEY`, and optionally `OPENAI_BASE_URL` and `OPENAI_MODEL`. The adapter tests model-generated text against the scenario but does not call company tools or mutate any data.

```bash
pip install -e '.[openai]'
export AGENTEVAL_PROVIDER=openai
export OPENAI_API_KEY='your-key'
export OPENAI_MODEL='your-model'
python -m app.evaluate --benchmark benchmarks/support.jsonl --output reports/latest.json
```

The adapter sends each case's system policy and user input to `POST /chat/completions` via the SDK. Put the key in a local environment variable; do not commit it. Provider/model pricing is deliberately not guessed: configure `AGENTEVAL_INPUT_USD_PER_1K` and `AGENTEVAL_OUTPUT_USD_PER_1K` for cost estimates. These are estimates from usage tokens and the configured rates, not provider billing records.

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

`.github/workflows/agent-evaluation.yml` runs unit tests, executes the benchmark, and uploads the report. Pull requests receive a pass/fail check. To deploy after successful evaluation, add a separate deploy job with the deployment action and credentials for your chosen host; this starter intentionally stops at the release gate.

## Product metrics in this prototype

- **Task success rate:** expected key facts appear in the response.
- **Policy pass rate:** prohibited content is absent.
- **Tool correctness:** the expected action/route was selected.
- **Latency:** wall-clock duration for each case.
- **Estimated cost:** token usage multiplied by configured per-token rates (provider adapter only).

These are sample metrics, not universal release standards. Thresholds live in `app/config.py` and should be chosen based on user impact and risk.

## Project brief

See [`docs/PROJECT_BRIEF.md`](docs/PROJECT_BRIEF.md) for product framing, API behavior, CI/CD flow, limitations, and a manual run checklist.
