# Phase 6.1A Original Link Smoke

One NYC [LINK TEST] message was sent successfully. State: SMOKE_API_PASS_USER_CONFIRMATION_REQUIRED. User confirmed mobile navigation FAILED: Kakao Developers or another page opened. Final gate HOLD. Do not send again. Do not repeat the smoke or delete any journal.

The saved Phase 5 text is unchanged except the smoke marker. Articles now explicitly declare a single buttons entry with title 원문 보기 and the exact safe_original_url in both web/mobile and the top-level content link. The same template is audited immediately before transport; only URLs, hashes and non-sensitive fields are logged.

`python -m news.phase6_1` is a dry-run. The already completed entry point is `python -m news.phase6_1 --domains-confirmed --send-link-smoke-test`. Its separate exclusive smoke journal blocks replay, including uncertain outcomes.

Corrected ten-item preview removes the header/overview service link and buttons. These two entries are preview-only: the default Kakao text API requires link, and omitting button_title can create a default button. No unsupported buttonless payload is sent. Full-send remains disabled even with a confirmation flag until a supported buttonless transport is established and the user confirms the smoke click. Phase 6.1B is not implemented or exercised as a successful ten-call flow in this 6.1A task.

Tests: 252 existing + 30 new, including explicit URL audit, one-call smoke, replay/timeout/secret/result guards, and full-send blocking. Actual phone navigation cannot be proven by unit tests or API acceptance.

Package is a delta, requiring the existing Phase 1–6 source and pinned Phase 5 outputs. No credentials, auth headers, .state, journal, Git internals or venv included. No account settings, schedules or existing evidence changed.
