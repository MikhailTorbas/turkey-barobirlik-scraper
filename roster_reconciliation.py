"""Independent official-roster candidates: queue lookups, never fabricate TBB records."""
import argparse
import hashlib
import json
import re
import time
from pathlib import Path
from urllib.parse import urlparse

import turkey_scraper as t


def normalized_name(value):
    return re.sub(r'\s+', ' ', t.turkish_upper(value or '')).strip()


def search_piece(value):
    """Use an existing contiguous source substring accepted by the TBB form."""
    pieces = re.findall('[' + re.escape(t.ALPHABET + '0123456789') + ']+', normalized_name(value))
    return max(pieces, key=len, default='')[:20]


def schema(db):
    db.db.executescript('''
      CREATE TABLE IF NOT EXISTS roster_sources(
        id TEXT PRIMARY KEY,baro TEXT NOT NULL,source_url TEXT NOT NULL,
        snapshot_date TEXT NOT NULL,receipt TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS roster_candidates(
        source_id TEXT NOT NULL,registration TEXT NOT NULL,expected_name TEXT NOT NULL,
        lookup_query_id INTEGER,lookup_issue TEXT NOT NULL DEFAULT '',
        PRIMARY KEY(source_id,registration));
      CREATE TABLE IF NOT EXISTS roster_lookup_attempts(
        baro TEXT NOT NULL,registration TEXT NOT NULL,attempts INTEGER NOT NULL DEFAULT 0,
        state TEXT NOT NULL DEFAULT 'pending',PRIMARY KEY(baro,registration));
    ''')


