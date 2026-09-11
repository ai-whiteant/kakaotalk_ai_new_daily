# Kakao ai news — Phase 3 Briefing & Kakao TEST Gate v1.0

- 프로젝트: Kakao ai news
- Canonical Root: `C:\Vibe Coding\kakaotalk_ai_new_daily`
- 기준 브랜치: `main`
- 시작 기준 커밋: `c94cfcd1fb163ed7bda4fc099a16b5119c65f39f`
- 선행 조건: Phase 2.3 독립 검토 PASS / Phase 2 전체 콘텐츠 게이트 PASS
- 목적: 검증 완료 `safe_*` 8건만 사용해 최종 AI 뉴스 브리핑과 Kakao 모바일판을 생성·검수하고, KakaoTalk `나에게 보내기` TEST 1회를 검증한다.
- LIVE 자동 발송: 금지. 별도 승인 필요.

---

## 1. 적용 우선순위

1. `AGENTS.md`
2. `SESSION_HANDOFF.md`
3. `docs/Kakao_ai_news_PROJECT_INSTRUCTIONS_FINAL.md`
4. `Kakao_ai_news_WORKFLOW_v1.0.md`
5. `Kakao_ai_news_AUTOMATION_SPEC_v1.0.md`
6. `Kakao_ai_news_CODEX_PHASE2_3_FINAL_CANDIDATE_VERIFICATION_v1.0.md`
7. `PHASE2_3_EXECUTION_REPORT.md`
8. 본 문서
9. `references/.../references/*.md`

충돌 시 상위 문서를 따른다.

---

## 2. Phase 3 입력 Source of Truth

최종 기사 입력은 다음만 사용한다.

- `outputs/phase2_3/samples/safe_content.json`
- 필요 시 `outputs/phase2_3/selection/final_candidates.json`
- 필요 시 `outputs/phase2_3/verification/final_verification_records.json`

`safe_content.json`의 8건을 기본 최종 풀로 고정한다.

금지:
- raw Gemini summary를 최종 메시지로 재사용
- HOLD/REJECT 사건 재진입
- 새 뉴스 수집을 위한 Tavily 재검색
- 기사 수를 맞추기 위한 후보 추가
- 검증된 의미보다 강한 표현 생성
- 원문에 없는 수치/성과/인과관계 생성

---

## 3. Phase 3A — 최종 브리핑 생성

### 3.1 상세 브리핑
기본 형식:

`뉴스 제목 → 핵심 내용 → 왜 중요한가 → 교육적 시사점 → 필요 시 수업 활용 → 원문 링크`

규칙:
- `safe_title` → 제목
- `safe_summary` → 핵심 내용
- `safe_why_it_matters` → 왜 중요한가
- `safe_education_implication`이 null이면 교육적 시사점 섹션을 생성하지 않는다.
- `safe_classroom_use`가 null이면 수업 활용 섹션을 생성하지 않는다.
- `safe_original_url`은 변경·추측하지 않는다.
- `safe_category`는 분야 구분에만 사용한다.

### 3.2 정렬
권장 순서:
1. AI 교육
2. AI 정책·윤리
3. 국내 AI
4. AI 기술·모델
5. AI 산업

기사 중요도를 해치지 않는 범위에서 동일 분야를 묶는다.

### 3.3 이번 주 AI 한눈에 보기
최종 8건에 근거해서만 다음을 작성한다.
- 가장 중요한 변화
- 교육계 핵심 이슈
- 주목할 AI 기술
- 향후 관찰 포인트

새 사실을 추가하지 않는다.
사실과 해석을 분리한다.

---

## 4. Phase 3A — Kakao 모바일판

모바일 가독성을 우선한다.

예시 구조:

```
📢 Kakao AI News [TEST]
YYYY.MM.DD | 최근 7일 AI 핵심 뉴스

━━━━━━━━━━━━
🏫 AI 교육
━━━━━━━━━━━━

① 제목

📌 핵심 내용
...

💡 왜 중요한가
...

👨‍🏫 교육적 시사점
...

📖 수업 활용
...

🔗 원문
https://...
```

규칙:
- TEST 단계에는 제목 또는 첫 메시지에 `[TEST]`를 명확히 표시한다.
- 긴 메시지는 논리 단위로 분할한다.
- 메시지 길이 한도는 현재 Kakao 공식 문서/기존 정상 구현을 확인해 적용하며 임의 숫자를 새로 고정하지 않는다.
- 분할 시 기사 중간을 임의로 잘라 의미가 깨지지 않도록 한다.
- 원문 URL은 해당 기사 블록과 함께 유지한다.

