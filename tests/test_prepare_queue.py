import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import prepare_queue as p
import refill_runner as r
import turkey_scraper as t


class PrepareQueueTests(unittest.TestCase):
    def test_fresh_allocations_have_discovery_and_no_cross_bar_jobs(self):
        with tempfile.TemporaryDirectory() as td, patch.object(r.subprocess, 'Popen') as child:
            for owner, bar in [('Elena', '35'), ('Pari', '16')]:
                root = Path(td) / owner
                report = p.prepare(root, bar, owner)
                self.assertEqual(report['paid_requests'], 0)
                self.assertEqual(report['done'], 0)
                self.assertEqual(report['owned'], 0)
                self.assertTrue(r.discovery_available(root))
                with r.read_db(root / 'discovery/checkpoint.sqlite3') as db:
                    self.assertEqual({x[0] for x in db.execute('SELECT DISTINCT baro FROM queries')}, {bar})
                    queries = {(row['surname'], row['name']) for row in db.execute('SELECT surname,name FROM queries')}
                expected = {pair for seed in t.prefix_pairs(t.ALPHABET) for pair in t.seed_filters(seed, 'both')}
                self.assertEqual(queries, expected)
                # First discovered jobs can be distributed by the production controller.
                db = t.Database(root / 'discovery/checkpoint.sqlite3')
                qid = db.put_query(bar, 'TE', '')
                db.upsert({'bar_association_id': bar, 'bar_registration_number': 'test-1',
                           '_detail_index': '1', 'detail_status': 'pending'}, qid)
                db.finish(qid, 'done'); db.db.close()
                registry = r.owner_db(root)
                try:
                    self.assertEqual(r.dispatch(root, registry, bar, [1, 2, 3, 4]), (1, 0))
                    self.assertEqual(r.validate(root, registry, json.loads((root / 'refill-plan.json').read_text()))['materialized'], 1)
                finally:
                    registry.close()
                before = (root / 'discovery/checkpoint.sqlite3').read_bytes()
                with self.assertRaises(FileExistsError):
                    p.prepare(root, bar, owner)
                self.assertEqual(before, (root / 'discovery/checkpoint.sqlite3').read_bytes())
            child.assert_not_called()

    def test_bad_scope_is_rejected_before_creation(self):
        with tempfile.TemporaryDirectory() as td:
            for bar, owner in [('999999', 'Elena'), ('35', ' ')]:
                root = Path(td) / 'bad'
                with self.assertRaises(ValueError): p.prepare(root, bar, owner)
                self.assertFalse(root.exists())
        with self.assertRaises(ValueError):
            p.prepare(Path(p.__file__).parent / 'must-not-create', '35', 'Elena')
