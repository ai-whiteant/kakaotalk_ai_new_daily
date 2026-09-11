# Kakao ai news — Phase 4 One-Time Production Send Gate v1.0

- Canonical Root: `C:\Vibe Coding\kakaotalk_ai_new_daily`
- 기준: Phase 3 독립 검토 PASS
- 목적: Phase 2.3에서 검증 완료된 고정 8건을 `[TEST]` 표식 없이 KakaoTalk `나에게 보내기`로 **1회 실제 발송**
- 자동 스케줄 / 반복 LIVE: 금지
- 새 뉴스 검색: 금지
- 기존 Tavily / Gemini / Kakao 인증·운영 설정 변경: 금지

## 1. 절대 원칙

1. Phase 3 TEST journal과 receipt를 삭제·수정하지 않는다.
2. `python -m news.phase3 --send-test`를 재실행하지 않는다.
3. Phase 4는 별도의 `PRODUCTION_ONCE` 모드와 별도 journal을 사용한다.
4. 입력은 `outputs/phase2_3/samples/safe_content.json` 8건만 사용한다.
5. 현재 시점의 최신 뉴스라고 표현하지 않는다.
6. 헤더에 고정 검증 기간을 표시한다:
   `2026.09.02 21:30 ~ 09.09 21:30 KST | 검증 완료 브리핑`
7. `[TEST]` 문자열은 실제 발송 콘텐츠에서 0건이어야 한다.
8. HOLD/REJECT 재진입 0.
9. 원문 URL 변경 0.
10. `safe_*` 범위 밖의 새 사실 생성 금지.
11. 자동 재시도 금지.
12. 사용자 승인 없는 Git push 금지.
13. 스케줄 등록·자동 LIVE 활성화 금지.

## 2. 구현 방향

기존 Phase 3의 검증·분할·Kakao 인증 흐름은 재사용한다.
새 인증 모듈을 만들지 않는다.

권장:
- `news/phase4.py`
- 필요 시 `news/phase4_briefing.py`
- 필요 시 `news/phase4_kakao.py`
- `news/test_phase4.py`

가능하면 Phase 3 코드를 최소 변경/재사용한다.

## 3. Production Once 메시지

첫 메시지 예시:

```text
📢 Kakao AI News
2026.09.02 21:30 ~ 09.09 21:30 KST
검증 완료 AI 핵심 뉴스 8건입니다.
```

각 기사:
- 제목
- 핵심 내용
- 왜 중요한가
- 교육적 시사점: null이 아닐 때만
- 수업 활용: null이 아닐 때만
- 원문

이번 주 AI 한눈에 보기 포함.

200자 텍스트 템플릿 제한은 기존 Phase 3의 UTF-16 계산과 논리 단위 분할을 재사용한다.

## 4. 실제 발송 전 Gate

모두 PASS해야 한다.

- 입력 SHA가 승인된 Phase 2.3 safe_content와 일치
- 기사 8건
- FINAL_VERIFIED 계열만
- TEST 문자열 0
- production mode 명시
- live scheduler 0
- 원문 URL 8/8
- secret 0
- 기존 168 tests PASS
- Phase 4 신규 tests PASS
- 기존 API 설정 hash 불변
- 기존 Phase 3 TEST journal/receipt 보존
- 별도 production journal 미존재 확인

하나라도 실패하면 실제 발송하지 않고 HOLD.

## 5. 중복·재전송 방지

별도 journal:
`.state/phase4_production_once_<input_sha256>.json`

exclusive create 사용.

이미 존재하면 자동 재전송 금지.
불확실한 전송 상태에서도 자동 재시도 금지.
재발송은 사용자의 별도 명시 승인 필요.

## 6. Kakao 실제 발송

대상:
KakaoTalk `나에게 보내기`

기존:
- `news.daily.config`
- `State`
- refresh
- api
- talk_message scope
를 그대로 재사용한다.

성공 조건:
각 메시지 `result_code == 0`.

receipt에는:
- sequence
- result_code
- http_success
- mode=`PRODUCTION_ONCE`
- messages_planned
- messages_sent
만 저장.

토큰 / 헤더 / 원시 인증 응답 저장 금지.

## 7. 신규 테스트

최소:
1. production header
2. TEST marker 0
3. 기사 8건 유지
4. safe-only
5. URL 8개 유지
6. null 섹션 생략
7. 200 UTF-16 이하
8. sequence unique
9. input hash binding
10. existing Phase 3 journal preservation
11. production journal exclusive create
12. replay blocking
13. uncertain delivery retry blocking
14. secret masking
15. API config unchanged
16. scheduler unchanged
17. LIVE schedule 0
18. Kakao response result_code validation
19. receipt non-sensitive
20. dry-run no API call

## 8. 실행 절차

### Phase 4A
구현 + dry-run + 기존 168 tests + 신규 tests.

### Phase 4B
Phase 4A PASS 시:
사용자가 이미 승인한 이번 1회 실제 발송을 수행한다.

권장 명령:
`python -m news.phase4 --send-production-once`

자동 스케줄은 만들지 않는다.

## 9. 필수 산출물

- `PHASE4_EXECUTION_REPORT.md`
- `PHASE4_RESULT_PACKAGE.zip`

권장:
- `outputs/phase4/kakao/mobile_preview.md`
- `outputs/phase4/kakao/production_receipt.json`
- `outputs/phase4/quality/quality_gate.json`
- `outputs/phase4/logs/tests_existing.txt`
- `outputs/phase4/logs/tests_phase4.txt`
- `outputs/phase4/logs/tests.txt`
- `outputs/phase4/logs/audit.json`
- `outputs/phase4/logs/run.json`

## 10. 최종 판정

### PASS
- production-once 메시지 생성 PASS
- 기존 168 + 신규 tests PASS
- Kakao actual send PASS
- TEST marker 0
- secret 0
- automatic LIVE schedule 0

### DELIVERY_HOLD
콘텐츠·테스트는 PASS지만 인증/scope/API 문제로 실제 발송 보류.

### FAIL
안전성/무결성 위반.

## 11. 종료 후

이번 1회 발송 성공 후에도 자동 LIVE 반복 운영은 활성화하지 않는다.
자동화는 별도 운영 승인 단계에서 다룬다.
