# Kakao ai news — Phase 6.2 Stable Link Gateway Gate v1.0

- Canonical Root: `C:\Vibe Coding\kakaotalk_ai_new_daily`
- 목적: Kakao 외부 링크 도메인 변동 문제를 고정 Gateway 도메인 1개로 해결
- 기술 후보: Vercel Functions + allowlisted event_id redirect
- 기존 Phase 3/4/6/6.1 journal/receipt: 보존
- 실제 full compact 재발송: smoke link 확인 전 금지
- Scheduled LIVE: 금지

## 1. 아키텍처

Kakao:
`https://<gateway-domain>/r/<safe_event_id>`

Gateway:
`safe_event_id -> allowlisted safe_original_url -> HTTP 302`

금지:
`/go?url=<arbitrary-url>`

임의 URL 입력을 받지 않는다.

## 2. 초기 allowlist

Phase 2.3 검증 완료 8건의 event_id와 safe_original_url만 등록.

Source of Truth:
`outputs/phase2_3/samples/safe_content.json`

Gateway의 `data/targets.json`은 이 8건과 정확히 일치해야 한다.

## 3. Gateway 보안 Gate

필수:
- event_id 형식 검증
- unknown event -> 404
- invalid event -> 400
- HTTPS target만 허용
- open redirect 테스트 FAIL이어야 함
- query `url=` 무시/미지원
- token/secret 0
- Cache-Control no-store
- Referrer-Policy no-referrer
- X-Content-Type-Options nosniff

## 4. Vercel 배포

`link-gateway/`를 독립 Vercel Project Root로 배포.

현재 사용자 Vercel 계정에는 Kakao ai news Gateway 프로젝트가 없으므로 신규 project가 필요하다.

배포 후 production URL 예:
`https://kakao-ai-news-link-gateway-....vercel.app`

중요:
Preview URL이 아니라 고정 production project domain을 Kakao에 등록한다.

## 5. 배포 후 Browser Preflight

8개 gateway URL을 실제 브라우저/HTTP에서 검사:

`/r/<event_id>`

각각:
- initial gateway response: 302
- Location == safe_original_url
- final destination host == expected original host

또한:
- `/r/not-valid` -> 400
- `/r/evt_ffffffffffffffffffff` -> 404
- `/health` -> 200

## 6. Kakao Product Link

Kakao Developers:
`앱 → 제품 링크 관리 → 웹 도메인`

등록:
`https://<production-gateway-domain>`

앞으로 기사 원문 도메인은 Kakao에 직접 등록하지 않는다.

기존 도메인을 즉시 삭제할 필요는 없으나 신규 compact 템플릿은 gateway 도메인만 사용한다.

## 7. Compact Template 변경

기사 버튼:
- title: `원문 보기`
- web_url: `https://<gateway-domain>/r/<safe_event_id>`
- mobile_web_url: 동일

헤더/overview:
- gateway root 또는 `/` 사용
- Kakao Developers 링크 사용 금지

## 8. Phase 6.2A Kakao Smoke

Gateway browser preflight PASS + Gateway domain Kakao 등록 확인 후:

기사 1번만:
`[GATEWAY LINK TEST]`

버튼:
`https://<gateway-domain>/r/evt_0da37ec7577bcd6b517d`

실제 휴대전화 클릭으로 NYC교육청 도착 확인.

API result_code 0만으로 PASS 아님.
사용자 클릭 확인 필요.

## 9. Full Send 조건

사용자가 smoke link PASS를 명시한 뒤 별도 승인으로 corrected compact 10개를 1회 발송.

기존 Phase 6/6.1 journal 삭제 금지.
Phase 6.2 전용 journal 사용.

## 10. 테스트

기존 282 tests 재실행.

신규 테스트 최소:
1. targets 8건 == safe input
2. event format validation
3. unknown 404
4. invalid 400
5. https-only
6. arbitrary url param unsupported
7. open redirect blocked
8. 302 Location exact
9. root/health available
10. secrets 0
11. gateway URL generation 8개
12. gateway host one domain
13. article button 8
14. developers.kakao.com article links 0
15. original domains direct button 0
16. header/overview gateway link
17. existing journals unchanged
18. scheduled LIVE 0
19. smoke exactly 1 call
20. full send locked before user confirmation

## 11. 필수 산출물

- `PHASE6_2_GATEWAY_EXECUTION_REPORT.md`
- `PHASE6_2_GATEWAY_RESULT_PACKAGE.zip`

권장:
- `outputs/phase6_2/gateway/deployment.json`
- `outputs/phase6_2/gateway/redirect_checks.json`
- `outputs/phase6_2/kakao/gateway_templates.json`
- `outputs/phase6_2/smoke/smoke_receipt.json`
- `outputs/phase6_2/quality/quality_gate.json`
- logs/tests...

## 12. 종료 상태

- `GATEWAY_IMPLEMENTATION_PASS`
- `GATEWAY_DEPLOYMENT_PASS`
- `GATEWAY_BROWSER_REDIRECT_PASS`
- `GATEWAY_KAKAO_SMOKE_API_PASS_USER_CONFIRMATION_REQUIRED`
- `GATEWAY_LINK_PASS`
- `HOLD`

자동 LIVE는 항상 0.
