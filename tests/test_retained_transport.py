import json,socket,sys,time,unittest,tempfile,os
from pathlib import Path
from threading import Lock,Thread
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from types import SimpleNamespace
from urllib.parse import parse_qs
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import turkey_scraper as t
from retained_transport import browser_class,PACK
CompactOverlapBrowser=browser_class(t)
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
FIX=ROOT/'tests/fixtures'
FORM='<form id="avForm" method="post" action="/"><input name="ad"><input name="soyad"><input name="barosicil"><input type="hidden" name="csrf" value="original"><select name="baroId"><option value="69">BAYBURT</option></select><button name="tip" value="Avukat">Search</button></form>'

def detail(reg):
 soup=BeautifulSoup((FIX/'live_bayburt_detail.html').read_text(),'html.parser')
 for tr in soup.select('tr'):
  cells=tr.select(':scope > td')
  if len(cells)<2:continue
  label=cells[0].get_text(' ',strip=True)
  if label=='Baro Sicil No':cells[-1].string=reg
  if label=='TBB Sicil No':cells[-1].string='1329'+reg
  if label=='E-Posta':
   cells[-1].clear();span=soup.new_tag('span');span['data-cfemail']=bytes([42,*[ord(c)^42 for c in f'lawyer{reg}@example.org']]).hex();span.string='[email protected]';cells[-1].append(span)
 return '<html><body><div>'+('outside '*10000)+'</div>'+str(soup)+'<script>irrelevant()</script></body></html>'

class Handler(BaseHTTPRequestHandler):
 mode='ok';active=0;maximum=0;fields=[];finishes=[];calls={};lock=Lock();searches=0;gets=0
 def log_message(self,*_):pass
 def send(self,html,status=200):
  body=html.encode();self.send_response(status);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
 def do_GET(self):
  Handler.gets+=1;self.send(FORM)
 def do_POST(self):
  data=parse_qs(self.rfile.read(int(self.headers['Content-Length'])).decode());Handler.fields.append(data)
  if 'detay' not in data:
   Handler.searches+=1
   if Handler.mode=='expire_once' and Handler.searches==1:return self.send('<form id="avForm"><div class="alert-danger">Expired form</div></form>')
   if data.get('soyad')==['ZZ']:return self.send('<form id="avForm"><h3>0 kayıt listelendi.</h3></form>')
   soup=BeautifulSoup((FIX/'live_bayburt_combined.html').read_text(),'html.parser');soup.select_one('#avForm')['action']='/'
   if data.get('barosicil') and Handler.mode!='registration_mismatch':
    for row in soup.select('tbody tr'):
     if row.select('td')[2].get_text(strip=True)!=data['barosicil'][0]:row.decompose()
    soup.select_one('h3').string=str(len(soup.select('button[name=detay]')))+' kayıt listelendi.'
   hidden=soup.new_tag('input');hidden['name']='csrf';hidden['value']='listing';soup.select_one('#avForm').append(hidden)
   wrapper='<div>'+('outside '*10000)+'</div>'
   if Handler.mode=='search_challenge':wrapper+='<script>window._cf_chl_opt={};</script>'
   if Handler.mode=='pagination':wrapper+='<a rel="next" href="/page2">Next</a>'
   return self.send('<html>'+wrapper+str(soup)+'</html>')
  reg={'1':'610001','2':'610002'}[data['detay'][0]]
  with Handler.lock:Handler.calls[reg]=Handler.calls.get(reg,0)+1;call=Handler.calls[reg];Handler.active+=1;Handler.maximum=max(Handler.maximum,Handler.active)
  try:
   if Handler.mode=='network' and reg=='610002' and call==1:
    self.connection.shutdown(socket.SHUT_RDWR);self.connection.close();return
   time.sleep((2 if Handler.mode=='slow' else .15) if reg=='610002' else .03);html=detail(reg)
   if Handler.mode=='detail_challenge' and reg=='610002':html='<script>window._cf_chl_opt={};</script>'+html
   if Handler.mode=='bad_email' and reg=='610002':html=html.replace('data-cfemail="','data-cfemail="zz')
   Handler.finishes.append(reg);self.send(html)
  finally:
   with Handler.lock:Handler.active-=1

