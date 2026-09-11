# Kakao ai news 자동화 구현 사양서 v1.0
## AUTOMATION SPEC — Paid API + Codex

- 문서명: `Kakao_ai_news_AUTOMATION_SPEC_v1.0.md`
- 프로젝트명: Kakao ai news
- 상위 기준 문서:
  1. `Kakao_ai_news_PROJECT_INSTRUCTIONS_FINAL.md`
  2. `Kakao_ai_news_WORKFLOW_v1.0.md`
- 참조 문서:
  - `00_REFERENCE_INDEX.md`
  - `01_TAVILY_SEARCH_API_REFERENCE.md`
  - `02_TAVILY_MCP_REFERENCE.md`
  - `03_GEMINI_API_AUTH_MODELS.md`
  - `04_GEMINI_RATE_LIMITS.md`
  - `05_GEMINI_ERROR_HANDLING.md`
  - `06_KAKAO_TALK_MESSAGE_API.md`
  - `07_KAKAO_LOGIN_SCOPE_TOKEN.md`
- 구현 환경 방향: Paid API + Codex
- 기본 검색 기간: 최근 7일
- 기본 최종 기사 수: 8~12건 권장
- 품질 원칙: 정확성 · 최신성 · 출처 신뢰성 · 교육적 활용성 · 모바일 가독성 · 보안성 · 장애 격리
- 상태 코드: PASS / WARN / HOLD / FAIL

---

# 1. 목적

이 문서는 `Kakao ai news`의 확정된 프로젝트 지침과 실행 워크플로우를
실제 코드로 구현하기 위한 기술 사양을 정의한다.

핵심 목표는 다음과 같다.

1. Tavily를 통해 최근 AI 뉴스를 분야별로 수집한다.
2. 중복·저품질·과장성 정보를 제거한다.
3. Gemini Paid API를 통해 분류·중복 보조·중요도 평가·요약·시사점 분석을 수행한다.
4. 사실 검증과 품질 게이트를 통과한 기사만 최종 브리핑에 포함한다.
5. KakaoTalk `나에게 보내기` 형식으로 모바일 친화적인 메시지를 생성한다.
6. Codex를 이용해 구현·테스트·회귀 검증을 수행한다.
7. API 장애를 서비스별로 격리하고, 정상 작동 중인 다른 서비스의 설정을 임의 변경하지 않는다.

---

# 2. 아키텍처

권장 처리 구조:

Scheduler / Manual Trigger
→ Orchestrator
→ Tavily Search Layer
→ Candidate Normalizer
→ Deduplication Layer
→ Gemini Analysis Layer
→ Verification Layer
→ Ranking & Selection
→ Detailed Brief Generator
→ Kakao Compact Formatter
→ Quality Gate
→ Kakao Sender
→ Run Logger

Codex는 위 구성 요소를 구현·수정·테스트하는 개발 에이전트로 사용한다.

---

# 3. 실행 모드

## 3.1 MANUAL

수동 실행 모드.

용도:
- 개발
- 회귀 테스트
- 뉴스 품질 검토
- Kakao 발송 전 최종 확인

## 3.2 TEST

실제 API를 호출하되 운영 발송을 차단할 수 있는 테스트 모드.

권장 동작:
- Tavily: 실제 호출
- Gemini Paid API: 실제 호출
- Kakao: 발송 차단 또는 테스트용 명시 옵션 적용
- 로그: 전체 기록

## 3.3 LIVE

자동 운영 모드.

조건:
- 최근 회귀 테스트 PASS
- API 인증 정상
- 품질 게이트 PASS
- Kakao 발송 설정 정상

LIVE에서는 HOLD 또는 FAIL 상태에서 자동 발송하지 않는다.

---

# 4. 환경설정

인증정보는 코드에 직접 입력하지 않는다.

권장 환경변수 예시:

- `TAVILY_API_KEY`
- `GEMINI_API_KEY`
- `KAKAO_ACCESS_TOKEN`
- `KAKAO_REFRESH_TOKEN` (필요한 경우)
- `KAKAO_CLIENT_ID` (필요한 경우)
- `GEMINI_MODEL`
- `RUN_MODE`
- `LOG_LEVEL`

환경별 설정:

- `.env.local`
- `.env.test`
- `.env.production`

단, 실제 인증정보가 포함된 파일은 Git에 포함하지 않는다.

---

# 5. 핵심 데이터 모델

## 5.1 SearchCandidate

