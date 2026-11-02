"""Prepare corrected discovery queues in a NEW snapshot; never edit the source."""
import argparse
import json
import sqlite3
from pathlib import Path

import turkey_scraper as t


def prepare(source, destination, max_length=5, alphabet=t.ALPHABET):
    source, destination = Path(source), Path(destination)
    files = ([source / 'checkpoint.sqlite3'] if (source / 'checkpoint.sqlite3').exists()
             else sorted(source.glob('bars/*/checkpoint.sqlite3')))
    if not files or any(not p.is_file() for p in files):
        raise ValueError('No source checkpoints')
    if source.resolve() == destination.resolve() or destination.exists():
        raise ValueError('Destination must be new; source data is preserved')
    destination.mkdir(parents=True)
    report = {'algorithm': 'both-field-seeds-and-extensions-v3', 'national_completeness_claim': False,
              'source': str(source.resolve()), 'checkpoints': []}
    for file in files:
        target = destination / file.relative_to(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(file.resolve().as_uri() + '?mode=ro', uri=True) as original:
            with sqlite3.connect(target) as copied:
                original.backup(copied)
        db = t.Database(target)
        before = db.db.execute('SELECT count(*) FROM queries').fetchone()[0]
        parents = list(db.db.execute('SELECT * FROM queries WHERE capped=1'))
        for bar in db.db.execute('SELECT id FROM bars WHERE selected=1').fetchall():
            for seed in t.prefix_pairs(alphabet):
                for surname,name in t.seed_filters(seed,'both'):
                    db.put_query(bar['id'], surname,name)
        for q in parents:
            children, gap = t.partition(q['surname'], q['name'], max_length, alphabet)
            for surname, name in children:
                db.put_query(q['baro'], surname, name, q['id'])
            db.db.execute('INSERT OR REPLACE INTO gaps VALUES(?,?)', (q['id'], gap))
            # Parent listings and detail jobs remain intact, including completed profiles.
        db.db.commit()
        after = db.db.execute('SELECT count(*) FROM queries').fetchone()[0]
        db.metadata('coverage_partition_algorithm', report['algorithm'])
        prior=db.metadata('run_configuration')
        if prior:
            db.metadata('coverage_prior_configuration',prior)
            db.metadata('run_configuration',{**prior,'alphabet':alphabet,'primary_field':'both','max_length':max_length})
        report['checkpoints'].append({'checkpoint': str(target.relative_to(destination)),
                                      'capped_parents': len(parents), 'new_queries': after-before})
        db.db.close()
    (destination / 'coverage-repair.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True)
    parser.add_argument('--destination', required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.source, args.destination), indent=2))
