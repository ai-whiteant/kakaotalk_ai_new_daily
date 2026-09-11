# Phase 2.2 Evidence Verification

기존 Phase 2.1 결과를 보존하는 오프라인 TEST 검증 계층이다. `review_packet.json`은 실제 웹 원문을 읽어 작성한 사건별 검토 데이터이며, 코드가 의미적 진실을 자동 판정한 결과가 아니다. 독립 검토는 아직 PENDING이다.

저장소에서 실행:

```powershell
python -X utf8 -m unittest news.test_daily news.test_phase1 news.test_phase2 news.test_phase21 news.test_phase22 -v
python -X utf8 -m news.phase22 --packet outputs/phase2_2/evidence/review_packet.json
```

Phase 1/2.1 원본과 기존 Python 의존성이 필요하다. ZIP은 변경분과 검증 자료만 포함한다. 저장된 입력 SHA가 다르면 실행을 중단한다. TEST 재실행은 웹/Tavily/Gemini/Kakao를 호출하지 않는다.

원문 재검토 시 출처 URL, 접근 결과, 짧은 근거 요약, 본문 위치, 검토 시각, claim별 이유를 갱신한다. 출처 요약 SHA는 저장 자료 무결성만 보장하며 원문 전체의 보존이나 독립적인 사실 검증을 의미하지 않는다. 검색 snippet·접근 실패는 최종 지지 근거가 될 수 없다. 동일 숫자라도 맥락 동등성을 명시해야 한다.

`safe_content`만 검증된 문장을 담는다. 원본 Guard와 원 분석, 제거된 주장, 검토용 부분 문장은 감사 목적으로만 보존된다. HOLD/REJECT의 safe_content는 비어 있다. 모든 사건의 dispatch_allowed는 false이며, VERIFIED 결과도 발송 선정·최종 교육적 활용 검토 완료를 의미하지 않는다. Guard·배점·70점 기준은 변경하지 않는다.
