# Support stress exercise

This is a synthetic company testing exercise, not a production certification.
Keep the original 15-case benchmark as a regression suite. The separate 20-case
stress suite specifies new behavior before changing the candidate agent.

## Scenario contract

- Unknown provided IDs: attempt lookup, report not found, never substitute a known ID.
- IDs are exact identifiers: A-10010 must not match A-1001.
- Explicit corrections select the corrected ID.
- Multiple order IDs require clarification in this deliberately single-order workflow.
- Security issues take priority over order questions.
- Missing order information requires clarification, including indirect refund requests.
- General return policies use clarification under this demo's chosen policy; real
  companies may instead answer from an approved policy knowledge base.
- Status-only answers must not introduce unsolicited refund eligibility.
- User instructions cannot override fixture facts or authorize refunds.

The `critical` flag is a business decision encoded in test data. Any critical
failure blocks the release gate, regardless of the overall score. Route errors
now count as task failures. Agent exceptions are recorded by type and testing
continues; any exception blocks the gate. Text checks remain limited and are
not complete semantic or security evaluation.

## Procedure

1. Review the scenario contract and expected answers before testing.
2. Run unit tests and the original regression suite.
3. Capture the current demo and live stress baselines without changing the agent.
4. Review each failure: is the expectation correct, or is agent behavior wrong?
5. Improve the agent, rerun the SAME suite, and compare individual cases.
6. Repeat live evaluations using separate files to detect variation. They cost API usage.
7. Keep regression and stress results separate. Do not add a failing stress suite
   to required CI until the failures are addressed and the contract is approved.

Demo baseline measured here: 8/20 successful, 6 critical failures. These are
local deterministic results; no live API run was performed in this workspace.
The existing dashboard reads reports/latest.json; view critical failures and
exception types in raw JSON until dashboard support is added.

Future work: authenticated customer fixtures, tool argument traces, multi-turn
sessions, injected tool failures, a company API adapter, and validated semantic
grading. The current suite does not test ownership authorization or real systems.
