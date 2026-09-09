# 카카오 나에게 보내기

인증된 카카오 커넥터가 있으면 그 도구의 실제 스키마와 제한을 따른다. 아래는 REST API를 직접 사용할 때의 절차다.

- 카카오 로그인 및 `talk_message` 동의가 있는 사용자 액세스 토큰이 필요하다. 앱 키만으로 발송할 수 없다. 토큰은 보안 저장소나 실행 환경에서 읽고 채팅으로 요구하거나 출력하지 않는다. 연결이 없으면 사용자에게 인증 연결을 요청하고 원고를 보존한다.
- 공식 API: `POST https://kapi.kakao.com/v2/api/talk/memo/default/send`
- 헤더: `Authorization: Bearer {사용자 액세스 토큰}`, `Content-Type: application/x-www-form-urlencoded`
- 폼 필드 `template_object`에 JSON 문자열을 넣는다. 텍스트 템플릿은 `object_type: text`, `text`, `link`를 포함한다. HTTP 클라이언트의 폼 인코딩을 사용한다.
- 공식 문서 기준 텍스트는 최대 200자다. 실행 시 문서를 확인하고 줄바꿈·공백·URL·순번을 포함한 실제 본문 길이를 계산한다. 기사마다 필요하면 여러 조각으로 나눈다. 예: `[해외 2 · 1/3] 제목·출처`, `[해외 2 · 2/3] 핵심내용·시사점`, `[해외 2 · 3/3] 링크`. 모든 필드는 해당 기사 조각 전체에 보존한다. URL은 중간에서 끊지 않는다.
- 템플릿의 버튼 링크는 앱 제품 링크 관리에 허용된 도메인 조건을 따른다. 기사 URL을 임의로 버튼에 넣지 않는다. 허용된 기사 도메인 또는 이미 설정된 실제 뉴스 모음 페이지를 사용하고 원문 URL은 본문에도 보존한다. 적합한 링크가 없다면 전송을 중단하고 링크 설정 필요를 알린다. 이 문제를 해결하려고 원고를 임의로 공개 게시하지 않는다.
- 모든 조각의 길이와 링크 적합성을 발송 전에 검사한다. 단일 URL 자체가 제한을 초과해 무손실 전송이 불가능하면 임의 단축 URL을 생성하지 말고 제약과 미전송 원고를 제공한다.
- HTTP 성공 및 응답의 `result_code: 0`을 확인해야 성공으로 기록한다. 토큰 만료·권한·도메인 오류는 구분해 안내한다. 인증 토큰이 포함될 수 있는 원시 요청·오류를 출력하지 않는다.

공식 근거 (작성 확인일: 2026-09-09):
- [카카오톡 메시지 REST API](https://developers.kakao.com/docs/ko/kakaotalk-message/rest-api)
- [기본 텍스트 템플릿](https://developers.kakao.com/docs/ko/message-template/default)
- [Tavily 검색 필터](https://docs.tavily.com/documentation/api-reference/endpoint/search)
