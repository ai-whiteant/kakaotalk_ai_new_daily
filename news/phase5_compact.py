"""Offline compact UX gate. No delivery entry point or authentication calls."""
import argparse
import hashlib
import json
import re
from pathlib import Path
from datetime import date
from urllib.parse import urlsplit
from news.phase3_briefing import load, units, sensitive, digest, GateError, INPUT_SHA
from news.phase3 import tests, write, EXISTING

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/phase5'
LIMIT=196
# Explicit reviewed mapping: event identity, title, compression, verified source label.
REVIEWED=[
('evt_0da37ec7577bcd6b517d','뉴욕 공립학교, 8학년까지 생성형 AI 사용 유예','뉴욕시는 2026~27학년도 2K~8학년 학생 대면 생성형 AI 사용을 유예한다. 보조공학 예외가 있으며 교사의 수업 준비·행정 활용과 AI 채점 금지는 구분된다. 학생·교사 사용 범위를 나눈 정책 사례다.','NYC교육청'),
('evt_4d1b5eaf0b2969af273d','美 의원, 학교 AI 실습실·교사 연수 지원 법안','AI LABS Act는 학교 AI 실습실과 교사 연수를 함께 지원하자는 법안이다. 시행이 완료된 정책이 아닌 입법 제안으로, 장비와 교사 준비를 함께 검토할 수 있다.','미 하원의원실'),
('evt_5e1e8fa929a91cc7a20f','학교 AI 도입, 학습과정과 교사 참여 함께 점검','Brookings는 학교 AI 도입 때 학생의 사고·대화와 교사 참여를 함께 점검하자고 제안했다. 학생 경험을 모든 학생의 인과적 학습 저하로 일반화하지 않는 것이 중요하다.','Brookings'),
('evt_d6a714447eb9102f7b6c','중국 최고법원, 딥페이크 등 AI 분쟁 지침 공개','중국 최고인민법원은 법정 예외 외 동의 없는 식별 가능한 얼굴·음성 이용과 침해 통지 후 조치하지 않은 생성형 AI 제공자 책임 등을 다룬 지침을 공개했다. 새 법 제정이 아닌 기존 법 적용 기준이다.','中최고인민법원'),
('evt_2c5e8e267c5e3b302614','네이버클라우드, 보안 특화 AI 모델 사업 선정','네이버클라우드 컨소시엄이 사이버보안 특화 AI 파운데이션 모델 개발 사업자로 선정됐다. 국내 보안 환경용 모델 개발과 현장 검증 계획이며 실제 보안 개선 성과가 확인된 단계는 아니다.','네이버'),
('evt_69c74bc9d2234f20c095','NVIDIA, 로컬 AI 연결 도구 PAIR 소개','NVIDIA는 로컬 네트워크의 여러 PC에 AI 추론 요청을 분배하는 PAIR를 소개했다. 로컬 AI를 여러 장치에서 실행하는 방식이지만 모든 환경의 속도·보안 개선이 입증된 것은 아니다.','NVIDIA'),
('evt_3ea3f9900f7045801269','H Company, 문서 검색용 NeoMME 공개','H Company는 이미지·텍스트를 처리하는 NeoMME를 공개했다. 260M·800M 체크포인트를 Apache 2.0으로 제공한다. 연구진의 검색 평가를 모든 현장 성능 보장으로 확대하지 않는다.','H Company'),
('evt_02616cccf42396459676','삼성·미스트랄, 반도체 설계·제조 AI 협력','삼성전자와 Mistral AI는 반도체 설계·제조용 AI 협력을 발표했다. 맞춤형 AI를 결함 탐지·장비 최적화 등에 적용할 계획이며 실제 수율·비용 개선이 확인된 단계는 아니다.','삼성전자')]
OVERVIEW='📌 이번 주 AI 한눈에 보기\n• 교육: 학생·교사 사용 기준과 교사 연수 논의\n• 정책: 얼굴·음성 동의와 AI 제공자 책임\n• 기술: 로컬 AI·멀티모달 문서 검색\n• 산업: 보안·반도체 현장 AI 적용 추진\n• 관찰: 발표·계획과 실제 성과를 구분'


def protected(root=ROOT):
    b=json.loads((root/'outputs/phase5/quality/baseline.json').read_text(encoding='utf-8'))
    return all((root/p).is_file() and hashlib.sha256((root/p).read_bytes()).hexdigest()==h for p,h in b['hashes'].items() if p!='SESSION_HANDOFF.md')


def format_parts(number,title,summary,label):
    prefix=f'{number}. {title} → '
    suffix=f'({label})▼'
    whole=prefix+summary+suffix
    if units(whole)<=LIMIT:return [whole]
    # Complete-sentence fallback. Never cut a word, sentence, decimal, or source label.
    sentences=re.split(r'(?<=[.!?])\s+',summary)
    for cut in range(1,len(sentences)):
        pair=[prefix+' '.join(sentences[:cut])+suffix,f'{number}. {title} (계속) → '+' '.join(sentences[cut:])+suffix]
        if all(units(x)<=LIMIT for x in pair):return pair
    raise GateError('Requires reviewed sentence compression; no character truncation')


def template(text,url,label):
    u=urlsplit(url)
    if u.scheme!='https' or not u.hostname or u.username or u.password:raise GateError('Invalid link')
    return {'object_type':'text','text':text,'link':{'web_url':url,'mobile_web_url':url},'button_title':label}


