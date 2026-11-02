import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from turkey_scraper import (ALPHABET, Database, ExtractionError, VerificationRequired,
    canonical_field, count_hint, merge_record, parse_html_records, parse_detail,
    partition, prefix_pairs, record_key, turkish_upper, retry)

FIX = Path(__file__).parent / 'fixtures'

class LogicTests(unittest.TestCase):
    def test_turkish_unicode_casing(self):
        self.assertEqual(turkish_upper('izmir ışık'), 'İZMİR IŞIK')
        self.assertEqual(turkish_upper('I\u0307S'), 'İS')
        self.assertEqual(len(ALPHABET), 32)
        self.assertEqual(len(prefix_pairs()), 1024)

    def test_live_table_parser(self):
        rows = parse_html_records((FIX/'live_bayburt_combined.html').read_text())
        self.assertEqual(len(rows),5)
        self.assertEqual(rows[-1]['last_name'],'UÇKANTEST')
        self.assertEqual(rows[1]['first_name'],'METİN DENEME')
        self.assertEqual(rows[1]['bar_registration_number'],'610002')
        self.assertEqual(rows[1]['_detail_index'],'2')
        self.assertEqual(rows[1]['profile_url'],'')

    def test_live_detail_contact_and_missing(self):
        row=parse_html_records((FIX/'live_bayburt_combined.html').read_text())[1]
        detail=parse_detail((FIX/'live_bayburt_detail.html').read_text(),row)
        self.assertEqual(detail['tbb_registration_number'],'990002')
        self.assertEqual(detail['phone'],'0(500) 000 0000')
        self.assertIn('BAYBURT',detail['address'])
        self.assertEqual(detail['_field_availability']['email'],'blank_on_site')
        self.assertEqual(detail['_field_availability']['website'],'not_displayed_on_detail')
        self.assertEqual(detail['professional_status'],'AVUKAT')

    def test_live_blank_contacts_are_not_failure(self):
        row={'bar_registration_number':'610006','full_name':'ANKARA TEST KİŞİ'}
        d=parse_detail((FIX/'live_ankara_blank_detail.html').read_text(),row)
        self.assertEqual(d['detail_status'],'done')
        self.assertEqual(d['email'],'')
        self.assertEqual(d['_field_availability']['address'],'blank_on_site')

    def test_detail_status_ignores_search_buttons(self):
        html=(FIX/'live_bayburt_detail.html').read_text().replace('</form>',
            '<button>STAJYER AVUKAT</button></form>')
        self.assertEqual(parse_detail(html)['professional_status'],'AVUKAT')
        html=html.replace('<h3>AVUKAT</h3>','')
        self.assertEqual(parse_detail(html)['professional_status'],'')

    def test_separator_only_address_is_blank(self):
        html=(FIX/'live_ankara_blank_detail.html').read_text()
        html=html.replace('<strong>Adres</strong>', '<strong>Adres</strong>')
        from bs4 import BeautifulSoup
        soup=BeautifulSoup(html,'html.parser')
        for tr in soup.select('tr'):
            if 'Adres' in tr.get_text():
                tr.select('td')[-1].string=' / '
        detail=parse_detail(str(soup))
        self.assertEqual(detail['address'],'')
        self.assertEqual(detail['_field_availability']['address'],'blank_on_site')

    def test_mismatched_detail_is_rejected(self):
        with self.assertRaises(ExtractionError):
            parse_detail((FIX/'live_bayburt_detail.html').read_text(),{'bar_registration_number':'999'})
        with self.assertRaises(ExtractionError):
            parse_detail('<h1>Cloudflare</h1>')

    def test_counts_and_noise(self):
        self.assertEqual(count_hint('1000 kayıt listelendi.'),1000)
        self.assertEqual(count_hint('Toplam 1.000 sonuç bulundu'),1000)
        self.assertIsNone(count_hint('2026 +90 312 292 59 00'))
        self.assertEqual(parse_html_records('<footer>Avukat Türkiye</footer>'),[])

    def test_official_identity_not_name(self):
        a={'bar_association_id':'6','bar_registration_number':'1','full_name':'AYŞE YILMAZ'}
        b={**a,'bar_registration_number':'2'}
        self.assertNotEqual(record_key(a),record_key(b))
        self.assertNotEqual(record_key(a),record_key({**a,'bar_association_id':'620'}))
        noid={'full_name':'AYŞE YILMAZ','address':'same'}
        self.assertNotEqual(record_key(noid),record_key(noid))

    def test_merge_provenance_conflicts_and_nonempty(self):
        a={'email':'a@example.org','full_name':'A','_origins':['q1']}
        b={'email':'','full_name':'B','_origins':['q2']}
        merged=merge_record(a,b)
        self.assertEqual(merged['email'],'a@example.org')
        self.assertEqual(merged['_origins'],['q1','q2'])
        self.assertEqual(merged['_conflicts']['full_name'],['A','B'])

    def test_substring_cross_field_cover(self):
        children,gap=partition('KA','')
        self.assertEqual(len(children),1088)
        self.assertIn(('KA','ME'),children)
        self.assertIn('exact-length',gap)
        children,gap=partition('KA','ME')
        self.assertIn(('KA','AME'),children)
        self.assertIn(('KA','MEA'),children)
        self.assertIn('exact-length',gap)
        self.assertEqual(partition('KARAR','MEHME')[0],[])

    def test_partition_does_not_drop_short_or_foreign_given_names(self):
        children, _ = partition('KA', '')
        for surname, name in [('KARA', 'A'), ('AKAR', 'Q'), ('KAYA', 'X')]:
            self.assertTrue(any(s in surname and n in name for s, n in children))
        children, _ = partition('KA', 'ME')
        self.assertTrue(any(s in 'KARA' and n in 'ME' for s, n in children))
        self.assertTrue(any(s in 'KA' and n in 'AHMET' for s, n in children))
        children, _ = partition('KARAR', 'ME')
        self.assertIn(('KARAR', 'AME'), children)

    def test_checkpoint_recovery_dedup_and_reports(self):
        with tempfile.TemporaryDirectory() as td:
            db=Database(Path(td)/'checkpoint.sqlite3')
            db.db.execute('INSERT INTO bars VALUES(?,?,?)',('69','BAYBURT',1))
            qid=db.put_query('69','KA','ME')
            q=db.take_query()
            self.assertEqual(q['id'],qid)
            db.recover()
            self.assertEqual(db.take_query()['id'],qid)
            row=parse_html_records((FIX/'live_bayburt_combined.html').read_text())[1]
            row['bar_association_id']='69'
            key=db.upsert(row,qid,1,0)
            db.upsert(row,qid,1,0) # interrupted query replay
            db.upsert(parse_detail((FIX/'live_bayburt_detail.html').read_text(),row))
            db.detail_state(key,'done')
            db.finish(qid,'done',seen=1,total_hint=1,pages=1)
            report=db.export(Path(td))
            self.assertEqual(report['unique_lawyers'],1)
            self.assertEqual(report['completeness']['national']['fields']['phone']['percent'],100)
            self.assertEqual(report['bars_queue_processed'],1)
            self.assertEqual(report['details'],{'done':1})
            db.db.close()

    def test_cap_cannot_be_claimed_resolved_with_pending_children(self):
        with tempfile.TemporaryDirectory() as td:
            db=Database(Path(td)/'cp.sqlite3')
            parent=db.put_query('6','KA')
            child=db.put_query('6','KA','ME',parent)
            db.finish(parent,'split',capped=1)
            report=db.export(Path(td))
            self.assertEqual(report['capped_queries_with_completed_child_queues'],0)
            db.finish(child,'done')
            self.assertEqual(db.export(Path(td))['capped_queries_with_completed_child_queues'],1)
            self.assertEqual(db.export(Path(td))['capped_queries_proven_exhaustive'],0)
            db.db.close()

    def test_retry_is_bounded_and_verification_is_not_retried(self):
        args=SimpleNamespace(retries=2,retry_backoff=0,max_backoff=0)
        calls=[]
        def fail():
            calls.append(1)
            raise ValueError('network')
        with self.assertRaises(ValueError): retry(fail,args)
        self.assertEqual(len(calls),3)
        calls.clear()
        def challenge():
            calls.append(1)
            raise VerificationRequired('manual verification')
        with self.assertRaises(VerificationRequired): retry(challenge,args)
        self.assertEqual(len(calls),1)

    def test_query_budget(self):
        with tempfile.TemporaryDirectory() as td:
            db=Database(Path(td)/'cp.sqlite3')
            db.put_query('6','KA',budget=1)
            with self.assertRaises(ExtractionError): db.put_query('6','ME',budget=1)
            db.db.close()

