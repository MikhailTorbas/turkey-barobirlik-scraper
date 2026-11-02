import os,unittest
from http.server import ThreadingHTTPServer
from threading import Thread
from types import SimpleNamespace
from test_overlap_browser import Handler
import turkey_scraper as t

@unittest.skipUnless(os.getenv('TBB_TEST_BROWSER')=='1','Enable with TBB_TEST_BROWSER=1')
class NetworkRetryTests(unittest.TestCase):
 def check(self,mode):
  from playwright.sync_api import sync_playwright
  server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=Thread(target=server.serve_forever,daemon=True);thread.start()
  try:
   with sync_playwright() as pw:
    browser=pw.chromium.launch(headless=True)
    try:
     page=browser.new_page();page.goto(f'http://127.0.0.1:{server.server_port}/')
     rows=t.parse_html_records(page.content())[:2];token=page.evaluate('()=>window.documentToken=Math.random()')
     page.evaluate('''mode=>{const real=window.fetch.bind(window);window.requestAttempts={};window.fetch=(url,options)=>{
       const index=options.body.get('detay');const count=window.requestAttempts[index]=(window.requestAttempts[index]||0)+1;
       if(index==='1' && mode==='challenge')return Promise.resolve(new Response('<h1>Cloudflare</h1>',{status:403}));
       if(index==='1' && (mode==='permanent'||count===1))return Promise.reject(new TypeError('Failed to fetch'));
       return real(url,options);
     };}''',mode)
     driver=t.DirectoryBrowser(page,t.Config(),SimpleNamespace(headless=True,unattended=True,navigation_timeout=3,auto_verification_timeout=1));driver.last_result=rows;driver.last_query=('69','KA','ME');seen=[];driver.on_detail_extracted=lambda r:seen.append(r['bar_registration_number'])
     if mode=='transient':
      with self.assertLogs(t.LOG,level='WARNING') as logs:found=driver.details(rows,('69','KA','ME'))
      self.assertEqual(len(found),2);self.assertEqual(seen,['610002','610001']);self.assertFalse(driver.needs_session_renewal)
      self.assertIn('"sameSessionRetry": true','\n'.join(logs.output))
     elif mode=='permanent':
      with self.assertRaises(t.SessionExpired):driver.details(rows,('69','KA','ME'))
      self.assertEqual(seen,['610002']);self.assertTrue(driver.needs_session_renewal)
     else:
      with self.assertRaises(t.VerificationRequired):driver.details(rows,('69','KA','ME'))
     attempts=page.evaluate('()=>window.requestAttempts');self.assertEqual(attempts['1'],1 if mode=='challenge' else 2);self.assertEqual(attempts['2'],1)
     self.assertEqual(page.evaluate('()=>window.documentToken'),token);self.assertEqual(len(page.context.pages),1)
     self.assertIsNone(page.evaluate('()=>window.__tbbDetailBatch||null'))
    finally:browser.close()
  finally:server.shutdown();server.server_close();thread.join()
 def test_transient_failure_recovers_in_same_document(self):self.check('transient')
 def test_persistent_failure_preserves_sibling_then_escalates(self):self.check('permanent')
 def test_challenge_is_not_retried_as_network_failure(self):self.check('challenge')
