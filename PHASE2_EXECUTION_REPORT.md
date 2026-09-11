# Phase 2 실행 결과

## 1. Git 기준상태

- 체크아웃: `C:/Vibe Coding/kakaotalk_ai_new_daily/work/phase1-repo`
- branch: `phase1/tavily-search-test`
- Phase 1 커밋 전 latest commit: `001c849c878b3423ab5cfa2d53cd6aea65cccbf9`
- 현재 latest commit: `ec09427ed94b336ac5c77463b45a40fa6c61a419`
- Phase 2 구현 시작 시 git status: clean. 종료 시 신규 Phase 2 파일만 untracked.
- 기존 추적 파일 diff 없음. 실제 secret/config 추적 0건. 원래 작업 폴더에는 Git 메타데이터가 없어 기존 별도 체크아웃을 계속 사용.

## 2. Phase 1 기준본 커밋

- commit: `ec09427ed94b336ac5c77463b45a40fa6c61a419`
- message: `feat: add phase1 tavily search pipeline baseline`
- Phase 1 소스·쿼리·보고서·결과·ZIP 17개 파일을 비밀정보 재검사 후 로컬 커밋으로 고정.
- 커밋 직후 clean 확인. push하지 않음. Phase 2 코드는 아직 커밋하지 않음.

## 3. 변경 파일

- 생성: `news/phase2.py`, `news/phase2_events.py`, `news/phase2_gemini.py`, `news/phase2_guard.py`, `news/phase2_schema.py`, `news/test_phase2.py`.
- 생성: `news/phase2_requirements.txt` (jsonschema 4.26.0), `PHASE2_README.md`.
- 생성: `outputs/phase2/`의 실행 결과·검증 로그·스키마·샘플·audit·git diff, Phase 2 보고서 및 ZIP.
- 보조 생성: 원래 폴더의 `work/package_phase2.py`.
- 기존 파일 수정/삭제: 없음. 기존 인증 구조와 모델 설정 변경 없음.

## 4. 사건 중복 통합 결과

- 입력: Phase 1 normalized 후보 57건. 입력 SHA-256 `490b4608eb820ed679ee41a6dcfd969f22d032c493837c3ca220eee53d389e40`.
- 최종 TEST의 NewsEvent: 50건, 통합으로 줄어든 후보 7건.
- 실제 Gemini 관계 판정: {"SAME_EVENT": 13}.
- 판정 실패로 분리 유지한 쌍: 8개. 불확실한 쌍과 FOLLOW_UP은 강제 통합하지 않음.
- 규칙 기반 후보화, 동일 제목·snippet 규칙 통합, Gemini 의미 판정, confidence >=0.9 및 원문 인용 근거 검증 적용.
- 모든 후보가 정확히 한 이벤트에 포함됨을 확인. 대표·보조 출처 필드는 입력과 동일. event_date는 발행일로 대체하지 않고 null.
- 동일 사건 3개 URL→1개 이벤트, FOLLOW_UP/DIFFERENT_EVENT 분리 및 전이적 오통합 방지 테스트 PASS.

## 5. Gemini Paid API 테스트 결과

- 사용자 지정 유료 프로젝트 키로 실제 호출. 모델 `gemini-3.1-flash-lite`은 기존 설정을 읽어 GEMINI_MODEL 환경변수로 주입.
- API 응답으로 결제 등급을 판정하지 않았으며 인증 방식·키·모델 설정 파일은 변경하지 않음.
- 최종 실행: `2026-09-09T12:57:23.856829+00:00` ~ `2026-09-09T13:00:38.358143+00:00` (UTC).
- 최종 HTTP 시도: 55회. 최초 실행·진단·재검증 합계: 121회.
- 구조화 분석 확보: 50건. 일반 분석 파일 22건, HOLD 위험 분석 28건.
- 실제 Gemini 접근 성공. 최종 콘텐츠 게이트는 HOLD.
- 400/401/403/404 재시도 없음. 429 Retry-After 우선, 5xx/네트워크 제한 백오프. 호출당 최대 3회, 스키마 재시도 최대 1회, 실행당 최대 150 HTTP 시도.

## 6. 구조화 출력/스키마 테스트

- jsonschema Draft 2020-12 검증 및 Gemini responseJsonSchema 적용.
- 필수 필드·추가 필드 금지·category·점수 범위·total 합계·타입·null·문자열 길이·event ID 검증 PASS.
- 최초 실제 중복 판정에서 대표 출처 설명문이 반환되어 ID 검증 실패. 후보 ID enum과 명시적 프롬프트로 수정 후 전체 재실행.
- 최종 저장된 이벤트 및 분석 스키마 재검증 PASS. 유효하지 않은 이벤트 응답은 성공 데이터에 넣지 않음.

## 7. 중요도 평가 통계

- 배점: 교육 30 / 기술 20 / 교사·학생 15 / 사회·산업 15 / 신뢰도 10 / 최신성 10.
- 점수 최저: 5, 최고: 85, 평균: 59.18.
- 70점 이상: 18건.
- 통계는 HOLD를 포함한 스키마 유효 분석 전체 기준. 70점 이상이어도 검증 완료나 발송 선정이 아님.
- 최종 8~12건 선정·발송 확정 없음.

