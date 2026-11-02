import tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from turkey_scraper import Database,parse_html_records,process_details,SessionExpired
FIX=Path(__file__).parent/'fixtures'
class OverlapQueueTests(unittest.TestCase):
 def setup_queue(self,folder,count=2):
  db=Database(Path(folder)/'checkpoint.sqlite3');qid=db.put_query('69','KA','ME')
  for record in parse_html_records((FIX/'live_bayburt_combined.html').read_text())[:count]:db.upsert(record,qid,1,0)
  q=dict(db.db.execute('select * from queries where id=?',(qid,)).fetchone())
  args=SimpleNamespace(detail_concurrency=2,max_details=count,retries=0,retry_backoff=0,max_backoff=0,min_delay=0,max_delay=0,export_every=1,fail_fast=True)
  return db,q,args
 def test_partial_batch_survives_disconnect_and_only_pending_job_resumes(self):
  with tempfile.TemporaryDirectory() as folder:
   db,q,args=self.setup_queue(folder);driver=Mock();driver.details_attempted=0;driver.needs_session_renewal=True
   def partial(records,query):
    saved={**records[0],'detail_status':'done','email':'saved@example.test'}
    driver.on_detail_extracted(saved)
    raise SessionExpired('Session expired with one profile still loading')
   driver.details.side_effect=partial
   with self.assertRaises(SessionExpired):process_details(driver,db,q,args,Path(folder))
   states=[r[0] for r in db.db.execute('select status from details')]
   self.assertCountEqual(states,['done','pending'])
   pending=db.detail_jobs(q['id']);self.assertEqual(len(pending),1)
   saved=db.db.execute("select json from lawyers where json like '%saved@example.test%'").fetchone();self.assertIsNotNone(saved)
   resumed=Mock();resumed.details_attempted=0;resumed.needs_session_renewal=False
   def finish(records,query):
    self.assertEqual(len(records),1)
    row={**records[0],'detail_status':'done'};resumed.on_detail_extracted(row);return [row]
   resumed.details.side_effect=finish
   process_details(resumed,db,q,args,Path(folder))
   self.assertEqual(db.db.execute("select count(*) from details where status='done'").fetchone()[0],2)
   db.db.close()
 def test_odd_budget_does_not_start_an_extra_job(self):
  with tempfile.TemporaryDirectory() as folder:
   db,q,args=self.setup_queue(folder,3);args.max_details=1
   driver=Mock();driver.details_attempted=0;driver.needs_session_renewal=False
   def finish(records,query):
    self.assertEqual(len(records),1);row={**records[0],'detail_status':'done'};driver.on_detail_extracted(row);return [row]
   driver.details.side_effect=finish;process_details(driver,db,q,args,Path(folder))
   self.assertEqual(driver.details_attempted,1)
   self.assertEqual(len(db.detail_jobs(q['id'])),2)
   db.db.close()
 def test_time_limit_requeues_unsaved_sibling_without_losing_completed_one(self):
  from turkey_scraper import RuntimeBudgetExceeded
  with tempfile.TemporaryDirectory() as folder:
   db,q,args=self.setup_queue(folder);driver=Mock();driver.details_attempted=0;driver.needs_session_renewal=False
   def partial(records,query):
    driver.on_detail_extracted({**records[0],'detail_status':'done','email':'saved@example.test'})
    raise RuntimeBudgetExceeded()
   driver.details.side_effect=partial
   with self.assertRaises(RuntimeBudgetExceeded):process_details(driver,db,q,args,Path(folder))
   self.assertCountEqual([tuple(r) for r in db.db.execute('select status,failures from details')],[('done',0),('pending',0)])
   self.assertEqual(db.db.execute("select count(*) from details where status='running'").fetchone()[0],0)
   db.db.close()
 def test_completion_transaction_rolls_back_if_stop_hits_between_writes(self):
  from unittest.mock import patch
  with tempfile.TemporaryDirectory() as folder:
   db,q,args=self.setup_queue(folder);job=db.detail_jobs(q['id'])[0];r=db.record(job['key'])
   with patch.object(db,'detail_state',side_effect=KeyboardInterrupt):
    with self.assertRaises(KeyboardInterrupt):db.complete_detail({**r,'detail_status':'done','email':'new@example.test'})
   self.assertNotEqual(db.record(job['key']).get('detail_status'),'done')
   self.assertEqual(db.db.execute('select status from details where key=?',(job['key'],)).fetchone()[0],'pending')
   db.complete_detail({**r,'detail_status':'done','email':'new@example.test'})
   self.assertEqual(db.db.execute('select status from details where key=?',(job['key'],)).fetchone()[0],'done')
   db.db.close()

class VerificationGraceTests(unittest.TestCase):
 def elapsed_grace(self,observed_form):
  from unittest.mock import patch
  from turkey_scraper import DirectoryBrowser,Config
  clock=[0.0];page=Mock();page.evaluate.return_value=observed_form
  page.wait_for_timeout.side_effect=lambda ms:clock.__setitem__(0,clock[0]+ms/1000)
  args=SimpleNamespace(_solver=Mock(),headless=True,unattended=True,auto_verification_timeout=30,widget_grace=5,capture_failures=False)
  driver=DirectoryBrowser(page,Config(),args);driver.challenge_required=Mock(return_value=True);driver.solve_turnstile=Mock()
  with patch('turkey_scraper.time.monotonic',side_effect=lambda:clock[0]):driver.wait_for_turnstile()
  driver.solve_turnstile.assert_called_once();return clock[0]
 def test_observed_widget_uses_short_grace(self):self.assertEqual(self.elapsed_grace(True),5)
 def test_outer_challenge_retains_long_grace(self):self.assertEqual(self.elapsed_grace(False),30)

class ExhaustedBudgetTests(unittest.TestCase):
 def test_access_retry_does_not_buy_a_new_session_without_detail_budget(self):
  from unittest.mock import patch
  import turkey_scraper as scraper
  with tempfile.TemporaryDirectory() as folder:
   calls=[]
   def blocked(args):
    calls.append(1);db=Database(Path(folder)/'checkpoint.sqlite3');qid=db.put_query('69','KA','ME')
    row=parse_html_records((FIX/'live_bayburt_combined.html').read_text())[0];key=db.upsert(row,qid,1,0)
    db.detail_state(key,'running');db.metadata('run_status','access_blocked');db.db.close();return 2
   with patch.object(scraper,'run',side_effect=blocked):
    code=scraper.cli(['--baro','69','--prefix','KA','--max-details','1','--max-searches','2','--output',folder,'--access-retries','2','--access-cooldown','1'])
   self.assertEqual(code,2);self.assertEqual(len(calls),1)

class DedicatedCloseTests(unittest.TestCase):
 def test_owned_remote_browser_is_asked_to_close_before_disconnect(self):
  from turkey_scraper import close_dedicated_browser
  browser=Mock();calls=[]
  browser.new_browser_cdp_session.return_value.send.side_effect=lambda method:calls.append(method)
  browser.close.side_effect=lambda:calls.append('disconnect')
  close_dedicated_browser(browser)
  self.assertEqual(calls,['Browser.close','disconnect'])
