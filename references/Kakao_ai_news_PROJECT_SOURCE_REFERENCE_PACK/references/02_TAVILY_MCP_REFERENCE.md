# Tavily MCP Reference --- Kakao ai news

최종 확인일: 2026-09-09 공식 문서:
https://docs.tavily.com/documentation/mcp 문서 인덱스:
https://docs.tavily.com/llms.txt

## 프로젝트 역할

Codex/에이전트 환경에서 Tavily 검색·추출 기능을 연결하는 계층.

## 운영 원칙

-   Remote MCP 연결 상태와 도구 목록을 먼저 확인한다.
-   Tavily 장애와 Gemini/Kakao 장애를 분리한다.
-   인증정보는 MCP 설정 또는 보안 설정에서만 관리한다.
-   MCP 연결 변경 전 현재 정상 기준본을 보존한다.

## 변경 시 확인

-   Remote MCP 연결 방식
-   제공 도구 이름과 인자
-   인증 방식
-   검색/추출 도구 변경 여부
