# kakaotalk_ai_new_daily

최근 7일 국내외 AI 교육 뉴스를 Tavily **Remote MCP**로 검색하고 한국어로 요약해 카카오톡 **나에게 보내기**로 전송합니다. 각 기사에는 제목, 핵심내용, 시사점, 원문 링크가 포함됩니다. 기존 `main.py` 오목 예제는 보존되어 있으며 뉴스 실행 진입점은 `news.daily`입니다.

## 현재 준비 상태

- 다른 PC에서 실행 가능한 Python 코드와 `Kakao ai news` 스킬 포함
- GitHub Actions 실행 시각: 매일 **오전 7시, 한국 시간** (`22:00 UTC`)
- 실제 예약 전송은 저장소 변수 `ENABLE_DAILY_NEWS=true`를 설정한 뒤 활성화됩니다. **코드 업로드만으로 발송이 시작되지 않습니다.**
- 최초 설정에는 Tavily API 키, 요약용 Gemini API 키, 카카오 REST API 키와 Client Secret, 본인 계정 OAuth 인증이 필요합니다. Google AI Studio에서 무료 등급 프로젝트를 사용하세요. 코드로 결제 등급을 판별할 수는 없습니다. 결제를 연결한 프로젝트는 요금이 발생할 수 있습니다. 한도 오류가 나면 자동 재시도나 다른 유료 모델로 전환하지 않고 중단합니다.

## 다른 PC에서 준비

Python 3.12 이상과 Git을 설치한 뒤 터미널에서 실행합니다.

```powershell
git clone https://github.com/ai-whiteant/kakaotalk_ai_new_daily.git
cd kakaotalk_ai_new_daily
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r news/requirements.txt
Copy-Item news/config.example.json news/config.json
notepad news/config.json
```

macOS/Linux에서는 `.venv/bin/python`을 사용합니다. 예제 복사는 최초 한 번만 하세요. 기존 설정을 덮어쓰지 마세요.

`news/config.json` 입력 항목:

| 키 | 입력할 값 |
| --- | --- |
| `TAVILY_API_KEY` | Tavily API 키 |
| `GEMINI_API_KEY` | Gemini API 키 |
| `GEMINI_MODEL` | 기본 `gemini-3.1-flash-lite`; 사용 가능한 모델로 변경 가능 |
| `KAKAO_REST_API_KEY` | 카카오 앱 → 플랫폼 키 → REST API 키 |
| `KAKAO_CLIENT_SECRET` | 해당 REST API 키의 클라이언트 시크릿; 기능 사용 시 필수 |
| `KAKAO_REFRESH_TOKEN` | 아래 OAuth 도구가 자동 입력 |
| `STATE_ENCRYPTION_KEY` | 아래 OAuth 도구가 자동 생성 |
| `KAKAO_LINK_URL` | 카카오 제품 링크 관리에 등록한 주소. 기본값은 개발자 문서 주소 |

키나 토큰을 채팅·이슈·커밋에 붙여넣지 마세요. 모든 경로의 `config.json`, `.state`, `work`는 Git에서 제외됩니다. `config.example.json`에는 실제 값을 넣지 않습니다.

## 카카오 최초 인증 및 갱신 토큰 받기

기존 REST API 테스트 화면에서 복사한 액세스 토큰만으로 매일 자동 실행할 수는 없습니다.

1. 카카오 앱에서 **카카오 로그인 ON**, **카카오톡 메시지 전송(`talk_message`) 동의항목**을 설정합니다.
2. 카카오 로그인에서 사용하는 REST API 키의 리다이렉트 URI에 **`http://localhost:8765/callback`**을 등록합니다.
3. 제품 링크 관리에 **`https://developers.kakao.com`**을 등록합니다. 이 버튼은 서비스 안내용이며 뉴스 원문 링크는 메시지 본문에 따로 포함됩니다.
4. 설정 파일에 REST API 키·Client Secret을 입력한 뒤 실행합니다.

```powershell
.venv\Scripts\python.exe -m news.authorize_kakao
```

브라우저에서 메시지를 받을 카카오 계정으로 로그인하고 전송 권한에 동의합니다. 도구는 5분 동안 기다린 뒤 종료하며, 토큰은 화면에 출력하지 않고 로컬 설정과 암호화된 상태 파일에 저장합니다.

## 확인 및 수동 실행

```powershell
.venv\Scripts\python.exe -m news.daily --check
.venv\Scripts\python.exe -m news.daily
.venv\Scripts\python.exe -m news.daily --send
```

`--check`는 Tavily 도구 목록, 카카오 토큰 갱신과 동의만 확인합니다. 실제 검색·요약은 기본 실행으로 검증합니다. 기본 실행은 `news-output/latest.md` 미리보기만 저장하며, `--send`가 있을 때만 카카오 메시지를 발송합니다.

## GitHub에서 매일 오전 7시에 자동 실행

