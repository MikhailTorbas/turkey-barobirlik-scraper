#!/usr/bin/env python3
"""Four-slot, single-bar discovery/refill and detail controller (macOS/Linux).

Discovery temporarily occupies one of the four slots; no fifth browser is used.
Durable ownership is reserved before materializing a job in a worker checkpoint.
Never run the earlier fixed-queue controller against this allocation concurrently.
"""
import argparse
import collections
import fcntl
import json
import os
import re
import signal
import sqlite3
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path

import turkey_scraper as t
from parallel_runner import atomic
from provider_budget import check_zenrows_cap,read_zenrows_usage,ProviderAuthorizationError


@contextmanager
def read_db(path):
    db=sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True,timeout=10)
    db.row_factory=sqlite3.Row
    try:yield db
    finally:db.close()


def owner_db(root):
    db=sqlite3.connect(root/'ownership.sqlite3',timeout=10)
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('CREATE TABLE IF NOT EXISTS owners(key TEXT PRIMARY KEY,worker INTEGER NOT NULL CHECK(worker BETWEEN 1 AND 4))')
    return db


def source_jobs(root,bar):
    with read_db(root/'discovery/checkpoint.sqlite3') as db:
        result={}
        for row in db.execute("SELECT l.key,l.json,q.baro,q.surname,q.name,d.failures FROM lawyers l JOIN details d ON d.key=l.key JOIN queries q ON q.id=d.query_id WHERE d.status='pending' AND d.failures<3"):
            rec=json.loads(row['json'])
            if str(rec.get('bar_association_id'))!=bar or row['baro']!=bar or not rec.get('bar_registration_number') or t.record_key(rec)!=row['key']:
                raise ValueError('Ambiguous or foreign discovered identity')
            result[row['key']]={'record':rec,'query':(bar,row['surname'],row['name']),'failures':row['failures']}
        return result


def snapshot(root,full=True):
    manifest=json.loads((root/'refill-plan.json').read_text());rows={};allkeys=set();valid=0;emails=set();availability=collections.Counter()
    for i in range(1,5):
        with read_db(root/f'worker-{i:02d}/checkpoint.sqlite3') as db:
            states=dict(db.execute('SELECT status,count(*) FROM details GROUP BY status'))
            for r in (db.execute("SELECT l.key,l.json FROM lawyers l JOIN details d ON d.key=l.key WHERE d.status='done'") if full else []):
                if r['key'] in allkeys:raise ValueError('Duplicate completed identity')
                allkeys.add(r['key']);record=json.loads(r['json'])
                availability[record.get('_field_availability',{}).get('email','unknown')]+=1
                if record.get('email'):valid+=1;emails.update(address.casefold() for address in t.contact_addresses(record['email']))
            ready=db.execute("SELECT count(*) FROM details WHERE status IN ('pending','running','verification','failed') AND failures<3").fetchone()[0]
        rows[str(i)]={'states':states,'done':states.get('done',0),'ready':ready}
    with read_db(root/'discovery/checkpoint.sqlite3') as db:
        queries=dict(db.execute('SELECT status,count(*) FROM queries GROUP BY status'))
    done=sum(r['done'] for r in rows.values())
    return {'bar':manifest['bar'],'workers':rows,'done':done,'ready':sum(r['ready'] for r in rows.values()),
            'profiles_with_email':valid,'unique_email_addresses':len(emails),'email_evidence':dict(availability),
            'email_fill_percent':round(valid*100/done,2) if done else None,'discovery_queries':queries,
            'discovery_progress':sum(queries.get(s,0) for s in ('done','split','unresolved'))}


