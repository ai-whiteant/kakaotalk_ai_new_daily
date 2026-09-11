Kakao ai news 프로젝트 Phase 6 Compact Production-Once Send Gate를 실행하라.

가장 먼저:
- AGENTS.md
- SESSION_HANDOFF.md
- Kakao_ai_news_CODEX_PHASE6_COMPACT_PRODUCTION_SEND_v1.0.md
- outputs/phase5 결과
를 읽어라.

Canonical Root:
C:\Vibe Coding\kakaotalk_ai_new_daily

사용자가 Kakao 제품 링크 관리에 8개 원문 도메인을 등록한 후 실행하는 단계다.

이번 목표:
Phase 5에서 독립 검토 PASS한 compact 10개 메시지를
KakaoTalk `나에게 보내기`로 딱 1회 실제 발송한다.

기사별:
- 원문 보기 버튼
- web_url = safe_original_url
- mobile_web_url = safe_original_url

중요:
- Phase 5 compact 문안 재생성 금지
- 새 Tavily 검색 금지
- Gemini 재생성 금지
- API 설정 변경 금지
- 기존 Phase 3/4 journal/receipt 삭제 금지
- 자동 재시도 금지
- scheduled LIVE 금지
- 승인 없는 git push 금지

기존 222 tests와 Phase 6 신규 tests를 실행한다.

도메인/링크 관련 API 오류가 나오면 다른 설정을 바꾸지 말고
COMPACT_SEND_HOLD_LINK_DOMAIN 으로 중단한다.

성공 시:
10/10 result_code 0
8개 기사 원문 버튼
TEST marker 0
scheduled LIVE 0

반드시 생성:
PHASE6_COMPACT_SEND_EXECUTION_REPORT.md
PHASE6_COMPACT_SEND_RESULT_PACKAGE.zip

마지막 출력:
1. PRE-FLIGHT
2. domain/link preflight
3. 기존 tests
4. Phase 6 tests
5. actual compact Kakao send 결과
6. planned/sent
7. article button count
8. TEST marker count
9. scheduled LIVE count
10. 최종 판정
11. 보고서/ZIP 경로
12. git status
