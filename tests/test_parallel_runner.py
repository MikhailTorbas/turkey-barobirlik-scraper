import fcntl,json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import parallel_runner as p
import worker_distribution as w
import turkey_scraper as t

class RunnerTests(unittest.TestCase):
    def fixture(self,root,done=False):
        worker=root/'worker-01';worker.mkdir();db=t.Database(worker/'checkpoint.sqlite3');q=db.put_query('69','KA')
        record={'bar_association_id':'69','bar_registration_number':'610002','_detail_index':'2','detail_status':'pending'}
        key=db.upsert(record,q);db.finish(q,'done')
        db.metadata('distribution_plan',{'plan_id':'test','worker':1,'scope':'test'})
        if done:db.complete_detail({**record,'detail_status':'done'})
        db.db.close()
        m={'plan_id':'test','scope':'test','assignments':[{'worker':1,'jobs':[{'key':key,'query':['69','KA',''],'record':record}]}]}
        (root/'manifest.json').write_text(json.dumps(m))
        (root/'connection.json').write_text(json.dumps({'cdp_endpoint':'wss://browser.zenrows.com?apikey=test'}))
        (root/'solver.json').write_text('{}')
        return SimpleNamespace(directory=str(root),worker=None,run_id='test',seconds=60,credit_cap=200000,solver_tasks=50,
                               connection_file=str(root/'connection.json'),solver_file=str(root/'solver.json'))
    def test_worker_selection_prevents_untested_eight_worker_launch(self):
        m={'assignments':[{'worker':i} for i in range(1,13)]}
        with self.assertRaises(ValueError):p.validate_selection(m,None)
        self.assertEqual(p.validate_selection(m,[1,2,3,4]),[1,2,3,4])
        with self.assertRaises(ValueError):p.validate_selection(m,[99])
    def test_missing_credit_preflight_opens_no_worker(self):
        with tempfile.TemporaryDirectory() as td:
            args=self.fixture(Path(td))
            with patch.object(p,'check_zenrows_cap',side_effect=RuntimeError('unavailable')),patch.object(p.subprocess,'Popen') as launch:
                with self.assertRaises(RuntimeError):p.run(args)
            launch.assert_not_called()
    def test_locked_worker_does_not_overwrite_controller_state(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);args=self.fixture(root);state=root/'parallel-state-test-1.json'
            with (root/'worker-01/parallel-owner.lock').open('a+') as lock:
                fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
                with patch.object(p,'check_zenrows_cap',return_value={'used_credits':0,'remaining_credits':100000}),patch.object(p.subprocess,'Popen') as launch:
                    with self.assertRaises(BlockingIOError):p.run(args)
                self.assertFalse(state.exists());launch.assert_not_called()
    def test_completed_queue_opens_no_browser_and_resume_keeps_initial_count(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);args=self.fixture(root,done=True)
            with patch.object(p,'check_zenrows_cap',return_value={'used_credits':10,'remaining_credits':100000}),patch.object(p.subprocess,'Popen') as launch,patch.object(p.time,'sleep'):
                self.assertEqual(p.run(args),0)
                first=json.loads((root/'parallel-state-test-1.json').read_text());self.assertEqual(p.run(args),0)
            self.assertEqual(json.loads((root/'parallel-state-test-1.json').read_text())['workers']['1']['initial_done'],1)
            self.assertEqual(json.loads((root/'parallel-report-test-1.json').read_text())['new_completed_profiles'],0)
            launch.assert_not_called()
    def test_planned_stop_keeps_recovery_budget(self):
        s={'cursor':0,'no_progress':0};p.phase_transition(s,0,True)
        self.assertEqual(s['no_progress'],0)
        for _ in range(3):p.phase_transition(s,0,False)
        self.assertEqual(s['stop_reason'],'three_phases_without_progress')
    def test_prepared_pending_job_runs_once_and_reports_only_new_completion(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);args=self.fixture(root);commands=[]
            class Child:
                returncode=0
                def poll(self):return 0
            def launch(cmd,**kwargs):
                commands.append(cmd);folder=Path(cmd[cmd.index('--output')+1]);db=t.Database(folder/'checkpoint.sqlite3')
                key=db.db.execute('select key from details').fetchone()[0]
                db.complete_detail({**db.record(key),'detail_status':'done','email':'new@example.test'});db.db.close()
                return Child()
            with patch.object(p,'check_zenrows_cap',return_value={'used_credits':10,'remaining_credits':100000}),patch.object(p.subprocess,'Popen',side_effect=launch),patch.object(p.time,'sleep'):
                self.assertEqual(p.run(args),0)
            self.assertEqual(len(commands),1)
            self.assertIn('--resume-details-only',commands[0]);self.assertIn('--startup-timeout',commands[0])
            self.assertEqual(json.loads((root/'parallel-report-test-1.json').read_text())['new_completed_profiles'],1)

if __name__=='__main__':unittest.main()
