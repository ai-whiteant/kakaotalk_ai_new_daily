# Phase 6.1 Manual Check

Before Codex smoke test:
- [ ] Kakao Developers에서 8개 원문 도메인이 실제 등록/저장되어 있음
- [ ] 기존 등록 도메인은 삭제하지 않음
- [ ] project root = C:\Vibe Coding\kakaotalk_ai_new_daily

After 1-message smoke test:
- [ ] KakaoTalk `나에게 보내기`에 `[LINK TEST]` 메시지 1개 도착
- [ ] `원문 보기` 버튼 표시
- [ ] 버튼 클릭 시 Kakao Developers가 아니라 NYC교육청 원문으로 이동
- [ ] URL의 호스트가 www.schools.nyc.gov
- [ ] 정상이라면 사용자에게 `원문 링크 정상`이라고 확인

그 확인 전에는 전체 10개 corrected compact 메시지를 보내지 않는다.
