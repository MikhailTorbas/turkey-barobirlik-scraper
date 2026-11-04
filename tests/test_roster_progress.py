import tempfile
import unittest
from pathlib import Path
import refill_runner as r
import roster_reconciliation as roster
import turkey_scraper as t
import test_refill_runner as fixtures


class RosterProgressTests(unittest.TestCase):
    def test_confirmed_absence_counts_as_progress_but_unanswered_attempt_does_not(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);_,registry=fixtures.RefillTests().fixture(root);registry.close()
            db=t.Database(root/'discovery/checkpoint.sqlite3')
            try:
                roster.schema(db)
                before=r.snapshot(root)['discovery_progress']
                db.db.execute("INSERT INTO roster_lookup_attempts VALUES('6','1',1,'pending')");db.db.commit()
                self.assertEqual(r.snapshot(root)['discovery_progress'],before)
                db.db.execute("UPDATE roster_lookup_attempts SET state='not_found'");db.db.commit()
                self.assertEqual(r.snapshot(root)['discovery_progress'],before+1)
                self.assertEqual(r.snapshot(root)['roster_verification_progress'],1)
                self.assertEqual(r.snapshot(root)['done'],0)
                # A repeated reading is not another unit of progress.
                self.assertEqual(r.snapshot(root)['discovery_progress'],before+1)
            finally:db.db.close()
