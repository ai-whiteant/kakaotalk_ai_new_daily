# Phase 1 — Tavily Search TEST

기존 `news.daily`, Gemini, Kakao, GitHub Actions에는 연결하지 않은 독립 실행 경로입니다.
Python 3.12+ 표준 라이브러리만 사용합니다. 기존 인증 파일은 변경하지 않습니다.

```powershell
python -m unittest news.test_phase1 -v
python -m news.phase1 --mode TEST --config "기존 news/config.json 절대 경로"
```

`TAVILY_API_KEY` 환경변수가 우선이며 지정한 JSON에서는 Tavily 키만 사용합니다.
키나 토큰을 명령행 인자로 입력하지 마세요. TEST도 Tavily 검색 사용량은 발생합니다.
LIVE는 거부합니다. Gemini 분석/호출, Kakao 인증/발송은 없습니다.

`config/news_queries.yaml`은 YAML 1.2의 JSON 부분집합으로 작성했습니다.
별도 YAML 의존성 없이 `json`으로 읽으므로 수정 시 JSON 문법을 유지하세요.
7개 분야 각각 한글·영문 1개, 총 14개 쿼리이며 우선순위는 선별 점수가 아닙니다.

검색 기본값은 news/week/basic, 쿼리별 최대 5개입니다. 재시도는 네트워크/5xx만
최대 총 3회, 대기는 1초·2초입니다. 인증 오류는 즉시 중단하고, 429/사용량 오류는
추가 호출 없이 해당 쿼리 실패로 기록합니다. 다른 쿼리는 계속 수행합니다.
두 분야 이상 검색 실패 또는 후보 스키마 오류는 HOLD입니다.

기간은 실행 시작 UTC 기준 정확히 직전 168시간이며 양 끝을 포함합니다.
검색 서버의 week 필터에 더해 발행일을 로컬에서 검사합니다. 누락·파싱 실패·
시간대 없는 날짜는 추정하지 않고 quarantine 파일로 격리합니다. 기간 밖과 미래
기사도 격리합니다. 검색 API의 발행일이며 원문 사실 검증은 아직 수행하지 않습니다.

정규화 전 원본 응답, 전체 정규화 후보, 기간 내 URL 중복 제거 후보, 격리 후보,
쿼리별 출처 연결(provenance), 실행 로그를 `outputs/phase1/`에 저장합니다.
URL은 호스트 소문자화·기본 포트·fragment·명백한 추적 인자만 정리하며,
기사 식별 query와 경로 마지막 slash는 보존합니다. 동일 사건의 의미 중복은 다루지 않습니다.
분야별 통계는 중복 제거 후 첫 쿼리의 category_hint 기준이며 복수 분야 연결은 provenance에 보존합니다.
언어는 문자 기반 추정, 국가는 `.kr`만 KR로 추정하고 나머지는 UNKNOWN입니다.
raw_content는 검색 비용/데이터 크기 제한을 위해 요청하지 않으며 null이 정상입니다.

로그에는 응답의 오류 본문·인증 헤더·키를 기록하지 않습니다. 응답 및 저장 직전
사용 Tavily 키와 알려진 키 형태를 검사하며 발견 시 HOLD로 차단합니다.
검사 범위는 모든 형태의 임의 토큰을 알아내는 범용 탐지기가 아닙니다.
결과 ZIP은 명시적 허용 파일 목록만 포함해야 합니다.

공식 계약 확인: [Tavily Search](https://docs.tavily.com/documentation/api-reference/endpoint/search)
(2026-09-09). 운영 배포·스케줄 변경은 이 단계에 포함하지 않습니다.
