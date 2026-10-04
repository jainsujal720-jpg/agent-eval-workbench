"""Tiny local report viewer; serves the latest JSON evaluation report."""

from http.server import BaseHTTPRequestHandler, HTTPServer
import html
import json
from pathlib import Path

REPORT = Path("reports/latest.json")


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/report.json":
            if not REPORT.exists():
                self.send_error(404, "Run the evaluator first")
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(REPORT.read_bytes())
            return
        if self.path != "/":
            self.send_error(404)
            return
        if not REPORT.exists():
            self.send_error(404, "Run the evaluator first to create reports/latest.json")
            return
        report = json.loads(REPORT.read_text())
        rows = "".join(
            "<tr>"
            f"<td>{html.escape(str(r['id']))}</td>"
            f"<td>{html.escape(str(r.get('category', '')))}</td>"
            f"<td>{'PASS' if r['success'] else 'FAIL'}</td>"
            f"<td>{html.escape(str(r.get('actual_tool') or 'none'))}</td>"
            f"<td>{r['latency_ms']} ms</td>"
            f"<td>{html.escape(str(r['answer']))}</td></tr>"
            for r in report["cases"]
        )
        m = report["metrics"]
        gate_class = "pass" if report["passed"] else "fail"
        gate_text = "PASS" if report["passed"] else "FAIL"
        page = """<!doctype html><meta charset='utf-8'><title>AgentEval Workbench</title>
        <style>body{{font:15px system-ui;margin:36px;background:#f4f7fb;color:#152238}}h1{{margin-bottom:4px}}.cards{{display:flex;gap:12px;flex-wrap:wrap}}.card{{background:white;padding:16px 20px;border-radius:12px;box-shadow:0 2px 8px #dce3ed}}table{{width:100%;background:white;border-collapse:collapse;margin-top:20px}}td,th{{padding:10px;border-bottom:1px solid #e3e8ef;text-align:left;vertical-align:top}}.pass{{color:#147d45}}.fail{{color:#bf3030}}</style>
        <h1>AgentEval Workbench</h1><p>Provider: PROVIDER · Overall gate: <b class='GATE_CLASS'>GATE_TEXT</b></p>
        <div class='cards'><div class='card'>Task success<br><b>TASK_RATE</b></div><div class='card'>Policy pass<br><b>POLICY_RATE</b></div><div class='card'>Tool correctness<br><b>TOOL_RATE</b></div><div class='card'>Mean latency<br><b>LATENCY ms</b></div><div class='card'>Estimated cost<br><b>$COST</b></div></div>
        <h2>Scenario runs</h2><table><tr><th>Case</th><th>Category</th><th>Result</th><th>Route</th><th>Latency</th><th>Agent response</th></tr>ROWS</table>
        <p><a href='/report.json'>Download raw evaluation report (JSON)</a></p>"""
        page = page.replace("PROVIDER", html.escape(str(report.get("provider", "unknown"))))
        page = page.replace("GATE_CLASS", gate_class).replace("GATE_TEXT", gate_text).replace("ROWS", rows)
        page = page.replace("TASK_RATE", f"{m['task_success_rate']:.0%}").replace("POLICY_RATE", f"{m['policy_pass_rate']:.0%}")
        page = page.replace("TOOL_RATE", f"{m['tool_correctness']:.0%}").replace("LATENCY", str(m["mean_latency_ms"]))
        page = page.replace("COST", f"{m['estimated_cost_usd']:.6f}")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(page.encode("utf-8"))


def serve():
    HTTPServer(("127.0.0.1", 8000), Handler).serve_forever()


if __name__ == "__main__":
    serve()
