# AGENTS.md — Kakao ai news

## 1. Project Root
Canonical project root:
`C:\Vibe Coding\kakaotalk_ai_new_daily`

Do not create a second active development root for this project.
Historical or backup copies may exist, but all new development must continue from the canonical project root.

## 2. Read Order
Before modifying code, read in this order when present:

1. `SESSION_HANDOFF.md`
2. `Kakao_ai_news_PROJECT_INSTRUCTIONS_FINAL.md` or the project instruction source available in the project
3. `Kakao_ai_news_WORKFLOW_v1.0.md`
4. `Kakao_ai_news_AUTOMATION_SPEC_v1.0.md`
5. The latest Phase implementation/gate document
6. The latest Phase execution report
7. `references/*.md`

If instructions conflict, follow the higher-priority project instruction.

## 3. Architecture Boundaries
Preserve the established separation:

Tavily
→ news discovery / source candidates

Gemini Paid API
→ classification / dedup support / importance scoring / summarization / implications

Kakao API
→ final KakaoTalk delivery

A failure in one API must not trigger arbitrary configuration changes in the others.

## 4. Change Policy
- Preserve the last known-good baseline before making changes.
- Make the smallest change needed.
- Do not redesign a working feature without an explicit reason.
- Run regression tests before declaring a phase complete.
- Do not advance to the next phase until the current phase gate is independently reviewed when the phase instructions require it.
- Do not change scoring weights, thresholds, date windows, production schedules, API models, or authentication modes unless the user explicitly approves the change.

## 5. Security
Never commit or print actual:
- API keys
- access tokens
- refresh tokens
- client secrets
- private keys
- credential files
- `.env` contents

Keep secrets outside Git. Mask secrets in logs and reports.

## 6. Git Policy
- Work only from the canonical project root.
- Before work: `git status -sb`, `git pull` only when the worktree is safe.
- At the end of a work session: update `SESSION_HANDOFF.md`.
- Do not run `git push`, force-push, destructive reset, history rewrite, or branch deletion without explicit user approval.
- Result-package ZIP files and local session-transfer folders are not source-of-truth files and should not be committed unless explicitly approved.

## 7. Kakao ai news Content Rules
- Quality is more important than article count.
- Prefer official / primary sources for important facts.
- Do not treat search snippets as sufficient evidence for critical claims.
- Do not invent or strengthen claims beyond the source.
- Preserve the distinction between fact, interpretation, and educational implication.
- Final export must use verified safe content fields when a phase defines them.
- Do not send Kakao messages or enable LIVE operation without explicit approval.

## 8. Current Phase State
Phase 2.3 independent review: PASS.
Phase 2 overall content gate: PASS.
Phase 3 is not started yet.

Before Phase 3, complete the home/office continuity and GitHub synchronization gate for the canonical project root.

## 9. Quality Gate
Use PASS / WARN / HOLD / FAIL where useful.

A task is not complete until:
- required tests pass,
- secrets are not exposed,
- expected outputs exist,
- Git status is reviewed,
- the handoff file is updated.
