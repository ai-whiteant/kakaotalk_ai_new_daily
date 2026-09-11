"""Conservative event grouping. Ambiguous/follow-up stories remain separate."""
import hashlib
import copy
import itertools
import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

from news.phase1_search import canonical_url, secret_found
from news.phase2_schema import CANDIDATE, DECISION, EVENT, Phase2Error, obj, validate

ALIASES = {'뉴욕': 'newyork', 'new york': 'newyork', 'nyc': 'newyork',
           '네이버': 'naver', '삼성': 'samsung', '미스트랄': 'mistral', '중국': 'china',
           '엔비디아': 'nvidia', '오픈ai': 'openai', '오픈에이아이': 'openai',
           '구글': 'google', '마이크로소프트': 'microsoft', '클로드': 'claude', '제미나이': 'gemini'}
ANCHORS = ('newyork', 'naver', 'samsung', 'mistral', 'china', 'nvidia', 'openai', 'google',
           'microsoft', 'claude', 'gemini', 'chatgpt', 'grok', 'deepseek', 'asml', 'tsmc')
STOP = {'the', 'and', 'for', 'with', 'that', 'this', 'from', 'news', 'ai', 'artificial', 'intelligence'}


def norm(text):
    text = text.casefold()
    for key, value in ALIASES.items():
        text = text.replace(key, value)
    return ' '.join(re.findall(r'[\w]+', text))


def load_candidates(path, secrets=()):
    try:
        rows = json.loads(Path(path).read_text(encoding='utf-8'))
        if not isinstance(rows, list) or not 1 <= len(rows) <= 200:
            raise Phase2Error('INPUT_SIZE_INVALID')
        if secret_found(rows, secrets):
            raise Phase2Error('SECRET_DETECTED')
        for row in rows:
            validate(row, CANDIDATE)
            canonical_url(row['url'])
        if len({r['candidate_id'] for r in rows}) != len(rows) or len({r['url'] for r in rows}) != len(rows):
            raise Phase2Error('INPUT_DUPLICATES')
        return rows
    except (OSError, ValueError, TypeError):
        raise Phase2Error('INPUT_INVALID') from None


def article_text(row):
    return row['title'] + '\n' + row['snippet'] + '\n' + (row['raw_content'] or '')


def anchors(row):
    text = norm(row['title'])
    return {name for name in ANCHORS if name in text}


def close_dates(a, b):
    if not a['published_at'] or not b['published_at']:
        return False
    return abs((datetime.fromisoformat(a['published_at']) - datetime.fromisoformat(b['published_at'])).total_seconds()) <= 172800


def pair_candidates(rows):
    rules, ambiguous = [], []
    for a, b in itertools.combinations(rows, 2):
        if not close_dates(a, b):
            continue
        left, right = norm(a['title']), norm(b['title'])
        # Matching title alone may be a recurring headline; require identical nonempty snippet.
        pair = {'pair_id': hashlib.sha256((a['candidate_id']+'|'+b['candidate_id']).encode()).hexdigest()[:20],
                'left_id': a['candidate_id'], 'right_id': b['candidate_id']}
        if left == right and len(left) >= 20 and a['snippet'] and norm(a['snippet']) == norm(b['snippet']):
            rules.append(pair)
            continue
        x, y = set(left.split())-STOP, set(right.split())-STOP
        shared = len(x & y) / max(1, len(x | y))
        if anchors(a) & anchors(b) or (shared >= 0.22 and len(x & y) >= 2):
            ambiguous.append(pair)
    return rules, ambiguous


def source_rank(row):
    host = urlsplit(row['url']).hostname.lower()
    def domain(names):
        return any(host == name or host.endswith('.'+name) for name in names)
    if host.endswith(('.gov', '.go.kr', '.edu', '.ac.kr')) or domain(
            ['openai.com', 'ai.google', 'microsoft.com', 'anthropic.com', 'nvidia.com', 'samsung.com', 'navercorp.com']):
        return 0
    if domain(['reuters.com', 'apnews.com', 'bbc.com', 'yonhapnews.co.kr', 'koreaherald.com']):
        return 1
    if domain(['zdnet.co.kr', 'zdnet.com', 'techcrunch.com', 'theverge.com', 'wired.com']):
        return 2
    return 3


