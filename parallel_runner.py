#!/usr/bin/env python3
"""Portable bounded controller for prepared, disjoint worker checkpoints.

Designed for macOS/Linux. Credentials stay in separately supplied local files.
Use at most four workers per process; multi-machine allocation is manual.
"""
import argparse,fcntl,hashlib,json,os,re,signal,sqlite3,subprocess,sys,time
from contextlib import contextmanager
from pathlib import Path
import worker_distribution as w
from provider_budget import check_zenrows_cap

def atomic(path,data):
    tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');tmp.replace(path)
@contextmanager
def database(path):
    db=sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True,timeout=5)
    try:yield db
    finally:db.close()
def snapshot(folder):
    with database(folder/'checkpoint.sqlite3') as db:
        states=dict(db.execute('select status,count(*) from details group by status'))
        bars=[r[0] for r in db.execute("select distinct q.baro from details d join queries q on q.id=d.query_id where d.status in ('pending','running','verification','failed') and d.failures<3 order by q.baro")]
    return {'done':states.get('done',0),'states':states,'bars':bars}
def validate_selection(manifest,selected):
    available={a['worker'] for a in manifest['assignments']}
    selected=sorted(set(selected or available))
    if not selected or len(selected)>4 or not set(selected)<=available:
        raise ValueError('Select 1..4 prepared worker IDs; use distinct IDs on each machine')
    return selected
def phase_transition(state,progress,expected_stop):
    if expected_stop:return
    state['cursor']+=1;state['no_progress']=0 if progress else state['no_progress']+1
    state['retry_after']=time.time()+(60*2**(state['no_progress']-1) if not progress and state['no_progress'] else 0)
    if state['no_progress']>=3:state['stop_reason']='three_phases_without_progress'

