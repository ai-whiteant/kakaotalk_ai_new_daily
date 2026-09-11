# Kakao ai news — Phase 2.3 Final Candidate Verification Gate v1.0

- 문서명: `Kakao_ai_news_CODEX_PHASE2_3_FINAL_CANDIDATE_VERIFICATION_v1.0.md`
- 프로젝트명: Kakao ai news
- 구현 환경: Paid Gemini API + Codex
- 현재 상태: Phase 1 PASS / Phase 2 구현 PASS / Phase 2.1 Guard·Dedup PASS / Phase 2.2 검증 시스템 PASS / 전체 콘텐츠 게이트 HOLD
- Phase 2.3 목적: 모든 사건을 끝까지 살리는 방식이 아니라, 실제 발송 가치가 높은 후보를 먼저 압축한 뒤 그 후보만 공식 원문 중심으로 전수검증하여 최소 8건 이상의 검증 완료 뉴스 후보를 확보한다.
- 핵심 원칙: 기사 수 맞추기보다 품질 우선. 검증되지 않은 HOLD 사건을 억지로 통과시키지 않는다.

---

# 1. 적용 문서 우선순위

1. `Kakao_ai_news_PROJECT_INSTRUCTIONS_FINAL.md`
2. `Kakao_ai_news_WORKFLOW_v1.0.md`
3. `Kakao_ai_news_AUTOMATION_SPEC_v1.0.md`
4. `Kakao_ai_news_CODEX_IMPLEMENTATION_START_PHASE1_v1.0.md`
5. `PHASE1_EXECUTION_REPORT.md`
6. `Kakao_ai_news_CODEX_IMPLEMENTATION_PHASE2_v1.0.md`
7. `PHASE2_EXECUTION_REPORT.md`
8. `Kakao_ai_news_CODEX_PHASE2_1_GUARD_DEDUP_HARDENING_v1.0.md`
9. `PHASE2_1_EXECUTION_REPORT.md`
10. `Kakao_ai_news_CODEX_PHASE2_2_EVIDENCE_VERIFICATION_v1.0.md`
11. `PHASE2_2_EXECUTION_REPORT.md`
12. 본 문서
13. `references/*.md`

충돌 시 상위 문서를 따른다.

---

# 2. Phase 2.3 시작 기준

Phase 2.2 기준:

- 전체 events: 49
- 기존 Guard PASS: 28
- Phase 2.2 VERIFIED_WITH_CONTEXT: 3
- Phase 2.2 VERIFICATION_HOLD: 17
- Phase 2.2 REJECT: 1
- 70점 이상 후보: 20
- 기존 112개 테스트: PASS
- Tavily/Gemini/Kakao 운영 설정 변경 없음
- Kakao 호출 0
- LIVE 0

Phase 2.3의 기본 검토 풀:

`PASS 28 + VERIFIED_WITH_CONTEXT 3 = 31 events`

17 HOLD와 1 REJECT는 `excluded_pool`에 보존한다.

---

# 3. Phase 2.3 목표

목표는 31개를 모두 외부 검증하는 것이 아니다.

다음 순서로 진행한다.

1. 31개 후보를 중요도·교육 가치·출처 신뢰도·최신성·중복성으로 재정렬
2. 약 12~15개 예비 후보 선정
3. 예비 후보만 공식 원문·주요 신뢰 출처 중심으로 전수검증
4. 검증 완료 후보를 최종 사용 가능 풀로 이동
5. 검증 완료 후보가 8건 이상이면 Phase 2 최종 PASS 검토
6. 8건 미만이면 HOLD pool에서 다음 우선순위 후보를 추가 검증
7. 저품질 뉴스로 숫자를 억지로 맞추지 않음

---

# 4. 후보 선별 점수

기존 100점 체계를 변경하지 않는다.

- AI·교육 관련성: 30
- AI 기술 중요도: 20
- 교사·학생 영향: 15
- 사회·산업 파급효과: 15
- 출처 신뢰도: 10
- 최신성: 10

기존 점수를 기본값으로 사용한다.

다만 Phase 2.3 예비선정에는 별도 `selection_adjustment`를 둘 수 있다.
이 값은 원래 100점 점수를 변경하지 않고 순위 조정 근거로만 사용한다.

권장 보정 요소:

- 공식 1차 출처 확보 가능성
- 동일 이슈 중복도
- 국내외 균형
- AI 교육 분야 대표성
- 생성형 AI/기술/정책/산업/보안 다양성
- 실제 교사·학생 영향
- 단순 홍보성 기사 여부
- 후속 보도보다 원 사건 우선 여부

---

# 5. 분야별 균형 원칙

최종 후보는 억지 할당하지 않는다.

다만 프로젝트 기본 가중치를 참고해 다음을 권장한다.

