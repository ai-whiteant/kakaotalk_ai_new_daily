"""All API calls here are mocked. Real paid TEST is a separate CLI command."""
import copy
import io
import json
import os
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import Mock, patch

from news.phase2 import run
from news.phase2_events import build_events, load_candidates
from news.phase2_gemini import Gemini, load_credentials, retry_delay
from news.phase2_guard import guard
from news.phase2_schema import ANALYSIS, LIMITS, Phase2Error, validate_analysis


def candidate(cid='a', title='OpenAI announces Atlas model', snippet='OpenAI announces Atlas model for schools.'):
    return {'candidate_id': cid, 'query_id': 'fixture', 'category_hint': 'ai_education',
        'title': title, 'url': 'https://example.org/'+cid, 'source_name': 'example.org',
        'published_at': '2026-09-09T12:00:00+00:00', 'retrieved_at': '2026-09-09T12:30:00+00:00',
        'snippet': snippet, 'raw_content': None, 'language': 'en', 'country_hint': 'UNKNOWN'}


def analysis(event_id='event'):
    scores = {k: v//2 for k, v in LIMITS.items()}
    scores['total'] = sum(scores.values())
    return {'event_id': event_id, 'category': 'ai_education', 'scores': scores,
        'summary': '제공된 자료에 발표 내용이 제시되어 있다.',
        'why_it_matters': '분석: 해당 발표의 영향을 검토할 필요가 있다.',
        'education_implication': None, 'classroom_use': None,
        'uncertainties': ['원문 사실 검증 필요'], 'fact_check_targets': ['발표 원문 확인'], 'hallucination_risk': 'low'}


class FakeGemini:
    model = 'test-model'
    key = 'TEST_ONLY_SECRET_VALUE'
    def __init__(self, relation='SAME_EVENT', failure_event=None, high=False):
        self.relation, self.failure_event, self.high = relation, failure_event, high
        self.calls = []

    def generate(self, task, data, schema, semantic_check=None):
        self.calls.append({'status': 'PASS'})
        if task.startswith('DEDUP'):
            value = {'decisions': [{'pair_id': p['pair_id'], 'relation': self.relation,
                'confidence': 0.97, 'reason': 'fixture evidence',
                'representative_source_preference': p['left']['candidate_id'],
                'left_evidence': p['left']['snippet'], 'right_evidence': p['right']['snippet']} for p in data]}
        else:
            if self.failure_event == data['event']['canonical_title']:
                raise Phase2Error('GEMINI_JSON_INVALID')
            value = analysis(data['event']['event_id'])
            if self.high:
                value['summary'] = '학교 999곳이 참여했다.'
        if semantic_check:
            semantic_check(value)
        return value


def response(value):
    return io.BytesIO(json.dumps({'candidates': [{'finishReason': 'STOP',
        'content': {'parts': [{'text': json.dumps(value)}]}}], 'usageMetadata': {'totalTokenCount': 5}}).encode())


class Phase2Tests(unittest.TestCase):
    def test_same_event_three_urls(self):
        rows = [candidate(str(i), title='OpenAI announces Atlas '+word,
                          snippet='OpenAI releases Atlas for schools '+word) for i, word in enumerate(('today', 'launch', 'announcement'))]
        events, decisions, warnings = build_events(rows, FakeGemini())
        self.assertEqual(len(events), 1)
        self.assertEqual(len(events[0]['candidate_ids']), 3)
        self.assertEqual(events[0]['dedup_status'], 'GEMINI')
        self.assertEqual(len(decisions), 3)
        self.assertFalse(warnings)

    def test_rule_exact_and_date_not_fabricated(self):
        client = FakeGemini()
        events, _, _ = build_events([candidate('a'), candidate('b')], client)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['dedup_status'], 'RULE')
        self.assertIsNone(events[0]['event_date'])
        self.assertFalse(client.calls)

    def test_follow_up_kept_separate(self):
        events, decisions, _ = build_events([candidate(), candidate('b', 'OpenAI Atlas update')], FakeGemini('FOLLOW_UP'))
        self.assertEqual(len(events), 2)
        self.assertEqual(decisions[0]['relation'], 'FOLLOW_UP')

    def test_different_product_same_company(self):
        events, _, _ = build_events([candidate(), candidate('b', 'OpenAI releases OtherModel')], FakeGemini('DIFFERENT_EVENT'))
        self.assertEqual(len(events), 2)

    def test_invalid_merge_evidence_rejected(self):
        class Bad(FakeGemini):
            def generate(self, task, data, schema, semantic_check):
                value = super().generate(task, data, schema)
                value['decisions'][0]['left_evidence'] = 'invented evidence'
                semantic_check(value)
        events, _, warnings = build_events([candidate(), candidate('b', 'OpenAI Atlas update')], Bad())
        self.assertEqual(len(events), 2)
        self.assertEqual(warnings[0]['code'], 'DEDUP_EVIDENCE_INVALID')

    def test_complete_link_prevents_bridge_merge(self):
        class Bridge(FakeGemini):
            def generate(self, task, data, schema, semantic_check):
                value = super().generate(task, data, schema)
                for p, d in zip(data, value['decisions']):
                    if {p['left']['candidate_id'], p['right']['candidate_id']} == {'a', 'c'}:
                        d['relation'] = 'DIFFERENT_EVENT'
                semantic_check(value)
                return value
        events, _, _ = build_events([candidate(c, 'OpenAI Atlas '+c) for c in 'abc'], Bridge())
        self.assertEqual(sorted(len(e['candidate_ids']) for e in events), [1, 2])

    def test_official_source_preferred(self):
        a, b = candidate('a'), candidate('b')
        b['url'] = 'https://openai.com/index/atlas'
        events, _, _ = build_events([a, b], FakeGemini())
        self.assertEqual(events[0]['primary_source']['candidate_id'], 'b')

    def test_normal_structured_output_and_nulls(self):
        validate_analysis(analysis(), 'event')
        result = analysis()
        result['category'] = 'industry'
        validate_analysis(result, 'event')

    def test_invalid_schema_and_scores(self):
        changes = [('category', 'bogus'), ('summary', None), ('summary', 'x'*1801), ('extra', 'forbidden')]
        for key, value in changes:
            with self.subTest(key=key):
                item = analysis()
                item[key] = value
                with self.assertRaises(Phase2Error):
                    validate_analysis(item, 'event')
        for key, value in [('total', 100), ('education_relevance', 31), ('recency', True)]:
            item = analysis()
            item['scores'][key] = value
            with self.assertRaises(Phase2Error):
                validate_analysis(item, 'event')
        item = analysis()
        del item['fact_check_targets']
        with self.assertRaises(Phase2Error):
            validate_analysis(item, 'event')

    def test_invented_numbers_dates_names_policies_urls(self):
        for statement, code in [
            ('학생 999명이 참가했다.', 'UNSUPPORTED_NUMBER_OR_DATE'),
            ('2035-12-25에 시행됐다.', 'UNSUPPORTED_NUMBER_OR_DATE'),
            ('Microsoft가 발표했다.', 'UNSUPPORTED_ENTITY_MODEL_POLICY'),
            ('GPT-99를 발표했다.', 'UNSUPPORTED_ENTITY_MODEL_POLICY'),
            ('가상교육청이 발표했다.', 'UNSUPPORTED_ENTITY_MODEL_POLICY'),
            ('가상기본법이 제정됐다.', 'UNSUPPORTED_ENTITY_MODEL_POLICY'),
            ('https://invented.invalid/news', 'GENERATED_URL')]:
            with self.subTest(statement=statement):
                item = analysis()
                item['summary'] = statement
                result = guard(item, [candidate()])
                self.assertEqual(result['status'], 'HOLD')
                self.assertIn(code, [i['code'] for i in result['issues']])
                self.assertGreater(len(result['analysis']['fact_check_targets']), 1)

    def test_uncertainty_not_upgraded(self):
        item = analysis()
        item['summary'] = '계획이 확정됐다.'
        self.assertEqual(guard(item, [candidate(snippet='OpenAI may announce a plan.')])['status'], 'HOLD')

    def test_schema_retry_once_then_success(self):
        bad = analysis()
        bad['scores']['total'] = 100
        opener = Mock(side_effect=[response(bad), response(analysis())])
        client = Gemini('secret-fixture', 'test-model', opener)
        result = client.generate('ANALYZE:', {}, ANALYSIS, lambda v: validate_analysis(v, 'event'))
        self.assertEqual(opener.call_count, 2)
        validate_analysis(result, 'event')

    def test_schema_retry_exhaustion(self):
        opener = Mock(side_effect=[response({}), response({})])
        with self.assertRaises(Phase2Error):
            Gemini('secret-fixture', 'test-model', opener).generate('ANALYZE:', {}, ANALYSIS)
        self.assertEqual(opener.call_count, 2)

    def test_429_and_5xx_bounded_retries(self):
        for status in (429, 503):
            opener = Mock(side_effect=lambda *a, **k: (_ for _ in ()).throw(
                urllib.error.HTTPError('https://example.org', status, 'hidden-detail', {'Retry-After': '2'}, None)))
            sleep = Mock()
            with self.assertRaises(Phase2Error):
                Gemini('secret-fixture', 'test-model', opener, sleep).generate('ANALYZE:', {}, ANALYSIS)
            self.assertEqual(opener.call_count, 3)
            self.assertEqual(sleep.call_count, 2)
            self.assertEqual(sleep.call_args.args, (2.0,))

    def test_400_403_404_no_retry(self):
        for status in (400, 401, 403, 404):
            opener = Mock(side_effect=urllib.error.HTTPError('https://example.org', status, 'secret-fixture', {}, None))
            with self.assertRaises(Phase2Error) as context:
                Gemini('secret-fixture', 'test-model', opener).generate('ANALYZE:', {}, ANALYSIS)
            self.assertNotIn('secret-fixture', str(context.exception))
            self.assertEqual(opener.call_count, 1)

    def test_retry_after_long_stops(self):
        with self.assertRaises(Phase2Error):
            retry_delay('3600', 1)
        self.assertEqual(retry_delay('bad', 2), 2)

    def test_secret_response_never_logged(self):
        client = Gemini('secret-fixture', 'test-model', Mock(return_value=response({'key': 'secret-fixture'})))
        with self.assertRaises(Phase2Error) as context:
            client.generate('ANALYZE:', {}, ANALYSIS)
        self.assertEqual(context.exception.code, 'SECRET_DETECTED')
        self.assertNotIn('secret-fixture', json.dumps(client.calls))

    def test_model_must_come_from_environment(self):
        with patch.dict(os.environ, {'GEMINI_API_KEY': 'fixture'}, clear=True):
            with self.assertRaises(Phase2Error):
                load_credentials(None)
            with patch.dict(os.environ, {'GEMINI_MODEL': 'model-from-env'}):
                self.assertEqual(load_credentials(None)[1], 'model-from-env')

    def fixture_run(self, rows, client, mode='TEST'):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'input.json'
            path.write_text(json.dumps(rows))
            log, output = run(path, Path(folder)/'out', mode=mode, client=client)
            saved = {p.name: json.loads(p.read_text(encoding='utf-8')) for p in output.rglob('*.json')}
            return log, saved

    def test_partial_analysis_failure_continues(self):
        rows = [candidate(), candidate('b', 'Separate industrial story')]
        log, saved = self.fixture_run(rows, FakeGemini(failure_event='Separate industrial story'))
        self.assertEqual(log['status'], 'WARN')
        self.assertEqual(len(saved['analysis.json']), 1)

    def test_high_risk_isolated(self):
        log, saved = self.fixture_run([candidate()], FakeGemini(high=True))
        self.assertEqual(log['status'], 'HOLD')
        self.assertEqual(saved['analysis.json'], [])
        self.assertEqual(len(saved['high_risk.json']), 1)

    def test_many_failed_dedup_pairs_holds(self):
        class FailedDedup(FakeGemini):
            def generate(self, task, data, schema, semantic_check=None):
                if task.startswith('DEDUP'):
                    raise Phase2Error('SCHEMA_INVALID')
                return super().generate(task, data, schema, semantic_check)
        log, _ = self.fixture_run([candidate(c, 'OpenAI Atlas '+c) for c in 'abc'], FailedDedup())
        self.assertEqual(log['status'], 'HOLD')

    def test_live_rejected(self):
        client = FakeGemini()
        log, _ = self.fixture_run([candidate()], client, 'LIVE')
        self.assertEqual(log['status'], 'FAIL')
        self.assertFalse(client.calls)

    def test_input_validation_and_secret_block(self):
        log, _ = self.fixture_run([candidate(), candidate()], FakeGemini())
        self.assertEqual(log['status'], 'FAIL')
        log, saved = self.fixture_run([candidate(snippet=FakeGemini.key)], FakeGemini())
        self.assertEqual(log['status'], 'HOLD')
        self.assertNotIn(FakeGemini.key, json.dumps(saved))


if __name__ == '__main__':
    unittest.main()
