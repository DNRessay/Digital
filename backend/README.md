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

Templates are added at **`/manage/templates/`** — a small custom page (not
the Django admin), restricted to superusers. Upload a zip of a static HTML
template (the usual multi-page-with-`assets/`-folder layout); it's sent to
the deployed Templify conversion service (`TEMPLIFY_FUNCTION_URL`), then
`builder/services/template_ingest.py` turns the result into a `Template`
with its pages/slots/assets. No redeploy required — it's available to
customers immediately.

Editing a customer's site content (which template, colors, contact info,
and each slot's text) is done through the **normal Django admin** at
`/admin/` — that part is exactly as the stock admin provides.

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

Visit `/manage/templates/` to upload a template, then `/admin/` to create a
`Site` using it, fill in its slot text, mark it "is_published", and visit
`/<slug>/` to view it.

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
`CONTACT_RECIPIENT_EMAIL` for the generic contact-form handler.

Template assets (CSS/JS/images/fonts) are stored in an S3 bucket created by
`template.yaml` (`TemplateAssetsBucket`, public-read) — this is required,
not optional, since Lambda's filesystem is ephemeral and would otherwise
lose every uploaded template's assets between invocations.

### Known gaps (v1)

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
