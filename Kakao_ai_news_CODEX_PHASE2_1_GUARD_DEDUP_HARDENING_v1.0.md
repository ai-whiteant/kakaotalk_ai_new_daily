# Kakao ai news — Phase 2.1 Guard Calibration & Dedup Hardening v1.0

- 문서명: `Kakao_ai_news_CODEX_PHASE2_1_GUARD_DEDUP_HARDENING_v1.0.md`
- 프로젝트명: Kakao ai news
- 구현 환경: Paid Gemini API + Codex
- 현재 상태: Phase 1 PASS / Phase 2 구현 검증 완료 / 콘텐츠 품질 게이트 HOLD
- Phase 2.1 목적: 기존 정상 구현을 보존하면서 hallucination Guard의 false positive를 줄이고 사건 중복 판정을 보강한 뒤, 동일 Phase 1 입력으로 Phase 2를 재검증한다.
- 최상위 원칙: HOLD 수를 인위적으로 줄이지 않는다. 실제 unsupported claim 탐지력은 유지하거나 강화한다.

---

# 1. 적용 문서 우선순위

1. `Kakao_ai_news_PROJECT_INSTRUCTIONS_FINAL.md`
2. `Kakao_ai_news_WORKFLOW_v1.0.md`
3. `Kakao_ai_news_AUTOMATION_SPEC_v1.0.md`
4. `Kakao_ai_news_CODEX_IMPLEMENTATION_START_PHASE1_v1.0.md`
5. `PHASE1_EXECUTION_REPORT.md`
6. `Kakao_ai_news_CODEX_IMPLEMENTATION_PHASE2_v1.0.md`
7. `PHASE2_EXECUTION_REPORT.md`
8. 본 문서
9. `references/*.md`

상위 문서와 충돌하면 상위 기준을 따른다.

---

# 2. Phase 2.1 시작 상태

Phase 2 실행 결과 기준:

- Phase 1 입력 후보: 57건
- Phase 2 NewsEvent: 50건
- 통합 감소: 7건
- Gemini 관계 판정 SAME_EVENT: 13
- 판정 실패로 분리 유지: 8쌍
- Gemini 구조화 분석: 50건
- 일반 분석: 22건
- HOLD high-risk: 28건
- 70점 이상: 18건
- 기존 전체 테스트: 49개 PASS
- Kakao 실제 호출: 0
- LIVE 실행: 0
- Phase 2 최종 콘텐츠 판정: HOLD

Phase 2 보고서가 인정한 핵심 한계:
- high-risk 탐지는 문자열/사전 기반으로 오탐 가능
- 번역·단위 환산·일반 대문자 표현 오탐 가능
- 의미적 hallucination 완전 탐지 불가
- 일부 의미 중복 판정 미해결
- 원문 사실 검증은 아직 미완료

Phase 2.1은 이 한계만 최소 범위로 보정한다.

---

# 3. 변경 금지 영역

이번 작업에서 변경하지 않는다.

- Tavily 검색 설정
- Phase 1 후보 57건
- 검색 기간
- Gemini API Key
- Gemini 인증 구조
- `GEMINI_MODEL` 운영 값
- Gemini Paid API 프로젝트
- Kakao 인증
- Kakao 발송 코드
- Kakao scope
- 운영 스케줄
- LIVE 설정
- Phase 1 정상 코드
- 중요도 배점 30/20/15/15/10/10
- 70점 핵심 후보 기준

새 Tavily 검색도 수행하지 않는다.

---

# 4. 핵심 문제 A — Guard False Positive

Phase 2 high-risk 28건은 모두 실제 hallucination이라고 볼 수 없다.

현재 Guard는 다음과 같은 경우를 과도하게 unsupported entity로 판단할 수 있다.

- 일반 영어 대문자 단어
- 문장 첫 단어
- 직업/역할을 나타내는 일반명사
- 일반 형용사
- 하이픈 결합 표현
- multi-token 고유명사의 토큰 분리
- 입력에 의미상 존재하지만 표면형이 다른 표현

예:
- `World Bank`를 `World`, `Bank`로 분리
- `AI-driven`
- `AI-generated`
- `Educators`
- `Policymakers`
- `Conversely`

이런 표현만으로 AUTO_HOLD를 만들면 안 된다.

---

# 5. Guard 보정 원칙

## 5.1 핵심 사실 중심 검증

Guard의 목적은 모든 새로운 단어를 차단하는 것이 아니라
Gemini가 입력 근거 없이 새로운 **핵심 사실**을 추가하는 것을 탐지하는 것이다.

