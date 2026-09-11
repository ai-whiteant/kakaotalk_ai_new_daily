# Phase 2 TEST

Phase 1 baseline: `ec09427ed94b336ac5c77463b45a40fa6c61a419`.
All Phase 2 files are additive. There are no Kakao calls, scheduler edits or LIVE mode.

Install `news/phase2_requirements.txt` in a separate environment in addition to the
existing requirements when running the complete regression suite.

```powershell
python -m unittest news.test_phase2 news.test_phase1 news.test_daily -v
# Supply GEMINI_MODEL through the environment; no model name is hard-coded.
python -m news.phase2 --mode TEST --input <Phase1-candidates.json> --config <existing-config.json>
```

The Gemini key uses the environment first, then the existing JSON config read-only.
Only that credential is used; billing tier cannot be inferred from a successful API response.
The operator identifies the configured project as Paid. Existing authentication is untouched.

## Event grouping

Input uses the 12-field Phase 1 format with JSON Schema validation. Exact normalized
titles AND identical nonempty snippets within 48 hours permit a rule merge.
Shared organization aliases or title tokens within 48 hours propose ambiguous pairs.
These heuristics are conservative candidate generation, not exhaustive multilingual deduplication.
Gemini classifies SAME_EVENT/FOLLOW_UP/DIFFERENT_EVENT. SAME_EVENT needs confidence >=0.9
and verbatim evidence from both inputs. Uncertain pairs remain separate. Complete-link
grouping prevents transitive merges without evidence for every pair of group members.
Up to 120 ambiguous pairs are evaluated in batches of 8; any excess is logged as unresolved.
Representative selection uses a limited domain preference list and preserves every source.
The model's representative preference is recorded, not blindly applied.
event_date remains null: a publication timestamp is not proof of an event date.

## Analysis and safety

Every event is analyzed; there is no final 8–12 article selection. All component scores
and total are validated (30+20+15+15+10+10). Schema enforcement uses jsonschema 4.26.0,
with required fields, ranges, null handling, size limits and no unexpected fields.
The same JSON Schema is sent to Gemini via responseJsonSchema and checked locally.
Fact-check targets and uncertainties are required; educational suggestions may be null.
Sources are explicitly untrusted data in the system instruction, not tool instructions.

Lexical guards flag unsupported numbers/dates, URLs, selected named entities/model/policy
names and stronger certainty than qualified input. This is not full semantic fact verification:
spelled-out numbers, paraphrases, translations and arbitrary Korean names can evade detection;
benign translations and unit conversions can produce false positives. High-risk outputs are
kept only in the high_risk artifact with HOLD and appended verification targets. They are
excluded from the normal analysis artifact. Even a low-risk output is NOT_FACT_CHECKED.

## Failures and limits

400/401/403/404 stop without retry. 429 uses Retry-After; 5xx/network errors use bounded
backoff. Maximum 3 HTTP attempts per logical call, including at most one schema retry.
Retry-After above 60 seconds defers the operation as a failure instead of sleeping longer
or retrying earlier than the provider requested. Total run limit is 150 HTTP attempts.
Per-event schema/transient failures are logged and processing continues. Auth or secret
errors stop the run. High-risk results make the overall run HOLD; partial nonfatal failures
or low-confidence dedup decisions make it WARN. No output is promoted to a send queue.

Each run writes separate events, dedup decisions, analysis, high-risk and log files under
`outputs/phase2/<run-id>/`. Only sanitized error codes are logged, never error bodies or
authorization headers. The packaging audit checks all known local secrets and ZIP contents.

Official references checked 2026-09-09:
- https://ai.google.dev/api/generate-content
- https://ai.google.dev/gemini-api/docs/structured-output
- https://ai.google.dev/gemini-api/docs/troubleshooting
