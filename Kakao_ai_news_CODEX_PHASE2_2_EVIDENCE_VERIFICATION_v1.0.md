# Kakao ai news — Phase 2.2 Evidence Verification v1.0

## 0. 목적과 상태
- 환경: Paid Gemini API + Codex
- 현재: Phase 1 PASS / Phase 2 구현 PASS / Phase 2.1 Guard·Dedup 보정 PASS / 콘텐츠 게이트 HOLD
- 목표: Phase 2.1의 VERIFY 5건과 AUTO_HOLD 16건을 실제 원문·공식 1차 자료·신뢰 출처로 검증한다.
- 원칙: Guard를 느슨하게 만들지 않는다. 위험 판정을 삭제하지 않고 증거로 해소한다.

## 1. 문서 우선순위
1. `Kakao_ai_news_PROJECT_INSTRUCTIONS_FINAL.md`
2. `Kakao_ai_news_WORKFLOW_v1.0.md`
3. `Kakao_ai_news_AUTOMATION_SPEC_v1.0.md`
4. `Kakao_ai_news_CODEX_IMPLEMENTATION_START_PHASE1_v1.0.md`
5. `PHASE1_EXECUTION_REPORT.md`
6. `Kakao_ai_news_CODEX_IMPLEMENTATION_PHASE2_v1.0.md`
7. `PHASE2_EXECUTION_REPORT.md`
8. `Kakao_ai_news_CODEX_PHASE2_1_GUARD_DEDUP_HARDENING_v1.0.md`
9. `PHASE2_1_EXECUTION_REPORT.md`
10. 본 문서
11. `references/*.md`

## 2. 고정 기준
Phase 2.1 기준: 후보 57 / NewsEvent 49 / PASS 28 / VERIFY 5 / AUTO_HOLD 16 / SAME_EVENT 17 / FOLLOW_UP 3 / DIFFERENT_EVENT 1 / 미해결 중복 0 / 70점 이상 20 / 테스트 79 PASS.

변경 금지: 뉴스 후보·기간, 중요도 배점(30/20/15/15/10/10), 70점 기준, Gemini 인증 및 운영 모델 값, Kakao 인증·발송, LIVE·스케줄. 새 뉴스 발굴 목적의 Tavily 재검색도 금지한다. 검증 대상 원문·공식 자료 확보를 위한 제한적 HTTP/웹 조회만 허용한다.

## 3. 검증 상태
각 `fact_check_target`을 다음 중 하나로 판정한다.
- `VERIFIED_SUPPORTED`: 신뢰 출처에서 직접 확인
- `VERIFIED_EQUIVALENT`: 표현만 다르고 의미가 안전하게 동일(two-hour↔2시간, 8th grade↔8학년 등)
- `VERIFIED_CONTEXTUAL`: 핵심은 맞으나 문맥 보존/문구 수정 필요
- `UNRESOLVED`: 접근 실패 또는 근거 부족
- `VERIFIED_UNSUPPORTED`: 검증 출처에서 근거가 없는 새 핵심 사실
- `CONTRADICTED`: 신뢰 출처가 다른 사실을 명시

## 4. 출처 우선순위
공식 정부·기관·대학·기업 원문 → 논문·연구기관 → 주요 통신·신뢰 언론 원 기사 → 기술·과학 전문매체 → 기타 신뢰 보조출처 순이다. 검색 snippet만으로 중요한 수치·정책·모델명을 최종 VERIFIED 처리하지 않는다. 기존 `primary_source.url`, `supporting_sources[].url`을 먼저 확인하고, 필요할 때만 검증 전용 공식 출처를 추가한다.

추가 검증 출처는 `url/source_name/source_type/retrieved_at/verification_only=true`를 기록한다. 긴 원문은 저장하지 말고 필요한 최소 증거 또는 짧은 paraphrase만 보존한다.

## 5. 검증 단위와 EvidenceRecord
이벤트 전체가 아니라 숫자·날짜·기관·모델·정책·제품·출시/금지/허용·학년·지역·URL 등 claim 단위로 검증한다.

```json
{
  "event_id":"evt_x",
  "target_id":"fc_x",
  "claim":"string",
  "claim_type":"number|date|entity|model|policy|url|event_claim|other",
  "guard_status":"VERIFY|AUTO_HOLD",
  "verification_status":"VERIFIED_SUPPORTED|VERIFIED_EQUIVALENT|VERIFIED_CONTEXTUAL|UNRESOLVED|VERIFIED_UNSUPPORTED|CONTRADICTED",
  "evidence":[{"source_url":"https://...","source_name":"string","source_type":"official|research|major_media|specialist","evidence_text":"short evidence/paraphrase","candidate_id":null}],
  "reason":"string",
  "checked_at":"ISO-8601"
}
```

