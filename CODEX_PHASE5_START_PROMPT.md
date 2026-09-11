Kakao ai news 프로젝트의 **Phase 5 Compact Kakao Format UX Gate**를 구현하고 실행하라.

가장 먼저:
1. AGENTS.md
2. SESSION_HANDOFF.md
3. Kakao_ai_news_CODEX_PHASE5_COMPACT_KAKAO_FORMAT_v1.0.md
를 읽어라.

Canonical Root:
C:\Vibe Coding\kakaotalk_ai_new_daily

목표:
기존 검증 엔진·safe_content·Phase 3/4 발송 기록을 그대로 보존하면서,
Kakao 최종 표시 형식만 다음처럼 개선한다.

날짜
→ 번호. 제목
→ 한 문단 핵심 요약
→ (출처)▼
→ 원문 보기 버튼

현재 검증 완료 8건 기준:
헤더 1 + 기사 8 + 이번 주 요약 1 = 총 10개 메시지 목표.

중요:
- outputs/phase2_3/samples/safe_content.json 8건만 사용
- safe_* 원본 수정 금지
- 새 Tavily 검색 금지
- Gemini 재생성 금지
- 실제 Kakao 발송 금지
- Phase 3/4 journal/receipt 수정 금지
- API 설정 변경 금지
- LIVE/스케줄 금지
- git push 금지

기사 메시지:
- 최대 196 UTF-16
- URL은 본문에 넣지 않고 Kakao link로 연결
- button_title = 원문 보기
- link URL = safe_original_url
- source_label은 승인된 검증 출처 매핑 사용
- 문자 중간 절단 금지
- 초과 시 문장 단위 압축 또는 fallback

기존 192개 테스트를 전부 재실행하고 Phase 5 신규 테스트를 추가하라.

반드시 생성:
PHASE5_COMPACT_FORMAT_EXECUTION_REPORT.md
PHASE5_COMPACT_FORMAT_RESULT_PACKAGE.zip

마지막 출력:
1. PRE-FLIGHT
2. 기존 tests
3. Phase 5 신규 tests
4. compact 메시지 수
5. 최대 UTF-16 길이
6. URL/button 검증
7. actual Kakao send count (반드시 0)
8. scheduled LIVE count (반드시 0)
9. 최종 판정
10. 보고서/ZIP 경로
11. git status
