# Phase 5 Compact Kakao Format

Canonical Root: C:\Vibe Coding\kakaotalk_ai_new_daily

Offline run: `python -m news.phase5_compact --display-date 2026-09-12`. No send option exists. The date is an explicit presentation date; the original September 2–9 verified period remains fixed.

This is a fixed-eight-pool formatter with reviewed compact text and explicit event-to-source labels. Input goes through the unchanged Phase 3 SHA and FinalVerification checks. New facts are not generated, and the supplied seed/preview and safe input are never overwritten.

Output: header + eight article text templates + weekly overview = ten messages. Article buttons use safe_original_url exactly for both web/mobile URLs. Header and overview retain the existing service link. No article source URL appears inside template text; Markdown preview renders the button as a clickable link.

Absolute maximum is 196 UTF-16 units. Whole-sentence two-part fallback is supported; an unsplittable sentence raises HOLD. The current eight articles need no fallback. A fallback causing more than ten messages does not silently pass the current ten-message gate.

The offline link gate verifies structure and approved URL identity only. Kakao product link/domain acceptance has NOT been tested. Before any future real compact send, separately verify all article domains are allowed by the existing app; do not assume these eight new button URLs work because earlier service-link messages succeeded. No domain/auth configuration is changed here.

Tests: existing 192 plus 30 new. Compression review and seed before/after are in outputs/phase5/quality/compression_review.json. Semantic review was performed by the implementer; independent UX/content review remains pending.

Result package is a delta and requires existing Phase 1–4 code and approved input. No secret, .state, journal, credential, Git internals or virtual environment is included. Actual delivery requires a separate user-approved gate after independent review.