저장소 **Settings → Secrets and variables → Actions → Secrets**에서 아래 Repository secrets를 설정합니다. 값은 `news/config.json`에서 가져옵니다.

- `TAVILY_API_KEY`
- `GEMINI_API_KEY`
- `KAKAO_REST_API_KEY`
- `KAKAO_CLIENT_SECRET` (앱에서 클라이언트 시크릿 기능을 사용하면 필수)
- `KAKAO_REFRESH_TOKEN`
- `STATE_ENCRYPTION_KEY`

이 값들은 GitHub가 암호화해 저장하고 지정한 실행 작업에만 전달합니다. **소스 파일에 넣지 마세요.**

1. **Actions → Kakao AI education news → Run workflow**에서 `send=false`로 실행합니다.
2. 실행 결과의 `ai-education-news` 파일을 내려받아 내용을 검토합니다.
3. `send=true`로 한 번 실행해 본인 카카오톡 도착을 확인합니다.
4. **Settings → Secrets and variables → Actions → Variables**에서 `ENABLE_DAILY_NEWS` 값을 `true`로 만듭니다.
5. GitHub Actions 실패 알림을 받을 수 있도록 본인 알림 설정을 확인합니다.

GitHub 예약 실행은 정각을 보장하지 않으며 지연되거나 누락될 수 있습니다. 공개 저장소는 장기간 활동이 없으면 예약이 비활성화될 수 있으므로 Actions 상태를 확인하세요.

## 토큰 갱신과 중복 방지의 한계

카카오 액세스 토큰은 매 실행 시 갱신합니다. 새 리프레시 토큰이 반환되면 Fernet으로 암호화해 `.state/kakao.enc`에 저장하고 GitHub Actions cache로 이어받습니다. 캐시에는 평문 토큰이 들어가지 않습니다. 암호화 키는 GitHub Secret으로만 전달합니다.

캐시는 영구 저장소가 아닙니다. 캐시가 사라지거나 장기간 실행이 중단되면 초기 갱신 토큰이 만료되어 수동 재인증이 필요할 수 있습니다. 그때 OAuth 도구를 다시 실행하고 `KAKAO_REFRESH_TOKEN` Secret을 업데이트한 뒤, 저장소 변수 `KAKAO_STATE_VERSION` 값을 새 숫자로 바꿉니다.

성공한 기사 URL은 반복 전송하지 않습니다. 전송 도중 오류가 나면 상태를 `unknown`으로 기록하고 이후 전송을 멈춥니다. 카카오톡을 확인한 뒤 복구해야 하며 무조건 재실행하지 마세요. 프로세스 강제 종료나 캐시 저장 실패까지 포함한 완전한 1회 전송은 보장하지 않습니다. 다른 PC에서 같은 시간에 `--send`하면 별도 상태를 사용하므로 중복될 수 있습니다. 서버 예약을 켠 뒤에는 다른 PC에서 미리보기만 사용하는 것을 권장합니다.

## 뉴스 선정 기준

한국어·영어로 각각 검색하고 원문을 추출합니다. 검색 결과의 발행일 필터에 더해 원문에서 최초 발행일을 확인한 기사만 선정합니다. 날짜가 확인되지 않는 기사, 기간 밖 기사, 광고성 강좌 홍보, 교육과 무관한 AI 소식은 제외합니다. 기본 최대 6건이며 적합한 기사가 적으면 줄어듭니다. 검증된 기사가 없으면 카카오 메시지를 보내지 않고 실행 로그에 0건을 표시합니다.

200자 제한 때문에 한 기사가 여러 메시지로 나뉠 수 있습니다. 원문 URL은 잘라내지 않습니다. AI가 수행하는 날짜·중복·중요도 판정에 오류가 있을 수 있으므로 중요한 판단에는 원문을 확인하세요.

## Codex 스킬

`.agents/skills/kakao-ai-news`는 이 저장소에서 사용할 프로젝트 스킬입니다. 표시 이름은 **Kakao ai news**입니다. 다른 프로젝트에서도 쓰려면 이 폴더를 개인 스킬 폴더에 복사합니다. Codex의 Tavily MCP 연결은 PC마다 별도로 등록해야 하며, GitHub Actions는 앱의 MCP 설정에 의존하지 않고 Remote MCP를 직접 호출합니다.

## 테스트

```text
python -m unittest news.test_daily -v
```

테스트는 실제 API 호출이나 메시지 전송 없이 메시지 길이·URL 보존·암호화·전송 상태·날짜 근거 검증을 확인합니다.

공식 문서: [Tavily MCP](https://docs.tavily.com/documentation/mcp), [카카오 로그인](https://developers.kakao.com/docs/ko/kakaologin/rest-api), [카카오 메시지](https://developers.kakao.com/docs/ko/kakaotalk-message/rest-api), [GitHub 예약 실행](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).

