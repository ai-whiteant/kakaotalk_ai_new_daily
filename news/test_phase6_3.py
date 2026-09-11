"""Phase6.3 offline regression: all real transports mocked."""
import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch,Mock
from news import phase6_3 as p
from news.phase3 import write
from news.phase3_briefing import GateError,units,digest
class FinalOnceTests(unittest.TestCase):
 def setUp(self):self.m=p.templates(p.ROOT)
 def test_phase62_click_pass(self):self.assertTrue(p.phase62_pass(p.ROOT))
 def test_count_order(self):self.assertEqual(len(self.m),10);self.assertEqual([x['sequence'] for x in self.m],list(range(1,11)))
 def test_articles_eight(self):self.assertEqual(sum(x['kind']=='article' for x in self.m),8)
 def test_safe_allowlist(self):self.assertEqual({x['safe_event_id'] for x in self.m if x['kind']=='article'},set(p.phase6_2.targets()))
 def test_gateway_urls(self):
  for x in self.m[1:9]:self.assertEqual(x['template']['link']['web_url'],p.DOMAIN+'/r/'+x['safe_event_id'])
 def test_web_mobile_equal(self):
  for x in self.m:self.assertEqual(x['template']['link']['web_url'],x['template']['link']['mobile_web_url'])
 def test_button_title(self):
  for x in self.m[1:9]:self.assertEqual(x['template']['buttons'][0]['title'],'원문 보기')
 def test_root_links(self):
  for x in [self.m[0],self.m[-1]]:self.assertEqual(x['template']['link']['web_url'],p.DOMAIN+'/')
 def test_no_direct_links(self):
  t=json.dumps(self.m);self.assertNotIn('developers.kakao.com',t)
  for u in p.phase6_2.targets().values():self.assertNotIn(u,t)
 def test_no_markers(self):
  for x in self.m:self.assertNotIn('TEST',x['template']['text'].upper())
 def test_text_preserved(self):self.assertEqual([x['template']['text'] for x in self.m],[x['template']['text'] for x in p.phase6.inputs(p.ROOT)[0]])
 def test_utf16(self):self.assertTrue(all(units(x['template']['text'])<=196 for x in self.m))
 def test_validate_good(self):self.assertTrue(p.validate(p.ROOT,self.m))
 def test_text_tamper(self):
  self.m[1]['template']['text']+='new'
  with self.assertRaises(GateError):p.validate(p.ROOT,self.m)
 def test_link_tamper(self):
  self.m[1]['template']['link']['web_url']='https://evil.invalid'
  with self.assertRaises(GateError):p.validate(p.ROOT,self.m)
 def test_order_tamper(self):
  self.m[1],self.m[2]=self.m[2],self.m[1]
  with self.assertRaises(GateError):p.validate(p.ROOT,self.m)
 def test_prior_preserved(self):self.assertTrue(p.protected(p.ROOT))
 def test_journal_separate(self):self.assertIn('phase6_3_gateway_compact_',p.journal(p.ROOT).name)
 def mocksend(self,fail_at=None,response=None,dry=False):
  with tempfile.TemporaryDirectory() as td:
   r=Path(td);calls=[]
   def post(payload,headers):
    audit=p.read(r/'outputs/phase6_3/link_audit/outbound_templates_redacted.json');self.assertEqual(audit[-1]['payload_sha256'],digest(payload));self.assertEqual(audit[-1]['payload'],payload)
    calls.append(payload)
    if fail_at==len(calls):raise TimeoutError('must not be logged')
    return {'result_code':0} if response is None else response
   with patch.object(p,'quality',return_value={'status':'PASS'}),patch.object(p,'protected',return_value=True),patch.object(p,'validate',return_value=True),patch.object(p.daily,'config',return_value={}),patch.object(p.daily,'State',return_value=Mock(data={})),patch.object(p.daily,'refresh',return_value={}),patch.object(p.phase6,'post',side_effect=post):
    result=p.send(r,self.m,{},not dry)
    if not dry:
     before=p.journal(r).read_bytes()
     with self.assertRaises(GateError):p.send(r,self.m,{},True)
     self.assertEqual(before,p.journal(r).read_bytes())
    else:self.assertFalse(p.journal(r).exists())
    return result,calls
 def test_exactly_ten_and_replay_block(self):
  r,c=self.mocksend();self.assertEqual(len(c),10);self.assertEqual(r['messages_sent'],10);self.assertEqual(r['status'],p.PASS)
 def test_partial_stops(self):
  r,c=self.mocksend(fail_at=4);self.assertEqual(len(c),4);self.assertEqual(r['messages_sent'],3);self.assertEqual(r['status'],'HOLD');self.assertEqual(r['pending_sequence'],4)
 def test_first_timeout_stops(self):
  r,c=self.mocksend(fail_at=1);self.assertEqual(len(c),1);self.assertEqual(r['messages_sent'],0)
 def test_invalid_result_stops(self):
  for code in [False,'0',1,None]:
   with self.subTest(code=code):
    r,c=self.mocksend(response={'result_code':code});self.assertEqual(len(c),1);self.assertEqual(r['status'],'HOLD')
 def test_dry_no_send(self):r,c=self.mocksend(dry=True);self.assertEqual(c,[]);self.assertEqual(r['status'],'DRY_RUN_PASS')
 def test_scheduled_zero(self):r,c=self.mocksend();self.assertEqual(r['scheduled_live_count'],0)
 def test_secret_gate(self):
  with patch.object(p,'evidence_valid',return_value=True):q=p.quality(p.ROOT,self.m,{},[self.m[1]['template']['text']])
  self.assertFalse(q['checks']['secret_zero']);self.assertEqual(q['status'],'HOLD')
 def test_test_evidence_tamper(self):
  with tempfile.TemporaryDirectory() as td:
   r=Path(td);d=r/'outputs/phase6_3/logs';d.mkdir(parents=True);(d/'tests_existing_python.txt').write_text('changed')
   e={'existing':{'passed':True,'count':312,'log_sha256':'0'*64}}
   self.assertFalse(p.evidence_valid(r,e))
 def test_click_gate_blocks(self):
  with patch.object(p,'phase62_pass',return_value=False),self.assertRaises(GateError):p.templates(p.ROOT)
 def test_quality_hold_no_auth(self):
  with tempfile.TemporaryDirectory() as td,patch.object(p.daily,'config',return_value={}),patch.object(p,'quality',return_value={'status':'HOLD'}),patch.object(p.daily,'refresh') as auth:
   with self.assertRaises(GateError):p.send(Path(td),self.m,{},True)
   auth.assert_not_called()
