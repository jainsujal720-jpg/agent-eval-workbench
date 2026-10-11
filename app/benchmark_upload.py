"""Validated conversation benchmark upload and local staging evaluation."""
import json
import os
import secrets
from pathlib import Path
from app.api_adapter import APISession, staging_target
from app.session_eval import FAULTS, evaluate_sessions
from app.visitor_data import report_directory, upload_path
from app.upload_security import reject_credential_like_content
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

def upload(text,owner=None):
    reject_credential_like_content(text)
    cases=validate(text)
    key=secrets.token_hex(12)
    target=upload_path(key,owner) if owner else UPLOADS/(key+'.json')
    target.parent.mkdir(parents=True,exist_ok=True)
    files=sorted(target.parent.glob('*.json'),key=lambda item:item.stat().st_mtime)
    with JOBS_LOCK:
        protected={job.get('upload_id') for job in JOBS.values() if job.get('status') in {'queued','running'} and job.get('owner')==owner}
    while len(files) >= 20:
        removable=next((item for item in files if item.stem not in protected),None)
        if removable is None: raise ValueError('Upload limit reached while evaluations are running')
        removable.unlink()
        files.remove(removable)
    target.write_text(json.dumps(cases,indent=2)+'\n')
    return dict(upload_id=key, cases=cases, session_count=len(cases),turn_count=sum(len(c['turns']) for c in cases))

def run(key,owner=None):
    if not isinstance(key,str) or len(key)!=24 or any(c not in '0123456789abcdef' for c in key): raise ValueError('Invalid upload identifier')
    source=upload_path(key,owner) if owner else UPLOADS/(key+'.json')
    cases=validate(source.read_text())
    target=staging_target()
    report=evaluate_sessions(cases,'staging',session_factory=APISession)
    report['chatbot_provider']=target['provider']
    report['chatbot_model']=target.get('model')
    output_dir=report_directory(owner)
    output_dir.mkdir(parents=True,exist_ok=True)
    filename=str(output_dir/('staging-'+secrets.token_hex(8)+'.json'))
    Path(filename).write_text(json.dumps(report,indent=2)+'\n')
    if owner is None:
        Path('reports/session-latest.json').write_text(json.dumps(report,indent=2)+'\n')
    return dict(report_file=filename,passed=report['passed'],metrics=report['metrics'],chatbot_provider=target['provider'],chatbot_model=target.get('model'))

