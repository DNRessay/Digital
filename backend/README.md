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

Session-cookie authenticated like the portal's `/api/...`, but for any
regular authenticated `User` (no superuser check) rather than staff — a
dedicated `/api/customer/login/` endpoint handles this since Django admin's
own login form (`AdminAuthenticationForm`) rejects non-staff users outright.

- `GET /api/customer/whoami/` — `{authenticated, username}` (also the
  endpoint the SPA calls first to pick up a CSRF cookie before logging in).
- `POST /api/customer/login/`, `POST /api/customer/logout/`
- `GET /api/customer/templates/` — public, no auth required: the `is_active`
  `Template`s, for the "create your site" form's picker.
- `POST /api/customer/register/` — public. Body: `{username, password}`.
  Validates the password against Django's own `AUTH_PASSWORD_VALIDATORS`
  (409 if the username is already taken), creates just the `User`, and logs
  them in — no `Site` yet.
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
- `GET /api/customer/packages/` — public: the three packages (id, label,
  monthly, setup) for the "remove branding" picker.
- `POST /api/customer/sites/<slug>/checkout/` — authenticated. See "PayFast
  subscriptions" above.

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

- **The PayFast integration hasn't been exercised against a real sandbox
  transaction yet** — the signing/verification logic and the ITN webhook's
  business logic are unit-tested (mocking the actual network call to
  PayFast, which this dev sandbox can't reach), but no one has clicked
  through PayFast's actual hosted checkout page end-to-end. Do that once
  this is deployed, before relying on it for real money.
- **No subscription-cancellation flow** — `Site.payfast_token` is stored
  for exactly this, but there's no endpoint or admin action that uses it
  yet to cancel a customer's recurring billing.
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
- **`/api/...` auth is a cross-origin session cookie** (`SameSite=None`),
  not a token scheme — see `../frontend/README.md`'s "Known limitation"
  section for the browser-compatibility caveat this carries.
