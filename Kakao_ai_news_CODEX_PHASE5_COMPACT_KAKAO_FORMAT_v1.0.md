# Kakao ai news — Phase 5 Compact Kakao Format UX Gate v1.0

- Canonical Root: `C:\Vibe Coding\kakaotalk_ai_new_daily`
- 선행 조건: Phase 4 Production Once 독립 검토 PASS
- 목적: 검증·분석 엔진은 변경하지 않고 Kakao 최종 표현 계층만 `날짜 → 번호 → 제목 → 한 문단 요약 → 출처 → 원문 보기` 형식으로 개선
- 실제 재발송: 본 Phase에서는 금지
- 자동 LIVE/스케줄: 금지

## 1. 변경 범위

변경 가능:
- Kakao compact formatter
- source label mapping
- per-article link/button 구성
- compact preview / dry-run / tests

변경 금지:
- Tavily 검색
- Gemini 분석/요약
- Phase 2.3 safe_content
- 점수/선별/검증 결과
- Kakao 인증 구조
- token/state/journal
- Phase 3/4 receipt
- 자동 LIVE/스케줄

## 2. 입력 Source of Truth

기사 입력:
`outputs/phase2_3/samples/safe_content.json`

현재 검증 완료 8건을 그대로 사용한다.

compact formatter는 safe_*를 수정하지 않고 별도 파생 데이터를 생성한다.

권장 파생 구조:

```json
{
  "safe_event_id": "evt_x",
  "number": 1,
  "compact_title": "string",
  "compact_summary": "string",
  "source_label": "string",
  "source_url": "https://...",
  "button_title": "원문 보기"
}
```

## 3. 최종 모바일 형식

### 헤더
```text
26.9.12.

📢 AI 핵심 뉴스 8선
2026.9.2~9.9 검증 브리핑
```

### 기사
```text
1. 뉴스 제목 → 핵심 사실과 의미를 2~4문장으로 압축한다.(출처)▼
```

각 기사 메시지의 Kakao 링크:
- `web_url` = 해당 `safe_original_url`
- `mobile_web_url` = 해당 `safe_original_url`
- `button_title` = `원문 보기`

`▼` 의미:
아래 원문 보기 버튼이 있음을 나타낸다.

### 마지막 종합
```text
📌 이번 주 AI 한눈에 보기
• 교육: ...
• 정책: ...
• 기술: ...
• 산업: ...
• 관찰: ...
```

## 4. 메시지 수 목표

현재 8건:
- 헤더 1
- 기사 8
- 주간 종합 1
= 총 10개 메시지 목표

기존 28개 메시지 방식은 보존한다.
새 compact 방식은 별도 formatter로 추가한다.

## 5. 길이 규칙

- Kakao Text Template 최대치 안에서 동작
- 목표: 기사 메시지 160~180 UTF-16 단위 이하
- 절대 상한: 196 UTF-16 단위
- 문자 중간 절단 금지
- 196 초과 시 문장 단위 압축 또는 2-part fallback
- 원문 URL은 본문에 노출하지 않고 Kakao link 버튼으로 전달

## 6. Compact 작성 규칙

### 일반 기사
`safe_summary + safe_why_it_matters`를 사실 범위 안에서 압축.

### AI 교육 기사
`safe_summary + safe_why_it_matters + safe_education_implication` 중 핵심만 사용.
수업 활용은 본문 196자에 억지로 넣지 않는다.

### 금지
- safe_*에 없는 새 사실
- 수치 추가
- 법안→시행 정책 변경
- 계획→성과 변경
- 연구 벤치마크→일반 성능 보장 변경
- source URL에서 출처 이름을 임의 추측
- 원본 safe_* 덮어쓰기

## 7. 출처 라벨

현재 8건의 검증 출처 라벨:

| event / 기사 | source_label |
|---|---|
| NYC 학교 AI 정책 | NYC교육청 |
| AI LABS Act | 미 하원의원실 |
| Brookings 학교 AI | Brookings |
| 중국 AI 분쟁 지침 | 中최고인민법원 |
| 네이버 보안 AI | 네이버 |
| NVIDIA PAIR | NVIDIA |
| NeoMME | H Company |
| 삼성·Mistral | 삼성전자 |

미래 기사에서는 Final Verification 단계의 공식 대표 출처를 `source_label`로 전달하도록 확장할 수 있다.
URL domain만 보고 라벨을 생성하지 않는다.

## 8. 현재 8건 목표 compact 문안

1. 뉴욕 공립학교, 8학년까지 생성형 AI 사용 유예
→ 뉴욕시는 2026~27학년도 2K~8학년 학생의 대면 생성형 AI 사용을 제한한다. 보조공학과 교사의 수업 준비·행정 활용은 구분한다. 학생과 교사의 AI 사용 범위를 나눈 학교 정책 사례다.(NYC교육청)▼

2. 美 의원, 학교 AI 실습실·교사 연수 지원 법안
→ AI LABS Act는 K-12 학교의 AI 실습 환경과 교사 연수를 함께 지원하자는 법안이다. 시행된 정책이 아니라 입법 제안 단계라는 점이 중요하다.(미 하원의원실)▼

