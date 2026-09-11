"""Offline TEST execution of a source-backed, explicitly reviewed evidence packet."""
import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from news.phase22_evidence import CLAIM_STATES, EVENT_STATES, digest, validate_sources, verify_event

PHASE1_SHA = '490b4608eb820ed679ee41a6dcfd969f22d032c493837c3ca220eee53d389e40'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def verify_inputs(repo, manifest):
    for name, expected in manifest.items():
        path = (repo / name).resolve()
        if not path.is_relative_to(repo.resolve()) or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError('INPUT_INTEGRITY_HOLD')
    candidate = repo / 'outputs/phase1/normalized/candidates_20260909T123020056320Z.json'
    if hashlib.sha256(candidate.read_bytes()).hexdigest() != PHASE1_SHA:
        raise ValueError('PHASE1_SHA_HOLD')


def run(repo, packet_path, output, mode='TEST'):
    if mode != 'TEST':
        raise ValueError('ONLY_OFFLINE_TEST_ALLOWED')
    packet = read(packet_path)
    mandatory = {'outputs/phase2_1/events/events.json'} | {
        f'outputs/phase2_1/analysis/{n}.json' for n in ('analysis', 'verify', 'auto_hold')}
    if not mandatory.issubset(packet['input_hashes']):
        raise ValueError('INCOMPLETE_INPUT_MANIFEST')
    verify_inputs(repo, packet['input_hashes'])
    registry = validate_sources(packet['sources'])
    original = []
    for name in ('analysis', 'verify', 'auto_hold'):
        original += read(repo / f'outputs/phase2_1/analysis/{name}.json')
    if Counter(r['guard_status'] for r in original) != {'PASS': 28, 'VERIFY': 5, 'AUTO_HOLD': 16}:
        raise ValueError('PHASE21_COUNTS_HOLD')
    targets = {r['analysis']['event_id']: r for r in original if r['guard_status'] != 'PASS'}
    reviews = packet['reviews']
    if len(reviews) != len(targets) or {r['event_id'] for r in reviews} != set(targets):
        raise ValueError('EVENT_COVERAGE_HOLD')
    verified = [verify_event(targets[r['event_id']], r, registry) for r in reviews]
    claims = [c for e in verified for c in e['claims']]
    stats = {'events_total': 49, 'events_reviewed': len(verified),
             'original_fact_check_targets': sum(len(r['analysis']['fact_check_targets']) for r in targets.values()),
             'evidence_records': len(claims),
             'factual_claims': sum(not c.get('administrative', False) for c in claims),
             'claim_states': {s: sum(c['verification_status'] == s for c in claims) for s in CLAIM_STATES},
             'factual_claim_states': {s: sum(c['verification_status'] == s and not c.get('administrative', False) for c in claims) for s in CLAIM_STATES},
             'event_states': {s: sum(e['verification_final'] == s for e in verified) for s in EVENT_STATES},
             'source_types': dict(Counter(s['source_type'] for s in registry.values())),
             'source_access': dict(Counter(s['access'] for s in registry.values()))}
    for state in EVENT_STATES:
        write(output / f'analysis/{state.lower()}.json', [e for e in verified if e['verification_final'] == state])
    write(output / 'evidence/evidence_records.json', claims)
    write(output / 'evidence/source_registry.json', packet['sources'])
    write(output / 'verification/before_after.json', {
        'before': {'PASS': 28, 'VERIFY': 5, 'AUTO_HOLD': 16}, 'after_reviewed_21': stats['event_states'],
        'original_pass_28': 'PRESERVED_NOT_EXTERNALLY_VERIFIED',
        'events': [{'event_id': e['event_id'], 'before': e['guard_original'], 'after': e['verification_final']} for e in verified]})
    write(output / 'logs/run.json', {'checked_at': datetime.now(timezone.utc).isoformat(),
        'mode': 'TEST', 'status': 'HOLD', 'method': 'Codex source review + deterministic offline evidence gate',
        'packet_sha256': hashlib.sha256(Path(packet_path).read_bytes()).hexdigest(),
        'stats': stats, 'tavily_calls': 0, 'gemini_calls': 0, 'kakao_calls': 0, 'live_runs': 0,
        'reason': 'Independent content review pending; no dispatch selection'})
    verify_inputs(repo, packet['input_hashes'])
    write(output / 'logs/integrity.json', {'input_hashes': packet['input_hashes'], 'unchanged': True,
        'original_pass_sha256': digest([r for r in original if r['guard_status'] == 'PASS'])})
    return stats


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--packet', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=Path('outputs/phase2_2'))
    args = parser.parse_args()
    print(json.dumps(run(Path.cwd(), args.packet, args.output), ensure_ascii=False))
