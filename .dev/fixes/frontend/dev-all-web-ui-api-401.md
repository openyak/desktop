# dev:all browser UI shows no models and API requests return 401
**Status**: active | **Created**: 2026-04-25 | **Tags**: frontend, auth, dev

## Symptoms
Running `npm run dev:all` and opening `http://localhost:3000/c/new` in a browser shows "No model available" even though the backend is running and `/health` reports connected providers. Backend logs show `/api/*` requests returning `401 Unauthorized`.

## Root Cause
The web dev path used Next.js rewrites to proxy `/api/*` to the authenticated backend, but unlike the Tauri shell it had no session-token bridge and sent no bearer credential.

## Fix
`npm run dev:all` now launches through `scripts/dev-all.mjs`, which generates one per-run dev session token and provides it to both backend and frontend. The backend accepts that override only when `OPENYAK_ALLOW_DEV_SESSION_TOKEN=true`, Next.js rewrites append it to proxied `/api/*` calls, and local SSE uses the same token query fallback.

## Prevention
- [x] Test added?
- [ ] Lint catches it?
- [ ] Gotcha updated?
