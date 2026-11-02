import json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch,Mock
import provider_budget as b
import refill_runner as r
import turkey_scraper as t
import test_refill_runner as fixtures


class OperationsTests(unittest.TestCase):
    def test_source_written_multi_addresses_and_annotations(self):
        for raw,expected in [('a@example.org - b@example.net',['a@example.org','b@example.net']),
                             ('a@example.org; b@example.net',['a@example.org','b@example.net']),
                             ('Av. a@example.org (office)',['a@example.org']),
                             ('abc @example.org',[]),('abc@example',[])]:
            self.assertEqual(t.contact_addresses(raw),expected)

    def test_uncapped_usage_accepts_no_key_caps(self):
        with patch.object(b,'read_zenrows_account',return_value={'usage_credits':123,'credit_limit':1000,'api_key':{'caps':[]}}):
            result=b.read_zenrows_usage('unused')
        self.assertEqual(result['used_credits'],123);self.assertEqual(result['provider_caps'],[])
        self.assertEqual(result['counter_scope'],'account')

    def test_uncapped_children_do_not_require_exact_cap(self):
        args=SimpleNamespace(connection_file='c',solver_file='s',credit_cap=600000,solver_tasks=250,discovery_solver_tasks=100,uncapped=True)
        cmd,_=r.command(Path('/tmp/unused'),'1',1,'34',90,args)
        self.assertNotIn('--provider-credit-cap',cmd)

    def test_solver_amendment_preserves_time_and_only_unblocks_solver_stop(self):
        config={'plan_id':'a','seconds':28800,'credit_cap':600000,'solver_tasks':50,'discovery_solver_tasks':50}
        state={'config':config,'elapsed_seconds':1234,'roles':{'3':{'stop_reason':'solver_limit'},'4':{'stop_reason':'three_phases_without_progress'}}}
        new={**config,'credit_cap':None,'uncapped':True,'solver_tasks':250,'discovery_solver_tasks':100}
        with self.assertRaises(ValueError):r.amend_state(state,new)
        r.amend_state(state,new,True)
        self.assertEqual(state['elapsed_seconds'],1234);self.assertNotIn('stop_reason',state['roles']['3'])
        self.assertEqual(state['roles']['4']['stop_reason'],'three_phases_without_progress')
        self.assertEqual(len(state['budget_amendments']),1)
        with self.assertRaises(ValueError):r.amend_state(state,{**new,'seconds':99999},True)

    def test_final_export_includes_newly_assigned_unstarted_jobs(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);fixture=fixtures.RefillTests();_,registry=fixture.fixture(root)
            try:
                fixture.job(root,'1');r.dispatch(root,registry,'6',[1]);r.export_idle(root,[1])
                rows=[json.loads(s) for s in (root/'worker-01/lawyers.jsonl').read_text().splitlines()]
                self.assertEqual(len(rows),1);self.assertEqual(rows[0]['detail_status'],'pending')
                self.assertIn('bar_association_id',(root/'worker-01/lawyers.csv').read_text().splitlines()[0])
            finally:registry.close()

    def test_uncapped_monitor_outage_does_not_prevent_real_queue_progress(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);fixture=fixtures.RefillTests();_,registry=fixture.fixture(root)
            fixture.job(root,'1');registry.close()
            (root/'c.json').write_text(json.dumps({'cdp_endpoint':'wss://browser.zenrows.com?apikey=test'}));(root/'s.json').write_text(json.dumps({'capsolver_api_key':'test'}))
            args=SimpleNamespace(directory=str(root),run_id='test',seconds=60,credit_cap=600000,solver_tasks=250,discovery_solver_tasks=100,uncapped=True,connection_file=str(root/'c.json'),solver_file=str(root/'s.json'))
            class Child:
                returncode=0
                def poll(self):return 0
            def launch(cmd,**kwargs):
                folder=Path(cmd[cmd.index('--output')+1]);db=t.Database(folder/'checkpoint.sqlite3')
                for key, in db.db.execute('SELECT key FROM details').fetchall():db.complete_detail({**db.record(key),'detail_status':'done'})
                db.db.close();return Child()
            with patch.object(r,'read_zenrows_usage',side_effect=b.BudgetError('outage')),patch.object(r.subprocess,'Popen',side_effect=launch),patch.object(r.time,'sleep'):
                r.run(args)
            report=json.loads((root/'refill-report-test.json').read_text())
            self.assertEqual(report['done'],1);self.assertIsNone(report['shared_key_credit_delta'])
            self.assertEqual(report['usage_monitor_status'],'usage_monitor_unavailable')

    def test_uncapped_authentication_failure_never_launches(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);_,registry=fixtures.RefillTests().fixture(root);registry.close()
            (root/'c.json').write_text(json.dumps({'cdp_endpoint':'wss://browser.zenrows.com?apikey=test'}));(root/'s.json').write_text(json.dumps({'capsolver_api_key':'test'}))
            args=SimpleNamespace(directory=str(root),run_id='test',seconds=60,credit_cap=600000,solver_tasks=250,discovery_solver_tasks=100,uncapped=True,connection_file=str(root/'c.json'),solver_file=str(root/'s.json'))
            with patch.object(r,'read_zenrows_usage',side_effect=b.ProviderAuthorizationError('unauthorized')),patch.object(r.subprocess,'Popen') as launch:
                with self.assertRaises(b.ProviderAuthorizationError):r.run(args)
                launch.assert_not_called()

    def test_rediscovery_does_not_fake_detail_freshness(self):
        old={'detail_status':'done','scraped_at':'old','email':'a@example.org'}
        new={'detail_status':'pending','scraped_at':'new'}
        merged=t.merge_record(old,new);self.assertEqual(merged['scraped_at'],'old');self.assertEqual(merged['_last_seen_at'],'new')

    def test_exact_recovery_attempt_limit_survives_network_failures(self):
        with tempfile.TemporaryDirectory() as td:
            db=t.Database(Path(td)/'checkpoint.sqlite3');qid=db.put_query('34','KA','')
            key=db.upsert({'bar_association_id':'34','bar_registration_number':'123','_lookup_registration':'123','_detail_index':'1','detail_status':'pending'},qid)
            args=SimpleNamespace(detail_concurrency=2,max_details=1,retries=0,min_delay=0,max_delay=0,export_every=10,fail_fast=False)
            q=dict(db.db.execute('SELECT * FROM queries WHERE id=?',(qid,)).fetchone())
            try:
                for _ in range(3):
                    driver=SimpleNamespace(details_attempted=0,details=Mock(side_effect=t.SessionExpired('network disconnected')))
                    with self.assertRaises(t.SessionExpired):t.process_details(driver,db,q,args,Path(td))
                driver=SimpleNamespace(details_attempted=0,details=Mock())
                t.process_details(driver,db,q,args,Path(td));driver.details.assert_not_called()
                self.assertEqual(db.metadata('detail_exact_attempts:'+key),3)
                self.assertEqual(db.db.execute('SELECT status FROM details').fetchone()[0],'needs_review')
            finally:db.db.close()

    def test_shutdown_uses_shared_grace_and_only_kills_unresponsive_child(self):
        import subprocess
        child=Mock();child.poll.return_value=None;child.wait.side_effect=[subprocess.TimeoutExpired('x',90),0]
        with patch.object(r.os,'killpg') as kill,patch.object(r.time,'monotonic',side_effect=[0,10]):
            forced=r.stop_children({2:{'p':child}},90)
        self.assertEqual(forced,[2]);child.terminate.assert_called_once();kill.assert_called_once()
        self.assertEqual(child.wait.call_args_list[0].kwargs['timeout'],80)

if __name__=='__main__':unittest.main()