if __name__=='__main__': unittest.main()

class HtmlLocator:
    def __init__(self,root,selector): self.root,self.selector=root,selector
    @property
    def first(self): return self
    def nodes(self): return self.root.select(self.selector)
    def count(self): return len(self.nodes())
    def inner_text(self,**kwargs): return self.nodes()[0].get_text(' ',strip=True)
    def inner_html(self): return ''.join(str(x) for x in self.nodes()[0].contents)
    def all_text_contents(self): return [x.get_text(' ',strip=True) for x in self.nodes()]
    def input_value(self): return self.nodes()[0].get('value','')
    def locator(self,selector): return HtmlLocator(self.nodes()[0],selector)
    def wait_for(self,**kwargs):
        if not self.count(): raise ExtractionError('Missing expected DOM element')
class HtmlPage:
    def __init__(self,html):
        from bs4 import BeautifulSoup
        self.soup=BeautifulSoup('<body>'+html+'</body>','html.parser');self.url='https://www.barobirlik.org.tr/AvukatArama'
    def locator(self,selector): return HtmlLocator(self.soup,selector)
    def content(self): return str(self.soup)
    def wait_for_timeout(self,ms): pass
class BrowserGuardTests(unittest.TestCase):
    def driver(self,html):
        from turkey_scraper import Config,DirectoryBrowser
        args=SimpleNamespace(headless=True,unattended=True,auto_verification_timeout=0,navigation_timeout=1,captcha_timeout=1)
        return DirectoryBrowser(HtmlPage(html),Config(),args)
    def test_real_result_shape_through_browser_adapter(self):
        rows,total,pages=self.driver((FIX/'live_bayburt_combined.html').read_text()).result()
        self.assertEqual((len(rows),total,pages),(5,5,1))
    def test_cloudflare_is_access_block_not_zero_lawyers(self):
        driver=self.driver('<h1>Just a moment</h1><p>Cloudflare</p>')
        self.assertTrue(driver.challenge_required())
        with self.assertRaises(VerificationRequired): driver.result()
    def test_widget_expiry_is_detected(self):
        html='<form id="avForm"><input name="ad"><div class="cf-turnstile"><input name="cf-turnstile-response" value=""></div></form>'
        self.assertTrue(self.driver(html).challenge_required())
        self.assertFalse(self.driver(html.replace('value=""','value="fixture"')).challenge_required())
    def test_count_mismatch_is_extraction_failure(self):
        html=(FIX/'live_bayburt_combined.html').read_text().replace('5 kayıt','6 kayıt')
        with self.assertRaises(ExtractionError):self.driver(html).result()
    def test_validation_error_is_not_empty(self):
        html='<form id="avForm"><div class="alert-danger">Geçersiz bir arama kriteri girdiniz.</div></form>'
        with self.assertRaises(ExtractionError):self.driver(html).result()
    def test_zero_and_unexpected_pagination(self):
        self.assertEqual(self.driver('<form id="avForm"><h3>0 kayıt listelendi.</h3></form>').result()[0],[])
        html=(FIX/'live_bayburt_combined.html').read_text()+'<div class="pagination"></div>'
        with self.assertRaises(ExtractionError):self.driver(html).result()
    def test_refresh_cannot_downgrade_completed_detail(self):
        merged=merge_record({'detail_status':'done','email':'a@test.org'}, {'detail_status':'pending','email':''})
        self.assertEqual(merged['detail_status'],'done')
        self.assertEqual(merged['email'],'a@test.org')

