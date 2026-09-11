"""Phase 6.3: frozen Gateway compact production-once; never retry."""
import argparse,copy,json,os,re,subprocess
from pathlib import Path
from news import daily,phase6,phase6_2
from news.phase3 import tests,write,EXISTING
from news.phase3_briefing import digest,sensitive,units,GateError
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'outputs/phase6_3'
DOMAIN='https://kakao-ai-news-link-gateway.vercel.app'
PASS='GATEWAY_COMPACT_PRODUCTION_ONCE_PASS'
def read(p):return phase6.read(p)
def journal(root):return root/'.state'/('phase6_3_gateway_compact_'+phase6.MESSAGE_SHA+'.json')
def protected(root):
    b=read(root/'outputs/phase6_3/quality/baseline.json')['hashes']
    return all((root/n).is_file() and phase6.sha(root/n)==h for n,h in b.items() if n not in ('SESSION_HANDOFF.md','.state/kakao.enc'))
def phase62_pass(root):
    o=root/'outputs/phase6_2';q=read(o/'quality/quality_gate.json');d=read(o/'gateway/deployment.json');c=read(o/'gateway/redirect_checks.json');r=read(o/'smoke/smoke_receipt.json')
    return (q.get('final_gate')=='GATEWAY_LINK_PASS' and q.get('user_click_verification')=='PASS'
        and q.get('kakao_domain_registration')=='PASS' and d.get('verified') is True
        and d.get('production_origin')==DOMAIN and d.get('status')=='GATEWAY_DEPLOYMENT_PASS'
        and c.get('passed') is True and len(c['articles'])==8 and all(x['gateway_passed'] for x in c['articles'])
        and r.get('messages_sent')==1 and type(r.get('result_code')) is int and r['result_code']==0)
def templates(root):
    if not phase62_pass(root):raise GateError('Phase6.2 link PASS required')
    return phase6_2.templates(DOMAIN,root)
def validate(root,m):
    if m!=templates(root):raise GateError('Frozen template mismatch')
    original,items=phase6.inputs(root)
    if len(m)!=10 or [x['kind'] for x in m]!=['header']+['article']*8+['overview']:raise GateError('Order/count')
    if [x['template']['text'] for x in m]!=[x['template']['text'] for x in original]:raise GateError('Text changed')
    for x in m:
        t=x['template'];text=t['text']
        if units(text)>196 or 'TEST' in text.upper():raise GateError('Text marker/size')
        url=DOMAIN+'/r/'+x['safe_event_id'] if x['kind']=='article' else DOMAIN+'/'
        if t['link']!={'web_url':url,'mobile_web_url':url} or len(t['buttons'])!=1 or t['buttons'][0]['link']!=t['link']:raise GateError('Link mismatch')
        if x['kind']=='article' and t['buttons'][0]['title']!='원문 보기':raise GateError('Button title')
    return True
def evidence_valid(root,e):
    for k,count,name in [('existing',312,'tests_existing_python.txt'),('gateway',20,'tests_gateway.txt')]:
        if e[k].get('passed') is not True or e[k].get('count')!=count or phase6.sha(root/'outputs/phase6_3/logs'/name)!=e[k]['log_sha256']:return False
    return e['new'].get('passed') is True and e['new'].get('count',0)>=20 and phase6.sha(root/'outputs/phase6_3/logs/tests_phase6_3.txt')==e['new']['log_sha256']
def quality(root,m,e,secrets=()):
    validate(root,m)
    checks={'tests':evidence_valid(root,e),'protected':protected(root),'phase62_link_pass':phase62_pass(root),'journal_absent':not journal(root).exists(),'secret_zero':not sensitive(json.dumps(m,ensure_ascii=False),secrets)}
    return {'status':'PASS' if all(checks.values()) else 'HOLD','checks':checks,'messages_planned':10,'article_buttons':8,'gateway_article_links':8,'direct_original_links':0,'developers_links':0,'test_markers':0,'scheduled_live_count':0}
def save_journal(path,value):
    tmp=path.with_suffix('.tmp')
    with tmp.open('w',encoding='utf-8') as f:
        json.dump(value,f,ensure_ascii=False,indent=2);f.flush();os.fsync(f.fileno())
    tmp.replace(path)
