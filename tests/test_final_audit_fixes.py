import json
from pathlib import Path
import sqlite3
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from bs4 import BeautifulSoup
import turkey_scraper as t

FIX = Path(__file__).parent / 'fixtures'


class AuditFixTests(unittest.TestCase):
    def test_listing_rediscovery_preserves_detail_blank_and_evidence(self):
        old={'bar_association_id':'69','bar_registration_number':'610002','detail_status':'done',
             'email':'','_field_availability':{'email':'blank_on_site'},
             '_detail_field_evidence':{'observed_at':'earlier','states':{'email':'blank_on_site'}}}
        new={'detail_status':'pending','_field_availability':{'email':'not_in_listing'}}
        merged=t.merge_record(old,new)
        self.assertEqual(merged['_field_availability']['email'],'blank_on_site')
        self.assertEqual(merged['detail_status'],'done')
        self.assertEqual(merged['_detail_field_evidence'],old['_detail_field_evidence'])
        newer=t.merge_record(merged,{'email':'new@example.test','detail_status':'done',
                                    '_field_availability':{'email':'present'}})
        self.assertEqual(newer['_field_availability']['email'],'present')

    def test_email_fill_report_excludes_unchecked_profiles(self):
        with tempfile.TemporaryDirectory() as td:
            db=t.Database(Path(td)/'checkpoint.sqlite3')
            for reg,status,email,state in [('1','done','a@example.test','present'),
                                           ('2','done','','unknown_after_listing_merge'),
                                           ('3','pending','','not_in_listing')]:
                db.upsert({'bar_association_id':'69','bar_registration_number':reg,
                           'detail_status':status,'email':email,'_field_availability':{'email':state}})
            report=db.export(td)['completed_profile_email_summary']
            self.assertEqual(report['completed_profiles'],2)
            self.assertEqual(report['fill_percent'],50)
            self.assertEqual(report['empty_email_availability'],{'unknown_after_listing_merge':1})
            db.db.close()

    def missing_tbb_fixture(self):
        html=BeautifulSoup((FIX/'live_bayburt_detail.html').read_text(),'html.parser')
        for row in html.select('tr'):
            cells=row.select(':scope > td')
            if cells and t.canonical_field(cells[0].get_text())=='tbb_registration_number':
                cells[-1].clear()
        form=html.select_one('#avForm')
        for h in form.select('h2,p'):h.decompose()
        heading=BeautifulSoup('<h1>METİN DENEME KAYA<br><small>Bayburt Barosu</small></h1>','html.parser')
        form.insert(0,heading)
        listing=t.parse_html_records((FIX/'live_bayburt_combined.html').read_text())[1]
        return str(html),listing

    def test_missing_tbb_requires_matching_official_bar_number_name_and_bar(self):
        html,listing=self.missing_tbb_fixture()
        record=t.parse_detail(html,listing)
        self.assertEqual(record['detail_status'],'done')
        self.assertEqual(record['bar_registration_number'],'610002')
        self.assertFalse(record.get('tbb_registration_number'))
        self.assertTrue(record['_identity_verification']['tbb_blank_on_site'])
        self.assertEqual(record['_detail_field_evidence']['states']['email'],'blank_on_site')
        for field,bad in [('full_name','OTHER LAWYER'),('bar_association','Bursa Barosu'),('bar_registration_number','99')]:
            with self.subTest(field=field),self.assertRaises(t.ExtractionError):
                t.parse_detail(html,{**listing,field:bad})
        with self.assertRaises(t.ExtractionError):t.parse_detail(html)

    def test_persistent_failure_limit_survives_retry_failed_and_database_restart(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'checkpoint.sqlite3'
            for i in range(3):
                db=t.Database(path);qid=db.put_query('69','KA')
                key=db.upsert({'bar_association_id':'69','bar_registration_number':'1',
                               '_detail_index':'1','detail_status':'pending'},qid)
                db.detail_state(key,'running')
                state=db.detail_state(key,'failed','Missing identifier')
                self.assertEqual(state,'needs_review' if i==2 else 'failed')
                db.recover(retry_failed=True)
                if i==2:
                    self.assertEqual(db.detail_jobs(qid),[])
                    self.assertEqual(db.db.execute('select failures from details').fetchone()[0],3)
                    db.detail_state(key,'verification','challenge')
                    self.assertEqual(db.db.execute('select failures from details').fetchone()[0],3)
                    db.detail_state(key,'needs_review','review')
                    db.recover(retry_review=True)
                    self.assertEqual(len(db.detail_jobs(qid)),1)
                    self.assertEqual(db.db.execute('select failures from details').fetchone()[0],0)
                    self.assertEqual(db.db.execute("select count(*) from events where kind='review_retries_authorized'").fetchone()[0],1)
                db.db.close()

    def test_missing_identity_moves_to_narrower_search_without_assuming_identity(self):
        with tempfile.TemporaryDirectory() as td:
            db=t.Database(Path(td)/'checkpoint.sqlite3');qid=db.put_query('34','KA')
            key=db.upsert({'bar_association_id':'34','bar_registration_number':'610007',
                           'first_name':'METİN DENEME','last_name':'KAYA DENEME',
                           'detail_status':'pending','_detail_index':'7'},qid)
            t.redirect_missing_detail(db,key,('34','KA',''))
            job=db.db.execute('select * from details where key=?',(key,)).fetchone()
            query=db.db.execute('select * from queries where id=?',(job['query_id'],)).fetchone()
            self.assertEqual((query['baro'],query['surname'],query['name']),('34','KAYA DENEME','METİN DENEME'))
            self.assertEqual(job['status'],'pending');self.assertEqual(job['failures'],0)
            self.assertNotEqual(job['query_id'],qid)
            t.redirect_missing_detail(db,key,('34','KAYA DENEME','METİN DENEME'))
            self.assertEqual(db.db.execute('select status from details where key=?',(key,)).fetchone()[0],'pending')
            self.assertEqual(db.record(key)['_lookup_registration'],'610007')
            t.redirect_missing_detail(db,key,('34','','','610007'))
            self.assertEqual(db.db.execute('select status from details where key=?',(key,)).fetchone()[0],'needs_review')
            db.db.close()

    def test_stale_listing_is_not_retried_in_the_same_document(self):
        args=SimpleNamespace(retries=3,retry_backoff=0,max_backoff=0)
        operation=Mock(side_effect=t.ListingIdentityMissing(['1']))
        with self.assertRaises(t.ListingIdentityMissing):t.retry(operation,args)
        self.assertEqual(operation.call_count,1)

    def test_missing_identity_does_not_fail_its_valid_sibling(self):
        with tempfile.TemporaryDirectory() as td:
            db=t.Database(Path(td)/'checkpoint.sqlite3');qid=db.put_query('69','KA')
            records=[{'bar_association_id':'69','bar_association':'Bayburt Barosu',
                      'bar_registration_number':str(i),'first_name':'TEST','last_name':'KAYA',
                      '_detail_index':str(i),'detail_status':'pending'} for i in [1,2]]
            keys=[db.upsert(r,qid,1,i) for i,r in enumerate(records)]
            driver=SimpleNamespace(details_attempted=0,needs_session_renewal=False,
                details=Mock(side_effect=[t.ListingIdentityMissing(['1']),[{**records[1],'detail_status':'done'}]]))
            args=SimpleNamespace(detail_concurrency=2,max_details=2,retries=1,retry_backoff=0,
                max_backoff=0,min_delay=0,max_delay=0,export_every=1,fail_fast=False)
            q=dict(db.db.execute('select * from queries where id=?',(qid,)).fetchone())
            t.process_details(driver,db,q,args,Path(td))
            self.assertEqual(db.db.execute('select status from details where key=?',(keys[1],)).fetchone()[0],'done')
            job=db.db.execute('select * from details where key=?',(keys[0],)).fetchone()
            self.assertEqual(job['status'],'pending');self.assertNotEqual(job['query_id'],qid)
            self.assertEqual(job['failures'],0)
            self.assertEqual(len(driver.details.call_args_list[-1].args[0]),1)
            db.db.close()

    def test_initial_browser_transport_failures_checkpoint_as_recoverable(self):
        from playwright import sync_api
        for message in ['Execution context was destroyed, most likely because of a navigation',
                        'Target page, context or browser has been closed',
                        'Page.goto: net::ERR_TIMED_OUT at https://www.barobirlik.org.tr/AvukatArama']:
            with self.subTest(message=message),tempfile.TemporaryDirectory() as td:
                manager=Mock();pw=manager.start.return_value;ctx=pw.chromium.launch_persistent_context.return_value
                ctx.pages=[];ctx.new_page.return_value=Mock()
                driver=Mock();driver.navigate.side_effect=RuntimeError(message)
                with patch.object(sync_api,'sync_playwright',return_value=manager),patch.object(t,'DirectoryBrowser',return_value=driver):
                    code=t.cli(['--baro','69','--prefix','KA','--output',td,'--population-file','',
                                '--session-restarts','0','--access-retries','0','--max-runtime','60','--search-mode','navigation'])
                self.assertEqual(code,2)
                report=json.loads((Path(td)/'quality_report.json').read_text())
                self.assertEqual(report['run_status'],'session_expired')

    def test_provider_cap_preflight_fails_closed_before_browser_launch(self):
        from provider_budget import validate_cap, BudgetError
        payload={'api_key':{'caps':[{'window':'billing_period','credits':200000,
                                    'used_credits':100000,'remaining_credits':100000}]}}
        self.assertEqual(validate_cap(payload,200000)['remaining_credits'],100000)
        for bad in [{}, {'api_key':{'caps':[]}},
                    {'api_key':{'caps':[{'window':'billing_period','credits':100000,'remaining_credits':100}]}}]:
            with self.assertRaises(BudgetError):validate_cap(bad,200000)
        with tempfile.TemporaryDirectory() as td,patch('provider_budget.check_zenrows_cap',side_effect=BudgetError('Cap unavailable')),patch('playwright.sync_api.sync_playwright') as launch:
            code=t.cli(['--provider-credit-cap','200000','--output',td,'--max-runtime','60'])
            self.assertEqual(code,1);launch.assert_not_called()

    def test_review_only_detail_resume_opens_no_paid_browser(self):
        with tempfile.TemporaryDirectory() as td:
            db=t.Database(Path(td)/'checkpoint.sqlite3');qid=db.put_query('69','KA')
            key=db.upsert({'bar_association_id':'69','bar_registration_number':'1',
                           '_detail_index':'1','detail_status':'pending'},qid)
            db.detail_state(key,'needs_review','Needs operator review');db.db.close()
            with patch('playwright.sync_api.sync_playwright') as launch:
                code=t.cli(['--resume-details-only','--baro','69','--prefix','KA','--output',td,'--population-file',''])
                self.assertEqual(code,2);launch.assert_not_called()
            self.assertEqual(json.loads((Path(td)/'quality_report.json').read_text())['run_status'],'review_required')

    def test_failed_only_resume_is_incomplete_without_implicit_paid_retry(self):
        with tempfile.TemporaryDirectory() as td:
            db=t.Database(Path(td)/'checkpoint.sqlite3');qid=db.put_query('69','KA')
            key=db.upsert({'bar_association_id':'69','bar_registration_number':'1',
                           '_detail_index':'1','detail_status':'pending'},qid)
            db.detail_state(key,'failed','Needs explicit retry');db.db.close()
            with patch('playwright.sync_api.sync_playwright') as launch:
                code=t.cli(['--resume-details-only','--baro','69','--prefix','KA','--output',td,'--population-file',''])
                self.assertEqual(code,2);launch.assert_not_called()
            self.assertEqual(json.loads((Path(td)/'quality_report.json').read_text())['run_status'],'detail_budget_paused')
