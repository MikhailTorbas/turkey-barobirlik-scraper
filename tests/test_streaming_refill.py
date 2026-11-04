import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import refill_runner as r
import turkey_scraper as t
import test_refill_runner as fixtures


class StreamingRefillTests(unittest.TestCase):
    def test_reader_does_not_dispatch_uncommitted_discovery_rows(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);plan,registry=fixtures.RefillTests().fixture(root)
            writer=t.Database(root/'discovery/checkpoint.sqlite3')
            try:
                qid=writer.put_query('6','TE','')
                writer.upsert({'bar_association_id':'6','bar_registration_number':'1','_detail_index':'1'},qid,commit=False)
                self.assertEqual(r.dispatch(root,registry,'6',[2]),(0,0))
                writer.db.commit()
                # Writer stays alive; only its committed identity is visible.
                writer.upsert({'bar_association_id':'6','bar_registration_number':'2','_detail_index':'2'},qid,commit=False)
                self.assertEqual(r.dispatch(root,registry,'6',[2]),(1,0))
                self.assertEqual(r.validate(root,registry,plan)['owned'],1)
            finally:writer.db.close();registry.close()

    def test_healthy_worker_runs_before_discovery_phase_exits(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);plan,registry=fixtures.RefillTests().fixture(root);registry.close()
            db=t.Database(root/'discovery/checkpoint.sqlite3');db.put_query('6','TE','');db.db.close()
            for name,data in [('c.json',{'cdp_endpoint':'wss://browser.zenrows.com?apikey=test'}),('s.json',{'capsolver_api_key':'test'})]:
                (root/name).write_text(json.dumps(data))
            args=SimpleNamespace(directory=str(root),run_id='test',seconds=90,credit_cap=600000,
                solver_tasks=50,discovery_solver_tasks=50,connection_file=str(root/'c.json'),solver_file=str(root/'s.json'))
            clock=[0];producer=[None];completed_while_producer_alive=[]
            class Child:
                returncode=None
                def __init__(self,cmd):self.cmd=cmd;self.polls=0;self.is_producer='--no-details' in cmd
                def poll(self):
                    self.polls+=1
                    if self.returncode is not None:return self.returncode
                    folder=Path(self.cmd[self.cmd.index('--output')+1])
                    if self.is_producer and self.polls==2:
                        db=t.Database(folder/'checkpoint.sqlite3');qid=db.put_query('6','TE','')
                        db.upsert({'bar_association_id':'6','bar_registration_number':'9001','_detail_index':'1','detail_status':'pending'},qid);db.db.close()
                    if self.is_producer and self.polls>=30:
                        db=t.Database(folder/'checkpoint.sqlite3');qid=db.put_query('6','TE','');db.finish(qid,'done');db.db.close();self.returncode=0
                    elif not self.is_producer and self.polls>=3:
                        db=t.Database(folder/'checkpoint.sqlite3')
                        for row in db.db.execute("SELECT key FROM details WHERE status='pending'").fetchall():db.complete_detail({**db.record(row[0]),'detail_status':'done'})
                        db.db.close();completed_while_producer_alive.append(producer[0].returncode is None);self.returncode=0
                    return self.returncode
                def terminate(self):self.returncode=-15
                def wait(self,timeout=None):return self.returncode
            def launch(cmd,**kwargs):
                child=Child(cmd)
                if child.is_producer:producer[0]=child
                return child
            with patch.object(r,'check_zenrows_cap',return_value={'used_credits':0,'remaining_credits':100000}),patch.object(r.subprocess,'Popen',side_effect=launch),patch.object(r.time,'monotonic',side_effect=lambda:clock[0]),patch.object(r.time,'sleep',side_effect=lambda n:clock.__setitem__(0,clock[0]+n)):
                r.run(args)
            self.assertEqual(completed_while_producer_alive,[True])
            self.assertEqual(r.snapshot(root)['done'],1)

    def test_roster_recovery_is_discovery_only_and_bounded(self):
        args=SimpleNamespace(connection_file='c',solver_file='s',credit_cap=600000,solver_tasks=50,discovery_solver_tasks=50,roster_lookups=30)
        discovery,_=r.command(Path('/tmp/unused'),'discovery',1,'6',900,args)
        details,_=r.command(Path('/tmp/unused'),'2',2,'6',900,args)
        self.assertEqual(discovery[discovery.index('--max-roster-lookups')+1],'30')
        self.assertNotIn('--max-roster-lookups',details)

    def test_discovery_uses_empty_slot_instead_of_blocking_assigned_details(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);fixture=fixtures.RefillTests();_,registry=fixture.fixture(root)
            fixture.job(root,'1');r.dispatch(root,registry,'6',[1]);registry.close()
            db=t.Database(root/'discovery/checkpoint.sqlite3');db.put_query('6','ZZ','');db.db.close()
            for name,data in [('c.json',{'cdp_endpoint':'wss://browser.zenrows.com?apikey=test'}),('s.json',{'capsolver_api_key':'test'})]:
                (root/name).write_text(json.dumps(data))
            args=SimpleNamespace(directory=str(root),run_id='test',seconds=30,credit_cap=600000,
                solver_tasks=50,discovery_solver_tasks=50,connection_file=str(root/'c.json'),solver_file=str(root/'s.json'))
            commands=[];clock=[0]
            class Child:
                returncode=None
                def poll(self):return self.returncode
                def terminate(self):self.returncode=-15
                def wait(self,timeout=None):return self.returncode
            def launch(cmd,**kwargs):commands.append(cmd);return Child()
            with patch.object(r,'check_zenrows_cap',return_value={'used_credits':0,'remaining_credits':100000}),patch.object(r.subprocess,'Popen',side_effect=launch),patch.object(r.time,'monotonic',side_effect=lambda:clock[0]),patch.object(r.time,'sleep',side_effect=lambda n:clock.__setitem__(0,clock[0]+n)):
                r.run(args)
            self.assertEqual(len(commands),2)
            self.assertNotIn('--no-details',commands[0])
            self.assertIn('worker-01',commands[0][commands[0].index('--output')+1])
            self.assertIn('--no-details',commands[1])
