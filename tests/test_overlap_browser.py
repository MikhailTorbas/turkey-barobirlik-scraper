import unittest,time,os,tempfile
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from threading import Thread,Lock
from urllib.parse import parse_qs
from pathlib import Path
from types import SimpleNamespace
from bs4 import BeautifulSoup
import sys
PROJECT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROJECT))
import turkey_scraper as t
FIX=PROJECT/'tests/fixtures'
CONTROLS='<input name="ad"><input name="soyad"><input name="barosicil"><select name="baroId"><option value="0">All</option><option value="69">BAYBURT</option></select><button name="tip" value="Avukat" type="submit">Search</button>'
def local_listing():
 soup=BeautifulSoup((FIX/'live_bayburt_combined.html').read_text(),'html.parser');form=soup.select_one('form');form['action']='/'
 for child in reversed(list(BeautifulSoup(CONTROLS,'html.parser').contents)):form.insert(0,child)
 return str(soup)
class Handler(BaseHTTPRequestHandler):
 lock=Lock();active=0;max_active=0;searches=[]
 def log_message(self,*args):pass
 def send(self,data):
  raw=data.encode();self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
 def do_GET(self):self.send(local_listing())
 def do_POST(self):
  fields=parse_qs(self.rfile.read(int(self.headers['Content-Length'])).decode())
  if 'detay' not in fields:
   Handler.searches.append(fields.get('soyad',[''])[0]);self.send(local_listing());return
  index=int(fields['detay'][0]);reg=['610001','610002','610003','610004','610005'][index-1]
  with Handler.lock:Handler.active+=1;Handler.max_active=max(Handler.max_active,Handler.active)
  time.sleep(.5 if index==1 else .1)
  soup=BeautifulSoup((FIX/'live_bayburt_detail.html').read_text(),'html.parser')
  for row in soup.select('tr'):
   cells=row.select(':scope > td')
   if cells and t.canonical_field(cells[0].get_text())=='bar_registration_number':cells[-1].string=reg
  try:self.send(str(soup))
  finally:
   with Handler.lock:Handler.active-=1
@unittest.skipUnless(os.getenv('TBB_TEST_BROWSER')=='1','Enable with TBB_TEST_BROWSER=1')
class ProductionOverlapTests(unittest.TestCase):
 def test_overlapping_native_posts_match_out_of_order_and_close_tabs(self):
  from playwright.sync_api import sync_playwright
  server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=Thread(target=server.serve_forever,daemon=True);thread.start()
  try:
   with sync_playwright() as pw:
    browser=pw.chromium.launch(headless=True)
    try:
     page=browser.new_page();page.goto(f'http://127.0.0.1:{server.server_port}/')
     # Fixture retains the real site's action; point the local test at its POST handler.
     page.evaluate("()=>document.querySelector('form').action='/'")
     rows=t.parse_html_records(page.content());args=SimpleNamespace(headless=True,unattended=True,navigation_timeout=3,auto_verification_timeout=1)
     driver=t.DirectoryBrowser(page,t.Config(),args);driver.last_result=rows;driver.last_query=('69','KA','ME')
     token=page.evaluate('()=>window.testToken=Math.random()')
     seen=[];driver.on_detail_extracted=lambda row:seen.append(row['bar_registration_number'])
     try:found=[(r,0) for r in driver.details(rows[:2],('69','KA','ME'))]
     except Exception as error:raise RuntimeError(f'{error}; server max concurrent={Handler.max_active}') from error
     self.assertEqual([r['bar_registration_number'] for r,_ in found],['610001','610002'])
     self.assertEqual(len(found),2)
     self.assertEqual(Handler.max_active,2)
     self.assertEqual(seen,['610002','610001'])
     self.assertEqual(len(page.context.pages),1)
     self.assertEqual(page.evaluate('()=>window.testToken'),token)
     self.assertIs(driver.page,page)
     self.assertEqual(page.locator('[formtarget]').count(),0)
    finally:browser.close()
  finally:server.shutdown();server.server_close();thread.join()
 def check_cli(self,extra=(),expected=2):
  Handler.searches=[]
  server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=Thread(target=server.serve_forever,daemon=True);thread.start()
  try:
   with tempfile.TemporaryDirectory() as folder:
    db=t.Database(Path(folder)/'checkpoint.sqlite3');qid=db.put_query('69','KA','ME')
    record=t.parse_html_records(local_listing())[0];record['bar_association_id']='69';db.upsert(record,qid,1,0)
    db.finish(qid,'done',seen=1,total_hint=1,pages=1,capped=0);db.db.close()
    code=t.cli(['--url',f'http://127.0.0.1:{server.server_port}/','--baro','69','--prefix','ZZ','--prefix','XX','--max-details','1','--max-searches','2','--detail-concurrency','2','--output',folder,'--population-file','','--min-delay','0','--max-delay','0','--max-runtime','20','--navigation-timeout','3','--retries','0']+list(extra))
    self.assertEqual(code,expected) # Deferred discovery stays queued in both modes.
    self.assertEqual(Handler.searches,['KA'])
    db=t.Database(Path(folder)/'checkpoint.sqlite3')
    self.assertEqual(db.db.execute("select count(*) from queries where status='pending'").fetchone()[0],0 if '--resume-details-only' in extra else 2)
    self.assertEqual(db.db.execute("select count(*) from details where status='done'").fetchone()[0],1);db.db.close()
  finally:server.shutdown();server.server_close();thread.join()
 def test_budget_defers_unrequested_discovery_in_real_cli(self):self.check_cli()
 def test_resume_only_finishes_saved_jobs_without_discovery(self):self.check_cli(['--resume-details-only','--max-details','5'],0)
if __name__=='__main__':unittest.main()
