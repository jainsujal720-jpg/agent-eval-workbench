# Synthetic session testing

Separate experimental harness: app/session_eval.py. Existing single-turn
app/agent.py and app/evaluate.py remain unchanged.

Eight conversations, eighteen turns cover refund clarification, pronoun
follow-ups, corrected IDs, multiple-order clarification, cross-customer denial,
identity spoofing, session isolation, and unknown-order enumeration.

Alice owns A-1001 and A-1002; Bob owns B-2001. These are synthetic fixtures.
Customer identity is supplied by the harness, never inferred from customer text.
The local order service checks ownership before returning order details.
Unknown and unauthorized IDs share a denial response to avoid revealing existence.
Every turn checks response text, route, and exact accessed-order IDs. Any failure
blocks the gate. Access-check failures include missing/wrong expected reads;
the count alone should not be interpreted as confirmed data disclosure.

Demo mode uses deterministic routing. OpenAI mode uses conversation history to
select an action and intent, followed by the same server-side fixture checks.
Each turn makes one model request; the complete live suite makes 18 requests.
Final answers are formatted in code. This tests model routing and local controls,
not arbitrary generated chatbot answers or a real company's customer API.

No real login, OAuth, persistent database, production access control, or external
chatbot adapter is implemented. The caller-provided identity is a simulated
trusted authentication boundary; a deployment must obtain identity from its
verified authentication middleware.

Run:
  AGENTEVAL_PROVIDER=demo python3 -m app.session_eval --output reports/session-demo.json
  AGENTEVAL_PROVIDER=openai python3 -m app.session_eval --output reports/session-openai.json

Session reports have their own schema. Do not copy them into reports/latest.json:
the existing dashboard does not yet support conversation reports. Review raw JSON
and printed failing turns. Unit tests automatically enter the existing CI test
step; a separate live session CI workflow is not configured.

## Expectation review after the first live baseline

The initial live run passed 16/18 turns with zero access-check failures.
Identity spoofing produced safe human escalation rather than explicit denial.
That case now permits either denial or escalation, with route-specific required
wording, forbidden order-status text, and an unchanged empty accessed-order list.
This is a reviewed expectation change, not an agent-only improvement; before/after
aggregate scores are not directly comparable without accounting for this change.

The denied follow-up still requires clarification. OpenAI routing now receives
trusted active-order state; a denial clears that state. Raw conversation history
alone previously allowed the model to resolve pronouns to a denied order.

## Server-enforced workflow (v3)

The v2 live run still had two routing failures and no unauthorized reads.
The session now enforces denial when the current message explicitly supplies
one inaccessible order ID, and clarification when a model attempts lookup with
no current explicit ID and no active order. Ownership remains server-enforced.
For these cases, inaccessible explicit orders take precedence over model escalation.
Every successful turn records model_choice and guard_reason. The aggregate
includes guard_intervention_count. A passing result measures the combined
model-plus-application workflow; it is not proof that raw model routing passed.
Guard count includes normal enforcement and is not itself a model-error count.
Multi-ID requests remain subject to model clarification and the ownership check.
