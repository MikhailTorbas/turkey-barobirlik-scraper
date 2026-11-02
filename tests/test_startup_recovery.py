import os,unittest,tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
import turkey_scraper as t

class StartupTests(unittest.TestCase):
    def driver(self,states,goto_error=None,timeout=3):
        clock=[0.0]
        page=Mock();page.wait_for_timeout.side_effect=lambda ms:clock.__setitem__(0,clock[0]+ms/1000)
        if goto_error:page.goto.side_effect=goto_error
        args=SimpleNamespace(navigation_timeout=1,startup_timeout=timeout)
        driver=t.DirectoryBrowser(page,t.Config(),args)
        state_iter=iter(states);last=states[-1]
        driver.directory_state=lambda:next(state_iter,last)
        driver.wait_for_turnstile=Mock()
        return driver,page,clock

    def test_outer_managed_view_waits_for_real_form_before_solver_path(self):
        driver,page,clock=self.driver([{'ready':False,'managed':True}]*4+[{'ready':True,'managed':False}])
        with patch.object(t.time,'monotonic',side_effect=lambda:clock[0]):driver.navigate(t.URL)
        driver.wait_for_turnstile.assert_called_once()
        self.assertEqual(page.goto.call_count,1)
        self.assertEqual(driver.startup_stats['managed_observations'],4)
        self.assertEqual(page.goto.call_args.kwargs['wait_until'],'commit')

    def test_deadline_without_form_never_enters_ordinary_solver(self):
        driver,page,clock=self.driver([{'ready':False,'managed':True}],timeout=2)
        with patch.object(t.time,'monotonic',side_effect=lambda:clock[0]):
            with self.assertRaisesRegex(t.VerificationRequired,'Startup deadline'):driver.navigate(t.URL)
        driver.wait_for_turnstile.assert_not_called()
        self.assertEqual(page.goto.call_count,1)
        self.assertEqual(clock[0],2)

    def test_transient_net_timeout_reuses_session_once_then_succeeds(self):
        driver,page,clock=self.driver([{'ready':False,'managed':False},{'ready':True,'managed':False}],
            [RuntimeError('Page.goto: net::ERR_TIMED_OUT'),None])
        with patch.object(t.time,'monotonic',side_effect=lambda:clock[0]):driver.navigate(t.URL)
        self.assertEqual(page.goto.call_count,2)
        self.assertEqual(driver.startup_stats['transient_navigation_retries'],1)

    def test_navigation_error_does_not_discard_already_ready_form(self):
        driver,page,clock=self.driver([{'ready':True,'managed':False}],[RuntimeError('Page.goto: net::ERR_TIMED_OUT')])
        with patch.object(t.time,'monotonic',side_effect=lambda:clock[0]):driver.navigate(t.URL)
        self.assertEqual(page.goto.call_count,1)
        driver.wait_for_turnstile.assert_called_once()

    def test_two_network_failures_escalate_without_unbounded_reload(self):
        driver,page,clock=self.driver([{'ready':False,'managed':False}],RuntimeError('Page.goto: net::ERR_TIMED_OUT'))
        with patch.object(t.time,'monotonic',side_effect=lambda:clock[0]):
            with self.assertRaises(t.SessionExpired):driver.navigate(t.URL)
        self.assertEqual(page.goto.call_count,2)
        driver.wait_for_turnstile.assert_not_called()

    def test_closed_browser_is_not_retried_inside_dead_context(self):
        driver,page,clock=self.driver([{'ready':False,'managed':False}],RuntimeError('browser has been closed'))
        with self.assertRaises(t.SessionExpired):driver.navigate(t.URL)
        self.assertEqual(page.goto.call_count,1)

    def test_blocked_access_retries_are_bounded_and_keep_saved_job(self):
        with tempfile.TemporaryDirectory() as td:
            attempts=[]
            def blocked(args):
                db=t.Database(Path(td)/'checkpoint.sqlite3')
                q=db.put_query('69','KA')
                key=db.upsert({'bar_association_id':'69','bar_registration_number':'610002','_detail_index':'2','detail_status':'pending'},q)
                attempts.append(db.db.execute('select status,failures from details where key=?',(key,)).fetchone()[:])
                db.metadata('run_status','access_blocked');db.db.close();return 2
            with patch.object(t,'run',side_effect=blocked),patch.object(t.time,'sleep') as sleep:
                result=t.cli(['--output',td,'--population-file','','--access-retries','2','--access-cooldown','10','--max-runtime','60'])
            self.assertEqual(result,2)
            self.assertEqual(attempts,[('pending',0)]*3)
            self.assertEqual([call.args[0] for call in sleep.call_args_list],[10,20])

    def test_successful_access_recovery_stops_without_resetting_detail_limit(self):
        with tempfile.TemporaryDirectory() as td:
            calls=[]
            def attempt(args):
                calls.append(args.max_details)
                db=t.Database(Path(td)/'checkpoint.sqlite3')
                db.metadata('run_status','access_blocked' if len(calls)==1 else 'detail_queue_finished')
                db.db.close();return 2 if len(calls)==1 else 0
            with patch.object(t,'run',side_effect=attempt),patch.object(t.time,'sleep') as sleep:
                result=t.cli(['--output',td,'--population-file','','--access-retries','2','--access-cooldown','10','--max-details','5','--max-runtime','60'])
            self.assertEqual(result,0);self.assertEqual(calls,[5,5]);sleep.assert_called_once_with(10)

@unittest.skipUnless(os.getenv('TBB_TEST_BROWSER')=='1','Enable local browser tests')
class StartupBrowserTests(unittest.TestCase):
    def test_asynchronous_challenge_replacement_and_real_form_structure(self):
        from playwright.sync_api import sync_playwright
        import json
        form='<form id="avForm"><input name="ad"><input name="soyad"><select name="baroId"><option value="69">Bayburt</option></select></form>'
        html='<body>Just a moment Cloudflare<script>setTimeout(()=>document.body.innerHTML='+json.dumps(form)+',250)</script>'
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True)
            try:
                page=browser.new_page();page.route('https://example.test/',lambda route:route.fulfill(body=html,content_type='text/html'))
                args=SimpleNamespace(navigation_timeout=2,startup_timeout=3,headless=True,unattended=True,auto_verification_timeout=1,
                    _solver=SimpleNamespace(solve=lambda _:self.fail('Outer challenge reached ordinary solver')))
                driver=t.DirectoryBrowser(page,t.Config(),args);driver.navigate('https://example.test/')
                self.assertTrue(driver.directory_state()['ready'])
                page.set_content('<form><input name="ad"></form><form><input name="soyad"><select name="baroId"></select></form>')
                self.assertFalse(driver.directory_state()['ready'])
            finally:browser.close()

if __name__=='__main__':unittest.main()
