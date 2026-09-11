"""Offline final-candidate gate over immutable Phase 1/2.1/2.2 inputs.

Source-specific semantic decisions are reviewed evidence data. This module
enforces completeness, provenance, selection, and export boundaries; it does
not infer truth from a model's memory or contact any service.
"""
import argparse
import copy
import hashlib
from collections import Counter
from datetime import datetime
from pathlib import Path

from news.phase22 import read, write, verify_inputs
from news.phase22_evidence import digest, public_url

STATES = ('FINAL_VERIFIED', 'FINAL_VERIFIED_WITH_CONTEXT', 'FINAL_HOLD', 'FINAL_REJECT')
GOOD = ('SUPPORTED', 'EQUIVALENT', 'CONTEXTUAL')
CLAIM_STATES = GOOD + ('UNRESOLVED', 'UNSUPPORTED', 'CONTRADICTED')
FIELDS = ('safe_title', 'safe_summary', 'safe_why_it_matters',
          'safe_education_implication', 'safe_classroom_use')
CHECKS = ('title', 'publication_date', 'event_date', 'entities', 'models', 'numbers',
          'policy', 'official_announcement', 'core_claims', 'why_it_matters',
          'education_implication', 'classroom_use', 'final_url')
START = datetime.fromisoformat('2026-09-02T12:30:20.056320+00:00')
END = datetime.fromisoformat('2026-09-09T12:30:20.056320+00:00')


def rank_candidates(candidates):
    if len({c['event_id'] for c in candidates}) != len(candidates):
        raise ValueError('Duplicate event')
    # Original threshold is a priority tier, never replaced by adjusted scores.
    ordered = sorted(copy.deepcopy(candidates), key=lambda c: (
        -int(c['original_score'] >= 70), -(c['original_score'] + c['selection_adjustment']),
        -c['education_score'], -c['source_score'], -c['recency_score'], c['event_id']))
    for i, c in enumerate(ordered, 1):
        c['selection_rank'] = i
    return ordered


def select(candidates, limit=15):
    if not 12 <= limit <= 15:
        raise ValueError('Preselection must be 12..15')
    result, groups = [], set()
    for c in rank_candidates(candidates):
        if c['origin_state'] not in ('PASS', 'VERIFIED_WITH_CONTEXT'):
            continue
        if not c['eligible'] or c['duplicate_group'] in groups or not public_url(c['original_url']):
            continue
        result.append(c)
        groups.add(c['duplicate_group'])
        if len(result) == limit:
            break
    return result


def rescue_order(excluded, verified_count, used_groups=()):
    if verified_count >= 8:
        return []
    return sorted([copy.deepcopy(c) for c in excluded if c['origin_state'] == 'VERIFICATION_HOLD'
                   and c['duplicate_group'] not in used_groups],
                  key=lambda c: (-c['original_score'], c['event_id']))


def validate_registry(sources):
    registry = {}
    for s in sources:
        if s['source_id'] in registry or not public_url(s['url']):
            raise ValueError('Invalid source URL/id')
        if s['verification_only'] is not True or s['access'] not in ('body', 'failed', 'partial'):
            raise ValueError('Source access/scope')
        if s['source_type'] not in ('official', 'research', 'major_media', 'specialist', 'other'):
            raise ValueError('Source type')
        if digest(s['notes']) != s['notes_sha256'] or not s['locator']:
            raise ValueError('Source note integrity')
        if datetime.fromisoformat(s['retrieved_at']).tzinfo is None:
            raise ValueError('Source timestamp')
        registry[s['source_id']] = s
    return registry


