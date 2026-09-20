# Frontend apps

Four separate apps, each its own Cloudflare Pages project pointed at a
different subdirectory of this same repo (monorepo-style — Cloudflare
Pages supports this via each project's own "Root directory" setting).

| App          | Purpose                                              | Stack                  | Status                    |
| ------------ | ----------------------------------------------------- | ---------------------- | ------------------------- |
| `site`       | Marketing site (vicinic.com)                          | Static HTML/CSS/JS     | Existing, live            |
| `admin`      | Central dashboard (sites, templates overview)         | Vite + React           | Scaffold — placeholder UI |
| `portal`     | Template manager (upload zips, list templates)        | Vite + React           | Functional — real API     |
| `web-portal` | Customer editor (edit your own site's slot text)      | Vite + React           | Scaffold — no API yet     |

`site` has no build step (plain static files); `admin`/`portal`/`web-portal`
are Vite apps and need a build.

## Deploying each app to Cloudflare Pages

For each app, create a **separate** Cloudflare Pages project (Workers &
Pages → Create → Pages → connect this repo), then in that project's
build settings, with **Root directory (advanced)** set to `frontend/<app>`:

- **`site`**: Build command *(empty)*, output directory `/`
- **`admin` / `portal` / `web-portal`**: Build command `npm run build`, output directory `dist`

Do **not** add a `wrangler.toml` to any of these apps — its mere presence
overrides the dashboard's build command field, which breaks git-integration
deploys (see `frontend/site/README.md` for the full explanation from when
this was hit on the `site` app).

### Environment variables per app

- **portal**: `VITE_API_BASE_URL` — the backend's Lambda Function URL, no
  trailing slash (see `frontend/portal/.env.example`).
- **site**: no build-time env vars (no build step) — the Web3Forms access
  key is a hardcoded value directly in `index.html` (see `frontend/site/README.md`
  — Web3Forms keys are meant to be public/embedded client-side).
- **admin**, **web-portal**: none yet — they're placeholder UI with no
  backend wiring.

### Backend-side: registering each app's origin

Once an app is deployed, add its Cloudflare Pages URL (and any custom
domain) to the backend's `FRONTEND_ORIGINS` env var (comma-separated) —
see `backend/.env.example`. Without this, the backend's CORS/CSRF config
will reject that app's API calls even though the app itself loads fine.

## Known limitation: cross-origin session cookies

`portal` (and eventually `web-portal`) authenticate by sending the
browser's Django session cookie cross-origin (`credentials: 'include'`)
rather than a token scheme. This requires `SameSite=None; Secure` cookies
(already configured in production — see `backend/config/settings.py`), and
works in current Chrome/Firefox, but browsers with stricter third-party
cookie policies (notably Safari's ITP) may block it intermittently. If
that becomes a real problem, the fix is a proper token-based auth flow
(e.g. a short-lived JWT returned from login, sent as an `Authorization`
header instead of relying on cookies) — not attempted here to keep this
first pass scoped.

## Local development

Each app is a normal Vite project:

```bash
cd frontend/<app>
npm install
npm run dev
```

`portal` needs the backend's `FRONTEND_ORIGINS` env var to include your
local dev origin (e.g. `http://localhost:5173`) to call the API — but note
the cross-origin cookie caveat above only fully works over HTTPS, so local
end-to-end testing of the login flow has the same limitation.
