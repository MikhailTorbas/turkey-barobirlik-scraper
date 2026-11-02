"""Offline quality/coverage report and optional completed JSONL export."""
import argparse,collections,json
from pathlib import Path
import refill_runner as r


def inspect(root,export=None):
    root=Path(root);plan=json.loads((root/'refill-plan.json').read_text())
    with r.read_db(root/'ownership.sqlite3') as db:verification=r.validate(root,db,plan)
    groups=collections.defaultdict(list);zero=[];invalid=[];unknown=[];reviews=[];completed=[]
    for i in range(1,5):
        with r.read_db(root/f'worker-{i:02d}/checkpoint.sqlite3') as db:
            for row in db.execute('SELECT l.key,l.json,d.status,d.error FROM lawyers l JOIN details d ON d.key=l.key'):
                record=json.loads(row['json']);evidence=record.get('_field_availability',{}).get('email','unknown')
                if row['status']!='done':
                    if row['status']=='needs_review':reviews.append({'key':row['key'],'worker':i,'reason':row['error']})
                    continue
                completed.append(record);number=record.get('tbb_registration_number')
                if number:groups[number].append({'key':row['key'],'bar_registration_number':record['bar_registration_number']})
                if number and set(number)=={'0'}:zero.append(row['key'])
                if evidence=='invalid_on_site':invalid.append(row['key'])
                if evidence not in ('present','blank_on_site','invalid_on_site'):unknown.append(row['key'])
    if export:
        with Path(export).open('x') as out:
            for record in completed:out.write(json.dumps(record,ensure_ascii=False)+'\n')
    return {'plan_id':plan['plan_id'],'bar':plan['bar'],'ownership':verification,**r.snapshot(root),
            'repeated_tbb_values':{k:v for k,v in groups.items() if len(v)>1},'zero_tbb_keys':zero,
            'invalid_email_keys':invalid,'unknown_email_keys':unknown,'needs_review':reviews,
            'national_completeness_claim':False,'source_recheck_required':bool(zero or any(len(v)>1 for v in groups.values())),
            'note':'Repeated TBB values are source-quality flags, not instructions to merge different official bar registrations.'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--directory',required=True);p.add_argument('--export-completed');a=p.parse_args()
    print(json.dumps(inspect(a.directory,a.export_completed),indent=2))
