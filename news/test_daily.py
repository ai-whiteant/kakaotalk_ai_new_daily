import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from datetime import datetime
from cryptography.fernet import Fernet
from news.daily import State, ServiceError, split_text, canonical, published, deliver, summarize, KST


class NewsTests(unittest.TestCase):
    def test_split_preserves_text_and_url(self):
        url = 'https://example.org/article?long=' + 'a' * 70
        text = '제목: 교육\n핵심내용: ' + '학습 ' * 150 + '\n링크: ' + url
        parts = split_text(text)
        self.assertEqual(''.join(parts), text)
        self.assertTrue(any(url in part for part in parts))
        self.assertTrue(all(len(p.encode('utf-16-le')) // 2 <= 175 for p in parts))

    def test_oversize_url_stops(self):
        with self.assertRaises(ServiceError):
            split_text('https://example.org/' + 'a' * 200)

    def test_canonical_preserves_article_id(self):
        self.assertEqual(canonical('https://EXAMPLE.org/view?id=42&utm_source=x#top'), 'https://example.org/view?id=42')

    def test_bad_and_future_dates(self):
        self.assertIsNone(published('not a date'))
        self.assertIsNotNone(published('Wed, 09 Sep 2026 02:00:00 GMT'))

    def test_state_encrypted_and_tamper_fails(self):
        with tempfile.TemporaryDirectory() as directory, patch('news.daily.ROOT', Path(directory)):
            cfg = {'STATE_ENCRYPTION_KEY': Fernet.generate_key().decode(), 'KAKAO_REFRESH_TOKEN': 'private-test-value'}
            state = State(cfg)
            state.save()
            self.assertNotIn(b'private-test-value', state.path.read_bytes())
            self.assertEqual(State(cfg).data['refresh_token'], 'private-test-value')
            state.path.write_bytes(b'broken')
            with self.assertRaises(Exception):
                State(cfg)

    def test_unknown_delivery_blocks_retry(self):
        with tempfile.TemporaryDirectory() as directory, patch('news.daily.ROOT', Path(directory)):
            cfg = {'STATE_ENCRYPTION_KEY': Fernet.generate_key().decode(), 'KAKAO_LINK_URL': 'https://example.org'}
            state = State(cfg)
            row = {'group': '국내', 'title': '제목', 'source': '기관', 'publication_date': '2026-09-09',
                   'summary': '핵심', 'implication': '분석', 'url': 'https://example.org/a'}
            with patch('news.daily.api', side_effect=ServiceError('timeout')) as call:
                with self.assertRaises(ServiceError):
                    deliver(cfg, state, {}, [row], datetime.now(KST))
                self.assertEqual(call.call_count, 1)
            with patch('news.daily.api') as call:
                with self.assertRaises(ServiceError):
                    deliver(cfg, State(cfg), {}, [row], datetime.now(KST))
                call.assert_not_called()

    def test_sent_article_not_repeated(self):
        with tempfile.TemporaryDirectory() as directory, patch('news.daily.ROOT', Path(directory)):
            cfg = {'STATE_ENCRYPTION_KEY': Fernet.generate_key().decode(), 'KAKAO_LINK_URL': 'https://example.org'}
            state = State(cfg)
            row = {'group': '국내', 'title': '제목', 'source': '기관', 'publication_date': '2026-09-09',
                   'summary': '핵심', 'implication': '분석', 'url': 'https://example.org/a'}
            with patch('news.daily.api', return_value={'result_code': 0}) as call:
                deliver(cfg, state, {}, [row], datetime.now(KST))
                first = call.call_count
                deliver(cfg, State(cfg), {}, [row], datetime.now(KST))
                self.assertEqual(call.call_count, first)

    def test_unfounded_date_evidence_rejected(self):
        source = {'id': 1, 'text': 'Published 2026-09-09', 'url': 'https://example.org/a', 'published_date': '2026-09-09'}
        row = {'id': 1, 'group': '국내', 'title': 't', 'summary': 's', 'implication': 'i', 'source': 'p',
               'publication_date': '2026-09-09', 'date_evidence': 'invented'}
        response = {'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps({'articles': [row]})}}]}
        with patch('news.daily.api', return_value=response):
            self.assertEqual(summarize({'OPENAI_MODEL': 'test', 'OPENAI_API_KEY': 'test'}, [source], datetime(2026,9,9,7,tzinfo=KST)), [])


if __name__ == '__main__':
    unittest.main()
