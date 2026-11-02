"""Real Playwright with a local POST server using synthetic DOM fixtures.
Enable with TBB_TEST_BROWSER=1; this is not a live TBB run.
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
from threading import Thread
from types import SimpleNamespace
from urllib.parse import parse_qs
import unittest
from turkey_scraper import Config, DirectoryBrowser, ExtractionError
FIX=Path(__file__).parent/'fixtures'
FORM='''<form id="avForm" method="post"><input name="ad" placeholder="Adı"><input name="soyad" placeholder="Soyadı"><input name="barosicil"><select name="baroId"><option value="0">Tüm Barolarda Ara</option><option value="69">BAYBURT</option></select><button name="tip" value="Avukat" type="submit">AVUKAT ARA</button></form>'''
class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def send(self,body):
        data=body.encode();self.send_response(200)
        self.send_header('Content-Type','text/html; charset=utf-8')
        self.send_header('Content-Length',str(len(data)))
        self.end_headers();self.wfile.write(data)
    def do_GET(self): self.send(FORM)
    def do_POST(self):
        fields=parse_qs(self.rfile.read(int(self.headers['Content-Length'])).decode())
        if fields.get('detay')==['2']: self.send((FIX/'live_bayburt_detail.html').read_text())
        elif 'detay' in fields: self.send('<form id="avForm">bad detail</form>')
        elif fields.get('soyad')==['ZZ']: self.send('<form id="avForm"><h3>0 kayıt listelendi.</h3><table><thead><tr><th>BARO</th><th>BARO SİCİL</th><th>AD</th><th>SOYAD</th></tr></thead><tbody></tbody></table></form>')
        else: self.send((FIX/'live_bayburt_combined.html').read_text())
@unittest.skipUnless(os.getenv('TBB_TEST_BROWSER')=='1','Enable with TBB_TEST_BROWSER=1')
class BrowserIntegrationTests(unittest.TestCase):
    def test_post_search_detail_back_and_zero(self):
        from playwright.sync_api import sync_playwright
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            with sync_playwright() as pw:
                browser=pw.chromium.launch(headless=True)
                try:
                    page=browser.new_page();url=f'http://127.0.0.1:{server.server_port}/';page.goto(url)
                    args=SimpleNamespace(headless=True,captcha_timeout=2,navigation_timeout=5,url=url)
                    driver=DirectoryBrowser(page,Config(),args)
                    self.assertEqual(driver.baro_options()[1]['value'],'69')
                    rows,total,pages=driver.fetch('69','KA','ME')
                    self.assertEqual((len(rows),total,pages),(5,5,1))
                    document_id=page.evaluate('() => window.testDocumentId = Math.random()')
                    updated=driver.detail(rows[1],('69','KA','ME'))
                    self.assertEqual(updated['tbb_registration_number'],'990002')
                    self.assertEqual(updated['detail_status'],'done')
                    self.assertEqual(page.evaluate('() => window.testDocumentId'),document_id)
                    self.assertEqual(len(page.context.pages),1)
                    self.assertIsNone(page.locator('button[name=detay][value="2"]').get_attribute('formtarget'))
                    driver.detail(rows[1],('69','KA','ME'))
                    self.assertEqual(len(page.context.pages),1)
                    with self.assertRaises(ExtractionError):driver.detail(rows[0],('69','KA','ME'))
                    self.assertEqual(len(page.context.pages),1)
                    self.assertEqual(page.evaluate('() => window.testDocumentId'),document_id)
                    self.assertEqual(page.locator('button[name="detay"]').count(),5)
                    rows,total,pages=driver.fetch('69','ZZ','')
                    self.assertEqual((rows,total),([],0))
                    with self.assertRaises(ExtractionError): driver.fetch('69','XY','')
                finally: browser.close()
        finally: server.shutdown();server.server_close();thread.join()
if __name__=='__main__':unittest.main()