def reconcile(db, roster, baro):
    baro = str(baro)
    if not db.db.execute('SELECT id FROM bars WHERE id=?', (baro,)).fetchone():
        raise ValueError('Roster bar is not in this checkpoint')
    source = roster.get('source', '')
    if urlparse(source).scheme != 'https' or not urlparse(source).hostname:
        raise ValueError('A public HTTPS source URL is required')
    date = roster.get('date', '')
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', date):
        raise ValueError('Snapshot date is required')
    rows = roster.get('rows')
    if not isinstance(rows, list) or not rows:
        raise ValueError('An empty/failed response cannot establish a roster')
    unique = {}
    for row in rows:
        reg = str(row.get('regNumber', ''))
        if not re.fullmatch(r'[0-9]{1,7}', reg):
            raise ValueError('Invalid official registration identity')
        name = normalized_name(row.get('fullName') or (row.get('firstName', '') + ' ' + row.get('lastName', '')))
        if not name:
            raise ValueError('Missing source name')
        if reg in unique and unique[reg][0] != name:
            raise ValueError('Conflicting source names for the same registration')
        unique[reg] = (name, row)
    canonical = {'baro': baro, 'source': source, 'date': date,
                 'rows': [(reg, pair[0]) for reg, pair in sorted(unique.items())]}
    source_id = hashlib.sha256(json.dumps(canonical, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    schema(db)
    evidence = {k: v for k, v in roster.items() if k not in ('rows', 'variants')}
    db.db.execute('INSERT OR IGNORE INTO roster_sources VALUES(?,?,?,?,?)',
                  (source_id, baro, source, date, json.dumps(evidence, ensure_ascii=False)))
    for reg, (expected, row) in unique.items():
        if db.db.execute('SELECT registration FROM roster_candidates WHERE source_id=? AND registration=?',
                         (source_id, reg)).fetchone():
            continue
        key = t.record_key({'bar_association_id': baro, 'bar_registration_number': reg})
        found = db.db.execute('SELECT json FROM lawyers WHERE key=?', (key,)).fetchone()
        qid, issue = None, ''
        if not found:
            surname, name = search_piece(row.get('lastName', '')), search_piece(row.get('firstName', ''))
            if len(surname) < 2: surname = ''
            if len(name) < 2: name = ''
            if surname or name:
                qid = db.put_query(baro, surname, name)
                # A previously exhausted name lookup cannot prove this missing ID.
                # Keep it visible for exact-registration investigation rather than
                # repeatedly charging for the same already completed search.
                status = db.db.execute('SELECT status FROM queries WHERE id=?', (qid,)).fetchone()[0]
                if status in ('done', 'split', 'unresolved'):
                    issue = 'registration_missing_after_previous_name_search'
            else:
                issue = 'exact_registration_lookup_required'
        db.db.execute('INSERT INTO roster_candidates VALUES(?,?,?,?,?)', (source_id, reg, expected, qid, issue))
    db.db.commit()
    return summary(db)


def verify_candidates(driver, db, bars, limit, deadline=None, on_listing=None, on_reserve=None):
    """Bounded exact-ID lookups. Only actual TBB responses enter lawyers/details."""
    if not 0 <= limit <= 100:
        raise ValueError('Roster lookup limit must be between 0 and 100')
    if not limit or not db.db.execute("SELECT name FROM sqlite_master WHERE name='roster_sources'").fetchone():
        return {'attempted':0, 'observed':0, 'verified_absent':0}
    schema(db)
    candidates = db.db.execute('SELECT DISTINCT s.baro,c.registration FROM roster_candidates c JOIN roster_sources s ON s.id=c.source_id ORDER BY s.baro,c.registration').fetchall()
    receipt = {'attempted':0,'observed':0,'verified_absent':0}
    for candidate in candidates:
        bar, reg = candidate['baro'], candidate['registration']
        if bar not in set(map(str,bars)):continue
        key=t.record_key({'bar_association_id':bar,'bar_registration_number':reg})
        if db.db.execute('SELECT key FROM lawyers WHERE key=?',(key,)).fetchone():continue
        previous=db.db.execute('SELECT * FROM roster_lookup_attempts WHERE baro=? AND registration=?',(bar,reg)).fetchone()
        if previous and (previous['attempts']>=3 or previous['state'] in ('not_found','observed')):continue
        if receipt['attempted']>=limit or (deadline is not None and time.monotonic()>=deadline):break
        # Reserve before network I/O so crashes cannot cause unlimited paid retries.
        db.db.execute("INSERT INTO roster_lookup_attempts VALUES(?,?,1,'pending') ON CONFLICT(baro,registration) DO UPDATE SET attempts=attempts+1,state='pending'",(bar,reg));db.db.commit()
        receipt['attempted']+=1
        if on_reserve:on_reserve()
        rows,total,_=driver.fetch_registration(bar,reg)
        if total != len(rows) or len(rows)>1:
            raise t.ExtractionError('Ambiguous exact-registration result')
        if not rows:
            db.db.execute("UPDATE roster_lookup_attempts SET state='not_found' WHERE baro=? AND registration=?",(bar,reg));db.db.commit();receipt['verified_absent']+=1
            continue
        record=rows[0]
        if record.get('bar_registration_number')!=reg or str(record.get('bar_association_id'))!=bar:
            raise t.ExtractionError('Exact roster lookup returned another official identity')
        surname,name=search_piece(record.get('last_name','')),search_piece(record.get('first_name',''))
        qid=db.put_query(bar,surname if len(surname)>=2 else '',name if len(name)>=2 else '')
        # Preserve exact recovery for detail restart without inventing completion
        # of the separate name-discovery query used to hold observations/jobs.
        record['_lookup_registration']=reg
        db.upsert(record,qid)
        db.db.execute("UPDATE roster_lookup_attempts SET state='observed' WHERE baro=? AND registration=?",(bar,reg));db.db.commit();receipt['observed']+=1
        if on_listing:on_listing(qid)
    return receipt


def lookup_status(db,bars):
    """Roster verification work, independent of overlapping name queries."""
    if not db.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='roster_sources'").fetchone():
        return {'candidates':0,'ready':0,'observed':0,'not_found':0,'exhausted':0}
    selected=set(map(str,bars));observed={row[0] for row in db.db.execute('SELECT key FROM lawyers')}
    attempts=({(row['baro'],row['registration']):(row['attempts'],row['state']) for row in db.db.execute('SELECT * FROM roster_lookup_attempts')}
              if db.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='roster_lookup_attempts'").fetchone() else {})
    result={'candidates':0,'ready':0,'observed':0,'not_found':0,'exhausted':0}
    for row in db.db.execute('SELECT DISTINCT s.baro,c.registration FROM roster_candidates c JOIN roster_sources s ON s.id=c.source_id'):
        bar,reg=row['baro'],row['registration']
        if bar not in selected:continue
        result['candidates']+=1
        if t.record_key({'bar_association_id':bar,'bar_registration_number':reg}) in observed:result['observed']+=1
        elif attempts.get((bar,reg),(0,''))[1]=='not_found':result['not_found']+=1
        elif attempts.get((bar,reg),(0,''))[0]>=3:result['exhausted']+=1
        else:result['ready']+=1
    return result


def summary(db, records=None):
    if not db.db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='roster_sources'").fetchone():
        return {'sources': [], 'national_completeness_claim': False}
    if records is None:
        records = [json.loads(r[0]) for r in db.db.execute('SELECT json FROM lawyers')]
    by_key = {t.record_key(r): r for r in records}
    sources = []
    for source in db.db.execute('SELECT * FROM roster_sources ORDER BY baro,id'):
        matched = missing = conflicts = issues = 0
        for row in db.db.execute('SELECT * FROM roster_candidates WHERE source_id=?', (source['id'],)):
            key = t.record_key({'bar_association_id': source['baro'], 'bar_registration_number': row['registration']})
            record = by_key.get(key)
            if record is None:
                missing += 1
                issues += bool(row['lookup_issue'])
            else:
                actual = normalized_name(record.get('full_name') or (record.get('first_name', '') + ' ' + record.get('last_name', '')))
                if actual != row['expected_name']: conflicts += 1
                else: matched += 1
        sources.append({'id': source['id'], 'baro': source['baro'], 'source_url': source['source_url'],
                        'snapshot_date': source['snapshot_date'], 'matched_id_and_name': matched,
                        'missing_registration': missing, 'name_conflicts': conflicts,
                        'missing_requiring_review': issues,
                        'all_source_candidates_observed': missing == 0 and conflicts == 0,
                        'source_conditions': json.loads(source['receipt'])})
    lookups=[dict(row) for row in db.db.execute('SELECT state,count(*) AS count FROM roster_lookup_attempts GROUP BY state')] if db.db.execute("SELECT name FROM sqlite_master WHERE name='roster_lookup_attempts'").fetchone() else []
    return {'sources': sources, 'exact_registration_checks':lookups, 'national_completeness_claim': False,
            'meaning': 'Observed roster identities only. Source conditions, roster scope and undiscovered national identities remain separate.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint', required=True)
    parser.add_argument('--roster', required=True)
    parser.add_argument('--baro', required=True)
    args = parser.parse_args()
    db = t.Database(Path(args.checkpoint))
    try:
        result = reconcile(db, json.loads(Path(args.roster).read_text()), args.baro)
        db.export(Path(args.checkpoint).parent)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        db.db.close()
