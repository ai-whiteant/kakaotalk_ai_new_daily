# Kakao ai news — Phase 6 Compact Production-Once Send Gate v1.0

- Canonical Root: `C:\Vibe Coding\kakaotalk_ai_new_daily`
- 선행 조건: Phase 5 독립 검토 PASS
- 목적: Phase 5에서 검증된 compact 10개 메시지를 KakaoTalk `나에게 보내기`로 1회 실제 발송
- 자동 반복 LIVE: 금지
- 기존 Phase 4 production-once journal: 보존
- Phase 6 전용 journal 사용

## 1. 수동 사전조건

Kakao Developers:
`앱 → 제품 링크 관리 → 웹 도메인`

아래 8개 등록 확인:
- https://www.schools.nyc.gov
- https://gottheimer.house.gov
- https://www.brookings.edu
- https://www.court.gov.cn
- https://www.navercorp.com
- https://blogs.nvidia.com
- https://huggingface.co
- https://news.samsung.com

기존 등록 도메인을 삭제하지 않는다.

## 2. 입력

`outputs/phase5/compact/mobile_messages.json`
및
`outputs/phase5/compact/compact_items.json`

Phase 5 결과의 10개 compact 메시지를 그대로 사용한다.
새 compact 문안을 재생성하지 않는다.

## 3. 실제 발송 조건

발송 전 모두 PASS:
- Phase 5 package integrity PASS
- 기존 222 tests PASS
- Phase 6 신규 tests PASS
- compact messages = 10
- article buttons = 8
- source URLs = 8/8
- TEST marker = 0
- max UTF-16 <= 196
- secret = 0
- Phase 3 TEST journal 보존
- Phase 4 production journal 보존
- Phase 6 journal 미존재
- scheduled LIVE = 0

## 4. 링크 Preflight

실제 send 전에 템플릿 10개를 dry-run 생성한다.

각 기사:
- text: compact message
- button title: `원문 보기`
- web_url = safe_original_url
- mobile_web_url = safe_original_url

헤더/overview:
- 기존 안전한 서비스 링크 또는 기존 Phase 3/4 방식 유지
- 기사별 외부 링크와 혼동하지 않는다.

실제 API가 도메인 미등록/템플릿 링크 오류를 반환하면:
`COMPACT_SEND_HOLD_LINK_DOMAIN`
으로 중단한다.

자동으로 제품 링크 설정을 바꾸지 않는다.
다른 API 설정도 변경하지 않는다.

## 5. 실제 발송

권장 실행:
`python -m news.phase6 --send-compact-production-once`

대상:
KakaoTalk `나에게 보내기`

성공 조건:
- 10/10 messages API success
- 각 result_code == 0
- 기사 버튼 8개 구성
- `[TEST]` 0
- mode = COMPACT_PRODUCTION_ONCE

## 6. 재전송 방지

별도 journal:
`.state/phase6_compact_production_once_<input_hash>.json`

exclusive create.

이미 존재하면 재실행 차단.
불확실 응답 자동 재시도 금지.
재발송은 별도 사용자 승인 필요.

## 7. 기존 기록 보호

절대 삭제/수정 금지:
- Phase 3 TEST journal
- Phase 3 test receipt
- Phase 4 production-once journal
- Phase 4 production receipt

## 8. 테스트

Phase 6 신규 테스트 최소:
1. compact 10개 고정
2. article 8개 고정
3. button 8개
4. button_title 정확히 `원문 보기`
5. web_url safe_original_url
6. mobile_web_url safe_original_url
7. TEST marker 0
8. mode COMPACT_PRODUCTION_ONCE
9. max UTF-16 <=196
10. article order 1~8
11. source label 보존
12. Phase 5 input hash binding
13. old journal preservation
14. Phase 6 exclusive journal
15. replay blocking
16. automatic retry blocking
17. link/domain API error → HOLD
18. auth/scope API error → HOLD
19. other API settings unchanged
20. secret masking
21. receipt non-sensitive
22. scheduled LIVE 0
23. dry-run actual API call 0
24. send path exactly 10 calls when no error
25. all result_code validation

기존 222 tests를 모두 재실행한다.

## 9. 실제 발송 결과 상태

- `COMPACT_SEND_PASS`
- `COMPACT_SEND_HOLD_LINK_DOMAIN`
- `COMPACT_SEND_HOLD_AUTH`
- `COMPACT_SEND_HOLD_SCOPE`
- `COMPACT_SEND_HOLD_API`
- `COMPACT_SEND_FAIL`

## 10. 필수 산출물

- `PHASE6_COMPACT_SEND_EXECUTION_REPORT.md`
- `PHASE6_COMPACT_SEND_RESULT_PACKAGE.zip`

권장:
- `outputs/phase6/kakao/production_receipt.json`
- `outputs/phase6/kakao/mobile_preview.md`
- `outputs/phase6/quality/quality_gate.json`
- `outputs/phase6/logs/tests_existing.txt`
- `outputs/phase6/logs/tests_phase6.txt`
- `outputs/phase6/logs/tests.txt`
- `outputs/phase6/logs/audit.json`
- `outputs/phase6/logs/run.json`

ZIP 제외:
`.state`, token, secret, config credentials, .git, venv.

## 11. 종료 조건

PASS:
- 기존 222 tests PASS
- Phase 6 tests PASS
- 10/10 actual send success
- 8 article buttons
- TEST marker 0
- scheduled LIVE 0
- secret 0

발송 후에도 자동 스케줄/LIVE는 켜지 않는다.
