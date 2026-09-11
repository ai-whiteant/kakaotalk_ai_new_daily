"""Phase 6 frozen-input, replay and API-error regression tests."""
import copy,io,json,tempfile,unittest,urllib.error
from pathlib import Path
from contextlib import contextmanager,ExitStack
from unittest.mock import patch,MagicMock
from news import phase6 as p
from news.phase3_briefing import units,GateError

class CompactSendTests(unittest.TestCase):
    def setUp(self):
        self.m,self.items=p.inputs(p.ROOT);self.e={'existing':{'count':222,'passed':True},'new':{'count':30,'passed':True}}
    @contextmanager
    def delivery(self,error=None):
        with tempfile.TemporaryDirectory() as d,ExitStack() as s:
            root=Path(d);cfg={'KAKAO_LINK_URL':'https://example.com'}
            s.enter_context(patch.object(p,'inputs',return_value=(self.m,self.items)))
            s.enter_context(patch.object(p,'protected',return_value=True))
            s.enter_context(patch.object(p.daily,'config',return_value=cfg))
            s.enter_context(patch.object(p.daily,'State'))
            auth=s.enter_context(patch.object(p.daily,'refresh',return_value={}))
            post=s.enter_context(patch.object(p,'post',return_value={'result_code':0,'http_success':True,'http_status':200},side_effect=error))
            yield root,cfg,post,auth
    def test_01_ten(self):self.assertEqual(len(self.m),10)
    def test_02_eight(self):self.assertEqual(sum(x['kind']=='article' for x in self.m),8)
    def test_03_buttons(self):self.assertEqual(sum(x['template']['button_title']=='원문 보기' for x in self.m),8)
    def test_04_titles(self):self.assertTrue(all(x['template']['button_title']=='원문 보기' for x in self.m if x['kind']=='article'))
    def test_05_web(self):
        for m,i in zip(self.m[1:9],self.items):self.assertEqual(m['template']['link']['web_url'],i['source_url'])
    def test_06_mobile(self):
        for m,i in zip(self.m[1:9],self.items):self.assertEqual(m['template']['link']['mobile_web_url'],i['source_url'])
    def test_07_test_zero(self):self.assertNotIn('[TEST]',json.dumps(self.m))
    def test_08_mode(self):self.assertEqual(p.MODE,'COMPACT_PRODUCTION_ONCE')
    def test_09_length(self):self.assertTrue(all(units(x['template']['text'])<=196 for x in self.m))
    def test_10_order(self):self.assertEqual([x['number'] for x in self.m[1:9]],list(range(1,9)))
    def test_11_labels(self):
        for m,i in zip(self.m[1:9],self.items):self.assertIn('('+i['source_label']+')▼',m['template']['text'])
    def test_12_hash(self):
        with patch.object(p,'sha',return_value='bad'):
            with self.assertRaises(GateError):p.inputs(p.ROOT)
    def test_13_old_journal_preservation(self):
        with self.delivery() as (root,cfg,post,auth):
            old=root/'.state'/'phase4_old.json';old.parent.mkdir();old.write_text('preserve')
            p.send(root,self.m,self.e,True,False);self.assertEqual(old.read_text(),'preserve')
    def test_14_exclusive(self):
        with self.delivery() as (root,cfg,post,auth):
            j=p.journal(root);j.parent.mkdir();j.write_text('pending')
            with self.assertRaises(GateError):p.send(root,self.m,self.e,True,False)
            post.assert_not_called();auth.assert_not_called()
    def test_15_replay(self):
        with self.delivery() as (root,cfg,post,auth):
            p.send(root,self.m,self.e,True,False)
            with self.assertRaises(GateError):p.send(root,self.m,self.e,True,False)
            self.assertEqual(post.call_count,10)
    def test_16_uncertain_no_retry(self):
        with self.delivery(error=TimeoutError('fixture-secret')) as (root,cfg,post,auth):
            status,r=p.send(root,self.m,self.e,True,False)
            self.assertEqual(status,'COMPACT_SEND_HOLD_API');self.assertEqual(post.call_count,1)
            with self.assertRaises(GateError):p.send(root,self.m,self.e,True,False)
    def test_17_link_error(self):self.assertEqual(p.error_status(-2,'unregistered domain',400),'COMPACT_SEND_HOLD_LINK_DOMAIN')
    def test_18_auth_scope(self):
        self.assertEqual(p.error_status(-401,'invalid token',401),'COMPACT_SEND_HOLD_AUTH')
        self.assertEqual(p.error_status(-402,'insufficient scopes',403),'COMPACT_SEND_HOLD_SCOPE')
    def test_19_config_unchanged(self):
        with self.delivery(error=p.SendError('COMPACT_SEND_HOLD_LINK_DOMAIN')) as (root,cfg,post,auth):
            before=copy.deepcopy(cfg);status,r=p.send(root,self.m,self.e,True,False);self.assertEqual(cfg,before);self.assertEqual(status,'COMPACT_SEND_HOLD_LINK_DOMAIN')
    def test_20_secret(self):
        with self.delivery() as (root,cfg,post,auth):
            q=p.quality(root,self.m,self.e,True,[self.m[1]['template']['text']]);self.assertEqual(q['status'],'HOLD')
    def test_21_receipt(self):
        with self.delivery() as (root,cfg,post,auth):
            status,r=p.send(root,self.m,self.e,True,False)
            self.assertEqual(set(r),{'mode','messages_planned','messages_sent','parts'})
            self.assertTrue(all(set(x)=={'sequence','result_code','http_success','http_status'} for x in r['parts']))
    def test_22_schedule(self):
        with self.delivery() as (root,cfg,post,auth):self.assertEqual(p.quality(root,self.m,self.e,True)['scheduled_live_count'],0)
    def test_23_dry_no_api(self):
        with self.delivery() as (root,cfg,post,auth):
            p.send(root,self.m,self.e);post.assert_not_called();auth.assert_not_called();self.assertFalse(p.journal(root).exists())
    def test_24_ten_calls(self):
        with self.delivery() as (root,cfg,post,auth):
            status,r=p.send(root,self.m,self.e,True,False);self.assertEqual(post.call_count,10);self.assertEqual(r['messages_sent'],10);self.assertEqual(status,'COMPACT_SEND_PASS')
    def test_25_result_codes(self):
        for code in [False,'0',1,None]:
            response=MagicMock();response.__enter__.return_value=response;response.read.return_value=json.dumps({'result_code':code}).encode();response.status=200
            with patch('urllib.request.urlopen',return_value=response):
                with self.assertRaises(p.SendError):p.post(self.m[0]['template'],{})
    def test_26_http_domain_body(self):
        error=urllib.error.HTTPError('https://kapi.kakao.com',400,'fixture',{},io.BytesIO(b'{"code":-2,"msg":"web_url domain not registered fixture-secret"}'))
        with patch('urllib.request.urlopen',side_effect=error):
            with self.assertRaises(p.SendError) as c:p.post(self.m[0]['template'],{})
        self.assertEqual(c.exception.status,'COMPACT_SEND_HOLD_LINK_DOMAIN');self.assertNotIn('fixture-secret',str(c.exception))
    def test_27_confirmation_missing(self):
        with self.delivery() as (root,cfg,post,auth):
            with self.assertRaises(GateError):p.send(root,self.m,self.e,False,False)
            post.assert_not_called();auth.assert_not_called();self.assertFalse(p.journal(root).exists())
    def test_28_regression_fail(self):
        self.e['existing']['passed']=False
        with self.delivery() as (root,cfg,post,auth):
            with self.assertRaises(GateError):p.send(root,self.m,self.e,True,False)
    def test_29_partial_domain_stop(self):
        with self.delivery() as (root,cfg,post,auth):
            post.side_effect=[{'result_code':0,'http_success':True,'http_status':200},p.SendError('COMPACT_SEND_HOLD_LINK_DOMAIN',-2,400)]
            status,r=p.send(root,self.m,self.e,True,False);self.assertEqual(r['messages_sent'],1);self.assertEqual(post.call_count,2);self.assertEqual(status,'COMPACT_SEND_HOLD_LINK_DOMAIN')
    def test_30_no_regeneration(self):
        with patch('news.phase5_compact.build',side_effect=AssertionError('No regeneration')):self.assertEqual(p.inputs(p.ROOT)[0],self.m)

if __name__=='__main__':unittest.main()
