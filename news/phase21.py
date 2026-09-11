"""Fixed-input TEST rerun; no credential, score or production configuration changes."""
import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from news.phase1 import write_json
from news.phase1_search import secret_found
from news.phase2_events import load_candidates
from news.phase2_gemini import Gemini, load_credentials
from news.phase2_schema import ANALYSIS, LIMITS, Phase2Error, validate_analysis
from news.phase21_events import build_events_hardened
from news.phase21_guard import calibrated_guard

EXPECTED_SHA = '490b4608eb820ed679ee41a6dcfd969f22d032c493837c3ca220eee53d389e40'


def verify_input(path):
    if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=EXPECTED_SHA:
        raise Phase2Error('INPUT_SHA_MISMATCH')


def replay_guard(previous, rows):
    events = json.loads((previous/'events/events.json').read_text(encoding='utf-8'))
    ordinary = json.loads((previous/'analysis/analysis.json').read_text(encoding='utf-8'))
    high = json.loads((previous/'analysis/high_risk.json').read_text(encoding='utf-8'))
    analysis = ordinary+[r['analysis'] for r in high]
    mapping = {e['event_id']:e for e in events}
    lookup = {r['candidate_id']:r for r in rows}
    compared = []
    high_ids = {r['analysis']['event_id'] for r in high}
    for item in analysis:
        event = mapping[item['event_id']]
        checked = calibrated_guard(item,[lookup[c] for c in event['candidate_ids']])
        compared.append({'event_id':event['event_id'],'before':'HOLD' if event['event_id'] in high_ids else 'NORMAL',
            'after':checked['guard_status'],'findings':checked['findings'],
            'risk_provenance':'Legacy high-risk flag may already include old Guard mutation; raw model risk unavailable'})
    return {'method':'Same 50 stored analyses, no Gemini calls; unchanged event membership',
        'before':{'normal':len(ordinary),'hold':len(high)},
        'after':dict(Counter(c['after'] for c in compared)), 'events':compared}


def run(input_path,output,config,previous,mode='TEST',client=None,progress=None):
    log = {'started_at':datetime.now(timezone.utc).isoformat(),'mode':mode,'status':'FAIL',
           'errors':[],'warnings':[],'kakao_calls':0,'tavily_calls':0,'live_runs':0,'input_sha256':None}
    events,decisions,results,rows = [],[],[],[]
    key=''
    try:
        if mode!='TEST':
            raise Phase2Error('TEST_MODE_REQUIRED')
        verify_input(input_path)
        log['input_sha256']=EXPECTED_SHA
        if client is None:
            key,model=load_credentials(config)
            client=Gemini(key,model)
        else:
            key,model=getattr(client,'key',''),getattr(client,'model','fixture')
        log['model']=model
        rows=load_candidates(input_path,(key,))
        replay=replay_guard(previous,rows)
        events,decisions,log['warnings']=build_events_hardened(rows,client,progress)
        lookup={r['candidate_id']:r for r in rows}
        for index,event in enumerate(events):
            try:
                related=[lookup[c] for c in event['candidate_ids']]
                item=client.generate('ANALYZE: Analyze this event from supplied excerpts ONLY. Return exact event_id. '
                    'Score limits: '+json.dumps(LIMITS)+'. Use Korean prose. Retain named entities in source spelling. '
                    'Do not add background dates, quantities, names, URLs or confirmed claims. '
                    'Education/classroom ideas may be null; list uncertainties and fact_check_targets.',
                    {'event':event,'articles':related},ANALYSIS,lambda v:validate_analysis(v,event['event_id']))
                checked=calibrated_guard(item,related)
                validate_analysis(checked['analysis'],event['event_id'])
                results.append(checked)
            except Phase2Error as error:
                log['errors'].append({'event_id':event['event_id'],'code':error.code,'http_status':error.status})
                if error.status in (400,401,403,404) or error.code=='SECRET_DETECTED':
                    raise
            if progress:
                progress({'stage':'analysis','completed':index+1,'total':len(events)})
        counts=Counter(r['guard_status'] for r in results)
        log['counts']={'candidates':len(rows),'events':len(events),'relations':dict(Counter(d['relation'] for d in decisions)),
            'unresolved':sum(w['code']!='LOW_CONFIDENCE' for w in log['warnings']),
            'guard':{k:counts[k] for k in ('PASS','VERIFY','AUTO_HOLD')},
            'at_least_70':sum(r['analysis']['scores']['total']>=70 for r in results)}
        log['status']='HOLD' if counts['AUTO_HOLD'] else ('WARN' if counts['VERIFY'] or log['warnings'] or log['errors'] else 'PASS')
        if not results:
            log['status']='FAIL'
        payloads={'events/events.json':events,'events/decisions.json':decisions,
            'analysis/analysis.json':[r for r in results if r['guard_status']=='PASS'],
            'analysis/verify.json':[r for r in results if r['guard_status']=='VERIFY'],
            'analysis/auto_hold.json':[r for r in results if r['guard_status']=='AUTO_HOLD'],
            'verification/guard_before_after.json':replay,
            'verification/dedup_before_after.json':{'before':{'candidates':57,'events':50,'same_event':13,'unresolved':8},'after':log['counts']}}
    except Phase2Error as error:
        log['errors'].append({'code':error.code,'http_status':error.status})
        log['status']='HOLD' if error.code in ('INPUT_SHA_MISMATCH','SECRET_DETECTED') else 'FAIL'
        payloads={}
    except Exception:
        log['errors'].append({'code':'PHASE21_INTERNAL_ERROR'})
        log['status']='FAIL'
        payloads={}
    log['calls']=getattr(client,'calls',[])
    log['finished_at']=datetime.now(timezone.utc).isoformat()
    if secret_found([payloads,log],(key,)):
        log={'status':'HOLD','errors':[{'code':'SECRET_DETECTED'}]}
        payloads={}
    for name,value in payloads.items():
        write_json(output/name,value)
    write_json(output/'logs/run.json',log)
    return log


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--previous',type=Path,required=True)
    parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('--output',type=Path,default=Path('outputs/phase2_1'))
    parser.add_argument('--mode',choices=['TEST'],default='TEST')
    args=parser.parse_args()
    try:
        log=run(args.input,args.output,args.config,args.previous,args.mode,
                progress=lambda v:print(json.dumps(v),flush=True))
        print(json.dumps({'status':log['status'],'counts':log.get('counts')},ensure_ascii=False))
        return 0 if log['status'] in ('PASS','WARN') else 1
    except OSError:
        print('FAIL: OUTPUT_WRITE_ERROR')
        return 1


if __name__=='__main__':
    raise SystemExit(main())
