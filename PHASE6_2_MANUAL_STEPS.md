# Phase 6.2 Manual Steps

## After Vercel production deployment

1. Note the production domain, e.g.
   `https://kakao-ai-news-link-gateway.vercel.app`

2. Browser test:
   - `<domain>/health`
   - `<domain>/r/evt_0da37ec7577bcd6b517d`
   It must reach NYC Schools.

3. Kakao Developers:
   앱 → 제품 링크 관리 → 웹 도메인

4. Add only the Gateway production origin:
   `https://<production-domain>`

5. Save.

6. Then authorize the Phase 6.2 Kakao smoke test.

Do not delete old journals.
Do not rerun Phase 6 or Phase 6.1.