def send(root,m,e,actual=False):
    if journal(root).exists():raise GateError('Prior attempt exists; no replay')
    cfg=daily.config();known=[v for k,v in cfg.items() if re.search('KEY|TOKEN|SECRET',k)]
    if quality(root,m,e,known)['status']!='PASS':raise GateError('Quality HOLD')
    result={'status':'DRY_RUN_PASS','messages_planned':10,'messages_sent':0,'parts':[],'scheduled_live_count':0,'input_sha256':phase6.MESSAGE_SHA,'templates_sha256':digest(m)}
    if not actual:return result
    frozen=copy.deepcopy(m);jp=journal(root);jp.parent.mkdir(exist_ok=True)
    try:
        with jp.open('x',encoding='utf-8') as f:
            json.dump({'status':'pending','input_sha256':phase6.MESSAGE_SHA},f);f.flush();os.fsync(f.fileno())
    except FileExistsError:raise GateError('Prior attempt exists; no replay') from None
    result['status']='pending';audit=[];stage='auth'
    try:
        auth=daily.State(cfg)
        if any(x.get('status') in ('pending','unknown') for x in auth.data.get('deliveries',{}).values()):raise GateError('Prior unknown delivery')
        headers=daily.refresh(cfg,auth);stage='send'
        for x in frozen:
            if not protected(root):raise GateError('Protected evidence changed')
            validate(root,frozen)
            result['pending_sequence']=x['sequence'];save_journal(jp,result)
            payload=copy.deepcopy(x['template'])
            audit.append({'sequence':x['sequence'],'kind':x['kind'],'event_id':x.get('safe_event_id'),'payload':payload,'payload_sha256':digest(payload),'stage':'IMMEDIATELY_BEFORE_NETWORK'})
            write(root/'outputs/phase6_3/link_audit/outbound_templates_redacted.json',audit)
            response=phase6.post(payload,headers)
            if type(response.get('result_code')) is not int or response['result_code']!=0:raise GateError('Unconfirmed result')
            result['parts'].append({'sequence':x['sequence'],'result_code':0});result['messages_sent']+=1
            result.pop('pending_sequence',None);save_journal(jp,result)
        result['status']=PASS
    except Exception as error:
        result.update(status='HOLD',error_type=type(error).__name__,error_stage=stage)
    save_journal(jp,result)
    write(root/'outputs/phase6_3/kakao/production_receipt.json',result)
    return result
def run(actual=False):
    if journal(ROOT).exists():raise GateError('Production-once already attempted; do not rerun')
    for d in ['quality','logs','kakao','link_audit']:(OUT/d).mkdir(parents=True,exist_ok=True)
    m=templates(ROOT)
    e={'existing':tests(EXISTING+['news.test_phase3','news.test_phase4','news.test_phase5_compact','news.test_phase6','news.test_phase6_1','news.test_phase6_2'],OUT/'logs/tests_existing_python.txt')}
    node=subprocess.run(['node','--test','link-gateway/tests/gateway.test.js'],cwd=ROOT,capture_output=True)
    (OUT/'logs/tests_gateway.txt').write_bytes(node.stdout+node.stderr)
    e['gateway']={'passed':node.returncode==0,'count':20,'log_sha256':phase6.sha(OUT/'logs/tests_gateway.txt')}
    e['new']=tests(['news.test_phase6_3'],OUT/'logs/tests_phase6_3.txt')
    write(OUT/'quality/test_evidence.json',e)
    (OUT/'logs/tests_existing.txt').write_bytes((OUT/'logs/tests_existing_python.txt').read_bytes()+(OUT/'logs/tests_gateway.txt').read_bytes())
    (OUT/'logs/tests.txt').write_bytes((OUT/'logs/tests_existing.txt').read_bytes()+(OUT/'logs/tests_phase6_3.txt').read_bytes())
    cfg=daily.config();known=[v for k,v in cfg.items() if re.search('KEY|TOKEN|SECRET',k)]
    q=quality(ROOT,m,e,known);write(OUT/'quality/quality_gate.json',q)
    write(OUT/'kakao/final_templates.json',m)
    (OUT/'kakao/mobile_preview.md').write_text('\n\n---\n\n'.join(x['template']['text']+'\n\n['+x['template']['buttons'][0]['title']+']('+x['template']['link']['web_url']+')' for x in m),encoding='utf-8')
    result=send(ROOT,m,e,actual)
    if not actual:write(OUT/'kakao/dry_run_receipt.json',result)
    write(OUT/'logs'/('audit.json' if actual else 'dry_run_audit.json'),dict(result,protected=protected(ROOT),tavily_calls=0,gemini_calls=0,automatic_retries=0))
    print(json.dumps({'status':result['status'],'messages_planned':10,'messages_sent':result['messages_sent'],'existing_tests':332,'new_tests':e['new'],'protected':protected(ROOT)}))
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--send-production-once',action='store_true');a=parser.parse_args()
    try:run(a.send_production_once)
    except Exception as error:print(json.dumps({'status':'HOLD','error_type':type(error).__name__}));raise SystemExit(1)
