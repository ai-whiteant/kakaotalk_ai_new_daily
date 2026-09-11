# Kakao ai news — Phase 6.1 Original-Link Correction Gate v1.0

- Canonical Root: `C:\Vibe Coding\kakaotalk_ai_new_daily`
- 선행 상태:
  - Phase 5 Compact UX Gate: PASS
  - Phase 6 compact API send: 10/10 API acceptance
  - 사용자 실제 화면 확인: `원문 보기` 클릭 시 Kakao Developers 페이지가 열림 → 링크 UX FAIL/HOLD
- 목적:
  1. 헤더/주간요약의 불필요한 Kakao Developers 버튼 제거
  2. 기사 버튼이 실제 `safe_original_url`로 전송되는지 발송 직전 payload까지 검증
  3. 기사 1건 링크 smoke test를 먼저 실행
  4. 사용자가 휴대전화에서 실제 원문 이동을 확인한 뒤에만 전체 compact 10개를 1회 재발송
- 자동 반복 LIVE: 금지
- 기존 Phase 3/4/6 journal 삭제: 금지
- 승인 없는 Git push: 금지

---

## 1. 문제 정의

Phase 6에서:
- compact message 10/10 API acceptance
- article buttons 8
- TEST marker 0
- scheduled LIVE 0

그러나 사용자 실제 KakaoTalk 화면에서 `원문 보기`를 누르면 Kakao Developers 페이지가 열렸다.

저장된 `templates.json`의 기사 URL이 올바른 것만으로 실제 클릭 동작이 보장되지는 않는다.

Phase 6.1은 실제 전송 payload와 모바일 클릭 결과를 분리해서 확인한다.

---

## 2. 기존 기록 보호

다음은 삭제·초기화·덮어쓰기 금지:
- Phase 3 TEST journal / receipt
- Phase 4 production-once journal / receipt
- Phase 6 compact production journal / receipt
- Phase 5 compact outputs
- Phase 6 templates / outputs

Phase 6.1은 완전히 별도 journal과 별도 outputs를 사용한다.

---

## 3. 도메인 사전 확인

Kakao Developers:
`앱 → 제품 링크 관리 → 웹 도메인`

아래 8개가 실제로 등록·저장되어 있는지 사용자가 직접 확인한 상태에서 진행:

1. `https://www.schools.nyc.gov`
2. `https://gottheimer.house.gov`
3. `https://www.brookings.edu`
4. `https://www.court.gov.cn`
5. `https://www.navercorp.com`
6. `https://blogs.nvidia.com`
7. `https://huggingface.co`
8. `https://news.samsung.com`

중요:
- 기존 도메인 삭제 금지
- 전체 기사 URL이 아니라 도메인만 등록
- `www` 유무는 실제 safe_original_url과 일치
- 앱/플랫폼 설정을 다른 목적으로 변경하지 않음

---

## 4. 링크 구조 수정

### 헤더
버튼 없음.

### 기사 8건
각 기사당 버튼 1개:

```json
{
  "title": "원문 보기",
  "link": {
    "web_url": "<safe_original_url>",
    "mobile_web_url": "<safe_original_url>"
  }
}
```

### 이번 주 AI 한눈에 보기
버튼 없음.

즉 Kakao Developers 링크를 사용하는 `서비스 안내` 버튼은 Phase 6.1 compact 포맷에서 완전히 제거한다.

---

## 5. 발송 직전 payload 감사

실제 네트워크 호출 직전의 **비민감 outbound template**을 별도 파일에 저장한다.

권장:
`outputs/phase6_1/link_audit/outbound_templates_redacted.json`

각 기사에 대해 저장:
- sequence
- kind
- article_number
- button_title
- web_url
- mobile_web_url
- text_sha256
- url_sha256

저장 금지:
- token
- Authorization header
- raw auth response
- cookies
- refresh token

발송 직전 검사:
- article 8개
- button 8개
- button title 모두 `원문 보기`
- URL 8/8 == Phase 5 safe_original_url
- `developers.kakao.com` 기사 버튼 0건
- header/overview button 0건

---

## 6. Phase 6.1A — 1건 링크 Smoke Test

전체 10개를 바로 재발송하지 않는다.

먼저 1번 기사만 별도 smoke-test 메시지로 실제 발송한다.

권장 명령:
`python -m news.phase6_1 --domains-confirmed --send-link-smoke-test`

Smoke test 내용:
- compact article 1번
- `[LINK TEST]` 표식 명시
- 버튼 1개 `원문 보기`
- URL: NYC교육청 safe_original_url
- 자동 LIVE 0

별도 journal:
`.state/phase6_1_link_smoke_<input_hash>.json`

