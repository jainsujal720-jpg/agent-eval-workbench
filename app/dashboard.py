"""Local browser dashboard for the latest AgentEval report."""

from http.server import BaseHTTPRequestHandler, HTTPServer
import html
import json
from pathlib import Path


REPORT = Path("reports/latest.json")


def safe(value) -> str:
    """Escape a value before displaying it in HTML."""
    return html.escape(str(value))


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/report.json":
            if not REPORT.exists():
                self.send_error(404, "Run the evaluator first")
                return

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(REPORT.read_bytes())
            return

        if self.path != "/":
            self.send_error(404)
            return

        if not REPORT.exists():
            self.send_error(
                404,
                "Run the evaluator first to create reports/latest.json",
            )
            return

        try:
            report = json.loads(REPORT.read_text())
        except (OSError, json.JSONDecodeError) as error:
            self.send_error(500, f"Could not read evaluation report: {error}")
            return

        metrics = report.get("metrics", {})
        cases = report.get("cases", [])
        overall_passed = bool(report.get("passed"))

        rows = []
        for case in cases:
            passed = bool(case.get("success"))
            result_class = "pass" if passed else "fail"
            result_label = "PASS" if passed else "FAIL"

            missing = case.get("missing_expected", [])
            violations = case.get("policy_violations", [])
            details = []

            if missing:
                details.append(
                    "<strong>Missing expected:</strong> "
                    + safe(", ".join(missing))
                )
            if violations:
                details.append(
                    "<strong>Policy violations:</strong> "
                    + safe(", ".join(violations))
                )
            if not details:
                details.append("All case checks passed.")

            rows.append(
                "<tr>"
                f"<td>{safe(case.get('id', ''))}</td>"
                f"<td>{safe(case.get('category', ''))}</td>"
                f"<td><span class='badge {result_class}'>{result_label}</span></td>"
                f"<td>{safe(case.get('expected_tool') or 'none')}</td>"
                f"<td>{safe(case.get('actual_tool') or 'none')}</td>"
                f"<td>{safe(case.get('latency_ms', 0))} ms</td>"
                f"<td>{safe(case.get('answer', ''))}</td>"
                f"<td>{'<br>'.join(details)}</td>"
                "</tr>"
            )

        gate_class = "pass" if overall_passed else "fail"
        gate_label = "PASS" if overall_passed else "FAIL"
        provider = safe(report.get("provider", "unknown"))

        task_rate = float(metrics.get("task_success_rate", 0))
        policy_rate = float(metrics.get("policy_pass_rate", 0))
        tool_rate = float(metrics.get("tool_correctness", 0))
        latency = safe(metrics.get("mean_latency_ms", 0))

        cost_value = float(metrics.get("estimated_cost_usd", 0))
        if provider == "openai" and cost_value == 0:
            cost_label = "Not configured"
        else:
            cost_label = f"${cost_value:.6f}"

        page = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AgentEval Workbench</title>
<style>
:root {
  color-scheme: light;
  --ink: #172033;
  --muted: #64748b;
  --line: #e2e8f0;
  --paper: #ffffff;
  --background: #f4f7fb;
  --green: #147d45;
  --green-bg: #e8f7ee;
  --red: #b42318;
  --red-bg: #fff0ee;
  --blue: #2457c5;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--background);
  color: var(--ink);
  font: 15px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
main { max-width: 1500px; margin: 0 auto; padding: 32px 24px 56px; }
h1 { margin: 0; font-size: 30px; letter-spacing: -0.5px; }
h2 { margin: 30px 0 12px; font-size: 20px; }
.subtitle { margin: 5px 0 22px; color: var(--muted); }
.statusline { margin-bottom: 22px; }
.badge {
  display: inline-block;
  padding: 3px 9px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
}
.pass { color: var(--green); background: var(--green-bg); }
.fail { color: var(--red); background: var(--red-bg); }
.cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  gap: 14px;
}
.card {
  background: var(--paper);
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 17px 19px;
  box-shadow: 0 2px 7px rgba(20, 35, 60, 0.04);
}
.card-label { color: var(--muted); font-size: 13px; }
.card-value { margin-top: 4px; font-size: 25px; font-weight: 700; }
.table-wrap {
  overflow-x: auto;
  background: var(--paper);
  border: 1px solid var(--line);
  border-radius: 12px;
}
table { width: 100%; border-collapse: collapse; min-width: 1050px; }
th, td {
  padding: 12px 14px;
  border-bottom: 1px solid var(--line);
  text-align: left;
  vertical-align: top;
}
th { background: #f8fafc; color: #475569; font-size: 12px; }
tr:last-child td { border-bottom: 0; }
.answer { min-width: 300px; }
.details { min-width: 220px; color: var(--muted); font-size: 13px; }
.links { margin-top: 18px; }
a { color: var(--blue); }
.note { color: var(--muted); font-size: 13px; margin-top: 16px; }
@media (max-width: 600px) {
  main { padding: 22px 14px 40px; }
  h1 { font-size: 25px; }
}
</style>
</head>
<body>
<main>
  <h1>AgentEval Workbench</h1>
  <p class="subtitle">Evaluation report for the latest benchmark run</p>
  <p class="statusline">Provider: <strong>__PROVIDER__</strong>
     &nbsp; Overall gate: <span class="badge __GATE_CLASS__">__GATE_LABEL__</span></p>

  <section class="cards" aria-label="Evaluation metrics">
    <div class="card"><div class="card-label">Task success</div><div class="card-value">__TASK_RATE__</div></div>
    <div class="card"><div class="card-label">Policy pass</div><div class="card-value">__POLICY_RATE__</div></div>
    <div class="card"><div class="card-label">Tool correctness</div><div class="card-value">__TOOL_RATE__</div></div>
    <div class="card"><div class="card-label">Mean latency</div><div class="card-value">__LATENCY__ ms</div></div>
    <div class="card"><div class="card-label">Estimated API cost</div><div class="card-value">__COST__</div></div>
  </section>

  <h2>Scenario results</h2>
  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>Case</th><th>Category</th><th>Result</th>
          <th>Expected route</th><th>Actual route</th><th>Latency</th>
          <th>Agent response</th><th>Check details</th>
        </tr>
      </thead>
      <tbody>__ROWS__</tbody>
    </table>
  </div>

  <p class="links"><a href="/report.json">Download the raw evaluation report (JSON)</a></p>
  <p class="note">This dashboard is served locally on your computer. A passing gate means the run met configured thresholds; review individual failed cases too.</p>
</main>
</body>
</html>
"""

        replacements = {
            "__PROVIDER__": provider,
            "__GATE_CLASS__": gate_class,
            "__GATE_LABEL__": gate_label,
            "__TASK_RATE__": f"{task_rate:.0%}",
            "__POLICY_RATE__": f"{policy_rate:.0%}",
            "__TOOL_RATE__": f"{tool_rate:.0%}",
            "__LATENCY__": latency,
            "__COST__": safe(cost_label),
            "__ROWS__": "".join(rows),
        }
        for marker, value in replacements.items():
            page = page.replace(marker, value)

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(page.encode("utf-8"))


def serve():
    """Serve the dashboard only on this computer."""
    server = HTTPServer(("127.0.0.1", 8000), Handler)
    print("AgentEval dashboard running at http://127.0.0.1:8000")
    print("Press Control-C to stop the server.")
    server.serve_forever()


if __name__ == "__main__":
    serve()