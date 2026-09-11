# Gemini API Rate Limits --- Kakao ai news

최종 확인일: 2026-09-09 공식 문서:
https://ai.google.dev/gemini-api/docs/rate-limits

## 목적

Free/Paid Tier의 호출 제한 및 대량 뉴스 처리 시 안정성 관리.

## 확인 항목

-   RPM: requests per minute
-   TPM: tokens per minute
-   RPD: requests per day
-   프로젝트 및 모델별 적용 제한
-   현재 AI Studio에 표시되는 실제 활성 한도

## 운영 원칙

-   문서에 숫자를 고정 저장하지 않고 공식 페이지/AI Studio의 현재 값을
    확인한다.
-   429 발생 시 무조건 키를 재생성하지 않는다.
-   배치 크기, 재시도, 지수 백오프, 기사 수를 조정한다.
