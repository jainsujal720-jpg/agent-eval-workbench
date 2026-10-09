"""Local dashboard for single-request and conversation reports."""
import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
import html
import json
import re
from pathlib import Path
from urllib.parse import urlsplit, parse_qs

REPORT = Path('reports/latest.json')
SESSION_REPORT = Path('reports/session-latest.json')


def safe(value):
    return html.escape(str(value), quote=True)


def badge(passed):
    return '<span class="badge '+('pass' if passed else 'fail')+'">'+('PASS' if passed else 'FAIL')+'</span>'


STYLE = '''
:root{color-scheme:light}*{box-sizing:border-box}body{margin:0;background:#f4f7fb;color:#172033;font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}main{max-width:1450px;margin:auto;padding:30px 24px}h1{margin:0;font-size:30px}h2{font-size:21px}.muted{color:#64748b}nav{display:flex;gap:12px;margin:20px 0}nav a,.button{padding:9px 16px;border:1px solid #d7e0ec;border-radius:9px;background:white;text-decoration:none;color:#2457c5}nav a.active{background:#2457c5;color:white}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(165px,1fr));gap:12px;margin:20px 0}.card,.conversation{background:white;border:1px solid #e2e8f0;border-radius:12px;padding:18px}.value{font-size:26px;font-weight:700}.badge{display:inline-block;border-radius:20px;padding:3px 10px;font-size:12px;font-weight:700}.pass{color:#147d45;background:#e8f7ee}.fail{color:#b42318;background:#fff0ee}.guard{color:#855100;background:#fff4d7}.table-wrap{overflow:auto;background:white;border:1px solid #e2e8f0;border-radius:12px}table{width:100%;border-collapse:collapse;min-width:900px}th,td{text-align:left;vertical-align:top;padding:12px;border-bottom:1px solid #e2e8f0}th{background:#f8fafc}a{color:#2457c5}.conversation{margin:18px 0}summary{cursor:pointer;font-weight:700;font-size:18px}.turn{margin-top:16px;padding-top:16px;border-top:1px solid #e2e8f0}.bubble{padding:12px 16px;border-radius:10px;background:#f1f5f9;margin:8px 0;white-space:pre-wrap;overflow-wrap:anywhere}.reply{background:#eef5ff}.turn-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px}.detail{padding:10px;background:#f8fafc;border-radius:8px;overflow-wrap:anywhere}pre{white-space:pre-wrap;overflow-wrap:anywhere;margin:4px 0}label,select{font:inherit}select{padding:7px;border:1px solid #cbd5e1;border-radius:6px}.note{font-size:13px;color:#64748b}@media(max-width:600px){main{padding:20px 12px}h1{font-size:25px}}
'''


def checks(case):
    details=[]
    for key,label in [('missing_expected','Missing expected'),('policy_violations','Forbidden text')]:
        if case.get(key):
            details.append(label+': '+', '.join(str(x) for x in case[key]))
    if case.get('tool_correct') is False: details.append('Route check failed')
    if case.get('access_correct') is False: details.append('Access check failed')
    if case.get('tool_outcome_correct') is False: details.append('Tool outcome check failed')
    if case.get('error'): details.append('Agent error: '+str(case['error']))
    if not details: details.append('All checks passed' if case.get('success') else 'Case failed; inspect raw report')
    return '<br>'.join(safe(d) for d in details)


def card(label,value):
    return f'<div class="card"><div class="muted">{safe(label)}</div><div class="value">{safe(value)}</div></div>'


