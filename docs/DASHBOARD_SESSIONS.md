# Conversation dashboard

Reports remain separate:
- reports/latest.json: single-request report
- reports/session-latest.json: conversation report

Copy an existing session report, then start the server:

    cp reports/session-openai-v3.json reports/session-latest.json
    python3 -m app.dashboard --port 8001

Open http://127.0.0.1:8001/sessions. The port option lets an older server remain
on 8000 while inspecting the new dashboard. Ctrl-C stops cleanly.

Conversations show customer identity, inputs, responses, expected routes,
original model choices, final routes, attempted/accessed order IDs, guard
reasons, and failed checks. Filter to failed turns or guard interventions.
Filters do not change the overall gate or summary metrics. Download links
return the full selected report. Missing traces in older reports are marked
as not recorded, rather than inferred.

The viewer rereads files per page load. Refresh after replacing a report.
It does not run evaluations or make model API calls. Customer text is escaped
before rendering. The server binds only to 127.0.0.1. Existing single-request
reports keep their own view. Session reports do not include latency or cost,
so those metrics are not displayed for conversations.

All 29 unit/integration tests passed locally. Browser visual inspection on
the user's Mac remains part of applying this update.
