"""Send the archived Phase 5 templates once, without regenerating compact text."""
import argparse,hashlib,json,re,zipfile
import urllib.request,urllib.parse,urllib.error
from pathlib import Path
from datetime import datetime,timezone
from news import daily
from news.phase3 import tests,write,EXISTING
from news.phase3_briefing import load as safe_load,units,sensitive,digest,GateError

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'outputs/phase6'
MODE='COMPACT_PRODUCTION_ONCE'
MESSAGE_SHA='8bd2d67d55faf32a5e8d1d1e695aed20738a12ab60ee1953b0be80f21a0f27e7'
ITEM_SHA='991868cecce7e57e19728558cb20991ddae48b1b1fcda1d4cc47bdede9d3c071'
PACKAGE_SHA='1433f227a28d9464a7b4fc4fc07f3315230959e053e9d53eef5ea8eb0620d8c5'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def journal(root):return root/'.state'/('phase6_compact_production_once_'+MESSAGE_SHA+'.json')

def protected(root):
    return all((root/n).is_file() and sha(root/n)==h for n,h in read(root/'outputs/phase6/quality/baseline.json')['hashes'].items() if n not in ('SESSION_HANDOFF.md','.state/kakao.enc'))

def inputs(root):
    package=root/'PHASE5_COMPACT_FORMAT_RESULT_PACKAGE.zip'
    if sha(package)!=PACKAGE_SHA:raise GateError('Phase5 package mismatch')
    with zipfile.ZipFile(package) as z:
        if z.testzip() is not None:raise GateError('Package CRC')
        manifest=json.loads(z.read('outputs/phase5/quality/package_manifest.json'))
        for n,h in manifest.items():
            if hashlib.sha256(z.read(n)).hexdigest()!=h:raise GateError('Package manifest mismatch')
    mp=root/'outputs/phase5/compact/mobile_messages.json';ip=root/'outputs/phase5/compact/compact_items.json'
    if sha(mp)!=MESSAGE_SHA or sha(ip)!=ITEM_SHA:raise GateError('Phase5 input hash mismatch')
    m=read(mp);items=read(ip);rows=safe_load(root);byid={r['safe_event_id']:r for r in rows}
    articles=[x for x in m if x['kind']=='article']
    if len(m)!=10 or len(articles)!=8 or len(items)!=8:raise GateError('Compact count mismatch')
    if [x['number'] for x in articles]!=list(range(1,9)):raise GateError('Article order mismatch')
    if {x['safe_event_id'] for x in articles}!=set(byid):raise GateError('Article identity mismatch')
    for x,item in zip(articles,items):
        url=byid[x['safe_event_id']]['safe_original_url'];t=x['template']
        if t['link']!={'web_url':url,'mobile_web_url':url} or t['button_title']!='원문 보기':raise GateError('Link mismatch')
        if item['safe_event_id']!=x['safe_event_id'] or '('+item['source_label']+')▼' not in t['text']:raise GateError('Source mismatch')
    if any(units(x['template']['text'])>196 or '[TEST]' in x['template']['text'] for x in m):raise GateError('Text gate')
    return m,items

def error_status(code,msg,http=0):
    # Bodies are used only in memory to classify ambiguous API codes.
    if re.search(r'domain|web_url|mobile_web_url|invalid.*link|link.*invalid|도메인|링크',str(msg),re.I):return 'COMPACT_SEND_HOLD_LINK_DOMAIN'
    if code==-402:return 'COMPACT_SEND_HOLD_SCOPE'
    if code==-401 or http==401:return 'COMPACT_SEND_HOLD_AUTH'
    return 'COMPACT_SEND_HOLD_API'

class SendError(Exception):
    def __init__(self,status,code=None,http=None):
        super().__init__(status);self.status=status;self.code=code if type(code)is int else None;self.http=http

def post(template,headers):
    # Existing daily.request hides HTTP bodies, so only this send transport reads
    # bounded error JSON to distinguish domain errors. Auth remains daily.refresh.
    data=urllib.parse.urlencode({'template_object':json.dumps(template,ensure_ascii=False)}).encode()
    req=urllib.request.Request('https://kapi.kakao.com/v2/api/talk/memo/default/send',data=data,headers={**headers,'Content-Type':'application/x-www-form-urlencoded'})
    try:
        with urllib.request.urlopen(req,timeout=90) as response:
            result=json.loads(response.read(65536));status=response.status
    except urllib.error.HTTPError as error:
        try: body=json.loads(error.read(16384))
        except Exception: body={}
        raise SendError(error_status(body.get('code'),body.get('msg',''),error.code),body.get('code'),error.code) from None
    except Exception:raise SendError('COMPACT_SEND_HOLD_API') from None
    if type(result.get('result_code')) is not int or result['result_code']!=0:
        raise SendError(error_status(result.get('code'),result.get('msg',''),status),result.get('code'),status)
    return {'result_code':0,'http_success':True,'http_status':status}

