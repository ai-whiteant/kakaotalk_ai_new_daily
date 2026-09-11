"""Pair-isolated dedup with extractive evidence enums and related event links."""
import copy
import hashlib
import itertools
import re
import unicodedata

from news.phase2_events import pair_candidates, source_rank, anchors
from news.phase2_schema import DECISION, EVENT, Phase2Error, obj, validate


def evidence_options(row):
    options = [row['title'][:480]]
    options += re.split(r'(?<=[.!?。])\s+|\n+', row['snippet'])
    # Long snippets are split into exact substrings; never paraphrase evidence.
    result = []
    for option in options:
        for start in range(0, min(len(option), 1920), 480):
            part = option[start:start+480].strip()
            if len(part)>=8 and part not in result:
                result.append(part)
    return result[:8]


def event_schema():
    schema = copy.deepcopy(EVENT)
    schema['properties']['related_events'] = {'type':'array', 'items':obj({
        'event_id': {'type':'string'}, 'relation': {'enum':['FOLLOW_UP']},
        'confidence': {'type':'number','minimum':0,'maximum':1},
        'pair_ids': {'type':'array','items':{'type':'string'}}})}
    schema['required'].append('related_events')
    return schema


def calibrate_relation(decision,lookup):
    decision=copy.deepcopy(decision)
    editorial=re.compile(r'\bopinion\b|what experts say|봐야 할 것|\[아침을 열며\]',re.I)
    left=bool(editorial.search(lookup[decision['left_id']]['title']))
    right=bool(editorial.search(lookup[decision['right_id']]['title']))
    if decision['relation']=='SAME_EVENT' and left!=right:
        decision['relation']='FOLLOW_UP'
        decision['reason']='Editorial/reaction versus originating report: preserve related events separately. Original model SAME_EVENT. '+decision['reason']
    return decision


def build_events_hardened(rows, client, progress=None):
    lookup = {r['candidate_id']:r for r in rows}
    rules, ambiguous = pair_candidates(rows)
    decisions = [dict(p, relation='SAME_EVENT',confidence=1.0,method='RULE',reason='Identical title and snippet',
                     left_evidence=lookup[p['left_id']]['title'],right_evidence=lookup[p['right_id']]['title']) for p in rules]
    warnings = []
    for index,pair in enumerate(ambiguous):
        left,right = lookup[pair['left_id']],lookup[pair['right_id']]
        le,re_ = evidence_options(left),evidence_options(right)
        if not le or not re_:
            warnings.append({'code':'EVIDENCE_UNAVAILABLE','pair_id':pair['pair_id']})
            continue
        schema = copy.deepcopy(DECISION)
        schema['properties']['pair_id']={'enum':[pair['pair_id']]}
        schema['properties']['representative_source_preference']={'enum':[pair['left_id'],pair['right_id']]}
        schema['properties']['left_evidence']={'type':'string','enum':le}
        schema['properties']['right_evidence']={'type':'string','enum':re_}
        schema['properties']['left_id']={'enum':[pair['left_id']]}
        schema['properties']['right_id']={'enum':[pair['right_id']]}
        schema['required'] += ['left_id','right_id']
        def check(value):
            # Validate even injected test clients; only exact supplied evidence can authorize a merge.
            validate(value,schema)
            for field,row in [('left_evidence',left),('right_evidence',right)]:
                if value[field] not in row['title'] and value[field] not in row['snippet']:
                    raise Phase2Error('DEDUP_EVIDENCE_INVALID')
        try:
            value = client.generate('DEDUP: Compare ONE pair. SAME_EVENT requires the same actor, action, object '
                '(model/policy/product), place/target and originating occurrence. Same organization/topic is insufficient. '
                'FOLLOW_UP for subsequent reactions, recovery, consequences or commentary; keep separate but related. '
                'DIFFERENT_EVENT for a different model/policy/announcement. Distinct named models or policies must not merge. '
                'Quote only one of the provided verbatim evidence options from each side. Explain action/object/date evidence '
                'and contradictions in reason. Return exact pair and candidate IDs. Confidence below 0.9 cannot authorize merge.',
                {'pair_id':pair['pair_id'],'left':left,'right':right,'left_evidence_options':le,'right_evidence_options':re_},schema,check)
            decisions.append(calibrate_relation(dict(value,method='GEMINI'),lookup))
            if value['confidence']<0.9:
                warnings.append({'code':'LOW_CONFIDENCE','pair_id':pair['pair_id']})
        except Phase2Error as error:
            if error.status in (400,401,403,404) or error.code=='SECRET_DETECTED':
                raise
            warnings.append({'code':error.code,'pair_id':pair['pair_id']})
        if progress:
            progress({'stage':'dedup','completed':index+1,'total':len(ambiguous)})
    return assemble_events(rows,decisions),decisions,warnings


def assemble_events(rows,decisions):
    lookup={r['candidate_id']:r for r in rows}
    same = {frozenset((d['left_id'],d['right_id'])):d for d in decisions
            if d['relation']=='SAME_EVENT' and d['confidence']>=0.9}
    groups = []
    for row in rows:
        found = next((g for g in groups if all(frozenset((row['candidate_id'],cid)) in same for cid in g)),None)
        if found is None:
            groups.append([row['candidate_id']])
        else:
            found.append(row['candidate_id'])
    events = []
    for group in groups:
        members = sorted([lookup[c] for c in group],key=lambda r:(source_rank(r),r['candidate_id']))
        def source(row):
            return {k:row[k] for k in ('candidate_id','title','url','source_name','published_at')}
        edges = [same[frozenset(p)] for p in itertools.combinations(group,2)]
        events.append({'event_id':'evt_'+hashlib.sha256('|'.join(sorted(group)).encode()).hexdigest()[:20],
            'canonical_title':members[0]['title'],'category_hint':members[0]['category_hint'],'candidate_ids':sorted(group),
            'primary_source':source(members[0]),'supporting_sources':[source(r) for r in members[1:]],
            'entities':sorted(set().union(*(anchors(r) for r in members))),'event_date':None,
            'dedup_status':'SINGLE' if not edges else ('GEMINI' if any(e['method']=='GEMINI' for e in edges) else 'RULE'),
            'dedup_confidence':min((e['confidence'] for e in edges),default=1.0),'related_events':[]})
    mapping = {cid:event for event in events for cid in event['candidate_ids']}
    for decision in decisions:
        if decision['relation']=='FOLLOW_UP':
            a,b = mapping[decision['left_id']],mapping[decision['right_id']]
            if a is b:
                raise Phase2Error('FOLLOW_UP_OVERMERGE')
            # Undirected relation: no chronological direction is invented.
            for source,target in ((a,b),(b,a)):
                link = next((r for r in source['related_events'] if r['event_id']==target['event_id']),None)
                if link:
                    link['pair_ids'].append(decision['pair_id'])
                else:
                    source['related_events'].append({'event_id':target['event_id'],'relation':'FOLLOW_UP',
                        'confidence':decision['confidence'],'pair_ids':[decision['pair_id']]})
    for event in events:
        validate(event,event_schema())
    return events
