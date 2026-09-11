"""Approved fixed-pool PRODUCTION_ONCE only. No TEST replay or scheduler."""
import argparse
import copy
import hashlib
import json
import re
from pathlib import Path
from datetime import datetime, timezone
from news import daily
from news.phase3 import tests, write, EXISTING
from news.phase3_briefing import build as test_build, load, quality as test_quality, digest, sensitive, units, INPUT_SHA, PERIOD

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/phase4'
HEADER='2026.09.02 21:30 ~ 09.09 21:30 KST | 검증 완료 브리핑'
MODE='PRODUCTION_ONCE'

class ProductionHold(ValueError):
    pass


def journal_path(root):
    return root/'.state'/('phase4_production_once_'+INPUT_SHA+'.json')


def build(rows):
    a=copy.deepcopy(test_build(rows))
    a.pop('content_sha256')
    a['mode']=MODE
    a['scheduled_live_count']=0
    a['detailed']=a['detailed'].replace('# Kakao AI News [TEST]','# Kakao AI News',1).replace(PERIOD,HEADER,1).replace('검증된 사실과 해석·수업 제안을 구분한 TEST 브리핑입니다.','검증된 사실과 해석·수업 제안을 구분한 브리핑입니다.',1)
    for m in a['messages']:
        if m['kind']=='intro': m['text']='📢 Kakao AI News\n'+HEADER+'\n검증 완료 AI 핵심 뉴스 8건입니다.'
        else:
            if not m['text'].startswith('[TEST] '): raise ProductionHold('Unexpected template')
            m['text']=m['text'][len('[TEST] '):]
    a['content_sha256']=digest(a)
    return a


def protected(root):
    b=json.loads((root/'outputs/phase4/quality/baseline.json').read_text(encoding='utf-8'))
    return all((root/p).is_file() and hashlib.sha256((root/p).read_bytes()).hexdigest()==h for p,h in b['hashes'].items() if p!='SESSION_HANDOFF.md')


def prior_test(root):
    receipt=root/'outputs/phase3/kakao/test_receipt.json'
    journal=root/'.state'/('phase3_test_'+INPUT_SHA+'.json')
    r=json.loads(receipt.read_text(encoding='utf-8'));j=json.loads(journal.read_text(encoding='utf-8'))
    return r==j and r['status']=='TEST_SEND_PASS' and r['messages_sent']==28


def quality(rows, a, evidence, settings_ok, prior_ok, journal_absent, secrets=()):
    # Reuse all Phase 3 content validations on its unchanged canonical rendering.
    q=test_quality(rows,test_build(rows),{'passed':True,'count':140},{'passed':True,'count':28},True,secrets)
    rendered=json.dumps(a,ensure_ascii=False)
    checks={
        'phase3_content_checks':q['status']=='PASS',
        'approved_production_content':a==build(rows),
        'input_sha':a.get('input_sha256')==INPUT_SHA,
        'articles_8':len(rows)==8,
        'test_marker_zero':'[TEST]' not in rendered,
        'production_mode':a.get('mode')==MODE,
        'scheduled_live_zero':a.get('scheduled_live_count')==0 and a.get('live')==0,
        'header':HEADER in a['messages'][0]['text'],
        'utf16_limit':all(units(m['text'])<=200 for m in a['messages']),
        'secret_zero':not sensitive(rendered,secrets),
        'existing_168':evidence['existing'].get('passed') is True and evidence['existing'].get('count')==168,
        'new_tests':evidence['new'].get('passed') is True and evidence['new'].get('count',0)>=20,
        'protected_files':settings_ok is True,
        'phase3_test_preserved':prior_ok is True,
        'production_journal_absent':journal_absent is True}
    return {'status':'PASS' if all(checks.values()) else 'HOLD','checks':checks,'artifact_sha256':digest(a)}