```json
{
  "candidate_id": "string",
  "query_id": "string",
  "category_hint": "ai_education",
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

## 5.2 NewsEvent

```json
{
  "event_id": "string",
  "canonical_title": "string",
  "category": "string",
  "primary_source": {
    "title": "string",
    "url": "string",
    "source_name": "string",
    "published_at": "ISO-8601 or null"
  },
  "supporting_sources": [],
  "entities": [],
  "event_date": "ISO-8601 or null",
  "key_facts": [],
  "dedup_confidence": 0.0
}
```

## 5.3 GeminiAnalysis

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
  "uncertainties": [],
  "fact_check_targets": [],
  "hallucination_risk": "low|medium|high"
}
```

## 5.4 FinalArticle

```json
{
  "rank": 1,
  "event_id": "string",
  "category": "string",
  "title": "string",
  "summary": "string",
  "why_it_matters": "string",
  "education_implication": "string or null",
  "classroom_use": "string or null",
  "source_url": "string",
  "source_name": "string",
  "published_at": "ISO-8601",
  "score": 0,
  "verification_status": "PASS|WARN|HOLD|FAIL"
}
```

---

# 6. Tavily 검색 사양

## 6.1 기본값

- topic: `news`
- time_range: `week`
- search_depth: `basic`
- 특정 검증이 필요한 검색에만 `advanced`
- max_results: 쿼리별 필요 범위에서 조정

## 6.2 검색 분야

### AI·교육
- artificial intelligence education
- generative AI education
- AI teachers students schools
- AI literacy education
- vocational education AI
- 대한민국 AI 교육
- 생성형 AI 학교 교사 학생
- 교육부 AI 교육 정책

### 생성형 AI
- generative AI latest news
- large language model latest
- AI agent latest
- multimodal AI
- ChatGPT Gemini Claude latest

### AI 기술·모델
- new AI model release
- frontier model
- reasoning model
- multimodal model
- AI agent benchmark
- open source AI model

### AI 정책·윤리
- AI regulation
- AI copyright
- AI privacy
- AI safety policy
- AI ethics education
- artificial intelligence law

### AI 산업
- AI industry
- AI semiconductor
- AI investment
- AI data center
- AI cloud platform

### 국내 AI
- 한국 AI
- 대한민국 인공지능
- 국내 생성형 AI
- 한국 AI 기업
- 과기정통부 AI
- 교육부 인공지능

### AI 보안
- AI cybersecurity
- generative AI security
- deepfake security
- AI privacy breach
- AI misuse

## 6.3 쿼리 관리

쿼리는 코드에 흩어놓지 않고 별도 설정 파일로 관리한다.

권장:
`config/news_queries.yaml`

각 쿼리는 다음 정보를 가진다.

```yaml
- id: edu_ko_01
  category: ai_education
  language: ko
  query: "대한민국 AI 교육"
  priority: 1
```

---

# 7. 후보 정규화

Tavily 검색 결과는 통합 포맷으로 정규화한다.

필수 처리:
- URL canonicalization
- 제목 공백 정리
- 발행일 ISO 변환
- 검색 시각 기록
- 출처명 표준화
- 언어 추정
- 중복 URL 제거

URL에서 불필요한 추적 파라미터가 명백한 경우 제거할 수 있다.

---

# 8. 중복 제거 사양

## 8.1 1차 규칙 기반 중복

다음이 동일하면 강한 중복 후보로 본다.

- canonical URL 동일
- 제목 정규화 후 높은 유사도
- 동일 출처 + 동일 날짜 + 동일 핵심 엔터티

## 8.2 2차 의미 기반 중복

규칙 기반으로 확정하기 어려운 경우 Gemini에 다음을 판정시킨다.

- 동일 사건인가?
- 후속 기사인가?
- 별도 사건인가?
- 대표 출처는 무엇인가?

## 8.3 대표 기사 우선순위

1. 공식 1차 출처
2. 주요 통신·언론
3. 기술·과학 전문매체
4. 업계 전문매체

동일 사건에서 대표 기사 1건을 선택하되,
사실 검증에 필요한 보조 출처는 유지한다.

---

# 9. Gemini Paid API 분석 사양

## 9.1 운영 원칙

- Paid API를 기본 분석 환경으로 사용한다.
- 모델명은 환경변수로 분리한다.
- 특정 모델명을 프로젝트 로직에 하드코딩하지 않는다.
- 구조화 출력(JSON)을 우선 사용한다.
- 응답 스키마 검증에 실패하면 재시도한다.
- 원문에 없는 사실을 생성하지 않도록 시스템 프롬프트에 명시한다.