- AI·교육: 가장 높은 우선순위
- 생성형 AI
- AI 기술·모델
- AI 정책·윤리
- AI 산업
- 국내 AI 생태계
- AI 보안

동일한 중요도라면 AI 교육 및 교육적 파급효과가 큰 기사를 우선한다.

단, 교육과 관련이 약한 중요한 산업·기술 뉴스에 억지 교육 해석을 붙이지 않는다.

---

# 6. 예비 후보 수

기본:
- 12~15건

최종 목표:
- 8~12건

예비 후보가 15건을 초과해도 기사 품질이 높다면 허용하지만,
불필요한 전수검증 비용 증가를 피한다.

---

# 7. 예비 후보 선정 규칙

예비 후보에 포함되려면 최소 다음 조건을 만족해야 한다.

- Guard PASS 또는 VERIFIED_WITH_CONTEXT
- event 구조 정상
- 원문 URL 존재
- 중복 사건 아님
- 점수·카테고리·근거 데이터 존재
- 명백한 광고/홍보성 저가치 기사 아님
- 핵심 사실 검증 가능성 있음

우선순위:
1. score >= 70
2. 공식/고신뢰 출처
3. 교육 또는 사회적 파급력 높음
4. 동일 사건 중 대표성 높음
5. 최근성
6. 국내외 포트폴리오 균형

---

# 8. 전수검증 범위

선정된 예비 후보는 다음 핵심 항목을 모두 검증한다.

- 제목
- 사건 발생/발표 날짜
- 핵심 기관·기업
- AI 모델명·제품명
- 핵심 수치
- 정책/규제 내용
- 공식 발표 여부
- 기사 요약의 핵심 주장
- why_it_matters의 사실 기반
- 교육적 시사점이 원 사실에서 과도하게 확대되지 않았는지
- classroom_use가 사실과 충돌하지 않는지
- 최종 원문 URL

---

# 9. 출처 우선순위

1. 공식 정부·기관·기업·대학 발표
2. 논문·연구기관
3. 주요 통신사/신뢰 언론
4. 기술·과학 전문매체

가능하면 핵심 사실은 1차 출처 또는 서로 독립적인 신뢰 출처 2개로 확인한다.

중요 숫자·정책·모델 정보는 검색 snippet만으로 승인하지 않는다.

---

# 10. FinalVerificationRecord

```json
{
  "event_id": "evt_x",
  "selection_rank": 1,
  "original_score": 82,
  "selection_adjustment": 3,
  "category": "ai_education",
  "verification_status": "FINAL_VERIFIED|FINAL_VERIFIED_WITH_CONTEXT|FINAL_HOLD|FINAL_REJECT",
  "verified_claims": [
    {
      "claim": "string",
      "status": "SUPPORTED|EQUIVALENT|CONTEXTUAL|UNRESOLVED|UNSUPPORTED|CONTRADICTED",
      "evidence_urls": ["https://..."]
    }
  ],
  "safe_title": "string",
  "safe_summary": "string",
  "safe_why_it_matters": "string",
  "safe_education_implication": "string or null",
  "safe_classroom_use": "string or null",
  "original_url": "https://...",
  "notes": ["string"]
}
```

---

# 11. 최종 상태 정의

## FINAL_VERIFIED
핵심 사실 모두 검증 완료.

## FINAL_VERIFIED_WITH_CONTEXT
핵심 사실은 확인됐지만 일부 문구를 좁히거나 맥락 수정 필요.

## FINAL_HOLD
핵심 사실 일부 미해결.

## FINAL_REJECT
핵심 사실이 틀리거나 기사 가치가 낮음.

---

# 12. 안전 콘텐츠 규칙

최종 후보에 포함되는 문장은 반드시 `safe_*` 필드만 사용한다.

원래 Gemini summary를 그대로 발송 데이터로 사용하지 않는다.

다음은 제거/수정 대상:

- 과도한 확정 표현
- 근거 없는 숫자
- 원문보다 강한 인과관계
- 출처가 확인되지 않은 모델명
- 정책 범위 과장
- 교사·학생 영향의 과도한 일반화
- 원문에 없는 교육적 효과 단정

교육적 시사점은 가능하면 “가능성이 있다”, “수업 설계에 영향을 줄 수 있다”처럼 사실과 해석을 구분한다.

---

# 13. HOLD pool 재진입 규칙

예비 후보 전수검증 후 FINAL_VERIFIED 계열이 8건 미만이면:

1. excluded_pool 중 점수가 높은 HOLD 사건 정렬
2. 원문 확보 가능성 확인
3. 가장 높은 후보부터 추가 검증
4. VERIFIED 가능한 경우만 final_pool에 추가
5. 최소 8건 확보 시 중단 가능

REJECT 사건은 자동 재진입 금지.

