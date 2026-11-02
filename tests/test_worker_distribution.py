import hashlib,json,tempfile,unittest
from pathlib import Path
import turkey_scraper as t
import worker_distribution as w

class DistributionTests(unittest.TestCase):
 def source(self,path,count=25):
  path=Path(path);path.mkdir();db=t.Database(path/'checkpoint.sqlite3');qid=db.put_query('69','KA');db.db.execute("insert into bars values('69','BAYBURT',1)")
  for n in range(count):
   record={'bar_association_id':'69','bar_association':'Bayburt Barosu','bar_registration_number':str(n),'full_name':f'NAME KAYA {n}','first_name':'NAME','last_name':'KAYA','_detail_index':str(n+1),'detail_status':'pending'};key=db.upsert(record,qid)
   if n==0:record['detail_status']='done';db.upsert(record);db.detail_state(key,'done')
  db.finish(qid,'done');db.db.close();return path
 def test_balanced_disjoint_plan_excludes_completed(self):
  with tempfile.TemporaryDirectory() as td:
   source=self.source(Path(td)/'source');plan=w.plan(source,12,2);keys=[j['key'] for a in plan['assignments'] for j in a['jobs']];self.assertEqual(len(keys),24);self.assertEqual(len(set(keys)),24);self.assertEqual(plan['completed_master_profiles_excluded'],1);self.assertEqual({len(a['jobs']) for a in plan['assignments']},{2})
 def test_materialize_preserves_master_and_refuses_overwrite(self):
  with tempfile.TemporaryDirectory() as td:
   source=self.source(Path(td)/'source');file=source/'checkpoint.sqlite3';before=hashlib.sha256(file.read_bytes()).hexdigest();plan=w.plan(source,3,2);dest=Path(td)/'workers';w.materialize(plan,dest);report=w.verify_outputs(plan,dest);self.assertEqual(report['unique_assigned_profiles'],24);self.assertEqual(hashlib.sha256(file.read_bytes()).hexdigest(),before)
   with self.assertRaises(ValueError):w.materialize(plan,dest)
 def test_repartitioning_worker_outputs_excludes_newly_completed_profiles(self):
  with tempfile.TemporaryDirectory() as td:
   source=self.source(Path(td)/'source',9);plan=w.plan(source,2,2);dest=Path(td)/'workers';w.materialize(plan,dest)
   job=plan['assignments'][0]['jobs'][0];db=t.Database(dest/'worker-01/checkpoint.sqlite3')
   db.complete_detail({**job['record'],'detail_status':'done'});db.db.close()
   new=w.plan(dest,4,2);keys={j['key'] for a in new['assignments'] for j in a['jobs']}
   self.assertEqual(len(keys),7);self.assertNotIn(job['key'],keys)
 def test_worker_copy_or_foreign_identity_is_rejected(self):
  with tempfile.TemporaryDirectory() as td:
   source=self.source(Path(td)/'source');plan=w.plan(source,2,2);dest=Path(td)/'workers';w.materialize(plan,dest)
   db=t.Database(dest/'worker-01/checkpoint.sqlite3');db.upsert({'bar_association_id':'69','bar_registration_number':'foreign'});db.db.close()
   with self.assertRaises(ValueError):w.verify_outputs(plan,dest)
 def test_merge_only_verified_completed_results_to_new_output(self):
  with tempfile.TemporaryDirectory() as td:
   source=self.source(Path(td)/'source',5);plan=w.plan(source,2,2);dest=Path(td)/'workers';w.materialize(plan,dest)
   first=plan['assignments'][0]['jobs'][0];db=t.Database(dest/'worker-01/checkpoint.sqlite3');record=db.record(first['key']);record.update(detail_status='done',email='result@example.org');db.upsert(record);db.detail_state(first['key'],'done');db.db.close()
   output=Path(td)/'merged';report=w.merge(plan,dest,output);rows=[json.loads(x) for x in (output/'lawyers.jsonl').read_text().splitlines()];self.assertEqual(len(rows),1);self.assertEqual(rows[0]['email'],'result@example.org');self.assertFalse(report['national_completeness_claim'])
   with self.assertRaises(ValueError):w.merge(plan,dest,output)
 def test_pending_failure_history_is_not_reset(self):
  with tempfile.TemporaryDirectory() as td:
   source=self.source(Path(td)/'source',2);db=t.Database(source/'checkpoint.sqlite3');db.db.execute("update details set failures=2 where status='pending'");db.db.commit();db.db.close();plan=w.plan(source,1);dest=Path(td)/'workers';w.materialize(plan,dest);db=t.Database(dest/'worker-01/checkpoint.sqlite3');self.assertEqual(db.db.execute('select failures from details').fetchone()[0],2);db.db.close()
 def test_exact_registration_recovery_survives_worker_distribution(self):
  with tempfile.TemporaryDirectory() as td:
   source=self.source(Path(td)/'source',2);db=t.Database(source/'checkpoint.sqlite3');key=db.db.execute("SELECT key FROM details WHERE status='pending'").fetchone()[0];record=db.record(key);record['_lookup_registration']=record['bar_registration_number'];db.upsert(record);db.db.close()
   plan=w.plan(source,1);dest=Path(td)/'workers';w.materialize(plan,dest);db=t.Database(dest/'worker-01/checkpoint.sqlite3');self.assertEqual(db.record(key)['_lookup_registration'],record['bar_registration_number']);db.db.close()
if __name__=='__main__':unittest.main()
