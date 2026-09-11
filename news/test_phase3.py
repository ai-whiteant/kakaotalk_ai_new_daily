"""Phase 3 regression: safe binding, semantic splitting and guarded TEST delivery."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch,MagicMock
from news.phase3_briefing import load,validate,build,quality,units,sensitive,group_atoms,GateError,INPUT,INPUT_SHA
from news.phase3_kakao import send

ROOT=Path(__file__).resolve().parents[1]

class Phase3Tests(unittest.TestCase):
    def setUp(self):
        self.rows=load(ROOT)
        self.final=copy.deepcopy(self.rows)
        self.records=json.loads((ROOT/'outputs/phase2_3/verification/final_verification_records.json').read_text(encoding='utf-8'))
        self.a=build(self.rows)
        self.e={'existing':{'passed':True,'count':140},'new':{'passed':True,'count':28},'unchanged':True}
    def q(self): return quality(self.rows,self.a,self.e['existing'],self.e['new'],self.e['unchanged'])
    def test_01_exact_eight(self):
        with self.assertRaises(GateError): validate(self.rows[:-1],self.final,self.records)
    def test_02_raw_field_blocked(self):
        self.rows[0]['summary']='raw'
        with self.assertRaises(GateError): validate(self.rows,self.rows,self.records)
    def test_03_hold_reject_blocked(self):
        for status in ['FINAL_HOLD','FINAL_REJECT']:
            self.records[0]['verification_status']=status
            with self.assertRaises(GateError): validate(self.rows,self.final,self.records)
    def test_04_urls_preserved(self):
        for r in self.rows:
            self.assertEqual(sum(r['safe_original_url'] in m['text'] for m in self.a['messages']),1)
    def test_05_null_education_omitted(self):
        for r in self.rows:
            if r['safe_education_implication'] is None:
                self.assertFalse(any(a['field']=='safe_education_implication' for m in self.a['messages'] if m.get('event_id')==r['safe_event_id'] for a in m.get('atoms',[])))
    def test_06_null_classroom_omitted(self):
        for r in self.rows:
            if r['safe_classroom_use'] is None:
                self.assertFalse(any(a['field']=='safe_classroom_use' for m in self.a['messages'] if m.get('event_id')==r['safe_event_id'] for a in m.get('atoms',[])))
    def test_07_education_first(self):
        first=[m['event_id'] for m in self.a['messages'] if m.get('part')==1]
        self.assertEqual(first[:3],[r['safe_event_id'] for r in self.rows if r['safe_category']=='ai_education'])
    def test_08_unique_numbers(self):
        self.assertEqual([m['article_number'] for m in self.a['messages'] if m.get('part')==1],list(range(1,9)))
    def test_09_split_preserves_all_fields(self):
        for r in self.rows:
            atoms=[a for m in self.a['messages'] if m.get('event_id')==r['safe_event_id'] for a in m.get('atoms',[])]
            self.assertEqual({a['field']:a['value'] for a in atoms},{k:v for k,v in r.items() if k not in ('safe_event_id','safe_category') and v is not None})
    def test_10_article_parts_contiguous(self):
        for r in self.rows:
            indexes=[i for i,m in enumerate(self.a['messages']) if m.get('event_id')==r['safe_event_id']]
            self.assertEqual(indexes,list(range(min(indexes),max(indexes)+1)))
    def test_11_test_marker(self): self.assertTrue(all('[TEST]' in m['text'] for m in self.a['messages']))
    def test_12_weekly_binding(self):
        self.a['overview'][0]['text']='새로운 성과 999%'
        self.assertEqual(self.q()['status'],'HOLD')
    def test_13_secret_detection(self):
        self.assertTrue(sensitive('test value fixture-secret-987', ['fixture-secret-987']))
        self.assertTrue(sensitive('Bearer dummyfixture'))
    def test_14_dry_run_no_api(self):
        with patch('news.phase3_kakao.daily.api') as api:
            self.assertEqual(send(ROOT,self.rows,self.a,self.e)['status'],'DRY_RUN_PASS'); api.assert_not_called()
    def test_15_error_no_config_mutation(self):
        cfg={'KAKAO_LINK_URL':'https://example.com'}; original=copy.deepcopy(cfg)
        with tempfile.TemporaryDirectory() as d, patch('news.phase3_kakao.daily.config',return_value=cfg),patch('news.phase3_kakao.daily.State'),patch('news.phase3_kakao.daily.refresh',side_effect=ValueError('dummycredential')):
            r=send(Path(d),self.rows,self.a,self.e,dry_run=False)
        self.assertEqual(cfg,original); self.assertEqual(r['status'],'TEST_SEND_HOLD_AUTH')
    def test_16_live_blocked(self):
        self.a['mode']='LIVE'; self.a['live']=1
        with self.assertRaises(GateError): send(ROOT,self.rows,self.a,self.e)
    def test_17_input_hash_binding(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/INPUT; p.parent.mkdir(parents=True);p.write_text('[]')
            with self.assertRaises(GateError): load(Path(d))
    def test_18_url_mutation(self):
        self.rows[0]['safe_original_url']='https://example.com/invented'
        with self.assertRaises(GateError): validate(self.rows,self.rows,self.records)
    def test_19_deterministic_order(self): self.assertEqual(self.a,build(self.rows))
    def test_20_receipt_allowlist(self):
        with tempfile.TemporaryDirectory() as d,patch('news.phase3_kakao.daily.config',return_value={'KAKAO_LINK_URL':'https://example.com'}),patch('news.phase3_kakao.daily.State'),patch('news.phase3_kakao.daily.refresh',return_value={}),patch('news.phase3_kakao.daily.api',return_value={'result_code':0,'access_token':'dummycredential'}):
            r=send(Path(d),self.rows,self.a,self.e,dry_run=False)
        self.assertEqual(r['status'],'TEST_SEND_PASS');self.assertNotIn('dummycredential',json.dumps(r))
    def test_21_limit(self): self.assertTrue(all(units(m['text'])<=200 for m in self.a['messages']))
    def test_22_atomic_long_field_hold(self):
        with self.assertRaises(GateError): group_atoms([{'text':'가'*201}],lambda p,n:'[TEST]')
    def test_23_duplicate_event(self):
        self.rows[-1]=self.rows[0]
        with self.assertRaises(GateError): validate(self.rows,self.rows,self.records)
    def test_24_failed_regression_blocks(self):
        self.e['existing']['passed']=False
        with self.assertRaises(GateError): send(ROOT,self.rows,self.a,self.e)
    def test_25_changed_settings_blocks(self):
        self.e['unchanged']=False
        with self.assertRaises(GateError): send(ROOT,self.rows,self.a,self.e)
    def test_26_uncertain_no_retry(self):
        with tempfile.TemporaryDirectory() as d,patch('news.phase3_kakao.daily.config',return_value={'KAKAO_LINK_URL':'https://example.com'}),patch('news.phase3_kakao.daily.State'),patch('news.phase3_kakao.daily.refresh',return_value={}),patch('news.phase3_kakao.daily.api',side_effect=TimeoutError('dummycredential')) as api:
            r=send(Path(d),self.rows,self.a,self.e,dry_run=False)
            with self.assertRaises(GateError): send(Path(d),self.rows,self.a,self.e,dry_run=False)
            self.assertEqual(api.call_count,1);self.assertEqual(r['messages_sent'],0)
    def test_27_scope_failure(self):
        with tempfile.TemporaryDirectory() as d,patch('news.phase3_kakao.daily.config',return_value={'KAKAO_LINK_URL':'https://example.com'}),patch('news.phase3_kakao.daily.State'),patch('news.phase3_kakao.daily.refresh',side_effect=ValueError('talk_message consent missing')):
            r=send(Path(d),self.rows,self.a,self.e,dry_run=False)
        self.assertEqual(r['status'],'TEST_SEND_HOLD_SCOPE')
    def test_28_text_tamper_blocks(self):
        self.a['messages'][1]['text']+=' 추가 주장'
        self.assertEqual(self.q()['status'],'HOLD')

if __name__=='__main__': unittest.main()
