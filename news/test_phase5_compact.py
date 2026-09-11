"""Compact formatting, bounds, semantic safeguards and offline regression."""
import copy,json,unittest
from unittest.mock import patch
from news import phase5_compact as p
from news.phase3_briefing import load,units,GateError

class CompactTests(unittest.TestCase):
    def setUp(self):
        self.rows=load(p.ROOT);self.a=p.build(self.rows,'2026-09-12','https://example.com')
        self.e={'existing':{'count':192,'passed':True},'new':{'count':28,'passed':True}}
    def q(self,**kwargs):return p.gate(self.rows,self.a,'2026-09-12','https://example.com',self.e,kwargs.pop('unchanged',True),**kwargs)
    def articles(self):return [m for m in self.a['messages'] if m['kind']=='article']
    def test_01_eight(self):self.assertEqual(len(self.a['items']),8)
    def test_02_ids(self):self.assertEqual({x['safe_event_id'] for x in self.a['items']},{r['safe_event_id'] for r in self.rows})
    def test_03_urls(self):self.assertEqual({x['source_url'] for x in self.a['items']},{r['safe_original_url'] for r in self.rows})
    def test_04_labels(self):self.assertEqual([x['source_label'] for x in self.a['items']],[r[3] for r in p.REVIEWED])
    def test_05_one_button(self):
        for m in self.articles():self.assertEqual(m['template']['button_title'],'원문 보기');self.assertNotIn('buttons',m['template'])
    def test_06_link_identity(self):self.assertTrue(self.q()['checks']['article_links'])
    def test_07_test_marker_zero(self):self.assertNotIn('[TEST]',json.dumps(self.a))
    def test_08_header(self):self.assertEqual(sum(m['kind']=='header' for m in self.a['messages']),1)
    def test_09_article_count(self):self.assertEqual(len(self.articles()),8)
    def test_10_overview(self):self.assertEqual(sum(m['kind']=='overview' for m in self.a['messages']),1)
    def test_11_total(self):self.assertEqual(len(self.a['messages']),10)
    def test_12_numbers(self):self.assertEqual([m['number'] for m in self.articles()],list(range(1,9)))
    def test_13_article_limit(self):self.assertTrue(all(units(m['template']['text'])<=196 for m in self.articles()))
    def test_14_overview_limit(self):self.assertLessEqual(units(self.a['messages'][-1]['template']['text']),196)
    def test_15_lossless_sentences(self):
        for item,m in zip(self.a['items'],self.articles()):self.assertIn(item['compact_summary'],m['template']['text'])
    def test_16_input_immutable(self):
        before=copy.deepcopy(self.rows);p.build(self.rows,'2026-09-12','https://example.com');self.assertEqual(before,self.rows)
    def test_17_unapproved_input(self):
        self.rows[0]['safe_event_id']='HOLD'
        with self.assertRaises(GateError):p.build(self.rows,'2026-09-12','https://example.com')
    def test_18_no_network(self):
        with patch('news.daily.api',side_effect=AssertionError('API forbidden')) as api,patch('news.daily.refresh',side_effect=AssertionError('auth forbidden')) as auth:
            p.build(self.rows,'2026-09-12','https://example.com');api.assert_not_called();auth.assert_not_called()
    def test_19_no_gemini(self):
        with patch('news.daily.summarize',side_effect=AssertionError('Gemini forbidden')) as mock:p.build(self.rows,'2026-09-12','https://example.com');mock.assert_not_called()
    def test_20_actual_send_zero(self):self.assertEqual(self.a['actual_kakao_send_count'],0)
    def test_21_preservation_gate(self):self.assertEqual(self.q(unchanged=False)['status'],'HOLD')
    def test_22_secret(self):self.assertEqual(self.q(secrets=[self.a['items'][0]['compact_summary']])['status'],'HOLD')
    def test_23_no_schedule(self):
        self.a['scheduled_live_count']=1;self.assertEqual(self.q()['status'],'HOLD')
    def test_24_failed_regression(self):
        self.e['existing']['passed']=False;self.assertEqual(self.q()['status'],'HOLD')
    def test_25_failed_new_tests(self):
        self.e['new']['passed']=False;self.assertEqual(self.q()['status'],'HOLD')
    def test_26_link_mutation(self):
        self.articles()[0]['template']['link']['web_url']='https://example.org';self.assertEqual(self.q()['status'],'HOLD')
    def test_27_sentence_fallback(self):
        first='가'*100+'.';second='나'*100+'.'
        parts=p.format_parts(1,'제목',first+' '+second,'출처')
        self.assertEqual(len(parts),2);self.assertIn(first,parts[0]);self.assertIn(second,parts[1]);self.assertTrue(all(units(x)<=196 for x in parts))
    def test_28_unsplittable_hold(self):
        with self.assertRaises(GateError):p.format_parts(1,'제목','가'*300,'출처')
    def test_29_caveats(self):
        text=json.dumps(self.a,ensure_ascii=False)
        self.assertNotIn('K-12',text)
        for phrase in ['법정 예외','입법 제안','성과가 확인된 단계는 아니다','성능 보장으로 확대하지 않는다']:self.assertIn(phrase,text)
    def test_30_body_no_urls(self):self.assertTrue(self.q()['checks']['no_body_url'])

if __name__=='__main__':unittest.main()