def verify(candidate, review, sources):
    if review['event_id'] != candidate['event_id'] or review['candidate_sha256'] != digest(candidate):
        raise ValueError('Candidate binding mismatch')
    result = copy.deepcopy(review)
    reasons = list(review.get('hold_reasons', []))
    if candidate['origin_state'] == 'REJECT':
        raise ValueError('REJECT reentry forbidden')
    claims = review['verified_claims']
    if len({c['claim_id'] for c in claims}) != len(claims):
        raise ValueError('Duplicate claim')
    lookup = {c['claim_id']: c for c in claims}
    for c in claims:
        if c['status'] not in CLAIM_STATES or type(c['core']) is not bool or not c['reason']:
            raise ValueError('Claim status/reason')
        if c['status'] != 'UNRESOLVED':
            if not c['source_ids'] or not c.get('semantic_review'):
                reasons.append('MISSING_CLAIM_EVIDENCE')
            for sid in c['source_ids']:
                if sources[sid]['access'] != 'body' or sources[sid]['source_type'] == 'other':
                    reasons.append('NO_RELIABLE_BODY')
        if c['core'] and c['status'] == 'UNRESOLVED':
            reasons.append('UNRESOLVED_CORE')
    checks = review['coverage']
    if set(checks) != set(CHECKS):
        reasons.append('INCOMPLETE_COVERAGE')
    for key, check in checks.items():
        if check['status'] not in ('CHECKED', 'NOT_APPLICABLE', 'UNRESOLVED') or not check['reason']:
            raise ValueError('Invalid coverage check')
        if check['status'] == 'UNRESOLVED':
            reasons.append('UNCHECKED_' + key)
        if key in ('title', 'publication_date', 'event_date', 'core_claims', 'final_url') and check['status'] != 'CHECKED':
            reasons.append('REQUIRED_' + key)
        for cid in check['claim_ids']:
            if cid not in lookup:
                raise ValueError('Unknown coverage claim')
        if check['status'] == 'CHECKED' and not check['claim_ids']:
            reasons.append('COVERAGE_WITHOUT_EVIDENCE_' + key)
    final_sid = review.get('final_source_id')
    if final_sid not in sources or sources[final_sid]['access'] != 'body' or sources[final_sid]['source_type'] == 'other':
        reasons.append('FINAL_URL_UNVERIFIED')
    if not review.get('freshness_review'):
        reasons.append('FRESHNESS_NOT_REVIEWED')
    interval = review.get('publication_interval')
    if not interval or len(interval) != 2:
        reasons.append('PUBLICATION_DATE_MISSING')
    else:
        low, high = map(datetime.fromisoformat, interval)
        if low.tzinfo is None or high.tzinfo is None or low > high or low < START or high > END:
            reasons.append('PUBLICATION_OUTSIDE_FIXED_WINDOW_OR_AMBIGUOUS')
    if candidate['original_score'] < 70 and not review.get('importance_exception'):
        reasons.append('BELOW_70_WITHOUT_IMPORTANCE_REASON')
    for field in FIELDS:
        value = review[field]
        assessment = review['field_reviews'][field]
        if assessment['text_sha256'] != digest(value):
            raise ValueError('Safe text changed after review')
        if value is None:
            if field in FIELDS[:3]:
                reasons.append('REQUIRED_SAFE_FIELD_EMPTY')
            continue
        if not value or not assessment['reviewed'] or not assessment['reason']:
            reasons.append('SAFE_FIELD_UNREVIEWED')
        if not assessment['claim_ids'] or any(lookup[c]['status'] not in GOOD for c in assessment['claim_ids']):
            reasons.append('SAFE_FIELD_UNSUPPORTED')
        if field in FIELDS[2:] and not assessment['interpretation_or_suggestion']:
            reasons.append('INTERPRETATION_NOT_LABELLED')
        if field in FIELDS[3:] and any(x in value for x in ('효과가 입증', '반드시 향상', '성적을 보장', '모든 학생에게 효과')):
            reasons.append('EDUCATION_OVERCLAIM')
    if any(c['core'] and c['status'] in ('UNSUPPORTED', 'CONTRADICTED') for c in claims) or review.get('reject_reason'):
        state = 'FINAL_REJECT'
    elif reasons:
        state = 'FINAL_HOLD'
    elif review.get('context_changed') or any(c['status'] not in ('SUPPORTED', 'EQUIVALENT') for c in claims):
        state = 'FINAL_VERIFIED_WITH_CONTEXT'
    else:
        state = 'FINAL_VERIFIED'
    result.update(verification_status=state, gate_reasons=sorted(set(reasons)),
                  selection_rank=candidate['selection_rank'], original_score=candidate['original_score'],
                  selection_adjustment=candidate['selection_adjustment'], category=candidate['category'],
                  duplicate_group=candidate['duplicate_group'], guard_original=candidate['guard_original'],
                  origin_state=candidate['origin_state'], original_url=candidate['original_url'],
                  final_url=sources[final_sid]['url'] if final_sid in sources else None,
                  dispatch_allowed=False)
    for c in result['verified_claims']:
        c['evidence_urls'] = [sources[s]['url'] for s in c['source_ids']]
    return result


def export_safe(records):
    result, groups = [], set()
    for r in records:
        if r['verification_status'] not in STATES[:2]:
            continue
        if r['duplicate_group'] in groups:
            raise ValueError('Final duplicate group')
        groups.add(r['duplicate_group'])
        if not public_url(r['final_url']):
            raise ValueError('Final URL')
        if any(digest(r[f]) != r['field_reviews'][f]['text_sha256'] for f in FIELDS):
            raise ValueError('Export text changed after review')
        if any(c['core'] and c['status'] not in GOOD for c in r['verified_claims']):
            raise ValueError('Unsafe core claim at export')
        result.append({**{f: r[f] for f in FIELDS}, 'safe_event_id': r['event_id'],
                       'safe_original_url': r['final_url'], 'safe_category': r['category']})
    if len(result) > 12:
        raise ValueError('Final pool exceeds 12; explicit value selection required')
    return result


