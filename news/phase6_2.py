"""Stable allowlist gateway. Offline by default; no full-send entry point."""
import argparse, copy, json, re
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError
from news import phase6, daily
from news.phase3 import write
from news.phase3_briefing import GateError, units, sensitive
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/phase6_2'
SAFE_SHA='1043ab60b27ee34b4e47cfb3af630eb8e3422af87ceb8f06b70f8d4faa1fbdb9'

def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def targets(root=ROOT):
    p=root/'outputs/phase2_3/samples/safe_content.json'
    if phase6.sha(p)!=SAFE_SHA:raise GateError('Safe input hash mismatch')
    rows=read(p); expected={x['safe_event_id']:x['safe_original_url'] for x in rows}
    actual=read(root/'link-gateway/data/targets.json')
    if len(rows)!=8 or len(expected)!=8 or actual!=expected:raise GateError('Allowlist mismatch')
    return actual

def origin(value):
    if not isinstance(value,str) or not re.fullmatch(r'https://[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?',value):raise GateError('Production HTTPS origin required')
    host=urlsplit(value).hostname
    if '.' not in host or host=='developers.kakao.com' or '..' in host:raise GateError('Invalid gateway host')
    return value

def templates(domain,root=ROOT):
    domain=origin(domain);allow=targets(root)
    original,items=phase6.inputs(root);result=copy.deepcopy(original)
    for x in result:
        t=x['template'];t.pop('button_title',None)
        if x['kind']=='article':
            event=x['safe_event_id']
            if event not in allow:raise GateError('Unknown article')
            url=domain+'/r/'+event;title='원문 보기'
        else:url=domain+'/';title='브리핑 안내'
        t['link']={'web_url':url,'mobile_web_url':url}
        t['buttons']=[{'title':title,'link':copy.deepcopy(t['link'])}]
        if units(t['text'])>196:raise GateError('Text too long')
    return result

def smoke(domain,root=ROOT):
    x=copy.deepcopy(templates(domain,root)[1]);x['sequence']=1
    x['template']['text']='[GATEWAY LINK TEST]\n'+x['template']['text']
    if units(x['template']['text'])>196:raise GateError('Smoke too long')
    return x

def protected(root=ROOT):
    h=read(root/'outputs/phase6_2/quality/baseline.json')['hashes']
    return all((root/n).is_file() and phase6.sha(root/n)==v for n,v in h.items()
               if n not in ('SESSION_HANDOFF.md','.state/kakao.enc') and not n.startswith('link-gateway/'))

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None

def http(url,follow=False):
    opener=build_opener() if follow else build_opener(NoRedirect)
    try:
        with opener.open(Request(url,headers={'User-Agent':'KakaoNewsGatewayVerification/1.0'}),timeout=25) as r:
            return {'status':r.status,'location':r.headers.get('Location'),'final_url':r.url}
    except HTTPError as e:
        return {'status':e.code,'location':e.headers.get('Location'),'final_url':e.url}
    except Exception as e:return {'status':None,'error_type':type(e).__name__}

def check_redirects(domain,root=ROOT):
    domain=origin(domain);records=[]
    for event,url in targets(root).items():
        first=http(domain+'/r/'+event)
        gateway_passed=first.get('status')==302 and first.get('location')==url
        final=http(url,True) if gateway_passed else {}
        final_verified=bool(gateway_passed and final.get('status')==200 and urlsplit(final.get('final_url','')).hostname==urlsplit(url).hostname)
        if not gateway_passed:final_error='NOT_CHECKED_GATEWAY_FAILED'
        elif final.get('error_type'):final_error=final['error_type']
        elif final.get('status')!=200:final_error='HTTP_'+str(final.get('status'))
        elif not final_verified:final_error='FINAL_HOST_MISMATCH'
        else:final_error=None
        records.append({'event_id':event,'expected_url':url,'initial':first,'final':final,
                        'gateway_passed':gateway_passed,'final_verified':final_verified,
                        'final_error':final_error,'passed':gateway_passed})
    controls=[{'path':p,'expected':s,'response':http(domain+p)} for p,s in [('/health',200),('/',200),('/r/not-valid',400),('/r/evt_ffffffffffffffffffff',404)]]
    advisory_warnings=[{'event_id':x['event_id'],'expected_url':x['expected_url'],'final_error':x['final_error']} for x in records if x['gateway_passed'] and not x['final_verified']]
    return {'domain':domain,'targets_sha256':phase6.sha(root/'link-gateway/data/targets.json'),'articles':records,'controls':controls,'advisory_warnings':advisory_warnings,'passed':len(records)==8 and all(x['gateway_passed'] for x in records) and all(x['response'].get('status')==x['expected'] for x in controls)}