Guard 원본 판정은 덮어쓰지 않는다. `guard_original=AUTO_HOLD`, `verification_final=VERIFIED_EQUIVALENT`처럼 함께 보존한다.

## 6. 세부 검증 규칙
숫자·날짜는 영문 숫자↔아라비아 숫자, ordinal↔학년, percent↔%, 쉼표, 날짜 표기 차이를 문맥까지 확인한다. 단순 문자열 치환만으로 VERIFIED 처리하지 않는다.

기관·모델·정책·제품은 공식 명칭과 alias/번역명이 실제 같은 대상을 뜻하는지 확인한다. 근거 없는 세부 버전·제품명은 UNSUPPORTED다.

Gemini가 새 URL을 생성했다면 기존 입력 URL 또는 실제 검증 과정에서 확보한 공식 URL인지 확인한다. 둘 다 아니면 UNSUPPORTED다.

출처가 충돌하면 임의 선택하지 않는다. 공식성·발표시점·원출처를 고려하되 해결되지 않으면 UNRESOLVED/CONTRADICTED로 남기고 자동 발송 후보에서 제외한다.

Gemini는 원문 근거 위치 요약, 표현 동등성 비교, 증거 차이 설명, 보수적 재작성만 보조할 수 있다. Gemini 자체 기억만으로 VERIFIED 처리하거나 URL·수치·사실을 보충하면 안 된다.

## 7. 검증 후 처리
- SUPPORTED/EQUIVALENT: claim 유지 가능
- CONTEXTUAL: 문맥을 반영해 수정 후 유지
- UNRESOLVED: 핵심 claim이면 이벤트 HOLD
- UNSUPPORTED: claim 제거 후 의미 재검증, 핵심이면 REJECT/HOLD
- CONTRADICTED: 잘못된 claim 제거, 핵심 사건과 충돌하면 REJECT

이벤트 최종 상태:
- `VERIFIED_PASS`
- `VERIFIED_WITH_CONTEXT`
- `VERIFICATION_HOLD`
- `REJECT`

## 8. 필수 테스트
1. two-hour ↔ 2시간 → EQUIVALENT
2. 8th grade ↔ 8학년 → 문맥 동일 시 EQUIVALENT
3. snippet에 없지만 공식 원문에 있는 숫자 → SUPPORTED
4. 입력·원문 모두에 없는 숫자 → UNSUPPORTED
5. 존재 근거 없는 모델명 → UNSUPPORTED
6. 정책 대상 범위가 원문과 다름 → CONTRADICTED
7. 원문 접근 실패 → UNRESOLVED
8. 공식 자료와 언론 충돌 → 우선순위 적용 및 unresolved 여부 기록
9. 검증용 공식 URL → verification_only
10. Gemini 임의 URL → UNSUPPORTED
11. 비핵심 unsupported 표현 제거 후 의미 유지 → 재검증 PASS
12. 핵심 unsupported claim 제거 시 사건 의미 붕괴 → REJECT/HOLD

기존 회귀 10 + Phase1 16 + Phase2 23 + Phase2.1 30 = 79개도 전부 다시 실행한다. 하나라도 실패하면 최종 PASS 금지.

## 9. 통계와 성공 기준
이벤트 수와 `fact_check_target` 수, 실제 검증 claim 수를 각각 기록한다.

Before: PASS 28 / VERIFY 5 / AUTO_HOLD 16.
After: VERIFIED_PASS / VERIFIED_WITH_CONTEXT / VERIFICATION_HOLD / REJECT.
Claim 통계도 6개 verification status별로 기록한다.

Phase 2 전체 콘텐츠 게이트 PASS 검토 조건:
1. 기존 PASS 이벤트 무결성 유지
2. 위험 이벤트 핵심 claim 검증
3. UNSUPPORTED/CONTRADICTED가 안전 콘텐츠에 남지 않음
4. UNRESOLVED 핵심 claim 이벤트 자동 제외
5. 최종 사용 URL 검증
6. 기존 79개+신규 테스트 PASS
7. Tavily/Gemini/Kakao 설정 무변경
8. secret 비노출
9. Kakao 호출 0
10. LIVE 0

## 10. 결과 파일
반드시 생성:
- `PHASE2_2_EXECUTION_REPORT.md`
- `PHASE2_2_RESULT_PACKAGE.zip`

