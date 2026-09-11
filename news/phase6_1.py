"""Phase 6.1A: explicit article button, outbound audit, one smoke only."""
import argparse,copy,hashlib,json,re
from pathlib import Path
from news import daily,phase6
from news.phase3 import tests,write,EXISTING
from news.phase3_briefing import units,sensitive,digest,GateError
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'outputs/phase6_1'

def protected(root):
 b=json.loads((root/'outputs/phase6_1/quality/baseline.json').read_text(encoding='utf-8'))
 return all((root/n).is_file() and phase6.sha(root/n)==h for n,h in b['hashes'].items() if n not in ('SESSION_HANDOFF.md','.state/kakao.enc'))

def corrected(root):
 original,items=phase6.inputs(root);m=copy.deepcopy(original)
 for x in m:
  t=x['template'];t.pop('button_title',None)
  if x['kind']=='article':t['buttons']=[{'title':'원문 보기','link':copy.deepcopy(t['link'])}]
  else:
   t.pop('link',None);t['buttons']=[]
   x['delivery_ready']=False
   x['hold_reason']='Buttonless header/overview transport requires validation; preview only'
 return m

def smoke(root):
 x=copy.deepcopy(corrected(root)[1]);x['template']['text']='[LINK TEST]\n'+x['template']['text'];x['sequence']=1
 if units(x['template']['text'])>196:raise GateError('Smoke too long')
 return x

def audit_article(x):
 t=x['template'];buttons=t.get('buttons',[])
 if len(buttons)!=1 or buttons[0]['title']!='원문 보기':raise GateError('Wrong explicit button')
 link=buttons[0]['link']
 if t.get('link')!=link or link['web_url']!=link['mobile_web_url'] or 'developers.kakao.com' in link['web_url']:raise GateError('Button/content URL mismatch')
 return {'sequence':x['sequence'],'kind':x['kind'],'article_number':x['number'],'button_title':buttons[0]['title'],'web_url':link['web_url'],'mobile_web_url':link['mobile_web_url'],'text_sha256':hashlib.sha256(t['text'].encode()).hexdigest(),'url_sha256':hashlib.sha256(link['web_url'].encode()).hexdigest(),'template_sha256':digest(t)}

def validate(root,m):
 if m!=corrected(root):raise GateError('Corrected preview changed')
 items=phase6.inputs(root)[1];articles=[x for x in m if x['kind']=='article']
 for x,i in zip(articles,items):
  a=audit_article(x)
  if a['web_url']!=i['source_url']:raise GateError('Source URL mismatch')
 if len(articles)!=8:raise GateError('Eight articles required')
 return [audit_article(x) for x in articles]

def journal(root):return root/'.state'/('phase6_1_link_smoke_'+phase6.MESSAGE_SHA+'.json')

def full_send(*args,**kwargs):
 raise GateError('Full delivery disabled: mobile click confirmation and buttonless transport validation required')

