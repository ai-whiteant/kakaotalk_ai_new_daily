"""Evidence-bearing calibration; unsupported concrete claims remain blocking."""
import copy
import re
import unicodedata
from datetime import date
from decimal import Decimal

from news.phase2_events import article_text
from news.phase2_guard import QUALIFIED, CERTAIN, URLS

ALIASES = {'세계은행': 'world bank', '구글 딥마인드': 'google deepmind',
           '뉴욕시 공립학교': 'new york city public schools', '프리윌린': 'freewillin',
           '네이버': 'naver', '마이크로소프트': 'microsoft', '엔비디아': 'nvidia'}
GENERIC = {'educators', 'teachers', 'students', 'policymakers', 'researchers',
           'conversely', 'additionally', 'however', 'therefore', 'this', 'these', 'the',
           'ai-driven', 'ai-generated', 'ai-powered', 'ai', 'it', 'llm', 'api'}
NAMED_CONTEXT = re.compile(r'\b(?:model|platform|company|university|act|policy|inc|corp)\b|모델|플랫폼|회사|법률|정책', re.I)
PHRASE = re.compile(r'(?<![A-Za-z0-9])(?:[A-Z][A-Za-z0-9.-]*(?:[ \t]+(?:of[ \t]+|the[ \t]+)?[A-Z][A-Za-z0-9.-]*){0,5})(?![A-Za-z0-9])')
KOREAN_NAME = re.compile(r'[가-힣]{2,}(?:대학교|교육청|위원회|연구원|특별법|기본법|교육부)')
NUMBER = re.compile(r'(?<![\d.])\d+(?:,\d{3})*(?:\.\d+)?(?:st|nd|rd|th)?(?:\s*(?:%|percent|퍼센트|billion|million|thousand|조|억|만))?', re.I)
WORDS = {'one':1, 'two':2, 'three':3, 'four':4, 'five':5, 'six':6, 'seven':7, 'eight':8, 'nine':9, 'ten':10}
WORD_COUNT = re.compile(r'\b('+'|'.join(WORDS)+r')\s+(teachers?|students?|schools?|people|years?|months?|days?)\b', re.I)
DATES = re.compile(r'(?<!\d)(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})(?!\d)|(20\d{2})년\s*(\d{1,2})월\s*(\d{1,2})일')


def normalized(value):
    value = unicodedata.normalize('NFKC', value).casefold()
    for alias, phrase in ALIASES.items():
        value = value.replace(alias, phrase)
    return ' '.join(value.split())


def number_key(value):
    value = value.lower().replace(',', '').strip()
    number = re.match(r'\d+(?:\.\d+)?', value).group()
    suffix = value[len(number):].strip()
    factor = {'thousand':1000, 'million':1000000, 'billion':1000000000,
              '만':10000, '억':100000000, '조':1000000000000}.get(suffix, 1)
    return str(Decimal(number)*factor), ('percent' if suffix in ('%', 'percent', '퍼센트') else 'number')


def entity_supported(entity,text):
    return bool(re.search(r'(?<![a-z0-9])'+re.escape(normalized(entity))+r'(?![a-z0-9])',normalized(text)))


def numbers(text):
    result = [(m.group(), number_key(m.group()), m.span()) for m in NUMBER.finditer(text)]
    for match in WORD_COUNT.finditer(text):
        result.append((match.group(), (str(WORDS[match.group(1).lower()]), 'number'), match.span()))
    return result


def dates(text):
    result = []
    for match in DATES.finditer(text):
        parts = match.groups()[:3] if match.group(1) else match.groups()[3:]
        try:
            key = date(*map(int, parts)).isoformat()
        except ValueError:
            key = 'INVALID_DATE'
        result.append((match.group(), key))
    return result


def entities(text):
    # Match phrases before tokens; consumed phrase interiors are never checked separately.
    for match in PHRASE.finditer(text):
        phrase = match.group().rstrip('.')
        words = phrase.split()
        # A generic sentence opener is not part of a following organization name.
        while len(words)>1 and words[0].lower() in GENERIC:
            words.pop(0)
        phrase = ' '.join(words)
        context = text[max(0,match.start()-20):min(len(text),match.end()+25)]
        named = bool(re.search(r'named|called|명칭|이름', context, re.I))
        # Merely discussing a policy/model does not turn Teachers into an institution.
        generic = normalized(phrase) in GENERIC and not named
        yield phrase, generic
    for match in KOREAN_NAME.finditer(text):
        yield match.group(), False


