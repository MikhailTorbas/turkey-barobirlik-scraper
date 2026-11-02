import unittest
from roster_pagination import assemble

def row(reg):return ['', '',str(reg),'NAME','SURNAME']
def page(total,*ids):return {'recordsFiltered':total,'data':[row(i) for i in ids]}

class PaginationTests(unittest.TestCase):
    def test_stable_public_total_requires_every_page_and_unique_ids(self):
        result=assemble({'A':{0:page(3,1,2),2:page(3,3)}},'A',2)
        self.assertTrue(result['all_letter_queries_complete'])
        self.assertFalse(result['national_completeness_claim'])
    def test_live_count_change_preserves_observed_new_ids_without_certifying_snapshot(self):
        result=assemble({'A':{0:page(3,1,2),2:page(4,3,4)}},'A',2)
        self.assertEqual(result['unique_registrations'],4)
        self.assertTrue(result['all_planned_pages_fetched'])
        self.assertEqual(result['letters_with_count_drift'],['A'])
        self.assertFalse(result['all_letter_queries_complete'])
    def test_missing_page_does_not_establish_coverage(self):
        result=assemble({'A':{0:page(5,1,2),4:page(5,5)}},'A',2)
        self.assertFalse(result['all_planned_pages_fetched'])
        self.assertEqual(result['errors'][0]['starts'],[2])
    def test_duplicate_ids_do_not_inflate_coverage(self):
        result=assemble({'A':{0:page(3,1,2),2:page(3,2)}},'A',2)
        self.assertEqual(result['unique_registrations'],2)
        self.assertFalse(result['all_letter_queries_complete'])

if __name__=='__main__':unittest.main()