## 9.2 기본 프롬프트 역할

Gemini는 다음 역할만 수행한다.

- 분야 분류
- 중복 판정 보조
- 중요도 평가
- 사실 요약
- 중요성 분석
- 교육적 시사점
- 수업 활용 가능성 판단
- 사실 검증 대상 추출

Gemini 자체 판단만으로 URL이나 날짜를 생성하지 않는다.

## 9.3 중요도 점수

- 교육 관련성: 30
- AI 기술 중요도: 20
- 교사·학생 영향: 15
- 사회·산업 영향: 15
- 출처 신뢰도: 10
- 최신성: 10

총점 100.

기본 선별 기준:
- 70점 이상 핵심 후보

단, 중대 정책·모델 공개·보안 사고 등은 별도 우선검토 플래그를 둘 수 있다.

---

# 10. Gemini 구조화 출력 검증

Gemini 응답은 JSON Schema 또는 동등한 검증 절차를 적용한다.

검증 실패 조건:
- 필수 필드 누락
- 점수 범위 초과
- 합계 오류
- 허용되지 않은 category
- 원문 URL 생성
- 원문에 없는 수치 생성 의심
- 필드 타입 오류

실패 시:
1. 동일 입력으로 1회 재시도
2. 재시도 실패 시 WARN 또는 HOLD
3. 전체 파이프라인을 불필요하게 중단하지 않는다.

---

# 11. 사실 검증 사양

검증 우선 항목:

- 기사 발행일
- 사건 발생일
- 기관·기업명
- 모델명
- 제품명
- 정책명
- 핵심 수치
- 공식 발표 여부
- 원문 URL

중요 뉴스는 공식 자료 또는 복수 신뢰 출처 검증을 우선한다.

다음은 자동 제외 또는 HOLD 후보:
- 출처 불명
- 날짜 불명확
- 서로 충돌하는 핵심 수치
- 본문과 제목 불일치
- 루머성 정보
- 원문 미확인
- 사실과 의견 분리 불가

---

# 12. 최종 선별 알고리즘

기본:
1. verification_status가 HOLD/FAIL인 사건 제외
2. total score 내림차순
3. 공식 출처 보유 기사 가점
4. AI 교육 분야 우선
5. 국내외 균형
6. 분야 과밀 방지
7. 최종 8~12건 권장

단, 품질이 낮으면 8건 미만도 허용한다.

---

# 13. 상세판 생성 사양

상세판은 검토·기록용이다.

기사당 포함:
- 제목
- 핵심 내용
- 왜 중요한가
- 교육적 시사점
- 필요 시 수업 활용
- 원문 URL
- 출처
- 발행일
- 중요도 점수
- 검증 상태

상세판은 Kakao 발송용보다 길어도 된다.

---

# 14. Kakao 발송용 압축 사양

기사당 기본 구조:

① 제목

📌 핵심
1~2문장

💡 의미
1문장

👨‍🏫 교육
교육 관련성이 있을 때 1문장

📖 수업 활용
실제 수업 가치가 높은 경우만

🔗 원문
실제 URL

원칙:
- 불필요한 배경설명 제거
- 동일 표현 반복 금지
- 한 기사에 너무 많은 수치 금지
- 교육적 연관성이 약하면 교육 필드 생략
- 모바일에서 한눈에 읽히는 길이 유지

---

# 15. 이번 주 AI 한눈에 보기

최종 브리핑 마지막에 생성한다.

필드:
- 가장 중요한 변화
- 교육계 핵심 이슈
- 주목할 AI 기술
- 다음 관찰 포인트

이는 개별 기사 재요약이 아니라 전체 뉴스의 공통 흐름을 종합해야 한다.

---

# 16. 품질 게이트

## PASS

- 날짜·URL·핵심 사실 확인
- 중복 제거 완료
- 중대한 수치 오류 없음
- 출처 신뢰 가능
- hallucination 의심 없음
- 인증정보 노출 없음

## WARN

- 핵심 사실에는 문제 없으나 비핵심 요소에 불확실성 존재
- 발송 가능하지만 로그에 기록

## HOLD

다음 중 하나라도 해당하면 자동 발송 중단:
- 중요 사실 미확인
- 원문 URL 불확실
- 핵심 수치 충돌
- 공식 발표 여부 불명확
- 높은 hallucination 위험
- 메시지 내용에 인증정보 가능성
- 발송 대상 데이터 이상

