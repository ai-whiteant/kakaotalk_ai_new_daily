"""Run `python -m news.phase1 --mode TEST`; no Gemini/Kakao imports or calls."""
import argparse
import json
import os
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

from news.phase1_search import (CATEGORIES, SearchError, TavilySearch, deduplicate,
                               load_key, load_queries, normalize, secret_found)

ROOT = Path(__file__).resolve().parents[1]


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    temp.replace(path)


def run(queries_path, output, config_path=None, mode='TEST', client=None, now=None):
    now = now or datetime.now(timezone.utc)
    start = now - timedelta(days=7)
    run_id = now.strftime('%Y%m%dT%H%M%S%fZ')
    log = {'run_id': run_id, 'mode': mode, 'started_at': now.isoformat(),
           'period_start': start.isoformat(), 'period_end': now.isoformat(),
           'gemini': 'NOT_CALLED', 'kakao': 'NOT_CALLED', 'queries': [], 'errors': [],
           'warnings': [], 'status': 'FAIL', 'security': 'PASS'}
    raw, normalized, eligible, quarantine = [], [], [], []
    key = ''
    try:
        if mode != 'TEST':
            raise SearchError('TEST_MODE_REQUIRED')
        key = load_key(config_path)
        queries = load_queries(queries_path)
        if secret_found(queries, (key,)):
            raise SearchError('SECRET_DETECTED')
        log['configured_queries'] = len(queries)
        client = client or TavilySearch(key)
        for query in queries:
            entry = {'query_id': query['id'], 'category': query['category'],
                     'started_at': datetime.now(timezone.utc).isoformat()}
            log['queries'].append(entry)
            try:
                data, attempts = client.search(query)
                if secret_found(data, (key,)):
                    raise SearchError('SECRET_DETECTED')
                entry.update(status='PASS', attempts=attempts, count=len(data['results']),
                             request_id=data.get('request_id'))
                raw.append({'query': query, 'response': data})
                for row in data['results']:
                    try:
                        candidate, date_status = normalize(row, query, datetime.now(timezone.utc))
                    except (ValueError, TypeError, AttributeError):
                        log['errors'].append({'query_id': query['id'], 'code': 'CANDIDATE_SCHEMA_INVALID'})
                        continue
                    normalized.append(candidate)
                    date = candidate['published_at']
                    if date and start <= datetime.fromisoformat(date) <= now:
                        eligible.append(candidate)
                    else:
                        reason = 'outside_period' if date else 'date_' + date_status
                        quarantine.append({'candidate': candidate, 'reason': reason})
            except SearchError as error:
                entry.update(status='FAIL', code=error.code, http_status=error.http_status,
                             attempts=error.attempts)
                log['errors'].append(dict(entry))
                if error.code in ('TAVILY_AUTH_ERROR', 'SECRET_DETECTED'):
                    raise
        unique, provenance = deduplicate(eligible)
        log['status'] = 'PASS'
        if log['errors'] or quarantine or not unique:
            log['status'] = 'WARN'
        successful = {q['category'] for q in log['queries'] if q['status'] == 'PASS'}
        if len(set(CATEGORIES) - successful) >= 2 or any(e.get('code') == 'CANDIDATE_SCHEMA_INVALID' for e in log['errors']):
            log['status'] = 'HOLD'
        if not successful:
            log['status'] = 'FAIL'
    except SearchError as error:
        log['errors'].append({'code': error.code, 'http_status': error.http_status, 'attempts': error.attempts})
        log['status'] = 'HOLD' if error.code in ('SECRET_DETECTED', 'QUERY_CONFIG_INVALID') else 'FAIL'
        unique, provenance = deduplicate(eligible)
    except Exception:
        log['errors'].append({'code': 'PHASE1_INTERNAL_ERROR'})
        log['status'] = 'FAIL'
        unique, provenance = [], {}
    log['counts'] = {'executed_queries': len(log['queries']),
        'raw': sum(len(r['response']['results']) for r in raw), 'normalized': len(normalized),
        'in_period': len(eligible), 'deduplicated': len(unique), 'quarantined': len(quarantine),
        'duplicates_removed': len(eligible) - len(unique),
        'by_category': {c: sum(r['category_hint'] == c for r in unique) for c in CATEGORIES}}
    log['warnings'] = [{'code': reason, 'count': count} for reason, count in
                       Counter(q['reason'] for q in quarantine).items()]
    if not unique:
        log['warnings'].append({'code': 'NO_ELIGIBLE_CANDIDATES'})
    log['finished_at'] = datetime.now(timezone.utc).isoformat()
    artifacts = {'raw': (output / 'raw' / f'tavily_raw_{run_id}.json', raw),
        'normalized': (output / 'normalized' / f'candidates_{run_id}.json', unique),
        'all_normalized': (output / 'normalized' / f'all_candidates_{run_id}.json', normalized),
        'quarantine': (output / 'normalized' / f'quarantine_{run_id}.json', quarantine),
        'provenance': (output / 'normalized' / f'provenance_{run_id}.json', provenance)}
    if secret_found([v for _, v in artifacts.values()] + [log], (key,)):
        log['status'], log['security'] = 'HOLD', 'HOLD'
        # Never persist any externally supplied data once a secret is detected.
        artifacts = {}
        log['queries'], log['errors'] = [], [{'code': 'SECRET_DETECTED'}]
    if any(e.get('code') == 'SECRET_DETECTED' for e in log['errors']):
        log['security'] = 'HOLD'
    log['files'] = {k: str(path) for k, (path, _) in artifacts.items()}
    log_path = output / 'logs' / f'run_{run_id}.json'
    for path, value in artifacts.values():
        write_json(path, value)
    write_json(log_path, log)
    return log, log_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['TEST'], default=os.environ.get('RUN_MODE', 'TEST'))
    parser.add_argument('--config', type=Path, default=ROOT / 'news/config.json')
    parser.add_argument('--queries', type=Path, default=ROOT / 'config/news_queries.yaml')
    parser.add_argument('--output', type=Path, default=ROOT / 'outputs/phase1')
    args = parser.parse_args()
    try:
        log, path = run(args.queries, args.output, args.config, args.mode)
        print(json.dumps({'status': log['status'], 'counts': log['counts'], 'log': str(path)}, ensure_ascii=False))
        return 0 if log['status'] in ('PASS', 'WARN') else 1
    except OSError:
        print('FAIL: OUTPUT_WRITE_ERROR')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
