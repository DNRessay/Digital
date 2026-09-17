# Viincci Digital — Site Builder Backend

Django backend for the self-service website builder. Content for each client
site (hero text, services, gallery, testimonials, colors) is edited entirely
through the stock Django admin — no custom admin UI. The theme templates in
`../frontend/themes/<theme>/` render whatever content is stored per `Site`.

## Local development

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # defaults to SQLite if DATABASE_URL is unset
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Visit `/admin/` to create a `Site`, fill in its Hero/About/Services/Gallery/
Testimonials inline, mark it "is_published", then visit `/<slug>/` to view it.

## Adding a new theme

1. Add the theme to `THEME_CHOICES` in `builder/models.py`.
2. Create `backend/templates/themes/<theme>/index.html` extending `base.html`.
3. Create `frontend/themes/<theme-slug>/css/theme.css` for its look.

The content model (`Site`, `HeroContent`, `AboutContent`, `Service`,
`GalleryImage`, `Testimonial`) is shared across every theme, so switching a
site's theme doesn't require re-entering its content.

## Deploying (AWS SAM + Lambda + Mangum)

Requires the AWS SAM CLI locally, or let the `backend-deploy.yml` GitHub
Actions workflow handle it on push to `main`.

```bash
python manage.py collectstatic --noinput
sam build
sam deploy --guided   # first time only, to set up the stack config
```

Required GitHub Actions secrets: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`,
`AWS_REGION`, `DATABASE_URL` (Neon), `DJANGO_SECRET_KEY`,
`DJANGO_ALLOWED_HOSTS`.

### Known gaps (v1)

- **Media uploads don't persist on Lambda.** Lambda's filesystem is
  ephemeral, so uploaded images will vanish between invocations in
  production. Swap `MEDIA` storage for S3 (e.g. `django-storages`) before
  using image uploads in production.
- **AWS credentials use long-lived access keys** in the GitHub Actions
  workflow for simplicity. Consider moving to OIDC role assumption later.