3. 학교 AI 도입, 속도보다 학습과정 함께 봐야
→ Brookings는 학교 AI 도입 때 학생의 사고·대화와 교사 참여를 함께 점검하자고 제안했다. AI 보급량보다 학습과정과 현장 관찰을 함께 보자는 접근이다.(Brookings)▼

4. 중국 최고법원, 딥페이크 등 AI 분쟁 지침 공개
→ 중국 최고인민법원은 얼굴·음성의 무단 이용과 생성형 AI 제공자 책임 등을 다룬 AI 분쟁 심리 지침을 공개했다. 새 법 제정보다 기존 법 적용 기준을 구체화한 자료다.(中최고인민법원)▼

5. 네이버클라우드, 보안 특화 AI 모델 사업 선정
→ 네이버클라우드 컨소시엄이 사이버보안 특화 AI 파운데이션 모델 개발 사업자로 선정됐다. 국내 보안 환경용 모델 개발과 현장 검증 계획이며 실제 보안 개선 성과가 확인된 단계는 아니다.(네이버)▼

6. NVIDIA, 로컬 AI 연결 도구 PAIR 소개
→ NVIDIA는 로컬 네트워크의 여러 PC에 AI 추론 요청을 분배하는 PAIR를 소개했다. 로컬 AI를 여러 장치에서 실행하는 방식이지만 모든 환경의 속도·보안 개선이 입증된 것은 아니다.(NVIDIA)▼

7. H Company, 문서 검색용 NeoMME 공개
→ H Company는 이미지와 텍스트를 처리하는 NeoMME 인코더를 공개했다. 260M·800M 체크포인트를 Apache 2.0으로 제공하며 시각 문서 검색 평가 결과를 제시했다.(H Company)▼

8. 삼성·미스트랄, 반도체 설계·제조 AI 협력
→ 삼성전자와 Mistral AI는 반도체 설계·제조용 AI 협력을 발표했다. 맞춤형 AI를 결함 탐지·장비 최적화 등에 적용할 계획이며 실제 수율·비용 개선이 확인된 단계는 아니다.(삼성전자)▼

## 9. 주간 종합 목표 문안

```text
📌 이번 주 AI 한눈에 보기
• 교육: 학생·교사 AI 사용 기준과 교사 연수 논의
• 정책: 얼굴·음성 동의와 AI 제공자 책임 구체화
• 기술: 로컬 AI·멀티모달 문서 검색 확대
• 산업: 보안·반도체 현장 AI 적용 추진
• 관찰: 발표·계획과 실제 성과를 구분해 볼 필요
```

## 10. 구현 권장

기존 Phase 3/4 코드를 최소 변경한다.

권장 신규 파일:
- `news/phase5_compact.py`
- `news/test_phase5_compact.py`

또는 기존 formatter에 별도 함수 추가 가능하나,
기존 28-message formatter를 깨뜨리지 않는 구조를 우선한다.

권장 출력:
- `outputs/phase5/compact/compact_items.json`
- `outputs/phase5/compact/mobile_messages.json`
- `outputs/phase5/compact/mobile_preview.md`
- `outputs/phase5/quality/quality_gate.json`
- `outputs/phase5/logs/tests_existing.txt`
- `outputs/phase5/logs/tests_phase5.txt`
- `outputs/phase5/logs/tests.txt`

## 11. Phase 5 테스트

필수:
1. 기사 8건
2. event_id 8개 일치
3. safe_original_url 8개 보존
4. source_label 8개 존재
5. 기사당 원문 버튼 1개
6. button link == safe_original_url
7. TEST marker 0
8. 헤더 1개
9. 기사 메시지 8개
10. 주간 요약 1개
11. 총 메시지 10개
12. 기사 번호 1~8
13. 각 기사 <= 196 UTF-16
14. overview <= 196 UTF-16
15. 중간 문자 절단 0
16. safe_* 원본 불변
17. HOLD/REJECT 0
18. 새 Tavily 호출 0
19. Gemini 호출 0
20. Kakao actual send 0
21. Phase 3/4 receipt/journal 변경 0
22. secret 0
23. scheduled LIVE 0
24. 기존 192 tests PASS
25. compact 신규 tests PASS

## 12. Gate

### PASS
- 기존 192 tests PASS
- Phase 5 신규 tests PASS
- compact 10 messages
- 모든 길이/링크/출처 PASS
- actual Kakao send 0

### HOLD
- 196 초과
- safe 원본과 의미 불일치
- URL/source mapping 오류
- 기존 회귀 실패

## 13. 본 Phase에서 하지 않을 것

- 실제 Kakao 재발송
- production-once journal 삭제
- Phase 3 TEST journal 삭제
- LIVE/스케줄 활성화
- Git push

## 14. 완료 산출물

- `PHASE5_COMPACT_FORMAT_EXECUTION_REPORT.md`
- `PHASE5_COMPACT_FORMAT_RESULT_PACKAGE.zip`

독립 검토 PASS 후,
사용자 승인 시 compact 형식으로 1회 Kakao 실제 발송 Gate를 별도 실행한다.
