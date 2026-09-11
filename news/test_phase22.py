"""Evidence-gate enforcement tests; fixtures are reviewed decisions, not live facts."""
import copy
import tempfile
import unittest
from pathlib import Path

from news.phase22 import run, verify_inputs
from news.phase22_evidence import adjudicate, digest, public_url, validate_sources, verify_event

S = 'VERIFIED_SUPPORTED'
E = 'VERIFIED_EQUIVALENT'
C = 'VERIFIED_CONTEXTUAL'
U = 'UNRESOLVED'
X = 'VERIFIED_UNSUPPORTED'
D = 'CONTRADICTED'


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.source = dict(source_id='official', url='https://agency.example/policy',
            source_name='Fixture agency', source_type='official',
            retrieved_at='2026-09-10T01:00:00+00:00', verification_only=True,
            access='body', notes=['Reviewed fixture: two-hour study, US grade 8.'], locator='Policy section')
        self.source['evidence_sha256'] = digest(self.source['notes'])
        self.registry = validate_sources([self.source])
        self.claim = dict(target_id='t1', event_id='e1', guard_status='AUTO_HOLD',
            claim='Two-hour study', claim_type='number', core=True,
            requested_status=S, reason='Explicit reviewed passage',
            checked_at='2026-09-10T01:00:00+00:00', reviewed_by='fixture reviewer',
            semantic_review='Wording assessed against the cited policy',
            evidence_refs=[dict(source_id='official', note_index=0)],
            original_target_indices=[0], safe_statement='Reviewed statement')
        self.original = dict(guard_status='AUTO_HOLD', original_model_risk='high',
            findings=[dict(code='NUMBER', value='2')],
            analysis=dict(event_id='e1', fact_check_targets=['Check duration'], scores={'total': 71}))
        self.review = dict(event_id='e1', original_record_sha256=digest(self.original),
            claims=[self.claim], coverage_complete=True, verified_source_ids=['official'])

    def result(self):
        return adjudicate(self.claim, self.registry)

    def event(self):
        return verify_event(self.original, self.review, self.registry)

    def test_two_hour_equivalence_review(self):
        self.claim.update(requested_status=E, claim='two-hour ↔ 2시간', equivalence_context='Same daily study duration')
        self.assertEqual(self.result()['verification_status'], E)

    def test_grade_eight_equivalence_review(self):
        self.claim.update(requested_status=E, claim='8th grade ↔ 8학년', equivalence_context='Same US grade; no Korean grade conversion')
        self.assertEqual(self.result()['verification_status'], E)

    def test_equivalence_without_context_downgrades(self):
        self.claim['requested_status'] = E
        self.assertEqual(self.result()['verification_status'], U)

    def test_number_absent_from_candidate_can_have_official_evidence(self):
        self.assertEqual(self.result()['verification_status'], S)

    def test_invented_number_requires_reviewed_absence(self):
        self.claim.update(requested_status=X, claim='999 hours', absence_review='Full relevant policy scope examined; no such claim')
        self.assertEqual(self.result()['verification_status'], X)
        self.assertEqual(self.event()['verification_final'], 'REJECT')

    def test_search_failure_does_not_establish_unsupported(self):
        self.claim.update(requested_status=X, evidence_refs=[])
        self.assertEqual(self.result()['verification_status'], U)

    def test_missing_absence_review_downgrades(self):
        self.claim['requested_status'] = X
        self.assertEqual(self.result()['verification_status'], U)

    def test_unsupported_model_removed(self):
        self.claim.update(requested_status=X, claim_type='model', claim='InventedModel', absence_review='Inspected exhaustive release list')
        self.assertEqual(self.event()['safe_content'], [])

    def test_wrong_policy_contradiction_rejects(self):
        self.claim.update(requested_status=D, claim_type='policy', contradicting_fact='Official policy explicitly states the opposite')
        self.assertEqual(self.event()['verification_final'], 'REJECT')

    def test_contradiction_without_specific_fact_downgrades(self):
        self.claim['requested_status'] = D
        self.assertEqual(self.result()['verification_status'], U)

    def test_missing_date_holds(self):
        self.claim.update(requested_status=U, claim_type='date', evidence_refs=[])
        self.assertEqual(self.event()['verification_final'], 'VERIFICATION_HOLD')

    def test_body_access_failure_holds(self):
        self.registry['official']['access'] = 'failed'
        self.assertEqual(self.event()['verification_final'], 'VERIFICATION_HOLD')

    def test_snippet_is_not_final_evidence(self):
        self.registry['official']['access'] = 'snippet_only'
        self.assertEqual(self.result()['verification_status'], U)

    def test_partial_body_is_not_final_evidence(self):
        self.registry['official']['access'] = 'partial'
        self.assertEqual(self.result()['verification_status'], U)

    def test_unreliable_blog_not_final_evidence(self):
        self.registry['official']['source_type'] = 'other'
        self.assertEqual(self.result()['verification_status'], U)

    def test_source_conflict_needs_explicit_resolution(self):
        self.claim['conflict'] = 'Official 33 versus article 32'
        self.assertEqual(self.result()['verification_status'], U)
        self.claim['conflict_resolution'] = 'Same date and scope; official roster is definitive for this reviewed claim'
        self.assertEqual(self.result()['verification_status'], S)

    def test_source_priority_is_preserved(self):
        second = copy.deepcopy(self.source)
        second.update(source_id='press', source_type='major_media', url='https://press.example/article')
        self.registry = validate_sources([second, self.source])
        self.claim['evidence_refs'].insert(0, dict(source_id='press', note_index=0))
        self.assertEqual(self.result()['evidence'][0]['source_type'], 'official')

    def test_new_url_requires_actual_body_retrieval(self):
        self.claim.update(claim_type='url', url_value='https://invented.example/not-retrieved')
        self.assertEqual(self.result()['verification_status'], U)
        self.claim['url_value'] = self.source['url']
        self.assertEqual(self.result()['verification_status'], S)

    def test_verification_url_cannot_be_new_candidate(self):
        self.source['verification_only'] = False
        with self.assertRaises(ValueError):
            validate_sources([self.source])

    def test_generated_url_without_input_or_official_provenance_is_unsupported(self):
        self.claim.update(claim_type='url', requested_status=X,
            url_value='https://invented.example/generated',
            absence_review='Compared with input URL registry and reviewed official body URL list; absent from both')
        self.assertEqual(self.result()['verification_status'], X)
        self.assertEqual(self.event()['safe_content'], [])

    def test_noncore_unsupported_removed_from_safe_content(self):
        extra = copy.deepcopy(self.claim)
        extra.update(target_id='t2', original_target_indices=[], core=False,
            requested_status=X, absence_review='Specific source scope reviewed', safe_statement='Unsafe text')
        self.review['claims'].append(extra)
        result = self.event()
        self.assertEqual(result['verification_final'], 'VERIFIED_WITH_CONTEXT')
        self.assertNotIn('Unsafe text', str(result['safe_content']))

    def test_unresolved_core_never_passes(self):
        self.claim['requested_status'] = U
        self.assertEqual(self.event()['safe_content'], [])
        self.assertFalse(self.event()['dispatch_allowed'])

    def test_context_requires_replacement(self):
        self.claim['requested_status'] = C
        self.assertEqual(self.result()['verification_status'], U)
        self.claim['replacement'] = 'Precise scope with exceptions'
        self.assertEqual(self.event()['safe_content'][0]['text'], self.claim['replacement'])

    def test_original_guard_and_scores_immutable(self):
        before = copy.deepcopy(self.original)
        result = self.event()
        self.assertEqual(self.original, before)
        self.assertEqual(result['guard_original_record'], before)
        self.assertEqual(result['original_scores'], {'total': 71})
        self.assertFalse(result['dispatch_allowed'])

    def test_old_unreviewed_summary_not_exported(self):
        self.original['analysis']['summary'] = 'Unverified dangerous summary'
        self.review['original_record_sha256'] = digest(self.original)
        self.assertNotIn('dangerous', str(self.event()['safe_content']))

    def test_original_record_tampering_fails(self):
        self.original['guard_status'] = 'PASS'
        with self.assertRaises(ValueError):
            self.event()

    def test_missing_target_coverage_fails(self):
        self.claim['original_target_indices'] = []
        with self.assertRaises(ValueError):
            self.event()

    def test_duplicate_target_id_fails(self):
        self.review['claims'].append(copy.deepcopy(self.claim))
        with self.assertRaises(ValueError):
            self.event()

    def test_source_notes_tampering_fails(self):
        self.source['notes'][0] = 'Changed'
        with self.assertRaises(ValueError):
            validate_sources([self.source])

    def test_private_and_credential_urls_rejected(self):
        for url in ('https://127.0.0.1/a', 'https://localhost/a', 'https://user:pass@example.com/a', 'http://example.com/a'):
            with self.subTest(url=url):
                self.assertFalse(public_url(url))

    def test_live_mode_rejected_before_io(self):
        with self.assertRaisesRegex(ValueError, 'ONLY_OFFLINE'):
            run(Path('.'), Path('missing'), Path('unused'), mode='LIVE')

    def test_input_sha_mismatch_holds(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder)
            (p / 'input.json').write_text('{}')
            with self.assertRaisesRegex(ValueError, 'INPUT_INTEGRITY_HOLD'):
                verify_inputs(p, {'input.json': '0' * 64})

    def test_missing_semantic_review_holds(self):
        self.claim.pop('semantic_review')
        self.assertEqual(self.result()['verification_status'], U)


if __name__ == '__main__':
    unittest.main()
