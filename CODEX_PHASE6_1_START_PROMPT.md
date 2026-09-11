Kakao ai news Phase 6.1 Original-Link Correction Gate를 구현하고 실행하라.

가장 먼저:
1. AGENTS.md
2. SESSION_HANDOFF.md
3. Kakao_ai_news_CODEX_PHASE6_1_ORIGINAL_LINK_CORRECTION_v1.0.md
4. outputs/phase5
5. outputs/phase6
을 읽어라.

Canonical Root:
C:\Vibe Coding\kakaotalk_ai_new_daily

확정된 문제:
Phase 6 API 발송은 10/10 성공했으나 사용자가 실제 KakaoTalk에서 `원문 보기`를 누르면 Kakao Developers 페이지가 열렸다.

목표:
원문 버튼 링크 문제를 교정하되 기존 Phase 3/4/6 journal과 증거를 절대 삭제·변경하지 않는다.

변경:
- 헤더의 서비스 안내 버튼 제거
- 주간요약 서비스 안내 버튼 제거
- 기사 8개 원문 보기 버튼만 유지
- 각 기사 web_url/mobile_web_url은 Phase 5 safe_original_url과 정확히 동일
- 실제 전송 직전 outbound template URL을 비민감 audit로 저장

중요:
전체 10개를 바로 다시 보내지 마라.

먼저 Phase 6.1A:
기사 1번만 `[LINK TEST]` 표시로 실제 발송하는 smoke test 기능을 구현한다.
기존 252 tests + Phase 6.1 신규 tests를 먼저 전부 PASS시킨다.
그 뒤 사용자가 이미 승인한 smoke-test 1회만 실행한다.

Smoke test 성공 후:
`SMOKE_API_PASS_USER_CONFIRMATION_REQUIRED`
상태로 종료하고 사용자가 휴대전화에서 원문 링크가 실제 NYC교육청 페이지로 열리는지 확인할 때까지 전체 10개 발송을 하지 마라.

금지:
- Phase 6 재실행
- 기존 journal 삭제
- 자동 재시도
- 전체 10개 즉시 재발송
- Tavily 검색
- Gemini 생성
- API 설정 변경
- LIVE/스케줄
- git push

필수 생성:
PHASE6_1_LINK_CORRECTION_EXECUTION_REPORT.md
PHASE6_1_LINK_CORRECTION_RESULT_PACKAGE.zip

마지막 출력:
1. PRE-FLIGHT
2. existing tests
3. Phase 6.1 tests
4. outbound article links audit
5. header button count
6. overview button count
7. article button count
8. smoke API result
9. smoke target URL
10. final gate state
11. report/ZIP paths
12. git status
