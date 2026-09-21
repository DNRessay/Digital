# Vicinic

Self-service website builder: customers pick a template and edit only its
text; templates are converted from static HTML zips via
[Templify](https://github.com/DNRessay/templify) and shared unmodified
across every site that uses them.

## Layout

```
backend/            Django + Mangum on Lambda (see backend/README.md)
frontend/
  site/             Marketing site (vicinic.com) — Vite + React
  admin/            Admin dashboard: template manager (real) + sites/overview (placeholder) — Vite + React
  web-portal/       Customer-facing site editor (edit your own site's text) — Vite + React
```

Each `frontend/*` app is deployed to Cloudflare Pages as its own project —
see `frontend/README.md` for the per-app setup. The backend is one Django
app deployed to AWS Lambda — see `backend/README.md`.

## How the pieces talk to each other

- **admin** and **web-portal** call the backend's JSON API
  (`/api/...`) with the browser's session cookie
  (`credentials: 'include'`). The backend's `FRONTEND_ORIGINS` env var
  must list every such app's deployed origin (CORS + CSRF).
- Signing in still happens on the backend's own `/admin/login/` page — the
  SPAs redirect the browser there on a `401` and rely on `next=` to bounce
  back afterward.
- Published customer sites (`Site.slug`) are rendered directly by the
  Django backend (`/<slug>/`) — not part of any frontend app.