def validate(root,registry,plan):
    if plan.get('schema')!=1 or plan.get('slots')!=4 or not str(plan.get('bar','')).isdigit():raise ValueError('Invalid refill plan')
    expected={k:i for k,i in registry.execute('SELECT key,worker FROM owners')};seen=set()
    for i in range(1,5):
        with read_db(root/f'worker-{i:02d}/checkpoint.sqlite3') as db:
            for row in db.execute('SELECT key,json FROM lawyers'):
                record=json.loads(row['json'])
                if expected.get(row['key'])!=i or row['key'] in seen or str(record.get('bar_association_id'))!=plan['bar'] or t.record_key(record)!=row['key']:
                    raise ValueError('Worker ownership, bar or identity mismatch')
                seen.add(row['key'])
    # A reservation may be missing from a worker after interruption; dispatch
    # repairs that gap before this worker can be started. Never reassign it.
    with read_db(root/'discovery/checkpoint.sqlite3') as db:
        baseline={r[0] for r in db.execute("SELECT key FROM details WHERE status='done'")}
    if set(expected)&baseline:raise ValueError('Previously completed baseline was assigned again')
    return {'owned':len(expected),'materialized':len(seen),'reservations_to_repair':len(set(expected)-seen)}


def dispatch(root,registry,bar,idle,target=400,after_reserve=None):
    """Only idle detail checkpoints may be written. Reservations are durable."""
    jobs=source_jobs(root,bar);owned=dict(registry.execute('SELECT key,worker FROM owners'))
    # Keep identities from the same search together to retain search reuse.
    free=iter(sorted(set(jobs)-set(owned),key=lambda key:(jobs[key]['query'],key)));added=0
    for i in idle:
        db=t.Database(root/f'worker-{i:02d}/checkpoint.sqlite3')
        try:
            existing={r[0] for r in db.db.execute('SELECT key FROM lawyers')}
            ready=db.db.execute("SELECT count(*) FROM details WHERE status IN ('pending','running','verification','failed') AND failures<3").fetchone()[0]
            missing=[key for key,worker in owned.items() if worker==i and key not in existing]
            for _ in range(max(0,target-ready-len(missing))):
                key=next(free,None)
                if key is None:break
                with registry:registry.execute('INSERT INTO owners VALUES(?,?)',(key,i))
                owned[key]=i;missing.append(key)
                if after_reserve:after_reserve(key,i)
            for key in missing:
                job=jobs.get(key)
                if job is None:raise ValueError('Reserved job has no source evidence')
                qid=db.put_query(*job['query']);actual=db.upsert(job['record'],qid)
                if actual!=key:raise ValueError('Materialized key mismatch')
                db.finish(qid,'done')
                db.db.execute('UPDATE details SET failures=? WHERE key=?',(job['failures'],key));db.db.commit();added+=1
        finally:db.db.close()
    return added,len(set(jobs)-set(owned))


def command(root,role,worker,bar,seconds,args):
    folder=root/('discovery' if role=='discovery' else f'worker-{worker:02d}')
    cmd=[sys.executable,str(Path(__file__).with_name('turkey_scraper.py')),'--output',str(folder),'--population-file','',
         '--baro',bar,'--connection-file',str(Path(args.connection_file).resolve()),'--capsolver','--solver-file',str(Path(args.solver_file).resolve()),
         '--solver-ledger',str(folder/'solver_usage.json'),
         '--max-captcha-tasks',str(args.discovery_solver_tasks if role=='discovery' else args.solver_tasks),
         '--max-runtime',str(seconds),'--detail-concurrency','2','--close-cdp-browser','--session-ttl','900',
         '--session-restarts','1','--access-retries','2','--access-cooldown','10','--startup-timeout','120',
         '--navigation-timeout','60','--retries','1','--retry-failed','--export-every','10']
    if not getattr(args,'uncapped',False):cmd+=['--provider-credit-cap',str(args.credit_cap)]
    if role=='discovery':cmd+=['--no-details','--primary-field','both','--max-searches','30']
    else:cmd+=['--resume-details-only','--max-details','240']
    return cmd,folder


def discovery_available(root):
    with read_db(root/'discovery/checkpoint.sqlite3') as db:
        return bool(db.execute("SELECT 1 FROM queries WHERE status IN ('pending','running','verification','failed') LIMIT 1").fetchone())


