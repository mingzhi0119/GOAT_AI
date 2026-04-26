# Vercel Frontend Deployment

This runbook covers the split deployment where the React/Vite frontend is hosted
on **Vercel** and the existing FastAPI backend stays on a Linux host behind
**Nginx**.

## Target shape

- Frontend origin: `https://goat-dev.vercel.app`
- Backend origin: `https://goat-api.duckdns.org`
- Browser API origin during runtime: `https://goat-dev.vercel.app/api/*`
- Runtime proxy model: Vercel rewrites `/api/*` to `https://goat-api.duckdns.org/api/*`
- Public demo model: no browser login, API key, OAuth, or owner-id gate

This preserves the frontend's same-origin runtime posture without adding browser
CORS complexity to chat, uploads, downloads, or SSE.

## Repository changes that enable this layout

- `frontend/vercel.json` rewrites `/api/:path*` to `https://goat-api.duckdns.org/api/:path*`
- `frontend/.vercelignore` excludes desktop packaging artifacts from local CLI uploads
- frontend runtime API calls now normalize to root-relative `/api/...` paths
- `frontend/package.json` now uses `node: 24.x` so Vercel can satisfy the engine
  constraint without depending on a specific Node 24 minor
- the SPA mounts immediately without an Auth bootstrap, so the shell remains usable
  even while the backend is unavailable

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

Do not set historical Auth env vars on this demo deployment. `load_settings()`
fails fast if any of `GOAT_API_KEY`, `GOAT_API_KEY_WRITE`,
`GOAT_API_CREDENTIALS_JSON`, `GOAT_SHARED_ACCESS_*`, `GOAT_ACCOUNT_*`,
`GOOGLE_*`, or `GOAT_REQUIRE_SESSION_OWNER` are configured. Use the rate limiter,
Ollama queueing, and host-level controls as the protection posture for the demo.

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
2. `https://goat-dev.vercel.app` loads the chat shell without a login screen,
   even if the backend is temporarily unavailable.
3. The browser can reach `GET /api/health`
   through the frontend origin.
4. `POST /api/chat` from the frontend receives streamed `thinking` or `token`
   frames without proxy buffering delays.
5. Anonymous `curl https://goat-dev.vercel.app/api/history` does not return an
   Auth-required response.
6. History load, upload, artifact download, and `/api/system/features` all work
   through `goat-dev.vercel.app` without Auth setup.
7. Preview deployments still proxy `/api/*` to `goat-api.duckdns.org` as intended.
8. Vercel build logs show the frontend root directory rather than repo-root
    entrypoint `.`.

## Rollback

- frontend rollback: use Vercel deployment rollback / promote controls
- backend rollback: use [ROLLBACK.md](ROLLBACK.md)
- if only the frontend proxy configuration regresses, revert `frontend/vercel.json`
  and redeploy the Vercel project