def quality(root,m,e,confirmed,secrets=()):
    checks={'input_unchanged':m==inputs(root)[0],'package_integrity':True,'ten_messages':len(m)==10,'eight_buttons':sum(x['kind']=='article' for x in m)==8,'utf16':all(units(x['template']['text'])<=196 for x in m),'test_zero':all('[TEST]' not in x['template']['text'] for x in m),'secret_zero':not sensitive(json.dumps(m,ensure_ascii=False),secrets),'prior_protected':protected(root),'existing_222':e['existing'].get('passed') is True and e['existing'].get('count')==222,'new_tests':e['new'].get('passed') is True and e['new'].get('count',0)>=25,'journal_absent':not journal(root).exists()}
    return {'status':'PASS' if all(checks.values()) else 'HOLD','checks':checks,'domain_registration':'USER_CONFIRMED' if confirmed else 'PENDING_USER_CONFIRMATION','send_authorized':bool(confirmed and all(checks.values())),'mode':MODE,'scheduled_live_count':0}

def send(root,m,e,confirmed=False,dry_run=True):
    cfg=daily.config();known=[v for k,v in cfg.items() if re.search('KEY|TOKEN|SECRET',k)]
    q=quality(root,m,e,confirmed,known)
    receipt={'mode':MODE,'messages_planned':len(m),'messages_sent':0,'parts':[]}
    if q['status']!='PASS':raise GateError('Quality HOLD')
    if dry_run:return 'DRY_RUN_PASS',receipt
    if not q['send_authorized']:raise GateError('Domain confirmation required')
    jp=journal(root);jp.parent.mkdir(exist_ok=True)
    try:
        with jp.open('x',encoding='utf-8') as f:json.dump({'status':'pending'},f)
    except FileExistsError:raise GateError('Already attempted; no replay') from None
    state={'status':'pending','input_sha256':MESSAGE_SHA,'receipt':receipt}
    def save():
        temp=jp.with_suffix('.tmp');temp.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8');temp.replace(jp)
    stage='auth'
    try:
        auth=daily.State(cfg)
        if any(x.get('status') in ('pending','unknown') for x in auth.data.get('deliveries',{}).values()):raise GateError('Prior uncertain delivery')
        headers=daily.refresh(cfg,auth);stage='send'
        for x in m:
            state['pending_sequence']=x['sequence'];save()
            result=post(x['template'],headers)
            receipt['parts'].append({'sequence':x['sequence'],**result});receipt['messages_sent']+=1
            state.pop('pending_sequence',None);save()
        state['status']='COMPACT_SEND_PASS'
    except SendError as error:
        state.update(status=error.status,error_code=error.code,http_status=error.http)
    except Exception as error:
        state['status']=('COMPACT_SEND_HOLD_SCOPE' if 'talk_message consent missing' in str(error) else 'COMPACT_SEND_HOLD_AUTH') if stage=='auth' else 'COMPACT_SEND_HOLD_API'
    save();return state['status'],receipt

def run(actual=False,confirmed=False):
    if actual and journal(ROOT).exists():raise GateError('Prior compact send already attempted')
    m,items=inputs(ROOT)
    e={'existing':tests(EXISTING+['news.test_phase3','news.test_phase4','news.test_phase5_compact'],OUT/'logs/tests_existing.txt'),'new':tests(['news.test_phase6'],OUT/'logs/tests_phase6.txt')}
    (OUT/'logs/tests.txt').write_text((OUT/'logs/tests_existing.txt').read_text(encoding='utf-8')+'\n'+(OUT/'logs/tests_phase6.txt').read_text(encoding='utf-8'),encoding='utf-8')
    cfg=daily.config();known=[v for k,v in cfg.items() if re.search('KEY|TOKEN|SECRET',k)]
    q=quality(ROOT,m,e,confirmed,known);write(OUT/'quality/quality_gate.json',q);write(OUT/'quality/test_evidence.json',e)
    write(OUT/'kakao/templates.json',m)
    (OUT/'kakao/mobile_preview.md').write_bytes((ROOT/'outputs/phase5/compact/mobile_preview.md').read_bytes())
    status='GATE_HOLD';receipt={'mode':MODE,'messages_planned':10,'messages_sent':0,'parts':[]}
    if q['status']=='PASS' and (not actual or q['send_authorized']):status,receipt=send(ROOT,m,e,confirmed,dry_run=not actual)
    elif actual:status='COMPACT_SEND_HOLD_LINK_DOMAIN'
    write(OUT/'kakao'/('production_receipt.json' if actual else 'dry_run_receipt.json'),receipt)
    result={'status':status,'quality':q['status'],'domain_registration':q['domain_registration'],'messages_planned':10,'messages_sent':receipt['messages_sent'],'article_buttons':8,'test_markers':0,'scheduled_live_count':0,'time':datetime.now(timezone.utc).isoformat(),'protected':protected(ROOT)}
    write(OUT/'logs'/('run.json' if actual else 'dry_run.json'),result);print(json.dumps(result))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--send-compact-production-once',action='store_true');parser.add_argument('--domains-confirmed',action='store_true',help='Use only after the user confirms all eight domains are saved')
    args=parser.parse_args()
    try:run(args.send_compact_production_once,args.domains_confirmed)
    except Exception as error:
        print(json.dumps({'status':'HOLD','error_type':type(error).__name__,'automatic_retry':False}));raise SystemExit(1)