핵심 사실 후보:

- 수치
- 날짜
- 비율
- 금액
- 인원
- 기관명
- 기업명
- 모델명
- 제품명
- 정책명
- 법률명
- 국가/지역
- 공식 발표·결정·금지·허용·출시 등의 사건 주장
- URL

일반적인 연결어·직업명·설명용 형용사는 핵심 사실로 취급하지 않는다.

---

# 6. Multi-token Entity 처리

고유명사는 가능한 경우 phrase 단위로 처리한다.

예:

`World Bank`
→ 하나의 entity

`New York City Public Schools`
→ 하나의 entity

`Google DeepMind`
→ 하나의 entity

금지:
`World`, `Bank`를 각각 unsupported entity로 판정하여 HOLD시키는 방식.

권장 처리 순서:

1. 입력 제목·snippet·supporting source 텍스트에서 entity phrase 후보 구성
2. 긴 phrase 우선 매칭
3. 매칭된 phrase 내부 토큰은 독립 신규 entity 검사에서 제외
4. 출력 entity를 입력 phrase 및 정규화 alias와 비교

---

# 7. 일반 표현 제외

다음 유형은 단독으로 unsupported entity high-risk를 발생시키지 않는다.

- 문장 첫 일반 영어 단어
- 일반 직업명
- 일반 집단명
- 일반 설명어
- 접속사
- 부사
- 일반 AI 수식 표현

예:
- Educators
- Teachers
- Students
- Policymakers
- Researchers
- Conversely
- Additionally
- AI-driven
- AI-generated
- AI-powered

단, 특정 기관명·정책명·모델명으로 사용되는 문맥이면 별도 검사한다.

단순 stopword 목록에만 의존하지 말고 문맥/형태 규칙과 함께 적용한다.

---

# 8. 숫자·날짜 Guard 보정

단순히 Gemini 출력에 숫자가 등장했다는 이유만으로 HOLD하지 않는다.

검증 입력 범위:

- canonical title
- primary source title
- primary source snippet
- supporting source title
- supporting source snippet
- Phase 1 원본 candidate의 관련 텍스트

숫자 정규화 예:

- `8th` ↔ `8`
- `three` ↔ `3`은 안전하게 변환 가능한 경우에만
- `%` 표현
- 쉼표 포함 숫자
- 날짜의 표기 차이

분류:

### SUPPORTED
입력에 동일하거나 안전하게 정규화 가능한 근거가 있음.

### VERIFY
표현 변환 또는 문맥상 근거 가능성이 있으나 자동 확정하기 어려움.

### UNSUPPORTED
입력 전체에서 근거가 없고 새로운 핵심 사실을 구성함.

UNSUPPORTED 핵심 수치/날짜는 AUTO_HOLD 후보로 유지한다.

---

# 9. 새로운 3단계 Guard 상태

기존 high/low만으로 운영 판정을 단순화하지 않는다.

각 탐지 항목에 다음 상태를 부여한다.

## PASS
입력 근거 확인 또는 비핵심 표현.

## VERIFY
자동으로 확정하기 어려워 Phase 3 사실 검증이 필요한 항목.

## AUTO_HOLD
입력 근거 없이 새 핵심 사실을 생성한 강한 증거.

이벤트 최종 Guard 상태:

- `PASS`
- `VERIFY`
- `AUTO_HOLD`

규칙:

- AUTO_HOLD 1개 이상 → 이벤트 AUTO_HOLD
- AUTO_HOLD 없음 + VERIFY 존재 → VERIFY
- 둘 다 없음 → PASS

`VERIFY`는 hallucination 확정이 아니다.

---

# 10. fact_check_targets 연계

VERIFY 항목은 삭제하지 않고 `fact_check_targets`에 명시한다.

예:

```json
{
  "type": "number",
  "value": "8",
  "status": "VERIFY",
  "reason": "Normalized support is ambiguous",
  "source_candidate_ids": []
}
```

Phase 3에서 공식 원문 또는 복수 신뢰 출처를 이용해 검증할 수 있도록
근거 추적 정보를 보존한다.

---

# 11. Guard Auditability

각 위험 판정은 최소 다음을 기록한다.

```json
{
  "code": "UNSUPPORTED_NUMBER_OR_DATE",
  "value": "string",
  "status": "PASS|VERIFY|AUTO_HOLD",
  "output_field": "summary",
  "reason": "string",
  "matched_input": "string or null",
  "candidate_ids": []
}
```

