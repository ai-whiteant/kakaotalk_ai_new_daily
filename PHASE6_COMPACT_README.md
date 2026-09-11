# Phase 6 Compact Production-Once Gate

Canonical Root: C:\Vibe Coding\kakaotalk_ai_new_daily

`python -m news.phase6` runs 252 tests and a dry-run with the saved Phase 5 templates. It never regenerates compact production text. Regression fixtures may independently exercise older formatters without modifying stored outputs.

Actual send remains blocked pending the user's confirmation that all eight source domains were saved in Kakao Developers. After that confirmation, the authorized entry point is `python -m news.phase6 --domains-confirmed --send-compact-production-once`. Do not set --domains-confirmed based on elapsed time or an unsubmitted UI default.

Phase 5 package and input SHA values are pinned. The Phase 6 exclusive journal is distinct from all older journals. Any journal presence, including partial or uncertain delivery, blocks replay; no automatic retry. Never remove old journals to enable this run.

Authentication reuses daily.config, State and refresh. The existing daily.request suppresses error bodies; a narrowly scoped send transport classifies bounded Kakao HTTP error JSON in memory and records only safe status/code. Domain/link errors stop with COMPACT_SEND_HOLD_LINK_DOMAIN. Other unknown errors stop safely without retry. No account configuration changes are made.

The reviewed Phase 5 templates include eight source buttons and the original service links on header/overview. Domain registration confirmation and actual Kakao acceptance are distinct. No API acceptance has been tested yet.

No LIVE schedules, new news search, Gemini regeneration, settings changes or push. Package is a review delta; existing project and local credentials are required. No credential, .state journal or encrypted runtime state is packaged.