---

# 14. Phase 2 최종 PASS 조건

다음 조건을 모두 만족해야 한다.

1. 최종 검증 완료 후보 최소 8건
2. 권장 범위 8~12건
3. 8건을 맞추기 위해 저가치 기사 추가 금지
4. 최종 후보 핵심 사실 전수검증
5. 최종 URL 검증
6. UNSUPPORTED/CONTRADICTED 핵심 claim 없음
7. FINAL_HOLD는 최종 후보에 없음
8. 카테고리 중복 과다 없음
9. AI 교육 우선순위 반영
10. 국내외 중요 이슈 균형 고려
11. 기존 112개 테스트 + Phase 2.3 신규 테스트 PASS
12. 기존 Tavily/Gemini/Kakao 설정 무변경
13. secret 비노출
14. Kakao 호출 0
15. LIVE 0

---

# 15. Phase 2.3 테스트

## TEST-P2.3-01
31개 후보에서 예비 12~15개 선별

## TEST-P2.3-02
70점 이상 우선 선정

## TEST-P2.3-03
중복 사건 대표 1개만 선택

## TEST-P2.3-04
낮은 점수지만 교육적으로 매우 중요한 공식 정책 기사 처리 검증

## TEST-P2.3-05
홍보성 고득점 기사 과대선정 방지

## TEST-P2.3-06
공식 원문과 summary 일치 → FINAL_VERIFIED

## TEST-P2.3-07
문맥 좁힘 필요 → FINAL_VERIFIED_WITH_CONTEXT

## TEST-P2.3-08
핵심 사실 미해결 → FINAL_HOLD

## TEST-P2.3-09
핵심 사실 반증 → FINAL_REJECT

## TEST-P2.3-10
최종 후보에서 HOLD 제거

## TEST-P2.3-11
최종 URL 검증

## TEST-P2.3-12
8건 미만 시 HOLD pool 단계적 재검증

## TEST-P2.3-13
REJECT 자동 재진입 차단

## TEST-P2.3-14
교육적 시사점 과장 방지

## TEST-P2.3-15
최종 safe_content만 export

---

# 16. 회귀 테스트

반드시 기존 112개 테스트를 모두 재실행한다.

기존 테스트 실패 시 Phase 2.3 PASS 금지.

---

# 17. 결과 파일

반드시 생성:

- `PHASE2_3_EXECUTION_REPORT.md`
- `PHASE2_3_RESULT_PACKAGE.zip`

권장:

- `outputs/phase2_3/selection/pre_candidates.json`
- `outputs/phase2_3/selection/final_candidates.json`
- `outputs/phase2_3/selection/excluded_pool.json`
- `outputs/phase2_3/verification/final_verification_records.json`
- `outputs/phase2_3/verification/source_registry.json`
- `outputs/phase2_3/verification/before_after.json`
- `outputs/phase2_3/logs/tests.txt`
- `outputs/phase2_3/logs/audit.json`
- `outputs/phase2_3/logs/run.json`
- `outputs/phase2_3/verification/git_diff.patch`

ZIP에서 secret/.env/token/.git/가상환경 제외.

---

# 18. 최종 보고 형식

```text
# Phase 2.3 실행 결과

## 1 Git 기준상태
## 2 입력 무결성
## 3 변경 파일
## 4 31개 후보 평가
## 5 예비 후보 선정 결과
## 6 출처 검증 통계
## 7 FinalVerification 결과
## 8 최종 사용 가능 후보 수
## 9 최종 후보 목록
## 10 제외/HOLD/REJECT 목록 요약
## 11 교육 분야 반영 결과
## 12 안전 콘텐츠 검증
## 13 기존 112개 회귀 테스트
## 14 신규 Phase2.3 테스트
## 15 Tavily/Gemini/Kakao 영향
## 16 보안 검사
## 17 생성 결과 파일
## 18 최종 PASS/WARN/HOLD/FAIL
## 19 Phase2 전체 콘텐츠 게이트 판정
## 20 Phase3 진입 가능 여부
```

---

# 19. Codex 실행 프롬프트

