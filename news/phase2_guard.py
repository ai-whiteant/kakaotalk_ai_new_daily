"""Conservative lexical risk flags, not completed fact verification."""
import copy
import re
from news.phase2_events import article_text, norm

NUMBERS = re.compile(r'(?<!\d)\d+(?:[.,]\d+)*(?:%|조|억|만)?')
URLS = re.compile(r'https?://[^\s<>\"\)]+', re.I)
NAMES = re.compile(r'(?<![A-Za-z0-9])(?:[A-Z]{2,}[A-Za-z0-9-]*|[A-Z][a-z]+[A-Z][A-Za-z0-9.-]*|[A-Z][a-z]{2,}|GPT-?\d[^\s,]*)(?![A-Za-z0-9])|[가-힣]{2,}(?:대학교|교육청|위원회|연구원|특별법|기본법|교육부)')
SAFE_TERMS = {'ai', 'it', 'api', 'llm', 'json'}
QUALIFIED = re.compile(r'\b(may|might|could|plans?|propos\w*|rumou?r\w*|forecast\w*|expected)\b|예정|계획|검토|전망|가능성', re.I)
CERTAIN = re.compile(r'확정(?:됐다|되었다|했다)|시행(?:됐다|되었다)|입증(?:됐다|되었다)|완료(?:했다|됐다)|성공(?:했다|하였다)|공식 발표했다')


def guard(analysis, rows):
    result = copy.deepcopy(analysis)
    source = '\n'.join(article_text(r) for r in rows)
    source_normal = norm(source)
    facts = '\n'.join(result[k] or '' for k in
                      ('summary', 'why_it_matters', 'education_implication', 'classroom_use'))
    all_text = facts + '\n' + '\n'.join(result['uncertainties'] + result['fact_check_targets'])
    issues = []
    input_numbers = {n.replace(',', '') for n in NUMBERS.findall(source)}
    for n in sorted(set(NUMBERS.findall(facts))):
        if n.replace(',', '') not in input_numbers:
            issues.append({'code': 'UNSUPPORTED_NUMBER_OR_DATE', 'value': n})
    known_urls = {r['url'] for r in rows} | set(URLS.findall(source))
    for url in sorted(set(URLS.findall(all_text))):
        if url not in known_urls:
            issues.append({'code': 'GENERATED_URL', 'value': url})
    for name in sorted(set(NAMES.findall(facts))):
        if norm(name) not in source_normal and norm(name) not in SAFE_TERMS:
            issues.append({'code': 'UNSUPPORTED_ENTITY_MODEL_POLICY', 'value': name})
    if QUALIFIED.search(source) and CERTAIN.search(facts):
        issues.append({'code': 'UNCERTAINTY_UPGRADED', 'value': 'uncertain input to definitive output'})
    if issues:
        result['hallucination_risk'] = 'high'
        for issue in issues:
            result['fact_check_targets'].append('자동 검증 필요: '+issue['code']+' / '+issue['value'])
        result['fact_check_targets'] = result['fact_check_targets'][:100]
    return {'analysis': result, 'status': 'HOLD' if result['hallucination_risk']=='high' else 'PASS',
            'issues': issues, 'verification': 'NOT_FACT_CHECKED'}
