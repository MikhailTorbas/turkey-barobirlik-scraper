"""Create a NEW single-bar, four-slot allocation offline; never opens a browser.

Existing queues must be resumed/upgraded, never initialized again. Assignment
exclusivity across different Macs is coordinated through TEAM.md, not a server.
"""
import argparse
import hashlib
import json
from pathlib import Path

import refill_runner as r
import turkey_scraper as t


def prepare(directory, bar, owner):
    root = Path(directory).expanduser().resolve()
    checkout = Path(__file__).resolve().parent
    if root == checkout or checkout in root.parents:
        raise ValueError('Queue must be outside the source checkout')
    catalog = json.loads((checkout / 'bar_catalog.json').read_text())
    match = [b for b in catalog['bars'] if b['id'] == str(bar)]
    if len(match) != 1 or not owner.strip():
        raise ValueError('Use a known bar ID and nonempty owner')
    # mkdir is exclusive: even an empty existing directory is not overwritten.
    root.mkdir(parents=True, exist_ok=False)
    plan = {'schema': 1, 'slots': 4, 'bar': str(bar),
            'bar_name': match[0]['label'], 'owner': owner.strip(),
            'discovery_within_four_slots': True, 'initial_pending': 0,
            'national_completeness_claim': False,
            'catalog_observed_at': catalog['observed_at']}
    plan['plan_id'] = hashlib.sha256(json.dumps(plan, sort_keys=True).encode()).hexdigest()
    for name in ['discovery'] + [f'worker-{i:02d}' for i in range(1, 5)]:
        db = t.Database(root / name / 'checkpoint.sqlite3')
        try:
            db.db.execute('INSERT INTO bars VALUES(?,?,1)', (str(bar), match[0]['label']))
            db.db.commit()
            if name == 'discovery':
                for seed in t.prefix_pairs(t.ALPHABET):
                    for surname, given in t.seed_filters(seed, 'both'):
                        db.put_query(str(bar), surname, given)
                baseline = json.loads((checkout / 'population_2025.json').read_text())
                db.metadata('population_baseline', baseline)
        finally:
            db.db.close()
    (root / 'refill-plan.json').write_text(json.dumps(plan, ensure_ascii=False, indent=2) + '\n')
    registry = r.owner_db(root)
    try:
        result = {**plan, **r.validate(root, registry, plan), **r.snapshot(root),
                  'paid_requests': 0, 'directory': str(root)}
    finally:
        registry.close()
    (root / 'INITIAL_STATUS.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    return result


def cli():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', required=True)
    parser.add_argument('--baro', required=True)
    parser.add_argument('--owner', required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.directory, args.baro, args.owner), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    cli()