## 8. hallucination 방어 테스트

- 입력에 없는 숫자·날짜·기관·모델·정책명·URL 및 불확실성의 확정 표현 강화 주입 테스트 PASS.
- 실제 high_risk: 28건. 탐지 코드별 발생 수: {"UNSUPPORTED_ENTITY_MODEL_POLICY": 30, "UNSUPPORTED_NUMBER_OR_DATE": 17}.
- 모델 자체 high 판정만 있는 사례: 3건.
- 위험 결과는 high_risk 파일에 HOLD로 보관하고 일반 분석에서 제외. fact_check_targets에 자동 탐지 사유 추가.
- 이 검사는 사전적/문자열 기반이며 번역·단위 환산·일반 대문자 단어의 오탐 가능성이 있다. 임의 고유명사·의미적 환각의 완전 탐지를 보장하지 않는다.
- 원문 사실 검증은 미완료. 정상 파일도 발송 승인 결과가 아니다.

## 9. 오류 및 경고

- 최종 이벤트 오류: [].
- 최종 경고 코드별 수: {"DEDUP_EVIDENCE_INVALID": 1}.
- 최초 실행과 추가 후보 한 쌍 진단에서 REPRESENTATIVE_ID_INVALID 발견. enum 제약 보강 후 재실행했으며 초기 로그를 보존.
- 한글 조사와 영문 기관명이 붙은 경우의 탐지 테스트 실패를 정규식 경계 수정으로 해결 후 전체 재검증.
- 고위험 판정은 미검증 사실 후보이며 모두 실제 허위라고 단정하지 않음. 사람/공식 출처 검토 없이 위험 등급을 낮추지 않음.
- 모델 기반 의미 판정의 불확실성 및 보수적 후보 생성에 따른 누락 가능성이 남음. 기준 데이터는 Phase 1 저장 시점의 최근 7일 결과이며 이번에 새 Tavily 검색하지 않음.

## 10. Phase 1 회귀 결과

- Phase 2 23개 + Phase 1 16개 + 기존 회귀 10개 = 49개 테스트 PASS.
- 기존 Phase 1 코드·결과·설정의 Git diff 없음. 원래 보호 파일 10개 해시 동일.
- 정적 검사: AST·컴파일·후행 공백·파일 끝 개행 PASS. 추가 외부 lint 도구는 사용하지 않음.
- 테스트의 전송 stdout은 mock 결과이며 실제 API 발송 없음.

## 11. 기존 Kakao 기능 영향

- Kakao 관련 구현·설정 수정 없음. Kakao 인증/발송 실제 호출 0회.
- LIVE 실행 0회, 운영 스케줄 변경 없음, push 없음.
- 기존 Gemini 인증 구조는 재설계하지 않고 Phase 2 전용 클라이언트만 추가.

## 12. 생성 결과 파일 경로

- 최종 결과 디렉터리: `C:/Vibe Coding/kakaotalk_ai_new_daily/work/phase1-repo/outputs/phase2/20260909T125723856804Z`
- events: `events/events.json`, 관계 판정: `events/decisions.json`.
- analysis: `analysis/analysis.json`, high_risk: `analysis/high_risk.json`.
- 실행 로그: `logs/run.json`.
- 검증 로그/audit/schema/diff: `C:/Vibe Coding/kakaotalk_ai_new_daily/work/phase1-repo/outputs/phase2/verification`.
- event/Gemini/high_risk 샘플: `C:/Vibe Coding/kakaotalk_ai_new_daily/work/phase1-repo/outputs/phase2/samples`.
- 보고서: `C:/Vibe Coding/kakaotalk_ai_new_daily/PHASE2_EXECUTION_REPORT.md`.
- ZIP: `C:/Vibe Coding/kakaotalk_ai_new_daily/PHASE2_RESULT_PACKAGE.zip`.
- ZIP은 명시적 허용 목록으로 구성하고 비밀 config·토큰·환경 파일·Git 메타데이터·가상환경 제외. 실제 알려진 비밀값 및 키 패턴 검사 수행.

## 13. 최종 PASS/WARN/HOLD/FAIL

**HOLD**

## 14. 판정 근거

구현과 49개 오프라인 테스트, 실제 Gemini 호출, 구조화 출력·점수 검증, 기준본 보존 및 보안 검사를 완료했다.
그러나 최종 실제 입력에서 고위험 결과 28건과 미해결 중복 판정 8쌍이 있으므로
완료된 구현의 테스트 통과와 별개로 콘텐츠 품질 게이트는 HOLD로 유지한다.
제공된 자료에 없는 사실을 확인 없이 승인하지 않으며 최종 발송 목록도 만들지 않았다.
지정 문서 우선순위 1~7을 적용했다. API 계약은 Google 공식 generate-content/structured-output/troubleshooting 문서를 확인했다.

## 15. Phase 3 진입 가능 여부

**보류.** Phase 2가 PASS되기 전 Phase 3로 진행하지 않는다.
중복 판정 실패 근거와 high_risk 샘플을 검토하고, 오탐과 실제 미검증 사실을 구분한 후 필요한 수정·재검증을 권고한다.
이번 작업에서 Phase 3, Kakao 발송, LIVE 운영 반영은 수행하지 않았다.
