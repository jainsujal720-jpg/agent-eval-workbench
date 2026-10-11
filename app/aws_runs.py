"""Sync summary-only ECS evaluation logs into a local dashboard report."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys


DEFAULT_LOG_GROUP = '/agenteval/synthetic-smoke'
DEFAULT_OUTPUT = Path('reports/aws-runs.json')
METRIC_KEYS = (
    'session_count', 'turn_count', 'failed_turn_count',
    'access_check_failure_count', 'error_count',
    'handled_tool_failure_count', 'guard_intervention_count',
)


def _aws_json(*arguments):
    result = subprocess.run(
        ['aws', *arguments, '--output', 'json'],
        check=True, capture_output=True, text=True,
    )
    return json.loads(result.stdout or '{}')


def _read_summary(messages):
    """Extract the first JSON summary object from CloudWatch log messages."""
    text='\n'.join(str(message) for message in messages).lstrip()
    if not text:
        raise ValueError('empty log stream')
    summary, _ = json.JSONDecoder().raw_decode(text)
    if not isinstance(summary,dict) or not isinstance(summary.get('passed'),bool):
        raise ValueError('log stream does not begin with an evaluation summary')
    if not isinstance(summary.get('metrics'),dict):
        raise ValueError('evaluation summary has no metrics')
    metrics={key:summary['metrics'][key] for key in METRIC_KEYS if key in summary['metrics']}
    cases=[]
    for item in summary.get('cases',[]):
        if not isinstance(item,dict) or not isinstance(item.get('case_number'),int):
            continue
        case={'case_number':item['case_number']}
        for key in ('success','tool_correct','access_correct','tool_outcome_correct',
                    'has_policy_violations','has_missing_expectations','has_error'):
            if key in item:
                case[key]=bool(item[key])
        cases.append(case)
    return {'provider':str(summary.get('provider','unknown')),
            'passed':summary['passed'],'metrics':metrics,'cases':cases}


def _safe_saved_run(run):
    """Keep only summary fields when retaining a previous local dashboard run."""
    if not isinstance(run,dict):
        return None
    safe={}
    for key in ('run_id','last_event_utc','summary_available'):
        if key in run and isinstance(run[key],(str,bool)):
            safe[key]=run[key]
    if not safe.get('run_id'):
        return None
    if run.get('summary_available') is True:
        safe.update({
            'provider':str(run.get('provider','unknown')),
            'passed':bool(run.get('passed')),
            'metrics':{key:value for key,value in run.get('metrics',{}).items()
                       if key in METRIC_KEYS and isinstance(value,(int,float))},
            'cases':[],
        })
        for item in run.get('cases',[]):
            if not isinstance(item,dict) or not isinstance(item.get('case_number'),int):
                continue
            case={'case_number':item['case_number']}
            for key in ('success','tool_correct','access_correct','tool_outcome_correct',
                        'has_policy_violations','has_missing_expectations','has_error'):
                if key in item:
                    case[key]=bool(item[key])
            safe['cases'].append(case)
    else:
        safe['summary_available']=False
    return safe


def sync_cloudwatch_runs(region='ap-south-1', log_group=DEFAULT_LOG_GROUP,
                         output=DEFAULT_OUTPUT):
    """Fetch task summaries, discard log text, and save a local history file."""
    response=_aws_json('logs','describe-log-streams','--log-group-name',log_group,
                       '--order-by','LastEventTime','--descending','--limit','50',
                       '--region',region)
    runs=[]
    for stream in response.get('logStreams',[]):
        stream_name=stream.get('logStreamName','')
        if not stream_name:
            continue
        last_ms=stream.get('lastEventTimestamp')
        last_utc=(datetime.fromtimestamp(last_ms/1000,timezone.utc).isoformat()
                  if isinstance(last_ms,(int,float)) else None)
        run={'run_id':stream_name.rsplit('/',1)[-1],
             'last_event_utc':last_utc or 'Unavailable',
             'summary_available':False}
        try:
            events=_aws_json('logs','get-log-events','--log-group-name',log_group,
                             '--log-stream-name',stream_name,'--start-from-head',
                             '--limit','10000','--region',region)
            summary=_read_summary([event.get('message','') for event in events.get('events',[])])
            run.update(summary)
            run['summary_available']=True
        except (ValueError,KeyError,TypeError,json.JSONDecodeError,subprocess.CalledProcessError):
            # Never copy raw log events or AWS error text into the dashboard file.
            pass
        runs.append(run)
    output=Path(output)
    # The stack's CloudWatch log group is deleted during cleanup. Retain prior
    # content-free local summaries so a later stack recreation does not erase
    # dashboard history.
    previous=[]
    try:
        old=json.loads(output.read_text())
        if old.get('source')=='aws-cloudwatch' and old.get('region')==region and old.get('log_group')==log_group:
            previous=[clean for item in old.get('runs',[])
                      if (clean:=_safe_saved_run(item)) is not None]
    except (OSError,json.JSONDecodeError,AttributeError,TypeError):
        pass
    combined=[]
    seen=set()
    for item in runs+previous:
        clean=_safe_saved_run(item)
        if clean is None or clean['run_id'] in seen:
            continue
        seen.add(clean['run_id'])
        combined.append(clean)
    report={'source':'aws-cloudwatch','region':region,'log_group':log_group,
            'synced_at':datetime.now(timezone.utc).isoformat(),'runs':combined[:100]}
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2)+'\n')
    return report


def main(argv=None):
    parser=argparse.ArgumentParser(description='Import summary-only AgentEval ECS runs from CloudWatch for the local dashboard.')
    parser.add_argument('--region',default=os.getenv('AWS_REGION') or os.getenv('AWS_DEFAULT_REGION') or 'ap-south-1')
    parser.add_argument('--log-group',default=DEFAULT_LOG_GROUP)
    parser.add_argument('--output',type=Path,default=DEFAULT_OUTPUT)
    args=parser.parse_args(argv)
    try:
        report=sync_cloudwatch_runs(args.region,args.log_group,args.output)
    except FileNotFoundError:
        parser.error('AWS CLI was not found. Install AWS CLI v2 and retry.')
    except subprocess.CalledProcessError:
        parser.error('AWS CLI could not read the log group. Check your sign-in, region, permissions, and that the stack logs still exist.')
    except (json.JSONDecodeError,OSError) as exc:
        parser.error(f'Could not save or parse the summary report: {exc}')
    available=sum(bool(run.get('summary_available')) for run in report['runs'])
    print(json.dumps({'saved_to':str(args.output),'runs_found':len(report['runs']),
                      'summaries_read':available,'region':args.region},indent=2))
    if not report['runs']:
        print('No log streams found. The stack may have been deleted, or no task has run.')
        return 1
    return 0 if available else 1


if __name__=='__main__':
    raise SystemExit(main())