def send_smoke(root,x,e,domains=False,dry=True):
 if x!=smoke(root) or not protected(root):raise GateError('Input/protected mismatch')
 if not(e['existing']['passed'] and e['existing']['count']==252 and e['new']['passed'] and e['new']['count']>=28):raise GateError('Tests required')
 cfg=daily.config();known=[v for k,v in cfg.items() if re.search('KEY|TOKEN|SECRET',k)]
 if sensitive(json.dumps(x,ensure_ascii=False),known):raise GateError('Secret gate')
 result={'status':'READY_FOR_SMOKE','messages_planned':1,'messages_sent':0,'parts':[],'mode':'LINK_SMOKE_ONLY','scheduled_live_count':0}
 if dry:return result
 if not domains:raise GateError('Domains confirmation required')
 jp=journal(root);jp.parent.mkdir(exist_ok=True)
 try:
  with jp.open('x',encoding='utf-8') as f:json.dump({'status':'pending'},f)
 except FileExistsError:raise GateError('Smoke already attempted') from None
 def save():
  temp=jp.with_suffix('.tmp');temp.write_text(json.dumps(result,indent=2),encoding='utf-8');temp.replace(jp)
 stage='auth'
 try:
  state=daily.State(cfg)
  if any(r.get('status') in ('pending','unknown') for r in state.data.get('deliveries',{}).values()):raise GateError('Prior unknown delivery')
  headers=daily.refresh(cfg,state);stage='send'
  # Freeze and audit the SAME template object passed into the existing transport.
  outbound=copy.deepcopy(x);record=audit_article(outbound)
  if outbound!=smoke(root):raise GateError('Outbound differs from approved smoke')
  result['status']='pending';save()
  write(root/'outputs/phase6_1/link_audit/outbound_templates_redacted.json',[dict(record,stage='IMMEDIATELY_BEFORE_NETWORK')])
  reply=phase6.post(outbound['template'],headers)
  if type(reply.get('result_code')) is not int or reply['result_code']!=0:raise GateError('Unconfirmed response')
  result['parts']=[{'sequence':1,'result_code':0,'http_success':True}];result['messages_sent']=1
  result['status']='SMOKE_API_PASS_USER_CONFIRMATION_REQUIRED'
 except phase6.SendError as error:
  result['status']={'COMPACT_SEND_HOLD_LINK_DOMAIN':'LINK_CORRECTION_HOLD_DOMAIN','COMPACT_SEND_HOLD_AUTH':'LINK_CORRECTION_HOLD_AUTH','COMPACT_SEND_HOLD_SCOPE':'LINK_CORRECTION_HOLD_SCOPE'}.get(error.status,'LINK_CORRECTION_HOLD_API')
 except Exception as error:
  result['status']=('LINK_CORRECTION_HOLD_SCOPE' if 'talk_message consent missing' in str(error) else 'LINK_CORRECTION_HOLD_AUTH') if stage=='auth' else 'LINK_CORRECTION_HOLD_API'
 save();return result

def run(actual=False,domains=False):
 if actual and journal(ROOT).exists():raise GateError('Prior smoke attempt: no replay')
 m=corrected(ROOT);planned=validate(ROOT,m);x=smoke(ROOT)
 e={'existing':tests(EXISTING+['news.test_phase3','news.test_phase4','news.test_phase5_compact','news.test_phase6'],OUT/'logs/tests_existing.txt'),'new':tests(['news.test_phase6_1'],OUT/'logs/tests_phase6_1.txt')}
 (OUT/'logs/tests.txt').write_text((OUT/'logs/tests_existing.txt').read_text(encoding='utf-8')+'\n'+(OUT/'logs/tests_phase6_1.txt').read_text(encoding='utf-8'),encoding='utf-8')
 write(OUT/'quality/test_evidence.json',e);write(OUT/'kakao/corrected_preview.json',m)
 write(OUT/'link_audit/planned_article_links.json',planned)
 (OUT/'kakao/mobile_preview.md').write_text('\n\n---\n\n'.join(y['template']['text']+('\n\n[원문 보기]('+y['template']['link']['web_url']+')' if y['kind']=='article' else '') for y in m),encoding='utf-8')
 (OUT/'smoke/smoke_preview.md').write_text(x['template']['text']+'\n\n[원문 보기]('+x['template']['link']['web_url']+')',encoding='utf-8')
 q={'status':'READY_FOR_SMOKE' if e['existing']['passed'] and e['existing']['count']==252 and e['new']['passed'] and e['new']['count']>=28 and protected(ROOT) else 'HOLD','header_buttons':0,'overview_buttons':0,'article_buttons':8,'full_send_enabled':False,'full_send_reason':'User click pending; buttonless header/overview REST transport unresolved','scheduled_live_count':0}
 write(OUT/'quality/quality_gate.json',q)
 r={'status':'HOLD','messages_sent':0}
 if q['status']=='READY_FOR_SMOKE':r=send_smoke(ROOT,x,e,domains,not actual)
 write(OUT/'smoke'/('smoke_receipt.json' if actual else 'dry_run_receipt.json'),r)
 write(OUT/'logs'/('run.json' if actual else 'dry_run.json'),r)
 print(json.dumps(r))

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--domains-confirmed',action='store_true');parser.add_argument('--send-link-smoke-test',action='store_true');args=parser.parse_args()
 try:run(args.send_link_smoke_test,args.domains_confirmed)
 except Exception as error:print(json.dumps({'status':'HOLD','error_type':type(error).__name__}));raise SystemExit(1)