## FAIL

- Tavily 호출 실패
- Gemini 호출 실패로 핵심 처리 불가
- Kakao 인증 실패
- 파이프라인 예외로 실행 중단

---

# 17. Kakao 발송 사양

기본 엔드포인트:
`POST https://kapi.kakao.com/v2/api/talk/memo/default/send`

발송 조건:
- 최종 품질 상태 PASS
- 허용된 WARN
- 유효한 Access Token
- `talk_message` 동의
- template_object 검증

메시지가 길면 다음처럼 분할한다.

- 1/3 AI 교육
- 2/3 AI 기술·산업
- 3/3 정책·보안·이번 주 AI 한눈에 보기

분할 기준은 실제 메시지 템플릿 제약과 가독성을 함께 고려한다.

---

# 18. 재시도 정책

## Tavily

- 네트워크/5xx: 지수 백오프 재시도
- 인증 오류: 재시도보다 즉시 FAIL
- 잘못된 쿼리/인자: 요청 수정 후 재실행

## Gemini

- 429: Retry-After가 있으면 우선 반영
- 5xx: 지수 백오프
- 403: 프로젝트·권한·접근 상태 확인, 무한 재시도 금지
- 400: 요청/스키마 검토
- 구조화 출력 실패: 동일 요청 1회 재시도 후 WARN/HOLD

## Kakao

- 인증/토큰 오류: 토큰 흐름 점검
- scope 오류: `talk_message` 상태 확인
- 5xx: 제한된 횟수로 재시도
- 발송 중복 방지용 idempotency 성격의 로컬 실행 기록 유지

---

# 19. 로깅 사양

권장 로그 구조:

```json
{
  "run_id": "20260909T210000+0900",
  "mode": "TEST",
  "period_start": "2026-09-03",
  "period_end": "2026-09-09",
  "tavily": {
    "status": "PASS",
    "queries": 20,
    "candidates": 85
  },
  "dedup": {
    "events": 31
  },
  "gemini": {
    "status": "PASS",
    "model": "from_env",
    "analyzed_events": 31
  },
  "selection": {
    "final_articles": 10
  },
  "quality_gate": "PASS",
  "kakao": {
    "status": "PASS",
    "messages_sent": 3
  }
}
```

인증정보, 전체 Access Token, API Key는 기록하지 않는다.

---

# 20. 오류 로그

기록:
- run_id
- 단계
- 발생 시각
- HTTP 상태
- 오류 코드
- 마스킹된 오류 메시지
- request ID
- 재시도 횟수
- 최종 상태

서비스별 오류를 별도 구분한다.

예:
- `TAVILY_SEARCH_ERROR`
- `GEMINI_AUTH_ERROR`
- `GEMINI_RATE_LIMIT`
- `GEMINI_SCHEMA_ERROR`
- `KAKAO_TOKEN_ERROR`
- `KAKAO_SEND_ERROR`

---

# 21. Codex 구현 규칙

Codex는 프로젝트의 기존 정상 기준본을 우선 보존한다.

작업 전:
1. 현재 Git 상태 확인
2. 기준본 커밋 확인
3. 설정/인증 파일 추적 여부 확인
4. 변경 범위 선언

작업 중:
- 한 단계씩 구현
- 작은 변경 단위 유지
- 기존 정상 기능 임의 재설계 금지
- API 역할 혼합 금지
- 인증정보 출력 금지

작업 후:
- lint
- unit test
- integration test
- regression test
- TEST 모드 실행
- 결과 보고
- 사용자 승인 전 LIVE 반영 금지

---

# 22. 권장 프로젝트 구조

```text
kakao-ai-news/
├─ README.md
├─ docs/
│  ├─ Kakao_ai_news_PROJECT_INSTRUCTIONS_FINAL.md
│  ├─ Kakao_ai_news_WORKFLOW_v1.0.md
│  ├─ Kakao_ai_news_AUTOMATION_SPEC_v1.0.md
│  └─ references/
│     ├─ 00_REFERENCE_INDEX.md
│     ├─ 01_TAVILY_SEARCH_API_REFERENCE.md
│     ├─ 02_TAVILY_MCP_REFERENCE.md
│     ├─ 03_GEMINI_API_AUTH_MODELS.md
│     ├─ 04_GEMINI_RATE_LIMITS.md
│     ├─ 05_GEMINI_ERROR_HANDLING.md
│     ├─ 06_KAKAO_TALK_MESSAGE_API.md
│     └─ 07_KAKAO_LOGIN_SCOPE_TOKEN.md
├─ config/
│  └─ news_queries.yaml
├─ src/
│  ├─ orchestrator/
│  ├─ tavily/
│  ├─ dedup/
│  ├─ gemini/
│  ├─ verification/
│  ├─ ranking/
│  ├─ briefing/
│  ├─ kakao/
│  └─ logging/
├─ tests/
│  ├─ unit/
│  ├─ integration/
│  └─ regression/
├─ outputs/
│  ├─ detailed/
│  ├─ kakao/
│  └─ logs/
└─ .gitignore
```

