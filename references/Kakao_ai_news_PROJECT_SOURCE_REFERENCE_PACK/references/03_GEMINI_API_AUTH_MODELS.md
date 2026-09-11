# Gemini API Authentication & Models --- Kakao ai news

최종 확인일: 2026-09-09 API Key 공식 문서:
https://ai.google.dev/gemini-api/docs/api-key Models 공식 문서:
https://ai.google.dev/gemini-api/docs/models

## 프로젝트 역할

뉴스 분류, 중복 제거 보조, 중요도 평가, 요약, 교육적 시사점, 최종 브리핑
생성.

## 인증 원칙

-   새 키 구조와 Google AI Studio 정책은 공식 API Key 문서를 기준으로
    확인한다.
-   인증키를 코드·문서·Git에 직접 기록하지 않는다.
-   Free Tier와 Paid Tier를 별도 환경으로 취급한다.

## 모델 원칙

-   특정 모델명을 프로젝트 지침에 영구 고정하지 않는다.
-   실제 운영 모델은 환경설정으로 분리한다.
-   모델 교체 전 가용성, 비용/쿼터, 출력 품질, 회귀 테스트를 확인한다.
-   Preview/Deprecated 모델 사용 시 종료 일정과 대체 모델을 확인한다.
