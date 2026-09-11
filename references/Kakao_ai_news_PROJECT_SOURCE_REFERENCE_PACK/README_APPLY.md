# Kakao ai news --- 프로젝트 소스 적용 안내

## 권장 적용

기존 프로젝트의 정상 작동 소스는 그대로 유지하고, 이 패키지의
`references/` 폴더만 프로젝트 소스에 추가한다.

## 권장 구조

Kakao-ai-news/ - SKILL.md -
Kakao_ai_news_PROJECT_INSTRUCTIONS_FINAL.md - references/ -
00_REFERENCE_INDEX.md - 01_TAVILY_SEARCH_API_REFERENCE.md -
02_TAVILY_MCP_REFERENCE.md - 03_GEMINI_API_AUTH_MODELS.md -
04_GEMINI_RATE_LIMITS.md - 05_GEMINI_ERROR_HANDLING.md -
06_KAKAO_TALK_MESSAGE_API.md - 07_KAKAO_LOGIN_SCOPE_TOKEN.md

## 적용 원칙

1.  `references/`를 통째로 복사한다.
2.  기존 SKILL.md, config.json, 실행 코드, 인증 설정은 덮어쓰지 않는다.
3.  PROJECT_INSTRUCTIONS는 프로젝트 최상위 지침으로 사용한다.
4.  references는 API 세부사항 확인용이며 공식 URL을 Source of Truth로
    한다.
5.  config/ 및 인증정보는 ZIP에 포함하지 않았다.
6.  공식 API 변경 시 참조 MD의 `최종 확인일`과 관련 내용만 갱신한다.

## 보안

API Key, Access Token, Client Secret, Refresh Token은 이 참조 패키지에
포함하지 않는다.
