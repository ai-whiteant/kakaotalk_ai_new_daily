"""Evidence review gate. Does not search, call models, send, or alter Guard.

Semantic judgements are explicitly reviewed data, never inferred from a token
match or a model's memory. Missing/partial evidence fails closed. An independent
review remains necessary; these checks validate traceability, not truth itself.
"""
import copy
import hashlib
import ipaddress
import json
from datetime import datetime
from urllib.parse import urlsplit

CLAIM_STATES = (
    'VERIFIED_SUPPORTED', 'VERIFIED_EQUIVALENT', 'VERIFIED_CONTEXTUAL',
    'UNRESOLVED', 'VERIFIED_UNSUPPORTED', 'CONTRADICTED',
)
GOOD = frozenset(CLAIM_STATES[:3])
BAD = frozenset(CLAIM_STATES[4:])
EVENT_STATES = ('VERIFIED_PASS', 'VERIFIED_WITH_CONTEXT', 'VERIFICATION_HOLD', 'REJECT')
RANK = {'official': 0, 'research': 1, 'major_media': 2, 'specialist': 3, 'other': 4}


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':')).encode()).hexdigest()


def public_url(value):
    """Structural validation only. Existence is separately evidenced by retrieval."""
    try:
        p = urlsplit(value)
        if p.scheme != 'https' or not p.hostname or p.username or p.password:
            return False
        if p.port not in (None, 443) or p.fragment:
            return False
        host = p.hostname.lower()
        if host == 'localhost' or host.endswith(('.local', '.internal')):
            return False
        try:
            return ipaddress.ip_address(host).is_global
        except ValueError:
            return '.' in host
    except (ValueError, TypeError):
        return False


def timestamp(value):
    return isinstance(value, str) and datetime.fromisoformat(value).tzinfo is not None


def validate_sources(sources):
    registry = {}
    for source in sources:
        sid = source['source_id']
        if sid in registry or not public_url(source['url']):
            raise ValueError('Invalid/duplicate source')
        if source['source_type'] not in RANK or not timestamp(source['retrieved_at']):
            raise ValueError('Invalid source metadata')
        if source['verification_only'] is not True:
            raise ValueError('Verification sources must not enter candidate collection')
        if source['access'] not in ('body', 'failed', 'snippet_only', 'partial'):
            raise ValueError('Invalid access classification')
        if source['evidence_sha256'] != digest(source['notes']):
            raise ValueError('Evidence note integrity mismatch')
        if any(not isinstance(x, str) or not x or len(x) > 900 for x in source['notes']):
            raise ValueError('Evidence must be short reviewed notes')
        registry[sid] = source
    return registry


def adjudicate(claim, registry):
    """Retain requested disposition and audit any failed evidence precondition."""
    c = copy.deepcopy(claim)
    if c['requested_status'] not in CLAIM_STATES:
        raise ValueError('Invalid claim status')
    if type(c['core']) is not bool or not c['reason'] or not c['claim']:
        raise ValueError('Claim classification/reason missing')
    if c['claim_type'] not in ('number', 'date', 'entity', 'model', 'policy', 'url', 'event_claim', 'other'):
        raise ValueError('Invalid claim type')
    if not timestamp(c['checked_at']):
        raise ValueError('Claim timestamp missing')
    evidence = []
    for ref in c['evidence_refs']:
        s = registry[ref['source_id']]
        note = s['notes'][ref['note_index']]
        evidence.append({'source_id': s['source_id'], 'source_url': s['url'],
                         'source_name': s['source_name'], 'source_type': s['source_type'],
                         'evidence_text': note, 'locator': s['locator'],
                         'access': s['access'], 'candidate_id': s.get('candidate_id')})
    evidence.sort(key=lambda e: RANK[e['source_type']])
    c['evidence'] = evidence
    status = c['requested_status']
    blocks = []
    body = [e for e in evidence if e['access'] == 'body' and e['source_type'] != 'other']
    if status != 'UNRESOLVED' and (not body or not c.get('reviewed_by')):
        blocks.append('NO_REVIEWED_RELIABLE_BODY_EVIDENCE')
    if status in GOOD and not c.get('semantic_review'):
        blocks.append('NO_CLAIM_SPECIFIC_SEMANTIC_REVIEW')
    if status == 'VERIFIED_EQUIVALENT' and not c.get('equivalence_context'):
        blocks.append('EQUIVALENCE_CONTEXT_REQUIRED')
    if status == 'VERIFIED_CONTEXTUAL' and not c.get('replacement'):
        blocks.append('CONTEXT_REWRITE_REQUIRED')
    if status == 'VERIFIED_UNSUPPORTED' and not c.get('absence_review'):
        blocks.append('ABSENCE_IS_NOT_ESTABLISHED_BY_SEARCH_FAILURE')
    if status == 'CONTRADICTED' and not c.get('contradicting_fact'):
        blocks.append('EXPLICIT_CONTRADICTION_REQUIRED')
    if c.get('conflict') and not c.get('conflict_resolution'):
        blocks.append('SOURCE_CONFLICT_UNRESOLVED')
    if c['claim_type'] == 'url' and status in GOOD:
        urls = {e['source_url'] for e in body}
        if c.get('url_value') not in urls:
            blocks.append('URL_NOT_ACTUALLY_RETRIEVED')
    c['verification_status'] = 'UNRESOLVED' if blocks else status
    c['validation_blocks'] = blocks
    return c