PAGE='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>AgentEval benchmark upload</title><style>body{font:16px/1.5 system-ui;background:#f4f7fb;color:#172033;max-width:1000px;margin:40px auto;padding:20px}section{background:white;padding:24px;border-radius:12px;margin:20px 0}button,a{margin:8px;color:#2457c5}button{padding:12px}pre{white-space:pre-wrap;overflow-wrap:anywhere}input{font:inherit}.warning{background:#fff4d7;padding:12px;border-radius:8px}</style><h1>AgentEval public demo</h1><nav><a href="/">Home</a><a href="/sessions">Conversations</a><a href="/benchmarks">Upload benchmarks</a><a href="/benchmark-history">Run history</a></nav><section><h2>1. Choose test scenarios</h2><p>This public demo uses a deterministic chatbot and synthetic Alice/Bob fixtures. It makes no model API calls and connects to no company systems. Upload a JSON array or JSONL conversation benchmark (maximum 256 KB, 50 conversations, 100 turns), or <a href="/sample-benchmark">download the sample benchmark</a>.</p><p class="warning"><strong>Public demo:</strong> uploads and reports are private to your browser session and automatically deleted after 30 minutes without activity or when you clear them. Still upload only synthetic or public test data; never upload customer information, credentials, or confidential company data.</p><input id="file" type="file" accept=".json,.jsonl"><button id="upload">Validate and preview</button></section><section><h2>2. Review and run</h2><p>Review the expected outcomes before you run. Only one evaluation can run at a time. Uploads and report history are temporary and may be cleared when the Space restarts.</p><pre id="preview">No benchmark uploaded.</pre><button id="run" disabled>Run evaluation</button><p id="status" role="status"></p><a href="/sessions">View conversation results</a> · <a href="/benchmark-history">Run history</a></section><script>
let uploadId=null;
const status=document.getElementById('status'),preview=document.getElementById('preview'),runButton=document.getElementById('run');
async function post(url,data){const r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});const result=await r.json();if(!r.ok)throw Error(result.error||'Request failed');return result;}
document.getElementById('upload').onclick=async()=>{runButton.disabled=true;uploadId=null;try{const f=document.getElementById('file').files[0];if(!f)throw Error('Select a benchmark file');if(f.size>262144)throw Error('File exceeds 256 KB');const r=await post('/benchmarks/upload',{text:await f.text()});uploadId=r.upload_id;preview.textContent=JSON.stringify(r.cases,null,2);status.textContent=`Validated ${r.session_count} conversations / ${r.turn_count} turns. Review expectations above.`;runButton.disabled=false;}catch(e){status.textContent=e.message;}};
runButton.onclick=async()=>{runButton.disabled=true;status.textContent='Starting evaluation…';try{const started=await post('/benchmarks/run',{upload_id:uploadId});let r;do{await new Promise(resolve=>setTimeout(resolve,700));const response=await fetch('/benchmarks/jobs/'+started.job_id);r=await response.json();if(r.status==='running'||r.status==='queued')status.textContent=`${r.status}: ${r.completed_turns||0} / ${r.total_turns||'…'} turns`; }while(r.status==='running'||r.status==='queued');if(r.status==='failed')throw Error('Evaluation failed ('+r.error+'). Check chatbot service and credentials.');const result=r.result;status.textContent=(result.passed?'PASS':'FAIL')+' — chatbot: '+result.chatbot_provider+(result.chatbot_model?' / '+result.chatbot_model:'')+' — '+JSON.stringify(result.metrics)+' Report: '+result.report_file+' — refresh Run history to view past runs.';}catch(e){status.textContent=e.message;}finally{runButton.disabled=false;}};
</script></html>'''

# In-memory job registry for small local demos. Reports persist in reports/.
import threading
import time
JOBS = {}
JOBS_LOCK = threading.Lock()

def enqueue(key,owner=None):
    if not isinstance(key,str) or len(key)!=24 or any(c not in '0123456789abcdef' for c in key): raise ValueError('Invalid upload identifier')
    source=upload_path(key,owner) if owner else UPLOADS/(key+'.json')
    if not source.is_file(): raise ValueError('Uploaded benchmark has expired or was cleared; upload it again')
    job_id=secrets.token_hex(12)
    with JOBS_LOCK:
        if any(job.get('status') in {'queued','running'} for job in JOBS.values()):
            raise ValueError('An evaluation is already running; wait for it to finish before starting another')
        JOBS[job_id]={'id':job_id,'upload_id':key,'owner':owner,'status':'queued','completed_turns':0,'total_turns':None,'created_at':time.time()}
    def work():
        with JOBS_LOCK: JOBS[job_id]['status']='running'
        try:
            cases=validate(source.read_text())
            with JOBS_LOCK: JOBS[job_id]['total_turns']=sum(len(c['turns']) for c in cases)
            def progress(done,total):
                with JOBS_LOCK: JOBS[job_id]['completed_turns']=done
            target=staging_target()
            report=evaluate_sessions(cases,'staging',session_factory=APISession,progress_callback=progress)
            report.update(chatbot_provider=target['provider'],chatbot_model=target.get('model'),created_at=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()))
            output_dir=report_directory(owner)
            output_dir.mkdir(parents=True,exist_ok=True)
            filename=str(output_dir/('staging-'+secrets.token_hex(8)+'.json'))
            Path(filename).write_text(json.dumps(report,indent=2)+'\n')
            if owner is None:
                Path('reports/session-latest.json').write_text(json.dumps(report,indent=2)+'\n')
            with JOBS_LOCK:
                report_name=Path(filename).name if owner else filename
                JOBS[job_id].update(status='completed',result={'report_file':report_name,'passed':report['passed'],'metrics':report['metrics'],'chatbot_provider':target['provider'],'chatbot_model':target.get('model')})
        except Exception as exc:
            with JOBS_LOCK: JOBS[job_id].update(status='failed',error=type(exc).__name__)
    threading.Thread(target=work,daemon=True).start()
    return job_id

def job_status(job_id,owner=None):
    with JOBS_LOCK:
        job=JOBS.get(job_id)
        if not job or job.get('owner')!=owner: return None
        visible=dict(job)
        visible.pop('owner',None)
        visible.pop('upload_id',None)
        return visible

HISTORY_PAGE='''<!doctype html><html lang="en"><meta charset="utf-8"><title>AgentEval run history</title><style>body{font:16px/1.5 system-ui;background:#f4f7fb;color:#172033;max-width:1100px;margin:40px auto;padding:20px}section{background:white;padding:20px;border-radius:12px;margin:12px 0}a{color:#2457c5}</style><h1>Benchmark run history</h1><nav><a href="/benchmarks">Upload benchmarks</a> · <a href="/sessions">Latest conversation report</a></nav><div id="runs">Loading reports…</div><script>fetch('/benchmarks/history.json').then(r=>r.json()).then(rows=>{const root=document.getElementById('runs');root.textContent='';if(!rows.length){root.textContent='No saved runs yet.';return;}for(const x of rows){const section=document.createElement('section'),summary=document.createElement('div');summary.textContent=`${x.created_at||'Date unavailable'} · ${x.chatbot_provider||'unknown'} ${x.chatbot_model||''} · ${x.passed?'PASS':'FAIL'} · ${x.metrics?.turn_count||0} turns · ${x.metrics?.failed_turn_count||0} failed · `;const view=document.createElement('a');view.href='/sessions?report='+encodeURIComponent(x.file);view.textContent='Open report';const download=document.createElement('a');download.href='/reports/'+encodeURIComponent(x.file);download.textContent='Download JSON';section.append(summary,view,document.createTextNode(' · '),download);root.append(section);}}).catch(()=>document.getElementById('runs').textContent='Could not load report history.');</script></html>'''

if os.getenv('AGENTEVAL_SPACE_DEMO') == '1':
    _clear_control='<button type="button" onclick="clearDemoData()">Clear my data</button>'
    _clear_script='<script>async function clearDemoData(){if(!confirm("Delete your uploads and reports now?"))return;const r=await fetch("/privacy/clear",{method:"POST",headers:{"Content-Type":"application/json"},body:"{}"});if(r.ok)location.href="/benchmarks";else alert((await r.json()).error||"Could not clear data")}</script>'
    PAGE=PAGE.replace('</nav>','</nav>'+_clear_control).replace('</script></html>',_clear_script+'</script></html>')
    HISTORY_PAGE=HISTORY_PAGE.replace('</nav>','</nav>'+_clear_control).replace('</script></html>',_clear_script+'</script></html>')
