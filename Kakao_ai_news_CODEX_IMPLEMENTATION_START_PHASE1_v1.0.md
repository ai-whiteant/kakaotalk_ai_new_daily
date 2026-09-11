# Kakao ai news — Codex 구현 시작 지침 + Phase 1 작업범위 v1.0

- 문서명: `Kakao_ai_news_CODEX_IMPLEMENTATION_START_PHASE1_v1.0.md`
- 프로젝트명: Kakao ai news
- 구현 환경: Paid API + Codex
- 상위 기준:
  1. `Kakao_ai_news_PROJECT_INSTRUCTIONS_FINAL.md`
  2. `Kakao_ai_news_WORKFLOW_v1.0.md`
  3. `Kakao_ai_news_AUTOMATION_SPEC_v1.0.md`
  4. API Reference 문서
- Phase 1 목표: 기존 정상 기준본을 보존하면서 프로젝트 구조·환경설정·Tavily 수집 계층을 구현하고 검증
- 원칙: 최소 변경 · 오류 격리 · 회귀 검증 · 인증정보 비노출 · 사용자 승인 전 LIVE 금지

---

# 1. 다음 작업

이번 단계는 실제 코드 구현의 시작 단계다.

전체 자동화 기능을 한 번에 구현하지 않고, 다음 3개만 우선 구현한다.

1. 프로젝트 구조 정리
2. 환경설정·보안 로더 구성
3. Tavily 뉴스 수집 계층 구현 및 TEST 검증

Gemini 분석, 중복 제거 고도화, 사실 검증, Kakao 발송은 Phase 1이 PASS된 후 다음 단계에서 구현한다.

---

# 2. Phase 1 범위

## 2.1 프로젝트 구조

기존 프로젝트 구조가 이미 존재하면 강제로 재구성하지 않는다.
현재 구조를 우선 확인하고 아래 역할이 논리적으로 분리되는지만 검증한다.

권장 역할:

- `config/`
  - 뉴스 검색 쿼리
  - 비민감 실행 설정
- `src/tavily/`
  - Tavily 호출
  - 응답 정규화
- `src/orchestrator/`
  - Phase 1 실행 제어
- `src/logging/`
  - 실행 로그
- `tests/`
  - 단위·통합·회귀 테스트
- `outputs/`
  - TEST 결과

기존 파일을 불필요하게 이동하거나 삭제하지 않는다.

---

# 3. 환경설정·보안

인증정보는 코드에 직접 기록하지 않는다.

환경변수 후보:

- `TAVILY_API_KEY`
- `GEMINI_API_KEY`
- `KAKAO_ACCESS_TOKEN`
- `KAKAO_REFRESH_TOKEN`
- `GEMINI_MODEL`
- `RUN_MODE`

Phase 1에서 실제 사용하는 인증정보는 Tavily만 허용한다.

보안 점검:

- `.env*` 실제 비밀값 파일 Git 제외
- `config.json`에 비밀값이 있다면 Git 추적 여부 확인
- 로그에 API Key 출력 금지
- 예외 메시지에 Authorization 헤더 출력 금지
- 테스트 fixture에 실제 키 사용 금지

---

# 4. 뉴스 쿼리 설정 파일

권장 파일:
`config/news_queries.yaml`

필수 분야:

- AI·교육
- 생성형 AI
- AI 기술·모델
- AI 정책·윤리
- AI 산업
- 국내 AI
- AI 보안

예시:

```yaml
queries:
  - id: edu_ko_01
    category: ai_education
    language: ko
    query: "대한민국 AI 교육"
    priority: 1

  - id: edu_en_01
    category: ai_education
    language: en
    query: "artificial intelligence education"
    priority: 1
```

쿼리 수는 과도하게 늘리지 않고, 각 분야를 충분히 탐색할 수 있는 수준에서 시작한다.

---

# 5. Tavily 클라이언트 구현

권장 책임:

- 인증
- Search API 호출
- timeout
- HTTP 오류 분류
- 재시도
- 응답 파싱

기본 검색값:

- `topic = news`
- `time_range = week`
- `search_depth = basic`

필요한 경우만 advanced를 사용한다.

클라이언트는 다음 값을 직접 생성하지 않는다.

- 뉴스 중요도
- 교육적 시사점
- 최종 기사 순위

Tavily는 후보 탐색과 원문 URL 확보 역할만 담당한다.

---

# 6. 후보 정규화

모든 검색 결과를 공통 데이터 구조로 변환한다.

필수 필드:

```json
{
  "candidate_id": "string",
  "query_id": "string",
  "category_hint": "string",
  "title": "string",
  "url": "string",
  "source_name": "string",
  "published_at": "ISO-8601 or null",
  "retrieved_at": "ISO-8601",
  "snippet": "string",
  "raw_content": "string or null",
  "language": "ko|en|other",
  "country_hint": "KR|INTL|UNKNOWN"
}
```

추가 처리:

- URL 중복 제거
- 제목 공백 정리
- 날짜 파싱
- 출처명 정리
- 쿼리 ID 보존

---

# 7. Phase 1 Orchestrator

Phase 1 실행 흐름:

실행 시작
→ 환경설정 확인
→ 쿼리 파일 로드
→ Tavily 호출
→ 후보 정규화
→ URL 중복 제거
→ 결과 저장
→ 실행 로그 저장
→ PASS / WARN / HOLD / FAIL 판정

아직 Gemini 또는 Kakao를 호출하지 않는다.

---

# 8. 출력 파일