---

## 5. Phase 3A 품질 게이트

아래를 모두 PASS해야 Kakao API TEST를 호출할 수 있다.

1. 최종 기사 정확히 8건
2. 입력 event_id 8개가 Phase 2.3 최종 후보와 일치
3. HOLD/REJECT 0건
4. final message의 사실 문구가 `safe_*` 범위를 벗어나지 않음
5. 원문 URL 8개 유지
6. null 교육/수업 필드에 억지 섹션 생성 없음
7. 중복 기사 없음
8. 모바일 분할 후 기사 누락 0
9. 메시지 순서·번호 중복 없음
10. `[TEST]` 표시
11. secret/log 노출 0
12. 기존 140개 테스트 PASS
13. Phase 3 신규 테스트 PASS
14. Tavily/Gemini/Kakao 운영 설정 변경 없음
15. LIVE 0

하나라도 실패하면 Kakao TEST 호출을 하지 않고 HOLD한다.

---

## 6. Phase 3B — KakaoTalk TEST 발송

Phase 3A 품질 게이트 PASS 후에만 실행한다.

대상:
- KakaoTalk `나에게 보내기`

규칙:
- 기존 Kakao 인증/토큰 흐름을 그대로 사용한다.
- `references/.../06_KAKAO_TALK_MESSAGE_API.md`
- `references/.../07_KAKAO_LOGIN_SCOPE_TOKEN.md`
를 확인한다.
- Access Token / Refresh Token / Client Secret을 출력·보고서·Git에 기록하지 않는다.
- 인증 오류 발생 시 Kakao 단계만 HOLD한다.
- Kakao 오류 때문에 Tavily/Gemini 설정을 변경하지 않는다.
- 토큰 갱신이 기존 정상 구현에 포함된 경우 그 흐름만 사용한다.
- TEST 발송은 1회 논리 실행으로 수행하고, 메시지 분할이 필요하면 동일 TEST 실행의 여러 메시지로 기록한다.
- 실제 응답은 status/code/message ID 등 비민감 정보만 마스킹 저장한다.

### TEST 결과 상태
- `TEST_SEND_PASS`
- `TEST_SEND_HOLD_AUTH`
- `TEST_SEND_HOLD_SCOPE`
- `TEST_SEND_HOLD_API`
- `TEST_SEND_FAIL`

LIVE는 어떤 경우에도 실행하지 않는다.

---

## 7. 신규 구현 권장 구조

기존 구조를 먼저 조사하고 최소 변경한다.

권장:
- `news/phase3.py`
- `news/phase3_briefing.py`
- `news/phase3_kakao.py` (기존 Kakao 모듈이 있으면 재사용 우선)
- `news/test_phase3.py`

기존 정상 Kakao 구현이 있으면 새 인증 모듈을 만들지 말고 재사용한다.

---

## 8. Phase 3 테스트

필수 신규 테스트 예시:

1. safe_content 정확히 8건
2. safe-only content enforcement
3. HOLD/REJECT 차단
4. URL 8개 보존
5. null 교육 필드 생략
6. null classroom 필드 생략
7. 교육 3건 우선 배치
8. 기사 번호 중복 방지
9. 모바일 분할 후 8건 보존
10. 기사 블록 중간 분할 방지
11. TEST 표식 확인
12. 이번 주 요약이 8건 밖의 사실을 생성하지 않음
13. secret masking
14. Kakao TEST dry-run
15. Kakao 오류 시 타 API 설정 불변
16. LIVE 차단
17. 기존 최종 후보 hash/input binding
18. 원문 URL 변경 차단
19. 메시지 순서 재현성
20. TEST receipt 민감정보 비노출

기존 140개 테스트를 모두 재실행한다.

---

## 9. 실행 순서

### PRE-FLIGHT
- `git status -sb`
- branch `main`
- HEAD `c94cfcd...` 또는 본 Phase 작업으로 생성된 후속 로컬 커밋
- worktree clean
- Phase 2.3 입력 8건 확인
- secret 추적 없음

### PHASE 3A
- 상세 브리핑 생성
- 모바일판 생성
- 주간 한눈에 보기 생성
- 신규 테스트
- 기존 140개 회귀 테스트
- dry-run
- 품질 게이트

