import hashlib
import tempfile
import unittest
from pathlib import Path

import turkey_scraper as t
from repair_coverage import prepare


class CoverageRepairTests(unittest.TestCase):
    def test_new_snapshot_repairs_old_split_without_touching_saved_data(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp)/'source'; source.mkdir()
            db = t.Database(source/'checkpoint.sqlite3')
            db.db.execute("INSERT INTO bars VALUES('16','BURSA',1)")
            qid = db.put_query('16','KA')
            db.finish(qid,'split',capped=1,seen=1000)
            db.metadata('run_configuration',{'alphabet':t.ALPHABET[:-3],'primary_field':'surname','max_length':5})
            record = {'bar_association_id':'16','bar_registration_number':'123',
                      'detail_status':'done','email':'saved@example.org'}
            key = db.upsert(record,qid)
            db.db.close()
            before = hashlib.sha256((source/'checkpoint.sqlite3').read_bytes()).hexdigest()
            dest = Path(temp)/'repaired'
            report = prepare(source,dest)
            self.assertFalse(report['national_completeness_claim'])
            self.assertEqual(hashlib.sha256((source/'checkpoint.sqlite3').read_bytes()).hexdigest(),before)
            copied=t.Database(dest/'checkpoint.sqlite3')
            self.assertEqual(copied.record(key)['email'],'saved@example.org')
            self.assertEqual(copied.metadata('run_configuration')['alphabet'],t.ALPHABET)
            self.assertEqual(copied.metadata('run_configuration')['primary_field'],'both')
            self.assertEqual(copied.db.execute('SELECT status FROM queries WHERE id=?',(qid,)).fetchone()[0],'split')
            for s,n in [('KAR',''),('QW',''),('KA','QW'),('','QW')]:
                self.assertIsNotNone(copied.db.execute('SELECT id FROM queries WHERE surname=? AND name=?',(s,n)).fetchone())
            copied.db.close()
            with self.assertRaises(ValueError):prepare(source,dest)


if __name__=='__main__':unittest.main()
