#!/usr/bin/env python3
"""Offline disjoint profile-job manifests; discovery remains a separate phase.

Prepare/verify/merge are offline and read source checkpoints only. The explicit
run command connects a worker using separately configured private credentials.
Every profile is owned by one worker. Completed master profiles are excluded.
"""
import argparse,hashlib,json,sqlite3,os
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse
import turkey_scraper as t


def checkpoints(path):
    path=Path(path)
    if path.is_file():return [path]
    if (path/'checkpoint.sqlite3').exists():return [path/'checkpoint.sqlite3']
    found=sorted(path.glob('bars/*/checkpoint.sqlite3'))
    if not found:found=sorted(path.glob('worker-*/checkpoint.sqlite3'))
    if not found:raise ValueError('No input checkpoints found')
    return found


def collect(path):
    jobs={};completed=set();sources=[]
    for file in checkpoints(path):
        with sqlite3.connect(file.resolve().as_uri()+'?mode=ro',uri=True) as db:
            db.row_factory=sqlite3.Row
            sources.append({'name':file.parent.name,'sha256':hashlib.sha256(file.read_bytes()).hexdigest()})
            for row in db.execute("SELECT l.key FROM lawyers l LEFT JOIN details d ON d.key=l.key WHERE d.status='done'"):
                completed.add(row['key'])
            for row in db.execute("SELECT l.key,l.json,d.failures,q.baro,q.surname,q.name FROM details d JOIN lawyers l ON l.key=d.key JOIN queries q ON q.id=d.query_id WHERE d.status='pending'"):
                record=json.loads(row['json'])
                if not record.get('bar_registration_number') or not record.get('bar_association_id'):raise ValueError('Ambiguous official profile identity; review before distribution')
                if t.record_key(record)!=row['key']:raise ValueError('Checkpoint identity key mismatch')
                # Carry public listing identity and audit evidence. Never carry
                # provider configuration, runtime metadata or browser profiles.
                keep=['first_name','last_name','full_name','bar_association','bar_association_id','bar_registration_number','source_url','_detail_index','_lookup_registration','_field_availability','_origins']
                listing={k:record[k] for k in keep if k in record};listing['detail_status']='pending';listing.setdefault('_detail_index','queued')
                candidate={'key':row['key'],'query':[row['baro'],row['surname'],row['name']],'record':listing,'failures':row['failures']}
                old=jobs.get(row['key'])
                if old and old['record']['bar_registration_number']!=listing['bar_registration_number']:raise ValueError('Conflicting official identity')
                if old:candidate['failures']=max(candidate['failures'],old['failures'])
                jobs[row['key']]=candidate
    for key in completed:jobs.pop(key,None)
    return jobs,sources,len(completed)


def plan(path,workers=12,chunk=64):
    if workers<1 or chunk<1:raise ValueError('Positive worker count and chunk size required')
    jobs,sources,done=collect(path);grouped=defaultdict(list)
    for item in jobs.values():grouped[tuple(item['query'])].append(item)
    chunks=[]
    for query,items in sorted(grouped.items()):
        items=sorted(items,key=lambda x:x['key'])
        chunks.extend(items[i:i+chunk] for i in range(0,len(items),chunk))
    loads=[[] for _ in range(workers)]
    for block in sorted(chunks,key=lambda x:(-len(x),x[0]['key'])):
        index=min(range(workers),key=lambda i:(len(loads[i]),i));loads[index].extend(block)
    flat=[j['key'] for group in loads for j in group]
    assert len(flat)==len(set(flat))==len(jobs)
    identity=hashlib.sha256(json.dumps({'sources':sources,'workers':workers,'chunk':chunk,'keys':sorted(flat)},sort_keys=True).encode()).hexdigest()
    return {'schema':1,'plan_id':identity,'scope':'Saved pending profile jobs only; does not complete national search discovery','workers':workers,'chunk_size':chunk,'completed_master_profiles_excluded':done,'pending_jobs':len(jobs),'sources':sources,'assignments':[{'worker':i+1,'jobs':group} for i,group in enumerate(loads)]}


