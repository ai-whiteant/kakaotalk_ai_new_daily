# Phase 2.1 Guard calibration and dedup hardening

The original Phase 1 and Phase 2 code, credentials, model settings and outputs are
unchanged. Phase 2.1 is a separate TEST entry point using the existing Gemini client.
No Tavily searches, Kakao calls, schedule changes, score-weight changes or push.

```powershell
python -m unittest news.test_phase21 news.test_phase2 news.test_phase1 news.test_daily -v
python -m news.phase21 --mode TEST --input <fixed-candidates.json> --previous <phase2-run-dir> --config <existing-config.json>
```

The SHA-256 must equal `490b4608eb820ed679ee41a6dcfd969f22d032c493837c3ca220eee53d389e40`.
Mismatch is HOLD before credentials or Gemini calls. Model is injected from the
existing GEMINI_MODEL value; the API client/authentication implementation is reused.

Guard findings include code, value, status, output_field, reason, matched_input and
candidate_ids. All related candidate titles/snippets/raw text are considered.
Multi-token capitalized names are consumed as phrases. Explicit bilingual aliases
are limited and source-dependent (World Bank is not globally allowed). Generic roles,
transitions and AI adjectives are nonblocking unless explicitly named/called as an object.
This is conservative lexical evidence checking, not a complete named-entity or truth model.

ISO/dotted/slashed numeric dates and Korean year/month/day dates are compared whole;
their components are not used to excuse a newly invented calendar date. Ordinal grade
8th/grade 8 is supported only in a matching grade context. Equal quantities with different
units/spellings go to VERIFY, not an unsupported AUTO_HOLD or unqualified PASS.
English count words one–ten are normalized only beside explicit count nouns.
Other natural-language dates, currency semantics and arbitrary paraphrases still need review.

PASS means supported lexical evidence or a nonfactual expression. VERIFY preserves
ambiguous transformations and model-reported risk. AUTO_HOLD means a specific
unsupported fact/URL or certainty upgrade was detected. Model risk is retained verbatim:
separating a model's high flag into VERIFY does not erase that flag or approve content.
Any AUTO_HOLD keeps the content run HOLD. Verification targets and all findings remain
available to later independent review. A lower count alone is never the success criterion.

Dedup calls operate independently on each proposed pair, using exact candidate IDs
and an enum of extractive title/snippet evidence. Invalid pairs do not discard successful
neighbors. SAME_EVENT at confidence >=0.9 may merge only with complete-link evidence;
FOLLOW_UP stays separate with reciprocal related_events links. No direction is invented.
Evidence selection proves traceability, not semantic correctness; merged pairs require review.
Explicit opinion/expert-reaction title markers versus an originating report preserve
FOLLOW_UP separation even when the model initially says SAME_EVENT. The prior relation
and reason are retained in the review artifact. Newly split events are reanalyzed;
analyses whose event membership is unchanged are reused without additional API calls.

Before/after includes two distinct comparisons: the same 50 legacy analyses under the
new Guard, and a new Gemini run on the identical 57 candidates. Legacy high flags may
already be modified by the old Guard, so original raw model risk cannot be reconstructed.
`phase21_recheck` permits final deterministic recalibration of saved Phase 2.1 outputs
without extra API calls, preserving original_model_risk and removing exact appended targets.
