# Phase 3 Briefing & Kakao TEST Gate

Canonical Root: C:\Vibe Coding\kakaotalk_ai_new_daily

Use `python -m news.phase3` for offline dry-run and all 168 tests. The sole input is the pinned Phase 2.3 safe_content.json eight-article pool. The fixed September 2–9 period is preserved; this is not a fresh news run.

`python -m news.phase3 --send-test` is an explicitly authorized self-message TEST, conditional on the dry-run gate. One logical TEST was already completed successfully. Its exclusive local journal blocks replay; do not remove the journal or repeat delivery without reviewing the prior receipt and obtaining authorization for another TEST. No LIVE mode exists.

Existing daily.config / State / refresh / api remain unchanged. The encrypted refresh state may rotate through the existing flow. A separate non-sensitive journal under .state prevents duplicate Phase 3 runs, including partial/uncertain delivery; automatic retries are disabled. No token or raw response is stored in the public receipt.

Text templates are limited to 200 characters per Kakao official documentation, checked 2026-09-12: https://developers.kakao.com/docs/ko/message-template/default . Existing conservative UTF-16 counting is retained. Whole semantic fields and URLs are kept intact in contiguous numbered article parts. A field too long for one part causes HOLD rather than truncation. The existing registered button URL is preserved; source URLs appear unchanged in the text.

The weekly overview is a fixed reviewed synthesis with eight-pool provenance, marked as interpretation/observation. No Gemini generation or new Tavily collection occurs. Phase 3 is scoped to this pinned pool, not a general future news pipeline.

Package is a delta: source, tests, briefing, preview, receipt, quality/audit, baseline hashes and diff. Existing Phase 1–2.3 input/code and Python dependencies are required for replay. Credentials, encrypted state, Git internals and virtual environments are not included.

Phase 3 independent review remains pending. LIVE and schedules require a later separate approval.
