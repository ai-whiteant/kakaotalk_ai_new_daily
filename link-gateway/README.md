# Kakao AI News Link Gateway

## 목적
Kakao Message의 버튼은 매주 바뀌는 외부 원문 도메인을 직접 사용하지 않고,
하나의 고정 Gateway 도메인을 사용한다.

예:
`https://<gateway-domain>/r/evt_0da37ec7577bcd6b517d`

Gateway는 내부 allowlist의 검증된 `safe_original_url`로만 302 redirect한다.

## 보안
- `?url=` 같은 임의 URL 파라미터를 받지 않는다.
- event_id는 `evt_` + 20 hex로 제한한다.
- allowlist에 없는 event_id는 404.
- target은 HTTPS만 허용.
- token, API key, Kakao credential 없음.
- 로그에 query secret 없음.

## 로컬
Node 의존성 설치가 필요하지 않는다.

## Vercel 배포
`link-gateway` 디렉터리를 Vercel Project Root로 배포한다.

Vercel CLI 사용 시 예:
```powershell
cd "C:\Vibe Coding\kakaotalk_ai_new_daily\link-gateway"
npx vercel
npx vercel --prod
```

배포 후:
1. `/health` 확인
2. `/r/<event_id>`가 원문으로 302 이동하는지 8건 확인
3. 생성된 production domain 하나만 Kakao Developers 제품 링크의 웹 도메인에 등록
4. 기존 8개 외부 원문 도메인 직접 사용 방식은 신규 메시지에서 중단

## Phase 6.2 검증 결과

기존 282 + Node Gateway 20 + Python Gate 20 = 322 PASS. 로컬 Node 24.18.0, 배포 설정 22.x 보존. 배포 runtime 미검증.
`node --test tests/gateway.test.js`를 link-gateway에서 실행한다. 동일성 테스트에는 상위 outputs/phase2_3/samples/safe_content.json이 필요하다.
중복 event 파라미터 차단, arbitrary url 무시, HTTPS target 및 보안 헤더 적용. Runtime npm dependency 0.

현재 DEPLOYMENT_HOLD: CLI 로그아웃. 기존 계정 로그인 후 이 디렉터리를 신규 프로젝트로 명시적으로 link하고 production 배포한다. 임시 deployment URL을 등록하지 않는다.
저장소 루트에서 `python -m news.phase6_2 --domain https://실제-production-domain --check-redirects`로 배포 후 HTTP를 확인한다. 이 명령은 Kakao를 호출하지 않는다.
배포 확인자는 gateway/deployment.json에 실제 배포 확인 결과 GATEWAY_DEPLOYMENT_PASS 및 production_origin을 기록해야 한다. 미배포 상태를 PASS로 바꾸지 않는다.
그 origin 하나만 Kakao Developers → 앱 → 제품 링크 관리 → 웹 도메인에 등록·저장하고 사용자 확인을 받는다.
모든 게이트와 등록 확인 후에만 `--send-smoke --domain-registered`를 추가한다. smoke는 [GATEWAY LINK TEST] NYC 1건이며 exclusive journal이 재발송을 차단한다. API 성공 후 사용자 휴대전화 NYC 도착 확인이 필요하다. 전체 발송은 잠겨 있다.
미리보기 gateway.example.org는 등록/발송용이 아니다. 이전 journal/receipt와 인증 설정을 변경하지 않는다.

## Redirect gate 최신 정책
사용자 승인으로 initial 302 + exact safe_original_url Location 및 control만 필수로 한다. 외부 final fetch는 advisory이며 접근 실패로 Gateway FAIL 처리하지 않는다. gateway_passed/final_verified/final_error를 별도 저장한다. 최신 검증 330 PASS, production Gateway PASS. 이전 DEPLOYMENT_HOLD 문단은 역사 기록이다.
