"""Upgrade a STOPPED queue into a NEW copy; never replace received data."""
import argparse,hashlib,json,shutil,sqlite3,time
import fcntl
from contextlib import ExitStack
from pathlib import Path
import refill_runner as r
import turkey_scraper as t


def hashes(root):
    return {str(f.relative_to(root)):hashlib.sha256(f.read_bytes()).hexdigest() for f in root.rglob('*') if f.is_file()}


def upgrade(source,destination):
    source=Path(source).resolve()
    # Lock existing lease files read-only: never create/write a file in source.
    # A copied queue on another machine must already be stopped there too.
    with ExitStack() as leases:
        files=[source/'refill-owner.lock',*source.glob('*/run.lock'),*source.glob('*/parallel-owner.lock')]
        for file in files:
            if file.exists():
                handle=leases.enter_context(file.open('rb'));fcntl.flock(handle.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        return _upgrade_stopped(source,destination)


def _upgrade_stopped(source,destination):
    source=Path(source).resolve();dest=Path(destination).resolve()
    if dest.exists() or source==dest or source in dest.parents:raise ValueError('Choose a new destination outside the original queue')
    before=hashes(source);plan=json.loads((source/'refill-plan.json').read_text())
    # Inspect a copy so even SQLite's WAL/SHM bookkeeping cannot alter inputs.
    shutil.copytree(source,dest)
    with r.read_db(dest/'ownership.sqlite3') as db:r.validate(dest,db,plan)
    start=r.snapshot(dest);resolved=[];requeued=[]
    for i in range(1,5):
        folder=dest/f'worker-{i:02d}';db=t.Database(folder/'checkpoint.sqlite3')
        try:
            rows=list(db.db.execute('SELECT l.key,l.json,d.status,d.error FROM lawyers l JOIN details d ON d.key=l.key'))
            for row in rows:
                key=row['key'];record=json.loads(row['json'])
                if row['status']=='done' and record.get('_field_availability',{}).get('email')=='invalid_on_site' and not record.get('email'):
                    raw=record.get('_invalid_contact_values',{}).get('email',[])
                    addresses=list(dict.fromkeys(address for value in raw for address in t.contact_addresses(value)))
                    if addresses:
                        record['email']='; '.join(addresses);record['_field_availability']['email']='present'
                        record.setdefault('_detail_field_evidence',{}).setdefault('states',{})['email']='present'
                        record.setdefault('_contact_value_evidence',{})['email']={'raw_values':raw,'addresses':addresses,'method':'source_address_tokens','reparsed_at':t.now()}
                        db.complete_detail(record);resolved.append({'worker':i,'key':key,'addresses':len(addresses)})
                elif row['status']=='needs_review' and row['error']=='Official identity absent from its narrower name search':
                    record['_lookup_registration']=record['bar_registration_number'];record['detail_status']='pending'
                    db.upsert(record);db.detail_state(key,'pending','Upgrade: queued bounded exact-registration recovery');db.event('exact_lookup_review_released',key)
                    requeued.append({'worker':i,'key':key,'registration':record['bar_registration_number']})
            db.export(folder)
        finally:db.db.close()
    with r.read_db(dest/'ownership.sqlite3') as db:verification=r.validate(dest,db,plan)
    end=r.snapshot(dest)
    if start['done']!=end['done']:raise ValueError('Upgrade changed completion count')
    if before!=hashes(source):raise ValueError('Original queue changed during copy; do not use this snapshot')
    receipt={'source_unchanged':True,'before':start,'after':end,'recovered_source_emails':resolved,'requeued_exact_ids':requeued,
             'ownership':verification,'solver_ledgers_reset':False,'runtime_reset':False}
    (dest/'UPGRADE_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--destination',required=True);args=p.parse_args()
    print(json.dumps(upgrade(args.source,args.destination),indent=2))
