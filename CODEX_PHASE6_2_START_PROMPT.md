Kakao ai news Phase 6.2 Stable Link Gateway Gate를 구현하고 실행하라.

Canonical Root:
C:\Vibe Coding\kakaotalk_ai_new_daily

가장 먼저 AGENTS.md, SESSION_HANDOFF.md, Phase 6.2 사양을 읽어라.

목표:
매주 바뀌는 외부 뉴스 도메인을 Kakao 버튼에 직접 넣지 않고,
Vercel 고정 Gateway 도메인 1개만 사용한다.

제공된 link-gateway/ seed를 검토·보완하라.
Phase 2.3 safe_content 8건과 data/targets.json이 정확히 일치하는지 검증하라.

보안:
- arbitrary url redirect 금지
- event_id allowlist only
- https target only
- unknown/invalid event 차단
- secret 0

기존 282 tests + Phase 6.2 신규 tests를 실행하라.

Vercel 배포:
가능하면 사용자의 기존 Vercel 계정에 link-gateway를 신규 project로 배포하라.
배포가 인증/CLI 문제로 불가하면 DEPLOYMENT_HOLD로 정확히 보고하고 설정을 임의 변경하지 마라.

배포 성공 시 production domain을 확보하고:
- /health
- 8개 /r/event_id
- invalid/unknown
을 실제 HTTP로 검증하라.

그 production gateway domain 하나를 Kakao Developers 제품 링크에 등록해야 한다고 사용자에게 명확히 표시하라.

Kakao smoke는 Gateway domain 등록 확인 전 실행하지 마라.
등록 확인 후에도 1번 기사 smoke 1회만 발송하고 전체 10개는 보내지 마라.

기존 Phase 3/4/6/6.1 journal 삭제 금지.
Tavily/Gemini 재실행 금지.
scheduled LIVE 금지.
git push 금지.

필수:
PHASE6_2_GATEWAY_EXECUTION_REPORT.md
PHASE6_2_GATEWAY_RESULT_PACKAGE.zip

마지막:
1 PRE-FLIGHT
2 gateway tests
3 existing tests
4 deployment status
5 production gateway domain
6 redirect checks
7 Kakao domain registration required
8 smoke send status
9 final gate
10 report/ZIP
11 git status
