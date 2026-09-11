"""Offline gate tests; all send/refresh transports are mocked."""
import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch,Mock
from news import phase6_2 as p
from news.phase3 import write
from news.phase3_briefing import GateError,units
D='https://gateway.example.org'
class GatewayTests(unittest.TestCase):
 def test_allowlist(self):self.assertEqual(len(p.targets()),8)
 def test_input_hash(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);write(r/'outputs/phase2_3/samples/safe_content.json',[])
   with self.assertRaises(GateError):p.targets(r)
 def test_bad_origins(self):
  for s in ['http://a.com','https://u:p@a.com','https://a.com/x','https://a.com?x=y','https://developers.kakao.com','https://a.com:444','https://a..com']:
   with self.subTest(s=s),self.assertRaises(GateError):p.origin(s)
 def test_urls_eight(self):
  a=[x for x in p.templates(D) if x['kind']=='article'];self.assertEqual(len(a),8)
  for x in a:self.assertEqual(x['template']['link']['web_url'],D+'/r/'+x['safe_event_id'])
 def test_single_domain(self):
  for x in p.templates(D):
   t=x['template'];self.assertEqual(t['link'],t['buttons'][0]['link']);self.assertTrue(t['link']['web_url'].startswith(D+'/'));self.assertEqual(t['link']['mobile_web_url'],t['link']['web_url'])
 def test_article_buttons(self):
  for x in p.templates(D)[1:9]:self.assertEqual(x['template']['buttons'][0]['title'],'원문 보기')
 def test_no_direct_originals(self):
  text=json.dumps(p.templates(D));self.assertNotIn('developers.kakao.com',text)
  for url in p.targets().values():self.assertNotIn(url,text)
 def test_header_overview(self):
  m=p.templates(D)
  for x in [m[0],m[-1]]:self.assertEqual(x['template']['link']['web_url'],D+'/')
 def test_text_preserved(self):
  old=p.phase6.inputs(p.ROOT)[0]
  self.assertEqual([x['template']['text'] for x in old],[x['template']['text'] for x in p.templates(D)])
 def test_smoke_marker_limit(self):
  x=p.smoke(D);self.assertTrue(x['template']['text'].startswith('[GATEWAY LINK TEST]\n'));self.assertLessEqual(units(x['template']['text']),196);self.assertEqual(x['safe_event_id'],'evt_0da37ec7577bcd6b517d')
 def test_existing_protected(self):self.assertTrue(p.protected())
 def test_full_locked(self):
  with self.assertRaises(GateError):p.full_send(confirmed=True)
 def test_registration_blocks_before_auth(self):
  with patch.object(p.daily,'refresh') as auth,self.assertRaises(GateError):p.send_smoke(D)
  auth.assert_not_called()
 def fixture(self,r):
  write(r/'outputs/phase6_2/gateway/deployment.json',{'status':'GATEWAY_DEPLOYMENT_PASS','production_origin':D})
  e={}
  for k,n,c in [('existing','tests_existing.txt',282),('new','tests_phase6_2.txt',20),('gateway','tests_gateway.txt',20)]:
   f=r/'outputs/phase6_2/logs'/n;f.parent.mkdir(parents=True,exist_ok=True);f.write_text('fixture')
   e[k]={'passed':True,'count':c,'log_sha256':p.phase6.sha(f)}
  write(r/'outputs/phase6_2/quality/test_evidence.json',e)
 def execute(self,failure=False):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);self.fixture(r);x=p.smoke(D)
   with patch.object(p,'check_redirects',return_value={'passed':True}),patch.object(p,'protected',return_value=True),patch.object(p,'smoke',return_value=x),patch.object(p.daily,'config',return_value={}),patch.object(p.daily,'State',return_value=Mock(data={})),patch.object(p.daily,'refresh',return_value={}),patch.object(p.phase6,'post') as post:
    if failure:post.side_effect=TimeoutError('hidden')
    else:post.return_value={'result_code':0}
    result=p.send_smoke(D,True,r)
    self.assertEqual(post.call_count,1);self.assertEqual(result['scheduled_live_count'],0)
    self.assertTrue((r/'outputs/phase6_2/smoke/outbound_audit.json').exists())
    with self.assertRaises(GateError):p.send_smoke(D,True,r)
    self.assertEqual(post.call_count,1)
    return result
 def test_smoke_exactly_one_and_replay(self):self.assertEqual(self.execute()['messages_sent'],1)
 def test_timeout_no_retry(self):self.assertEqual(self.execute(True)['status'],'HOLD')
 def test_deployment_hold(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);write(r/'outputs/phase6_2/gateway/deployment.json',{'status':'DEPLOYMENT_HOLD'})
   with self.assertRaises(GateError):p.send_smoke(D,True,r)
 def test_http_gate_blocks(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);self.fixture(r)
   with patch.object(p,'check_redirects',return_value={'passed':False}),patch.object(p.daily,'refresh') as a,self.assertRaises(GateError):p.send_smoke(D,True,r)
   a.assert_not_called();self.assertFalse((r/'.state').exists())
 def test_preflight_rejects_wrong_location(self):
  with patch.object(p,'http',return_value={'status':302,'location':'https://evil.invalid'}):self.assertFalse(p.check_redirects(D)['passed'])
 def test_log_tamper(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);self.fixture(r);(r/'outputs/phase6_2/logs/tests_existing.txt').write_text('tampered')
   with self.assertRaises(GateError):p.send_smoke(D,True,r)
 def test_preflight_success(self):
  allow=p.targets()
  def fake(url,follow=False):
   event=next((k for k,v in allow.items() if v==url),url.rsplit('/',1)[-1])
   if event in allow:return {'status':200,'final_url':allow[event]} if follow else {'status':302,'location':allow[event]}
   return {'status':400 if event=='not-valid' else 404 if event.startswith('evt_') else 200}
  with patch.object(p,'http',side_effect=fake):self.assertTrue(p.check_redirects(D)['passed'])

 def advisory_result(self,final,initial_status=302,wrong_location=False,control_status=None):
  allow=p.targets()
  def fake(url,follow=False):
   if follow:return final
   event=url.rsplit('/',1)[-1]
   if event in allow:return {'status':initial_status,'location':'https://evil.invalid' if wrong_location else allow[event]}
   return {'status':control_status if control_status is not None else 400 if event=='not-valid' else 404 if event.startswith('evt_') else 200}
  with patch.object(p,'http',side_effect=fake):return p.check_redirects(D)
 def test_final_urlerror_advisory(self):
  r=self.advisory_result({'status':None,'error_type':'URLError'})
  self.assertTrue(r['passed'])
  for a in r['articles']:
   self.assertTrue(a['gateway_passed']);self.assertFalse(a['final_verified']);self.assertEqual(a['final_error'],'URLError')
 def test_final_403_advisory(self):
  r=self.advisory_result({'status':403});self.assertTrue(r['passed']);self.assertEqual(r['articles'][0]['final_error'],'HTTP_403')
 def test_final_timeout_advisory(self):
  r=self.advisory_result({'status':None,'error_type':'TimeoutError'});self.assertTrue(r['passed']);self.assertEqual(r['articles'][0]['final_error'],'TimeoutError')
 def test_final_wrong_host_advisory(self):
  r=self.advisory_result({'status':200,'final_url':'https://evil.invalid'});self.assertTrue(r['passed']);self.assertFalse(r['articles'][0]['final_verified']);self.assertEqual(r['articles'][0]['final_error'],'FINAL_HOST_MISMATCH')
 def test_initial_wrong_status_still_fails(self):
  r=self.advisory_result({'status':200},initial_status=301);self.assertFalse(r['passed']);self.assertEqual(r['articles'][0]['final_error'],'NOT_CHECKED_GATEWAY_FAILED')
 def test_wrong_location_still_fails(self):self.assertFalse(self.advisory_result({'status':200},wrong_location=True)['passed'])
 def test_control_failure_still_fails(self):self.assertFalse(self.advisory_result({'status':None,'error_type':'URLError'},control_status=500)['passed'])
 def test_final_success_fields(self):
  allow=p.targets()
  def fake(url,follow=False):
   if follow:return {'status':200,'final_url':url}
   event=url.rsplit('/',1)[-1]
   if event in allow:return {'status':302,'location':allow[event]}
   return {'status':400 if event=='not-valid' else 404 if event.startswith('evt_') else 200}
  with patch.object(p,'http',side_effect=fake):r=p.check_redirects(D)
  self.assertTrue(r['passed'])
  for a in r['articles']:self.assertTrue(a['final_verified']);self.assertIsNone(a['final_error'])

 def test_advisory_warnings_include_external_errors(self):
  for response,error in [({'status':None,'error_type':'URLError'},'URLError'),({'status':403},'HTTP_403'),({'status':None,'error_type':'TimeoutError'},'TimeoutError')]:
   with self.subTest(error=error):
    r=self.advisory_result(response);self.assertTrue(r['passed']);self.assertEqual(len(r['advisory_warnings']),8)
    self.assertEqual({w['event_id'] for w in r['advisory_warnings']},set(p.targets()))
    for w in r['advisory_warnings']:self.assertEqual(w['final_error'],error);self.assertEqual(w['expected_url'],p.targets()[w['event_id']])
 def test_gateway_failure_not_external_warning(self):
  r=self.advisory_result({'status':None,'error_type':'URLError'},initial_status=500)
  self.assertFalse(r['passed']);self.assertEqual(r['advisory_warnings'],[])