def verify_event(original, review, registry):
    event_id = original['analysis']['event_id']
    if review['event_id'] != event_id:
        raise ValueError('Event mismatch')
    if review.get('original_record_sha256') != digest(original):
        raise ValueError('Original record integrity mismatch')
    targets = original['analysis']['fact_check_targets']
    claims = review['claims']
    if not claims or len({c['target_id'] for c in claims}) != len(claims):
        raise ValueError('Empty/duplicate claim set')
    covered = set()
    for c in claims:
        if c['event_id'] != event_id or c['guard_status'] != original['guard_status']:
            raise ValueError('Original Guard/event binding mismatch')
        for i in c['original_target_indices']:
            if type(i) is not int or not 0 <= i < len(targets):
                raise ValueError('Unknown original target')
            covered.add(i)
    if covered != set(range(len(targets))):
        raise ValueError('Original fact_check_target coverage incomplete')
    results = [adjudicate(c, registry) for c in claims]
    reasons = list(review.get('hold_reasons', []))
    if any(c['core'] and c['verification_status'] == 'UNRESOLVED' for c in results):
        reasons.append('UNRESOLVED_CORE_CLAIM')
    if not review.get('coverage_complete'):
        reasons.append('SUMMARY_AND_FACT_TARGET_REVIEW_INCOMPLETE')
    used_urls = review.get('verified_source_ids', [])
    if not used_urls or any(registry[s]['access'] != 'body' or registry[s]['source_type'] == 'other' for s in used_urls):
        reasons.append('FINAL_SOURCE_URL_UNVERIFIED')
    # No unreviewed old prose is copied. Only a claim-specific safe statement
    # can survive, and only when its evidence supports the reviewed wording.
    safe = []
    removed = []
    for c in results:
        state = c['verification_status']
        if state not in GOOD:
            removed.append({'target_id': c['target_id'], 'status': state})
            continue
        text = c.get('replacement') if state == 'VERIFIED_CONTEXTUAL' else c.get('safe_statement')
        if text:
            safe.append({'target_id': c['target_id'], 'text': text})
    bad_core = any(c['core'] and c['verification_status'] in BAD for c in results)
    if bad_core or review.get('reject_reason'):
        status = 'REJECT'
    elif reasons or not safe:
        status = 'VERIFICATION_HOLD'
    elif any(c['verification_status'] == 'VERIFIED_CONTEXTUAL' for c in results) or removed:
        status = 'VERIFIED_WITH_CONTEXT'
    else:
        status = 'VERIFIED_PASS'
    return {'event_id': event_id, 'guard_original': original['guard_status'],
            'guard_original_record': copy.deepcopy(original),
            'guard_original_sha256': digest(original), 'original_targets': copy.deepcopy(targets),
            'original_model_risk': original['original_model_risk'],
            'original_scores': copy.deepcopy(original['analysis']['scores']),
            'verification_final': status, 'claims': results, 'removed_claims': removed,
            'hold_reasons': reasons, 'reject_reason': review.get('reject_reason'),
            'source_urls': [registry[s]['url'] for s in used_urls],
            'safe_content': safe if status in EVENT_STATES[:2] else [],
            'verified_fragments_for_review_only': safe,
            'dispatch_allowed': False, 'independent_review': 'PENDING'}
