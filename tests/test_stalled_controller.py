import copy
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import refill_runner as r
import turkey_scraper as t
import test_refill_runner as fixtures


class StalledControllerTests(unittest.TestCase):
    def test_stopped_800_backlog_does_not_starve_discovery_or_healthy_slots(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);fixture=fixtures.RefillTests();plan,registry=fixture.fixture(root)
            for i in range(800):fixture.job(root,str(i+1))
            r.dispatch(root,registry,'6',[3,4],400);registry.close()
            db=t.Database(root/'discovery/checkpoint.sqlite3');db.put_query('6','ZZ','');db.db.close()
            roles={role:{'no_progress':0,'retry_after':0} for role in ['discovery','1','2','3','4']}
            for role in ['3','4']:roles[role].update(no_progress=3,stop_reason='three_phases_without_progress')
            args=SimpleNamespace(directory=str(root),run_id='test',seconds=90,credit_cap=600000,
                solver_tasks=50,discovery_solver_tasks=50,connection_file=str(root/'c.json'),solver_file=str(root/'s.json'))
            for name,data in [('c.json',{'cdp_endpoint':'wss://browser.zenrows.com?apikey=test'}),('s.json',{'capsolver_api_key':'test'})]:
                (root/name).write_text(json.dumps(data))
            state={'config':{'plan_id':plan['plan_id'],'seconds':90,'credit_cap':600000,'solver_tasks':50,'discovery_solver_tasks':50},
                'elapsed_seconds':0,'initial_done':0,'initial_key_credits':0,'roles':roles,'slot_seconds':{'details':0,'discovery':0}}
            (root/'refill-state-test.json').write_text(json.dumps(state))
            clock=[0];commands=[]
            class Child:
                returncode=None
                def __init__(self,cmd):self.cmd=cmd;self.polls=0
                def poll(self):
                    self.polls+=1
                    if self.returncode is None and self.polls>=3:
                        folder=Path(self.cmd[self.cmd.index('--output')+1]);db=t.Database(folder/'checkpoint.sqlite3')
                        try:
                            if '--no-details' in self.cmd:
                                qid=db.db.execute("SELECT id FROM queries WHERE status='pending' LIMIT 1").fetchone()[0]
                                db.upsert({'bar_association_id':'6','bar_registration_number':'9001','_detail_index':'1','detail_status':'pending'},qid)
                                db.finish(qid,'done')
                            else:
                                for row in db.db.execute("SELECT key FROM details WHERE status='pending'").fetchall():
                                    db.complete_detail({**db.record(row[0]),'detail_status':'done','email':'test@example.test'})
                        finally:db.db.close()
                        self.returncode=0
                    return self.returncode
                def terminate(self):self.returncode=-15
                def wait(self,timeout=None):return self.returncode
            def launch(cmd,**kwargs):commands.append(cmd);return Child(cmd)
            with patch.object(r,'check_zenrows_cap',return_value={'used_credits':0,'remaining_credits':100000}), \
                 patch.object(r.subprocess,'Popen',side_effect=launch), \
                 patch.object(r.time,'monotonic',side_effect=lambda:clock[0]), \
                 patch.object(r.time,'sleep',side_effect=lambda n:clock.__setitem__(0,clock[0]+n)):
                r.run(args)
            self.assertTrue(any('--no-details' in cmd for cmd in commands))
            self.assertEqual(r.snapshot(root)['done'],1)
            self.assertEqual(r.snapshot(root)['workers']['3']['ready'],400)
            self.assertEqual(r.snapshot(root)['workers']['4']['ready'],400)
            self.assertFalse(any('worker-03' in x or 'worker-04' in x for cmd in commands for x in cmd))
            report=json.loads((root/'refill-report-test.json').read_text())
            self.assertEqual(report['stranded_ready'],800)
            self.assertEqual(report['runnable_ready'],0)

    def test_operator_recovery_is_recorded_idempotent_and_preserves_limits(self):
        state={'elapsed_seconds':123,'config':{'solver_tasks':500},'roles':{
            '1':{'no_progress':3,'retry_after':999,'stop_reason':'three_phases_without_progress'},
            '2':{'no_progress':0,'stop_reason':'solver_limit'}}}
        original=copy.deepcopy(state)
        self.assertTrue(r.recover_stopped(state,'repair-1'))
        self.assertEqual(state['config'],original['config'])
        self.assertEqual(state['elapsed_seconds'],123)
        self.assertEqual(state['roles']['2'],original['roles']['2'])
        self.assertEqual(state['operator_recoveries'][0]['before']['1'],original['roles']['1'])
        state['roles']['1']['stop_reason']='three_phases_without_progress'
        self.assertFalse(r.recover_stopped(state,'repair-1'))
        self.assertIn('stop_reason',state['roles']['1'])
