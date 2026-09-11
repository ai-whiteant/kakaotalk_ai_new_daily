# Phase 2.1 실행 결과

## 1. Git 기준상태

- 작업 저장소: `C:/Vibe Coding/kakaotalk_ai_new_daily/work/phase1-repo`
- branch: `phase1/tavily-search-test`
- latest commit / Phase 1 baseline: `ec09427ed94b336ac5c77463b45a40fa6c61a419`
- 시작 시 Phase 2 소스·보고서·결과가 untracked인 기존 상태 확인. 해당 미커밋 파일 보존.
- Phase 2.1 신규 파일만 추가. 기존 추적 파일 수정 없음. commit/push 없음. 실제 secret/config 추적 0건.

## 2. 입력 무결성 SHA 검증

- 기대값 및 실제값: `490b4608eb820ed679ee41a6dcfd969f22d032c493837c3ca220eee53d389e40`
- 정확히 일치, 후보 57건. 시작 전과 결과 감사 시 재확인.
- 불일치 시 API 호출 전 HOLD하는 신규 테스트 PASS. 새 Tavily 검색 없음.

## 3. 변경 파일

- 생성: `news/phase21.py`, `news/phase21_guard.py`, `news/phase21_events.py`, `news/phase21_recheck.py`, `news/test_phase21.py`, `PHASE2_1_README.md`.
- 생성: Phase 2.1 결과·로그·Before/After·audit·샘플·git diff·보고서·ZIP.
- 보조 파일: `work/phase21_before_hashes.json`, `work/package_phase21.py`.
- 기존 Phase 1/2 파일 수정·삭제 없음. 기존 59개 체크아웃 파일의 SHA 동일.

## 4. 기존 49개 회귀 테스트

- 기존 회귀 10 + Phase 1 16 + Phase 2 23 = 49개 전부 PASS.
- 신규 30개 포함 총 79개 PASS. API 호출은 mock이며 실제 Kakao 전송 없음.

## 5. 신규 Guard 테스트

- World Bank phrase/alias, World·Bank 분리 방지 PASS.
- Educators, Policymakers, Conversely, Additionally, AI-driven/generated/powered 일반 표현 처리 PASS.
- 단, 명시적으로 이름 붙인 모델/기관 문맥은 제외 목록으로 통과시키지 않음.
- 8th grade ↔ grade 8 및 supporting candidate 근거 PASS.
- 숫자 표기 변환 불확실성 VERIFY, 완전한 날짜 비교, 감사 필드 및 fact_check_targets 연계 PASS.
- GPT-99와 GPT-999의 접두어 혼동 방지, 원 모델 위험 보존, 재검사 원본 필드 복구 테스트 PASS.

## 6. 신규 Dedup 테스트

- 동일 정책 다중 보도, 같은 기관 다른 정책, 같은 기업 다른 모델, 후속 관계 보존 PASS.
- 잘못된 evidence는 해당 쌍만 실패 처리. 유효한 다른 쌍 보존 PASS.
- 전이적 과병합 방지 및 해설/전문가 반응을 원 보도와 분리하는 테스트 PASS.
- 실제 사건 검토에서 발견한 해설 혼합 2쌍을 FOLLOW_UP으로 분리. 변경 근거와 원 판정을 보존.

## 7. Guard Before/After

비교 A — 동일한 기존 분석 50건을 그대로 새 Guard로 검사(API 호출 없음):

- Before: 일반 22 / high-risk HOLD 28.
- After: {"PASS": 11, "VERIFY": 10, "AUTO_HOLD": 29}.
- 기존 high 필드는 이전 Guard가 이미 수정했을 수 있어 원 모델 판정은 복원 불가. 이 한계를 비교 파일에 기록.

비교 B — 동일 후보 57건으로 새 Gemini 실행 및 사건 분리 후 최종 분석:

- PASS 28 / VERIFY 5 / AUTO_HOLD 16 (총 49건).
- 새 실행의 AUTO_HOLD 감소를 Guard 보정만의 효과로 해석할 수 없다. 사건 구성·모델 생성 결과가 달라졌으며, 감소 자체를 성공 기준으로 삼지 않았다.
- 마지막 결정적 Guard 재검사는 추가 API 호출 0회, 판정 건수 변동 없음.

## 8. Dedup Before/After

| 항목 | Phase 2 | Phase 2.1 최종 |
|---|---:|---:|
| 후보 | 57 | 57 |
| 사건 | 50 | 49 |
| SAME_EVENT | 13 | 17 |
| FOLLOW_UP | 0 | 3 |
| DIFFERENT_EVENT | 0 | 1 |
| 미해결 쌍 | 8 | 0 |
| 70점 이상 | 18 | 20 |

- 쌍별 호출과 원문 evidence enum으로 배치 동반 실패 제거.
- 후속 관계는 related_events로 양방향 보존하며 사건의 시간적 방향은 추정하지 않음.
- 57개 후보가 정확히 한 이벤트에 포함, 모든 병합은 complete-link 근거, 출처 필드 원본 일치 확인.
- 70점 기준과 배점은 그대로이며 최종 발송 선정 없음.