단순히 `high_risk=true`만 저장하지 않는다.

왜 차단했는지 사람이 재검토할 수 있어야 한다.

---

# 12. 핵심 문제 B — 의미 중복 보강

Phase 2에서 URL 중복을 넘어 의미 중복 통합을 구현했지만
판정 실패 8쌍과 보수적 분리 사례가 남아 있다.

Phase 2.1에서는 동일 사건 판단 근거를 보강한다.

---

# 13. Dedup 판단 신호

다음 신호를 조합한다.

- 핵심 기관/기업 동일
- 동일 모델/제품/정책
- 동일 핵심 행위
- 동일 발표/출시/판결/규제/사고
- 사건 날짜 근접
- 제목 의미 유사
- 핵심 수치 일치
- 지역/대상 동일

중요:
같은 기업 또는 같은 AI 주제라는 이유만으로 합치지 않는다.

---

# 14. SAME_EVENT / FOLLOW_UP / DIFFERENT_EVENT

## SAME_EVENT

동일한 원 사건을 보도하며
핵심 행위·주체·대상이 사실상 동일.

## FOLLOW_UP

같은 원 사건과 연결되지만
새로운 후속 조치·반응·결과·분석이 핵심.

FOLLOW_UP은 원 사건과 관계는 보존하되
자동으로 하나의 NewsEvent로 강제 병합하지 않는다.

## DIFFERENT_EVENT

주체가 같더라도 별개의 발표·제품·정책·사건.

---

# 15. 관계 데이터 보존

NewsEvent에 필요 시 관계를 별도 보존한다.

예:

```json
{
  "event_id": "evt_x",
  "related_events": [
    {
      "event_id": "evt_y",
      "relation": "FOLLOW_UP",
      "confidence": 0.93
    }
  ]
}
```

이렇게 하면 중복 제거를 위해 서로 다른 후속 사건을 잃는 것을 방지할 수 있다.

---

# 16. Dedup Evidence 검증

Gemini의 관계 판정은 다음을 반드시 반환해야 한다.

- relation
- confidence
- candidate IDs
- evidence
- reason

candidate ID는 입력 enum에 포함된 값만 허용한다.

evidence는 제공된 title/snippet에서 추적 가능한 근거여야 한다.

근거가 유효하지 않으면 강제 병합하지 않는다.

---

# 17. 재검증 입력 고정

Phase 2.1 재검증에는 Phase 2에서 사용한 동일 Phase 1 normalized 후보를 사용한다.

입력 SHA-256이 Phase 2 보고서의 기준과 일치하는지 먼저 확인한다.

기준:
`490b4608eb820ed679ee41a6dcfd969f22d032c493837c3ca220eee53d389e40`

불일치 시:
- 실행 중단
- HOLD
- 새 Tavily 검색 금지
- 원인 보고

---

# 18. False-positive Regression Tests

기존 테스트 외에 반드시 추가한다.

## TEST-P2.1-01 Multi-token entity
입력: `World Bank`
출력: `World Bank`
기대: PASS

## TEST-P2.1-02 Split-token prevention
입력에 `World Bank`
출력에 `World Bank`
기대: `World`, `Bank` 개별 unsupported 탐지 금지

## TEST-P2.1-03 Generic role noun
출력: Educators / Policymakers
기대: 단독 AUTO_HOLD 금지

## TEST-P2.1-04 Generic transition word
출력: Conversely / Additionally
기대: entity 위험 판정 금지

## TEST-P2.1-05 Hyphenated AI expression
출력: AI-driven / AI-generated
기대: 단독 AUTO_HOLD 금지

## TEST-P2.1-06 Supported ordinal
입력: 8th grade
출력: grade 8
기대: 안전한 정규화 가능 시 PASS

## TEST-P2.1-07 Unsupported number
입력에 없는 핵심 수치 추가
기대: AUTO_HOLD

## TEST-P2.1-08 Unsupported date
입력에 없는 핵심 날짜 추가
기대: AUTO_HOLD

## TEST-P2.1-09 Unsupported model
입력에 없는 구체적 모델명 추가
기대: AUTO_HOLD

## TEST-P2.1-10 New URL
Gemini가 입력에 없는 URL 생성
기대: AUTO_HOLD

## TEST-P2.1-11 Paraphrase
입력 사실을 새로운 숫자/기관 추가 없이 자연어로 재표현
기대: PASS 또는 VERIFY, AUTO_HOLD 금지

## TEST-P2.1-12 Ambiguous normalization
근거가 있을 가능성은 있으나 자동 확정 곤란
기대: VERIFY

