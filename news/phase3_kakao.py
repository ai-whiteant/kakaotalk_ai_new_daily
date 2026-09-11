"""One logical TEST delivery; reuse daily.config/State/refresh/api unchanged."""
import json
import re
from news import daily
from news.phase3_briefing import GateError, digest, quality, sensitive

ENDPOINT='https://kapi.kakao.com/v2/api/talk/memo/default/send'


def classify(error, stage):
    # Error bodies, token values and arbitrary exception messages never enter receipts.
    text=str(error)
    if stage=='auth' and 'talk_message consent missing' in text: return 'TEST_SEND_HOLD_SCOPE'
    if stage=='auth': return 'TEST_SEND_HOLD_AUTH'
    return 'TEST_SEND_HOLD_API'


def send(root, rows, artifact, evidence, secrets=(), dry_run=True):
    gate=quality(rows,artifact,evidence['existing'],evidence['new'],evidence['unchanged'],secrets)
    if gate['status']!='PASS': raise GateError('Delivery gate HOLD')
    receipt={'status':'DRY_RUN_PASS','mode':'TEST','live':0,'target':'self','messages_planned':len(artifact['messages']),'messages_sent':0,'parts':[],'content_sha256':digest(artifact)}
    if dry_run: return receipt
    cfg=daily.config()
    known=[v for k,v in cfg.items() if re.search('KEY|TOKEN|SECRET',k)]
    if sensitive(json.dumps(artifact,ensure_ascii=False),known): raise GateError('Secret in message')
    daily.canonical(cfg['KAKAO_LINK_URL'])
    state_dir=root/'.state'; state_dir.mkdir(exist_ok=True)
    journal=state_dir/('phase3_test_'+artifact['input_sha256']+'.json')
    # Exclusive create stops concurrent/repeated runs, including uncertain delivery.
    try:
        with journal.open('x',encoding='utf-8') as f: json.dump({'status':'pending'},f)
    except FileExistsError: raise GateError('TEST already attempted; inspect receipt before any further delivery') from None
    def save():
        temp=journal.with_suffix('.tmp')
        temp.write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
        temp.replace(journal)
    stage='auth'
    try:
        state=daily.State(cfg)
        if any(x.get('status') in ('pending','unknown') for x in state.data.get('deliveries',{}).values()):
            raise daily.ServiceError('Previous delivery uncertain')
        headers=daily.refresh(cfg,state)
        stage='send'
        for m in artifact['messages']:
            receipt['status']='pending'; receipt['pending_sequence']=m['sequence']; save()
            template={'object_type':'text','text':m['text'],'link':{'web_url':cfg['KAKAO_LINK_URL'],'mobile_web_url':cfg['KAKAO_LINK_URL']},'button_title':'서비스 안내'}
            result=daily.api(ENDPOINT,{'template_object':json.dumps(template,ensure_ascii=False)},headers,form=True)
            code=result.get('result_code')
            if type(code) is not int or code!=0: raise daily.ServiceError('Unconfirmed result')
            receipt['parts'].append({'sequence':m['sequence'],'result_code':0,'http_success':True})
            receipt['messages_sent']+=1
            receipt.pop('pending_sequence',None); save()
        receipt['status']='TEST_SEND_PASS'
    except Exception as error:
        receipt['status']=classify(error,stage)
        receipt['error_stage']=stage
        receipt['delivery_uncertain']=stage=='send'
        receipt['error_message']='Kakao '+stage+' not confirmed; no automatic retry'
    save()
    return receipt