실제 기존 프로젝트 구조가 이미 존재하면
위 구조를 강제로 덮어쓰지 않고 기존 구조와 일관되게 매핑한다.

---

# 23. 최소 테스트 시나리오

## TEST-01 최근 7일 정상 실행
- Tavily 검색
- Gemini 분석
- 최종 8~12건
- Kakao 발송은 차단 또는 테스트 처리
- 기대 결과: PASS

## TEST-02 동일 사건 다중 기사
- 동일 사건 기사 3건 이상 입력
- 기대 결과: 1개 NewsEvent로 통합

## TEST-03 날짜 범위 밖 기사
- 최근 7일 밖 기사 포함
- 기대 결과: 최종 후보에서 제거

## TEST-04 출처 불명 기사
- 기대 결과: 낮은 신뢰도 또는 제외

## TEST-05 Gemini 429
- 기대 결과: 재시도 후 복구 또는 WARN/FAIL

## TEST-06 Gemini 403
- 기대 결과: 무한 재시도 금지, Gemini 장애로 격리

## TEST-07 Kakao 토큰 오류
- 기대 결과: Kakao 단계 FAIL, Tavily/Gemini 설정 변경 없음

## TEST-08 Hallucination 방어
- 원문에 없는 수치가 Gemini 결과에 포함되도록 테스트
- 기대 결과: HOLD

## TEST-09 메시지 길이 초과
- 기대 결과: 논리적 단위 자동 분할

## TEST-10 보안정보 노출 검사
- 테스트용 dummy secret 삽입
- 기대 결과: HOLD

---

# 24. 운영 승인 게이트

LIVE 반영 전 반드시 확인한다.

- [ ] Tavily 실제 검색 PASS
- [ ] Gemini Paid API 정상
- [ ] 구조화 출력 검증 PASS
- [ ] 중복 제거 PASS
- [ ] 사실 검증 PASS
- [ ] Kakao 메시지 포맷 PASS
- [ ] Kakao TEST 발송 PASS
- [ ] 인증정보 비노출 PASS
- [ ] 회귀 테스트 PASS
- [ ] 사용자 최종 승인

하나라도 중대한 HOLD가 있으면 LIVE 전환하지 않는다.

---

# 25. 변경 관리

변경 절차:

현재 정상 기준본 보존
→ 변경 목적 정의
→ 변경 범위 최소화
→ 코드 수정
→ 단위 테스트
→ 통합 테스트
→ 회귀 테스트
→ TEST 실행
→ 결과 검토
→ 사용자 승인
→ LIVE 반영

특히 다음을 동시에 변경하지 않는 것을 원칙으로 한다.

- Tavily 검색 로직
- Gemini 인증 구조
- Gemini 모델
- Kakao 인증 구조
- 출력 포맷

대규모 동시 변경은 장애 원인 추적을 어렵게 하므로 금지한다.

---

# 26. 프로젝트 최종 원칙

자동화의 목적은 기사 수를 늘리는 것이 아니다.

최종 우선순위:

정확성
→ 최신성
→ 출처 신뢰성
→ AI 분야 중요도
→ 교육적 활용성
→ 모바일 가독성
→ 보안성
→ 안정적 자동화

Paid API와 Codex 도입은 품질·안정성·개발 생산성을 높이기 위한 수단이며,
프로젝트의 원래 목적과 뉴스 선별 기준을 변경하지 않는다.

최종 목표는 사용자가 짧은 시간 안에 최근 국내외 AI 변화를 정확히 파악하고,
교육·사회·산업에 미치는 의미를 이해하며,
실제 수업과 업무에 활용할 수 있는 신뢰도 높은 개인 AI 뉴스 브리핑을
안정적으로 제공하는 것이다.
