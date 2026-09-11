# Kakao ai news — Phase 2 Codex 구현지침 v1.0

- 문서명: `Kakao_ai_news_CODEX_IMPLEMENTATION_PHASE2_v1.0.md`
- 프로젝트명: Kakao ai news
- 구현 환경: Paid Gemini API + Codex
- 상위 기준:
  1. `Kakao_ai_news_PROJECT_INSTRUCTIONS_FINAL.md`
  2. `Kakao_ai_news_WORKFLOW_v1.0.md`
  3. `Kakao_ai_news_AUTOMATION_SPEC_v1.0.md`
  4. `Kakao_ai_news_CODEX_IMPLEMENTATION_START_PHASE1_v1.0.md`
  5. `PHASE1_EXECUTION_REPORT.md`
  6. references/*.md
- Phase 2 목표: Phase 1의 정상 기준본을 고정한 뒤, 사건 단위 중복 통합과 Gemini Paid API 구조화 분석 계층을 구현·검증
- 원칙: 기존 PASS 기준본 보존 · 최소 변경 · 구조화 출력 · 사실 보존 · hallucination 방어 · API 장애 격리 · LIVE 금지

---

# 1. Phase 2 시작 전 필수 선행 작업

Phase 2를 시작하기 전에 Phase 1 PASS 상태를 기준본으로 고정한다.

반드시 수행:
1. 현재 작업 체크아웃 위치 확인
2. `git status` 확인
3. Phase 1 신규 파일 목록 확인
4. Phase 1 결과물이 검토된 상태인지 확인
5. Phase 1 기준본을 별도 커밋으로 고정
6. 커밋 후 `git status` clean 확인

권장 커밋 메시지:

`feat: add phase1 tavily search pipeline baseline`

주의:
- 사용자 승인 없이 push하지 않는다.
- 원격 main에 직접 반영하지 않는다.
- 현재 Phase 1 브랜치 또는 후속 작업 브랜치에서만 진행한다.
- 실제 인증정보가 커밋 대상에 포함되지 않았는지 재확인한다.

---

# 2. Phase 2 범위

이번 단계에서 구현하는 기능은 다음과 같다.

1. Phase 1 후보 입력 로더
2. 사건 단위 의미 중복 후보 생성
3. 규칙 기반 1차 사건 통합
4. Gemini Paid API 클라이언트
5. Gemini 구조화 출력
6. 중요도 평가
7. 교육적 시사점 분석
8. 수업 활용 가능성 판단
9. fact_check_targets 추출
10. hallucination 위험 플래그
11. JSON Schema 검증
12. Gemini 오류·재시도 처리
13. Phase 2 TEST 및 결과 저장

이번 단계에서 구현하지 않는 기능:
- 최종 사실 검증 계층의 완성
- 최종 8~12건 선정 확정
- Kakao 실제 발송
- LIVE 자동화
- 운영 스케줄 변경

---

# 3. 입력 기준

Phase 2 입력은 Phase 1의 정규화 후보를 사용한다.

예:
`outputs/phase1/normalized/candidates_<run_id>.json`

입력 후보는 다음 정보를 최소 보유해야 한다.

- candidate_id
- query_id
- category_hint
- title
- url
- source_name
- published_at
- retrieved_at
- snippet
- raw_content
- language
- country_hint

Phase 1 데이터 구조를 임의로 변경하지 않는다.
필요한 필드는 Phase 2 파생 데이터에 추가한다.

---

# 4. 사건 단위 중복 통합

## 4.1 목적

URL이 달라도 동일 사건을 다룬 기사들을 하나의 `NewsEvent`로 통합한다.

예:
- 동일 기업의 동일 모델 발표
- 동일 정부 정책 발표
- 동일 소송·판결 사건
- 동일 보안 사고
- 동일 연구 결과

## 4.2 1차 규칙 기반 후보화

다음 신호를 활용할 수 있다.

- 제목 정규화 유사도
- 핵심 고유명사 겹침
- 동일 기관·기업명
- 발행일 근접
- 모델명·제품명·정책명 일치
- 동일 핵심 수치
- 동일 사건 키워드

규칙 기반 단계는 보수적으로 동작해야 한다.
확실하지 않은 후보를 강제로 합치지 않는다.

## 4.3 Gemini 의미 중복 판정

규칙 기반으로 확정하기 어려운 경우 Gemini에 다음 셋 중 하나를 판정시킨다.

- SAME_EVENT
- FOLLOW_UP
- DIFFERENT_EVENT

추가 출력:
- confidence
- reason
- representative_source_preference

중복 판정에는 기사 제목과 snippet 등 주어진 정보만 사용한다.
원문에 없는 사실을 새로 만들지 않는다.

---

# 5. NewsEvent 구조

```json
{
  "event_id": "string",
  "canonical_title": "string",
  "category_hint": "string",
  "candidate_ids": ["string"],
  "primary_source": {
    "candidate_id": "string",
    "title": "string",
    "url": "string",
    "source_name": "string",
    "published_at": "ISO-8601 or null"
  },
  "supporting_sources": [
    {
      "candidate_id": "string",
      "title": "string",
      "url": "string",
      "source_name": "string",
      "published_at": "ISO-8601 or null"
    }
  ],
  "entities": ["string"],
  "event_date": "ISO-8601 or null",
  "dedup_status": "RULE|GEMINI|SINGLE",
  "dedup_confidence": 0.0
}
```

대표 출처 우선순위:
1. 공식 1차 출처
2. 주요 통신·언론
3. 기술·과학 전문매체
4. 업계 전문매체

---

# 6. Gemini Paid API 클라이언트

## 6.1 원칙

- 실제 Paid Gemini API 환경 사용
- 모델명은 `GEMINI_MODEL` 환경변수로 주입
- 특정 모델명을 코드에 영구 고정하지 않음
- API Key를 코드·로그·출력에 기록하지 않음
- 요청/응답의 민감정보를 마스킹
- 구조화 JSON 출력 우선

## 6.2 클라이언트 책임

- 인증
- 요청 전송
- timeout
- 400/403/404/429/5xx 오류 분류
- 제한된 재시도
- 응답 파싱
- 스키마 검증 호출
- request ID 기록 가능 시 기록

---

# 7. Gemini 분석 출력 스키마

각 NewsEvent에 대해 다음 구조를 생성한다.

```json
{
  "event_id": "string",
  "category": "ai_education|generative_ai|ai_models|policy_ethics|industry|domestic_ai|security|other",
  "scores": {
    "education_relevance": 0,
    "ai_technical_importance": 0,
    "teacher_student_impact": 0,
    "social_industry_impact": 0,
    "source_reliability": 0,
    "recency": 0,
    "total": 0
  },
  "summary": "string",
  "why_it_matters": "string",
  "education_implication": "string or null",
  "classroom_use": "string or null",
  "uncertainties": ["string"],
  "fact_check_targets": ["string"],
  "hallucination_risk": "low|medium|high"
}
```

---

# 8. 점수 규칙

100점 기준:

- 교육 관련성: 30
- AI 기술 중요도: 20
- 교사·학생 영향: 15
- 사회·산업 영향: 15
- 출처 신뢰도: 10
- 최신성: 10

필수 검증:
- 각 점수 범위 초과 금지
- total 합계 자동 계산 또는 검증
- 모델 응답 total을 그대로 신뢰하지 않음

기본 핵심 후보:
- total >= 70

단, Phase 2에서는 최종 8~12건 선정을 확정하지 않는다.

---

# 9. Gemini 프롬프트 규칙

시스템 또는 상위 프롬프트에 다음을 명시한다.

- 제공된 기사 정보만 사용
- URL 생성 금지
- 날짜 생성 금지
- 원문에 없는 수치 생성 금지
- 사실과 해석 구분
- 불확실하면 uncertainties에 기록
- 교육적 연관성이 약하면 education_implication=null 허용
- 억지 수업 활용 금지
- 기사 제목만으로 과도한 추론 금지
- 과장 표현 금지
- 정치적·상업적 편향 금지

---

# 10. 구조화 출력 검증

반드시 JSON Schema 또는 동등한 강제 검증 절차를 적용한다.

검증 실패 조건:

- 필수 필드 누락
- 허용되지 않은 category
- score 범위 초과
- total 합계 오류
- 필드 타입 오류
- URL 생성
- 입력에 없는 수치 생성 의심
- 지나치게 긴 출력
- 잘못된 null 처리

처리 순서:

1. 1차 응답 검증
2. 실패 시 동일 입력으로 1회 재시도
3. 재시도 실패 시 해당 이벤트 WARN 또는 HOLD
4. 전체 실행을 불필요하게 중단하지 않음

---

# 11. Hallucination 방어

Phase 2에서 특히 다음을 검사한다.

- 입력에 없는 숫자
- 입력에 없는 날짜
- 입력에 없는 기관명
- 입력에 없는 모델명
- 입력에 없는 정책명
- 새로 생성된 URL
- 확정되지 않은 내용을 확정형으로 표현

권장 방식:

1. 입력에서 숫자·날짜·고유명사 후보 추출
2. Gemini 출력과 비교
3. 새롭게 등장한 핵심 사실 후보를 `fact_check_targets`로 이동
4. 높은 위험이면 `hallucination_risk=high`
5. high이면 자동 HOLD 후보

Phase 2에서는 사실 검증 자체를 완전히 끝내지 않아도 되지만,
검증이 필요한 대상을 명확히 추출해야 한다.

---

# 12. Gemini 오류 처리

## 400
- 요청 구조/스키마 확인
- 자동 무한 재시도 금지

## 403
- 프로젝트 접근/권한/환경 확인
- 다른 API 설정 변경 금지
- FAIL 또는 HOLD

## 404
- 모델명 또는 엔드포인트 확인

## 429
- Retry-After 우선
- 지수 백오프
- 제한 횟수만 재시도
- 키 재생성으로 해결하려 하지 않음

## 5xx
- 일시 장애 가능성
- 제한된 재시도
- 반복 실패 시 WARN/FAIL

---

# 13. Phase 2 출력 파일

권장:

- `outputs/phase2/events/events_<run_id>.json`
- `outputs/phase2/analysis/analysis_<run_id>.json`
- `outputs/phase2/analysis/high_risk_<run_id>.json`
- `outputs/phase2/logs/run_<run_id>.json`
- `outputs/phase2/logs/tests.txt`
- `outputs/phase2/logs/audit.json`
- `outputs/phase2/sample.json`

인증정보는 포함하지 않는다.

---

# 14. Phase 2 테스트 시나리오

## TEST-P2-01 SAME_EVENT
동일 사건 다른 URL 3개 입력
→ 1개 NewsEvent로 통합

## TEST-P2-02 FOLLOW_UP
동일 사건 후속 기사
→ SAME_EVENT와 구분

## TEST-P2-03 DIFFERENT_EVENT
같은 기업이지만 다른 발표
→ 분리 유지

## TEST-P2-04 Gemini 정상 구조화 출력
→ JSON Schema PASS

## TEST-P2-05 점수 합계 오류
→ 자동 검증에서 탐지

## TEST-P2-06 허용되지 않은 category
→ schema FAIL

## TEST-P2-07 원문에 없는 수치 생성
→ hallucination 위험 상승 및 HOLD 후보

## TEST-P2-08 URL 생성
→ HOLD

## TEST-P2-09 교육 연관성 약한 산업 기사
→ education_implication null 허용

## TEST-P2-10 Gemini 429
→ 제한된 재시도

## TEST-P2-11 Gemini 403
→ Gemini 장애로 격리, Tavily/Kakao 설정 변경 없음

## TEST-P2-12 일부 이벤트 분석 실패
→ 전체 파이프라인 지속 가능 여부 확인

## TEST-P2-13 비밀정보 노출 검사
→ 로그·출력·오류에 키 없음

## TEST-P2-14 Phase 1 회귀
→ Phase 1 테스트 재실행 PASS

---

# 15. Phase 2 상태 판정

## PASS

- Phase 1 기준본 보존
- 사건 단위 중복 통합 정상
- Gemini Paid API 정상
- 구조화 출력 검증 정상
- 점수 계산 정상
- hallucination 방어 정상
- 인증정보 비노출
- Phase 1 회귀 PASS

## WARN

- 일부 이벤트 Gemini 분석 실패
- 일부 중복 판정 confidence 낮음
- 전체 파이프라인은 정상 완료

## HOLD

- 의미 중복 통합 오류 다수
- Gemini 출력에서 미검증 사실 생성
- URL 생성
- 핵심 점수/스키마 검증 실패 다수
- 비밀정보 노출 가능성
- Phase 1 기준본 훼손

## FAIL

- Gemini 인증 실패
- 분석 계층 전체 중단
- 필수 입력 로드 실패
- 실행 자체 실패

---

# 16. Codex 실행 프롬프트

아래를 Codex에 그대로 입력한다.

```text
Kakao ai news 프로젝트 Phase 2를 구현하고 TEST하라.

적용 우선순위:
1. Kakao_ai_news_PROJECT_INSTRUCTIONS_FINAL.md
2. Kakao_ai_news_WORKFLOW_v1.0.md
3. Kakao_ai_news_AUTOMATION_SPEC_v1.0.md
4. Kakao_ai_news_CODEX_IMPLEMENTATION_START_PHASE1_v1.0.md
5. PHASE1_EXECUTION_REPORT.md
6. Kakao_ai_news_CODEX_IMPLEMENTATION_PHASE2_v1.0.md
7. references/*.md

Phase 2 시작 전에 반드시 Phase 1 PASS 기준본을 커밋으로 고정하라.
단, push는 하지 마라.

이번 작업 범위:
- Phase 1 normalized 후보 입력
- 사건 단위 의미 중복 통합
- NewsEvent 생성
- Gemini Paid API 구조화 분석
- 중요도 100점 평가
- 교육적 시사점
- 수업 활용 가능성 판단
- fact_check_targets
- hallucination_risk
- JSON Schema 검증
- Gemini 오류 분류 및 제한적 재시도
- Phase 2 TEST
- Phase 1 회귀 테스트

금지:
- Kakao 발송 구현
- LIVE 실행
- 운영 스케줄 변경
- 기존 인증 구조 재설계
- API Key/Access Token 출력
- 최종 8~12건 발송 확정
- 사용자 승인 없는 push

작업 전 출력:
1. git status
2. branch
3. latest commit
4. Phase 1 baseline commit
5. 변경 예정 파일
6. secret 추적 여부

작업 후 출력:

# Phase 2 실행 결과

## 1. Git 기준상태
## 2. Phase 1 기준본 커밋
## 3. 변경 파일
## 4. 사건 중복 통합 결과
## 5. Gemini Paid API 테스트 결과
## 6. 구조화 출력/스키마 테스트
## 7. 중요도 평가 통계
## 8. hallucination 방어 테스트
## 9. 오류 및 경고
## 10. Phase 1 회귀 결과
## 11. 기존 Kakao 기능 영향
## 12. 생성 결과 파일 경로
## 13. 최종 PASS/WARN/HOLD/FAIL
## 14. 판정 근거
## 15. Phase 3 진입 가능 여부

그리고 반드시 생성:
- PHASE2_EXECUTION_REPORT.md
- PHASE2_RESULT_PACKAGE.zip

ZIP 포함:
- 보고서
- 신규/수정 소스
- 테스트 로그
- audit
- event 샘플
- Gemini analysis 샘플
- high_risk 샘플
- git diff
- 비밀정보 제외

마지막에는 다음 4개만 다시 요약:
1. 최종 판정
2. PHASE2_EXECUTION_REPORT.md 경로
3. PHASE2_RESULT_PACKAGE.zip 경로
4. git status
```

---

# 17. Phase 2 완료 후 다음 단계

Phase 2가 PASS되면 Phase 3로 이동한다.

Phase 3 예정 범위:

- 공식 1차 자료/복수 출처 사실 검증
- 검증 상태 PASS/WARN/HOLD
- 최종 8~12건 선별
- 상세 브리핑 생성
- Kakao 압축판 생성
- 메시지 길이 검증
- Kakao TEST 발송

LIVE 자동 발송은 Phase 3 이후에도 별도 승인 후 진행한다.

---

# 18. 최종 원칙

Phase 2의 성공 기준은 Gemini가 답변을 생성하는 것이 아니다.

성공 기준은:

- 동일 사건을 안정적으로 통합하고
- Paid Gemini API가 구조화된 결과를 생성하며
- 프로젝트의 점수체계를 정확히 적용하고
- 원문에 없는 사실 생성을 탐지하며
- 교육적 시사점을 과장하지 않고
- 기존 Phase 1 정상 기준본을 보존하는 것

이다.