권장:
`outputs/phase2_2/evidence/evidence_records.json`, `source_registry.json`, `analysis/verified_pass.json`, `verified_with_context.json`, `verification_hold.json`, `reject.json`, `logs/run.json`, `tests.txt`, `audit.json`, `verification/before_after.json`, `git_diff.patch`.

ZIP에서 secret/.env/token/Git metadata/가상환경을 제외한다.

## 11. Codex 실행 프롬프트
```text
Kakao ai news 프로젝트 Phase 2.2 Evidence Verification을 구현하고 실행하라.

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
11 references/*.md

Phase 2.1 Guard를 완화하지 말고 남은 VERIFY/AUTO_HOLD의 fact_check_targets를 실제 원문·공식 자료·신뢰 출처의 증거로 검증하라.

시작 전 git status, branch, latest commit, Phase1 baseline, Phase2/2.1 미커밋 보존, secret 추적 여부, Phase1 입력 SHA와 Phase2.1 결과 무결성을 확인하라.

금지: 새 뉴스 후보 수집 목적 Tavily 재검색, 기간 변경, Guard 완화, 배점/70점 기준 변경, Gemini 인증·운영 모델 설정 변경, Kakao 설정/호출, LIVE, 운영 스케줄 변경, 최종 8~12건 확정, 승인 없는 push.

검증 대상은 Phase2.1 VERIFY 5건 + AUTO_HOLD 16건을 우선하되 event 수와 fact_check_target 수를 분리 기록하라.

공식/정부/기관/기업/대학 원문 → 연구 원문 → 주요 통신·언론 원 기사 → 전문매체 순으로 증거를 확인하라. 검색 snippet만으로 핵심 claim을 최종 VERIFIED 처리하지 마라.

claim 상태:
VERIFIED_SUPPORTED / VERIFIED_EQUIVALENT / VERIFIED_CONTEXTUAL / UNRESOLVED / VERIFIED_UNSUPPORTED / CONTRADICTED.

event 상태:
VERIFIED_PASS / VERIFIED_WITH_CONTEXT / VERIFICATION_HOLD / REJECT.

Guard 원본 상태를 삭제하지 말고 verification 결과와 함께 보존하라. 특히 two-hour↔2시간, 8th grade↔8학년, 숫자, 날짜, 모델명, 기관명, 정책명, 새 URL, 공식 발표 여부를 검증하라.

UNSUPPORTED/CONTRADICTED claim은 안전 콘텐츠에 남기지 말고, UNRESOLVED 핵심 claim은 자동 발송 후보로 통과시키지 마라.

기존 79개 테스트를 전부 재실행하고 Phase2.2 신규 테스트를 추가하라.

보고서:
# Phase 2.2 실행 결과
## 1 Git 기준상태
## 2 입력/결과 무결성
## 3 변경 파일
## 4 검증 대상 통계
## 5 사용 출처 통계
## 6 Claim 검증 결과
## 7 Event 최종 검증 결과
## 8 two-hour/8th-grade 사례
## 9 UNSUPPORTED/CONTRADICTED 처리
## 10 UNRESOLVED 처리
## 11 기존 79개 회귀 테스트
## 12 신규 Phase2.2 테스트
## 13 Tavily/Gemini/Kakao 영향
## 14 보안 검사
## 15 생성 결과 파일
## 16 최종 PASS/WARN/HOLD/FAIL
## 17 판정 근거
## 18 Phase2 전체 콘텐츠 게이트 권고
## 19 Phase3 진입 가능 여부

반드시 PHASE2_2_EXECUTION_REPORT.md와 PHASE2_2_RESULT_PACKAGE.zip을 생성하라. ZIP은 보고서·신규소스·테스트·audit·evidence/source registry·before/after·verified/hold/reject 샘플·git diff만 포함하고 secret을 제외하라.

마지막에는 최종 판정, 보고서 경로, ZIP 경로, git status만 다시 출력하라.
```

## 12. 완료 후
Codex 결과는 독립 검토한다. 원문 증거가 claim을 실제 지지하는지, 공식 자료 우선순위, unsupported/contradicted 제거, unresolved 차단, URL 검증, 기존 정상 기준본/API 설정 보존을 확인한다.

독립 검토 PASS 후에만 Phase 3(검증 완료 이벤트 → 가치 선별 → 8~12건 권고 → 상세 브리핑 → Kakao 모바일 압축판 → Kakao TEST 발송)로 이동한다. LIVE 자동 발송은 이후 별도 승인 대상이다.