def render_report(report, sessions=False, filter_mode='all'):
    nav='<nav><a href="/" class="'+('' if sessions else 'active')+'">Single requests</a><a href="/sessions" class="'+('active' if sessions else '')+'">Conversations</a><a href="/benchmarks">Upload benchmarks</a><a href="/benchmark-history">Run history</a></nav>'
    title='Conversation evaluation' if sessions else 'Single-request evaluation'
    body='<h1>AgentEval Workbench</h1>'+nav+f'<h2>{title}</h2>'
    if report is None:
        filename='reports/session-latest.json' if sessions else 'reports/latest.json'
        body+=f'<div class="card">No report available. Save a report to <strong>{filename}</strong>, then refresh.</div>'
    else:
        metrics=report.get('metrics',{});cases=report.get('cases',[])
        body+=f'<p>Provider: <strong>{safe(report.get("provider","unknown"))}</strong> &nbsp; Overall gate: {badge(bool(report.get("passed")))}</p>'
        if report.get('chatbot_provider'):
            body+='<p>Chatbot provider: <strong>'+safe(report['chatbot_provider'])+'</strong> · Model: '+safe(report.get('chatbot_model') or 'deterministic demo')+'</p>'
        if sessions:
            cards=[('Conversations',metrics.get('session_count','Unavailable')),('Turns',metrics.get('turn_count','Unavailable')),('Failed turns',metrics.get('failed_turn_count','Unavailable')),('Access check failures',metrics.get('access_check_failure_count','Unavailable')),('Guard interventions',metrics.get('guard_intervention_count','Unavailable')),('Agent errors',metrics.get('error_count','Unavailable')),('Handled tool failures',metrics.get('handled_tool_failure_count','Not recorded'))]
            body+='<div class="cards">'+''.join(card(*c) for c in cards)+'</div>'
            body+='<p class="note">Results measure the combined model and application workflow. A guard intervention is not automatically a model error. Access checks compare actual and expected reads; they are not a complete security certification.</p>'
            options=[('all','All turns'),('failed','Failed turns'),('guards','Guard interventions')]
            body+='<form method="get" action="/sessions"><label for="filter">Show: </label><select id="filter" name="filter">'+''.join(f'<option value="{v}"'+(' selected' if filter_mode==v else '')+f'>{l}</option>' for v,l in options)+'</select> <button class="button" type="submit">Apply</button></form>'
            groups={}
            for c in cases: groups.setdefault(c.get('session_id','Unknown session'),[]).append(c)
            visible=0
            for name,turns in groups.items():
                shown=[t for t in turns if filter_mode=='all' or (filter_mode=='failed' and not t.get('success')) or (filter_mode=='guards' and t.get('guard_reason'))]
                if not shown: continue
                visible+=len(shown)
                body+=f'<details class="conversation" open><summary>{safe(name)} &nbsp; {badge(all(t.get("success") for t in turns))}</summary><p class="muted">Customer: {safe(turns[0].get("customer_id","unknown"))} · {len(turns)} turns total</p>'
                for t in shown:
                    allowed=t.get('allowed_outcomes')
                    expected=', '.join(allowed) if allowed else t.get('expected_tool','none')
                    model=t.get('model_choice')
                    model_text=json.dumps(model,indent=2) if model is not None else 'Not recorded in this report'
                    guard=t.get('guard_reason') or 'No intervention'
                    body+=f'<article class="turn"><strong>Turn {safe(t.get("turn",""))}</strong> {badge(bool(t.get("success")))}'
                    if t.get('guard_reason'): body+=' <span class="badge guard">Guard applied</span>'
                    body+=f'<div class="bubble"><strong>Customer</strong>\n{safe(t.get("input",""))}</div><div class="bubble reply"><strong>Agent</strong>\n{safe(t.get("answer",""))}</div><div class="turn-grid">'
                    for label,value in [('Expected route(s)',expected),('Final route',t.get('actual_tool') or 'none'),('Model choice',model_text),('Guard reason',guard),('Injected fault',t.get('injected_fault','Not recorded')),('Tool outcome',t.get('tool_outcome','Not recorded')),('Expected tool outcome',t.get('expected_tool_outcome') or 'Not specified'),('Attempted order',t.get('attempted_order_id') or 'none'),('Accessed orders',json.dumps(t.get('accessed_order_ids',[]))),('Expected accessed orders',json.dumps(t.get('expected_accessed_order_ids',[])))]:
                        body+=f'<div class="detail"><strong>{safe(label)}</strong><pre>{safe(value)}</pre></div>'
                    body+='</div><p>'+checks(t)+'</p></article>'
                body+='</details>'
            if not visible: body+='<p>No turns match this filter.</p>'
        else:
            cost=metrics.get('estimated_cost_usd')
            cost_label='Not configured' if cost is None or (report.get('provider')=='openai' and cost==0) else f'${cost:.6f}'
            cards=[('Task success',f'{metrics.get("task_success_rate",0):.1%}'),('Policy pass',f'{metrics.get("policy_pass_rate",0):.1%}'),('Tool correctness',f'{metrics.get("tool_correctness",0):.1%}'),('Mean latency',str(metrics.get('mean_latency_ms','Unavailable'))+' ms'),('Estimated API cost',cost_label)]
            body+='<div class="cards">'+''.join(card(*c) for c in cards)+'</div><div class="table-wrap"><table><thead><tr><th>Case</th><th>Category</th><th>Result</th><th>Expected route</th><th>Actual route</th><th>Response</th><th>Latency</th><th>Checks</th></tr></thead><tbody>'
            for c in cases:
                body+='<tr>'+''.join(f'<td>{safe(c.get(k) or "none")}</td>' for k in ['id','category'])+'<td>'+badge(bool(c.get('success')))+'</td>'+''.join(f'<td>{safe(c.get(k) or "none")}</td>' for k in ['expected_tool','actual_tool','answer'])+'<td>'+safe(c.get('latency_ms','Unavailable'))+' ms</td><td>'+checks(c)+'</td></tr>'
            body+='</tbody></table></div>'
        download='/session-report.json' if sessions else '/report.json'
        body+=f'<p><a href="{download}">Download raw report (JSON)</a></p>'
    body+='<p class="note">Local report viewer. Refresh after replacing a report. Opening this page does not run tests or call a model API.</p>'
    return '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>AgentEval Workbench</title><style>'+STYLE+'</style></head><body><main>'+body+'</main></body></html>'


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        from app.benchmark_upload import upload, enqueue
        if self.headers.get('Content-Type','').split(';')[0] != 'application/json':
            self.send_error(415); return
        origin=self.headers.get('Origin')
        expected='http://'+self.headers.get('Host','')
        if origin and origin != expected:
            self.send_error(403); return
        code=200
        try:
            size=int(self.headers.get('Content-Length','0'))
            if not 0 < size <= 524288: raise ValueError('Invalid upload size')
            data=json.loads(self.rfile.read(size))
            if self.path == '/benchmarks/upload': result=upload(data['text'])
            elif self.path == '/benchmarks/run':
                result={'job_id':enqueue(data['upload_id'])}; code=202
            else: self.send_error(404); return
        except (ValueError,KeyError,TypeError,OSError) as exc:
            result={'error': str(exc) if isinstance(exc,ValueError) else 'Could not process benchmark request'};code=400
        self.send_response(code)
        self.send_header('Content-Type','application/json')
        self.end_headers(); self.wfile.write(json.dumps(result).encode())
    def do_GET(self):
        parsed=urlsplit(self.path)
        if parsed.path == '/benchmarks':
            from app.benchmark_upload import PAGE
            self.send_response(200); self.send_header('Content-Type','text/html; charset=utf-8')
            self.end_headers(); self.wfile.write(PAGE.encode()); return
        from app.benchmark_upload import job_status
        if parsed.path.startswith('/benchmarks/jobs/'):
            job=job_status(parsed.path.rsplit('/',1)[-1])
            if not job: self.send_error(404); return
            self.send_response(200); self.send_header('Content-Type','application/json'); self.send_header('Cache-Control','no-store')
            self.end_headers(); self.wfile.write(json.dumps(job).encode()); return
        if parsed.path == '/benchmark-history':
            from app.benchmark_upload import HISTORY_PAGE
            self.send_response(200); self.send_header('Content-Type','text/html; charset=utf-8'); self.send_header('Cache-Control','no-store')
            self.end_headers(); self.wfile.write(HISTORY_PAGE.encode()); return
        if parsed.path == '/benchmarks/history.json':
            reports=Path('reports'); rows=[]
            for candidate in sorted(reports.glob('staging-*.json'),key=lambda f:f.stat().st_mtime,reverse=True)[:100]:
                try:
                    item=json.loads(candidate.read_text())
                    rows.append({'file':candidate.name,'created_at':item.get('created_at'),'chatbot_provider':item.get('chatbot_provider'),'chatbot_model':item.get('chatbot_model'),'passed':item.get('passed'),'metrics':item.get('metrics',{})})
                except (OSError,ValueError): continue
            self.send_response(200); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Cache-Control','no-store')
            self.end_headers(); self.wfile.write(json.dumps(rows).encode()); return
        if parsed.path.startswith('/reports/'):
            name=parsed.path.removeprefix('/reports/')
            if not re.fullmatch(r'staging-[a-f0-9]+\.json',name): self.send_error(404); return
            target=Path('reports')/name
            if not target.is_file(): self.send_error(404); return
            self.send_response(200); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Content-Disposition','attachment; filename="'+name+'"')
            self.end_headers(); self.wfile.write(target.read_bytes()); return
        sessions=parsed.path in {'/sessions','/session-report.json'}
        if parsed.path not in {'/','/sessions','/report.json','/session-report.json'}:
            self.send_error(404);return
        path=SESSION_REPORT if sessions else REPORT
        report_name=parse_qs(parsed.query).get('report',[''])[0]
        if sessions and report_name:
            if not re.fullmatch(r'staging-[a-f0-9]+\.json',report_name):
                self.send_error(400,'Invalid report name'); return
            path=Path('reports')/report_name
        raw=parsed.path.endswith('.json')
        try:
            report=json.loads(path.read_text()) if path.exists() else None
            if report is not None and (not isinstance(report,dict) or not isinstance(report.get('metrics'),dict) or not isinstance(report.get('cases'),list)):
                raise ValueError('Invalid report structure')
            if report is not None and (('session_count' in report['metrics']) != sessions):
                raise ValueError('Wrong report type for this view')
        except (OSError,ValueError):
            self.send_error(500,'Could not read a valid report for this view');return
        if raw and report is None:
            self.send_error(404,'No report available');return
        mode=parse_qs(parsed.query).get('filter',['all'])[0]
        if mode not in {'all','failed','guards'}:mode='all'
        data=(json.dumps(report,indent=2)+'\n') if raw else render_report(report,sessions,mode)
        self.send_response(200)
        self.send_header('Content-Type','application/json; charset=utf-8' if raw else 'text/html; charset=utf-8')
        self.send_header('Cache-Control','no-store')
        self.end_headers();self.wfile.write(data.encode())


def serve():
    parser=argparse.ArgumentParser()
    parser.add_argument('--port',type=int,default=8000)
    args=parser.parse_args()
    with HTTPServer(('127.0.0.1',args.port),Handler) as server:
        print(f'AgentEval dashboard running at http://127.0.0.1:{args.port}')
        print('Press Control-C to stop the server.')
        try:server.serve_forever()
        except KeyboardInterrupt:print('\nDashboard stopped.')

if __name__=='__main__':serve()