def send(root, a, evidence, dry_run=True):
    rows=load(root)
    cfg=daily.config()
    secrets=[v for k,v in cfg.items() if re.search('KEY|TOKEN|SECRET',k)]
    q=quality(rows,a,evidence,protected(root),prior_test(root),not journal_path(root).exists(),secrets)
    if q['status']!='PASS': raise ProductionHold('Production gate HOLD')
    receipt={'mode':MODE,'messages_planned':len(a['messages']),'messages_sent':0,'parts':[]}
    if dry_run: return 'DRY_RUN_PASS',receipt
    daily.canonical(cfg['KAKAO_LINK_URL'])
    journal=journal_path(root);journal.parent.mkdir(exist_ok=True)
    # Reserve before any authentication/send call, including concurrent invocations.
    try:
        with journal.open('x',encoding='utf-8') as f: json.dump({'status':'pending','receipt':receipt},f)
    except FileExistsError: raise ProductionHold('Already attempted; no replay') from None
    state={'status':'pending','artifact_sha256':digest(a),'receipt':receipt}
    def save():
        temp=journal.with_suffix('.tmp')
        temp.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
        temp.replace(journal)
    stage='auth'
    try:
        auth=daily.State(cfg)
        if any(x.get('status') in ('pending','unknown') for x in auth.data.get('deliveries',{}).values()):
            raise ProductionHold('Previous legacy delivery uncertain')
        headers=daily.refresh(cfg,auth)
        stage='send'
        for m in a['messages']:
            state['pending_sequence']=m['sequence'];save()
            template={'object_type':'text','text':m['text'],'link':{'web_url':cfg['KAKAO_LINK_URL'],'mobile_web_url':cfg['KAKAO_LINK_URL']},'button_title':'서비스 안내'}
            result=daily.api('https://kapi.kakao.com/v2/api/talk/memo/default/send',{'template_object':json.dumps(template,ensure_ascii=False)},headers,form=True)
            code=result.get('result_code')
            if type(code) is not int or code!=0: raise ProductionHold('Send not confirmed')
            receipt['parts'].append({'sequence':m['sequence'],'result_code':0,'http_success':True})
            receipt['messages_sent']+=1
            state.pop('pending_sequence',None);save()
        state['status']='PRODUCTION_SEND_PASS'
    except Exception:
        state['status']='DELIVERY_HOLD'
        state['stage']=stage
        state['uncertain']=stage=='send'
        # No exception text, raw response or credential enters the journal/receipt.
    save()
    return state['status'],receipt


def run(actual=False):
    # Never overwrite a prior successful/uncertain actual receipt on replay.
    if actual and journal_path(ROOT).exists(): raise ProductionHold('Production already attempted')
    rows=load(ROOT);a=build(rows)
    cfg=daily.config();known=[v for k,v in cfg.items() if re.search('KEY|TOKEN|SECRET',k)]
    evidence={'existing':tests(EXISTING+['news.test_phase3'],OUT/'logs/tests_existing.txt'),'new':tests(['news.test_phase4'],OUT/'logs/tests_phase4.txt')}
    (OUT/'logs/tests.txt').write_text((OUT/'logs/tests_existing.txt').read_text(encoding='utf-8')+'\n'+(OUT/'logs/tests_phase4.txt').read_text(encoding='utf-8'),encoding='utf-8')
    q=quality(rows,a,evidence,protected(ROOT),prior_test(ROOT),not journal_path(ROOT).exists(),known)
    write(OUT/'quality/quality_gate.json',q);write(OUT/'quality/test_evidence.json',evidence);write(OUT/'quality/artifact.json',a)
    write(OUT/'kakao/mobile_messages.json',a['messages'])
    (OUT/'kakao/mobile_preview.md').write_text('\n\n---\n\n'.join(m['text'] for m in a['messages']),encoding='utf-8')
    (OUT/'briefing/detailed_briefing.md').write_text(a['detailed'],encoding='utf-8')
    write(OUT/'briefing/weekly_overview.json',a['overview'])
    status='GATE_HOLD';receipt={'mode':MODE,'messages_planned':len(a['messages']),'messages_sent':0,'parts':[]}
    if q['status']=='PASS':status,receipt=send(ROOT,a,evidence,dry_run=not actual)
    write(OUT/'kakao'/('production_receipt.json' if actual else 'dry_run_receipt.json'),receipt)
    result={'time':datetime.now(timezone.utc).isoformat(),'mode':MODE,'quality':q['status'],'send_status':status,'messages_planned':receipt['messages_planned'],'messages_sent':receipt['messages_sent'],'test_marker_count':sum(m['text'].count('[TEST]') for m in a['messages']),'scheduled_live_count':0,'tavily_calls':0,'gemini_calls':0,'protected_files_unchanged':protected(ROOT),'phase3_test_preserved':prior_test(ROOT)}
    write(OUT/'logs'/('run.json' if actual else 'dry_run.json'),result)
    print(json.dumps(result))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--send-production-once',action='store_true')
    args=parser.parse_args()
    try: run(args.send_production_once)
    except Exception as error:
        print(json.dumps({'status':'HOLD','error_type':type(error).__name__,'automatic_retry':False}))
        raise SystemExit(1)