def build_events(rows, client, max_pairs=120):
    lookup = {r['candidate_id']: r for r in rows}
    rules, pairs = pair_candidates(rows)
    decisions = [dict(p, relation='SAME_EVENT', confidence=1.0, method='RULE', reason='identical title and snippet') for p in rules]
    warnings = []
    if len(pairs) > max_pairs:
        warnings.append({'code': 'DEDUP_PAIR_LIMIT', 'unresolved_pairs': len(pairs)-max_pairs})
    for offset in range(0, min(len(pairs), max_pairs), 8):
        batch = pairs[offset:min(offset+8, max_pairs)]
        evidence = [{'pair_id': p['pair_id'], 'left': lookup[p['left_id']], 'right': lookup[p['right_id']]} for p in batch]
        decision_schema = copy.deepcopy(DECISION)
        decision_schema['properties']['pair_id']['enum'] = [p['pair_id'] for p in batch]
        decision_schema['properties']['representative_source_preference'] = {
            'type': 'string', 'enum': sorted({p[k] for p in batch for k in ('left_id', 'right_id')}),
            'description': 'Exact candidate_id of the preferred article from this pair, never a source name or explanation.'}
        schema = obj({'decisions': {'type': 'array', 'items': decision_schema, 'minItems': len(batch), 'maxItems': len(batch)}})
        def check(value):
            if {d['pair_id'] for d in value['decisions']} != {p['pair_id'] for p in batch}:
                raise Phase2Error('PAIR_ID_MISMATCH')
            for decision in value['decisions']:
                pair = next(p for p in batch if p['pair_id'] == decision['pair_id'])
                if decision['representative_source_preference'] not in (pair['left_id'], pair['right_id']):
                    raise Phase2Error('REPRESENTATIVE_ID_INVALID')
                if decision['relation'] == 'SAME_EVENT':
                    for side in ('left', 'right'):
                        quote = decision[side+'_evidence']
                        if len(quote.strip()) < 8 or quote not in article_text(lookup[pair[side+'_id']]):
                            raise Phase2Error('DEDUP_EVIDENCE_INVALID')
        try:
            result = client.generate('DEDUP: Classify each pair as SAME_EVENT, FOLLOW_UP or DIFFERENT_EVENT. '
                'Same company/topic alone is insufficient. Distinct products, dates, changes of status and commentary '
                'are not automatically the same event. For SAME_EVENT quote exact supporting text from each input. '
                'representative_source_preference MUST be the exact left.candidate_id or right.candidate_id, not its name. '
                'Use confidence conservatively; prefer separation when uncertain. Return all pair_ids once.', evidence, schema, check)
            for decision in result['decisions']:
                pair = next(p for p in batch if p['pair_id'] == decision['pair_id'])
                decisions.append(dict(pair, **{k: v for k, v in decision.items() if k != 'pair_id'}, method='GEMINI'))
                if decision['confidence'] < 0.9:
                    warnings.append({'code': 'DEDUP_LOW_CONFIDENCE', 'pair_id': pair['pair_id']})
        except Phase2Error as error:
            if error.status in (400, 401, 403, 404) or error.code == 'SECRET_DETECTED':
                raise
            warnings.append({'code': error.code, 'pair_ids': [p['pair_id'] for p in batch]})
    same = {frozenset((d['left_id'], d['right_id'])): d for d in decisions
            if d['relation'] == 'SAME_EVENT' and d['confidence'] >= 0.9}
    groups = []
    for row in rows:
        # Complete-link avoids transitive A-B-C merging when A-C is unknown/follow-up.
        group = next((g for g in groups if all(frozenset((row['candidate_id'], m)) in same for m in g)), None)
        if group is None:
            groups.append([row['candidate_id']])
        else:
            group.append(row['candidate_id'])
    events = []
    for group in groups:
        members = sorted((lookup[c] for c in group), key=lambda r: (source_rank(r), r['candidate_id']))
        def source(row):
            return {k: row[k] for k in ('candidate_id', 'title', 'url', 'source_name', 'published_at')}
        edges = [same[frozenset(pair)] for pair in itertools.combinations(group, 2)]
        event = {'event_id': 'evt_'+hashlib.sha256('|'.join(sorted(group)).encode()).hexdigest()[:20],
            'canonical_title': members[0]['title'], 'category_hint': members[0]['category_hint'],
            'candidate_ids': sorted(group), 'primary_source': source(members[0]),
            'supporting_sources': [source(r) for r in members[1:]],
            'entities': sorted(set().union(*(anchors(r) for r in members))),
            # Publication date is not event date. Do not manufacture the latter.
            'event_date': None, 'dedup_status': 'SINGLE' if not edges else
                ('GEMINI' if any(e['method']=='GEMINI' for e in edges) else 'RULE'),
            'dedup_confidence': min((e['confidence'] for e in edges), default=1.0)}
        validate(event, EVENT)
        events.append(event)
    return events, decisions, warnings