class HostedNavigationRegressionTests(unittest.TestCase):
    def test_old_result_document_is_not_new_post_result(self):
        from unittest.mock import Mock
        driver=BrowserGuardTests().driver((FIX/'live_bayburt_combined.html').read_text())
        driver._submitted_document='old-document'
        driver.page.evaluate=Mock(side_effect=['old-document',None])
        driver.wait_for_turnstile=Mock()
        driver.page.wait_for_timeout=Mock()
        driver.wait_for_view('results')
        self.assertEqual(driver.page.evaluate.call_count,2)
        driver.wait_for_turnstile.assert_called_once()
    def test_view_poll_survives_document_replacement_after_post(self):
        from unittest.mock import Mock
        driver=BrowserGuardTests().driver((FIX/'live_bayburt_combined.html').read_text())
        driver.args.navigation_timeout=2
        driver.wait_for_turnstile=Mock(side_effect=[RuntimeError('Execution context was destroyed, most likely because of a navigation'),None])
        driver.page.wait_for_timeout=Mock()
        driver.wait_for_view('results')
        self.assertEqual(driver.wait_for_turnstile.call_count,2)

    def test_ready_dom_does_not_wait_for_provider_navigation(self):
        from unittest.mock import patch
        driver=BrowserGuardTests().driver((FIX/'live_bayburt_combined.html').read_text())
        with patch.object(HtmlLocator,'wait_for',side_effect=TimeoutError('provider navigation pending')):
            rows,total,pages=driver.result()
        self.assertEqual((len(rows),total,pages),(5,5,1))