def run(args):
    root=Path(args.directory).resolve();plan=json.loads((root/'refill-plan.json').read_text())
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,48}',args.run_id) or min(args.seconds,args.credit_cap,args.solver_tasks,args.discovery_solver_tasks)<1:
        raise ValueError('Invalid runtime, budget or run ID')
    endpoint=json.loads(Path(args.connection_file).read_text())['cdp_endpoint']
    json.loads(Path(args.solver_file).read_text())['capsolver_api_key']
    # Persistent lease covers both queue writers and every child directory.
    leases=[];registry=None
    try:
        for name in ('controller', 'discovery', 'worker-01','worker-02','worker-03','worker-04'):
            folder=root if name=='controller' else root/name
            lease=(folder/('refill-owner.lock' if name=='controller' else 'parallel-owner.lock')).open('a+')
            leases.append(lease);fcntl.flock(lease.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
            if name!='controller':
                with (folder/'run.lock').open('a+') as childlock:fcntl.flock(childlock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        registry=owner_db(root);validate(root,registry,plan)
        return supervise(root,registry,plan,args,endpoint)
    finally:
        if registry is not None:registry.close()
        for lease in leases:lease.close()


def amend_state(state,config,allowed=False):
    old=state['config']
    if old==config:return
    permitted={'solver_tasks','discovery_solver_tasks','credit_cap','uncapped'}
    changed={k for k in set(old)|set(config) if old.get(k)!=config.get(k)}
    if not allowed or not changed<=permitted:raise ValueError('Resume configuration differs; explicitly amend budgets without resetting runtime')
    for key in ('solver_tasks','discovery_solver_tasks'):
        if config[key]<old[key]:raise ValueError('Solver amendment cannot lower the existing lifetime allowance')
    state.setdefault('budget_amendments',[]).append({'at_unix':time.time(),'before':dict(old),'after':dict(config)})
    for role,data in state['roles'].items():
        key='discovery_solver_tasks' if role=='discovery' else 'solver_tasks'
        if data.get('stop_reason')=='solver_limit' and config[key]>old[key]:
            data.pop('stop_reason');data['retry_after']=0
    state['config']=config


def recover_stopped(state,recovery_id):
    """Explicit, idempotent operator recovery; keep prior failures and budgets."""
    if not recovery_id:return False
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,48}',recovery_id):
        raise ValueError('Invalid recovery ID')
    history=state.setdefault('operator_recoveries',[])
    if any(item['id']==recovery_id for item in history):return False
    recovered={}
    for role,data in state['roles'].items():
        if data.get('stop_reason')!='three_phases_without_progress':continue
        recovered[role]=dict(data)
        data.pop('stop_reason')
        data.update(no_progress=0,retry_after=0)
    history.append({'id':recovery_id,'at_unix':time.time(),'before':recovered,
                    'elapsed_seconds':state['elapsed_seconds']})
    return True


def export_idle(root,workers):
    for i in workers:
        folder=root/f'worker-{i:02d}';db=t.Database(folder/'checkpoint.sqlite3')
        try:db.export(folder)
        finally:db.db.close()


def stop_children(active,grace=90):
    """One shared grace deadline; kill only children still alive afterwards."""
    for entry in active.values():
        if entry['p'].poll() is None:entry['p'].terminate()
    deadline=time.monotonic()+grace;forced=[]
    for slot,entry in active.items():
        try:entry['p'].wait(timeout=max(1,deadline-time.monotonic()))
        except subprocess.TimeoutExpired:
            os.killpg(entry['p'].pid,signal.SIGKILL);entry['p'].wait();forced.append(slot)
    return forced


def supervise(root,registry,plan,args,endpoint):
    uncapped=getattr(args,'uncapped',False)
    def budget():return read_zenrows_usage(endpoint) if uncapped else check_zenrows_cap(endpoint,args.credit_cap)
    telemetry_error=None
    try:latest=budget()
    except ProviderAuthorizationError:raise
    except Exception:
        if not uncapped:raise
        latest={'mode':'uncapped','counter_scope':'account','used_credits':None};telemetry_error='usage_monitor_unavailable'
    tag=args.run_id;state_path=root/f'refill-state-{tag}.json';report_path=root/f'refill-report-{tag}.json'
    initial=snapshot(root);config={'plan_id':plan['plan_id'],'seconds':args.seconds,'credit_cap':args.credit_cap,
                                  'solver_tasks':args.solver_tasks,'discovery_solver_tasks':args.discovery_solver_tasks}
    if uncapped:config.update(uncapped=True,credit_cap=None)
    state=json.loads(state_path.read_text()) if state_path.exists() else {
        'config':config,'elapsed_seconds':0,'initial_done':initial['done'],'initial_key_credits':latest['used_credits'],
        'roles':{role:{'no_progress':0,'retry_after':0} for role in ['discovery','1','2','3','4']},'slot_seconds':{'details':0,'discovery':0}}
    if state['config']!=config:
        old_uncapped=state['config'].get('uncapped',False)
        amend_state(state,config,getattr(args,'amend_budgets',False))
        if old_uncapped!=uncapped:
            # Key-cap and account counters may be different scopes. Preserve
            # historical observations but never subtract across scopes.
            state.setdefault('counter_history',[]).append({'initial_key_credits':state['initial_key_credits'],'ending_at_mode_change':None})
            state['initial_key_credits']=latest['used_credits']
    if recover_stopped(state,getattr(args,'recover_stopped','')):
        # Persist authorization/history before any paid child can be launched.
        atomic(state_path,state)
    started=time.monotonic();prior=state['elapsed_seconds'];active={};stop=False;reason='time_limit_reached';next_budget=0;unreadable=0;next_start=0;next_report=0
    idle_since=None
    old_handlers={}
    def interrupt(signum,frame):
        nonlocal stop,reason
        stop=True;reason='interrupted'
    for sig in (signal.SIGINT,signal.SIGTERM):old_handlers[sig]=signal.signal(sig,interrupt)
    def event(data):
        with (root/f'refill-events-{tag}.jsonl').open('a') as f:f.write(json.dumps({'at_unix':time.time(),**data})+'\n')
    def report(status):
        snap=snapshot(root);elapsed=min(args.seconds,prior+time.monotonic()-started);new=snap['done']-state['initial_done']
        runnable=sum(v['ready'] for role,v in snap['workers'].items() if not state['roles'][role].get('stop_reason'))
        samples=state.setdefault('recent_progress_samples',[])
        if samples and snap['done']>samples[-1][1]:state['last_completion_elapsed_seconds']=elapsed
        samples.append([elapsed,snap['done']])
        while len(samples)>2 and samples[1][0]<=elapsed-300:samples.pop(0)
        window=elapsed-samples[0][0]
        recent=(snap['done']-samples[0][1])*60/window if window>0 else None
        state['elapsed_seconds']=elapsed;atomic(state_path,state)
        data={'status':status,'elapsed_seconds':round(elapsed,2),'remaining_seconds':round(max(0,args.seconds-elapsed),2),
              'new_completed_profiles':new,'profiles_per_minute':round(new*60/elapsed,3) if elapsed else 0,
              'recent_profiles_per_minute':round(recent,3) if recent is not None else None,
              'recent_window_seconds':round(window,2),
              'provider_budget':latest,'shared_key_credit_delta':credit_delta(),
              'usage_monitor_status':telemetry_error or 'available',
              'billing_note':'Shared company counter. Never add concurrent Mac deltas. Billing can lag.',
              'active_slots':len(active),'roles':state['roles'],'slot_seconds':state['slot_seconds'],
              'runnable_ready':runnable,'stranded_ready':snap['ready']-runnable,**snap}
        atomic(report_path,data);return data
    def credit_delta():
        before=state['initial_key_credits'];after=latest.get('used_credits')
        if before is None or after is None or after<before:return None
        return after-before
    def finish(slot,entry,planned=False):
        entry['log'].close();snap=snapshot(root,False);role=entry['role'];s=state['roles'][role]
        progress=(snap['discovery_progress']-entry['before']) if role=='discovery' else snap['workers'][role]['done']-entry['before']
        folder=root/('discovery' if role=='discovery' else f'worker-{int(role):02d}')
        with read_db(folder/'checkpoint.sqlite3') as db:
            status=db.execute("SELECT value FROM metadata WHERE key='run_status'").fetchone()
        s['last_worker_status']=json.loads(status[0]) if status else 'unknown'
        if not planned:
            s['no_progress']=0 if progress else s['no_progress']+1
            s['retry_after']=time.time()+(60*2**(s['no_progress']-1) if s['no_progress'] else 0)
            if s['no_progress']>=3:s['stop_reason']='three_phases_without_progress'
        state['slot_seconds']['discovery' if role=='discovery' else 'details']+=time.monotonic()-entry['started']
        event({'role':role,'slot':slot,'progress':progress,'exit_code':entry['p'].returncode,'planned_stop':planned})
        if role!='discovery':export_idle(root,[int(role)])
    try:
        while not stop and prior+time.monotonic()-started<args.seconds:
            elapsed=prior+time.monotonic()-started
            for slot,entry in list(active.items()):
                if entry['p'].poll() is not None:finish(slot,entry);del active[slot]
            if elapsed>=next_budget:
                try:
                    latest=budget();unreadable=0;telemetry_error=None
                    if state['initial_key_credits'] is None:
                        state['initial_key_credits']=latest['used_credits'];state['credit_baseline_delayed']=True
                except ProviderAuthorizationError:
                    reason='provider_authentication_or_funding_rejected';break
                except Exception:
                    unreadable+=1;telemetry_error='usage_monitor_unavailable'
                    event({'usage_monitor_error':telemetry_error,'attempt':unreadable,'uncapped':uncapped})
                next_budget=elapsed+min(300,15*2**min(unreadable,4))
                if unreadable>=2 and not uncapped:reason='credit_preflight_unavailable';break
                if not uncapped and latest['remaining_credits']<=5000:reason='provider_cap_safety_margin';break
            # Producer cannot race dispatch: its checkpoint is read only after
            # it exits. A detail worker's checkpoint is written only when idle.
            producer=any(e['role']=='discovery' for e in active.values())
            idle=[i for i in range(1,5) if i not in active]
            added=0;unowned=0
            if not producer and idle:
                accepting=[i for i in idle if not state['roles'][str(i)].get('stop_reason')]
                added,unowned=dispatch(root,registry,plan['bar'],accepting)
                if added:event({'assigned_jobs':added,'unowned_buffer':unowned})
            snap=snapshot(root,False);dstate=state['roles']['discovery']
            if all(state['roles'][str(i)].get('stop_reason') for i in range(1,5)):
                reason='all_detail_workers_safely_stopped';break
            # Jobs owned by stopped workers cannot feed healthy slots. Counting
            # them as buffer caused all healthy workers to idle forever at 800.
            runnable_ready=sum(v['ready'] for role,v in snap['workers'].items() if not state['roles'][role].get('stop_reason'))
            need_discovery=not producer and unowned+runnable_ready<800 and discovery_available(root) and not dstate.get('stop_reason')
            for i in idle:
                if elapsed<next_start:break
                role='discovery' if need_discovery and time.time()>=dstate['retry_after'] else str(i)
                s=state['roles'][role]
                if s.get('stop_reason') or time.time()<s['retry_after']:continue
                if role!='discovery' and not snap['workers'][role]['ready']:continue
                folder=root/('discovery' if role=='discovery' else f'worker-{i:02d}')
                ledger=folder/'solver_usage.json';attempts=json.loads(ledger.read_text()).get('attempts',0) if ledger.exists() else 0
                limit=args.discovery_solver_tasks if role=='discovery' else args.solver_tasks
                if attempts>=limit:s['stop_reason']='solver_limit';continue
                seconds=min(900,int(args.seconds-elapsed))
                if seconds<15:continue
                cmd,folder=command(root,role,i,plan['bar'],seconds,args)
                log=(folder/'refill-console.log').open('a',buffering=1)
                try:p=subprocess.Popen(cmd,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                except Exception:log.close();raise
                active[i]={'p':p,'log':log,'role':role,'started':time.monotonic(),
                           'before':snap['discovery_progress'] if role=='discovery' else snap['workers'][role]['done']}
                next_start=elapsed+5
                if role=='discovery':need_discovery=False
            if elapsed>=next_report:
                report('running' if active else 'waiting_for_work_or_recovery');next_report=elapsed+15
            if not active:
                detail_possible=any(snap['workers'][str(i)]['ready'] and not state['roles'][str(i)].get('stop_reason') for i in range(1,5))
                producer_possible=discovery_available(root) and not dstate.get('stop_reason')
                if not detail_possible and not producer_possible:
                    reason='work_exhausted_or_recovery_limit';break
                # A zero-browser scheduling fault must not look healthy for hours.
                waiting=elapsed<next_start or any(
                    not s.get('stop_reason') and time.time()<s.get('retry_after',0)
                    for s in state['roles'].values())
                if waiting:idle_since=None
                elif idle_since is None:idle_since=time.monotonic()
                elif time.monotonic()-idle_since>=120:
                    reason='scheduler_no_launch';break
            else:idle_since=None
            time.sleep(2)
    except Exception:
        reason='controller_error';raise
    finally:
        forced=stop_children(active,getattr(args,'shutdown_grace',90))
        for slot,e in active.items():
            if slot in forced:event({'forced_child_stop':slot,'role':e['role'],'reason':'shutdown_grace_exhausted'})
            finish(slot,e,True)
        active.clear()
        # Repair running states only after all writers have stopped.
        for i in range(1,5):
            db=t.Database(root/f'worker-{i:02d}/checkpoint.sqlite3')
            try:db.recover(False)
            finally:db.db.close()
        export_idle(root,range(1,5));validate(root,registry,plan)
        final=report(reason);readbacks=[]
        for delay in (0,10,10,10):
            if delay:time.sleep(delay)
            try:latest=budget();readbacks.append(latest);telemetry_error=None
            except Exception:pass
        final.update(provider_budget=latest,shared_key_credit_delta=credit_delta(),credit_readbacks=readbacks,forced_child_stops=forced,
                     usage_monitor_status=telemetry_error or 'available')
        atomic(report_path,final)
        for sig,handler in old_handlers.items():signal.signal(sig,handler)
    return 0 if reason=='time_limit_reached' else 2


def cli():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--directory',required=True)
    p.add_argument('--seconds',type=int,default=28800);p.add_argument('--credit-cap',type=int,default=600000)
    p.add_argument('--uncapped',action='store_true',help='No local credit ceiling; usage telemetry failures do not stop collection. Provider caps still apply.')
    p.add_argument('--amend-budgets',action='store_true',help='Record explicit budget/uncapped-mode changes on resume without resetting elapsed time or ledgers')
    p.add_argument('--solver-tasks',type=int,default=250);p.add_argument('--discovery-solver-tasks',type=int,default=100)
    p.add_argument('--shutdown-grace',type=int,default=90)
    p.add_argument('--run-id',default='eight-hour-refill')
    p.add_argument('--recover-stopped',default='',metavar='RECOVERY_ID',help='Explicitly release no-progress stops once per recorded recovery ID; preserves runtime, budgets and failure history')
    p.add_argument('--connection-file',default=os.getenv('TBB_CONNECTION_FILE',''));p.add_argument('--solver-file',default=os.getenv('TBB_SOLVER_FILE',''))
    return run(p.parse_args())

if __name__=='__main__':raise SystemExit(cli())
