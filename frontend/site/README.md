# Vicinic

Multi-page React site for Vicinic, built with Vite + React Router, deployed on Cloudflare Pages.

## Pages

- `/` – Home
- `/about` – About
- `/services` – Services
- `/portfolio` – Portfolio
- `/contact` – Contact (Web3Forms)

## Local development

```bash
npm install
cp .env.example .env   # add your Web3Forms access key
npm run dev
```

## Contact form (Web3Forms)

1. Get a free access key at [web3forms.com](https://web3forms.com).
2. Set `VITE_WEB3FORMS_ACCESS_KEY` in `.env` (local) and in the Cloudflare Pages
   project's environment variables (production/preview).
3. The form in `src/pages/Contact.jsx` posts directly to the Web3Forms API —
   no backend required.

## SEO

- Per-page `<title>`, meta description, canonical URL, Open Graph, and Twitter
  card tags via `react-helmet-async` (`src/components/SEO.jsx`).
- `Organization` JSON-LD structured data on the homepage.
- `public/robots.txt` and `public/sitemap.xml` — update the domain in both if
  it changes from `vicinic.com`.
- Semantic headings and descriptive link/button text throughout.

If you swap in a custom domain, update `SITE_URL` in `src/components/SEO.jsx`
and the URLs in `public/robots.txt` and `public/sitemap.xml`.

## Deploying to Cloudflare Pages

> **This app moved from the repo root into `frontend/site/`.** If you
> already have a live Cloudflare Pages project for it, its build will
> break on the next push unless you update that project's **Root
> directory** setting (Settings → Builds & deployments) to `frontend/site`
> — otherwise Cloudflare still looks for `package.json` at the repo root,
> which no longer exists there.

**Option A — Git integration (recommended)**

1. Push this repo to GitHub.
2. In the Cloudflare dashboard: Workers & Pages → Create → Pages → connect
   the repo (or open the existing `vicinic` project's settings if it
   already exists).
3. Build settings:
   - Root directory (advanced): `frontend/site`
   - Build command: `npm run build`
   - Build output directory: `dist`
4. Add the `VITE_WEB3FORMS_ACCESS_KEY` environment variable in the Pages
   project settings.

**Option B — Wrangler CLI**

```bash
cd frontend/site
npm run build
npx wrangler pages deploy dist --project-name=vicinic
```

> Note: this project has no `wrangler.toml`. Cloudflare Pages'
> `wrangler.toml` support doesn't allow a `[build]` command, and its mere
> presence overrides the dashboard's build command field — so for a
> git-integration deploy, set the build command/output directory in the
> dashboard (Option A) instead of adding one back.

`public/_redirects` (`/* /index.html 200`) is included so client-side routes
resolve correctly on Cloudflare Pages.
