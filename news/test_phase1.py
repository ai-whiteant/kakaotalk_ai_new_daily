"""Offline contract, failure isolation, security and regression tests."""
import io
import json
import os
import tempfile
import unittest
import urllib.error
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from news.phase1 import ROOT, run
from news.phase1_search import (CATEGORIES, SearchError, TavilySearch, canonical_url,
                               load_key, load_queries, normalize, parse_date)

NOW = datetime(2026, 9, 9, 12, tzinfo=timezone.utc)
QUERIES = ROOT / 'config/news_queries.yaml'


def row(url='https://example.org/news?id=1', date=None):
    return {'title': '  AI   education  ', 'url': url, 'content': 'School AI news',
            'published_date': date or NOW.isoformat()}


class FixtureClient:
    def __init__(self, fail=(), results=None):
        self.fail = fail
        self.results = results if results is not None else [row()]

    def search(self, query):
        if query['id'] in self.fail:
            raise SearchError('TAVILY_HTTP_ERROR', 500, 3)
        return {'results': self.results, 'request_id': 'fixture'}, 1


class Phase1Tests(unittest.TestCase):
    def run_fixture(self, client, **kwargs):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {'TAVILY_API_KEY': 'dummy-key'}):
            log, path = run(QUERIES, Path(folder), client=client, now=NOW, **kwargs)
            files = {k: json.loads(Path(v).read_text(encoding='utf-8')) for k, v in log['files'].items()}
            self.assertEqual(json.loads(path.read_text(encoding='utf-8')), log)
            return log, files

    def test_environment_and_local_config(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {}, clear=True):
            path = Path(folder) / 'config.json'
            path.write_text('{"TAVILY_API_KEY":"local-dummy"}')
            self.assertEqual(load_key(path), 'local-dummy')
            with patch.dict(os.environ, {'TAVILY_API_KEY': 'env-dummy'}):
                self.assertEqual(load_key(path), 'env-dummy')
            with self.assertRaises(SearchError):
                load_key()

    def test_queries_cover_seven_bilingual_categories(self):
        queries = load_queries(QUERIES)
        self.assertEqual(len(queries), 14)
        self.assertEqual({q['category'] for q in queries}, set(CATEGORIES))

    def test_invalid_query_config_holds(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {'TAVILY_API_KEY': 'dummy'}):
            config = Path(folder) / 'queries.yaml'
            config.write_text('{"queries": []}')
            log, _ = run(config, Path(folder)/'out', client=FixtureClient(), now=NOW)
            self.assertEqual(log['status'], 'HOLD')

    def test_request_contract(self):
        requests = []
        def opener(request, timeout):
            requests.append(request)
            self.assertEqual(timeout, 30)
            return io.BytesIO(b'{"results": []}')
        TavilySearch('dummy', opener=opener).search(load_queries(QUERIES)[0])
        request = requests[0]
        self.assertEqual(request.full_url, 'https://api.tavily.com/search')
        payload = json.loads(request.data)
        self.assertEqual((payload['topic'], payload['time_range'], payload['search_depth']), ('news', 'week', 'basic'))
        self.assertFalse(payload['include_answer'])
        self.assertEqual(request.get_header('Authorization'), 'Bearer dummy')

    def test_network_and_5xx_retry_then_success(self):
        for error in [urllib.error.URLError('dummy'), urllib.error.HTTPError('https://example.org', 503, 'dummy', {}, None)]:
            with self.subTest(error=type(error).__name__):
                from unittest.mock import Mock
                opener = Mock(side_effect=[error, io.BytesIO(b'{"results": []}')])
                sleeper = Mock()
                _, attempts = TavilySearch('dummy', opener, sleeper).search(load_queries(QUERIES)[0])
                self.assertEqual(attempts, 2)
                sleeper.assert_called_once_with(1)

    def test_auth_and_quota_not_retried(self):
        for status in (400, 401, 403, 429, 432, 433):
            from unittest.mock import Mock
            opener = Mock(side_effect=urllib.error.HTTPError('https://example.org', status, 'secret-dummy', {}, None))
            with self.assertRaises(SearchError) as context:
                TavilySearch('dummy', opener).search(load_queries(QUERIES)[0])
            self.assertEqual(opener.call_count, 1)
            self.assertNotIn('secret-dummy', str(context.exception))

    def test_partial_failure_continues(self):
        log, _ = self.run_fixture(FixtureClient(fail=('edu_ko_01',)))
        self.assertEqual(log['status'], 'WARN')
        self.assertEqual(len(log['queries']), 14)

    def test_missing_multiple_categories_holds(self):
        fail = [q['id'] for q in load_queries(QUERIES) if q['category'] in CATEGORIES[:2]]
        log, _ = self.run_fixture(FixtureClient(fail=fail))
        self.assertEqual(log['status'], 'HOLD')

    def test_url_dedup_preserves_provenance(self):
        log, files = self.run_fixture(FixtureClient(results=[row(), row('https://EXAMPLE.org/news?id=1&utm_source=test#top')]))
        self.assertEqual(log['status'], 'PASS')
        self.assertEqual(log['counts']['deduplicated'], 1)
        self.assertEqual(len(next(iter(files['provenance'].values()))), 28)
        self.assertNotEqual(canonical_url('https://example.org/a?id=1'), canonical_url('https://example.org/a?id=2'))
        self.assertNotEqual(canonical_url('https://example.org/a'), canonical_url('https://example.org/a/'))
        for url in ('javascript:alert(1)', 'https://user:pass@example.org/a', 'https://example.org/a b'):
            with self.assertRaises(ValueError):
                canonical_url(url)

    def test_date_parsing(self):
        self.assertEqual(parse_date(None)[1], 'missing')
        self.assertEqual(parse_date('bad')[1], 'invalid')
        self.assertEqual(parse_date('2026-09-09')[1], 'ambiguous')
        self.assertEqual(parse_date('Wed, 09 Sep 2026 12:00:00 GMT')[0], NOW)
        self.assertEqual(parse_date('2026-09-09T21:00:00+09:00')[0], NOW)

    def test_period_boundaries_and_quarantine(self):
        dates = [NOW, NOW-timedelta(days=7), NOW-timedelta(days=7, seconds=1), NOW+timedelta(seconds=1)]
        results = [row('https://example.org/' + str(i), date.isoformat()) for i, date in enumerate(dates)]
        results += [dict(row(), published_date=None), dict(row(), published_date='bad')]
        log, files = self.run_fixture(FixtureClient(results=results))
        self.assertEqual(log['counts']['deduplicated'], 2)
        self.assertEqual(log['counts']['quarantined'], 56)
        self.assertTrue(all(c['published_at'] for c in files['normalized']))

    def test_normalization_schema(self):
        candidate, _ = normalize(row(), load_queries(QUERIES)[0], NOW)
        self.assertEqual(set(candidate), {'candidate_id', 'query_id', 'category_hint', 'title',
            'url', 'source_name', 'published_at', 'retrieved_at', 'snippet', 'raw_content',
            'language', 'country_hint'})
        self.assertEqual(candidate['title'], 'AI education')
        self.assertEqual(candidate['country_hint'], 'UNKNOWN')
        self.assertIsNone(candidate['raw_content'])

    def test_secret_in_response_is_not_saved(self):
        log, files = self.run_fixture(FixtureClient(results=[dict(row(), content='dummy-key')]))
        self.assertEqual(log['status'], 'HOLD')
        self.assertEqual(log['security'], 'HOLD')
        self.assertNotIn('dummy-key', json.dumps([log, files]))

    def test_malformed_row_holds(self):
        log, _ = self.run_fixture(FixtureClient(results=[{'title': 'missing URL'}]))
        self.assertEqual(log['status'], 'HOLD')

    def test_live_rejected_without_call(self):
        from unittest.mock import Mock
        client = Mock()
        log, _ = self.run_fixture(client, mode='LIVE')
        self.assertEqual(log['status'], 'FAIL')
        client.search.assert_not_called()

    def test_all_failed(self):
        log, _ = self.run_fixture(FixtureClient(fail=[q['id'] for q in load_queries(QUERIES)]))
        self.assertEqual(log['status'], 'FAIL')


if __name__ == '__main__':
    unittest.main()
