"""TEST-only Phase 2. Consumes recorded Phase 1 candidates; never sends messages."""
import argparse
import hashlib
import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from news.phase1 import write_json
from news.phase1_search import secret_found
from news.phase2_events import build_events, load_candidates
from news.phase2_gemini import Gemini, load_credentials
from news.phase2_guard import guard
from news.phase2_schema import ANALYSIS, LIMITS, Phase2Error, dump_schemas, validate_analysis

ROOT = Path(__file__).resolve().parents[1]


def run(input_path, output, config=None, mode='TEST', client=None, progress=None):
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    folder = output / run_id
    log = {'run_id': run_id, 'mode': mode, 'status': 'FAIL', 'started_at': datetime.now(timezone.utc).isoformat(),
           'errors': [], 'warnings': [], 'kakao': 'NOT_CALLED', 'tavily': 'NOT_CALLED',
           'final_selection': 'NOT_PERFORMED', 'security': 'PASS', 'events': []}
    rows, events, decisions, analyses, risks = [], [], [], [], []
    key = ''
    try:
        if mode != 'TEST':
            raise Phase2Error('TEST_MODE_REQUIRED')
        if client is None:
            key, model = load_credentials(config)
            client = Gemini(key, model)
        else:
            key, model = getattr(client, 'key', ''), getattr(client, 'model', 'fixture')
        log['model'] = model
        log['billing_tier'] = 'USER_IDENTIFIED_PAID_PROJECT; NOT_INFERRED_FROM_API'
        rows = load_candidates(input_path, (key,))
        log['input_sha256'] = hashlib.sha256(Path(input_path).read_bytes()).hexdigest()
        events, decisions, log['warnings'] = build_events(rows, client)
        if progress:
            progress({'stage': 'events', 'candidates': len(rows), 'events': len(events), 'pairs': len(decisions)})
        lookup = {r['candidate_id']: r for r in rows}
        for index, event in enumerate(events):
            event_rows = [lookup[c] for c in event['candidate_ids']]
            try:
                value = client.generate('ANALYZE: Analyze this event from the supplied excerpts only. '
                    'Return the exact event_id. Score limits: '+json.dumps(LIMITS)+
                    '. These are unverified search snippets, not independently verified facts. '
                    'List source/date/claim verification needs. Keep proper names in source spelling.',
                    {'event': event, 'articles': event_rows}, ANALYSIS,
                    lambda v: validate_analysis(v, event['event_id']))
                checked = guard(value, event_rows)
                validate_analysis(checked['analysis'], event['event_id'])
                if checked['status'] == 'HOLD':
                    risks.append(checked)
                else:
                    analyses.append(checked['analysis'])
                log['events'].append({'event_id': event['event_id'], 'status': checked['status'],
                                      'risk': checked['analysis']['hallucination_risk']})
            except Phase2Error as error:
                log['errors'].append({'event_id': event['event_id'], 'code': error.code, 'http_status': error.status})
                log['events'].append({'event_id': event['event_id'], 'status': 'ERROR'})
                if error.status in (400, 401, 403, 404) or error.code == 'SECRET_DETECTED':
                    raise
            if progress:
                progress({'stage': 'analysis', 'completed': index+1, 'total': len(events), 'high_risk': len(risks)})
        completed = len(analyses) + len(risks)
        log['status'] = 'PASS'
        if log['errors'] or log['warnings']:
            log['status'] = 'WARN'
        failed_pairs = sum(len(w.get('pair_ids', [])) for w in log['warnings'])
        if risks or len(log['errors']) > max(1, len(events)//5) or failed_pairs >= max(2, (len(decisions)+failed_pairs)//5):
            log['status'] = 'HOLD'
        if completed == 0:
            log['status'] = 'FAIL'
    except Phase2Error as error:
        log['errors'].append({'code': error.code, 'http_status': error.status})
        log['status'] = 'HOLD' if error.code == 'SECRET_DETECTED' else 'FAIL'
    except Exception:
        log['errors'].append({'code': 'PHASE2_INTERNAL_ERROR'})
        log['status'] = 'FAIL'
    log['calls'] = getattr(client, 'calls', [])
    all_analysis = analyses + [r['analysis'] for r in risks]
    scores = [a['scores']['total'] for a in all_analysis]
    log['counts'] = {'input_candidates': len(rows), 'events': len(events),
        'merged_candidates': len(rows)-len(events), 'dedup_relations': dict(Counter(d['relation'] for d in decisions)),
        'analyses': len(all_analysis), 'non_high_risk': len(analyses), 'high_risk': len(risks),
        'http_attempts': len(log['calls']), 'scores': {'min': min(scores, default=None),
        'max': max(scores, default=None), 'mean': round(sum(scores)/len(scores), 2) if scores else None,
        'at_least_70': sum(s >= 70 for s in scores)}}
    log['finished_at'] = datetime.now(timezone.utc).isoformat()
    artifacts = {'events/events.json': events, 'events/decisions.json': decisions,
                 'analysis/analysis.json': analyses, 'analysis/high_risk.json': risks}
    if secret_found([artifacts, log], (key,)):
        log = {'run_id': run_id, 'status': 'HOLD', 'security': 'HOLD', 'errors': [{'code': 'SECRET_DETECTED'}]}
        artifacts = {}
    if any(e['code'] == 'SECRET_DETECTED' for e in log['errors']):
        log['security'] = 'HOLD'
        artifacts = {}
    for name, value in artifacts.items():
        write_json(folder/name, value)
    write_json(folder/'logs/run.json', log)
    return log, folder


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--config', type=Path, default=ROOT/'news/config.json')
    parser.add_argument('--output', type=Path, default=ROOT/'outputs/phase2')
    parser.add_argument('--mode', choices=['TEST'], default=os.environ.get('RUN_MODE', 'TEST'))
    args = parser.parse_args()
    try:
        log, folder = run(args.input, args.output, args.config, args.mode,
                          progress=lambda value: print(json.dumps(value), flush=True))
        print(json.dumps({'status': log['status'], 'output': str(folder), 'counts': log.get('counts')}, ensure_ascii=False))
        return 0 if log['status'] in ('PASS', 'WARN') else 1
    except OSError:
        print('FAIL: OUTPUT_WRITE_ERROR')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
