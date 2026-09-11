"""Deterministic, lossless Phase 3 briefing over the approved eight records."""
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

INPUT = 'outputs/phase2_3/samples/safe_content.json'
INPUT_SHA = '1043ab60b27ee34b4e47cfb3af630eb8e3422af87ceb8f06b70f8d4faa1fbdb9'
LIMIT = 200  # Kakao default text template, official docs checked 2026-09-12.
PERIOD = '2026.09.02 21:30 ~ 09.09 21:30 KST | 고정 검증 자료'
CATEGORIES = {'ai_education':'AI 교육','policy_ethics':'AI 정책·윤리','domestic_ai':'국내 AI','ai_models':'AI 기술·모델','industry':'AI 산업'}
FIELDS = {'safe_title':'제목','safe_summary':'📌 핵심 내용','safe_why_it_matters':'💡 왜 중요한가','safe_education_implication':'👨‍🏫 교육적 시사점','safe_classroom_use':'📖 수업 활용','safe_original_url':'🔗 원문'}
KEYS = set(FIELDS) | {'safe_event_id','safe_category'}

class GateError(ValueError):
    pass


def digest(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True).encode()).hexdigest()


def units(text):
    return len(text.encode('utf-16-le')) // 2


def sensitive(text, secrets=()):
    return bool(any(isinstance(s,str) and len(s)>=8 and s in text for s in secrets) or re.search(r'AIza[\w-]{30,}|tvly-[\w-]{15,}|Bearer\s+\S+|-----BEGIN .*PRIVATE KEY|(?:access_token|refresh_token|client_secret)\s*[=:]\s*\S+',text,re.I))


def validate(rows, final, records):
    if not isinstance(rows,list) or len(rows)!=8 or rows!=final:
        raise GateError('Final pool mismatch')
    ids=[r.get('safe_event_id') for r in rows]
    if len(set(ids))!=8: raise GateError('Duplicate event')
    urls=[]
    for row in rows:
        if set(row)!=KEYS or row['safe_category'] not in CATEGORIES: raise GateError('Not safe-only')
        for field in FIELDS:
            v=row[field]
            if v is None and field in ('safe_education_implication','safe_classroom_use'): continue
            if not isinstance(v,str) or not v.strip() or sensitive(v): raise GateError('Invalid safe field')
        matches=[r for r in records if r['event_id']==row['safe_event_id']]
        if len(matches)!=1 or matches[0]['verification_status'] not in ('FINAL_VERIFIED','FINAL_VERIFIED_WITH_CONTEXT'):
            raise GateError('Unverified event')
        rec=matches[0]
        for f in FIELDS:
            expected=rec['final_url'] if f=='safe_original_url' else rec[f]
            if row[f]!=expected: raise GateError('Verified field changed')
        if row['safe_category']!=rec['category']: raise GateError('Category changed')
        u=urlsplit(row['safe_original_url'])
        if u.scheme!='https' or not u.hostname or u.username or u.password: raise GateError('Invalid URL')
        urls.append(row['safe_original_url'])
    if len(set(urls))!=8: raise GateError('Duplicate URL')
    return rows


def load(root):
    p=root/INPUT
    if hashlib.sha256(p.read_bytes()).hexdigest()!=INPUT_SHA: raise GateError('Input SHA mismatch')
    read=lambda s: json.loads((root/s).read_text(encoding='utf-8-sig'))
    return validate(read(INPUT),read('outputs/phase2_3/selection/final_candidates.json'),read('outputs/phase2_3/verification/final_verification_records.json'))


def weekly(rows):
    # Fixed, reviewed synthesis is bound to this approved input; no generation API.
    ids={r['safe_category']:[x['safe_event_id'] for x in rows if x['safe_category']==r['safe_category']] for r in rows}
    specs=[('가장 중요한 변화','해석: 학교의 AI 사용 범위와 기업의 특정 업무용 AI 적용을 함께 살펴볼 수 있다. 도입 계획·법안과 확인된 성과를 구분해야 한다.',ids['ai_education']+ids['domestic_ai']+ids['industry']),
    ('교육계 핵심 이슈','해석: 학생의 직접 사용, 교사 연수와 현장 참여를 구분해 검토할 필요가 있다. 학생 경험을 모든 학생의 인과적 학습 저하로 일반화하지 않는다.',ids['ai_education']),
    ('주목할 AI 기술','해석: 로컬 네트워크 추론 분배와 문서 검색용 공개 인코더를 살펴볼 수 있다. 모든 환경의 속도·보안·검색 성능을 보장하는 발표는 아니다.',ids['ai_models']),
    ('향후 관찰 포인트','관찰 제안: 학교 정책의 범위·예외, 얼굴·음성 동의와 제공자 책임, 기업 개발 계획과 실제 성과의 구분을 확인한다.',ids['ai_education']+ids['policy_ethics']+ids['industry'])]
    return [{'heading':h,'text':t,'kind':'interpretation_or_observation','source_event_ids':i} for h,t,i in specs]


