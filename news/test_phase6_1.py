"""Phase 6.1 smoke/audit safety tests; full delivery remains disabled."""
import copy,json,tempfile,unittest
from contextlib import contextmanager,ExitStack
from pathlib import Path
from unittest.mock import patch
from news import phase6_1 as p
from news.phase3_briefing import GateError,units

class LinkTests(unittest.TestCase):
 def setUp(self):
  self.m=p.corrected(p.ROOT);self.x=p.smoke(p.ROOT);self.e={'existing':{'passed':True,'count':252},'new':{'passed':True,'count':30}}
 @contextmanager
 def delivery(self,error=None,reply=None):
  with tempfile.TemporaryDirectory() as d,ExitStack() as s:
   root=Path(d);cfg={}
   s.enter_context(patch.object(p,'smoke',return_value=self.x));s.enter_context(patch.object(p,'protected',return_value=True));s.enter_context(patch.object(p.daily,'config',return_value=cfg));s.enter_context(patch.object(p.daily,'State'));auth=s.enter_context(patch.object(p.daily,'refresh',return_value={}))
   post=s.enter_context(patch.object(p.phase6,'post',side_effect=error,return_value=reply if reply is not None else {'result_code':0,'http_success':True}))
   yield root,cfg,post,auth
 def test_01_header_zero(self):self.assertEqual(self.m[0]['template']['buttons'],[])
 def test_02_overview_zero(self):self.assertEqual(self.m[-1]['template']['buttons'],[])
 def test_03_eight_buttons(self):self.assertEqual(sum(len(x['template']['buttons']) for x in self.m),8)
 def test_04_button_title(self):self.assertTrue(all(x['template']['buttons'][0]['title']=='원문 보기' for x in self.m[1:9]))
 def test_05_web(self):
  for x,i in zip(self.m[1:9],p.phase6.inputs(p.ROOT)[1]):self.assertEqual(x['template']['buttons'][0]['link']['web_url'],i['source_url'])
 def test_06_mobile(self):
  for x in self.m[1:9]:self.assertEqual(x['template']['buttons'][0]['link']['mobile_web_url'],x['template']['link']['web_url'])
 def test_07_no_developers(self):self.assertNotIn('developers.kakao.com',json.dumps(self.m))
 def test_08_audit_before_post(self):
  with self.delivery() as (root,cfg,post,auth):
   def check(t,h):
    a=json.loads((root/'outputs/phase6_1/link_audit/outbound_templates_redacted.json').read_text());self.assertEqual(a[0]['template_sha256'],p.digest(t));return {'result_code':0}
   post.side_effect=check;p.send_smoke(root,self.x,self.e,True,False)
 def test_09_audit_allowlist(self):self.assertEqual(set(p.audit_article(self.x)),{'sequence','kind','article_number','button_title','web_url','mobile_web_url','text_sha256','url_sha256','template_sha256'})
 def test_10_one_call(self):
  with self.delivery() as (root,cfg,post,auth):
   r=p.send_smoke(root,self.x,self.e,True,False);self.assertEqual(post.call_count,1);self.assertEqual(r['messages_sent'],1)
 def test_11_link_test_marker(self):self.assertTrue(self.x['template']['text'].startswith('[LINK TEST]'))
 def test_12_exclusive(self):
  with self.delivery() as (root,cfg,post,auth):
   j=p.journal(root);j.parent.mkdir();j.write_text('pending')
   with self.assertRaises(GateError):p.send_smoke(root,self.x,self.e,True,False)
   post.assert_not_called()
 def test_13_replay(self):
  with self.delivery() as (root,cfg,post,auth):
   p.send_smoke(root,self.x,self.e,True,False)
   with self.assertRaises(GateError):p.send_smoke(root,self.x,self.e,True,False)
   self.assertEqual(post.call_count,1)
 def test_14_full_confirmation_required(self):
  with self.assertRaises(GateError):p.full_send()
 def test_15_full_transport_not_pretended_ready(self):
  with self.assertRaises(GateError):p.full_send(link_smoke_confirmed=True)
 def test_16_order(self):self.assertEqual([x['number'] for x in self.m[1:9]],list(range(1,9)))
 def test_17_full_test_marker_zero(self):self.assertNotIn('[LINK TEST]',json.dumps(self.m))
 def test_18_nonarticle_no_link(self):self.assertNotIn('link',self.m[0]['template']);self.assertNotIn('link',self.m[-1]['template'])
 def test_19_old_journal_preserved(self):
  with self.delivery() as (root,cfg,post,auth):
   old=root/'.state'/'phase6_old.json';old.parent.mkdir();old.write_text('keep');p.send_smoke(root,self.x,self.e,True,False);self.assertEqual(old.read_text(),'keep')
 def test_20_hash_binding(self):
  with patch.object(p.phase6,'sha',return_value='bad'):
   with self.assertRaises(GateError):p.corrected(p.ROOT)
 def test_21_source_unchanged(self):
  before=p.phase6.inputs(p.ROOT)[0];p.corrected(p.ROOT);self.assertEqual(before,p.phase6.inputs(p.ROOT)[0])
 def test_22_timeout_no_retry(self):
  with self.delivery(error=TimeoutError()) as (root,cfg,post,auth):
   r=p.send_smoke(root,self.x,self.e,True,False);self.assertEqual(r['status'],'LINK_CORRECTION_HOLD_API');self.assertEqual(post.call_count,1)
 def test_23_result_validation(self):
  for code in [False,'0',1]:
   with self.delivery(reply={'result_code':code}) as (root,cfg,post,auth):self.assertEqual(p.send_smoke(root,self.x,self.e,True,False)['messages_sent'],0)
 def test_24_no_secret_exception(self):
  with self.delivery(error=ValueError('dummy-sensitive-secret')) as (root,cfg,post,auth):self.assertNotIn('dummy-sensitive-secret',json.dumps(p.send_smoke(root,self.x,self.e,True,False)))
 def test_25_schedule_zero(self):
  with self.delivery() as (root,cfg,post,auth):self.assertEqual(p.send_smoke(root,self.x,self.e)['scheduled_live_count'],0)
 def test_26_config_preserved(self):
  with self.delivery() as (root,cfg,post,auth):before=copy.deepcopy(cfg);p.send_smoke(root,self.x,self.e,True,False);self.assertEqual(before,cfg)
 def test_27_no_scope_bypass(self):
  with self.delivery() as (root,cfg,post,auth):
   auth.side_effect=ValueError('talk_message consent missing');self.assertEqual(p.send_smoke(root,self.x,self.e,True,False)['status'],'LINK_CORRECTION_HOLD_SCOPE');post.assert_not_called()
 def test_28_dry_no_api(self):
  with self.delivery() as (root,cfg,post,auth):p.send_smoke(root,self.x,self.e);post.assert_not_called();auth.assert_not_called()
 def test_29_content_link_mismatch(self):
  self.x['template']['link']['web_url']='https://example.com'
  with self.assertRaises(GateError):p.audit_article(self.x)
 def test_30_smoke_length(self):self.assertLessEqual(units(self.x['template']['text']),196)

if __name__=='__main__':unittest.main()