---

# 19. Dedup Regression Tests

## TEST-P2.1-D01 동일 정책 다중 보도
동일 기관·정책·핵심 행위
→ SAME_EVENT

## TEST-P2.1-D02 같은 기관 다른 정책
→ DIFFERENT_EVENT

## TEST-P2.1-D03 후속 반응
원 발표 이후 반응/후속조치
→ FOLLOW_UP

## TEST-P2.1-D04 동일 기업 다른 모델 발표
→ DIFFERENT_EVENT

## TEST-P2.1-D05 evidence invalid
Gemini evidence가 입력에서 확인되지 않음
→ 병합 금지

## TEST-P2.1-D06 transitive overmerge
A≈B, B≈C이나 A와 C가 다른 사건
→ 무조건 전이 병합 금지

---

# 20. 기존 회귀 테스트

반드시 모두 다시 실행한다.

- 기존 회귀 10개
- Phase 1 16개
- Phase 2 23개
- Phase 2.1 신규 Guard 테스트
- Phase 2.1 신규 Dedup 테스트

기존 49개 중 하나라도 실패하면 Phase 2.1 PASS 금지.

---

# 21. 재실행 통계

재검증 보고서에는 반드시 Before/After를 함께 기록한다.

## Before — Phase 2
- candidates: 57
- events: 50
- normal analysis: 22
- high-risk/HOLD: 28
- unresolved dedup pairs: 8
- >=70 score: 18

## After — Phase 2.1
기록:
- candidates
- events
- SAME_EVENT
- FOLLOW_UP
- DIFFERENT_EVENT
- unresolved
- Guard PASS
- Guard VERIFY
- Guard AUTO_HOLD
- >=70 score

주의:
AUTO_HOLD 감소 자체를 성공 기준으로 사용하지 않는다.

---

# 22. Phase 2.1 PASS 기준

다음 조건을 모두 만족해야 한다.

1. 동일 Phase 1 입력 사용
2. 기존 49개 테스트 전부 PASS
3. 신규 false-positive 테스트 PASS
4. 신규 dedup 테스트 PASS
5. 실제 unsupported 숫자/날짜/모델/URL 주입 테스트가 AUTO_HOLD
6. 일반 단어·multi-token entity 오탐 개선
7. Guard 판정 근거 audit 가능
8. 불확실 항목 VERIFY 분리
9. 의미 중복 오통합 없음
10. Gemini 인증/모델/Tavily/Kakao 설정 변경 없음
11. 실제 secret 노출 없음
12. Kakao 호출 0
13. LIVE 실행 0

---

# 23. HOLD 기준

다음 중 하나면 HOLD:

- false positive 개선 과정에서 실제 unsupported claim을 통과시킴
- 입력 SHA 불일치
- 기존 테스트 회귀
- 의미 중복 과병합
- Guard 근거 추적 불가
- secret 노출 가능성
- 기존 정상 설정 변경
- AUTO_HOLD를 단순히 VERIFY/PASS로 강등하여 수치만 개선

---

# 24. Phase 2.1 결과 파일

반드시 생성:

- `PHASE2_1_EXECUTION_REPORT.md`
- `PHASE2_1_RESULT_PACKAGE.zip`

권장 결과:

- `outputs/phase2_1/events/events.json`
- `outputs/phase2_1/events/decisions.json`
- `outputs/phase2_1/analysis/analysis.json`
- `outputs/phase2_1/analysis/verify.json`
- `outputs/phase2_1/analysis/auto_hold.json`
- `outputs/phase2_1/logs/run.json`
- `outputs/phase2_1/logs/tests.txt`
- `outputs/phase2_1/logs/audit.json`
- `outputs/phase2_1/verification/guard_before_after.json`
- `outputs/phase2_1/verification/dedup_before_after.json`
- `outputs/phase2_1/verification/git_diff.patch`

ZIP에는 secret/config/token/.env/Git metadata/가상환경을 포함하지 않는다.

---

# 25. Codex 실행 프롬프트

아래 프롬프트를 Codex에 그대로 입력한다.

