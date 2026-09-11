"""Calibration regressions and pair-isolation tests; no live API requests."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from news.test_phase2 import candidate,analysis
from news.phase21 import verify_input,run
from news.phase21_guard import calibrated_guard
from news.phase21_events import build_events_hardened


def checked(output,source='학교에서 AI 활용을 검토한다.',field='summary'):
    item=analysis()
    item[field]=output
    return calibrated_guard(item,[candidate(title=source,snippet=source)])


class GuardCalibrationTests(unittest.TestCase):
    def test_world_bank_phrase(self):
        result=checked('World Bank가 발표했다.','World Bank announced a report.')
        self.assertEqual(result['guard_status'],'PASS')
        entities=[f['value'] for f in result['findings'] if f['code']=='ENTITY_SUPPORTED']
        self.assertIn('World Bank',entities)
        self.assertNotIn('World',entities)
        self.assertNotIn('Bank',entities)

    def test_world_bank_alias(self):
        result=checked('World Bank 보고서를 검토한다.','세계은행이 보고서를 발표했다.')
        self.assertEqual(result['guard_status'],'PASS')
        self.assertTrue(result['findings'][0]['candidate_ids'])

    def test_generic_roles(self):
        for word in ['Educators','Policymakers','Teachers','Students','Researchers']:
            with self.subTest(word=word):
                self.assertEqual(checked(word+' should examine the implications.')['guard_status'],'PASS')

    def test_generic_transitions(self):
        for word in ['Conversely','Additionally']:
            self.assertEqual(checked(word+', further review is useful.')['guard_status'],'PASS')

    def test_generic_roles_discussing_policy_are_not_names(self):
        self.assertEqual(checked('Educators should review the policy.')['guard_status'],'PASS')

    def test_hyphenated_ai_adjectives(self):
        for word in ['AI-driven','AI-generated','AI-powered']:
            self.assertEqual(checked(word+' model 활용을 검토할 수 있다.')['guard_status'],'PASS')

    def test_named_model_context_not_stopword_exempt(self):
        result=checked('The new model is called Educators.')
        self.assertEqual(result['guard_status'],'AUTO_HOLD')

    def test_supported_grade_ordinal_both_directions(self):
        for source,output in [('8th grade','grade 8'),('grade 8','8th grade')]:
            result=checked(output+' students',source+' students')
            self.assertEqual(result['guard_status'],'PASS')
            self.assertIn('ORDINAL_SUPPORTED',[f['code'] for f in result['findings']])

    def test_supporting_candidate_number(self):
        item=analysis()
        item['summary']='grade 8 students'
        result=calibrated_guard(item,[candidate(),candidate('b',snippet='8th grade students')])
        self.assertEqual(result['guard_status'],'PASS')
        matches=[f for f in result['findings'] if f['code']=='ORDINAL_SUPPORTED']
        self.assertEqual(matches[0]['candidate_ids'],['b'])

    def test_unsupported_number(self):
        self.assertEqual(checked('학생 999명이 참여했다.')['guard_status'],'AUTO_HOLD')

    def test_unsupported_date_even_when_digits_exist(self):
        result=checked('2026-10-09에 발표했다.','2026-09-10에 발표했다.')
        self.assertEqual(result['guard_status'],'AUTO_HOLD')
        self.assertIn('UNSUPPORTED_DATE',[f['code'] for f in result['findings']])

    def test_supported_date_format(self):
        self.assertEqual(checked('2026년 9월 9일','2026-09-09')['guard_status'],'PASS')

    def test_unsupported_model(self):
        self.assertEqual(checked('GPT-99가 발표됐다.')['guard_status'],'AUTO_HOLD')

    def test_model_prefix_is_not_evidence(self):
        self.assertEqual(checked('GPT-99','GPT-999')['guard_status'],'AUTO_HOLD')

    def test_unsupported_url(self):
        self.assertEqual(checked('https://new.invalid/news')['guard_status'],'AUTO_HOLD')

    def test_unsupported_world_bank_not_globally_allowed(self):
        self.assertEqual(checked('World Bank announced a decision.')['guard_status'],'AUTO_HOLD')

    def test_paraphrase_without_new_claim(self):
        self.assertIn(checked('교육 현장 적용에 앞서 검토가 필요하다.')['guard_status'],('PASS','VERIFY'))

    def test_ambiguous_number_normalization(self):
        result=checked('학생 1000명','1,000 people')
        self.assertEqual(result['guard_status'],'VERIFY')
        self.assertTrue(result['fact_check_evidence'])

    def test_word_number_safe_count_context(self):
        result=checked('3 teachers','three teachers')
        self.assertEqual(result['guard_status'],'VERIFY')

    def test_audit_fields_and_fact_check_link(self):
        result=checked('학생 999명')
        issue=next(f for f in result['findings'] if f['status']=='AUTO_HOLD')
        self.assertEqual(set(issue),{'code','value','status','output_field','reason','matched_input','candidate_ids'})
        self.assertTrue(any('999' in s for s in result['analysis']['fact_check_targets']))

    def test_model_risk_preserved_with_verification(self):
        item=analysis()
        item['hallucination_risk']='high'
        result=calibrated_guard(item,[candidate()])
        self.assertEqual(result['guard_status'],'VERIFY')
        self.assertEqual(result['analysis']['hallucination_risk'],'high')


class PairClient:
    key='fixture-only-secret'
    model='fixture'
    def __init__(self,relation='SAME_EVENT',bad_pair=None,bridge=False):
        self.relation,self.bad_pair,self.bridge=relation,bad_pair,bridge
        self.calls=[]
    def generate(self,task,data,schema,semantic_check=None):
        self.calls.append({'status':'fixture'})
        left,right=data['left']['candidate_id'],data['right']['candidate_id']
        relation='DIFFERENT_EVENT' if self.bridge and {left,right}=={'a','c'} else self.relation
        result={'pair_id':data['pair_id'],'left_id':left,'right_id':right,'relation':relation,
            'confidence':0.97,'reason':'fixture actor/action/object evidence','representative_source_preference':left,
            'left_evidence':data['left_evidence_options'][0],'right_evidence':data['right_evidence_options'][0]}
        if self.bad_pair=={left,right}:
            result['left_evidence']='invented citation'
        semantic_check(result)
        return result


class DedupHardeningTests(unittest.TestCase):
    def rows(self):
        return [candidate(c,'OpenAI school policy announcement '+c) for c in 'abc']

    def test_same_policy_multisource(self):
        events,decisions,_=build_events_hardened(self.rows(),PairClient())
        self.assertEqual(len(events),1)
        self.assertEqual(len(decisions),3)

    def test_same_institution_different_policy(self):
        events,_,_=build_events_hardened(self.rows()[:2],PairClient('DIFFERENT_EVENT'))
        self.assertEqual(len(events),2)

    def test_follow_up_relationship_preserved(self):
        events,_,_=build_events_hardened(self.rows()[:2],PairClient('FOLLOW_UP'))
        self.assertEqual(len(events),2)
        self.assertEqual(events[0]['related_events'][0]['event_id'],events[1]['event_id'])
        self.assertEqual(events[1]['related_events'][0]['relation'],'FOLLOW_UP')

    def test_same_company_different_model(self):
        rows=[candidate('a','OpenAI Atlas release'),candidate('b','OpenAI Nova release')]
        events,_,_=build_events_hardened(rows,PairClient('DIFFERENT_EVENT'))
        self.assertEqual(len(events),2)

    def test_editorial_not_merged_into_original_report(self):
        rows=[candidate('a','OpenAI policy announcement'),candidate('b','OpenAI policy: What experts say')]
        events,decisions,_=build_events_hardened(rows,PairClient())
        self.assertEqual(len(events),2)
        self.assertEqual(decisions[0]['relation'],'FOLLOW_UP')

    def test_invalid_pair_does_not_discard_valid_pairs(self):
        events,decisions,warnings=build_events_hardened(self.rows(),PairClient(bad_pair={'a','b'}))
        self.assertEqual(len(decisions),2)
        self.assertEqual(len(warnings),1)
        self.assertEqual(sorted(len(e['candidate_ids']) for e in events),[1,2])

    def test_no_transitive_overmerge(self):
        events,_,_=build_events_hardened(self.rows(),PairClient(bridge=True))
        self.assertEqual(sorted(len(e['candidate_ids']) for e in events),[1,2])


class InputIntegrityTests(unittest.TestCase):
    def test_guard_recheck_restores_original_model_fields(self):
        from news.phase21_recheck import recover_model_analysis
        item=analysis()
        item['summary']='학생 999명'
        result=calibrated_guard(item,[candidate()])
        self.assertEqual(recover_model_analysis(result),item)

    def test_mismatch_holds_before_any_api(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'input.json'
            path.write_text('[]')
            client=Mock()
            client.calls=[]
            log=run(path,Path(directory)/'out',None,Path(directory),client=client)
            self.assertEqual(log['status'],'HOLD')
            client.generate.assert_not_called()


if __name__=='__main__':
    unittest.main()