def materialize(manifest,dest):
    dest=Path(dest)
    if dest.exists():raise ValueError('Destination must be new; resume existing worker folders in place')
    dest.mkdir(parents=True)
    for assignment in manifest['assignments']:
        folder=dest/f"worker-{assignment['worker']:02d}";folder.mkdir();db=t.Database(folder/'checkpoint.sqlite3')
        db.metadata('distribution_plan',{'plan_id':manifest['plan_id'],'worker':assignment['worker'],'scope':manifest['scope']})
        for job in assignment['jobs']:
            qid=db.put_query(*job['query']);key=db.upsert(job['record'],qid);assert key==job['key'];db.finish(qid,'done')
            db.db.execute('UPDATE details SET failures=? WHERE key=?',(job['failures'],key))
        db.db.commit();db.export(folder);db.db.close()
    (dest/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')


def verify_outputs(manifest,directory):
    directory=Path(directory);expected={a['worker']:{j['key'] for j in a['jobs']} for a in manifest['assignments']};seen=set();summary=[]
    for worker,keys in expected.items():
        path=directory/f'worker-{worker:02d}'/'checkpoint.sqlite3'
        with sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True) as db:
            meta=db.execute("SELECT value FROM metadata WHERE key='distribution_plan'").fetchone()
            if not meta or json.loads(meta[0])!={'plan_id':manifest['plan_id'],'worker':worker,'scope':manifest['scope']}:raise ValueError('Worker output belongs to another plan')
            rows=db.execute('SELECT key,json FROM lawyers').fetchall();actual={row[0] for row in rows}
            if actual!=keys or seen & actual:raise ValueError('Missing, foreign or duplicate worker identity')
            seen.update(actual);states=dict(db.execute('SELECT status,count(*) FROM details GROUP BY status'))
            for key,text in rows:
                if t.record_key(json.loads(text))!=key:raise ValueError('Worker record identity drift')
            summary.append({'worker':worker,'assigned':len(keys),'states':states})
    return {'plan_id':manifest['plan_id'],'unique_assigned_profiles':len(seen),'workers':summary,'national_completeness_claim':False}


def merge(manifest,directory,dest):
    report=verify_outputs(manifest,directory);dest=Path(dest)
    if dest.exists():raise ValueError('Merge output must be new; original master is never modified')
    dest.mkdir(parents=True);merged=t.Database(dest/'checkpoint.sqlite3')
    for assignment in manifest['assignments']:
        file=Path(directory)/f"worker-{assignment['worker']:02d}"/'checkpoint.sqlite3'
        with sqlite3.connect(file.resolve().as_uri()+'?mode=ro',uri=True) as db:
            for key,text in db.execute("SELECT l.key,l.json FROM lawyers l JOIN details d ON d.key=l.key WHERE d.status='done'"):
                record=json.loads(text)
                if record.get('detail_status')!='done':raise ValueError('Worker completion state conflicts with record')
                merged.upsert(record)
    merged.metadata('distribution_merge',report);merged.metadata('run_status','distributed_subset_merge');merged.export(dest);merged.db.close();return report


def run_worker(directory,seconds=3600,credit_cap=200000,solver_tasks=4):
    directory=Path(directory)
    with sqlite3.connect((directory/'checkpoint.sqlite3').resolve().as_uri()+'?mode=ro',uri=True) as db:
        meta=db.execute("SELECT value FROM metadata WHERE key='distribution_plan'").fetchone()
        if not meta:raise ValueError('Not a prepared worker checkpoint')
        bars=[r[0] for r in db.execute('SELECT DISTINCT baro FROM queries')]
    if not bars:return 0
    if not os.getenv('TBB_CONNECTION_FILE') or not os.getenv('TBB_SOLVER_FILE'):raise ValueError('Set private TBB_CONNECTION_FILE and TBB_SOLVER_FILE paths before running')
    args=['--output',str(directory),'--population-file','','--resume-details-only','--capsolver','--provider-credit-cap',str(credit_cap),'--max-runtime',str(seconds),'--max-captcha-tasks',str(solver_tasks),'--detail-concurrency','2','--close-cdp-browser','--session-restarts','2','--access-retries','2']
    for bar in bars:args.extend(['--baro',bar])
    return t.cli(args)


def cli():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['prepare','verify','merge','run']);parser.add_argument('--source');parser.add_argument('--directory',required=True);parser.add_argument('--workers',type=int,default=12);parser.add_argument('--chunk',type=int,default=64);parser.add_argument('--output');parser.add_argument('--seconds',type=int,default=3600);parser.add_argument('--credit-cap',type=int,default=200000);parser.add_argument('--solver-tasks',type=int,default=4);args=parser.parse_args()
    if args.action=='run':return run_worker(args.directory,args.seconds,args.credit_cap,args.solver_tasks)
    if args.action=='prepare':
        if not args.source:parser.error('--source required')
        manifest=plan(args.source,args.workers,args.chunk);materialize(manifest,args.directory);result=verify_outputs(manifest,args.directory)
    else:
        manifest=json.loads((Path(args.directory)/'manifest.json').read_text())
        if args.action=='merge':
            if not args.output:parser.error('--output required')
            result=merge(manifest,args.directory,args.output)
        else:result=verify_outputs(manifest,args.directory)
    print(json.dumps(result,indent=2))
if __name__=='__main__':raise SystemExit(cli())
