# Gemini API Error Handling --- Kakao ai news

최종 확인일: 2026-09-09 공식 문서:
https://ai.google.dev/gemini-api/docs/api-errors

## 진단 원칙

오류 코드를 먼저 분류하고 Tavily/Kakao 설정을 임의 변경하지 않는다.

## 핵심 분류

-   400: 요청 형식/인자 검토
-   401: 인증/API Key 검토
-   403: 권한·프로젝트 접근 상태 검토
-   404: 모델/리소스/엔드포인트 검토
-   429: Rate Limit/Quota 검토
-   5xx: 서비스 측 일시 장애 가능성 검토

## 기록

-   발생 시각
-   HTTP 상태
-   오류 메시지
-   사용 모델
-   요청 단계
-   request ID가 제공되면 해당 ID
-   인증정보는 반드시 마스킹
