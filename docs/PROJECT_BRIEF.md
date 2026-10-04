# AgentEval Workbench: project brief

## User and problem

The target user is an AI product/engineering team changing an agent's prompt, tools, or implementation. They need evidence that a change improved behavior and did not introduce a regression before release. The demonstration scenario is ShopCo, a synthetic online retailer.

## Product hypothesis

If teams can run a stable task set automatically on every proposed change and inspect failures by case, they can catch regressions earlier and make release decisions with clearer evidence.

## What the demo implements

The demo defines JSONL test cases, runs a reproducible support workflow with a simulated read-only order lookup, scores expected answer phrases, prohibited phrases and expected routes, summarizes metrics by category, compares a candidate report to a baseline, and exits nonzero when thresholds fail. A local dashboard shows metrics and case-level traces. GitHub Actions runs tests and the benchmark on pushes and pull requests, then uploads a JSON report.

## APIs and external services

- **Default path:** no external model API is called. The sample agent is local and deterministic.
- **Optional live path:** with `AGENTEVAL_PROVIDER=openai`, the runner uses the official Python SDK and OpenAI-compatible Chat Completions function calling. The model can select a simulated read-only order lookup, an order-ID clarification, or a recommended human handoff. Only local fixture logic runs; no real order system is called and no human is contacted. Tool-using cases generally require two model requests (selection and final response). Authentication uses `OPENAI_API_KEY`; endpoint/model are configurable with `OPENAI_BASE_URL` and `OPENAI_MODEL`.
- **CI service:** GitHub Actions runs hosted workflow jobs; checkout/setup-python/upload-artifact are GitHub-maintained actions. This is not an AI API call.

## Product metrics and release gate

Task success checks expected phrases, policy pass checks prohibited phrases are absent, tool correctness checks expected routing, and mean latency is measured locally. The live adapter reports token-based cost only when rates are configured. Initial thresholds are deliberately illustrative; a real product team must set them from user impact, risk tolerance, and baseline measurements.

## Current limitations

- Phrase matching is a transparent starter evaluator, not semantic grading.
- The live adapter uses simulated tools but has no human evaluation step and is nondeterministic.
- The synthetic benchmark is small and does not establish production readiness.
- The dashboard is a local-only development viewer; this workspace blocks local port binding, so its HTTP flow must be verified on the owner's machine.
- No deployment is configured. The workflow acts as a CI quality gate; deployment should be added only after choosing a target environment and a release strategy.
- Model pricing is not embedded because pricing changes; configured rates can become stale and must be verified by the project owner.

## Manual steps for the owner

1. Run locally using the README commands and inspect `reports/latest.json`.
2. Create a GitHub repository and push this folder if you want hosted CI. Add `.github/workflows/agent-evaluation.yml` to the repository root.
3. Open a pull request or push a commit to see the CI check and uploaded report.
4. Improve the benchmark with realistic cases, expected routes, and reviewed failure examples.
5. Only if desired, configure the live API environment variables and install the optional SDK. Keep API keys in environment variables or GitHub Secrets; never commit them.
6. If you want automatic deployment, choose a hosting target, then add a deploy job that depends on the passing evaluation job.

## Suggested next product iteration

Add a baseline comparison: persist a known-good report, compare each pull request against it, and mark significant metric regressions separately from absolute threshold failures. That lets the product answer whether this change got better or worse, rather than only whether it crossed a fixed bar.
