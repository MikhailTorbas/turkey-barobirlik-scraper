"""Reduced live-browser budgets must preserve every durable worker and resume."""
import json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import refill_runner as r
import turkey_scraper as t
import test_refill_runner as fixtures

class SlotBudgetTests(unittest.TestCase):
 def scenario(self,slots):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);f=fixtures.RefillTests();plan,registry=f.fixture(root)
   for n in range(8):f.job(root,str(n+1))
   r.dispatch(root,registry,'6',[1,2,3,4],2);registry.close()
   db=t.Database(root/'discovery/checkpoint.sqlite3');db.put_query('6','ZZ','');db.db.close()
   for name,data in [('c.json',{'cdp_endpoint':'wss://browser.zenrows.com?apikey=test'}),('s.json',{'capsolver_api_key':'test'})]:(root/name).write_text(json.dumps(data))
   args=SimpleNamespace(directory=str(root),run_id='test',seconds=240,credit_cap=600000,solver_tasks=50,discovery_solver_tasks=50,connection_file=str(root/'c.json'),solver_file=str(root/'s.json'),browser_slots=slots)
   clock=[0];children=[];peak=[0];completed_roles=set();discovered=[False]
   class Child:
    def __init__(self,cmd):self.cmd=cmd;self.returncode=None;self.polls=0
    def poll(self):
     if self.returncode is not None:return self.returncode
     self.polls+=1
     if self.polls<7:return None
     folder=Path(self.cmd[self.cmd.index('--output')+1]);db=t.Database(folder/'checkpoint.sqlite3')
     if '--no-details' in self.cmd:
      for qid, in db.db.execute("SELECT id FROM queries WHERE status='pending'").fetchall():db.finish(qid,'done')
      discovered[0]=True
     else:
      completed_roles.add(folder.name)
      for k, in db.db.execute("SELECT key FROM details WHERE status='pending'").fetchall():db.complete_detail({**db.record(k),'detail_status':'done'})
     db.db.close();self.returncode=0;return 0
    def terminate(self):self.returncode=-15
    def wait(self,timeout=None):return self.returncode
   def launch(cmd,**kw):
    c=Child(cmd);children.append(c);peak[0]=max(peak[0],sum(c.returncode is None for c in children));return c
   with patch.object(r,'check_zenrows_cap',return_value={'used_credits':0,'remaining_credits':100000}),patch.object(r.subprocess,'Popen',side_effect=launch),patch.object(r.time,'monotonic',side_effect=lambda:clock[0]),patch.object(r.time,'sleep',side_effect=lambda n:clock.__setitem__(0,clock[0]+n)):
    r.run(args);before=r.snapshot(root)['done'];args.browser_slots=4;r.run(args)
   self.assertLessEqual(peak[0],slots);self.assertEqual(before,8);self.assertEqual(r.snapshot(root)['done'],8)
   self.assertEqual(completed_roles,{f'worker-{i:02d}' for i in range(1,5)});self.assertTrue(discovered[0])
   state=json.loads((root/'refill-state-test.json').read_text());changes=state['operating_policy_changes']
   self.assertEqual(changes[0]['after']['browser_slots'],slots);self.assertEqual(changes[-1]['after']['browser_slots'],4)
   self.assertEqual(r.validate(root,r.owner_db(root),plan)['owned'],8)
 def test_two_slots_service_all_four_owned_queues_and_discovery(self):self.scenario(2)
 def test_single_slot_does_not_starve_discovery_or_owned_details(self):self.scenario(1)
 def test_invalid_limit_starts_nothing(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);_,reg=fixtures.RefillTests().fixture(root);reg.close()
   args=SimpleNamespace(directory=td,run_id='bad',seconds=1,credit_cap=1,solver_tasks=1,discovery_solver_tasks=1,browser_slots=5)
   with patch.object(r.subprocess,'Popen') as child:
    with self.assertRaises(ValueError):r.run(args)
    child.assert_not_called()