### PHASE 3B
품질 게이트 PASS인 경우에만:
- Kakao `나에게 보내기` TEST 실행
- 응답 검증
- receipt 저장
- LIVE 차단 확인

---

## 10. 필수 산출물

- `PHASE3_EXECUTION_REPORT.md`
- `PHASE3_RESULT_PACKAGE.zip`

권장:
- `outputs/phase3/briefing/detailed_briefing.md`
- `outputs/phase3/briefing/weekly_overview.json`
- `outputs/phase3/kakao/mobile_messages.json`
- `outputs/phase3/kakao/mobile_preview.md`
- `outputs/phase3/kakao/test_receipt.json`
- `outputs/phase3/quality/quality_gate.json`
- `outputs/phase3/logs/tests_existing.txt`
- `outputs/phase3/logs/tests_phase3.txt`
- `outputs/phase3/logs/tests.txt`
- `outputs/phase3/logs/audit.json`
- `outputs/phase3/logs/run.json`

ZIP 제외:
- `.env`
- token
- secret
- config credential
- `.git`
- venv
- runtime state

---

## 11. Phase 3 최종 판정

### PASS
- 상세/모바일 브리핑 품질 게이트 PASS
- 기존 140개 + 신규 Phase 3 테스트 PASS
- Kakao TEST 발송 PASS
- secret 노출 0
- LIVE 0

### IMPLEMENTATION_PASS_DELIVERY_HOLD
콘텐츠·테스트는 PASS이나 Kakao 인증/scope/API 문제로 TEST 발송만 보류.

### HOLD
콘텐츠/입력/테스트 중 중요 미해결 존재.

### FAIL
안전성 또는 무결성 위반.

---

## 12. Phase 3 종료 후

Phase 3 결과는 반드시 독립 검토한다.

독립 검토 PASS 전:
- LIVE 금지
- 운영 스케줄 변경 금지

독립 검토 PASS 후:
- 사용자의 별도 명시 승인 시에만 LIVE/자동 발송 운영 Gate로 이동한다.

---

## 13. Codex 실행 프롬프트

```text
Kakao ai news 프로젝트를 현재 노트북에서 마무리하기 위해 Phase 3 Briefing & Kakao TEST Gate를 구현하고 실행하라.

가장 먼저 저장소 루트의 AGENTS.md와 SESSION_HANDOFF.md를 읽어라.
Canonical Root는 C:\Vibe Coding\kakaotalk_ai_new_daily 이다.

Phase 2.3 독립 검토 PASS 및 Phase 2 전체 콘텐츠 게이트 PASS를 확정 기준으로 유지하라.
Phase 3의 유일한 기사 입력 Source of Truth는 outputs/phase2_3/samples/safe_content.json의 검증 완료 8건이다.

새 뉴스 수집을 위한 Tavily 재검색 금지.
Gemini raw summary 재사용 금지.
HOLD/REJECT 재진입 금지.
기존 Tavily/Gemini/Kakao 운영 설정·인증 구조·모델·스케줄 임의 변경 금지.
LIVE 금지.
승인 없는 git push 금지.

Phase 3A:
1. 8건으로 상세 브리핑 생성
2. AI 교육 우선 모바일 Kakao 판 생성
3. null 교육/수업 필드는 억지 생성하지 않음
4. 이번 주 AI 한눈에 보기 생성
5. 메시지 길이·분할·링크·번호·중복 검증
6. 기존 140개 테스트 + 신규 Phase 3 테스트
7. dry-run 품질 게이트

Phase 3A 품질 게이트가 모두 PASS한 경우에만 Phase 3B:
8. 기존 Kakao 인증 흐름을 사용해 KakaoTalk 나에게 보내기 TEST 실행
9. TEST 메시지임을 명확히 표시
10. 응답의 비민감 정보만 저장
11. 오류 시 Kakao 단계만 HOLD하며 다른 API 설정 변경 금지
12. LIVE는 절대 실행하지 않음

반드시 생성:
PHASE3_EXECUTION_REPORT.md
PHASE3_RESULT_PACKAGE.zip

마지막 출력:
1. PRE-FLIGHT 판정
2. Phase 3A 품질 게이트
3. 기존 테스트 결과
4. 신규 Phase 3 테스트 결과
5. Kakao TEST 발송 결과
6. 최종 판정
7. PHASE3_EXECUTION_REPORT.md 경로
8. PHASE3_RESULT_PACKAGE.zip 경로
9. git status
10. LIVE 실행 여부(반드시 0)
```