def calibrated_guard(analysis, rows):
    result = copy.deepcopy(analysis)
    evidence = [(r['candidate_id'], article_text(r)) for r in rows]
    findings = []
    def record(code, value, status, field, reason, matches=()):
        findings.append({'code': code, 'value': value, 'status': status, 'output_field': field,
            'reason': reason, 'matched_input': matches[0][1] if matches else None,
            'candidate_ids': sorted({m[0] for m in matches})})
    for field in ('summary', 'why_it_matters', 'education_implication', 'classroom_use'):
        value = result[field] or ''
        for entity, generic in entities(value):
            matches = [(cid, text) for cid, text in evidence if entity_supported(entity,text)]
            if generic:
                record('GENERIC_EXPRESSION', entity, 'PASS', field, 'Generic role/transition/adjective; no named-object context')
            elif matches:
                record('ENTITY_SUPPORTED', entity, 'PASS', field, 'Whole phrase or explicit alias supported', matches)
            elif len(entity)==1:
                record('AMBIGUOUS_ENTITY', entity, 'VERIFY', field, 'Single initial does not establish a named entity')
            else:
                record('UNSUPPORTED_ENTITY_MODEL_POLICY', entity, 'AUTO_HOLD', field, 'Specific named phrase absent from every related candidate')
        output_dates = dates(value)
        for raw, key in output_dates:
            matches = [(cid, s) for cid, text in evidence for s, k in dates(text) if k==key and key!='INVALID_DATE']
            record('DATE_SUPPORTED' if matches else 'UNSUPPORTED_DATE', raw, 'PASS' if matches else 'AUTO_HOLD',
                   field, 'Full calendar date comparison (not separate year/month/day tokens)', matches)
        for raw, key, span in numbers(value):
            if any(m.start()<=span[0] and span[1]<=m.end() for m in DATES.finditer(value)):
                continue  # Date components are validated as a complete calendar date above.
            matches = [(cid, s) for cid, text in evidence for s,k,_ in numbers(text) if k==key]
            if not matches:
                record('UNSUPPORTED_NUMBER_OR_DATE', raw, 'AUTO_HOLD', field, 'No equal normalized quantity in any related candidate')
                continue
            context = value[max(0,span[0]-18):span[1]+18].lower()
            grade = bool(re.search(r'grade\s*\d|\d+(?:st|nd|rd|th)?\s*grade|\d+학년', context))
            if grade:
                grade_matches = [(cid,text) for cid,text in evidence if re.search(
                    r'(?:grade\s*'+re.escape(key[0])+r'\b|\b'+re.escape(key[0])+r'(?:st|nd|rd|th)?\s*grade|'+re.escape(key[0])+r'학년)', text, re.I)]
                if grade_matches:
                    record('ORDINAL_SUPPORTED', raw, 'PASS', field, 'Same grade and ordinal/cardinal quantity', grade_matches)
                else:
                    record('QUANTITY_CONTEXT_AMBIGUOUS', raw, 'VERIFY', field, 'Quantity exists but grade context is not established', matches)
            elif any(normalized(raw)==normalized(s) for _,s in matches):
                record('NUMBER_SUPPORTED', raw, 'PASS', field, 'Equal literal quantity; semantic claim still requires fact checking', matches)
            else:
                record('NUMBER_NORMALIZED', raw, 'VERIFY', field, 'Equal numeric value after safe normalization; unit/claim context needs review', matches)
        for url in URLS.findall(value):
            matches = [(r['candidate_id'],r['url']) for r in rows if r['url']==url]
            matches += [(cid,url) for cid,text in evidence if url in URLS.findall(text)]
            record('URL_SUPPORTED' if matches else 'GENERATED_URL', url, 'PASS' if matches else 'AUTO_HOLD',
                   field, 'Exact URL must occur in supplied sources', matches)
        if CERTAIN.search(value) and any(QUALIFIED.search(text) for _,text in evidence):
            record('UNCERTAINTY_UPGRADED', CERTAIN.search(value).group(), 'AUTO_HOLD', field,
                   'Qualified source text was rendered as confirmed completion')
    for field in ('uncertainties', 'fact_check_targets'):
        for value in result[field]:
            for url in URLS.findall(value):
                if not any(url==r['url'] or url in article_text(r) for r in rows):
                    record('GENERATED_URL', url, 'AUTO_HOLD', field, 'Verification text cannot introduce a new URL')
    if result['hallucination_risk'] in ('medium','high'):
        record('MODEL_REPORTED_RISK', result['hallucination_risk'], 'VERIFY', 'hallucination_risk',
               'Original model risk retained; it is not by itself proof of an unsupported claim')
    pending = [f for f in findings if f['status']!='PASS']
    for finding in pending:
        target = f"[{finding['status']}] {finding['output_field']}: {finding['value']} — {finding['reason']}"
        if len(result['fact_check_targets'])<100:
            result['fact_check_targets'].append(target[:590])
    status = 'AUTO_HOLD' if any(f['status']=='AUTO_HOLD' for f in findings) else ('VERIFY' if pending else 'PASS')
    if status=='AUTO_HOLD':
        result['hallucination_risk']='high'
    return {'analysis': result, 'guard_status': status, 'findings': findings, 'fact_check_evidence': pending,
            'original_model_risk': analysis['hallucination_risk'], 'verification': 'NOT_FACT_CHECKED'}
