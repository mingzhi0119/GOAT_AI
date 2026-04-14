# Vercel Frontend Deployment

This runbook covers the split deployment where the React/Vite frontend is hosted
on **Vercel** and the existing FastAPI backend stays on a Linux host behind
**Nginx**.

## Target shape

- Frontend origin: `https://goat-dev.vercel.app`
- Backend origin: `https://goat-api.duckdns.org`
- Browser API origin during runtime: `https://goat-dev.vercel.app/api/*`
- Runtime proxy model: Vercel rewrites `/api/*` to `https://goat-api.duckdns.org/api/*`
- Public browser auth model: one shared site password plus a signed browser-specific cookie

This preserves the frontend's same-origin runtime posture without adding browser
CORS complexity to chat, uploads, downloads, or SSE.

## Repository changes that enable this layout

- `frontend/vercel.json` rewrites `/api/:path*` to `https://goat-api.duckdns.org/api/:path*`
- `frontend/.vercelignore` excludes desktop packaging artifacts from local CLI uploads
- frontend runtime API calls now normalize to root-relative `/api/...` paths
- `frontend/package.json` now uses `node: 24.x` so Vercel can satisfy the engine
  constraint without depending on a specific Node 24 minor
- the SPA now bootstraps `GET /api/auth/session` before loading history/models/features
  and shows a shared-password gate when the backend enables browser access control

## Vercel project setup

Create a **new** Vercel project for this frontend. Do not reuse unrelated
projects.

Recommended project settings:

- Team: `mingzhi0119's projects`
- Framework preset: `Vite`
- Root Directory: `frontend`
- Install Command: `npm ci`
- Build Command: `npm run build`
- Output Directory: `dist`
- Production Branch: `main`

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

Recommended backend auth env vars for the public site:

```bash
export GOAT_SHARED_ACCESS_PASSWORD='replace-with-a-site-password'
export GOAT_SHARED_ACCESS_SESSION_SECRET='replace-with-a-long-random-signing-secret'
export GOAT_SHARED_ACCESS_SESSION_TTL_SEC=2592000
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
   `auth_required=true`.
3. `https://goat-dev.vercel.app` loads and the browser can reach `GET /api/health`
   through the frontend origin.
4. `POST /api/chat` from the frontend receives streamed `thinking` or `token`
   frames without proxy buffering delays.
5. Anonymous `curl https://goat-dev.vercel.app/api/history` now returns `401`
   with `code = AUTH_LOGIN_REQUIRED`.
6. Two clean browser profiles can log in with the same shared site password but
   only see their own history rows and artifact downloads.
7. History load, upload, artifact download, and `/api/system/features` all work
   through `goat-dev.vercel.app` after login.
8. Preview deployments still proxy `/api/*` to `goat-api.duckdns.org` as intended.

## Rollback

- frontend rollback: use Vercel deployment rollback / promote controls
- backend rollback: use [ROLLBACK.md](ROLLBACK.md)
- if only the frontend proxy configuration regresses, revert `frontend/vercel.json`
  and redeploy the Vercel project
