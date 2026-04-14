# Vercel Frontend Deployment

This runbook covers the split deployment where the React/Vite frontend is hosted
on **Vercel** and the existing FastAPI backend stays on a Linux host behind
**Nginx**.

## Target shape

- Frontend origin: `https://goat-dev.vercel.app`
- Backend origin: `https://goat-api.duckdns.org`
- Browser API origin during runtime: `https://goat-dev.vercel.app/api/*`
- Runtime proxy model: Vercel rewrites `/api/*` to `https://goat-api.duckdns.org/api/*`
- Public browser auth model: shared password and/or account login, both backed by signed browser cookies

This preserves the frontend's same-origin runtime posture without adding browser
CORS complexity to chat, uploads, downloads, or SSE.

## Repository changes that enable this layout

- `frontend/vercel.json` rewrites `/api/:path*` to `https://goat-api.duckdns.org/api/:path*`
- `frontend/.vercelignore` excludes desktop packaging artifacts from local CLI uploads
- frontend runtime API calls now normalize to root-relative `/api/...` paths
- `frontend/package.json` now uses `node: 24.x` so Vercel can satisfy the engine
  constraint without depending on a specific Node 24 minor
- the SPA now bootstraps `GET /api/auth/session` before loading history/models/features
  and shows the appropriate shared-password/account login gate when the backend enables browser auth

## Vercel project setup

Recommended project settings:

- Team: `mingzhi0119's projects`
- Framework preset: `Vite`
- Root Directory: `frontend`
- Install Command: `npm ci`
- Build Command: `npm run build`
- Output Directory: `dist`
- Production Branch: `main`

Current linked project truth:

- Project id: `prj_9nxlqv85gJ2WcRn4K2tN9sxpiocj`
- Team id: `team_JQbuOYqV6eUzhLDpwtLbbpAf`
- The live project must keep `Root Directory=frontend`; if Vercel drifts back to
  repo-root entrypoint `.` the deployment can show `READY` while both `/` and
  `/api/health` return `404 NOT_FOUND`.
- Repo-root [`.vercelignore`](/E:/simonbb/GOAT_AI/.vercelignore) must exclude
  `frontend/src-tauri/target` and related desktop artifacts, otherwise a repo-root
  production deploy can fail before build upload completes.

For one-off local preview deployments from the `frontend/` directory, prefer:

```bash
npx vercel build
npx vercel deploy --prebuilt
```

That path builds from the local checkout, where `frontend/scripts/generate-api-types.mjs`
can still read `../docs/api/openapi.json`, and avoids uploading desktop build artifacts.

Current frontend domain:

- active Vercel domain: `goat-dev.vercel.app`

Preview deployments in this layout still proxy `/api/*` to the production backend
at `goat-api.duckdns.org`. That is an intentional tradeoff for fast rollout, so preview
traffic can reach real API data.

## DNS

Point the backend hostname to the Linux host or its reverse proxy:

- `goat-api.duckdns.org` -> the public IP / load balancer that terminates TLS for Nginx

## Linux backend reverse proxy

Keep FastAPI/Uvicorn on the existing Linux host at `127.0.0.1:62606`, then place
Nginx in front of it for `goat-api.duckdns.org`.

Deploy the backend in this shape with:

```bash
bash ops/deploy/deploy_remote_server.sh
```

Recommended backend auth env vars for the public site:

```bash
export GOAT_SHARED_ACCESS_PASSWORD_HASH="$(python -c "from pwdlib import PasswordHash; print(PasswordHash.recommended().hash('replace-with-a-site-password'))")"
export GOAT_SHARED_ACCESS_SESSION_SECRET='replace-with-a-long-random-signing-secret'
export GOAT_SHARED_ACCESS_SESSION_TTL_SEC=2592000
export GOAT_ACCOUNT_AUTH_ENABLED=1
export GOAT_BROWSER_SESSION_SECRET='replace-with-a-second-long-random-signing-secret'
export GOAT_ACCOUNT_SESSION_TTL_SEC=2592000
export GOOGLE_CLIENT_ID='replace-with-google-client-id'
export GOOGLE_CLIENT_SECRET='replace-with-google-client-secret'
export GOOGLE_REDIRECT_URI='https://goat-dev.vercel.app/'
```

Keep header-based API keys only for operator/script access; the public browser
path should rely on the signed cookie flow instead of a visible owner id.

Example Nginx server block:

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name goat-api.duckdns.org;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name goat-api.duckdns.org;

    ssl_certificate /etc/letsencrypt/live/goat-api.duckdns.org/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/goat-api.duckdns.org/privkey.pem;

    client_max_body_size 25m;

    location /api/ {
        proxy_pass http://127.0.0.1:62606;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_redirect off;

        # Keep SSE and long-running streams responsive.
        proxy_buffering off;
        proxy_request_buffering off;
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }
}
```

Notes:

- keep FastAPI bound to localhost rather than exposing `:62606` directly
- `proxy_buffering off` is required for streamed chat tokens and other SSE-style
  responses
- `client_max_body_size` should stay above the app's upload cap (`GOAT_MAX_UPLOAD_MB`)
- TLS certificate issuance can be handled with Certbot or the host's existing ACME flow

## Validation checklist

Repository-local:

```bash
cd frontend
npm ci
npm run lint
npm run depcruise
npm run contract:check
npm test -- --run
npm run build
```

Public deployment:

1. `https://goat-api.duckdns.org/api/health` returns `200`.
2. `https://goat-api.duckdns.org/api/auth/session` returns `200` with
   `auth_required=true` and the expected `available_login_methods`.
3. `https://goat-dev.vercel.app` loads and the browser can reach `GET /api/health`
   through the frontend origin.
4. `POST /api/chat` from the frontend receives streamed `thinking` or `token`
   frames without proxy buffering delays.
5. Anonymous `curl https://goat-dev.vercel.app/api/history` now returns `401`
   with `code = AUTH_LOGIN_REQUIRED`.
6. Two clean browser profiles can log in with the same shared site password but
   only see their own history rows and artifact downloads.
7. The same account can log in from two browsers and see the same stable history rows.
8. If Google OAuth is enabled, the configured `GOOGLE_REDIRECT_URI` is allow-listed in Google Console and a browser login can round-trip through `/api/auth/account/google/url` plus `/api/auth/account/google`.
9. History load, upload, artifact download, and `/api/system/features` all work
   through `goat-dev.vercel.app` after login.
10. Preview deployments still proxy `/api/*` to `goat-api.duckdns.org` as intended.
11. Vercel build logs show the frontend root directory rather than repo-root
    entrypoint `.`.

## Rollback

- frontend rollback: use Vercel deployment rollback / promote controls
- backend rollback: use [ROLLBACK.md](ROLLBACK.md)
- if only the frontend proxy configuration regresses, revert `frontend/vercel.json`
  and redeploy the Vercel project
