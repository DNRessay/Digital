# Frontend apps

Three separate apps, each its own Cloudflare Pages project pointed at a
different subdirectory of this same repo (monorepo-style — Cloudflare
Pages supports this via each project's own "Root directory" setting).

| App          | Purpose                                                          | Stack                  | Status                |
| ------------ | ----------------------------------------------------------------- | ---------------------- | --------------------- |
| `site`       | Marketing site (vicinic.com)                                      | Vite + React           | Existing, live        |
| `admin`      | Internal dashboard — template manager (real), sites/overview (placeholder) | Vite + React | Partly functional     |
| `web-portal` | Customer editor (edit your own site's slot text)                  | Vite + React           | Functional — real API |

`admin` used to be split across two apps (`admin` — a placeholder shell,
and `portal` — the real template manager); they were merged into one so
there's a single internal app instead of two to keep in sync. `portal`'s
upload/list template functionality is now `admin`'s `/templates` route.

All three are Vite apps and need a build (`npm run build` → `dist/`).

## Deploying each app to Cloudflare Pages

For each app, create a **separate** Cloudflare Pages project (Workers &
Pages → Create → Pages → connect this repo), then in that project's
build settings, with **Root directory (advanced)** set to `frontend/<app>`:

- **`site` / `admin` / `web-portal`**: Build command `npm run build`, output directory `dist`

Do **not** add a `wrangler.toml` to any of these apps — its mere presence
overrides the dashboard's build command field, which breaks git-integration
deploys.

### Client-side routing (`admin`, `site`) needs a `404.html` fallback

Both apps use React Router (`BrowserRouter`), so a direct visit or refresh
on a client-side route (e.g. `admin`'s `/templates`, `site`'s `/about`)
needs the server to fall back to `index.html` and let the router take it
from there. The classic fix is a `public/_redirects` file with
`/* /index.html 200` — both apps still have one — but Cloudflare Pages'
own build-time validator now rejects that exact rule as an "infinite loop"
(it collides with Cloudflare's automatic trailing-slash/`.html`-stripping
behavior) and silently drops it entirely, which would otherwise 404 every
deep link in production. Each app's `package.json` has a `postbuild` step
instead (`node -e "require('fs').copyFileSync('dist/index.html','dist/404.html')"`)
— Cloudflare's static asset server serves `404.html` for any unmatched
path by default, so the SPA shell loads either way and the router renders
the right page client-side. `web-portal` doesn't need this — no client-side
routes, so the root path it always serves is enough.

> **If you have a live Cloudflare Pages project for `site` from before this
> app went back to Vite+React**, update its build command back to
> `npm run build` and its output directory back to `dist` — it was
> previously set to an empty build command and `/` output for a brief
> plain-static-HTML version of this app, which no longer applies.

### Environment variables per app

- **admin**, **web-portal**: `VITE_API_BASE_URL` — the backend's Lambda
  Function URL, no trailing slash (see each app's `.env.example`).
- **site**: no env vars — the Web3Forms access key is a hardcoded value in
  `src/sections/Contact.jsx`'s form markup (see `frontend/site/README.md` —
  Web3Forms keys are meant to be public/embedded client-side).

### Backend-side: registering each app's origin

Once an app is deployed, add its Cloudflare Pages URL (and any custom
domain) to the backend's `FRONTEND_ORIGINS` env var (comma-separated) —
see `backend/.env.example`. Without this, the backend's CORS config will
reject that app's API calls even though the app itself loads fine.

## Auth: both apps use bearer tokens, not session cookies

`admin` and `web-portal` both authenticate via a token (`CustomerAuthToken`
— see `backend/README.md`'s section on it) returned from a login endpoint,
stored in `localStorage`, and sent as an `Authorization` header — no
cookies, no CSRF, no HTTPS requirement for local testing.

`admin` didn't start out this way — it originally sent the browser's
Django session cookie cross-origin (`credentials: 'include'`), the same
approach `web-portal` briefly used before hitting the problem this section
used to describe: a same-origin login works fine (cookies always attach to
a real page load), but the SPA's own subsequent cross-origin `fetch()`
calls can come back looking logged-out anyway, because browsers
increasingly refuse to attach a cross-site cookie to a fetch even with
`SameSite=None; Secure` set correctly (Safari's ITP, and increasingly
Chrome too). `admin` hit this in practice — bearer tokens sidestep it
entirely, which is why both apps use the same pattern now.

## Local development

Each app is a normal Vite project:

```bash
cd frontend/<app>
npm install
npm run dev
```

**`web-portal`** works cross-origin against any backend (local or
deployed) — just set `VITE_API_BASE_URL` (see its `.env.example`).

**`admin`** needs the backend's `FRONTEND_ORIGINS` env var to include your
local dev origin (e.g. `http://localhost:5173`) to call the API — but per
the cross-origin cookie caveat above, this only actually works end-to-end
over HTTPS, so local testing of its login/upload flow requires the real
deployed backend.
