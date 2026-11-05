import json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import refill_runner as r
import turkey_scraper as t
import test_refill_runner as fixtures

class DiscoveryYieldTests(unittest.TestCase):
 def test_queries_do_not_extend_yield_window_but_new_ids_do(self):
  state={};snap={'discovered_identities':5,'discovery_progress':0}
  self.assertEqual(r.discovery_idle_age(state,snap,100),0)
  self.assertEqual(r.discovery_idle_age(state,{**snap,'discovery_progress':100},170),70)
  self.assertEqual(r.discovery_idle_age(state,{**snap,'discovered_identities':6},180),0)
 def test_verified_roster_absences_are_useful_audit_progress(self):
  state={};snap={'discovered_identities':5,'roster_verification_progress':10}
  r.discovery_idle_age(state,snap,100)
  self.assertEqual(r.discovery_idle_age(state,{**snap,'roster_verification_progress':11},200),0)
 def test_counter_regression_is_an_integrity_error(self):
  state={};r.discovery_idle_age(state,{'discovered_identities':5},0)
  with self.assertRaises(ValueError):r.discovery_idle_age(state,{'discovered_identities':4},20)
 def test_explicit_recovery_is_idempotent_and_preserves_runtime_and_attempts(self):
  state={'elapsed_seconds':120,'roles':{'discovery':{'no_progress':0}},'discovery_yield':{'counters':[5,0],'last_progress_elapsed':0},'discovery_yield_pause':{'idle_seconds':120},'config':{'solver_tasks':50},'solver_attempts':17}
  self.assertTrue(r.recover_stopped(state,'reviewed-1'));self.assertNotIn('discovery_yield_pause',state)
  self.assertEqual(state['discovery_yield']['last_progress_elapsed'],120);self.assertEqual(state['elapsed_seconds'],120);self.assertEqual(state['solver_attempts'],17)
  state['discovery_yield_pause']={'idle_seconds':200}
  self.assertFalse(r.recover_stopped(state,'reviewed-1'));self.assertIn('discovery_yield_pause',state)
 def test_completed_searches_cannot_run_paid_children_forever_and_pause_survives_resume(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);_,reg=fixtures.RefillTests().fixture(root);reg.close()
   db=t.Database(root/'discovery/checkpoint.sqlite3')
   for n in range(30):db.put_query('6','TE',str(n))
   db.db.close()
   for name,data in [('c.json',{'cdp_endpoint':'wss://browser.zenrows.com?apikey=test'}),('s.json',{'capsolver_api_key':'test'})]:(root/name).write_text(json.dumps(data))
   args=SimpleNamespace(directory=td,run_id='test',seconds=600,credit_cap=600000,solver_tasks=50,discovery_solver_tasks=50,connection_file=str(root/'c.json'),solver_file=str(root/'s.json'),discovery_idle_seconds=60)
   clock=[0];children=[]
   class Child:
    def __init__(self,cmd):self.returncode=None;self.polls=0
    def poll(self):
     if self.returncode is not None:return self.returncode
     self.polls+=1
     if self.polls>=5:
      db=t.Database(root/'discovery/checkpoint.sqlite3');row=db.db.execute("SELECT id FROM queries WHERE status='pending' LIMIT 1").fetchone()
      if row:db.finish(row[0],'done')
      db.db.close();self.returncode=0
     return self.returncode
    def terminate(self):self.returncode=-15
    def wait(self,timeout=None):return self.returncode
   def launch(cmd,**kw):c=Child(cmd);children.append(c);return c
   with patch.object(r,'check_zenrows_cap',return_value={'used_credits':0,'remaining_credits':100000}),patch.object(r.subprocess,'Popen',side_effect=launch),patch.object(r.time,'monotonic',side_effect=lambda:clock[0]),patch.object(r.time,'sleep',side_effect=lambda n:clock.__setitem__(0,clock[0]+n)):
    r.run(args);number=len(children);r.run(args)
   self.assertGreater(number,1);self.assertEqual(len(children),number)
   report=json.loads((root/'refill-report-test.json').read_text());self.assertEqual(report['status'],'discovery_yield_paused')
   self.assertGreater(report['discovery_queries']['pending'],0);self.assertGreater(report['discovery_queries']['done'],0);self.assertEqual(report['done'],0)
   state=json.loads((root/'refill-state-test.json').read_text());self.assertIn('discovery_yield_pause',state)
