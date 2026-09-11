# Kakao Login / Scope / Token --- Kakao ai news

최종 확인일: 2026-09-09 동의항목 공식 문서:
https://developers.kakao.com/docs/en/kakaologin/utilize 사전 설정:
https://developers.kakao.com/docs/en/kakaologin/prerequisite 개념/토큰:
https://developers.kakao.com/docs/en/kakaologin/common

## 핵심

KakaoTalk 메시지 전송에는 `talk_message` 동의 상태가 중요하다.

## 운영 원칙

-   `talk_message` 동의 여부를 토큰 발급/갱신 흐름과 함께 확인한다.
-   scope 부족 오류가 발생하면 필요한 동의를 확인한 뒤 추가 동의 절차를
    사용한다.
-   Access Token과 Refresh Token을 문서·Git에 기록하지 않는다.
-   토큰 문제와 Gemini API 문제를 서로 연결해 추정하지 않는다.

## 장애 점검 순서

Kakao Login 설정 → 동의항목 → 토큰 유효성 → scope → 메시지 API 요청 →
응답 코드
