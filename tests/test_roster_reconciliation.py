import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import turkey_scraper as t
import roster_reconciliation as r
from types import SimpleNamespace


class RosterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.dest=Path(self.temp.name)
        self.db=t.Database(self.dest/'checkpoint.sqlite3')
        self.db.db.execute("INSERT INTO bars VALUES('6','ANKARA',1)")
        self.db.db.commit()
        self.roster={'source':'https://official.example/register','date':'2026-10-21',
                     'rows':[{'regNumber':'10','firstName':'ALİ','lastName':'KAYA'},
                             {'regNumber':'11','firstName':'AYŞE','lastName':'Q'}]}
    def tearDown(self):
        self.db.db.close();self.temp.cleanup()
    def test_import_queues_lookups_without_inventing_profiles_or_emails(self):
        result=r.reconcile(self.db,self.roster,'6')
        self.assertEqual(result['sources'][0]['missing_registration'],2)
        self.assertEqual(self.db.db.execute('SELECT count(*) FROM lawyers').fetchone()[0],0)
        self.assertEqual(self.db.db.execute("SELECT name FROM queries WHERE surname='' ").fetchone()[0],'AYŞE')
        self.assertTrue(self.db.export(self.dest)['roster_candidates_unresolved'])
        r.reconcile(self.db,self.roster,'6')
        self.assertEqual(self.db.db.execute('SELECT count(*) FROM queries').fetchone()[0],2)
    def test_observation_requires_matching_registration_and_name(self):
        r.reconcile(self.db,self.roster,'6')
        self.db.upsert({'bar_association_id':'6','bar_registration_number':'10','full_name':'ALİ KAYA'})
        self.db.upsert({'bar_association_id':'6','bar_registration_number':'11','full_name':'OTHER PERSON'})
        result=r.summary(self.db)['sources'][0]
        self.assertEqual(result['matched_id_and_name'],1)
        self.assertEqual(result['name_conflicts'],1)
        self.assertFalse(result['all_source_candidates_observed'])
    def test_invalid_or_conflicting_roster_is_not_partially_imported(self):
        self.roster['rows'].append({'regNumber':'10','firstName':'OTHER','lastName':'PERSON'})
        with self.assertRaises(ValueError):r.reconcile(self.db,self.roster,'6')
        self.assertEqual(self.db.db.execute('SELECT count(*) FROM queries').fetchone()[0],0)
    def test_interrupted_import_resumes_remaining_candidates(self):
        original=self.db.put_query;count=0
        def interrupted(*args,**kwargs):
            nonlocal count
            count+=1
            if count==2:raise RuntimeError('interruption')
            return original(*args,**kwargs)
        with patch.object(self.db,'put_query',interrupted):
            with self.assertRaises(RuntimeError):r.reconcile(self.db,self.roster,'6')
        self.db.db.close();self.db=t.Database(self.dest/'checkpoint.sqlite3')
        result=r.reconcile(self.db,self.roster,'6')
        self.assertEqual(result['sources'][0]['missing_registration'],2)
        self.assertEqual(self.db.db.execute('SELECT count(*) FROM roster_candidates').fetchone()[0],2)
    def test_already_completed_name_query_stays_visible_as_missing_identity(self):
        qid=self.db.put_query('6','KAYA','ALİ');self.db.finish(qid,'done')
        result=r.reconcile(self.db,self.roster,'6')['sources'][0]
        self.assertEqual(result['missing_requiring_review'],1)
        self.assertEqual(self.db.db.execute('SELECT status FROM queries WHERE id=?',(qid,)).fetchone()[0],'done')
    def test_both_field_seed_plan_covers_short_surname(self):
        self.assertTrue(any(s in 'Q' and n in 'ALİ' for s,n in t.seed_filters('AL','both')))
        self.assertEqual(t.seed_filters('AL','surname'),[('AL','')])
        self.assertEqual(r.search_piece('M.AZİZ'),'AZİZ')
    def test_exact_lookup_queues_real_listing_and_preserves_discovery_pending(self):
        r.reconcile(self.db,self.roster,'6');calls=[]
        record={'bar_association_id':'6','bar_registration_number':'10','first_name':'ALİ',
                'last_name':'KAYA','full_name':'ALİ KAYA','_detail_index':'1','detail_status':'pending'}
        driver=SimpleNamespace(fetch_registration=lambda bar,reg:([record],1,1))
        result=r.verify_candidates(driver,self.db,['6'],1,on_listing=calls.append)
        self.assertEqual(result['observed'],1);self.assertEqual(len(calls),1)
        saved=self.db.record(t.record_key(record));self.assertEqual(saved['_lookup_registration'],'10')
        self.assertNotEqual(saved.get('detail_status'),'done');self.assertFalse(saved.get('email'))
        self.assertEqual(self.db.db.execute('SELECT status FROM queries WHERE id=?',(calls[0],)).fetchone()[0],'pending')
    def test_verified_zero_is_recorded_without_inventing_a_profile_or_repeating(self):
        r.reconcile(self.db,self.roster,'6');calls=[]
        driver=SimpleNamespace(fetch_registration=lambda bar,reg:(calls.append(reg) or ([],0,1)))
        result=r.verify_candidates(driver,self.db,['6'],2)
        self.assertEqual(result['verified_absent'],2)
        r.verify_candidates(driver,self.db,['6'],2);self.assertEqual(len(calls),2)
        self.assertEqual(self.db.db.execute('SELECT count(*) FROM lawyers').fetchone()[0],0)
        self.assertEqual(r.summary(self.db)['sources'][0]['missing_registration'],2)
    def test_exact_lookup_retry_budget_reserved_before_failed_network(self):
        r.reconcile(self.db,self.roster,'6');budget={'remaining':2}
        def unavailable(*args):raise t.SessionExpired('connection lost')
        def reserve():budget['remaining']-=1
        driver=SimpleNamespace(fetch_registration=unavailable)
        for _ in range(2):
            with self.assertRaises(t.SessionExpired):
                r.verify_candidates(driver,self.db,['6'],budget['remaining'],on_reserve=reserve)
        self.assertEqual(budget['remaining'],0)
        self.assertEqual(r.verify_candidates(driver,self.db,['6'],0)['attempted'],0)
    def test_exact_lookup_rejects_wrong_identity_before_saving(self):
        r.reconcile(self.db,self.roster,'6')
        driver=SimpleNamespace(fetch_registration=lambda *args:([{'bar_association_id':'6','bar_registration_number':'999'}],1,1))
        with self.assertRaises(t.ExtractionError):r.verify_candidates(driver,self.db,['6'],1)
        self.assertEqual(self.db.db.execute('SELECT count(*) FROM lawyers').fetchone()[0],0)


if __name__=='__main__':unittest.main()