Smoke test API 성공 후 사용자가 휴대전화에서 직접 눌러:
`schools.nyc.gov/...guidance-on-artificial-intelligence`
로 이동하는지 확인한다.

API success만으로 Phase 6.1A PASS 처리하지 않는다.
사용자의 실제 클릭 확인이 필요하다.

---

## 7. Phase 6.1B — Corrected Compact Production Once

Smoke test의 실제 클릭이 사용자에 의해 PASS 확인된 경우에만 실행.

권장 명령:
`python -m news.phase6_1 --link-smoke-confirmed --send-corrected-compact-once`

발송:
- 헤더 1
- 기사 8
- 주간요약 1
= 총 10개

헤더/overview button: 0
기사 button: 8

별도 journal:
`.state/phase6_1_corrected_compact_<input_hash>.json`

기존 Phase 6 journal은 삭제하지 않는다.

---

## 8. 재전송 및 실패 정책

- 자동 재시도 금지
- 부분 성공/불확실 응답 시 재전송 금지
- journal 삭제로 재실행 금지
- 재발송은 별도 사용자 승인 필요

링크/도메인 오류:
`LINK_CORRECTION_HOLD_DOMAIN`

인증 오류:
`LINK_CORRECTION_HOLD_AUTH`

scope 오류:
`LINK_CORRECTION_HOLD_SCOPE`

기타 API:
`LINK_CORRECTION_HOLD_API`

---

## 9. Source of Truth

문안:
`outputs/phase5/compact/mobile_messages.json`

기사/URL:
`outputs/phase5/compact/compact_items.json`
+
`outputs/phase2_3/samples/safe_content.json`

새 Tavily 검색 금지.
Gemini 재생성 금지.
compact 문안 재작성 금지.

---

## 10. 테스트

기존 252 tests 모두 재실행.

Phase 6.1 신규 테스트 최소:

1. header button 0
2. overview button 0
3. article button 8
4. button title == `원문 보기`
5. article web_url == safe_original_url
6. mobile_web_url == safe_original_url
7. developers.kakao.com article link count 0
8. outbound redacted audit 생성
9. audit에 secret 0
10. smoke test exactly 1 API call
11. smoke test `[LINK TEST]` 존재
12. smoke journal exclusive create
13. smoke replay blocked
14. full send requires `--link-smoke-confirmed`
15. full send exactly 10 calls
16. article order 1~8
17. TEST marker 0 in corrected full send
18. header/overview no link
19. Phase 3/4/6 journals unchanged
20. Phase 5 input hash binding
21. Phase 6 original output unchanged
22. actual send no automatic retry
23. result_code validation
24. secret masking
25. scheduled LIVE 0
26. config/auth settings unchanged
27. git push 0
28. dry-run actual API calls 0

---

## 11. Phase 6.1 산출물

필수:
- `PHASE6_1_LINK_CORRECTION_EXECUTION_REPORT.md`
- `PHASE6_1_LINK_CORRECTION_RESULT_PACKAGE.zip`

권장:
- `outputs/phase6_1/link_audit/outbound_templates_redacted.json`
- `outputs/phase6_1/smoke/smoke_preview.md`
- `outputs/phase6_1/smoke/smoke_receipt.json`
- `outputs/phase6_1/kakao/mobile_preview.md`
- `outputs/phase6_1/kakao/production_receipt.json`
- `outputs/phase6_1/quality/quality_gate.json`
- `outputs/phase6_1/logs/tests_existing.txt`
- `outputs/phase6_1/logs/tests_phase6_1.txt`
- `outputs/phase6_1/logs/tests.txt`
- `outputs/phase6_1/logs/audit.json`

ZIP 제외:
- `.state`
- token
- credentials
- `.env`
- `.git`
- venv
- auth headers

---

## 12. Gate 판정

### READY_FOR_SMOKE
구현·테스트·payload audit PASS, 실제 smoke 발송 전.

### SMOKE_API_PASS_USER_CONFIRMATION_REQUIRED
1건 API 발송 성공, 휴대전화 클릭 확인 대기.

### SMOKE_LINK_PASS
사용자가 실제 원문 이동 확인.

### CORRECTED_COMPACT_SEND_PASS
Smoke PASS 후 전체 10개 실제 발송 성공.

### HOLD
도메인/링크/인증/scope/품질 문제.

---

## 13. 절대 금지

- 기존 journal 삭제
- Phase 6 journal을 지우고 재사용
- `python -m news.phase6 --...` 재실행
- 자동 LIVE
- 스케줄 등록
- Tavily 재검색
- Gemini 재요약
- 승인 없는 git push
