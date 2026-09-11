# KakaoTalk Message REST API --- Kakao ai news

최종 확인일: 2026-09-09 공식 문서:
https://developers.kakao.com/docs/ko/kakaotalk-message/rest-api 개념
문서: https://developers.kakao.com/docs/en/kakaotalk-message/common

## 프로젝트 역할

완성된 AI 뉴스 브리핑을 KakaoTalk `나에게 보내기`로 전달.

## 현재 핵심 엔드포인트

POST https://kapi.kakao.com/v2/api/talk/memo/default/send

## 요구 사항

-   Kakao Login 사용 설정
-   유효한 사용자 Access Token
-   `talk_message` 동의
-   기본 템플릿 형식에 맞는 template_object

## 운영 원칙

-   친구에게 보내기 API와 혼동하지 않는다.
-   메시지 전송 오류는 Tavily/Gemini 오류와 분리한다.
-   Access Token을 소스·로그·문서에 노출하지 않는다.
-   Kakao 메시지 길이/템플릿 제약을 고려해 브리핑을 논리적으로 분할한다.
