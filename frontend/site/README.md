# Vicinic — Marketing Site

Plain static HTML/CSS/JS — no build step, no framework. Built on the
["Orbit" template](https://bootstrapmade.com/orbit-bootstrap-template/) by
BootstrapMade, recolored to Vicinic's black/white/gold brand and rewritten
with real content (see "What changed from the template" below).

## Pages

- `index.html` — one-page site: hero, about, services, pricing, portfolio,
  why-us, contact (all anchor-linked sections, e.g. `#pricing`)
- `privacy.html`, `terms.html` — plain-language policy pages (short, real
  content — not the template's original Lorem Ipsum placeholders)
- `404.html` — Cloudflare Pages automatically serves this for unmatched
  routes; no `_redirects` file needed

## Local development

No build tooling needed — it's just static files:

```bash
cd frontend/site
python3 -m http.server 8000
# visit http://localhost:8000/
```

## Contact form (Web3Forms)

The form in `index.html`'s Contact section posts to Web3Forms via
`assets/js/forms.js` (a small custom script — see below for why).

1. Get a free access key at [web3forms.com](https://web3forms.com).
2. Replace `YOUR_WEB3FORMS_ACCESS_KEY` in the hidden `access_key` input in
   `index.html`'s contact `<form>` with your real key. Web3Forms access
   keys are meant to be public/embedded client-side (unlike a typical API
   secret) — this is their documented usage pattern, not a leak.

### Why a custom `forms.js` instead of the template's own vendor script

The Orbit template ships `assets/vendor/php-email-form/validate.js`, which
expects its own PHP backend to reply with the literal text `"OK"` on
success. Web3Forms replies with JSON (`{success: true/false, message}`)
instead, so that vendor script would always report an error even when the
message actually sent. `assets/js/forms.js` replaces it with the same
loading/error/success UI, parsing Web3Forms' actual response format.

## What changed from the template

- **Colors**: `assets/css/main.css`'s `:root` variables recolored to
  black/white/gold (was blue-on-slate). See the comments at the top of
  that file.
- **Content**: every section's copy replaced with real Vicinic content
  (packages, portfolio, about, etc.) — the original had placeholder
  Lorem Ipsum and fabricated stats (fake years-in-business, team size,
  client counts) that would be actively misleading on a real business's
  site, so those were dropped rather than translated.
- **Dropped sections**: Testimonials and Team — the originals used
  fabricated named reviewers/staff with stock photos, which isn't
  something to publish as genuine on a real company's site. Add these
  back for real once there's real content for them.
- **Added**: a Pricing section (not in the original template) with
  Vicinic's actual packages — custom CSS for this lives at the bottom of
  `main.css` under "Pricing Section (added for Vicinic...)".
- **Removed vendor libraries** no longer used after dropping
  testimonials/team and simplifying portfolio to a plain grid: Swiper
  (testimonial carousel), Isotope + imagesLoaded (portfolio filtering),
  PureCounter (animated stat counters), the PHP email form vendor script.
  AOS (scroll reveals) and GLightbox (image/video lightbox) are still used.
- **Logo**: still a text wordmark ("Vicinic.") — swap in an image logo in
  the header once one exists (see the commented-out example in the
  original template's header markup pattern). The `og:image` meta tag is
  also commented out pending a real brand image.

## SEO

- Title, meta description, canonical URL, Open Graph tags, and an
  `Organization` JSON-LD block directly in `index.html`'s `<head>`.
- `robots.txt` and `sitemap.xml` at the project root — update the domain
  in both if it changes from `vicinic.com`.

## Deploying to Cloudflare Pages

1. Workers & Pages → Create → Pages → connect this repo (or open the
   existing `vicinic` project's settings if it already exists).
2. Build settings:
   - Root directory (advanced): `frontend/site`
   - Build command: *(leave empty — there's nothing to build)*
   - Build output directory: `/` (the root of `frontend/site`)

> **If you already have a live Cloudflare Pages project for this app**,
> update its Root directory setting to `frontend/site` and clear its build
> command — it previously expected a `package.json`/`npm run build`, which
> no longer exist now that this is a plain static site.
