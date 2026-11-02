"""A malformed contact must not lose its concurrent sibling or buy a session."""
import os,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from http.server import ThreadingHTTPServer
from threading import Thread
from test_overlap_browser import Handler
import turkey_scraper as t

@unittest.skipUnless(os.getenv('TBB_TEST_BROWSER')=='1','Enable with TBB_TEST_BROWSER=1')
class ParseIsolationTests(unittest.TestCase):
 def test_bad_fast_response_saves_slow_sibling_and_retries_only_bad_in_same_session(self):
  from playwright.sync_api import sync_playwright
  server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=Thread(target=server.serve_forever,daemon=True);thread.start()
  try:
   with tempfile.TemporaryDirectory() as folder,sync_playwright() as pw:
    browser=pw.chromium.launch(headless=True)
    try:
     page=browser.new_page();page.goto(f'http://127.0.0.1:{server.server_port}/')
     token=page.evaluate('()=>window.documentToken=Math.random()')
     rows=t.parse_html_records(page.content())[:2]
     db=t.Database(Path(folder)/'checkpoint.sqlite3');qid=db.put_query('69','KA','ME')
     for row in rows:db.upsert(row,qid,1,0)
     q=dict(db.db.execute('select * from queries where id=?',(qid,)).fetchone())
     args=SimpleNamespace(headless=True,unattended=True,navigation_timeout=3,auto_verification_timeout=1,detail_concurrency=2,max_details=2,retries=1,retry_backoff=0,max_backoff=0,min_delay=0,max_delay=0,export_every=1,fail_fast=False)
     driver=t.DirectoryBrowser(page,t.Config(),args);driver.last_result=rows;driver.last_query=('69','KA','ME');calls=[];original=t.parse_detail
     def parse(html,listing=None):
      calls.append(listing['bar_registration_number'])
      if listing['bar_registration_number']=='610002':raise t.ExtractionError('Cannot decode protected email; detail remains pending')
      return original(html,listing)
     with patch.object(t,'parse_detail',side_effect=parse):t.process_details(driver,db,q,args,Path(folder))
     self.assertEqual(calls.count('610001'),1);self.assertEqual(calls.count('610002'),2)
     states={db.record(r['key'])['bar_registration_number']:r['status'] for r in db.db.execute('select * from details')}
     self.assertEqual(states,{'610001':'done','610002':'failed'})
     self.assertFalse(driver.needs_session_renewal)
     self.assertEqual(page.evaluate('()=>window.documentToken'),token)
     self.assertEqual(len(page.context.pages),1)
     self.assertIsNone(page.evaluate('()=>window.__tbbDetailBatch || null'))
     db.db.close()
    finally:browser.close()
  finally:server.shutdown();server.server_close();thread.join()
