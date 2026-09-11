"""Selection, evidence enforcement, and safe export regression cases."""
import copy
import unittest
from pathlib import Path

from news.phase22_evidence import digest
from news.phase23 import CHECKS, FIELDS, export_safe, rank_candidates, rescue_order, run, select, validate_registry, verify


class FinalGateTests(unittest.TestCase):
    def setUp(self):
        self.c = dict(event_id='e1', original_score=80, selection_adjustment=0,
            education_score=25, source_score=8, recency_score=10, category='ai_education',
            eligible=True, origin_state='PASS', guard_original='PASS', selection_rank=1,
            duplicate_group='e1', original_url='https://agency.example/news')
        self.s = dict(source_id='s1', url='https://agency.example/news', source_name='Agency',
            source_type='official', notes=['Fixture official policy publication'], locator='main body',
            retrieved_at='2026-09-11T00:00:00+00:00', access='body', verification_only=True)
        self.s['notes_sha256'] = digest(self.s['notes'])
        self.registry = validate_registry([self.s])
        self.r = dict(event_id='e1', candidate_sha256=digest(self.c),
            verified_claims=[dict(claim_id='c1', claim='Policy announced', status='SUPPORTED',
                core=True, source_ids=['s1'], reason='Reviewed original policy', semantic_review=True)],
            coverage={k:dict(status='CHECKED', reason='Claim assessed', claim_ids=['c1']) for k in CHECKS},
            final_source_id='s1', publication_interval=['2026-09-04T00:00:00+00:00','2026-09-04T23:59:59+00:00'],
            freshness_review='New policy announcement', context_changed=False,
            field_reviews={})
        for field in FIELDS:
            self.r[field] = '검토한 문장' if field in FIELDS[:3] else None
            self.r['field_reviews'][field] = dict(text_sha256=digest(self.r[field]), reviewed=True,
                reason='Source-specific review', claim_ids=['c1'], interpretation_or_suggestion=True)

    def result(self):
        return verify(self.c, self.r, self.registry)

    def pool(self):
        return [dict(self.c, event_id='e'+str(i), duplicate_group='g'+str(i), original_score=100-i) for i in range(31)]

    def test_01_select_fifteen_from_31(self):
        self.assertEqual(len(select(self.pool())), 15)

    def test_02_original_70_priority_not_adjusted_threshold(self):
        rows=self.pool()
        rows[-1].update(original_score=69, selection_adjustment=999)
        self.assertNotEqual(rank_candidates(rows)[0]['event_id'], rows[-1]['event_id'])

    def test_03_one_representative_per_group(self):
        rows=self.pool()
        rows[1]['duplicate_group']=rows[0]['duplicate_group']
        self.assertEqual(len({c['duplicate_group'] for c in select(rows)}),15)

    def test_04_low_score_important_policy_keeps_original_score(self):
        self.c['original_score']=65
        self.r['candidate_sha256']=digest(self.c)
        self.assertEqual(self.result()['verification_status'],'FINAL_HOLD')
        self.r['importance_exception']='Direct official school policy under workflow exception'
        self.assertEqual(self.result()['original_score'],65)
        self.assertEqual(self.result()['verification_status'],'FINAL_VERIFIED')

    def test_05_high_score_promotion_not_eligible(self):
        rows=self.pool();rows[0]['eligible']=False
        self.assertNotIn(rows[0]['event_id'],[c['event_id'] for c in select(rows)])

    def test_06_verified_fact(self):
        self.assertEqual(self.result()['verification_status'],'FINAL_VERIFIED')

    def test_07_context_rewrite(self):
        self.r['context_changed']=True
        self.assertEqual(self.result()['verification_status'],'FINAL_VERIFIED_WITH_CONTEXT')

    def test_08_unresolved_core_holds(self):
        self.r['verified_claims'][0]['status']='UNRESOLVED'
        self.assertEqual(self.result()['verification_status'],'FINAL_HOLD')

    def test_09_contradicted_core_rejects(self):
        self.r['verified_claims'][0]['status']='CONTRADICTED'
        self.assertEqual(self.result()['verification_status'],'FINAL_REJECT')

    def test_10_hold_not_exported(self):
        self.r['hold_reasons']=['Publication unknown']
        self.assertEqual(export_safe([self.result()]),[])

    def test_11_final_url_must_have_body(self):
        self.registry['s1']['access']='partial'
        self.assertEqual(self.result()['verification_status'],'FINAL_HOLD')

    def test_12_rescue_only_below_eight_and_descending(self):
        rows=[dict(self.c,event_id='low',origin_state='VERIFICATION_HOLD',original_score=70),
              dict(self.c,event_id='high',origin_state='VERIFICATION_HOLD',original_score=90)]
        self.assertEqual(rescue_order(rows,7)[0]['event_id'],'high')
        self.assertEqual(rescue_order(rows,8),[])

    def test_13_reject_never_reenters(self):
        rows=[dict(self.c,origin_state='REJECT',original_score=100)]
        self.assertEqual(rescue_order(rows,0),[])
        self.c['origin_state']='REJECT';self.r['candidate_sha256']=digest(self.c)
        with self.assertRaisesRegex(ValueError,'REJECT'):
            self.result()

    def test_14_education_overclaim_blocked(self):
        field='safe_education_implication'
        self.r[field]='이 도구는 성적을 보장한다'
        self.r['field_reviews'][field]['text_sha256']=digest(self.r[field])
        self.assertIn('EDUCATION_OVERCLAIM',self.result()['gate_reasons'])

    def test_15_only_safe_fields_export(self):
        self.r['summary']='Unreviewed old Gemini text'
        out=export_safe([self.result()])[0]
        self.assertTrue(all(k.startswith('safe_') for k in out))
        self.assertNotIn('Unreviewed',str(out))

    def test_16_changed_safe_text_rejected(self):
        self.r['safe_summary']='Injected new model'
        with self.assertRaisesRegex(ValueError,'Safe text'):
            self.result()

    def test_17_changed_export_text_rejected(self):
        result=self.result();result['safe_summary']='Injected after gate'
        with self.assertRaisesRegex(ValueError,'Export text'):
            export_safe([result])

    def test_18_fixed_period_end_precision(self):
        self.r['publication_interval']=['2026-09-09T00:00:00+00:00','2026-09-09T23:59:59+00:00']
        self.assertEqual(self.result()['verification_status'],'FINAL_HOLD')

    def test_19_unknown_event_date_holds(self):
        self.r['coverage']['event_date']['status']='UNRESOLVED'
        self.assertEqual(self.result()['verification_status'],'FINAL_HOLD')

    def test_20_coverage_gap_holds(self):
        self.r['coverage'].pop('entities')
        self.assertEqual(self.result()['verification_status'],'FINAL_HOLD')

    def test_21_original_candidate_tamper_rejected(self):
        self.c['original_score']=99
        with self.assertRaises(ValueError):
            self.result()

    def test_22_unchanged_input_objects(self):
        original=copy.deepcopy((self.c,self.r,self.registry))
        self.result()
        self.assertEqual(original,(self.c,self.r,self.registry))

    def test_23_final_duplicates_rejected(self):
        with self.assertRaisesRegex(ValueError,'duplicate'):
            export_safe([self.result(),self.result()])

    def test_24_failed_body_not_support(self):
        self.registry['s1']['access']='failed'
        self.assertIn('NO_RELIABLE_BODY',self.result()['gate_reasons'])

    def test_25_note_tampering_rejected(self):
        self.s['notes'].append('Unreviewed')
        with self.assertRaises(ValueError):
            validate_registry([self.s])

    def test_26_live_refused_before_io(self):
        with self.assertRaisesRegex(ValueError,'TEST only'):
            run(Path('.'),Path('missing'),Path('unused'),mode='LIVE')

    def test_27_rescue_skips_already_used_issue(self):
        row=dict(self.c,origin_state='VERIFICATION_HOLD')
        self.assertEqual(rescue_order([row],7,used_groups=['e1']),[])

    def test_28_noncore_contradiction_cannot_enter_safe_text(self):
        self.r['verified_claims'].append(dict(claim_id='c2',claim='Wrong number',status='CONTRADICTED',
            core=False,source_ids=['s1'],reason='Official number differs',semantic_review=True))
        self.assertEqual(self.result()['verification_status'],'FINAL_VERIFIED_WITH_CONTEXT')
        self.r['field_reviews']['safe_summary']['claim_ids'].append('c2')
        self.assertEqual(self.result()['verification_status'],'FINAL_HOLD')


if __name__ == '__main__':
    unittest.main()
