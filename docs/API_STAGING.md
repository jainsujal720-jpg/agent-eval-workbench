# Upload and staging chatbot demonstration

The dashboard now accepts conversation JSONL files or JSON arrays. Each case includes id, customer_id, category, and turns. Each turn requires input, expected_tool, expected_contains (list), and expected_accessed_order_ids (list). Optional fields: must_not_contain, allowed_outcomes, fault, expected_tool_outcome. Required empty lists must be written explicitly. The single-request benchmark format is not accepted by this page yet.

## Start locally

Terminal tab 1, project root:

```bash
python3 -m app.staging_api
```

Terminal tab 2, project root (stop old dashboard with Control-C first):

```bash
python3 -m app.dashboard --port 8001
```

Visit http://127.0.0.1:8001/benchmarks . Choose benchmarks/support_failures.jsonl, validate and review the preview, then Run staging evaluation. Open Conversations to inspect results. On the Mac file picker, Command-Shift-G opens Go to Folder; paste ~/Downloads/agent-eval-workbench/benchmarks/ .

Expected demo result: staging provider, 16 sessions, 20 turns, zero failures/errors, nine handled tool failures. No OpenAI calls are made. The report is saved with a unique name under reports and also becomes reports/session-latest.json. Existing uniquely named reports remain intact. Uploads are saved under benchmarks/uploads using generated names. Do not commit uploads or reports containing customer data.

## What crosses the API

APISession sends POST http://127.0.0.1:8010/chat with message, customer_id, session_id, and simulated fault. The service returns session_id plus answer and execution traces. Expected phrases, expected routes, and expected reads remain in the evaluator. Session IDs isolate conversations. The evaluator uses exact route/access/tool checks and phrase-based answer checks.

Both servers bind localhost. The shared demo bearer token defaults to local-demo-token. You may set AGENTEVAL_STAGING_TOKEN to the same value in both Terminal tabs. This is a local fixture harness, not production authentication: the harness supplies alice/bob identities, and the service uses the same deterministic support logic as our demo agent. It is a real HTTP boundary, not an independent new model. Fault injection exists only for synthetic testing. A passing benchmark proves the supplied checks passed, not complete production safety.

## Company adaptation

Replace the adapter's fixed URL and request/response mapping with the company's staging API contract. Use its real test authentication; do not trust customer identity from chat messages. Obtain trusted tool/access traces if you want to evaluate records used. Fault injection should use company-approved staging controls. Add company policies and fixtures to benchmarks. The current upload page targets only this local staging service and does not execute arbitrary URLs or uploaded code.

Evaluation runs synchronously; 100 turns maximum, each HTTP call has a 10-second timeout. An unavailable service produces failed/error rows rather than a pass. A background job runner would be needed for larger or slow company evaluations.

## Verification

```bash
python3 -m unittest discover -s tests -v
```

Tests include real local HTTP requests, session isolation, failure injection, upload/run/report flow, benchmark rejection, and all existing regression tests. GitHub integration and CI configuration are unchanged by this update.

## OpenAI mode behind the HTTP API

Stop the staging service with Control-C. In that same Terminal tab, ensure OPENAI_API_KEY is set, then start:

```bash
python3 -m app.staging_api --provider openai
```

The default model is gpt-4o-mini; OPENAI_MODEL and OPENAI_BASE_URL override the model/endpoint. Missing keys or SDK stop startup with a clear error. Install the optional SDK with python3 -m pip install -e '.[openai]' if required. Keep the key only in the service environment, never in uploads or the browser. This makes paid requests using the existing session function-calling implementation, one request per turn. Guards, order service faults, and final formatting still execute locally. No real orders, refunds, or handoffs occur.

Restart the dashboard after applying this update. Upload and run the same support_failures.jsonl benchmark. Report provider remains staging (HTTP transport); chatbot_provider is openai and chatbot_model records the configured model. Both appear on the results page. New reports preserve earlier demo reports. The upload page also displays the provider/model after the run. The dashboard does not select or hold the OpenAI key.

The adapter checks /health before running; an unavailable staging service produces an immediate upload-page error. Requests have 120-second HTTP timeouts; the OpenAI SDK uses a 45-second request timeout and no automatic retries. The synchronous dashboard can remain busy during an evaluation. Provider errors become failed evaluation turns, not passing fallbacks. No live OpenAI call is made by unit tests; provider propagation is tested over HTTP with mocked model selection.
