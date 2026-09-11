# Kakao AI News 최종 운영 기준본

Canonical Root: `C:\Vibe Coding\kakaotalk_ai_new_daily`
GitHub: https://github.com/ai-whiteant/kakaotalk_ai_new_daily

## 목적 및 아키텍처
검증된 AI 뉴스를 교육적 시사점과 함께 개인 KakaoTalk으로 전달한다.
Tavily → Gemini → Verification → Compact Formatter → Stable Link Gateway → Kakao Message API.
Gateway: https://kakao-ai-news-link-gateway.vercel.app
Vercel project: kakao-ai-news-link-gateway.

## 확정 상태
Phase1 PASS; Phase2/2.1/2.2 구현·검증 이력 보존; Phase2.3 및 Phase2 전체 콘텐츠 gate PASS.
Phase3 TEST 28/28 PASS; Phase4 production-once 28/28 PASS; Phase5 Compact UX PASS.
Phase6 API 성공 및 링크 HOLD 이력, Phase6.1 조사 및 실패 증거 보존.
Phase6.2 GATEWAY_LINK_PASS: smoke 1회, 사용자 실제 NYC 및 Gottheimer 원문 이동 PASS.
Phase6.3 GATEWAY_COMPACT_PRODUCTION_ONCE_PASS: planned/sent 10/10; result_code 10건 모두 0.
기사 버튼/Gateway 링크 8, direct-original/developers/TEST marker 0.
court.gov.cn final URLError는 advisory only, Gateway initial 302와 exact Location 8/8 PASS.
최종 offline 테스트 360/360 PASS (Python 312 + Gateway Node 20 + Phase6.3 28).

## 실행 및 보안
Scheduled LIVE = OFF. 이번 Closeout 추가 발송/검색/요약/재배포 0.
기존 exclusive journal/receipt를 삭제·재사용하지 않는다. Phase6.3 재실행 금지.
API key/token/Authorization/credential/암호화 auth state/.vercel/.env/venv/ZIP을 Git에 올리지 않는다.
Git에는 검증된 source, safe inputs/previews/receipts/audit와 선별된 테스트 증거만 포함한다.
과거 receipt 상태와 현재 gate를 구분한다. 과거 HOLD는 삭제하지 않는다.

## Home / Office 재현
두 PC 모두 Canonical Root 사용. Git clone/pull은 clean worktree에서 수행하고 AGENTS.md와 SESSION_HANDOFF.md를 읽는다.
이 Git 커밋은 소스·공개 가능 증거 기준본이며 credential 및 runtime journal은 Git으로 동기화하지 않는다.
**새 clone만으로 과거 360개 테스트 전체가 실행되는 것은 아니다.** 역사적 integrity 테스트는 Phase5 원본 ZIP의 고정 SHA와 과거 로컬 baseline 파일을 검증한다. ZIP·로컬 상태를 Git에서 제외했으므로 기존 승인된 원본 패키지/증거를 별도 안전 경로에서 복원해야 한다. 누락을 해소하려고 baseline이나 journal을 삭제·조작하지 않는다.
Gateway 단위 테스트는 Node와 tracked safe_content 입력으로 실행할 수 있다: link-gateway에서 `node --test tests/gateway.test.js`.
전체 Python 회귀는 기존 승인 환경에서 `python -m unittest news.test_daily news.test_phase1 news.test_phase2 news.test_phase21 news.test_phase22 news.test_phase23 news.test_phase3 news.test_phase4 news.test_phase5_compact news.test_phase6 news.test_phase6_1 news.test_phase6_2 news.test_phase6_3`.
새 PC에서는 실제 send 진입점을 실행하지 않는다. 기존 journal을 안전하게 보존/이관하고 별도 승인된 새 작업만 수행한다. 토큰은 문서·Git·메시지로 전달하지 않는다.

## 다음 운영 과제
이번 단계는 검증된 1회 발송 기준본 마감이다. 자동 반복 발송은 포함하지 않는다.
향후 별도 Phase에서 수집 스케줄 → 검증 → Gateway mapping update → scheduled send를 설계·검토·승인한다.
휴대성 개선(과거 로컬 artifact 의존을 분리한 회귀 suite)은 기능 개발로 별도 수행한다.

## Git Closeout
기존 e9214a6 보존. 새 커밋 메시지: feat: complete Kakao AI news gateway compact production workflow.
최종 커밋 SHA, push 및 Local/Remote 일치 증거는 로컬 FINAL_GIT_CLOSEOUT_REPORT.md에 기록한다. 자기 자신의 커밋 SHA를 포함하는 후속 커밋 반복을 피하기 위해 이 최종 Git 영수증은 로컬 전용이다.
성공 조건: tests/secret scan PASS, 공개 secret/state/ZIP 0, normal push PASS, Local HEAD == origin/main.
최종 성공 상태명: KAKAO_AI_NEWS_PRODUCTION_ONCE_VALIDATED_AND_GIT_CLOSED.

## Closeout 실제 확인 사항
- GitHub ENABLE_DAILY_NEWS 조회 시 true였으므로 사용자 요구 Scheduled LIVE OFF에 맞춰 false로 교정하고 재조회 확인했다. 워크플로/스케줄 신규 생성 및 dispatch 없음.
- .gitattributes로 SHA-pinned source/evidence 원본 바이트를 보존한다. 기존 LF-normalized Git blob과 Windows CRLF 파일 차이는 줄바꿈 보존 변경이며 코드 로직 변경이 아니다.