def run(args):
    root=Path(args.directory).resolve();manifest=json.loads((root/'manifest.json').read_text())
    selected=validate_selection(manifest,args.worker)
    w.verify_outputs(manifest,root)
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,48}',args.run_id):raise ValueError('Invalid run ID')
    if args.seconds<1 or args.solver_tasks<1 or args.credit_cap<1:raise ValueError('Positive runtime and budgets required')
    connection=Path(args.connection_file).resolve();solver=Path(args.solver_file).resolve()
    if not connection.is_file() or not solver.is_file():raise ValueError('Private connection and solver files required')
    endpoint=json.loads(connection.read_text())['cdp_endpoint']
    def budget():return check_zenrows_cap(endpoint,args.credit_cap)
    latest=budget();locks=[];active={};stop=False;reason='time_limit_reached'
    tag=args.run_id+'-'+'-'.join(map(str,selected));state_path=root/f'parallel-state-{tag}.json'
    report_path=root/f'parallel-report-{tag}.json';log_path=root/f'parallel-events-{tag}.jsonl'
    state=json.loads(state_path.read_text()) if state_path.exists() else {
        'plan_id':manifest['plan_id'],'selected':selected,'seconds_limit':args.seconds,'credit_cap':args.credit_cap,
        'solver_limit':args.solver_tasks,'elapsed_seconds':0,'initial_key_credits':latest['used_credits'],
        'workers':{str(i):{'initial_done':snapshot(root/f'worker-{i:02d}')['done'],'cursor':i-1,'no_progress':0} for i in selected}}
    if any(state[k]!=v for k,v in [('plan_id',manifest['plan_id']),('selected',selected),('seconds_limit',args.seconds),('credit_cap',args.credit_cap),('solver_limit',args.solver_tasks)]):
        raise ValueError('Controller configuration differs; use the same arguments to resume or an explicit new run ID')
    prior=state['elapsed_seconds'];started=time.monotonic();next_start=0;next_budget=0;unreadable=0
    def interrupted(signum,frame):
        nonlocal stop,reason
        stop=True;reason='interrupted'
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    def completed(i):return snapshot(root/f'worker-{i:02d}')['done']
    def finish(i,entry,planned=False):
        entry['log'].close();progress=completed(i)-entry['before']
        phase_transition(state['workers'][str(i)],progress,planned or entry['p'].returncode==130)
        with log_path.open('a') as f:f.write(json.dumps({'worker':i,'bar':entry['bar'],'exit_code':entry['p'].returncode,'new_completed':progress,'planned_stop':planned})+'\n')
    def report(status):
        rows={str(i):snapshot(root/f'worker-{i:02d}') for i in selected}
        elapsed=min(args.seconds,prior+time.monotonic()-started)
        new=sum(rows[str(i)]['done']-state['workers'][str(i)]['initial_done'] for i in selected)
        data={'status':status,'elapsed_seconds':round(elapsed,2),'remaining_seconds':round(max(0,args.seconds-elapsed),2),
            'new_completed_profiles':new,'profiles_per_minute':round(new*60/elapsed,3) if elapsed else 0,
            'key_credit_delta':latest['used_credits']-state['initial_key_credits'],'provider_budget':latest,
            'credit_attribution':'Shared key delta includes all other use and any usage during a pause; provider billing may lag.',
            'running_workers':len(active),'workers':rows}
        state['elapsed_seconds']=elapsed;atomic(state_path,state);atomic(report_path,data);return data
    try:
        for i in selected:
            folder=root/f'worker-{i:02d}'
            lease=(folder/'parallel-owner.lock').open('a+');locks.append(lease);fcntl.flock(lease.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
            with (folder/'run.lock').open('a+') as lock:fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
    except Exception:
        for lock in locks:lock.close()
        raise
    try:
        while not stop and prior+time.monotonic()-started<args.seconds:
            elapsed=prior+time.monotonic()-started
            for i,entry in list(active.items()):
                if entry['p'].poll() is not None:finish(i,entry);del active[i]
            if elapsed>=next_budget:
                try:latest=budget();unreadable=0
                except Exception:unreadable+=1
                next_budget=elapsed+15
                if unreadable>=2:reason='credit_preflight_unavailable';break
                if latest['remaining_credits']<=3000:reason='provider_cap_safety_margin';break
            for i in selected:
                s=state['workers'][str(i)];folder=root/f'worker-{i:02d}'
                if i in active or s.get('stop_reason') or time.time()<s.get('retry_after',0) or elapsed<next_start:continue
                snap=snapshot(folder);bars=snap['bars'];ledger=folder/'solver_usage.json'
                tasks=json.loads(ledger.read_text()).get('attempts',0) if ledger.exists() else 0
                if not bars:s['stop_reason']='queue_finished_or_review_required';continue
                if tasks>=args.solver_tasks:s['stop_reason']='solver_limit';continue
                seconds=min(900,int(args.seconds-elapsed))
                if seconds<15:continue
                bar=bars[s['cursor']%len(bars)]
                cmd=[sys.executable,str(Path(__file__).with_name('turkey_scraper.py')),'--output',str(folder),
                    '--population-file','','--resume-details-only','--baro',bar,'--connection-file',str(connection),
                    '--capsolver','--solver-file',str(solver),'--provider-credit-cap',str(args.credit_cap),
                    '--solver-ledger',str(ledger),'--max-captcha-tasks',str(args.solver_tasks),
                    '--max-runtime',str(seconds),'--max-details','240','--detail-concurrency','2','--close-cdp-browser',
                    '--session-ttl','900','--session-restarts','1','--access-retries','2','--access-cooldown','10',
                    '--startup-timeout','120','--navigation-timeout','60','--retries','1','--retry-failed','--export-every','10']
                log=(folder/'parallel-console.log').open('a',buffering=1)
                active[i]={'p':subprocess.Popen(cmd,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True),
                           'log':log,'bar':bar,'before':snap['done']}
                next_start=elapsed+5
            report('running')
            if not active and all(state['workers'][str(i)].get('stop_reason') for i in selected):reason='queues_finished_or_safely_stopped';break
            time.sleep(2)
    except Exception:
        reason='controller_error';raise
    finally:
        for e in active.values():
            if e['p'].poll() is None:e['p'].terminate()
        for i,e in active.items():
            try:e['p'].wait(timeout=30)
            except subprocess.TimeoutExpired:os.killpg(e['p'].pid,signal.SIGKILL);e['p'].wait()
            finish(i,e,True)
        active.clear()
        # Fix the elapsed runtime before observing delayed post-close billing.
        final=report(reason);settlement=[]
        for delay in (0,10,10,10):
            if delay:time.sleep(delay)
            try:latest=budget();settlement.append(latest)
            except Exception:pass
        final.update(provider_budget=latest,key_credit_delta=latest['used_credits']-state['initial_key_credits'],credit_readbacks=settlement)
        atomic(report_path,final)
        for lock in locks:lock.close()
    return 0 if reason in ('time_limit_reached','queues_finished_or_safely_stopped') else 2

def cli():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--directory',required=True,help='Prepared folder containing manifest.json and worker-NN checkpoints')
    p.add_argument('--worker',type=int,action='append',help='Select 1..4 unique assigned IDs; repeat for additional workers')
    p.add_argument('--seconds',type=int,default=7200);p.add_argument('--credit-cap',type=int,default=200000)
    p.add_argument('--solver-tasks',type=int,default=50,help='Lifetime task ceiling for each existing worker ledger; not reset on restart')
    p.add_argument('--run-id',default='run1',help='Same ID resumes remaining time; a new ID explicitly starts a new time allowance')
    p.add_argument('--connection-file',default=os.getenv('TBB_CONNECTION_FILE',''));p.add_argument('--solver-file',default=os.getenv('TBB_SOLVER_FILE',''))
    return run(p.parse_args())
if __name__=='__main__':raise SystemExit(cli())