def group_atoms(atoms, header):
    """Keep full semantic fields and URLs; never truncate or character-split."""
    parts=[]
    current=[]
    for atom in atoms:
        if units(header(99,99)+'\n'+atom['text'])>LIMIT: raise GateError('Whole semantic field exceeds template limit')
        if current and units(header(99,99)+'\n'+'\n\n'.join(a['text'] for a in current+[atom]))>LIMIT:
            parts.append(current); current=[]
        current.append(atom)
    if current: parts.append(current)
    return [{'text':header(i,len(parts))+'\n'+'\n\n'.join(a['text'] for a in p),'atoms':p,'part':i,'parts':len(parts)} for i,p in enumerate(parts,1)]


def build(rows):
    ordered=sorted(rows,key=lambda r:list(CATEGORIES).index(r['safe_category']))
    overview=weekly(rows)
    detail=['# Kakao AI News [TEST]','',PERIOD,'','검증된 사실과 해석·수업 제안을 구분한 TEST 브리핑입니다.','']
    messages=[{'kind':'intro','event_id':None,'text':'📢 Kakao AI News [TEST]\n'+PERIOD+'\n검증 완료 8건의 TEST입니다. 최신 재검색·LIVE 발송이 아닙니다.'}]
    for number,row in enumerate(ordered,1):
        detail += [f"## {number}. {row['safe_title']}",'',CATEGORIES[row['safe_category']],'']
        atoms=[]
        for field,label in FIELDS.items():
            value=row[field]
            if value is None: continue
            text=(CATEGORIES[row['safe_category']]+'\n'+value) if field=='safe_title' else label+'\n'+value
            atoms.append({'field':field,'value':value,'text':text})
            if field!='safe_title': detail += [label,'',value,'']
        for part in group_atoms(atoms,lambda p,n:f'[TEST] 기사 {number}/8 · {p}/{n}'):
            messages.append(dict(part,kind='article',event_id=row['safe_event_id'],article_number=number))
    detail += ['## 이번 주 AI 한눈에 보기','']
    for number,item in enumerate(overview,1):
        detail += ['### '+item['heading'],'',item['text'],'']
        text=f"[TEST] 이번 주 AI 한눈에 보기 {number}/4\n{item['heading']}\n\n{item['text']}"
        if units(text)>LIMIT: raise GateError('Overview exceeds limit')
        messages.append({'kind':'overview','event_id':None,'text':text,'source_event_ids':item['source_event_ids']})
    for i,m in enumerate(messages,1): m['sequence']=i
    result={'detailed':'\n'.join(detail),'overview':overview,'messages':messages,'input_sha256':INPUT_SHA,'mode':'TEST','live':0}
    result['content_sha256']=digest(result)
    return result


def quality(rows, artifact, existing, new, unchanged, secrets=()):
    expected=build(rows)
    checks={'exactly_8':len(rows)==8,'safe_fields_and_input_binding':artifact==expected,
        'hold_reject_zero':artifact==expected,
        'null_sections_omitted':artifact==expected,
        'no_articles_missing_after_split':artifact==expected,
        'sequence_numbers_unique': [m.get('sequence') for m in artifact['messages']]==list(range(1,len(expected['messages'])+1)),
        'unique_events':len({r['safe_event_id'] for r in rows})==8,
        'url_preservation':all(sum(a.get('field')=='safe_original_url' and a['value']==r['safe_original_url'] for m in artifact['messages'] for a in m.get('atoms',[]))==1 for r in rows),
        'message_limit':all(units(m['text'])<=LIMIT for m in artifact['messages']),
        'test_marker':all('[TEST]' in m['text'] for m in artifact['messages']),
        'no_secrets':not sensitive(json.dumps(artifact,ensure_ascii=False),secrets),
        'existing_140':existing.get('passed') is True and existing.get('count')==140,
        'new_tests':new.get('passed') is True and new.get('count',0)>=20,
        'settings_unchanged':unchanged is True,'no_live':artifact.get('live')==0 and artifact.get('mode')=='TEST'}
    return {'status':'PASS' if all(checks.values()) else 'HOLD','checks':checks,'artifact_sha256':digest(artifact)}
