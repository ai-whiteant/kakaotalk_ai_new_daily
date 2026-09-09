"""Local interactive OAuth; saves tokens without printing them."""
import json
import secrets
import sys
import time
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from cryptography.fernet import Fernet
from news.daily import ROOT, api, config, require, ServiceError, State


def main():
    cfg = config()
    require(cfg, 'KAKAO_REST_API_KEY')
    redirect = cfg['KAKAO_REDIRECT_URI']
    if redirect != 'http://localhost:8765/callback':
        raise ServiceError('Register and use redirect URI http://localhost:8765/callback')
    nonce = secrets.token_urlsafe(32)
    received = {}

    class Callback(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            parsed = urllib.parse.urlsplit(self.path)
            query = urllib.parse.parse_qs(parsed.query)
            valid = parsed.path == '/callback' and query.get('state') == [nonce]
            if valid:
                received.update(query)
            self.send_response(200 if valid else 400)
            self.end_headers()
            self.wfile.write(b'Authorization received. Return to the terminal.' if valid else b'Invalid callback.')

    with HTTPServer(('127.0.0.1', 8765), Callback) as server:
        server.timeout = 1
        url = 'https://kauth.kakao.com/oauth/authorize?' + urllib.parse.urlencode({
            'client_id': cfg['KAKAO_REST_API_KEY'], 'redirect_uri': redirect,
            'response_type': 'code', 'scope': 'talk_message', 'state': nonce})
        webbrowser.open(url)
        print('Complete Kakao login and message consent in the opened browser. Waiting up to 5 minutes.')
        deadline = time.monotonic() + 300
        while not received and time.monotonic() < deadline:
            server.handle_request()
    if not received.get('code'):
        raise ServiceError('Authorization was not completed; no tokens saved')
    payload = {'grant_type': 'authorization_code', 'client_id': cfg['KAKAO_REST_API_KEY'],
               'redirect_uri': redirect, 'code': received['code'][0]}
    if cfg.get('KAKAO_CLIENT_SECRET'):
        payload['client_secret'] = cfg['KAKAO_CLIENT_SECRET']
    result = api('https://kauth.kakao.com/oauth/token', payload, form=True)
    scopes = api('https://kapi.kakao.com/v2/user/scopes', headers={'Authorization': 'Bearer ' + result['access_token']})
    if not any(s.get('id') == 'talk_message' and s.get('agreed') is True for s in scopes.get('scopes', [])):
        raise ServiceError('Message consent missing; repeat authorization')
    cfg['KAKAO_REFRESH_TOKEN'] = result['refresh_token']
    cfg['STATE_ENCRYPTION_KEY'] = cfg.get('STATE_ENCRYPTION_KEY') or Fernet.generate_key().decode()
    path = ROOT / 'news/config.json'
    path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding='utf-8')
    state = State(cfg)
    state.data['refresh_token'] = result['refresh_token']
    state.save()
    print('Refresh token saved to news/config.json and encrypted state. No token values displayed.')


if __name__ == '__main__':
    try:
        main()
    except ServiceError as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
    except Exception as error:
        print('Authorization stopped: ' + type(error).__name__, file=sys.stderr)
        raise SystemExit(1)
