"""JSON Schema contracts and semantic checks; independent of Phase 1 storage."""
import json
from jsonschema import Draft202012Validator, FormatChecker

CATEGORIES = ['ai_education', 'generative_ai', 'ai_models', 'policy_ethics',
              'industry', 'domestic_ai', 'security', 'other']
LIMITS = dict(education_relevance=30, ai_technical_importance=20,
              teacher_student_impact=15, social_industry_impact=15, source_reliability=10, recency=10)


class Phase2Error(Exception):
    def __init__(self, code, status=None):
        super().__init__(code)
        self.code, self.status = code, status


def obj(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}


def text(maximum=1800, nullable=False):
    return {'type': ['string', 'null'] if nullable else 'string', 'minLength': 1, 'maxLength': maximum}


def strings(maximum=15):
    return {'type': 'array', 'items': text(600), 'maxItems': maximum}


CANDIDATE = obj({**{k: text(2000) for k in ['candidate_id', 'query_id', 'category_hint', 'title',
                                          'url', 'source_name', 'retrieved_at']},
    'published_at': {'type': ['string', 'null'], 'format': 'date-time'},
    'snippet': {'type': 'string', 'maxLength': 50000},
    'raw_content': {'type': ['string', 'null'], 'maxLength': 500000},
    'language': {'enum': ['ko', 'en', 'other']}, 'country_hint': {'enum': ['KR', 'INTL', 'UNKNOWN']}})
CANDIDATE['properties']['retrieved_at']['format'] = 'date-time'
CANDIDATE['properties']['url']['format'] = 'uri'
ANALYSIS = obj({'event_id': text(100), 'category': {'enum': CATEGORIES},
    'scores': obj({**{k: {'type': 'integer', 'minimum': 0, 'maximum': v} for k, v in LIMITS.items()},
                   'total': {'type': 'integer', 'minimum': 0, 'maximum': 100}}),
    'summary': text(), 'why_it_matters': text(), 'education_implication': text(nullable=True),
    'classroom_use': text(nullable=True), 'uncertainties': strings(), 'fact_check_targets': strings(100),
    'hallucination_risk': {'enum': ['low', 'medium', 'high']}})
DECISION = obj({'pair_id': text(100), 'relation': {'enum': ['SAME_EVENT', 'FOLLOW_UP', 'DIFFERENT_EVENT']},
    'confidence': {'type': 'number', 'minimum': 0, 'maximum': 1}, 'reason': text(800),
    'representative_source_preference': text(100), 'left_evidence': text(500), 'right_evidence': text(500)})
SOURCE = obj({k: CANDIDATE['properties'][k] for k in
              ('candidate_id', 'title', 'url', 'source_name', 'published_at')})
EVENT = obj({'event_id': text(100), 'canonical_title': text(2000), 'category_hint': text(100),
    'candidate_ids': {'type': 'array', 'items': text(100), 'minItems': 1, 'uniqueItems': True},
    'primary_source': SOURCE, 'supporting_sources': {'type': 'array', 'items': SOURCE},
    'entities': strings(100), 'event_date': {'type': ['string', 'null'], 'format': 'date-time'},
    'dedup_status': {'enum': ['RULE', 'GEMINI', 'SINGLE']},
    'dedup_confidence': {'type': 'number', 'minimum': 0, 'maximum': 1}})


def validate(value, schema):
    # Never expose ValidationError: it includes the model response/instance.
    if next(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(value), None):
        raise Phase2Error('SCHEMA_INVALID')
    return value


def validate_analysis(value, event_id):
    validate(value, ANALYSIS)
    if value['event_id'] != event_id:
        raise Phase2Error('EVENT_ID_MISMATCH')
    if value['scores']['total'] != sum(value['scores'][k] for k in LIMITS):
        raise Phase2Error('SCORE_TOTAL_MISMATCH')
    return value


def dump_schemas(path):
    path.write_text(json.dumps({'candidate': CANDIDATE, 'event': EVENT,
                               'analysis': ANALYSIS, 'decision': DECISION}, indent=2), encoding='utf-8')
