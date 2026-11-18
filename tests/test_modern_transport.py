import unittest
from types import SimpleNamespace
from unittest.mock import Mock
import turkey_scraper as t
from modern_transport import ModernDirectory,bar_key

class ModernTests(unittest.TestCase):
    def driver(self):
        d=Mock();d.args=SimpleNamespace(navigation_timeout=5,trainees=False);d.page.url=t.URL
        d.stats={'search_post_attempts':0,'detail_post_attempts':0};d.page.locator.return_value.count.return_value=0
        m=ModernDirectory(d,t);m.wire={'342':'İstanbul 2 Nolu Barosu'}
        return d,m
    def row(self,reg='1'):
        return {'baro':'İstanbul 2 Nolu Barosu','baroSicil':reg,'ad':'TEST','soyad':'AK'}
    def reply(self,rows,total=1,page=1,pages=1):
        return {'status':200,'data':{'kayitlar':rows,'toplamKayit':total,'sayfa':page,'toplamSayfa':pages}}
    def test_names_map_to_original_numeric_identity(self):
        d,m=self.driver();r=m.listing(self.row(),'342')
        self.assertEqual(r['bar_association_id'],'342')
        self.assertEqual(r['bar_association'],'İSTANBUL 2 NOLU')
        self.assertEqual(bar_key('İstanbul 1 Nolu Barosu'),bar_key('İSTANBUL'))
        with self.assertRaises(t.ExtractionError):m.listing(self.row(),'34')
    def test_all_pages_verified_and_duplicate_rejected(self):
        d,m=self.driver();d.page.evaluate.side_effect=[self.reply([self.row()],2,1,2),self.reply([self.row('2')],2,2,2)]
        rows,total,pages=m.submit('342','AK','');self.assertEqual((len(rows),total,pages),(2,2,2))
        d.page.evaluate.side_effect=[self.reply([self.row()],2,1,2),self.reply([self.row()],2,2,2)]
        with self.assertRaises(t.ExtractionError):m.submit('342','AK','')
    def test_rejection_is_not_an_empty_search(self):
        d,m=self.driver();d.page.evaluate.return_value={'status':400,'data':{'error':'verification failed'}}
        with self.assertRaises(t.VerificationRequired):m.submit('342','AK','')
        self.assertFalse(m.authorized)
    def test_missing_metadata_or_truncated_page_never_done(self):
        d,m=self.driver();d.page.evaluate.return_value=self.reply([],1)
        with self.assertRaises(t.ExtractionError):m.submit('342','AK','')
        d.page.evaluate.return_value={'status':200,'data':{'kayitlar':[]}}
        with self.assertRaises(t.ExtractionError):m.submit('342','AK','')
    def test_only_explicit_zero_is_empty(self):
        d,m=self.driver();d.page.evaluate.return_value=self.reply([],0,1,0)
        self.assertEqual(m.submit('342','AK',''),([],0,1))
    def test_detail_contact_evidence_and_identity(self):
        d,m=self.driver();rec=m.listing(self.row(),'342');d.last_query=('342','AK','');d.last_result=[rec]
        item={**self.row(),'tbbSicil':'2','eposta':'test@example.com','cep':'','is':'','fax':'','kep':'','adres':''}
        d.page.evaluate.return_value={'status':200,'data':{'kayit':item}}
        updated=m.detail(rec,d.last_query)
        self.assertEqual(updated['detail_status'],'done');self.assertEqual(updated['email'],'test@example.com')
        self.assertEqual(updated['_field_availability']['email'],'present');d.on_detail_extracted.assert_called_once()
        del item['eposta']
        with self.assertRaises(t.ExtractionError):m.detail(rec,d.last_query)
        item['eposta']='';item['baroSicil']='99'
        with self.assertRaises(t.ExtractionError):m.detail(rec,d.last_query)
    def test_first_detail_saved_before_second_fails(self):
        d,m=self.driver();a=m.listing(self.row(),'342');b=m.listing(self.row('2'),'342');d.last_query=('342','AK','');d.last_result=[a,b]
        d.page.evaluate.side_effect=[{'status':200,'data':{'kayit':{**self.row(),'tbbSicil':'2','eposta':''}}},{'status':403,'data':None}]
        with self.assertRaises(t.VerificationRequired):m.details([a,b],d.last_query)
        d.on_detail_extracted.assert_called_once()
        self.assertEqual(d.on_detail_extracted.call_args.args[0]['_field_availability']['email'],'blank_on_site')

    def test_rejected_natural_token_gets_only_one_budgeted_solve(self):
        d,m=self.driver();d.args._solver=Mock()
        rejected={'status':400,'data':{'error':'Güvenlik doğrulaması başarısız. Lütfen yeniden deneyin.'}}
        d.page.evaluate.side_effect=[rejected,rejected]
        with self.assertRaises(t.VerificationRequired):m.submit('342','AK','')
        d.solve_turnstile.assert_called_once_with(d.args._solver)
        self.assertEqual(d.page.evaluate.call_count,2)
        self.assertFalse(m.authorized)
    def test_no_solver_retry_for_managed_http_failure(self):
        d,m=self.driver();d.args._solver=Mock();d.page.evaluate.return_value={'status':403,'data':None}
        with self.assertRaises(t.VerificationRequired):m.submit('342','AK','')
        d.solve_turnstile.assert_not_called()
