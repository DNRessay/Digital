# Vicinic — Marketing Site

Vite + React (react-router-dom), built on top of the
["Orbit" template](https://bootstrapmade.com/orbit-bootstrap-template/) by
BootstrapMade, recolored to Vicinic's black/white/gold brand and rewritten
with real content (see "What changed from the template" below).

## Pages / routes

- `/` (Home) — one-page layout with every section: hero, about, services,
  pricing, portfolio, why-us, contact. Nav links on this page behave exactly
  like the original template's in-page anchors (`#pricing`, `#contact`, ...)
  — clicking them scrolls within the page, it does not navigate away.
- `/about`, `/services`, `/pricing`, `/portfolio`, `/contact` — each nav menu
  item also has its own dedicated, directly-linkable page rendering just that
  section. The same `src/sections/*.jsx` components back both Home and these
  pages, so content stays in sync automatically.
- `/privacy`, `/terms` — plain static HTML pages (`public/privacy.html`,
  `public/terms.html`), not part of the React bundle.
- Any unmatched route renders a React 404 page (`src/pages/NotFound.jsx`).

Internal links (nav, CTAs like "See Packages") are context-aware via
`src/components/SectionLink.jsx`: on Home they render a plain in-page anchor
(`<a href="#pricing">`); on any other page they render a real
`react-router-dom` `<Link>` to that section's dedicated route instead, since
the section doesn't exist on the current page.

## Local development

```bash
cd frontend/site
npm install
npm run dev
```

`npm run build` outputs to `dist/`; `npm run preview` serves that build
locally.

## Contact form (Web3Forms)

The Contact section (`src/sections/Contact.jsx`) posts to Web3Forms directly
from a React submit handler (no vendor form-validation script needed).

1. Get a free access key at [web3forms.com](https://web3forms.com).
2. Replace `YOUR_WEB3FORMS_ACCESS_KEY` in the hidden `access_key` input in
   `src/sections/Contact.jsx` with your real key. Web3Forms access keys are
   meant to be public/embedded client-side (unlike a typical API secret) —
   this is their documented usage pattern, not a leak.

## Static assets

Everything under `public/assets/` (vendor CSS/JS, images, `main.css`) is
served as-is by Vite — same relative paths as before. `public/assets/js/main.js`
and `forms.js` are only used by the two plain static pages (`privacy.html`,
`terms.html`); the React app ports the same behaviors itself
(`src/hooks/useOrbitChrome.js`, `src/components/Header.jsx`,
`src/sections/Contact.jsx`) since a classic `<script>` tag can't reliably run
against DOM that React renders and re-renders.

## What changed from the template

- **Colors**: `public/assets/css/main.css`'s `:root` variables recolored to
  black/white/gold (was blue-on-slate). See the comments at the top of that
  file.
- **Content**: every section's copy replaced with real Vicinic content
  (packages, portfolio, about, etc.) — the original had placeholder Lorem
  Ipsum and fabricated stats (fake years-in-business, team size, client
  counts) that would be actively misleading on a real business's site, so
  those were dropped rather than translated.
- **Dropped sections**: Testimonials and Team — the originals used
  fabricated named reviewers/staff with stock photos, which isn't something
  to publish as genuine on a real company's site. Add these back for real
  once there's real content for them.
- **Added**: a Pricing section (not in the original template) with Vicinic's
  actual packages — custom CSS for this lives at the bottom of `main.css`
  under "Pricing Section (added for Vicinic...)".
- **Removed vendor libraries** no longer used after dropping
  testimonials/team and simplifying portfolio to a plain grid: Swiper
  (testimonial carousel), Isotope + imagesLoaded (portfolio filtering),
  PureCounter (animated stat counters), the PHP email form vendor script.
  AOS (scroll reveals) and GLightbox (image/video lightbox) are still used,
  as the npm packages `aos` and `glightbox` driven from React.
- **Logo**: the real Vicinic mark (`public/assets/img/logo.png`), sized up in
  the header/footer from the template's default.
- **Per-section pages**: each nav item also routes to its own page (see
  "Pages / routes" above) — not part of the original one-page template.

## SEO

- Title, meta description, canonical URL, Open Graph tags, and an
  `Organization` JSON-LD block in `index.html`'s `<head>` (used for every
  route — `document.title` is set per-page in each `src/pages/*.jsx`).
- Every page has exactly one `<h1>`: the Hero headline on Home, and a
  visually-hidden `<h1>` matching the section title on each dedicated page
  (so the visible `<h2>` styling from `main.css` stays unchanged).
- `public/robots.txt` and `public/sitemap.xml` — update the domain in both if
  it changes from `vicinic.com`.

## Deploying to Cloudflare Pages

1. Workers & Pages → Create → Pages → connect this repo (or open the
   existing `vicinic` project's settings if it already exists).
2. Build settings:
   - Root directory (advanced): `frontend/site`
   - Build command: `npm run build`
   - Build output directory: `dist`

> **If your Cloudflare Pages project still has an empty build command and
> `/` as the output directory** (from a brief plain-static-HTML version of
> this app), change it back to `npm run build` / `dist` as above.