TEST 실행 시 권장 출력:

- `outputs/raw/tavily_raw_<run_id>.json`
- `outputs/normalized/candidates_<run_id>.json`
- `outputs/logs/run_<run_id>.json`

비밀정보는 출력 파일에 포함하지 않는다.

---

# 9. Phase 1 상태 판정

## PASS

- 환경설정 로드 성공
- 쿼리 파일 로드 성공
- Tavily 검색 성공
- 후보 정규화 성공
- URL 중복 제거 성공
- 결과 저장 성공
- 실제 인증정보 비노출

## WARN

- 일부 쿼리만 실패
- 일부 기사 날짜 누락
- 일부 원문 content 누락
- 전체 파이프라인은 정상 완료

## HOLD

- 실제 키가 로그·파일에 노출됨
- 쿼리 설정 오류로 다수 분야 검색 실패
- 데이터 구조 검증 실패
- 날짜 범위 처리 오류
- 기존 정상 기준본 훼손 가능성 발견

## FAIL

- Tavily 인증 실패
- 실행 자체 중단
- 필수 설정 로드 실패
- 저장 경로 치명적 오류

---

# 10. 최소 테스트 시나리오

## TEST-P1-01 환경설정
실제 키 값 자체는 출력하지 않고 존재 여부만 확인.

## TEST-P1-02 쿼리 로드
7개 분야가 모두 로드되는지 확인.

## TEST-P1-03 Tavily 정상 검색
최근 7일 news 검색 성공 여부 확인.

## TEST-P1-04 부분 실패
일부 쿼리 실패 시 전체가 중단되지 않는지 확인.

## TEST-P1-05 URL 중복
동일 URL이 여러 쿼리에 등장할 때 1개 후보로 정리되는지 확인.

## TEST-P1-06 날짜 처리
발행일 존재/누락/파싱 실패를 각각 처리하는지 확인.

## TEST-P1-07 비밀정보 노출
로그 및 출력물에 API Key가 없는지 검사.

## TEST-P1-08 회귀
기존 정상 설정·Kakao·Gemini 관련 파일을 변경하지 않았는지 확인.

---

# 11. Codex 구현 시작 프롬프트

아래 프롬프트를 Codex에 그대로 사용할 수 있다.

```text
프로젝트명은 "Kakao ai news"다.

첨부 또는 프로젝트 소스에 있는 다음 문서를 우선순위대로 읽고 작업 기준으로 적용하라.

1. Kakao_ai_news_PROJECT_INSTRUCTIONS_FINAL.md
2. Kakao_ai_news_WORKFLOW_v1.0.md
3. Kakao_ai_news_AUTOMATION_SPEC_v1.0.md
4. Kakao_ai_news_CODEX_IMPLEMENTATION_START_PHASE1_v1.0.md
5. references/*.md

목표는 Phase 1만 구현하는 것이다.

이번 단계의 범위:
- 기존 프로젝트 구조와 Git 상태 확인
- 기존 정상 기준본 보존
- 환경설정/보안 로더 확인 또는 최소 구현
- config/news_queries.yaml 작성 또는 기존 구조에 맞게 동등하게 구현
- Tavily Search 계층 구현
- 검색 결과를 SearchCandidate 구조로 정규화
- URL 기준 1차 중복 제거
- TEST 실행 로그와 결과 파일 저장
- 최소 테스트 시나리오 실행
- 결과를 PASS / WARN / HOLD / FAIL로 판정

금지:
- Gemini 분석 로직 구현
- Kakao 발송 로직 변경
- 정상 작동 중인 인증 구조 재설계
- API Key/Access Token 출력
- 기존 파일 대규모 이동 또는 삭제
- LIVE 실행
- 사용자 승인 없는 운영 반영

작업 시작 전 반드시:
1. git status 확인
2. 현재 브랜치와 최신 커밋 확인
3. 비밀설정 파일의 Git 추적 여부 확인
4. 수정 대상 파일 목록 제시
5. 기존 정상 파일을 임의로 덮어쓰지 않음

구현 후 반드시:
- 변경 파일 목록
- 테스트 결과
- 실행 로그 요약
- 발견된 오류/주의사항
- 기존 기능 영향 여부
- 최종 판정
- 다음 단계 제안

을 보고하라.

Phase 1이 PASS되기 전에는 Gemini 또는 Kakao 구현으로 넘어가지 마라.
```

---

# 12. Phase 1 완료 후 다음 단계

Phase 1이 PASS되면 Phase 2로 이동한다.

Phase 2 예정 범위:

- 규칙 기반 중복 사건 통합
- Gemini Paid API 구조화 출력
- 중요도 평가
- 교육적 시사점 분석
- JSON Schema 검증
- Gemini 오류·재시도 처리

Kakao 발송은 아직 Phase 2에 포함하지 않는다.

---

# 13. 최종 원칙

Paid API + Codex 전환은 구현 환경 변경일 뿐,
Kakao ai news의 프로젝트 목적과 뉴스 품질 기준을 변경하지 않는다.

항상 다음을 유지한다.

정확성
→ 최신성
→ 출처 신뢰성
→ 중요도
→ 교육적 활용성
→ 모바일 가독성
→ 보안성
→ 안정적 자동화

Phase 1의 성공 기준은 “검색 결과가 나온다”가 아니라,
기존 정상 기준본을 훼손하지 않고
최근 7일 AI 뉴스 후보를 안정적으로 수집·정규화·기록할 수 있는가이다.