def run(repo, packet_path, output, mode='TEST'):
    if mode != 'TEST':
        raise ValueError('TEST only')
    p = read(packet_path)
    verify_inputs(repo, p['input_hashes'])
    required = {'outputs/phase2_1/events/events.json', 'outputs/phase2_1/analysis/analysis.json',
                'outputs/phase2_2/analysis/verified_with_context.json',
                'outputs/phase2_2/analysis/verification_hold.json', 'outputs/phase2_2/analysis/reject.json'}
    if not required <= p['input_hashes'].keys():
        raise ValueError('Input manifest incomplete')
    original = {}
    for n in ('analysis', 'verify', 'auto_hold'):
        original.update({r['analysis']['event_id']: r for r in read(repo / f'outputs/phase2_1/analysis/{n}.json')})
    states = {k: 'PASS' for k, r in original.items() if r['guard_status'] == 'PASS'}
    for n, state in [('verified_with_context', 'VERIFIED_WITH_CONTEXT'), ('verification_hold', 'VERIFICATION_HOLD'), ('reject', 'REJECT')]:
        states.update({r['event_id']: state for r in read(repo / f'outputs/phase2_2/analysis/{n}.json')})
    if Counter(states.values()) != {'PASS': 28, 'VERIFIED_WITH_CONTEXT': 3, 'VERIFICATION_HOLD': 17, 'REJECT': 1}:
        raise ValueError('Pool baseline mismatch')
    pool = p['candidates'] + p['excluded_pool']
    if len(pool) != 49 or {c['event_id'] for c in pool} != set(states):
        raise ValueError('Pool membership mismatch')
    for c in pool:
        old = original[c['event_id']]
        if c['origin_state'] != states[c['event_id']] or c['original_record_sha256'] != digest(old) or c['original_score'] != old['analysis']['scores']['total']:
            raise ValueError('Original state/score mismatch')
        if c['original_scores'] != old['analysis']['scores'] or c['category'] != old['analysis']['category']:
            raise ValueError('Original score components/category changed')
    if len(p['candidates']) != 31 or len(p['excluded_pool']) != 18:
        raise ValueError('Pool partition mismatch')
    sources = validate_registry(p['sources'])
    pre = select(p['candidates'])
    if not 12 <= len(pre) <= 15:
        raise ValueError('Insufficient eligible preliminary candidates')
    reviews = {r['event_id']: r for r in p['reviews']}
    if len(reviews) != len(p['reviews']):
        raise ValueError('Duplicate review')
    records = [verify(c, reviews[c['event_id']], sources) for c in pre]
    used = {r['duplicate_group'] for r in records if r['verification_status'] in STATES[:2]}
    rescue = []
    for c in rescue_order(p['excluded_pool'], sum(r['verification_status'] in STATES[:2] for r in records), used):
        if c['event_id'] not in reviews:
            rescue.append({'event_id': c['event_id'], 'result': 'PENDING_REVIEW'})
            break
        c['selection_rank'] = len(records) + 1
        record = verify(c, reviews[c['event_id']], sources)
        records.append(record)
        rescue.append({'event_id': c['event_id'], 'result': record['verification_status']})
        if sum(r['verification_status'] in STATES[:2] for r in records) >= 8:
            break
    final = export_safe(records)
    for name, data in [('selection/ranked_pool.json', rank_candidates(p['candidates'])),
                       ('selection/pre_candidates.json', pre), ('selection/excluded_pool.json', p['excluded_pool']),
                       ('selection/rescue_audit.json', rescue), ('selection/final_candidates.json', final),
                       ('verification/final_verification_records.json', records),
                       ('verification/source_registry.json', p['sources']),
                       ('verification/before_after.json', {'before': dict(Counter(states.values())),
                        'after_reviewed': dict(Counter(r['verification_status'] for r in records)), 'final_count': len(final)})]:
        write(output / name, data)
    verify_inputs(repo, p['input_hashes'])
    outcome = {'mode': 'TEST', 'gate_candidate': 'PASS' if len(final) >= 8 else 'HOLD',
               'status': 'WARN' if len(final) >= 8 else 'HOLD', 'independent_review': 'PENDING',
               'pre_candidates': len(pre), 'final_count': len(final),
               'tavily_calls': 0, 'gemini_calls': 0, 'kakao_calls': 0, 'live_runs': 0,
               'packet_sha256': hashlib.sha256(packet_path.read_bytes()).hexdigest()}
    write(output / 'logs/run.json', outcome)
    return outcome


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--packet', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=Path('outputs/phase2_3'))
    args = parser.parse_args()
    print(run(Path.cwd(), args.packet, args.output))
