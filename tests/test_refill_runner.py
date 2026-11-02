import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import refill_runner as r
import turkey_scraper as t


class RefillTests(unittest.TestCase):
    def fixture(self,root):
        plan={'schema':1,'slots':4,'bar':'6','plan_id':'fixture'}
        (root/'refill-plan.json').write_text(json.dumps(plan))
        for name in ['discovery']+[f'worker-{i:02d}' for i in range(1,5)]:
            folder=root/name;folder.mkdir();db=t.Database(folder/'checkpoint.sqlite3');db.db.close()
        registry=r.owner_db(root)
        return plan,registry

    def job(self,root,reg,bar='6'):
        db=t.Database(root/'discovery/checkpoint.sqlite3');qid=db.put_query(bar,'KA','')
        record={'bar_association_id':bar,'bar_registration_number':reg,'_detail_index':'1','detail_status':'pending'}
        key=db.upsert(record,qid);db.finish(qid,'done');db.db.close();return key

    def test_refills_are_disjoint_and_idempotent(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);plan,registry=self.fixture(root)
            try:
                for i in range(20):self.job(root,str(i+1))
                self.assertEqual(r.dispatch(root,registry,'6',[1,2,3,4],5),(20,0))
                self.assertEqual(r.dispatch(root,registry,'6',[1,2,3,4],5),(0,0))
                self.assertEqual(r.validate(root,registry,plan)['materialized'],20)
                self.assertEqual([v['ready'] for v in r.snapshot(root)['workers'].values()],[5]*4)
            finally:registry.close()

    def test_reserved_job_is_repaired_after_crash_without_reassignment(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);plan,registry=self.fixture(root);key=self.job(root,'610002')
            def crash(*args):raise RuntimeError('power loss')
            try:
                with self.assertRaises(RuntimeError):r.dispatch(root,registry,'6',[2],5,crash)
                self.assertEqual(r.validate(root,registry,plan)['reservations_to_repair'],1)
                r.dispatch(root,registry,'6',[1,2],5)
                self.assertEqual(registry.execute('SELECT worker FROM owners WHERE key=?',(key,)).fetchone()[0],2)
                self.assertEqual(r.snapshot(root)['workers']['2']['ready'],1)
                self.assertEqual(r.snapshot(root)['workers']['1']['ready'],0)
            finally:registry.close()

    def test_completed_baseline_is_not_dispatched_and_completed_workers_unchanged(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);plan,registry=self.fixture(root);key=self.job(root,'610002')
            db=t.Database(root/'discovery/checkpoint.sqlite3');db.complete_detail({**db.record(key),'detail_status':'done','email':'old@example.test'});db.db.close()
            try:
                self.assertEqual(r.dispatch(root,registry,'6',[1,2,3,4]),(0,0))
                key=self.job(root,'69');r.dispatch(root,registry,'6',[1])
                db=t.Database(root/'worker-01/checkpoint.sqlite3');db.complete_detail({**db.record(key),'detail_status':'done','email':'new@example.test'});before=db.record(key);db.db.close()
                self.job(root,'70');r.dispatch(root,registry,'6',[1])
                db=t.Database(root/'worker-01/checkpoint.sqlite3');self.assertEqual(before,db.record(key));db.db.close()
                self.assertEqual(r.snapshot(root)['done'],1)
            finally:registry.close()

    def test_foreign_discovery_and_foreign_worker_are_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);plan,registry=self.fixture(root);self.job(root,'610002','34')
            try:
                with self.assertRaises(ValueError):r.dispatch(root,registry,'6',[1])
                db=t.Database(root/'worker-01/checkpoint.sqlite3');qid=db.put_query('6','KA','');db.upsert({'bar_association_id':'6','bar_registration_number':'99','_detail_index':'1'},qid);db.db.close()
                with self.assertRaises(ValueError):r.validate(root,registry,plan)
            finally:registry.close()

    def test_active_worker_is_not_written(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);plan,registry=self.fixture(root);self.job(root,'610002')
            file=root/'worker-01/checkpoint.sqlite3';before=file.read_bytes()
            try:r.dispatch(root,registry,'6',[2,3,4]);self.assertEqual(file.read_bytes(),before)
            finally:registry.close()

    def test_discovery_uses_same_slot_budget_and_separate_lifetime_ledger(self):
        args=SimpleNamespace(connection_file='c.json',solver_file='s.json',credit_cap=600000,solver_tasks=50,discovery_solver_tasks=50)
        a,_=r.command(Path('/tmp/refill'),'discovery',2,'6',900,args)
        b,_=r.command(Path('/tmp/refill'),'2',2,'6',900,args)
        self.assertIn('--no-details',a);self.assertIn('--primary-field',a);self.assertNotIn('--resume-details-only',a)
        self.assertIn('--resume-details-only',b);self.assertNotEqual(a[a.index('--solver-ledger')+1],b[b.index('--solver-ledger')+1])

    def test_budget_failure_starts_no_children_and_leases_are_released(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);plan,registry=self.fixture(root);registry.close()
            (root/'c.json').write_text(json.dumps({'cdp_endpoint':'wss://browser.zenrows.com?apikey=test'}));(root/'s.json').write_text(json.dumps({'capsolver_api_key':'test'}))
            args=SimpleNamespace(directory=str(root),run_id='test',seconds=60,credit_cap=600000,solver_tasks=50,discovery_solver_tasks=50,connection_file=str(root/'c.json'),solver_file=str(root/'s.json'))
            with patch.object(r,'check_zenrows_cap',side_effect=RuntimeError('cap unavailable')),patch.object(r.subprocess,'Popen') as child:
                for _ in range(2):
                    with self.assertRaises(RuntimeError):r.run(args)
                child.assert_not_called()

    def test_controller_discovers_refills_and_resumes_without_duplicate_completions(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);plan,registry=self.fixture(root)
            for i in range(20):self.job(root,str(i+1))
            r.dispatch(root,registry,'6',[1,2,3,4],5);registry.close()
            db=t.Database(root/'discovery/checkpoint.sqlite3');db.put_query('6','ZZ','');db.db.close()
            (root/'c.json').write_text(json.dumps({'cdp_endpoint':'wss://browser.zenrows.com?apikey=test'}));(root/'s.json').write_text(json.dumps({'capsolver_api_key':'test'}))
            args=SimpleNamespace(directory=str(root),run_id='test',seconds=180,credit_cap=600000,solver_tasks=50,discovery_solver_tasks=50,connection_file=str(root/'c.json'),solver_file=str(root/'s.json'))
            clock=[0];children=[];commands=[];peak=[0]
            class Child:
                def __init__(self,cmd):self.cmd=cmd;self.returncode=None;self.polls=0
                def poll(self):
                    self.polls+=1
                    if self.returncode is None and self.polls>12:
                        folder=Path(self.cmd[self.cmd.index('--output')+1]);db=t.Database(folder/'checkpoint.sqlite3')
                        if '--no-details' in self.cmd:
                            qid=db.db.execute("SELECT id FROM queries WHERE status='pending'").fetchone()[0]
                            db.upsert({'bar_association_id':'6','bar_registration_number':'999','_detail_index':'1','detail_status':'pending'},qid);db.finish(qid,'done')
                        else:
                            for row in db.db.execute("SELECT key FROM details WHERE status='pending'").fetchall():
                                db.complete_detail({**db.record(row[0]),'detail_status':'done','email':'one@example.test'})
                        db.db.close();self.returncode=0
                    return self.returncode
                def terminate(self):self.returncode=-15
                def wait(self,timeout=None):self.returncode=0;return 0
            def launch(cmd,**kwargs):
                child=Child(cmd);children.append(child);commands.append(cmd)
                peak[0]=max(peak[0],sum(c.returncode is None for c in children));return child
            def sleep(seconds):clock[0]+=seconds
            with patch.object(r,'check_zenrows_cap',return_value={'used_credits':10,'remaining_credits':100000}),patch.object(r.subprocess,'Popen',side_effect=launch),patch.object(r.time,'monotonic',side_effect=lambda:clock[0]),patch.object(r.time,'sleep',side_effect=sleep):
                r.run(args)
                completed=r.snapshot(root)['done'];r.run(args)
            self.assertEqual(peak[0],4);self.assertTrue(any('--no-details' in c for c in commands))
            self.assertEqual(completed,21);self.assertEqual(r.snapshot(root)['done'],21)
            registry=r.owner_db(root)
            try:self.assertEqual(r.validate(root,registry,plan)['materialized'],21)
            finally:registry.close()

if __name__=='__main__':unittest.main()
