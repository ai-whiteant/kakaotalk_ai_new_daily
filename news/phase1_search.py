"""Independent TEST-only Tavily Search layer. Standard library only."""
import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

CATEGORIES = ('ai_education', 'generative_ai', 'ai_models', 'policy_ethics',
              'industry', 'domestic_ai', 'security')
SECRET_PATTERN = re.compile(r'(?:tvly-[A-Za-z0-9_-]{16,}|AIza[A-Za-z0-9_-]{20,}|Bearer\s+\S+)', re.I)


class SearchError(Exception):
    def __init__(self, code, http_status=None, attempts=0):
        super().__init__(code)
        self.code, self.http_status, self.attempts = code, http_status, attempts


def load_key(config_path=None):
    value = os.environ.get('TAVILY_API_KEY')
    if not value and config_path:
        try:
            value = json.loads(Path(config_path).read_text(encoding='utf-8-sig')).get('TAVILY_API_KEY')
        except (OSError, ValueError, AttributeError):
            raise SearchError('CONFIG_INVALID') from None
    if not isinstance(value, str) or not value.strip():
        raise SearchError('TAVILY_KEY_MISSING')
    return value.strip()


def load_queries(path):
    # JSON is a YAML 1.2 subset: avoids adding a dependency to the existing service.
    try:
        config = json.loads(Path(path).read_text(encoding='utf-8-sig'))
        rows = config['queries']
        def require(condition):
            if not condition:
                raise ValueError('query validation failed')
        require(isinstance(rows, list) and 14 <= len(rows) <= 28)
        require(len({q['id'] for q in rows}) == len(rows))
        require({q['category'] for q in rows} == set(CATEGORIES))
        for q in rows:
            require(re.fullmatch(r'[a-z0-9_]+', q['id']))
            require(q['language'] in ('ko', 'en'))
            require(isinstance(q['query'], str) and 1 <= len(q['query'].strip()) <= 400)
            require(type(q['priority']) is int and 1 <= q['priority'] <= 7)
        for category in CATEGORIES:
            require({q['language'] for q in rows if q['category'] == category} == {'ko', 'en'})
    except (OSError, ValueError, KeyError, TypeError):
        raise SearchError('QUERY_CONFIG_INVALID') from None
    return sorted(rows, key=lambda q: q['priority'])


def secret_found(value, secrets=()):
    text = json.dumps(value, ensure_ascii=False)
    return bool(SECRET_PATTERN.search(text) or any(s and s in text for s in secrets))


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class TavilySearch:
    def __init__(self, key, opener=None, sleep=time.sleep):
        self._key = key
        self._open = opener or urllib.request.build_opener(NoRedirect()).open
        self._sleep = sleep

    def search(self, query):
        payload = {'query': query['query'], 'topic': 'news', 'time_range': 'week',
                   'search_depth': 'basic', 'max_results': 5, 'include_answer': False,
                   'include_raw_content': False, 'auto_parameters': False}
        for attempt in range(1, 4):
            request = urllib.request.Request('https://api.tavily.com/search',
                data=json.dumps(payload).encode(), headers={
                    'Authorization': 'Bearer ' + self._key, 'Content-Type': 'application/json'})
            try:
                with self._open(request, timeout=30) as response:
                    data = json.load(response)
                if not isinstance(data, dict) or not isinstance(data.get('results'), list):
                    raise SearchError('RESPONSE_SCHEMA_INVALID', attempts=attempt)
                if secret_found(data, (self._key,)):
                    raise SearchError('SECRET_DETECTED', attempts=attempt)
                return data, attempt
            except urllib.error.HTTPError as error:
                status = error.code
                error.close()
                if status in (401, 403):
                    raise SearchError('TAVILY_AUTH_ERROR', status, attempt) from None
                if status < 500 or attempt == 3:
                    raise SearchError('TAVILY_HTTP_ERROR', status, attempt) from None
            except (urllib.error.URLError, TimeoutError, OSError):
                if attempt == 3:
                    raise SearchError('TAVILY_NETWORK_ERROR', attempts=attempt) from None
            except (ValueError, UnicodeError):
                raise SearchError('RESPONSE_JSON_INVALID', attempts=attempt) from None
            self._sleep(2 ** (attempt - 1))


def canonical_url(value):
    if not isinstance(value, str) or re.search(r'\s', value):
        raise ValueError('invalid URL')
    parts = urlsplit(value)
    if parts.scheme.lower() not in ('http', 'https') or not parts.hostname or parts.username or parts.password:
        raise ValueError('invalid URL')
    host = parts.hostname.lower()
    if ':' in host:
        host = '[' + host + ']'
    port = parts.port
    if port and (parts.scheme.lower(), port) not in (('http', 80), ('https', 443)):
        host += ':' + str(port)
    # Keep identity-bearing query parameters and path/slash semantics intact.
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
             if not k.lower().startswith('utm_') and k.lower() not in ('fbclid', 'gclid')]
    return urlunsplit((parts.scheme.lower(), host, parts.path or '/', urlencode(query), ''))


def parse_date(value):
    if not value:
        return None, 'missing'
    if not isinstance(value, str):
        return None, 'invalid'
    try:
        try:
            result = datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError:
            result = parsedate_to_datetime(value)
        # Do not invent a timezone or midnight for ambiguous timestamps/date-only values.
        if result.tzinfo is None:
            return None, 'ambiguous'
        return result.astimezone(timezone.utc), 'valid'
    except (ValueError, TypeError, OverflowError):
        return None, 'invalid'


@dataclass(frozen=True)
class SearchCandidate:
    candidate_id: str
    query_id: str
    category_hint: str
    title: str
    url: str
    source_name: str
    published_at: str | None
    retrieved_at: str
    snippet: str
    raw_content: str | None
    language: str
    country_hint: str


def normalize(row, query, retrieved):
    if not isinstance(row, dict) or not isinstance(row.get('title'), str) or not row['title'].strip():
        raise ValueError('invalid result')
    url = canonical_url(row.get('url'))
    date, date_status = parse_date(row.get('published_date'))
    title = ' '.join(row['title'].split())
    snippet = row.get('content') or ''
    raw = row.get('raw_content')
    source = row.get('source') or urlsplit(url).hostname
    if not isinstance(snippet, str) or (raw is not None and not isinstance(raw, str)) or not isinstance(source, str):
        raise ValueError('invalid content')
    text = title + ' ' + snippet
    language = 'ko' if re.search('[가-힣]', text) else ('en' if re.search('[A-Za-z]', text) else 'other')
    country = 'KR' if urlsplit(url).hostname.endswith('.kr') else 'UNKNOWN'
    candidate = SearchCandidate(hashlib.sha256(url.encode()).hexdigest()[:24], query['id'],
        query['category'], title, url, ' '.join(source.split()), date.isoformat() if date else None,
        retrieved.isoformat(), snippet, raw, language, country)
    return asdict(candidate), date_status


def deduplicate(candidates):
    unique, provenance = {}, {}
    for row in candidates:
        url = row['url']
        unique.setdefault(url, row)
        provenance.setdefault(row['candidate_id'], []).append({
            'query_id': row['query_id'], 'category_hint': row['category_hint']})
    return list(unique.values()), provenance
