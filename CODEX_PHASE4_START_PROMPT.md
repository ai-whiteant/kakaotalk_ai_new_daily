Kakao ai news 프로젝트를 현재 노트북에서 마무리하기 위해 **1회 실제 Kakao 메시지 발송**을 수행하라.

가장 먼저 저장소 루트의 `AGENTS.md`, `SESSION_HANDOFF.md`, `Kakao_ai_news_CODEX_PHASE4_ONE_TIME_PRODUCTION_SEND_v1.0.md`를 읽어라.

Canonical Root:
`C:\Vibe Coding\kakaotalk_ai_new_daily`

확정 상태:
- Phase 2.3 독립 검토 PASS
- Phase 3A PASS
- 기존 140 + Phase 3 신규 28 = 168/168 PASS
- Phase 3 Kakao TEST 실제 발송 28/28 PASS
- Phase 3 독립 검토 PASS

중요:
Phase 3 TEST는 이미 실제 Kakao API를 호출했다.
`python -m news.phase3 --send-test`를 재실행하지 마라.
기존 Phase 3 journal/receipt를 삭제하거나 수정하지 마라.

이번 목표:
`outputs/phase2_3/samples/safe_content.json`의 검증 완료 8건을 `[TEST]` 없이 KakaoTalk `나에게 보내기`로 딱 1회 실제 발송한다.

메시지에는 현재 최신 뉴스라고 쓰지 말고:
`2026.09.02 21:30 ~ 09.09 21:30 KST | 검증 완료 브리핑`
을 명시하라.

Phase 3의 safe-only, URL 보존, null 생략, 200 UTF-16 제한, 논리 단위 분할, secret 차단, 기존 Kakao 인증 흐름을 재사용하라.

별도 production-once journal을 사용해 중복/재전송을 차단하라.
자동 재시도 금지.
자동 스케줄/LIVE 반복 운영 금지.
Tavily/Gemini/Kakao 설정 변경 금지.
새 뉴스 검색 금지.
Gemini 재생성 금지.
HOLD/REJECT 재진입 금지.
승인 없는 git push 금지.

기존 168개 테스트와 Phase 4 신규 테스트를 모두 실행한다.
dry-run gate PASS 후 이번 사용자 승인에 따라 실제 production-once 발송을 수행한다.

반드시 생성:
PHASE4_EXECUTION_REPORT.md
PHASE4_RESULT_PACKAGE.zip

마지막에는 다음만 출력:
1. PRE-FLIGHT
2. Phase 4 quality gate
3. 기존 tests
4. Phase 4 신규 tests
5. actual Kakao send 결과
6. messages planned/sent
7. TEST marker count
8. scheduled LIVE count
9. 최종 판정
10. 보고서/ZIP 경로
11. git status
