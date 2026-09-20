# Frontend apps

Four separate apps, each its own Cloudflare Pages project pointed at a
different subdirectory of this same repo (monorepo-style — Cloudflare
Pages supports this via each project's own "Root directory" setting).

| App          | Purpose                                              | Stack                  | Status                    |
| ------------ | ----------------------------------------------------- | ---------------------- | ------------------------- |
| `site`       | Marketing site (vicinic.com)                          | Vite + React           | Existing, live            |
| `admin`      | Central dashboard (sites, templates overview)         | Vite + React           | Scaffold — placeholder UI |
| `portal`     | Template manager (upload zips, list templates)        | Vite + React           | Functional — real API     |
| `web-portal` | Customer editor (edit your own site's slot text)      | Vite + React           | Functional — real API     |

All four are Vite apps and need a build (`npm run build` → `dist/`).

## Deploying each app to Cloudflare Pages

For each app, create a **separate** Cloudflare Pages project (Workers &
Pages → Create → Pages → connect this repo), then in that project's
build settings, with **Root directory (advanced)** set to `frontend/<app>`:

- **`site` / `admin` / `portal` / `web-portal`**: Build command `npm run build`, output directory `dist`

Do **not** add a `wrangler.toml` to any of these apps — its mere presence
overrides the dashboard's build command field, which breaks git-integration
deploys.

> **If you have a live Cloudflare Pages project for `site` from before this
> app went back to Vite+React**, update its build command back to
> `npm run build` and its output directory back to `dist` — it was
> previously set to an empty build command and `/` output for a brief
> plain-static-HTML version of this app, which no longer applies.

### Environment variables per app

- **portal**, **web-portal**: `VITE_API_BASE_URL` — the backend's Lambda
  Function URL, no trailing slash (see each app's `.env.example`).
- **site**: no env vars — the Web3Forms access key is a hardcoded value in
  `src/sections/Contact.jsx`'s form markup (see `frontend/site/README.md` —
  Web3Forms keys are meant to be public/embedded client-side).
- **admin**: none yet — still placeholder UI with no backend wiring.

### Backend-side: registering each app's origin

Once an app is deployed, add its Cloudflare Pages URL (and any custom
domain) to the backend's `FRONTEND_ORIGINS` env var (comma-separated) —
see `backend/.env.example`. Without this, the backend's CORS config will
reject that app's API calls even though the app itself loads fine.

## Known limitation: `portal`'s cross-origin session cookie

`portal` authenticates by sending the browser's Django session cookie
cross-origin (`credentials: 'include'`) rather than a token scheme. This
requires `SameSite=None; Secure` cookies (already configured in production
— see `backend/config/settings.py`), and works in current Chrome/Firefox,
but browsers with stricter third-party cookie policies (notably Safari's
ITP, and increasingly Chrome too) may block it intermittently — the page
still loads fine (GET requests work), but a POST needing the matching CSRF
cookie can fail with no earlier warning. `SameSite=None` also requires
HTTPS, so this only actually works against the real deployed backend, not
a plain-HTTP local one — testing `portal`'s login/upload flow end-to-end
currently requires the real deployed backend.

**`web-portal` doesn't have this problem** — it hit exactly this failure
mode in practice (registration 403ing on a phone whose browser silently
never stored the cross-site cookie) and was switched to bearer-token auth
instead (`src/api.js`: a token from login/register stored in
`localStorage`, sent as an `Authorization` header). No cookies, no CSRF,
and no HTTPS requirement for local testing — see `backend/README.md`'s
`CustomerAuthToken` section. If `portal` ever hits the same problem in
practice, the fix is the same pattern.

## Local development

Each app is a normal Vite project:

```bash
cd frontend/<app>
npm install
npm run dev
```

**`web-portal`** works cross-origin against any backend (local or
deployed) — just set `VITE_API_BASE_URL` (see its `.env.example`).

**`portal`** needs the backend's `FRONTEND_ORIGINS` env var to include your
local dev origin (e.g. `http://localhost:5173`) to call the API — but per
the cross-origin cookie caveat above, this only actually works end-to-end
over HTTPS, so local testing of its login/upload flow requires the real
deployed backend.