```text
Kakao ai news 프로젝트 Phase 2.3 Final Candidate Verification Gate를 구현하고 실행하라.

문서 우선순위:
1 Kakao_ai_news_PROJECT_INSTRUCTIONS_FINAL.md
2 Kakao_ai_news_WORKFLOW_v1.0.md
3 Kakao_ai_news_AUTOMATION_SPEC_v1.0.md
4 Kakao_ai_news_CODEX_IMPLEMENTATION_START_PHASE1_v1.0.md
5 PHASE1_EXECUTION_REPORT.md
6 Kakao_ai_news_CODEX_IMPLEMENTATION_PHASE2_v1.0.md
7 PHASE2_EXECUTION_REPORT.md
8 Kakao_ai_news_CODEX_PHASE2_1_GUARD_DEDUP_HARDENING_v1.0.md
9 PHASE2_1_EXECUTION_REPORT.md
10 Kakao_ai_news_CODEX_PHASE2_2_EVIDENCE_VERIFICATION_v1.0.md
11 PHASE2_2_EXECUTION_REPORT.md
12 Kakao_ai_news_CODEX_PHASE2_3_FINAL_CANDIDATE_VERIFICATION_v1.0.md
13 references/*.md

목표:
모든 사건을 완전히 검증하려 하지 말고 실제 발송 가치가 높은 후보를 먼저 선별한 뒤 그 후보만 전수 사실검증하여 최종 사용 가능한 뉴스 8~12건을 확보하라.

기본 검토 풀:
Phase2.2 기준 기존 PASS 28 + VERIFIED_WITH_CONTEXT 3 = 31 events.

VERIFICATION_HOLD 17과 REJECT 1은 excluded_pool에 보존하라.

절차:
1. 31개 후보를 기존 100점 점수, 교육 가치, 출처 신뢰도, 최신성, 중복도, 분야 균형으로 정렬
2. 12~15개 예비 후보 선정
3. 예비 후보의 제목·날짜·기관·모델·수치·정책·핵심 주장·원문 URL을 전수검증
4. 안전 문구 safe_title/safe_summary/safe_why_it_matters/safe_education_implication/safe_classroom_use 생성
5. FINAL_VERIFIED / FINAL_VERIFIED_WITH_CONTEXT / FINAL_HOLD / FINAL_REJECT 판정
6. 검증 완료 후보가 8건 이상이면 Phase2 PASS 후보
7. 8건 미만이면 excluded HOLD pool에서 점수 높은 순으로 추가 검증
8. REJECT 자동 재진입 금지

금지:
- 새 뉴스 후보 수집 목적의 Tavily 재검색
- 기간 변경
- Gemini 인증/운영 모델 변경
- 점수 배점 변경
- 70점 기준 변경
- Kakao 호출
- LIVE
- 운영 스케줄 변경
- 승인 없는 push
- 기사 수 맞추기 위한 저품질 뉴스 추가

출처 우선:
공식/정부/기관/기업/대학 → 연구 → 주요 통신·언론 → 전문매체.

중요 사실은 검색 snippet만으로 최종 승인하지 마라.

기존 112개 테스트를 모두 재실행하고 Phase2.3 신규 테스트를 추가하라.

최종 후보에는 safe_* 필드만 사용하도록 export 구조를 분리하라.

최종 보고 형식:
# Phase 2.3 실행 결과
## 1 Git 기준상태
## 2 입력 무결성
## 3 변경 파일
## 4 31개 후보 평가
## 5 예비 후보 선정 결과
## 6 출처 검증 통계
## 7 FinalVerification 결과
## 8 최종 사용 가능 후보 수
## 9 최종 후보 목록
## 10 제외/HOLD/REJECT 목록 요약
## 11 교육 분야 반영 결과
## 12 안전 콘텐츠 검증
## 13 기존 112개 회귀 테스트
## 14 신규 Phase2.3 테스트
## 15 Tavily/Gemini/Kakao 영향
## 16 보안 검사
## 17 생성 결과 파일
## 18 최종 PASS/WARN/HOLD/FAIL
## 19 Phase2 전체 콘텐츠 게이트 판정
## 20 Phase3 진입 가능 여부

반드시 생성:
PHASE2_3_EXECUTION_REPORT.md
PHASE2_3_RESULT_PACKAGE.zip

ZIP에는 보고서, 신규 소스, selection 결과, final verification records, source registry, safe_content 샘플, 테스트, audit, before/after, git diff를 포함하되 secret/.env/token/.git/가상환경은 제외하라.

마지막에는 다음 4개만 다시 출력:
1. 최종 판정
2. PHASE2_3_EXECUTION_REPORT.md 경로
3. PHASE2_3_RESULT_PACKAGE.zip 경로
4. git status
```

---

# 20. Phase 2.3 이후

Phase 2.3 결과에서 독립 검토를 실시한다.

검증 완료 후보가 최소 8건 이상이고 안전 콘텐츠·원문 URL·핵심 사실 검증이 모두 적절하면 Phase 2 전체 콘텐츠 게이트를 PASS로 전환할 수 있다.

그 후 Phase 3에서:
- 최종 8~12건 확정
- 상세 브리핑 생성
- 교육적 시사점 정제
- 수업 활용 아이디어 선택
- Kakao 모바일 압축판 생성
- 메시지 길이/링크/형식 검증
- Kakao TEST 발송

LIVE 자동 발송은 Phase 3 이후 별도 승인 후 진행한다.
