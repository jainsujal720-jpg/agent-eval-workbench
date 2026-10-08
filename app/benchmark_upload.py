"""Validated conversation benchmark upload and local staging evaluation."""
import json
import secrets
from pathlib import Path
from app.api_adapter import APISession
from app.session_eval import FAULTS, evaluate_sessions

UPLOADS = Path('benchmarks/uploads')
ROUTES = {'order_lookup','ask_order_id','access_denied','human_handoff','tool_unavailable','tool_invalid_response'}

def validate(text):
    if not isinstance(text,str): raise ValueError('Benchmark content must be text')
    if len(text.encode()) > 262144: raise ValueError('Maximum upload size is 256 KB')
    try:
        cases = json.loads(text) if text.lstrip().startswith('[') else [json.loads(line) for line in text.splitlines() if line.strip()]
    except ValueError as exc: raise ValueError('Invalid JSON or JSONL') from exc
    if not isinstance(cases, list) or not 1 <= len(cases) <= 50: raise ValueError('Supply 1–50 conversation cases')
    ids=set(); total=0
    for case in cases:
        if not isinstance(case, dict): raise ValueError('Each case must be an object')
        if not isinstance(case.get('id'), str) or not case['id'] or case['id'] in ids: raise ValueError('Case IDs must be nonempty and unique')
        ids.add(case['id'])
        if case.get('customer_id') not in {'alice','bob'}: raise ValueError('This staging demo supports alice and bob')
        if not isinstance(case.get('category'), str): raise ValueError('Each case needs a category')
        turns=case.get('turns')
        if not isinstance(turns,list) or not turns: raise ValueError('Each case needs turns')
        total+=len(turns)
        for t in turns:
            if not isinstance(t,dict) or not isinstance(t.get('input'),str) or not t['input'].strip(): raise ValueError('Each turn needs a customer input')
            if t.get('expected_tool') not in ROUTES: raise ValueError('Each turn needs a supported expected_tool')
            for key in ['expected_contains','must_not_contain','expected_accessed_order_ids']:
                if key not in t or not isinstance(t[key],list) or any(not isinstance(x,str) for x in t[key]):
                    if key == 'must_not_contain' and key not in t: continue
                    raise ValueError(key+' must be an explicit list of strings')
            if t.get('fault','none') not in FAULTS: raise ValueError('Unsupported simulated fault')
            if t.get('expected_tool_outcome') not in {None,'not_called','success','timeout','unavailable','invalid_response'}: raise ValueError('Invalid expected tool outcome')
            allowed=t.get('allowed_outcomes')
            if allowed is not None and (not isinstance(allowed,dict) or not allowed or any(k not in ROUTES or not isinstance(v,list) or any(not isinstance(x,str) for x in v) for k,v in allowed.items())): raise ValueError('Invalid allowed_outcomes')
    if total > 100: raise ValueError('Maximum 100 turns per upload')
    return cases

def upload(text):
    cases=validate(text)
    UPLOADS.mkdir(parents=True,exist_ok=True)
    key=secrets.token_hex(12)
    (UPLOADS/(key+'.json')).write_text(json.dumps(cases,indent=2)+'\n')
    return dict(upload_id=key, cases=cases, session_count=len(cases),turn_count=sum(len(c['turns']) for c in cases))

def run(key):
    if not isinstance(key,str) or len(key)!=24 or any(c not in '0123456789abcdef' for c in key): raise ValueError('Invalid upload identifier')
    cases=validate((UPLOADS/(key+'.json')).read_text())
    report=evaluate_sessions(cases,'staging',session_factory=APISession)
    Path('reports').mkdir(exist_ok=True)
    filename='reports/staging-'+secrets.token_hex(8)+'.json'
    Path(filename).write_text(json.dumps(report,indent=2)+'\n')
    Path('reports/session-latest.json').write_text(json.dumps(report,indent=2)+'\n')
    return dict(report_file=filename,passed=report['passed'],metrics=report['metrics'])

PAGE='''<!doctype html><html lang="en"><meta charset="utf-8"><title>AgentEval benchmark upload</title><style>body{font:16px/1.5 system-ui;background:#f4f7fb;color:#172033;max-width:1000px;margin:40px auto;padding:20px}section{background:white;padding:24px;border-radius:12px;margin:20px 0}button,a{margin:8px;color:#2457c5}button{padding:12px}pre{white-space:pre-wrap;overflow-wrap:anywhere}input{font:inherit}</style><h1>Benchmarks &amp; staging tests</h1><nav><a href="/">Single requests</a><a href="/sessions">Conversations</a><a href="/benchmarks">Upload benchmarks</a></nav><section><h2>1. Upload scenarios and expectations</h2><p>Select a JSON array or JSONL conversation benchmark. Maximum 256 KB, 50 conversations, 100 turns. This page supports the synthetic Alice/Bob staging chatbot.</p><input id="file" type="file" accept=".json,.jsonl"><button id="upload">Validate and preview</button></section><section><h2>2. Review and run</h2><p>Target: separate staging chatbot at http://127.0.0.1:8010/chat. Start it in another Terminal tab first. Messages and test faults go to the chatbot; expected outcomes remain in AgentEval.</p><pre id="preview">No benchmark uploaded.</pre><button id="run" disabled>Run staging evaluation</button><p id="status" role="status"></p><a href="/sessions">View conversation results</a></section><script>
let uploadId=null;
const status=document.getElementById('status'),preview=document.getElementById('preview'),runButton=document.getElementById('run');
async function post(url,data){const r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});const result=await r.json();if(!r.ok)throw Error(result.error||'Request failed');return result;}
document.getElementById('upload').onclick=async()=>{runButton.disabled=true;uploadId=null;try{const f=document.getElementById('file').files[0];if(!f)throw Error('Select a benchmark file');if(f.size>262144)throw Error('File exceeds 256 KB');const r=await post('/benchmarks/upload',{text:await f.text()});uploadId=r.upload_id;preview.textContent=JSON.stringify(r.cases,null,2);status.textContent=`Validated ${r.session_count} conversations / ${r.turn_count} turns. Review expectations above.`;runButton.disabled=false;}catch(e){status.textContent=e.message;}};
runButton.onclick=async()=>{runButton.disabled=true;status.textContent='Running evaluation. Keep this page open.';try{const r=await post('/benchmarks/run',{upload_id:uploadId});status.textContent=(r.passed?'PASS':'FAIL')+' — '+JSON.stringify(r.metrics)+' Report: '+r.report_file;}catch(e){status.textContent=e.message;}finally{runButton.disabled=false;}};
</script></html>'''
