# Tool failures and input mistakes

Separate benchmark: benchmarks/support_failures.jsonl (16 conversations, 20 turns).
Fault injection is configured by the test harness, not by customer messages.

Injected conditions: timeout, service unavailable, missing status, invalid status,
malformed payload, and a response for the wrong order. No network outage is
created; this is a controlled local fixture service. Ownership is checked before
calling that service. Incomplete or mismatched responses never produce order
facts. Expected outages get a fallback and next step; unexpected exceptions still
fail evaluation. A valid authorized ID survives a temporary failure so a retry
can fetch fresh data. This does not implement automatic retries or backoff.

Input cases: misspelled ordinary words, malformed IDs, wrong digits, missing ID
separator, prefix collisions, and correction after clarification. Ordinary words
can be interpreted by meaning. Identifiers must not be guessed or shortened.
These are examples, not exhaustive language coverage.

Reports include injected_fault, tool_outcome, expected_tool_outcome,
tool_outcome_correct, and handled_tool_failure_count. accessed_order_ids means
validated records returned to the application; it does not mean a backend was
never contacted. Ownership checks use trusted local fixtures in this demo;
a production service must enforce authorization independently.

Run:
 AGENTEVAL_PROVIDER=demo python3 -m app.session_eval --benchmark benchmarks/support_failures.jsonl --output reports/failure-demo.json
 AGENTEVAL_PROVIDER=openai python3 -m app.session_eval --benchmark benchmarks/support_failures.jsonl --output reports/failure-openai.json

Live routing makes one model request per turn. Tool failures are simulated in
both providers; live mode does not test actual OpenAI outages. The model selects
routing before the tool runs; final fallback wording is formatted in code.

Copy a report into reports/session-latest.json and restart the dashboard process
to load the updated viewer. Existing report files remain separate baselines.
CI discovers the new unit tests; no additional live API workflow is configured.
