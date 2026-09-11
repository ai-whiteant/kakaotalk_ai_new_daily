# Tavily Search API Reference --- Kakao ai news

최종 확인일: 2026-09-09 공식 문서:
https://docs.tavily.com/documentation/api-reference/endpoint/search

## 프로젝트 역할

최근 국내외 AI 뉴스 후보 탐색과 원문 URL 확보.

## 기본 권장값

-   topic: `news`
-   time_range: `week`
-   max_results: 쿼리별 필요 범위에서 조정
-   search_depth: 기본 `basic`; 정밀 검증이 필요한 경우만 `advanced`
-   include_domains / exclude_domains: 신뢰 출처 우선 및 저품질 출처
    배제에 선택적으로 사용
-   start_date / end_date: 특정 기간 요청 시 사용

## 주의

-   Tavily 검색 순위 자체를 최종 뉴스 중요도로 간주하지 않는다.
-   분야별 복수 쿼리를 실행한 뒤 중복 사건을 통합한다.
-   검색 비용과 품질을 함께 관리한다.
-   URL, 발행일, 원문 내용은 후속 검증 대상으로 취급한다.