```text
Kakao ai news 프로젝트의 Phase 2.1 Guard Calibration & Dedup Hardening을 실행하라.

적용 문서 우선순위:
1. Kakao_ai_news_PROJECT_INSTRUCTIONS_FINAL.md
2. Kakao_ai_news_WORKFLOW_v1.0.md
3. Kakao_ai_news_AUTOMATION_SPEC_v1.0.md
4. Kakao_ai_news_CODEX_IMPLEMENTATION_START_PHASE1_v1.0.md
5. PHASE1_EXECUTION_REPORT.md
6. Kakao_ai_news_CODEX_IMPLEMENTATION_PHASE2_v1.0.md
7. PHASE2_EXECUTION_REPORT.md
8. Kakao_ai_news_CODEX_PHASE2_1_GUARD_DEDUP_HARDENING_v1.0.md
9. references/*.md

목표:
Phase 2의 정상 구현을 보존하면서 Guard false positive와 의미 중복 판정만 최소 범위로 보강하고,
동일 Phase 1 후보 57건을 사용하여 Phase 2 콘텐츠 품질 게이트를 다시 검증한다.

시작 전:
- git status
- branch
- latest commit
- Phase 1 baseline commit
- Phase 2 uncommitted 변경 확인
- secret 추적 여부
- Phase 1 normalized 입력 SHA-256 확인

입력 SHA-256은 반드시 다음과 일치해야 한다.
490b4608eb820ed679ee41a6dcfd969f22d032c493837c3ca220eee53d389e40

불일치하면 실행하지 말고 HOLD 보고하라.

변경 범위:
1. Guard false-positive 보정
2. multi-token entity 처리
3. 일반 영어 표현 오탐 방지
4. 숫자/날짜 근거 정규화
5. PASS / VERIFY / AUTO_HOLD 3단계 판정
6. fact_check_targets 및 audit 근거 강화
7. SAME_EVENT / FOLLOW_UP / DIFFERENT_EVENT 판정 보강
8. related event 관계 보존
9. false-positive regression test 추가
10. dedup regression test 추가
11. 동일 입력 재실행
12. Before/After 비교

절대 금지:
- 새 Tavily 검색
- Gemini API Key 변경
- Gemini 인증 구조 변경
- GEMINI_MODEL 운영 값 변경
- Kakao 설정 변경
- Kakao 실제 호출
- LIVE 실행
- 운영 스케줄 변경
- 점수 배점 변경
- 70점 기준 변경
- HOLD 숫자를 줄이기 위한 위험 판정 임의 완화
- 사용자 승인 없는 push

특히 다음을 테스트하라:
World Bank
Educators
Policymakers
Conversely
AI-driven
AI-generated
8th grade ↔ grade 8
입력에 없는 숫자
입력에 없는 날짜
입력에 없는 모델명
입력에 없는 URL

기존 테스트 49개를 전부 다시 실행하고
Phase 2.1 신규 Guard/Dedup 테스트를 추가하라.

완료 후 다음 형식으로 보고하라.

# Phase 2.1 실행 결과

## 1. Git 기준상태
## 2. 입력 무결성 SHA 검증
## 3. 변경 파일
## 4. 기존 49개 회귀 테스트
## 5. 신규 Guard 테스트
## 6. 신규 Dedup 테스트
## 7. Guard Before/After
## 8. Dedup Before/After
## 9. 실제 unsupported claim 방어 결과
## 10. Gemini API 실행 결과
## 11. 오류 및 경고
## 12. 기존 Tavily/Gemini/Kakao 설정 영향
## 13. 보안 검사
## 14. 생성 결과 파일
## 15. 최종 PASS/WARN/HOLD/FAIL
## 16. 판정 근거
## 17. Phase 3 진입 가능 여부

반드시 생성:
PHASE2_1_EXECUTION_REPORT.md
PHASE2_1_RESULT_PACKAGE.zip

ZIP에는 보고서, 변경 소스, 테스트 로그, audit, Before/After, event/analysis/verify/auto_hold 샘플,
git diff만 포함하고 실제 secret은 제외하라.

마지막에는 다음만 다시 출력:
1. 최종 판정
2. PHASE2_1_EXECUTION_REPORT.md 경로
3. PHASE2_1_RESULT_PACKAGE.zip 경로
4. git status
```

---

# 26. Phase 2.1 이후

Phase 2.1이 PASS되면 Phase 2 콘텐츠 품질 게이트를 최종 PASS로 전환할 수 있는지 독립 검토한다.

독립 검토까지 PASS한 뒤 Phase 3로 이동한다.

Phase 3 예정:
- 공식 원문/복수 신뢰 출처 사실 검증
- VERIFY 항목 해소
- 최종 기사 선별
- 상세 브리핑
- Kakao 모바일 압축판
- 메시지 품질 게이트
- Kakao TEST 발송

LIVE 자동 발송은 여전히 별도 승인 대상이다.