class DetailDurabilityRegressionTests(unittest.TestCase):
    def test_expiry_promoted_by_retry_stays_pending_for_reconnect(self):
        from unittest.mock import Mock
        from turkey_scraper import process_details, SessionExpired
        with tempfile.TemporaryDirectory() as td:
            db=Database(Path(td)/'cp.sqlite3')
            qid=db.put_query('69','KA')
            row=parse_html_records((FIX/'live_bayburt_combined.html').read_text())[0]
            db.upsert(row,qid,1,0)
            q=dict(db.db.execute('select * from queries where id=?',(qid,)).fetchone())
            driver=Mock();driver.details_attempted=0
            driver.detail.side_effect=RuntimeError('Target page, context or browser has been closed')
            args=SimpleNamespace(max_details=2,retries=1,retry_backoff=0,max_backoff=0)
            with self.assertRaises(SessionExpired):
                process_details(driver,db,q,args,Path(td))
            self.assertEqual(db.db.execute('select status from details').fetchone()[0],'pending')
            self.assertEqual(driver.detail.call_count,1)
            db.db.close()
    def popup_driver(self):
        from unittest.mock import Mock, MagicMock
        driver=BrowserGuardTests().driver((FIX/'live_bayburt_combined.html').read_text())
        rows=parse_html_records((FIX/'live_bayburt_combined.html').read_text())
        query=('69','KA','ME')
        driver.last_query=query;driver.last_result=rows
        listing=Mock();listing.evaluate.return_value=None
        listing.locator.return_value.count.return_value=5
        popup=Mock();popup.evaluate.return_value=True
        popup.content.return_value=(FIX/'live_bayburt_detail.html').read_text()
        opened=MagicMock();opened.__enter__.return_value.value=popup
        listing.expect_popup.return_value=opened
        driver.page=listing;driver.click_control=Mock();driver.wait_for_view=Mock()
        return driver,rows,query,listing,popup
    def test_saved_detail_survives_popup_close_failure(self):
        driver,rows,query,listing,popup=self.popup_driver()
        popup.close.side_effect=RuntimeError('session expired')
        saved=[];driver.on_detail_extracted=saved.append
        result=driver.detail(rows[1],query)
        self.assertEqual(result['tbb_registration_number'],'990002')
        self.assertEqual(len(saved),1)
        self.assertIs(driver.page,listing)
        self.assertEqual(driver.last_query,query)
        listing.go_back.assert_not_called()
        driver.fetch=__import__('unittest.mock',fromlist=['Mock']).Mock()
        driver.detail(rows[1],query)
        driver.fetch.assert_not_called()
    def test_wrong_detail_closes_popup_without_saving(self):
        driver,rows,query,listing,popup=self.popup_driver()
        saved=[];driver.on_detail_extracted=saved.append
        with self.assertRaises(ExtractionError):driver.detail(rows[0],query)
        self.assertEqual(saved,[])
        popup.close.assert_called_once()
        self.assertIs(driver.page,listing)
        self.assertEqual(listing.evaluate.call_count,2)