def build(rows,display_date,service_link):
    # This fixed-pool formatter must not silently use new or modified source data.
    if rows!=load(ROOT):raise GateError('Approved safe pool mismatch')
    d=date.fromisoformat(display_date)
    heading=f'{d.year%100}.{d.month}.{d.day}.\n\n📢 AI 핵심 뉴스 8선\n2026.9.2~9.9 검증 브리핑'
    messages=[{'kind':'header','template':template(heading,service_link,'서비스 안내')}]
    items=[];byid={r['safe_event_id']:r for r in rows}
    for n,(eid,title,summary,label) in enumerate(REVIEWED,1):
        row=byid[eid];url=row['safe_original_url']
        item={'safe_event_id':eid,'number':n,'compact_title':title,'compact_summary':summary,'source_label':label,'source_url':url,'button_title':'원문 보기'}
        items.append(item)
        parts=format_parts(n,title,summary,label)
        for part,text in enumerate(parts,1):
            messages.append({'kind':'article','safe_event_id':eid,'number':n,'part':part,'parts':len(parts),'template':template(text,url,'원문 보기')})
    messages.append({'kind':'overview','source_event_ids':[r['safe_event_id'] for r in rows],'template':template(OVERVIEW,service_link,'서비스 안내')})
    for n,m in enumerate(messages,1):m['sequence']=n
    return {'mode':'PREVIEW_ONLY','input_sha256':INPUT_SHA,'display_date':display_date,'items':items,'messages':messages,'actual_kakao_send_count':0,'scheduled_live_count':0}


def gate(rows,a,display_date,service_link,evidence,unchanged,secrets=()):
    expected=build(rows,display_date,service_link)
    articles=[m for m in a['messages'] if m['kind']=='article']
    checks={'input_and_review_binding':a==expected,'eight_items':len(a['items'])==8,'eight_article_messages':len(articles)==8,'ten_total':len(a['messages'])==10,
        'header_one':sum(m['kind']=='header' for m in a['messages'])==1,'overview_one':sum(m['kind']=='overview' for m in a['messages'])==1,
        'length':all(units(m['template']['text'])<=LIMIT for m in a['messages']),
        'no_body_url':not any(re.search(r'https?://',m['template']['text']) for m in a['messages']),
        'article_links':all(m['template']['link']=={'web_url':next(r['safe_original_url'] for r in rows if r['safe_event_id']==m['safe_event_id']),'mobile_web_url':next(r['safe_original_url'] for r in rows if r['safe_event_id']==m['safe_event_id'])} and m['template']['button_title']=='원문 보기' for m in articles),
        'test_marker_zero':all('[TEST]' not in m['template']['text'] for m in a['messages']),
        'secret_zero':not sensitive(json.dumps(a,ensure_ascii=False),secrets),
        'prior_files_preserved':unchanged is True,'existing_192':evidence['existing'].get('passed') is True and evidence['existing'].get('count')==192,
        'new_tests':evidence['new'].get('passed') is True and evidence['new'].get('count',0)>=25,
        'no_actual_send':a.get('actual_kakao_send_count')==0,'no_scheduled_live':a.get('scheduled_live_count')==0}
    return {'status':'PASS' if all(checks.values()) else 'HOLD','checks':checks,'artifact_sha256':digest(a),'button_validation_scope':'offline structure and approved URL identity only; Kakao registered-domain acceptance NOT tested'}


def run(display_date):
    from news import daily
    rows=load(ROOT);cfg=daily.config();service_link=cfg['KAKAO_LINK_URL']
    known=[v for k,v in cfg.items() if re.search('KEY|TOKEN|SECRET',k)]
    a=build(rows,display_date,service_link)
    evidence={'existing':tests(EXISTING+['news.test_phase3','news.test_phase4'],OUT/'logs/tests_existing.txt'),'new':tests(['news.test_phase5_compact'],OUT/'logs/tests_phase5.txt')}
    (OUT/'logs/tests.txt').write_text((OUT/'logs/tests_existing.txt').read_text(encoding='utf-8')+'\n'+(OUT/'logs/tests_phase5.txt').read_text(encoding='utf-8'),encoding='utf-8')
    q=gate(rows,a,display_date,service_link,evidence,protected(),known)
    write(OUT/'quality/quality_gate.json',q);write(OUT/'quality/test_evidence.json',evidence);write(OUT/'quality/artifact.json',a)
    write(OUT/'compact/compact_items.json',a['items']);write(OUT/'compact/mobile_messages.json',a['messages'])
    preview='\n\n---\n\n'.join(m['template']['text']+'\n\n['+m['template']['button_title']+']('+m['template']['link']['web_url']+')' for m in a['messages'])
    (OUT/'compact/mobile_preview.md').write_text(preview,encoding='utf-8')
    result={'status':q['status'],'existing':evidence['existing']['count'],'new':evidence['new']['count'],'messages':len(a['messages']),'max_utf16':max(units(m['template']['text']) for m in a['messages']),'actual_kakao_send_count':0,'scheduled_live_count':0}
    write(OUT/'logs/run.json',result);print(json.dumps(result))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description='Offline compact preview only; no sending options')
    parser.add_argument('--display-date',default='2026-09-12')
    args=parser.parse_args()
    try:run(args.display_date)
    except Exception as error:
        print(json.dumps({'status':'HOLD','error_type':type(error).__name__,'actual_kakao_send_count':0}))
        raise SystemExit(1)
