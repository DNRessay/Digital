# Vicinic — Site Builder Backend

Django backend for the self-service website builder. Templates are uploaded
as static HTML zips, converted via [Templify](https://github.com/DNRessay/templify)
into Django markup, then processed so every visible piece of text becomes an
editable "slot" — customers pick a template and edit only its text; the
markup/CSS/assets are shared and never touched per-site.

## How it fits together

- **Template** — one uploaded design. Its pages/assets are shared across
  every `Site` that picks it.
- **TemplateSlot** — one editable text node found while scanning the
  template's HTML (`builder/services/slot_extractor.py`). `page=None` means
  it's shared chrome (header/nav/footer); otherwise it belongs to one page.
- **Site** — a customer's site: picks a `Template`, has its own colors/
  contact info, and one `SiteSlotValue` per slot (blank = use the
  template's own default text).
- Rendering (`builder/views.render_site_page`) merges slot defaults +
  per-site overrides into `TemplatePage.document` (a flattened, standalone
  Django template string per page) and renders it directly — no Django app
  registration or code deploy needed per template.

## Adding a template

Templates are managed through **`frontend/portal`** (a separate React app —
see `../frontend/README.md`), which calls this backend's JSON API
(`builder/api_views.py`, `/api/templates/`). Upload a zip of a static HTML
template (the usual multi-page-with-`assets/`-folder layout); it's sent to
the deployed Templify conversion service (`TEMPLIFY_FUNCTION_URL`), then
`builder/services/template_ingest.py` turns the result into a `Template`
with its pages/slots/assets. No redeploy required — it's available to
customers immediately.

The old server-rendered `/manage/templates/` page (`builder/views.template_manager`)
still exists and works — it's the same underlying logic — but is superseded
by the portal app. Remove it once the portal app is deployed and verified.

A `Site` can also be set up through the **normal Django admin** at `/admin/`
— that part is exactly as the stock admin provides — for cases where staff
need to create or reassign one directly (e.g. attaching an existing `Site`
to a different `owner`, or changing its template/colors/contact info).
Staff can always edit the same slot values directly via the
`SiteSlotValue` inline on the `Site` admin page too — every path writes to
the same rows.

Getting a new customer set up is two separate steps, both self-serve
through **`frontend/web-portal`**: registering an account
(`POST /api/customer/register/`, just a username/password — no `Site`
yet), and, once logged in, creating a `Site` of their own
(`POST /api/customer/sites/`, picking a name and one of the active
`Template`s — provisions every one of that template's `SiteSlotValue`
rows, and publishes it immediately). This is deliberately free and
unrestricted — anyone can create a `Site` — but a freshly created one is on
the free tier: its rendered pages carry a small "Powered by Vicinic" credit
(see "PayFast subscriptions" below) until its owner subscribes to one of
the paid packages, which removes it.

Provisioning also does its best to replace the template's own hardcoded
demo name (e.g. a Bootstrap template called "CoreBiz" out of the box)
with the name the customer actually gave their `Site`, wherever it
appears — the logo, the `<title>`, a footer credit — rather than leaving
every new site showing the template author's own brand until someone
manually finds and edits each occurrence
(`services/site_provisioning._detect_brand_token`/`_name_overrides_for`).
It guesses the demo name from whatever slot text is present in the
page's own `<title>` and isn't a generic word (`_GENERIC_TEXT`) that
could coincidentally also appear in one, like "Home" or "Contact" — that
anchor is what tells "CoreBiz" (the actual brand) apart from those. This
only ever touches a slot's very first `SiteSlotValue` row (still blank,
never yet given a real override), so it can't clobber an edit made
later, and it's skipped entirely if no `<title>` slot is found or
nothing in it looks like a name. Both this and `apply_contact_info`
below only ever swap a *whole word* (`_contains_whole_word`/
`_replace_whole_word`, regex `\b`-bounded) — a plain substring match
doesn't know a word's edges, and a real report from a site named "Tea"
proved it: `"Tea" in "Team"` is true, so the very first version of this
silently corrupted a "Team" nav link into "CoffeeTeam" while never
touching the actual "CoreBiz" logo, since that false match "succeeded"
and starved the (also real, separately fixed) brand-detection logic of
ever running.

### Why the name can't be changed later

`Site.name` is chosen once at creation and locked after that — there's
deliberately no way to rename it through `PATCH /api/customer/sites/
<slug>/`, and web-portal's Overview tab shows it as a disabled field.
An arbitrary customer-chosen name has no reliable shape the way an email
address or phone number does (see `apply_contact_info` below), so
finding everywhere the *old* name appeared to swap in a new one always
comes back to some form of substring matching — which is exactly what
produced the "Team" corruption above. Locking it after creation removes
the failure mode entirely rather than trying to out-guess it.

## PayFast subscriptions (`builder/services/payfast.py`, `builder/payfast_views.py`)

A `Site.is_branded` property (true unless `subscription_status == "active"`)
controls whether `builder/views._render_site_page` injects that credit
before `</body>` on every rendered page. Subscribing to one of the three
packages already advertised on the marketing site's Pricing section
(Starter/Growth/Business OS — `builder/services/payfast.PACKAGES` is the
source of truth for the exact amounts) removes it, via PayFast's hosted
recurring-billing checkout:

1. `POST /api/customer/sites/<slug>/checkout/` (authenticated, owner-only).
   Body: `{package, return_url, cancel_url}` (the latter two must be on one
   of `FRONTEND_ORIGINS` — this endpoint refuses to build a redirect to
   anywhere else). Marks the `Site` `subscription_status="pending"`, and
   returns `{process_url, fields}` — an ordered list of `{name, value}`
   pairs the frontend submits as a real browser form POST to `process_url`
   (a `fetch()`/XHR redirect won't work; PayFast's checkout page has to be
   the top-level navigation). The first charge is `setup + monthly` for the
   chosen package; every renewal after that is `monthly` only
   (PayFast's own `amount` vs. `recurring_amount` fields).
2. PayFast's checkout happens entirely on their site — this backend never
   sees card details.
3. **`POST /api/payfast/notify/`** (public, `@csrf_exempt` — PayFast's own
   server calls this, no browser or CSRF token involved) is the only thing
   that ever actually activates a subscription. It: verifies the payload's
   signature (`verify_itn_signature`), then performs the required
   server-to-server confirmation back to PayFast itself
   (`confirm_with_payfast` — an ITN can be spoofed, so PayFast's own docs
   require this step before trusting it), checks the charged amount matches
   the expected package price **on first activation only** (subsequent
   monthly renewals are PayFast billing the previously-agreed
   `recurring_amount` on its own schedule), then sets
   `subscription_status="active"` and stores the returned subscription
   `token` (for any future cancel/manage call — not yet built).
4. The browser separately lands back on `return_url`/`cancel_url` — this is
   for UX only (a "payment received, activating…" message) and is **never**
   treated as proof of payment; only the ITN is.

Without any `PAYFAST_*` env vars set, this all runs against PayFast's own
published **sandbox test-merchant credentials** — safe, public, meant for
exactly this — so it works out of the box locally. Before this can take
real money, set `PAYFAST_MERCHANT_ID`/`PAYFAST_MERCHANT_KEY`/
`PAYFAST_PASSPHRASE` to a real PayFast merchant account's details and
`PAYFAST_SANDBOX=false` — see `.env.example` and "Deploying" below.

## Customer-facing API (`builder/customer_api.py`, `/api/customer/...`)

**Bearer-token authenticated (`CustomerAuthToken`), not session-cookie
based** — unlike the portal's `/api/...`. web-portal's backend is a
different site from the frontend, and browsers increasingly block
third-party cookies by default; a cross-site session cookie can silently
never get set at all (the page still loads fine — only a later POST
needing a matching CSRF cookie fails, with no earlier warning). This
actually happened in testing. A bearer token in an `Authorization` header
sidesteps it entirely: it doesn't touch the browser's cookie jar, works
identically over plain HTTP or HTTPS, and needs no CSRF protection (CSRF
exists to stop a forged cross-site request riding on ambient cookie auth —
moot for a header a cross-site page can't read or set). `login`/`register`
return `{token, ...}`; every other endpoint below requires
`Authorization: Token <token>`; `POST /api/customer/logout/` deletes the
token row server-side (a real revoke, not just "forget it client-side").

- `GET /api/customer/whoami/` — `{authenticated, username, name}`.
- `POST /api/customer/login/`, `POST /api/customer/logout/`
- `GET /api/customer/templates/` — public, no auth required: the `is_active`
  `Template`s, for the "create your site" form's picker.
- `POST /api/customer/register/` — public. Body: `{name, username, email,
  password}`. Validates the email format and the password against Django's
  own `AUTH_PASSWORD_VALIDATORS` (409 if the username or email is already
  taken — email is kept unique even though stock `User` doesn't enforce
  that, since a future "confirm your email" / 2FA flow needs it to be),
  splits `name` into `User.first_name`/`last_name`, creates just the `User`
  (no `Site` yet) and its token.
- `GET /api/customer/sites/` — the Sites owned by the current user.
- `POST /api/customer/sites/` — authenticated. Body: `{site_name,
  template_slug}`. Slugifies `site_name` for the `Site`'s slug (409 if it's
  already taken, or if `template_slug` isn't an active `Template`), creates
  the `Site` owned by the current user plus every one of its slot values.
- `GET /api/customer/sites/<slug>/slots/` — that site's slots grouped by
  page (`page: null` first, for shared header/footer text), each with its
  current effective value (an override, or the template's default).
- `POST /api/customer/sites/<slug>/slots/` — body is a flat JSON
  `{slot_key: value, ...}` map; only keys that are actually one of this
  site's slots are written (a 404 if the slug isn't owned by the caller).
  **Free-tier sites (`subscription_status != "active"`) can only write
  slots on the home page** — a key for any other page is silently
  dropped rather than erroring, since web-portal's editor already only
  ever offers the home page in that case (see "Click-to-edit preview"
  below).
- `PATCH /api/customer/sites/<slug>/` — authenticated. Body: any subset of
  `{tagline, phone, whatsapp_number, email, address, primary_color}` — the
  `Site`'s own profile fields, as opposed to its page text. `email` is
  validated as an address if non-blank (it's also where this site's own
  contact form sends messages — see `builder.views.site_contact`);
  `primary_color` must be a `#rrggbb` hex code or blank (falls back to the
  template's own `default_primary_color` — see "Theme color" below).
  **`name` is deliberately not accepted here** — see "Why the name can't
  be changed later" below. Setting `email`/`phone` also calls
  `services.site_provisioning.apply_contact_info`, which finds whatever
  already looks like an email address / phone number anywhere on the
  page and swaps in the new one (see the same section).
- `GET /api/customer/packages/` — public: the three packages (id, label,
  monthly, setup) for the "remove branding" picker.
- `POST /api/customer/sites/<slug>/checkout/` — authenticated. See "PayFast
  subscriptions" above.

## Theme color (`services/template_ingest._parametrize_theme_color`, `Site.primary_color`)

At ingest, after a template's pages/slots/assets are all created, a
best-effort pass looks at its own (non-vendor — anything named like
`bootstrap`/`jquery`/`owl`/etc. or ending `.min.css` is skipped, since
that's a bundled library's own palette, not the template author's) CSS
for the accent color used most often — a button/link/heading color, not
gray or white/black — and rewrites every occurrence of it, across *all*
of the template's CSS files, to `var(--vicinic-primary, <that same
color>)`. The fallback value keeps every site on that template looking
pixel-identical by default (the shared CSS file — same S3 object for
every `Site` on this `Template` — is otherwise untouched, matching "the
markup/CSS/assets are shared and never touched per-site" above), and the
detected color itself is stored on `Template.default_primary_color`
purely for the UI to show as a sensible default color-picker value.

A `Site.primary_color` override (blank means "use the template's
default") gets turned into a real, per-site color by
`builder.views._render_site_page` injecting `<style>:root{
--vicinic-primary:<color>;}</style>` right after `<head>` on every one of
that `Site`'s rendered pages — since a custom property set anywhere in
the document cascades to every element referencing it via `var()`, this
recolors the whole site without ever duplicating or rewriting the shared
stylesheet itself.

Only runs at ingest, so a `Template` uploaded before this feature
existed keeps `default_primary_color` blank forever (its CSS was never
rewritten with the `var()` wrapping, so a `Site.primary_color` override
would have nothing to hook into and silently do nothing) — run
`python manage.py backfill_theme_colors` once to catch those up; it's a
no-op for anything that already has a `default_primary_color`.

## Contact info find-and-replace (`services/site_provisioning.apply_contact_info`)

Setting a `Site`'s `email`/`phone` via the `PATCH` above doesn't just
save those fields — it also finds whatever already looks like an email
address or phone number anywhere on the page (every page, not just the
one currently being edited) and replaces it with the new one. Unlike the
site's name (see "Why the name can't be changed later" above), an email
or phone number has a distinctive enough shape that a plain regex can
find every occurrence directly, with no need to know what the *old*
value was and no realistic risk of a false match: `EMAIL_RE` is a
standard `local@domain.tld` pattern, and phone numbers use a digit-count
filter (`_looks_like_phone`, ≥7 actual digits) on top of a loose
candidate regex specifically to rule out things that merely *contain*
digits — a stat ("150+ Successful Projects"), a date ("February 27,
2025"), a price ("$25,000"), a range ("12-20 weeks") — none of which
should ever be mistaken for a phone number.

There's no equivalent for `address`: unlike an email or phone number, a
street address has no reliable pattern to match by regex, and the real
CoreBiz template alone splits it across two separate slots (a street
line and a city/zip line) with nothing tying them together — so this is
edited the same way any other page text is, directly on the Edit tab.

## Click-to-edit preview (`builder/views._render_site_page`, `?vicinic_edit=1`)

web-portal's editor doesn't just show a form of every slot anymore — it
embeds the site's own real rendered page in an iframe and lets the owner
click straight onto a piece of text to edit it, like Squarespace/Wix.
That's the same `site_home`/`site_page` views real visitors hit, with one
query param: `?vicinic_edit=1` makes `_resolve_slots` wrap each slot's
value in `<span class="vicinic-editable" data-vicinic-slot="...">` (skipped
for the handful of tags that can never contain an element — `<title>`,
`<option>`, `<textarea>`, `<noscript>`, and the odd bare-text-node
`[document]` case — detected from the `<tagname>` prefix
`slot_extractor.py` already puts on every slot's `label`; those stay
editable through a small fallback text-input list in web-portal instead),
and appends a small vanilla-JS "bridge" script before `</body>` that:
makes every wrapped span clickable → `contentEditable` (Enter commits,
Escape reverts), blocks all in-page link clicks (so the preview never
navigates itself away), and reports each committed edit up to the parent
frame via `postMessage({source: 'vicinic-editor', type: 'slot-changed',
key, value})` — it never calls the save API itself. `?vicinic_edit=1`
also gets `response.xframe_options_exempt = True` (only that response —
never the plain public one) since web-portal is a different origin and
the default clickjacking header would otherwise stop the iframe from
loading it at all.

**Edits are cached client-side, not saved as they happen.** web-portal
keeps a `{slot_key: value}` draft in `localStorage` (per site slug) that
every `slot-changed` message updates; nothing reaches the server until
the owner clicks "Publish changes" (`POST .../slots/`, same endpoint the
old form used). Switching pages or reloading the tab replays the current
draft back into the freshly-loaded iframe via a matching `postMessage`
the bridge script listens for, so in-progress edits keep showing even
though the server hasn't seen them yet. A "Discard changes" action just
clears the local draft and reloads the iframe to the last-published copy.

**Free-tier sites only get the home page here.** web-portal hides the
page picker and defaults straight to the home page whenever
`subscription_status != "active"`, with an upsell note in its place if
the template actually has more than one page — matching the backend's
own restriction on `POST .../slots/` above, so there's no path (UI or
direct API call) to editing another page's text without upgrading.

## Local development

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # defaults to SQLite + local disk storage if unset
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Run `frontend/portal` (`npm run dev`) to upload a template — or use
`/manage/templates/` directly if you'd rather skip running the frontend
locally. Then use `/admin/` to create a `Site` using it, fill in its slot
text, mark it "is_published", and visit `/<slug>/` to view it.

## Deploying (AWS SAM + Lambda + Mangum)

Requires the AWS SAM CLI locally, or let the `backend-deploy.yml` GitHub
Actions workflow handle it on push to `main` (or manual dispatch).

```bash
python manage.py collectstatic --noinput
sam build
sam deploy --guided   # first time only, to set up the stack config
```

Required GitHub Actions secrets: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`,
`AWS_REGION`, `DATABASE_URL` (Neon), `DJANGO_SECRET_KEY`,
`DJANGO_ALLOWED_HOSTS`, and optionally `DEFAULT_FROM_EMAIL` /
`CONTACT_RECIPIENT_EMAIL` for the generic contact-form handler,
`FRONTEND_ORIGINS` (comma-separated) for every `frontend/*` app's deployed
origin that needs to call `/api/...`, and `PAYFAST_MERCHANT_ID` /
`PAYFAST_MERCHANT_KEY` / `PAYFAST_PASSPHRASE` / `PAYFAST_SANDBOX` for real
PayFast billing (left unset, the deploy keeps PayFast's public sandbox
test-merchant defaults) — see `.env.example`.

Template assets (CSS/JS/images/fonts) are stored in an S3 bucket created by
`template.yaml` (`TemplateAssetsBucket`, public-read) — this is required,
not optional, since Lambda's filesystem is ephemeral and would otherwise
lose every uploaded template's assets between invocations.

### Known gaps (v1)

- **Email is collected but not verified, and there's no 2FA** — `User.email`
  is captured and kept unique at registration for exactly this reason, but
  nothing sends a confirmation link or enforces a second factor yet.
- **The PayFast integration hasn't been exercised against a real sandbox
  transaction yet** — the signing/verification logic and the ITN webhook's
  business logic are unit-tested (mocking the actual network call to
  PayFast, which this dev sandbox can't reach), but no one has clicked
  through PayFast's actual hosted checkout page end-to-end. Do that once
  this is deployed, before relying on it for real money.
- **No subscription-cancellation flow** — `Site.payfast_token` is stored
  for exactly this, but there's no endpoint or admin action that uses it
  yet to cancel a customer's recurring billing.
- **Theme-color detection is a heuristic, not guaranteed correct** — it
  picks whichever non-gray hex color repeats most across a template's own
  (non-vendor) CSS, which works well for the common "one accent color used
  for buttons/links/headings" case but could pick the wrong color for a
  template with a genuinely multi-color palette, or detect nothing at all
  (leaving `Template.default_primary_color` blank, so a `Site`'s color
  picker just has no useful default) if the accent color is only ever used
  once. Nothing breaks either way — a site's own `primary_color` still
  works fine, and the template's original CSS is the fallback either way
  — but it's worth a spot-check on a newly uploaded template.
- **Header/nav/footer text is duplicated per page, not truly shared**, for
  templates (like the bundled Axis example) where Templify couldn't hoist
  the header into `base.html` because it differs slightly per page (e.g.
  active-nav-state markup). Editing a nav label on one page won't update
  it on others. Global slots (`page=None`) only cover what Templify's own
  `base.html` actually contains.
- **Per-page `<title>`/SEO metadata isn't distinct per page** — the title
  block from `base.html`'s default is treated as one shared slot rather
  than parameterized per page, to keep v1 scope manageable.
- **AWS credentials in the GitHub Actions workflow use long-lived access
  keys**, not OIDC role assumption. Works, just less secure than the
  modern approach.
- **`/api/...` (the portal app's, `api_views.py`) auth is a cross-origin
  session cookie** (`SameSite=None`), not a token scheme — see
  `../frontend/README.md`'s "Known limitation" section for the
  browser-compatibility caveat this carries. `/api/customer/...` (this
  section) doesn't have this problem — it already moved to bearer tokens
  after hitting the same failure mode in practice.
