# Configuring a company staging API

AgentEval can call an approved HTTPS staging endpoint without changing the evaluator. Set these environment variables in the Terminal tab that starts the dashboard (the API token is read by that process and is never saved in benchmark files):

```bash
export AGENTEVAL_CHAT_URL='https://staging.example.com/support/chat'
export AGENTEVAL_AUTH_TOKEN='your-staging-token'
export AGENTEVAL_AUTH_HEADER='Authorization'
export AGENTEVAL_AUTH_SCHEME='Bearer'
export AGENTEVAL_CUSTOMER_FIELD='customer_id'
export AGENTEVAL_MESSAGE_FIELD='message'
export AGENTEVAL_SESSION_FIELD='session_id'
export AGENTEVAL_RESPONSE_ANSWER_FIELD='answer'
export AGENTEVAL_RESPONSE_ROUTE_FIELD='trace.route'
export AGENTEVAL_RESPONSE_SESSION_FIELD='session_id'
export AGENTEVAL_RESPONSE_ACCESSED_FIELD='trace.accessed_order_ids'
export AGENTEVAL_TARGET_PROVIDER='company-staging'
export AGENTEVAL_TARGET_MODEL='your-model-name'
```

Restart the dashboard after setting them. `AGENTEVAL_HEALTH_URL` is optional; when set, it supplies JSON metadata including a `provider` field. Without it, provider/model labels come from `AGENTEVAL_TARGET_PROVIDER` and `AGENTEVAL_TARGET_MODEL`.

The endpoint must use HTTPS, except localhost during development. The adapter sends one JSON POST per turn. Request field names, auth header/scheme, and dotted response-field paths are configurable. Expected phrases and expected routes remain inside AgentEval. By default, simulated faults are sent only to localhost; use `AGENTEVAL_FAULT_FIELD` only for a company-approved staging fault-injection contract.

Responses must include an answer string, final route string, conversation/session ID string, and an accessed-order IDs list (which may be empty). Mapping the actual access trace is required to make authorization checks meaningful. A chat API that only returns answer text can be tested for text expectations, but it cannot substantiate tool routing or data-access checks and therefore is not accepted by this strict adapter until the company exposes those traces or the evaluator contract is deliberately changed.

The benchmark's `customer_id` is test input. A company must map it to a real test identity through its approved staging authentication mechanism; do not let a production service trust this JSON field as proof of identity. Never use production credentials, customer data, or a real refund/handoff endpoint for this demo. `AGENTEVAL_HTTP_TIMEOUT_SECONDS` defaults to 120. Company endpoint connectivity and auth are tested only against a company-approved staging environment.

For current environment variable names and the deployment sequence, see `docs/NEXT_STAGES.md`. Hugging Face Spaces hosting is intentionally the next deployment milestone after the four implementation priorities are tested and merged.
