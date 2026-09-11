"""Reapply final deterministic Guard to saved responses without paid calls."""
import copy
import json
from collections import Counter
from pathlib import Path

from news.phase1 import write_json
from news.phase21 import verify_input,replay_guard
from news.phase21_guard import calibrated_guard
from news.phase21_events import assemble_events,calibrate_relation
from news.phase2_schema import ANALYSIS,LIMITS,validate_analysis


def recover_model_analysis(checked):
    result=copy.deepcopy(checked['analysis'])
    result['hallucination_risk']=checked['original_model_risk']
    generated=[f"[{f['status']}] {f['output_field']}: {f['value']} — {f['reason']}"[:590]
               for f in checked['fact_check_evidence']]
    targets=result['fact_check_targets']
    for count in range(min(len(targets),len(generated)),0,-1):
        if targets[-count:]==generated[:count]:
            result['fact_check_targets']=targets[:-count]
            break
    return result


def recheck(input_path,output,previous):
    verify_input(input_path)
    rows=json.loads(Path(input_path).read_text(encoding='utf-8'))
    lookup={r['candidate_id']:r for r in rows}
    events=json.loads((output/'events/events.json').read_text(encoding='utf-8'))
    event_map={e['event_id']:e for e in events}
    old=[]
    for name in ('analysis','verify','auto_hold'):
        old+=json.loads((output/f'analysis/{name}.json').read_text(encoding='utf-8'))
    updated=[]
    for checked in old:
        item=recover_model_analysis(checked)
        event=event_map[item['event_id']]
        updated.append(calibrated_guard(item,[lookup[c] for c in event['candidate_ids']]))
    comparison={'method':'Same API outputs; restore original_model_risk and remove only appended guard targets',
        'before':dict(Counter(r['guard_status'] for r in old)),
        'after':dict(Counter(r['guard_status'] for r in updated)),
        'api_calls':0,
        'changes':[{'event_id':a['analysis']['event_id'],'before':a['guard_status'],'after':b['guard_status']}
                   for a,b in zip(old,updated) if a['guard_status']!=b['guard_status']]}
    for name,status in [('analysis','PASS'),('verify','VERIFY'),('auto_hold','AUTO_HOLD')]:
        write_json(output/f'analysis/{name}.json',[r for r in updated if r['guard_status']==status])
    write_json(output/'verification/final_guard_recheck.json',comparison)
    write_json(output/'verification/guard_before_after.json',replay_guard(previous,rows))
    log=json.loads((output/'logs/run.json').read_text(encoding='utf-8'))
    counts=Counter(r['guard_status'] for r in updated)
    log['counts']['guard']={k:counts[k] for k in ('PASS','VERIFY','AUTO_HOLD')}
    log['deterministic_guard_recheck']=comparison
    log['status']='HOLD' if counts['AUTO_HOLD'] else ('WARN' if counts['VERIFY'] or log['warnings'] or log['errors'] else 'PASS')
    write_json(output/'logs/run.json',log)
    before_after=json.loads((output/'verification/dedup_before_after.json').read_text(encoding='utf-8'))
    before_after['after']=log['counts']
    write_json(output/'verification/dedup_before_after.json',before_after)
    return log


def recheck_relations(input_path,output,client):
    verify_input(input_path)
    rows=json.loads(Path(input_path).read_text(encoding='utf-8'))
    lookup={r['candidate_id']:r for r in rows}
    old_decisions=json.loads((output/'events/decisions.json').read_text(encoding='utf-8'))
    decisions=[calibrate_relation(d,lookup) for d in old_decisions]
    events=assemble_events(rows,decisions)
    saved=[]
    for name in ('analysis','verify','auto_hold'):
        saved+=json.loads((output/f'analysis/{name}.json').read_text(encoding='utf-8'))
    cache={r['analysis']['event_id']:r for r in saved}
    results=[]
    new_ids=[]
    for event in events:
        related=[lookup[c] for c in event['candidate_ids']]
        if event['event_id'] in cache:
            model_analysis=recover_model_analysis(cache[event['event_id']])
        else:
            model_analysis=client.generate('ANALYZE: Analyze this event from supplied excerpts ONLY. Return exact event_id. '
                'Use Korean prose and source names; no invented numbers, dates, names or URLs. Score limits: '+json.dumps(LIMITS),
                {'event':event,'articles':related},ANALYSIS,lambda v:validate_analysis(v,event['event_id']))
            new_ids.append(event['event_id'])
        result=calibrated_guard(model_analysis,related)
        validate_analysis(result['analysis'],event['event_id'])
        results.append(result)
    write_json(output/'events/events.json',events)
    write_json(output/'events/decisions.json',decisions)
    for name,status in [('analysis','PASS'),('verify','VERIFY'),('auto_hold','AUTO_HOLD')]:
        write_json(output/f'analysis/{name}.json',[r for r in results if r['guard_status']==status])
    audit={'before_events':len(saved),'after_events':len(events),'new_event_analyses':new_ids,
        'changed_pairs':[{'pair_id':a['pair_id'],'before':a['relation'],'after':b['relation'],'reason':b['reason']}
                         for a,b in zip(old_decisions,decisions) if a['relation']!=b['relation']]}
    write_json(output/'verification/editorial_relation_review.json',audit)
    log=json.loads((output/'logs/run.json').read_text(encoding='utf-8'))
    log['counts']['events']=len(events)
    log['counts']['relations']=dict(Counter(d['relation'] for d in decisions))
    log['counts']['at_least_70']=sum(r['analysis']['scores']['total']>=70 for r in results)
    log['calls']+=client.calls
    write_json(output/'logs/run.json',log)
    return audit