@unittest.skipUnless(os.getenv('TBB_TEST_BROWSER')=='1','Enable with TBB_TEST_BROWSER=1')
class CompactTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.server=ThreadingHTTPServer(('127.0.0.1',0),Handler);Thread(target=cls.server.serve_forever,daemon=True).start();cls.pw=sync_playwright().start();cls.browser=cls.pw.chromium.launch(headless=True)
 @classmethod
 def tearDownClass(cls):cls.browser.close();cls.pw.stop();cls.server.shutdown();cls.server.server_close()
 def setUp(self):
  Handler.mode='ok';Handler.fields=[];Handler.maximum=0;Handler.active=0;Handler.calls={};Handler.finishes=[];Handler.searches=0;Handler.gets=0
  self.page=self.browser.new_page();self.url=f'http://127.0.0.1:{self.server.server_port}/';self.page.goto(self.url);self.page.evaluate('window.marker=19');self.driver=CompactOverlapBrowser(self.page,t.Config(),SimpleNamespace(navigation_timeout=3,url=self.url,form_refreshes=0))
 def tearDown(self):self.page.close()
 def targets(self):
  rows,total,_=self.driver.fetch('69','KA','ME');self.assertEqual(total,5);return [next(r for r in rows if r['bar_registration_number']==reg) for reg in ['610002','610001']]
 def test_exact_registration_and_detail_use_same_verified_listing(self):
  rows,total,_=self.driver.fetch_registration('69','610002')
  self.assertEqual(total,1);self.assertEqual(rows[0]['bar_registration_number'],'610002')
  self.assertEqual(Handler.fields[-1]['barosicil'],['610002'])
  found=self.driver.details(rows,('69','','','610002'))
  self.assertEqual(found[0]['email'],'lawyer610002@example.org');self.assertEqual(Handler.searches,1)
  self.driver.fetch('69','KA','ME');self.assertNotIn('barosicil',Handler.fields[-1])
 def test_exact_registration_zero_is_distinct_from_mismatched_identity(self):
  rows,total,_=self.driver.fetch_registration('69','9999999')
  self.assertEqual((rows,total),([],0))
  Handler.mode='registration_mismatch'
  with self.assertRaisesRegex(t.ExtractionError,'another identity'):self.driver.fetch_registration('69','610002')
 def test_pending_discovery_can_resume_exact_detail_without_a_name_search(self):
  with tempfile.TemporaryDirectory() as temp:
   db=t.Database(Path(temp)/'checkpoint.sqlite3');qid=db.put_query('69','','')
   rows,_,_=self.driver.fetch_registration('69','610002');record=rows[0];record['_lookup_registration']='610002';db.upsert(record,qid)
   self.driver.last_query=None;self.driver.details_attempted=0
   args=SimpleNamespace(detail_concurrency=2,max_details=1,retries=0,retry_backoff=0,max_backoff=0,min_delay=0,max_delay=0,export_every=1,fail_fast=True,max_queries=20,max_detail_failures=3)
   q=dict(db.db.execute('SELECT * FROM queries WHERE id=?',(qid,)).fetchone())
   t.process_details(self.driver,db,q,args,Path(temp))
   saved=db.record(t.record_key(record));self.assertEqual(saved['email'],'lawyer610002@example.org')
   self.assertEqual(db.db.execute('SELECT status FROM queries WHERE id=?',(qid,)).fetchone()[0],'pending')
   self.assertEqual(Handler.fields[-2]['barosicil'],['610002']);db.db.close()
 def test_overlap_payload_identity_fields_and_csrf(self):
  records=self.targets();found=self.driver.details(records,('69','KA','ME'))
  self.assertEqual([r['bar_registration_number'] for r in found],['610002','610001']);self.assertEqual(Handler.maximum,2);self.assertEqual(Handler.finishes,['610001','610002'])
  for record,result in zip(records,found):
   expected=t.parse_detail(detail(record['bar_registration_number']),record)
   for field in [*t.CONTACT_FIELDS,'tbb_registration_number','bar_registration_number','_field_availability']:self.assertEqual(result.get(field),expected.get(field),field)
  self.assertLess(self.driver.search_reply['returned_html_bytes']/self.driver.search_reply['raw_html_bytes'],0.1)
  self.assertTrue(all(x['returned_html_bytes']/x['raw_html_bytes']<0.1 for x in self.driver.detail_payloads))
  self.assertTrue(all(x['csrf']==['listing'] for x in Handler.fields if 'detay' in x));self.assertEqual(Handler.fields[0]['csrf'],['original'])
  self.assertEqual(self.page.evaluate('window.marker'),19);self.assertFalse(self.page.locator('button[name=detay]').count())
  self.targets();self.assertEqual(self.page.evaluate('window.marker'),19)
 def test_challenge_outside_form_survives_reduction(self):
  Handler.mode='search_challenge'
  with self.assertRaises(t.VerificationRequired):self.targets()
 def test_external_pagination_survives_reduction(self):
  Handler.mode='pagination'
  with self.assertRaisesRegex(t.ExtractionError,'pagination'):self.targets()
 def test_invalid_email_preserves_good_sibling(self):
  records=self.targets();Handler.mode='bad_email';saved=[];self.driver.on_detail_extracted=saved.append
  with self.assertRaises(t.ExtractionError):self.driver.details(records,('69','KA','ME'))
  self.assertEqual([r['bar_registration_number'] for r in saved],['610001'])
 def test_challenged_sibling_preserves_good_sibling(self):
  records=self.targets();Handler.mode='detail_challenge';saved=[];self.driver.on_detail_extracted=saved.append
  with self.assertRaises(t.VerificationRequired):self.driver.details(records,('69','KA','ME'))
  self.assertEqual([r['bar_registration_number'] for r in saved],['610001'])
 def test_transport_retry_is_bounded_and_same_document(self):
  records=self.targets();Handler.mode='network';found=self.driver.details(records,('69','KA','ME'));self.assertEqual(len(found),2);self.assertEqual(Handler.calls['610002'],2);self.assertEqual(Handler.calls['610001'],1);self.assertEqual(self.page.evaluate('window.marker'),19)
 def test_search_fetch_retry_preserves_verified_document_and_counts_attempts(self):
  self.page.evaluate('''()=>{const real=fetch.bind(window);window.searchTries=0;window.fetch=(url,opts)=>{
   if(!opts.body.has('detay') && ++window.searchTries===1)return Promise.reject(new TypeError('Failed to fetch'));
   return real(url,opts);
  };}''')
  rows,total,_=self.driver.fetch('69','KA','ME')
  self.assertEqual(total,5);self.assertEqual(self.page.evaluate('window.searchTries'),2)
  self.assertEqual(self.driver.stats['search_post_attempts'],2)
  self.assertEqual(self.page.evaluate('window.marker'),19);self.assertEqual(Handler.gets,1)
 def test_exhausted_search_transport_does_not_fail_profile_extraction(self):
  for error in ['TypeError','AbortError']:
   with self.subTest(error=error),tempfile.TemporaryDirectory() as folder:
    self.page.evaluate('''name=>{window.searchTries=0;window.fetch=()=>{
     window.searchTries++;return Promise.reject(name==='TypeError'?new TypeError('Failed to fetch'):new DOMException('signal is aborted without reason','AbortError'));
    };}''',error)
    driver=CompactOverlapBrowser(self.page,t.Config(),SimpleNamespace(navigation_timeout=3,form_refreshes=0))
    db=t.Database(Path(folder)/'checkpoint.sqlite3');qid=db.put_query('69','KA','ME')
    for r in t.parse_html_records((FIX/'live_bayburt_combined.html').read_text())[:2]:db.upsert(r,qid)
    args=SimpleNamespace(detail_concurrency=2,max_details=2,retries=1,retry_backoff=0,max_backoff=0,min_delay=0,max_delay=0,export_every=1,fail_fast=True)
    q=dict(db.db.execute('select * from queries where id=?',(qid,)).fetchone())
    with self.assertRaises(t.SessionExpired):t.process_details(driver,db,q,args,Path(folder))
    self.assertEqual({tuple(r) for r in db.db.execute('select status,failures from details')},{('pending',0)})
    self.assertEqual(self.page.evaluate('window.searchTries'),2 if error=='TypeError' else 1)
    db.db.close()
 def test_saved_missing_tbb_profile_keeps_corroboration(self):
  from test_final_audit_fixes import AuditFixTests
  html,listing=AuditFixTests().missing_tbb_fixture()
  packed=self.page.evaluate('(html)=>{'+PACK+'return pack(html,200);}',html)
  expected=t.parse_detail(html,listing);actual=t.parse_detail(packed['html'],listing)
  for field in [*t.CONTACT_FIELDS,'bar_registration_number','tbb_registration_number','_field_availability','_identity_verification']:self.assertEqual(actual.get(field),expected.get(field),field)
 def test_explicit_zero_and_identity_guards(self):
  rows,total,_=self.driver.fetch('69','ZZ','');self.assertEqual((rows,total),([],0));records=self.targets()
  with self.assertRaises(t.ExtractionError):self.driver.details([records[0],records[0]],('69','KA','ME'))
  with self.assertRaises(t.ExtractionError):self.driver.details(records,('69','WRONG',''))
  changed=dict(records[0],bar_registration_number='999999')
  with self.assertRaises(t.ListingIdentityMissing):self.driver.details([changed],('69','KA','ME'))
 def queue(self,folder):
  db=t.Database(Path(folder)/'checkpoint.sqlite3');qid=db.put_query('69','KA','ME')
  for i,r in enumerate(self.targets()):db.upsert(r,qid,1,i)
  db.finish(qid,'done');q=dict(db.db.execute('select * from queries where id=?',(qid,)).fetchone())
  args=SimpleNamespace(detail_concurrency=2,max_details=2,retries=1,retry_backoff=0,max_backoff=0,min_delay=0,max_delay=0,export_every=1,fail_fast=False,max_queries=20,max_detail_failures=3)
  return db,q,args
 def test_checkpoint_fast_sibling_survives_disconnect_then_resume(self):
  with tempfile.TemporaryDirectory() as folder:
   db,q,args=self.queue(folder);Handler.mode='slow'
   def disconnect(kind,message):
    if kind=='retained_detail_saved':self.page.close()
   self.driver.on_transport_event=disconnect
   with self.assertRaises(t.SessionExpired):t.process_details(self.driver,db,q,args,Path(folder))
   states={db.record(r['key'])['bar_registration_number']:r['status'] for r in db.db.execute('select * from details')};self.assertEqual(states,{'610002':'pending','610001':'done'});self.assertEqual(self.driver.stats['detail_post_attempts'],2)
   self.assertEqual(db.db.execute('select sum(failures) from details').fetchone()[0],0)
   db.db.close();db=t.Database(Path(folder)/'checkpoint.sqlite3');db.recover();Handler.mode='ok';self.page=self.browser.new_page();self.page.goto(self.url)
   resumed=CompactOverlapBrowser(self.page,t.Config(),SimpleNamespace(navigation_timeout=3,url=self.url,form_refreshes=0));t.process_details(resumed,db,q,args,Path(folder))
   self.assertEqual(db.db.execute("select count(*) from details where status='done'").fetchone()[0],2);self.assertEqual(Handler.calls['610001'],1);db.db.close()
 def test_checkpoint_parse_failure_retries_only_bad_sibling(self):
  with tempfile.TemporaryDirectory() as folder:
   db,q,args=self.queue(folder);Handler.mode='bad_email';t.process_details(self.driver,db,q,args,Path(folder))
   states={db.record(r['key'])['bar_registration_number']:r['status'] for r in db.db.execute('select * from details')};self.assertEqual(states,{'610002':'failed','610001':'done'});self.assertEqual(Handler.calls['610002'],2);self.assertEqual(Handler.calls['610001'],1);self.assertFalse(self.driver.needs_session_renewal);db.db.close()
 def test_checkpoint_rejected_detail_refreshes_once_only_pending_sibling(self):
  with tempfile.TemporaryDirectory() as folder:
   db,q,args=self.queue(folder);Handler.mode='detail_challenge';self.driver.refresh_limit=1
   def release(kind,message):
    if kind=='retained_form_refresh':Handler.mode='ok'
   self.driver.on_transport_event=release;t.process_details(self.driver,db,q,args,Path(folder))
   self.assertEqual(db.db.execute("select count(*) from details where status='done'").fetchone()[0],2);self.assertEqual(Handler.calls['610001'],1);self.assertEqual(Handler.calls['610002'],2);self.assertEqual(self.driver.stats['form_refreshes'],1);db.db.close()
 def test_one_hanging_request_defers_exact_identity_without_discarding_healthy_browser(self):
  with tempfile.TemporaryDirectory() as folder:
   db,q,args=self.queue(folder);self.driver.args.navigation_timeout=1
   marker=self.page.evaluate('()=>window.marker')
   self.page.evaluate('''()=>{window.realFetch=fetch.bind(window);window.fetch=(url,opts)=>{
    if(opts.body.get('detay')==='2')return new Promise((resolve,reject)=>opts.signal.addEventListener('abort',()=>reject(new DOMException('aborted','AbortError')),{once:true}));
    return window.realFetch(url,opts);
   };}''')
   t.process_details(self.driver,db,q,args,Path(folder))
   bad=db.db.execute("SELECT key,status,failures FROM details WHERE status='pending'").fetchone()
   self.assertIsNotNone(bad);self.assertEqual(bad['failures'],0)
   self.assertEqual(db.record(bad['key'])['_lookup_registration'],'610002')
   self.assertEqual(db.db.execute("SELECT count(*) FROM details WHERE status='done'").fetchone()[0],1)
   self.assertFalse(self.driver.needs_session_renewal)
   self.assertEqual(self.page.evaluate('()=>window.marker'),marker)
   self.assertIsNone(self.page.evaluate('()=>window.__tbbDetailBatch || null'))
   self.page.evaluate('()=>window.fetch=window.realFetch');self.driver.details_attempted=0
   t.process_details(self.driver,db,q,args,Path(folder))
   self.assertEqual(db.db.execute("SELECT count(*) FROM details WHERE status='done'").fetchone()[0],2)
   self.assertEqual(Handler.calls['610001'],1)
   self.assertEqual(Handler.calls['610002'],1)
   self.assertEqual(self.page.evaluate('()=>window.marker'),marker);db.db.close()
 def test_persistent_challenge_stops_refreshing_and_leaves_verification_pending(self):
  with tempfile.TemporaryDirectory() as folder:
   db,q,args=self.queue(folder);Handler.mode='detail_challenge';self.driver.refresh_limit=1
   with self.assertRaises(t.VerificationRequired):t.process_details(self.driver,db,q,args,Path(folder))
   states={db.record(r['key'])['bar_registration_number']:r['status'] for r in db.db.execute('select * from details')};self.assertEqual(states,{'610002':'verification','610001':'done'});self.assertEqual(self.driver.stats['form_refreshes'],1);self.assertEqual(Handler.calls['610002'],2);self.assertEqual(db.db.execute('select sum(failures) from details').fetchone()[0],0);db.db.close()
 def test_rejected_search_refreshes_normal_form_once(self):
  Handler.mode='expire_once';self.driver.refresh_limit=1;self.targets();self.assertEqual(Handler.searches,2);self.assertEqual(self.driver.stats['form_refreshes'],1);self.assertEqual(self.page.locator('input[name=soyad]').input_value(),'')
 def test_cli_entry_checkpoint_resume_does_not_refetch_completed_detail(self):
  import subprocess
  with tempfile.TemporaryDirectory() as folder:
   command=[sys.executable,str(ROOT/'turkey_scraper.py'),'--url',self.url,'--baro','69','--prefix','KA','--max-details','1','--max-searches','1','--output',folder,'--population-file','','--min-delay','0','--max-delay','0','--max-runtime','20','--navigation-timeout','3','--auto-verification-timeout','1','--session-restarts','0','--access-retries','0','--retries','0']
   env={k:v for k,v in os.environ.items() if k not in ('TBB_CDP_ENDPOINT','TBB_CONNECTION_FILE','TBB_SOLVER_FILE','CAPSOLVER_API_KEY')}
   first=subprocess.run(command,capture_output=True,text=True,env=env,timeout=30);self.assertEqual(first.returncode,2,first.stderr)
   second=subprocess.run(command+['--resume-details-only'],capture_output=True,text=True,env=env,timeout=30);self.assertEqual(second.returncode,2,second.stderr)
   db=t.Database(Path(folder)/'checkpoint.sqlite3');self.assertEqual(db.db.execute("select count(*) from details where status='done'").fetchone()[0],2);self.assertEqual(Handler.calls,{'610001':1,'610002':1});self.assertEqual(db.metadata('transport_mode'),'retained');self.assertEqual(db.metadata('transport_statistics')['detail_post_attempts'],2);db.db.close()
 def test_cli_exact_roster_lookup_uses_real_entrypoint_and_stores_pending_details(self):
  import subprocess
  from roster_reconciliation import reconcile
  with tempfile.TemporaryDirectory() as folder:
   db=t.Database(Path(folder)/'checkpoint.sqlite3');db.db.execute("INSERT INTO bars VALUES('69','BAYBURT',1)");db.db.commit()
   ref=next(r for r in t.parse_html_records((FIX/'live_bayburt_combined.html').read_text(),self.url) if r['bar_registration_number']=='610002')
   reconcile(db,{'source':'https://official.example/roster','date':'2026-10-21','rows':[{'regNumber':'610002','firstName':ref['first_name'],'lastName':ref['last_name']}]},'69');db.db.close()
   command=[sys.executable,str(ROOT/'turkey_scraper.py'),'--url',self.url,'--baro','69','--prefix','ZZ','--max-roster-lookups','1','--no-details','--max-searches','1','--output',folder,'--population-file','','--min-delay','0','--max-delay','0','--max-runtime','20','--navigation-timeout','3','--auto-verification-timeout','1','--session-restarts','0','--access-retries','0','--retries','0']
   env={k:v for k,v in os.environ.items() if k not in ('TBB_CDP_ENDPOINT','TBB_CONNECTION_FILE','TBB_SOLVER_FILE','CAPSOLVER_API_KEY')}
   result=subprocess.run(command,capture_output=True,text=True,env=env,timeout=30);self.assertEqual(result.returncode,2,result.stderr)
   self.assertEqual(sum(x.get('barosicil')==['610002'] for x in Handler.fields),1)
   db=t.Database(Path(folder)/'checkpoint.sqlite3');self.assertEqual(db.record(t.record_key({**ref,'bar_association_id':'69'}))['_lookup_registration'],'610002');self.assertEqual(db.db.execute("SELECT count(*) FROM details WHERE status='done'").fetchone()[0],0);db.db.close()
 def test_complete_known_checkpoint_opens_no_browser_and_new_seed_is_not_skipped(self):
  from unittest.mock import patch
  with tempfile.TemporaryDirectory() as folder:
   db=t.Database(Path(folder)/'checkpoint.sqlite3');db.db.execute("insert into bars values('69','BAYBURT',1)");qid=db.put_query('69','KA');db.finish(qid,'done');db.db.close()
   args=['--baro','69','--prefix','KA','--output',folder,'--population-file','','--max-runtime','20']
   with patch('playwright.sync_api.sync_playwright',side_effect=AssertionError('Paid browser should not open')):
    self.assertEqual(t.cli(args),0)
   db=t.Database(Path(folder)/'checkpoint.sqlite3');self.assertEqual(db.metadata('run_status'),'queue_finished')
   check=SimpleNamespace(inspect=False,list_baros=False,all_baros=False,baro=['69'],prefix=['ZZ'],alphabet=t.ALPHABET,primary_field='surname',no_details=False,output=folder)
   self.assertIsNone(t.cached_work_status(db,check));db.db.close()
if __name__=='__main__':unittest.main()
