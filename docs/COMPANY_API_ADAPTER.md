# Configuring a company staging API

AgentEval can call an approved HTTPS staging endpoint without changing the evaluator. For a company pilot, run it inside the company's approved private environment and inject the API token into the process from its secret manager. Do not type a real token into a shell command, save it in a `.env` file, or put it in the benchmark. The process reads the token from its environment and does not write it to benchmark or report files.

```bash
export AGENTEVAL_CHAT_URL='https://staging.example.com/support/chat'
# AGENTEVAL_AUTH_TOKEN is injected by the approved runtime secret manager.
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

For the company-controlled CI/API pilot and public demo separation, see [`DEPLOYMENT_MODES.md`](DEPLOYMENT_MODES.md). Hugging Face Spaces is for the synthetic public demo only; never place a real company token or confidential benchmark there.
