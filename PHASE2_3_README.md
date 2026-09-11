# Phase 2.3 Final Candidate Verification Gate

이전 저장소의 Phase 1 커밋과 Phase 2/2.1/2.2 미커밋 파일을 현재 `project` 저장소로 복원했다. 실제 비밀 설정은 복사하지 않았다. 상위 작업 폴더의 빈 Git 저장소와 이 저장소를 구분한다.

실행 위치는 이 파일이 있는 저장소 루트다. 기존 Python 의존성에 추가 설치는 없다.

```powershell
python -X utf8 -m unittest news.test_daily news.test_phase1 news.test_phase2 news.test_phase21 news.test_phase22 news.test_phase23 -v
python -X utf8 -m news.phase23 --packet outputs/phase2_3/verification/review_packet.json
```

TEST는 저장된 검토 자료를 재평가하며 인터넷/API/카카오를 호출하지 않는다. 실제 원문 검토는 이번 세션에서 별도로 수행하고 짧은 근거와 위치를 source_registry에 저장했다. 원문 판단은 독립 검토 대상이며 프로그램 테스트가 이를 대체하지 않는다.

최종 사용 후보는 `selection/final_candidates.json`이다. 이 파일은 safe_* 키만 포함한다. `verification/final_verification_records.json`은 감사 기록으로 원 분석·제거한 주장도 포함하므로 발송 입력으로 사용하지 않는다. 원래 점수는 유지하며 70점 미만 별도 중요 후보는 이유를 기록한다.

검증용 URL 추가는 새 후보 수집이 아니다. 발행일·사건일·후속 해설일을 구분하고 고정 기간을 유지한다. 8건 확보는 Phase 2 PASS 검토 조건이며 독립 검토가 완료되기 전 Phase 3 및 Kakao 실행은 보류한다.

결과 ZIP은 변경분 패키지다. 전체 프로젝트 복구용 ZIP이 아니므로 기존 Phase 1/2.1/2.2 입력과 소스가 필요하다.