class SessionRecoveryTests(unittest.TestCase):
    def test_hosted_ttl_uses_documented_minute_format(self):
        from unittest.mock import patch
        from urllib.parse import urlparse,parse_qs
        import turkey_scraper
        with tempfile.TemporaryDirectory() as td:
            seen=[]
            def fake_run(args):
                seen.append(parse_qs(urlparse(args.cdp_endpoint).query)['session_ttl'])
                db=Database(Path(td)/'checkpoint.sqlite3')
                db.metadata('run_status','queue_finished');db.db.close()
                return 0
            with patch.object(turkey_scraper,'run',side_effect=fake_run):
                result=turkey_scraper.cli(['--baro','BAYBURT','--cdp-endpoint','wss://browser.zenrows.com?apikey=dummy',
                    '--session-ttl','900','--output',td])
            self.assertEqual(result,0)
            self.assertEqual(seen,[['15m']])

    def test_closed_browser_is_distinct_from_empty_or_parser_error(self):
        from turkey_scraper import session_was_closed
        self.assertTrue(session_was_closed(RuntimeError('Target page, context or browser has been closed')))
        self.assertFalse(session_was_closed(ExtractionError('Result count not found')))

    def test_reconnect_keeps_remaining_query_and_detail_budgets(self):
        from unittest.mock import patch
        import turkey_scraper
        with tempfile.TemporaryDirectory() as td:
            seen=[]
            def fake_run(args):
                seen.append((args.max_searches,args.max_details))
                db=Database(Path(td)/'checkpoint.sqlite3')
                if len(seen)==1:
                    q=db.put_query('69','KA')
                    db.db.execute("UPDATE queries SET attempts=1,status='done' WHERE id=?",(q,))
                    db.db.execute("INSERT INTO details(key,query_id,status,attempts) VALUES('one',?,'done',1)",(q,))
                    db.db.execute("INSERT INTO details(key,query_id,status,attempts) VALUES('two',?,'pending',0)",(q,))
                    db.db.commit();db.metadata('run_status','session_expired')
                    result=2
                else:
                    db.db.execute("UPDATE details SET status='done',attempts=1 WHERE key='two'")
                    db.db.commit();db.metadata('run_status','queue_finished');result=0
                db.db.close();return result
            with patch.object(turkey_scraper,'run',side_effect=fake_run):
                result=turkey_scraper.cli(['--baro','BAYBURT','--max-searches','1','--max-details','2',
                    '--session-restarts','1','--access-retries','0','--output',td])
            self.assertEqual(result,0)
            self.assertEqual(seen,[(1,2),(0,1)])