def full_send(*args,**kwargs):raise GateError('Full send locked; separate click confirmation and approval required')

def send_smoke(domain,registered=False,root=ROOT):
    domain=origin(domain)
    if not registered:raise GateError('Gateway domain registration confirmation required')
    dep=read(root/'outputs/phase6_2/gateway/deployment.json')
    if dep.get('status')!='GATEWAY_DEPLOYMENT_PASS' or dep.get('production_origin')!=domain:raise GateError('Verified production deployment required')
    evidence=read(root/'outputs/phase6_2/quality/test_evidence.json')
    if not(evidence['existing']['passed'] and evidence['existing']['count']==282 and evidence['gateway']['passed'] and evidence['new']['passed']):raise GateError('Tests required')
    for key,name in [('existing','tests_existing.txt'),('new','tests_phase6_2.txt'),('gateway','tests_gateway.txt')]:
        if phase6.sha(root/'outputs/phase6_2/logs'/name)!=evidence[key]['log_sha256']:raise GateError('Test log changed')
    checks=check_redirects(domain,root)
    write(root/'outputs/phase6_2/gateway/redirect_checks.json',checks)
    if not checks['passed'] or not protected(root):raise GateError('Redirect/protected gate')
    x=smoke(domain,root);cfg=daily.config()
    known=[v for k,v in cfg.items() if re.search('KEY|TOKEN|SECRET',k)]
    if sensitive(json.dumps(x,ensure_ascii=False),known):raise GateError('Secret gate')
    jp=root/'.state'/('phase6_2_gateway_smoke_'+phase6.MESSAGE_SHA+'.json')
    jp.parent.mkdir(exist_ok=True)
    try:
        with jp.open('x',encoding='utf-8') as f:json.dump({'status':'pending','domain':domain},f)
    except FileExistsError:raise GateError('Prior smoke attempt; no replay') from None
    result={'status':'HOLD','messages_sent':0,'messages_planned':1,'scheduled_live_count':0,'domain':domain}
    try:
        state=daily.State(cfg)
        if any(r.get('status') in ('pending','unknown') for r in state.data.get('deliveries',{}).values()):raise GateError('Prior uncertain delivery')
        headers=daily.refresh(cfg,state)
        write(root/'outputs/phase6_2/smoke/outbound_audit.json',{'template':x['template'],'stage':'IMMEDIATELY_BEFORE_NETWORK'})
        reply=phase6.post(x['template'],headers)
        if type(reply.get('result_code')) is not int or reply['result_code']!=0:raise GateError('Unconfirmed response')
        result.update(status='GATEWAY_KAKAO_SMOKE_API_PASS_USER_CONFIRMATION_REQUIRED',messages_sent=1,result_code=0)
    except Exception as e:result['error_type']=type(e).__name__
    temp=jp.with_suffix('.tmp');write(temp,result);temp.replace(jp)
    write(root/'outputs/phase6_2/smoke/smoke_receipt.json',result)
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--domain',required=True);p.add_argument('--check-redirects',action='store_true');p.add_argument('--send-smoke',action='store_true');p.add_argument('--domain-registered',action='store_true');a=p.parse_args()
    try:
        write(OUT/'kakao/gateway_templates.json',templates(a.domain))
        if a.send_smoke:print(json.dumps(send_smoke(a.domain,a.domain_registered)))
        elif a.check_redirects:
            result=check_redirects(a.domain);write(OUT/'gateway/redirect_checks.json',result);print(json.dumps({'passed':result['passed']}))
        else:print(json.dumps({'status':'PREVIEW_ONLY','messages_sent':0}))
    except Exception as e:print(json.dumps({'status':'HOLD','error_type':type(e).__name__}));raise SystemExit(1)
