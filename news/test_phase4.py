"""Production-once regression with mocked API and isolated journals."""
import copy
import json
import tempfile
import unittest
from contextlib import ExitStack,contextmanager
from pathlib import Path
from unittest.mock import patch
from news import phase4 as p
from news.phase3_briefing import load,units,GateError,INPUT

class Phase4Tests(unittest.TestCase):
    def setUp(self):
        self.rows=load(p.ROOT); self.a=p.build(self.rows)
        self.e={'existing':{'passed':True,'count':168},'new':{'passed':True,'count':24}}
    def q(self,**kwargs):
        args=dict(settings_ok=True,prior_ok=True,journal_absent=True);args.update(kwargs)
        return p.quality(self.rows,self.a,self.e,**args)
    @contextmanager
    def delivery(self,result=None,error=None):
        with tempfile.TemporaryDirectory() as d, ExitStack() as stack:
            root=Path(d)
            cfg={'KAKAO_LINK_URL':'https://example.com','GEMINI_MODEL':'fixture-model'}
            stack.enter_context(patch.object(p,'load',return_value=self.rows))
            stack.enter_context(patch.object(p,'protected',return_value=True))
            stack.enter_context(patch.object(p,'prior_test',return_value=True))
            stack.enter_context(patch.object(p.daily,'config',return_value=cfg))
            stack.enter_context(patch.object(p.daily,'State'))
            refresh=stack.enter_context(patch.object(p.daily,'refresh',return_value={}))
            api=stack.enter_context(patch.object(p.daily,'api',return_value=result if result is not None else {'result_code':0},side_effect=error))
            yield root,cfg,api,refresh
    def test_01_production_header(self): self.assertIn(p.HEADER,self.a['messages'][0]['text'])
    def test_02_test_marker_zero(self): self.assertNotIn('[TEST]',json.dumps(self.a,ensure_ascii=False))
    def test_03_eight_articles(self):
        self.assertEqual(len({m['event_id'] for m in self.a['messages'] if m['kind']=='article'}),8)
    def test_04_safe_only_tamper(self):
        self.a['messages'][1]['text']+=' 새 성과'
        self.assertEqual(self.q()['status'],'HOLD')
    def test_05_urls(self):
        for row in self.rows:self.assertEqual(sum(row['safe_original_url'] in m['text'] for m in self.a['messages']),1)
    def test_06_null_fields(self):
        for row in self.rows:
            for field in ('safe_education_implication','safe_classroom_use'):
                if row[field] is None:self.assertFalse(any(a['field']==field for m in self.a['messages'] if m.get('event_id')==row['safe_event_id'] for a in m.get('atoms',[])))
    def test_07_utf16_limit(self):self.assertTrue(all(units(m['text'])<=200 for m in self.a['messages']))
    def test_08_sequence(self):self.assertEqual([m['sequence'] for m in self.a['messages']],list(range(1,29)))
    def test_09_input_sha(self):
        self.a['input_sha256']='bad'
        self.assertEqual(self.q()['status'],'HOLD')
    def test_10_phase3_journal_preserved(self):
        with self.delivery() as (root,cfg,api,refresh):
            path=root/'.state'/'phase3_test_fixture.json';path.parent.mkdir();path.write_text('preserve')
            p.send(root,self.a,self.e,dry_run=False)
            self.assertEqual(path.read_text(),'preserve')
    def test_11_exclusive_create(self):
        with self.delivery() as (root,cfg,api,refresh):
            j=p.journal_path(root);j.parent.mkdir();j.write_text('pending')
            with self.assertRaises(p.ProductionHold):p.send(root,self.a,self.e,dry_run=False)
            api.assert_not_called();refresh.assert_not_called();self.assertEqual(j.read_text(),'pending')
    def test_12_success_replay_blocked(self):
        with self.delivery() as (root,cfg,api,refresh):
            status,receipt=p.send(root,self.a,self.e,dry_run=False)
            self.assertEqual(status,'PRODUCTION_SEND_PASS')
            with self.assertRaises(p.ProductionHold):p.send(root,self.a,self.e,dry_run=False)
            self.assertEqual(api.call_count,28)
    def test_13_timeout_no_retry(self):
        with self.delivery(error=TimeoutError('credential-fixture')) as (root,cfg,api,refresh):
            status,receipt=p.send(root,self.a,self.e,dry_run=False)
            self.assertEqual(status,'DELIVERY_HOLD')
            with self.assertRaises(p.ProductionHold):p.send(root,self.a,self.e,dry_run=False)
            self.assertEqual(api.call_count,1);self.assertEqual(receipt['messages_sent'],0)
    def test_14_secret_blocking(self):
        self.assertEqual(self.q(secrets=[self.rows[0]['safe_title']])['status'],'HOLD')
    def test_15_config_unchanged(self):
        with self.delivery(error=ValueError('fixture')) as (root,cfg,api,refresh):
            before=copy.deepcopy(cfg);p.send(root,self.a,self.e,dry_run=False);self.assertEqual(before,cfg)
    def test_16_config_scheduler_hash_gate(self):self.assertEqual(self.q(settings_ok=False)['status'],'HOLD')
    def test_17_live_schedule_blocked(self):
        self.a['scheduled_live_count']=1
        self.assertEqual(self.q()['status'],'HOLD')
    def test_18_nonzero_response(self):
        for code in [False,'0',1,None]:
            with self.delivery(result={'result_code':code}) as (root,cfg,api,refresh):
                status,receipt=p.send(root,self.a,self.e,dry_run=False)
                self.assertEqual(status,'DELIVERY_HOLD');self.assertEqual(receipt['messages_sent'],0);self.assertEqual(api.call_count,1)
    def test_19_receipt_allowlist(self):
        with self.delivery(result={'result_code':0,'access_token':'fixture-sensitive-value'}) as (root,cfg,api,refresh):
            status,receipt=p.send(root,self.a,self.e,dry_run=False)
        self.assertEqual(set(receipt),{'mode','messages_planned','messages_sent','parts'})
        self.assertTrue(all(set(x)=={'sequence','result_code','http_success'} for x in receipt['parts']))
        self.assertNotIn('fixture-sensitive-value',json.dumps(receipt))
    def test_20_dry_run_no_api(self):
        with self.delivery() as (root,cfg,api,refresh):
            status,receipt=p.send(root,self.a,self.e)
            self.assertEqual(status,'DRY_RUN_PASS');api.assert_not_called();refresh.assert_not_called();self.assertFalse(p.journal_path(root).exists())
    def test_21_partial_failure_no_replay(self):
        with self.delivery() as (root,cfg,api,refresh):
            api.side_effect=[{'result_code':0},TimeoutError()]
            status,receipt=p.send(root,self.a,self.e,dry_run=False)
            self.assertEqual(receipt['messages_sent'],1)
            with self.assertRaises(p.ProductionHold):p.send(root,self.a,self.e,dry_run=False)
            self.assertEqual(api.call_count,2)
    def test_22_prior_test_gate(self):self.assertEqual(self.q(prior_ok=False)['status'],'HOLD')
    def test_23_regression_gate(self):
        self.e['existing']['passed']=False
        self.assertEqual(self.q()['status'],'HOLD')
    def test_24_logical_fields_lossless(self):
        from news.phase3_briefing import build
        before=build(self.rows)
        self.assertEqual([m.get('atoms') for m in before['messages']],[m.get('atoms') for m in self.a['messages']])
        self.assertEqual(before['overview'],self.a['overview'])

if __name__=='__main__':unittest.main()