## 9. 실제 unsupported claim 방어 결과

- 없는 숫자·날짜·모델·URL 주입 시 AUTO_HOLD 유지.
- 단순 고유명사 허용 목록으로 실제 새 World Bank/모델 주장을 통과시키지 않음.
- 실제 잔여 AUTO_HOLD 16건. 탐지 발생 수: {"UNSUPPORTED_NUMBER_OR_DATE": 10, "UNSUPPORTED_ENTITY_MODEL_POLICY": 10}.
- 각 발견은 output_field·reason·matched_input·candidate_ids와 fact_check_evidence에 기록.
- 문자열/정규화 기반 검사이므로 완전한 의미 검증은 아니다. VERIFY 및 AUTO_HOLD 모두 사람/공식 출처 검토 대상.

## 10. Gemini API 실행 결과

- 기존 키·프로젝트·모델 `gemini-3.1-flash-lite` 및 기존 인증 클라이언트 재사용.
- 실제 HTTP 시도 총 72회. 21쌍 의미 판정, 최초 47개 사건 분석, 분리된 새 사건 4개만 추가 분석.
- 나머지 동일 사건 분석은 재사용. Guard 재검사는 추가 API 호출 없음.
- 실제 호출 오류: []. 경고: [].
- 설정 파일 변경 없이 기존 모델 값을 실행 환경에 주입. 응답으로 결제 등급을 새로 추정하지 않음.

## 11. 오류 및 경고

- 개발 중 한글 조사 뒤 날짜 경계 및 날짜 구성 숫자 중복 검증 문제를 수정하고 전체 재검증 PASS.
- 해설 기사 2쌍의 과병합 위험을 발견해 FOLLOW_UP으로 수정; 신규 사건 4개 재분석 완료.
- 고위험 잔여 항목은 해결되지 않았다. AUTO_HOLD를 수치 개선 목적으로 VERIFY/PASS로 낮추지 않음.
- 일반 표현·명칭 문맥 및 날짜 형식의 지원 범위에는 한계가 있음. 원문 사실 검증과 독립 Phase 3 진입 승인은 미완료.

## 12. 기존 Tavily/Gemini/Kakao 설정 영향

- Tavily 검색·설정 변경 없음, 호출 0회.
- Gemini 키·인증 구조·운영 모델 값·점수 배점 변경 없음.
- Kakao 설정·인증·발송 변경 없음, 호출 0회.
- LIVE 실행·운영 스케줄 변경·push 없음.
- 원래 보호 파일 10개 및 기존 체크아웃 59개 파일 해시 동일.

## 13. 보안 검사

- 실제 알려진 config/environment 비밀값 및 키 형태를 신규 소스·출력·ZIP 내부에서 검사: PASS.
- 실제 secret 추적 0건. 비밀 config/token/.env/Git metadata/가상환경은 ZIP 제외.
- 스키마·기준본·입력·출처·complete-link·정적 검사 PASS. audit 파일에 근거 기록.

## 14. 생성 결과 파일

- 보고서: `C:/Vibe Coding/kakaotalk_ai_new_daily/work/codex_etc/PHASE2_1_EXECUTION_REPORT.md`
- ZIP: `C:/Vibe Coding/kakaotalk_ai_new_daily/work/codex_etc/PHASE2_1_RESULT_PACKAGE.zip`
- 전체 실제 결과: `C:/Vibe Coding/kakaotalk_ai_new_daily/work/phase1-repo/outputs/phase2_1`
- TEST 로그/audit: `logs/tests.txt`, `logs/audit.json`, `logs/run.json`.
- Before/After: `verification/guard_before_after.json`, `dedup_before_after.json`.
- 보정 근거: `verification/editorial_relation_review.json`, `final_guard_recheck.json`.
- 샘플: `samples/events.json`, `analysis.json`, `verify.json`, `auto_hold.json`.
- ZIP에는 보고서·신규 소스·테스트/실행 로그·audit·Before/After·샘플·git diff만 포함.

## 15. 최종 PASS/WARN/HOLD/FAIL

**HOLD**

## 16. 판정 근거

동일 입력 무결성, 기존 49개 및 신규 30개 테스트, 설정 보존, 근거 추적, 중복 미해결 해소를 검증했다.
그러나 실제 콘텐츠에 AUTO_HOLD 16건과 VERIFY 5건이 남아 최종 콘텐츠 게이트는 HOLD로 유지한다.
일반 표현 오탐 사례의 개선과 전체 결과의 위험 해소는 구분하며, 기존 분석 재검사의 AUTO_HOLD 29건도 숨기지 않았다.
지정 문서 우선순위 1~9를 적용했으며 기존 Phase 1/2 정상 구현은 보존했다.

## 17. Phase 3 진입 가능 여부

**보류.** 잔여 AUTO_HOLD/VERIFY의 근거 검토 및 독립 품질 검토 PASS가 필요하다.
이번 작업에서는 Phase 3·Kakao 발송·LIVE를 진행하지 않았다.
